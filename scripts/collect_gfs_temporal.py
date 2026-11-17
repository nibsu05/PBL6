"""Resume temporal GFS extraction in a new cache, preserving all old sources."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime,timezone
import hashlib
import json
import os
import time
import numpy as np
import pandas as pd
import requests
from src.gfs_temporal import (BASE,PUBLIC,OLD,UPDATE,RAIN_LEADS,MET_LEADS,NEW_RAIN,NEW_MET,
    sha,write_json,protocol,load_protocol,eligible_source,select_records,temporal_summaries)
from src.gfs_station import MET_FIELDS,parse_index,range_groups,regular_grid_weights
from scripts.collect_gfs_station_pilot import BUCKET,range_bytes,decode,DECODE_LOCK

def index(session,day,lead):
    relative=Path('indexes')/day/f'f{lead:03}.json'
    for base in (BASE,OLD,UPDATE):
        path=base/relative
        if path.exists():
            saved=json.loads(path.read_text())
            if hashlib.sha256(saved['text'].encode()).hexdigest()!=saved['sha256']:raise ValueError('Index SHA mismatch')
            return saved
    filename=f'gfs.t00z.pgrb2.0p25.f{lead:03}'
    for layout in ('atmos/',''):
        url=f'{BUCKET}gfs.{day}/00/{layout}{filename}'
        r=session.get(url+'.idx',timeout=(15,45))
        if r.status_code==404:continue
        r.raise_for_status()
        if not r.text.startswith('1:'):raise ValueError('Unexpected index response')
        saved=dict(url=url,text=r.text,sha256=hashlib.sha256(r.text.encode()).hexdigest())
        write_json(BASE/relative,saved);return saved
    raise ValueError('Index unavailable in both archive layouts')

def cache_day(day,registry,indices,weights,signature):
    path=BASE/'days'/f'{day}.npz';manifest=path.with_suffix('.json')
    if manifest.exists():
        info=json.loads(manifest.read_text())
        if info['signature']!=signature or sha(path)!=info['sha256']:raise ValueError('Temporal day cache mismatch')
        return info
    oldbase=OLD if (OLD/'days'/f'{day}.npz').exists() else UPDATE
    oldpath=oldbase/'days'/f'{day}.npz';oldinfo=json.loads(oldpath.with_suffix('.json').read_text())
    if sha(oldpath)!=oldinfo['sha256']:raise ValueError('Original cache SHA mismatch')
    z=np.load(oldpath)
    order={s:i for i,s in enumerate(z['station_ids'])};take=[order[s] for s in registry.canonical_id]
    rain=np.full((13,len(registry)),np.nan,'float32');met=np.full((9,len(registry),5),np.nan,'float32');quantum=np.full(13,np.nan)
    for k,lead in enumerate((12,36,60,84)):
        j=RAIN_LEADS.index(lead);rain[j]=z['cumulative_mm'][k,take];quantum[j]=z['packing_quantums'][k]
    for k,lead in enumerate((24,48,72)):met[MET_LEADS.index(lead)]=z['met'][k,take]
    messages=[];transferred=0
    with requests.Session() as session:
        session.headers['User-Agent']='PBL6-temporal-GFS-research/1.0'
        for lead in sorted(NEW_RAIN):
            part=BASE/'parts'/day/f'f{lead:03}.npz';partinfo=part.with_suffix('.json')
            if part.exists() and partinfo.exists():
                info=json.loads(partinfo.read_text())
                if info['signature']!=signature or sha(part)!=info['sha256']:raise ValueError('Partial cache checksum mismatch')
                fields=np.load(part)
            else:
                saved=index(session,day,lead);chosen=select_records(parse_index(saved['text']),lead)
                values={};leadmessages=[];nbytes=0
                for group in range_groups(chosen):
                    first,last=group[0][1].start,group[-1][1].stop
                    data,modified=range_bytes(session,saved['url'],first,last);nbytes+=len(data)
                    for name,record in group:
                        raw=data[record.start-first:record.stop-first+1]
                        with DECODE_LOCK:sampled,meta=decode(raw,name,day,lead,indices,weights)
                        meta.update(name=name,source_url=saved['url'],range=[record.start,record.stop],
                                    source_last_modified=modified,index_sha256=saved['sha256'],index_level=record.level)
                        values[name]=sampled;leadmessages.append(meta)
                part.parent.mkdir(parents=True,exist_ok=True);tmp=part.with_suffix('.tmp.npz')
                np.savez_compressed(tmp,**values);tmp.replace(part)
                info=dict(signature=signature,sha256=sha(part),messages=leadmessages,transferred_bytes=nbytes)
                write_json(partinfo,info);fields=values
            messages.extend(info['messages']);transferred+=info['transferred_bytes']
            j=RAIN_LEADS.index(lead);rain[j]=fields['rain_cumulative']
            quantum[j]=next(m['packing_quantum'] for m in info['messages'] if m['name']=='rain_cumulative')
            if lead in NEW_MET:
                for k,name in enumerate(MET_FIELDS):met[MET_LEADS.index(lead),:,k]=fields[name]
        features,clipped=temporal_summaries(rain,quantum,met)
        if len(messages)!=39:raise ValueError('Expected39 new GRIB messages')
        path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp.npz')
        np.savez_compressed(tmp,station_ids=registry.canonical_id.to_numpy(str),cumulative_mm=rain,
            packing_quantums=quantum,met=met,features=features,negative_rounding_clipped=clipped)
        tmp.replace(path)
        info=dict(day=day,signature=signature,sha256=sha(path),original_cache=str(oldpath.relative_to(ROOT)),
            original_sha256=sha(oldpath),messages=messages,transferred_bytes=transferred,
            rounding_clipped=int(clipped.sum()),actual_historical_release_availability_proven=False)
        write_json(manifest,info);return info

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workers',type=int,default=8)
    parser.add_argument('--probe',action='store_true');parser.add_argument('--initialize',action='store_true');args=parser.parse_args()
    if not 1<=args.workers<=32:raise ValueError('workers outside1..32')
    BASE.mkdir(parents=True,exist_ok=True);PUBLIC.mkdir(parents=True,exist_ok=True)
    if not (PUBLIC/'protocol.json').exists():
        write_json(PUBLIC/'protocol.json',protocol());write_json(BASE/'protocol_lock.json',dict(sha256=sha(PUBLIC/'protocol.json')))
    p=load_protocol()
    registry=pd.read_csv(OLD/'cohort_private.csv').sort_values('canonical_id').reset_index(drop=True)
    signature=hashlib.sha256((registry[['canonical_id','latitude','longitude']].to_json(orient='records',double_precision=15)+json.dumps([RAIN_LEADS,MET_LEADS])).encode()).hexdigest()
    registry.to_csv(BASE/'registry_private.csv',index=False)
    indices,weights=regular_grid_weights(registry.latitude.to_numpy(),registry.longitude.to_numpy())
    f=eligible_source();dates=sorted(f.gfs_init_utc.dt.strftime('%Y%m%d').unique())
    write_json(BASE/'collection_plan.json',dict(days=dates,count=len(dates),signature=signature,protocol_sha256=sha(PUBLIC/'protocol.json')))
    if args.initialize:return
    if args.probe:dates=[d for d in ['20210108','20220401','20240101','20250101','20261112'] if d in dates]
    start=time.monotonic();results={};errors={}
    def progress(state):
        write_json(BASE/('probe_progress.json' if args.probe else 'collection_progress.json'),dict(state=state,pid=os.getpid(),
            updated_utc=datetime.now(timezone.utc).isoformat(),planned=len(dates),completed=len(results),failed=len(errors),errors=errors,
            transferred_bytes=sum(r['transferred_bytes'] for r in results.values()),elapsed_seconds=round(time.monotonic()-start,1)))
    def retry(day):
        for attempt in range(4):
            try:return cache_day(day,registry,indices,weights,signature)
            except Exception:
                if attempt==3:raise
                time.sleep(min(2**attempt,4))
    progress('collecting')
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(retry,day):day for day in dates}
        for future in as_completed(futures):
            day=futures[future]
            try:results[day]=future.result()
            except Exception as exc:errors[day]=f'{type(exc).__name__}: {exc}'
            progress('collecting')
            if (len(results)+len(errors))%20==0 or args.probe:print(json.dumps(dict(completed=len(results),failed=len(errors),day=day)),flush=True)
    progress('complete' if not errors else 'incomplete')
    if errors:raise RuntimeError(json.dumps(errors))

if __name__=='__main__':main()
