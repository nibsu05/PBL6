"""Ensembles and shared calendar-block resampling for development ablations."""
from __future__ import annotations

import numpy as np
import pandas as pd

KEYS = ['issue','lead_day']
VALUES = ['amount','p16','p50','p100']


def seed_mean(frames, seeds=(42,43,44)):
    """Require a complete matched seed set and identical truth/reference rows."""
    if len(frames) != len(seeds):
        raise ValueError('Incomplete ensemble seed set')
    seen, result = set(), None
    for frame in frames:
        if frame.duplicated(KEYS).any():
            raise ValueError('Duplicate issue/lead in one seed')
        seed_values = frame.seed.unique()
        if len(seed_values)!=1 or int(seed_values[0]) in seen:
            raise ValueError('Duplicate or mixed seeds')
        seen.add(int(seed_values[0]))
        current = frame.sort_values(KEYS).reset_index(drop=True)
        if result is None:
            result = current.copy()
            result[VALUES] = 0.
        if not current[KEYS].equals(result[KEYS]):
            raise ValueError('Mismatched ensemble sample universe')
        for name in ['obs','ref16','ref50','ref100','model','experiment','year']:
            if not current[name].equals(result[name]):
                raise ValueError('Mismatched ensemble '+name)
        result[VALUES] += current[VALUES] / len(seeds)
    if seen != set(seeds):
        raise ValueError('Unexpected ensemble seed set')
    result['seed'] = -1
    return result


def ensemble_thresholds(calibration, evaluation, min_events=20):
    """Select on calibration ensemble only; never fit/tune on evaluation truth."""
    output = evaluation.copy()
    records = []
    for lead in [1,2,3]:
        part = calibration[calibration.lead_day==lead]
        for threshold in [16,50,100]:
            event = part.obs.to_numpy() >= threshold
            positive, negative = int(event.sum()), int((~event).sum())
            best, tau = -1., .5
            if min(positive,negative)>=min_events:
                for candidate in np.arange(.01,1.,.01):
                    decision = part[f'p{threshold}'].to_numpy() >= candidate
                    union = np.sum(event | decision)
                    csi = np.sum(event & decision)/union if union else np.nan
                    if np.isfinite(csi) and csi >= best:
                        best, tau = csi,float(candidate)
            output.loc[output.lead_day==lead,f'tau{threshold}'] = tau
            records.append(dict(lead_day=lead,threshold_mm=threshold,positive=positive,
                negative=negative,decision_threshold=tau,fallback=min(positive,negative)<min_events))
    return output, records


def calendar_block_weights(issues, years, repeats=20000, block_days=7, seed=20261021):
    """Moving noncircular blocks within each year; retain gaps in calendar days.

    Each row counts the number of times each valid issue was selected. Missing
    issues remain missing when their calendar date is selected. Draws are shared
    by all leads/contrasts; labels, predictions and references stay paired.
    """
    dates = pd.DatetimeIndex(issues).normalize()
    years = np.asarray(years)
    if len(dates)!=len(years) or dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError('Expected sorted unique daily issues')
    if repeats<1 or block_days<1:
        raise ValueError('Positive bootstrap parameters required')
    rng = np.random.default_rng(seed)
    weights = np.zeros((repeats,len(dates)),dtype=np.float32)
    for year in np.unique(years):
        ids = np.flatnonzero(years==year)
        days = pd.date_range(dates[ids].min(),dates[ids].max(),freq='D')
        lookup = np.full(len(days),-1,dtype=np.int32)
        lookup[days.get_indexer(dates[ids])] = ids
        length, block = len(days), min(block_days,len(days))
        count = int(np.ceil(length/block))
        for first in range(0,repeats,1000):
            size = min(1000,repeats-first)
            starts = rng.integers(0,length-block+1,size=(size,count))
            positions = (starts[:,:,None]+np.arange(block)[None,None,:]).reshape(size,-1)[:,:length]
            sample = lookup[positions]
            rows = np.broadcast_to(np.arange(first,first+size)[:,None],sample.shape)
            valid = sample>=0
            np.add.at(weights,(rows[valid],sample[valid]),1.)
    if np.any(weights.sum(1)==0):
        raise ValueError('Empty bootstrap replicate')
    return weights


def paired_matrix_bootstrap(frame, repeats=20000, block_days=7, seed=20261021):
    """BSS16 family of nine predeclared TFT contrasts, others descriptive."""
    parts, contributions, descriptors = {}, [], []
    base = frame[(frame.model=='tft')&(frame.experiment=='E0')&(frame.lead_day==1)]
    base = base.sort_values('issue')
    if base.duplicated('issue').any():
        raise ValueError('Bootstrap expects one ensemble row per issue/lead')
    dates = pd.DatetimeIndex(base.issue)
    for (model,exp,lead), part in frame.groupby(['model','experiment','lead_day']):
        if model not in ['tft','lgbm'] or exp=='BASE': continue
        part = part.sort_values('issue')
        if not pd.DatetimeIndex(part.issue).equals(dates):
            raise ValueError('All configurations must share exact issue universe')
        reference_part = frame[(frame.model=='tft')&(frame.experiment=='E0')&(frame.lead_day==lead)]
        reference_part = reference_part.sort_values('issue')
        if not np.array_equal(part.obs.to_numpy(),reference_part.obs.to_numpy()):
            raise ValueError('Observed targets differ across models')
        if not np.array_equal(part.ref16.to_numpy(),reference_part.ref16.to_numpy()):
            raise ValueError('Brier references differ across models')
        event = part.obs.to_numpy()>=16
        decision = part.p16.to_numpy()>=part.tau16.to_numpy()
        parts[(model,exp,lead)] = len(contributions)
        contributions.extend([(part.amount.to_numpy()-part.obs.to_numpy())**2,
                              (part.p16.to_numpy()-event)**2,
                              (part.ref16.to_numpy()-event)**2,
                              (decision & event).astype(float), (decision | event).astype(float)])
        descriptors.append((model,exp,lead))
    terms = np.stack(contributions,axis=1).astype(np.float64)
    weights = calendar_block_weights(dates,base.year.to_numpy(),repeats,block_days,seed)
    # Weighted sums (not means) suffice for BSS/CSI; counts used for RMSE.
    totals = weights @ terms
    counts = weights.sum(1).astype(float)
    point = terms.sum(0)
    output = []
    for model,exp,lead in descriptors:
        if exp=='E0': continue
        a,b = parts[(model,'E0',lead)],parts[(model,exp,lead)]
        deltas = dict(
            RMSE=(np.sqrt(totals[:,b]/counts)-np.sqrt(totals[:,a]/counts),
                  np.sqrt(point[b]/len(dates))-np.sqrt(point[a]/len(dates))),
            BSS16=((totals[:,a+1]-totals[:,b+1])/totals[:,a+2],
                   (point[a+1]-point[b+1])/point[a+2]),
            CSI16=(np.divide(totals[:,b+3],totals[:,b+4],out=np.full(repeats,np.nan),where=totals[:,b+4]>0)
                   -np.divide(totals[:,a+3],totals[:,a+4],out=np.full(repeats,np.nan),where=totals[:,a+4]>0),
                   point[b+3]/point[b+4]-point[a+3]/point[a+4]))
        for metric,(draws,estimate) in deltas.items():
            finite = draws[np.isfinite(draws)]
            low,high = np.quantile(finite,[.025,.975])
            primary = model=='tft' and exp in ['E1','E2','E3'] and metric=='BSS16'
            adj = np.quantile(finite,[.05/(2*9),1-.05/(2*9)]) if primary else [np.nan,np.nan]
            output.append(dict(model=model,contrast=exp+'-E0',lead_day=lead,metric=metric,
                estimate=float(estimate),ci_low=float(low),ci_high=float(high),
                family_adjusted_low=float(adj[0]),family_adjusted_high=float(adj[1]),
                primary_family=primary,family_size=9 if primary else None,
                n=len(dates),replicates=repeats,valid_replicates=len(finite),block_days=block_days,
                scope='Explored development years; conditional on fitted models; no independent holdout'))
    return pd.DataFrame(output)
