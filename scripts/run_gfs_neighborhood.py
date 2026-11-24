"""Matched test of neighboring GFS rainfall, separate from the frozen B study."""

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
import pandas as pd

from scripts.run_gfs_window import check_freeze
from src.gfs_daily_evaluation import block_draw_counts
from src.gfs_daily_models import fit_tree, predict_tree
from src.gfs_final_metrics import summary_tables
from src.gfs_window import (
    BASE as FROZEN, PUBLIC as FROZEN_REPORT, OLD, VRAIN, SOURCE, FEATURES, SEEDS,
    apply_calibration, calibrate, fit_mask, load_frame, read_json, save_csv,
    save_parquet, sha, write_json,
)
from src.gfs_window_models import fit_mean, predict_auxiliary, predict_means, save_model


NAME = 'gfs_neighborhood_2026_11_24'
PUBLIC = ROOT / 'reports' / NAME
PRIVATE = ROOT / 'data' / 'operational' / NAME
RADII_KM = (25, 50)
HORIZONS = (1, 2, 3)
KEYS = ['issue_utc', 'station_id', 'horizon']
EXTRA = [f'gfs_rain_{stat}_{radius}km_mm' for radius in RADII_KM for stat in ('mean', 'max')]
INPUTS = FEATURES['N3'] + EXTRA
SCOPE = 'retrospective2026_modern'
DRAWS = 5000
BLOCK_DAYS = 14


def prepare_features():
    # Only the weather forecast archive supplies neighbor values, including for
    # sites omitted from Vrain-ready samples at a given timestamp.
    keys = pd.read_parquet(SOURCE, columns=KEYS + ['gfs_rain_mm'])
    dates = list(pd.DatetimeIndex(keys.issue_utc.unique()).sort_values())
    sites = pd.read_csv(OLD / 'cohort_private.csv').sort_values('canonical_id')
    ids = sites.canonical_id.tolist()
    if len(ids) != 57 or set(keys.station_id) != set(ids):
        raise ValueError('The experiment requires the frozen 57-site cohort')
    lat, lon = np.radians(sites.latitude), np.radians(sites.longitude)
    lat, lon = lat.to_numpy(), lon.to_numpy()
    hav = np.sin((lat[:, None] - lat) / 2)**2
    hav += np.cos(lat[:, None]) * np.cos(lat) * np.sin((lon[:, None] - lon) / 2)**2
    distance = 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(hav, 0, 1)))
    weather = np.empty((len(dates), len(HORIZONS), len(ids)), dtype=np.float64)
    manifest = {}
    for index, date in enumerate(dates):
        day = date.strftime('%Y%m%d')
        archive = OLD / 'days' if day <= '20241228' else VRAIN / 'gfs' / 'days'
        path = archive / (day + '.npz')
        ledger = read_json(path.with_suffix('.json'))
        digest = sha(path)
        if digest != ledger['sha256'] or len(ledger['messages']) != 19 or pd.Timestamp(ledger['issue_utc']) != date:
            raise ValueError(f'Unverified or misaligned GFS cycle: {day}')
        with np.load(path) as payload:
            order = {sid: i for i, sid in enumerate(payload['station_ids'])}
            weather[index] = payload['rain_day_mm'][:, [order[sid] for sid in ids]]
        manifest[path.relative_to(ROOT).as_posix()] = digest
    if not np.isfinite(weather).all() or (weather < 0).any():
        raise ValueError('Incomplete GFS raster extracts in the fixed cohort')
    table = pd.MultiIndex.from_product([dates, HORIZONS, ids], names=['issue_utc','horizon','station_id']).to_frame(index=False)
    table['check_gfs_rain_mm'] = weather.reshape(-1)
    sizes = {}
    for radius in RADII_KM:
        within = distance <= radius
        sizes[str(radius)] = dict(min=int(within.sum(1).min()), max=int(within.sum(1).max()),
                                  median=float(np.median(within.sum(1))))
        selected = [weather[:, :, members] for members in within]
        for name, aggregate in (('mean', np.mean), ('max', np.max)):
            values = np.stack([aggregate(group, axis=-1) for group in selected], axis=-1)
            table[f'gfs_rain_{name}_{radius}km_mm'] = values.reshape(-1)
    matched = keys.merge(table, on=KEYS, how='left', validate='many_to_one')
    np.testing.assert_allclose(matched.gfs_rain_mm, matched.check_gfs_rain_mm, rtol=0, atol=0)
    if matched[EXTRA].isna().any().any() or len(matched) != len(keys):
        raise ValueError('All original train/calibration/evaluation rows must retain input support')
    write_json(PRIVATE / 'gfs_archives.json', manifest)
    save_parquet(table.drop(columns='check_gfs_rain_mm'), PRIVATE / 'gfs_features_private.parquet')
    return dict(cycles=len(dates), station_radius_counts_include_self=sizes,
                base_rows_preserved=len(keys), fields_verified_per_cycle=19,
                raw_gfs_identical_to_frozen_point_feature=True, uses_neighbor_gauge=False,
                archive_manifest_sha256=sha(PRIVATE / 'gfs_archives.json'))


def join_features(frame, features):
    out = frame.merge(features, on=KEYS, how='left', validate='many_to_one', sort=False)
    if len(out) != len(frame) or not np.isfinite(out[INPUTS].to_numpy()).all():
        raise ValueError('Matched feature matrix incomplete')
    return out


def fit_models(features, selection, aux_params):
    training = join_features(load_frame(training_only=True), features)
    models = PRIVATE / 'models'
    models.mkdir(exist_ok=True)
    final = {}
    for horizon in HORIZONS:
        frame = training[training.horizon.eq(horizon)].reset_index(drop=True)
        train = fit_mask(frame, 'long')
        calibration = frame.loc[frame.role.eq('calibration2025')].reset_index(drop=True)
        if int(train.sum()) != 72886 or len(calibration) != 18723:
            raise ValueError('Year split or matched sample count changed')
        mean_models, aux_models = [], []
        for seed in SEEDS:
            mean = fit_mean(frame, INPUTS, train, None, 'tweedie', selection['candidate'],
                            seed, selection['trees'][str(horizon)])
            mean_models.append(dict(model=mean, features=INPUTS))
            heads = {}
            for head, config in aux_params.items():
                heads[head] = fit_tree(frame, INPUTS, train, None, head, config['candidate'],
                                       seed, config['trees'][str(horizon)])
            aux_models.append(dict(heads=heads, features=INPUTS))
            save_model(models / f'neighbors_d{horizon}_s{seed}.joblib',
                       dict(mean=mean_models[-1], auxiliary=aux_models[-1]))
            print(f'Fitted horizon {horizon}, seed {seed}', flush=True)
        _, raw = predict_auxiliary(aux_models, calibration)
        platt, _, _ = calibrate(calibration, *zip(*raw))
        save_model(models / f'calibration_d{horizon}.joblib', platt)
        final[horizon] = (mean_models, aux_models, platt)
    return final


def paired_bootstrap(frame):
    rows = []
    for horizon, part in frame.groupby('horizon'):
        dates = pd.date_range(part.issue_utc.min(), part.issue_utc.max(), freq='D')
        ids = sorted(part.station_id.unique())
        counts = block_draw_counts(len(dates), draws=DRAWS, block=BLOCK_DAYS, seed=1701)

        def matrix(values):
            return part.assign(error=values).pivot(index='issue_utc', columns='station_id', values='error').reindex(
                index=dates, columns=ids).to_numpy()

        for metric, functional in [('macro_rmse', np.sqrt), ('macro_bs50', lambda x: x)]:
            def losses(model):
                if metric == 'macro_rmse':
                    err = part[f'{model}_mean'].to_numpy() - part.y_mm.to_numpy()
                else:
                    err = part[f'{model}_p50'].to_numpy() - part.y_mm.ge(50).to_numpy()
                return matrix(err ** 2)

            base, new = losses('B'), losses('B_nbr')
            np.testing.assert_array_equal(np.isfinite(base), np.isfinite(new))
            support = counts @ np.isfinite(base).astype(float)
            if (support == 0).any():
                raise ValueError('Bootstrap changed station support')
            scores = [functional(np.nanmean(items, axis=0)).mean() for items in (base, new)]
            boot = [functional((counts @ np.nan_to_num(items)) / support).mean(1) for items in (base, new)]
            differences = boot[1] - boot[0]
            low, high = np.quantile(differences, [.025 / 3, 1 - .025 / 3])
            rows.append(dict(metric=metric, horizon=int(horizon), reference=scores[0], model=scores[1],
                             difference=scores[1] - scores[0], simultaneous_low=low, simultaneous_high=high,
                             exploratory_improvement=bool(high < 0), draws=DRAWS, block_days=BLOCK_DAYS,
                             horizon_family_size=3))
    return pd.DataFrame(rows)


def score(features, models):
    base_file = FROZEN / 'predictions_private.parquet'
    if sha(base_file) != read_json(FROZEN / 'scoring_complete.json')['predictions_sha256']:
        raise ValueError('Frozen predictions changed')
    base = pd.read_parquet(base_file, filters=[('evaluation_set','==',SCOPE)])
    frame = join_features(base, features)
    cutoffs = {('B', int(r.horizon)): float(r.cutoff) for r in
               pd.read_csv(FROZEN_REPORT / 'cutoffs.csv').query("model == 'B'").itertuples()}
    for horizon, (mean_models, aux_models, calibration) in models.items():
        mask = frame.horizon.eq(horizon)
        fitted = frame.loc[mask, INPUTS].copy()
        mean, _ = predict_means(mean_models, fitted)
        median, raw = predict_auxiliary(aux_models, fitted)
        probability = apply_calibration(calibration, raw)
        for suffix, values in [('mean', mean), ('median', median), ('p1', probability[:, 0]), ('p50', probability[:, 1])]:
            frame.loc[mask, 'B_nbr_' + suffix] = values
        cutoffs[('B_nbr', horizon)] = float(calibration['cutoff'])
    if not ((frame.B_nbr_p50 <= frame.B_nbr_p1) & (frame.B_nbr_p50 >= 0) & (frame.B_nbr_p1 <= 1)).all():
        raise ValueError('Non-nested predictions')
    tables = summary_tables(frame, ['B', 'B_nbr'], cutoffs)
    for name, table in tables.items():
        save_csv(table, (PRIVATE if name.endswith('_private') else PUBLIC) / (name + '.csv'))
    comparisons = paired_bootstrap(frame)
    save_csv(comparisons, PUBLIC / 'paired_comparisons.csv')
    save_parquet(frame, PRIVATE / 'predictions_private.parquet')
    print(comparisons[['metric','horizon','reference','model','difference','simultaneous_low','simultaneous_high']].to_string(index=False), flush=True)
    return frame, comparisons


def main():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    if (PRIVATE / 'model_freeze.json').exists():
        raise FileExistsError('This run has frozen outputs; use a new experiment version for another fit')
    check_freeze()
    selection = read_json(FROZEN_REPORT / 'selection.json')
    aux_source = ROOT / 'reports/gfs_station_daily_v2_2026_11_10/tree_selection.json'
    aux_params = {head: read_json(aux_source)['selected'][head] for head in ('median','wet','conditional')}
    inputs = prepare_features()
    features = pd.read_parquet(PRIVATE / 'gfs_features_private.parquet')
    protocol = dict(
        reference='Frozen LightGBM B (26 features)', candidate='B_nbr (30 features)',
        primary_question='Does pre-issue GFS spatial context improve station rainfall?',
        hypothesis='Higher surrounding forecast rain may retain context when GFS rain at the target station is too low',
        extra_features=EXTRA, radius_km=list(RADII_KM),
        weight='equal across the locked cohort inside each radius; includes the target itself',
        feature_source='same-cycle archived GFS interpolates at all 57 fixed locations before Vrain label filtering',
        model_fit='2021–2024 only', probability_calibration='2025 Platt and cutoffs only, same rule as reference',
        evaluation_scope=SCOPE, evaluated_2026_previously=True, choose_default_from_2026=False,
        fixed_mean_loss='tweedie', mean_tree_budget=selection['trees'], seeds=list(SEEDS),
        same_auxiliary_budgets_and_candidate_as_B=True, bootstrap_draws=DRAWS, block_days=BLOCK_DAYS,
        metrics=['macro_rmse','macro_bs50'], intervals='95% Bonferroni percentile within the 3 horizons for each metric',
        exploratory=True, created_before_candidate_fit=datetime.now(timezone.utc).isoformat(),
        source_sha256=sha(SOURCE), frozen_model_sha256=sha(FROZEN / 'model_freeze.json'),
        builder_sha256=sha(Path(__file__)), dataset_audit=inputs,
    )
    write_json(PUBLIC / 'protocol.json', protocol)
    print(f'Checked {inputs["cycles"]} GFS cycles before candidate fitting.', flush=True)
    models = fit_models(features, selection, aux_params)
    freeze = dict(
        protocol_sha256=sha(PUBLIC / 'protocol.json'),
        artifacts={p.name: sha(p) for p in (PRIVATE / 'models').glob('*.joblib')},
        source_features_sha256=sha(PRIVATE / 'gfs_features_private.parquet'),
        candidate_frozen_before_evaluation=True,
    )
    write_json(PRIVATE / 'model_freeze.json', freeze)
    frame, comparisons = score(features, models)
    check_freeze()
    write_json(PUBLIC / 'verification.json', dict(
        status='passed', fit_rows_per_horizon=72886, calibration_rows_per_horizon=18723, evaluated_rows=len(frame),
        stations=frame.station_id.nunique(), issue_dates=frame.issue_utc.nunique(), final_trees_and_classifiers=36,
        artifact_count=len(freeze['artifacts']), old_models_rechecked=True, evaluation_rows_matched=True,
        no_vrain_neighbor_inputs=True, exploratory_improvements=int(comparisons.exploratory_improvement.sum()),
        prediction_sha256=sha(PRIVATE / 'predictions_private.parquet'), **inputs,
    ))


if __name__ == '__main__':
    main()
