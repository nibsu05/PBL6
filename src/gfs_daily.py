"""Frozen daily experiment contracts and causal/probabilistic utilities."""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

NAME = 'gfs_station_daily_v2_2026_11_10'
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/operational' / NAME
PUBLIC = ROOT / 'reports' / NAME
DATA = ROOT / 'data/processed' / NAME
PARENT = ROOT / 'data/operational/gfs_station_57_2026_11_10'
OLD_CACHE = ROOT / 'data/operational/gfs_station_pilot_2026_11_10'
VRAIN = ROOT / 'data/operational/vrain_2026_11_09'
HISTORY = [f'rain_lag_day{k}_mm' for k in range(1, 8)]
RECENT = [f'rain_recent{k}h_mm' for k in (1, 6, 24)]
N0 = ['gfs_rain_mm', 'sin_doy', 'cos_doy', 'latitude', 'longitude', 'station_code'] + HISTORY + RECENT
RAW_MET = ['gfs_t850_c', 'gfs_rh850_pct', 'gfs_u850', 'gfs_v850', 'gfs_pwat']
DERIVED_MET = ['gfs_q850_gkg', 'gfs_qflux_e', 'gfs_qflux_n', 'gfs_wspd850']
TERRAIN = ['dem_elev_m', 'dem_mean_5km_m', 'dem_std_5km_m', 'dem_slope_east', 'dem_slope_north']
INTERACTION = ['wind_upslope', 'moist_upslope']
FEATURES = dict(N0=N0, N1=N0 + RAW_MET, N2=N0 + RAW_MET + DERIVED_MET,
                N3=N0 + RAW_MET + TERRAIN, N4=N0 + RAW_MET + TERRAIN + DERIVED_MET,
                N5=N0 + RAW_MET + TERRAIN + DERIVED_MET + INTERACTION)
TREE_CANDIDATES = [dict(name='small', num_leaves=7, max_depth=3, min_child_samples=40, reg_lambda=5.),
                   dict(name='pilot', num_leaves=15, max_depth=4, min_child_samples=40, reg_lambda=2.),
                   dict(name='medium', num_leaves=31, max_depth=5, min_child_samples=80, reg_lambda=5.)]
GRU_CANDIDATES = [dict(name='small', hidden=16, head=24, lr=.001),
                  dict(name='pilot', hidden=24, head=32, lr=.001),
                  dict(name='wide', hidden=48, head=48, lr=.0007)]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def protocol_definition(cohort_sha):
    return dict(version=NAME, authorized_date='2026-11-10', parent_experiment='gfs_station_57_2026_11_10',
        task='three separate station-observed next-24h rainfall amounts, mean and median, plus nested exceedance probabilities',
        station_count=57, station_manifest_sha256=cohort_sha, cohort_selection='unchanged train-only 57-station cohort',
        first_issue_day='2021-01-08', last_issue_day='2024-12-28', cadence_days=1,
        init_hour_utc=0, issue_hour_utc=12, issue_hour_vietnam=19, rain_leads=[12, 36, 60, 84], met_leads=[24, 48, 72],
        met_note='instantaneous midpoint forecasts, not daily atmospheric means',
        gfs_delay_assumed_hours=8, gfs_delay_scenarios_hours=[8, 12, 16],
        unavailable_cycle_policy='never use an unavailable cycle; delay16h has no same-cycle eligibility; earlier-cycle replacement requires another protocol',
        original_release_times_proven=False, gauge_delay_hours=[1, 3, 6], primary_gauge_delay_hours=1,
        common_mask='all features, all three targets and all gauge-delay scenarios complete, identical examples for all primary models',
        history_days=7, full_targets_within_fold=True,
        split=dict(train='2021-2022', calibration='2023', development='2024; explored, not final test'),
        tuning=dict(anchor='N3 raw-only; shared selected hyperparameters across all feature ablations',
            folds=[dict(start=f'2022-{m:02d}-01', end=end) for m, end in [(1, '2022-04-01'), (4, '2022-07-01'), (7, '2022-10-01'), (10, '2023-01-01')]],
            train_end_gap_days=7, seed=17, tree_candidates=TREE_CANDIDATES, max_trees=600, learning_rate=.04, patience=50,
            mean_objective='Tweedie p1.5; choose hyperparameters by mean fold/horizon macro RMSE relative to raw GFS',
            median_objective='quantile alpha0.5; choose by mean fold/horizon macro MAE relative to raw GFS',
            probability_objective='wet binary plus heavy-given-wet binary; select by average threshold macro Brier ratios to train-frequency references',
            final_trees='median best_iteration over train-only validation folds, per horizon and head',
            gru_candidates=GRU_CANDIDATES, gru_max_epochs=60, gru_patience=10, gru_batch=256,
            gru_loss='scaled Tweedie mean + pinball median +0.5*(BCE wet + BCE heavy conditional on wet)',
            gru_selection='equal-weight average of normalized mean RMSE, median MAE, BS1 and BS50 on train-only folds',
            gru_final_epochs='median best epoch over four train-only folds; fixed for N3 and N5'),
        calibration=dict(period='2023 only; no early stopping on this period',
            method='Platt wet and Platt heavy-given-wet, then p50=p1*q50_given_wet',
            cutoff_selection='four leave-quarter-out calibration folds, exclude 7-day neighborhoods; shared cutoff across both thresholds per model/horizon',
            cutoff_grid=[round(float(x), 2) for x in np.arange(.05, 1., .05)],
            cutoff_score='mean macro CSI over 1mm and 50mm on cross-fitted calibration probabilities',
            final_calibrator='fit all 2023 after cutoff selection; calibration diagnostics are not independent forecast validation'),
        features=FEATURES, feature_counts={k:len(v) for k,v in FEATURES.items()},
        feature_pairs=[['N1','N0'], ['N2','N1'], ['N3','N1'], ['N4','N3'], ['N5','N4'], ['N5','N3']],
        seeds=[17,29,43], sample_weighting='uniform samples; station-macro evaluation',
        baselines=['ZERO', 'CLIM mean/weighted median and event frequencies', 'PERSISTENCE', 'GFS', 'MOS ridge mean/linear quantile median/logistic nested events'],
        gru_configurations=['N3','N5'], gauge_latency_retraining='LightGBM N3 at 3h and 6h, shared primary hyperparameters, no retuning',
        probability_thresholds_mm24h=[1.,50.], heavy_threshold_status='exploratory, not an asserted warning standard',
        probability_ordering='p50<=p1 per seed, after calibration and after ensemble; same decision cutoff preserves event nesting',
        amount_primary_metrics=dict(mean='macro RMSE', median='macro MAE'),
        reported_metrics=['MAE','RMSE','Bias','BS','BSS','CSI','POD','FAR'],
        uncertainty=dict(method='paired circular moving blocks of 14 daily issue dates; keep all stations/horizons together',draws=1000,seed=1701),
        heavy_analysis='amount errors conditional on observed >=50mm and monthly summaries; descriptive only, no y-based operational routing',
        test2025_read=False, recent2026_used_for_fit=False,
        no_single_change_attribution='daily-v2 changes several design choices; compare within this protocol, not unmatched old/new score averages')


def load_protocol():
    path = PUBLIC / 'protocol.json'
    lock = json.loads((BASE / 'protocol_lock.json').read_text())
    if sha(path) != lock['protocol_sha256']:
        raise ValueError('Protocol changed after freeze; create a new version')
    return json.loads(path.read_text(encoding='utf-8'))


def gauge_history(hourly, daily, day_index, station_index, delay):
    if day_index < 7 or delay not in (1, 3, 6):
        raise ValueError('History/delay outside frozen contract')
    last = 24 * day_index + 23 - delay
    history = daily[day_index-7:day_index, station_index][::-1]
    return {**dict(zip(HISTORY, history)), **{name:hourly[last-k+1:last+1, station_index].sum()
                                               for k, name in zip((1,6,24), RECENT)}}


def cv_masks(frame, fold):
    start = pd.Timestamp(fold['start'], tz='Asia/Ho_Chi_Minh').tz_convert('UTC')
    end = pd.Timestamp(fold['end'], tz='Asia/Ho_Chi_Minh').tz_convert('UTC')
    max_end = frame.issue_utc + pd.Timedelta(hours=72)
    train = frame.split.eq('train') & (max_end <= start-pd.Timedelta(days=7))
    valid = frame.split.eq('train') & (frame.issue_utc >= start) & (max_end < end)
    if 'station_id' in frame:valid &= frame.station_id.isin(frame.loc[train,'station_id'].unique())
    if not train.any() or not valid.any():
        raise ValueError('Empty chronological tuning fold')
    return train.to_numpy(), valid.to_numpy()


def nested_probabilities(wet, conditional_heavy):
    wet = np.asarray(wet, float); conditional_heavy = np.asarray(conditional_heavy, float)
    if not np.isfinite(wet).all() or not np.isfinite(conditional_heavy).all():
        raise ValueError('Nonfinite probabilities')
    if ((wet < 0)|(wet > 1)|(conditional_heavy < 0)|(conditional_heavy > 1)).any():
        raise ValueError('Probability outside unit interval')
    return np.stack([wet, wet * conditional_heavy], axis=-1)


class Platt:
    def fit(self, probability, y):
        probability = np.asarray(probability); y = np.asarray(y, int)
        self.estimator = None
        self.constant = float((y.sum()+.5)/(len(y)+1)) if len(y) else .5
        if len(np.unique(y)) == 2:
            self.estimator = LogisticRegression(C=1.,solver='lbfgs',max_iter=500).fit(self._x(probability),y)
        return self

    @staticmethod
    def _x(p):
        p = np.clip(p, 1e-5, 1-1e-5)
        return np.log(p/(1-p)).reshape(-1,1)

    def predict(self, p):
        return np.full(len(p),self.constant) if self.estimator is None else self.estimator.predict_proba(self._x(p))[:,1]


def calibrate_nested(raw_wet, raw_conditional, y, calibration_mask):
    y=np.asarray(y); c=np.asarray(calibration_mask,bool)
    wet = Platt().fit(np.asarray(raw_wet)[c], y[c]>=1)
    conditional = Platt().fit(np.asarray(raw_conditional)[c & (y>=1)], y[c & (y>=1)]>=50)
    return nested_probabilities(wet.predict(raw_wet),conditional.predict(raw_conditional)), (wet,conditional)


def with_delay(frame, delay):
    if delay not in (1,3,6):raise ValueError('Unsupported latency scenario')
    f=frame.copy()
    for name in RECENT:f[name]=f[f'{name}_delay{delay}']
    f['observation_cutoff_utc']=f.issue_utc-pd.Timedelta(hours=delay)
    return f


def station_average(values, stations):
    return float(pd.Series(np.asarray(values)).groupby(np.asarray(stations)).mean().mean())


def score_bundle(y, mean, median, raw_wet, raw_conditional, stations, gfs, training_y):
    y=np.asarray(y);gfs=np.asarray(gfs);prob=nested_probabilities(raw_wet,raw_conditional)
    codes=pd.factorize(stations)[0];n=np.bincount(codes)
    def avg(values,root=False):
        per=np.bincount(codes,weights=np.asarray(values))/n
        return float(np.sqrt(per).mean() if root else per.mean())
    rmse=avg((np.asarray(mean)-y)**2,True);mae=avg(abs(np.asarray(median)-y))
    rmse_ref=max(avg((gfs-y)**2,True),1e-6);mae_ref=max(avg(abs(gfs-y)),1e-6)
    ratios=[]
    for j,t in enumerate((1,50)):
        label=y>=t;prior=float(np.mean(np.asarray(training_y)>=t))
        reference=max(avg((prior-label)**2),1e-6)
        ratios.append(avg((prob[:,j]-label)**2)/reference)
    return dict(mean_score=rmse/rmse_ref,median_score=mae/mae_ref,
                probability_score=float(np.mean(ratios)),joint_score=float(np.mean([rmse/rmse_ref,mae/mae_ref]+ratios)),
                macro_rmse=rmse,macro_mae=mae)


def crossfit_calibration(frame, raw_wet_by_seed, raw_conditional_by_seed):
    """Quarter-held-out calibration predictions plus final all-cal calibrators.

    Calibration folds are tuning diagnostics; they are not issued forecasts.
    The final independent development forecasts use only calibrators fit on 2023.
    """
    y=frame.y_mm.to_numpy();cal=frame.split.eq('cal').to_numpy()
    when=frame.issue_utc.dt.tz_convert('Asia/Ho_Chi_Minh')
    probability=[];oof=[];artifacts=[]
    for wet,conditional in zip(raw_wet_by_seed,raw_conditional_by_seed):
        full,artifact=calibrate_nested(wet,conditional,y,cal)
        probability.append(full);artifacts.append(artifact)
        cross=np.full((len(frame),2),np.nan)
        for quarter in range(1,5):
            start=pd.Timestamp(year=2023,month=3*(quarter-1)+1,day=1,tz='Asia/Ho_Chi_Minh')
            end=start+pd.DateOffset(months=3)
            hold=cal&(when>=start).to_numpy()&(when<end).to_numpy()
            fit=cal&((when<start-pd.Timedelta(days=7))|(when>=end+pd.Timedelta(days=7))).to_numpy()
            converted,_=calibrate_nested(wet,conditional,y,fit)
            cross[hold]=converted[hold]
        if not np.isfinite(cross[cal]).all():raise ValueError('Missing calibration OOF probabilities')
        oof.append(cross)
    return np.mean(probability,axis=0),np.mean(oof,axis=0),artifacts


def macro_csi(y, probability, stations, cutoff):
    label=np.asarray(y,bool);yes=np.asarray(probability)>=cutoff
    codes=pd.factorize(stations)[0]
    hit=np.bincount(codes,weights=(yes&label));miss=np.bincount(codes,weights=(~yes&label));false=np.bincount(codes,weights=(yes&~label))
    denominator=hit+miss+false
    return float(np.nanmean(np.divide(hit,denominator,out=np.full(len(hit),np.nan),where=denominator>0)))


def choose_cutoff(frame, oof, grid):
    cal=frame.split.eq('cal').to_numpy();y=frame.loc[cal,'y_mm'].to_numpy();sid=frame.loc[cal,'station_id'].to_numpy()
    scores=[]
    for cutoff in grid:
        score=np.mean([macro_csi(y>=t,oof[cal,j],sid,cutoff) for j,t in enumerate((1,50))])
        scores.append((float(score),-abs(cutoff-.5),float(cutoff)))
    # A single cutoff for both events cannot yield a heavy-only decision.
    return max(scores)[2], [dict(cutoff=c,score=s) for s,_,c in scores]
