"""Lưu snapshot forecast khí tượng của93ô, ghi thời điểm tải và grid nguồn.

Không chạy checkpoint ML: thiếu quan trắc NRT đã kiểm định. Không khẳng định init_time.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,logging,sys,time
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import requests
import numpy as np
import pandas as pd
from src.live_domain_inputs import weather_frame

SURFACE=['temperature_2m','dew_point_2m','relative_humidity_2m','surface_pressure','pressure_msl',
         'wind_speed_10m','wind_direction_10m','cloud_cover','cloud_cover_low','cloud_cover_mid','cloud_cover_high',
         'precipitation','cape','convective_inhibition','total_column_integrated_water_vapour','soil_moisture_0_to_7cm']
PRESSURE=['temperature_850hPa','relative_humidity_850hPa','wind_speed_850hPa','wind_direction_850hPa']
LOG=logging.getLogger('collect')

def collect_once(batch_size=20):
    cells=pd.read_parquet(ROOT/'data/processed/dataset_v2_danang/cells.parquet')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out=ROOT/'data/operational/domain_live_snapshots'/stamp
    out.mkdir(parents=True,exist_ok=True)
    payloads={}
    entries=[]
    session=requests.Session()
    for model,fields in [('ecmwf_ifs',SURFACE),('ecmwf_ifs025',PRESSURE)]:
        all_payload=[]
        for start in range(0,len(cells),batch_size):
            part=cells.iloc[start:start+batch_size]
            params=dict(latitude=','.join(map(str,part.lat)),longitude=','.join(map(str,part.lon)),
                        models=model,hourly=','.join(fields),wind_speed_unit='ms',timezone='UTC',
                        past_days=2,forecast_days=4,cell_selection='nearest',elevation=','.join(['nan']*len(part)))
            response=session.get('https://api.open-meteo.com/v1/forecast',params=params,timeout=90)
            if not response.ok:
                (out/f'{model}_{start:03d}_error.json').write_text(response.text,encoding='utf-8')
            response.raise_for_status()
            content=response.content
            filename=f'{model}_{start:03d}.json'
            (out/filename).write_bytes(content)
            body=response.json()
            group=body if isinstance(body,list) else [body]
            if len(group)!=len(part):raise ValueError('API trả sai số tọa độ')
            for payload,(_,cell) in zip(group,part.iterrows()):
                all_payload.append(payload)
                entries.append(dict(site=cell.site,model=model,request_lat=cell.lat,request_lon=cell.lon,
                    returned_lat=payload.get('latitude'),returned_lon=payload.get('longitude'),
                    elevation=payload.get('elevation'),retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                    file=filename,sha256=hashlib.sha256(content).hexdigest()))
            LOG.info('%s cells %s-%s saved',model,start,start+len(part)-1)
            time.sleep(1)
        payloads[model]=all_payload
    successful,failed,failures=0,0,[]
    for i,cell in cells.iterrows():
        try:
            frame=weather_frame(payloads['ecmwf_ifs'][i],payloads['ecmwf_ifs025'][i])
            frame.index.name='valid_at'
            frame.to_parquet(out/f'weather_{cell.site}.parquet')
            successful+=1
        except ValueError as exc:
            failed+=1;failures.append(dict(site=cell.site,reason=str(exc)))
    manifest=dict(retrieved_start_utc=stamp,requested_cells=len(cells),weather_contract_passed=successful,
                  failed=failed,failures=failures,entries=entries,
                  init_time_known=False,ready_for_ml=False,
                  reason='Chưa có GSMaP NRT/IMERG Early đã kiểm định và chưa có kiểm định T-OPS; chỉ ghi khí tượng.',
                  query_options=dict(cell_selection='nearest',elevation='nan',timezone='UTC',wind_speed_unit='ms'),
                  spatial_caveat='Nearest native IFS grid; chưa là bilinear spatial parity với ERA5.')
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    public=dict(snapshot_id=stamp,requested_cells=len(cells),weather_contract_passed=successful,failed=failed,
                failures=failures,init_time_known=False,ready_for_ml=False,source_models=list(payloads))
    report=ROOT/'reports/domain_screen_danang'
    report.mkdir(parents=True,exist_ok=True)
    (report/'live_collection_status.json').write_text(json.dumps(public,ensure_ascii=False,indent=2),encoding='utf-8')
    LOG.info('Complete %s contract %s/%s',stamp,successful,len(cells))
    return public

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--hours',type=float,default=0,help='0 = một lượt, >0 = lặp tới thời lượng này')
    ap.add_argument('--interval',type=int,default=3600)
    args=ap.parse_args()
    if args.hours<0 or args.interval<900:raise ValueError('hours>=0, interval>=900')
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    deadline=time.monotonic()+args.hours*3600
    while True:
        try:collect_once()
        except Exception:
            LOG.exception('Collection failed')
            if args.hours==0:raise
        if args.hours==0 or time.monotonic()+args.interval>deadline:break
        time.sleep(args.interval)
if __name__=='__main__':main()
