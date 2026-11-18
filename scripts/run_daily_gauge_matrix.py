"""Daily ERA5 -> CPC regional daily rainfall: three models, E0--E7."""
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import math
import sys
import time

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import torch
from src.daily_gauge_dataset import load_development, feature_groups, tabular_inputs, TIME, PRIVATE, SOURCE
from src.daily_gauge_models import DailyTFT, DailyInformer
from src.short_range_dataset import train_scaler, scale_inputs, fit_climatology, predict_climatology
from src.tft_regional import daily_joint_loss, daily_tweedie_deviance
from src.short_range_evaluation import fit_calibration, apply_calibration, prediction_frame, score_predictions
from src.short_range_ablation import seed_mean, ensemble_thresholds
from scripts.pilot_short_range import fit_lgbm, network_predict, raw_logit, dump

REPORT = ROOT / 'reports/daily_gauge_2026_11_04'
MODELS = ['lgbm','tft','informer']; SEEDS = [42,43,44]; YEARS = [2021,2022,2023]


def sha(path): return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n',b'\n') if Path(path).suffix=='.py' else Path(path).read_bytes()).hexdigest()


def new_model(kind, samples):
    kw = dict(input_features=len(samples.features), hidden=32, heads=4, dropout=.1, history_steps=7)
    if kind == 'informer': kw.update(time_indices=[samples.features.index(n) for n in TIME], factor=3, label_len=3)
    return (DailyTFT if kind=='tft' else DailyInformer)(**kw)


def fit_network(kind, data, train, cal, ev, tag, device):
    seed = int(tag.rsplit('_s',1)[1]); np.random.seed(seed); torch.manual_seed(seed)
    if device=='cuda': torch.cuda.manual_seed_all(seed)
    scaler = train_scaler(data.x[train]); x = scale_inputs(data.x,scaler)
    model = new_model(kind,data).to(device)
    if kind=='informer': model.set_scaler(scaler)
    y = torch.as_tensor(data.y[train],device=device)
    mu = y.mean(0).clamp_min(.001); scale = daily_tweedie_deviance(mu,y).mean(0).detach()
    assert (scale>0).all()
    rate = (y[:,:,None]>=y.new_tensor([16.,50.,100.])).float().mean((0,1)).cpu().numpy()
    with torch.no_grad():
        mean = float(mu.mean()); model.amount.bias.fill_(mean if mean>20 else math.log(math.expm1(mean)))
        model.events.bias.copy_(torch.as_tensor(raw_logit(rate),device=device,dtype=torch.float32))
    tx = torch.as_tensor(x[train],device=device); tc = torch.as_tensor(data.future[train],device=device)
    optimizer = torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.0001)
    rng = np.random.default_rng(seed); history=[]; best=float('inf'); stale=0; state=None
    tick=time.perf_counter()
    for epoch in range(1,41):
        model.train(); losses=[]
        order=rng.permutation(len(tx))
        for start in range(0,len(order),64):
            ids=torch.as_tensor(order[start:start+64],device=device); optimizer.zero_grad(set_to_none=True)
            a,l=model(tx[ids],tc[ids]); loss=daily_joint_loss(a,l,y[ids],scale)
            assert torch.isfinite(loss); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
            optimizer.step(); losses.append(float(loss.detach()))
        _,p=network_predict(model,x[cal],data.future[cal],device)
        bs=float(np.mean((p[:,:,0]-(data.y[cal]>=16))**2))
        history.append(dict(epoch=epoch,loss=float(np.mean(losses)),cal_BS16=bs))
        if bs<best:
            best,best_epoch,stale=bs,epoch,0
            state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
        else: stale+=1
        if stale>=6: break
    model.load_state_dict(state)
    ac,pc=network_predict(model,x[cal],data.future[cal],device)
    ae,pe=network_predict(model,x[ev],data.future[ev],device)
    checkpoint=PRIVATE/'models'/f'{tag}.pt'
    torch.save(dict(state=state,config=model.config,features=data.features,
        scaler={k:torch.as_tensor(v) for k,v in scaler.items()},seed=seed,best_epoch=best_epoch),checkpoint)
    result=dict(checkpoint=checkpoint.name,checkpoint_sha256=sha(checkpoint),best_epoch=best_epoch,
        best_cal_BS16=best,parameters=sum(p.numel() for p in model.parameters()),
        history=history,seconds=time.perf_counter()-tick)
    del model,tx,tc,y
    if device=='cuda':torch.cuda.empty_cache()
    return ac,ae,pc,pe,result


def score(frame):
    # Seasons refer to the target day's nominal end, rather than all three leads' issue month.
    shifted=frame.copy(); shifted.issue=pd.to_datetime(shifted.issue)+pd.to_timedelta(shifted.lead_day,unit='D')
    return score_predictions(shifted)


def collect(manifest):
    frames=[]; thresholds=[]; seeds=[]
    for year,exp,kind in itertools.product(YEARS,feature_groups(),MODELS):
        entries=[m for m in manifest['models'] if (m['year'],m['experiment'],m['model'])==(year,exp,kind)]
        expected=[42] if kind=='lgbm' else SEEDS
        if sorted(m['seed'] for m in entries)!=expected:raise ValueError('Incomplete matrix')
        c=[pd.read_parquet(PRIVATE/m['cal_predictions']) for m in entries]
        e=[pd.read_parquet(PRIVATE/m['eval_predictions']) for m in entries]
        seeds.extend(e)
        if kind!='lgbm':
            cm=seed_mean(c,tuple(expected)); em=seed_mean(e,tuple(expected)); em,tau=ensemble_thresholds(cm,em)
            thresholds.extend([dict(year=year,experiment=exp,model=kind,**t) for t in tau])
        else:em=e[0]
        frames.append(em)
    all_frames=pd.concat(frames,ignore_index=True)
    for day in [1,2,3]:
        parts=[g.sort_values('issue') for _,g in all_frames[all_frames.lead_day==day].groupby(['model','experiment'])]
        for p in parts[1:]:
            for key in ['issue','obs','ref16','ref50','ref100']:
                np.testing.assert_array_equal(p[key].to_numpy(),parts[0][key].to_numpy())
    all_frames.to_parquet(PRIVATE/'predictions_ensemble.parquet',index=False)
    pd.concat(seeds,ignore_index=True).to_parquet(PRIVATE/'predictions_seed.parquet',index=False)
    score(all_frames).to_csv(REPORT/'scores_by_year.csv',index=False,lineterminator='\n')
    pooled=all_frames.copy();pooled.year='pooled2021-2023'
    scores=score(pooled);scores.to_csv(REPORT/'scores_pooled.csv',index=False,lineterminator='\n')
    main=scores[(scores.season=='all')&(scores.threshold_mm==16)]
    assert len(main)==72
    main.to_csv(REPORT/'scores_main_72.csv',index=False,lineterminator='\n')
    pd.DataFrame(thresholds).to_csv(REPORT/'ensemble_thresholds.csv',index=False,lineterminator='\n')


def baselines(data):
    frames=[]
    for year in YEARS:
        train=data.dates.year<=year-2;ev=data.dates.year==year
        fitted=fit_climatology(data.dates[train],data.y[train])
        amount,prob=predict_climatology(data.dates[ev],fitted)
        for kind,a,p in [('climatology',amount,prob),('always_zero',np.zeros_like(amount),np.zeros_like(prob))]:
            frames.append(prediction_frame(data.dates[ev],data.y[ev],a,p,prob,[],kind,'REF',year,-1))
    frame=pd.concat(frames,ignore_index=True);frame.to_parquet(PRIVATE/'predictions_baselines.parquet',index=False)
    frame.year='pooled2021-2023';score(frame).to_csv(REPORT/'baseline_scores.csv',index=False,lineterminator='\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--pilot',action='store_true')
    args=parser.parse_args()
    assert json.loads((REPORT/'source_audit.json').read_text(encoding='utf8'))['status']=='passed'
    (PRIVATE/'models').mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(4);device='cuda' if torch.cuda.is_available() else 'cpu'
    data,daily=load_development()
    daily.to_parquet(PRIVATE/'daily_predictors_and_labels.parquet')
    paths=['src/daily_gauge_dataset.py','src/daily_gauge_models.py','scripts/run_daily_gauge_matrix.py',
        'src/short_range_dataset.py','src/short_range_evaluation.py','src/short_range_ablation.py',
        'src/tft_regional.py','src/informer_regional_pilot.py','scripts/pilot_short_range.py']
    protocol=dict(status='frozen_before_first_fit',date='2026-11-04',region='Existing approximate 93-cell Danang-new footprint',
        predictors='Past-only ERA5 daily 12--12 UTC means; no satellite rain or future weather',
        label='CPC daily station-based gridded analysis, not direct area observation',
        history_days=7,encoder_steps=7,decoder_steps=3,calendar_variables=list(TIME),
        issue_utc_hour=12,target_intervals_hours=[[0,24],[24,48],[48,72]],
        feature_counts={k:len(v) for k,v in feature_groups().items()},groups=feature_groups(),
        years=YEARS,seeds=SEEDS,expected_models=168,models=MODELS,
        max_epochs=40,patience=6,batch=64,hidden=32,heads=4,informer_label_len=3,
        loss='normalized daily Tweedie+BCE; same thresholds16/50/100 as previous experiment',
        early_stopping='raw calibration BS16 averaged over three days',
        calibration='Platt and CSI decision thresholds on calibration only',
        fold='train2015..eval-2 / calibration eval-1 / evaluation2021,2022,2023',
        no_hyperparameter_tuning=True,shared_E7_mask=True,test2025_read=False,
        not_directly_comparable_to_previous='Label source, issue12Z, aggregation1d and readout changed; do not subtract old scores',
        code_hashes={p:sha(ROOT/p) for p in paths},source_hourly_sha256=sha(SOURCE),
        labels_sha256=sha(PRIVATE/'cpc_daily_region.parquet'),source_audit_sha256=sha(REPORT/'source_audit.json'))
    path=REPORT/'protocol_frozen.json'
    if path.exists():assert json.loads(path.read_text(encoding='utf8'))==protocol,'Protocol changed after freezing'
    else:dump(path,protocol)
    run_path=REPORT/'run.json'
    manifest=json.loads(run_path.read_text(encoding='utf8')) if run_path.exists() else dict(
        status='running',protocol_sha256=sha(path),device=device,total_samples=len(data.dates),models=[],baselines=[])
    assert manifest['protocol_sha256']==sha(path)
    finished={(m['year'],m['experiment'],m['model'],m['seed']) for m in manifest['models']}
    tasks=list(itertools.product(YEARS,feature_groups(),MODELS))
    if args.pilot:tasks=[(2021,'E0',kind) for kind in MODELS]
    for year,exp,kind in tasks:
        train=data.dates.year<=year-2;cal=data.dates.year==year-1;ev=data.dates.year==year
        sample=data.select(feature_groups()[exp]);clim=fit_climatology(data.dates[train],data.y[train])
        _,ref=predict_climatology(data.dates[ev],clim);_,cref=predict_climatology(data.dates[cal],clim)
        for seed in ([42] if kind=='lgbm' or args.pilot else SEEDS):
            if (year,exp,kind,seed) in finished:continue
            tag=f'{kind}_{exp}_{year}_s{seed}';tick=time.perf_counter()
            if kind=='lgbm':
                x,names=tabular_inputs(sample)
                ac,ae,pc,pe,meta=fit_lgbm(x,sample.y,train,cal,ev,PRIVATE/'models',tag)
                meta['tabular_names']=names
                for item in meta['output_models']:
                    if 'path' in item:item['sha256']=sha(PRIVATE/'models'/item['path'])
            else:ac,ae,pc,pe,meta=fit_network(kind,sample,train,cal,ev,tag,device)
            params=fit_calibration(sample.y[cal],pc)
            c=prediction_frame(data.dates[cal],sample.y[cal],ac,apply_calibration(pc,params),cref,params,kind,exp,year,seed)
            e=prediction_frame(data.dates[ev],sample.y[ev],ae,apply_calibration(pe,params),ref,params,kind,exp,year,seed)
            cp=f'{tag}_cal.parquet';ep=f'{tag}_eval.parquet'
            c.to_parquet(PRIVATE/cp,index=False);e.to_parquet(PRIVATE/ep,index=False)
            meta.update(year=year,experiment=exp,model=kind,seed=seed,features=sample.features,
                n_train=int(train.sum()),n_cal=int(cal.sum()),n_eval=int(ev.sum()),calibration=params,
                cal_predictions=cp,eval_predictions=ep,cal_predictions_sha256=sha(PRIVATE/cp),
                eval_predictions_sha256=sha(PRIVATE/ep),total_seconds=time.perf_counter()-tick)
            manifest['models'].append(meta);dump(run_path,manifest)
            print(f'{len(manifest["models"])}/168 {tag}: {meta["total_seconds"]:.1f}s',flush=True)
    if args.pilot:
        print('Pilot complete; run without --pilot to finish the frozen matrix.');return
    assert len(manifest['models'])==168
    collect(manifest);baselines(data);manifest['status']='complete';dump(run_path,manifest)
    print('Complete daily matrix: LightGBM24, TFT72, Informer72',flush=True)


if __name__=='__main__':main()
