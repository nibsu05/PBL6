"""Frozen development factorial; reuse pilot fitting code, never read >=2024.

Outputs per-run calibration predictions privately so ensemble CSI thresholds can
be selected on calibration predictions, rather than averaged from seed thresholds.
Existing pilot files and its four hashed source modules are left untouched.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import torch

from pilot_short_range import dump, fit_tft, fit_lgbm
from src.short_range_dataset import (load_development, feature_groups, tabular_inputs,
    fit_climatology, predict_climatology, file_hash, SOURCE)
from src.short_range_evaluation import fit_calibration, apply_calibration, prediction_frame, score_predictions

REPORT = ROOT / 'reports/short_range_ablation_2026_10_21'
PRIVATE = ROOT / 'data/operational/short_range/ablation_2026_10_21'
CODE = ['src/short_range_dataset.py', 'src/tft_regional.py', 'src/short_range_evaluation.py',
        'scripts/pilot_short_range.py', 'scripts/run_short_range_matrix.py']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['stability', 'all'], default='all')
    parser.add_argument('--max-minutes', type=float, default=90.)
    args = parser.parse_args()
    REPORT.mkdir(parents=True, exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    data = load_development()
    source_hash = file_hash(SOURCE)
    if source_hash != '92a6bc6a527b25107761e85f0d14e64713a39dfd2930560a4498927c27dfc448':
        raise ValueError('Frozen V1 source changed')
    if len(data.dates) != 3248 or data.dates.max().year != 2023:
        raise ValueError('Unexpected development-only sample universe')
    code_hashes = {p: file_hash(ROOT / p) for p in CODE}
    protocol_path = REPORT / 'protocol_frozen.json'
    protocol = dict(scope='Development factorial on frozen approximate 93-full-cell footprint',
        frozen_before_first_matrix_run=True, seeds=[42,43,44], experiments=list(feature_groups()),
        source_hash=source_hash, code_hashes=code_hashes, years=[2021,2022,2023],
        primary_family='TFT ensemble E1-E0,E2-E0,E3-E0 x3days BSS16, pooled2021-2023',
        primary_family_size=9, simultaneous_confidence=1-.05/9,
        bootstrap_repeats=20000, block_days=7, sensitivity_block_days=14,
        bootstrap_seed=20261021, ensemble='Arithmetic mean of three calibrated probabilities and amounts',
        ensemble_threshold='CSI grid selected from averaged calibration probabilities only; rare fallback0.5',
        region_gate_resolution='Freeze existing 93 full cells and describe as approximate footprint, not administrative polygon',
        administrative_boundary_or_independent_label_validation_complete=False,
        future_era5=False, past_rain=False, max_epochs=40, batch=64, hidden=32, patience=6,
        identical_pilot_fitting_code=True, test2025_read=False, final_holdout_authorized_by_this_run=False,
        limitations=['Development years already explored; not confirmatory independent holdout',
                    'Calibration used for epoch selection and probability fitting',
                    'Bootstrap conditional on fitted ensemble, not all training or label uncertainty',
                    'Approximate regional footprint and retrospective reanalysis; no operational claim'])
    if protocol_path.exists():
        if json.loads(protocol_path.read_text(encoding='utf-8')) != protocol:
            raise ValueError('Frozen protocol/code differs; use a new run directory')
    else:
        dump(protocol_path, protocol)
    groups = feature_groups()
    folds, baselines, references = [], [], {}
    for year in [2021,2022,2023]:
        train = data.dates.year < year-1
        cal, ev = data.dates.year == year-1, data.dates.year == year
        fitted = fit_climatology(data.dates[train], data.y[train])
        ac, pc = predict_climatology(data.dates[cal], fitted)
        ae, pe = predict_climatology(data.dates[ev], fitted)
        references[year] = (pc, pe)
        folds.append(dict(year=year, n_train=int(train.sum()), n_cal=int(cal.sum()), n_eval=int(ev.sum())))
        for name, a, p in [('climatology',ae,pe), ('zero',np.zeros_like(ae),np.zeros_like(pe))]:
            baselines.append(prediction_frame(data.dates[ev], data.y[ev], a, p, pe, [], name, 'BASE', year, 0))
    pd.concat(baselines,ignore_index=True).to_parquet(PRIVATE/'baselines.parquet',index=False)

    # Paired E0/E7 stability first; all remaining factorial runs follow with no tuning.
    jobs = [('tft', year, exp, seed) for seed in [42,43,44]
            for year in [2021,2022,2023] for exp in ['E0','E7']]
    if args.stage == 'all':
        jobs += [('lgbm', year, exp, 42) for year in [2021,2022,2023] for exp in groups]
        jobs += [('tft', year, exp, seed) for seed in [42,43,44] for year in [2021,2022,2023]
                 for exp in ['E1','E2','E3','E4','E5','E6']]
    started = time.perf_counter()
    manifest = dict(status='running', scope=protocol['scope'], stage=args.stage, device=device,
        gpu=torch.cuda.get_device_name(0) if device=='cuda' else None, folds=folds,
        source_hash=source_hash, code_hashes=code_hashes, test2025_read=False, expected_runs=len(jobs),
        models=[], resumed=0, new_runs=0)
    selected_cache, tab_cache = {}, {}
    for learner, year, experiment, seed in jobs:
        tag = f'{learner}_{year}_{experiment}_seed{seed}'
        meta_path = PRIVATE / f'{tag}_metadata.json'
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            for name, expected in meta['artifact_hashes'].items():
                if file_hash(PRIVATE/name) != expected:
                    raise ValueError('Resume artifact checksum differs: '+name)
            manifest['resumed'] += 1
        else:
            if time.perf_counter()-started > args.max_minutes*60:
                manifest['status'] = 'partial_time_budget'
                break
            train = data.dates.year < year-1
            cal, ev = data.dates.year == year-1, data.dates.year == year
            if experiment not in selected_cache:
                selected_cache[experiment] = data.select(groups[experiment])
            selected = selected_cache[experiment]
            print('START', tag, flush=True)
            tick = time.perf_counter()
            if learner == 'tft':
                ac,ae,pc,pe,meta = fit_tft(selected,train,cal,ev,PRIVATE,tag,40,64,seed,device)
            else:
                if experiment not in tab_cache:
                    tab_cache[experiment] = tabular_inputs(selected)
                x,names = tab_cache[experiment]
                ac,ae,pc,pe,meta = fit_lgbm(x,selected.y,train,cal,ev,PRIVATE,tag)
                meta['tabular_features'] = names
            params = fit_calibration(data.y[cal], pc)
            pred_cal = prediction_frame(data.dates[cal], data.y[cal], ac, apply_calibration(pc,params),
                references[year][0], params, learner, experiment, year, seed)
            pred_ev = prediction_frame(data.dates[ev], data.y[ev], ae, apply_calibration(pe,params),
                references[year][1], params, learner, experiment, year, seed)
            paths = [f'{tag}_cal.parquet', f'{tag}_eval.parquet']
            pred_cal.to_parquet(PRIVATE/paths[0],index=False)
            pred_ev.to_parquet(PRIVATE/paths[1],index=False)
            if learner=='tft': paths.append(meta['checkpoint'])
            else: paths += [m['path'] for m in meta['output_models'] if 'path' in m]
            meta.update(learner=learner,year=year,experiment=experiment,seed=seed,
                feature_names=selected.features,calibration=params,seconds=time.perf_counter()-tick,
                eval_predictions=f'{tag}_eval.parquet',cal_predictions=f'{tag}_cal.parquet',
                artifact_hashes={p:file_hash(PRIVATE/p) for p in paths})
            dump(meta_path,meta)
            manifest['new_runs'] += 1
            print('DONE',tag,'seconds',round(meta['seconds'],2),flush=True)
        manifest['models'].append(meta)
        manifest['elapsed_seconds_this_invocation'] = time.perf_counter()-started
        dump(REPORT/'run.json',manifest)
    else:
        manifest['status'] = 'complete'
    manifest['elapsed_seconds_this_invocation'] = time.perf_counter()-started
    manifest['total_fitting_seconds'] = sum(m['seconds'] for m in manifest['models'])
    dump(REPORT/'run.json',manifest)
    predictions = pd.concat(baselines+[pd.read_parquet(PRIVATE/m['eval_predictions'])
                                      for m in manifest['models']],ignore_index=True)
    predictions.to_parquet(PRIVATE/'predictions_seed.parquet',index=False)
    score_predictions(predictions).to_csv(REPORT/'scores_seed.csv',index=False,lineterminator='\n')
    pooled = predictions.copy(); pooled['year'] = 'pooled2021-2023'
    score_predictions(pooled).to_csv(REPORT/'scores_seed_pooled.csv',index=False,lineterminator='\n')
    print('MATRIX',manifest['status'],len(manifest['models']),'runs',flush=True)


if __name__ == '__main__': main()
