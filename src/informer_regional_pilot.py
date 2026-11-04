"""Small regional Informer adaptation for a matched development pilot.

Reuses the repository's encoder/decoder modules, not old data or checkpoints.
ProbSparse query count follows factor*ceil(log(Lq)), as in the author's code:
https://raw.githubusercontent.com/zhouhaoyi/Informer2020/main/models/attn.py
Evaluation key sampling is fixed for reproducible replay. Daily Tweedie/BCE
heads, calendar scaling and meteorological decoder prefix are adaptations.
"""
from __future__ import annotations

import math
import torch
from torch import nn
from torch.nn import functional as F

from src.informer.attention import ProbAttention, FullAttention, AttentionLayer
from src.informer.encoder import Encoder, EncoderLayer, ConvLayer
from src.informer.decoder import Decoder, DecoderLayer
from src.informer.embed import DataEmbedding


class RegionalProbAttention(ProbAttention):
    def _prob_QK(self, Q, K, sample_k, n_top):
        B,H,LK,D=K.shape;LQ=Q.shape[2]
        if self.training:
            index=torch.randint(LK,(LQ,sample_k),device=K.device)
        else:
            generator=torch.Generator(device=K.device).manual_seed(20261021)
            index=torch.randint(LK,(LQ,sample_k),generator=generator,device=K.device)
        sampled=K.unsqueeze(-3).expand(B,H,LQ,LK,D)[:,:,torch.arange(LQ,device=K.device)[:,None],index,:]
        scores=(Q.unsqueeze(-2) @ sampled.transpose(-2,-1)).squeeze(-2)
        sparsity=scores.max(-1).values-scores.sum(-1)/LK
        selected=sparsity.topk(n_top,sorted=False).indices
        reduced=Q[torch.arange(B,device=Q.device)[:,None,None],torch.arange(H,device=Q.device)[None,:,None],selected]
        return reduced,selected

    def forward(self,queries,keys,values,attn_mask=None):
        B,LQ,H,D=queries.shape;LK=keys.shape[1]
        q,k,v=[x.transpose(1,2) for x in (queries,keys,values)]
        sample_k=min(LK,max(1,self.factor*math.ceil(math.log(max(LK,2)))))
        n_top=min(LQ,max(1,self.factor*math.ceil(math.log(max(LQ,2)))))
        reduced,index=self._prob_QK(q,k,sample_k,n_top)
        scores=(reduced @ k.transpose(-2,-1))*(self.scale or D**-.5)
        context=self._get_initial_context(v,LQ)
        context=self._update_context(context,v,scores,index,LQ,attn_mask)
        return context.transpose(1,2).contiguous(),None


class RegionalInformer(nn.Module):
    def __init__(self,input_features,time_indices,hidden=32,heads=4,factor=3,dropout=.1,label_len=14):
        super().__init__()
        self.config=dict(input_features=input_features,time_indices=list(time_indices),hidden=hidden,
                         heads=heads,factor=factor,dropout=dropout,label_len=label_len)
        self.label_len=label_len;self.time_indices=list(time_indices)
        self.register_buffer("time_center",torch.zeros(4));self.register_buffer("time_scale",torch.ones(4))
        self.enc_embedding=DataEmbedding(input_features,hidden,"timeF","h",dropout)
        self.dec_embedding=DataEmbedding(input_features,hidden,"timeF","h",dropout)
        self.encoder=Encoder([EncoderLayer(AttentionLayer(RegionalProbAttention(False,factor,attention_dropout=dropout),hidden,heads),
                            hidden,2*hidden,dropout,"gelu") for _ in range(2)],
                            [ConvLayer(hidden)],nn.LayerNorm(hidden))
        self.decoder=Decoder([DecoderLayer(
            AttentionLayer(FullAttention(True,attention_dropout=dropout),hidden,heads),
            AttentionLayer(FullAttention(False,attention_dropout=dropout),hidden,heads),
            hidden,2*hidden,dropout,"gelu")],nn.LayerNorm(hidden))
        self.amount=nn.Linear(4*hidden,1);self.events=nn.Linear(4*hidden,3)

    def set_scaler(self,scaler):
        self.time_center.copy_(torch.as_tensor(scaler['center'][self.time_indices],device=self.time_center.device))
        self.time_scale.copy_(torch.as_tensor(scaler['scale'][self.time_indices],device=self.time_scale.device))

    def forward(self,past,calendar):
        if past.shape[1]!=28 or calendar.shape[1:]!=(12,4):raise ValueError("Expected 28 past /12 calendar steps")
        past_marks=past[:,:,self.time_indices]
        future_marks=(calendar-self.time_center)/self.time_scale
        dec_values=torch.cat([past[:,-self.label_len:],past.new_zeros(len(past),12,past.shape[-1])],1)
        dec_marks=torch.cat([past_marks[:,-self.label_len:],future_marks],1)
        enc,_=self.encoder(self.enc_embedding(past,past_marks))
        latent,_,_=self.decoder(self.dec_embedding(dec_values,dec_marks),enc)
        days=latent[:,-12:].reshape(len(past),3,-1)
        return F.softplus(self.amount(days).squeeze(-1))+1e-4,self.events(days)
