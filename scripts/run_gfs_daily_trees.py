"""Controlled train-only tuning, dual point heads and nested probabilities."""
from pathlib import Path
from datetime import datetime,timezone
import json
import os
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge,QuantileRegressor,LogisticRegression
from sklearn.preprocessing import StandardScaler
from src.gfs_daily import (BASE,PUBLIC,DATA,FEATURES,TREE_CANDIDATES,load_protocol,write_json,sha,
    cv_masks,score_bundle,with_delay,crossfit_calibration,choose_cutoff)
from src.gfs_daily_models import fit_tree,predict_tree,best_round,climatology,ConstantBinary
from src.gfs_daily_lock import training_lock

HEADS=('mean','median','wet','conditional')


def progress(stage,**details):
    write_json(BASE/'tree_progress.json',dict(stage=stage,pid=os.getpid(),updated_utc=datetime.now(timezone.utc).isoformat(),**details))


def tune(frame,p,dataset_sha):
    path=PUBLIC/'tree_selection.json'
    if path.exists():
        value=json.loads(path.read_text());assert value['dataset_sha256']==dataset_sha
        return value
    trials=[];folder=BASE/'tuning_models';folder.mkdir(exist_ok=True)
    for ci,candidate in enumerate(TREE_CANDIDATES):
        for fi,fold in enumerate(p['tuning']['folds']):
            for h in (1,2,3):
                f=frame[frame.horizon.eq(h)].reset_index(drop=True);tr,va=cv_masks(f,fold)
                progress('tuning',candidate=candidate['name'],fold=fi+1,horizon=h)
                modelpath=folder/f'tree_c{ci}_f{fi}_h{h}.joblib'
                if modelpath.exists():
                    saved=joblib.load(modelpath);assert saved['dataset_sha256']==dataset_sha;models=saved['models']
                else:
                    models={head:fit_tree(f,FEATURES['N3'],tr,va,head,candidate,trees=p['tuning']['max_trees']) for head in HEADS}
                    joblib.dump(dict(models=models,dataset_sha256=dataset_sha),modelpath,compress=3)
                out={head:predict_tree(models[head],FEATURES['N3'],f.loc[va],head) for head in HEADS}
                score=score_bundle(f.loc[va,'y_mm'],out['mean'],out['median'],out['wet'],out['conditional'],
                    f.loc[va,'station_id'],f.loc[va,'gfs_rain_mm'],f.loc[tr,'y_mm'])
                row=dict(candidate=candidate['name'],fold=fi+1,horizon=h,train_rows=int(tr.sum()),valid_rows=int(va.sum()),
                    train_stations=int(f.loc[tr,'station_id'].nunique()),valid_stations=int(f.loc[va,'station_id'].nunique()),
                    **score,**{head+'_trees':best_round(models[head],p['tuning']['max_trees']) for head in HEADS})
                trials.append(row);pd.DataFrame(trials).to_csv(PUBLIC/'tree_tuning_trials.csv',index=False)
                print(json.dumps(row),flush=True)
    table=pd.DataFrame(trials);selected={}
    for head,metric in [('mean','mean_score'),('median','median_score'),('wet','probability_score'),('conditional','probability_score')]:
        name=str(table.groupby('candidate')[metric].mean().idxmin());candidate=next(c for c in TREE_CANDIDATES if c['name']==name)
        selected[head]=dict(candidate=candidate,trees={str(h):max(1,int(np.median(table.loc[(table.candidate==name)&table.horizon.eq(h),head+'_trees']))) for h in (1,2,3)})
    result=dict(status='selected_from_train_only_cv',anchor='N3',dataset_sha256=dataset_sha,selected=selected,
        tuning_used_years=[2021,2022],cal2023_used_for_tuning=False,dev2024_used_for_tuning=False,test2025_read=False)
    write_json(path,result);return result


def calibrate_outputs(f,wet,conditional,label,p,cutoffs):
    probability,oof,calibrators=crossfit_calibration(f,wet,conditional)
    cutoff,grid=choose_cutoff(f,oof,p['calibration']['cutoff_grid'])
    cutoffs.append(dict(model=label,horizon=int(f.horizon.iloc[0]),cutoff=cutoff,selection='cross-fitted calibration2023',grid=grid))
    return probability,calibrators


def main():
    training_lock()
    p=load_protocol();path=DATA/'dataset.parquet';dataset_sha=sha(path)
    frame=pd.read_parquet(path).reset_index(drop=True)
    if frame.target_end_utc.dt.year.max()>2024:raise ValueError('Reserved year in model input')
    selection=tune(frame,p,dataset_sha)
    cutoffs=[];diagnostics=[];model_names=[]
    scenarios=[(name,1) for name in FEATURES]+[('N3',3),('N3',6)]
    for config,delay in scenarios:
        label='LGB_'+config+('' if delay==1 else f'_delay{delay}');names=FEATURES[config];model_names.append(label)
        for h in (1,2,3):
            positions=frame.index[frame.horizon.eq(h)]
            f=with_delay(frame.loc[positions].reset_index(drop=True),delay);train=f.split.eq('train').to_numpy()
            out={head:[] for head in HEADS}
            for seed in p['seeds']:
                progress('fitting_final',model=label,horizon=h,seed=seed)
                artifactpath=BASE/'models'/f'{label}_d{h}_seed{seed}.joblib'
                if artifactpath.exists():
                    artifact=joblib.load(artifactpath);assert artifact['dataset_sha256']==dataset_sha
                    assert artifact['features']==names;models=artifact['models']
                else:
                    models={head:fit_tree(f,names,train,None,head,selection['selected'][head]['candidate'],
                        seed,selection['selected'][head]['trees'][str(h)]) for head in HEADS}
                    artifact=dict(models=models,features=names,dataset_sha256=dataset_sha,delay=delay,seed=seed)
                    joblib.dump(artifact,artifactpath,compress=3)
                for head in HEADS:out[head].append(predict_tree(models[head],names,f,head))
                diagnostics.append(dict(model=label,horizon=h,seed=seed,train_rows=int(train.sum()),
                    **{head+'_trees':selection['selected'][head]['trees'][str(h)] for head in HEADS}))
            for head in ('mean','median'):frame.loc[positions,label+'_'+head]=np.mean(out[head],axis=0)
            probability,calibrators=calibrate_outputs(f,out['wet'],out['conditional'],label,p,cutoffs)
            frame.loc[positions,label+'_p1']=probability[:,0];frame.loc[positions,label+'_p50']=probability[:,1]
            joblib.dump(calibrators,BASE/'models'/f'{label}_d{h}_calibrators.joblib')
            print(json.dumps(dict(fitted=label,horizon=h)),flush=True)
    reference=climatology(frame)
    for label,values in [('ZERO',np.zeros(len(frame))),('GFS',frame.gfs_rain_mm.to_numpy()),('PERSISTENCE',frame.rain_recent24h_mm.to_numpy())]:
        frame[label+'_mean']=values;frame[label+'_median']=values
        for t in (1,50):frame[f'{label}_p{t}']=(values>=t).astype(float)
        model_names.append(label)
    for col in ('mean','median','p1','p50'):frame['CLIM_'+col]=reference[col]
    model_names.append('CLIM')
    for h in (1,2,3):
        progress('fitting_MOS',horizon=h)
        positions=frame.index[frame.horizon.eq(h)];f=frame.loc[positions].reset_index(drop=True)
        tr=f.split.eq('train').to_numpy();features=['gfs_rain_mm','sin_doy','cos_doy']
        scale=StandardScaler().fit(f.loc[tr,features]);x=scale.transform(f[features]);y=f.y_mm.to_numpy()
        mean=Ridge(alpha=1.).fit(x[tr],y[tr]);median=QuantileRegressor(quantile=.5,alpha=.01,solver='highs').fit(x[tr],y[tr])
        classifiers=[];raw=[]
        for threshold,mask in [(1,tr),(50,tr&(y>=1))]:
            labels=(y>=threshold).astype(int)
            model=LogisticRegression(C=1.,solver='lbfgs',max_iter=500).fit(x[mask],labels[mask]) if len(np.unique(labels[mask]))==2 else ConstantBinary(labels[mask])
            classifiers.append(model);raw.append(model.predict_proba(x)[:,1])
        probability,calibrators=calibrate_outputs(f,[raw[0]],[raw[1]],'MOS',p,cutoffs)
        frame.loc[positions,'MOS_mean']=np.maximum(mean.predict(x),0);frame.loc[positions,'MOS_median']=np.maximum(median.predict(x),0)
        frame.loc[positions,'MOS_p1']=probability[:,0];frame.loc[positions,'MOS_p50']=probability[:,1]
        joblib.dump(dict(scaler=scale,mean=mean,median=median,classifiers=classifiers,calibrators=calibrators,features=features,dataset_sha256=dataset_sha),BASE/'models'/f'MOS_d{h}.joblib')
    model_names.append('MOS')
    for name in model_names:
        if not (frame[name+'_p50']<=frame[name+'_p1']+1e-12).all():raise ValueError('Event nesting failed')
    frame.to_parquet(BASE/'tree_predictions_private.parquet',index=False,compression='zstd')
    write_json(PUBLIC/'decision_cutoffs.json',cutoffs)
    pd.DataFrame(diagnostics).to_csv(PUBLIC/'tree_fit_diagnostics.csv',index=False)
    write_json(PUBLIC/'tree_summary.json',dict(status='complete',models=model_names,dataset_sha256=dataset_sha,
        calibration='2023 only, nested conditional probabilities',amount_functionals=['mean','median'],
        final_lightgbm_estimators=len(diagnostics)*4,hyperparameter_tuning_years=[2021,2022],test2025_read=False))
    progress('complete',models=len(model_names),final_lightgbm_estimators=len(diagnostics)*4)
    print(json.dumps(dict(status='complete',models=len(model_names))),flush=True)


if __name__=='__main__':main()
