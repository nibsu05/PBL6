"""Replay checkpoints/calibrators, independent metrics and preservation checks."""
from pathlib import Path
import json
import sys
import platform
import importlib.metadata
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import joblib
import numpy as np
import pandas as pd
import torch
from threadpoolctl import threadpool_limits
from src.gfs_daily import BASE,PUBLIC,DATA,FEATURES,load_protocol,sha,write_json,with_delay,calibrate_nested,nested_probabilities
from src.gfs_daily_lock import training_lock
from src.gfs_daily_models import predict_tree,climatology
from src.gfs_daily_gru import replay,arrays,normalizers


def equal(a,b):np.testing.assert_allclose(a,b,rtol=1e-5,atol=3e-5)


def mean_station(values,stations,root=False):
    per=pd.Series(np.asarray(values)).groupby(np.asarray(stations)).mean()
    return float(np.sqrt(per).mean() if root else per.mean())


def seed_metrics(frame,model,seed,out,prob):
    result=[]
    for h in (1,2,3):
        mask=(frame.split.eq('dev')&frame.horizon.eq(h)).to_numpy();y=frame.loc[mask,'y_mm'].to_numpy();sid=frame.loc[mask,'station_id'].to_numpy()
        result.append(dict(model=model,seed=int(seed),horizon=h,
            mean_rmse=mean_station((out['mean'][mask]-y)**2,sid,True),median_mae=mean_station(abs(out['median'][mask]-y),sid),
            bs1=mean_station((prob[mask,0]-(y>=1))**2,sid),bs50=mean_station((prob[mask,1]-(y>=50))**2,sid)))
    return result


def main():
    threadpool_limits(limits=4);torch.set_num_threads(4)
    write_json(PUBLIC/'runtime_environment.json',dict(captured_utc=datetime.now(timezone.utc).isoformat(),
        captured_at='checkpoint verification',python=platform.python_version(),operating_system=platform.system(),
        packages={name:importlib.metadata.version(name) for name in ['torch','lightgbm','scikit-learn','numpy','pandas','scipy','eccodes','python-docx','matplotlib']},
        cuda_runtime=torch.version.cuda,gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        gpu_memory_bytes=torch.cuda.get_device_properties(0).total_memory if torch.cuda.is_available() else None))
    lock=training_lock();p=load_protocol();frame=pd.read_parquet(BASE/'predictions_private.parquet');source=pd.read_parquet(DATA/'dataset.parquet')
    pd.testing.assert_frame_equal(frame[source.columns],source)
    tree=json.loads((PUBLIC/'tree_summary.json').read_text());selection=json.loads((PUBLIC/'tree_selection.json').read_text())
    seeds=[];replayed=0;calibrators=0
    for label in [s for s in tree['models'] if s.startswith('LGB_')]:
        config=label.split('_')[1];delay=int(label.split('delay')[1]) if 'delay' in label else 1
        byseed={seed:dict(mean=np.zeros(len(frame)),median=np.zeros(len(frame)),prob=np.zeros((len(frame),2))) for seed in p['seeds']}
        for h in (1,2,3):
            pos=frame.horizon.eq(h).to_numpy();f=with_delay(frame.loc[pos].reset_index(drop=True),delay);pred=[];prob=[]
            cal=joblib.load(BASE/'models'/f'{label}_d{h}_calibrators.joblib')
            for j,seed in enumerate(p['seeds']):
                artifact=joblib.load(BASE/'models'/f'{label}_d{h}_seed{seed}.joblib')
                assert artifact['dataset_sha256']==lock['dataset_sha256'] and artifact['features']==FEATURES[config] and artifact['delay']==delay
                out={}
                for head,model in artifact['models'].items():
                    if hasattr(model,'get_params'):
                        actual=model.get_params();chosen=selection['selected'][head]
                        assert actual['n_estimators']==chosen['trees'][str(h)] and actual['random_state']==seed
                        for key,value in chosen['candidate'].items():
                            if key!='name':assert actual[key]==value
                        assert model.best_iteration_==0
                    out[head]=predict_tree(model,FEATURES[config],f,head);replayed+=1
                expected,_=calibrate_nested(out['wet'],out['conditional'],f.y_mm.to_numpy(),f.split.eq('cal').to_numpy())
                actual=nested_probabilities(cal[j][0].predict(out['wet']),cal[j][1].predict(out['conditional']))
                equal(expected,actual);calibrators+=2;prob.append(actual);pred.append(out)
                for head in ('mean','median'):byseed[seed][head][pos]=out[head]
                byseed[seed]['prob'][pos]=actual
            for head in ('mean','median'):equal(np.mean([o[head] for o in pred],0),f[label+'_'+head])
            equal(np.mean(prob,0),f[[label+'_p1',label+'_p50']])
        for seed,values in byseed.items():seeds+=seed_metrics(frame,label,seed,values,values['prob'])
        print(json.dumps(dict(verified=label,estimators=replayed)),flush=True)
    reference=climatology(source)
    for col in reference:equal(frame['CLIM_'+col],reference[col])
    for label,point in [('ZERO',np.zeros(len(frame))),('GFS',frame.gfs_rain_mm),('PERSISTENCE',frame.rain_recent24h_mm)]:
        for head in ('mean','median'):equal(frame[label+'_'+head],point)
        for t in (1,50):equal(frame[f'{label}_p{t}'],np.asarray(point)>=t)
    for h in (1,2,3):
        f=frame[frame.horizon.eq(h)];artifact=joblib.load(BASE/'models'/f'MOS_d{h}.joblib');names=artifact['features']
        equal(artifact['scaler'].mean_,f.loc[f.split.eq('train'),names].mean())
        x=artifact['scaler'].transform(f[names])
        for head in ('mean','median'):equal(np.maximum(artifact[head].predict(x),0),f['MOS_'+head])
        wet,conditional=[m.predict_proba(x)[:,1] for m in artifact['classifiers']]
        probability,_=calibrate_nested(wet,conditional,f.y_mm,f.split.eq('cal'))
        equal(probability,f[['MOS_p1','MOS_p50']]);calibrators+=2
    gru_selection=json.loads((PUBLIC/'gru_selection.json').read_text());neural=0
    train=source.iloc[::3].split.eq('train').to_numpy()
    for config in p['gru_configurations']:
        label='GRU_'+config;outputs=[];prob=[]
        for j,seed in enumerate(p['seeds']):
            artifact=torch.load(BASE/'models'/f'{label}_seed{seed}.pt',map_location='cpu',weights_only=False)
            assert artifact['dataset_sha256']==lock['dataset_sha256'] and artifact['epochs']==gru_selection['epochs']
            assert artifact['candidate']==gru_selection['candidate'] and artifact['seed']==seed
            fresh=normalizers(arrays(source,config),train)
            for key in fresh:equal(fresh[key],artifact['normalizers'][key])
            out=replay(source,artifact);outputs.append(out);q=np.zeros((len(frame),2))
            for h in (1,2,3):
                mask=frame.horizon.eq(h).to_numpy();f=frame.loc[mask]
                wet,cond=out['wet'][:,h-1],out['conditional'][:,h-1]
                actual,_=calibrate_nested(wet,cond,f.y_mm,f.split.eq('cal'))
                cal=joblib.load(BASE/'models'/f'{label}_d{h}_calibrators.joblib')[j]
                equal(actual,nested_probabilities(cal[0].predict(wet),cal[1].predict(cond)));calibrators+=2;q[mask]=actual
            prob.append(q);neural+=1
            seeds+=seed_metrics(frame,label,seed,{k:v.ravel() for k,v in out.items()},q)
        for head in ('mean','median'):equal(np.mean([o[head] for o in outputs],0).ravel(),frame[label+'_'+head])
        equal(np.mean(prob,0),frame[[label+'_p1',label+'_p50']])
        print(json.dumps(dict(verified=label,neural_models=neural)),flush=True)
    models=tree['models']+['GRU_'+c for c in p['gru_configurations']]
    cutoffs=json.loads((PUBLIC/'decision_cutoffs.json').read_text());cut={(r['model'],r['horizon']):r['cutoff'] for r in cutoffs}
    assert len(cut)==len(cutoffs)
    for model in models:
        v=frame[[model+'_'+c for c in ('mean','median','p1','p50')]].to_numpy()
        assert np.isfinite(v).all() and (v>=0).all() and (v[:,2:]<=1).all() and (v[:,3]<=v[:,2]+1e-12).all()
        for h in (1,2,3):
            part=frame[frame.horizon.eq(h)];tau=cut.get((model,h),.5)
            assert not ((part[model+'_p50']>=tau)&(part[model+'_p1']<tau)).any()
    # Independent recomputation of published amount and event metrics.
    metrics=pd.read_csv(PUBLIC/'point_metrics.csv');checks=0
    for row in metrics.itertuples():
        s=frame[frame.split.eq(row.fold)&frame.horizon.eq(row.horizon)];e=s[row.model+'_'+row.functional].to_numpy()-s.y_mm.to_numpy()
        equal([mean_station(abs(e),s.station_id),mean_station(e*e,s.station_id,True),mean_station(e,s.station_id)],
              [row.macro_mae,row.macro_rmse,row.macro_bias]);checks+=3
    for row in pd.read_csv(PUBLIC/'event_metrics.csv').itertuples():
        s=frame[frame.split.eq(row.fold)&frame.horizon.eq(row.horizon)];yes=s[f'{row.model}_p{row.threshold_mm}']>=row.cutoff;actual=s.y_mm>=row.threshold_mm
        assert int((yes&actual).sum())==row.hits and int((~yes&actual).sum())==row.misses and int((yes&~actual).sum())==row.false_alarms;checks+=3
    for row in pd.read_csv(PUBLIC/'probability_metrics.csv').itertuples():
        s=frame[frame.split.eq(row.fold)&frame.horizon.eq(row.horizon)];actual=s.y_mm.ge(row.threshold_mm).to_numpy()
        square=(s[f'{row.model}_p{row.threshold_mm}'].to_numpy()-actual)**2
        equal(mean_station(square,s.station_id),row.macro_bs)
        errors=pd.DataFrame(dict(sid=s.station_id.to_numpy(),bs=square,reference=(s[f'CLIM_p{row.threshold_mm}'].to_numpy()-actual)**2)).groupby('sid').mean()
        bss=(1-errors.bs/errors.reference.where(errors.reference>0)).mean()
        equal(bss,row.macro_bss);checks+=2
    unchanged=0
    for name,checksum in json.loads((BASE/'preserved_hashes.json').read_text()).items():
        assert sha(ROOT/name)==checksum,name;unchanged+=1
    protected=json.loads((ROOT/'data/operational/workspace_cleanup_2026_11_09/user_files.json').read_text(encoding='utf8'))
    for item in protected:assert sha(ROOT/item['path'])==item['sha256'];unchanged+=1
    pd.DataFrame(seeds).to_csv(PUBLIC/'seed_metrics.csv',index=False)
    result=dict(status='passed',lightgbm_estimators_replayed=replayed,gru_models_replayed=neural,
        calibrators_refit_on_2023=calibrators,metric_checks=checks,previous_artifacts_unchanged=unchanged,
        training_code_lock_verified=True,dataset_sha256=lock['dataset_sha256'],probability_and_decision_nesting=True,
        primary_and_latency_models_same_samples=True,test2025_read=False)
    write_json(PUBLIC/'model_verification.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':main()
