"""Gọi thử hợp đồng dữ liệu ECMWF; giữ snapshot ngoài Git."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import requests
import numpy as np
FIELDS=['temperature_2m','dew_point_2m','relative_humidity_2m','surface_pressure','pressure_msl',
        'wind_speed_10m','wind_direction_10m','cloud_cover','cloud_cover_low','cloud_cover_mid','cloud_cover_high',
        'precipitation','cape','convective_inhibition','total_column_integrated_water_vapour','soil_moisture_0_to_7cm',
        'temperature_850hPa','relative_humidity_850hPa','wind_speed_850hPa','wind_direction_850hPa']

def main():
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out=ROOT/'data/operational/live_contract_probe'/stamp
    out.mkdir(parents=True,exist_ok=True)
    summary=[]
    for model in ['ecmwf_ifs','ecmwf_ifs025']:
        params=dict(latitude=16.05,longitude=108.15,hourly=','.join(FIELDS),models=model,
                    timezone='UTC',forecast_days=2,past_days=2,wind_speed_unit='ms')
        response=requests.get('https://api.open-meteo.com/v1/forecast',params=params,timeout=90)
        body=response.json()
        raw=json.dumps(body,ensure_ascii=False,indent=2)
        (out/f'{model}.json').write_text(raw,encoding='utf-8')
        rows=[]
        if response.ok and 'hourly' in body:
            for name in FIELDS:
                x=np.asarray([np.nan if v is None else v for v in body['hourly'].get(name,[])],dtype=float)
                rows.append(dict(field=name,unit=body.get('hourly_units',{}).get(name),
                                 total=len(x),finite=int(np.isfinite(x).sum()),
                                 min=float(np.nanmin(x)) if np.isfinite(x).any() else None,
                                 max=float(np.nanmax(x)) if np.isfinite(x).any() else None))
        summary.append(dict(requested_model=model,http=response.status_code,
            error=body.get('reason'),latitude=body.get('latitude'),longitude=body.get('longitude'),
            fields=rows,sha256=hashlib.sha256(raw.encode()).hexdigest(),
            retrieved_at_utc=stamp,first_time=body.get('hourly',{}).get('time',[None])[0],
            last_time=body.get('hourly',{}).get('time',[None])[-1]))
        print(json.dumps(summary[-1],ensure_ascii=False),flush=True)
    report=ROOT/'reports/domain_screen_danang'
    report.mkdir(exist_ok=True,parents=True)
    (report/'live_contract_probe.json').write_text(json.dumps(dict(probes=summary,
        docs='https://open-meteo.com/en/docs/ecmwf-api',
        caveats=['Snapshot tại lúc tải, không bảo đảm đầy đủ hoặc liên tục.',
                 'past_days là chuỗi lưu trữ cập nhật, không chứng minh biết trước đúng thời điểm phát hành.',
                 'IFS025 nội suy giờ từ bước 3/6h; cần kiểm tra kho run theo thời điểm trước app.',
                 'q850 cần suy từ nhiệt độ/RH và 850hPa, kiểm tra đơn vị/parity trước triển khai.']),
        ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
