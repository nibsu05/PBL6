"""Regional TFT adaptation: no static covariates, daily mean/event readouts.

Architecture references (independent PyTorch implementation, not a port):
https://arxiv.org/abs/1912.09363
https://github.com/google-research/google-research/tree/master/tft
Changes: no static context, 6-hour sequence, three daily Tweedie/BCE heads.
"""
from __future__ import annotations

import math
import torch
from torch import nn
from torch.nn import functional as F


class GateAddNorm(nn.Module):
    def __init__(self, hidden, dropout):
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        self.gate = nn.Linear(hidden, 2 * hidden)
        self.norm = nn.LayerNorm(hidden)

    def forward(self, value, residual):
        return self.norm(residual + F.glu(self.gate(self.dropout(value)), dim=-1))


class GRN(nn.Module):
    def __init__(self, inputs, hidden, outputs=None, dropout=.1):
        super().__init__()
        outputs = hidden if outputs is None else outputs
        self.first = nn.Linear(inputs, hidden)
        self.second = nn.Linear(hidden, outputs)
        self.residual = nn.Identity() if inputs == outputs else nn.Linear(inputs, outputs)
        self.finish = GateAddNorm(outputs, dropout)

    def forward(self, x):
        return self.finish(self.second(F.elu(self.first(x))), self.residual(x))


class VariableSelection(nn.Module):
    """Separate scalar embeddings and feature-specific GRNs, vectorized over F."""
    def __init__(self, features, hidden, dropout):
        super().__init__()
        self.features, self.hidden = features, hidden
        self.embedding_weight = nn.Parameter(torch.randn(features, hidden) * .1)
        self.embedding_bias = nn.Parameter(torch.zeros(features, hidden))
        self.w1 = nn.Parameter(torch.empty(features, hidden, hidden))
        self.w2 = nn.Parameter(torch.empty(features, hidden, hidden))
        self.wg = nn.Parameter(torch.empty(features, hidden, 2 * hidden))
        self.b1 = nn.Parameter(torch.zeros(features, hidden))
        self.b2 = nn.Parameter(torch.zeros(features, hidden))
        self.bg = nn.Parameter(torch.zeros(features, 2 * hidden))
        self.norm_weight = nn.Parameter(torch.ones(features, hidden))
        self.norm_bias = nn.Parameter(torch.zeros(features, hidden))
        self.weight_network = GRN(features * hidden, hidden, features, dropout)
        self.dropout = nn.Dropout(dropout)
        for weights in [self.w1, self.w2, self.wg]:
            for feature_weights in weights:
                nn.init.xavier_uniform_(feature_weights)

    def forward(self, x):
        embedded = x[..., None] * self.embedding_weight + self.embedding_bias
        weights = self.weight_network(embedded.flatten(-2)).softmax(-1)
        z = F.elu(torch.einsum('btfi,fij->btfj', embedded, self.w1) + self.b1)
        z = torch.einsum('btfi,fij->btfj', z, self.w2) + self.b2
        z = F.glu(torch.einsum('btfi,fij->btfj', self.dropout(z), self.wg) + self.bg, dim=-1)
        transformed = F.layer_norm(embedded + z, (self.hidden,))
        transformed = transformed * self.norm_weight + self.norm_bias
        return (weights[..., None] * transformed).sum(-2), weights


class InterpretableAttention(nn.Module):
    """Head-specific queries/keys; shared values, mean heads (TFT attention)."""
    def __init__(self, hidden, heads, dropout):
        super().__init__()
        if hidden % heads:
            raise ValueError('hidden must be divisible by attention heads')
        self.heads, self.dim = heads, hidden // heads
        self.q = nn.Linear(hidden, hidden, bias=False)
        self.k = nn.Linear(hidden, hidden, bias=False)
        self.v = nn.Linear(hidden, self.dim, bias=False)
        self.out = nn.Linear(self.dim, hidden, bias=False)
        self.dropout = nn.Dropout(dropout)

    def forward(self, sequence, history_steps):
        batch, length, _ = sequence.shape
        q = self.q(sequence[:, history_steps:]).reshape(batch, -1, self.heads, self.dim).transpose(1, 2)
        k = self.k(sequence).reshape(batch, length, self.heads, self.dim).transpose(1, 2)
        scores = q @ k.transpose(-1, -2) / math.sqrt(self.dim)
        future_steps = length - history_steps
        mask = torch.arange(length, device=sequence.device)[None, :] > (
            history_steps + torch.arange(future_steps, device=sequence.device)[:, None])
        weights = scores.masked_fill(mask, float('-inf')).softmax(-1)
        values = self.v(sequence)[:, None]
        attended = self.dropout(weights @ values).mean(1)
        return self.dropout(self.out(attended)), weights


class RegionalTFT(nn.Module):
    def __init__(self, input_features, hidden=32, heads=4, dropout=.1):
        super().__init__()
        self.config = dict(input_features=input_features, hidden=hidden, heads=heads, dropout=dropout)
        self.past_selection = VariableSelection(input_features, hidden, dropout)
        self.future_selection = VariableSelection(4, hidden, dropout)
        self.encoder = nn.LSTM(hidden, hidden, batch_first=True)
        self.decoder = nn.LSTM(hidden, hidden, batch_first=True)
        self.post_lstm = GateAddNorm(hidden, dropout)
        self.enrichment = GRN(hidden, hidden, dropout=dropout)
        self.attention = InterpretableAttention(hidden, heads, dropout)
        self.post_attention = GateAddNorm(hidden, dropout)
        self.positionwise = GRN(hidden, hidden, dropout=dropout)
        self.final = GateAddNorm(hidden, dropout)
        self.amount = nn.Linear(4 * hidden, 1)
        self.events = nn.Linear(4 * hidden, 3)

    def forward(self, past, calendar, return_details=False):
        if past.shape[1] != 28 or calendar.shape[1:] != (12, 4):
            raise ValueError('Expected past[B,28,F], calendar[B,12,4]')
        p, pw = self.past_selection(past)
        c, cw = self.future_selection(calendar)
        encoded, state = self.encoder(p)
        decoded, _ = self.decoder(c, state)
        selected = torch.cat([p, c], 1)
        recurrent = self.post_lstm(torch.cat([encoded, decoded], 1), selected)
        enriched = self.enrichment(recurrent)
        attended, attention = self.attention(enriched, 28)
        combined = self.post_attention(attended, enriched[:, 28:])
        latent = self.final(self.positionwise(combined), recurrent[:, 28:])
        days = latent.reshape(len(past), 3, -1)
        amount = F.softplus(self.amount(days).squeeze(-1)) + 1e-4
        logits = self.events(days)
        if return_details:
            return amount, logits, {'past_weights': pw, 'future_weights': cw, 'attention': attention}
        return amount, logits


def daily_tweedie_deviance(mu, target):
    mu = mu.clamp_min(1e-3)
    return (4 * (target / mu.sqrt() + mu.sqrt() - 2 * target.clamp_min(0).sqrt())).clamp_min(0)


def daily_joint_loss(amount, logits, target, null_scale):
    thresholds = target.new_tensor([16., 50., 100.])
    events = (target[..., None] >= thresholds).to(target.dtype)
    deviance = (daily_tweedie_deviance(amount, target) / null_scale).mean()
    return deviance + F.binary_cross_entropy_with_logits(logits, events)
