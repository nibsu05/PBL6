"""Hợp đồng khí tượng cho app; chưa thay thế kiểm định T-OPS."""
from __future__ import annotations
import numpy as np
import pandas as pd

SURFACE_MAP={'temperature_2m':'t2m_c','dew_point_2m':'td2m_c','relative_humidity_2m':'rh2m_pct',
             'surface_pressure':'sp_hpa','pressure_msl':'mslp_hpa'}
CLOUD_MAP={'cloud_cover':'tcc','cloud_cover_low':'lcc','cloud_cover_mid':'mcc','cloud_cover_high':'hcc'}

def wind_uv(speed_ms,direction_degrees):
    """Hướng khí tượng là hướng gió đến từ; u đông và v bắc dương."""
    s=np.asarray(speed_ms,float);theta=np.deg2rad(np.asarray(direction_degrees,float))
    if not np.isfinite(s).all() or not np.isfinite(theta).all() or np.any(s<0):
        raise ValueError('Gió không hữu hạn hoặc tốc độ âm')
    return -s*np.sin(theta),-s*np.cos(theta)

def specific_humidity_gkg(temperature_c,rh_pct,pressure_hpa=850.):
    """Suy q từ RH/T (Magnus nước lỏng); chưa tương đương q ERA5 tuyệt đối."""
    t=np.asarray(temperature_c,float);rh=np.asarray(rh_pct,float)
    if not np.isfinite(t).all() or not np.isfinite(rh).all() or np.any((rh<0)|(rh>100)):
        raise ValueError('T/RH không hợp lệ')
    e=(rh/100)*6.112*np.exp(17.67*t/(t+243.5))
    if np.any(e>=pressure_hpa):raise ValueError('Áp suất hơi không vật lý')
    return 1000*.622*e/(pressure_hpa-.378*e)

def weather_frame(surface,pressure):
    """Gộp hai payload chỉ khi timestamp UTC giống hệt. Không điền dữ liệu thiếu."""
    if surface.get('utc_offset_seconds',0)!=0 or pressure.get('utc_offset_seconds',0)!=0:
        raise ValueError('Payload phải UTC')
    checks=[(surface,{'temperature_2m':'°C','dew_point_2m':'°C','relative_humidity_2m':'%',
                     'surface_pressure':'hPa','pressure_msl':'hPa','wind_speed_10m':'m/s','wind_direction_10m':'°',
                     'cloud_cover':'%','cloud_cover_low':'%','cloud_cover_mid':'%','cloud_cover_high':'%',
                     'total_column_integrated_water_vapour':'kg/m²'}),
            (pressure,{'temperature_850hPa':'°C','relative_humidity_850hPa':'%',
                       'wind_speed_850hPa':'m/s','wind_direction_850hPa':'°'})]
    for payload,expected in checks:
        for field,unit in expected.items():
            if payload.get('hourly_units',{}).get(field)!=unit:raise ValueError('Sai/thiếu đơn vị '+field)
    sh,ph=surface['hourly'],pressure['hourly']
    st,pt=pd.to_datetime(sh['time'],utc=True),pd.to_datetime(ph['time'],utc=True)
    if not st.equals(pt) or not st.is_unique or not st.is_monotonic_increasing:
        raise ValueError('Hai nguồn không cùng thời gian UTC duy nhất tăng dần')
    frame=pd.DataFrame(index=st)
    def take(payload,name):
        if name not in payload:raise ValueError('Thiếu trường '+name)
        x=np.asarray(payload[name],float)
        if len(x)!=len(st) or not np.isfinite(x).all():raise ValueError('Thiếu/NaN '+name)
        return x
    for source,target in SURFACE_MAP.items():frame[target]=take(sh,source)
    for source,target in CLOUD_MAP.items():
        x=take(sh,source)
        if np.any((x<0)|(x>100)):raise ValueError('Mây phải %')
        frame[target]=x/100
    frame['u10'],frame['v10']=wind_uv(take(sh,'wind_speed_10m'),take(sh,'wind_direction_10m'))
    frame['tcwv']=take(sh,'total_column_integrated_water_vapour')
    frame['u850'],frame['v850']=wind_uv(take(ph,'wind_speed_850hPa'),take(ph,'wind_direction_850hPa'))
    frame['q850_gkg']=specific_humidity_gkg(take(ph,'temperature_850hPa'),take(ph,'relative_humidity_850hPa'))
    return frame
