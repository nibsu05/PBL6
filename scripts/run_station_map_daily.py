"""Run a scheduled attempt at collection or verification on the forecast workstation."""

import argparse
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
import logging
import sqlite3
import sys
from time import sleep
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from demo.station_map_live import LIVE, VIETNAM, read_optional, timestamp
from demo.station_map_alerts import AdminAlerts
from demo.station_map_status import probe_sources
from src.gfs_window import write_json
from src.gfs_window_live import record_issue, verify_due
from src.vrain_download import process_lock

STATE = ROOT / 'data/operational/station_map_web/daily'
START = time(18, 40)
LAST_ATTEMPT = time(18, 56)
VERIFY = time(20, 5)


def publication_day(at):
    local = at.astimezone(VIETNAM)
    return local.replace(hour=19, minute=0, second=0, microsecond=0)


def source_block(sources, required_hour):
    vrain = sources['vrain']
    channels = vrain.get('channels', {})
    if not channels or any(value.get('http_status') != 200 for value in channels.values()):
        return 'vrain_unavailable'
    latest = vrain.get('last_hour')
    if latest is None or timestamp(latest) < required_hour:
        return 'vrain_18h_pending'
    if sources['gfs'].get('status') != 'ok':
        return 'gfs_unavailable'
    return None


def collect_sources(state, at, refresh=False):
    report = probe_sources(at)
    vrain = report['sources']['vrain']
    channels = vrain.get('channels', {})
    session_rejected = vrain.get('inventory_http_status') in (401, 403) or any(
        info.get('http_status') in (401, 403) for info in channels.values()
    )
    if refresh and session_rejected:
        from scripts.track_gfs_window_issue import refresh_authorized_session

        try:
            refresh_authorized_session()
        except (OSError, ValueError, RuntimeError) as error:
            report['sources']['vrain']['renewal_error'] = type(error).__name__
        else:
            report = probe_sources(datetime.now(timezone.utc))
    write_json(state / 'source_status.json', report)
    notify_owner(state, report, source=True)
    return report['sources']


def notify_owner(state, report, source=False):
    try:
        inbox = AdminAlerts(state.parent / 'admin_alerts.sqlite')
        if source:
            inbox.sources(report)
        else:
            inbox.job(report)
    except (OSError, sqlite3.Error) as error:
        logging.warning('Cannot save admin notification: %s', type(error).__name__)


def forecast(state, started):
    issue = publication_day(started)
    reference = dict(issue_utc=issue.astimezone(timezone.utc).isoformat())
    local_time = started.astimezone(VIETNAM).time()
    if not START <= local_time < LAST_ATTEMPT:
        return dict(status='skipped', reason='outside_forecast_window', **reference)
    issue_folder = LIVE / 'issuances' / issue.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    if (issue_folder / 'issuance.json').exists():
        return dict(status='already_recorded', **reference)
    gate = issue - timedelta(hours=1)
    reason = 'vrain_18h_pending'
    for attempt in range(3):
        if datetime.now(VIETNAM).time() >= LAST_ATTEMPT:
            break
        sources = collect_sources(state, datetime.now(timezone.utc), refresh=attempt == 0)
        reason = source_block(sources, gate)
        if reason == 'vrain_unavailable':
            break
        if reason is None:
            if datetime.now(VIETNAM).time() >= LAST_ATTEMPT:
                return dict(status='skipped', reason='outside_forecast_window', **reference)
            try:
                result = record_issue(issue.date().isoformat())
            except Exception as error:
                return dict(status='failed', reason='issue_record_error', error_type=type(error).__name__, **reference)
            return dict(status='recorded', recorded_utc=result['recorded_utc'],
                        stations=result['station_count'], stations_expected=result['candidate_stations'], **reference)
        if attempt < 2:
            sleep(75)
    return dict(status='blocked', reason=reason, **reference)


def preserve_partial_truth(root, folder):
    partial = root / 'verification' / folder.name
    if not partial.is_dir():
        return
    recovery = root / 'incomplete_verification'
    archived = recovery / (folder.name + '_' + uuid4().hex[:8])
    if not all(path.resolve().is_relative_to(root.resolve()) for path in (partial, archived)):
        raise ValueError('Verification recovery escaped the live workspace')
    recovery.mkdir(exist_ok=True)
    partial.rename(archived)


def verify(started):
    due = []
    for folder in sorted((LIVE / 'issuances').glob('*')):
        record = read_optional(folder / 'issuance.json')
        if not record or record.get('status') != 'recorded_before_issue':
            continue
        if started < timestamp(record['truth_due_utc']) + timedelta(hours=1):
            continue
        truth = read_optional(LIVE / 'verification' / folder.name / 'verification.json')
        if truth and truth.get('valid_common_rows', 0) > 0:
            continue
        due.append(folder)
    if not due:
        return dict(status='waiting', reason='no_due_issue', verified_issues=0)
    for folder in due:
        preserve_partial_truth(LIVE, folder)
    try:
        result = verify_due()
    except PermissionError:
        from scripts.track_gfs_window_issue import refresh_authorized_session

        refresh_authorized_session()
        for folder in due:
            report = read_optional(LIVE / 'verification' / folder.name / 'verification.json')
            if not report or report.get('valid_common_rows', 0) <= 0:
                preserve_partial_truth(LIVE, folder)
        result = verify_due()
    verified = [
        read_optional(LIVE / 'verification' / folder.name / 'verification.json')
        for folder in due
    ]
    valid = sum(bool(item and item.get('valid_common_rows', 0) > 0) for item in verified)
    return dict(status='verified' if valid else 'pending', verified_issues=valid,
                attempted_issues=result['verified_issues'])


def run(state, job, started):
    state.mkdir(parents=True, exist_ok=True)
    local = started.astimezone(VIETNAM)
    if job == 'auto':
        job = 'forecast' if START <= local.time() < VERIFY else 'verify'
    details = dict(job=job, started_utc=started.isoformat())
    try:
        with process_lock(state / 'jobs.lock'):
            write_json(state / (job + '.json'), dict(details, status='running'))
            try:
                if job == 'forecast':
                    result = forecast(state, started)
                elif job == 'verify':
                    result = verify(started)
                else:
                    sources = collect_sources(state, started)
                    result = dict(status='checked', sources={key: item['status'] for key, item in sources.items()})
            except Exception as error:
                result = dict(status='failed', reason='job_error', error_type=type(error).__name__)
            report = dict(details, **result, finished_utc=datetime.now(timezone.utc).isoformat())
            write_json(state / (job + '.json'), report)
            write_json(state / 'history' / f'{local:%Y%m%dT%H%M%S%f}_{job}.json', report)
            notify_owner(state, report)
    except OSError:
        return dict(details, status='skipped', reason='job_lock_or_storage_error')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', choices=('auto', 'forecast', 'verify', 'probe'), default='auto')
    args = parser.parse_args()
    report = run(STATE, args.job, datetime.now(timezone.utc))
    if sys.stdout:
        print(report, flush=True)
    return int(report['status'] == 'failed')


if __name__ == '__main__':
    sys.exit(main())
