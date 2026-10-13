"""Đọc GSMaP_NRT binary và ghép đúng mặt nạ context của datasetv2."""
from __future__ import annotations
import gzip,io,re
from pathlib import Path
import numpy as np
import pandas as pd
from src.dataset_v2 import neighbourhood_stats
SHAPE=(1200,3600)
BYTE_COUNT=1200*3600*4

def decode_nrt_binary(payload):
    if payload[:2]==b'\x1f\x8b':
        with gzip.GzipFile(fileobj=io.BytesIO(payload)) as f:
            payload=f.read(BYTE_COUNT+1)
    if len(payload)!=BYTE_COUNT:raise ValueError('BinaryNRT phải đúng1200x3600 float32LE')
    grid=np.frombuffer(payload,dtype='<f4').reshape(SHAPE)
    return np.where(np.isfinite(grid)&(grid>=0),grid,np.nan).astype(np.float32)

def native_indices(lat,lon):
    lat=np.asarray(lat,float);lon=np.asarray(lon,float)%360
    i=np.rint((59.95-lat)/.1).astype(int)
    j=np.rint((lon-.05)/.1).astype(int)
    if np.any((i<0)|(i>=1200)|(j<0)|(j>=3600)):raise ValueError('Ngoài lướiNRT60N–60S')
    if not np.allclose(lat,59.95-i*.1,atol=1e-5) or not np.allclose(lon,.05+j*.1,atol=1e-5):
        raise ValueError('Cần tâm ô0,1°, không tự dịch nửaô')
    return i,j

def features_for_context(grid,context_cells,target_sites=None):
    if grid.shape!=SHAPE:raise ValueError('Sai shape gridNRT')
    i,j=native_indices(context_cells.lat,context_cells.lon)
    values=grid[i,j]
    # Dùng đúng296ô context cũ; không lén thêm pixelbiển vào5x5 đã train.
    mean,maximum=neighbourhood_stats(values[None,:],context_cells.lat.to_numpy(),context_cells.lon.to_numpy())
    frame=pd.DataFrame(dict(site=context_cells.site.to_numpy(),gsmap_mm=values,
        gsmap_nb5_mean_mm=mean[0],gsmap_nb5_max_mm=maximum[0]))
    if target_sites is not None:
        frame=frame.set_index('site').loc[list(target_sites)].reset_index()
    return frame

def interval_from_filename(name):
    match=re.fullmatch(r'gsmap_nrt\.(\d{8})\.(\d{2})00\.dat(?:\.gz)?',Path(name).name)
    if not match:raise ValueError('Chỉ rawgsmap_nrt hourly; không gauge/NOW hoặc tên khác')
    t=pd.to_datetime(match.group(1)+match.group(2),format='%Y%m%d%H',utc=True)
    return t,t+pd.Timedelta(hours=1)
