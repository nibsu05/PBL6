"""Replay the NWP pilot against raw gauge arrays and selected GRIB messages."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import requests
import eccodes as ec

from src.gfs_station_dataset import FEATURES, forecast_met
from scripts.collect_gfs_station_pilot import range_bytes

BASE=ROOT / "data/operational/gfs_station_pilot_2026_11_10"
PUBLIC=ROOT / "reports/gfs_station_pilot_2026_11_10"
VRAIN=ROOT / "data/operational/vrain_2026_11_09"
DATA=ROOT / "data/processed/gfs_station_pilot/gfs_vrain_pilot.parquet"


def equal(a,b):np.testing.assert_allclose(a,b,rtol=3e-6,atol=3e-5,equal_nan=True)


def main():
    f=pd.read_parquet(DATA)
    audit=json.loads((PUBLIC / "dataset_audit.json").read_text())
    protocol=json.loads((PUBLIC / "protocol.json").read_text())
    assert hashlib.sha256(DATA.read_bytes()).hexdigest()==audit['dataset_sha256']
    assert np.isfinite(f[FEATURES['A3']+['y_mm']].to_numpy()).all()
    assert not f.duplicated(['station_id','issue_utc','horizon']).any()
    assert f.groupby(['station_id','issue_utc']).horizon.nunique().eq(3).all()
    assert pd.DatetimeIndex(f.issue_utc).tz_convert('Asia/Ho_Chi_Minh').hour.tolist()==[19]*len(f)
    assert ((f.issue_utc-f.gfs_init_utc)==pd.Timedelta(hours=12)).all()
    assert ((f.issue_utc-f.observation_cutoff_utc)==pd.Timedelta(hours=1)).all()
    assert ((f.target_end_utc-f.target_start_utc)==pd.Timedelta(hours=24)).all()
    assert (f.target_start_utc==f.issue_utc+pd.to_timedelta((f.horizon-1)*24,unit='h')).all()
    assert ((f.gfs_midpoint_valid_utc>f.target_start_utc)&(f.gfs_midpoint_valid_utc<f.target_end_utc)).all()
    assert pd.DatetimeIndex(f.target_end_utc).tz_convert('Asia/Ho_Chi_Minh').year.max()<=2024
    for fold,first,stop in [('train','2021-01-01','2023-01-01'),('cal','2023-01-01','2024-01-01'),('dev','2024-01-01','2025-01-01')]:
        part=f[f.split.eq(fold)]
        a=pd.Timestamp(first,tz='Asia/Ho_Chi_Minh');b=pd.Timestamp(stop,tz='Asia/Ho_Chi_Minh')
        assert (part.target_start_utc>=a).all() and (part.target_end_utc<=b).all()
    registry=pd.read_csv(BASE / 'registry_private.csv',dtype={'legacy_id':str})
    aliases=dict(zip(registry.canonical_id,registry.legacy_id))
    coordinates=registry.set_index('canonical_id')
    z=np.load(VRAIN / 'freeze_work/station_matrices.npz')
    rain=np.where(z['valid'],z['rain'],np.nan).reshape(-1,82)
    days=pd.DatetimeIndex(z['marked_day']);order={s:i for i,s in enumerate(z['station_ids'])}
    source_ends=pd.to_datetime(z['clock_end_naive']).tz_localize('Asia/Ho_Chi_Minh').tz_convert('UTC')
    source_ends=source_ends.as_unit('ns')
    replayed=0; forecast_headers=0;packing=0;generators=set()
    for issue,part in f.groupby('issue_utc'):
        name=issue.strftime('%Y%m%d');path=BASE / 'days' / (name+'.npz')
        meta=json.loads(path.with_suffix('.json').read_text())
        assert hashlib.sha256(path.read_bytes()).hexdigest()==meta['sha256']
        archive=np.load(path);archive_order={s:i for i,s in enumerate(archive['station_ids'])}
        packing+=meta['rounding_corrections']
        for message in meta['messages']:
            assert message['dataDate']==int(name) and message['dataTime']==0
            assert message['Ni']==1440 and message['Nj']==721
            expected_units={'rain_cumulative':'kg m**-2','t850_k':'K','rh850':'%',
                            'u850':'m s**-1','v850':'m s**-1','pwat':'kg m**-2'}
            assert message['units']==expected_units[message['name']]
            if message['name']=='rain_cumulative':assert message['startStep']==0
            generators.add(message['generatingProcessIdentifier']);forecast_headers+=1
        for row in part.itertuples():
            si=order[aliases[row.station_id]];gi=archive_order[row.station_id]
            local_day=issue.tz_convert('Asia/Ho_Chi_Minh').tz_localize(None).normalize()
            di=days.get_loc(local_day)
            # Independently select intervals by their actual source clocks.
            mask=(source_ends>row.target_start_utc)&(source_ends<=row.target_end_utc)
            assert mask.sum()==24
            equal(rain[mask,si].sum(),row.y_mm)
            for lag in range(1,8):
                end=issue-pd.Timedelta(days=lag)
                mask=(source_ends>end-pd.Timedelta(hours=24))&(source_ends<=end)
                assert mask.sum()==24 and end<=row.observation_cutoff_utc
                equal(rain[mask,si].sum(),getattr(row,f'rain_lag_day{lag}_mm'))
            for duration in (1,6,24):
                cutoff=row.observation_cutoff_utc
                mask=(source_ends>cutoff-pd.Timedelta(hours=duration))&(source_ends<=cutoff)
                assert mask.sum()==duration
                equal(rain[mask,si].sum(),getattr(row,f'rain_recent{duration}h_mm'))
            h=row.horizon
            cumulative=archive['cumulative_mm']
            expected=max(float(cumulative[h,gi]-cumulative[h-1,gi]),0)
            equal(row.gfs_rain_mm,expected)
            met=forecast_met(archive['met_names'].tolist(),archive['met'][h-1,gi])
            for key,value in met.items():equal(getattr(row,key),value)
            replayed+=1
    # Independent ecCodes nearest-four-corners sampling from newly fetched
    # messages; checks flat-grid indexing and cached station column order.
    raw_replays=0;range_requests=0
    sample_dates=[f[f.split.eq(fold)].issue_utc.sort_values().iloc[len(f[f.split.eq(fold)])//2].strftime('%Y%m%d') for fold in ['train','cal','dev']]
    with requests.Session() as session:
        for name in sample_dates:
            meta=json.loads((BASE/'days'/(name+'.json')).read_text());archive=np.load(BASE/'days'/(name+'.npz'))
            ids=archive['station_ids'];indices=[0,len(ids)//2,len(ids)-1]
            for message in meta['messages']:
                data,_=range_bytes(session,message['source_url'],*message['range']);range_requests+=1
                assert hashlib.sha256(data).hexdigest()==message['message_sha256']
                g=ec.codes_new_from_message(data)
                try:
                    for k in indices:
                        station=coordinates.loc[ids[k]]
                        nearest=ec.codes_grib_find_nearest(g,float(station.latitude),float(station.longitude),npoints=4)
                        lo_lat=min(p['lat'] for p in nearest);lo_lon=min(p['lon'] for p in nearest)
                        fy=(station.latitude-lo_lat)/.25;fx=(station.longitude-lo_lon)/.25
                        value=0.
                        for p in nearest:
                            wy=fy if p['lat']>lo_lat else 1-fy
                            wx=fx if p['lon']>lo_lon else 1-fx
                            value+=p['value']*wy*wx
                        lead=message['endStep']
                        if message['name']=='rain_cumulative':
                            expected=archive['cumulative_mm'][[12,36,60,84].index(lead),k]
                        else:
                            expected=archive['met'][[24,48,72].index(lead),k,archive['met_names'].tolist().index(message['name'])]
                        equal(value,expected);raw_replays+=1
                finally:ec.codes_release(g)
    report=dict(status='passed',dataset_sha256=audit['dataset_sha256'],rows_replayed=replayed,
        forecast_message_headers_checked=forecast_headers,new_raw_grib_range_requests=range_requests,
        independent_four_corner_samples=raw_replays,small_negative_rounding_values_clipped=packing,
        generating_process_identifiers=sorted(generators),source_cycle_before_issue=True,
        gauge_history_before_assumed_cutoff=True,nonoverlapping_24h_target_windows=True,
        complete_common_A0_A3_mask=True,whole_targets_within_fold=True,
        no_ERA5_or_future_observed_weather=True,test2025_read=False,
        actual_operational_release_delays_verified=False)
    (PUBLIC/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
