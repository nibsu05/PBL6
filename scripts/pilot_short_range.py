"""Pilot E0/E7, train/cal/eval2021–2023; never load test2025 rows."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import lightgbm as lgb
import numpy as np
import pandas as pd
import torch

from src.short_range_dataset import (load_development, feature_groups, train_scaler,
    scale_inputs, tabular_inputs, fit_climatology, predict_climatology, THRESHOLDS, SOURCE, file_hash)
from src.short_range_evaluation import (fit_calibration, apply_calibration, prediction_frame, score_predictions)
from src.tft_regional import RegionalTFT, daily_joint_loss, daily_tweedie_deviance


def clean(value):
    if isinstance(value, dict): return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [clean(v) for v in value]
    if isinstance(value, np.ndarray): return clean(value.tolist())
    if isinstance(value, np.generic): return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value): return None
    return value


def dump(path,value):
    path.write_text(json.dumps(clean(value),ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')


def raw_logit(p):
    p=np.clip(p,1e-6,1-1e-6)
    return np.log(p/(1-p))


def brier_metric(y,p):
    return 'brier',float(np.mean((y-p)**2)),False


def fit_lgbm(x,y,train,cal,ev,private,tag):
    ac,ae=np.zeros((cal.sum(),3)),np.zeros((ev.sum(),3))
    pc,pe=np.zeros((cal.sum(),3,3)),np.zeros((ev.sum(),3,3))
    models=[]
    options=dict(n_estimators=400,learning_rate=.04,num_leaves=15,min_child_samples=30,
                  n_jobs=4,random_state=42,verbosity=-1,deterministic=True,force_col_wise=True,
                  feature_fraction=1.,bagging_fraction=1.)
    for lead in range(3):
        reg=lgb.LGBMRegressor(objective='tweedie',tweedie_variance_power=1.5,**options)
        reg.fit(x[train],y[train,lead],eval_set=[(x[cal],y[cal,lead])],eval_metric='tweedie',
                 callbacks=[lgb.early_stopping(30,verbose=False)])
        ac[:,lead]=np.maximum(reg.booster_.predict(x[cal]),0.)
        ae[:,lead]=np.maximum(reg.booster_.predict(x[ev]),0.)
        path=private/f'{tag}_day{lead+1}_amount.txt'; reg.booster_.save_model(str(path))
        models.append(dict(lead=lead+1,kind='amount',path=path.name,best_iteration=reg.best_iteration_))
        for ti,threshold in enumerate(THRESHOLDS):
            target=(y[:,lead]>=threshold).astype(int)
            if len(np.unique(target[train]))==1:
                constant=(target[train].sum()+.5)/(train.sum()+1.)
                pc[:,lead,ti]=pe[:,lead,ti]=constant
                models.append(dict(lead=lead+1,kind='event',threshold=float(threshold),constant=float(constant)))
                continue
            clf=lgb.LGBMClassifier(objective='binary',metric='None',**options)
            clf.fit(x[train],target[train],eval_set=[(x[cal],target[cal])],eval_metric=brier_metric,
                    callbacks=[lgb.early_stopping(30,first_metric_only=True,verbose=False)])
            pc[:,lead,ti]=clf.booster_.predict(x[cal])
            pe[:,lead,ti]=clf.booster_.predict(x[ev])
            path=private/f'{tag}_day{lead+1}_event{int(threshold)}.txt'
            clf.booster_.save_model(str(path))
            models.append(dict(lead=lead+1,kind='event',threshold=float(threshold),path=path.name,
                               best_iteration=clf.best_iteration_))
    return ac,ae,pc,pe,dict(output_models=models)


def network_predict(model,x,c,device,batch=128):
    model.eval(); amounts=[]; probabilities=[]
    with torch.inference_mode():
        for start in range(0,len(x),batch):
            a,l=model(torch.as_tensor(x[start:start+batch],device=device),
                      torch.as_tensor(c[start:start+batch],device=device))
            amounts.append(a.cpu().numpy()); probabilities.append(l.sigmoid().cpu().numpy())
    return np.concatenate(amounts),np.concatenate(probabilities)


def fit_tft(samples,train,cal,ev,private,tag,epochs,batch,seed,device):
    np.random.seed(seed); torch.manual_seed(seed)
    if device.startswith('cuda'): torch.cuda.manual_seed_all(seed)
    scaler=train_scaler(samples.x[train]); x=scale_inputs(samples.x,scaler)
    model=RegionalTFT(x.shape[-1],hidden=32,heads=4,dropout=.1).to(device)
    y=torch.as_tensor(samples.y[train],device=device)
    mu=y.mean(0).clamp_min(.001)
    scale=daily_tweedie_deviance(mu,y).mean(0).detach()
    if (scale<=0).any(): raise ValueError('Zero null deviance in train')
    event_rate=(y[:,:,None]>=y.new_tensor([16.,50.,100.])).float().mean((0,1)).cpu().numpy()
    with torch.no_grad():
        mean=float(mu.mean()); model.amount.bias.fill_(mean if mean>20 else math.log(math.expm1(mean)))
        model.events.bias.copy_(torch.as_tensor(raw_logit(event_rate),device=device,dtype=torch.float32))
    train_x=torch.as_tensor(x[train],device=device)
    train_c=torch.as_tensor(samples.future[train],device=device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.0001)
    history=[]; best=float('inf'); best_epoch=0; best_state=None; stale=0
    if device.startswith('cuda'): torch.cuda.reset_peak_memory_stats()
    rng=np.random.default_rng(seed)
    for epoch in range(1,epochs+1):
        tick=time.perf_counter(); model.train(); losses=[]
        order=rng.permutation(len(train_x))
        for start in range(0,len(order),batch):
            ids=torch.as_tensor(order[start:start+batch],device=device)
            optimizer.zero_grad(set_to_none=True)
            amount,logits=model(train_x[ids],train_c[ids])
            loss=daily_joint_loss(amount,logits,y[ids],scale)
            if not torch.isfinite(loss): raise ValueError('Nonfinite TFT loss')
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
            optimizer.step(); losses.append(float(loss.detach()))
        _,pcal=network_predict(model,x[cal],samples.future[cal],device)
        bs=float(np.mean((pcal[:,:,0]-(samples.y[cal]>=16))**2))
        history.append(dict(epoch=epoch,loss=float(np.mean(losses)),cal_BS16=bs,
                            seconds=time.perf_counter()-tick))
        if bs<best:
            best,best_epoch,stale=bs,epoch,0
            best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
        else: stale+=1
        print(f'{tag} epoch{epoch} calBS16={bs:.5f} seconds={history[-1]["seconds"]:.2f}',flush=True)
        if stale>=6: break
    model.load_state_dict(best_state)
    ac,pc=network_predict(model,x[cal],samples.future[cal],device)
    ae,pe=network_predict(model,x[ev],samples.future[ev],device)
    checkpoint=private/f'{tag}.pt'
    torch.save(dict(state=best_state,config=model.config,features=samples.features,
                    scaler={k:torch.tensor(v) for k,v in scaler.items()},best_epoch=best_epoch,
                    null_scale=scale.cpu(),seed=seed),checkpoint)
    restored=torch.load(checkpoint,map_location='cpu',weights_only=True)
    check=RegionalTFT(**restored['config']).to(device)
    check.load_state_dict(restored['state'])
    ra,rp=network_predict(check,x[ev][:8],samples.future[ev][:8],device)
    np.testing.assert_allclose(ra,ae[:8],rtol=2e-5,atol=1e-5)
    np.testing.assert_allclose(rp,pe[:8],rtol=2e-5,atol=1e-6)
    peak=float(torch.cuda.max_memory_allocated()/1024**2) if device.startswith('cuda') else None
    del check,model,train_x,train_c,y
    if device.startswith('cuda'): torch.cuda.empty_cache()
    return ac,ae,pc,pe,dict(best_epoch=best_epoch,best_cal_BS16=best,history=history,
                            checkpoint=checkpoint.name,checkpoint_sha256=file_hash(checkpoint),
                            checkpoint_roundtrip='passed',peak_allocated_mib=peak)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--learners',nargs='+',choices=['lgbm','tft'],default=['lgbm','tft'])
    parser.add_argument('--epochs',type=int,default=40)
    parser.add_argument('--batch',type=int,default=64)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--max-minutes',type=float,default=150.)
    parser.add_argument('--report',type=Path,default=ROOT/'reports/short_range_pilot_2026_10_21')
    args=parser.parse_args(); report=args.report; report.mkdir(parents=True,exist_ok=True)
    private=ROOT/'data/operational/short_range/pilot_2026_10_21'; private.mkdir(parents=True,exist_ok=True)
    data=load_development(); groups=feature_groups()
    if len(data.dates)!=3248: raise ValueError('Current frozen footprint expected3248 development issues')
    if file_hash(SOURCE)!='92a6bc6a527b25107761e85f0d14e64713a39dfd2930560a4498927c27dfc448':
        raise ValueError('V1 checksum changed; audit dataset before training')
    torch.set_num_threads(4)
    device='cuda' if torch.cuda.is_available() else 'cpu'
    code_paths=['src/short_range_dataset.py','src/tft_regional.py','src/short_range_evaluation.py',
                'scripts/pilot_short_range.py']
    manifest=dict(status='running',scope='Exploratory pilot only',date_local='2026-10-21',
                  user_approved=True,years_eval=[2021,2022,2023],experiments=['E0','E7'],seed=args.seed,
                  architecture='Regional TFT adaptation: no static context; 6h backbone; daily Tweedie/BCE heads',
                  tft=dict(hidden=32,heads=4,dropout=.1,batch=args.batch,epochs_max=args.epochs,patience=6),
                  device=device,source_hash=file_hash(SOURCE),development_issues=len(data.dates),
                  git_base=subprocess.check_output(['git','-c','safe.directory=D:/PBL6_v2','rev-parse','HEAD'],
                                                   cwd=ROOT).decode().strip(),
                  worktree_code_sha256={p:file_hash(ROOT/p) for p in code_paths},
                  history_hours=168,encoder_steps=28,bin_hours=6,target_intervals=[[0,24],[24,48],[48,72]],
                  target='Area-mean GSMaP Gauge over93selected full cells; approximate footprint',
                  test2025_read=False,forecast_future_era5_used=False,models=[],folds=[],
                  limitations=['One seed only; no full E0-E7 factorial or final holdout',
                               'Reanalysis retrospective; no as-of operational availability claim',
                               'Footprint not exact administrative polygon; label independent truth unverified'])
    if device=='cuda': manifest['gpu']=torch.cuda.get_device_name(0)
    dump(report/'run.json',manifest)
    started=time.perf_counter(); all_predictions=[]; fitted_climates={}
    for year in [2021,2022,2023]:
        train=data.dates.year<year-1; cal=data.dates.year==year-1; ev=data.dates.year==year
        climate=fit_climatology(data.dates[train],data.y[train]); fitted_climates[year]=climate
        ac,pc=predict_climatology(data.dates[ev],climate)
        manifest['folds'].append(dict(year=year,n_train=int(train.sum()),n_cal=int(cal.sum()),n_eval=int(ev.sum())))
        for name,a,p in [('climatology',ac,pc),('zero',np.zeros_like(ac),np.zeros_like(pc))]:
            all_predictions.append(prediction_frame(data.dates[ev],data.y[ev],a,p,pc,[],name,'BASE',year,0))
    def flush():
        frame=pd.concat(all_predictions,ignore_index=True)
        frame.to_parquet(private/'predictions.parquet',index=False)
        score_predictions(frame).to_csv(report/'scores.csv',index=False,lineterminator='\n')
        manifest['elapsed_seconds']=time.perf_counter()-started
        dump(report/'run.json',manifest)
    flush()
    for learner in args.learners:
        for year in [2021,2022,2023]:
            train=data.dates.year<year-1; cal=data.dates.year==year-1; ev=data.dates.year==year
            _,reference=predict_climatology(data.dates[ev],fitted_climates[year])
            for experiment in ['E0','E7']:
                if time.perf_counter()-started>args.max_minutes*60:
                    manifest['status']='partial_time_budget'; flush(); return
                selected=data.select(groups[experiment]); tag=f'{learner}_{year}_{experiment}_seed{args.seed}'
                print('START',tag,flush=True); tick=time.perf_counter()
                if learner=='lgbm':
                    x,tab_names=tabular_inputs(selected)
                    ac,ae,pc,pe,meta=fit_lgbm(x,selected.y,train,cal,ev,private,tag)
                    meta.update(tabular_features=tab_names)
                else:
                    ac,ae,pc,pe,meta=fit_tft(selected,train,cal,ev,private,tag,args.epochs,args.batch,args.seed,device)
                params=fit_calibration(data.y[cal],pc)
                prob=apply_calibration(pe,params)
                pred=prediction_frame(data.dates[ev],data.y[ev],ae,prob,reference,params,
                                      learner,experiment,year,args.seed)
                all_predictions.append(pred)
                meta.update(learner=learner,year=year,experiment=experiment,seed=args.seed,
                            feature_names=selected.features,seconds=time.perf_counter()-tick,calibration=params)
                dump(private/f'{tag}_metadata.json',meta)
                manifest['models'].append(meta)
                flush()
                print('DONE',tag,'seconds',round(meta['seconds'],2),flush=True)
    manifest['status']='complete'; flush()
    print('COMPLETE',round(manifest['elapsed_seconds'],2),'seconds',flush=True)


if __name__=='__main__': main()
