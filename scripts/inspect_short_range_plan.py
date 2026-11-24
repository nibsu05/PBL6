"""Kiểm kê V1 cho kế hoạch 24–72 h; chỉ đọc development 2015–2023, không fit mô hình."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/short_range_plan_2026_10_21/preflight_development.json')
    args = parser.parse_args()
    source = ROOT / 'data/processed/regional_danang/v1_hourly.parquet'
    groups_path = ROOT / 'reports/regional_research_plan_2026_10_20/feature_groups.json'
    groups = json.loads(groups_path.read_text(encoding='utf-8'))
    calendar = {'sin_hour', 'cos_hour', 'sin_doy', 'cos_doy'}
    features = [name if name in calendar else 'mean__' + name
                for group in ['B', 'A', 'M', 'C'] for name in groups[group]]
    assert len(features) == len(set(features)) == 44
    cutoff = pa.scalar(pd.Timestamp('2024-01-01', tz='UTC'), type=pa.timestamp('ns', tz='UTC'))
    columns = ['datetime', 'y_region_gc_mm', 'label_permanent', 'label_valid_weight_fraction', *features]
    table = pq.read_table(source, columns=columns, filters=[('datetime', '<', cutoff)])
    frame = table.to_pandas()
    dates = pd.DatetimeIndex(frame.datetime)
    assert dates.year.max() == 2023 and dates.year.min() == 2015
    assert dates.is_monotonic_increasing and dates.is_unique
    assert np.all(np.diff(dates.asi8) == pd.Timedelta(hours=1).value)
    x = frame[features].to_numpy(dtype=np.float64)
    rain = frame.y_region_gc_mm.to_numpy(dtype=np.float64)
    coverage = frame.label_valid_weight_fraction.to_numpy(dtype=np.float64)
    label_ok = (np.isfinite(rain) & (rain >= 0) & frame.label_permanent.to_numpy(bool)
                & np.isfinite(coverage) & np.isclose(coverage, 1., atol=1e-7, rtol=0))
    missing_x = (~np.isfinite(x)).any(axis=1)
    bad_x = np.r_[0, np.cumsum(missing_x)]
    bad_y = np.r_[0, np.cumsum(~label_ok)]
    rain_sum = np.r_[0., np.cumsum(np.where(label_ok, rain, 0.))]
    issues = np.arange(168, len(frame) - 72 + 1, 24)
    assert (dates[issues].hour == 0).all()
    history_ok = (bad_x[issues] - bad_x[issues - 168]) == 0
    future_ok = (bad_y[issues + 72] - bad_y[issues]) == 0
    year_ok = dates[issues].year == dates[issues + 71].year
    valid = history_ok & future_ok & year_ok
    totals = np.stack([rain_sum[issues + end] - rain_sum[issues + start]
                       for start, end in [(0, 24), (24, 48), (48, 72)]], axis=1)
    for issue in issues[valid][:3]:
        for start, end in [(0, 24), (24, 48), (48, 72)]:
            assert np.isclose(rain_sum[issue + end] - rain_sum[issue + start],
                              rain[issue + start:issue + end].sum())
    per_year = []
    for year in range(2015, 2024):
        candidate = dates[issues].year == year
        keep = candidate & valid
        per_year.append({
            'year': year, 'candidate_issues': int(candidate.sum()),
            'valid_common_issues': int(keep.sum()),
            'invalid_history': int((candidate & ~history_ok).sum()),
            'invalid_label': int((candidate & ~future_ok).sum()),
            'cross_year_label': int((candidate & ~year_ok).sum()),
            'events': {str(threshold): [int((totals[keep, h] >= threshold).sum()) for h in range(3)]
                       for threshold in [16, 50, 100]},
        })
    folds = []
    issue_years = dates[issues].year.to_numpy()
    for year in [2021, 2022, 2023]:
        folds.append({'evaluation_year': year,
                      'train_issues': int((valid & (issue_years < year - 1)).sum()),
                      'calibration_issues': int((valid & (issue_years == year - 1)).sum()),
                      'evaluation_issues': int((valid & (issue_years == year)).sum())})
    result = {
        'status': 'planning_inventory_only_no_models_fitted',
        'inspected_date_local': '2026-10-21',
        'dataset_id': 'regional-v1-v2-2026-10-20',
        'source_path': source.relative_to(ROOT).as_posix(),
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'hash_scope': 'whole file mechanical integrity only; row-level inspection restricted to 2015–2023',
        'feature_groups_path': groups_path.relative_to(ROOT).as_posix(),
        'development_rows_read': len(frame), 'predictors_in_common_mask': len(features),
        'history_hours': 168, 'future_hours': 72, 'issue_hour_utc': 0, 'stride_hours': 24,
        'candidate_issues': len(issues), 'valid_common_issues': int(valid.sum()),
        'planned_input_shape_per_sample': [28, 44], 'planned_decoder_calendar_shape_per_sample': [12, 4],
        'planned_target_shape_per_sample': [3], 'planned_hourly_inputs_mean_aggregated_to_hours': 6,
        'per_year': per_year, 'development_folds': folds,
        'test_2025_rows_read_for_diagnostics': False, 'models_fitted': False,
        'source_package_verification': 'See package_data.py verify result recorded separately in plan',
        'spatial_support': '93 selected full cells, approximate footprint; polygon intersection not yet resolved',
        'caveats': ['Validity reasons can overlap and must not be added as mutually exclusive counts.',
                    'All E0–E7 share the E7 history-validity and all-72h label-validity mask.',
                    'Overlapping issue targets and the three horizons are not independent samples.',
                    'Forecast field missingness and spatial support require a separate audit if dataset changes.'],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    print(json.dumps({'output': str(args.output), 'rows_read': len(frame),
                      'valid_common_issues': int(valid.sum()), 'folds': folds,
                      'models_fitted': False, 'test_2025_read': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
