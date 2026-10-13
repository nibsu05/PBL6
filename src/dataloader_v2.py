"""Dataloader cho dataset v2: cửa sổ (ô, thời điểm phát hành) cho Bi-LSTM, Informer, TFT, LightGBM.

Quy ước. Một dự báo phát hành lúc ``t`` (đầu giờ, UTC) dự báo mưa cho các khoảng
``[t, t+1h) … [t+H−1, t+H)``. Mỗi mẫu gồm:

- ``x_past``  ``[W, F_past]``: biến khí quyển của W giờ trước ``t`` (hàng ``t−W … t−1``),
  cùng biến quan trắc (nhóm A1) **dịch trễ L giờ**: bước ``τ`` dùng quan trắc của
  khoảng ``τ−L``, nên khoảng quan trắc mới nhất mô hình thấy kết thúc lúc ``t−L``.
  L=None nghĩa là không dùng quan trắc (mô hình dự phòng). Thời gian nằm trong ``x_past``.
- ``x_future`` ``[H, F_future]``: biến "đã biết trước" tại các giờ đích. Khi huấn luyện
  là ERA5 tại giờ đích (perfect prog), khi chạy app là dự báo ECMWF. Luôn có thời gian.
- ``static`` ``[F_static]``: đặc trưng tĩnh của ô.
- ``y`` ``[H]``: nhãn GSMaP hiệu chỉnh trạm, mm/h, chưa biến đổi.

Chia train/val/test theo **năm của giờ đích đầu tiên** để mọi nhãn của một mẫu nằm trong
cùng một phần; đầu vào được phép nhìn lùi sang phần trước (đúng như dự báo cuốn chiếu).
Chuẩn hóa chỉ fit trên các năm train và các ô train.

Dữ liệu lưu dạng ``[ô, giờ, đặc trưng]`` (memmap) để một cửa sổ là vùng nhớ liền nhau;
tạo một lần bằng ``build_cell_major``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT / "data" / "processed" / "dataset_v2"
CUBE = "cube_cell_major.npy"
HOURS = "hours_all.npy"
LABEL = "y_gsmap_gc_mm"
TIME_FEATURES = ("sin_hour", "cos_hour", "sin_doy", "cos_doy")
STATIC_FEATURES = ("elev_mean_m", "elev_std_m", "elev_max_m", "ocean_frac", "coast_dist_km", "ne_upslope_m", "lat", "lon")
LOG1P_FEATURES = {"gsmap_mm", "gsmap_nb5_mean_mm", "gsmap_nb5_max_mm", "era5_tp_mm", "cape", "blh", LABEL}

# Nhóm đặc trưng theo plan v2 (mục 4.3–4.4). "past" = chuỗi quá khứ, "obs" = quan trắc dịch
# trễ L, "future" = giá trị tại giờ đích (perfect prog khi huấn luyện, ECMWF khi chạy thật).
SURFACE = ("t2m_c", "td2m_c", "rh2m_pct", "sp_hpa", "mslp_hpa", "u10", "v10", "tcc", "lcc", "mcc", "hcc")
FEATURE_GROUPS: dict[str, dict[str, tuple[str, ...]]] = {
    # Sản phẩm A — Bi-LSTM 0–6 h
    "A0": {"past": SURFACE},
    "A1": {"obs": ("gsmap_mm", "gsmap_nb5_mean_mm", "gsmap_nb5_max_mm")},
    "A2": {"past": ("cape", "cin_capped", "has_lfc", "tcwv", "kx", "tt", "blh")},
    "A3": {"past": ("ivt_u", "ivt_v", "ivt_mag", "vimd_mmh", "u850", "v850", "q850_gkg", "t850_c", "w850_pas",
                    "rh850_pct", "u500", "v500", "q500_gkg", "t500_c", "w500_pas", "shear_850_500")},
    "A4": {"past": ("era5_tp_mm",), "future": ("era5_tp_mm", "cape", "tcwv", "ivt_mag", "u850", "v850")},
    "A5": {"past": ("ctx_tcwv", "ctx_ivt_mag")},
    # Sản phẩm B — TFT 1–3 ngày (Informer chỉ chạy một cấu hình để đối chiếu)
    "B0": {"past": SURFACE, "obs": ("gsmap_mm",)},
    "B1": {"past": ("cold_surge_dp_hpa", "dp_tonkin_south_hpa", "u850", "v850", "tcwv", "ivt_u", "ivt_v", "ivt_mag")},
    "B2": {"past": ("cape", "cin_capped", "has_lfc", "kx", "tt")},
    "B3": {"future": ("era5_tp_mm", "tcwv", "cape", "mslp_hpa", "u850", "v850", "ivt_mag", "cold_surge_dp_hpa")},
    "B4": {"past": ("sst_region_c",)},
    "B5": {"past": ("ctx_tcwv", "ctx_ivt_mag")},
}
SEASON_OF_MONTH = {m: ("winter" if m in (11, 12, 1, 2) else "summer" if 5 <= m <= 10 else "spring") for m in range(1, 13)}


@dataclass
class WindowConfig:
    """Mô tả đầy đủ một thí nghiệm về mặt dữ liệu; hash của nó đặt tên cho cache."""
    groups: tuple[str, ...]
    input_len: int = 24
    horizon: int = 6
    latency_h: int | None = 4          # độ trễ quan trắc; None = không dùng nhóm obs
    issue_stride_h: int = 1            # 1 = phát hành mỗi giờ (A); 6 = mỗi 6 h (B)
    issue_hours_utc: tuple[int, ...] | None = None  # ví dụ (0, 6, 12, 18); None = mọi giờ chia hết stride
    provinces: tuple[str, ...] | None = None        # None = mọi ô thuộc Việt Nam
    include_foreign: bool = False                    # thêm ô bên Lào (nhãn kém tin cậy hơn)
    exclude_sites: tuple[str, ...] = ()              # ô giữ lại cho thí nghiệm "bỏ ô"
    require_permanent_label: bool = True

    def feature_lists(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {"past": [], "obs": [], "future": []}
        for g in self.groups:
            if g not in FEATURE_GROUPS:
                raise ValueError(f"Nhóm đặc trưng không tồn tại: {g}")
            for kind, names in FEATURE_GROUPS[g].items():
                if kind == "obs" and self.latency_h is None:
                    continue
                out[kind] += [n for n in names if n not in out[kind]]
        out["past"] += list(TIME_FEATURES)
        out["future"] += list(TIME_FEATURES)
        return out

    def key(self) -> str:
        return hashlib.sha1(json.dumps(asdict(self), sort_keys=True, default=list).encode()).hexdigest()[:10]


# ------------------------------------------------------------------ dữ liệu --

def build_cell_major(dataset_dir: Path = DATASET_DIR, years: Iterable[int] | None = None) -> None:
    """Gộp các file năm ``[giờ, ô, đặc trưng]`` thành một memmap ``[ô, giờ, đặc trưng]``."""
    if years is None:
        years = sorted(int(p.stem) for p in dataset_dir.glob("[0-9][0-9][0-9][0-9].npy"))
    years = list(years)
    shapes = [np.load(dataset_dir / f"{y}.npy", mmap_mode="r").shape for y in years]
    n_cells, n_feat = shapes[0][1], shapes[0][2]
    total = sum(s[0] for s in shapes)
    cube = np.lib.format.open_memmap(dataset_dir / CUBE, mode="w+", dtype=np.float32, shape=(n_cells, total, n_feat))
    hours, t0 = [], 0
    for y, s in zip(years, shapes):
        block = np.load(dataset_dir / f"{y}.npy", mmap_mode="r")
        for c in range(n_cells):
            cube[c, t0:t0 + s[0], :] = block[:, c, :]
        hours.append(np.load(dataset_dir / f"{y}_hours.npy"))
        t0 += s[0]
    cube.flush()
    hours_all = np.concatenate(hours).astype("datetime64[ns]")
    if np.any(np.diff(hours_all) != np.timedelta64(1, "h")):
        raise ValueError("Trục thời gian sau khi gộp không liên tục từng giờ")
    np.save(dataset_dir / HOURS, hours_all)


class DatasetV2:
    """Truy cập dataset v2 đã gộp; không tự nạp hết vào RAM."""

    def __init__(self, dataset_dir: Path = DATASET_DIR):
        self.dir = Path(dataset_dir)
        manifest = json.loads((self.dir / "manifest.json").read_text(encoding="utf-8"))
        self.feature_names: list[str] = [f["name"] for f in manifest["features"]]
        self.feature_index = {n: k for k, n in enumerate(self.feature_names)}
        self.cells = pd.read_parquet(self.dir / "cells.parquet")
        self.cube = np.load(self.dir / CUBE, mmap_mode="r")
        self.hours = pd.DatetimeIndex(np.load(self.dir / HOURS))
        if self.cube.shape != (len(self.cells), len(self.hours), len(self.feature_names)):
            raise ValueError(f"Kích thước cube {self.cube.shape} không khớp metadata")

    def idx(self, names: Sequence[str]) -> np.ndarray:
        return np.array([self.feature_index[n] for n in names], dtype=np.int64)

    def select_cells(self, cfg: WindowConfig) -> np.ndarray:
        cells = self.cells
        mask = cells["province"].notna() | cfg.include_foreign
        if cfg.provinces is not None:
            mask &= cells["province"].isin(cfg.provinces)
        if cfg.exclude_sites:
            mask &= ~cells["site"].isin(cfg.exclude_sites)
        return np.flatnonzero(mask.to_numpy())


# ------------------------------------------------------------ chỉ số mẫu --

def _window_all(ok: np.ndarray, start_offset: int, length: int, issue: np.ndarray) -> np.ndarray:
    """``ok[τ]`` đúng cho mọi τ ∈ [issue+start_offset, issue+start_offset+length)."""
    csum = np.concatenate([[0], np.cumsum(ok, dtype=np.int64)])
    lo = issue + start_offset
    hi = lo + length
    inside = (lo >= 0) & (hi <= len(ok))
    out = np.zeros(len(issue), dtype=bool)
    out[inside] = (csum[hi[inside]] - csum[lo[inside]]) == length
    return out


def sample_index(ds: DatasetV2, cfg: WindowConfig, years: Iterable[int], cache_dir: Path | None = None) -> np.ndarray:
    """Mảng ``[N, 2]`` gồm (vị trí ô trong cube, chỉ số giờ phát hành) của mọi cửa sổ hợp lệ.

    Hợp lệ khi: giờ đích đầu tiên thuộc ``years``; đủ dữ liệu cho mọi đặc trưng quá khứ,
    quan trắc (sau khi dịch trễ), tương lai và nhãn; nhãn là bản permanent nếu yêu cầu.
    """
    years = sorted(set(int(y) for y in years))
    cache = None
    if cache_dir is not None:
        cache = Path(cache_dir) / f"index_v2_{cfg.key()}_{'-'.join(map(str, years))}.npy"
        if cache.exists():
            return np.load(cache)
    feats = cfg.feature_lists()
    p_idx, o_idx, f_idx = ds.idx(feats["past"]), ds.idx(feats["obs"]), ds.idx(feats["future"])
    lab = ds.feature_index[LABEL]
    perm = ds.feature_index["label_permanent"]
    W, H, L = cfg.input_len, cfg.horizon, (cfg.latency_h or 0)

    t_all = np.arange(len(ds.hours))
    in_years = np.isin(ds.hours.year, years)
    hour_ok = (ds.hours.hour % cfg.issue_stride_h) == 0
    if cfg.issue_hours_utc is not None:
        hour_ok &= np.isin(ds.hours.hour, cfg.issue_hours_utc)
    candidates = t_all[in_years & hour_ok]

    out = []
    for c in ds.select_cells(cfg):
        block = np.asarray(ds.cube[c])                      # [T, F], một ô ~20 MB
        past_ok = np.isfinite(block[:, p_idx]).all(axis=1)
        fut_ok = np.isfinite(block[:, f_idx]).all(axis=1)
        lab_ok = np.isfinite(block[:, lab])
        if cfg.require_permanent_label:
            lab_ok &= block[:, perm] == 1
        valid = (_window_all(past_ok, -W, W, candidates)
                 & _window_all(fut_ok, 0, H, candidates)
                 & _window_all(lab_ok, 0, H, candidates)
                 & _window_all(in_years, 0, H, candidates))
        if len(o_idx):
            obs_ok = np.isfinite(block[:, o_idx]).all(axis=1)
            valid &= _window_all(obs_ok, -W - L, W, candidates)
        good = candidates[valid]
        out.append(np.stack([np.full(len(good), c), good], axis=1))
    # int32 đủ cho chỉ số ô và giờ (< 2^31); cache nhẹ bằng một nửa so với int64.
    index = np.concatenate(out).astype(np.int32) if out else np.zeros((0, 2), dtype=np.int32)
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.save(cache, index)
    return index


def season_of(ds: DatasetV2, index: np.ndarray, utc_offset_hours: int = 7) -> np.ndarray:
    """Mùa (winter/summer/spring) theo tháng địa phương của giờ đích đầu tiên."""
    months = (ds.hours[index[:, 1]] + pd.Timedelta(hours=utc_offset_hours)).month
    return np.array([SEASON_OF_MONTH[m] for m in months])


def epoch_subset(index: np.ndarray, n: int, seed: int) -> np.ndarray:
    """Rút ngẫu nhiên ``n`` cửa sổ cho một epoch (mỗi epoch một seed khác nhau).

    Các cửa sổ liền giờ của cùng một ô gần như trùng nhau, nên duyệt hết hàng chục
    triệu cửa sổ mỗi epoch là lãng phí; lấy mẫu con giữ được đa dạng mà nhanh hơn nhiều.
    """
    if n >= len(index):
        return index[np.random.default_rng(seed).permutation(len(index))]
    return index[np.random.default_rng(seed).choice(len(index), n, replace=False)]


def holdout_sites(ds: DatasetV2, cfg: WindowConfig, frac: float = 0.2, seed: int = 0) -> tuple[str, ...]:
    """Chọn ngẫu nhiên một phần ô làm tập "ô chưa thấy" (thí nghiệm bỏ ô trong cùng tỉnh)."""
    cells = ds.cells.iloc[ds.select_cells(cfg)]
    rng = np.random.default_rng(seed)
    n = max(1, int(round(frac * len(cells))))
    return tuple(sorted(rng.choice(cells["site"].to_numpy(), n, replace=False)))


# ------------------------------------------------------------ chuẩn hóa --

@dataclass
class Normalizer:
    """log1p cho biến lệch phải rồi chuẩn hóa z; mean/std chỉ tính trên dữ liệu train."""
    mean: dict[str, float] = field(default_factory=dict)
    std: dict[str, float] = field(default_factory=dict)
    static_mean: dict[str, float] = field(default_factory=dict)
    static_std: dict[str, float] = field(default_factory=dict)

    @classmethod
    def fit(cls, ds: DatasetV2, cfg: WindowConfig, train_years: Iterable[int], max_rows_per_cell: int = 5_000,
            seed: int = 0) -> "Normalizer":
        feats = cfg.feature_lists()
        names = sorted(set(feats["past"] + feats["obs"] + feats["future"]) - set(TIME_FEATURES))
        idx = ds.idx(names)
        rows = np.flatnonzero(np.isin(ds.hours.year, list(train_years)))
        rng = np.random.default_rng(seed)
        cells = ds.select_cells(cfg)
        samples = []
        for c in cells:
            pick = np.sort(rng.choice(rows, min(max_rows_per_cell, len(rows)), replace=False))
            samples.append(np.asarray(ds.cube[c][pick][:, idx]))
        data = np.concatenate(samples)
        norm = cls()
        for k, name in enumerate(names):
            col = data[:, k]
            col = col[np.isfinite(col)]
            if name in LOG1P_FEATURES:
                col = np.log1p(np.maximum(col, 0))
            norm.mean[name] = float(col.mean())
            norm.std[name] = float(col.std()) or 1.0
        static = ds.cells.iloc[cells][list(STATIC_FEATURES)].astype(float)
        for name in STATIC_FEATURES:
            col = static[name].fillna(0.0)
            norm.static_mean[name] = float(col.mean())
            norm.static_std[name] = float(col.std()) or 1.0
        return norm

    def transform(self, values: np.ndarray, names: Sequence[str]) -> np.ndarray:
        out = values.astype(np.float32, copy=True)
        for k, name in enumerate(names):
            if name in TIME_FEATURES:
                continue
            col = out[..., k]
            if name in LOG1P_FEATURES:
                col = np.log1p(np.maximum(col, 0))
            out[..., k] = (col - self.mean[name]) / self.std[name]
        return out

    def transform_static(self, frame: pd.DataFrame) -> np.ndarray:
        cols = [(frame[n].astype(float).fillna(0.0) - self.static_mean[n]) / self.static_std[n] for n in STATIC_FEATURES]
        return np.stack(cols, axis=-1).astype(np.float32)

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Normalizer":
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))


# ---------------------------------------------------------------- lấy mẫu --

class WindowSampler:
    """Lấy batch numpy từ chỉ số mẫu; dùng chung cho mọi framework."""

    def __init__(self, ds: DatasetV2, cfg: WindowConfig, norm: Normalizer):
        self.ds, self.cfg, self.norm = ds, cfg, norm
        feats = cfg.feature_lists()
        self.past_names = feats["past"]
        self.obs_names = feats["obs"]
        self.future_names = feats["future"]
        self._p = ds.idx(self.past_names)
        self._o = ds.idx(self.obs_names)
        self._f = ds.idx(self.future_names)
        self._y = ds.feature_index[LABEL]
        self._static = norm.transform_static(ds.cells)

    @property
    def x_past_names(self) -> list[str]:
        return self.past_names + [f"{n}@lag{self.cfg.latency_h}" for n in self.obs_names]

    def get(self, cell: int, issue: int) -> dict[str, np.ndarray]:
        W, H, L = self.cfg.input_len, self.cfg.horizon, (self.cfg.latency_h or 0)
        lo = issue - W - L
        block = np.asarray(self.ds.cube[cell, lo:issue + H])      # một lần đọc liền mạch
        past = block[L:L + W][:, self._p]
        parts = [self.norm.transform(past, self.past_names)]
        if len(self._o):
            parts.append(self.norm.transform(block[0:W][:, self._o], self.obs_names))
        future = block[L + W:L + W + H]
        return {
            "x_past": np.concatenate(parts, axis=1),
            "x_future": self.norm.transform(future[:, self._f], self.future_names),
            "static": self._static[cell],
            "y": future[:, self._y].astype(np.float32),
        }

    def batch(self, index: np.ndarray) -> dict[str, np.ndarray]:
        items = [self.get(int(c), int(t)) for c, t in index]
        out = {k: np.stack([it[k] for it in items]) for k in items[0]}
        out["cell"] = index[:, 0].copy()
        out["issue"] = index[:, 1].copy()
        return out


def torch_dataset(sampler: WindowSampler, index: np.ndarray):
    """Bọc ``WindowSampler`` thành ``torch.utils.data.Dataset`` (chỉ import torch khi cần)."""
    import torch
    from torch.utils.data import Dataset

    class _WindowDataset(Dataset):
        def __len__(self) -> int:
            return len(index)

        def __getitem__(self, i: int) -> dict:
            item = sampler.get(int(index[i, 0]), int(index[i, 1]))
            out = {k: torch.from_numpy(v) for k, v in item.items()}
            out["cell"] = torch.tensor(int(index[i, 0]))
            out["issue"] = torch.tensor(int(index[i, 1]))
            return out

    return _WindowDataset()


# ------------------------------------------------------------ cấu hình sẵn --

DEFAULT_SPLIT = {"train": tuple(range(2015, 2022)), "val": (2022, 2023), "val_ops": (2024,), "test": (2025,)}


def product_a(groups: Sequence[str] = ("A0",), latency_h: int | None = 4, **kw) -> WindowConfig:
    return WindowConfig(groups=tuple(groups), input_len=24, horizon=6, latency_h=latency_h,
                        issue_stride_h=kw.pop("issue_stride_h", 1), **kw)


def product_b(groups: Sequence[str] = ("B0",), latency_h: int | None = 4, **kw) -> WindowConfig:
    return WindowConfig(groups=tuple(groups), input_len=168, horizon=72, latency_h=latency_h, issue_stride_h=6,
                        issue_hours_utc=(0, 6, 12, 18), **kw)
