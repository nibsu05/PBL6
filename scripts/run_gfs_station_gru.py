"""Small fixed GRU A2 comparison, gated only by calibration-period skill."""
from pathlib import Path
import copy
import json
import os
import sys
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG",":4096:8")

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import TensorDataset,DataLoader

from src.gfs_station_dataset import FEATURES,HISTORY,macro_metrics
from scripts.run_gfs_station_pilot import calibrate,report_predictions

BASE=ROOT/'data/operational/gfs_station_pilot_2026_11_10'
PUBLIC=ROOT/'reports/gfs_station_pilot_2026_11_10'


class RainGRU(nn.Module):
    def __init__(self,known_channels):
        super().__init__()
        self.encoder=nn.GRU(1,24,batch_first=True)
        self.station=nn.Embedding(86,4)
        self.heads=nn.ModuleList([nn.Sequential(nn.Linear(24+4+known_channels,32),nn.ReLU(),
                                     nn.Dropout(.1),nn.Linear(32,3)) for _ in range(3)])

    def forward(self,history,known,station):
        _,h=self.encoder(history)
        shared=torch.cat([h[-1],self.station(station)],dim=1)
        out=torch.stack([head(torch.cat([shared,known[:,i]],dim=1)) for i,head in enumerate(self.heads)],dim=1)
        return nn.functional.softplus(out[:,:,0])+1e-5,out[:,:,1:]


def loss_fn(mu,logits,y,events):
    # Tweedie p=1.5, omitting target-only constants, plus event cross entropy.
    amount=(2*y/torch.sqrt(mu)+2*torch.sqrt(mu)).mean()
    binary=nn.functional.binary_cross_entropy_with_logits(logits,events)
    return amount+.5*binary


def main():
    summary=json.loads((PUBLIC/'run_summary.json').read_text())
    if not any(g['passed'] for g in summary['small_gru_gate_based_only_on_cal']):
        result=dict(status='skipped',reason='predefined A2 calibration skill gate not passed',
                    development_scores_used_for_gate=False)
        (PUBLIC/'gru_summary.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result));return
    frame=pd.read_parquet(BASE/'predictions_private.parquet').sort_values(['issue_utc','station_id','horizon']).reset_index(drop=True)
    if not np.array_equal(frame.horizon.to_numpy().reshape(-1,3),np.tile([1,2,3],(len(frame)//3,1))):
        raise ValueError('Horizon grouping mismatch')
    n=len(frame)//3
    known_names=[c for c in FEATURES['A2'] if c not in HISTORY+['station_code']]
    raw_history=np.log1p(frame[HISTORY].to_numpy('float32').reshape(n,3,7)[:,0,::-1,None].copy())
    raw_known=frame[known_names].to_numpy('float32').reshape(n,3,-1)
    y=frame.y_mm.to_numpy('float32').reshape(n,3)
    sid=frame.station_code.to_numpy('int64').reshape(n,3)[:,0]
    fold=frame.split.to_numpy().reshape(n,3)[:,0]
    train=fold=='train';cal=fold=='cal'
    hmean=float(raw_history[train].mean());hstd=max(float(raw_history[train].std()),1e-5)
    kmean=raw_known[train].mean((0,1));kstd=np.maximum(raw_known[train].std((0,1)),1e-5)
    scale=max(float(y[train].mean()),1.)
    history=(raw_history-hmean)/hstd;known=(raw_known-kmean)/kstd
    events=np.stack([y>=1,y>=50],-1).astype('float32')
    tensors=[torch.from_numpy(v.copy()) for v in [history,known,sid,y/scale,events]]
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.use_deterministic_algorithms(True,warn_only=True)
    all_mu=[];all_prob=[];details=[];seed_rows=[]
    for seed in summary['seeds']:
        np.random.seed(seed);torch.manual_seed(seed)
        if device.type=='cuda':torch.cuda.manual_seed_all(seed)
        model=RainGRU(len(known_names)).to(device)
        optimizer=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.001)
        generator=torch.Generator().manual_seed(seed)
        train_data=TensorDataset(*[t[train] for t in tensors])
        loader=DataLoader(train_data,batch_size=128,shuffle=True,generator=generator,num_workers=0)
        validation=[t[cal].to(device) for t in tensors]
        best=np.inf;best_state=None;stale=0;best_epoch=0
        for epoch in range(1,81):
            model.train()
            for batch in loader:
                h,k,s,target,event=[t.to(device) for t in batch]
                optimizer.zero_grad(set_to_none=True)
                mu,logits=model(h,k,s)
                loss=loss_fn(mu,logits,target,event)
                if not torch.isfinite(loss):raise ValueError('Nonfinite GRU loss')
                loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step()
            model.eval()
            with torch.no_grad():
                mu,logits=model(*validation[:3]);value=float(loss_fn(mu,logits,*validation[3:]).cpu())
            if value<best-1e-5:
                best=value;best_state=copy.deepcopy(model.state_dict());best_epoch=epoch;stale=0
            else:stale+=1
            if stale>=12:break
        model.load_state_dict(best_state);model.eval()
        amounts=[];probs=[]
        with torch.no_grad():
            for start in range(0,n,256):
                mu,logits=model(*[t[start:start+256].to(device) for t in tensors[:3]])
                amounts.append(mu.cpu().numpy()*scale);probs.append(torch.sigmoid(logits).cpu().numpy())
        amount=np.concatenate(amounts);raw_prob=np.concatenate(probs);prob=raw_prob.copy();platt={}
        for horizon in range(3):
            for ti,t in enumerate([1.,50.]):
                p,calibrator=calibrate(raw_prob[cal,horizon,ti],events[cal,horizon,ti],raw_prob[:,horizon,ti])
                prob[:,horizon,ti]=p
                platt[(horizon,ti)]=calibrator
        all_mu.append(amount);all_prob.append(prob)
        torch.save(dict(model=best_state,known_features=known_names,scale=scale,
            history_mean=hmean,history_std=hstd,known_mean=kmean,known_std=kstd,seed=seed),
            BASE/'models'/f'GRU_A2_seed{seed}.pt')
        import joblib
        joblib.dump(platt,BASE/'models'/f'GRU_A2_seed{seed}_platt.joblib')
        for part in ['cal','dev']:
            for horizon in [1,2,3]:
                ok=(frame.split==part)&(frame.horizon==horizon)
                score,_=macro_metrics(pd.DataFrame(dict(station_id=frame.loc[ok,'station_id'],y=frame.loc[ok,'y_mm'],pred=amount.ravel()[ok])))
                seed_rows.append(dict(config='GRU_A2',horizon=horizon,seed=seed,fold=part,**score))
        details.append(dict(seed=seed,epochs=epoch,best_epoch=best_epoch,cal_loss=best))
        print(json.dumps(details[-1]),flush=True)
    frame['GRU_A2']=np.mean(all_mu,axis=0).ravel()
    probability=np.mean(all_prob,axis=0)
    for i,t in enumerate([1.,50.]):frame[f'GRU_A2_p{t:g}']=probability[:,:,i].ravel()
    report_predictions(frame,summary['models']+['GRU_A2'])
    frame.to_parquet(BASE/'predictions_private.parquet',index=False)
    existing=pd.read_csv(PUBLIC/'seed_point_metrics.csv')
    pd.concat([existing[existing.config.ne('GRU_A2')],pd.DataFrame(seed_rows)],ignore_index=True).to_csv(PUBLIC/'seed_point_metrics.csv',index=False)
    result=dict(status='complete',model='GRU_A2',history_days=7,history_channels=1,
        known_forecast_channels=len(known_names),hidden_units=24,station_embedding=4,
        parameter_count=sum(p.numel() for p in model.parameters()),seeds=details,device=str(device),
        gate_based_only_on_cal=True,development_used_for_early_stopping=False,
        test2025_read=False,normalizers_fit_only_on_train=True)
    (PUBLIC/'gru_summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
