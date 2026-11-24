"""Build identical-sample ablations; retain old values and never repair labels."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import json
import numpy as np
import pandas as pd
from src.gfs_temporal import (BASE,PUBLIC,OLD,SOURCE,CATALOG,RAIN_FEATURES,MET_FEATURES,
    sha,write_json,load_protocol,eligible_source,temporal_summaries)

def main():
    p=load_protocol();f=eligible_source();original=len(f)
    names=RAIN_FEATURES+MET_FEATURES
    feature=np.full((len(f),len(names)),np.nan,'float32');failures={};corrections=0;cache_hashes={}
    registry=pd.read_csv(BASE/'registry_private.csv');order={s:i for i,s in enumerate(registry.canonical_id)}
    for day,positions in f.groupby(f.gfs_init_utc.dt.strftime('%Y%m%d')).groups.items():
        path=BASE/'days'/f'{day}.npz'
        if not path.exists():failures[day]='source cache unavailable';continue
        info=json.loads(path.with_suffix('.json').read_text())
        if sha(path)!=info['sha256']:raise ValueError('Temporal source checksum mismatch')
        z=np.load(path);cache_hashes[day]=info['sha256']
        if not np.array_equal(z['station_ids'],registry.canonical_id):raise ValueError('Station ordering changed')
        values,flags=temporal_summaries(z['cumulative_mm'],z['packing_quantums'],z['met'])
        np.testing.assert_array_equal(values,z['features']);corrections+=int(flags.sum())
        loc=f.loc[positions];s=loc.station_id.map(order).to_numpy();h=loc.horizon.to_numpy()-1
        feature[positions]=values[h,s]
        oldrain=z['cumulative_mm'][[4,8,12]]-z['cumulative_mm'][[0,4,8]]
        np.testing.assert_allclose(np.maximum(oldrain[h,s],0),loc.gfs_rain_mm,atol=1e-5,rtol=1e-6)
    f[names]=feature
    good=np.isfinite(f[CATALOG['T3']].to_numpy()).all(1)
    packgood=good.reshape(-1,3).all(1)
    f=f.loc[np.repeat(packgood,3)].copy().reset_index(drop=True)
    expected=np.tile([1,2,3],(len(f)//3,1))
    np.testing.assert_array_equal(f.horizon.to_numpy().reshape(-1,3),expected)
    f['evaluation_set']=np.select([f.split.eq('train'),f.split.eq('cal'),f.split.eq('dev'),f.split.eq('reserved2025')],
        ['train2021_2022','cal2023','dev2024','retrospective2025_legacy'],default='retrospective2026_'+f.gauge_namespace.astype(str))
    # Independent parity with the previously frozen development table.
    old=pd.read_parquet(OLD/'predictions_private.parquet')
    keys=['issue_utc','station_id','horizon']
    shared=f[f.split.isin(['train','cal','dev'])].merge(old,on=keys,suffixes=('','_old'),validate='one_to_one')
    for name in CATALOG['T0']+['y_mm']:
        np.testing.assert_allclose(shared[name],shared[name+'_old'],atol=1e-6,rtol=0)
    path=BASE/'dataset_private.parquet';f.to_parquet(path,index=False,compression='zstd')
    write_json(BASE/'source_hashes.json',cache_hashes)
    counts=f.iloc[::3].groupby(['evaluation_set','gauge_namespace']).agg(packs=('station_id','size'),stations=('station_id','nunique'),issues=('issue_utc','nunique')).reset_index()
    counts.to_csv(PUBLIC/'sample_counts.csv',index=False,lineterminator='\n')
    write_json(PUBLIC/'dataset_verification.json',dict(status='passed',source_sha256=sha(SOURCE),dataset_sha256=sha(path),
        original_rows=original,common_rows=len(f),common_packs=len(f)//3,excluded_rows=original-len(f),
        source_issues=len(cache_hashes),new_source_failures=failures,packing_rounding_clipped=corrections,
        old_development_rows_reproduced=len(shared),features_same_samples=True,source_hash_manifest_sha256=sha(BASE/'source_hashes.json'),
        feature_counts={k:len(v) for k,v in CATALOG.items()},no_labels_filled_or_removed_by_score=True))
    print(counts.to_string(index=False));print('rows',len(f),'failures',failures)

if __name__=='__main__':main()
