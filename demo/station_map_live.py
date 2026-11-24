"""Build map snapshots from time-stamped LightGBM issuances."""

from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/operational/gfs_training_window_2026_11_18'
LIVE = BASE / 'live'
VIETNAM = timezone(timedelta(hours=7))


def read_optional(path):
    try:
        data = json.loads(path.read_bytes())
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def timestamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError('Expected a timezone')
    return parsed.astimezone(timezone.utc)


def load_record(path, now, freeze):
    record = read_optional(path)
    if not record or record.get('status') != 'recorded_before_issue':
        return None
    issue, recorded = timestamp(record['issue_utc']), timestamp(record['recorded_utc'])
    if (not recorded < issue <= now or (issue.hour, issue.minute, issue.second) != (12, 0, 0)
            or issue.strftime('%Y%m%dT%H%M%SZ') != path.parent.name
            or record.get('selected_case') != 'B' or record.get('model_freeze_sha256') != freeze
            or timestamp(record['truth_due_utc']) != issue + timedelta(days=3)):
        return None
    payload = (path.parent / 'predictions_private.parquet').read_bytes()
    if hashlib.sha256(payload).hexdigest() != record.get('forecast_sha256'):
        return None
    return issue, record, payload


def observed_values(folder, record, issue, expected, now):
    import pandas as pd

    report = read_optional(folder / 'verification.json')
    if not report or report.get('forecast_sha256') != record.get('forecast_sha256'):
        return {}
    try:
        if (report.get('status') != 'truth_observed' or report.get('labels_after_forecast') is not True
                or timestamp(report['issue_utc']) != issue
                or not issue + timedelta(hours=73) <= timestamp(report['verified_utc']) <= now
                or report.get('forecast_rows') != len(expected) or report.get('valid_common_rows', 0) <= 0):
            return {}
        label_frame = pd.read_parquet(folder / 'verified_private.parquet',
                                      columns=['station_id', 'horizon', 'issue_utc', 'target_end_utc', 'y_mm'])
        if len(label_frame) != len(expected) or label_frame.duplicated(['station_id', 'horizon']).any():
            return {}
        if not label_frame['issue_utc'].eq(issue).all():
            return {}
        if not label_frame['target_end_utc'].eq(issue + pd.to_timedelta(24 * label_frame.horizon, unit='h')).all():
            return {}
        if set(zip(label_frame.station_id, label_frame.horizon)) != expected:
            return {}
        return {(row.station_id, row.horizon): float(row.y_mm)
                for row in label_frame.itertuples() if math.isfinite(row.y_mm) and row.y_mm >= 0}
    except (OSError, TypeError, ValueError, KeyError):
        return {}


def build_snapshot(path, now, freeze, station_ids, cutoffs):
    import pandas as pd

    checked = load_record(path, now, freeze)
    if checked is None:
        return None
    issue, record, payload = checked
    keys = ['station_id', 'horizon', 'issue_utc', 'target_start_utc', 'target_end_utc', 'gfs_init_utc']
    columns = ['B_mean', 'GFS_mean', 'MOS_LONG_mean', 'B_p50', 'B_p1']
    frame = pd.read_parquet(io.BytesIO(payload), columns=keys + columns)
    stations = set(frame.station_id)
    if (not stations or not stations <= station_ids or len(stations) != record['station_count']
            or len(frame) != record['rows'] or len(frame) != len(stations) * 3
            or frame.duplicated(['station_id', 'horizon']).any() or not frame.horizon.isin([1, 2, 3]).all()):
        raise ValueError('Invalid issuance station pack')
    end = issue + pd.to_timedelta(24 * frame.horizon, unit='h')
    if (not frame.issue_utc.eq(issue).all() or not frame.target_end_utc.eq(end).all()
            or not frame.target_start_utc.eq(end - timedelta(days=1)).all()
            or not frame.gfs_init_utc.eq(issue.replace(hour=0)).all()):
        raise ValueError('Invalid issuance times')
    if (not all(math.isfinite(value) and value >= 0 for value in frame[columns].to_numpy().ravel())
            or not frame.B_p50.le(frame.B_p1).all() or not frame.B_p1.le(1).all()):
        raise ValueError('Invalid issuance values')

    expected = set(zip(frame.station_id, frame.horizon))
    truth_path = path.parents[2] / 'verification' / path.parent.name
    observed = observed_values(truth_path, record, issue, expected, now)
    windows = []
    for h, group in frame.groupby('horizon', sort=True):
        h = int(h)
        points = [dict(station_id=row.station_id, predicted_mm=float(row.B_mean),
                       gfs_mm=float(row.GFS_mean), mos_mm=float(row.MOS_LONG_mean),
                       observed_mm=observed.get((row.station_id, h)),
                       probability_ge50=float(row.B_p50)) for row in group.itertuples()]
        windows.append(dict(horizon=h, start_utc=(issue + timedelta(days=h-1)).isoformat(),
                            end_utc=(issue + timedelta(days=h)).isoformat(),
                            cutoff_ge50_probability=cutoffs[h], points=points))
    return dict(id='live-' + path.parent.name, mode='prospective', label='19:00 giờ Việt Nam',
                issue_utc=issue.isoformat(), gfs_init_utc=issue.replace(hour=0).isoformat(),
                recorded_utc=record['recorded_utc'], truth_due_utc=record['truth_due_utc'],
                station_count=len(stations), has_truth=bool(observed), windows=windows)


def recent_snapshots(stations, cutoffs, now=None, live=LIVE):
    now = now or datetime.now(timezone.utc)
    paths = sorted((live / 'issuances').glob('*/issuance.json'), reverse=True)
    if not paths:
        return []
    try:
        freeze = hashlib.sha256((live.parent / 'model_freeze.json').read_bytes()).hexdigest()
    except OSError:
        return []
    snapshots = []
    for path in paths:
        try:
            snapshot = build_snapshot(path, now, freeze, stations, cutoffs)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if snapshot is not None:
            snapshots.append(snapshot)
        if len(snapshots) == 7:
            break
    return snapshots
