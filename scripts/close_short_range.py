"""Close the short-range study without refitting or modifying frozen outputs."""

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from scripts.run_gfs_window import check_freeze, predict_frame
from src.gfs_daily_evaluation import block_draw_counts
from src.gfs_window import BASE, PUBLIC, read_json, sha, write_json


NAME = 'gfs_short_range_closeout_2026_11_24'
REPORT = ROOT / 'reports' / NAME
PRIVATE = ROOT / 'data' / 'operational' / NAME
FINAL_REPORT = ROOT / 'reports' / 'gfs_station_final_2026_11_17'
FINAL_PRIVATE = ROOT / 'data' / 'operational' / FINAL_REPORT.name
WINDOW_SCOPE = 'retrospective2026_modern'
KEYS = ['issue_utc', 'station_id', 'horizon']
DISPLAY_FIELDS = ['B_mean', 'B_median', 'B_p1', 'B_p50', 'GFS_mean', 'MOS_LONG_mean']
REFERENCES = ('GFS', 'MOS_LONG')
TARGET_HORIZONS = (1, 2, 3)
BLOCKS = (7, 14, 28)
DRAWS = 5000
FAMILY_SIZE = len(REFERENCES) * len(TARGET_HORIZONS)


def verified_sources():
    """Validate the immutable inputs and published evidence used in the closeout."""
    freeze = check_freeze()
    replay_path = BASE / 'predictions_private.parquet'
    final_predictions = FINAL_PRIVATE / 'holdout_predictions_private.parquet'
    checks = {
        replay_path: read_json(BASE / 'scoring_complete.json')['predictions_sha256'],
        final_predictions: read_json(FINAL_PRIVATE / 'holdout_prediction_manifest.json')['sha256'],
        FINAL_REPORT / 'final_manifest.json': read_json(FINAL_REPORT / 'release.json')['final_manifest_sha256'],
    }
    for directory, field, names in (
        (PUBLIC, 'report_files', ['point_metrics.csv', 'event_metrics.csv', 'probability_metrics.csv',
                                  'selection.json', 'protocol.json', 'model_catalog.json']),
        (FINAL_REPORT, 'report_sha256', ['point_metrics.csv', 'paired_bootstrap.csv']),
    ):
        hashes = read_json(directory / 'release.json')[field]
        checks.update({directory / name: hashes[name] for name in names})
    for path, digest in checks.items():
        if sha(path) != digest:
            raise ValueError(f'Frozen evidence changed: {path.name}')
    selection = freeze['selection']
    if (selection['selected_loss'], selection['selected_window'], read_json(PUBLIC / 'model_catalog.json')['selected_prospective_case']) != ('tweedie', 'long', 'B'):
        raise ValueError('Frozen choice is not B')
    return checks, freeze


def paired_skill(frame, scores):
    """Post-hoc RMSE contrasts with paired calendar blocks.

    Reuse one resample of calendar dates for every station, model and horizon.
    Each simultaneous interval covers the six B versus baseline contrasts for
    one block length. The 7 and 28 day choices are sensitivity analyses.
    """
    dates = pd.date_range(frame.issue_utc.min(), frame.issue_utc.max(), freq='D')
    stations = sorted(frame.station_id.unique())
    counts_by_block = {
        block: block_draw_counts(len(dates), draws=DRAWS, block=block, seed=1701)
        for block in BLOCKS
    }
    rows = []
    for horizon in TARGET_HORIZONS:
        part = frame.loc[frame.horizon.eq(horizon), ['issue_utc', 'station_id', 'y_mm', 'B_mean', 'GFS_mean', 'MOS_LONG_mean']]
        pivots = {
            model: part.assign(square=(part[f'{model}_mean'] - part.y_mm)**2)
            .pivot(index='issue_utc', columns='station_id', values='square')
            .reindex(index=dates, columns=stations).to_numpy()
            for model in ('B', *REFERENCES)
        }
        support = np.isfinite(pivots['B'])
        for model, squared_error in pivots.items():
            np.testing.assert_array_equal(np.isfinite(squared_error), support)
            point = np.sqrt(np.nanmean(squared_error, axis=0)).mean()
            published = scores.loc[scores.model.eq(model) & scores.horizon.eq(horizon), 'macro_rmse'].item()
            np.testing.assert_allclose(point, published, rtol=2e-7, atol=1e-7)

        points = {model: np.sqrt(np.nanmean(matrix, axis=0)) for model, matrix in pivots.items()}
        for block, counts in counts_by_block.items():
            denominators = counts @ support.astype(float)
            all_supported = (denominators > 0).all(1)
            if not all_supported.all():
                raise ValueError('A bootstrap draw lost a station; constant cohort cannot be compared')
            distributions = {
                model: np.sqrt((counts @ np.nan_to_num(matrix)) / denominators).mean(1)
                for model, matrix in pivots.items()
            }
            for ref in REFERENCES:
                distribution = distributions['B'] - distributions[ref]
                low, high = np.quantile(distribution, [.025 / FAMILY_SIZE, 1 - .025 / FAMILY_SIZE])
                model_score = points['B'].mean()
                ref_score = points[ref].mean()
                rows.append(dict(
                    evaluation_set=WINDOW_SCOPE, horizon=horizon, model='B', reference=ref,
                    matched_rows=len(part), stations=len(stations), issue_days=part.issue_utc.nunique(),
                    block_days=block, draws=DRAWS, family_size=FAMILY_SIZE,
                    metric='macro_rmse_mm_24h', model_score=model_score, reference_score=ref_score,
                    difference=model_score-ref_score, relative_reduction_pct=100*(ref_score-model_score)/ref_score,
                    simultaneous_ci_low=low, simultaneous_ci_high=high,
                    stations_improved=int((points['B'] < points[ref]).sum()),
                    exploratory_interval_excludes_zero=bool(high < 0),
                ))
    return pd.DataFrame(rows).sort_values(['block_days', 'reference', 'horizon'])


def holdout_evidence():
    comparisons = pd.read_csv(FINAL_REPORT / 'paired_bootstrap.csv')
    accepted = comparisons.loc[comparisons.evaluation_set.eq('test2025_legacy') &
                               comparisons.primary_improvement_supported].copy()
    expected = {('LGB_N1', 'LGB_N0', 2), ('LGB_N1', 'LGB_N0', 3), ('LGB_N3', 'MOS', 3),
                ('GRU_N5', 'MOS', 1), ('GRU_N5', 'MOS', 3)}
    if set(zip(accepted.model, accepted.reference, accepted.horizon)) != expected:
        raise ValueError('Locked holdout conclusions changed')
    metrics = pd.read_csv(FINAL_REPORT / 'point_metrics.csv')
    metrics = metrics[metrics.evaluation_set.eq('test2025_legacy')]
    for row in accepted.itertuples():
        functional, metric = row.metric.split('_')
        subset = metrics[metrics.horizon.eq(row.horizon) & metrics.functional.eq(functional)]
        model_score = subset.loc[subset.model.eq(row.model), 'macro_'+metric].item()
        ref_score = subset.loc[subset.model.eq(row.reference), 'macro_'+metric].item()
        np.testing.assert_allclose(model_score-ref_score, row.difference, atol=1e-7)
        accepted.loc[row.Index, ['model_score', 'reference_score']] = (model_score, ref_score)
    return accepted.sort_values(['family', 'model', 'horizon'])


def to_snapshot(frame, outputs, freeze_sha):
    """Public UI schema; instance values stay in private local workspace."""
    cutoffs = pd.read_csv(PUBLIC / 'cutoffs.csv')
    cutoff = cutoffs[cutoffs.model.eq('B')].set_index('horizon').cutoff.to_dict()
    roster = frame[['station_id', 'latitude', 'longitude']].drop_duplicates().sort_values('station_id')
    if len(roster) != 57 or not roster.station_id.is_unique:
        raise ValueError('Station roster did not match the frozen cohort')

    # Latest date and the date with most observed D1 heavy rain, chosen by the
    # observations only for illustration. Both display replay provenance.
    by_issue = list(outputs.groupby('issue_utc', sort=True))
    latest_issue, latest = by_issue[-1]
    rainy_issue, rainy = max(by_issue, key=lambda group: (
        group[1].loc[group[1].horizon.eq(1), 'y_mm'].ge(50).sum(), group[0]))
    cases = [('latest', 'Lần dự báo gần nhất trong bộ đánh giá', latest_issue, latest)]
    if rainy_issue != latest_issue:
        cases.append(('heavy_observed', 'Ngày có nhiều trạm ghi nhận mưa lớn', rainy_issue, rainy))
    snapshots = []
    for case_id, label, issue, rows in cases:
        if not rows.groupby('station_id').horizon.apply(lambda series: tuple(sorted(series)) == TARGET_HORIZONS).all():
            raise ValueError('Incomplete or duplicated three-window prediction')
        windows = []
        for horizon in TARGET_HORIZONS:
            part = rows[rows.horizon.eq(horizon)].sort_values('station_id')
            start, end = part.target_start_utc.unique().item(), part.target_end_utc.unique().item()
            if pd.Timestamp(start) != issue + pd.Timedelta(hours=24*(horizon-1)) or pd.Timestamp(end) != issue + pd.Timedelta(hours=24*horizon):
                raise ValueError('Forecast windows do not match the model contract')
            points = [
                dict(station_id=row.station_id, predicted_mm=float(row.B_mean), median_mm=float(row.B_median),
                     gfs_mm=float(row.GFS_mean), mos_mm=float(row.MOS_LONG_mean), observed_mm=float(row.y_mm),
                     probability_ge1=float(row.B_p1), probability_ge50=float(row.B_p50))
                for row in part.itertuples()
            ]
            windows.append(dict(horizon=horizon, start_utc=pd.Timestamp(start).isoformat(),
                                end_utc=pd.Timestamp(end).isoformat(), cutoff_ge50_probability=float(cutoff[horizon]),
                                points=points))
        snapshots.append(dict(id=case_id, label=label, issue_utc=issue.isoformat(),
                              gfs_init_utc=pd.Timestamp(rows.gfs_init_utc.unique().item()).isoformat(),
                              available_stations=rows.station_id.nunique(), windows=windows))
    return dict(
        schema_version=1, product='short_range', mode='historical_replay', model='LightGBM B',
        window_hours=24, rain_unit='mm', gauge_source='Vrain modern', model_freeze_sha256=freeze_sha,
        stations=roster.to_dict(orient='records'), snapshots=snapshots,
    )


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    checks, freeze = verified_sources()
    print(f'Frozen inputs and {len(freeze["artifacts"])} model artifacts verified.', flush=True)
    source = pd.read_parquet(BASE / 'predictions_private.parquet', filters=[('evaluation_set', '==', WINDOW_SCOPE)])
    metadata = ['latitude', 'longitude', 'gfs_init_utc', 'target_start_utc', 'target_end_utc', 'y_mm']
    # Remove labels and old predictions before replay. Keep date/feature inputs.
    new, _ = predict_frame(source.drop(columns=['y_mm', *[c for c in source if c.endswith(('_mean', '_median', '_p1', '_p50'))]]))
    np.testing.assert_allclose(new[DISPLAY_FIELDS], source[DISPLAY_FIELDS], atol=1e-7, rtol=2e-7)
    if source.duplicated(KEYS).any() or not np.isfinite(source[DISPLAY_FIELDS + ['y_mm']].to_numpy()).all():
        raise ValueError('The evaluation rows must be paired, unique and finite')
    if not ((new.B_p50 <= new.B_p1) & (new.B_p50 >= 0) & (new.B_p1 <= 1) &
            (new.B_mean >= 0) & (new.B_median >= 0)).all():
        raise ValueError('Invalid amount or event probability')
    print(f'Replayed {len(new):,} rows with no Vrain labels passed to inference.', flush=True)
    replay = source[KEYS + metadata].join(new[DISPLAY_FIELDS])
    metrics = pd.read_csv(PUBLIC / 'point_metrics.csv')
    metrics = metrics[metrics.evaluation_set.eq(WINDOW_SCOPE) & metrics.functional.eq('mean')]
    skill = paired_skill(replay, metrics)
    holdout = holdout_evidence()
    freeze_sha = sha(BASE / 'model_freeze.json')
    payload = to_snapshot(source, replay, freeze_sha)
    map_path = PRIVATE / 'station_map_private.json'
    write_json(map_path, payload)
    skill.to_csv(REPORT / 'doi_chieu_hoi_cuu_2026.csv', index=False, float_format='%.8f', lineterminator='\n')
    holdout.to_csv(REPORT / 'doi_chieu_kiem_dinh_2025.csv', index=False, float_format='%.8f', lineterminator='\n')
    preserved = read_json(BASE / 'protected_before.json')
    for relative, digest in preserved.items():
        if sha(ROOT / relative) != digest:
            raise ValueError(f'Protected file changed: {relative}')
    write_json(REPORT / 'verification.json', dict(
        status='passed', checked_at_utc=datetime.now(timezone.utc).isoformat(), model='B', fit_years=[2021,2024],
        calibration_year=2025, evaluation_scope=WINDOW_SCOPE, replay_rows=len(replay),
        replayed_values=len(replay)*len(DISPLAY_FIELDS), replay_input_includes_target=False,
        largest_absolute_replay_difference=float((new[DISPLAY_FIELDS]-source[DISPLAY_FIELDS]).abs().max().max()),
        distinct_issue_dates=replay.issue_utc.nunique(), stations=replay.station_id.nunique(),
        model_freeze_sha256=freeze_sha, frozen_model_artifacts=len(freeze['artifacts']),
        preserved_files=len(preserved), compared_blocks=list(BLOCKS), draws_per_block=DRAWS,
        exploratory_contrasts_per_block=FAMILY_SIZE,
        comparison_2025_sha256=sha(REPORT / 'doi_chieu_kiem_dinh_2025.csv'),
        comparison_2026_sha256=sha(REPORT / 'doi_chieu_hoi_cuu_2026.csv'),
        source_sha256={p.relative_to(ROOT).as_posix():digest for p,digest in checks.items()},
        model_refit=False, private_snapshot_sha256=sha(map_path),
        private_snapshot_counts=[case['available_stations'] for case in payload['snapshots']],
    ))
    print(skill[skill.block_days.eq(14)][['reference','horizon','difference','simultaneous_ci_low','simultaneous_ci_high','stations_improved']].to_string(index=False))


if __name__ == '__main__':
    main()
