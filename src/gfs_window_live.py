"""Timestamped live inputs and immutable pre-issue forecasts; no historical replay as live."""
from __future__ import annotations

from datetime import datetime
import gzip
import hashlib
import json
import math
import re
import time
import uuid

import numpy as np
import pandas as pd
import requests

from src.gfs_window import ROOT, BASE, PUBLIC, VRAIN, OLD, FEATURES, now, sha, write_json, read_json, save_parquet
from src.vrain_download import load_session, process_lock
from src.vrain_station_hours import current_modern_aliases, fetch_station_hours, fetch_station_inventory
from src.gfs_station import (RAIN_LEADS,MET_LEADS,MET_FIELDS,choose_records,parse_index,
    range_groups,regular_grid_weights,rainfall_windows)
from src.gfs_daily import gauge_history
from src.gfs_station_dataset import forecast_met,add_calendar
from scripts.collect_gfs_station_pilot import BUCKET,range_bytes,decode,DECODE_LOCK

CLOCK=re.compile(r'^(\d{2}):(\d{2}) (\d{2})/(\d{2})$')


def parse_live_day(payload,day,aliases,station_ids):
    """Same source/QC rules as station_archive_update.parse_day, without its old date fence.

    A partial current day is retained, never zero-filled; complete-day sum mismatch
    invalidates that station-day. The paged report may end in a reading from the
    hour still in progress. That reading stays in the raw response for auditing.
    """
    marked=pd.Timestamp(day);times=pd.date_range(marked-pd.Timedelta(hours=4),periods=24,freq='h')
    if not isinstance(payload,dict) or not isinstance(payload.get('stats'),list):raise ValueError('Invalid daily schema')
    pos={s:i for i,s in enumerate(station_ids)};values=np.full((24,len(pos)),np.nan);total=np.full(len(pos),np.nan)
    seen_times=set();summaries=0;membership=None
    for row_number, row in enumerate(payload['stats']):
        if not isinstance(row,dict) or not isinstance(row.get('stations'),list):raise ValueError('Invalid source row')
        match=CLOCK.fullmatch(row.get('timePoint','').strip());index=None
        if match:
            hh,mm,dd,month=map(int,match.groups())
            if hh>23:raise ValueError('Invalid source clock')
            possible=[]
            for year in (marked.year-1,marked.year,marked.year+1):
                try:possible.append(pd.Timestamp(datetime(year,month,dd,hh,mm)))
                except ValueError:pass
            if not possible:raise ValueError('Invalid source date')
            tick=min(possible,key=lambda t:abs(t-marked))
            if mm:
                # Accept only the terminal partial row backed by the local timestamp
                # supplied by the paged endpoint, inside this report's hour bins.
                stamp=row.get('ts')
                if (row_number!=len(payload['stats'])-1 or not isinstance(stamp,str)
                        or pd.Timestamp(stamp)!=tick or tick.ceil('h') not in times
                        or any(previous>=tick for previous in seen_times)):
                    raise ValueError('Invalid partial source clock')
                continue
            if tick not in times or tick in seen_times:raise ValueError('Duplicate/shifted clock')
            seen_times.add(tick);index=times.get_loc(tick)
        else:
            if not row.get('timePoint') or re.match(r'^\d{2}:',row['timePoint']):raise ValueError('Malformed clock')
            summaries+=1
        members=set()
        for item in row['stations']:
            sid=str(item.get('id'))
            if sid not in aliases or aliases[sid] not in pos:raise ValueError('Unknown station alias; registry review required')
            canonical=aliases[sid]
            if canonical in members:raise ValueError('Duplicate station')
            members.add(canonical);value=item.get('depth')
            if isinstance(value,str) and value.strip()=='-':continue
            if value is None or isinstance(value,bool):raise ValueError('Invalid rain value')
            value=float(value)
            if not math.isfinite(value) or value<0:raise ValueError('Invalid rain range')
            if index is None:total[pos[canonical]]=value
            else:values[index,pos[canonical]]=value
        if membership is None:membership=members
        elif membership!=members:raise ValueError('Source membership changes within daily response')
    # The live endpoint returns only the hourly rows already released today.
    # Missing clocks stay NaN; historical truth still requires all24 valid bins.
    if summaries!=1:raise ValueError('Need exactly one daily summary')
    complete=np.isfinite(values).all(0)
    bad=complete & np.isfinite(total) & (abs(values.sum(0)-total)>1e-6)
    return dict(raw=values.astype('float32'),valid=np.isfinite(values)&~bad[None,:],times=times,bad=bad)


def source_context(inventory=None):
    registry=pd.read_csv(VRAIN/'station_registry_private.csv',dtype={'legacy_id':str,'modern_id':str},
        float_precision='round_trip')
    aliases={c:dict(zip(registry.loc[registry[c+'_id'].notna(),c+'_id'],registry.loc[registry[c+'_id'].notna(),'canonical_id'])) for c in ('legacy','modern')}
    groups=read_json(VRAIN/'groups_modern_current_private.json')
    group=[g for g in groups if any(int(s.get('groupId',-1))==29 for s in g.get('stats',[]))]
    if len(group)!=1 or not group[0].get('groupOrgUuid'):raise ValueError('Authorized organization absent')
    organization=group[0]['groupOrgUuid']
    if inventory is not None:
        aliases['modern']=current_modern_aliases(registry,inventory,organization)
    return registry,aliases,organization


def load_live_sources(session):
    try:
        return source_context(fetch_station_inventory(session))
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code in (401,403):
            raise PermissionError('Vrain session requires renewal') from error
        raise


def fetch_gauge(session,org,channel,day,directory):
    started=now()
    try:
        payload,raw=fetch_station_hours(session,day,channel,org,timeout=(15,45))
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code in (401,403):
            raise PermissionError('Vrain session requires renewal') from error
        raise
    received=now()
    # Keep the unmodified pages as well as the normalized table used for QC.
    source_pages=[]
    for index,page in enumerate(raw,1):
        source=directory/f'{channel}_{day}.page{index}.json.gz'
        source.write_bytes(gzip.compress(page))
        source_pages.append(dict(file=source.name,sha256=sha(source)))
    path=directory/f'{channel}_{day}.json.gz'
    path.write_bytes(gzip.compress(json.dumps(payload,ensure_ascii=False).encode('utf-8')))
    record=dict(channel=channel,day=day,request_started_utc=started,retrieved_utc=received,
        http_status=200,sha256=sha(path),file=path.name,route='paged_web',source_pages=source_pages)
    return payload,record


def fetch_gfs(day,cohort,directory):
    """Fetch the19 original fields and record actual successful retrieval times."""
    indices,weights=regular_grid_weights(cohort.latitude.to_numpy(),cohort.longitude.to_numpy())
    rain=np.full((4,len(cohort)),np.nan,'float32');met=np.full((3,len(cohort),5),np.nan,'float32');quantums=np.zeros(4)
    messages=[]
    with requests.Session() as session:
        session.headers['User-Agent']='PBL6-prospective-rainfall/1.0'
        for lead in sorted(RAIN_LEADS+MET_LEADS):
            filename=f'gfs.t00z.pgrb2.0p25.f{lead:03}'
            url=BUCKET+'gfs.'+day+'/00/atmos/'+filename
            response=session.get(url+'.idx',timeout=(15,45));response.raise_for_status()
            if not response.text.startswith('1:'):raise ValueError('Unexpected GFS index')
            text=response.text;index_sha=hashlib.sha256(text.encode()).hexdigest()
            (directory/f'f{lead:03}.idx').write_text(text,encoding='utf-8',newline='\n')
            selected=choose_records(parse_index(text),lead)
            for group in range_groups(selected):
                first,last=group[0][1].start,group[-1][1].stop
                data,modified=range_bytes(session,url,first,last);retrieved=now()
                for name,record in group:
                    message=data[record.start-first:record.stop-first+1]
                    with DECODE_LOCK:sampled,meta=decode(message,name,day,lead,indices,weights)
                    meta.update(name=name,retrieved_utc=retrieved,source_last_modified=modified,index_sha256=index_sha)
                    messages.append(meta)
                    if name=='rain_cumulative':
                        i=RAIN_LEADS.index(lead);rain[i]=sampled;quantums[i]=meta['packing_quantum']
                    else:met[MET_LEADS.index(lead),:,list(MET_FIELDS).index(name)]=sampled
    daily,clipped=rainfall_windows(rain,quantums)
    path=directory/'gfs_station_inputs.npz'
    np.savez_compressed(path,station_ids=cohort.canonical_id.to_numpy(str),rain_day_mm=daily,
        met=met,met_names=np.array(list(MET_FIELDS)),cumulative_mm=rain,packing_quantums=quantums)
    return dict(rain_day_mm=daily,met=met,met_names=list(MET_FIELDS)),dict(messages=messages,sha256=sha(path),file=path.name,rounding_clipped=int(clipped.sum()))


def input_frame(issue,registry,cohort,parsed,gfs,retrieved):
    """Only observed intervals ending<=18h local may be inputs for19h issue."""
    dates=pd.date_range(issue.tz_convert('Asia/Ho_Chi_Minh').normalize().tz_localize(None)-pd.Timedelta(days=7),periods=8)
    pos={s:i for i,s in enumerate(registry.canonical_id)};rows=[]
    clean={}
    cutoff=issue-pd.Timedelta(hours=1)
    for channel in ('legacy','modern'):
        pieces=[]
        for day in dates:
            p=parsed[(channel,day.strftime('%Y-%m-%d'))]
            good=p['valid'].copy()
            clocks=p['times'].tz_localize('Asia/Ho_Chi_Minh').tz_convert('UTC')
            good[clocks>min(cutoff,retrieved)]=False
            pieces.append(np.where(good,p['raw'],np.nan))
        clean[channel]=np.stack(pieces)
    conflict=np.isfinite(clean['legacy'])&np.isfinite(clean['modern'])&(abs(clean['legacy']-clean['modern'])>1e-6)
    for channel in clean:clean[channel][conflict]=np.nan
    terrain=pd.read_csv(OLD/'cohort_private.csv').set_index('canonical_id')
    for gi,station in enumerate(cohort.itertuples()):
        si=pos[station.canonical_id]
        selected=None
        for channel in ('legacy','modern'):
            values=clean[channel];history=gauge_history(values.reshape(-1,len(registry)),values.sum(1),7,si,1)
            if np.isfinite(list(history.values())).all():selected=(channel,history);break
        if selected is None:continue
        channel,history=selected
        static={n:float(terrain.loc[station.canonical_id,n]) for n in FEATURES['N3'] if n.startswith('dem_')}
        for h in (1,2,3):
            end=issue+pd.Timedelta(hours=24*h)
            met=forecast_met(gfs['met_names'],gfs['met'][h-1,gi])
            rows.append(dict(station_id=station.canonical_id,station_code=int(station.canonical_id[2:])-1,
                latitude=station.latitude,longitude=station.longitude,gauge_namespace=channel,issue_utc=issue,
                gfs_init_utc=issue.normalize(),target_start_utc=issue+pd.Timedelta(hours=24*(h-1)),target_end_utc=end,
                observation_cutoff_utc=cutoff,horizon=h,**history,**static,**met,**add_calendar(end),gfs_rain_mm=float(gfs['rain_day_mm'][h-1,gi])))
    frame=pd.DataFrame(rows)
    if len(frame) and not np.isfinite(frame[FEATURES['N3']].to_numpy()).all():raise ValueError('Invalid live features')
    return frame


def assert_preissue(issue,input_received,recorded):
    issue=pd.Timestamp(issue);recorded=pd.Timestamp(recorded)
    if recorded>=issue:raise ValueError('Too late for prospective issue; retrospective replay forbidden')
    if any(pd.Timestamp(t)>recorded for t in input_received):raise ValueError('Input snapshot is from the future')


def record_issue(day):
    from scripts.run_gfs_window import check_freeze,predict_frame
    check_freeze()
    issue=pd.Timestamp(day,tz='UTC')+pd.Timedelta(hours=12)
    assert_preissue(issue,[],now())
    root=BASE/'live';root.mkdir(exist_ok=True)
    dest=root/'issuances'/issue.strftime('%Y%m%dT%H%M%SZ')
    if dest.exists():raise FileExistsError('Immutable issuance already exists')
    attempt=root/'attempts'/(pd.Timestamp.now(tz='UTC').strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:8]);attempt.mkdir(parents=True)
    parsed={};records=[]
    with process_lock(root/'record.lock'):
        try:
            session=load_session(VRAIN/'session.dpapi')
            registry,aliases,org=load_live_sources(session);ids=registry.canonical_id.tolist()
            cohort=registry[registry.canonical_id.isin(pd.read_csv(OLD/'cohort_private.csv').canonical_id)].sort_values('canonical_id').reset_index(drop=True)
            gfs,gfs_record=fetch_gfs(issue.strftime('%Y%m%d'),cohort,attempt)
            dates=pd.date_range(pd.Timestamp(day)-pd.Timedelta(days=7),pd.Timestamp(day)).strftime('%Y-%m-%d')
            for d in dates:
                for channel in ('legacy','modern'):
                    payload,record=fetch_gauge(session,org,channel,d,attempt)
                    parsed[(channel,d)]=parse_live_day(payload,d,aliases[channel],ids);records.append(record);time.sleep(1)
            received=max(pd.Timestamp(r['retrieved_utc']) for r in records)
            frame=input_frame(issue,registry,cohort,parsed,gfs,received)
            if frame.empty:raise ValueError('No station has complete same-channel live inputs')
            out,_=predict_frame(frame)
            save_parquet(frame,attempt/'inputs_private.parquet');save_parquet(out,attempt/'predictions_private.parquet')
            recorded=now();all_received=[r['retrieved_utc'] for r in records]+[r['retrieved_utc'] for r in gfs_record['messages']]
            assert_preissue(issue,all_received,recorded)
            manifest=dict(status='recorded_before_issue',recorded_utc=recorded,issue_utc=str(issue),
                input_available_at='actual successful retrieval times, not archive Last-Modified',
                station_count=int(frame.station_id.nunique()),candidate_stations=57,rows=len(frame),
                model_freeze_sha256=sha(BASE/'model_freeze.json'),forecast_sha256=sha(attempt/'predictions_private.parquet'),
                input_sha256=sha(attempt/'inputs_private.parquet'),gauge_sources=records,gfs_source=gfs_record,
                truth_seen=False,truth_due_utc=str(issue+pd.Timedelta(hours=72)),
                selected_case=read_json(PUBLIC/'model_catalog.json')['selected_prospective_case'],
                labels='three future24h station amounts; no regional aggregation')
            write_json(attempt/'issuance.json',manifest)
            dest.parent.mkdir(exist_ok=True);attempt.rename(dest)
            write_json(root/'status.json',dict(stage='issued',issue_utc=str(issue),recorded_utc=recorded,stations=manifest['station_count'],truth_pending=True))
            return manifest
        except Exception as exc:
            # Public/private status contains error type, no response bodies or credentials.
            record=dict(status='not_issued',issue_utc=str(issue),recorded_utc=now(),error_type=type(exc).__name__)
            write_json(attempt/'attempt.json',record);write_json(root/'status.json',record)
            raise


def probe():
    """One current successful/failed retrieval is evidence of availability now only."""
    directory=BASE/'live/probes'/(pd.Timestamp.now(tz='UTC').strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:8])
    directory.mkdir(parents=True)
    session=load_session(VRAIN/'session.dpapi')
    registry,aliases,org=load_live_sources(session);day=pd.Timestamp.now(tz='Asia/Ho_Chi_Minh').strftime('%Y-%m-%d')
    rows=[]
    for channel in ('legacy','modern'):
        try:
            payload,r=fetch_gauge(session,org,channel,day,directory)
            p=parse_live_day(payload,day,aliases[channel],registry.canonical_id.tolist())
            when=p['times'].tz_localize('Asia/Ho_Chi_Minh').tz_convert('UTC')
            seen=p['valid'].any(1)&(when<=pd.Timestamp(r['retrieved_utc']))
            latest=when[seen].max() if seen.any() else None
            rows.append(dict(source=channel,status='retrieved',retrieved_utc=r['retrieved_utc'],
                latest_observed_hour_end_utc=str(latest) if latest is not None else None,
                stations_with_any_hours=int(p['valid'][seen].any(0).sum()) if seen.any() else 0,
                most_recent_hour_lag_minutes=float((pd.Timestamp(r['retrieved_utc'])-latest).total_seconds()/60) if latest is not None else None,
                interpretation='one snapshot; not a measured long-term latency distribution'))
        except Exception as exc:rows.append(dict(source=channel,status='failed',error_type=type(exc).__name__,retrieved_utc=now()))
        time.sleep(1)
    day_utc=pd.Timestamp.now(tz='UTC').strftime('%Y%m%d')
    url=BUCKET+'gfs.'+day_utc+'/00/atmos/gfs.t00z.pgrb2.0p25.f084.idx'
    try:
        response=requests.get(url,timeout=(15,40));rows.append(dict(source='GFS_current00UTC_f084_index',status='retrieved' if response.status_code==200 else 'not_available',http_status=response.status_code,retrieved_utc=now()))
    except Exception as exc:rows.append(dict(source='GFS_current00UTC_f084_index',status='failed',error_type=type(exc).__name__,retrieved_utc=now()))
    report=dict(probed_utc=now(),snapshots=rows,next_issue_utc=str(pd.Timestamp(day,tz='UTC')+pd.Timedelta(hours=12)),
        forecast_issued=False,prospective_verification_completed=False)
    write_json(directory/'probe.json',report);write_json(PUBLIC/'live_availability_snapshot.json',report)
    return report


def verify_due():
    """Observe future truth only after all three windows close; never refit models."""
    from src.gfs_final_metrics import summary_tables
    session=load_session(VRAIN/'session.dpapi')
    registry,aliases,org=load_live_sources(session)
    results=[]
    for folder in sorted((BASE/'live/issuances').glob('*')):
        manifest=read_json(folder/'issuance.json')
        if pd.Timestamp.now(tz='UTC')<pd.Timestamp(manifest['truth_due_utc'])+pd.Timedelta(hours=1):continue
        truth_dir=BASE/'live/verification'/folder.name
        if truth_dir.exists():continue
        truth_dir.mkdir(parents=True);f=pd.read_parquet(folder/'predictions_private.parquet')
        issue=pd.Timestamp(manifest['issue_utc']);start=issue.tz_convert('Asia/Ho_Chi_Minh').normalize().tz_localize(None)
        days=pd.date_range(start+pd.Timedelta(days=1),periods=3).strftime('%Y-%m-%d');parsed={};sources=[]
        for day in days:
            for channel in ('legacy','modern'):
                payload,r=fetch_gauge(session,org,channel,day,truth_dir)
                parsed[(channel,day)]=parse_live_day(payload,day,aliases[channel],registry.canonical_id.tolist());sources.append(r);time.sleep(1)
        pos={s:i for i,s in enumerate(registry.canonical_id)};values=[]
        for row in f.itertuples():
            d=days[row.horizon-1];p=parsed[(row.gauge_namespace,d)];other=parsed[('modern' if row.gauge_namespace=='legacy' else 'legacy',d)]
            i=pos[row.station_id];valid=p['valid'][:,i].copy()
            conflict=valid&other['valid'][:,i]&(abs(p['raw'][:,i]-other['raw'][:,i])>1e-6)
            valid[conflict]=False
            values.append(float(p['raw'][:,i].sum()) if valid.all() else np.nan)
        f['y_mm']=values;f['evaluation_set']='prospective';save_parquet(f,truth_dir/'verified_private.parquet')
        valid=f[np.isfinite(f.y_mm)].copy();packs=valid.groupby(['station_id','issue_utc']).horizon.nunique()
        complete=set(packs[packs.eq(3)].index);valid=valid[[x in complete for x in zip(valid.station_id,valid.issue_utc)]]
        if len(valid):
            c=pd.read_csv(PUBLIC/'cutoffs.csv');cutoffs={(r.model,int(r.horizon)):float(r.cutoff) for r in c.itertuples()}
            tables=summary_tables(valid,['A','B','C','D','GFS','MOS_LONG'],cutoffs)
            for key,table in tables.items():
                # First reports aggregate independent issue counts; per-station details stay private.
                table.to_csv(truth_dir/(key+'.csv'),index=False)
        report=dict(status='truth_observed',verified_utc=now(),issue_utc=str(issue),forecast_rows=len(f),valid_common_rows=len(valid),
            forecast_sha256=manifest['forecast_sha256'],labels_after_forecast=True,sources=sources,
            scientific_skill_conclusion='one issue is insufficient; accumulate independent weather events')
        write_json(truth_dir/'verification.json',report);results.append(report)
    return dict(verified_issues=len(results),completed_utc=now())
