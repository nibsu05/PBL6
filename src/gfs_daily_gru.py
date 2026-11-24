"""Small dual-functional GRU with nested wet/conditional-heavy event heads."""
from __future__ import annotations
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import copy
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader,TensorDataset
from src.gfs_daily import FEATURES,HISTORY,score_bundle


class DailyGRU(nn.Module):
    def __init__(self, context_channels, hidden=24, head=32):
        super().__init__();self.encoder=nn.GRU(1,hidden,batch_first=True);self.station=nn.Embedding(86,4)
        self.heads=nn.ModuleList([nn.Sequential(nn.Linear(hidden+4+context_channels,head),nn.ReLU(),nn.Dropout(.1),nn.Linear(head,4)) for _ in range(3)])
    def forward(self, history, context, station):
        _,encoded=self.encoder(history);shared=torch.cat([encoded[-1],self.station(station)],1)
        out=torch.stack([head(torch.cat([shared,context[:,j]],1)) for j,head in enumerate(self.heads)],1)
        return nn.functional.softplus(out[:,:,:2])+1e-5,out[:,:,2:]


def loss_function(point, logits, target_scaled, events):
    mean,median=point[:,:,0],point[:,:,1]
    amount=(2*target_scaled/torch.sqrt(mean)+2*torch.sqrt(mean)).mean()
    pinball=.5*torch.abs(target_scaled-median).mean()
    wet=nn.functional.binary_cross_entropy_with_logits(logits[:,:,0],events[:,:,0])
    conditional=nn.functional.binary_cross_entropy_with_logits(logits[:,:,1],events[:,:,1],reduction='none')
    conditional=(conditional*events[:,:,0]).sum()/events[:,:,0].sum().clamp_min(1)
    return amount+pinball+.5*(wet+conditional)


def arrays(frame, config):
    n=len(frame)//3
    if len(frame)%3 or not np.array_equal(frame.horizon.to_numpy().reshape(n,3),np.tile([1,2,3],(n,1))):
        raise ValueError('GRU requires sorted complete horizon packs')
    names=[c for c in FEATURES[config] if c not in HISTORY+['station_code']]
    history=np.log1p(frame[HISTORY].to_numpy('float32').reshape(n,3,7)[:,0,::-1,None].copy())
    context=frame[names].to_numpy('float32').reshape(n,3,-1)
    station=frame.station_code.to_numpy('int64').reshape(n,3)[:,0]
    y=frame.y_mm.to_numpy('float32').reshape(n,3)
    events=np.stack([y>=1,y>=50],-1).astype('float32')
    return dict(history=history,context=context,station=station,y=y,events=events,names=names)


def normalizers(raw, train):
    if not np.asarray(train).any():raise ValueError('Empty training mask')
    return dict(history_mean=float(raw['history'][train].mean()),history_std=max(float(raw['history'][train].std()),1e-5),
        context_mean=raw['context'][train].mean((0,1)),context_std=np.maximum(raw['context'][train].std((0,1)),1e-5),
        target_scale=max(float(raw['y'][train].mean()),1.))


def tensors(raw, norm):
    values=[(raw['history']-norm['history_mean'])/norm['history_std'],
        (raw['context']-norm['context_mean'])/norm['context_std'],raw['station'],raw['y']/norm['target_scale'],raw['events']]
    return [torch.from_numpy(np.array(v,copy=True)) for v in values]


def predict(model, inputs, scale, device, chunk=1024):
    point=[];prob=[];model.eval()
    with torch.no_grad():
        for start in range(0,len(inputs[0]),chunk):
            a,b=model(*[t[start:start+chunk].to(device) for t in inputs[:3]])
            point.append(a.cpu().numpy()*scale);prob.append(torch.sigmoid(b).cpu().numpy())
    point=np.concatenate(point);prob=np.concatenate(prob)
    return dict(mean=point[:,:,0],median=point[:,:,1],wet=prob[:,:,0],conditional=prob[:,:,1])


def train_network(frame, config, train, valid, candidate, seed, max_epochs, patience, callback=None):
    raw=arrays(frame,config);norm=normalizers(raw,train);inputs=tensors(raw,norm)
    torch.set_num_threads(4);torch.manual_seed(seed);np.random.seed(seed)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    if device.type=='cuda':torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.use_deterministic_algorithms(True,warn_only=True)
    model=DailyGRU(len(raw['names']),candidate['hidden'],candidate['head']).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=candidate['lr'],weight_decay=.001)
    loader=DataLoader(TensorDataset(*[t[train] for t in inputs]),batch_size=256,shuffle=True,
        generator=torch.Generator().manual_seed(seed),num_workers=0)
    best=np.inf;best_epoch=0;best_state=None;stale=0;curves=[]
    validation=None if valid is None else [t[valid] for t in inputs]
    n=len(raw['y']);first=frame.iloc[::3].reset_index(drop=True)
    for epoch in range(1,max_epochs+1):
        model.train();total=0.;seen=0
        for batch in loader:
            h,c,s,target,event=[t.to(device) for t in batch]
            optimizer.zero_grad(set_to_none=True);point,logits=model(h,c,s)
            loss=loss_function(point,logits,target,event)
            if not torch.isfinite(loss):raise ValueError('Nonfinite neural training loss')
            loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step()
            total+=float(loss.detach().cpu())*len(h);seen+=len(h)
        row=dict(epoch=epoch,train_loss=total/max(seen,1))
        if valid is not None:
            out=predict(model,validation,norm['target_scale'],device);scores=[]
            for h in range(3):
                gfs=frame.gfs_rain_mm.to_numpy().reshape(n,3)[valid,h]
                scores.append(score_bundle(raw['y'][valid,h],out['mean'][:,h],out['median'][:,h],out['wet'][:,h],out['conditional'][:,h],
                    first.loc[valid,'station_id'],gfs,raw['y'][train,h]))
            value=float(np.mean([s['joint_score'] for s in scores]));row['valid_joint_score']=value
            if value<best-1e-5:
                best=value;best_epoch=epoch;best_state=copy.deepcopy(model.state_dict());stale=0
            else:stale+=1
        else:best_epoch=epoch
        curves.append(row)
        if callback:callback(row)
        if valid is not None and stale>=patience:break
    if valid is not None:model.load_state_dict(best_state)
    artifact=dict(state={k:v.detach().cpu() for k,v in model.state_dict().items()},normalizers=norm,
        features=raw['names'],config=config,candidate=candidate,seed=seed,best_epoch=best_epoch,
        epochs=epoch,validation_score=None if valid is None else best,parameter_count=sum(p.numel() for p in model.parameters()),
        device=str(device),curves=curves)
    out=predict(model,inputs,norm['target_scale'],device)
    del model
    if device.type=='cuda':torch.cuda.empty_cache()
    return artifact,out


def replay(frame, artifact):
    raw=arrays(frame,artifact['config']);inputs=tensors(raw,artifact['normalizers'])
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');c=artifact['candidate']
    model=DailyGRU(len(raw['names']),c['hidden'],c['head']).to(device);model.load_state_dict(artifact['state'])
    result=predict(model,inputs,artifact['normalizers']['target_scale'],device)
    del model
    if device.type=='cuda':torch.cuda.empty_cache()
    return result
