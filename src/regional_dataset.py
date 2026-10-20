"""Tổng hợp vùng từ cube ô; không fit chuẩn hóa hoặc nhìn nhãn tương lai."""
from __future__ import annotations

import numpy as np
import pandas as pd

TIME_NAMES = ('sin_hour', 'cos_hour', 'sin_doy', 'cos_doy')
COMMON_MET = ('t2m_c', 'rh2m_pct', 'sp_hpa', 'u10', 'v10', 'sst_region_c',
              'cape', 'tcwv', 'swvl1', 'u850', 'v850', 'q850_gkg')
SPATIAL_NAMES = ('t2m_c', 'rh2m_pct', 'sp_hpa', 'tcwv', 'cape', 'cin_capped',
                 'has_lfc', 'u10', 'v10', 'u850', 'v850', 'q850_gkg',
                 'ivt_mag', 'vimd_mmh', 'w850_pas', 'shear_850_500',
                 'gsmap_mm', 'era5_tp_mm')
ZONE_NAMES = ('t2m_c', 'rh2m_pct', 'tcwv', 'cape', 'u850', 'v850',
              'q850_gkg', 'ivt_mag')
RAIN_INPUTS = {'gsmap_mm', 'gsmap_nb5_mean_mm', 'gsmap_nb5_max_mm', 'era5_tp_mm'}
LABEL = 'y_region_gc_mm'


def cell_areas_km2(latitude, resolution=.1):
    """Diện tích toàn ô trên cầu; chưa cắt theo polygon hành chính."""
    lat = np.asarray(latitude, dtype=float)
    return (6371.0088 ** 2 * np.deg2rad(resolution) *
            (np.sin(np.deg2rad(lat + resolution / 2)) -
             np.sin(np.deg2rad(lat - resolution / 2))))


def normalized_weights(weights, n_cells):
    weights = np.asarray(weights, dtype=float)
    if weights.shape != (n_cells,) or not np.isfinite(weights).all() or np.any(weights <= 0):
        raise ValueError('Trọng số phải hữu hạn, dương và khớp số ô')
    return weights / weights.sum()


def weighted_summary(values, weights):
    """[giờ, ô] → mean/std/p90/max. Thiếu một ô: để NaN, không đổi vùng."""
    x = np.asarray(values, dtype=float)
    if x.ndim != 2:
        raise ValueError('values phải là [giờ, ô]')
    w = normalized_weights(weights, x.shape[1])
    valid = np.isfinite(x)
    complete = valid.all(axis=1)
    safe = np.where(valid, x, 0.)
    mean = safe @ w
    std = np.sqrt(np.maximum(((safe - mean[:, None]) ** 2) @ w, 0.))
    order = np.argsort(np.where(valid, x, np.inf), axis=1)
    sorted_x = np.take_along_axis(x, order, axis=1)
    sorted_w = np.broadcast_to(w, x.shape)[np.arange(len(x))[:, None], order]
    cdf = np.cumsum(sorted_w, axis=1)
    cdf[:, -1] = 1.
    p90 = sorted_x[np.arange(len(x)), (cdf >= .9).argmax(axis=1)]
    maximum = np.max(safe, axis=1)
    out = {'mean': mean, 'std': std, 'p90': p90, 'max': maximum}
    for a in out.values():
        a[~complete] = np.nan
    out['coverage'] = valid @ w
    return out


def weighted_mean(values, weights):
    x = np.asarray(values, dtype=float)
    w = normalized_weights(weights, x.shape[1])
    valid = np.isfinite(x)
    mean = np.where(valid, x, 0.) @ w
    mean[~valid.all(1)] = np.nan
    return mean, valid @ w


def zone_masks(cells):
    """Phân vùng địa hình định trước; không dùng lượng mưa để chọn ngưỡng."""
    coastal = cells.coast_dist_km.to_numpy(float) <= 30.
    highland = (~coastal) & (cells.elev_mean_m.to_numpy(float) >= 600.)
    interior = ~(coastal | highland)
    return {'coastal': coastal, 'interior': interior, 'highland': highland}


def feature_catalog(feature_names):
    """Danh mục predictor, tách metadata và nhãn; có truy vết biến nguồn."""
    catalog = {}
    for name in feature_names:
        if name in ('y_gsmap_gc_mm', 'label_permanent'):
            continue
        col = name if name in TIME_NAMES else f'mean__{name}'
        catalog[col] = {'source': name, 'statistic': 'calendar' if name in TIME_NAMES else 'area_mean',
                        'version': 'V1'}
    for name in SPATIAL_NAMES:
        for stat in ('std', 'p90', 'max'):
            catalog[f'{stat}__{name}'] = {'source': name, 'statistic': stat, 'version': 'V2'}
    for zone in ('coastal', 'interior', 'highland'):
        for name in ZONE_NAMES:
            catalog[f'{zone}__{name}'] = {'source': name, 'statistic': 'zone_mean', 'version': 'V2'}
    for name in ZONE_NAMES:
        catalog[f'coastal_minus_highland__{name}'] = {
            'source': name, 'statistic': 'zone_contrast', 'version': 'V2'}
    for name in ('ne_moisture_mean', 'ne_terrain_flux_mean', 'above850_area_fraction'):
        catalog[name] = {'source': 'wind_humidity_terrain_proxy', 'statistic': 'physical_proxy', 'version': 'V2'}
    return catalog


def aggregate_block(cube, names, cells, weights):
    """Cube [ô, giờ, biến] → dict V1/V2; nguyên liệu của proxy luôn là cùng giờ."""
    cube = np.asarray(cube)
    pos = {n: i for i, n in enumerate(names)}
    w = normalized_weights(weights, len(cells))
    if cube.shape[0] != len(cells) or cube.shape[2] != len(names):
        raise ValueError('Cube/cells/names không khớp')
    get = lambda n: np.asarray(cube[:, :, pos[n]], dtype=float).T
    gc_mean, gc_coverage = weighted_mean(get('y_gsmap_gc_mm'), w)
    permanent = get('label_permanent')
    v1 = {LABEL: gc_mean, 'label_valid_weight_fraction': gc_coverage,
          'label_permanent': np.isfinite(permanent).all(1) & (permanent == 1).all(1)}
    summaries = {}
    for name in names:
        if name in ('y_gsmap_gc_mm', 'label_permanent'):
            continue
        if name in SPATIAL_NAMES:
            s = weighted_summary(get(name), w)
            summaries[name] = s
            mean = s['mean']
        else:
            mean = weighted_mean(get(name), w)[0]
        v1[name if name in TIME_NAMES else f'mean__{name}'] = mean
    v2 = dict(v1)
    for name in SPATIAL_NAMES:
        for stat in ('std', 'p90', 'max'):
            v2[f'{stat}__{name}'] = summaries[name][stat]
    for zone, mask in zone_masks(cells).items():
        if not mask.any():
            raise ValueError('Không có ô trong tiểu vùng ' + zone)
        for name in ZONE_NAMES:
            v2[f'{zone}__{name}'] = weighted_mean(get(name)[:, mask], w[mask])[0]
    for name in ZONE_NAMES:
        v2[f'coastal_minus_highland__{name}'] = v2[f'coastal__{name}'] - v2[f'highland__{name}']
    u, v, q, sp = map(get, ('u850', 'v850', 'q850_gkg', 'sp_hpa'))
    above = sp >= 850.
    valid = np.isfinite(u) & np.isfinite(v) & np.isfinite(q) & np.isfinite(sp)
    moisture = np.where(valid, np.maximum(q, 0.) / 1000. * np.maximum(-(u + v) / np.sqrt(2), 0.) * above, np.nan)
    distance = 111320. * .1 * np.sqrt(1 + np.cos(np.deg2rad(cells.lat.to_numpy(float))) ** 2)
    slope = np.maximum(cells.ne_upslope_m.to_numpy(float), 0.) / distance
    v2['ne_moisture_mean'] = weighted_mean(moisture, w)[0]
    v2['ne_terrain_flux_mean'] = weighted_mean(moisture * slope[None, :], w)[0]
    v2['above850_area_fraction'] = weighted_mean(np.where(valid, above.astype(float), np.nan), w)[0]
    return v1, v2


def legacy_predictors(frame):
    """Đưa bộ cũ về UTC/đơn vị chung; không bfill, không dùng ONI hoặc nhãn cũ."""
    f = frame.copy()
    dates = pd.to_datetime(f['datetime'], utc=True)
    if dates.duplicated().any():
        raise ValueError('Thời gian legacy bị trùng')
    out = pd.DataFrame(index=pd.DatetimeIndex(dates))
    mapping = {'temperature_2m': 't2m_c', 'relative_humidity_2m': 'rh2m_pct',
               'surface_pressure': 'sp_hpa', 'sea_surface_temperature': 'sst_region_c',
               'cape': 'cape', 'tcwv': 'tcwv', 'swvl1': 'swvl1',
               'u_850': 'u850', 'v_850': 'v850', 'specific_humidity_850': 'q850_gkg'}
    for old, new in mapping.items():
        x = f[old].to_numpy(float)
        out[f'mean__{new}'] = x * 1000 if new == 'q850_gkg' else x
    speed = f.wind_speed_10m.to_numpy(float) / 3.6  # source config: km/h
    angle = np.deg2rad(f.wind_direction_10m.to_numpy(float))
    out['mean__u10'] = -speed * np.sin(angle)
    out['mean__v10'] = -speed * np.cos(angle)
    # Lịch dùng chung cùng định nghĩa với bộ mới, không có fitted statistic.
    from src.dataset_v2 import time_features
    time = time_features(out.index.tz_localize(None))
    for k, name in enumerate(TIME_NAMES):
        out[name] = time[:, k]
    return out.sort_index()


def supervised_windows(frame, columns, window=24, horizon=6, stride=6):
    """Chỉ predictor [t-W,t); nhãn [t,t+H), không vượt ranh năm."""
    if window < 7 or horizon != 6:
        raise ValueError('Pilot cần window>=7, horizon=6')
    dates = pd.DatetimeIndex(frame.index).as_unit('ns')
    if not dates.is_unique or not dates.is_monotonic_increasing or not np.all(np.diff(dates.asi8) == 3600_000_000_000):
        raise ValueError('Frame phải có trục giờ UTC liên tục, duy nhất')
    issues = np.arange(window, len(frame) - horizon + 1, stride)
    values = frame[list(columns)].to_numpy(float)
    valid = np.isfinite(values)
    sums = np.vstack([np.zeros((1, len(columns))), np.cumsum(np.where(valid, values, 0.), axis=0)])
    counts = np.vstack([np.zeros((1, len(columns)), dtype=int), np.cumsum(valid, axis=0)])
    blocks, feature_names = [], []
    for k, name in enumerate(columns):
        if name in TIME_NAMES:
            blocks.append(values[issues - 1, k:k + 1]); feature_names.append(name + '@past1')
            continue
        for stat, array in [('last', values[issues - 1, k]),
                            ('mean6', (sums[issues, k] - sums[issues - 6, k]) / 6.),
                            ('mean24', (sums[issues, k] - sums[issues - window, k]) / window),
                            ('change6', values[issues - 1, k] - values[issues - 7, k])]:
            blocks.append(array[:, None]); feature_names.append(name + '@' + stat)
    x = np.concatenate(blocks, axis=1).astype(np.float32)
    y = frame[LABEL].to_numpy(float)
    y_ok = np.isfinite(y) & frame.label_permanent.to_numpy(bool)
    ys = np.r_[0., np.cumsum(np.where(y_ok, y, 0.))]
    yc = np.r_[0, np.cumsum(y_ok)]
    targets = np.stack([ys[issues + h] - ys[issues] for h in (3, 6)], axis=1)
    good = ((counts[issues] - counts[issues - window]) == window).all(1)
    good &= (yc[issues + horizon] - yc[issues]) == horizon
    good &= dates[issues].year == dates[issues + horizon - 1].year
    good &= np.isfinite(x).all(1)
    return {'issue': issues, 'dates': dates[issues], 'x': x, 'y': targets,
            'valid': good, 'features': feature_names}
