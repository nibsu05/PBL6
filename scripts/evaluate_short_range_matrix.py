"""Ensemble on matched seeds, then 20,000 shared paired calendar-block draws."""
from pathlib import Path
import json
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from src.short_range_ablation import seed_mean,ensemble_thresholds,paired_matrix_bootstrap
from src.short_range_evaluation import score_predictions
from src.short_range_dataset import file_hash

REPORT=ROOT/'reports/short_range_ablation_2026_10_21'
PRIVATE=ROOT/'data/operational/short_range/ablation_2026_10_21'


def main():
    tick=time.perf_counter()
    run=json.loads((REPORT/'run.json').read_text(encoding='utf-8'))
    if run['status']!='complete' or len(run['models'])!=96:
        raise ValueError('Complete72 TFT and24 deterministic LightGBM pipelines required')
    rows,thresholds=[],[]
    for model in ['lgbm','tft']:
        for year in [2021,2022,2023]:
            for exp in [f'E{i}' for i in range(8)]:
                entries=[m for m in run['models'] if m['learner']==model and m['year']==year and m['experiment']==exp]
                if model=='tft':
                    cal=seed_mean([pd.read_parquet(PRIVATE/m['cal_predictions']) for m in entries])
                    ev=seed_mean([pd.read_parquet(PRIVATE/m['eval_predictions']) for m in entries])
                    ev,params=ensemble_thresholds(cal,ev)
                    thresholds.extend([dict(model=model,year=year,experiment=exp,**p) for p in params])
                else:
                    if len(entries)!=1: raise ValueError('Expected one deterministic LightGBM')
                    ev=pd.read_parquet(PRIVATE/entries[0]['eval_predictions'])
                rows.append(ev)
    predictions=pd.concat([pd.read_parquet(PRIVATE/'baselines.parquet')]+rows,ignore_index=True)
    predictions.to_parquet(PRIVATE/'predictions_ensemble.parquet',index=False)
    pd.DataFrame(thresholds).to_csv(REPORT/'ensemble_calibration_thresholds.csv',index=False,lineterminator='\n')
    score_predictions(predictions).to_csv(REPORT/'scores_ensemble.csv',index=False,lineterminator='\n')
    pooled=predictions.copy();pooled['year']='pooled2021-2023'
    score_predictions(pooled).to_csv(REPORT/'scores_ensemble_pooled.csv',index=False,lineterminator='\n')
    seed_scores=pd.read_csv(REPORT/'scores_seed_pooled.csv')
    summary=seed_scores[seed_scores.model=='tft'].groupby(['experiment','lead_day','season','threshold_mm'])[['RMSE','BSS','CSI']].agg(['mean','std','min','max'])
    summary.columns=['_'.join(c) for c in summary.columns]
    summary.reset_index().to_csv(REPORT/'seed_stability.csv',index=False,lineterminator='\n')
    boot=[]
    with threadpool_limits(limits=4):
        for block in [7,14]:
            print('BOOTSTRAP',block,'days20000draws',flush=True)
            boot.append(paired_matrix_bootstrap(predictions,20000,block,20261021))
    pd.concat(boot,ignore_index=True).to_csv(REPORT/'paired_bootstrap.csv',index=False,lineterminator='\n')
    # Reliability bins shared across all configurations, no tuning from this table.
    bins=np.linspace(0,1,11);reliability=[]
    for (model,exp,lead),part in predictions.groupby(['model','experiment','lead_day']):
        if model=='zero':continue
        index=np.minimum(np.searchsorted(bins,part.p16,side='right')-1,9)
        for b in range(10):
            subset=part.iloc[np.flatnonzero(index==b)]
            reliability.append(dict(model=model,experiment=exp,lead_day=lead,bin=b,n=len(subset),
                mean_probability=float(subset.p16.mean()) if len(subset) else np.nan,
                observed_frequency=float((subset.obs>=16).mean()) if len(subset) else np.nan))
    pd.DataFrame(reliability).to_csv(REPORT/'reliability16.csv',index=False,lineterminator='\n')
    output=dict(status='complete',ensemble_issues_per_lead=1075,seed_predictions_rows=len(pd.read_parquet(PRIVATE/'predictions_seed.parquet')),
        ensemble_prediction_rows=len(predictions),bootstrap_repeats=20000,blocks=[7,14],
        primary_family_size=9,test2025_read=False,seconds=time.perf_counter()-tick,
        evaluation_code_hashes={p:file_hash(ROOT/p) for p in ['src/short_range_ablation.py','scripts/evaluate_short_range_matrix.py']})
    (REPORT/'evaluation.json').write_text(json.dumps(output,indent=2),encoding='utf-8',newline='\n')
    print('EVALUATION_COMPLETE',round(output['seconds'],2),'seconds',flush=True)


if __name__=='__main__':main()
