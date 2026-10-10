import torch
import torch.nn as nn
import math

class TokenEmbedding(nn.Module):
    """
    Nhúng giá trị (Token Embedding) sử dụng 1D Convolution để chiếu các đặc trưng thô lên không gian d_model.
    """
    def __init__(self, c_in: int, d_model: int):
        super(TokenEmbedding, self).__init__()
        # Sử dụng nn.Conv1d theo yêu cầu
        self.tokenConv = nn.Conv1d(in_channels=c_in, out_channels=d_model,
                                   kernel_size=3, padding=1, padding_mode='circular')
        for m in self.modules():
            if isinstance(m, nn.Conv1d):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='leaky_relu')

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (B, L, c_in) -> permute -> (B, c_in, L) -> conv1d -> (B, d_model, L) -> permute -> (B, L, d_model)
        x = self.tokenConv(x.permute(0, 2, 1)).transpose(1, 2)
        return x

class PositionalEmbedding(nn.Module):
    """
    Nhúng vị trí (Positional Embedding) sử dụng hàm sin và cos (theo chuẩn Transformer).
    """
    def __init__(self, d_model: int, max_len: int = 5000):
        super(PositionalEmbedding, self).__init__()
        # Tính toán PE 1 lần
        pe = torch.zeros(max_len, d_model).float()
        pe.require_grad = False

        position = torch.arange(0, max_len).float().unsqueeze(1)
        div_term = (torch.arange(0, d_model, 2).float() * -(math.log(10000.0) / d_model)).exp()

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)

        pe = pe.unsqueeze(0) # (1, max_len, d_model)
        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (B, L, d_model)
        return self.pe[:, :x.size(1)]

class TemporalEmbedding(nn.Module):
    """
    Nhúng thời gian (Temporal Embedding) dạng học được (learned) cho các đặc trưng thời gian (giờ, thứ, ngày, tháng).
    """
    def __init__(self, d_model: int, embed_type: str = 'fixed', freq: str = 'h'):
        super(TemporalEmbedding, self).__init__()
        
        # Số lượng lớp embedding phụ thuộc vào các thành phần thời gian (ví dụ freq='h')
        self.hour_embed = nn.Embedding(24, d_model)
        self.weekday_embed = nn.Embedding(7, d_model)
        self.day_embed = nn.Embedding(32, d_model)
        self.month_embed = nn.Embedding(13, d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, L, 4) chứa (month, day, weekday, hour) hoặc ngược lại tùy chuẩn bị data.
        # Giả sử: month (0), day (1), weekday (2), hour (3)
        x = x.long()
        month_x = self.month_embed(x[:, :, 0])
        day_x = self.day_embed(x[:, :, 1])
        weekday_x = self.weekday_embed(x[:, :, 2])
        hour_x = self.hour_embed(x[:, :, 3])
        
        return hour_x + weekday_x + day_x + month_x

class TimeFeatureEmbedding(nn.Module):
    """
    Nhúng đặc trưng thời gian (Time Feature Embedding) sử dụng Linear layer cho các giá trị thời gian liên tục.
    """
    def __init__(self, d_model: int, embed_type: str = 'timeF', freq: str = 'h'):
        super(TimeFeatureEmbedding, self).__init__()
        # Số chiều đầu vào phụ thuộc vào freq. Nếu 'h', thường là 4 (month, day, weekday, hour).
        d_inp = 4 if freq == 'h' else 5 # tùy config, mặc định 4 cho hour
        self.embed = nn.Linear(d_inp, d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (B, L, d_inp)
        return self.embed(x)

class DataEmbedding(nn.Module):
    """
    Nhúng Dữ liệu (Data Embedding) kết hợp Token, Positional và Temporal/TimeFeature.
    """
    def __init__(self, c_in: int, d_model: int, embed_type: str = 'timeF', freq: str = 'h', dropout: float = 0.1):
        super(DataEmbedding, self).__init__()
        self.value_embedding = TokenEmbedding(c_in=c_in, d_model=d_model)
        self.position_embedding = PositionalEmbedding(d_model=d_model)
        
        if embed_type == 'timeF':
            self.temporal_embedding = TimeFeatureEmbedding(d_model=d_model, embed_type=embed_type, freq=freq)
        else:
            self.temporal_embedding = TemporalEmbedding(d_model=d_model, embed_type=embed_type, freq=freq)
            
        self.dropout = nn.Dropout(p=dropout)

    def forward(self, x: torch.Tensor, x_mark: torch.Tensor) -> torch.Tensor:
        # Tổng hợp các embedding
        x = self.value_embedding(x) + self.position_embedding(x) + self.temporal_embedding(x_mark)
        return self.dropout(x)
