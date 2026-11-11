"""Station-macro metrics and paired calendar-block uncertainty, no fitting."""
from __future__ import annotations
import warnings
import numpy as np
import pandas as pd
from src.gfs_station_dataset import macro_metrics,event_metrics


def point_report(frame,models):
    rows=[];private=[];conditional=[];months=[]
    for part in ('train','cal','dev'):
        for horizon in (1,2,3):
            f=frame[frame.split.eq(part)&frame.horizon.eq(horizon)]
            for model in models:
                for functional in ('mean','median'):
                    col=model+'_'+functional
                    score,station=macro_metrics(pd.DataFrame(dict(station_id=f.station_id,y=f.y_mm,pred=f[col])))
                    rows.append(dict(fold=part,horizon=horizon,model=model,functional=functional,**score))
                    station=station.assign(fold=part,horizon=horizon,model=model,functional=functional);private.append(station)
                    if part=='train':continue
                    for label,mask in [('under1',f.y_mm<1),('1_to_10',(f.y_mm>=1)&(f.y_mm<10)),('10_to_50',(f.y_mm>=10)&(f.y_mm<50)),('ge50',f.y_mm>=50)]:
                        s=f.loc[mask];error=s[col].to_numpy()-s.y_mm.to_numpy()
                        conditional.append(dict(fold=part,horizon=horizon,model=model,functional=functional,observed_rain_bin=label,
                            n=len(s),stations=int(s.station_id.nunique()),issue_dates=int(s.issue_utc.nunique()),
                            micro_mae=float(np.abs(error).mean()) if len(s) else np.nan,
                            micro_rmse=float(np.sqrt(np.mean(error**2))) if len(s) else np.nan,
                            micro_bias=float(error.mean()) if len(s) else np.nan))
                    if part=='dev':
                        month=f.target_end_utc.dt.tz_convert('Asia/Ho_Chi_Minh').dt.month
                        for number,s in f.groupby(month):
                            score,_=macro_metrics(pd.DataFrame(dict(station_id=s.station_id,y=s.y_mm,pred=s[col])))
                            months.append(dict(month=int(number),horizon=horizon,model=model,functional=functional,**score))
    return pd.DataFrame(rows),pd.concat(private,ignore_index=True),pd.DataFrame(conditional),pd.DataFrame(months)


def probability_report(frame,models,cutoffs):
    cut={(r['model'],int(r['horizon'])):float(r['cutoff']) for r in cutoffs}
    probability=[];events=[];reliability=[];coherence=[]
    for model in models:
        dev=frame[frame.split.eq('dev')]
        gap=dev[model+'_p50']-dev[model+'_p1']
        coherence.append(dict(model=model,rows=len(dev),violations=int((gap>1e-12).sum()),
            max_positive_gap=float(max(gap.max(),0)),decision_contradictions=int(((dev[model+'_p50']>=.5)&(dev[model+'_p1']<.5)).sum())))
    for part in ('cal','dev'):
        for h in (1,2,3):
            f=frame[frame.split.eq(part)&frame.horizon.eq(h)]
            for model in models:
                kind='degenerate_0_or_1' if model in ('ZERO','GFS','PERSISTENCE') else 'train_monthly_frequency' if model=='CLIM' else 'calibrated_nested'
                for threshold in (1,50):
                    col=f'{model}_p{threshold}';reference=f[f'CLIM_p{threshold}']
                    reports=[]
                    for _,s in f.groupby('station_id'):
                        reports.append(event_metrics(s.y_mm.ge(threshold),s[col],s[f'CLIM_p{threshold}']))
                    station=pd.DataFrame(reports);micro=event_metrics(f.y_mm.ge(threshold),f[col],reference)
                    probability.append(dict(fold=part,horizon=h,model=model,probability_type=kind,threshold_mm=threshold,
                        macro_bs=float(station.bs.mean()),macro_bss=float(station.bss.mean()),stations_with_bss=int(station.bss.notna().sum()),
                        micro_bs=micro['bs'],micro_bss=micro['bss'],events=micro['events'],issue_dates=int(f.loc[f.y_mm.ge(threshold),'issue_utc'].nunique())))
                    rules=[('fixed_0.5',.5)]
                    if (model,h) in cut:rules.append(('calibration_selected',cut[(model,h)]))
                    for rule,tau in rules:
                        reports=[event_metrics(s.y_mm.ge(threshold),s[col],s[f'CLIM_p{threshold}'],cutoff=tau) for _,s in f.groupby('station_id')]
                        station=pd.DataFrame(reports);micro=event_metrics(f.y_mm.ge(threshold),f[col],reference,cutoff=tau)
                        events.append(dict(fold=part,horizon=h,model=model,threshold_mm=threshold,decision_rule=rule,cutoff=tau,
                            macro_csi=float(station.csi.mean()),macro_pod=float(station.pod.mean()),macro_far=float(station.far.mean()),
                            stations_with_pod=int(station.pod.notna().sum()),stations_with_far=int(station.far.notna().sum()),
                            micro_csi=micro['csi'],micro_pod=micro['pod'],micro_far=micro['far'],events=micro['events'],
                            hits=micro['hits'],misses=micro['misses'],false_alarms=micro['false_alarms']))
                    if part=='dev':
                        bins=np.minimum((f[col]*10).astype(int),9)
                        for number,s in f.groupby(bins):
                            reliability.append(dict(horizon=h,model=model,threshold_mm=threshold,bin=int(number),n=len(s),
                                mean_probability=float(s[col].mean()),observed_frequency=float(s.y_mm.ge(threshold).mean())))
    return pd.DataFrame(probability),pd.DataFrame(events),pd.DataFrame(reliability),pd.DataFrame(coherence)


def block_draw_counts(n,draws=1000,block=14,seed=1701):
    rng=np.random.default_rng(seed);out=np.zeros((draws,n),dtype=float)
    for j in range(draws):
        starts=rng.integers(0,n,size=int(np.ceil(n/block)))
        positions=((starts[:,None]+np.arange(block)[None,:])%n).ravel()[:n]
        out[j]=np.bincount(positions,minlength=n)
    return out


def paired_uncertainty(frame,models,feature_pairs,draws=1000):
    rows=[]
    for h in (1,2,3):
        f=frame[frame.split.eq('dev')&frame.horizon.eq(h)].copy()
        dates=pd.date_range(f.issue_utc.min(),f.issue_utc.max(),freq='D');stations=sorted(f.station_id.unique())
        counts=block_draw_counts(len(dates),draws=draws)
        def matrix(values):
            q=f[['issue_utc','station_id']].copy();q['v']=values
            return q.pivot(index='issue_utc',columns='station_id',values='v').reindex(index=dates,columns=stations).to_numpy()
        valid=matrix(np.ones(len(f)));valid=np.isfinite(valid).astype(float)
        den=counts@valid
        def sample_metric(values,root=False):
            x=matrix(values);sums=counts@np.nan_to_num(x)
            with np.errstate(invalid='ignore',divide='ignore'):
                result=sums/den
                if root:result=np.sqrt(result)
            return np.nanmean(result,axis=1)
        def overall(values,root=False):
            x=matrix(values)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',RuntimeWarning);means=np.nanmean(x,axis=0)
            return float(np.nanmean(np.sqrt(means) if root else means))
        cached={}
        for model in models:
            for functional in ('mean','median'):
                error=f[model+'_'+functional].to_numpy()-f.y_mm.to_numpy()
                for metric,values,root in [('mae',abs(error),False),('rmse',error**2,True)]:
                    cached[(model,functional,metric)]=(overall(values,root),sample_metric(values,root))
            for t in (1,50):
                values=(f[f'{model}_p{t}'].to_numpy()-f.y_mm.ge(t).to_numpy())**2
                cached[(model,f'prob_ge{t}','bs')]=(overall(values),sample_metric(values))
        pairs={(model,reference) for model in models for reference in ('ZERO','GFS','CLIM','MOS') if model!=reference}
        pairs.update(('LGB_'+a,'LGB_'+b) for a,b in feature_pairs)
        pairs.update((f'GRU_{c}',f'LGB_{c}') for c in ('N3','N5'))
        pairs.update((f'LGB_N3_delay{d}','LGB_N3') for d in (3,6))
        pairs.add(('GRU_N5','GRU_N3'))
        if 'LGB_N3_exclude_archive_late' in models:pairs.add(('LGB_N3_exclude_archive_late','LGB_N3'))
        pairs={(a,b) for a,b in pairs if a in models and b in models}
        for model,reference in sorted(pairs):
            for functional,metric in [('mean','mae'),('mean','rmse'),('median','mae'),('median','rmse'),('prob_ge1','bs'),('prob_ge50','bs')]:
                point,a=cached[(model,functional,metric)];other,b=cached[(reference,functional,metric)]
                low,high=np.nanquantile(a-b,[.025,.975])
                rows.append(dict(horizon=h,model=model,reference=reference,functional=functional,metric=metric,
                    difference=point-other,ci95_low=float(low),ci95_high=float(high),
                    calendar_days=len(dates),draws=draws,block_days=14,sign='negative favors first model',
                    interpretation='exploratory unadjusted paired development comparison'))
    return pd.DataFrame(rows)
