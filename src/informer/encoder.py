import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, List, Tuple

class ConvLayer(nn.Module):
    """
    Lớp chưng cất (Distilling Layer) dùng 1D Convolution và MaxPool để giảm một nửa chiều dài chuỗi.
    Được sử dụng giữa các lớp encoder để làm nổi bật thông tin chính.
    """
    def __init__(self, c_in: int):
        super(ConvLayer, self).__init__()
        self.downConv = nn.Conv1d(in_channels=c_in,
                                  out_channels=c_in,
                                  kernel_size=3,
                                  padding=1)
        self.norm = nn.BatchNorm1d(c_in)
        self.activation = nn.ELU()
        self.maxPool = nn.MaxPool1d(kernel_size=3, stride=2, padding=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (B, L, d_model) -> permute -> (B, d_model, L)
        x = self.downConv(x.permute(0, 2, 1))
        x = self.norm(x)
        x = self.activation(x)
        x = self.maxPool(x)
        # return shape: (B, L/2, d_model)
        x = x.transpose(1, 2)
        return x

class EncoderLayer(nn.Module):
    """
    Lớp mã hóa cơ bản (Encoder Layer) của mô hình Transformer, thường sử dụng ProbSparse Attention.
    """
    def __init__(self, attention: nn.Module, d_model: int, d_ff: Optional[int] = None, dropout: float = 0.1, activation: str = "relu"):
        super(EncoderLayer, self).__init__()
        d_ff = d_ff or 4 * d_model
        self.attention = attention
        self.conv1 = nn.Conv1d(in_channels=d_model, out_channels=d_ff, kernel_size=1)
        self.conv2 = nn.Conv1d(in_channels=d_ff, out_channels=d_model, kernel_size=1)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)
        self.activation = F.relu if activation == "relu" else F.gelu

    def forward(self, x: torch.Tensor, attn_mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        # Sub-layer 1: Attention
        new_x, attn = self.attention(x, x, x, attn_mask=attn_mask)
        x = x + self.dropout(new_x)
        x = self.norm1(x)

        # Sub-layer 2: Feed Forward Network
        y = x.transpose(-1, -2) # (B, d_model, L)
        y = self.dropout(self.activation(self.conv1(y)))
        y = self.dropout(self.conv2(y))
        y = y.transpose(-1, -2) # (B, L, d_model)
        
        x = x + y
        x = self.norm2(x)

        return x, attn

class Encoder(nn.Module):
    """
    Bộ mã hóa (Encoder) gồm một chồng các EncoderLayer xen kẽ với ConvLayer (chưng cất).
    """
    def __init__(self, attn_layers: List[nn.Module], conv_layers: Optional[List[nn.Module]] = None, norm_layer: Optional[nn.Module] = None):
        super(Encoder, self).__init__()
        self.attn_layers = nn.ModuleList(attn_layers)
        self.conv_layers = nn.ModuleList(conv_layers) if conv_layers is not None else None
        self.norm = norm_layer

    def forward(self, x: torch.Tensor, attn_mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, List[Optional[torch.Tensor]]]:
        attns = []
        for i, attn_layer in enumerate(self.attn_layers):
            x, attn = attn_layer(x, attn_mask=attn_mask)
            attns.append(attn)
            
            # Áp dụng ConvLayer nếu có
            if self.conv_layers is not None and i < len(self.conv_layers):
                x = self.conv_layers[i](x)

        if self.norm is not None:
            x = self.norm(x)

        return x, attns
