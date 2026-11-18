"""Score frozen new models; all post2024 results are explicitly retrospective."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from datetime import datetime,timezone
import json
import os
from importlib.metadata import version
import joblib
import numpy as np
import pandas as pd
import torch
from threadpoolctl import threadpool_limits
from src.gfs_temporal import BASE,PUBLIC,OLD,CATALOG,SEEDS,sha,write_json,load_protocol
from src.gfs_temporal_models import replay_gru,calibrated
from src.gfs_temporal_evaluation import paired_comparisons,amount_error_diagnostics
from src.gfs_daily_models import predict_tree,climatology
from src.gfs_final_metrics import summary_tables

MODELS=['ZERO','CLIM','PERSISTENCE','GFS','MOS','LGB_T0','LGB_T1','LGB_T2','LGB_T3','GRU_T0','GRU_T3','GRU_LINEAR23']

def assert_freeze():
    p=load_protocol();freeze=json.loads((BASE/'model_freeze.json').read_text())
    if sha(BASE/'training_lock.json')!=freeze['training_lock_sha256']:raise ValueError('Training lock changed')
    lock=json.loads((BASE/'training_lock.json').read_text())
    if any(version(name)!=expected for name,expected in lock['environment'].items()):raise ValueError('Locked software environment changed')
    for name,expected in lock['code'].items():
        if sha(ROOT/name)!=expected:raise ValueError('Locked source changed: '+name)
    for name,expected in lock['baseline_dependencies'].items():
        if sha(ROOT/name)!=expected:raise ValueError('Baseline input changed: '+name)
    if sha(BASE/'dataset_private.parquet')!=lock['dataset']:raise ValueError('Dataset changed')
    for name,expected in freeze['artifacts'].items():
        if sha(ROOT/name)!=expected:raise ValueError('Frozen artifact changed: '+name)
    return p

def predict_all(f,callback=None):
    f=f.sort_values(['issue_utc','station_id','horizon']).reset_index(drop=True).copy();seed_outputs={}
    for config,names in CATALOG.items():
        label='LGB_'+config;values=[{k:np.zeros(len(f)) for k in ('mean','median','p1','p50')} for _ in SEEDS]
        for h in (1,2,3):
            mask=f.horizon.eq(h).to_numpy();sub=f.loc[mask];pairs=joblib.load(BASE/'models'/f'{label}_d{h}_calibrators.joblib')
            for j,seed in enumerate(SEEDS):
                a=joblib.load(BASE/'models'/f'{label}_d{h}_seed{seed}.joblib')
                if a['features']!=names:raise ValueError('Tree feature mismatch')
                raw={head:predict_tree(est,names,sub,head) for head,est in a['models'].items()}
                prob=calibrated(raw['wet'],raw['conditional'],pairs[j])
                for head in ('mean','median'):values[j][head][mask]=raw[head]
                values[j]['p1'][mask]=prob[:,0];values[j]['p50'][mask]=prob[:,1]
        seed_outputs[label]=values
        for head in values[0]:f[label+'_'+head]=np.mean([v[head] for v in values],0)
        if callback:callback(label)
    for config in ('T0','T3','LINEAR23'):
        label='GRU_'+config;values=[]
        for j,seed in enumerate(SEEDS):
            a=torch.load(BASE/'models'/f'{label}_seed{seed}.pt',map_location='cpu',weights_only=False)
            raw=replay_gru(f,a);value=dict(mean=raw['mean'].ravel(),median=raw['median'].ravel(),p1=np.zeros(len(f)),p50=np.zeros(len(f)))
            for h in (1,2,3):
                mask=f.horizon.eq(h).to_numpy();pairs=joblib.load(BASE/'models'/f'{label}_d{h}_calibrators.joblib')
                prob=calibrated(raw['wet'][:,h-1],raw['conditional'][:,h-1],pairs[j]);value['p1'][mask]=prob[:,0];value['p50'][mask]=prob[:,1]
            values.append(value)
        seed_outputs[label]=values
        for head in values[0]:f[label+'_'+head]=np.mean([v[head] for v in values],0)
        if callback:callback(label)
    ref=climatology(f)
    for name in ref:f['CLIM_'+name]=ref[name].to_numpy()
    for label,amount in [('ZERO',np.zeros(len(f))),('GFS',f.gfs_rain_mm.to_numpy()),('PERSISTENCE',f.rain_recent24h_mm.to_numpy())]:
        for head in ('mean','median'):f[label+'_'+head]=amount
        for t in (1,50):f[f'{label}_p{t}']=(amount>=t).astype(float)
    for h in (1,2,3):
        mask=f.horizon.eq(h).to_numpy();sub=f.loc[mask];a=joblib.load(OLD/'models'/f'MOS_d{h}.joblib')
        x=a['scaler'].transform(sub[a['features']])
        for head in ('mean','median'):f.loc[mask,'MOS_'+head]=np.maximum(a[head].predict(x),0)
        wet,conditional=[m.predict_proba(x)[:,1] for m in a['classifiers']]
        prob=calibrated(wet,conditional,a['calibrators'][0]);f.loc[mask,'MOS_p1']=prob[:,0];f.loc[mask,'MOS_p50']=prob[:,1]
    for model in MODELS:
        a=f[[model+'_'+k for k in ('mean','median','p1','p50')]].to_numpy()
        if not np.isfinite(a).all() or (a<0).any() or (a[:,2:]>1).any() or (a[:,3]>a[:,2]+1e-12).any():raise ValueError('Invalid output '+model)
    return f,seed_outputs

def progress(stage,**details):
    write_json(BASE/'scoring_progress.json',dict(stage=stage,pid=os.getpid(),updated_utc=datetime.now(timezone.utc).isoformat(),**details))

def main():
    p=assert_freeze();torch.set_num_threads(4)
    f=pd.read_parquet(BASE/'dataset_private.parquet');f=f[~f.split.isin(['train','cal'])].reset_index(drop=True)
    predictions=BASE/'evaluation_predictions_private.parquet';seedpath=BASE/'seed_outputs_private.npz'
    if not predictions.exists():
        progress('inference');f,seeds=predict_all(f,lambda m:progress('inference',model=m))
        f.to_parquet(predictions,index=False,compression='zstd')
        np.savez_compressed(seedpath,**{f'{m}__{j}__{k}':v[k] for m,vs in seeds.items() for j,v in enumerate(vs) for k in v})
    else:f=pd.read_parquet(predictions)
    cuts=json.loads((PUBLIC/'decision_cutoffs.json').read_text())
    oldcuts=json.loads((ROOT/'reports/gfs_station_daily_v2_2026_11_10/decision_cutoffs.json').read_text())
    cuts=[*cuts,*[c for c in oldcuts if c['model']=='MOS']]
    cutoffs={(r['model'],r['horizon']):r['cutoff'] for r in cuts}
    progress('metrics')
    tables=summary_tables(f,MODELS,cutoffs)
    for name,table in tables.items():table.to_csv((BASE if name.endswith('_private') else PUBLIC)/(name+'.csv'),index=False,lineterminator='\n')
    amount_error_diagnostics(f,MODELS).to_csv(PUBLIC/'error_contribution.csv',index=False,lineterminator='\n')
    progress('bootstrap')
    with threadpool_limits(limits=2):paired_comparisons(f,p).to_csv(PUBLIC/'paired_comparisons.csv',index=False,lineterminator='\n')
    # Seed-level amount/probability metrics, rather than treating seeds as data replicas.
    z=np.load(seedpath);rows=[]
    for model in [m for m in MODELS if m.startswith(('LGB_','GRU_'))]:
        for j,seed in enumerate(SEEDS):
            for (scope,h),indices in f.groupby(['evaluation_set','horizon']).groups.items():
                sub=f.loc[indices];y=sub.y_mm.to_numpy();sid=sub.station_id.to_numpy()
                for functional,metric in [('mean','macro_rmse'),('median','macro_mae')]:
                    error=z[f'{model}__{j}__{functional}'][indices]-y
                    per=pd.Series(error**2 if functional=='mean' else abs(error)).groupby(sid).mean()
                    value=float(np.sqrt(per).mean() if functional=='mean' else per.mean())
                    rows.append(dict(evaluation_set=scope,horizon=int(h),model=model,seed=seed,metric=metric,value=value))
    pd.DataFrame(rows).to_csv(PUBLIC/'seed_metrics.csv',index=False,lineterminator='\n')
    assert_freeze();progress('complete',rows=len(f),models=len(MODELS))

if __name__=='__main__':main()
