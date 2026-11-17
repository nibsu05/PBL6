"""Train only 2021--2022; calibrate2023; lock before retrospective scoring."""
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
from src.gfs_temporal import BASE,PUBLIC,OLD,CATALOG,SEEDS,sha,write_json,load_protocol
from src.gfs_temporal_models import train_gru,replay_gru
from src.gfs_daily import crossfit_calibration,choose_cutoff
from src.gfs_daily_models import fit_tree,predict_tree

CODE=['src/gfs_temporal.py','src/gfs_temporal_models.py','src/gfs_temporal_evaluation.py',
      'scripts/build_gfs_temporal.py','scripts/train_gfs_temporal.py','scripts/score_gfs_temporal.py',
      'scripts/collect_gfs_temporal.py','scripts/collect_gfs_station_pilot.py','src/gfs_station.py',
      'src/gfs_daily.py','src/gfs_daily_gru.py','src/gfs_daily_models.py','src/gfs_daily_evaluation.py',
      'src/gfs_station_dataset.py','src/gfs_final_metrics.py']

def progress(stage,**details):
    write_json(BASE/'training_progress.json',dict(stage=stage,pid=os.getpid(),updated_utc=datetime.now(timezone.utc).isoformat(),**details))

def training_lock():
    references=[OLD/'models'/f'MOS_d{h}.joblib' for h in (1,2,3)]
    references += [OLD/'cohort_private.csv',ROOT/'data/operational/vrain_2026_11_09/freeze_work/station_matrices.npz']
    value=dict(protocol=sha(PUBLIC/'protocol.json'),dataset=sha(BASE/'dataset_private.parquet'),
        tree_selection=sha(ROOT/'reports/gfs_station_daily_v2_2026_11_10/tree_selection.json'),
        environment={name:version(name) for name in ['numpy','pandas','pyarrow','scikit-learn','lightgbm','torch','joblib','eccodes']},
        baseline_dependencies={str(path.relative_to(ROOT)):sha(path) for path in references},
        code={name:sha(ROOT/name) for name in CODE})
    path=BASE/'training_lock.json'
    if path.exists():
        if json.loads(path.read_text())!=value:raise ValueError('Training dependencies changed; new version required')
    else:write_json(path,value)
    return value

def main():
    p=load_protocol()
    for name in ('source_verification','dataset_verification','tests_verification'):
        v=json.loads((PUBLIC/(name+'.json')).read_text())
        if v['status']!='passed':raise ValueError('Required verification failed: '+name)
    if json.loads((PUBLIC/'source_verification.json').read_text())['protocol_sha256']!=sha(PUBLIC/'protocol.json'):raise ValueError('Source verification protocol changed')
    if json.loads((PUBLIC/'dataset_verification.json').read_text())['dataset_sha256']!=sha(BASE/'dataset_private.parquet'):raise ValueError('Verified dataset changed')
    lock=training_lock();folder=BASE/'models';folder.mkdir(exist_ok=True)
    if (BASE/'model_freeze.json').exists():raise ValueError('Model freeze already exists; do not refit')
    f=pd.read_parquet(BASE/'dataset_private.parquet',filters=[('split','in',['train','cal','dev'])]).reset_index(drop=True)
    if f.target_end_utc.dt.tz_convert('Asia/Ho_Chi_Minh').dt.year.max()>2024:raise ValueError('Post2024 label reached training process')
    for part,years in [('train',(2021,2022)),('cal',(2023,2023)),('dev',(2024,2024))]:
        sub=f[f.split.eq(part)]
        start=sub.target_start_utc.dt.tz_convert('Asia/Ho_Chi_Minh').dt.year
        end=sub.target_end_utc.dt.tz_convert('Asia/Ho_Chi_Minh').dt.year
        if not (start.between(*years)&end.between(*years)).all():raise ValueError('Target crosses split boundary: '+part)
    dataset_sha=lock['dataset'];cutoffs=[];details=[];seed_values={}
    selection=json.loads((ROOT/'reports/gfs_station_daily_v2_2026_11_10/tree_selection.json').read_text())['selected']
    def calibrate(frame,wet,conditional,label,h):
        probability,oof,pairs=crossfit_calibration(frame,wet,conditional)
        cutoff,grid=choose_cutoff(frame,oof,[round(float(x),2) for x in np.arange(.05,1,.05)])
        cutoffs.append(dict(model=label,horizon=h,cutoff=cutoff,selection='cross-fitted2023',grid=grid))
        joblib.dump(pairs,folder/f'{label}_d{h}_calibrators.joblib');return probability
    for config,names in CATALOG.items():
        label='LGB_'+config;seed_values[label]=[]
        allraw=[{k:np.zeros(len(f)) for k in ('mean','median','wet','conditional')} for _ in SEEDS]
        for h in (1,2,3):
            mask=f.horizon.eq(h).to_numpy();sub=f.loc[mask].reset_index(drop=True);train=sub.split.eq('train').to_numpy()
            for j,seed in enumerate(SEEDS):
                path=folder/f'{label}_d{h}_seed{seed}.joblib';progress('tree',model=label,horizon=h,seed=seed)
                if path.exists():
                    a=joblib.load(path)
                    if a['dataset_sha256']!=dataset_sha or a['features']!=names:raise ValueError('Saved tree changed')
                else:
                    models={head:fit_tree(sub,names,train,None,head,selection[head]['candidate'],seed,selection[head]['trees'][str(h)])
                            for head in ('mean','median','wet','conditional')}
                    a=dict(models=models,features=names,seed=seed,dataset_sha256=dataset_sha);joblib.dump(a,path,compress=3)
                for head,model in a['models'].items():allraw[j][head][mask]=predict_tree(model,names,sub,head)
            prob=calibrate(sub,[v['wet'][mask] for v in allraw],[v['conditional'][mask] for v in allraw],label,h)
            f.loc[mask,label+'_p1']=prob[:,0];f.loc[mask,label+'_p50']=prob[:,1]
        for head in ('mean','median'):f[label+'_'+head]=np.mean([v[head] for v in allraw],0)
        print(json.dumps(dict(fitted=label)),flush=True)
    for config in ('T0','T3','LINEAR23'):
        label='GRU_'+config;outputs=[]
        for seed in SEEDS:
            path=folder/f'{label}_seed{seed}.pt'
            if path.exists():
                a=torch.load(path,map_location='cpu',weights_only=False)
                if a['dataset_sha256']!=dataset_sha:raise ValueError('Saved GRU changed')
                out=replay_gru(f,a)
            else:
                a,out=train_gru(f,config,seed,lambda row:progress('gru',model=label,seed=seed,**row))
                a['dataset_sha256']=dataset_sha;torch.save(a,path)
            outputs.append(out);details.append(dict(model=label,seed=seed,epochs=a['epochs'],parameters=a['parameter_count'],device=a['device']))
        for head in ('mean','median'):f[label+'_'+head]=np.mean([v[head] for v in outputs],0).ravel()
        for h in (1,2,3):
            mask=f.horizon.eq(h).to_numpy();sub=f.loc[mask].reset_index(drop=True)
            prob=calibrate(sub,[v['wet'][:,h-1] for v in outputs],[v['conditional'][:,h-1] for v in outputs],label,h)
            f.loc[mask,label+'_p1']=prob[:,0];f.loc[mask,label+'_p50']=prob[:,1]
        print(json.dumps(dict(fitted=label)),flush=True)
    f.to_parquet(BASE/'development_predictions_private.parquet',index=False,compression='zstd')
    write_json(PUBLIC/'decision_cutoffs.json',cutoffs);write_json(PUBLIC/'gru_fit_summary.json',details)
    # Compare the T0 refit with original predictions on exactly matching rows.
    old=pd.read_parquet(OLD/'predictions_private.parquet');keys=['issue_utc','station_id','horizon']
    common=f.merge(old,on=keys,suffixes=('','_old'),validate='one_to_one')
    parity={}
    for model,newold in [('LGB','LGB_N3'),('GRU','GRU_N3')]:
        for head in ('mean','median','p1','p50'):
            parity[f'{model}_{head}']=float(np.max(abs(common[f'{model}_T0_{head}']-common[f'{newold}_{head}'])))
    write_json(PUBLIC/'baseline_refit_parity.json',dict(rows=len(common),maximum_absolute_differences=parity,
        note='different common training rows would legitimately require a baseline refit; disclose any differences'))
    dependencies={str(path.relative_to(ROOT)):sha(path) for path in sorted(folder.glob('*'))}
    dependencies[str((PUBLIC/'decision_cutoffs.json').relative_to(ROOT))]=sha(PUBLIC/'decision_cutoffs.json')
    write_json(BASE/'model_freeze.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),
        training_lock_sha256=sha(BASE/'training_lock.json'),artifacts=dependencies,
        retrospective_status='already inspected previously; locked here only to prevent within-run result-dependent refitting'))
    progress('complete',tree_estimators=144,gru_fits=9,artifacts=len(dependencies))

if __name__=='__main__':main()
