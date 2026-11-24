"""Retrospective, paired evaluation; does not call seen years an untouched test."""
import warnings
import numpy as np
import pandas as pd
from src.gfs_daily_evaluation import block_draw_counts
from src.gfs_final_metrics import holm

def paired_comparisons(frame,p):
    rows=[]
    pairs=p['primary_comparisons']+[ ['LGB_T3','MOS'],['GRU_T3','MOS'],['GRU_T3','GRU_T0'] ]
    for (scope,h),f in frame.groupby(['evaluation_set','horizon'],sort=False):
        days=pd.date_range(f.issue_utc.min(),f.issue_utc.max(),freq='D');stations=sorted(f.station_id.unique())
        counts=block_draw_counts(len(days),draws=p['uncertainty']['draws'],block=p['uncertainty']['block_days'],seed=p['uncertainty']['seed'])
        def matrix(v):
            x=f[['issue_utc','station_id']].copy();x['v']=v
            return x.pivot(index='issue_utc',columns='station_id',values='v').reindex(index=days,columns=stations).to_numpy()
        support=np.isfinite(matrix(np.ones(len(f))));denominator=counts@support.astype(float);cache={}
        for model in sorted({m for pair in pairs for m in pair}):
            for functional,metric in [('mean','mean_rmse'),('median','median_mae')]:
                error=f[model+'_'+functional].to_numpy()-f.y_mm.to_numpy()
                values=matrix(error**2 if functional=='mean' else abs(error))
                per=np.nansum(values,0)/support.sum(0)
                with np.errstate(invalid='ignore',divide='ignore'):boot=(counts@np.nan_to_num(values))/denominator
                if functional=='mean':per=np.sqrt(per);boot=np.sqrt(boot)
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore',RuntimeWarning)
                    cache[model,metric]=(float(per.mean()),np.nanmean(boot,1))
        for model,reference in pairs:
            for metric in ('mean_rmse','median_mae'):
                value,a=cache[model,metric];ref,b=cache[reference,metric];delta=value-ref;distribution=a-b
                distribution=distribution[np.isfinite(distribution)]
                primary=[model,reference] in p['primary_comparisons'] and metric=='mean_rmse'
                family=12 if primary else 1;lo,hi=np.quantile(distribution,[.025,.975])
                low,high=np.quantile(distribution,[.025/family,1-.025/family])
                approximate_p=(1+np.sum(distribution-delta<=delta))/(len(distribution)+1)
                rows.append(dict(evaluation_set=scope,horizon=int(h),model=model,reference=reference,metric=metric,
                    difference=delta,ci95_low=float(lo),ci95_high=float(hi),simultaneous_ci_low=float(low),
                    simultaneous_ci_high=float(high),approximate_p=float(approximate_p),primary=primary,
                    family_size=family,draws=len(distribution),block_days=14,
                    full_station_support_fraction=float((denominator>0).all(1).mean()),
                    interpretation='exploratory; evaluation years already seen; not untouched-test confirmation'))
    result=pd.DataFrame(rows);result['holm_p']=np.nan
    for scope,indices in result[result.primary].groupby('evaluation_set').groups.items():result.loc[indices,'holm_p']=holm(result.loc[indices,'approximate_p'])
    result['adjusted_exploratory_signal']=result.primary & result.difference.lt(0) & result.simultaneous_ci_high.lt(0) & result.holm_p.lt(.05)
    return result

def amount_error_diagnostics(frame,models):
    rows=[]
    for (scope,h),f in frame.groupby(['evaluation_set','horizon']):
        y=f.y_mm.to_numpy();n=len(y)
        for model in models:
            for functional in ('mean','median'):
                pred=f[model+'_'+functional].to_numpy();error=pred-y;squared=error**2
                for name,mask in [('under1',y<1),('1_to_10',(y>=1)&(y<10)),('10_to_50',(y>=10)&(y<50)),('ge50',y>=50),('ge200',y>=200)]:
                    rows.append(dict(evaluation_set=scope,horizon=int(h),model=model,functional=functional,observed_bin=name,
                        n=int(mask.sum()),fraction_samples=float(mask.mean()),
                        fraction_squared_error=float(squared[mask].sum()/max(squared.sum(),1e-20)),
                        average_prediction_mm=float(pred[mask].mean()) if mask.any() else np.nan,
                        average_observation_mm=float(y[mask].mean()) if mask.any() else np.nan,
                        bias_mm=float(error[mask].mean()) if mask.any() else np.nan))
    return pd.DataFrame(rows)
