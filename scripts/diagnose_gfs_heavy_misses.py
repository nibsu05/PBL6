"""Count low point-forecast amounts among missed heavy-rain events in 2026."""

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.gfs_window import BASE, PUBLIC, read_json, save_csv, sha

OUTPUT = ROOT / 'reports/gfs_gated_amount_2026_11_24/missed_signal.csv'


def main():
    predictions = BASE / 'predictions_private.parquet'
    if sha(predictions) != read_json(BASE / 'scoring_complete.json')['predictions_sha256']:
        raise ValueError('Forecast file checksum changed')
    frame = pd.read_parquet(
        predictions, columns=['horizon', 'y_mm', 'B_mean', 'B_p50', 'GFS_mean'],
        filters=[('evaluation_set', '==', 'retrospective2026_modern')],
    )
    cutoffs = pd.read_csv(PUBLIC / 'cutoffs.csv').query("model == 'B'").set_index('horizon').cutoff
    rows = []
    for horizon, all_cases in frame.groupby('horizon'):
        observed = all_cases[all_cases.y_mm.ge(50)]
        missed = observed[observed.B_p50.lt(cutoffs[horizon])]
        low_gfs = missed.GFS_mean.lt(10)
        low_model = missed.B_mean.lt(10)
        rows.append(dict(
            horizon=horizon, rows=len(all_cases), cutoff=float(cutoffs[horizon]),
            observed_ge50=len(observed), missed=len(missed), low_gfs=int(low_gfs.sum()),
            low_lightgbm=int(low_model.sum()), both_under10=int((low_gfs & low_model).sum()),
        ))
    save_csv(pd.DataFrame(rows), OUTPUT)
    print(f'Saved aggregate diagnosis for {len(frame):,} matched rows.')


if __name__ == '__main__':
    main()
