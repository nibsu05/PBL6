"""Audit nhãn Đà Nẵng theo UTC; chỉ đọc giai đoạn <=2023, không chấm test 2025."""
from pathlib import Path
import sys, json
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from src.dataloader_v2 import DatasetV2
from src.verification import continuous_scores, contingency_scores

def main():
    ds = DatasetV2(ROOT / 'data/processed/dataset_v2_danang')
    out = ROOT / 'reports/domain_screen_danang'
    private = ROOT / 'data/operational/label_audit_danang'
    out.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)
    station = pd.read_parquet(ROOT/'data/processed/stations/gsod_daily.parquet',
                              filters=[('date','<',pd.Timestamp('2024-01-01'))])
    station = station[(station.usaf.astype(str)=='488550') & station.usable_year].copy()
    station['date'] = pd.to_datetime(station.date)
    lat, lon = float(station.lat.iloc[0]), float(station.lon.iloc[0])
    c_lat, c_lon = np.floor(lat*10)/10+.05, np.floor(lon*10)/10+.05
    ci = np.flatnonzero(np.isclose(ds.cells.lat,c_lat)&np.isclose(ds.cells.lon,c_lon))[0]
    dates = ds.hours.normalize()
    mask = (ds.hours.year>=2021)&(ds.hours.year<=2023)
    cube = {}
    for source, feature in [('cube_gc','y_gsmap_gc_mm'),('cube_raw','gsmap_mm'),('cube_era5','era5_tp_mm')]:
        hourly = pd.Series(np.asarray(ds.cube[ci,mask,ds.feature_index[feature]]), index=dates[mask])
        groups = hourly.groupby(level=0)
        cube[source] = groups.sum(min_count=24)
    frame = pd.DataFrame(cube)
    frame.index.name = 'date'
    frame = frame.reset_index().merge(station[['date','precip_mm']],on='date').rename(columns={'precip_mm':'station'})
    point = pd.read_parquet(ROOT/'data/processed/stations/gee_daily.parquet',
                           filters=[('date','<',pd.Timestamp('2024-01-01'))])
    point = point[point.usaf.astype(str)=='488550'].copy()
    point['date'] = pd.to_datetime(point.date)
    point = point.pivot_table(index='date',columns='source',values='precip_mm',aggfunc='first').add_prefix('point_')
    frame = frame.merge(point,on='date',how='left')
    sources = [x for x in ['cube_gc','cube_raw','cube_era5','point_gsmap_gc','point_imerg'] if x in frame]
    common = frame.dropna(subset=['station',*sources])
    rows = []
    for season, months in [('all',range(1,13)),('may_oct',range(5,11)),('nov_feb',[11,12,1,2]),('mar_apr',[3,4])]:
        sub = common[common.date.dt.month.isin(months)]
        for source in sources:
            row = dict(season=season,source=source,**continuous_scores(sub.station,sub[source]))
            for thr in [16,50,100]:
                cs = contingency_scores(sub.station,sub[source],thr)
                for k in ['CSI','POD','FAR','n_obs_events']:
                    row[f'{k}_{thr}'] = cs[k]
            rows.append(row)
    pd.DataFrame(rows).to_csv(out/'label_station_scores.csv',index=False)
    frame.to_parquet(private/'station_daily_pairs_2021_2023.parquet',index=False)
    alignment = {}
    if 'point_gsmap_gc' in frame:
        matched = frame.dropna(subset=['cube_gc','point_gsmap_gc'])
        err = matched.cube_gc-matched.point_gsmap_gc
        alignment = dict(n=len(matched),mae=float(abs(err).mean()),max_abs=float(abs(err).max()),
                         fraction_close_01mm=float((abs(err)<.1).mean()))
    correction = []
    local_months=(ds.hours[mask]+pd.Timedelta(hours=7)).month.to_numpy()
    for season, months in [('may_oct',range(5,11)),('nov_feb',[11,12,1,2]),('mar_apr',[3,4])]:
        season_mask=np.isin(local_months,list(months))
        total, raw_dry_volume, hourly_n, raw_dry_gc_wet = 0.,0.,0,0
        for c in range(len(ds.cells)):
            gc=np.asarray(ds.cube[c,mask,ds.feature_index['y_gsmap_gc_mm']])[season_mask]
            raw=np.asarray(ds.cube[c,mask,ds.feature_index['gsmap_mm']])[season_mask]
            valid=np.isfinite(gc)&np.isfinite(raw)
            total+=float(gc[valid].sum())
            raw_dry_volume+=float(gc[valid&(raw<=.01)].sum())
            raw_dry_gc_wet+=int((valid&(raw<=.01)&(gc>=.1)).sum())
            hourly_n+=int(valid.sum())
        correction.append(dict(season=season,n_cell_hours=hourly_n,
            gc_volume_mm_sum=total,fraction_gc_volume_raw_le_001=raw_dry_volume/total,
            n_raw_dry_gc_wet_hours=raw_dry_gc_wet))
    eligibility = np.isfinite(ds.cells.ne_upslope_m.to_numpy(float))
    report=dict(station_usaf='488550',station_lat=lat,station_lon=lon,
        containing_cell=ds.cells.iloc[ci].to_dict(),years=[2021,2022,2023],
        common_daily_pairs=len(common),sources=sources,cube_point_alignment=alignment,
        eligible_domain_cells=int(eligibility.sum()),total_cells=len(ds.cells),
        excluded_sites=ds.cells.loc[~eligibility,'site'].tolist(),correction_dependence=correction,
        caveats=['GSOD ngày UTC; kiểm tra hàng đủ 24 giờ.',
                 'Trạm và ô 0.1 độ khác diện tích đại diện.',
                 'GSMaP GC có hiệu chỉnh trạm nên GSOD không bảo đảm độc lập.',
                 'GC có mưa khi raw khô là chỉ báo phụ thuộc hiệu chỉnh, không chứng minh mưa thật sai giờ.',
                 'Không đọc/chấm dự báo test 2025.'])
    (out/'label_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    print(json.dumps(dict(common_pairs=len(common),alignment=alignment,eligible=report['eligible_domain_cells'],
                         correction=correction),ensure_ascii=False))

if __name__=='__main__': main()
