"""RAW Bi-LSTM mean/Tweedie, p1.5, ngân sách cũ; scale loss chỉ từ train."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,logging,sys,time
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import torch
from src.dataloader_v2 import DatasetV2,sample_index
from src.rainfall_losses import tweedie_deviance,TweedieJointLoss
from src.verification import paired_block_bootstrap,metric_rmse,metric_csi
from scripts.followup_danang import metadata,write_run,load_sampler,cfg_for,taus_for,source_predictions,SOURCE,PRIVATE,REPORT
from scripts.screen_danang_domain import pack,nn_train,predict_pack,score
from scripts.pilot_bilstm_v2 import calibrate,climatology,totals

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--epochs',type=int,default=15);ap.add_argument('--patience',type=int,default=4)
    ap.add_argument('--batch-size',type=int,default=256);ap.add_argument('--bootstrap',type=int,default=1000)
    args=ap.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    ds=DatasetV2(ROOT/'data/processed/dataset_v2_danang')
    source,meta=metadata('bilstm_tweedie',args)
    report=REPORT/'bilstm_tweedie';private=PRIVATE/'bilstm_tweedie'
    rows,comparisons=[],[]
    for year in [2021,2022,2023]:
        target=private/str(year);target.mkdir(parents=True,exist_ok=True)
        train,cal,ev=[np.load(SOURCE/str(year)/f'index_{n}.npy') for n in ['train','cal','eval']]
        sampler=load_sampler(ds,source,year,'RAW')
        tr,ca,ee=[pack(sampler,ix) for ix in [train,cal,ev]]
        assert (tr['y']>=0).all()
        yt=torch.from_numpy(tr['y'])
        scale=float(tweedie_deviance(torch.full_like(yt,yt.mean()),yt))
        loss_fn=TweedieJointLoss(max(scale,1e-6))
        ensemble=[]
        for seed in [42,43,44]:
            start=time.perf_counter();logging.info('RAW_TWEEDIE fold%s seed%s nullscale%.4f',year,seed,scale)
            model,state,history=nn_train(tr,ca,seed,args,device,loss_fn=loss_fn)
            ac,lc=predict_pack(model,ca,args.batch_size,device,amount_mode='mean')
            ae,le=predict_pack(model,ee,args.batch_size,device,amount_mode='mean')
            pc,params=calibrate(lc,ca['y'],lc);pe,_=calibrate(lc,ca['y'],le)
            torch.save(dict(model=state,amount_mode='mean',seed=seed,year=year),target/f'seed{seed}.pt')
            np.savez_compressed(target/f'seed{seed}.npz',amount_cal=ac,amount_eval=ae,prob_cal=pc,prob_eval=pe)
            ensemble.append(dict(amount_cal=ac,amount_eval=ae,prob_cal=pc,prob_eval=pe))
            meta['history'].append(dict(year=year,seed=seed,epochs=history,calibration=params,
                null_deviance_train=scale,amount_mode='mean',params=sum(p.numel() for p in model.parameters()),
                seconds=time.perf_counter()-start))
            write_run(report,meta);del model
            if device.type=='cuda':torch.cuda.empty_cache()
        new={k:np.mean([v[k] for v in ensemble],axis=0) for k in ensemble[0]}
        np.savez_compressed(target/'ensemble.npz',**new)
        old=source_predictions(year,'BiLSTM_RAW')
        reference=climatology(ds,sample_index(ds,cfg_for(ds,source),range(2015,year-1)),ev)[1]
        warm=np.isin((ds.hours[ev[:,1]]+pd.Timedelta(hours=7)).month,range(5,11))
        frame=pd.DataFrame(dict(date=ds.hours[ev[warm,1]]+pd.Timedelta(hours=7),obs=totals(ee['y'])[warm,0]))
        for name,pred in [('BiLSTM_RAW_TWEEDIE',new),('BiLSTM_RAW',old)]:
            tau=taus_for(ds,cal,ca['y'],pred['prob_cal'])
            r,_=score(ds,ev,ee['y'],pred['amount_eval'],pred['prob_eval'],reference,tau,name,year);rows+=r
            frame[name]=totals(pred['amount_eval'])[warm,0]
        for metric in [metric_rmse,metric_csi(10)]:
            comparisons.append(dict(year=year,**paired_block_bootstrap(frame,'obs','BiLSTM_RAW_TWEEDIE','BiLSTM_RAW',metric,n_boot=args.bootstrap,seed=year)))
        pd.DataFrame(rows).to_csv(report/'scores.csv',index=False)
        (report/'paired_bootstrap.json').write_text(json.dumps(comparisons,indent=2),encoding='utf-8')
    meta['completed']=True;meta['calibration_note']='Jointencoder/loss changed; event heads recalibrated on original30cell cal year.'
    write_run(report,meta);logging.info('COMPLETE bilstm_tweedie')
if __name__=='__main__':main()
