"""Aggregate the frozen pilot; paired exploratory intervals, no model selection."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
from src.short_range_evaluation import score_predictions,paired_pilot_bootstrap
from src.verification import reliability_table


def main():
    report=ROOT/'reports/short_range_pilot_2026_10_21'
    run=json.loads((report/'run.json').read_text(encoding='utf-8'))
    if run['status']!='complete': raise ValueError('Pilot must complete before evaluation')
    frame=pd.read_parquet(ROOT/'data/operational/short_range/pilot_2026_10_21/predictions.parquet')
    if frame.year.max()>2023: raise ValueError('Development only')
    pooled=frame.copy(); pooled['year']='pooled2021-2023'
    score_predictions(pooled).to_csv(report/'scores_pooled.csv',index=False,lineterminator='\n')
    cis=[]
    for model in ['lgbm','tft']:
        for block in [7,14]:
            result=paired_pilot_bootstrap(frame,model,repeats=2000,block_days=block)
            cis.append(result)
            print('BOOTSTRAP_DONE',model,block,flush=True)
    pd.concat(cis).to_csv(report/'paired_bootstrap.csv',index=False,lineterminator='\n')
    reliability=[]
    for (model,exp,lead),part in pooled.groupby(['model','experiment','lead_day']):
        table=reliability_table((part.obs>=16).astype(float),part.p16).reset_index(names='bin')
        table['model']=model; table['experiment']=exp; table['lead_day']=lead
        reliability.append(table)
    pd.concat(reliability).to_csv(report/'reliability16.csv',index=False,lineterminator='\n')
    summary=score_predictions(pooled)
    main=summary[(summary.season=='all')&(summary.threshold_mm==16)]
    print(main[['model','experiment','lead_day','n','events','RMSE','BSS','CSI']].to_string(index=False))


if __name__=='__main__': main()
