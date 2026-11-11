"""Measure spatial holdout errors and historical-network thinning sensitivity.

No 2025 or 2026 rain values; no forecast models or operational label are made.
Full-network estimates are an internal reference, NEVER independent truth.
"""
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import sys
import warnings
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial.distance import cdist

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.inspect_vrain_spatial_panel import spatial_weights
from src.vrain_label_feasibility import neighbor_weights, error_metrics, weighted_quantiles

BASE = ROOT / 'data/operational/vrain_2026_11_09'
OUT = ROOT / 'reports/vrain_data_handoff_2026_11_09'


def main():
    warnings.filterwarnings('ignore', category=DeprecationWarning,
                            module='scripts.inspect_vrain_spatial_panel')
    a = np.load(BASE / 'freeze_work/station_matrices.npz')
    stations = pd.read_csv(BASE / 'freeze_work/station_inventory_qc.csv')
    cells = pd.read_parquet(ROOT / 'data/processed/regional_danang/cell_weights.parquet')
    dates = pd.DatetimeIndex(a['marked_day'])
    if not set(dates.year).issubset({2021, 2022, 2023, 2024}):
        raise ValueError('Only development years may be inspected')
    observed = np.where(a['valid'], a['rain'], np.nan).sum(axis=1, dtype=np.float64)
    available = np.isfinite(observed)
    full_weights, spatial, _, _, crs = spatial_weights(cells, stations)
    tx = Transformer.from_crs('EPSG:4326', crs, always_xy=True)
    xy = np.column_stack(tx.transform(stations.longitude.to_numpy(), stations.latitude.to_numpy()))/1000
    distances = cdist(xy, xy)
    zone_index = cdist(stations[['longitude', 'latitude']], cells[['lon', 'lat']]).argmin(axis=1)
    zones = cells.zone.to_numpy()[zone_index]
    # Fixed 25-km projected blocks, geometry only; not chosen using rainfall.
    blocks = np.floor(xy/25).astype(int)
    same_block = (blocks[:, None, :] == blocks[None, :, :]).all(axis=2)
    masks, inverse = np.unique(available, axis=0, return_inverse=True)
    methods = [('nearest', 1), ('idw2_k8', 8)]
    cv_rows = []
    for holdout, excluded in [('leave_one_station', np.eye(len(stations), dtype=bool)),
                              ('leave_25km_block', same_block)]:
        predictions = {name: np.full_like(observed, np.nan) for name, _ in methods}
        for i, mask in enumerate(masks):
            day_ids = np.flatnonzero(inverse == i)
            allowed = mask[None, :] & ~excluded
            for name, k in methods:
                w = neighbor_weights(distances, allowed, k=k)
                values = np.nan_to_num(observed[day_ids], nan=0.) @ w.T
                values[:, w.sum(axis=1) == 0] = np.nan
                values[:, ~mask] = np.nan
                predictions[name][day_ids] = values
        for name, pred in predictions.items():
            for year in [2021, 2022, 2023, 2024]:
                for zone in ['all'] + sorted(set(zones)):
                    selection = (dates.year == year)[:, None] & np.ones_like(available)
                    if zone != 'all':
                        selection &= (zones == zone)[None, :]
                    for rain_subset, rain_mask in [('all', np.ones_like(available)), ('observed_ge_50', observed >= 50)]:
                        use = selection & rain_mask
                        cv_rows.append(dict(holdout=holdout, method=name, year=year,
                                            zone_proxy=zone, rain_subset=rain_subset,
                                            **error_metrics(observed[use], pred[use])))
    pd.DataFrame(cv_rows).to_csv(OUT / 'spatial_holdout_daily.csv', index=False)
    # Fine quadrature only for the IDW area integral, not new measurements.
    offsets = (np.arange(5)+.5)/5*.1-.05
    grid_lon, grid_lat, grid_weight = [], [], []
    for row in cells.itertuples():
        lon, lat = np.meshgrid(row.lon+offsets, row.lat+offsets)
        weight = np.cos(np.deg2rad(lat));weight = row.weight*weight/weight.sum()
        grid_lon.extend(lon.ravel());grid_lat.extend(lat.ravel());grid_weight.extend(weight.ravel())
    grid_xy = np.column_stack(tx.transform(np.asarray(grid_lon), np.asarray(grid_lat)))/1000
    grid_distances = cdist(grid_xy, xy)
    grid_weight = np.asarray(grid_weight)
    dense = available.all(axis=1)
    dense_dates = dates[dense]
    dense_values = observed[dense]
    thiessen_reference = dense_values @ full_weights
    full_idw = grid_weight @ neighbor_weights(grid_distances, np.ones(len(stations), bool), k=8)
    references = {'renormalized_full_weights': thiessen_reference,
                  'thiessen_available_network': thiessen_reference,
                  'idw2_k8_area': dense_values @ full_idw}
    cache = {}
    def estimator_weights(mask):
        key = np.packbits(mask).tobytes()
        if key not in cache:
            if mask.sum() < 3 or full_weights[mask].sum() == 0:
                return None
            normalized = full_weights*mask;normalized /= normalized.sum()
            wt, *_ = spatial_weights(cells, stations.loc[mask])
            expanded = np.zeros(len(stations));expanded[mask] = wt
            wi = grid_weight @ neighbor_weights(grid_distances, mask, k=8)
            cache[key] = dict(renormalized_full_weights=normalized,
                              thiessen_available_network=expanded, idw2_k8_area=wi)
        return cache[key]
    stress_rows = []
    scenarios = {str(year): available[dates.year == year] for year in [2021, 2022, 2023]}
    core = (stations.valid_fraction_2021 >= .98) & (stations.valid_fraction_2022 >= .98)
    scenarios['fixed_core45'] = core.to_numpy()[None, :]
    core_weights = estimator_weights(core.to_numpy())['thiessen_available_network']
    hourly_values = np.where(a['valid'], a['rain'], np.nan).reshape(-1, len(stations))
    hourly_dense = np.isfinite(hourly_values).all(axis=1)
    full_hour = hourly_values[hourly_dense] @ full_weights
    core_hour = hourly_values[hourly_dense] @ core_weights
    fixed_core_temporal = dict(
        hourly=error_metrics(full_hour, core_hour),
        hourly_same_days=error_metrics(
            (a['rain'][dense].astype(np.float64) @ full_weights).ravel(),
            (a['rain'][dense].astype(np.float64) @ core_weights).ravel()),
        daily=error_metrics(thiessen_reference, dense_values @ core_weights),
        note='hourly_same_days uses the same 67 complete days as daily; hourly uses all complete clock rows; internal network sensitivity, not forecast error')
    private_rows = []
    for scenario, history in scenarios.items():
        unique, counts = np.unique(history, axis=0, return_counts=True)
        buckets = defaultdict(list)
        for mask, count in zip(unique, counts):
            estimates = estimator_weights(mask)
            if estimates is None:
                continue
            for method, weights in estimates.items():
                estimate = dense_values @ weights
                for ref_name, reference in [('same_method_dense', references[method]),
                                             ('dense_thiessen', thiessen_reference)]:
                    metrics = error_metrics(reference, estimate)
                    flips = {f'event_flip_{threshold}':float(np.mean((reference >= threshold) != (estimate >= threshold)))
                             for threshold in [16, 50, 100]}
                    record = dict(scenario=scenario, method=method, reference=ref_name,
                                  historical_days=int(count), stations_available=int(mask.sum()), **metrics, **flips)
                    private_rows.append(record)
                    buckets[(method, ref_name)].append(record)
        for (method, reference), records in buckets.items():
            weights = [r['historical_days'] for r in records]
            summary = dict(scenario=scenario, method=method, reference=reference,
                           historical_days_represented=sum(weights), unique_masks=len(records),
                           reference_days=len(dense_values))
            for metric in ['mae', 'rmse', 'bias', 'nrmse', 'volume_bias', 'event_flip_16', 'event_flip_50', 'event_flip_100']:
                values = [r[metric] for r in records]
                for quantile, value in zip(['p10', 'p50', 'p90'], weighted_quantiles(values, weights)):
                    summary[metric+'_'+quantile] = value
            stress_rows.append(summary)
        print('Assessed historical scenario:', scenario, flush=True)
    pd.DataFrame(stress_rows).to_csv(OUT / 'network_thinning_daily.csv', index=False)
    # Spatial diagnostics only: these zones are not administrative boundaries.
    zone_rows = []
    for zone in sorted(cells.zone.unique()):
        zone_cells = cells.loc[cells.zone == zone].copy()
        zone_area_fraction = float(zone_cells.weight.sum())
        zone_cells['weight'] /= zone_area_fraction
        zone_full, zone_spatial, *_ = spatial_weights(zone_cells, stations)
        zone_reference = dense_values @ zone_full
        for scenario, history in scenarios.items():
            unique, counts = np.unique(history, axis=0, return_counts=True)
            records = []
            for mask, count in zip(unique, counts):
                if mask.sum() < 3:
                    continue
                w, *_ = spatial_weights(zone_cells, stations.loc[mask])
                estimate = dense_values[:, mask] @ w
                records.append(dict(count=int(count), **error_metrics(zone_reference, estimate)))
            row = dict(zone=zone, scenario=scenario, reference_days=len(dense_values),
                       reference_mean_daily=float(zone_reference.mean()),
                       area_km2=zone_spatial['region_km2'],
                       geometry_scope='R93 diagnostic zone, NOT an administrative area')
            for metric in ['mae', 'rmse', 'nrmse', 'volume_bias']:
                for name, value in zip(['p10', 'p50', 'p90'], weighted_quantiles(
                        [r[metric] for r in records], [r['count'] for r in records])):
                    row[metric+'_'+name] = value
            zone_rows.append(row)
    pd.DataFrame(zone_rows).to_csv(OUT / 'zone_thinning_daily.csv', index=False)
    private = BASE / 'label_feasibility';private.mkdir(exist_ok=True)
    pd.DataFrame(private_rows).to_parquet(private / 'mask_metrics_private.parquet', index=False)
    report = dict(status='development_label_feasibility_not_forecast_training',
                  observation_dates=[str(dates.min().date()), str(dates.max().date())],
                  region='R93 approximation; not the confirmed administrative polygon',
                  source_time='marked source day; timezone/interval alignment still unconfirmed',
                  reference_not_independent_truth=True, reference_days=int(dense.sum()),
                  reference_date_span=[str(dense_dates.min().date()), str(dense_dates.max().date())],
                  reference_days_by_month=pd.Series(dense_dates.month).value_counts().sort_index().to_dict(),
                  reference_events={str(t):int((thiessen_reference >= t).sum()) for t in [16, 50, 100]},
                  full_network_idw_vs_thiessen=error_metrics(thiessen_reference, references['idw2_k8_area']),
                  fixed_core45_vs_full_thiessen_by_duration=fixed_core_temporal,
                  nrmse_definition='RMSE / mean of dense-reference daily depth',
                  percentile_definition='10/50/90 percentiles over historical daily availability masks; NOT confidence intervals',
                  limits=[f'{int(dense.sum())} days complete at all 82 gauges are concentrated in Aug-Dec 2024',
                          'Dense gauge reference can share systematic measurement and spatial sampling error',
                          'Spatial station holdout measures point reconstruction, not true area-average error',
                          'Nearest R93 cell zone is a proxy, not verified gauge elevation',
                          'No elevation covariate or independent radar used',
                          'No final acceptance threshold was selected from these outcomes'],
                  test2025_read=False, recent2026_values_read=False, forecast_training_performed=False)
    inputs = [BASE / 'freeze_work/station_matrices.npz',
              BASE / 'freeze_work/station_inventory_qc.csv',
              ROOT / 'data/processed/regional_danang/cell_weights.parquet']
    report['input_sha256'] = {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    (OUT / 'label_feasibility_audit.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
