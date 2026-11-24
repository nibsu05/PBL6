"""Apply the rain-weighted amount only when the unweighted forecast already indicates rain."""

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from scripts.run_gfs_window import check_freeze
from scripts.run_gfs_weighted_amount import (
    BASELINE, BASELINE_REPORT, INPUTS, RMSE_GUARD, DRY_BIAS_GUARD, amount_metrics,
    fit_scores, model_for, uncertainty,
)
from src.gfs_window import FOLDS, SEEDS, cv_masks, fit_mask, load_frame, read_json, save_csv, save_parquet, sha, write_json
from src.gfs_window_models import save_model


NAME = 'gfs_gated_amount_2026_11_24'
PUBLIC = ROOT / 'reports' / NAME
PRIVATE = ROOT / 'data' / 'operational' / NAME
GATES_MM = (5., 10., 20.)
RAMP_MM = 20.


def gated(b, w, threshold):
    strength = np.clip((b - threshold) / RAMP_MM, 0, 1)
    return b + strength * np.maximum(w - b, 0.)


def select_gate(training, settings):
    rows = []
    for horizon, f in training.groupby('horizon'):
        for quarter, fold in enumerate(FOLDS, start=1):
            train, valid = cv_masks(f, fold)
            val = f[valid]
            p0, p1 = [np.maximum(model_for(f, train, alpha, horizon, 17, settings).predict(val[INPUTS]), 0.)
                      for alpha in (0., 1.)]
            for config, predicted in [('base', p0)] + [(str(t), gated(p0, p1, t)) for t in GATES_MM]:
                rows.append(dict(horizon=int(horizon), fold=quarter, config=config, **fit_scores(val, predicted)))
        print(f'Checked gated fits in ordered 2022 folds, horizon {horizon}', flush=True)
    cv = pd.DataFrame(rows)
    save_csv(cv, PUBLIC / 'train_only_cv.csv')
    scores = cv.groupby('config')[['macro_rmse','heavy_mae','heavy_bias','dry_bias']].mean()
    ref = scores.loc['base']
    eligible = scores.macro_rmse.le(ref.macro_rmse + RMSE_GUARD) & scores.dry_bias.le(ref.dry_bias + DRY_BIAS_GUARD)
    choice = scores[eligible].sort_values(['heavy_mae', 'macro_rmse']).index[0]
    table = scores.assign(eligible=eligible, selected=scores.index == choice).reset_index()
    save_csv(table, PUBLIC / 'train_only_selection.csv')
    print(table.to_string(index=False), flush=True)
    return choice


def main():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    if (PRIVATE / 'model_freeze.json').exists():
        raise FileExistsError('Use a new experiment version to refit')
    check_freeze()
    settings = read_json(BASELINE_REPORT / 'selection.json')
    write_json(PUBLIC / 'protocol.json', dict(
        choice_predeclared_utc=datetime.now(timezone.utc).isoformat(),
        reference='LightGBM B', motivation='reduce overprediction on dry cases introduced by global high-rain weights',
        formula='B + clip((B - threshold_mm) / 20, 0, 1) * max(weighted_amount - B, 0)',
        weighted_tree_alpha=1., threshold_candidates_mm=list(GATES_MM), ramp_mm=RAMP_MM,
        selection='ordered 2022 folds; minimum >=50mm MAE among configurations passing both guards',
        increase_guards_mm=dict(macro_rmse=RMSE_GUARD, dry_bias=DRY_BIAS_GUARD),
        fit_years=[2021, 2024], evaluation='matched already-viewed modern 2026', probabilities_unchanged=True,
        amount_is_a_risk_oriented_adjustment=True, may_change_forecast_default=False,
        baseline_freeze_sha256=sha(BASELINE / 'model_freeze.json'), builder_sha256=sha(Path(__file__)),
    ))
    training = load_frame(training_only=True)
    training = training[fit_mask(training,'long')].reset_index(drop=True)
    choice = select_gate(training, settings)
    models = {}
    if choice != 'base':
        for h, f in training.groupby('horizon'):
            if len(f) != 72886:
                raise ValueError('Cannot compare different training rows')
            models[h] = [model_for(f, np.ones(len(f), bool), 1., h, seed, settings) for seed in SEEDS]
            for seed, model in zip(SEEDS, models[h]):
                save_model(PRIVATE / f'weighted_d{h}_s{seed}.joblib', model)
    write_json(PRIVATE / 'model_freeze.json', dict(choice=choice, protocol_sha256=sha(PUBLIC/'protocol.json'),
              artifacts={p.name:sha(p) for p in PRIVATE.glob('*.joblib')}))
    if choice == 'base':
        write_json(PUBLIC/'verification.json', dict(status='base_selected_in_training_cv', choice=choice,
                   candidate_evaluated=False, selection_used_2022_only=True))
        return
    source = BASELINE/'predictions_private.parquet'
    if sha(source) != read_json(BASELINE/'scoring_complete.json')['predictions_sha256']:
        raise ValueError('Baseline forecast mismatch')
    frame = pd.read_parquet(source, filters=[('evaluation_set','==','retrospective2026_modern')])
    rows, paired = [], []
    for h, part in frame.groupby('horizon'):
        b = part.B_mean.to_numpy()
        w = np.maximum([m.predict(part[INPUTS]) for m in models[h]], 0.).mean(0)
        p = gated(b, w, float(choice))
        np.testing.assert_array_equal(p[b <= float(choice)], b[b <= float(choice)])
        frame.loc[part.index, 'adjusted_mm'] = p
        for name, values in [('B',b), ('B_gated',p)]:
            rows.extend(dict(horizon=int(h), **item) for item in amount_metrics(part, values, name))
        paired.append(dict(horizon=int(h), changed=int((p != b).sum()), **uncertainty(part, p)))
    save_csv(pd.DataFrame(rows), PUBLIC/'amount_metrics.csv')
    save_csv(pd.DataFrame(paired), PUBLIC/'paired_comparisons.csv')
    save_parquet(frame[['station_id','issue_utc','horizon','y_mm','B_mean','adjusted_mm']], PRIVATE/'predictions_private.parquet')
    check_freeze()
    write_json(PUBLIC/'verification.json', dict(status='passed', choice=choice, candidate_evaluated=True,
               selection_used_2022_only=True, evaluation_rows=len(frame), treesets=9, probabilities_unchanged=True))
    print(pd.DataFrame(paired).to_string(index=False), flush=True)


if __name__ == '__main__':
    main()
