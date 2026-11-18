"""Paired calendar-block uncertainty for the daily CPC development matrix."""
from pathlib import Path
import itertools
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from src.short_range_ablation import calendar_block_weights
from scripts.run_daily_gauge_matrix import REPORT,PRIVATE,MODELS,sha,dump,score


def main():
    tick=time.perf_counter()
    run=json.loads((REPORT/'run.json').read_text(encoding='utf8'));assert run['status']=='complete' and len(run['models'])==168
    validation=json.loads((REPORT/'validation.json').read_text(encoding='utf8'));assert validation['status']=='passed'
    frame=pd.read_parquet(PRIVATE/'predictions_ensemble.parquet')
    anchor=frame[(frame.model=='tft')&(frame.experiment=='E0')&(frame.lead_day==1)].sort_values('issue')
    parts={};terms=[]
    for key,p in frame.groupby(['model','experiment','lead_day'],sort=True):
        p=p.sort_values('issue')
        np.testing.assert_array_equal(p.issue,anchor.issue)
        event=p.obs.to_numpy()>=16;decision=p.p16.to_numpy()>=p.tau16.to_numpy()
        parts[key]=len(terms)
        terms.extend([(p.amount.to_numpy()-p.obs.to_numpy())**2,
            (p.p16.to_numpy()-event)**2,(p.ref16.to_numpy()-event)**2,
            (decision&event).astype(float),(decision|event).astype(float)])
    terms=np.stack(terms,axis=1);paired=[];absolute=[]
    def metrics(sums,index,n):
        mse,bs,ref,hit,union=[sums[...,index+k] for k in range(5)]
        return dict(RMSE=np.sqrt(mse/n),BSS16=1-bs/np.maximum(ref,1e-14),CSI16=np.divide(hit,union,out=np.full_like(hit,np.nan),where=union>0))
    for block in [7,14]:
        w=calendar_block_weights(anchor.issue,anchor.year.to_numpy(),20000,block,20261104)
        with threadpool_limits(limits=2):boot=w@terms
        point=terms.sum(0);n=w.sum(1);est={};draws={}
        for key,index in parts.items():est[key]=metrics(point,index,len(anchor));draws[key]=metrics(boot,index,n)
        def contrast(kind,model,exp,day,reference,reference_model):
            a=(model,exp,day);b=(reference_model,reference,day)
            for metric in ['RMSE','BSS16','CSI16']:
                delta=draws[a][metric]-draws[b][metric];lo,hi=np.nanquantile(delta,[.025,.975])
                row=dict(kind=kind,model=model,experiment=exp,lead_day=day,reference_model=reference_model,
                    reference=reference,metric=metric,estimate=est[a][metric]-est[b][metric],
                    ci_low=lo,ci_high=hi,block_days=block,replicates=20000,confirmatory=False)
                if kind=='feature' and metric=='BSS16':
                    q=.05/(2*63);low,high=np.nanquantile(delta,[q,1-q])
                    row.update(ci_low_family63=low,ci_high_family63=high,family_size=63)
                paired.append(row)
        for model,exp,day in itertools.product(MODELS,[f'E{i}' for i in range(1,8)],[1,2,3]):
            contrast('feature',model,exp,day,'E0',model)
        for a,b in itertools.combinations(MODELS,2):
            for day in [1,2,3]:contrast('architecture',a,'E7',day,'E7',b)
        for (model,exp,day),m in draws.items():
            lo,hi=np.nanquantile(m['BSS16'],[.025,.975])
            absolute.append(dict(model=model,experiment=exp,lead_day=day,metric='BSS16',
                estimate=est[(model,exp,day)]['BSS16'],ci_low=lo,ci_high=hi,
                block_days=block,replicates=20000,confirmatory=False))
    pd.DataFrame(paired).to_csv(REPORT/'paired_bootstrap.csv',index=False,lineterminator='\n')
    pd.DataFrame(absolute).to_csv(REPORT/'absolute_bss_ci.csv',index=False,lineterminator='\n')
    seeds=pd.read_parquet(PRIVATE/'predictions_seed.parquet');seeds.year='pooled2021-2023'
    scored=score(seeds);scored.to_csv(REPORT/'scores_seed_pooled.csv',index=False,lineterminator='\n')
    stability=scored[scored.model.isin(['tft','informer'])].groupby(['model','experiment','lead_day','season','threshold_mm'])[
        ['RMSE','BSS','CSI','POD','FAR']].agg(['mean','std','min','max'])
    stability.columns=['_'.join(c) for c in stability.columns]
    stability.reset_index().to_csv(REPORT/'seed_stability.csv',index=False,lineterminator='\n')
    thresholds=pd.read_csv(REPORT/'ensemble_thresholds.csv').to_dict('records')
    for m in run['models']:
        if m['model']!='lgbm':continue
        for row in m['calibration']:
            thresholds.append(dict(model='lgbm',experiment=m['experiment'],year=m['year'],lead_day=row['lead_index']+1,
                threshold_mm=row['threshold_mm'],positive=row['positive'],negative=row['negative'],
                decision_threshold=row['decision_threshold'],fallback=min(row['positive'],row['negative'])<20))
    assert len(thresholds)==648
    pd.DataFrame(thresholds).to_csv(REPORT/'thresholds_all_models.csv',index=False,lineterminator='\n')
    dump(REPORT/'evaluation.json',dict(status='complete',bootstrap_repeats=20000,block_days=[7,14],
        bootstrap_seed=20261104,paired_rows=len(paired),absolute_rows=len(absolute),
        scope='Exploratory conditional on fitted models, not independent holdout or full training/label uncertainty',
        adjustment='Bonferroni family63 for all 7 feature contrasts x 3 days x 3 models, BSS16 only; others pointwise95%',
        confirmatory=False,test2025_read=False,seconds=time.perf_counter()-tick,code_sha256=sha(__file__)))
    print('Bootstrap, seed stability and 648 calibration thresholds complete')


if __name__=='__main__':main()
