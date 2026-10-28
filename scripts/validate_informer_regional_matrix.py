"""Independently replay all 72 Informers and reconstruct calibration and scores."""
from pathlib import Path
import itertools
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import torch
from scripts.run_informer_regional_matrix import (REPORT, PRIVATE, PILOT_REPORT, MATRIX_PRIVATE, MATRIX_REPORT,
    EXPERIMENTS, SEEDS, YEARS, artifact_root, verify_frozen_sources)
from scripts.pilot_short_range import network_predict, dump
from src.informer_regional_pilot import RegionalInformer
from src.short_range_dataset import load_development, feature_groups, train_scaler, scale_inputs, file_hash, fit_climatology, predict_climatology
from src.short_range_evaluation import apply_calibration, fit_calibration, score_predictions
from src.short_range_ablation import seed_mean, ensemble_thresholds


def main():
    tick = time.perf_counter(); verify_frozen_sources()
    run = json.loads((REPORT / 'run.json').read_text(encoding='utf8'))
    old_evaluation = json.loads((MATRIX_REPORT / 'evaluation.json').read_text(encoding='utf8'))
    for path, digest in old_evaluation['evaluation_code_hashes'].items(): assert file_hash(ROOT / path) == digest, path
    assert run['status'] == 'complete' and run['new_runs'] == 54 and run['reused_runs'] == 18
    assert {(m['seed'], m['year'], m['experiment']) for m in run['models']} == set(itertools.product(SEEDS, YEARS, EXPERIMENTS))
    assert file_hash(ROOT / 'scripts/run_informer_regional_matrix.py') == run['protocol']['extension_runner_sha256']
    torch.set_num_threads(4); device = 'cuda' if torch.cuda.is_available() else 'cpu'
    data = load_development(); groups = feature_groups(); details = []
    for i, meta in enumerate(run['models'], 1):
        directory = artifact_root(meta); path = directory / meta['checkpoint']
        assert file_hash(path) == meta['checkpoint_sha256']
        ck = torch.load(path, map_location='cpu', weights_only=True)
        assert ck['features'] == groups[meta['experiment']] and ck['seed'] == meta['seed']
        samples = data.select(groups[meta['experiment']]); train = data.dates.year < meta['year']-1
        scaler = {k: v.numpy() for k, v in ck['scaler'].items()}
        expected = train_scaler(samples.x[train])
        for key in scaler: np.testing.assert_array_equal(scaler[key], expected[key])
        x = scale_inputs(samples.x, scaler)
        model = RegionalInformer(**ck['config']).to(device); model.load_state_dict(ck['state'])
        climate = fit_climatology(data.dates[train], data.y[train])
        calibration_mask = data.dates.year == meta['year']-1
        raw_cal = network_predict(model, x[calibration_mask], samples.future[calibration_mask], device)[1]
        recalculated = fit_calibration(data.y[calibration_mask], raw_cal)
        for a, b in zip(recalculated, meta['calibration']):
            assert a.keys() == b.keys()
            for key in a:
                if isinstance(a[key], (int, float, np.number)): np.testing.assert_allclose(a[key], b[key], rtol=2e-5, atol=2e-6)
                else: assert a[key] == b[key]
        best = min(meta['history'], key=lambda r: r['cal_BS16'])
        assert best['epoch'] == meta['best_epoch']
        actual_bs = np.mean((raw_cal[:, :, 0] - (samples.y[calibration_mask] >= 16))**2)
        np.testing.assert_allclose(actual_bs, meta['best_cal_BS16'], rtol=1e-5, atol=1e-7)
        for split, year, key in [('cal', meta['year']-1, 'cal_predictions'), ('eval', meta['year'], 'eval_predictions')]:
            mask = data.dates.year == year
            amount, probability = network_predict(model, x[mask], samples.future[mask], device)
            probability = apply_calibration(probability, meta['calibration'])
            saved = pd.read_parquet(directory / meta[key]); _, reference = predict_climatology(data.dates[mask], climate)
            if key + '_sha256' in meta: assert file_hash(directory / meta[key]) == meta[key + '_sha256']
            for day in [1, 2, 3]:
                part = saved[saved.lead_day == day]
                assert part.issue.tolist() == data.dates[mask].tolist()
                np.testing.assert_array_equal(part.obs, samples.y[mask, day-1])
                np.testing.assert_allclose(part.amount, amount[:, day-1], rtol=2e-5, atol=1e-5)
                for j, q in enumerate([16, 50, 100]):
                    np.testing.assert_allclose(part[f'p{q}'], probability[:, day-1, j], rtol=2e-5, atol=1e-6)
                    np.testing.assert_array_equal(part[f'ref{q}'], reference[:, day-1, j])
        details.append(dict(year=meta['year'], experiment=meta['experiment'], seed=meta['seed'],
                            full_cal_eval_replayed=True, train_scaler_reproduced=True, calibration_reproduced=True))
        del model
        if i % 9 == 0: print('REPLAY', i, '/72', flush=True)
    frames = []
    for year, exp in itertools.product(YEARS, EXPERIMENTS):
        entries = [m for m in run['models'] if m['year'] == year and m['experiment'] == exp]
        cal = seed_mean([pd.read_parquet(artifact_root(m) / m['cal_predictions']) for m in entries])
        ev = seed_mean([pd.read_parquet(artifact_root(m) / m['eval_predictions']) for m in entries])
        ev, _ = ensemble_thresholds(cal, ev); frames.append(ev)
    old = pd.read_parquet(MATRIX_PRIVATE / 'predictions_ensemble.parquet')
    frames.insert(0, old[old.model.isin(['lgbm', 'tft'])])
    expected = pd.concat(frames, ignore_index=True)
    saved = pd.read_parquet(PRIVATE / 'predictions_ensemble.parquet')
    pd.testing.assert_frame_equal(saved, expected, check_dtype=False, rtol=1e-12, atol=1e-12)
    assert set(saved.year) == set(YEARS) and len(saved) == 3 * 8 * 3 * 1075
    for filename, frame in [('scores_ensemble.csv', expected), ('scores_ensemble_pooled.csv', expected.assign(year='pooled2021-2023'))]:
        pd.testing.assert_frame_equal(score_predictions(frame), pd.read_csv(REPORT / filename), check_dtype=False, rtol=1e-12, atol=1e-12)
    scored = pd.read_csv(REPORT / 'scores_ensemble_pooled.csv')
    prior = pd.read_csv(PILOT_REPORT / 'scores_pooled.csv')
    pd.testing.assert_frame_equal(scored[(scored.model=='informer') & scored.experiment.isin(['E0','E7'])].reset_index(drop=True),
                                  prior[prior.model=='informer'].reset_index(drop=True), check_dtype=False, rtol=1e-12, atol=1e-12)
    prior = pd.read_csv(MATRIX_REPORT / 'scores_ensemble_pooled.csv')
    pd.testing.assert_frame_equal(scored[scored.model.isin(['lgbm','tft'])].reset_index(drop=True),
                                  prior[prior.model.isin(['lgbm','tft'])].reset_index(drop=True), check_dtype=False, rtol=1e-12, atol=1e-12)
    result = dict(status='passed', informer_checkpoints_replayed=72, calibration_evaluation_splits=144,
                  train_scalers_reproduced=72, calibration_reproduced=72, ensemble_reconstructed=True,
                  old_e0_e7_unchanged=True, tft_lgbm_unchanged=True, scores_reproduced=True,
                  test2025_read=False, seconds=time.perf_counter()-tick, validator_sha256=file_hash(__file__), results=details)
    dump(REPORT / 'validation.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'results'}, indent=2))


if __name__ == '__main__': main()
