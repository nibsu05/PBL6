"""Publish a private week of retrospective forecast snapshots from frozen results."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.close_short_range import DISPLAY_FIELDS, KEYS, PRIVATE, WINDOW_SCOPE, replay_snapshot
from scripts.run_gfs_window import check_freeze
from src.gfs_window import BASE, PUBLIC, read_json, sha, write_json


def main():
    check_freeze()
    artifact = BASE / 'predictions_private.parquet'
    if sha(artifact) != read_json(BASE / 'scoring_complete.json')['predictions_sha256']:
        raise ValueError('Forecast data differs from frozen results')
    replay_file = PRIVATE / 'station_map_private.json'
    replay = read_json(replay_file)
    latest = replay['snapshots'][0]
    anchor = pd.Timestamp(latest['issue_utc'])
    columns = KEYS + ['target_start_utc', 'target_end_utc', 'gfs_init_utc', 'y_mm'] + DISPLAY_FIELDS
    frame = pd.read_parquet(
        artifact, columns=columns,
        filters=[('evaluation_set', '==', WINDOW_SCOPE), ('issue_utc', '>=', anchor - pd.Timedelta(days=7)),
                 ('issue_utc', '<=', anchor)],
    )
    station_ids = {station['station_id'] for station in replay['stations']}
    if (frame.duplicated(KEYS).any() or not set(frame.station_id) <= station_ids
            or not np.isfinite(frame[['y_mm'] + DISPLAY_FIELDS].to_numpy()).all()):
        raise ValueError('Invalid station predictions in the replay archive')
    cutoffs = pd.read_csv(PUBLIC / 'cutoffs.csv').query("model == 'B'").set_index('horizon').cutoff.to_dict()
    latest_rows = frame[frame.issue_utc.eq(anchor)]
    expected = replay_snapshot(latest['id'], latest['label'], anchor, latest_rows, cutoffs)
    if expected != latest:
        raise ValueError('Latest replay differs from verified snapshot')
    snapshots = [
        replay_snapshot('replay-' + issue.strftime('%Y%m%d'), 'Lưu trữ đánh giá', issue, rows, cutoffs)
        for issue, rows in frame[frame.issue_utc.lt(anchor)].groupby('issue_utc', sort=False)
    ]
    snapshots.sort(key=lambda issue: issue['issue_utc'], reverse=True)
    write_json(PRIVATE / 'past_week_private.json', dict(
        schema_version=1, anchor_utc=latest['issue_utc'], model_freeze_sha256=replay['model_freeze_sha256'],
        replay_sha256=sha(replay_file), snapshots=snapshots,
    ))
    print(f'Prepared {len(snapshots)} archived issue dates before {anchor.date():%Y-%m-%d}; {len(frame):,} rows checked.')


if __name__ == '__main__':
    main()
