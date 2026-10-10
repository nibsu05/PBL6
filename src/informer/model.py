import torch
import torch.nn as nn
from .embed import DataEmbedding
from .attention import FullAttention, ProbAttention, AttentionLayer
from .encoder import ConvLayer, EncoderLayer, Encoder
from .decoder import DecoderLayer, Decoder

class Informer(nn.Module):
    """
    Mô hình Informer cho dự báo chuỗi thời gian dựa trên cơ chế ProbSparse Attention.
    """
    def __init__(self, enc_in: int, dec_in: int, c_out: int, 
                 seq_len: int = 168, label_len: int = 48, pred_len: int = 24, 
                 factor: int = 5, d_model: int = 128, n_heads: int = 8, 
                 e_layers: int = 2, d_layers: int = 1, d_ff: int = 256, 
                 dropout: float = 0.1, attn: str = 'prob', activation: str = 'gelu', 
                 distil: bool = True, freq: str = 'h', embed_type: str = 'timeF'):
        super(Informer, self).__init__()
        self.pred_len = pred_len
        self.attn = attn
        
        # 1. Embedding
        self.enc_embedding = DataEmbedding(enc_in, d_model, embed_type, freq, dropout)
        self.dec_embedding = DataEmbedding(dec_in, d_model, embed_type, freq, dropout)
        
        # Lựa chọn loại Attention cho Encoder
        Attn = ProbAttention if attn == 'prob' else FullAttention
        
        # 2. Encoder
        encoder_layers = []
        conv_layers = []
        for i in range(e_layers):
            encoder_layers.append(
                EncoderLayer(
                    AttentionLayer(Attn(mask_flag=False, factor=factor, attention_dropout=dropout, output_attention=False), 
                                   d_model, n_heads, mix=False),
                    d_model,
                    d_ff,
                    dropout=dropout,
                    activation=activation
                )
            )
            # Thêm lớp chưng cất (ConvLayer) nếu distil=True, nhưng không thêm sau lớp EncoderLayer cuối cùng
            if distil and i < e_layers - 1:
                conv_layers.append(ConvLayer(d_model))
                
        self.encoder = Encoder(encoder_layers, conv_layers if distil else None, norm_layer=nn.LayerNorm(d_model))
        
        # 3. Decoder
        decoder_layers = []
        for _ in range(d_layers):
            decoder_layers.append(
                DecoderLayer(
                    AttentionLayer(FullAttention(mask_flag=True, factor=factor, attention_dropout=dropout, output_attention=False), 
                                   d_model, n_heads, mix=False),
                    AttentionLayer(FullAttention(mask_flag=False, factor=factor, attention_dropout=dropout, output_attention=False), 
                                   d_model, n_heads, mix=False),
                    d_model,
                    d_ff,
                    dropout=dropout,
                    activation=activation
                )
            )
        self.decoder = Decoder(decoder_layers, norm_layer=nn.LayerNorm(d_model))
        
        # 4. Projection
        self.projection = nn.Linear(d_model, c_out)

    def forward(self, x_enc: torch.Tensor, x_mark_enc: torch.Tensor, x_dec: torch.Tensor, x_mark_dec: torch.Tensor) -> torch.Tensor:
        """
        Thực hiện một lượt lan truyền xuôi (forward pass).
        :param x_enc: Đầu vào cho encoder (B, seq_len, enc_in)
        :param x_mark_enc: Đặc trưng thời gian cho encoder (B, seq_len, 4)
        :param x_dec: Đầu vào cho decoder (B, label_len + pred_len, dec_in)
        :param x_mark_dec: Đặc trưng thời gian cho decoder (B, label_len + pred_len, 4)
        :return: Chuỗi dự báo (B, pred_len, c_out)
        """
        # Encoder
        enc_out = self.enc_embedding(x_enc, x_mark_enc)
        enc_out, _ = self.encoder(enc_out, attn_mask=None)
        
        # Decoder
        dec_out = self.dec_embedding(x_dec, x_mark_dec)
        dec_out, _, _ = self.decoder(dec_out, enc_out, x_mask=None, cross_mask=None)
        
        # Phóng chiếu (Projection) đầu ra cuối cùng
        output = self.projection(dec_out)
        
        # Chỉ lấy phần dự báo (pred_len token cuối cùng)
        return output[:, -self.pred_len:, :]
