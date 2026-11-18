"""New, explicitly authorized training-window/loss study; old studies are read-only."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import time
import uuid

import numpy as np
import pandas as pd

from src.gfs_daily import FEATURES, TREE_CANDIDATES, Platt, nested_probabilities, macro_csi

ROOT = Path(__file__).resolve().parents[1]
NAME = 'gfs_training_window_2026_11_18'
BASE = ROOT / 'data/operational' / NAME
PUBLIC = ROOT / 'reports' / NAME
SOURCE = ROOT / 'data/operational/gfs_temporal_2026_11_17/dataset_private.parquet'
SOURCE_SHA = '3497f0832313df953640a8d83229117bc2da51d2adae434a405edf66cdcda8a2'
VRAIN = ROOT / 'data/operational/vrain_update_2026_11_16'
OLD = ROOT / 'data/operational/gfs_station_daily_v2_2026_11_10'
SEEDS = (17, 29, 43)
CASES = {'A': ('short', 'tweedie'), 'B': ('long', 'tweedie'),
         'C': ('short', 'l2'), 'D': ('long', 'l2')}
FOLDS = [dict(start=f'2022-{m:02d}-01', end=e) for m, e in
         [(1, '2022-04-01'), (4, '2022-07-01'), (7, '2022-10-01'), (10, '2023-01-01')]]
CONTRASTS = [('B', 'A'), ('D', 'C'), ('C', 'A'), ('D', 'B')]
CODE = ['src/gfs_window.py', 'src/gfs_window_models.py', 'src/gfs_window_evaluation.py',
        'src/gfs_window_live.py', 'scripts/run_gfs_window.py', 'scripts/record_gfs_window.py',
        'scripts/verify_gfs_window.py', 'src/gfs_daily.py', 'src/gfs_daily_models.py',
        'src/gfs_final_metrics.py', 'src/gfs_daily_evaluation.py', 'src/gfs_station_dataset.py',
        'src/gfs_station.py', 'scripts/collect_gfs_station_pilot.py', 'tests/test_gfs_window.py']


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def atomic(path, writer):
    """A reader without FILE_SHARE_DELETE must not kill a completed fit on Windows."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.part')
    writer(temp)
    for attempt in range(30):
        try:
            temp.replace(path)
            return
        except PermissionError:
            if attempt == 29:
                raise
            time.sleep(.1)


def write_json(path, value):
    atomic(path, lambda p: p.write_text(json.dumps(value, indent=2, ensure_ascii=False,
        allow_nan=False) + '\n', encoding='utf-8', newline='\n'))


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save_csv(frame, path):
    atomic(path, lambda p: frame.to_csv(p, index=False, lineterminator='\n'))


def save_parquet(frame, path):
    atomic(path, lambda p: frame.to_parquet(p, index=False, compression='zstd'))


def progress(stage, **kw):
    write_json(BASE / 'progress.json', dict(stage=stage, pid=os.getpid(), updated_utc=now(), **kw))


def protocol():
    return dict(version=NAME, authorization='User approved new training-window/loss study on 2026-11-18',
        task='57 stations; three separate nonoverlapping 24-hour rainfall totals issued daily at19h Vietnam',
        issue_hour_utc=12, init_hour_utc=0, gauge_assumed_delay_hours=1,
        gfs_original_release_proven=False, gauge_original_availability_proven=False,
        source_sha256=SOURCE_SHA, cohort='unchanged 57 stations selected using2021-2022 only',
        source='frozen temporal-study rows; use only N0/N1/N3, no new satellite/ERA5 labels',
        boundaries='retain original year-qualified windows and conservative purges; no window added between years',
        cases={k:dict(training_years=[2021,2022] if w=='short' else [2021,2022,2023,2024],
                      mean_objective=o, feature_set='N3', features=26) for k,(w,o) in CASES.items()},
        calibration_year=2025, calibration_role='probability calibration and warning cutoff only; never tree weights or early stopping',
        retrospective='2026 legacy and modern separately; already seen, partial year, exploratory only',
        prospective='new input snapshots and predictions recorded before issue; future truth only after target end',
        tuning=dict(years=[2021,2022], folds=FOLDS, gap_days=7, full_72h_labels_within_fold=True,
            candidates=TREE_CANDIDATES, objectives=['tweedie','l2'], seed=17, maximum_trees=600,
            patience=50, learning_rate=.04, validation_metric='station-macro RMSE after nonnegative clipping',
            selection='one shared candidate minimizes mean normalized macro RMSE over both losses/all folds/all horizons',
            final_rounds='per-horizon median best iteration across both losses and four folds at shared candidate',
            final_loss='choose objective for long-window ablation/prospective only from training-only CV at shared candidate',
            final_window='long predeclared, not selected using2026',
            auxiliary_heads='reuse old train-only candidate/rounds for median, wet, conditional; same by training window'),
        ablation=dict(window='long', selected_loss='training-only CV', configs=['N0','N1','N3'],
            counts=[16,21,26], retuning=False, N3='alias of B or D; do not refit alias'),
        probability=dict(wet='P(y>=1)', conditional='P(y>=50|y>=1)', heavy='p50=p1*conditional',
            calibration='Platt per seed/head on2025; leave-quarter-out with7day gap for cutoff',
            cutoff_grid=[round(x/20,2) for x in range(1,20)], cutoff='one shared cutoff for1/50 per configuration/horizon',
            objective_effect='A/C share auxiliary heads and calibrated probabilities; B/D share them'),
        targets=dict(primary='conditional mean, assessed by station-macro RMSE',
            secondary='conditional median assessed by station-macro MAE; dry/heavy bias; BS/BSS and POD/FAR/CSI'),
        loss_parameters=dict(tweedie_variance_power=1.5, l2='unweighted squared error', negative_prediction='clip to0 for all regressors'),
        seeds=list(SEEDS), weighting='uniform training rows; equal-station macro reporting',
        baselines=['ZERO','GFS','PERSIST','CLIM_SHORT','CLIM_LONG','MOS_SHORT','MOS_LONG'],
        bss_reference='CLIM_LONG for every model on exactly the same rows',
        primary_factorial_contrasts=[list(x) for x in CONTRASTS],
        secondary_ablation_contrasts=[['N1','N0'],['N3','N1']],
        uncertainty=dict(calendar_block_days=14, draws=5000, seed=1701,
            factorial_family=12, ablation_family=6, correction='Bonferroni simultaneous95%CI plus Holm centered-bootstrap approximate p',
            status='exploratory retrospective; corrections do not undo prior examination of2026'),
        label_policy='no deletion/repair based on model residuals or extreme rainfall',
        prospective_candidates='record all four A-D plus train-CV-selected long model; never select using2026 scores',
        live_truth='same namespace as input; complete24h each day, sum QC, no cross-channel splicing',
        no_fit_years=[2025,2026], no_claims=['untouched2026 test','operational skill before prospective verification',
            'cross-API continuity','spatial regional-average rainfall','improvement guaranteed'])


def load_frame(training_only=False):
    filters = [('split','in',['train','cal','dev','reserved2025'])] if training_only else None
    columns = list(dict.fromkeys(['station_id','gauge_namespace','issue_utc','gfs_init_utc',
        'target_start_utc','target_end_utc','observation_cutoff_utc','horizon','split','y_mm',
        'sample_ready','recommended_sample','in_frozen_57_cohort'] + FEATURES['N3']))
    f = pd.read_parquet(SOURCE, columns=columns, filters=filters).reset_index(drop=True)
    f['role'] = f.split.map({'train':'fit2021_22','cal':'fit2023','dev':'fit2024',
        'reserved2025':'calibration2025','external2026':'retrospective2026'})
    if f.role.isna().any():
        raise ValueError('Unrecognized original split; never silently change roles')
    return f


def fit_mask(frame, window):
    roles = ['fit2021_22'] if window=='short' else ['fit2021_22','fit2023','fit2024']
    if window not in ('short','long'):
        raise ValueError('Unknown training window')
    mask = frame.role.isin(roles).to_numpy()
    if mask.any() and frame.loc[mask,'target_end_utc'].dt.tz_convert('Asia/Ho_Chi_Minh').dt.year.max() > (2022 if window=='short' else 2024):
        raise ValueError('Future label entered model-weight fitting')
    return mask


def cv_masks(frame, fold):
    start = pd.Timestamp(fold['start'],tz='Asia/Ho_Chi_Minh').tz_convert('UTC')
    end = pd.Timestamp(fold['end'],tz='Asia/Ho_Chi_Minh').tz_convert('UTC')
    last = frame.issue_utc + pd.Timedelta(hours=72)
    train = frame.role.eq('fit2021_22') & (last <= start-pd.Timedelta(days=7))
    valid = frame.role.eq('fit2021_22') & (frame.issue_utc>=start) & (last<end)
    valid &= frame.station_id.isin(frame.loc[train,'station_id'].unique())
    if not train.any() or not valid.any():
        raise ValueError('Empty chronological CV fold')
    return train.to_numpy(), valid.to_numpy()


def macro_rmse(y, pred, stations):
    codes = pd.factorize(np.asarray(stations))[0]
    n = np.bincount(codes)
    mse = np.bincount(codes,weights=(np.asarray(pred,dtype=float)-np.asarray(y,dtype=float))**2)/n
    return float(np.sqrt(mse).mean())


def calibration_masks(frame, quarter):
    cal = frame.role.eq('calibration2025').to_numpy()
    start = pd.Timestamp(year=2025,month=3*(quarter-1)+1,day=1,tz='Asia/Ho_Chi_Minh').tz_convert('UTC')
    end = start + pd.DateOffset(months=3)
    hold = cal & (frame.issue_utc>=start).to_numpy() & (frame.issue_utc<end).to_numpy()
    fit = cal & ((frame.issue_utc<start-pd.Timedelta(days=7)) |
                 (frame.issue_utc>=end+pd.Timedelta(days=7))).to_numpy()
    return fit, hold


def calibrate(frame, wet_by_seed, conditional_by_seed):
    """2025-only auxiliary adjustment; outputs only calibration rows, no retrospective labels."""
    cal = frame.role.eq('calibration2025').to_numpy()
    if not cal.all():
        raise ValueError('Calibrator input must consist exclusively of2025 calibration rows')
    y = frame.y_mm.to_numpy()
    final, oofs, pairs = [], [], []
    for wet, conditional in zip(wet_by_seed,conditional_by_seed):
        a = Platt().fit(wet,y>=1)
        b = Platt().fit(np.asarray(conditional)[y>=1],y[y>=1]>=50)
        pairs.append((a,b))
        final.append(nested_probabilities(a.predict(wet),b.predict(conditional)))
        oof = np.full((len(frame),2),np.nan)
        for quarter in range(1,5):
            fit, hold = calibration_masks(frame,quarter)
            c = Platt().fit(np.asarray(wet)[fit],y[fit]>=1)
            d = Platt().fit(np.asarray(conditional)[fit & (y>=1)],y[fit & (y>=1)]>=50)
            oof[hold] = nested_probabilities(c.predict(np.asarray(wet)[hold]),d.predict(np.asarray(conditional)[hold]))
        if not np.isfinite(oof).all():
            raise ValueError('Missing cross-fitted2025 calibration probabilities')
        oofs.append(oof)
    cross = np.mean(oofs,axis=0)
    scores = []
    for cutoff in protocol()['probability']['cutoff_grid']:
        score = float(np.mean([macro_csi(y>=t,cross[:,j],frame.station_id,cutoff) for j,t in enumerate((1,50))]))
        scores.append(dict(cutoff=cutoff,score=score))
    cutoff = max(scores,key=lambda r:(r['score'],-abs(r['cutoff']-.5),r['cutoff']))['cutoff']
    return dict(pairs=pairs, cutoff=cutoff, grid=scores, calibration_rows=len(frame), calibration_year=2025), np.mean(final,axis=0), cross


def apply_calibration(artifact, raw):
    result = []
    for a,(wet,conditional) in zip(artifact['pairs'],raw):
        result.append(nested_probabilities(a[0].predict(wet),a[1].predict(conditional)))
    return np.mean(result,axis=0)


def assert_dependencies(lock):
    if sha(SOURCE)!=lock['dataset_sha256'] or sha(PUBLIC/'protocol.json')!=lock['protocol_sha256']:
        raise ValueError('Frozen dataset/protocol changed')
    for rel,digest in lock['code'].items():
        if sha(ROOT/rel)!=digest:
            raise ValueError('Locked code changed: '+rel)
