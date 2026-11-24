"""Temporal contract and leakage-safe windows for station rainfall forecasts.

No station measurements or private registry are stored in this module. The
Parquet contains complete time axes; filter sample indices, never the history
rows themselves. Values are physical units, not fitted/normalized features.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

GROUPS = {
    "B": ["t2m_c", "td2m_c", "rh2m_pct", "sp_hpa", "mslp_hpa", "u10", "v10",
          "sin_hour", "cos_hour", "sin_doy", "cos_doy"],
    "A": ["cape", "cin_capped", "has_lfc", "tcwv", "kx", "tt", "blh",
          "tcc", "lcc", "mcc", "hcc", "swvl1"],
    "M": ["u850", "v850", "q850_gkg", "t850_c", "rh850_pct", "w850_pas",
          "u500", "v500", "q500_gkg", "t500_c", "w500_pas", "shear_850_500",
          "ivt_u", "ivt_v", "ivt_mag", "vimd_mmh", "ctx_tcwv", "ctx_ivt_mag",
          "cold_surge_dp_hpa", "dp_tonkin_south_hpa"],
    "C": ["sst_region_c"],
}
EXPERIMENTS = {
    "E0": "B", "E1": "BA", "E2": "BM", "E3": "BC", "E4": "BAM",
    "E5": "BAC", "E6": "BMC", "E7": "BAMC",
}
SPECS = {"1h": {"history": 24, "horizon": 6, "hours": 1, "prefix": "y_h"},
         "24h": {"history": 7, "horizon": 3, "hours": 24, "prefix": "y_d"}}
ALL_FEATURES = sum(GROUPS.values(), [])
PHYSICAL_FEATURES = [c for c in ALL_FEATURES if not c.startswith(("sin_", "cos_"))]


def feature_names(resolution: str, experiment: str = "E7", use_rain: bool = True) -> list[str]:
    SPECS[resolution]  # Validate rather than silently choose a default.
    names = sum((GROUPS[g] for g in EXPERIMENTS[experiment]), [])
    if resolution == "24h":
        names = [n for n in names if n not in ("sin_hour", "cos_hour")]
    return names + (["rain_mm"] if use_rain else [])


def label_names(resolution: str) -> list[str]:
    s = SPECS[resolution]
    return [f"{s['prefix']}{h}_mm" for h in range(1, s["horizon"] + 1)]


def utc_intervals(clock_end_naive: np.ndarray) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex]:
    """Vrain 10:00 Vietnam means rain 09:00--10:00, i.e. 02:00--03:00 UTC."""
    end = pd.DatetimeIndex(pd.to_datetime(clock_end_naive)).tz_localize("Asia/Ho_Chi_Minh").tz_convert("UTC").as_unit("ns")
    if end.has_duplicates or not end.is_monotonic_increasing:
        raise ValueError("Duplicate or unsorted source clocks")
    if len(end) > 1 and not np.all(np.diff(end.asi8) == pd.Timedelta(hours=1).value):
        raise ValueError("Source time axis must contain every hour, including missing observations")
    return end - pd.Timedelta(hours=1), end


def calendar_at_end(end_utc: pd.DatetimeIndex) -> np.ndarray:
    local = end_utc.tz_convert("Asia/Ho_Chi_Minh")
    hour = local.hour.to_numpy() + local.minute.to_numpy() / 60
    doy = local.dayofyear.to_numpy()
    return np.stack([np.sin(2*np.pi*hour/24), np.cos(2*np.pi*hour/24),
                     np.sin(2*np.pi*doy/365.25), np.cos(2*np.pi*doy/365.25)], 1).astype("float32")


def strict_bilinear(nodes: np.ndarray, indices: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """No extrapolation or renormalization over missing contributing corners."""
    if not np.allclose(weights.sum(1), 1) or np.any(weights < -1e-8):
        raise ValueError("Invalid spatial weights")
    values = nodes[:, indices, :]
    valid = np.isfinite(values)
    required = weights[None, :, :, None] > 1e-10
    out = (np.where(valid, values, 0) * weights[None, :, :, None]).sum(2)
    out[~(valid | ~required).all(2)] = np.nan
    return out.astype("float32")


def history_complete(valid: np.ndarray, length: int) -> np.ndarray:
    valid = np.asarray(valid, bool)
    out = np.zeros(len(valid), bool)
    counts = np.r_[0, np.cumsum(valid, dtype="int64")]
    if len(valid) >= length:
        out[length-1:] = counts[length:] - counts[:-length] == length
    return out


def future_labels(rain: np.ndarray, horizon: int) -> np.ndarray:
    y = np.full((len(rain), horizon), np.nan, dtype="float32")
    for h in range(1, horizon+1):
        if h < len(rain):
            y[:-h, h-1] = rain[h:]
    return y


def target_splits(issue: pd.DatetimeIndex, horizon_hours: int) -> np.ndarray:
    """The entire target interval must be inside one chronological fold."""
    result = np.full(len(issue), "unused", dtype=object)
    target_end = issue + pd.Timedelta(hours=horizon_hours)
    for name, first, stop in [("train", "2021-01-01", "2023-01-01"),
                              ("cal", "2023-01-01", "2024-01-01"),
                              ("dev", "2024-01-01", "2025-01-01")]:
        a = pd.Timestamp(first, tz="Asia/Ho_Chi_Minh").tz_convert("UTC")
        b = pd.Timestamp(stop, tz="Asia/Ho_Chi_Minh").tz_convert("UTC")
        result[(issue >= a) & (target_end <= b)] = name
    return result


def sample_flags(weather: np.ndarray, rain: np.ndarray, issue: pd.DatetimeIndex,
                 resolution: str) -> dict[str, np.ndarray | bool]:
    spec = SPECS[resolution]
    complete = np.isfinite(weather).all(1)
    y = future_labels(rain, spec["horizon"])
    split = target_splits(issue, spec["horizon"] * spec["hours"])
    r0 = history_complete(complete, spec["history"]) & np.isfinite(y).all(1) & (split != "unused")
    r1 = r0 & history_complete(np.isfinite(rain), spec["history"])
    # Known-station evaluation: eligibility comes only from the training fold.
    seen = bool((r1 & (split == "train")).any())
    return {"weather_complete": complete, "labels": y, "split": split,
            "station_seen_train": seen, "sample_ready_r0": r0 & seen,
            "sample_ready_r1": r1 & seen}


class StationForecastData:
    """Small NumPy dataset compatible with torch DataLoader, without torch dependency.

    All E/model variants default to the same R1-ready sample mask. R0 omits past
    rain from X while retaining this mask for a fair R0/R1 comparison. Set
    paired_r=False explicitly only for the separate weather-only availability
    sensitivity. Never feed all numeric Parquet columns to a model.
    """
    def __init__(self, path: str | Path, resolution: str, split: str = "train",
                 experiment: str = "E7", use_rain: bool = True, paired_r: bool = True,
                 stations: list[str] | None = None):
        if split not in ("train", "cal", "dev"):
            raise ValueError("2025 is reserved; choose train, cal or dev")
        self.spec = SPECS[resolution]
        self.feature_names = feature_names(resolution, experiment, use_rain)
        self.label_names = label_names(resolution)
        flag = "sample_ready_r1" if paired_r or use_rain else "sample_ready_r0"
        columns = list(dict.fromkeys(["station_id", "period_end_utc", "latitude", "longitude",
                                      "split", flag] + self.feature_names + self.label_names))
        filters = [("resolution", "=", resolution)]
        if stations is not None:
            if not stations:
                raise ValueError("Empty station selection")
            filters.append(("station_id", "in", stations))
        frame = pd.read_parquet(path, columns=columns, filters=filters)
        frame = frame.sort_values(["station_id", "period_end_utc"]).reset_index(drop=True)
        self.x = frame[self.feature_names].to_numpy("float32")
        self.y = frame[self.label_names].to_numpy("float32")
        self.static = frame[["latitude", "longitude"]].to_numpy("float32")
        self.sid = frame.station_id.to_numpy()
        self.times = pd.DatetimeIndex(frame.period_end_utc).as_unit("ns").asi8
        self.indices = np.flatnonzero(frame[flag].to_numpy(bool) & frame.split.eq(split).to_numpy())
        self.resolution = resolution
        self.split = split
        self.contract = json.loads(pq.read_schema(path).metadata[b"pbl6_contract"])
        # Validate index topology without constructing a giant window tensor.
        lo = self.indices - self.spec["history"] + 1
        if (lo < 0).any() or not np.all(self.sid[lo] == self.sid[self.indices]):
            raise ValueError("Window crosses a station boundary")
        step = pd.Timedelta(hours=self.spec["hours"]).value
        if not np.all(self.times[self.indices] - self.times[lo] == (self.spec["history"]-1)*step):
            raise ValueError("Window crosses a removed timestamp")

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, n: int) -> dict:
        i = self.indices[n]
        x = self.x[i-self.spec["history"]+1:i+1]
        y = self.y[i]
        if not np.isfinite(x).all() or not np.isfinite(y).all():
            raise ValueError("Selected sample is not complete")
        hours = self.spec["hours"] * np.arange(1, self.spec["horizon"]+1)
        future = pd.to_datetime(self.times[i], utc=True) + pd.to_timedelta(hours, unit="h")
        cal = calendar_at_end(pd.DatetimeIndex(future))
        if self.resolution == "24h":
            cal = cal[:, 2:]
        return {"x": x, "y": y, "static": self.static[i], "station_id": str(self.sid[i]),
                "station_code": int(self.sid[i][2:])-1, "issue_time_utc_ns": int(self.times[i]),
                "future_calendar": cal}
