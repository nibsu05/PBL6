import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, List, Tuple

class DecoderLayer(nn.Module):
    """
    Lớp giải mã (Decoder Layer) với self-attention, cross-attention và mạng nơ-ron truyền thẳng (FFN).
    """
    def __init__(self, self_attention: nn.Module, cross_attention: nn.Module, d_model: int, d_ff: Optional[int] = None, dropout: float = 0.1, activation: str = "relu"):
        super(DecoderLayer, self).__init__()
        d_ff = d_ff or 4 * d_model
        
        self.self_attention = self_attention
        self.cross_attention = cross_attention
        
        self.conv1 = nn.Conv1d(in_channels=d_model, out_channels=d_ff, kernel_size=1)
        self.conv2 = nn.Conv1d(in_channels=d_ff, out_channels=d_model, kernel_size=1)
        
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.norm3 = nn.LayerNorm(d_model)
        
        self.dropout = nn.Dropout(dropout)
        self.activation = F.relu if activation == "relu" else F.gelu

    def forward(self, x: torch.Tensor, cross: torch.Tensor, x_mask: Optional[torch.Tensor] = None, cross_mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[torch.Tensor]]:
        # Sub-layer 1: Self Attention (Masked)
        x_new, self_attn = self.self_attention(x, x, x, attn_mask=x_mask)
        x = x + self.dropout(x_new)
        x = self.norm1(x)

        # Sub-layer 2: Cross Attention ( attending to Encoder output)
        x_new, cross_attn = self.cross_attention(x, cross, cross, attn_mask=cross_mask)
        x = x + self.dropout(x_new)
        x = self.norm2(x)

        # Sub-layer 3: Feed Forward Network
        y = x.transpose(-1, -2) # (B, d_model, L)
        y = self.dropout(self.activation(self.conv1(y)))
        y = self.dropout(self.conv2(y))
        y = y.transpose(-1, -2) # (B, L, d_model)
        
        x = x + y
        x = self.norm3(x)

        return x, self_attn, cross_attn

class Decoder(nn.Module):
    """
    Bộ giải mã (Decoder) bao gồm nhiều DecoderLayer và một lớp chuẩn hóa (LayerNorm) cuối cùng.
    """
    def __init__(self, layers: List[nn.Module], norm_layer: Optional[nn.Module] = None):
        super(Decoder, self).__init__()
        self.layers = nn.ModuleList(layers)
        self.norm = norm_layer

    def forward(self, x: torch.Tensor, cross: torch.Tensor, x_mask: Optional[torch.Tensor] = None, cross_mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, List[Optional[torch.Tensor]], List[Optional[torch.Tensor]]]:
        self_attns = []
        cross_attns = []
        
        for layer in self.layers:
            x, self_attn, cross_attn = layer(x, cross, x_mask=x_mask, cross_mask=cross_mask)
            self_attns.append(self_attn)
            cross_attns.append(cross_attn)
            
        if self.norm is not None:
            x = self.norm(x)

        return x, self_attns, cross_attns
