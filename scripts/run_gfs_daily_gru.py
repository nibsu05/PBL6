"""Train-only GRU selection, then fixed-epoch N3/N5 three-seed comparison."""
from pathlib import Path
from datetime import datetime,timezone
import json
import os
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import joblib
import numpy as np
import pandas as pd
import torch
from src.gfs_daily import BASE,PUBLIC,DATA,GRU_CANDIDATES,load_protocol,cv_masks,sha,write_json
from src.gfs_daily_gru import train_network,replay
from scripts.run_gfs_daily_trees import calibrate_outputs
from src.gfs_daily_lock import training_lock


def progress(stage,**details):
    write_json(BASE/'gru_progress.json',dict(stage=stage,pid=os.getpid(),updated_utc=datetime.now(timezone.utc).isoformat(),**details))


def tune(frame,p,dataset_sha):
    path=PUBLIC/'gru_selection.json'
    if path.exists():
        value=json.loads(path.read_text());assert value['dataset_sha256']==dataset_sha;return value
    trials=[];curves=[];folder=BASE/'tuning_models';folder.mkdir(exist_ok=True)
    for ci,candidate in enumerate(GRU_CANDIDATES):
        for fi,fold in enumerate(p['tuning']['folds']):
            train,valid=cv_masks(frame.iloc[::3].reset_index(drop=True),fold)
            modelpath=folder/f'gru_c{ci}_f{fi}.pt'
            progress('tuning',candidate=candidate['name'],fold=fi+1)
            if modelpath.exists():
                artifact=torch.load(modelpath,map_location='cpu',weights_only=False);assert artifact['dataset_sha256']==dataset_sha
            else:
                def update(row):progress('tuning',candidate=candidate['name'],fold=fi+1,**row)
                artifact,_=train_network(frame,'N3',train,valid,candidate,17,p['tuning']['gru_max_epochs'],p['tuning']['gru_patience'],update)
                artifact['dataset_sha256']=dataset_sha;torch.save(artifact,modelpath)
            trials.append(dict(candidate=candidate['name'],fold=fi+1,best_epoch=artifact['best_epoch'],epochs=artifact['epochs'],
                valid_joint_score=artifact['validation_score'],train_samples=int(train.sum()),valid_samples=int(valid.sum())))
            curves.extend(dict(candidate=candidate['name'],fold=fi+1,**r) for r in artifact['curves'])
            pd.DataFrame(trials).to_csv(PUBLIC/'gru_tuning_trials.csv',index=False)
            pd.DataFrame(curves).to_csv(PUBLIC/'gru_learning_curves.csv',index=False)
            print(json.dumps(trials[-1]),flush=True)
    table=pd.DataFrame(trials);name=str(table.groupby('candidate').valid_joint_score.mean().idxmin())
    candidate=next(c for c in GRU_CANDIDATES if c['name']==name)
    epochs=max(1,int(np.median(table.loc[table.candidate.eq(name),'best_epoch'])))
    result=dict(status='selected_from_train_only_cv',candidate=candidate,epochs=epochs,dataset_sha256=dataset_sha,
        anchor='N3',tuning_used_years=[2021,2022],cal2023_used_for_tuning=False,dev2024_used_for_tuning=False,test2025_read=False)
    write_json(path,result);return result


def main():
    training_lock()
    p=load_protocol();dataset_sha=sha(DATA/'dataset.parquet')
    frame=pd.read_parquet(BASE/'tree_predictions_private.parquet').sort_values(['issue_utc','station_id','horizon']).reset_index(drop=True)
    selected=tune(frame,p,dataset_sha);cutoffs=[c for c in json.loads((PUBLIC/'decision_cutoffs.json').read_text()) if not c['model'].startswith('GRU_')]
    details=[];curves=[];n=len(frame)//3;train=frame.split.to_numpy().reshape(n,3)[:,0]=='train'
    for config in p['gru_configurations']:
        label='GRU_'+config;outputs=[]
        for seed in p['seeds']:
            progress('fitting_final',config=config,seed=seed)
            path=BASE/'models'/f'{label}_seed{seed}.pt'
            if path.exists():
                artifact=torch.load(path,map_location='cpu',weights_only=False);assert artifact['dataset_sha256']==dataset_sha
                out=replay(frame,artifact)
            else:
                def update(row):progress('fitting_final',config=config,seed=seed,**row)
                artifact,out=train_network(frame,config,train,None,selected['candidate'],seed,selected['epochs'],0,update)
                artifact['dataset_sha256']=dataset_sha;torch.save(artifact,path)
            outputs.append(out)
            details.append(dict(config=config,seed=seed,epochs=artifact['epochs'],parameter_count=artifact['parameter_count'],device=artifact['device']))
            curves.extend(dict(config=config,seed=seed,**r) for r in artifact['curves'])
        for head in ('mean','median'):frame[label+'_'+head]=np.mean([out[head] for out in outputs],axis=0).ravel()
        for h in (1,2,3):
            positions=frame.horizon.eq(h);f=frame.loc[positions].reset_index(drop=True)
            probability,calibrators=calibrate_outputs(f,[out['wet'][:,h-1] for out in outputs],
                [out['conditional'][:,h-1] for out in outputs],label,p,cutoffs)
            frame.loc[positions,label+'_p1']=probability[:,0];frame.loc[positions,label+'_p50']=probability[:,1]
            joblib.dump(calibrators,BASE/'models'/f'{label}_d{h}_calibrators.joblib')
        if not (frame[label+'_p50']<=frame[label+'_p1']+1e-12).all():raise ValueError('Nested neural probabilities failed')
    frame.to_parquet(BASE/'predictions_private.parquet',index=False,compression='zstd')
    write_json(PUBLIC/'decision_cutoffs.json',cutoffs)
    pd.DataFrame(curves).to_csv(PUBLIC/'gru_final_learning_curves.csv',index=False)
    write_json(PUBLIC/'gru_summary.json',dict(status='complete',configurations=p['gru_configurations'],seeds=details,
        dataset_sha256=dataset_sha,train_only_selection=True,calibration_only_2023=True,test2025_read=False))
    progress('complete',final_models=len(details))
    print(json.dumps(dict(status='complete',models=len(details))),flush=True)


if __name__=='__main__':main()
