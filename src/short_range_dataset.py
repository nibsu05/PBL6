"""Past-only regional windows: 168 h history -> three disjoint 24 h totals."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.dataset_v2 import time_features

ROOT = Path(__file__).resolve().parents[1]
TIME = ('sin_hour', 'cos_hour', 'sin_doy', 'cos_doy')
THRESHOLDS = np.array([16., 50., 100.], dtype=np.float32)
SOURCE = ROOT / 'data/processed/regional_danang/v1_hourly.parquet'
GROUPS = ROOT / 'reports/regional_research_plan_2026_10_20/feature_groups.json'


def feature_groups():
    config = json.loads(GROUPS.read_text(encoding='utf-8'))
    result = {}
    for experiment, keys in config['experiments'].items():
        result[experiment] = [name if name in TIME else 'mean__' + name
                              for key in keys for name in config[key]]
    return result


@dataclass
class DailySamples:
    dates: pd.DatetimeIndex
    x: np.ndarray
    future: np.ndarray
    y: np.ndarray
    features: list[str]
    positions: np.ndarray

    def select(self, names):
        indices = [self.features.index(name) for name in names]
        return DailySamples(self.dates, self.x[:, :, indices], self.future, self.y,
                            list(names), self.positions)


def daily_samples(frame, features):
    """All E share E7's history mask; future meteorology never enters a sample."""
    dates = pd.DatetimeIndex(pd.to_datetime(frame.datetime, utc=True)).as_unit('ns')
    if (not dates.is_monotonic_increasing or not dates.is_unique
            or not np.all(np.diff(dates.asi8) == pd.Timedelta(hours=1).value)):
        raise ValueError('Expected unique contiguous hourly UTC rows')
    values = frame[list(features)].to_numpy(dtype=np.float64)
    y = frame.y_region_gc_mm.to_numpy(dtype=np.float64)
    coverage = frame.label_valid_weight_fraction.to_numpy(dtype=np.float64)
    ok_y = (np.isfinite(y) & (y >= 0) & frame.label_permanent.to_numpy(bool)
            & np.isfinite(coverage) & np.isclose(coverage, 1., rtol=0, atol=1e-7))
    bad_x = np.r_[0, np.cumsum((~np.isfinite(values)).any(1))]
    bad_y = np.r_[0, np.cumsum(~ok_y)]
    positions = np.flatnonzero(dates.hour == 0)
    positions = positions[(positions >= 168) & (positions + 72 <= len(frame))]
    valid = ((bad_x[positions] - bad_x[positions - 168] == 0)
             & (bad_y[positions + 72] - bad_y[positions] == 0)
             & (dates[positions].year == dates[positions + 71].year))
    positions = positions[valid]
    if len(positions) == 0:
        raise ValueError('No complete daily windows')
    hist = positions[:, None] + np.arange(-168, 0)[None, :]
    x = values[hist].reshape(-1, 28, 6, len(features)).mean(2).astype(np.float32)
    target_pos = positions[:, None] + np.arange(72)[None, :]
    target = y[target_pos].reshape(-1, 3, 24).sum(2).astype(np.float32)
    # Derive future calendar from timestamps, never from future data columns.
    future_dates = pd.to_datetime(dates.asi8[target_pos].ravel(), utc=True)
    future = time_features(future_dates).reshape(-1, 12, 6, 4).mean(2).astype(np.float32)
    return DailySamples(dates[positions], x, future, target, list(features), positions)


def load_development():
    """Hard upper limit before 2024: no 2025 targets, features or diagnostics."""
    names = feature_groups()['E7']
    cutoff = pa.scalar(pd.Timestamp('2024-01-01', tz='UTC'), type=pa.timestamp('ns', tz='UTC'))
    columns = ['datetime', 'y_region_gc_mm', 'label_permanent', 'label_valid_weight_fraction', *names]
    frame = pq.read_table(SOURCE, columns=columns, filters=[('datetime', '<', cutoff)]).to_pandas()
    samples = daily_samples(frame, names)
    if samples.dates.year.min() < 2015 or samples.dates.year.max() > 2023:
        raise ValueError('Development years must be within 2015–2023')
    return samples


def train_scaler(x):
    center = x.mean((0, 1), dtype=np.float64)
    scale = x.std((0, 1), dtype=np.float64)
    scale = np.where(scale < 1e-6, 1., scale)
    return {'center': center.astype(np.float32), 'scale': scale.astype(np.float32)}


def scale_inputs(x, scaler):
    return ((x - scaler['center']) / scaler['scale']).astype(np.float32)


def tabular_inputs(samples):
    parts, names = [], []
    for i, name in enumerate(samples.features):
        x = samples.x[:, :, i]
        if name in TIME:
            parts.append(x[:, -1]); names.append(name + '@last6')
        else:
            for suffix, array in [('last6', x[:, -1]), ('mean24', x[:, -4:].mean(1)),
                                  ('mean72', x[:, -12:].mean(1)), ('mean168', x.mean(1)),
                                  ('change6', x[:, -1] - x[:, -2])]:
                parts.append(array); names.append(name + '@' + suffix)
    for step in range(12):
        for ci, name in enumerate(TIME):
            parts.append(samples.future[:, step, ci]); names.append(f'{name}@future6h{step}')
    return np.stack(parts, axis=1).astype(np.float32), names


def target_months(dates):
    return np.stack([(dates + pd.Timedelta(hours=24 * d)).month for d in range(3)], axis=1)


def fit_climatology(dates, y, strength=20.):
    months = target_months(dates)
    events = y[:, :, None] >= THRESHOLDS
    amount, probability = np.empty((12, 3)), np.empty((12, 3, 3))
    for lead in range(3):
        base = events[:, lead].mean(0)
        for month in range(1, 13):
            keep = months[:, lead] == month
            amount[month - 1, lead] = y[keep, lead].mean() if keep.any() else y[:, lead].mean()
            probability[month - 1, lead] = (events[keep, lead].sum(0) + strength * base) / (keep.sum() + strength)
    return {'amount': amount, 'probability': probability, 'strength': float(strength)}


def predict_climatology(dates, fitted):
    months = target_months(dates) - 1
    amount = np.stack([fitted['amount'][months[:, lead], lead] for lead in range(3)], axis=1)
    prob = np.stack([fitted['probability'][months[:, lead], lead] for lead in range(3)], axis=1)
    return amount, prob


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
