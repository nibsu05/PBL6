"""Independent arithmetic, checkpoint replay, temporal guards and preservation."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import warnings
import joblib
import numpy as np
import pandas as pd
from src.gfs_window import BASE,PUBLIC,SEEDS,CASES,now,sha,read_json,write_json,load_frame,fit_mask
from scripts.run_gfs_window import check_freeze,predict_frame


def compare(a,b):
    np.testing.assert_allclose(a,b,rtol=2e-7,atol=1e-7,equal_nan=True)


def verify():
    check_freeze()
    f=pd.read_parquet(BASE/'predictions_private.parquet')
    source=load_frame();source=source[source.role.eq('retrospective2026')].reset_index(drop=True)
    keys=['station_id','gauge_namespace','issue_utc','horizon']
    pd.testing.assert_frame_equal(f[keys+['y_mm']],source[keys+['y_mm']])
    metric_checks=0
    points=pd.read_csv(PUBLIC/'point_metrics.csv')
    for r in points.itertuples():
        s=f[f.evaluation_set.eq(r.evaluation_set)&f.horizon.eq(r.horizon)]
        col=r.model+'_'+r.functional
        per=[]
        for _,g in s.groupby('station_id'):
            error=g[col].to_numpy(dtype=float)-g.y_mm.to_numpy(dtype=float)
            per.append([abs(error).mean(),np.sqrt(np.mean(error**2)),error.mean()])
        error=s[col].to_numpy(dtype=float)-s.y_mm.to_numpy(dtype=float)
        expected=np.r_[np.mean(per,axis=0),[abs(error).mean(),np.sqrt(np.mean(error**2)),error.mean()]]
        actual=[r.macro_mae,r.macro_rmse,r.macro_bias,r.micro_mae,r.micro_rmse,r.micro_bias]
        compare(actual,expected);metric_checks+=6
    events=pd.read_csv(PUBLIC/'event_metrics.csv')
    probabilities=pd.read_csv(PUBLIC/'probability_metrics.csv')
    for r in probabilities.itertuples():
        s=f[f.evaluation_set.eq(r.evaluation_set)&f.horizon.eq(r.horizon)]
        scores=[]
        for _,g in s.groupby('station_id'):
            y=(g.y_mm.to_numpy()>=r.threshold_mm).astype(float)
            bs=float(np.mean((g[f'{r.model}_p{r.threshold_mm}'].to_numpy(dtype=float)-y)**2))
            ref=float(np.mean((g[f'CLIM_p{r.threshold_mm}'].to_numpy(dtype=float)-y)**2))
            scores.append([bs,1-bs/ref if ref else np.nan])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',RuntimeWarning);expected=np.nanmean(scores,axis=0)
        compare([r.macro_bs,r.macro_bss],expected);metric_checks+=2
    for r in events.itertuples():
        s=f[f.evaluation_set.eq(r.evaluation_set)&f.horizon.eq(r.horizon)]
        per=[];sums=np.zeros(3,dtype=int)
        for _,g in s.groupby('station_id'):
            truth=g.y_mm.to_numpy()>=r.threshold_mm;yes=g[f'{r.model}_p{r.threshold_mm}'].to_numpy()>=r.cutoff
            h=int((truth&yes).sum());m=int((truth&~yes).sum());fa=int((~truth&yes).sum());sums+=[h,m,fa]
            per.append([h/(h+m+fa) if h+m+fa else np.nan,h/(h+m) if h+m else np.nan,fa/(h+fa) if h+fa else np.nan])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',RuntimeWarning);expected=np.nanmean(per,axis=0)
        compare([r.macro_csi,r.macro_pod,r.macro_far],expected)
        np.testing.assert_array_equal([r.hits,r.misses,r.false_alarms],sums);metric_checks+=6
    # Same-window loss experiments intentionally share all auxiliary predictions.
    for a,b in [('A','C'),('B','D')]:
        for head in ('median','p1','p50'):np.testing.assert_array_equal(f[a+'_'+head],f[b+'_'+head])
    for model in list(CASES)+['N0','N1','N3','MOS_SHORT','MOS_LONG']:
        if not ((f[model+'_p50']<=f[model+'_p1'])&(f[model+'_p50']>=0)&(f[model+'_p1']<=1)).all():raise ValueError('Non-nested probabilities')
        if (f[model+'_mean']<0).any():raise ValueError('Negative rainfall')
    sample=f.groupby(['evaluation_set','horizon'],group_keys=False).head(8).reset_index(drop=True)
    replay,_=predict_frame(sample)
    changed=sample.copy();changed['y_mm']=1234567.
    replay_changed,_=predict_frame(changed)
    prediction_columns=[c for c in sample if c.endswith(('_mean','_median','_p1','_p50'))]
    compare(sample[prediction_columns],replay[prediction_columns])
    np.testing.assert_array_equal(replay[prediction_columns],replay_changed[prediction_columns])
    selection=read_json(PUBLIC/'selection.json');model_checks=0
    train=load_frame(training_only=True)
    for path in (BASE/'models').glob('MEAN_*.joblib'):
        a=joblib.load(path);h=int(path.name.split('_d')[1].split('_')[0]);sub=train[train.horizon.eq(h)]
        if a['training_rows']!=int(fit_mask(sub,a['window']).sum()):raise ValueError('Training row mismatch')
        if a['tree_budget']!=selection['trees'][str(h)]:raise ValueError('Unequal tree budgets')
        model_checks+=1
    # Direct calendar resampling of squared-error arrays, independently of count matrices.
    comparisons=pd.read_csv(PUBLIC/'paired_comparisons.csv');bootstrap_checks=0
    for scope,g in f[f.horizon.eq(1)].groupby('evaluation_set'):
        dates=pd.date_range(g.issue_utc.min(),g.issue_utc.max(),freq='D');stations=sorted(g.station_id.unique())
        arrays=[]
        for model in ('B','A'):
            z=g[keys].copy();z['square']=(g[model+'_mean'].to_numpy()-g.y_mm.to_numpy())**2
            arrays.append(z.pivot(index='issue_utc',columns='station_id',values='square').reindex(index=dates,columns=stations).to_numpy())
        rng=np.random.default_rng(1701);distribution=[]
        for _ in range(5000):
            starts=rng.integers(0,len(dates),size=int(np.ceil(len(dates)/14)))
            indices=((starts[:,None]+np.arange(14)[None,:])%len(dates)).ravel()[:len(dates)]
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',RuntimeWarning)
                distribution.append(np.nanmean(np.sqrt(np.nanmean(arrays[0][indices],axis=0)))-np.nanmean(np.sqrt(np.nanmean(arrays[1][indices],axis=0))))
        row=comparisons[comparisons.evaluation_set.eq(scope)&comparisons.horizon.eq(1)&comparisons['first'].eq('B')&comparisons.reference.eq('A')].iloc[0]
        compare([row.ci_low,row.ci_high,row.simultaneous_ci_low,row.simultaneous_ci_high],
            np.quantile(distribution,[.025,.975,.025/12,1-.025/12]));bootstrap_checks+=4
    protected=read_json(BASE/'protected_before.json')
    for rel,digest in protected.items():
        if sha(ROOT/rel)!=digest:raise ValueError('Protected old artifact changed: '+rel)
    if (ROOT/'reports/short_range_three_models_2026_10_21/PBL6_SO_SANH_3_MO_HINH.pptx').exists():raise ValueError('User-deleted original slide was restored')
    report=dict(status='passed',verified_utc=now(),evaluation_rows=len(f),independent_metric_values=metric_checks,
        replay_rows=len(sample),replayed_prediction_values=len(sample)*len(prediction_columns),
        future_label_perturbation_invariant=True,matched_source_rows_and_labels=True,
        matched_same_window_auxiliary_predictions=True,mean_checkpoint_training_budgets_checked=model_checks,
        direct_calendar_bootstrap_quantiles_checked=bootstrap_checks,protected_artifacts_preserved=len(protected),
        training_max_year=2024,calibration_year=2025,retrospective_not_untouched=True)
    write_json(PUBLIC/'verification.json',report)
    print(report,flush=True)


if __name__=='__main__':verify()
