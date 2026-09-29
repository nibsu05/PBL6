"""Kiến trúc Bi-LSTM dự báo đồng thời 1–6 giờ tới."""

from __future__ import annotations

import torch
from torch import nn


class BiLSTM(nn.Module):
    """Đọc 24 giờ quan trắc và xuất lượng mưa cho các giờ kế tiếp.

    Tầng LSTM hai chiều chỉ đọc *quá khứ trong cửa sổ đầu vào*. Nó không
    nhận quan trắc của các giờ cần dự báo, nên không rò rỉ nhãn tương lai.
    """

    def __init__(
        self,
        input_dim: int,
        output_dim: int = 6,
        hidden_dim: int = 50,
        num_layers: int = 2,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        if input_dim < 1 or output_dim < 1:
            raise ValueError("input_dim và output_dim phải lớn hơn 0")
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 3:
            raise ValueError("Đầu vào phải có dạng (batch, sequence, feature)")
        _, (hidden, _) = self.lstm(x)
        # hidden[-2] và hidden[-1] là hai chiều ở lớp LSTM cuối cùng.
        context = torch.cat((hidden[-2], hidden[-1]), dim=-1)
        return self.head(context)
