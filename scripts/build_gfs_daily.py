"""Build daily-v2 with an identical mask for features, horizons and gauge delays."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from src.gfs_daily import BASE,PUBLIC,DATA,VRAIN,FEATURES,RECENT,load_protocol,gauge_history,sha,write_json
from src.gfs_station_dataset import forecast_met,add_calendar
from src.gfs_station import issue_contract
from src.station_forecast_data import target_splits


def main():
    p=load_protocol();cohort=pd.read_csv(BASE/'cohort_private.csv',dtype={'legacy_id':str})
    if sha(BASE/'cohort_private.csv')!=p['station_manifest_sha256']:raise ValueError('Cohort changed')
    expected=pd.date_range(p['first_issue_day'],p['last_issue_day'],freq='D').strftime('%Y%m%d')
    missing=[d for d in expected if not (BASE/'days'/(d+'.npz')).exists() or not (BASE/'days'/(d+'.json')).exists()]
    manifest=BASE/'collection_manifest.json'
    if not manifest.exists():raise ValueError('Wait for the full fixed-date collection to finish')
    policy=json.loads((PUBLIC/'source_coverage_policy.json').read_text())
    confirmed={r['day'] for r in policy['confirmed_source_missing']}
    if policy['status']!='confirmed' or set(missing)!=confirmed:
        raise ValueError(f'Unresolved daily source gaps: {len(set(missing)-confirmed)}')
    z=np.load(VRAIN/'freeze_work/station_matrices.npz')
    hourly=np.where(z['valid'],z['rain'],np.nan).reshape(-1,82)
    daily=hourly.reshape(-1,24,82).sum(1);days=pd.DatetimeIndex(z['marked_day'])
    source_order={str(s):j for j,s in enumerate(z['station_ids'])}
    rows=[];reject=dict(boundary_issues=0,incomplete_station_issues=0);message_count=0
    dates_sha={}
    for day in expected:
        if day in confirmed:continue
        path=BASE/'days'/(day+'.npz');meta=json.loads(path.with_suffix('.json').read_text())
        if sha(path)!=meta['sha256']:raise ValueError('Forecast checksum mismatch')
        if len(meta['messages'])!=19:raise ValueError('Unexpected forecast message count')
        message_count+=19;dates_sha[day]=meta['sha256']
        init,issue=issue_contract(pd.Timestamp(day).strftime('%Y-%m-%d'))
        fold=target_splits(pd.DatetimeIndex([issue]),72)[0]
        if fold=='unused':reject['boundary_issues']+=1;continue
        j=days.get_loc(pd.Timestamp(day));g=np.load(path);order={s:i for i,s in enumerate(g['station_ids'])}
        for station in cohort.itertuples():
            si=source_order[station.legacy_id];gi=order[station.canonical_id]
            histories={delay:gauge_history(hourly,daily,j,si,delay) for delay in p['gauge_delay_hours']}
            targets=daily[j+1:j+4,si]
            complete=np.isfinite([v for history in histories.values() for v in history.values()]+targets.tolist()).all()
            if len(targets)!=3 or not complete:reject['incomplete_station_issues']+=1;continue
            terrain={name:getattr(station,name) for name in FEATURES['N5'] if name.startswith('dem_')}
            for h in (1,2,3):
                start=issue+pd.Timedelta(hours=24*(h-1));end=start+pd.Timedelta(hours=24)
                met=forecast_met(g['met_names'].tolist(),g['met'][h-1,gi])
                upslope=met['gfs_u850']*terrain['dem_slope_east']+met['gfs_v850']*terrain['dem_slope_north']
                row=dict(station_id=station.canonical_id,station_code=int(station.canonical_id[2:])-1,
                    latitude=station.latitude,longitude=station.longitude,issue_utc=issue,gfs_init_utc=init,
                    gfs_midpoint_valid_utc=init+pd.Timedelta(hours=24*h),target_start_utc=start,target_end_utc=end,
                    observation_cutoff_utc=issue-pd.Timedelta(hours=1),horizon=h,split=fold,y_mm=float(targets[h-1]),
                    gfs_rain_mm=float(g['rain_day_mm'][h-1,gi]),**histories[1],**met,**terrain,**add_calendar(end),
                    wind_upslope=upslope,moist_upslope=upslope*met['gfs_q850_gkg'])
                for delay,history in histories.items():
                    row.update({f'{name}_delay{delay}':history[name] for name in RECENT})
                if not np.isfinite([row[name] for name in FEATURES['N5']]).all():raise ValueError('Nonfinite forecast/static input')
                rows.append(row)
    frame=pd.DataFrame(rows).sort_values(['issue_utc','station_id','horizon']).reset_index(drop=True)
    if frame.duplicated(['station_id','issue_utc','horizon']).any():raise ValueError('Duplicate examples')
    if not np.array_equal(frame.horizon.to_numpy().reshape(-1,3),np.tile([1,2,3],(len(frame)//3,1))):raise ValueError('Incomplete horizon packs')
    if set(frame.split)!={'train','cal','dev'}:raise ValueError('Chronological fold missing')
    if frame.target_end_utc.dt.tz_convert('Asia/Ho_Chi_Minh').dt.year.max()>2024:raise ValueError('Reserved year accessed')
    path=DATA/'dataset.parquet'
    if any((BASE/'models').glob('*.joblib')) and path.exists():
        old=pd.read_parquet(path)
        pd.testing.assert_frame_equal(old,frame)
    else:frame.to_parquet(path,index=False,compression='zstd')
    write_json(BASE/'source_checksums.json',dates_sha)
    counts={part:dict(station_issues=int((frame.split==part).sum()//3),rows=int((frame.split==part).sum()),
             issue_dates=int(frame.loc[frame.split==part,'issue_utc'].nunique()),stations=int(frame.loc[frame.split==part,'station_id'].nunique())) for part in ('train','cal','dev')}
    audit=dict(status='complete',planned_issues=len(expected),available_source_issues=len(expected)-len(confirmed),
        source_unavailable_issues=len(confirmed),station_count=57,source_messages=message_count,
        station_issues=len(frame)//3,long_horizon_rows=len(frame),counts=counts,rejected=reject,
        feature_counts=p['feature_counts'],dataset_sha256=sha(path),source_gauge_sha256=sha(VRAIN/'freeze_work/station_matrices.npz'),
        test2025_read=False,common_mask_gauge_delays=[1,3,6],all_hourly_values_required=True)
    write_json(PUBLIC/'dataset_audit.json',audit)
    print(json.dumps(audit),flush=True)


if __name__=='__main__':main()
