"""Daily past-only ERA5 predictors and station-based CPC regional targets."""
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.dataset_v2 import time_features
from src.short_range_dataset import DailySamples, feature_groups as hourly_groups

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/operational/daily_gauge_2026_11_04'
SOURCE = ROOT / 'data/processed/regional_danang/v1_hourly.parquet'
TIME = ('sin_doy', 'cos_doy')
HISTORY_DAYS = 7


def feature_groups():
    return {e: [c for c in columns if c not in ('sin_hour', 'cos_hour')]
            for e, columns in hourly_groups().items()}


def calendar(dates):
    return time_features(pd.DatetimeIndex(dates))[:, 2:].astype(np.float32)


def aggregate_daily(hourly, labels):
    """Mean each complete 12Z--12Z predictor day; CPC already is a daily total."""
    dates = pd.DatetimeIndex(pd.to_datetime(hourly.datetime, utc=True)).as_unit('ns')
    if not dates.is_unique or not dates.is_monotonic_increasing or not np.all(np.diff(dates.asi8) == 3600_000_000_000):
        raise ValueError('Expected complete contiguous hourly source timestamps')
    physical = [c for c in feature_groups()['E7'] if c not in TIME]
    values = hourly[physical].copy(); values.index = dates
    groups = values.resample('24h', offset='12h', closed='left', label='left')
    daily = groups.mean().where(groups.count() == 24)
    daily[list(TIME)] = calendar(daily.index + pd.Timedelta(days=1))
    target = labels.set_index('period_end').y_cpc_region_mm.copy()
    target.index = pd.DatetimeIndex(target.index).as_unit('ns') - pd.Timedelta(days=1)
    if not target.index.is_unique or not (target.index.hour == 12).all():
        raise ValueError('CPC labels must have unique 12 UTC period starts')
    daily['y_cpc_region_mm'] = target.reindex(daily.index)
    return daily


def samples_from_daily(daily):
    dates = pd.DatetimeIndex(daily.index).as_unit('ns')
    if not dates.is_unique or not np.all(np.diff(dates.asi8) == 86400_000_000_000):
        raise ValueError('Expected contiguous daily periods')
    names = feature_groups()['E7']
    x = daily[names].to_numpy(float); y = daily.y_cpc_region_mm.to_numpy(float)
    positions = np.arange(HISTORY_DAYS, len(daily) - 2)
    history = positions[:, None] + np.arange(-HISTORY_DAYS, 0)[None, :]
    target = positions[:, None] + np.arange(3)[None, :]
    last_end = dates[positions] + pd.Timedelta(days=3)
    good = np.isfinite(x[history]).all((1, 2)) & np.isfinite(y[target]).all(1) & (y[target] >= 0).all(1)
    good &= (dates[positions].year == last_end.year) & (dates[positions].year >= 2015) & (last_end.year <= 2023)
    positions, history, target = positions[good], history[good], target[good]
    future_dates = dates.asi8[target].ravel() + pd.Timedelta(days=1).value
    future = calendar(pd.to_datetime(future_dates, utc=True)).reshape(-1, 3, 2)
    return DailySamples(dates[positions], x[history].astype(np.float32), future,
                        y[target].astype(np.float32), names, positions)


def load_development():
    cutoff = pa.scalar(pd.Timestamp('2024-01-01', tz='UTC'), type=pa.timestamp('ns', tz='UTC'))
    columns = ['datetime', *[c for c in feature_groups()['E7'] if c not in TIME]]
    hourly = pq.read_table(SOURCE, columns=columns, filters=[('datetime', '<', cutoff)]).to_pandas()
    labels = pd.read_parquet(PRIVATE / 'cpc_daily_region.parquet', filters=[('marked_date', '<', pd.Timestamp('2024-01-01'))])
    daily = aggregate_daily(hourly, labels)
    return samples_from_daily(daily), daily


def tabular_inputs(samples):
    parts, names = [], []
    for i, name in enumerate(samples.features):
        x = samples.x[:, :, i]
        stats = [('last1d', x[:, -1])] if name in TIME else [
            ('last1d', x[:, -1]), ('mean3d', x[:, -3:].mean(1)),
            ('mean7d', x.mean(1)), ('change1d', x[:, -1] - x[:, -2])]
        for suffix, value in stats: parts.append(value); names.append(name + '@' + suffix)
    for day in range(3):
        for i, name in enumerate(TIME):
            parts.append(samples.future[:, day, i]); names.append(f'{name}@future{day+1}d')
    return np.stack(parts, axis=1).astype(np.float32), names

