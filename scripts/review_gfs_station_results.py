"""Read-only, post-hoc dev diagnostics; no fitting, threshold tuning or 2025 data.

Adds a constant-zero diagnostic and errors conditional on observed rain amount.
Conditional scores are descriptive, not a deployable choice of model per sample.
Only aggregates are published. The original frozen experiment remains unchanged.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/gfs_station_review_2026_11_10'
SOURCE = ROOT / 'data/operational/gfs_station_57_2026_11_10/predictions_private.parquet'
METRICS = ROOT / 'reports/gfs_station_57_2026_11_10/point_metrics.csv'
MODELS = ('ZERO', 'CLIM', 'GFS', 'A2', 'A3', 'GRU_A2')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    before = sha(SOURCE)
    columns = ['station_id', 'issue_utc', 'target_end_utc', 'horizon', 'split', 'y_mm']
    f = pd.read_parquet(SOURCE, columns=columns + [m for m in MODELS if m != 'ZERO'])
    assert pd.to_datetime(f.target_end_utc).dt.year.max() <= 2024
    dev = f[f.split.eq('dev')].copy()
    published = pd.read_csv(METRICS)
    published = published[published.fold.eq('dev')]
    results = {}
    rows = []
    for h in (1, 2, 3):
        g = dev[dev.horizon.eq(h)].copy()
        assert len(g) == 2782 and g.station_id.nunique() == 57
        result = dict(n=len(g), stations=57, dry_under1_fraction=float((g.y_mm < 1).mean()),
                      events_ge50=int((g.y_mm >= 50).sum()),
                      issues_with_ge50=int(g.loc[g.y_mm >= 50, 'issue_utc'].nunique()), models={})
        for model in MODELS:
            prediction = np.zeros(len(g)) if model == 'ZERO' else g[model].to_numpy()
            g['error'] = prediction - g.y_mm
            g['absolute_error'] = g.error.abs()
            g['squared_error'] = g.error ** 2
            stations = g.groupby('station_id').agg(
                mae=('absolute_error', 'mean'), mse=('squared_error', 'mean'), bias=('error', 'mean'))
            metrics = dict(macro_mae=float(stations.mae.mean()),
                           macro_rmse=float(np.sqrt(stations.mse).mean()),
                           macro_bias=float(stations.bias.mean()))
            if model != 'ZERO':
                reference = published[published.model.eq(model) & published.horizon.eq(h)].iloc[0]
                assert all(np.isclose(metrics[k], reference[k], rtol=1e-10, atol=1e-10) for k in metrics)
            else:
                assert np.isclose(metrics['macro_mae'], g.groupby('station_id').y_mm.mean().mean())
            for label, mask in [('under1', g.y_mm < 1), ('ge1', g.y_mm >= 1), ('ge50', g.y_mm >= 50)]:
                subset = g.loc[mask]
                metrics[label + '_micro_mae'] = float(subset.absolute_error.mean())
                metrics[label + '_micro_bias'] = float(subset.error.mean())
            if model in ('A2', 'GRU_A2'):
                errors = g.assign(raw_error=(g.GFS - g.y_mm).abs()).groupby('station_id')[['absolute_error', 'raw_error']].mean()
                metrics['stations_mae_better_gfs'] = int((errors.absolute_error < errors.raw_error).sum())
            result['models'][model] = metrics
            rows.append(dict(horizon=h, model=model, **metrics))
        results[str(h)] = result
    assert sha(SOURCE) == before
    diagnostic = dict(date='2026-11-10', experiment='gfs_station_57_2026_11_10',
                      scope='post-hoc development diagnostics, not preregistered confirmatory results',
                      zero_baseline='constant 0mm; never trained; not an event-warning solution',
                      conditional_metric='micro over rows selected by observed rain; descriptive only',
                      training_performed=False, predictions_changed=False, test2025_read=False,
                      private_predictions_sha256=before, source_metrics_sha256=sha(METRICS),
                      script_sha256=sha(Path(__file__)), results=results)
    (OUT / 'diagnostics.json').write_text(json.dumps(diagnostic, indent=2) + '\n', encoding='utf-8')
    pd.DataFrame(rows).to_csv(OUT / 'diagnostic_metrics.csv', index=False)
    print(json.dumps(dict(horizons=3, rows=len(rows), source_metrics_reproduced=True,
                          zero_macro_mae=[results[str(h)]['models']['ZERO']['macro_mae'] for h in (1, 2, 3)],
                          training_performed=False, test2025_read=False)), flush=True)


if __name__ == '__main__':
    main()
