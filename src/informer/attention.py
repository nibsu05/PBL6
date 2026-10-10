"""ProbSparse Attention & Full Attention cho Informer.

Cơ chế ProbSparse Attention giảm độ phức tạp từ O(L^2) xuống O(L log L)
bằng cách chỉ chọn top-u active queries thay vì tính attention cho tất cả.

Reference: Zhou et al., "Informer: Beyond Efficient Transformer for Long
Sequence Time-Series Forecasting", AAAI 2021.
"""

from __future__ import annotations

from math import sqrt
from typing import Optional, Tuple

import numpy as np
import torch
import torch.nn as nn


class TriangularCausalMask:
    """Mặt nạ nhân quả tam giác cho self-attention ở decoder."""

    def __init__(self, B: int, L: int, device: torch.device = torch.device("cpu")) -> None:
        mask_shape = [B, 1, L, L]
        with torch.no_grad():
            self._mask = torch.triu(torch.ones(mask_shape, dtype=torch.bool, device=device), diagonal=1)

    @property
    def mask(self) -> torch.Tensor:
        return self._mask


class ProbMask:
    """Mặt nạ xác suất cho ProbSparse Attention."""

    def __init__(self, B: int, H: int, L: int, index: torch.Tensor,
                 scores: torch.Tensor, device: torch.device = torch.device("cpu")) -> None:
        _mask = torch.ones(L, scores.shape[-1], dtype=torch.bool, device=device).triu(1)
        _mask_ex = _mask[None, None, :].expand(B, H, L, scores.shape[-1])
        indicator = _mask_ex[
            torch.arange(B)[:, None, None],
            torch.arange(H)[None, :, None],
            index, :
        ].to(device)
        self._mask = indicator.view(scores.shape).to(device)

    @property
    def mask(self) -> torch.Tensor:
        return self._mask


class FullAttention(nn.Module):
    """Scaled Dot-Product Attention tiêu chuẩn.

    Dùng cho cross-attention ở decoder và tùy chọn thay thế ProbSparse.
    Input layout: queries/keys/values có shape (B, L, H, D).
    """

    def __init__(
        self,
        mask_flag: bool = True,
        factor: int = 5,
        scale: Optional[float] = None,
        attention_dropout: float = 0.1,
        output_attention: bool = False,
    ) -> None:
        super().__init__()
        self.scale = scale
        self.mask_flag = mask_flag
        self.output_attention = output_attention
        self.dropout = nn.Dropout(attention_dropout)

    def forward(
        self,
        queries: torch.Tensor,
        keys: torch.Tensor,
        values: torch.Tensor,
        attn_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        # queries: (B, L_Q, H, D), keys: (B, L_K, H, D), values: (B, L_V, H, D)
        B, L_Q, H, D = queries.shape
        _, L_K, _, _ = keys.shape
        scale = self.scale or 1.0 / sqrt(D)

        # Tính scores: (B, H, L_Q, L_K)
        scores = torch.einsum("blhd,bshd->bhls", queries, keys) * scale

        if self.mask_flag:
            if attn_mask is None:
                attn_mask = TriangularCausalMask(B, L_Q, device=queries.device).mask
            scores.masked_fill_(attn_mask, -np.inf)

        A = self.dropout(torch.softmax(scores, dim=-1))
        # Áp dụng attention lên values: (B, L_Q, H, D)
        V = torch.einsum("bhls,bshd->blhd", A, values)

        if self.output_attention:
            return V, A
        return V, None


class ProbAttention(nn.Module):
    """ProbSparse Self-Attention — cốt lõi của Informer.

    Giảm O(L^2) xuống O(L log L) bằng cách chỉ chọn top-u active queries
    dựa trên đo lường KL-divergence gần đúng.

    Input layout: queries/keys/values có shape (B, L, H, D).
    """

    def __init__(
        self,
        mask_flag: bool = True,
        factor: int = 5,
        scale: Optional[float] = None,
        attention_dropout: float = 0.1,
        output_attention: bool = False,
    ) -> None:
        super().__init__()
        self.factor = factor
        self.scale = scale
        self.mask_flag = mask_flag
        self.output_attention = output_attention
        self.dropout = nn.Dropout(attention_dropout)

    def _prob_QK(
        self,
        Q: torch.Tensor,
        K: torch.Tensor,
        sample_k: int,
        n_top: int,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Chọn top-u active queries dựa trên sparsity measurement M.

        Args:
            Q: (B, H, L_Q, D) — queries đã transpose
            K: (B, H, L_K, D) — keys đã transpose
            sample_k: Số keys lấy mẫu
            n_top: Số active queries cần chọn

        Returns:
            Q_reduce: (B, H, n_top, D) — active queries
            M_top: (B, H, n_top) — indices of active queries
        """
        B, H, L_K, D = K.shape
        _, _, L_Q, _ = Q.shape

        # Lấy mẫu ngẫu nhiên sample_k keys
        # K_expand: (B, H, L_Q, L_K, D) — sẽ rất tốn bộ nhớ nếu L lớn
        # Thay vào đó, lấy mẫu index rồi gather
        K_expand = K.unsqueeze(-3).expand(B, H, L_Q, L_K, D)
        index_sample = torch.randint(L_K, (L_Q, sample_k), device=K.device)  # (L_Q, sample_k)
        K_sample = K_expand[:, :, torch.arange(L_Q, device=K.device).unsqueeze(1), index_sample, :]
        # K_sample: (B, H, L_Q, sample_k, D)

        # Tính Q·K_sample^T để ước lượng M (sparsity measurement)
        Q_K_sample = torch.matmul(
            Q.unsqueeze(-2),        # (B, H, L_Q, 1, D)
            K_sample.transpose(-2, -1),  # (B, H, L_Q, D, sample_k)
        ).squeeze(-2)  # (B, H, L_Q, sample_k)

        # M = max(Q·K) - mean(Q·K): đo "nhọn" của phân bố attention
        M = Q_K_sample.max(-1)[0] - torch.div(Q_K_sample.sum(-1), L_K)

        # Chọn top-u queries có M cao nhất
        M_top = M.topk(n_top, sorted=False)[1]  # (B, H, n_top)

        # Trích xuất active queries
        Q_reduce = Q[
            torch.arange(B, device=Q.device)[:, None, None],
            torch.arange(H, device=Q.device)[None, :, None],
            M_top,
        ]  # (B, H, n_top, D)

        return Q_reduce, M_top

    def _get_initial_context(self, V: torch.Tensor, L_Q: int) -> torch.Tensor:
        """Tạo context mặc định (trung bình V) cho lazy queries.

        Args:
            V: (B, H, L_V, D) — values đã transpose
            L_Q: Chiều dài queries

        Returns:
            context: (B, H, L_Q, D)
        """
        B, H, L_V, D = V.shape
        if not self.mask_flag:
            # Trung bình toàn bộ V
            V_mean = V.mean(dim=2)  # (B, H, D)
            context = V_mean.unsqueeze(2).expand(B, H, L_Q, D).clone()
        else:
            # Causal: tổng tích lũy / count
            assert L_Q == L_V, "Causal mask yêu cầu L_Q == L_V"
            V_cumsum = V.cumsum(dim=2)  # (B, H, L_V, D)
            counts = torch.arange(1, L_Q + 1, device=V.device, dtype=V.dtype).view(1, 1, L_Q, 1)
            context = (V_cumsum / counts).clone()
        return context

    def _update_context(
        self,
        context_in: torch.Tensor,
        V: torch.Tensor,
        scores: torch.Tensor,
        index: torch.Tensor,
        L_Q: int,
        attn_mask: Optional[torch.Tensor],
    ) -> torch.Tensor:
        """Cập nhật context cho active queries bằng attention scores thực.

        Args:
            context_in: (B, H, L_Q, D)
            V: (B, H, L_V, D)
            scores: (B, H, n_top, L_K)
            index: (B, H, n_top) — indices of active queries
            L_Q: Chiều dài queries gốc
            attn_mask: Optional mask
        """
        B, H, n_top, L_K = scores.shape

        if self.mask_flag:
            if attn_mask is None:
                attn_mask = ProbMask(B, H, L_Q, index, scores, device=V.device).mask
            scores.masked_fill_(attn_mask, -np.inf)

        attn = self.dropout(torch.softmax(scores, dim=-1))  # (B, H, n_top, L_K)
        context_active = torch.matmul(attn, V)  # (B, H, n_top, D)

        # Scatter active context vào vị trí tương ứng
        context_in[
            torch.arange(B, device=context_in.device)[:, None, None],
            torch.arange(H, device=context_in.device)[None, :, None],
            index,
        ] = context_active

        return context_in

    def forward(
        self,
        queries: torch.Tensor,
        keys: torch.Tensor,
        values: torch.Tensor,
        attn_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        # Input: (B, L, H, D) → transpose sang (B, H, L, D) cho tính toán
        B, L_Q, H, D = queries.shape
        _, L_K, _, _ = keys.shape

        queries = queries.transpose(2, 1)  # (B, H, L_Q, D)
        keys = keys.transpose(2, 1)        # (B, H, L_K, D)
        values = values.transpose(2, 1)    # (B, H, L_V, D)

        # Tham số sparsity
        U_part = self.factor * max(1, int(np.ceil(np.log(L_K))))
        u = self.factor * max(1, int(np.ceil(np.log(L_K)))) * max(1, int(np.ceil(np.log(L_Q))))
        u = max(1, min(L_Q, u))
        U_part = max(1, min(L_K, U_part))

        scale = self.scale or 1.0 / sqrt(D)

        # 1. Chọn active queries
        Q_reduce, index = self._prob_QK(queries, keys, sample_k=U_part, n_top=u)

        # 2. Tính attention scores cho active queries
        scores = torch.matmul(Q_reduce, keys.transpose(-2, -1)) * scale  # (B, H, u, L_K)

        # 3. Initial context (trung bình V cho lazy queries)
        context = self._get_initial_context(values, L_Q)  # (B, H, L_Q, D)

        # 4. Cập nhật context cho active queries
        context = self._update_context(context, values, scores, index, L_Q, attn_mask)

        # Transpose lại về (B, L_Q, H, D)
        context = context.transpose(2, 1).contiguous()

        if self.output_attention:
            return context, scores
        return context, None


class AttentionLayer(nn.Module):
    """Lớp Attention bao bọc Q/K/V projections + multi-head split."""

    def __init__(
        self,
        attention: nn.Module,
        d_model: int,
        n_heads: int,
        d_keys: Optional[int] = None,
        d_values: Optional[int] = None,
        mix: bool = False,
    ) -> None:
        super().__init__()
        d_keys = d_keys or (d_model // n_heads)
        d_values = d_values or (d_model // n_heads)

        self.inner_attention = attention
        self.query_projection = nn.Linear(d_model, d_keys * n_heads)
        self.key_projection = nn.Linear(d_model, d_keys * n_heads)
        self.value_projection = nn.Linear(d_model, d_values * n_heads)
        self.out_projection = nn.Linear(d_values * n_heads, d_model)
        self.n_heads = n_heads
        self.mix = mix

    def forward(
        self,
        queries: torch.Tensor,
        keys: torch.Tensor,
        values: torch.Tensor,
        attn_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        B, L_Q, _ = queries.shape
        _, L_K, _ = keys.shape
        H = self.n_heads

        # Linear projections → reshape thành multi-head: (B, L, H, D)
        queries = self.query_projection(queries).view(B, L_Q, H, -1)
        keys = self.key_projection(keys).view(B, L_K, H, -1)
        values = self.value_projection(values).view(B, L_K, H, -1)

        # Áp dụng attention (input/output: B, L, H, D)
        out, attn = self.inner_attention(queries, keys, values, attn_mask)

        if self.mix:
            out = out.transpose(2, 1).contiguous()

        # Concat heads → output projection
        out = out.contiguous().view(B, L_Q, -1)
        return self.out_projection(out), attn
