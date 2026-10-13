"""Sàng lọc domain Đà Nẵng: BASE / RAW / DOMAIN, fold năm và hai learner.

Chỉ dùng khí tượng quá khứ. RAW/DOMAIN cùng nguồn, kích thước và tham số NN.
Các năm 2021–2023 là validation lịch sử; test 2025 giữ kín.
"""
from __future__ import annotations
import argparse, copy, gc, hashlib, json, logging, random, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import faulthandler
faulthandler.dump_traceback_later(60,repeat=True)
import numpy as np
import pandas as pd
import torch
import lightgbm as lgb
from src.bilstm_v2 import BiLSTMV2,pilot_loss,THRESHOLDS,AGG_WINDOWS
from src.dataloader_v2 import DatasetV2,Normalizer,WindowSampler,product_a,sample_index,epoch_subset
from src.domain_features import DomainSampler,DerivedNormalizer,DERIVED_NAMES
from src.verification import (continuous_scores,contingency_scores,brier_score,brier_skill_score,
                              paired_block_bootstrap,metric_csi)
from scripts.pilot_bilstm_v2 import choose_cells,labels,totals,calibrate,climatology
faulthandler.cancel_dump_traceback_later()
LOG=logging.getLogger('domain')

def pack(sampler,index):
    parts=[sampler.batch(index[i:i+512]) for i in range(0,len(index),512)]
    out={k:np.concatenate([p[k] for p in parts]) for k in ('x_past','x_future','static','y')}
    if not all(np.isfinite(v).all() for v in out.values()):
        raise ValueError('Tensor không hữu hạn')
    return out

def batches(data,order,batch_size,device):
    for i in range(0,len(order),batch_size):
        ix=order[i:i+batch_size]
        yield {k:torch.from_numpy(v[ix]).to(device) for k,v in data.items()}

@torch.no_grad()
def predict_pack(model,data,batch_size,device):
    model.eval()
    amount,logit=[],[]
    for b in batches(data,np.arange(len(data['y'])),batch_size,device):
        a,l=model(b['x_past'],b['x_future'],b['static'])
        amount.append(torch.expm1(a).cpu().numpy())
        logit.append(l.cpu().numpy())
    return np.concatenate(amount),np.concatenate(logit)

def tune_threshold(obs,prob):
    # Lưới và mục tiêu cố định trước eval; tie dùng ngưỡng đầu tiên (nhỏ hơn).
    if not np.any(obs): return .5
    grid=np.arange(.01,.951,.01)
    scores=[contingency_scores(obs,(prob>=t).astype(float),1)['CSI'] for t in grid]
    return float(grid[int(np.nanargmax(scores))])

def nn_train(train,cal,seed,args,device):
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    model=BiLSTMV2(train['x_past'].shape[2],train['x_future'].shape[2]).to(device)
    optimizer=torch.optim.Adam(model.parameters(),lr=1e-3)
    cal_ix=epoch_subset(np.arange(len(cal['y'])),min(12000,len(cal['y'])),2026)
    best_loss,best,stale=float('inf'),None,0
    history=[]
    for epoch in range(args.epochs):
        start=time.perf_counter()
        model.train()
        loss_sum=0.
        order=np.random.default_rng(seed*1000+epoch).permutation(len(train['y']))
        for b in batches(train,order,args.batch_size,device):
            optimizer.zero_grad(set_to_none=True)
            a,l=model(b['x_past'],b['x_future'],b['static'])
            loss=pilot_loss(a,l,b['y'])
            if not torch.isfinite(loss):raise ValueError('Loss không hữu hạn')
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
            optimizer.step()
            loss_sum+=float(loss.item())*len(b['y'])
        model.eval()
        vloss=0.
        with torch.no_grad():
            for b in batches(cal,cal_ix,args.batch_size,device):
                a,l=model(b['x_past'],b['x_future'],b['static'])
                vloss+=float(pilot_loss(a,l,b['y']).item())*len(b['y'])
        vloss/=len(cal_ix)
        history.append(dict(epoch=epoch+1,train_loss=loss_sum/len(order),cal_loss=vloss,seconds=time.perf_counter()-start))
        LOG.info('seed%s epoch%s train %.4f cal %.4f %.1fs',seed,epoch+1,loss_sum/len(order),vloss,history[-1]['seconds'])
        if vloss<best_loss:
            best_loss,best,stale=vloss,copy.deepcopy(model.state_dict()),0
        else:
            stale+=1
            if stale>=args.patience:break
    model.load_state_dict(best)
    return model,best,history

def tree_matrix(data):
    return np.concatenate([data['x_past'].reshape(len(data['y']),-1),
                           data['x_future'].reshape(len(data['y']),-1),data['static']],axis=1)

def tree_train(train,cal,evaluation,args,private,name):
    x,xc,xe=map(tree_matrix,(train,cal,evaluation))
    opts=dict(n_estimators=args.trees,num_leaves=15,max_bin=63,min_child_samples=50,
              learning_rate=.05,n_jobs=4,random_state=42,verbosity=-1,
              deterministic=True,force_col_wise=True)
    ac,ae=np.zeros_like(cal['y']),np.zeros_like(evaluation['y'])
    lc,le=np.empty((len(xc),9),np.float32),np.empty((len(xe),9),np.float32)
    for h in range(6):
        model=lgb.LGBMRegressor(objective='regression_l1',**opts).fit(x,np.log1p(train['y'][:,h]))
        ac[:,h]=np.expm1(np.maximum(model.booster_.predict(xc),0))
        ae[:,h]=np.expm1(np.maximum(model.booster_.predict(xe),0))
        model.booster_.save_model(str(private/f'{name}_amount{h}.txt'))
    ev=(totals(train['y'])[:,:,None]>=np.array(THRESHOLDS)).reshape(-1,9)
    for j in range(9):
        if len(np.unique(ev[:,j]))<2:
            p=(ev[:,j].sum()+1)/(len(x)+2)
            lc[:,j]=le[:,j]=np.log(p/(1-p))
        else:
            model=lgb.LGBMClassifier(objective='binary',**opts).fit(x,ev[:,j].astype(int))
            lc[:,j]=model.booster_.predict(xc,raw_score=True)
            le[:,j]=model.booster_.predict(xe,raw_score=True)
            model.booster_.save_model(str(private/f'{name}_event{j}.txt'))
    return ac,ae,lc,le

def score(ds,index,y,amount,prob,reference,taus,source,year):
    month=(ds.hours[index[:,1]]+pd.Timedelta(hours=7)).month.to_numpy()
    seasons=np.where(np.isin(month,[11,12,1,2]),'nov_feb',np.where((month>=5)&(month<=10),'may_oct','mar_apr'))
    rows=[]
    for season in ['may_oct','nov_feb','mar_apr']:
        mask=seasons==season
        for j in ([2] if season=='nov_feb' else [0,1,2]):
            o=totals(y)[mask,j]; a=totals(amount)[mask,j]
            row=dict(year=year,source=source,season=season,window=f'{AGG_WINDOWS[j][0]}-{AGG_WINDOWS[j][1]}h',
                     **continuous_scores(o,a))
            for k,thr in enumerate(THRESHOLDS):
                event=(o>=thr).astype(float)
                rule=(prob[mask,j,k]>=taus[j,k]).astype(float)
                cs=contingency_scores(event,rule,1)
                row[f'CSI_amount_{thr:g}']=contingency_scores(o,a,thr)['CSI']
                row[f'BS_{thr:g}']=brier_score(event,prob[mask,j,k])
                row[f'BSS_{thr:g}']=brier_skill_score(event,prob[mask,j,k],reference[mask,j,k])
                for key in ['CSI','POD','FAR','FBI','n_obs_events','hits','misses','false_alarms']:
                    row[f'{key}_prob_{thr:g}']=cs[key]
                row[f'tau_{thr:g}']=taus[j,k]
            rows.append(row)
    return rows,seasons

def bs1(obs,p):
    return brier_score(obs>=1,p)
bs1.lower_is_better=True
bs1.__name__='BS>=1mm/3h'
def bs10(obs,p):
    return brier_score(obs>=10,p)
bs10.lower_is_better=True
bs10.__name__='BS>=10mm/3h'

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--years',nargs='+',type=int,default=[2021,2022,2023])
    ap.add_argument('--seeds',nargs='+',type=int,default=[42,43,44])
    ap.add_argument('--cells',type=int,default=30)
    ap.add_argument('--train-samples',type=int,default=30000)
    ap.add_argument('--epochs',type=int,default=15)
    ap.add_argument('--patience',type=int,default=4)
    ap.add_argument('--trees',type=int,default=100)
    ap.add_argument('--batch-size',type=int,default=256)
    ap.add_argument('--bootstrap',type=int,default=1000)
    ap.add_argument('--smoke',action='store_true')
    ap.add_argument('--name',default='domain_screen_danang')
    ap.add_argument('--resume',action='store_true')
    args=ap.parse_args()
    if not set(args.years).issubset({2021,2022,2023}):raise ValueError('Chỉ các fold 2021–2023; test 2025 giữ kín')
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    import warnings
    warnings.filterwarnings('ignore',message="'force_all_finite' was renamed",category=FutureWarning)
    torch.set_num_threads(4)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    torch.backends.cudnn.benchmark=False
    report=ROOT/'reports'/args.name
    private=ROOT/'data/operational'/args.name
    report.mkdir(parents=True,exist_ok=True);private.mkdir(parents=True,exist_ok=True)
    ds=DatasetV2(ROOT/'data/processed/dataset_v2_danang')
    selected=choose_cells(ds,args.cells)
    if not np.isfinite(ds.cells.iloc[selected].ne_upslope_m).all():raise ValueError('Chọn ô có địa hình đủ trước khi train')
    excluded=tuple(ds.cells.loc[~ds.cells.index.isin(selected),'site'])
    cfgs={n:product_a(g,latency_h=4,provinces=('Đà Nẵng',),exclude_sites=excluded,issue_stride_h=6)
          for n,g in [('BASE',('A0','A1')),('RAW',('A0','A1','D_RAW')),('DOMAIN',('A0','A1','D_RAW'))]}
    meta=dict(args=vars(args),created_utc=datetime.now(timezone.utc).isoformat(),device=str(device),
              gpu=torch.cuda.get_device_name() if device.type=='cuda' else None,torch=torch.__version__,
              lightgbm=lgb.__version__,git_commit=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip(),
              cells=ds.cells.iloc[selected][['site','elev_mean_m','coast_dist_km']].to_dict('records'),
              test_2025_scored=False,folds=[],history=[],
              design='T-ERA5 past-only + GSMaP raw latency4; historical validation. RAW/DOMAIN equal parameters, all share sampled training windows. Tree uses flattened same tensors, different loss from NN.')
    if args.resume and (report/'run.json').exists():
        previous=json.loads((report/'run.json').read_text(encoding='utf-8'))
        comparable=lambda a:{k:v for k,v in a.items() if k!='resume'}
        if comparable(previous['args'])!=comparable(vars(args)):raise ValueError('Resume phải dùng nguyên cấu hình cũ')
        meta['history']=previous.get('history',[])
    rows,comparisons,fold_frames,regime_rows=[],[],[],[]
    for year in args.years:
        train_years=list(range(2015,year-1)); cal_year=year-1
        fold_dir=private/str(year);fold_dir.mkdir(exist_ok=True)
        all_train=sample_index(ds,cfgs['RAW'],train_years)
        train=epoch_subset(all_train,args.train_samples,2026+year)
        cal=sample_index(ds,cfgs['RAW'],[cal_year])
        ev=sample_index(ds,cfgs['RAW'],[year])
        if args.smoke:
            cal=epoch_subset(cal,800,year);ev=epoch_subset(ev,800,year+1)
        for n,ix in [('train',train),('cal',cal),('eval',ev)]:np.save(fold_dir/f'index_{n}.npy',ix)
        y_cal,y_eval=labels(ds,cal),labels(ds,ev)
        reference=climatology(ds,all_train,ev)[1]
        warm_cal=np.isin((ds.hours[cal[:,1]]+pd.Timedelta(hours=7)).month,range(5,11))
        if not warm_cal.any():raise ValueError('Không có calibration tháng 5–10')
        meta['folds'].append(dict(eval=year,train_years=train_years,cal=cal_year,all_train=len(all_train),
                                  train_unique=len(train),cal_n=len(cal),eval_n=len(ev),
                                  train_index_sha256=hashlib.sha256(train.tobytes()).hexdigest()))
        LOG.info('Fold %s train/cal/eval %s/%s/%s',year,len(train),len(cal),len(ev))
        predictions={}
        for config,cfg in cfgs.items():
            norm=Normalizer.fit(ds,cfg,train_years)
            norm.save(fold_dir/f'{config}_normalizer.json')
            base=WindowSampler(ds,cfg,norm)
            derived=None
            if config=='DOMAIN':
                derived=DomainSampler.fit_derived(base,train,train_years,n=min(len(train),5000))
                derived.save(fold_dir/'derived_normalizer.json')
            sampler=DomainSampler(base,'domain' if config=='DOMAIN' else 'padding',derived)
            LOG.info('Pack %s; past/future %s/%s',config,len(sampler.x_past_names),len(sampler.future_names))
            tr,ca,ee=[pack(sampler,ix) for ix in [train,cal,ev]]
            assert np.array_equal(tr['y'],labels(ds,train))
            nn_ac,nn_ae,nn_pc,nn_pe=[],[],[],[]
            for seed in args.seeds:
                name=f'BiLSTM_{config}_seed{seed}'
                saved=fold_dir/f'{name}.npz'
                if args.resume and saved.exists():
                    with np.load(saved) as data:
                        assert np.array_equal(data['y_eval'],y_eval)
                        ac,ae,pc,pe=[data[k].copy() for k in ('amount_cal','amount_eval','prob_cal','prob_eval')]
                else:
                    start=time.perf_counter()
                    LOG.info('Train %s fold%s',name,year)
                    model,state,history=nn_train(tr,ca,seed,args,device)
                    ac,lc=predict_pack(model,ca,args.batch_size,device)
                    ae,le=predict_pack(model,ee,args.batch_size,device)
                    pe,params=calibrate(lc,y_cal,le)
                    pc,_=calibrate(lc,y_cal,lc)
                    torch.save(dict(model=state,config=cfg.__dict__,derived=derived.__dict__ if derived else None,
                                    seed=seed,past_names=sampler.x_past_names),fold_dir/f'{name}.pt')
                    np.savez_compressed(saved,y_eval=y_eval,amount_cal=ac,amount_eval=ae,prob_cal=pc,prob_eval=pe)
                    meta['history'].append(dict(year=year,run=name,epochs=history,calibration=params,
                                                params=sum(p.numel() for p in model.parameters()),seconds=time.perf_counter()-start))
                    (report/'run.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
                    del model
                    if device.type=='cuda':torch.cuda.empty_cache()
                predictions[name]=(ac,ae,pc,pe)
                nn_ac.append(ac);nn_ae.append(ae);nn_pc.append(pc);nn_pe.append(pe)
            predictions[f'BiLSTM_{config}']=tuple(np.mean(z,axis=0) for z in [nn_ac,nn_ae,nn_pc,nn_pe])
            name=f'LightGBM_{config}'
            saved=fold_dir/f'{name}.npz'
            if args.resume and saved.exists():
                with np.load(saved) as data:
                    assert np.array_equal(data['y_eval'],y_eval)
                    ac,ae,pc,pe=[data[k].copy() for k in ('amount_cal','amount_eval','prob_cal','prob_eval')]
            else:
                start=time.perf_counter();LOG.info('Train %s fold%s',name,year)
                ac,ae,lc,le=tree_train(tr,ca,ee,args,fold_dir,name)
                pe,params=calibrate(lc,y_cal,le);pc,_=calibrate(lc,y_cal,lc)
                np.savez_compressed(saved,y_eval=y_eval,amount_cal=ac,amount_eval=ae,prob_cal=pc,prob_eval=pe)
                meta['history'].append(dict(year=year,run=name,seconds=time.perf_counter()-start,calibration=params))
            predictions[name]=(ac,ae,pc,pe)
            del tr,ca,ee;gc.collect()
        frame=pd.DataFrame(dict(date=ds.hours[ev[:,1]]+pd.Timedelta(hours=7),obs=totals(y_eval)[:,0]))
        regimes=[]
        for c,t in ev:
            u=float(ds.cube[c,t-6:t,ds.feature_index['u850']].mean())
            v=float(ds.cube[c,t-6:t,ds.feature_index['v850']].mean())
            regimes.append('NE' if u<-.5 and v<-.5 else 'W' if u>.5 else 'other')
        frame['regime']=regimes
        for source,(ac,ae,pc,pe) in predictions.items():
            taus=np.empty((3,3))
            for j in range(3):
                months=(ds.hours[cal[:,1]]+pd.Timedelta(hours=7)).month
                cal_mask=np.isin(months,[11,12,1,2]) if j==2 else warm_cal
                for k,thr in enumerate(THRESHOLDS):
                    taus[j,k]=tune_threshold(totals(y_cal)[cal_mask,j]>=thr,pc[cal_mask,j,k])
            more,seasons=score(ds,ev,y_eval,ae,pe,reference,taus,source,year);rows+=more
            frame[source]=(pe[:,0,1]>=taus[0,1]).astype(float)
            frame[f'p1_{source}']=pe[:,0,0];frame[f'p10_{source}']=pe[:,0,1]
            for regime in ['NE','W','other']:
                m=(seasons=='may_oct')&(frame.regime.to_numpy()==regime)
                if m.any():
                    regime_rows.append(dict(year=year,source=source,regime=regime,n=int(m.sum()),
                        **contingency_scores((frame.obs.to_numpy()[m]>=10).astype(float),frame[source].to_numpy()[m],1)))
        warm=frame[np.isin(frame.date.dt.month,range(5,11))].copy()
        fold_frames.append(warm)
        for learner in ['BiLSTM','LightGBM']:
            for config_a,config_b in [('DOMAIN','RAW'),('RAW','BASE')]:
                a,b=f'{learner}_{config_a}',f'{learner}_{config_b}'
                for oc,ca,cb,metric in [('obs',a,b,metric_csi(1)),
                                       ('obs','p1_'+a,'p1_'+b,bs1),('obs','p10_'+a,'p10_'+b,bs10)]:
                    data=warm.copy()
                    if ca==a:data['event']=(data.obs>=10).astype(float);oc='event'
                    result=paired_block_bootstrap(data,oc,ca,cb,metric,n_boot=args.bootstrap,seed=year)
                    if result['metric'].startswith('CSI'):result['metric']='CSI_probability>=10mm/3h'
                    comparisons.append(dict(year=year,learner=learner,**result))
        pd.DataFrame(rows).to_csv(report/'scores.csv',index=False)
        pd.DataFrame(regime_rows).to_csv(report/'regimes.csv',index=False)
        (report/'paired_bootstrap.json').write_text(json.dumps(comparisons,ensure_ascii=False,indent=2),encoding='utf-8')
        (report/'run.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
        LOG.info('Fold %s COMPLETE',year)
    LOG.info('All complete. %s',report)

if __name__=='__main__':main()
