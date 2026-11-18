"""Independent clock-based replay of all daily-v2 examples and GRIB spot checks."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import requests
import eccodes as ec
from src.gfs_daily import BASE,PUBLIC,DATA,VRAIN,FEATURES,load_protocol,sha,write_json,cv_masks
from src.gfs_station_dataset import forecast_met
from scripts.collect_gfs_station_pilot import range_bytes


def equal(a,b):np.testing.assert_allclose(a,b,rtol=3e-6,atol=3e-5)


def main():
    p=load_protocol();f=pd.read_parquet(DATA/'dataset.parquet')
    assert sha(DATA/'dataset.parquet')==json.loads((PUBLIC/'dataset_audit.json').read_text())['dataset_sha256']
    assert np.isfinite(f[FEATURES['N5']+['y_mm']].to_numpy()).all()
    assert not f.duplicated(['station_id','issue_utc','horizon']).any()
    assert f.groupby(['station_id','issue_utc']).horizon.nunique().eq(3).all()
    assert f.issue_utc.dt.hour.eq(12).all()
    assert (f.issue_utc-f.gfs_init_utc).eq(pd.Timedelta(hours=12)).all()
    assert (f.issue_utc-f.observation_cutoff_utc).eq(pd.Timedelta(hours=1)).all()
    assert (f.target_end_utc-f.target_start_utc).eq(pd.Timedelta(hours=24)).all()
    assert (f.target_start_utc==f.issue_utc+pd.to_timedelta(24*(f.horizon-1),unit='h')).all()
    assert ((f.gfs_midpoint_valid_utc>f.target_start_utc)&(f.gfs_midpoint_valid_utc<f.target_end_utc)).all()
    for split,start,end in [('train','2021','2023'),('cal','2023','2024'),('dev','2024','2025')]:
        part=f[f.split.eq(split)]
        assert part.target_start_utc.ge(pd.Timestamp(start,tz='Asia/Ho_Chi_Minh')).all()
        assert part.target_end_utc.lt(pd.Timestamp(end,tz='Asia/Ho_Chi_Minh')).all()
    registry=pd.read_csv(BASE/'registry_private.csv',dtype={'legacy_id':str}).set_index('canonical_id')
    cohort=pd.read_csv(BASE/'cohort_private.csv').canonical_id.tolist()
    assert set(f.station_id)==set(cohort) and len(cohort)==57
    z=np.load(VRAIN/'freeze_work/station_matrices.npz')
    rain=np.where(z['valid'],z['rain'],np.nan).reshape(-1,82)
    source_ends=pd.to_datetime(z['clock_end_naive']).tz_localize('Asia/Ho_Chi_Minh').tz_convert('UTC')
    si={str(s):j for j,s in enumerate(z['station_ids'])}
    def values(end,hours,stations):
        pos=np.flatnonzero((source_ends>end-pd.Timedelta(hours=hours))&(source_ends<=end))
        assert len(pos)==hours
        return rain[np.ix_(pos,stations)].sum(0)
    checked=0;headers=0
    for issue,part in f.groupby('issue_utc',sort=True):
        day=issue.strftime('%Y%m%d');path=BASE/'days'/(day+'.npz');g=np.load(path)
        meta=json.loads(path.with_suffix('.json').read_text());assert sha(path)==meta['sha256']
        order={s:j for j,s in enumerate(g['station_ids'])}
        for m in meta['messages']:
            assert m['dataDate']==int(day) and m['dataTime']==0 and m['Ni']==1440 and m['Nj']==721
            assert m['stepType']==('accum' if m['name']=='rain_cumulative' else 'instant')
            if m['name']=='rain_cumulative':assert m['startStep']==0 and m['endStep'] in (12,36,60,84)
            else:assert m['endStep'] in (24,48,72)
            headers+=1
        for h,sub in part.groupby('horizon'):
            stations=[si[str(registry.loc[s,'legacy_id'])] for s in sub.station_id]
            gi=[order[s] for s in sub.station_id]
            equal(values(issue+pd.Timedelta(hours=24*h),24,stations),sub.y_mm)
            equal(np.maximum(g['cumulative_mm'][h,gi]-g['cumulative_mm'][h-1,gi],0),sub.gfs_rain_mm)
            expected_met=pd.DataFrame([forecast_met(g['met_names'].tolist(),g['met'][h-1,k]) for k in gi])
            equal(expected_met.to_numpy(),sub[expected_met.columns].to_numpy())
            checked+=len(sub)
        first=part[part.horizon.eq(1)]
        stations=[si[str(registry.loc[s,'legacy_id'])] for s in first.station_id]
        for lag in range(1,8):equal(values(issue-pd.Timedelta(days=lag),24,stations),first[f'rain_lag_day{lag}_mm'])
        for delay in (1,3,6):
            cutoff=issue-pd.Timedelta(hours=delay)
            for hours in (1,6,24):
                expected=values(cutoff,hours,stations);equal(expected,first[f'rain_recent{hours}h_mm_delay{delay}'])
                if delay==1:equal(expected,first[f'rain_recent{hours}h_mm'])
        for col in [c for c in f.columns if c.startswith('rain_')]:
            assert part.groupby('station_id')[col].nunique().eq(1).all()
    folds=[]
    for fold in p['tuning']['folds']:
        tr,va=cv_masks(f.iloc[::3],fold)
        a=f.iloc[::3].loc[tr];b=f.iloc[::3].loc[va]
        assert (a.issue_utc+pd.Timedelta(hours=72)).max()<b.issue_utc.min()-pd.Timedelta(days=7)
        assert set(b.station_id)<=set(a.station_id)
        folds.append(dict(start=fold['start'],train_samples=len(a),validation_samples=len(b)))
    # Fresh official messages, sampled with ecCodes nearest-point coordinates,
    # independently of the collector's flattened grid indexing.
    samples=0;requests_count=0
    with requests.Session() as session:
        for split in ('train','cal','dev'):
            dates=sorted(f.loc[f.split.eq(split),'issue_utc'].unique());day=pd.Timestamp(dates[len(dates)//2]).strftime('%Y%m%d')
            meta=json.loads((BASE/'days'/(day+'.json')).read_text());g=np.load(BASE/'days'/(day+'.npz'))
            order={s:j for j,s in enumerate(g['station_ids'])}
            for m in meta['messages']:
                if m['endStep'] not in (12,24,36,60,84):continue
                data,_=range_bytes(session,m['source_url'],*m['range']);requests_count+=1
                import hashlib
                assert hashlib.sha256(data).hexdigest()==m['message_sha256']
                grib=ec.codes_new_from_message(data)
                try:
                    for sid in [cohort[0],cohort[len(cohort)//2],cohort[-1]]:
                        station=registry.loc[sid];k=order[sid]
                        near=ec.codes_grib_find_nearest(grib,float(station.latitude),float(station.longitude),npoints=4)
                        lowlat=min(v['lat'] for v in near);lowlon=min(v['lon'] for v in near)
                        fy=(station.latitude-lowlat)/.25;fx=(station.longitude-lowlon)/.25
                        actual=sum(v['value']*(fy if v['lat']>lowlat else 1-fy)*(fx if v['lon']>lowlon else 1-fx) for v in near)
                        expected=g['cumulative_mm'][[12,36,60,84].index(m['endStep']),k] if m['name']=='rain_cumulative' else g['met'][0,k,g['met_names'].tolist().index(m['name'])]
                        equal(actual,expected);samples+=1
                finally:ec.codes_release(grib)
    result=dict(status='passed',rows_replayed=checked,source_clock_replay=True,gauge_delays_replayed=[1,3,6],
        forecast_headers_checked=headers,raw_range_requests=requests_count,independent_grid_samples=samples,
        chronological_tuning_folds=folds,common_mask=True,test2025_read=False,operational_delivery_latency_proven=False,
        dataset_sha256=sha(DATA/'dataset.parquet'))
    write_json(PUBLIC/'dataset_verification.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':main()
