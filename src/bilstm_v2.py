"""Bi-LSTM pipeline v2: lịch sử, đặc trưng tĩnh, tương lai perfect prog và xác suất tổng mưa.

Hai đầu: lượng mưa giờ ở thang log1p; logits cho tổng 0–3/3–6/0–6 h >= 1/10/25 mm.
Bi-directional chỉ đọc cửa sổ quá khứ; đầu vào tương lai là dự báo số và lịch đã biết.
"""
from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F

AGG_WINDOWS = ((0, 3), (3, 6), (0, 6))
THRESHOLDS = (1.0, 10.0, 25.0)


class BiLSTMV2(nn.Module):
    def __init__(self, past_dim: int, future_dim: int, static_dim: int = 8,
                 hidden_dim: int = 64, dropout: float = 0.1):
        super().__init__()
        self.encoder = nn.LSTM(past_dim, hidden_dim, num_layers=2, bidirectional=True,
                               batch_first=True, dropout=dropout)
        self.static = nn.Sequential(nn.Linear(static_dim, hidden_dim), nn.ReLU())
        context_dim = hidden_dim * 3
        self.amount = nn.Sequential(nn.Linear(context_dim + future_dim, hidden_dim), nn.ReLU(),
                                    nn.Dropout(dropout), nn.Linear(hidden_dim, 1), nn.Softplus())
        self.events = nn.Sequential(nn.Linear(context_dim + 6 * future_dim, hidden_dim), nn.ReLU(),
                                    nn.Dropout(dropout), nn.Linear(hidden_dim, 9))

    def forward(self, x_past, x_future, static):
        _, (h, _) = self.encoder(x_past)
        context = torch.cat((h[-2], h[-1], self.static(static)), dim=-1)
        steps = torch.cat((context[:, None, :].expand(-1, 6, -1), x_future), dim=-1)
        return self.amount(steps).squeeze(-1), self.events(torch.cat((context, x_future.flatten(1)), dim=-1))


def aggregate_targets(y: torch.Tensor) -> torch.Tensor:
    totals = torch.stack([y[:, lo:hi].sum(1) for lo, hi in AGG_WINDOWS], dim=1)
    thresholds = y.new_tensor(THRESHOLDS)
    return (totals[:, :, None] >= thresholds).to(y.dtype).flatten(1)


def pilot_loss(amount_log, logits, y):
    # BCE không tăng trọng số lớp dương: trọng số như vậy làm méo xác suất và BSS.
    return F.smooth_l1_loss(amount_log, torch.log1p(y.clamp_min(0))) + \
        F.binary_cross_entropy_with_logits(logits, aggregate_targets(y))
