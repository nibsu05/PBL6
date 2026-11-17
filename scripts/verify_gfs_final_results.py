"""Independent metric/CI replay and frozen inference checks after final scoring."""
from pathlib import Path
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from src.gfs_final import BASE, PUBLIC, protocol, model_names, unchanged, progress, SEEDS
from src.gfs_daily import sha, write_json
from src.gfs_final_gate import check_manifest
from src.gfs_final_inference import predict_all, cutoffs
from src.gfs_daily_evaluation import block_draw_counts
from scripts.score_gfs_final import load_holdout_examples


def equal(a, b, tol=1e-10):
    np.testing.assert_allclose(a, b, rtol=tol, atol=tol, equal_nan=True)


def macro(values, codes, root=False):
    means = np.bincount(codes, weights=np.asarray(values))/np.bincount(codes)
    return float(np.sqrt(means).mean() if root else means.mean())


def main():
    threadpool_limits(limits=4)
    p = protocol()
    check_manifest()
    manifest = json.loads((PUBLIC / "final_manifest.json").read_text())
    opening = json.loads((BASE / "holdout_opened.json").read_text())
    assert pd.Timestamp(opening["first_model_evaluation_opened_utc"]) >= pd.Timestamp(manifest["locked_utc"])
    source = load_holdout_examples()
    holdout = pd.read_parquet(BASE / "holdout_predictions_private.parquet")
    pd.testing.assert_frame_equal(holdout[source.columns], source)
    cache = json.loads((BASE / "holdout_prediction_manifest.json").read_text())
    assert cache["sha256"] == sha(BASE / "holdout_predictions_private.parquet")
    assert cache["seed_outputs_sha256"] == sha(BASE / "holdout_seed_outputs.npz")
    dev = pd.read_parquet(BASE / "development_predictions_private.parquet")
    dev = dev.loc[dev.split.eq("dev")].copy()
    dev["evaluation_set"] = "dev2024_legacy"
    frame = pd.concat([dev, holdout], ignore_index=True)
    parts = {(scope, int(h)): s for (scope, h), s in frame.groupby(["evaluation_set", "horizon"])}
    point = pd.read_csv(PUBLIC / "point_metrics.csv")
    checks = 0
    for r in point.itertuples():
        f = parts[(r.evaluation_set, r.horizon)]
        code = pd.factorize(f.station_id, sort=True)[0]
        error = f[r.model+"_"+r.functional].to_numpy()-f.y_mm.to_numpy()
        equal([macro(abs(error), code), macro(error**2, code, True), macro(error, code)],
              [r.macro_mae, r.macro_rmse, r.macro_bias])
        equal([abs(error).mean(), np.sqrt((error**2).mean()), error.mean()], [r.micro_mae, r.micro_rmse, r.micro_bias])
        assert len(f) == r.n and len(np.unique(code)) == r.stations
        checks += 8
    for r in pd.read_csv(PUBLIC / "probability_metrics.csv").itertuples():
        f = parts[(r.evaluation_set, r.horizon)]
        codes = pd.factorize(f.station_id, sort=True)[0]
        n = np.bincount(codes)
        label = f.y_mm.to_numpy() >= r.threshold_mm
        errors = (f[f"{r.model}_p{r.threshold_mm}"].to_numpy()-label)**2
        ref = (f[f"CLIM_p{r.threshold_mm}"].to_numpy()-label)**2
        bs = np.bincount(codes, weights=errors)/n
        ref_bs = np.bincount(codes, weights=ref)/n
        skill = 1-bs/np.where(ref_bs > 0, ref_bs, np.nan)
        equal([bs.mean(), np.nanmean(skill), errors.mean(), 1-errors.mean()/ref.mean() if ref.mean() > 0 else np.nan],
              [r.macro_bs, r.macro_bss, r.micro_bs, r.micro_bss])
        checks += 4
    locked_cutoffs = cutoffs()
    for r in pd.read_csv(PUBLIC / "event_metrics.csv").itertuples():
        f = parts[(r.evaluation_set, r.horizon)]
        expected = locked_cutoffs.get((r.model, r.horizon), .5) if r.decision_rule == "calibration_selected" else .5
        equal(r.cutoff, expected)
        codes = pd.factorize(f.station_id, sort=True)[0]
        label = f.y_mm.to_numpy() >= r.threshold_mm
        yes = f[f"{r.model}_p{r.threshold_mm}"].to_numpy() >= r.cutoff
        hit = np.bincount(codes, weights=yes & label)
        miss = np.bincount(codes, weights=~yes & label)
        false = np.bincount(codes, weights=yes & ~label)
        for a, b in [(hit.sum(), r.hits), (miss.sum(), r.misses), (false.sum(), r.false_alarms)]:
            assert int(a) == int(b)
        def ratio(a, b):
            return np.divide(a, b, out=np.full_like(a, np.nan), where=b > 0)
        scores = [np.nanmean(ratio(hit, hit+miss+false)), np.nanmean(ratio(hit, hit+miss)),
                  float(np.nanmean(ratio(false, hit+false))) if (hit+false > 0).any() else np.nan]
        equal(scores, [r.macro_csi, r.macro_pod, r.macro_far])
        checks += 7
    archived = np.load(BASE / "holdout_seed_outputs.npz")
    seed_checks = 0
    for r in pd.read_csv(PUBLIC / "holdout_seed_metrics.csv").itertuples():
        mask = holdout.evaluation_set.eq(r.evaluation_set) & holdout.horizon.eq(r.horizon)
        f = holdout.loc[mask]
        code = pd.factorize(f.station_id, sort=True)[0]
        y = f.y_mm.to_numpy()
        prefix = f"{r.model}__{r.seed}__"
        equal([macro((archived[prefix+"mean"][mask]-y)**2, code, True),
               macro(abs(archived[prefix+"median"][mask]-y), code),
               macro((archived[prefix+"p1"][mask]-(y >= 1))**2, code),
               macro((archived[prefix+"p50"][mask]-(y >= 50))**2, code)],
              [r.mean_rmse, r.median_mae, r.bs1, r.bs50], tol=2e-8)
        seed_checks += 4
    for model in {key.split("__")[0] for key in archived.files}:
        for head in ("mean", "median", "p1", "p50"):
            equal(np.mean([archived[f"{model}__{seed}__{head}"] for seed in SEEDS], axis=0), holdout[model+"_"+head], tol=3e-6)
    # Reconstruct the principal paired CIs using integer day/station indexing,
    # independently of the scoring code's pivot/matrix implementation.
    ci = pd.read_csv(PUBLIC / "paired_bootstrap.csv")
    primary = ci[ci.family.ne("exploratory")]
    ci_checks = 0
    for (scope, h), f in parts.items():
        table = primary[primary.evaluation_set.eq(scope) & primary.horizon.eq(h)]
        dates = pd.date_range(f.issue_utc.min(), f.issue_utc.max(), freq="D")
        day = dates.get_indexer(f.issue_utc)
        codes, stations = pd.factorize(f.station_id, sort=True)
        counts = block_draw_counts(len(dates), p["uncertainty"]["draws"], p["uncertainty"]["block_days"], p["uncertainty"]["seed"])
        valid = np.zeros((len(dates), len(stations)))
        valid[day, codes] = 1
        denominator = counts @ valid
        def values(model, metric):
            error = f[model+("_mean" if metric == "mean_rmse" else "_median")].to_numpy()-f.y_mm.to_numpy()
            loss = error**2 if metric == "mean_rmse" else abs(error)
            matrix = np.zeros_like(valid)
            matrix[day, codes] = loss
            observed = matrix.sum(0)/valid.sum(0)
            with np.errstate(divide="ignore", invalid="ignore"):
                boot = (counts @ matrix)/denominator
            if metric == "mean_rmse":
                observed = np.sqrt(observed)
                boot = np.sqrt(boot)
            return observed.mean(), np.nanmean(boot, axis=1)
        for r in table.itertuples():
            a, boot_a = values(r.model, r.metric)
            b, boot_b = values(r.reference, r.metric)
            distribution = boot_a-boot_b
            distribution = distribution[np.isfinite(distribution)]
            family = r.family_size
            equal([a-b, *np.quantile(distribution, [.025, .975, .025/family, 1-.025/family])],
                [r.difference, r.ci95_low, r.ci95_high, r.simultaneous_ci_low, r.simultaneous_ci_high], tol=2e-9)
            approximate = (1+np.sum(distribution-(a-b) <= a-b))/(len(distribution)+1)
            equal(approximate, r.approximate_p, tol=1/(len(distribution)+1)+1e-7)
            ci_checks += 6
    for _, f in primary.groupby(["evaluation_set", "family"]):
        order = np.argsort(f.approximate_p.to_numpy())
        ranked = f.approximate_p.to_numpy()[order]
        computed = np.minimum(1., np.maximum.accumulate(ranked*(len(ranked)-np.arange(len(ranked)))))
        equal(computed, f.holm_p.to_numpy()[order])
    # Production replay on deterministic date-spanning packs in every source.
    selected = []
    for _, f in holdout.groupby("evaluation_set"):
        packs = f[["issue_utc", "station_id"]].drop_duplicates().reset_index(drop=True)
        keys = packs.iloc[np.unique(np.linspace(0, len(packs)-1, 12).astype(int))]
        selected.append(f.merge(keys, on=["issue_utc", "station_id"], how="inner"))
    sample = pd.concat(selected, ignore_index=True).sort_values(["issue_utc", "station_id", "horizon"]).reset_index(drop=True)
    replayed, _ = predict_all(sample)
    changed = sample.copy()
    changed["y_mm"] = np.arange(len(changed))*10000.
    independent, _ = predict_all(changed)
    for model in model_names():
        for head in ("mean", "median", "p1", "p50"):
            equal(replayed[model+"_"+head], sample[model+"_"+head], tol=3e-5)
            equal(replayed[model+"_"+head], independent[model+"_"+head], tol=3e-5)
    result = dict(status="passed", holdout_rows_checked=len(holdout),
        independent_metric_checks=checks, seed_metric_checks=seed_checks,
        primary_bootstrap_checks=ci_checks, primary_comparisons_reproduced=len(primary),
        production_replay_rows=len(sample), future_label_perturbation_invariant=True,
        final_manifest_verified=True, models_fit_after_opening=0,
        old_artifacts_preserved=unchanged(), holdout_predictions_sha256=sha(BASE / "holdout_predictions_private.parquet"),
        complete_source_frame_reproduced=True, no_source_2026_continuity_claim=True)
    write_json(PUBLIC / "final_verification.json", result)
    summary = json.loads((PUBLIC / "result_summary.json").read_text())
    summary["status"] = "verified_final_test_and_source_separated_external_evaluation"
    write_json(PUBLIC / "result_summary.json", summary)
    progress("verified_pending_publication", **{k: v for k, v in result.items() if k != "status"})
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
