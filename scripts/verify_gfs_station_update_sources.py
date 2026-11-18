"""Re-fetch fixed GRIB ranges and independently check the extended join."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import requests
from src.station_archive_update import BASE,OUT,PUBLIC,write_json,sha
from src.gfs_station import regular_grid_weights
from scripts import collect_gfs_station_pilot as collector


def main():
    registry=pd.read_csv(BASE/'gfs/registry_private.csv')
    indices,weights=regular_grid_weights(registry.latitude.to_numpy(),registry.longitude.to_numpy())
    checks=0;points=0;f=pd.read_parquet(OUT/'PBL6_GFS_VRAIN_NGAY_2021_2026.parquet')
    assert f.gfs_midpoint_valid_utc.eq(f.gfs_init_utc+pd.to_timedelta(f.horizon*24,unit='h')).all()
    assert (f.issue_utc-f.gfs_init_utc).eq(pd.Timedelta(hours=12)).all()
    with requests.Session() as s:
      for day in ('20241229','20250101','20250615','20261112'):
        cached=np.load(BASE/'gfs/days'/(day+'.npz'))
        manifest=json.loads((BASE/'gfs/days'/(day+'.json')).read_text())
        for name,lead in (('rain_cumulative',36),('t850_k',24)):
            record=next(r for r in manifest['messages'] if r['name']==name and r['endStep']==lead)
            data,_=collector.range_bytes(s,record['source_url'],*record['range'])
            sampled,meta=collector.decode(data,name,day,lead,indices,weights)
            expected=cached['cumulative_mm'][1] if name=='rain_cumulative' else cached['met'][0,:,cached['met_names'].tolist().index('t850_k')]
            np.testing.assert_array_equal(sampled,expected)
            assert meta['message_sha256']==record['message_sha256']
            checks+=1;points+=len(sampled)
        issue=pd.Timestamp(day,tz='UTC')+pd.Timedelta(hours=12)
        selected=f[f.issue_utc.eq(issue)]
        order={sid:j for j,sid in enumerate(cached['station_ids'])}
        for h in (1,2,3):
            part=selected[selected.horizon.eq(h)]
            gi=part.station_id.map(order).to_numpy(int);names=cached['met_names'].tolist()
            for column,key,offset in [('gfs_t850_c','t850_k',-273.15),('gfs_rh850_pct','rh850',0),('gfs_u850','u850',0),('gfs_v850','v850',0),('gfs_pwat','pwat',0)]:
                expected=cached['met'][h-1,gi,names.index(key)].astype(float)+offset
                np.testing.assert_allclose(part[column],expected,rtol=0,atol=1e-10)
            np.testing.assert_array_equal(part.gfs_rain_mm,cached['rain_day_mm'][h-1,gi])
            slope=part.gfs_u850*part.dem_slope_east+part.gfs_v850*part.dem_slope_north
            np.testing.assert_allclose(part.wind_upslope,slope,rtol=0,atol=1e-12)
        cached.close()
    report=dict(status='passed',fresh_grib_ranges=checks,independent_station_samples=points,
                dataset_sha256=sha(OUT/'PBL6_GFS_VRAIN_NGAY_2021_2026.parquet'),
                fixed_source_dates=['2024-12-29','2025-01-01','2025-06-15','2026-11-12'],
                joined_fields_checked=['gfs_rain_mm','gfs_t850_c','gfs_rh850_pct','gfs_u850','gfs_v850','gfs_pwat','wind_upslope'],
                init_valid_issue_times_checked=True,actual_historical_receipt_time_proven=False,training_performed=False,model_evaluation=False)
    write_json(PUBLIC/'fresh_source_verification.json',report);print(json.dumps(report))


if __name__=='__main__':main()
