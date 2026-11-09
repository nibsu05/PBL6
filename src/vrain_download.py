"""Resumable, rate-limited Vrain archive capture. Never trains or opens 2025."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, timedelta, datetime, timezone
import ctypes
import gzip
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time

import requests
from src.vrain_export_audit import audit_history, inventory_from_groups

ORIGIN = 'https://www.vrain.vn'
HEADERS = {'User-Agent': 'Mozilla/5.0', 'x-vrain-user-agent': 'Mozilla/5.0',
           'Origin': ORIGIN, 'Referer': ORIGIN+'/landing',
           'Accept': 'application/json', 'Cache-Control': 'no-cache'}


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def planned_dates(start: str, end: str, allow_recent=False):
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if last < first:
        raise ValueError('End precedes start')
    if first <= date(2025, 12, 31) and last >= date(2025, 1, 1):
        raise ValueError('2025 is reserved; this collector refuses it')
    if allow_recent:
        # A nominal 1 January gauge day can include observations from December 2025.
        if first < date(2026,1,2) or last > date(2026,12,31):
            raise ValueError('Recent archive must stay inside 2026 and exclude 1 January')
    elif first < date(2015, 1, 1) or last > date(2024, 12, 31):
        raise ValueError('This collection is limited to 2015-2024')
    return [(first+timedelta(days=i)).isoformat() for i in range((last-first).days+1)]


def _dpapi(raw, decrypt=False):
    if os.name != 'nt':
        raise OSError('Session storage requires Windows DPAPI')
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buffer = ctypes.create_string_buffer(raw)
    source = Blob(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel.LocalFree(target.data)


def atomic_bytes(path, raw):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.part')
    temporary.write_bytes(raw)
    os.replace(temporary, path)


def save_session(session, path):
    cookies = [dict(name=c.name, value=c.value, domain=c.domain, path=c.path,
                    secure=c.secure, expires=c.expires) for c in session.cookies]
    if not cookies:
        raise ValueError('Authenticated cookie is absent')
    atomic_bytes(path, _dpapi(json.dumps(cookies).encode('utf8')))


def load_session(path):
    cookies = json.loads(_dpapi(Path(path).read_bytes(), decrypt=True))
    session = requests.Session(); session.headers.update(HEADERS)
    for cookie in cookies:
        session.cookies.set_cookie(requests.cookies.create_cookie(**cookie))
    return session


def login(username, password):
    session = requests.Session(); session.headers.update(HEADERS)
    response = session.post(ORIGIN+'/api/vrain/public/v1/login',
                            json=dict(username=username, password=password), timeout=(10, 40))
    if response.status_code != 200 or 'json' not in response.headers.get('content-type', ''):
        raise PermissionError('Login was not confirmed')
    response.json()
    return session


@contextmanager
def process_lock(path):
    with Path(path).open('a+b') as handle:
        if not handle.tell():handle.write(b'0');handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:yield
        finally:
            handle.seek(0)
            if os.name == 'nt':msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class Archive:
    def __init__(self, output, start, end, allow_recent=False):
        self.output = Path(output);self.output.mkdir(parents=True, exist_ok=True)
        self.dates = planned_dates(start, end, allow_recent=allow_recent)
        self.date_set = set(self.dates)
        self.database = sqlite3.connect(self.output/'manifest.sqlite')
        self.database.execute('CREATE TABLE IF NOT EXISTS days(day TEXT PRIMARY KEY, record TEXT NOT NULL)')
        self.database.commit()

    def path(self, day):
        if day not in self.date_set:raise ValueError('Date is outside this collection')
        return self.output/'raw'/day[:4]/(day+'.json.gz')

    def record(self, day):
        row = self.database.execute('SELECT record FROM days WHERE day=?', (day,)).fetchone()
        return json.loads(row[0]) if row else None

    def verified(self, day):
        record = self.record(day);path = self.path(day)
        if not record or not path.exists():return False
        return hashlib.sha256(path.read_bytes()).hexdigest() == record['gzip_sha256']

    def store(self, day, raw, inventory, legacy, origin, elapsed):
        payload = json.loads(raw)
        if not isinstance(payload, dict) or not isinstance(payload.get('stats'), list):
            raise ValueError('Expected Vrain daily JSON, not a login/error page')
        details = None
        try:
            details = audit_history(payload, day, inventory, legacy_inventory=legacy)
            status = 'hourly_rows_present' if details['hourly_rows'] else 'no_hourly_data'
        except ValueError as error:
            # Preserve the actual source and flag it; no substitution or silent deletion.
            status = 'structure_flag'
            reason = str(error)
        path = self.path(day)
        compressed = gzip.compress(raw, compresslevel=6, mtime=0)
        atomic_bytes(path, compressed)
        record = dict(day=day, status=status, retrieved_at_utc=utcnow(), origin=origin,
                      raw_sha256=hashlib.sha256(raw).hexdigest(), gzip_sha256=hashlib.sha256(compressed).hexdigest(),
                      raw_bytes=len(raw), gzip_bytes=len(compressed), request_seconds=elapsed,
                      relative_path=path.relative_to(self.output).as_posix(), training_ready=False)
        if details is not None:
            record.update(hourly_rows=details['hourly_rows'],
                          station_count=details['nstation_union'],
                          complete_24_station_count=details['all24_complete_station_count'],
                          valid_numeric_cells=details['valid_numeric_cells'],
                          missing_cells=details['missing_cells'],
                          sum_mismatches=details['complete_station_sum_mismatches'])
        else:record['structure_flag_reason'] = reason
        self.database.execute('INSERT OR REPLACE INTO days VALUES (?,?)', (day,json.dumps(record)))
        self.database.commit()
        return record

    def progress(self, state, current=None, seconds_per_day=1.0, **extra):
        records = [json.loads(row[0]) for row in self.database.execute('SELECT record FROM days')]
        active = [r for r in records if r['day'] in self.date_set]
        completed = len(active);remaining = len(self.dates)-completed
        result = dict(state=state, updated_at_utc=utcnow(), pid=os.getpid(),
                      requested_start=self.dates[0], requested_end=self.dates[-1],
                      requested_days=len(self.dates), downloaded_days=completed,
                      remaining_days=remaining, current_day=current,
                      days_with_hourly_rows=sum(r['status']=='hourly_rows_present' for r in active),
                      days_without_hourly_rows=sum(r['status']=='no_hourly_data' for r in active),
                      days_flagged=sum(r['status']=='structure_flag' for r in active),
                      raw_bytes=sum(r['raw_bytes'] for r in active),
                      gzip_bytes=sum(r['gzip_bytes'] for r in active),
                      estimated_remaining_minutes=round(remaining*seconds_per_day/60,1),
                      test2025_read=False, training_performed=False, training_ready=False, **extra)
        atomic_bytes(self.output/'progress.json', (json.dumps(result,indent=2)+'\n').encode('utf8'))
        return result


def collect(output, start, end, group_id=29, interval=1.0, session=None):
    if interval < 1.0:raise ValueError('Use at most one request per second')
    output = Path(output);output.mkdir(parents=True, exist_ok=True)
    with process_lock(output/'collector.lock'):
        archive = Archive(output,start,end)
        stop = output/'STOP'
        if stop.exists():return archive.progress('stopped', seconds_per_day=interval)
        session = session or load_session(output/'session.dpapi')
        source_folder = output.parent
        inventory = inventory_from_groups(json.loads((source_folder/'groups_v2_private.json').read_text(encoding='utf8')))
        legacy = inventory_from_groups(json.loads((source_folder/'groups_private.json').read_text(encoding='utf8')))
        last_request = 0.0;measurements=[];failed=[];consecutive_failures=0
        def request(url, **kwargs):
            nonlocal last_request
            delay = interval-(time.monotonic()-last_request)
            if delay>0:time.sleep(delay)
            last_request=time.monotonic()
            return session.get(url, timeout=(10,90), **kwargs)
        # Confirm the signed-in scope before requesting history; no guessed groups.
        try:
            response=request(ORIGIN+'/api/vrain/private/v1/stats/summary')
            if response.status_code in (401,403):raise PermissionError('Session expired')
            response.raise_for_status();groups=response.json()
            if not isinstance(groups,list) or any(not isinstance(g,dict) or not isinstance(g.get('stats'),list) for g in groups):
                raise ValueError('Unexpected authenticated summary schema')
            permitted={int(s['groupId']) for g in groups for s in g.get('stats',[]) if s.get('groupId') is not None}
            if int(group_id) not in permitted:raise PermissionError('Group is outside authenticated scope')
            archive.progress('downloading',seconds_per_day=interval)
            # Latest years first; every requested day is still independently captured.
            for day in reversed(archive.dates):
                if stop.exists():return archive.progress('stopped',seconds_per_day=interval, failed_days=failed)
                if archive.verified(day):continue
                existing=source_folder/('history_'+day+'.json')
                if existing.exists():
                    archive.store(day,existing.read_bytes(),inventory,legacy,'saved_probe',0)
                    archive.progress('downloading',day,interval,failed_days=failed)
                    continue
                success=False
                for attempt in range(4):
                    try:
                        began=time.monotonic()
                        response=request(ORIGIN+f'/api/vrain/private/v1/groups/{int(group_id)}/stats/details',params={'from':day,'to':day})
                        if response.status_code in (401,403):raise PermissionError('Session expired or scope denied')
                        if response.status_code==429:
                            retry=response.headers.get('Retry-After','30')
                            delay=min(120,max(5,float(retry))) if retry.replace('.','',1).isdigit() else 30
                            archive.progress('rate_limit_wait',day,interval,retry_after_seconds=delay)
                            time.sleep(delay);continue
                        response.raise_for_status()
                        if 'json' not in response.headers.get('content-type',''):raise ValueError('Non-JSON response')
                        record=archive.store(day,response.content,inventory,legacy,'authenticated_web_daily',time.monotonic()-began)
                        measurements.append(time.monotonic()-began)
                        if len(measurements)>60:measurements.pop(0)
                        speed=max(interval,sum(measurements)/len(measurements))
                        archive.progress('downloading',day,speed,failed_days=failed)
                        if record['status']=='structure_flag':print(f'{day}: saved, structure flagged',flush=True)
                        success=True;consecutive_failures=0;break
                    except PermissionError:raise
                    except (requests.RequestException,ValueError,OSError) as error:
                        # Only the class is logged; no response body, cookie or token.
                        archive.progress('retry_wait',day,interval,error_type=type(error).__name__,attempt=attempt+1)
                        time.sleep(min(30,2**attempt))
                if not success:
                    failed.append(day);consecutive_failures+=1
                    if consecutive_failures>=5:return archive.progress('network_error',day,interval,failed_days=failed)
            return archive.progress('download_complete' if not failed else 'incomplete',seconds_per_day=interval,failed_days=failed)
        except PermissionError:
            return archive.progress('login_required',seconds_per_day=interval,failed_days=failed)
        except (requests.RequestException, ValueError) as error:
            return archive.progress('source_error',seconds_per_day=interval,error_type=type(error).__name__)
        finally:
            archive.database.close()
