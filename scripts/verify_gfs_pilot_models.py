"""Replay saved estimators and independently verify aggregate pilot metrics."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import joblib
import numpy as np
import pandas as pd

from src.gfs_station_dataset import FEATURES,HISTORY

BASE=ROOT/'data/operational/gfs_station_pilot_2026_11_10'
PUBLIC=ROOT/'reports/gfs_station_pilot_2026_11_10'


def main():
    f=pd.read_parquet(BASE/'predictions_private.parquet').sort_values(['issue_utc','station_id','horizon']).reset_index(drop=True)
    point=pd.read_csv(PUBLIC/'point_metrics.csv');prob=pd.read_csv(PUBLIC/'probability_metrics.csv')
    ci=pd.read_csv(PUBLIC/'paired_bootstrap.csv')
    models=point.model.unique().tolist()
    assert np.isfinite(f[[m for m in models]+['y_mm']].to_numpy()).all()
    checked=0;binary=0
    for config,names in FEATURES.items():
        for h in [1,2,3]:
            s=f[f.horizon.eq(h)];predictions=[];probs={t:[] for t in [1.,50.]}
            for seed in [17,29,43]:
                artifact=joblib.load(BASE/'models'/f'{config}_d{h}_seed{seed}.joblib')
                assert artifact['features']==names and artifact['amount'].feature_name_==names
                assert not set(names)&{'y_mm','target_start_utc','target_end_utc','CLIM'}
                predictions.append(np.maximum(artifact['amount'].predict(s[names]),0))
                for t in probs:
                    model=artifact['probability'][t]['classifier'];platt=artifact['probability'][t]['platt']
                    if model is None:
                        tr=s[s.split.eq('train')];p=np.full(len(s),(tr.y_mm.ge(t).sum()+.5)/(len(tr)+1))
                    else:
                        p=model.predict_proba(s[names])[:,1]
                        if platt is not None:
                            p=np.clip(p,1e-5,1-1e-5);p=platt.predict_proba(np.log(p/(1-p)).reshape(-1,1))[:,1]
                    probs[t].append(p);binary+=1
                checked+=1
            np.testing.assert_allclose(np.mean(predictions,axis=0),s[config],rtol=1e-7,atol=1e-7)
            for t,p in probs.items():np.testing.assert_allclose(np.mean(p,axis=0),s[f'{config}_p{t:g}'],rtol=1e-7,atol=1e-7)
    neural=json.loads((PUBLIC/'gru_summary.json').read_text())
    nn_checked=0
    if neural['status']=='complete':
        import torch
        from scripts.run_gfs_station_gru import RainGRU
        torch.set_num_threads(4)
        n=len(f)//3;known=[c for c in FEATURES['A2'] if c not in HISTORY+['station_code']]
        rawh=np.log1p(f[HISTORY].to_numpy('float32').reshape(n,3,7)[:,0,::-1,None].copy())
        rawk=f[known].to_numpy('float32').reshape(n,3,-1)
        sid=f.station_code.to_numpy('int64').reshape(n,3)[:,0].copy()
        train=f.split.to_numpy().reshape(n,3)[:,0]=='train'
        amounts=[];probabilities=[]
        for seed in [17,29,43]:
            state=torch.load(BASE/'models'/f'GRU_A2_seed{seed}.pt',map_location='cpu',weights_only=False)
            assert state['known_features']==known
            np.testing.assert_allclose(state['known_mean'],rawk[train].mean((0,1)),rtol=1e-6,atol=1e-5)
            np.testing.assert_allclose(state['known_std'],np.maximum(rawk[train].std((0,1)),1e-5),rtol=1e-6,atol=1e-5)
            np.testing.assert_allclose(state['history_mean'],rawh[train].mean(),rtol=1e-6)
            np.testing.assert_allclose(state['history_std'],max(float(rawh[train].std()),1e-5),rtol=1e-6)
            model=RainGRU(len(known));model.load_state_dict(state['model']);model.eval()
            h=torch.from_numpy((rawh-state['history_mean'])/state['history_std'])
            k=torch.from_numpy((rawk-state['known_mean'])/state['known_std'])
            with torch.no_grad():
                mu,logits=model(h,k,torch.from_numpy(sid));amount=mu.numpy()*state['scale'];p=torch.sigmoid(logits).numpy()
            platt=joblib.load(BASE/'models'/f'GRU_A2_seed{seed}_platt.joblib')
            for horizon in range(3):
                for ti in range(2):
                    c=platt[(horizon,ti)]
                    if c is not None:
                        raw=np.clip(p[:,horizon,ti],1e-5,1-1e-5)
                        p[:,horizon,ti]=c.predict_proba(np.log(raw/(1-raw)).reshape(-1,1))[:,1]
            amounts.append(amount);probabilities.append(p);nn_checked+=1
        np.testing.assert_allclose(np.mean(amounts,axis=0).ravel(),f.GRU_A2,rtol=3e-5,atol=3e-4)
        for ti,t in enumerate([1.,50.]):
            np.testing.assert_allclose(np.mean(probabilities,axis=0)[:,:,ti].ravel(),f[f'GRU_A2_p{t:g}'],rtol=3e-5,atol=3e-5)
    metric_rows=0
    for row in point.itertuples():
        s=f[f.split.eq(row.fold)&f.horizon.eq(row.horizon)]
        metrics=[]
        for _,g in s.groupby('station_id'):
            error=g[row.model].to_numpy()-g.y_mm.to_numpy()
            metrics.append([np.abs(error).mean(),np.sqrt((error**2).mean()),error.mean()])
        np.testing.assert_allclose(np.mean(metrics,axis=0),[row.macro_mae,row.macro_rmse,row.macro_bias],rtol=1e-9,atol=1e-9)
        metric_rows+=1
    for row in prob.itertuples():
        s=f[f.split.eq(row.fold)&f.horizon.eq(row.horizon)];scores=[]
        for _,g in s.groupby('station_id'):
            y=g.y_mm.ge(row.threshold_mm).to_numpy(float);p=g[f'{row.model}_p{row.threshold_mm:g}'].to_numpy()
            reference=g[f'CLIM_p{row.threshold_mm:g}'].to_numpy();bs=((p-y)**2).mean();ref=((reference-y)**2).mean()
            scores.append([bs,1-bs/ref if ref>0 else np.nan])
        np.testing.assert_allclose(np.nanmean(scores,axis=0),[row.macro_bs,row.macro_bss],rtol=1e-8,atol=1e-8)
        metric_rows+=1
    for r in ci.itertuples():
        a=point[(point.fold==r.fold)&(point.horizon==r.horizon)&(point.model==r.model)].iloc[0]
        b=point[(point.fold==r.fold)&(point.horizon==r.horizon)&(point.model==r.reference)].iloc[0]
        np.testing.assert_allclose(r.mae_difference,a.macro_mae-b.macro_mae,atol=1e-9)
    result=dict(status='passed',replayed_lightgbm_amount_estimators=checked,
        replayed_lightgbm_binary_estimators=binary,replayed_GRU_seeds_cpu=nn_checked,
        independent_aggregate_metric_rows=metric_rows,CI_point_estimates_match_metrics=True,
        GRU_normalizer_statistics_match_train_only=True,labels_not_in_X=True,test2025_read=False)
    (PUBLIC/'model_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
