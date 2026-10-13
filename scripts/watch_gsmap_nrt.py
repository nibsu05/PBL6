"""Ghi giờ file GSMaP NRT v8 *mới* xuất hiện trên JAXA, chạy có thời hạn.

Nhập credential qua prompt, giữ trong RAM phiên này; không ghi vào tệp/Git/log.
Lần poll đầu chỉ ghi baseline tên file; các file mới sau đó mới đo latency.
"""
from __future__ import annotations

import argparse
import ftplib
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.fetch_gsmap_nrt import HOST, DIRECTORY, connect, credentials
from src.gsmap_nrt import decode_nrt_binary, interval_from_filename

PATTERN = re.compile(r'gsmap_nrt\.\d{8}\.\d{2}00\.dat\.gz')
PRIVATE = ROOT / 'data/operational/jaxa_downloads'
STATUS = ROOT / 'reports/followup_danang/jaxa_live_watch_status.json'


def utc_now():
    return datetime.now(timezone.utc)


def open_ftp(uid, pw, allow_plain):
    client, transport = connect(allow_plain, announce=False)
    try:
        client.login(uid, pw)
        if transport == 'FTPS':
            client.prot_p()
        client.cwd(DIRECTORY)
        return client, transport
    except Exception:
        client.close()
        raise


def list_raw_files(client):
    names = sorted({Path(name).name for name in client.nlst()
                    if PATTERN.fullmatch(Path(name).name)})
    if not names:
        raise RuntimeError('JAXA latest không có file raw NRT; giữ baseline cũ')
    return names, utc_now()


def download_new(client, names, first_seen, transport):
    if not names:
        return []
    stamp=utc_now().strftime('%Y%m%dT%H%M%SZ')
    out=PRIVATE / (stamp + '_watch')
    out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for name in names:
        lo,hi=interval_from_filename(name)
        if first_seen < hi:
            raise ValueError('FTP báo file khi khoảng mưa chưa kết thúc')
        path=out/name
        temporary=out/(name+'.part')
        try:
            with temporary.open('wb') as f:
                client.retrbinary('RETR '+name,f.write)
            body=temporary.read_bytes()
            grid=decode_nrt_binary(body)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        completed=utc_now()
        rows.append(dict(file=name,bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),
                         first_seen_at_utc=first_seen.isoformat(),
                         first_recorded_at_utc=completed.isoformat(),
                         observed_age_from_interval_end_h=(first_seen-hi).total_seconds()/3600,
                         retrieved_age_from_interval_end_h=(completed-hi).total_seconds()/3600,
                         decoded_shape=list(grid.shape),
                         source_uri='ftp://'+HOST+DIRECTORY+name))
        print('NEW '+name+' first_seen='+first_seen.isoformat()+' age_h='+
              f'{(first_seen-hi).total_seconds()/3600:.2f}',flush=True)
    manifest=dict(authenticated=True,host=HOST,transport=transport,directory=DIRECTORY,
                  algorithm_version=8,product='GSMaP_NRT',credential_persisted=False,
                  collection_mode='watch_new_files_only',files=rows)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return rows


def publish_status(state):
    STATUS.parent.mkdir(parents=True,exist_ok=True)
    STATUS.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hours',type=float,default=8,help='thời lượng ghi, mặc định 8 giờ')
    parser.add_argument('--interval-s',type=int,default=600,help='mỗi 10 phút poll; tối thiểu 300 giây')
    parser.add_argument('--allow-plain-ftp',action='store_true',help='cho phép FTP thường nếu JAXA không hỗ trợ FTPS')
    args=parser.parse_args()
    if not 0.25<=args.hours<=72 or args.interval_s<300:
        parser.error('hours 0.25–72 và interval-s ≥300')
    uid,pw=credentials()
    started=utc_now()
    deadline=time.monotonic()+args.hours*3600
    state=dict(started_at_utc=started.isoformat(),poll_interval_s=args.interval_s,
               hours_requested=args.hours,baseline_files=0,polls=0,new_files=0,
               last_new_file=None,last_new_age_h=None,errors=0,last_error_type=None,
               credential_persisted=False,source='JAXA GSMaP_NRT v8 FTP latest',
               source_publication_time_attested=False,
               nominal_poll_interval_minutes=args.interval_s/60,
               ready_for_ml=False)
    seen=None
    while time.monotonic()<deadline:
        try:
            client,transport=open_ftp(uid,pw,args.allow_plain_ftp)
            state['transport']=transport
            try:
                names,seen_at=list_raw_files(client)
                state['polls']+=1
                if seen is None:
                    seen=set(names)
                    state['baseline_files']=len(names)
                    print('BASELINE '+str(len(names))+' files; transport='+transport+'; waiting for new files',flush=True)
                else:
                    new=[name for name in names if name not in seen]
                    rows=download_new(client,new,seen_at,transport)
                    seen.update(new)
                    state['new_files']+=len(rows)
                    if rows:
                        state['new_file_first_seen_after_start']=True
                        state['last_new_file']=rows[-1]['file']
                        state['last_new_age_h']=rows[-1]['observed_age_from_interval_end_h']
            finally:
                try:client.quit()
                except Exception:client.close()
        except Exception as exc:
            state['errors']+=1
            state['last_error_type']=type(exc).__name__
            print('POLL_FAILED type='+type(exc).__name__,flush=True)
        state['last_polled_at_utc']=utc_now().isoformat()
        publish_status(state)
        next_poll=min(deadline,time.monotonic()+args.interval_s)
        while time.monotonic()<next_poll:
            time.sleep(min(30,next_poll-time.monotonic()))
    state['finished_at_utc']=utc_now().isoformat()
    publish_status(state)
    pw=None
    print('WATCH_COMPLETE '+json.dumps({k:state[k] for k in ('polls','new_files','errors')}),flush=True)


if __name__=='__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('WATCH_INTERRUPTED',flush=True)
