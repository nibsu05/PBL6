"""Paired hourly station samples and a pooled Bi-LSTM for six rainfall depths."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch
from torch import nn

from src.hourly_station_update import DATASET, OUT, VERSION, source_windows
from src.station_forecast_data import future_labels, history_complete, label_names


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/station_nowcast_2026_11_24"
PRIVATE = ROOT / "data/operational" / REPORT.name
SOURCE = OUT / DATASET
PROTOCOL = json.loads((REPORT / "protocol.json").read_text(encoding="utf-8"))
HISTORY = PROTOCOL["history_hours"]
LEADS = PROTOCOL["lead_hours"]
HORIZON = len(LEADS)
FEATURES = PROTOCOL["feature_sets"]
ALL = FEATURES["E2"]
RAW = ["rain_mm", "t2m_c", "u10", "v10", "rh2m_pct", "sp_hpa", "u850", "v850"]
DELTA = {
    "delta_rain": "rain_mm",
    "delta_t2m": "t2m_c",
    "delta_wind_speed": "wind_speed",
    "delta_rh": "rh2m_pct",
    "delta_pressure": "sp_hpa",
}
DELTA_IDX = [ALL.index(name) for name in DELTA]
LABELS = label_names("1h")
HOUR_NS = pd.Timedelta(hours=1).value
ZONE = PROTOCOL["time_zone"]


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_json(path: Path, payload: dict) -> None:
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                       encoding="utf-8")
    pending.replace(path)


def local_year(year: int) -> pd.Timestamp:
    return pd.Timestamp(f"{year}-01-01", tz=ZONE).tz_convert("UTC")


def feature_rows(frame: pd.DataFrame, names: list[str]) -> np.ndarray:
    """Prepare causal hourly covariates on one uninterrupted station axis."""
    raw = {name: frame[name].to_numpy(dtype=np.float32) for name in names if name in frame}
    raw["month"] = pd.DatetimeIndex(frame["period_end_utc"]).tz_convert(ZONE).month.to_numpy("float32")
    if "wind_speed" in names:
        raw["wind_speed"] = np.hypot(frame["u10"].to_numpy("float32"), frame["v10"].to_numpy("float32"))
    for derived, base in DELTA.items():
        if derived in names:
            raw[derived] = np.diff(raw[base], prepend=np.float32(0))
    return np.column_stack([raw[name] for name in names]).astype("float32", copy=False)


def supported_history(rain: np.ndarray, source: np.ndarray, code: int) -> np.ndarray:
    """Eligibility to issue a forecast depends solely on past observations."""
    return history_complete(np.isfinite(rain) & (rain >= 0) & (source == code), HISTORY)


def scoring_windows(rain: np.ndarray, source: np.ndarray, weather_ok: np.ndarray,
                    code: int) -> tuple[np.ndarray, np.ndarray]:
    """Intersect history availability with observed verification bins."""
    y = future_labels(rain, HORIZON)
    valid = (supported_history(rain, source, code)
             & history_complete(weather_ok, HISTORY)
             & np.isfinite(y).all(axis=1)
             & (y >= 0).all(axis=1)
             & source_windows(source, history=HISTORY, horizon=HORIZON))
    return valid, y


def _station_blocks(frame: pd.DataFrame):
    for station, group in frame.groupby("station_id", sort=True, observed=True):
        group = group.sort_values("period_end_utc", ignore_index=True)
        ticks = pd.DatetimeIndex(group.period_end_utc).as_unit("ns").asi8
        if len(ticks) > 1 and not (np.diff(ticks) == HOUR_NS).all():
            raise ValueError(f"Incomplete or duplicate hourly axis at {station}")
        yield str(station), group, ticks


@dataclass
class Samples:
    x: np.ndarray
    y: np.ndarray
    times: np.ndarray
    station_index: np.ndarray
    stations: list[str]
    origins: dict[str, np.ndarray]
    train_rows: np.ndarray | None
    coverage: pd.DataFrame

    def ids(self, idx: np.ndarray) -> np.ndarray:
        return np.asarray(self.stations)[self.station_index[idx]]


def read_samples(path: Path, roles: tuple[str, ...], stations: list[str] | None = None,
                 fit_scaler: bool = False) -> Samples:
    """Keep continuous rows. Restrict origins by fold only after building windows."""
    contract = json.loads(pq.read_schema(path).metadata[b"pbl6_contract"])
    if contract.get("version") != VERSION:
        raise ValueError("Select the verified hourly release")
    dates = {role: [local_year(year) for year in PROTOCOL["splits"][role]] for role in roles}
    start = min(pair[0] for pair in dates.values())
    stop = max(pair[1] for pair in dates.values())
    columns = [*RAW, *LABELS, "station_id", "period_end_utc", "gauge_source_code",
               "weather_complete", "sample_ready_r1", "split"]
    frame = pd.read_parquet(
        path, columns=columns,
        filters=[("period_end_utc", ">=", start - pd.Timedelta(hours=HISTORY)),
                 ("period_end_utc", "<=", stop)],
    )
    roster = stations or sorted(frame.station_id.unique().tolist())
    lookup = {station: i for i, station in enumerate(roster)}
    if len(lookup) != len(roster):
        raise ValueError("Duplicate station IDs in model roster")
    obs_code = PROTOCOL["historical_gauge_source_code"]
    parts, targets, clocks, mapping, scaling, coverage = [], [], [], [], [], []
    origins = {role: [] for role in roles}
    offset = 0
    for station, group, ticks in _station_blocks(frame):
        row = {"station_id": station}
        if station not in lookup:
            coverage.append({**row, **dict.fromkeys(roles, 0)})
            continue
        rain = group.rain_mm.to_numpy("float32")
        codes = group.gauge_source_code.to_numpy()
        complete = group.weather_complete.to_numpy(bool)
        valid, y = scoring_windows(rain, codes, complete, obs_code)
        packed = group[LABELS].to_numpy("float32")
        release_ready = group.sample_ready_r1.to_numpy(bool)
        selected = []
        for role, (a, b) in dates.items():
            inside = (ticks >= a.value) & (ticks + HORIZON * HOUR_NS <= b.value)
            mask = inside & valid & release_ready
            expected = (group["split"].eq(role).to_numpy(bool) & release_ready)
            if not np.array_equal(mask, expected):
                raise ValueError(f"Rebuilt sample mask disagrees with release at {station}/{role}")
            if not np.array_equal(y[mask], packed[mask]):
                raise ValueError(f"Six future rain bins disagree at {station}/{role}")
            idx = np.flatnonzero(mask)
            origins[role].append(idx + offset)
            selected.append(idx)
            row[role] = len(idx)
        if not any(row[role] for role in roles) and stations is None:
            coverage.append(row)
            continue
        x = feature_rows(group, ALL)
        if fit_scaler:
            fit_origins = selected[roles.index("train")]
            # Union of rows actually used by training windows, for train-only scaling.
            occupied = np.zeros(len(group) + 1, dtype=np.int32)
            np.add.at(occupied, fit_origins - HISTORY + 1, 1)
            np.add.at(occupied, fit_origins + 1, -1)
            train = occupied[:-1].cumsum() > 0
            scaling.append(train)
        parts.append(x)
        targets.append(y)
        clocks.append(ticks)
        mapping.append(np.full(len(group), lookup[station], np.int16))
        offset += len(group)
        coverage.append(row)
    if not parts or not all(any(len(a) for a in offsets) for offsets in origins.values()):
        raise ValueError("One of the requested roles does not contain paired samples")
    train_rows = np.concatenate(scaling) if fit_scaler else None
    return Samples(np.concatenate(parts), np.concatenate(targets), np.concatenate(clocks),
                   np.concatenate(mapping), roster,
                   {role: np.concatenate(result) for role, result in origins.items()},
                   train_rows, pd.DataFrame(coverage))


def fit_scaling(samples: Samples) -> tuple[np.ndarray, np.ndarray]:
    train = samples.x[samples.train_rows].astype("float64")
    # A delta can be missing in the oldest bin only; it is zeroed per window.
    values = np.where(np.isfinite(train), train, np.nan)
    mean, std = np.nanmean(values, axis=0), np.nanstd(values, axis=0)
    if not (np.isfinite(mean).all() and np.isfinite(std).all()):
        raise ValueError("Missing train-only scaling statistics")
    return mean.astype("float32"), np.where(std > 1e-8, std, 1).astype("float32")


class WindowTensors:
    def __init__(self, x, y, indices, mean, std, device):
        self.device = device
        self.x = torch.as_tensor((x - mean) / std, device=device)
        self.zero = torch.as_tensor(-mean / std, device=device)
        self.y = torch.as_tensor(y, device=device)
        self.stations = torch.as_tensor(indices, dtype=torch.long, device=device)
        self.offset = torch.arange(1 - HISTORY, 1, device=device)

    def window(self, origins, experiment):
        x = self.x[origins[:, None] + self.offset]
        x[:, 0, DELTA_IDX] = self.zero[DELTA_IDX]
        x[:, :, len(FEATURES[experiment]):] = 0.0
        return x, self.stations[origins]


class PooledBiLSTM(nn.Module):
    def __init__(self, n_stations: int):
        super().__init__()
        hp = PROTOCOL["bilstm"]
        size = hp["hidden_size_per_direction"]
        self.station_embedding = nn.Embedding(n_stations, hp["station_embedding_size"])
        self.recurrent = nn.LSTM(len(ALL), size, bidirectional=True, batch_first=True)
        self.head = nn.Sequential(nn.Linear(size * 2 + hp["station_embedding_size"], hp["head_size"]),
                                  nn.ReLU(), nn.Dropout(hp["dropout"]),
                                  nn.Linear(hp["head_size"], HORIZON), nn.Softplus())
        nn.init.constant_(self.head[-2].bias, -2)

    def forward(self, x, station):
        _, (hidden, _) = self.recurrent(x)
        return self.head(torch.cat((hidden[0], hidden[1], self.station_embedding(station)), dim=1))


@torch.inference_mode()
def predict(model, data, indices, experiment, batch_size=2048):
    model.eval()
    amounts = []
    for batch in torch.as_tensor(indices, device=data.device).split(batch_size):
        x, station = data.window(batch, experiment)
        amounts.append(torch.expm1(model(x, station)).cpu().numpy())
    result = np.concatenate(amounts)
    if not np.isfinite(result).all() or (result < 0).any():
        raise ValueError("Forecast produced invalid rainfall depths")
    return result


def rain_tree_features(x, origins, station_index) -> np.ndarray:
    r = x[origins[:, None] + np.arange(1 - HISTORY, 1), ALL.index("rain_mm")]
    totals = [r[:, -length:].sum(1) for length in (3, 6, 24)]
    extremes = [r[:, -length:].max(1) for length in (6, 24)]
    return np.column_stack([r, *totals, *extremes, x[origins, ALL.index("month")],
                            station_index[origins]]).astype("float32", copy=False)
