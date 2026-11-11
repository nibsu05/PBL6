"""Publish daily-v2 metrics, conditional errors and calendar-block uncertainty."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd
import numpy as np
from threadpoolctl import threadpool_limits
from src.gfs_daily import BASE,PUBLIC,load_protocol,write_json,sha
from src.gfs_daily_evaluation import point_report,probability_report,paired_uncertainty


def main():
    threadpool_limits(limits=4)
    p=load_protocol();frame=pd.read_parquet(BASE/'predictions_private.parquet')
    tree=json.loads((PUBLIC/'tree_summary.json').read_text());models=tree['models']+['GRU_'+c for c in p['gru_configurations']]
    cutoffs=json.loads((PUBLIC/'decision_cutoffs.json').read_text())
    label_rows=[]
    for (split,h),s in frame.groupby(['split','horizon']):
        y=s.y_mm
        label_rows.append(dict(fold=split,horizon=int(h),samples=len(s),stations=int(s.station_id.nunique()),
            fraction_under1=float((y<1).mean()),mean_mm=float(y.mean()),median_mm=float(y.median()),
            p90_mm=float(y.quantile(.9)),p99_mm=float(y.quantile(.99)),max_mm=float(y.max()),
            events_ge50=int((y>=50).sum()),issue_dates_ge50=int(s.loc[y>=50,'issue_utc'].nunique())))
    pd.DataFrame(label_rows).to_csv(PUBLIC/'label_distribution.csv',index=False)
    point,station,conditional,monthly=point_report(frame,models)
    improvement=[]
    for horizon in (1,2,3):
        for functional,metric in [('mean','rmse'),('median','mae')]:
            per=station[station.fold.eq('dev')&station.horizon.eq(horizon)&station.functional.eq(functional)].pivot(index='station_id',columns='model',values=metric)
            for model in models:
                for reference in ('ZERO','GFS','CLIM','MOS'):
                    if model==reference:continue
                    difference=per[model]-per[reference]
                    improvement.append(dict(model=model,reference=reference,horizon=horizon,functional=functional,metric=metric,
                        stations=len(difference),improved=int((difference < -1e-8).sum()),worsened=int((difference > 1e-8).sum()),
                        tied=int((abs(difference)<=1e-8).sum()),fraction_improved=float((difference < -1e-8).mean())))
    pd.DataFrame(improvement).to_csv(PUBLIC/'station_improvement_summary.csv',index=False)
    prob,event,reliability,coherence=probability_report(frame,models,cutoffs)
    if coherence.violations.sum() or coherence.decision_contradictions.sum():raise ValueError('Probability coherence failed')
    uncertainty=paired_uncertainty(frame,models,p['feature_pairs'],p['uncertainty']['draws'])
    for name,value in [('point_metrics',point),('probability_metrics',prob),('event_metrics',event),('conditional_amount_metrics',conditional),
        ('monthly_point_metrics',monthly),('reliability',reliability),('probability_coherence',coherence),('paired_bootstrap',uncertainty)]:
        value.to_csv(PUBLIC/(name+'.csv'),index=False)
    station.to_csv(BASE/'metrics_by_station_private.csv',index=False)
    dev=point[point.fold.eq('dev')]
    result=dict(status='evaluated',models=models,station_count=int(frame.station_id.nunique()),
        prediction_sha256=sha(BASE/'predictions_private.parquet'),point_rows=len(point),probability_rows=len(prob),event_rows=len(event),
        bootstrap_comparisons=len(uncertainty),probability_order_violations=0,decision_nesting_violations=0,
        calibration_scores='apparent, calibration fitted on 2023',development='2024, not final test',
        test2025_read=False,development_used_for_model_selection=False,
        primary_dev=[dict(model=m,functional=fun,horizon=int(h),value=float(g.iloc[0][metric]))
            for m in models for fun,metric in [('mean','macro_rmse'),('median','macro_mae')] for h in (1,2,3)
            for g in [dev[dev.model.eq(m)&dev.functional.eq(fun)&dev.horizon.eq(h)]]])
    write_json(PUBLIC/'result_summary.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='primary_dev'}),flush=True)


if __name__=='__main__':main()
