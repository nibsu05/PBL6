"""Recompute published rain-improvement scores from the private prediction files."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_gfs_window import check_freeze
from src.gfs_daily_evaluation import block_draw_counts
from src.gfs_window import BASE, read_json, sha

GATED = 'gfs_gated_amount_2026_11_24'
NEIGHBOR = 'gfs_neighborhood_2026_11_24'
WEIGHTED = 'gfs_weighted_amount_2026_11_24'
PUBLIC = ROOT / 'reports'
PRIVATE = ROOT / 'data' / 'operational'
KEY_AND_REFERENCE = ['station_id', 'issue_utc', 'horizon', 'y_mm', 'B_mean']
HORIZONS = [1, 2, 3]


def check_tail_scores(frame):
    directory = PUBLIC / GATED
    scores_file = directory / 'tail_mae_paired.csv'
    recorded = read_json(directory / 'independent_verification.json')
    if sha(scores_file) != recorded['tail_intervals_sha256']:
        raise ValueError('Conditional MAE file checksum differs')
    scores = pd.read_csv(scores_file).set_index('horizon').loc[HORIZONS]
    for h, rows in frame.groupby('horizon'):
        tail = rows[rows.y_mm.ge(50)]
        days = pd.date_range(rows.issue_utc.min(), rows.issue_utc.max(), freq='D')
        errors = pd.DataFrame({
            'count': 1,
            'base': (tail.B_mean - tail.y_mm).abs(),
            'adjusted': (tail.adjusted_mm - tail.y_mm).abs(),
        })
        daily = errors.groupby(tail.issue_utc).sum().reindex(days, fill_value=0)
        totals = daily.sum()
        base, adjusted = totals[['base', 'adjusted']] / totals['count']
        counts = block_draw_counts(len(days), draws=5000, block=14, seed=1701)
        events = counts @ daily['count'].to_numpy()
        differences = counts @ (daily.adjusted - daily.base).to_numpy()
        available = events > 0
        low, high = np.quantile(differences[available] / events[available], [.025 / 3, 1 - .025 / 3])
        np.testing.assert_allclose(
            [len(tail), base, adjusted, adjusted - base, low, high],
            scores.loc[h, ['events', 'reference', 'model', 'difference',
                           'simultaneous_low', 'simultaneous_high']].to_numpy(dtype=float),
            atol=1e-9, rtol=0,
        )


def check_neighborhood_scores(frame):
    contrasts = pd.read_csv(PUBLIC / NEIGHBOR / 'paired_comparisons.csv')
    np.testing.assert_array_equal(
        frame.B_nbr_p50.between(0, 1) & frame.B_nbr_p1.between(0, 1) & frame.B_nbr_p50.le(frame.B_nbr_p1),
        np.ones(len(frame), dtype=bool),
    )
    for metric, forecasts, targets in [
        ('macro_rmse', ['B_mean', 'B_nbr_mean'], frame.y_mm),
        ('macro_bs50', ['B_p50', 'B_nbr_p50'], frame.y_mm.ge(50)),
    ]:
        losses = frame[forecasts].subtract(targets.astype(float), axis=0).pow(2)
        per_station = losses.groupby([frame.horizon, frame.station_id]).mean()
        if metric == 'macro_rmse':
            per_station = np.sqrt(per_station)
        per_horizon = per_station.groupby(level='horizon').mean().loc[HORIZONS]
        expected = contrasts[contrasts.metric.eq(metric)].set_index('horizon').loc[HORIZONS]
        np.testing.assert_allclose(per_horizon, expected[['reference', 'model']], atol=1e-9, rtol=0)


def main():
    check_freeze()
    for experiment, stem in [(GATED, 'gated_amount'), (NEIGHBOR, 'neighborhood'), (WEIGHTED, 'weighted_amount')]:
        protocol = read_json(PUBLIC / experiment / 'protocol.json')
        if sha(ROOT / 'scripts' / f'run_gfs_{stem}.py') != protocol['builder_sha256']:
            raise ValueError(f'Builder checksum differs for {experiment}')

    baseline = pd.read_parquet(
        BASE / 'predictions_private.parquet',
        columns=KEY_AND_REFERENCE,
        filters=[('evaluation_set', '==', 'retrospective2026_modern')],
    )
    check_rows = baseline.groupby('horizon').size().to_dict()
    if check_rows != dict.fromkeys(HORIZONS, 14488):
        raise ValueError('Unexpected evaluation support')
    gated = pd.read_parquet(PRIVATE / GATED / 'predictions_private.parquet')
    neighbor = pd.read_parquet(PRIVATE / NEIGHBOR / 'predictions_private.parquet')
    for frame in (gated, neighbor):
        pd.testing.assert_frame_equal(frame[KEY_AND_REFERENCE], baseline)
    no_change = gated.B_mean.le(float(read_json(PUBLIC / GATED / 'verification.json')['choice']))
    np.testing.assert_array_equal(gated.loc[no_change, 'adjusted_mm'], gated.loc[no_change, 'B_mean'])
    check_tail_scores(gated)
    check_neighborhood_scores(neighbor)
    print(f'Verified {len(baseline):,} matched rows, 3 conditional MAE intervals and 6 neighborhood scores.')


if __name__ == '__main__':
    main()
