"""Time-bounded matched E0/E7 Informer development pilot; never open 2025."""
from pathlib import Path
import argparse,json,math,sys,time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import torch
from src.informer_regional_pilot import RegionalInformer
from src.short_range_dataset import (load_development,feature_groups,train_scaler,scale_inputs,
    fit_climatology,predict_climatology,file_hash,SOURCE,TIME)
from src.short_range_evaluation import fit_calibration,apply_calibration,prediction_frame,score_predictions
from src.short_range_ablation import seed_mean,ensemble_thresholds
from src.tft_regional import daily_joint_loss,daily_tweedie_deviance
from scripts.pilot_short_range import dump,raw_logit,network_predict

REPORT=ROOT/"reports/informer_regional_pilot_2026_10_21"
PRIVATE=ROOT/"data/operational/short_range/informer_pilot_2026_10_21"


def fit(samples,train,cal,ev,tag,seed,device):
    np.random.seed(seed);torch.manual_seed(seed)
    if device=='cuda':torch.cuda.manual_seed_all(seed)
    scaler=train_scaler(samples.x[train]);x=scale_inputs(samples.x,scaler)
    model=RegionalInformer(x.shape[-1],[samples.features.index(n) for n in TIME]).to(device);model.set_scaler(scaler)
    y=torch.as_tensor(samples.y[train],device=device);mu=y.mean(0).clamp_min(.001)
    scale=daily_tweedie_deviance(mu,y).mean(0).detach()
    with torch.no_grad():
        mean=float(mu.mean());model.amount.bias.fill_(mean if mean>20 else math.log(math.expm1(mean)))
        rates=(y[:,:,None]>=y.new_tensor([16.,50.,100.])).float().mean((0,1)).cpu().numpy()
        model.events.bias.copy_(torch.as_tensor(raw_logit(rates),device=device))
    tx=torch.as_tensor(x[train],device=device);tc=torch.as_tensor(samples.future[train],device=device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.0001)
    rng=np.random.default_rng(seed);best=float('inf');best_state=None;history=[];stale=0;tick=time.perf_counter()
    if device=='cuda':torch.cuda.reset_peak_memory_stats()
    for epoch in range(1,41):
        model.train();losses=[];order=rng.permutation(len(tx))
        for start in range(0,len(order),64):
            ids=torch.as_tensor(order[start:start+64],device=device);optimizer.zero_grad(set_to_none=True)
            amount,logits=model(tx[ids],tc[ids]);loss=daily_joint_loss(amount,logits,y[ids],scale)
            if not torch.isfinite(loss):raise ValueError("Nonfinite Informer loss")
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step();losses.append(float(loss.detach()))
        _,prob=network_predict(model,x[cal],samples.future[cal],device)
        bs=float(np.mean((prob[:,:,0]-(samples.y[cal]>=16))**2))
        history.append(dict(epoch=epoch,loss=float(np.mean(losses)),cal_BS16=bs))
        if bs<best:
            best,best_epoch,stale=bs,epoch,0;best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
        else:stale+=1
        if stale>=6:break
    model.load_state_dict(best_state)
    ac,pc=network_predict(model,x[cal],samples.future[cal],device);ae,pe=network_predict(model,x[ev],samples.future[ev],device)
    target=PRIVATE/(tag+'.pt')
    torch.save(dict(config=model.config,state=best_state,scaler={k:torch.as_tensor(v) for k,v in scaler.items()},features=samples.features,seed=seed),target)
    saved=torch.load(target,map_location='cpu',weights_only=True);check=RegionalInformer(**saved['config']).to(device);check.load_state_dict(saved['state'])
    for mask,a,p in [(cal,ac,pc),(ev,ae,pe)]:
        aa,pp=network_predict(check,x[mask],samples.future[mask],device)
        np.testing.assert_allclose(aa,a,rtol=2e-5,atol=1e-5);np.testing.assert_allclose(pp,p,rtol=2e-5,atol=1e-6)
    meta=dict(seed=seed,best_epoch=best_epoch,best_cal_BS16=best,history=history,seconds=time.perf_counter()-tick,
              parameters=sum(p.numel() for p in model.parameters()),checkpoint=target.name,
              checkpoint_sha256=file_hash(target),full_calibration_evaluation_replay=True,
              peak_allocated_mib=float(torch.cuda.max_memory_allocated()/1024**2) if device=='cuda' else None)
    del model,check,tx,tc,y
    if device=='cuda':torch.cuda.empty_cache()
    return ac,ae,pc,pe,meta


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--max-minutes',type=float,default=10.);args=parser.parse_args()
    REPORT.mkdir(parents=True,exist_ok=True);PRIVATE.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(4);device='cuda' if torch.cuda.is_available() else 'cpu'
    paths=['src/informer_regional_pilot.py','scripts/pilot_informer_regional.py','src/short_range_dataset.py',
           'src/short_range_evaluation.py','src/tft_regional.py']+[p.relative_to(ROOT).as_posix() for p in (ROOT/'src/informer').glob('*.py')]
    protocol=dict(scope='Exploratory E0/E7 regional Informer adaptation, not a full architecture study',
        frozen_before_first_fit=True,experiments=['E0','E7'],seeds=[42,43,44],evaluation_years=[2021,2022,2023],
        max_epochs=40,patience=6,batch=64,hidden=32,heads=4,factor=3,encoder_layers=2,decoder_layers=1,distil=True,label_len=14,
        loss='Same daily normalized Tweedie + BCE as TFT',selection='raw calibration BS16 averaged over three days',
        optimizer='AdamW lr0.001 weight_decay0.0001, gradient norm1',time_budget_minutes=args.max_minutes,
        no_future_weather=True,no_past_rain=True,test2025_read=False,
        limitations=['Local Informer adaptation; not exact reproduction of paper benchmarks','Decoder prefix uses past meteorology; future meteorology zero',
                     'Corrected sparse query count; deterministic evaluation key samples','Only E0/E7; no hyperparameter tuning; development years already explored',
                     'Compare same completed seed set with TFT; no claim of superiority from point estimates'],
        code_sha256={p:file_hash(ROOT/p) for p in paths},source_sha256=file_hash(SOURCE))
    if protocol['source_sha256']!='92a6bc6a527b25107761e85f0d14e64713a39dfd2930560a4498927c27dfc448':raise ValueError('Source changed')
    frozen=REPORT/'protocol_frozen.json'
    if frozen.exists():assert json.loads(frozen.read_text(encoding='utf8'))==protocol
    else:dump(frozen,protocol)
    data=load_development();assert len(data.dates)==3248 and data.dates.max().year==2023
    manifest=dict(status='running',protocol=protocol,device=device,gpu=torch.cuda.get_device_name(0) if device=='cuda' else None,
                  models=[],test2025_read=False)
    dump(REPORT/'run.json',manifest);start=time.perf_counter();frames=[];calframes=[];groups=feature_groups()
    jobs=[(seed,year,exp) for seed in [42,43,44] for year in [2021,2022,2023] for exp in ['E0','E7']]
    for seed,year,exp in jobs:
        if time.perf_counter()-start>args.max_minutes*60:manifest['status']='partial_time_budget';break
        tag=f'informer_{year}_{exp}_seed{seed}';selected=data.select(groups[exp])
        train=data.dates.year<year-1;cal=data.dates.year==year-1;ev=data.dates.year==year
        climate=fit_climatology(data.dates[train],data.y[train]);_,rc=predict_climatology(data.dates[cal],climate);_,re=predict_climatology(data.dates[ev],climate)
        print('START',tag,flush=True)
        ac,ae,pc,pe,meta=fit(selected,train,cal,ev,tag,seed,device)
        params=fit_calibration(data.y[cal],pc)
        cf=prediction_frame(data.dates[cal],data.y[cal],ac,apply_calibration(pc,params),rc,params,'informer',exp,year,seed)
        ef=prediction_frame(data.dates[ev],data.y[ev],ae,apply_calibration(pe,params),re,params,'informer',exp,year,seed)
        cf.to_parquet(PRIVATE/(tag+'_cal.parquet'),index=False);ef.to_parquet(PRIVATE/(tag+'_eval.parquet'),index=False)
        meta.update(year=year,experiment=exp,n_train=int(train.sum()),n_cal=int(cal.sum()),n_eval=int(ev.sum()),
                    calibration=params,cal_predictions=tag+'_cal.parquet',eval_predictions=tag+'_eval.parquet')
        manifest['models'].append(meta);dump(REPORT/'run.json',manifest)
        print('DONE',tag,round(meta['seconds'],2),'seconds',flush=True)
    else:manifest['status']='complete'
    complete=[seed for seed in [42,43,44] if sum(m['seed']==seed for m in manifest['models'])==6]
    manifest.update(completed_seeds=complete,elapsed_seconds=time.perf_counter()-start)
    if not complete:dump(REPORT/'run.json',manifest);raise RuntimeError('No complete matched seed set')
    ensemble=[];matched=[];old=ROOT/'data/operational/short_range/ablation_2026_10_21'
    oldrun=json.loads((ROOT/'reports/short_range_ablation_2026_10_21/run.json').read_text(encoding='utf8'))
    for year in [2021,2022,2023]:
        for exp in ['E0','E7']:
            for learner in ['informer','tft']:
                entries=manifest['models'] if learner=='informer' else oldrun['models']
                entries=[m for m in entries if m.get('learner',learner)==learner and m['year']==year and m['experiment']==exp and m['seed'] in complete]
                directory=PRIVATE if learner=='informer' else old
                c=[pd.read_parquet(directory/m['cal_predictions']) for m in entries];e=[pd.read_parquet(directory/m['eval_predictions']) for m in entries]
                if len(complete)>1:cm=seed_mean(c,tuple(complete));em=seed_mean(e,tuple(complete));em,_=ensemble_thresholds(cm,em)
                else:em=e[0]
                ensemble.append(em);matched+=e
    combined=pd.concat(ensemble,ignore_index=True);combined.to_parquet(PRIVATE/'predictions_matched.parquet',index=False)
    score_predictions(combined).to_csv(REPORT/'scores_by_year.csv',index=False,lineterminator='\n')
    pooled=combined.copy();pooled['year']='pooled2021-2023';score_predictions(pooled).to_csv(REPORT/'scores_pooled.csv',index=False,lineterminator='\n')
    manifest.update(comparison='TFT/Informer same completed seeds, exact same observations and Brier references',
                    evaluation_rows_per_model_experiment_lead=1075,full_replayed_runs=len(manifest['models']))
    for exp in ['E0','E7']:
        for day in [1,2,3]:
            a=combined[(combined.model=='tft')&(combined.experiment==exp)&(combined.lead_day==day)].sort_values('issue')
            b=combined[(combined.model=='informer')&(combined.experiment==exp)&(combined.lead_day==day)].sort_values('issue')
            assert a.issue.tolist()==b.issue.tolist();np.testing.assert_array_equal(a.obs,b.obs);np.testing.assert_array_equal(a.ref16,b.ref16)
    dump(REPORT/'run.json',manifest);print('PILOT_COMPLETE',len(manifest['models']),'runs',complete,round(manifest['elapsed_seconds'],2),'seconds',flush=True)


if __name__=='__main__':main()
