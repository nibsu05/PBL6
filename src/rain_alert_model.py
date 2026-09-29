"""Bi-LSTM hai đầu ra: lượng mưa và xác suất vượt 5 mm/h.

Chỉ có 24 giờ quá khứ đi vào cả hai đầu; không có thông tin tương lai.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn
from torch.nn import functional as F


class RainAlertBiLSTM(nn.Module):
    def __init__(self, input_dim: int, output_dim: int = 6, hidden_dim: int = 50,
                 dropout: float = 0.2) -> None:
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers=2, dropout=dropout,
                            batch_first=True, bidirectional=True)
        self.shared = nn.Sequential(nn.Dropout(dropout), nn.Linear(hidden_dim * 2, hidden_dim),
                                    nn.ReLU())
        self.amount_head = nn.Linear(hidden_dim, output_dim)
        self.heavy_head = nn.Linear(hidden_dim, output_dim)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if x.ndim != 3:
            raise ValueError("X phải có dạng (batch, 24 giờ, số đặc trưng)")
        _, (hidden, _) = self.lstm(x)
        context = self.shared(torch.cat((hidden[-2], hidden[-1]), dim=-1))
        return F.softplus(self.amount_head(context)), self.heavy_head(context)


@dataclass(frozen=True)
class RainAlertConfig:
    max_epochs: int = 30
    patience: int = 7
    learning_rate: float = 0.001
    heavy_threshold_mm_h: float = 5.0
    amount_heavy_weight: float = 4.0
    classification_pos_weight: float = 12.0
    classification_loss_weight: float = 0.5
    seed: int = 42


def rain_alert_loss(amount: torch.Tensor, logit: torch.Tensor, target: torch.Tensor,
                    config: RainAlertConfig) -> tuple[torch.Tensor, dict[str, float]]:
    """Huber có trọng số cho lượng mưa; BCE cho xác suất mưa lớn."""
    if amount.shape != target.shape or logit.shape != target.shape:
        raise ValueError("Hai đầu ra phải khớp nhãn (batch, 6)")
    heavy = target > config.heavy_threshold_mm_h
    weight = torch.where(heavy, config.amount_heavy_weight, 1.0)
    amount_loss = (weight * F.smooth_l1_loss(amount, target, beta=1.0, reduction="none")).mean()
    classification_loss = F.binary_cross_entropy_with_logits(
        logit, heavy.float(), pos_weight=torch.tensor(config.classification_pos_weight,
                                                      device=logit.device),
    )
    total = amount_loss + config.classification_loss_weight * classification_loss
    return total, {"amount": float(amount_loss.detach()),
                   "classification": float(classification_loss.detach())}
