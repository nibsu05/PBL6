"""Biến đổi thuần để dựng dataset v2 (ô 0,1° × giờ) từ GSMaP, ERA5 và đặc trưng tĩnh.

Quy ước thời gian chung: hàng ``t`` mô tả khoảng ``[t, t+1h)`` theo UTC.

- GSMaP lưu theo đầu khoảng → dùng trực tiếp.
- ERA5 ``total_precipitation`` tại mốc ``T`` là tích lũy ``(T−1h, T]`` → gán vào hàng ``T−1h``.
- Biến tức thời ERA5 tại ``T`` là trạng thái lúc bắt đầu khoảng ``[T, T+1h)`` → gán vào hàng ``T``.

CIN bị mask khi không có mực đối lưu tự do: mã hóa thành ``cin_capped`` (NaN → 500 J/kg,
tức lực cản rất lớn) và ``has_lfc`` (0/1) *trước* khi nội suy, không điền 0.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

CIN_CAP = 500.0
ERA5_RES = 0.25


def to_cube(frame: pd.DataFrame, time_col: str, hours: pd.DatetimeIndex, sites: list[str],
            columns: list[str]) -> np.ndarray:
    """Bảng dài → mảng ``[giờ, điểm, biến]``; ô không có dữ liệu là NaN."""
    cube = np.full((len(hours), len(sites), len(columns)), np.nan, dtype=np.float32)
    t_idx = hours.get_indexer(pd.DatetimeIndex(frame[time_col]))
    s_idx = pd.Index(sites).get_indexer(frame["site"])
    ok = (t_idx >= 0) & (s_idx >= 0)
    cube[t_idx[ok], s_idx[ok], :] = frame.loc[ok, columns].to_numpy(np.float32)
    return cube


def encode_cin(cin: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    has_lfc = np.isfinite(cin).astype(np.float32)
    capped = np.where(np.isfinite(cin), np.minimum(cin, CIN_CAP), CIN_CAP).astype(np.float32)
    return capped, has_lfc


def bilinear_weights(cell_lat: np.ndarray, cell_lon: np.ndarray, node_lat: np.ndarray,
                     node_lon: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Chỉ số 4 nút ERA5 bao quanh mỗi ô và trọng số song tuyến tương ứng.

    ``node_lat``/``node_lon`` là toạ độ của từng nút (thứ tự cột của mảng ERA5).
    Trả về ``idx`` và ``w`` dạng ``[ô, 4]``.
    """
    lookup = {(round(a, 2), round(b, 2)): k for k, (a, b) in enumerate(zip(node_lat, node_lon))}
    lat0 = np.floor(cell_lat / ERA5_RES) * ERA5_RES
    lon0 = np.floor(cell_lon / ERA5_RES) * ERA5_RES
    fy = (cell_lat - lat0) / ERA5_RES
    fx = (cell_lon - lon0) / ERA5_RES
    corners = [(0, 0, (1 - fy) * (1 - fx)), (0, 1, (1 - fy) * fx), (1, 0, fy * (1 - fx)), (1, 1, fy * fx)]
    idx = np.zeros((len(cell_lat), 4), dtype=np.int64)
    w = np.zeros((len(cell_lat), 4), dtype=np.float64)
    for k, (dy, dx, wk) in enumerate(corners):
        for i, (a, b) in enumerate(zip(lat0 + dy * ERA5_RES, lon0 + dx * ERA5_RES)):
            key = (round(float(a), 2), round(float(b), 2))
            if key not in lookup:
                raise ValueError(f"Thiếu nút ERA5 {key} để nội suy ô {cell_lat[i]:.2f},{cell_lon[i]:.2f}")
            idx[i, k] = lookup[key]
        w[:, k] = wk
    return idx, w


def interpolate(nodes: np.ndarray, idx: np.ndarray, w: np.ndarray, chunk_hours: int = 500) -> np.ndarray:
    """Nội suy ``[giờ, nút, biến]`` → ``[giờ, ô, biến]``; bỏ qua nút NaN và chuẩn hóa lại trọng số.

    Xử lý theo khối thời gian để mảng trung gian ``[giờ, ô, 4, biến]`` vừa bộ nhớ máy 8 GB.
    """
    out = np.empty((nodes.shape[0], idx.shape[0], nodes.shape[2]), dtype=np.float32)
    w32 = w.astype(np.float32)[None, :, :, None]
    for t0 in range(0, nodes.shape[0], chunk_hours):
        vals = nodes[t0:t0 + chunk_hours][:, idx, :]          # [t, C, 4, V]
        valid = np.isfinite(vals)
        num = np.where(valid, vals * w32, 0.0).sum(axis=2)
        den = np.where(valid, np.broadcast_to(w32, vals.shape), 0.0).sum(axis=2)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[t0:t0 + chunk_hours] = np.where(den > 0, num / den, np.nan)
    return out


def neighbourhood_stats(field: np.ndarray, lat: np.ndarray, lon: np.ndarray, radius: int = 2,
                        res: float = 0.1) -> tuple[np.ndarray, np.ndarray]:
    """Trung bình và lớn nhất trên cửa sổ (2r+1)×(2r+1) ô quanh mỗi ô; ``field`` dạng ``[giờ, ô]``."""
    ii = np.round((lat - lat.min()) / res).astype(int)
    jj = np.round((lon - lon.min()) / res).astype(int)
    grid = np.full((field.shape[0], ii.max() + 1 + 2 * radius, jj.max() + 1 + 2 * radius), np.nan, dtype=np.float32)
    grid[:, ii + radius, jj + radius] = field
    stack = np.stack([grid[:, ii + radius + di, jj + radius + dj]
                      for di in range(-radius, radius + 1) for dj in range(-radius, radius + 1)], axis=-1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # cửa sổ toàn NaN → NaN
        return np.nanmean(stack, axis=-1).astype(np.float32), np.nanmax(stack, axis=-1).astype(np.float32)


def time_features(hours: pd.DatetimeIndex, utc_offset_hours: int = 7) -> np.ndarray:
    """sin/cos của giờ địa phương và ngày-trong-năm, dạng ``[giờ, 4]``."""
    local = hours + pd.Timedelta(hours=utc_offset_hours)
    hour = local.hour.to_numpy() + 0.5  # giữa khoảng [t, t+1h)
    doy = local.dayofyear.to_numpy()
    return np.stack([np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24),
                     np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)], axis=1).astype(np.float32)


def relative_humidity(t_k: np.ndarray, td_k: np.ndarray) -> np.ndarray:
    """RH (%) từ nhiệt độ và điểm sương theo công thức Magnus."""
    t, td = t_k - 273.15, td_k - 273.15
    return (100 * np.exp(17.625 * td / (243.04 + td)) / np.exp(17.625 * t / (243.04 + t))).astype(np.float32)
