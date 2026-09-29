"""Lấy mẫu các đợt mưa lớn trên tập train, không đụng validation/test."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch.utils.data import DataLoader, WeightedRandomSampler

from .dataset_prep import TimeSeriesWindowDataset

HOUR_NS = 3_600_000_000_000


@dataclass(frozen=True)
class EventSamplingInfo:
    train_windows: int
    heavy_windows: int
    heavy_window_fraction: float
    heavy_events: int
    event_gap_hours: int
    target_draw_fraction: float


def build_event_sampled_loader(
    dataset: TimeSeriesWindowDataset,
    *,
    batch_size: int = 256,
    heavy_threshold: float = 5.0,
    event_gap_hours: int = 6,
    target_draw_fraction: float = 0.25,
    seed: int = 42,
) -> tuple[DataLoader, EventSamplingInfo]:
    """Chia đều xác suất lấy mẫu cho các đợt mưa lớn trong train.

    Một đợt gồm các giờ mưa > ngưỡng cách nhau không quá ``event_gap_hours``.
    Cửa sổ có nhiều giờ mưa được gán cho đợt của giờ mưa lớn đầu tiên trong
    6 nhãn. Mọi đợt nhận tổng trọng số như nhau, tránh một đợt dài chiếm hết
    minibatch. Phần cửa sổ không có mưa lớn chia đều trọng số còn lại.
    """
    if len(dataset) == 0:
        raise ValueError("Dataset train rỗng")
    if batch_size < 1 or event_gap_hours < 1:
        raise ValueError("batch_size và event_gap_hours phải dương")
    if not 0 < target_draw_fraction < 1:
        raise ValueError("target_draw_fraction phải nằm trong (0, 1)")

    n = len(dataset)
    first_target = dataset.starts + dataset.input_length
    positions = first_target[:, None] + np.arange(dataset.output_length)[None, :]
    heavy = dataset.targets[positions] > heavy_threshold
    positive = heavy.any(axis=1)
    positive_count = int(positive.sum())
    negative_count = n - positive_count
    if positive_count == 0 or negative_count == 0:
        raise ValueError("Cần cả cửa sổ mưa lớn và không mưa lớn để lấy mẫu cân bằng")

    first_heavy_offset = np.argmax(heavy[positive], axis=1)
    first_heavy_position = positions[positive, first_heavy_offset]
    unique_positions = np.unique(first_heavy_position)
    timestamps_ns = dataset.timestamps.as_unit("ns").asi8[unique_positions]
    new_event = np.r_[True, np.diff(timestamps_ns) > event_gap_hours * HOUR_NS]
    event_ids = np.cumsum(new_event) - 1
    window_event_ids = event_ids[np.searchsorted(unique_positions, first_heavy_position)]
    event_sizes = np.bincount(window_event_ids)
    event_count = len(event_sizes)

    weights = np.empty(n, dtype=np.float64)
    weights[~positive] = (1.0 - target_draw_fraction) / negative_count
    weights[positive] = target_draw_fraction / (event_count * event_sizes[window_event_ids])
    if not np.isfinite(weights).all() or np.any(weights <= 0):
        raise RuntimeError("Trọng số lấy mẫu không hợp lệ")

    sampler = WeightedRandomSampler(
        weights=torch.from_numpy(weights),
        num_samples=n,
        replacement=True,
        generator=torch.Generator().manual_seed(seed),
    )
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        sampler=sampler,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )
    info = EventSamplingInfo(
        train_windows=n,
        heavy_windows=positive_count,
        heavy_window_fraction=positive_count / n,
        heavy_events=event_count,
        event_gap_hours=event_gap_hours,
        target_draw_fraction=target_draw_fraction,
    )
    return loader, info
