"""Build hourly observations and daily GFS features through November 2026.

Raw data remain private. Channels remain explicit; no model is fit or scored.
"""
from pathlib import Path
import argparse,json,gzip,sqlite3,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from src.station_archive_update import BASE,OUT,PUBLIC,OLD,FIRST,LAST,parse_day,sha,write_json,combine_hourly
from src.gfs_daily import FEATURES,RECENT,gauge_history
from src.gfs_station_dataset import forecast_met,add_calendar


def matrices(registry):
    status=json.loads((BASE/'progress.json').read_text(encoding='utf8'))
    if status['state']!='complete' or status['remaining_responses'] or status['failed']:raise ValueError('Gauge collection not complete')
    lock=json.loads((BASE/'contract_lock.json').read_text(encoding='utf8'))
    assert sha(PUBLIC/'data_contract.json')==lock['sha256']
    days=pd.date_range(FIRST,LAST).as_unit('ns');ids=registry.canonical_id.tolist();n=len(ids);pos={s:j for j,s in enumerate(ids)}
    aliases={c:dict(zip(registry.loc[registry[c+'_id'].notna(),c+'_id'],registry.loc[registry[c+'_id'].notna(),'canonical_id'])) for c in ('legacy','modern')}
    raw=np.full((2,len(days),24,n),np.nan,dtype=np.float32);valid=np.zeros(raw.shape,bool)
    bad=np.zeros((2,len(days),n),bool);queried=np.zeros((2,len(days)),bool)
    old=np.load(OLD/'freeze_work/station_matrices.npz');j=days.get_indexer(pd.DatetimeIndex(old['marked_day']))
    for k,sid in enumerate(old['station_ids']):
        si=pos[aliases['legacy'][str(sid)]]
        raw[0,j,:,si]=old['rain'][:,:,k];valid[0,j,:,si]=old['valid'][:,:,k];bad[0,j,si]=old['bad_daily_sum'][:,k]
    queried[0,j]=True;source_manifest={'old_matrix':sha(OLD/'freeze_work/station_matrices.npz')}
    db=sqlite3.connect(BASE/'manifest.sqlite')
    records={(c,d):json.loads(r) for c,d,r in db.execute('select channel,day,record from responses')};db.close()
    daily_records=[]
    for channel_index,channel in enumerate(('legacy','modern')):
        for di,day in enumerate(days):
            name=day.strftime('%Y-%m-%d')
            if name<'2025-01-01':continue
            path=BASE/'raw'/channel/name[:4]/(name+'.json.gz');record=records[(channel,name)]
            if sha(path)!=record['gzip_sha256']:raise ValueError('Gauge compressed checksum mismatch')
            compressed=path.read_bytes();uncompressed=gzip.decompress(compressed)
            if __import__('hashlib').sha256(uncompressed).hexdigest()!=record['raw_sha256']:raise ValueError('Gauge raw checksum mismatch')
            parsed=parse_day(json.loads(uncompressed),name,aliases[channel],ids)
            raw[channel_index,di]=parsed['raw'];valid[channel_index,di]=parsed['valid'];bad[channel_index,di]=parsed['bad_daily_sum'];queried[channel_index,di]=True
            source_manifest[channel+'/'+name]=record['gzip_sha256']
            if di%100==0:print(json.dumps(dict(stage='parse_gauges',channel=channel,day=name)),flush=True)
        for year in range(2021,2027):
            mask=days.year==year;v=valid[channel_index,mask];r=raw[channel_index,mask]
            complete=v.all(1)
            daily_records.append(dict(year=year,channel=channel,requested_days=int(queried[channel_index,mask].sum()),
                days_with_numeric=int(np.isfinite(r).any((1,2)).sum()),stations_with_numeric=int(np.isfinite(r).any((0,1)).sum()),
                valid_hour_cells=int(v.sum()),expected_hour_cells=int(mask.sum()*24*n),complete_station_days=int(complete.sum()),
                stations_with_complete_days=int(complete.any(0).sum()),bad_sum_station_days=int(bad[channel_index,mask].sum()),
                first_numeric_marked_day=days[mask][np.flatnonzero(np.isfinite(r).any((1,2)))[0]].strftime('%Y-%m-%d') if np.isfinite(r).any() else None,
                last_numeric_marked_day=days[mask][np.flatnonzero(np.isfinite(r).any((1,2)))[-1]].strftime('%Y-%m-%d') if np.isfinite(r).any() else None))
    conflict=valid[0]&valid[1]&(np.abs(raw[0]-raw[1])>1e-6)
    overlap=valid[0]&valid[1]
    overlap_rows=[]
    for year in range(2021,2027):
        mask=days.year==year;b=overlap[mask];c=conflict[mask]
        overlap_rows.append(dict(year=year,overlap_hour_pairs=int(b.sum()),conflicting_hour_pairs=int(c.sum()),
                                 overlap_stations=int(b.any((0,1)).sum()),overlap_days=int(b.any((1,2)).sum()),
                                 wet_overlap_pairs=int((b&(np.maximum(raw[0,mask],raw[1,mask])>0)).sum())))
    pd.DataFrame(daily_records).to_csv(PUBLIC/'coverage_by_year_channel.csv',index=False)
    pd.DataFrame(overlap_rows).to_csv(PUBLIC/'channel_overlap.csv',index=False)
    np.savez_compressed(BASE/'rain_channels.npz',raw=raw,valid=valid,bad_daily_sum=bad,queried=queried,
                        marked_day=days.values,station_ids=np.asarray(ids),conflict=conflict)
    write_json(BASE/'source_checksums.json',source_manifest)
    return days,raw,valid,bad,queried,conflict


def hourly(registry,days,raw,valid,bad,queried,conflict):
    path=OUT/'PBL6_MUA_TRAM_GIO_2021_2026.parquet';temporary=path.with_suffix('.part.parquet')
    writer=None;rows=0;n=len(registry)
    for year in range(2021,2027):
        mask=days.year==year;selected=days[mask]
        # At most one year per Arrow chunk; all nominal bins remain present.
        clocks=pd.date_range(selected[0]-pd.Timedelta(hours=4),periods=len(selected)*24,freq='h',tz='Asia/Ho_Chi_Minh').tz_convert('UTC')
        lraw=raw[0,mask].reshape(-1);mraw=raw[1,mask].reshape(-1)
        lv=valid[0,mask].reshape(-1);mv=valid[1,mask].reshape(-1);cf=conflict[mask].reshape(-1)
        combined,code,independent_cf=combine_hourly(lraw,mraw,lv,mv)
        assert np.array_equal(cf,independent_cf)
        frame=pd.DataFrame(dict(station_id=np.tile(registry.canonical_id.to_numpy(),len(clocks)),
            period_end_utc=np.repeat(clocks,n),source_marked_day=np.repeat(selected.values,24*n),
            legacy_rain_raw_mm=lraw,modern_rain_raw_mm=mraw,
            legacy_rain_qc_mm=np.where(lv,lraw,np.nan),modern_rain_qc_mm=np.where(mv,mraw,np.nan),
            legacy_sum_flag=np.repeat(bad[0,mask,None,:],24,axis=1).reshape(-1),
            modern_sum_flag=np.repeat(bad[1,mask,None,:],24,axis=1).reshape(-1),
            legacy_requested=np.repeat(queried[0,mask],24*n),modern_requested=np.repeat(queried[1,mask],24*n),
            cross_channel_conflict=cf,rain_mm=combined,gauge_source_code=code,
            cross_channel_continuity_unverified=np.full(len(combined),True)))
        frame['period_start_utc']=frame.period_end_utc-pd.Timedelta(hours=1)
        frame['station_id']=pd.Categorical(frame.station_id,categories=registry.canonical_id)
        table=pa.Table.from_pandas(frame,preserve_index=False)
        if writer is None:writer=pq.ParquetWriter(temporary,table.schema,compression='zstd')
        writer.write_table(table);rows+=len(frame)
        print(json.dumps(dict(stage='write_hourly',year=year,rows=rows)),flush=True)
    writer.close();temporary.replace(path)
    return dict(file=path.name,rows=rows,sha256=sha(path),bytes=path.stat().st_size)


def split_for_issue(issue):
    start=issue.tz_convert('Asia/Ho_Chi_Minh');end=(issue+pd.Timedelta(hours=72)).tz_convert('Asia/Ho_Chi_Minh')
    def role(year):return 'train' if year<=2022 else 'cal' if year==2023 else 'dev' if year==2024 else 'reserved2025' if year==2025 else 'external2026'
    return role(start.year) if role(start.year)==role(end.year) else 'boundary'


def daily(registry,days,raw,valid,conflict):
    p=json.loads((BASE/'gfs/progress.json').read_text(encoding='utf8'))
    if p['state'] not in ('complete','incomplete') or p['remaining_issues']:raise ValueError('GFS collection not finished')
    errors=p['errors'];old_gfs=ROOT/'data/operational/gfs_station_daily_v2_2026_11_10/days'
    cohort=set(pd.read_csv(ROOT/'data/operational/gfs_station_daily_v2_2026_11_10/cohort_private.csv').canonical_id)
    terrain=pd.read_csv(BASE/'station_terrain_private.csv').set_index('canonical_id')
    old_policy=json.loads((ROOT/'reports/gfs_station_daily_v2_2026_11_10/source_coverage_policy.json').read_text())
    old_missing={r['day'] for r in old_policy['confirmed_source_missing']}
    clean=np.where(valid&~conflict[None,...],raw,np.nan)
    rain_daily=clean.sum(2);flat=clean.reshape(2,-1,len(registry))
    path=OUT/'PBL6_GFS_VRAIN_NGAY_2021_2026.parquet';temporary=path.with_suffix('.part.parquet')
    dates=pd.date_range('2021-01-08','2026-11-12');rows=[];writer=None;total=0;coverage=[];source_sha={}
    def flush():
        nonlocal writer,rows,total
        if not rows:return
        frame=pd.DataFrame(rows)
        for col in ['station_id','gauge_namespace','split','gfs_source_status']:
            frame[col]=frame[col].astype('string')
        table=pa.Table.from_pandas(frame,preserve_index=False)
        if writer is None:writer=pq.ParquetWriter(temporary,table.schema,compression='zstd')
        writer.write_table(table);total+=len(frame);rows=[]
    for di,day in enumerate(dates):
        daykey=day.strftime('%Y%m%d');j=days.get_loc(day);issue=day.tz_localize('UTC')+pd.Timedelta(hours=12);split=split_for_issue(issue)
        directory=old_gfs if daykey<='20241228' else BASE/'gfs/days'
        file=directory/(daykey+'.npz');meta=file.with_suffix('.json');g=None;order={}
        if file.exists() and meta.exists():
            record=json.loads(meta.read_text());assert sha(file)==record['sha256'];assert len(record['messages'])==19
            g=np.load(file);order={sid:k for k,sid in enumerate(g['station_ids'])};source_sha[daykey]=record['sha256'];source_status='verified'
        else:
            source_status='confirmed_missing' if daykey in old_missing else 'source_error'
            if source_status=='source_error' and daykey not in errors:raise ValueError('Unexplained missing forecast')
        legacy_ready={}
        for ci,channel in enumerate(('legacy','modern')):
            if channel=='modern' and day.year<2025:continue
            ready_count=0;gauge_ready_count=0
            for si,station in enumerate(registry.itertuples()):
                histories={delay:gauge_history(flat[ci],rain_daily[ci],j,si,delay) for delay in (1,3,6)}
                targets=rain_daily[ci,j+1:j+4,si]
                gauge_ready=len(targets)==3 and np.isfinite([v for history in histories.values() for v in history.values()]+targets.tolist()).all()
                field={name:float(terrain.loc[station.canonical_id,name]) for name in FEATURES['N5'] if name.startswith('dem_')}
                feature_pack=[]
                for h in (1,2,3):
                    end=issue+pd.Timedelta(hours=24*h);met={name:np.nan for name in FEATURES['N5'] if name.startswith('gfs_') and name!='gfs_rain_mm'}
                    gf=np.nan
                    if g is not None and station.canonical_id in order:
                        gi=order[station.canonical_id];met=forecast_met(g['met_names'].tolist(),g['met'][h-1,gi]);gf=float(g['rain_day_mm'][h-1,gi])
                    upslope=met['gfs_u850']*field['dem_slope_east']+met['gfs_v850']*field['dem_slope_north']
                    row=dict(station_id=station.canonical_id,station_code=int(station.canonical_id[2:])-1,
                        latitude=station.latitude,longitude=station.longitude,gauge_namespace=channel,
                        issue_utc=issue,gfs_init_utc=day.tz_localize('UTC'),gfs_midpoint_valid_utc=day.tz_localize('UTC')+pd.Timedelta(hours=24*h),
                        target_start_utc=issue+pd.Timedelta(hours=24*(h-1)),target_end_utc=end,
                        observation_cutoff_utc=issue-pd.Timedelta(hours=1),horizon=h,split=split,
                        y_mm=float(targets[h-1]),gfs_rain_mm=gf,**histories[1],**met,**field,**add_calendar(end),
                        wind_upslope=upslope,moist_upslope=upslope*met['gfs_q850_gkg'],
                        in_frozen_57_cohort=station.canonical_id in cohort,continuity_with_legacy_confirmed=channel=='legacy',
                        gauge_history_targets_complete=bool(gauge_ready),gfs_source_status=source_status)
                    for delay,history in histories.items():row.update({f'{name}_delay{delay}':history[name] for name in RECENT})
                    feature_pack.append(row)
                complete=bool(gauge_ready and all(np.isfinite([r[name] for name in FEATURES['N5']]).all() for r in feature_pack) and split!='boundary')
                if channel=='legacy':legacy_ready[station.canonical_id]=complete
                for row in feature_pack:
                    row['sample_ready']=complete
                    row['recommended_sample']=bool(complete and (channel=='legacy' or not legacy_ready[station.canonical_id]))
                    row['eligible_frozen_57_legacy']=bool(complete and row['in_frozen_57_cohort'] and channel=='legacy')
                    rows.append(row)
                ready_count+=complete;gauge_ready_count+=bool(gauge_ready)
            coverage.append(dict(day=day.strftime('%Y-%m-%d'),year=day.year,channel=channel,split=split,
                                 gauge_ready_station_issues=gauge_ready_count,ready_station_issues=ready_count,forecast_status=source_status))
        if g is not None:g.close()
        if (di+1)%30==0:flush();print(json.dumps(dict(stage='write_daily',issue=str(day.date()),rows=total)),flush=True)
    flush();writer.close();temporary.replace(path)
    pd.DataFrame(coverage).to_csv(BASE/'daily_coverage_private.csv',index=False)
    report=pd.DataFrame(coverage).groupby(['year','channel','split'],as_index=False).agg(issue_days=('day','size'),gauge_ready_station_issues=('gauge_ready_station_issues','sum'),ready_station_issues=('ready_station_issues','sum'))
    report.to_csv(PUBLIC/'daily_sample_counts.csv',index=False);write_json(BASE/'gfs_source_checksums.json',source_sha)
    return dict(file=path.name,rows=total,sha256=sha(path),bytes=path.stat().st_size,new_gfs_source_errors=errors)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--reuse-matrices',action='store_true');parser.add_argument('--gauges-only',action='store_true');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    registry=pd.read_csv(BASE/'station_registry_private.csv',dtype={'legacy_id':str,'modern_id':str})
    if args.reuse_matrices:
        z=np.load(BASE/'rain_channels.npz');days=pd.DatetimeIndex(z['marked_day']);raw=z['raw'];valid=z['valid'];bad=z['bad_daily_sum'];queried=z['queried'];conflict=z['conflict']
    else:days,raw,valid,bad,queried,conflict=matrices(registry)
    h_manifest=BASE/'hourly_summary.json';matrix_sha=sha(BASE/'rain_channels.npz')
    cached=json.loads(h_manifest.read_text(encoding='utf8')) if h_manifest.exists() else None
    if cached and cached['matrix_sha256']==matrix_sha and sha(OUT/cached['record']['file'])==cached['record']['sha256']:
        h=cached['record']
    else:
        h=hourly(registry,days,raw,valid,bad,queried,conflict)
        write_json(h_manifest,dict(matrix_sha256=matrix_sha,record=h))
    if args.gauges_only:print(json.dumps(dict(status='hourly_built_daily_forecasts_pending',hourly=h)),flush=True);return
    result=daily(registry,days,raw,valid,conflict)
    summary=dict(status='built_pending_independent_validation',station_inventory=len(registry),source_marked_days=len(days),
                 first_marked_day=FIRST,last_marked_day=LAST,last_daily_issue='2026-11-12',
                 hourly=h,daily=result,training_performed=False,model_evaluation=False,
                 collection_2025_authorized=True,modern_continuity_confirmed=False,all_stations_complete=False)
    write_json(PUBLIC/'dataset_summary.json',summary);print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
