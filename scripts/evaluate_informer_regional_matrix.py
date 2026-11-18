"""Exploratory paired block confidence intervals; keep old primary tests intact."""
from pathlib import Path
import json
import sys
import time
import itertools

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from scripts.run_informer_regional_matrix import REPORT, PRIVATE
from scripts.pilot_short_range import dump
from src.short_range_ablation import calendar_block_weights
from src.short_range_dataset import file_hash


def main():
    tick = time.perf_counter()
    run = json.loads((REPORT / 'run.json').read_text(encoding='utf8'))
    assert run['status'] == 'complete' and len(run['models']) == 72
    frame = pd.read_parquet(PRIVATE / 'predictions_ensemble.parquet')
    descriptors, terms, positions = [], [], {}
    base = frame[(frame.model == 'tft') & (frame.experiment == 'E0') & (frame.lead_day == 1)].sort_values('issue')
    dates = pd.DatetimeIndex(base.issue)
    for model, exp, day in itertools.product(['lgbm','tft','informer'], [f'E{i}' for i in range(8)], [1,2,3]):
        part = frame[(frame.model==model) & (frame.experiment==exp) & (frame.lead_day==day)].sort_values('issue')
        assert pd.DatetimeIndex(part.issue).equals(dates)
        event = part.obs.to_numpy() >= 16; decision = part.p16.to_numpy() >= part.tau16.to_numpy()
        positions[(model,exp,day)] = len(terms)
        terms.extend([(part.amount.to_numpy()-part.obs.to_numpy())**2,
                      (part.p16.to_numpy()-event)**2, (part.ref16.to_numpy()-event)**2,
                      (decision & event).astype(float), (decision | event).astype(float)])
        descriptors.append((model,exp,day))
    values = np.stack(terms, axis=1).astype(np.float64); point = values.sum(0)
    output, absolute = [], []
    for block in [7,14]:
        print('BOOTSTRAP', block, 'days, 20000 shared draws', flush=True)
        weights = calendar_block_weights(dates, base.year.to_numpy(), repeats=20000, block_days=block, seed=20261021)
        with threadpool_limits(limits=4): totals = weights @ values
        n = weights.sum(1).astype(float)
        def metrics(index, draws):
            table = totals if draws else point[None, :]
            counts = n if draws else np.array([len(dates)])
            return dict(RMSE=np.sqrt(table[:,index]/counts),
                        BSS16=1-table[:,index+1]/table[:,index+2],
                        CSI16=np.divide(table[:,index+3],table[:,index+4],out=np.full(len(table),np.nan),where=table[:,index+4]>0))
        contrasts = []
        for model, exp, day in descriptors:
            if exp != 'E0': contrasts.append(('feature', (model,exp,day), (model,'E0',day)))
            if exp == 'E7':
                for key, draws in metrics(positions[(model,exp,day)],True).items():
                    low, high = np.nanquantile(draws,[.025,.975])
                    absolute.append(dict(model=model,experiment=exp,lead_day=day,metric=key,
                        estimate=float(metrics(positions[(model,exp,day)],False)[key][0]),ci_low=float(low),ci_high=float(high),
                        block_days=block,replicates=20000,confirmatory=False))
        for day in [1,2,3]:
            for first,second in [('lgbm','tft'),('lgbm','informer'),('tft','informer')]:
                contrasts.append(('architecture',(first,'E7',day),(second,'E7',day)))
        for kind, first, second in contrasts:
            a=metrics(positions[first],True); b=metrics(positions[second],True)
            pa=metrics(positions[first],False); pb=metrics(positions[second],False)
            for metric in a:
                delta=a[metric]-b[metric];low,high=np.nanquantile(delta,[.025,.975])
                output.append(dict(kind=kind,model=first[0],reference_model=second[0],experiment=first[1],
                    reference_experiment=second[1],lead_day=first[2],metric=metric,
                    estimate=float(pa[metric][0]-pb[metric][0]),ci_low=float(low),ci_high=float(high),
                    block_days=block,replicates=20000,confirmatory=False,
                    scope='Exploratory development; pointwise 95%; conditional on fitted ensembles, not training/label uncertainty'))
        del weights,totals
    pd.DataFrame(output).to_csv(REPORT/'paired_bootstrap_exploratory.csv',index=False,lineterminator='\n')
    pd.DataFrame(absolute).to_csv(REPORT/'absolute_skill_ci.csv',index=False,lineterminator='\n')
    # Reliability at identical bins, without selecting or retuning from evaluation.
    rows=[]
    for (model,exp,day), part in frame.groupby(['model','experiment','lead_day']):
        ids=np.minimum(np.searchsorted(np.linspace(0,1,11),part.p16,side='right')-1,9)
        for b in range(10):
            p=part.iloc[np.flatnonzero(ids==b)]
            rows.append(dict(model=model,experiment=exp,lead_day=day,bin=b,n=len(p),
                mean_probability=float(p.p16.mean()) if len(p) else None,
                observed_frequency=float((p.obs>=16).mean()) if len(p) else None))
    pd.DataFrame(rows).to_csv(REPORT/'reliability16.csv',index=False,lineterminator='\n')
    dump(REPORT/'evaluation.json',dict(status='complete',architecture_comparisons_per_block=27,
        feature_comparisons_per_block=189,blocks=[7,14],replicates=20000,confidence=.95,
        confirmatory=False,multiplicity_adjusted=False,old_primary_tft_family_unchanged=True,test2025_read=False,
        seconds=time.perf_counter()-tick,code_sha256=file_hash(__file__)))
    print('EXPLORATORY_EVALUATION_COMPLETE', round(time.perf_counter()-tick,2),'seconds',flush=True)


if __name__=='__main__':main()
