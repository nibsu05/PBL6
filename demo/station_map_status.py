"""Status and verification data for the local station dashboard."""

import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import math
from pathlib import Path
from threading import Lock, Thread
from urllib.error import HTTPError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
OPERATIONAL = ROOT / 'data' / 'operational'
REPLAY_DIR = OPERATIONAL / 'gfs_short_range_closeout_2026_11_24'
WINDOW_STUDY = 'gfs_training_window_2026_11_18'
LIVE = OPERATIONAL / WINDOW_STUDY / 'live'
RESULTS = ROOT / 'reports' / WINDOW_STUDY
REFERENCE = ROOT / 'reports' / 'gfs_short_range_closeout_2026_11_24'
VIETNAM = timezone(timedelta(hours=7))
GFS_LEADS = (12, 24, 36, 48, 60, 72, 84)


def read_optional(path):
    try:
        return json.loads(path.read_bytes())
    except (OSError, ValueError):
        return None


def timestamp(value):
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def read_csv(path):
    with path.open(encoding='utf-8', newline='') as source:
        return list(csv.DictReader(source))


def replay():
    return json.loads((REPLAY_DIR / 'station_map_private.json').read_bytes())


def forecast_payload(data, signed_in):
    data['viewer'] = 'member' if signed_in else 'guest'
    if not signed_in:
        for issue in data['snapshots']:
            for window in issue['windows']:
                for point in window['points']:
                    for field in ('observed_mm', 'mos_mm'):
                        point.pop(field, None)
    return data


def compare_window(window):
    points = window['points']
    completed = [
        point for point in points
        if all(isinstance(point.get(field), (int, float)) and math.isfinite(point[field])
               for field in ('observed_mm', 'predicted_mm', 'gfs_mm', 'mos_mm', 'probability_ge50'))
    ]
    scores = []
    for name, field in [('LightGBM B', 'predicted_mm'), ('GFS', 'gfs_mm'), ('MOS', 'mos_mm')]:
        errors = [point[field] - point['observed_mm'] for point in completed]
        n = len(errors)
        scores.append(dict(
            model=name, mae=sum(map(abs, errors)) / n if n else None,
            rmse=math.sqrt(sum(error ** 2 for error in errors) / n) if n else None,
            bias=sum(errors) / n if n else None,
            over_20=sum(abs(error) > 20 for error in errors),
        ))
    cutoff = window['cutoff_ge50_probability']
    hits = misses = false_alarms = 0
    for point in completed:
        rain_ge50 = point['observed_mm'] >= 50
        predicted_ge50 = point['probability_ge50'] >= cutoff
        hits += rain_ge50 and predicted_ge50
        misses += rain_ge50 and not predicted_ge50
        false_alarms += not rain_ge50 and predicted_ge50
    return dict(horizon=window['horizon'], start_utc=window['start_utc'], end_utc=window['end_utc'],
                stations=len(completed), scores=scores, heavy_events=hits + misses, hits=hits, misses=misses,
                false_alarms=false_alarms, cutoff=cutoff)


def verification_payload():
    data = replay()
    issues = [dict(id=case['id'], label=case['label'], issue_utc=case['issue_utc'],
                   windows=[compare_window(window) for window in case['windows']]) for case in data['snapshots']]
    aggregate = [
        dict(horizon=int(row['horizon']), model=row['model'], rmse=float(row['macro_rmse']))
        for row in read_csv(RESULTS / 'point_metrics.csv')
        if row['evaluation_set'] == 'retrospective2026_modern' and row['functional'] == 'mean'
        and row['model'] in ('B', 'GFS', 'MOS_LONG')
    ]
    holdout = [
        dict(horizon=int(row['horizon']), reference=float(row['reference_score']),
             model=float(row['model_score']), difference=float(row['difference']))
        for row in read_csv(REFERENCE / 'doi_chieu_kiem_dinh_2025.csv')
        if row['model'] == 'LGB_N1' and row['reference'] == 'LGB_N0'
    ]
    return dict(roster=len(data['stations']), replay_issues=issues, retrospective_rmse=aggregate,
                feature_holdout=holdout)


def export_csv(issue_id, horizon):
    data = replay()
    issue = next((case for case in data['snapshots'] if case['id'] == issue_id), None)
    if not issue:
        raise ValueError('unknown_issue')
    window = next((item for item in issue['windows'] if item['horizon'] == horizon), None)
    if not window:
        raise ValueError('unknown_horizon')
    fields = ('station_id', 'predicted_mm', 'gfs_mm', 'mos_mm', 'observed_mm', 'probability_ge50')
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(('issue_utc', 'start_utc', 'end_utc', *fields, 'lightgbm_minus_vrain_mm'))
    for point in window['points']:
        difference = point['predicted_mm'] - point['observed_mm']
        writer.writerow((issue['issue_utc'], window['start_utc'], window['end_utc'],
                         *(point.get(field) for field in fields), round(difference, 6)))
    return output.getvalue().encode('utf-8-sig'), f'pbl6-{issue_id}-ngay-{horizon}.csv'


def saved_sources():
    sources = {}
    decode = None
    for path in sorted((REPLAY_DIR / 'daily_rehearsals').glob('*/report.json')):
        report = read_optional(path)
        if not report or not report.get('checked_vietnam'):
            continue
        checked = report['checked_vietnam']
        if report.get('decoded_fields'):
            decode = dict(status='ok', checked_at=checked, kind='decode', fields=report['decoded_fields'],
                          stations=report['stations'], cycle=report['cycle'])
            sources['gfs'] = decode
        attempts = report.get('attempts', [])
        modern = next((row for row in attempts if row.get('channel') == 'modern'), None)
        if modern:
            status = 'error'
            if modern.get('http_status') == 200:
                status = 'ok' if modern.get('stations_with_values') else 'waiting'
            sources['vrain'] = dict(status=status,
                                    checked_at=checked, kind='station_hours', http_status=modern.get('http_status'),
                                    day=modern['day'], stations=modern.get('stations_with_values'),
                                    last_hour=modern.get('latest_valid_hour'))
    return sources, decode


def recorded_issue():
    now = datetime.now(timezone.utc)
    for path in sorted((LIVE / 'issuances').glob('*/issuance.json'), reverse=True):
        record = read_optional(path)
        if not record or record.get('status') != 'recorded_before_issue':
            continue
        try:
            if not timestamp(record['recorded_utc']) < timestamp(record['issue_utc']) <= now:
                continue
            saved = path.parent / 'predictions_private.parquet'
            if not saved.is_file() or hashlib.sha256(saved.read_bytes()).hexdigest() != record['forecast_sha256']:
                continue
            verified = read_optional(LIVE / 'verification' / path.parent.name / 'verification.json')
            return dict(issue_utc=record['issue_utc'], recorded_utc=record['recorded_utc'],
                        station_count=record['station_count'], truth_due_utc=record['truth_due_utc'],
                        verified=bool(verified and verified.get('forecast_sha256') == record.get('forecast_sha256')
                                      and verified.get('valid_common_rows', 0) > 0))
        except (OSError, TypeError, ValueError, KeyError):
            continue
    return None


def check_gfs(now):
    from src.gfs_station import choose_records, parse_index

    cycle_day = now.date()
    if now.hour < 7:
        cycle_day -= timedelta(days=1)
    day = cycle_day.strftime('%Y%m%d')
    fields = 0
    for lead in GFS_LEADS:
        url = f'https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{day}/00/atmos/gfs.t00z.pgrb2.0p25.f{lead:03}.idx'
        try:
            with urlopen(url, timeout=6) as response:
                index = response.read(500_000).decode('utf-8')
            fields += len(choose_records(parse_index(index), lead))
        except (OSError, ValueError) as error:
            return dict(status='error', kind='index', fields=fields,
                        http_status=error.code if isinstance(error, HTTPError) else None)
    return dict(status='ok' if fields == 19 else 'error', fields=fields, kind='index',
                cycle=cycle_day.isoformat() + 'T00:00:00Z')


def check_vrain(now):
    import requests
    from src.gfs_window import VRAIN
    from src.gfs_window_live import parse_live_day, source_context
    from src.vrain_download import ORIGIN, load_session

    day = now.date().isoformat()
    registry, aliases, organization = source_context()
    with load_session(VRAIN / 'session.dpapi') as session:
        response = session.get(ORIGIN + '/api/kttv/private/v1/organizations/details',
                               params={'from': day, 'to': day, 'i': '_1h'},
                               headers={'x-org-uuid': organization}, timeout=(6, 12))
        if response.status_code != requests.codes.ok:
            return dict(status='error', kind='station_hours', day=day, http_status=response.status_code)
        parsed = parse_live_day(response.json(), day, aliases['modern'], registry.canonical_id.tolist())
    clocks = parsed['times'].tz_localize(VIETNAM)
    received = datetime.now(VIETNAM)
    released = (clocks <= received) & parsed['valid'].any(axis=1)
    return dict(status='ok' if released.any() else 'waiting', kind='station_hours', day=day,
                http_status=200, stations=int(parsed['valid'][released].any(axis=0).sum()),
                last_hour=clocks[released].max().isoformat() if released.any() else None)


class SourceMonitor:
    def __init__(self, state_dir):
        self.path = state_dir / 'source_status.json'
        self.lock = Lock()
        self.started = None
        self.running = False

    def start_check(self):
        now = datetime.now(timezone.utc)
        with self.lock:
            last = self.started
            saved = read_optional(self.path)
            if last is None and saved and saved.get('started_at'):
                last = timestamp(saved['started_at'])
            if self.running or (last and now - last < timedelta(minutes=5)):
                return False
            self.started = now
            self.running = True
            Thread(target=self.run_check, args=(now,), daemon=True).start()
        return True

    def run_check(self, started):
        try:
            from src.gfs_window import write_json

            sources = {}
            for key, check in [('gfs', check_gfs), ('vrain', check_vrain)]:
                try:
                    result = check(started.astimezone(VIETNAM))
                except (OSError, ImportError, ValueError, RuntimeError, KeyError, TypeError):
                    result = dict(status='error', kind='index' if key == 'gfs' else 'station_hours')
                sources[key] = dict(checked_at=datetime.now(timezone.utc).isoformat(), **result)
            write_json(self.path, dict(started_at=started.isoformat(), sources=sources))
        finally:
            with self.lock:
                self.running = False

    def status(self):
        sources, decode = saved_sources()
        saved = read_optional(self.path)
        for key, record in (saved or {}).get('sources', {}).items():
            if key not in sources or timestamp(record['checked_at']) >= timestamp(sources[key]['checked_at']):
                sources[key] = record
        tracker = read_optional(LIVE / 'tracker.json') or {}
        return dict(
            checked_at=datetime.now(timezone.utc).isoformat(), sources=sources, last_gfs_decode=decode,
            source_probe_running=self.running, last_recorded_issue=recorded_issue(),
            tracker_heartbeat=tracker.get('updated_utc'), planned_issue_local='19:00',
        )
