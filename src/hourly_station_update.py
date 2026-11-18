"""Contracts for the versioned hourly ERA5/Vrain handoff; no model fitting."""
from pathlib import Path
import numpy as np
import pandas as pd

from src.station_forecast_data import future_labels, history_complete, StationForecastData

ROOT = Path(__file__).resolve().parents[1]
VERSION = "station_hourly_era5_2026_11_17"
BASE = ROOT / "data/operational/era5_station_hourly_2026_11_17"
OUT = ROOT / "data/processed" / VERSION
PUBLIC = ROOT / "reports" / VERSION
RAIN_BASE = ROOT / "data/operational/vrain_update_2026_11_16"
DATASET = "PBL6_TRAM_GIO_ERA5_2021_2026.parquet"
ROLES = ("train", "cal", "dev", "reserved2025", "external2026")


def extended_splits(issue):
    """Every future rain interval must remain in one local chronological role."""
    issue = pd.DatetimeIndex(issue)
    stop = issue + pd.Timedelta(hours=6)
    result = np.full(len(issue), "boundary", dtype=object)
    for role, first, end in [("train", 2021, 2023), ("cal", 2023, 2024),
                             ("dev", 2024, 2025), ("reserved2025", 2025, 2026),
                             ("external2026", 2026, 2027)]:
        a = pd.Timestamp(f"{first}-01-01", tz="Asia/Ho_Chi_Minh").tz_convert("UTC")
        b = pd.Timestamp(f"{end}-01-01", tz="Asia/Ho_Chi_Minh").tz_convert("UTC")
        result[(issue >= a) & (stop <= b)] = role
    return result


def source_windows(codes, history=24, horizon=6):
    """Require one source, with no missing/conflicting bins, over X and all y."""
    codes = np.asarray(codes)
    out = np.zeros(len(codes), bool)
    for source in (0, 1):
        ok = codes == source
        past = history_complete(ok, history)
        future = np.zeros(len(ok), bool)
        if len(ok) > horizon:
            counts = np.r_[0, np.cumsum(ok, dtype="int64")]
            future[:-horizon] = counts[horizon+1:] - counts[1:-horizon] == horizon
        out |= past & future
    return out


def hourly_flags(weather, rain, codes, end):
    complete = np.isfinite(weather).all(1)
    y = future_labels(rain, 6)
    split = extended_splits(end)
    same_source = source_windows(codes)
    technical = (history_complete(complete, 24) &
                 history_complete(np.isfinite(rain), 24) &
                 np.isfinite(y).all(1) & same_source & (split != "boundary"))
    seen = bool((technical & (split == "train")).any())
    ready = technical & seen
    return dict(weather_complete=complete, source_consistent_window=same_source,
                sample_complete=technical, station_seen_train=seen,
                sample_ready_r0=ready, sample_ready_r1=ready,
                recommended_sample=ready, split=split, labels=y)


class HourlyStationData(StationForecastData):
    """Consumer for this new release, preserving the old loader's year guard.

    Reads reserve/external data only when the caller names that role explicitly;
    does not fit a scaler or model. The old v1 consumer remains unchanged.
    """
    def __init__(self, path, split="train", experiment="E7", use_rain=True, stations=None):
        if split not in ROLES:
            raise ValueError("Unknown hourly release role")
        # Parent reads the continuous axes and the whitelisted features. Its old
        # train/cal/dev guard stays intact; replace only the selected issue role.
        super().__init__(path, "1h", "train", experiment, use_rain=use_rain,
                         stations=stations, paired_r=True)
        if self.contract.get("version") != VERSION:
            raise ValueError("Use this loader only with the new hourly release")
        if split != "train":
            filters = [("resolution", "=", "1h")]
            if stations is not None:
                filters.append(("station_id", "in", stations))
            frame = pd.read_parquet(path, columns=["station_id", "period_end_utc", "split", "sample_ready_r1"],
                                    filters=filters).sort_values(["station_id", "period_end_utc"]).reset_index(drop=True)
            if not np.array_equal(frame.station_id.to_numpy(), self.sid):
                raise ValueError("Consumer station axes differ")
            times = pd.DatetimeIndex(frame.period_end_utc).as_unit("ns").asi8
            if not np.array_equal(times, self.times):
                raise ValueError("Consumer time axes differ")
            self.indices = np.flatnonzero(frame.sample_ready_r1.to_numpy(bool) & frame.split.eq(split).to_numpy())
            lo = self.indices-23
            if (lo < 0).any() or not np.all(self.sid[lo] == self.sid[self.indices]):
                raise ValueError("Window crosses station boundary")
            if not np.all(self.times[self.indices]-self.times[lo] == pd.Timedelta(hours=23).value):
                raise ValueError("Window crosses a removed timestamp")
        self.split = split
