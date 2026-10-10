"""Dataset và data preparation cho Informer ablation study.

Xử lý cắt cửa sổ encoder/decoder, tạo temporal marks, và chia dữ liệu
theo thời gian (chronological split) cho thí nghiệm ablation 5 nhóm features.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, Dataset

logger = logging.getLogger(__name__)

HOUR_NS = 3_600_000_000_000  # 1 giờ tính bằng nanosecond


class InformerDataset(Dataset):
    """Dataset cho Informer: trả về 5 tensor mỗi sample.

    Mỗi sample gồm:
    - x_enc: (seq_len, num_features) — encoder input
    - x_mark_enc: (seq_len, 4) — temporal marks encoder
    - x_dec: (label_len + pred_len, num_features) — decoder input (label + zero-pad)
    - x_mark_dec: (label_len + pred_len, 4) — temporal marks decoder
    - y: (pred_len,) — target precipitation (chưa scale, đơn vị gốc mm/h)
    """

    def __init__(
        self,
        data: np.ndarray,
        targets: np.ndarray,
        time_marks: np.ndarray,
        valid_starts: np.ndarray,
        seq_len: int,
        label_len: int,
        pred_len: int,
    ) -> None:
        self.data = data
        self.targets = targets
        self.time_marks = time_marks
        self.valid_starts = np.asarray(valid_starts, dtype=np.int64)
        self.seq_len = seq_len
        self.label_len = label_len
        self.pred_len = pred_len

    def __len__(self) -> int:
        return len(self.valid_starts)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, ...]:
        s = int(self.valid_starts[idx])

        # Encoder input: [s, s + seq_len)
        x_enc = self.data[s: s + self.seq_len]
        x_mark_enc = self.time_marks[s: s + self.seq_len]

        # Decoder input: label part = [s + seq_len - label_len, s + seq_len)
        #                pred part  = zeros (pred_len, num_features)
        dec_label_start = s + self.seq_len - self.label_len
        dec_label_end = s + self.seq_len

        x_dec_label = self.data[dec_label_start: dec_label_end].copy()
        x_dec_pred = np.zeros((self.pred_len, self.data.shape[1]), dtype=np.float32)
        x_dec = np.concatenate([x_dec_label, x_dec_pred], axis=0)

        # Temporal marks cho decoder: [dec_label_start, dec_label_end + pred_len)
        x_mark_dec = self.time_marks[dec_label_start: dec_label_end + self.pred_len]

        # Target: precipitation tại [dec_label_end, dec_label_end + pred_len)
        y = self.targets[dec_label_end: dec_label_end + self.pred_len]

        return (
            torch.from_numpy(x_enc).float(),
            torch.from_numpy(x_mark_enc).float(),
            torch.from_numpy(x_dec).float(),
            torch.from_numpy(x_mark_dec).float(),
            torch.from_numpy(y).float(),
        )


@dataclass
class PreparedInformerData:
    """Kết quả sau khi chuẩn bị dữ liệu."""
    train_loader: DataLoader
    val_loader: DataLoader
    test_loader: DataLoader
    feature_cols: List[str]
    feature_scaler: StandardScaler
    target_scaler: StandardScaler
    split_boundaries: Dict[str, str]
    diagnostics: Dict


def _create_time_marks(dt_index: pd.DatetimeIndex) -> np.ndarray:
    """Tạo temporal features chuẩn hóa [0, 1] từ DatetimeIndex.

    Returns: (N, 4) array với [hour/23, dayofweek/6, (day-1)/30, (month-1)/11]
    """
    hour = dt_index.hour / 23.0
    dow = dt_index.dayofweek / 6.0
    dom = (dt_index.day - 1) / 30.0
    month = (dt_index.month - 1) / 11.0
    return np.column_stack([hour, dow, dom, month]).astype(np.float32)


def _find_valid_windows(
    times_ns: np.ndarray,
    finite_mask: np.ndarray,
    window_len: int,
) -> np.ndarray:
    """Tìm tất cả vị trí bắt đầu hợp lệ cho cửa sổ.

    Một cửa sổ hợp lệ khi:
    1. Tất cả giờ liên tiếp (diff = 1h)
    2. Tất cả features hữu hạn (không NaN/inf)
    """
    n = len(times_ns)
    if n < window_len:
        return np.array([], dtype=np.int64)

    n_candidates = n - window_len + 1

    # Kiểm tra liên tục: diff giữa giờ kề nhau phải = 1 giờ
    is_gap = np.diff(times_ns) != HOUR_NS
    gap_prefix = np.concatenate([[0], np.cumsum(is_gap)])
    contiguous = gap_prefix[np.arange(window_len - 1, n)] == gap_prefix[np.arange(n_candidates)]

    # Kiểm tra đầy đủ: không có NaN trong cửa sổ
    invalid_prefix = np.concatenate([[0], np.cumsum(~finite_mask)])
    complete = invalid_prefix[np.arange(window_len, n + 1)] == invalid_prefix[np.arange(n_candidates)]

    valid = np.where(contiguous & complete)[0]
    return valid.astype(np.int64)


def prepare_informer_data(
    data_path: str | Path,
    feature_cols: List[str],
    seq_len: int = 168,
    label_len: int = 48,
    pred_len: int = 24,
    batch_size: int = 32,
    train_fraction: float = 0.70,
    val_fraction: float = 0.15,
) -> PreparedInformerData:
    """Chuẩn bị dữ liệu cho Informer ablation study.

    Args:
        data_path: Đường dẫn CSV (danang_full_features_2021_2026.csv)
        feature_cols: Danh sách features cho thí nghiệm (ví dụ EXP-0: 6 biến surface)
        seq_len: Chiều dài encoder input
        label_len: Chiều dài label portion của decoder
        pred_len: Chiều dài phần dự báo
        batch_size: Batch size
        train_fraction: Tỷ lệ train (mặc định 0.70)
        val_fraction: Tỷ lệ validation (mặc định 0.15)

    Returns:
        PreparedInformerData với train/val/test DataLoaders và metadata
    """
    logger.info("Đang tải dữ liệu từ %s", data_path)
    df = pd.read_csv(data_path, parse_dates=["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    logger.info("  Tổng số dòng: %d", len(df))

    # --- Xử lý CIN ---
    actual_features = list(feature_cols)
    if "cin" in actual_features:
        df["cin_value"] = df["cin"].fillna(0.0)
        df["is_convective"] = df["cin"].notna().astype(np.float32)
        actual_features.remove("cin")
        actual_features.extend(["cin_value", "is_convective"])
        logger.info("  CIN → cin_value + is_convective")

    # --- Kiểm tra cột ---
    missing_cols = [c for c in actual_features if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Thiếu cột trong CSV: {missing_cols}")

    # --- Fill NaN (forward/backward cho các biến ERA5 có thể thiếu vài giờ) ---
    na_count = df[actual_features].isna().sum().sum()
    if na_count > 0:
        logger.warning("  Phát hiện %d NaN trong features → ffill + bfill", na_count)
        df[actual_features] = df[actual_features].ffill().bfill()

    # --- Temporal marks ---
    dt_index = pd.DatetimeIndex(df["datetime"])
    time_marks = _create_time_marks(dt_index)

    # --- Chronological split ---
    total = len(df)
    train_end_idx = int(total * train_fraction)
    val_end_idx = int(total * (train_fraction + val_fraction))

    train_end_time = str(df["datetime"].iloc[train_end_idx])
    val_end_time = str(df["datetime"].iloc[val_end_idx])

    logger.info("  Train: 0 → %d (%s)", train_end_idx, train_end_time)
    logger.info("  Val:   %d → %d (%s)", train_end_idx, val_end_idx, val_end_time)
    logger.info("  Test:  %d → %d", val_end_idx, total)

    # --- Fit Scalers chỉ trên train ---
    feature_scaler = StandardScaler()
    feature_scaler.fit(df.iloc[:train_end_idx][actual_features].values)

    target_scaler = StandardScaler()
    target_scaler.fit(df.iloc[:train_end_idx][["precipitation"]].values)

    # --- Scale toàn bộ dữ liệu ---
    all_features = feature_scaler.transform(df[actual_features].values).astype(np.float32)
    all_targets = df["precipitation"].values.astype(np.float32)

    # --- Tìm valid windows trên toàn bộ timeline ---
    times_ns = dt_index.as_unit("ns").asi8
    finite_mask = np.isfinite(all_features).all(axis=1) & np.isfinite(all_targets)
    window_len = seq_len + pred_len

    all_valid = _find_valid_windows(times_ns, finite_mask, window_len)
    logger.info("  Tổng cửa sổ hợp lệ trên timeline: %d", len(all_valid))

    # --- Phân chia cửa sổ vào train/val/test ---
    # Cửa sổ thuộc split nào dựa vào vị trí TARGET (prediction portion)
    # target_start = start + seq_len, target_end = start + seq_len + pred_len - 1
    target_end_indices = all_valid + seq_len + pred_len - 1

    train_windows = all_valid[target_end_indices < train_end_idx]
    val_windows = all_valid[(all_valid + seq_len >= train_end_idx) & (target_end_indices < val_end_idx)]
    test_windows = all_valid[all_valid + seq_len >= val_end_idx]

    logger.info("  Train windows: %d, Val windows: %d, Test windows: %d",
                len(train_windows), len(val_windows), len(test_windows))

    if len(train_windows) == 0 or len(val_windows) == 0 or len(test_windows) == 0:
        raise ValueError("Một trong các tập không có cửa sổ hợp lệ!")

    # --- Tạo datasets ---
    def make_dataset(starts: np.ndarray) -> InformerDataset:
        return InformerDataset(
            data=all_features,
            targets=all_targets,
            time_marks=time_marks,
            valid_starts=starts,
            seq_len=seq_len,
            label_len=label_len,
            pred_len=pred_len,
        )

    train_ds = make_dataset(train_windows)
    val_ds = make_dataset(val_windows)
    test_ds = make_dataset(test_windows)

    pin = torch.cuda.is_available()
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                              num_workers=0, pin_memory=pin, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False,
                            num_workers=0, pin_memory=pin)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False,
                             num_workers=0, pin_memory=pin)

    diagnostics = {
        "total_rows": total,
        "num_features_raw": len(feature_cols),
        "num_features_actual": len(actual_features),
        "feature_names": actual_features,
        "train_windows": len(train_windows),
        "val_windows": len(val_windows),
        "test_windows": len(test_windows),
        "seq_len": seq_len,
        "label_len": label_len,
        "pred_len": pred_len,
    }

    return PreparedInformerData(
        train_loader=train_loader,
        val_loader=val_loader,
        test_loader=test_loader,
        feature_cols=actual_features,
        feature_scaler=feature_scaler,
        target_scaler=target_scaler,
        split_boundaries={"train_end": train_end_time, "val_end": val_end_time},
        diagnostics=diagnostics,
    )
