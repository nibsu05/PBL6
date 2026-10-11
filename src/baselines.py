"""Baseline không học: khí hậu theo ngày-trong-năm và persistence.

Khí hậu chỉ được fit trên các ngày *trước* giai đoạn đánh giá; hàm nhận chuỗi
đã cắt sẵn để người gọi không vô tình dùng năm test.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


def _circular_smooth(values: np.ndarray, window: int) -> np.ndarray:
    """Trung bình trượt vòng tròn 366 ngày; bỏ qua NaN. ``window`` phải lẻ."""
    if window < 1 or window % 2 == 0:
        raise ValueError("window_days phải là số lẻ dương")
    half = window // 2
    padded = np.concatenate([values[len(values) - half:], values, values[:half]])
    finite = np.isfinite(padded)
    kernel = np.ones(window)
    total = np.convolve(np.where(finite, padded, 0.0), kernel, mode="valid")
    count = np.convolve(finite.astype(float), kernel, mode="valid")
    with np.errstate(invalid="ignore", divide="ignore"):
        return total / count


def doy_climatology(daily: pd.Series, thresholds: Iterable[float] = (16.0, 50.0, 100.0),
                    window_days: int = 31) -> pd.DataFrame:
    """Lượng mưa trung bình và xác suất vượt ngưỡng theo ngày-trong-năm (1–366).

    ``daily`` là tổng mưa ngày có ``DatetimeIndex``; NaN bị bỏ qua. Làm trơn
    bằng cửa sổ ``window_days`` ngày để 10 năm dữ liệu không cho ra khí hậu
    răng cưa.
    """
    series = daily.dropna()
    if series.empty:
        raise ValueError("Chuỗi khí hậu rỗng")
    doy = series.index.dayofyear
    out = pd.DataFrame(index=pd.RangeIndex(1, 367, name="doy"))
    raw_mean = series.groupby(doy).mean().reindex(out.index).to_numpy(float)
    out["clim_mean"] = _circular_smooth(raw_mean, window_days)
    for thr in thresholds:
        raw_p = (series >= thr).astype(float).groupby(doy).mean().reindex(out.index).to_numpy(float)
        out[f"clim_p>={thr:g}"] = _circular_smooth(raw_p, window_days)
    return out


def apply_climatology(index: pd.DatetimeIndex, clim: pd.DataFrame) -> pd.DataFrame:
    """Gán giá trị khí hậu cho từng ngày của ``index``."""
    values = clim.reindex(pd.DatetimeIndex(index).dayofyear)
    values.index = index
    return values


def persistence(daily: pd.Series, lag_days: int = 1) -> pd.Series:
    """Giá trị của ``lag_days`` ngày trước theo lịch; ngày trước bị thiếu thì NaN."""
    series = daily.copy()
    series.index = pd.DatetimeIndex(series.index)
    full = series.asfreq("D")
    return full.shift(lag_days).reindex(series.index)
