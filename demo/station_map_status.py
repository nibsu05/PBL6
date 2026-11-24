"""Status and verification data for the local station dashboard."""

import csv
from datetime import datetime, timedelta, timezone
import io
import json
import math
from threading import Lock, Thread
from urllib.error import HTTPError
from urllib.request import urlopen

from demo.station_map_live import LIVE, ROOT, VIETNAM, read_optional, recent_snapshots, timestamp

OPERATIONAL = ROOT / 'data' / 'operational'
REPLAY_DIR = OPERATIONAL / 'gfs_short_range_closeout_2026_11_24'
WINDOW_STUDY = 'gfs_training_window_2026_11_18'
RESULTS = ROOT / 'reports' / WINDOW_STUDY
REFERENCE = ROOT / 'reports' / 'gfs_short_range_closeout_2026_11_24'
GFS_LEADS = (12, 24, 36, 48, 60, 72, 84)


def read_csv(path):
    with path.open(encoding='utf-8', newline='') as source:
        return list(csv.DictReader(source))


def replay():
    return json.loads((REPLAY_DIR / 'station_map_private.json').read_bytes())


def available_forecasts():
    data = replay()
    historical = data['snapshots']
    for issue in historical:
        issue.update(mode='historical_replay', has_truth=True)
    if not any((LIVE / 'issuances').glob('*/issuance.json')):
        return data
    cutoffs = {int(row['horizon']): float(row['cutoff']) for row in read_csv(RESULTS / 'cutoffs.csv')
               if row['model'] == 'B'}
    actual = recent_snapshots({row['station_id'] for row in data['stations']}, cutoffs, live=LIVE)
    if actual:
        data.update(mode='prospective', snapshots=actual + historical)
    return data


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
    largest_errors = sorted(
        (dict(station_id=p['station_id'], predicted_mm=p['predicted_mm'], observed_mm=p['observed_mm'],
              error=p['predicted_mm'] - p['observed_mm']) for p in completed),
        key=lambda p: abs(p['error']), reverse=True,
    )[:5]
    return dict(horizon=window['horizon'], start_utc=window['start_utc'], end_utc=window['end_utc'],
                stations=len(completed), scores=scores, heavy_events=hits + misses, hits=hits, misses=misses,
                false_alarms=false_alarms, cutoff=cutoff, largest_errors=largest_errors)


def verification_payload():
    data = available_forecasts()
    issues = [dict(id=case['id'], label=case['label'], issue_utc=case['issue_utc'], mode=case['mode'],
                   windows=[compare_window(window) for window in case['windows']])
              for case in data['snapshots'] if case['has_truth']]
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
    heavy_cases = [
        dict(horizon=int(row['horizon']), cases=int(row['events']), baseline=float(row['reference']),
             adjusted=float(row['model']), change=float(row['difference']))
        for row in read_csv(ROOT / 'reports/gfs_gated_amount_2026_11_24/tail_mae_paired.csv')
    ]
    return dict(roster=len(data['stations']), replay_issues=issues, retrospective_rmse=aggregate,
                feature_holdout=holdout, heavy_amount_variant=heavy_cases)


def export_csv(issue_id, horizon):
    data = available_forecasts()
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
        measured = point.get('observed_mm')
        difference = round(point['predicted_mm'] - measured, 6) if measured is not None else None
        writer.writerow((issue['issue_utc'], window['start_utc'], window['end_utc'],
                         *(point.get(field) for field in fields), difference))
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
    latest = available_forecasts()['snapshots'][0]
    if latest['mode'] != 'prospective':
        return None
    fields = ('id', 'issue_utc', 'recorded_utc', 'station_count', 'truth_due_utc')
    return dict(**{key: latest[key] for key in fields}, verified=latest['has_truth'])


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
    stations = registry.canonical_id.tolist()
    channels = {}
    with load_session(VRAIN / 'session.dpapi') as session:
        for channel, endpoint, headers, extra in [
            ('modern', '/api/kttv/private/v1/organizations/details', {'x-org-uuid': organization}, {'i': '_1h'}),
            ('legacy', '/api/vrain/private/v1/groups/29/stats/details', {}, {}),
        ]:
            try:
                response = session.get(ORIGIN + endpoint, params={'from': day, 'to': day, **extra},
                                       headers=headers, timeout=(6, 12))
                status = response.status_code
                if status != requests.codes.ok:
                    channels[channel] = dict(status='error', http_status=status)
                    continue
                parsed = parse_live_day(response.json(), day, aliases[channel], stations)
                clocks = parsed['times'].tz_localize(VIETNAM)
                released = (clocks <= datetime.now(VIETNAM)) & parsed['valid'].any(axis=1)
                channels[channel] = dict(status='ok' if released.any() else 'waiting', http_status=status,
                                         stations=int(parsed['valid'][released].any(axis=0).sum()),
                                         last_hour=clocks[released].max().isoformat() if released.any() else None)
            except (requests.RequestException, ValueError, KeyError, TypeError) as error:
                channels[channel] = dict(status='error', error_type=type(error).__name__)
    representative = max(channels.values(),
                         key=lambda item: (item.get('last_hour') or '', item['status'] == 'waiting'))
    return dict(kind='station_hours', day=day, channels=channels, **representative)


def probe_sources(started):
    sources = {}
    for key, check in [('gfs', check_gfs), ('vrain', check_vrain)]:
        try:
            result = check(started.astimezone(VIETNAM))
        except (OSError, ImportError, ValueError, RuntimeError, KeyError, TypeError) as error:
            result = dict(status='error', error_type=type(error).__name__,
                          kind='index' if key == 'gfs' else 'station_hours')
        sources[key] = dict(checked_at=datetime.now(timezone.utc).isoformat(), **result)
    return dict(started_at=started.isoformat(), sources=sources)


class SourceMonitor:
    def __init__(self, state_dir):
        self.path = state_dir / 'source_status.json'
        self.daily = state_dir / 'daily'
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

            write_json(self.path, probe_sources(started))
        finally:
            with self.lock:
                self.running = False

    def status(self):
        checked_at = datetime.now(timezone.utc)
        sources, decode = saved_sources()
        for saved in (read_optional(self.daily / 'source_status.json'), read_optional(self.path)):
            for key, record in (saved or {}).get('sources', {}).items():
                if key not in sources or timestamp(record['checked_at']) >= timestamp(sources[key]['checked_at']):
                    sources[key] = record
        daily = {key: read_optional(self.daily / (key + '.json'))
                 for key in ('schedule', 'forecast', 'verify', 'probe')}
        for job in ('forecast', 'verify'):
            last = daily[job]
            if last and last.get('status') == 'running' and checked_at - timestamp(last['started_utc']) > timedelta(minutes=25):
                daily[job] = dict(last, status='interrupted', reason='job_timeout')
        return dict(
            checked_at=checked_at.isoformat(), sources=sources, last_gfs_decode=decode,
            source_probe_running=self.running, last_recorded_issue=recorded_issue(),
            planned_issue_local='19:00', daily=daily,
        )
