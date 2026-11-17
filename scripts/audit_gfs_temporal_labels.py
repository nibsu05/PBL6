"""Posthoc spatial/satellite context, never automatic deletion of extreme labels."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import json
import numpy as np
import pandas as pd
from src.gfs_temporal import BASE,PUBLIC,sha,write_json

def distances(lat,lon):
    lat=np.radians(np.asarray(lat));lon=np.radians(np.asarray(lon))
    a=np.sin((lat[:,None]-lat[None,:])/2)**2+np.cos(lat[:,None])*np.cos(lat[None,:])*np.sin((lon[:,None]-lon[None,:])/2)**2
    return 6371*2*np.arcsin(np.sqrt(np.clip(a,0,1)))

def satellite_context(registry):
    folder=ROOT/'data/raw_data/gee/gsmap/grid'
    files=sorted(p for p in folder.glob('*.parquet') if '20240101'<=p.name[:8]<='20261001')
    if not files:return None,None,dict(status='unavailable')
    meta=pd.read_parquet(files[0],columns=['site','pixel_lat','pixel_lon']).drop_duplicates('site')
    mapping=[]
    for row in registry.itertuples():
        lat=np.radians(meta.pixel_lat.to_numpy());lon=np.radians(meta.pixel_lon.to_numpy())
        a=np.sin((lat-np.radians(row.latitude))/2)**2+np.cos(lat)*np.cos(np.radians(row.latitude))*np.sin((lon-np.radians(row.longitude))/2)**2
        dist=6371*2*np.arcsin(np.sqrt(np.clip(a,0,1)));i=int(np.argmin(dist))
        mapping.append(dict(station_id=row.canonical_id,site=meta.site.iloc[i],distance_km=float(dist[i])))
    mapping=pd.DataFrame(mapping);chosen=mapping.site.unique().tolist();pieces=[]
    for path in files:
        f=pd.read_parquet(path,columns=['time_start_utc','site','hourlyPrecipRate_mm'],filters=[('site','in',chosen)])
        pieces.append(f)
    f=pd.concat(pieces,ignore_index=True);f['time_start_utc']=pd.to_datetime(f.time_start_utc,utc=True)
    duplicate=f.duplicated(['time_start_utc','site'],keep=False)
    if duplicate.any():
        if f[duplicate].groupby(['time_start_utc','site']).hourlyPrecipRate_mm.nunique(dropna=False).gt(1).any():raise ValueError('Inconsistent overlapping GSMaP hours')
        f=f.drop_duplicates(['time_start_utc','site'])
    f['marked_day']=(f.time_start_utc+pd.Timedelta(hours=12)).dt.tz_localize(None).dt.normalize()
    f.loc[f.hourlyPrecipRate_mm.lt(0),'hourlyPrecipRate_mm']=np.nan
    g=f.groupby(['marked_day','site']).hourlyPrecipRate_mm.agg(['sum','count']).reset_index()
    g.loc[g['count'].ne(24),'sum']=np.nan
    return g,mapping,dict(status='available',source='GSMaP hourlyPrecipRate_mm, not gauge-adjusted GC',
        complete_24h_required=True,grid_degrees=.1,files=len(files),first_hour_utc=str(f.time_start_utc.min()),last_hour_utc=str(f.time_start_utc.max()),
        maximum_nearest_pixel_distance_km=float(mapping.distance_km.max()),
        caveat='independent product context, not point-gauge truth or proof of sensor accuracy')

def main():
    BASE.mkdir(parents=True,exist_ok=True);PUBLIC.mkdir(parents=True,exist_ok=True)
    final=ROOT/'data/operational/gfs_station_final_2026_11_17'
    dev=pd.read_parquet(final/'development_predictions_private.parquet',filters=[('split','==','dev')])
    dev['gauge_namespace']='legacy';dev['evaluation_set']='dev2024'
    f=pd.concat([dev,pd.read_parquet(final/'holdout_predictions_private.parquet')],ignore_index=True)
    f=f.drop_duplicates(['gauge_namespace','station_id','target_end_utc']).copy()
    f['marked_day']=f.target_end_utc.dt.tz_convert('Asia/Ho_Chi_Minh').dt.tz_localize(None).dt.normalize()
    registry=pd.read_csv(ROOT/'data/operational/vrain_update_2026_11_16/station_registry_private.csv').sort_values('canonical_id').reset_index(drop=True)
    z=np.load(ROOT/'data/operational/vrain_update_2026_11_16/rain_channels.npz')
    if not np.array_equal(z['station_ids'],registry.canonical_id):raise ValueError('Gauge registry order mismatch')
    valid=z['valid'] & ~z['bad_daily_sum'][:,:,None,:] & ~z['conflict'][None,...]
    hourly=np.where(valid,z['raw'],np.nan);daily=hourly.sum(2)
    marked=pd.DatetimeIndex(z['marked_day']);days={d:i for i,d in enumerate(marked)};stations={s:i for i,s in enumerate(registry.canonical_id)}
    distance=distances(registry.latitude,registry.longitude);near=(distance<=30)&(distance>0)
    satellite,mapping,satinfo=satellite_context(registry)
    if satellite is not None:
        mapping.to_csv(BASE/'satellite_mapping_private.csv',index=False)
        mapped=mapping.set_index('station_id').site.to_dict();lookup=satellite.set_index(['marked_day','site'])['sum'].to_dict()
    rows=[]
    for row in f.itertuples():
        channel=0 if row.gauge_namespace=='legacy' else 1;d=days[row.marked_day];s=stations[row.station_id]
        value=daily[channel,d,s]
        if not np.isclose(value,row.y_mm,atol=1e-4,rtol=1e-6):raise ValueError('QC daily replay mismatch')
        neighbor=daily[channel,d,near[s]];neighbor=neighbor[np.isfinite(neighbor)]
        median=float(np.median(neighbor)) if len(neighbor) else np.nan
        largest=float(np.max(hourly[channel,d,:,s]));fraction=largest/value if value>0 else 0.
        flag=bool(value>=200 and len(neighbor)>=3 and median<=10 and value-median>=150 and value>=10*max(median,1))
        sat=lookup.get((row.marked_day,mapped[row.station_id]),np.nan) if satellite is not None else np.nan
        rows.append(dict(evaluation_set=row.evaluation_set,station_id=row.station_id,gauge_namespace=row.gauge_namespace,
            target_end_utc=row.target_end_utc,y_mm=float(value),neighbors_30km=len(neighbor),neighbor_median_mm=median,
            neighbors_ge50=int((neighbor>=50).sum()),max_hour_mm=largest,max_hour_fraction=fraction,
            spatial_review_flag=flag,hour_concentration_review_flag=bool(value>=50 and fraction>=.8),
            gsmap_raw_mm=float(sat)))
    audit=pd.DataFrame(rows);audit.to_parquet(BASE/'label_context_private.parquet',index=False,compression='zstd')
    summaries=[];product=[]
    for scope,g in audit.groupby('evaluation_set'):
        extreme=g[g.y_mm>=200];heavy=g[g.y_mm>=50];paired=g[g.gsmap_raw_mm.notna()]
        summaries.append(dict(evaluation_set=scope,unique_station_days=len(g),days_ge50=len(heavy),days_ge200=len(extreme),
            extreme_with_at_least3_neighbors=int(extreme.neighbors_30km.ge(3).sum()),
            extreme_with_neighbor_ge50=int(extreme.neighbors_ge50.gt(0).sum()),
            spatial_review_flags=int(g.spatial_review_flag.sum()),hour_concentration_flags=int(g.hour_concentration_review_flag.sum()),
            extreme_with_gsmap_context=int(extreme.gsmap_raw_mm.notna().sum()),
            extreme_with_gsmap_ge50=int(extreme.gsmap_raw_mm.ge(50).sum()),labels_removed=0))
        for name,sub in [('all',paired),('gauge_ge50',paired[paired.y_mm>=50]),('gauge_ge200',paired[paired.y_mm>=200])]:
            if not len(sub):continue
            error=sub.gsmap_raw_mm-sub.y_mm
            product.append(dict(evaluation_set=scope,subset=name,n=len(sub),mean_gauge_mm=float(sub.y_mm.mean()),
                mean_satellite_mm=float(sub.gsmap_raw_mm.mean()),satellite_minus_gauge_bias=float(error.mean()),
                absolute_difference_mm=float(abs(error).mean()),correlation=float(sub.y_mm.corr(sub.gsmap_raw_mm)) if len(sub)>2 else None))
    pd.DataFrame(summaries).to_csv(PUBLIC/'label_context_summary.csv',index=False,lineterminator='\n')
    pd.DataFrame(product).to_csv(PUBLIC/'independent_product_context.csv',index=False,lineterminator='\n')
    write_json(PUBLIC/'label_context_audit.json',dict(status='complete',daily_matrix_replay_rows=len(audit),no_labels_changed=True,
        spatial_rule='>=200mm/24h, >=3 valid gauges within30km, neighbor median<=10mm, difference>=150mm and ratio>=10; diagnostic, not a standard or exclusion rule',
        hourly_rule='>=50mm/24h and >=80percent in one hour; diagnostic only',satellite=satinfo,
        gsod_not_used='UTC calendar-day summaries cannot validate the different19h-to19h Vietnam windows without hourly reaggregation',
        source_continuity='two APIs from one provider, not independent sensors; cause of coverage transition remains unconfirmed',
        physical_sensor_validation_completed=False,
        references=['https://sharaku.eorc.jaxa.jp/GSMaP/faq/GSMaP_faq03.html',
                    'https://www.eorc.jaxa.jp/GPM/doc/product/format/en/07.GPM_GSMaP_Product_Format_E.pdf',
                    'https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc%3AC00516']))
    print(pd.DataFrame(summaries).to_string(index=False))

if __name__=='__main__':main()
