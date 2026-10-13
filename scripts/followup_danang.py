"""Ba phép thử tiếp theo: Tweedie amount / bỏ terrain / 63ô chưa train.

Giữ artifact và hiệu chỉnh của domain screen; không đọc/chấm test2025.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,logging,subprocess,sys,time,warnings
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import torch
import lightgbm as lgb
from src.dataloader_v2 import DatasetV2,Normalizer,WindowSampler,product_a,sample_index
from src.domain_features import DomainSampler,DerivedNormalizer
from src.bilstm_v2 import BiLSTMV2,THRESHOLDS
from src.domain_inference import calibrated_probability
from src.verification import paired_block_bootstrap,metric_rmse,metric_csi,continuous_scores,contingency_scores
from scripts.screen_danang_domain import pack,tree_matrix,nn_train,predict_pack,score,tune_threshold,bs1
from scripts.pilot_bilstm_v2 import labels,totals,calibrate,climatology

SOURCE=ROOT/'data/operational/domain_screen_danang'
SOURCE_REPORT=ROOT/'reports/domain_screen_danang'
PRIVATE=ROOT/'data/operational/followup_danang'
REPORT=ROOT/'reports/followup_danang'
LOG=logging.getLogger('followup')

def metadata(task,args):
    source=json.loads((SOURCE_REPORT/'run.json').read_text(encoding='utf-8'))
    meta=dict(task=task,args=vars(args),started_utc=datetime.now(timezone.utc).isoformat(),
        git_commit=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip(),
        source_training_git=source['git_commit'],source_report_sha256=hashlib.sha256((SOURCE_REPORT/'run.json').read_bytes()).hexdigest(),
        source_cells=[r['site'] for r in source['cells']],history=[],completed=False,test_2025_scored=False)
    return source,meta

def write_run(report,meta):
    report.mkdir(parents=True,exist_ok=True)
    temporary=report/'run.tmp.json'
    temporary.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(report/'run.json')

def cfg_for(ds,source,scope='trained'):
    selected=set(r['site'] for r in source['cells'])
    if scope not in ('trained','unseen'):raise ValueError('Scope không hợp lệ')
    exclude=tuple(ds.cells.loc[~ds.cells.site.isin(selected) if scope=='trained' else ds.cells.site.isin(selected),'site'])
    return product_a(('A0','A1','D_RAW'),latency_h=4,provinces=('Đà Nẵng',),exclude_sites=exclude,issue_stride_h=6)

def load_sampler(ds,source,year,config,scope='trained'):
    folder=SOURCE/str(year)
    norm=Normalizer.load(folder/f'{"DOMAIN" if config in ("DOMAIN","NO_TERRAIN") else "RAW"}_normalizer.json')
    derived=DerivedNormalizer(**json.loads((folder/'derived_normalizer.json').read_text(encoding='utf-8'))) if config in ('DOMAIN','NO_TERRAIN') else None
    return DomainSampler(WindowSampler(ds,cfg_for(ds,source,scope),norm),
        'domain' if derived else 'padding',derived,derived_mask=[1,0,1,1] if config=='NO_TERRAIN' else None)

def taus_for(ds,index,y,prob):
    months=(ds.hours[index[:,1]]+pd.Timedelta(hours=7)).month
    tau=np.empty((3,3))
    for j in range(3):
        m=np.isin(months,[11,12,1,2]) if j==2 else np.isin(months,range(5,11))
        for k,t in enumerate(THRESHOLDS):
            tau[j,k]=tune_threshold(totals(y)[m,j]>=t,prob[m,j,k])
    return tau

def source_predictions(year,source):
    fold=SOURCE/str(year)
    if source.startswith('BiLSTM_'):
        config=source.removeprefix('BiLSTM_')
        runs=[f'BiLSTM_{config}_seed{s}' for s in [42,43,44]]
    else:runs=[source]
    values=[]
    for run in runs:
        with np.load(fold/f'{run}.npz') as f:
            values.append({k:f[k].copy() for k in ['amount_cal','amount_eval','prob_cal','prob_eval','y_eval']})
    for v in values[1:]:np.testing.assert_array_equal(v['y_eval'],values[0]['y_eval'])
    return {k:np.mean([v[k] for v in values],axis=0) if k!='y_eval' else values[0][k] for k in values[0]}

def compare_amount(ds,index,y,predictions,args,year):
    warm=np.isin((ds.hours[index[:,1]]+pd.Timedelta(hours=7)).month,range(5,11))
    frame=pd.DataFrame(dict(date=ds.hours[index[warm,1]]+pd.Timedelta(hours=7),obs=totals(y)[warm,0],
        **{name:totals(pred)[warm,0] for name,pred in predictions.items()}))
    a='LightGBM_RAW_TWEEDIE';results=[]
    for b in ['LightGBM_RAW_L1LOG','BiLSTM_RAW']:
        results.append(dict(year=year,**paired_block_bootstrap(frame,'obs',a,b,metric_rmse,n_boot=args.bootstrap,seed=year)))
        results.append(dict(year=year,**paired_block_bootstrap(frame,'obs',a,b,metric_csi(10),n_boot=args.bootstrap,seed=year)))
    return results

def amount_task(ds,args):
    source,meta=metadata('amount',args)
    report=REPORT/'amount';private=PRIVATE/'amount'
    report.mkdir(parents=True,exist_ok=True);private.mkdir(parents=True,exist_ok=True)
    rows,comparisons,events=[],[],[]
    for year in args.years:
        folder=SOURCE/str(year);target=private/str(year);target.mkdir(exist_ok=True)
        train,cal,ev=[np.load(folder/f'index_{n}.npy') for n in ['train','cal','eval']]
        sampler=load_sampler(ds,source,year,'RAW')
        tr,ca,ee=[pack(sampler,ix) for ix in [train,cal,ev]]
        x,xc,xe=map(tree_matrix,[tr,ca,ee])
        opts=dict(n_estimators=100,num_leaves=15,max_bin=63,min_child_samples=50,learning_rate=.05,
            n_jobs=4,random_state=42,verbosity=-1,deterministic=True,force_col_wise=True,
            objective='tweedie',tweedie_variance_power=1.5)
        ac,ae=np.empty_like(ca['y']),np.empty_like(ee['y'])
        start=time.perf_counter();LOG.info('Tweedie fold%s train%s',year,len(train))
        for h in range(6):
            model=lgb.LGBMRegressor(**opts).fit(x,tr['y'][:,h])
            ac[:,h]=model.booster_.predict(xc);ae[:,h]=model.booster_.predict(xe)
            model.booster_.save_model(str(target/f'amount{h}.txt'))
        if not np.isfinite(ae).all() or (ae<0).any():raise ValueError('Tweedie không hữu hạn/nonnegative')
        old=source_predictions(year,'LightGBM_RAW');nn=source_predictions(year,'BiLSTM_RAW')
        np.testing.assert_array_equal(old['y_eval'],ee['y'])
        pc,pe=old['prob_cal'],old['prob_eval']
        np.savez_compressed(target/'predictions.npz',amount_cal=ac,amount_eval=ae,prob_cal=pc,prob_eval=pe)
        tau=taus_for(ds,cal,ca['y'],pc)
        reference=climatology(ds,sample_index(ds,cfg_for(ds,source),range(2015,year-1)),ev)[1]
        for name,pred in [('LightGBM_RAW_TWEEDIE',ae),('LightGBM_RAW_L1LOG',old['amount_eval']),('BiLSTM_RAW',nn['amount_eval'])]:
            use_pe=nn['prob_eval'] if name=='BiLSTM_RAW' else pe
            use_tau=taus_for(ds,cal,ca['y'],nn['prob_cal']) if name=='BiLSTM_RAW' else tau
            r,_=score(ds,ev,ee['y'],pred,use_pe,reference,use_tau,name,year);rows+=r
            warm=np.isin((ds.hours[ev[:,1]]+pd.Timedelta(hours=7)).month,range(5,11))
            o,p=totals(ee['y'])[:,0],totals(pred)[:,0]
            for threshold in [10,25]:
                mask=warm&(o>=threshold)
                events.append(dict(year=year,source=name,event_threshold=threshold,
                    **continuous_scores(o[mask],p[mask])))
        comparisons+=compare_amount(ds,ev,ee['y'],dict(LightGBM_RAW_TWEEDIE=ae,LightGBM_RAW_L1LOG=old['amount_eval'],BiLSTM_RAW=nn['amount_eval']),args,year)
        meta['history'].append(dict(year=year,seconds=time.perf_counter()-start,n_train=len(train),n_eval=len(ev),
            train_index_sha256=hashlib.sha256(train.tobytes()).hexdigest(),event_head_changed=False,opts=opts))
        pd.DataFrame(rows).to_csv(report/'scores.csv',index=False)
        pd.DataFrame(events).to_csv(report/'wet_event_scores.csv',index=False)
        (report/'paired_bootstrap.json').write_text(json.dumps(comparisons,indent=2),encoding='utf-8')
        write_run(report,meta)
        LOG.info('Tweedie fold%s COMPLETE',year)
        del tr,ca,ee,x,xc,xe;gc.collect()
    meta['completed']=True;write_run(report,meta)

def terrain_task(ds,args,device):
    source,meta=metadata('terrain',args)
    report=REPORT/'terrain';private=PRIVATE/'terrain'
    report.mkdir(parents=True,exist_ok=True);private.mkdir(parents=True,exist_ok=True)
    rows,comparisons=[],[]
    for year in args.years:
        folder=SOURCE/str(year);target=private/str(year);target.mkdir(exist_ok=True)
        train,cal,ev=[np.load(folder/f'index_{n}.npy') for n in ['train','cal','eval']]
        sampler=load_sampler(ds,source,year,'NO_TERRAIN')
        tr,ca,ee=[pack(sampler,ix) for ix in [train,cal,ev]]
        ensemble=[]
        for seed in [42,43,44]:
            run=f'NO_TERRAIN_seed{seed}'
            start=time.perf_counter();LOG.info('%s fold%s',run,year)
            model,state,history=nn_train(tr,ca,seed,args,device)
            ac,lc=predict_pack(model,ca,args.batch_size,device)
            ae,le=predict_pack(model,ee,args.batch_size,device)
            pc,params=calibrate(lc,ca['y'],lc);pe,_=calibrate(lc,ca['y'],le)
            torch.save(dict(model=state,seed=seed,derived_mask=[1,0,1,1],year=year),target/f'{run}.pt')
            np.savez_compressed(target/f'{run}.npz',amount_cal=ac,amount_eval=ae,prob_cal=pc,prob_eval=pe)
            ensemble.append(dict(amount_cal=ac,amount_eval=ae,prob_cal=pc,prob_eval=pe))
            meta['history'].append(dict(year=year,run=run,epochs=history,calibration=params,
                params=sum(p.numel() for p in model.parameters()),seconds=time.perf_counter()-start))
            write_run(report,meta)
            del model
            if device.type=='cuda':torch.cuda.empty_cache()
        new={k:np.mean([v[k] for v in ensemble],axis=0) for k in ensemble[0]}
        np.savez_compressed(target/'ensemble.npz',**new)
        full=source_predictions(year,'BiLSTM_DOMAIN');raw=source_predictions(year,'BiLSTM_RAW')
        reference=climatology(ds,sample_index(ds,cfg_for(ds,source),range(2015,year-1)),ev)[1]
        month=(ds.hours[ev[:,1]]+pd.Timedelta(hours=7)).month
        warm=np.isin(month,range(5,11))
        frame=pd.DataFrame(dict(date=ds.hours[ev[warm,1]]+pd.Timedelta(hours=7),obs=totals(ee['y'])[warm,0]))
        for name,pred in [('BiLSTM_NO_TERRAIN',new),('BiLSTM_DOMAIN',full),('BiLSTM_RAW',raw)]:
            tau=taus_for(ds,cal,ca['y'],pred['prob_cal'])
            r,_=score(ds,ev,ee['y'],pred['amount_eval'],pred['prob_eval'],reference,tau,name,year);rows+=r
            frame[name]=(pred['prob_eval'][warm,0,1]>=tau[0,1]).astype(float)
            frame['p_'+name]=pred['prob_eval'][warm,0,0]
        frame['event']=(frame.obs>=10).astype(float)
        for a,b in [('BiLSTM_DOMAIN','BiLSTM_NO_TERRAIN'),('BiLSTM_NO_TERRAIN','BiLSTM_RAW')]:
            r=paired_block_bootstrap(frame,'event',a,b,metric_csi(1),n_boot=args.bootstrap,seed=year)
            r['metric']='CSI_probability>=10mm/3h'
            comparisons.append(dict(year=year,**r))
            comparisons.append(dict(year=year,**paired_block_bootstrap(frame,'obs','p_'+a,'p_'+b,bs1,n_boot=args.bootstrap,seed=year)))
        pd.DataFrame(rows).to_csv(report/'scores.csv',index=False)
        (report/'paired_bootstrap.json').write_text(json.dumps(comparisons,indent=2),encoding='utf-8')
        LOG.info('Terrain fold%s COMPLETE',year)
        del tr,ca,ee;gc.collect()
    meta['completed']=True;write_run(report,meta)

def spatial_task(ds,args,device):
    source,meta=metadata('spatial',args)
    report=REPORT/'spatial';private=PRIVATE/'spatial'
    report.mkdir(parents=True,exist_ok=True);private.mkdir(parents=True,exist_ok=True)
    rows,comparisons,geography=[],[],[]
    trained=set(r['site'] for r in source['cells'])
    cfg=cfg_for(ds,source,'unseen')
    sites=ds.cells.iloc[ds.select_cells(cfg)].site.tolist()
    assert len(sites)==63 and not set(sites)&trained
    meta['unseen_sites']=sites;meta['fit_on_unseen']=False
    meta['climatology']='Reference uses past labels at unseen cells; neural weights/norm/Platt/tau use only30trained cells. Nearby cells/episodes correlated; not independent cross-province test.'
    for year in args.years:
        target=private/str(year);target.mkdir(exist_ok=True)
        ev=sample_index(ds,cfg,[year]);np.save(target/'index_eval.npy',ev)
        yy=labels(ds,ev)
        reference=climatology(ds,sample_index(ds,cfg,range(2015,year-1)),ev)[1]
        source_scores=pd.read_csv(SOURCE_REPORT/'scores.csv')
        month=(ds.hours[ev[:,1]]+pd.Timedelta(hours=7)).month
        warm=np.isin(month,range(5,11))
        frame=pd.DataFrame(dict(date=ds.hours[ev[warm,1]]+pd.Timedelta(hours=7),obs=totals(yy)[warm,0]))
        for config in ['RAW','DOMAIN']:
            start=time.perf_counter();LOG.info('Unseen %s fold%s n%s',config,year,len(ev))
            sampler=load_sampler(ds,source,year,config,'unseen')
            data=pack(sampler,ev);ensemble=[]
            for seed in [42,43,44]:
                name=f'BiLSTM_{config}_seed{seed}'
                state=torch.load(SOURCE/str(year)/f'{name}.pt',map_location=device,weights_only=True)
                model=BiLSTMV2(data['x_past'].shape[-1],data['x_future'].shape[-1]).to(device)
                model.load_state_dict(state['model']);model.eval()
                ae,le=predict_pack(model,data,args.batch_size,device)
                params=next(r['calibration'] for r in source['history'] if r['year']==year and r['run']==name)
                pe=calibrated_probability(le,params)
                ensemble.append((ae,pe));del model
                if device.type=='cuda':torch.cuda.empty_cache()
            ae=np.mean([v[0] for v in ensemble],axis=0);pe=np.mean([v[1] for v in ensemble],axis=0)
            np.savez_compressed(target/f'BiLSTM_{config}.npz',amount_eval=ae,prob_eval=pe)
            name='BiLSTM_'+config
            tau=np.empty((3,3))
            for j,window in enumerate(['0-3h','3-6h','0-6h']):
                row=source_scores[(source_scores.year==year)&(source_scores.source==name)&
                    (source_scores.window==window)&(source_scores.season==('nov_feb' if j==2 else 'may_oct'))].iloc[0]
                tau[j]=[row[f'tau_{t:g}'] for t in THRESHOLDS]
            r,_=score(ds,ev,yy,ae,pe,reference,tau,name+'_unseen63',year);rows+=r
            frame[name]=(pe[warm,0,1]>=tau[0,1]).astype(float);frame['p_'+name]=pe[warm,0,0]
            for band in ['coast_le20km','inland_gt20km']:
                dist=ds.cells.iloc[ev[:,0]].coast_dist_km.to_numpy()
                m=warm&(dist<=20 if band=='coast_le20km' else dist>20)
                geography.append(dict(year=year,source=name,band=band,
                    **continuous_scores(totals(yy)[m,0],totals(ae)[m,0]),
                    **{'CSI_probability10':contingency_scores((totals(yy)[m,0]>=10).astype(float),
                        (pe[m,0,1]>=tau[0,1]).astype(float),1)['CSI']}))
            meta['history'].append(dict(year=year,config=config,n_eval=len(ev),seconds=time.perf_counter()-start,
                index_sha256=hashlib.sha256(ev.tobytes()).hexdigest(),calibration_ref='Frozen30cell source'))
            del data;gc.collect()
        frame['event']=(frame.obs>=10).astype(float)
        r=paired_block_bootstrap(frame,'event','BiLSTM_DOMAIN','BiLSTM_RAW',metric_csi(1),n_boot=args.bootstrap,seed=year)
        r['metric']='CSI_probability>=10mm/3h'
        comparisons.append(dict(year=year,**r))
        comparisons.append(dict(year=year,**paired_block_bootstrap(frame,'obs','p_BiLSTM_DOMAIN','p_BiLSTM_RAW',bs1,n_boot=args.bootstrap,seed=year)))
        pd.DataFrame(rows).to_csv(report/'scores.csv',index=False)
        pd.DataFrame(geography).to_csv(report/'geography.csv',index=False)
        (report/'paired_bootstrap.json').write_text(json.dumps(comparisons,indent=2),encoding='utf-8')
        write_run(report,meta);LOG.info('Unseen fold%s COMPLETE',year)
    meta['completed']=True;write_run(report,meta)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--task',choices=['amount','terrain','spatial','all'],default='all')
    ap.add_argument('--years',nargs='+',type=int,default=[2021,2022,2023])
    ap.add_argument('--epochs',type=int,default=15);ap.add_argument('--patience',type=int,default=4)
    ap.add_argument('--batch-size',type=int,default=256);ap.add_argument('--bootstrap',type=int,default=1000)
    args=ap.parse_args()
    if not set(args.years).issubset({2021,2022,2023}):raise ValueError('Test2025 giữ kín')
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    warnings.filterwarnings('ignore',message="'force_all_finite' was renamed",category=FutureWarning)
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    ds=DatasetV2(ROOT/'data/processed/dataset_v2_danang')
    if args.task in ('amount','all'):amount_task(ds,args)
    if args.task in ('terrain','all'):terrain_task(ds,args,device)
    if args.task in ('spatial','all'):spatial_task(ds,args,device)
    LOG.info('COMPLETE %s',args.task)
if __name__=='__main__':main()
