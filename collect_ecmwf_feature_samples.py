"""Tải đúng một mốc SM20 S2S, rồi một mốc CIN/CAPE/TCWV ERA5.

Mẫu được lưu tách khỏi dữ liệu huấn luyện. Lưu ID request để chạy lại tiếp tục
request cũ, không tạo hàng đợi trùng. Không ghi token vào log hay metadata.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import xarray as xr
from cdsapi.api import read_config
from ecmwf.datastores import Client

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'data/samples/ecmwf_features'
LAT, LON = 16.0544, 108.2022
REQUESTS = {
    's2s': {
        'url': 'https://ecds.ecmwf.int/api', 'dataset': 's2s-forecasts',
        'filename': 's2s_ecmwf_sm20_init_20240829_00_lead_0_24.grib',
        'request': {'origin':'ecmwf', 'forecast_type':'control_forecast',
                    'level_type':'single_level', 'variable':['soil_moisture_top_20_cm'],
                    'year':['2024'], 'month':['08'], 'day':['29'], 'time':['00:00'],
                    'leadtime_hour':['0_24'], 'data_format':'grib',
                    'area':[18,105,13.5,111]},
    },
    'era5': {
        'url':'https://cds.climate.copernicus.eu/api', 'dataset':'reanalysis-era5-single-levels',
        'filename':'era5_cin_cape_tcwv_20240830_00.nc',
        'request':{'product_type':['reanalysis'],
                   'variable':['convective_inhibition','convective_available_potential_energy',
                               'total_column_water_vapour'],
                   'year':['2024'], 'month':['08'], 'day':['30'], 'time':['00:00'],
                   'data_format':'netcdf', 'download_format':'unarchived',
                   'area':[16.5,107.75,15.75,108.5]},
    },
}


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False),encoding='utf-8')


def distance(lat,lon):
    """Khoảng cách cung lớn đến vị trí yêu cầu, km."""
    a=np.radians(np.asarray(lat)); b=np.radians(np.asarray(lon))
    p,q=np.radians([LAT,LON])
    d=np.sin((a-p)/2)**2 + np.cos(p)*np.cos(a)*np.sin((b-q)/2)**2
    return 6371.0088*2*np.arcsin(np.sqrt(np.clip(d,0,1)))


def extract_s2s(path):
    import eccodes as ec
    rows=[]
    with path.open('rb') as fh:
        while (gid:=ec.codes_grib_new_from_file(fh)) is not None:
            try:
                meta={k:ec.codes_get(gid,k) for k in ['paramId','shortName','name','units',
                    'dataDate','dataTime','validityDate','validityTime','startStep','endStep',
                    'stepUnits','stepType','gridType','iDirectionIncrementInDegrees',
                    'jDirectionIncrementInDegrees']}
                if meta['paramId'] != 228086:
                    raise ValueError(f'Không phải SM20: {meta["paramId"]}')
                lat=ec.codes_get_array(gid,'latitudes'); lon=ec.codes_get_array(gid,'longitudes')
                vals=ec.codes_get_array(gid,'values')
                valid=np.isfinite(vals)
                if ec.codes_get(gid,'bitmapPresent'):
                    valid &= ec.codes_get_array(gid,'bitmap').astype(bool)
                if not valid.any(): raise ValueError('Mẫu SM20 không có ô đất hợp lệ')
                km=distance(lat,lon); nearest=int(np.argmin(km))
                chosen=int(np.argmin(np.where(valid,km,np.inf)))
                stamp=pd.to_datetime(f'{meta["validityDate"]}{meta["validityTime"]:04d}',format='%Y%m%d%H%M',utc=True)
                init=pd.to_datetime(f'{meta["dataDate"]}{meta["dataTime"]:04d}',format='%Y%m%d%H%M',utc=True)
                if meta['stepUnits']!=1 or meta['stepType']!='avg':
                    raise ValueError('Mẫu SM20 không có khoảng trung bình theo giờ như yêu cầu')
                start=init+pd.Timedelta(hours=float(meta['startStep']))
                end=init+pd.Timedelta(hours=float(meta['endStep']))
                if (init!=pd.Timestamp('2024-08-29T00:00:00Z')
                        or meta['startStep']!=0 or meta['endStep']!=24 or end!=stamp):
                    raise ValueError('Ngày khởi tạo hoặc hạn dự báo SM20 không khớp request')
                row={'source':'ECMWF S2S control forecast', 'feature':'sm20',
                     'value':float(vals[chosen]), 'units':meta['units'],
                     'forecast_reference_time_utc':init.isoformat(),
                     'mean_period_start_utc':start.isoformat(),
                     'mean_period_end_utc':end.isoformat(),
                     'mean_period_start_local':start.tz_convert('Asia/Ho_Chi_Minh').isoformat(),
                     'mean_period_end_local':end.tz_convert('Asia/Ho_Chi_Minh').isoformat(),
                     'valid_time_utc':stamp.isoformat(),
                     'valid_time_local':stamp.tz_convert('Asia/Ho_Chi_Minh').isoformat(),
                     'latitude':float(lat[chosen]),'longitude':float(lon[chosen]),
                     'distance_km':float(km[chosen]),
                     'requested_latitude':LAT,'requested_longitude':LON,
                     'nearest_grid_latitude':float(lat[nearest]),
                     'nearest_grid_longitude':float(lon[nearest]),
                     'nearest_grid_is_missing':not bool(valid[nearest]),
                     'selection':'nearest nonmissing soil grid point',
                     'temporal_meaning':'daily mean over GRIB startStep/endStep; not an hourly observation',
                     'extracted_at_utc':now(), **meta}
                rows.append(row)
            finally: ec.codes_release(gid)
    if len(rows)!=1: raise ValueError(f'Cần đúng 1 trường SM20, nhận {len(rows)}')
    pd.DataFrame(rows).to_csv(OUT/'sample_sm20_s2s.csv',index=False,encoding='utf-8-sig')
    save(OUT/'sample_sm20_s2s.json',rows[0])
    return rows


def extract_era5(path):
    rows=[]
    with xr.open_dataset(path) as ds:
        tc='valid_time' if 'valid_time' in ds.coords else 'time'
        times=pd.DatetimeIndex(pd.to_datetime(ds[tc].values.reshape(-1),utc=True))
        if len(times)!=1 or times[0]!=pd.Timestamp('2024-08-30T00:00:00Z'):
            raise ValueError(f'Mốc thời gian ERA5 không đúng: {times}')
        point=ds.sel(latitude=LAT,longitude=LON,method='nearest')
        lat,lon=float(point.latitude),float(point.longitude)
        for name in ['cin','cape','tcwv']:
            if name not in point: raise ValueError(f'Thiếu {name}')
            val=float(point[name].values.reshape(-1)[0])
            rows.append({'source':'ERA5 reanalysis', 'feature':name,'value':val if np.isfinite(val) else None,
                         'units':point[name].attrs.get('units'),
                         'long_name':point[name].attrs.get('long_name'),
                         'valid_time_utc':times[0].isoformat(),
                         'valid_time_local':times[0].tz_convert('Asia/Ho_Chi_Minh').isoformat(),
                         'latitude':lat,'longitude':lon,'distance_km':float(distance(lat,lon)),
                         'requested_latitude':LAT,'requested_longitude':LON,
                         'is_missing':not np.isfinite(val),'extracted_at_utc':now()})
    pd.DataFrame(rows).to_csv(OUT/'sample_cin_cape_tcwv_era5.csv',index=False,encoding='utf-8-sig')
    # Một hàng rộng để người dùng kiểm tra trực tiếp một mốc thời gian.
    wide={k:rows[0][k] for k in ['valid_time_utc','valid_time_local','latitude','longitude','distance_km']}
    wide.update({r['feature']:r['value'] for r in rows})
    wide.update({r['feature']+'_units':r['units'] for r in rows})
    pd.DataFrame([wide]).to_csv(OUT/'sample_era5_one_timestamp.csv',index=False,encoding='utf-8-sig')
    save(OUT/'sample_cin_cape_tcwv_era5.json',rows)
    return rows


def collect(kind, wait=False):
    spec=REQUESTS[kind]
    OUT.mkdir(parents=True,exist_ok=True)
    state_path=OUT/f'{kind}_request.json'
    state=json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
    target=OUT/spec['filename']
    key=''
    try:
        if not target.exists():
            config=read_config(os.environ.get('CDSAPI_RC',str(Path.home()/'.cdsapirc')))
            key=os.environ.get('CDSAPI_KEY',config.get('key',''))
            if not key:raise RuntimeError('Chưa có CDS API token trong cấu hình local')
            # ECMWF xác nhận CDS token dùng được ở ECDS; không sửa ~/.cdsapirc.
            client=Client(url=spec['url'],key=key,timeout=45,maximum_tries=1,
                          sleep_max=30,progress=False)
            if state.get('request_id'):
                if state.get('request')!=spec['request']:raise ValueError('Không đổi request đã gửi')
                job=client.get_remote(state['request_id'])
            else:
                state={**spec,'created_at_utc':now(),'status':'submitting'}
                save(state_path,state)
                job=client.submit(spec['dataset'],spec['request'])
                state['request_id']=job.request_id
                save(state_path,state)
            state['status']=job.status
            state['checked_at_utc']=now()
            save(state_path,state)
            if state['status']!='successful' and not wait:
                print(f'{kind}: {state["status"]}; request_id={job.request_id}',flush=True)
                return
            part=target.with_suffix(target.suffix+'.part')
            job.download(str(part))
            part.replace(target)
            state['downloaded_at_utc']=now()
            save(state_path,state)
        result=extract_s2s(target) if kind=='s2s' else extract_era5(target)
        state.update(status='downloaded_and_extracted',bytes=target.stat().st_size,
                     sha256=hashlib.sha256(target.read_bytes()).hexdigest(),completed_at_utc=now())
        state.pop('error',None)
        save(state_path,state)
        print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
    except Exception as exc:
        error=str(exc).replace(key,'<redacted>') if key else str(exc)
        state.update(status='blocked_or_failed',error=error,checked_at_utc=now())
        save(state_path,state)
        print(f'{kind}: {error}',flush=True)


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    parser=argparse.ArgumentParser()
    parser.add_argument('--kind',choices=['s2s','era5','all'],default='all')
    parser.add_argument('--wait',action='store_true')
    args=parser.parse_args()
    for kind in (['s2s','era5'] if args.kind=='all' else [args.kind]):collect(kind,args.wait)
