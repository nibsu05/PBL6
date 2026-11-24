"""Extend verified GFS fields to 2025--2026 without changing frozen collectors."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import sys,json,time,os,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd
from src.station_archive_update import BASE,OLD,issue_contract,write_json
from src.gfs_station import regular_grid_weights,MET_FIELDS,RAIN_LEADS,MET_LEADS
from src.vrain_download import process_lock
from scripts import collect_gfs_station_pilot as collector


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers',type=int,default=8);parser.add_argument('--limit',type=int)
    args=parser.parse_args()
    if not 1<=args.workers<=8:raise ValueError('Use 1..8 workers')
    folder=BASE/'gfs';folder.mkdir(parents=True,exist_ok=True);(folder/'days').mkdir(exist_ok=True)
    registry=pd.read_csv(BASE/'station_registry_private.csv').sort_values('canonical_id').reset_index(drop=True)
    signature=collector.sha((registry[['canonical_id','latitude','longitude']].to_json(orient='records',double_precision=15)+json.dumps(MET_FIELDS)+str(RAIN_LEADS)+str(MET_LEADS)).encode())
    registry.to_csv(folder/'registry_private.csv',index=False)
    # The verified decoder has dependency injection via module globals. Override
    # only in this isolated process; the older module/file/contract is untouched.
    collector.BASE=folder;collector.issue_contract=issue_contract
    indices,weights=regular_grid_weights(registry.latitude.to_numpy(),registry.longitude.to_numpy())
    dates=pd.date_range('2024-12-29','2026-11-12').strftime('%Y%m%d').tolist()
    # Newest first supplies a quick source check; every fixed date is still used.
    dates=list(reversed(dates))
    if args.limit:dates=dates[:args.limit]
    start=time.monotonic();results={};errors={};new_bytes=0;reused=0
    def progress(state):
        n=len(results);elapsed=time.monotonic()-start;remaining=len(dates)-n-len(errors)
        record=dict(state=state,pid=os.getpid(),updated_at_utc=datetime.now(timezone.utc).isoformat(),
                    planned_issues=len(dates),completed_issues=n,failed_issues=len(errors),remaining_issues=remaining,
                    station_count=len(registry),elapsed_seconds=round(elapsed,1),new_transferred_bytes=new_bytes,
                    reused_issues=reused,estimated_remaining_minutes=round(remaining*elapsed/max(n-reused,1)/60,1) if n-reused>3 else None,
                    errors=errors,collection_2025_authorized=True,training_run=False,model_evaluation=False)
        write_json(folder/'progress.json',record);return record
    def fetch(day):
        cached=(folder/'days'/(day+'.npz')).exists()
        for attempt in range(4):
            try:return collector.collect_day(day,registry,indices,weights,signature),cached
            except Exception:
                if attempt==3:raise
                time.sleep(min(2**attempt,4))
    with process_lock(folder/'collector.lock'):
        progress('collecting')
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            tasks={pool.submit(fetch,d):d for d in dates}
            for future in as_completed(tasks):
                day=tasks[future]
                try:
                    r,cached=future.result();results[day]=r
                    if cached:reused+=1
                    else:new_bytes+=r['transferred_bytes']
                except Exception as exc:errors[day]=type(exc).__name__+': '+str(exc)[:180]
                p=progress('collecting')
                if (len(results)+len(errors))%10==0:print(json.dumps(p),flush=True)
        write_json(folder/'collection_manifest.json',dict(planned_dates=sorted(dates),completed_dates=sorted(results),errors=errors,station_signature=signature))
        print(json.dumps(progress('complete' if not errors else 'incomplete')),flush=True)


if __name__=='__main__':main()
