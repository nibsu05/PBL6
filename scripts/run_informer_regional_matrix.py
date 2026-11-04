"""Finish Informer E1-E6 with the frozen pilot fit; reuse its E0/E7 artifacts."""
from pathlib import Path
import copy
import hashlib
import itertools
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import torch
from scripts import pilot_informer_regional as pilot
from scripts.pilot_short_range import dump
from src.short_range_dataset import load_development, feature_groups, fit_climatology, predict_climatology, file_hash, SOURCE
from src.short_range_evaluation import fit_calibration, apply_calibration, prediction_frame, score_predictions
from src.short_range_ablation import seed_mean, ensemble_thresholds

REPORT = ROOT / 'reports/informer_regional_matrix_2026_10_28'
PRIVATE = ROOT / 'data/operational/short_range/informer_matrix_2026_10_28'
PILOT_REPORT = ROOT / 'reports/informer_regional_pilot_2026_10_21'
PILOT_PRIVATE = ROOT / 'data/operational/short_range/informer_pilot_2026_10_21'
MATRIX_REPORT = ROOT / 'reports/short_range_ablation_2026_10_21'
MATRIX_PRIVATE = ROOT / 'data/operational/short_range/ablation_2026_10_21'
EXPERIMENTS = [f'E{i}' for i in range(8)]
NEW_EXPERIMENTS = [f'E{i}' for i in range(1, 7)]
SEEDS = [42, 43, 44]
YEARS = [2021, 2022, 2023]


def artifact_root(meta):
    return PILOT_PRIVATE if meta['artifact_origin'] == 'pilot_2026_10_21' else PRIVATE


def verify_frozen_sources():
    old = json.loads((PILOT_REPORT / 'run.json').read_text(encoding='utf8'))
    provenance = json.loads((PILOT_REPORT / 'code_provenance.json').read_text(encoding='utf8'))
    assert old['status'] == 'complete' and len(old['models']) == 18
    for path, digest in old['protocol']['code_sha256'].items():
        content = (ROOT / path).read_bytes()
        canonical = hashlib.sha256(content.replace(b'\r\n', b'\n')).hexdigest()
        assert file_hash(ROOT / path) == digest or canonical == provenance['files'][path]['normalized_lf_sha256'], path
    assert file_hash(SOURCE) == old['protocol']['source_sha256'], 'V1 changed'
    matrix = json.loads((MATRIX_REPORT / 'run.json').read_text(encoding='utf8'))
    for path, digest in matrix['code_hashes'].items(): assert file_hash(ROOT / path) == digest, path
    return old


def collect_scores(manifest):
    ensemble, seed_frames, threshold_rows = [], [], []
    for year, exp in itertools.product(YEARS, EXPERIMENTS):
        entries = [m for m in manifest['models'] if m['year'] == year and m['experiment'] == exp]
        assert sorted(m['seed'] for m in entries) == SEEDS
        cal = [pd.read_parquet(artifact_root(m) / m['cal_predictions']) for m in entries]
        ev = [pd.read_parquet(artifact_root(m) / m['eval_predictions']) for m in entries]
        cal_mean = seed_mean(cal, tuple(SEEDS)); ev_mean = seed_mean(ev, tuple(SEEDS))
        ev_mean, thresholds = ensemble_thresholds(cal_mean, ev_mean)
        threshold_rows.extend([dict(model='informer', year=year, experiment=exp, **r) for r in thresholds])
        ensemble.append(ev_mean); seed_frames.extend(ev)
    informer = pd.concat(ensemble, ignore_index=True)
    old = pd.read_parquet(MATRIX_PRIVATE / 'predictions_ensemble.parquet')
    assert set(old.year) == set(YEARS) and set(informer.year) == set(YEARS)
    old = old[old.model.isin(['lgbm', 'tft'])].copy()
    combined = pd.concat([old, informer], ignore_index=True)
    for exp, day in itertools.product(EXPERIMENTS, [1, 2, 3]):
        parts = [combined[(combined.model == model) & (combined.experiment == exp) & (combined.lead_day == day)].sort_values('issue')
                 for model in ['lgbm', 'tft', 'informer']]
        for p in parts: assert len(p) == 1075 and not p.issue.duplicated().any()
        for p in parts[1:]:
            for key in ['issue', 'obs', 'ref16', 'ref50', 'ref100']:
                np.testing.assert_array_equal(p[key].to_numpy(), parts[0][key].to_numpy())
    combined.to_parquet(PRIVATE / 'predictions_ensemble.parquet', index=False)
    pd.concat(seed_frames, ignore_index=True).to_parquet(PRIVATE / 'predictions_seed.parquet', index=False)
    score_predictions(combined).to_csv(REPORT / 'scores_ensemble.csv', index=False, lineterminator='\n')
    pooled = combined.copy(); pooled['year'] = 'pooled2021-2023'
    scored = score_predictions(pooled)
    scored.to_csv(REPORT / 'scores_ensemble_pooled.csv', index=False, lineterminator='\n')
    per_seed = pd.concat(seed_frames, ignore_index=True); per_seed['year'] = 'pooled2021-2023'
    scored_seed = score_predictions(per_seed)
    scored_seed.to_csv(REPORT / 'scores_seed_pooled.csv', index=False, lineterminator='\n')
    pd.DataFrame(threshold_rows).to_csv(REPORT / 'ensemble_calibration_thresholds.csv', index=False, lineterminator='\n')
    stability = scored_seed.groupby(['experiment', 'lead_day', 'season', 'threshold_mm'])[['RMSE', 'BSS', 'CSI', 'POD', 'FAR']].agg(['mean', 'std', 'min', 'max'])
    stability.columns = ['_'.join(c) for c in stability.columns]
    stability.reset_index().to_csv(REPORT / 'seed_stability.csv', index=False, lineterminator='\n')
    # The 18 reused runs must preserve their originally published scores exactly.
    previous = pd.read_csv(PILOT_REPORT / 'scores_pooled.csv')
    a = scored[(scored.model == 'informer') & scored.experiment.isin(['E0', 'E7'])].reset_index(drop=True)
    b = previous[previous.model == 'informer'].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b, check_dtype=False, rtol=1e-12, atol=1e-12)
    original = pd.read_csv(MATRIX_REPORT / 'scores_ensemble_pooled.csv')
    a = scored[scored.model.isin(['lgbm', 'tft'])].reset_index(drop=True)
    b = original[original.model.isin(['lgbm', 'tft'])].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b, check_dtype=False, rtol=1e-12, atol=1e-12)
    manifest.update(ensemble_score_rows=len(scored), evaluation_issues_per_lead=1075,
                    reused_pilot_scores_unchanged=True, tft_lgbm_scores_unchanged=True,
                    ensemble_predictions_sha256=file_hash(PRIVATE / 'predictions_ensemble.parquet'))


def main():
    REPORT.mkdir(parents=True, exist_ok=True); PRIVATE.mkdir(parents=True, exist_ok=True)
    old = verify_frozen_sources()
    protocol = dict(scope='Complete Informer E0-E7 development matrix; frozen fit inherited from pilot',
        user_authorization_date='2026-10-28', frozen_before_extension_fits=True,
        base_protocol=old['protocol'], base_protocol_sha256=file_hash(PILOT_REPORT / 'protocol_frozen.json'),
        experiments=EXPERIMENTS, new_experiments=NEW_EXPERIMENTS, seeds=SEEDS, evaluation_years=YEARS,
        expected_new_runs=54, expected_reused_runs=18, expected_total_informer_runs=72,
        fit_function='scripts.pilot_informer_regional.fit (unchanged)', no_hyperparameter_tuning=True,
        comparison='LightGBM/TFT/Informer, same issue/target/reference/split/threshold procedure',
        exploratory_bootstrap=dict(repeats=20000, block_days=[7,14], seed=20261021,
            architecture_scope='Three model pairs x three days at E7; BSS16, RMSE and CSI16, descriptive 95% CIs',
            feature_scope='Each model Ei-E0, i=1..7; descriptive 95% CIs; previous TFT primary family remains separate',
            confirmatory=False, reason='Development years and pilot E0/E7 already inspected'),
        test2025_read=False, source_sha256=file_hash(SOURCE),
        extension_runner_sha256=file_hash(__file__))
    frozen = REPORT / 'protocol_frozen.json'
    if frozen.exists(): assert json.loads(frozen.read_text(encoding='utf8')) == protocol
    else: dump(frozen, protocol)
    torch.set_num_threads(4)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    data = load_development(); groups = feature_groups()
    assert len(data.dates) == 3248 and data.dates.max().year == 2023
    if (REPORT / 'run.json').exists():
        manifest = json.loads((REPORT / 'run.json').read_text(encoding='utf8'))
        assert manifest['protocol'] == protocol and manifest['device'] == device
    else:
        entries = []
        for meta in old['models']:
            meta = copy.deepcopy(meta); meta['artifact_origin'] = 'pilot_2026_10_21'; entries.append(meta)
        manifest = dict(status='running', protocol=protocol, models=entries, test2025_read=False,
                        device=device, gpu=torch.cuda.get_device_name(0) if device == 'cuda' else None,
                        torch_version=torch.__version__, new_fits_seconds=0., invocation_seconds=0.)
    # fit() is reused verbatim; only its output directory is redirected.
    pilot.PRIVATE = PRIVATE
    start = time.perf_counter(); already = {(m['seed'], m['year'], m['experiment']) for m in manifest['models']}
    for seed, year, exp in itertools.product(SEEDS, YEARS, NEW_EXPERIMENTS):
        if (seed, year, exp) in already: continue
        tag = f'informer_{year}_{exp}_seed{seed}'
        train = data.dates.year < year-1; cal = data.dates.year == year-1; ev = data.dates.year == year
        climate = fit_climatology(data.dates[train], data.y[train])
        _, rc = predict_climatology(data.dates[cal], climate); _, re = predict_climatology(data.dates[ev], climate)
        print('START', tag, f'new={len(manifest["models"])-18}/54', flush=True)
        ac, ae, pc, pe, meta = pilot.fit(data.select(groups[exp]), train, cal, ev, tag, seed, device)
        params = fit_calibration(data.y[cal], pc)
        cf = prediction_frame(data.dates[cal], data.y[cal], ac, apply_calibration(pc, params), rc, params, 'informer', exp, year, seed)
        ef = prediction_frame(data.dates[ev], data.y[ev], ae, apply_calibration(pe, params), re, params, 'informer', exp, year, seed)
        cf.to_parquet(PRIVATE / (tag+'_cal.parquet'), index=False); ef.to_parquet(PRIVATE / (tag+'_eval.parquet'), index=False)
        meta.update(year=year, experiment=exp, artifact_origin='matrix_2026_10_28',
                    n_train=int(train.sum()), n_cal=int(cal.sum()), n_eval=int(ev.sum()), calibration=params,
                    cal_predictions=tag+'_cal.parquet', eval_predictions=tag+'_eval.parquet',
                    cal_predictions_sha256=file_hash(PRIVATE / (tag+'_cal.parquet')),
                    eval_predictions_sha256=file_hash(PRIVATE / (tag+'_eval.parquet')))
        manifest['models'].append(meta); manifest['new_fits_seconds'] += meta['seconds']
        dump(REPORT / 'run.json', manifest)
        print('DONE', tag, f'{meta["seconds"]:.2f}s', f'new={len(manifest["models"])-18}/54', flush=True)
    assert len(manifest['models']) == 72
    assert {(m['seed'], m['year'], m['experiment']) for m in manifest['models']} == set(itertools.product(SEEDS, YEARS, EXPERIMENTS))
    collect_scores(manifest)
    manifest.update(status='complete', completed_seeds=SEEDS, reused_runs=18, new_runs=54,
                    invocation_seconds=manifest.get('invocation_seconds',0.) + time.perf_counter()-start)
    dump(REPORT / 'run.json', manifest)
    print('INFORMER_MATRIX_COMPLETE', manifest['new_runs'], 'new;', len(manifest['models']), 'total;',
          round(manifest['new_fits_seconds'], 2), 'fitting seconds', flush=True)


if __name__ == '__main__': main()
