"""Paired retrospective comparisons; calendar blocks retain storm dependence."""
import numpy as np
import pandas as pd

from src.gfs_window import CONTRASTS, macro_rmse
from src.gfs_daily_evaluation import block_draw_counts
from src.gfs_final_metrics import holm


def bootstrap_table(frame, draws=5000, block=14, seed=1701):
    rows=[]
    pairs=[(a,b,'factorial',12) for a,b in CONTRASTS]
    pairs += [('N1','N0','ablation',6),('N3','N1','ablation',6)]
    for (scope,h),f in frame.groupby(['evaluation_set','horizon'],sort=False):
        dates=pd.date_range(f.issue_utc.min(),f.issue_utc.max(),freq='D')
        stations=sorted(f.station_id.unique())
        counts=block_draw_counts(len(dates),draws=draws,block=block,seed=seed)
        def matrix(values):
            q=f[['issue_utc','station_id']].copy();q['value']=values
            return q.pivot(index='issue_utc',columns='station_id',values='value').reindex(index=dates,columns=stations).to_numpy()
        support=np.isfinite(matrix(np.ones(len(f)))).astype(float)
        denominator=counts@support
        cache={}
        for model in sorted({x for a,b,_,_ in pairs for x in (a,b)}):
            error=f[model+'_mean'].to_numpy(dtype=float)-f.y_mm.to_numpy(dtype=float)
            square=matrix(error**2)
            with np.errstate(invalid='ignore',divide='ignore'):
                boot_mse=(counts@np.nan_to_num(square))/denominator
                distribution=np.nanmean(np.sqrt(boot_mse),axis=1)
            cache[model]=(macro_rmse(f.y_mm,f[model+'_mean'],f.station_id),distribution)
        for a,b,family,size in pairs:
            value=cache[a][0]-cache[b][0]
            distribution=cache[a][1]-cache[b][1]
            distribution=distribution[np.isfinite(distribution)]
            centered=distribution-value
            p=float((1+(centered<=value).sum())/(len(distribution)+1))
            lo,hi=np.quantile(distribution,[.025,.975])
            adjlo,adjhi=np.quantile(distribution,[.025/size,1-.025/size])
            rows.append(dict(evaluation_set=scope,horizon=int(h),first=a,reference=b,family=family,
                family_size=size,metric='mean_macro_rmse',difference=value,ci_low=float(lo),ci_high=float(hi),
                simultaneous_ci_low=float(adjlo),simultaneous_ci_high=float(adjhi),approx_p=p,
                draws=len(distribution),calendar_days=len(dates),block_days=block,
                fraction_draws_all_stations_supported=float((denominator>0).all(1).mean()),
                inference_status='exploratory_retrospective_not_confirmatory'))
    table=pd.DataFrame(rows)
    for _,ix in table.groupby(['evaluation_set','family']).groups.items():
        table.loc[ix,'holm_p']=holm(table.loc[ix,'approx_p'])
    table['supported_exploratory_improvement']=(table.simultaneous_ci_high<0)&(table.holm_p<.05)
    return table


def dry_heavy_table(frame,models):
    rows=[]
    for (scope,h),f in frame.groupby(['evaluation_set','horizon']):
        y=f.y_mm.to_numpy(dtype=float)
        for model in models:
            p=f[model+'_mean'].to_numpy(dtype=float);err=p-y;total=float((err**2).sum())
            for name,mask in [('under1',y<1),('1_to_50',(y>=1)&(y<50)),('ge50',y>=50),('ge200',y>=200)]:
                n=int(mask.sum())
                rows.append(dict(evaluation_set=scope,horizon=int(h),model=model,observed_bin=name,
                    rows=n,issue_dates=int(f.loc[mask,'issue_utc'].nunique()),stations=int(f.loc[mask,'station_id'].nunique()),
                    mean_y=float(y[mask].mean()) if n else np.nan,mean_prediction=float(p[mask].mean()) if n else np.nan,
                    micro_bias=float(err[mask].mean()) if n else np.nan,micro_mae=float(abs(err[mask]).mean()) if n else np.nan,
                    micro_rmse=float(np.sqrt((err[mask]**2).mean())) if n else np.nan,
                    fraction_total_squared_error=float((err[mask]**2).sum()/total) if total else np.nan))
    return pd.DataFrame(rows)
