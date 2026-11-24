"""Check a rain-weighted amount head with selection limited to chronological training folds."""

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import lightgbm as lgb
import numpy as np
import pandas as pd

from scripts.run_gfs_window import check_freeze
from src.gfs_daily_evaluation import block_draw_counts
from src.gfs_daily_models import tree_parameters
from src.gfs_window import (
    BASE as BASELINE, PUBLIC as BASELINE_REPORT, FEATURES, FOLDS, SEEDS, cv_masks,
    fit_mask, load_frame, macro_rmse, read_json, save_csv, save_parquet, sha, write_json,
)
from src.gfs_window_models import save_model


NAME = 'gfs_weighted_amount_2026_11_24'
PUBLIC = ROOT / 'reports' / NAME
PRIVATE = ROOT / 'data' / 'operational' / NAME
ALPHAS = (0., .5, 1.)
RMSE_GUARD = .25  # mm, scope is mean across training folds and horizons
DRY_BIAS_GUARD = .5  # mm, allowed increase in signed mean error for observed <1 mm
HORIZONS = (1, 2, 3)
INPUTS = FEATURES['N3']


def model_for(frame, mask, alpha, horizon, seed, selection):
    params = tree_parameters(selection['candidate'], seed, selection['trees'][str(horizon)])
    model = lgb.LGBMRegressor(**params, objective='tweedie', tweedie_variance_power=1.5)
    train = frame[mask]
    y = train.y_mm.to_numpy()
    kwargs = {'categorical_feature': ['station_code']}
    if alpha:
        kwargs['sample_weight'] = 1 + alpha * np.minimum(y / 50., 1.)
    model.fit(train[INPUTS], y, **kwargs)
    return model


def fit_scores(frame, predictions):
    error = predictions - frame.y_mm.to_numpy()
    return dict(
        macro_rmse=macro_rmse(frame.y_mm, predictions, frame.station_id),
        heavy_mae=float(np.mean(abs(error[frame.y_mm.ge(50)]))),
        heavy_bias=float(np.mean(error[frame.y_mm.ge(50)])),
        dry_bias=float(np.mean(error[frame.y_mm.lt(1)])),
    )


def select_alpha(training, selection):
    rows = []
    for horizon, f in training.groupby('horizon'):
        for quarter, fold in enumerate(FOLDS, start=1):
            train, valid = cv_masks(f, fold)
            validation = f[valid]
            if not (validation.y_mm.ge(50).any() and validation.y_mm.lt(1).any()):
                raise ValueError('Insufficient heavy or dry examples in a training-only fold')
            for alpha in ALPHAS:
                model = model_for(f, train, alpha, horizon, 17, selection)
                prediction = np.maximum(model.predict(validation[INPUTS]), 0.)
                rows.append(dict(horizon=int(horizon), fold=quarter, alpha=alpha, **fit_scores(validation, prediction)))
        print(f'Completed training-only selection for horizon {horizon}', flush=True)
    cv = pd.DataFrame(rows)
    save_csv(cv, PUBLIC / 'train_only_cv.csv')
    average = cv.groupby('alpha')[['macro_rmse','heavy_mae','heavy_bias','dry_bias']].mean()
    reference = average.loc[0.]
    eligible = average.macro_rmse.le(reference.macro_rmse + RMSE_GUARD) & average.dry_bias.le(reference.dry_bias + DRY_BIAS_GUARD)
    choice = float(average[eligible].sort_values(['heavy_mae', 'macro_rmse']).index[0])
    summary = average.assign(eligible=eligible, selected=average.index == choice).reset_index()
    save_csv(summary, PUBLIC / 'train_only_selection.csv')
    print(summary.to_string(index=False), flush=True)
    return choice


def amount_metrics(frame, predicted, model):
    observed = frame.y_mm.to_numpy()
    error = predicted - observed
    rows = []
    for name, mask in [('all', np.ones(len(frame), bool)), ('under1', observed < 1), ('ge50', observed >= 50)]:
        grouped = pd.DataFrame(dict(station=frame.station_id.to_numpy()[mask], error=error[mask]))
        station = grouped.assign(square=grouped.error**2, absolute=abs(grouped.error)).groupby('station').mean()
        rows.append(dict(model=model, group=name, n=int(mask.sum()), stations=len(station),
                         macro_rmse=float(np.sqrt(station.square).mean()), macro_mae=float(station.absolute.mean()),
                         micro_mae=float(np.mean(abs(error[mask]))), micro_bias=float(np.mean(error[mask]))))
    return rows


def uncertainty(frame, predicted):
    dates = pd.date_range(frame.issue_utc.min(), frame.issue_utc.max(), freq='D')
    loss = frame.assign(base=(frame.B_mean-frame.y_mm)**2, candidate=(predicted-frame.y_mm)**2)
    arrays = [loss.pivot(index='issue_utc', columns='station_id', values=k).reindex(dates).to_numpy()
              for k in ('base', 'candidate')]
    counts = block_draw_counts(len(dates), draws=5000, block=14, seed=1701)
    valid = np.isfinite(arrays[0])
    np.testing.assert_array_equal(valid, np.isfinite(arrays[1]))
    n = counts @ valid.astype(float)
    if (n == 0).any():
        raise ValueError('Bootstrap lost station support')
    dist = [np.sqrt((counts @ np.nan_to_num(a)) / n).mean(axis=1) for a in arrays]
    delta = dist[1] - dist[0]
    ci = np.quantile(delta, [.025 / len(HORIZONS), 1 - .025 / len(HORIZONS)])
    return dict(difference=float(np.sqrt(np.nanmean(arrays[1], axis=0)).mean() -
                                 np.sqrt(np.nanmean(arrays[0], axis=0)).mean()),
                simultaneous_low=float(ci[0]), simultaneous_high=float(ci[1]), exploratory_improvement=bool(ci[1] < 0.))


def main():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    if (PRIVATE / 'model_freeze.json').exists():
        raise FileExistsError('Retain the frozen weight test; start a new version to refit')
    check_freeze()
    settings = read_json(BASELINE_REPORT / 'selection.json')
    write_json(PUBLIC / 'protocol.json', dict(
        choice_predeclared_utc=datetime.now(timezone.utc).isoformat(), reference='B with 26 input features',
        candidate='Tweedie with mild, capped rain-amount weights', weight='1 + alpha * min(y_mm / 50, 1)',
        alpha_candidates=list(ALPHAS), fit_and_choice='same N3 and tree budgets; select only from ordered 2022 folds',
        rule='minimize heavy-case MAE among eligible settings, including unweighted B',
        allowable_rmse_increase_mm=RMSE_GUARD, allowable_dry_bias_increase_mm=DRY_BIAS_GUARD,
        can_change_forecast_default=False, years_fit=[2021, 2024], calibration_2025_used=False,
        classifier_heads_changed=False, eval='already-viewed modern 2026 retrospective, paired on identical rows',
        uncertainty='5000 paired draws with 14-day blocks, simultaneous 95% interval across 3 horizons',
        baseline_freeze_sha256=sha(BASELINE / 'model_freeze.json'), builder_sha256=sha(Path(__file__)),
    ))
    training = load_frame(training_only=True)
    training = training[fit_mask(training,'long')].reset_index(drop=True)
    alpha = select_alpha(training, settings)
    if alpha == 0:
        write_json(PRIVATE / 'model_freeze.json', dict(alpha=0, protocol_sha256=sha(PUBLIC/'protocol.json'), artifacts={}))
        write_json(PUBLIC / 'verification.json', dict(status='kept_B_in_train_only_selection', alpha=0,
                   candidate_forecast_evaluated=False, no_post_training_selection=True))
        return
    models = {}
    for horizon, f in training.groupby('horizon'):
        if len(f) != 72886:
            raise ValueError('Matched four-year training rows changed')
        models[horizon] = [model_for(f, np.ones(len(f),bool), alpha, horizon, seed, settings) for seed in SEEDS]
        for seed, model in zip(SEEDS, models[horizon]):
            save_model(PRIVATE / f'amount_d{horizon}_s{seed}.joblib', model)
    write_json(PRIVATE / 'model_freeze.json', dict(
        alpha=alpha, protocol_sha256=sha(PUBLIC/'protocol.json'),
        artifacts={p.name:sha(p) for p in PRIVATE.glob('*.joblib')},
    ))
    source = BASELINE / 'predictions_private.parquet'
    if sha(source) != read_json(BASELINE / 'scoring_complete.json')['predictions_sha256']:
        raise ValueError('Frozen forecast supply changed')
    scope = 'retrospective2026_modern'
    subset = pd.read_parquet(source, filters=[('evaluation_set','==',scope)])
    results, comparisons = [], []
    for horizon, model_set in models.items():
        mask = subset.horizon.eq(horizon)
        frame = subset[mask].copy()
        mean = np.maximum([m.predict(frame[INPUTS]) for m in model_set], 0.).mean(axis=0)
        if not np.isfinite(mean).all():
            raise ValueError('Invalid weighted rainfall')
        for name, p in [('B', frame.B_mean.to_numpy()), ('B_weighted', mean)]:
            results.extend(dict(horizon=int(horizon), **score) for score in amount_metrics(frame, p, name))
        comparisons.append(dict(horizon=int(horizon), **uncertainty(frame, mean)))
        subset.loc[mask, 'weighted_amount_mm'] = mean
    save_csv(pd.DataFrame(results), PUBLIC/'amount_metrics.csv')
    save_csv(pd.DataFrame(comparisons), PUBLIC/'paired_comparisons.csv')
    save_parquet(subset[['station_id','issue_utc','horizon','y_mm','B_mean','weighted_amount_mm']], PRIVATE/'predictions_private.parquet')
    check_freeze()
    write_json(PUBLIC/'verification.json', dict(status='passed', alpha=alpha, candidate_forecast_evaluated=True,
               prediction_rows=len(subset), estimators=9, fit_rows_per_horizon=72886, test_2026_already_seen=True,
               selection_used_2022_only=True, forecast_probabilities_untouched=True))
    print(pd.DataFrame(comparisons).to_string(index=False), flush=True)


if __name__ == '__main__':
    main()
