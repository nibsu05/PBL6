"""Collect both authorized channels through the last complete day, with resume."""
from pathlib import Path
import sys,json,gzip,sqlite3,time,os,shutil
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd
from src.station_archive_update import BASE,OLD,LAST,parse_day,sha,write_json
from src.vrain_download import load_session,ORIGIN,process_lock


def main():
    registry=pd.read_csv(OLD/'handoff_v1/station_registry_private.csv',dtype={'legacy_id':str,'modern_id':str})
    registry.to_csv(BASE/'station_registry_private.csv',index=False)
    ids=registry.canonical_id.tolist()
    aliases={c:dict(zip(registry.loc[registry[c+'_id'].notna(),c+'_id'],registry.loc[registry[c+'_id'].notna(),'canonical_id'])) for c in ('legacy','modern')}
    dates=pd.date_range('2025-01-01',LAST).strftime('%Y-%m-%d').tolist()
    database=sqlite3.connect(BASE/'manifest.sqlite');database.execute('CREATE TABLE IF NOT EXISTS responses(channel TEXT,day TEXT,record TEXT,PRIMARY KEY(channel,day))');database.commit()
    records={(c,d):json.loads(r) for c,d,r in database.execute('select channel,day,record from responses')}
    session=load_session(BASE/'session.dpapi')
    groups=json.loads((BASE/'groups_modern_current_private.json').read_text(encoding='utf8'))
    group=[g for g in groups if any(int(s.get('groupId',-1))==29 for s in g.get('stats',[]))]
    if len(group)!=1 or not group[0].get('groupOrgUuid'):raise ValueError('Authorized organization absent')
    org=group[0]['groupOrgUuid'];start=time.monotonic();last=0;new=0;cached=0;failures=[]
    def progress(state,current=None):
        active=[r for (c,d),r in records.items() if d in date_set]
        remaining=2*len(dates)-len(active)
        elapsed=time.monotonic()-start;rate=elapsed/max(new,1)
        report=dict(state=state,pid=os.getpid(),updated_at_utc=datetime.now(timezone.utc).isoformat(),
                    first_day=dates[0],last_day=dates[-1],planned_responses=2*len(dates),completed_responses=len(active),
                    remaining_responses=remaining,new_downloads=new,reused_responses=cached,current=current,
                    elapsed_seconds=round(elapsed,1),estimated_remaining_minutes=round(remaining*rate/60,1) if new>3 else None,
                    failed=failures,collection_2025_authorized=True,model_fit=False,model_evaluation=False,
                    channels={c:dict(responses=sum(r['channel']==c for r in active),numeric_days=sum(r['channel']==c and r['numeric_cells']>0 for r in active)) for c in aliases})
        write_json(BASE/'progress.json',report);return report
    date_set=set(dates)
    try:
      with process_lock(BASE/'collector.lock'):
        progress('collecting')
        for day in dates:
          for channel in aliases:
            if (BASE/'STOP').exists():print(json.dumps(progress('stopped')));return
            key=(channel,day);path=BASE/'raw'/channel/day[:4]/(day+'.json.gz');path.parent.mkdir(parents=True,exist_ok=True)
            if key in records and path.exists() and sha(path)==records[key]['gzip_sha256']:continue
            old=OLD/'recent_archive'/channel/'raw'/day[:4]/(day+'.json.gz')
            probe=BASE/'probes'/channel/(day+'.json.gz')
            source=old if old.exists() else probe if probe.exists() else None
            raw=None;origin=None
            if source is not None:
                raw=gzip.decompress(source.read_bytes());origin=str(source.relative_to(ROOT)).replace('\\','/');cached+=1
            else:
              for attempt in range(4):
                try:
                  delay=1-(time.monotonic()-last)
                  if delay>0:time.sleep(delay)
                  last=time.monotonic()
                  if channel=='legacy':r=session.get(ORIGIN+'/api/vrain/private/v1/groups/29/stats/details',params={'from':day,'to':day},timeout=(10,60))
                  else:r=session.get(ORIGIN+'/api/kttv/private/v1/organizations/details',params={'from':day,'to':day,'i':'_1h'},headers={'x-org-uuid':org},timeout=(10,60))
                  if r.status_code in (401,403):print(json.dumps(progress('login_required')));return
                  if r.status_code==429:progress('rate_limit_wait');time.sleep(30);continue
                  r.raise_for_status();raw=r.content;origin='authenticated_'+channel;new+=1;break
                except Exception as exc:
                  if attempt==3:failures.append(dict(day=day,channel=channel,error_type=type(exc).__name__))
                  else:time.sleep(min(2**attempt,4))
            if raw is None:
                progress('collecting');continue
            parsed=parse_day(json.loads(raw),day,aliases[channel],ids)
            compressed=gzip.compress(raw,compresslevel=6,mtime=0)
            temp=path.with_name(path.name+'.part');temp.write_bytes(compressed);temp.replace(path)
            record=dict(channel=channel,day=day,origin=origin,retrieved_or_reused_at_utc=datetime.now(timezone.utc).isoformat(),
                        raw_sha256=__import__('hashlib').sha256(raw).hexdigest(),gzip_sha256=sha(path),bytes=len(compressed),**parsed['metadata'])
            database.execute('INSERT OR REPLACE INTO responses VALUES (?,?,?)',(channel,day,json.dumps(record)));database.commit();records[key]=record
            if len(records)%20==0:print(json.dumps(progress('collecting',channel+':'+day)),flush=True)
            else:progress('collecting',channel+':'+day)
        print(json.dumps(progress('complete' if not failures else 'incomplete')),flush=True)
    finally:database.close()


if __name__=='__main__':main()
