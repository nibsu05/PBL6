"""Compare training-selected station panels on the fixed R93 footprint."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely import MultiPoint,Point,box,union_all,voronoi_polygons,segmentize
from shapely.ops import transform
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1]


def spatial_weights(cells,stations):
    polygons=[box(round(r.lon-.05,6),round(r.lat-.05,6),round(r.lon+.05,6),round(r.lat+.05,6)) for r in cells.itertuples()]
    geographic=union_all(polygons)
    crs='+proj=laea +lat_0=15.7 +lon_0=108 +R=6371000 +units=m +no_defs'
    tx=Transformer.from_crs('EPSG:4326',crs,always_xy=True)
    region=transform(tx.transform,segmentize(geographic,.02))
    xy=np.column_stack(tx.transform(stations.longitude.to_numpy(),stations.latitude.to_numpy()))
    if len(np.unique(xy,axis=0))!=len(xy):raise ValueError('Duplicate station coordinates')
    vor=voronoi_polygons(MultiPoint(xy),extend_to=region.envelope.buffer(10000),ordered=True)
    pieces=[p.intersection(region) for p in vor.geoms]
    weights=np.array([p.area/region.area for p in pieces]);assert np.isclose(weights.sum(),1,atol=1e-8)
    assert abs(union_all(pieces).area-region.area)/region.area<1e-8
    sample_xy=np.column_stack(tx.transform(cells.lon.to_numpy(),cells.lat.to_numpy()))
    distances=cKDTree(xy).query(sample_xy)[0]/1000
    positive=weights>1e-10
    return weights,dict(stations_with_positive_weight=int(positive.sum()),region_km2=region.area/1e6,
                        largest_weight=float(weights.max()),effective_weight_count=float(1/(weights**2).sum()),
                        max_distance_cell_center_km=float(distances.max()),
                        area_fraction_centers_over_20km=float(cells.weight.to_numpy()[distances>20].sum()),
                        zones={zone:float(np.average(distances[cells.zone==zone],weights=cells.loc[cells.zone==zone,'weight'])) for zone in cells.zone.unique()}),geographic,region,crs


def main():
    base=ROOT/'data/operational/vrain_2026_11_09/freeze_work'
    a=np.load(base/'station_matrices.npz');valid=a['valid'];days=pd.DatetimeIndex(a['marked_day'])
    stations=pd.read_csv(base/'station_inventory_qc.csv',dtype={'station_id':str,'station_uuid':str})
    cells=pd.read_parquet(ROOT/'data/processed/regional_danang/cell_weights.parquet')
    results=[]
    for threshold in [0.,.98,.99,.995]:
        selected=(stations.valid_fraction_2021>=threshold)&(stations.valid_fraction_2022>=threshold)
        positions=np.flatnonzero(selected)
        weights,spatial,*_=spatial_weights(cells,stations.iloc[positions])
        positions=positions[weights>1e-10]
        hours=valid[:,:,positions].all(2);daily=hours.all(1)
        # Provisional count before predictor QC and exact UTC split guards.
        issues=np.arange(7,len(days)-2)
        target=issues[:,None]+np.arange(3)[None,:]
        hist=issues[:,None]+np.arange(-7,0)[None,:]
        r0=daily[target].all(1);r1=r0&daily[hist].all(1)
        result=dict(threshold=threshold,spatial=spatial,days_by_year={str(y):int(daily[days.year==y].sum()) for y in [2021,2022,2023,2024]},
                    daily_samples_R0={str(y):int((r0&(days[issues].year==y)).sum()) for y in [2021,2022,2023,2024]},
                    daily_samples_R1={str(y):int((r1&(days[issues].year==y)).sum()) for y in [2021,2022,2023,2024]})
        results.append(result)
    (base/'spatial_panel_inspection.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf8')
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
