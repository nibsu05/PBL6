"""Isolated daily-v2 collector; uses the verified pilot HTTP/GRIB decoder."""
from pathlib import Path
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import json
import os
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from src.gfs_daily import BASE,PUBLIC,VRAIN,load_protocol,write_json,sha
from src.gfs_station import MET_FIELDS,RAIN_LEADS,MET_LEADS,regular_grid_weights
from src.vrain_download import process_lock
from scripts import collect_gfs_station_pilot as collector


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workers',type=int,default=8)
    args=parser.parse_args()
    if not 1<=args.workers<=8:raise ValueError('Use 1..8 HTTP workers')
    p=load_protocol();collector.BASE=BASE
    registry=pd.read_csv(VRAIN/'handoff_v1/station_registry_private.csv')
    registry=registry[registry.legacy_id.notna()].sort_values('canonical_id').reset_index(drop=True)
    signature=sha_registry=(collector.sha((registry[['canonical_id','latitude','longitude']].to_json(orient='records',double_precision=15)
                              +json.dumps(MET_FIELDS)+str(RAIN_LEADS)+str(MET_LEADS)).encode()))
    registry.to_csv(BASE/'registry_private.csv',index=False)
    indices,weights=regular_grid_weights(registry.latitude.to_numpy(),registry.longitude.to_numpy())
    dates=pd.date_range(p['first_issue_day'],p['last_issue_day'],freq='D').strftime('%Y%m%d').tolist()
    started=time.monotonic();results={};errors={};new_bytes=0;cached=0
    def progress(state):
        missing=len(dates)-len(results)-len(errors)
        value=dict(state=state,pid=os.getpid(),updated_utc=datetime.now(timezone.utc).isoformat(),
            planned_issues=len(dates),completed_issues=len(results),failed_issues=len(errors),remaining_issues=missing,
            cadence_days=1,new_transferred_bytes=new_bytes,reused_issues=cached,
            elapsed_seconds=round(time.monotonic()-started,1),errors=errors,test2025_read=False)
        write_json(BASE/'progress.json',value)
        return value
    def retry(day):
        was_cached=(BASE/'days'/(day+'.npz')).exists()
        for attempt in range(4):
            try:return collector.collect_day(day,registry,indices,weights,signature),was_cached
            except Exception:
                if attempt==3:raise
                time.sleep(min(2**attempt,4))
    with process_lock(BASE/'collector.lock'):
        progress('collecting')
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            tasks={pool.submit(retry,day):day for day in dates}
            for future in as_completed(tasks):
                day=tasks[future]
                try:
                    record,was_cached=future.result();results[day]=record
                    if was_cached:cached+=1
                    else:new_bytes+=record['transferred_bytes']
                except Exception as exc:errors[day]=f'{type(exc).__name__}: {str(exc)[:200]}'
                value=progress('collecting')
                if (len(results)+len(errors))%10==0 or errors:
                    print(json.dumps({k:v for k,v in value.items() if k!='errors'}),flush=True)
        write_json(BASE/'collection_manifest.json',dict(planned_dates=dates,completed_dates=sorted(results),errors=errors,station_signature=signature))
        value=progress('complete' if not errors else 'incomplete')
        write_json(PUBLIC/'collection_summary.json',{k:v for k,v in value.items() if k!='errors'})
        print(json.dumps(value),flush=True)
        if errors:raise SystemExit(1)


if __name__=='__main__':main()
