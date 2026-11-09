"""Capture 2026 from both authorized namespaces; never merge observations."""
from pathlib import Path
import ctypes
import json
import os
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.vrain_download import Archive,ORIGIN,load_session,process_lock,atomic_bytes,utcnow
from src.vrain_export_audit import inventory_from_groups

BASE=ROOT/'data/operational/vrain_2026_11_09'
OUT=BASE/'recent_archive'


def main():
    OUT.mkdir(exist_ok=True)
    if os.name=='nt':ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    archives={key:Archive(OUT/key,'2026-01-02','2026-11-08',allow_recent=True) for key in ['legacy','modern']}
    def progress(state,failed=None):
        items={key:archive.progress(state,seconds_per_day=2.) for key,archive in archives.items()}
        result=dict(state=state,updated_at_utc=utcnow(),pid=os.getpid(),requested_start='2026-01-02',requested_end='2026-11-08',
                    requested_responses=622,downloaded_responses=sum(r['downloaded_days'] for r in items.values()),
                    namespaces=items,test2025_read=False,merged=False,training_ready=False,failed=failed or [])
        atomic_bytes(OUT/'progress.json',(json.dumps(result,indent=2)+'\n').encode('utf8'))
        return result
    try:
        with process_lock(OUT/'collector.lock'):
            s=load_session(BASE/'download/session.dpapi')
            g=s.get(ORIGIN+'/api/vrain/private/v2/stats/summary',timeout=(10,45))
            if g.status_code in (401,403):print(json.dumps(progress('login_required')));return
            g.raise_for_status();groups=g.json()
            chosen=[x for x in groups if any(int(q.get('groupId',-1))==29 for q in x.get('stats',[]))]
            if len(chosen)!=1 or not chosen[0].get('groupOrgUuid'):raise ValueError('Authorized organization context absent')
            org_uuid=chosen[0]['groupOrgUuid']
            inventories={key:inventory_from_groups(json.loads((BASE/name).read_text(encoding='utf8'))) for key,name in [('legacy','groups_private.json'),('modern','groups_v2_private.json')]}
            last_request=time.monotonic();failed=[];progress('downloading')
            for day in reversed(archives['legacy'].dates):
                for key,archive in archives.items():
                    if (OUT/'STOP').exists():print(json.dumps(progress('stopped',failed)));return
                    if archive.verified(day):continue
                    for attempt in range(4):
                        try:
                            delay=1.-(time.monotonic()-last_request)
                            if delay>0:time.sleep(delay)
                            last_request=time.monotonic();began=time.monotonic()
                            if key=='legacy':
                                response=s.get(ORIGIN+'/api/vrain/private/v1/groups/29/stats/details',params={'from':day,'to':day},timeout=(10,60))
                            else:
                                response=s.get(ORIGIN+'/api/kttv/private/v1/organizations/details',params={'from':day,'to':day,'i':'_1h'},headers={'x-org-uuid':org_uuid},timeout=(10,60))
                            if response.status_code in (401,403):print(json.dumps(progress('login_required',failed)));return
                            if response.status_code==429:progress('rate_limit_wait',failed);time.sleep(30);continue
                            response.raise_for_status()
                            archive.store(day,response.content,inventories[key],inventories['legacy'],f'authenticated_{key}_2026',time.monotonic()-began)
                            progress('downloading',failed);break
                        except Exception as error:
                            if attempt==3:failed.append({'day':day,'namespace':key,'error_type':type(error).__name__})
                            else:time.sleep(2**attempt)
                    if len(failed)>=5:print(json.dumps(progress('source_error',failed)));return
            print(json.dumps(progress('download_complete' if not failed else 'incomplete',failed),indent=2))
    finally:
        for archive in archives.values():archive.database.close()
        if os.name=='nt':ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__=='__main__':main()
