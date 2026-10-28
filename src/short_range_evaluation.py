"""Calibration and paired evaluation for regional 24-hour totals."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from src.short_range_dataset import THRESHOLDS
from src.verification import continuous_scores, contingency_scores, brier_score, brier_skill_score


def monotone_probabilities(prob):
    result = np.clip(np.asarray(prob, dtype=float), 0., 1.).copy()
    if result.shape[-1] != 3:
        raise ValueError('Expected three nested thresholds')
    for row in result.reshape(-1, 3):
        blocks = []
        for index, value in enumerate(row):
            blocks.append([float(value), 1, [index]])
            while len(blocks) > 1 and blocks[-2][0] < blocks[-1][0]:
                b, a = blocks.pop(), blocks.pop()
                count = a[1] + b[1]
                blocks.append([(a[0]*a[1]+b[0]*b[1])/count, count, a[2]+b[2]])
        for value, _, indices in blocks:
            row[indices] = value
    return result


def logit(prob):
    p = np.clip(prob, 1e-6, 1-1e-6)
    return np.log(p/(1-p))


def apply_calibration(raw, params):
    result = np.asarray(raw, dtype=float).copy()
    for row in params:
        lead, index = row['lead_index'], row['threshold_index']
        if row['platt_fitted']:
            value = row['coef']*logit(result[:, lead, index]) + row['intercept']
            result[:, lead, index] = 1/(1+np.exp(-np.clip(value, -60, 60)))
    return monotone_probabilities(result)


def fit_calibration(y_cal, raw_cal, min_events=20):
    params = []
    for lead in range(3):
        for ti, threshold in enumerate(THRESHOLDS):
            event = (y_cal[:, lead] >= threshold).astype(int)
            positive, negative = int(event.sum()), int((1-event).sum())
            row = dict(lead_index=lead, threshold_index=ti, threshold_mm=float(threshold),
                       positive=positive, negative=negative, platt_fitted=False,
                       coef=1., intercept=0., decision_threshold=.5)
            if min(positive, negative) >= min_events:
                fitted = LogisticRegression(C=1., max_iter=200).fit(logit(raw_cal[:, lead, ti])[:,None], event)
                row.update(platt_fitted=True, coef=float(fitted.coef_[0,0]), intercept=float(fitted.intercept_[0]))
            params.append(row)
    calibrated = apply_calibration(raw_cal, params)
    for row in params:
        if min(row['positive'], row['negative']) < min_events:
            continue
        lead, ti = row['lead_index'], row['threshold_index']
        event = y_cal[:, lead] >= THRESHOLDS[ti]
        best, selected = -1., .5
        for tau in np.arange(.01, 1., .01):
            forecast = calibrated[:, lead, ti] >= tau
            hit = np.sum(event & forecast)
            denom = np.sum(event | forecast)
            csi = hit/denom if denom else float('nan')
            if np.isfinite(csi) and csi >= best:
                best, selected = csi, float(tau)
        row['decision_threshold'] = selected
    return params


def prediction_frame(dates, obs, amount, prob, ref_prob, params, model, experiment, year, seed):
    records = []
    for lead in range(3):
        frame = pd.DataFrame({'issue': dates, 'lead_day': lead+1, 'obs': obs[:,lead],
                              'amount': amount[:,lead], 'model': model,
                              'experiment': experiment, 'year': year, 'seed': seed})
        for ti, threshold in enumerate(THRESHOLDS.astype(int)):
            match = [r for r in params if r['lead_index']==lead and r['threshold_index']==ti]
            tau = match[0]['decision_threshold'] if match else .5
            frame[f'p{threshold}'] = prob[:,lead,ti]
            frame[f'ref{threshold}'] = ref_prob[:,lead,ti]
            frame[f'tau{threshold}'] = tau
        records.append(frame)
    return pd.concat(records, ignore_index=True)


def score_predictions(frame):
    result = []
    for keys, part in frame.groupby(['model','experiment','year','seed','lead_day']):
        month = (pd.DatetimeIndex(part.issue) + pd.Timedelta(hours=7)).month
        seasons = {'all': np.ones(len(part), bool), 'may_oct': np.isin(month,range(5,11)),
                   'nov_feb': np.isin(month,[11,12,1,2]), 'mar_apr': np.isin(month,[3,4])}
        for season, mask in seasons.items():
            data = part.iloc[np.flatnonzero(mask)]
            if not len(data): continue
            base = dict(zip(['model','experiment','year','seed','lead_day'], keys))
            base.update(season=season, **continuous_scores(data.obs, data.amount))
            for threshold in THRESHOLDS.astype(int):
                event = (data.obs >= threshold).to_numpy()
                prob = data[f'p{threshold}'].to_numpy()
                decision = (prob >= data[f'tau{threshold}'].to_numpy()).astype(float)
                csi = contingency_scores(event.astype(float), decision, .5)
                direct = contingency_scores(data.obs, data.amount, threshold)
                row = dict(base, threshold_mm=int(threshold), events=int(event.sum()),
                           BS=brier_score(event,prob),
                           BSS=brier_skill_score(event,prob,data[f'ref{threshold}']),
                           CSI=csi['CSI'], POD=csi['POD'], FAR=csi['FAR'],
                           amount_CSI=direct['CSI'])
                result.append(row)
    return pd.DataFrame(result)


def paired_pilot_bootstrap(frame, model, repeats=2000, block_days=7, seed=20261021):
    """E7−E0, conditional on fitted seed; all obs/pred/reference resampled jointly."""
    subset = frame[(frame.model==model) & frame.experiment.isin(['E0','E7'])]
    out = []
    for lead in [1,2,3]:
        cols = ['issue','year','obs','amount','p16','ref16','tau16']
        a = subset[(subset.lead_day==lead)&(subset.experiment=='E0')][cols]
        b = subset[(subset.lead_day==lead)&(subset.experiment=='E7')][cols]
        pair = a.merge(b,on=['issue','year'],suffixes=('_0','_7'),validate='one_to_one').sort_values('issue')
        if pair.empty: continue
        np.testing.assert_allclose(pair.obs_0,pair.obs_7,rtol=0,atol=0)
        np.testing.assert_allclose(pair.ref16_0,pair.ref16_7,rtol=0,atol=0)
        obs = pair.obs_0.to_numpy(); event = obs>=16
        error0 = (pair.amount_0.to_numpy()-obs)**2
        error7 = (pair.amount_7.to_numpy()-obs)**2
        ref_error = (pair.ref16_0.to_numpy()-event)**2
        bs0 = (pair.p16_0.to_numpy()-event)**2
        bs7 = (pair.p16_7.to_numpy()-event)**2
        def metrics(indices):
            ref = ref_error[indices].mean()
            return [np.sqrt(error7[indices].mean())-np.sqrt(error0[indices].mean()),
                    (bs0[indices].mean()-bs7[indices].mean())/ref if ref>0 else np.nan]
        years = []
        for year, data in pair.groupby('year', sort=True):
            days = pd.DatetimeIndex(data.issue).normalize()
            calendar = pd.date_range(days.min(),days.max(),freq='D')
            lookup = {d: np.flatnonzero((pair.year.to_numpy()==year)&(pair.issue==d).to_numpy()) for d in calendar}
            years.append((calendar,lookup))
        rng=np.random.default_rng(seed)
        boot=[]
        for _ in range(repeats):
            selections=[]
            for calendar, lookup in years:
                length=len(calendar); count=int(np.ceil(length/block_days))
                starts=rng.integers(0,max(1,length-block_days+1),size=count)
                day_positions=np.concatenate([np.arange(s,min(s+block_days,length)) for s in starts])[:length]
                selections.extend(lookup[calendar[k]] for k in day_positions)
            indices=np.concatenate(selections)
            boot.append(metrics(indices))
        point=metrics(np.arange(len(pair)))
        for mi,name in enumerate(['RMSE','BSS16']):
            values=np.asarray(boot)[:,mi]; valid=values[np.isfinite(values)]
            lo,hi=np.quantile(valid,[.025,.975]) if len(valid) else [np.nan,np.nan]
            out.append(dict(model=model,lead_day=lead,contrast='E7-E0',metric=name,
                            estimate=float(point[mi]),ci_low=float(lo),ci_high=float(hi),
                            n=len(pair),replicates=repeats,valid_replicates=len(valid),
                            block_days=block_days,scope='Exploratory pooled2021-2023; fixed seed42; no multiplicity correction'))
    return pd.DataFrame(out)
