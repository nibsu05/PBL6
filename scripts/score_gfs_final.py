"""Open the authorized holdouts only after freeze; score all declared models."""
from pathlib import Path
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from src.gfs_final import BASE, PUBLIC, OLD, EXTENDED, protocol, model_names, progress, unchanged, SEEDS
from src.gfs_daily import sha, write_json
from src.gfs_final_gate import freeze_manifest, check_manifest, record_holdout_opening
from src.gfs_final_inference import predict_all, cutoffs
from src.gfs_final_metrics import summary_tables, bootstrap_comparisons


def seed_scores(frame, values):
    rows = []
    for (scope, h), positions in frame.groupby(["evaluation_set", "horizon"]).groups.items():
        index = np.asarray(list(positions))
        f = frame.iloc[index]
        y = f.y_mm.to_numpy()
        sid = f.station_id.to_numpy()
        def macro(error, root=False):
            means = pd.Series(error).groupby(sid).mean().to_numpy()
            return float(np.sqrt(means).mean() if root else means.mean())
        for model, by_seed in values.items():
            for seed, out in zip(SEEDS, by_seed):
                rows.append(dict(evaluation_set=scope, horizon=int(h), model=model, seed=seed,
                    mean_rmse=macro((out["mean"][index]-y)**2, True),
                    median_mae=macro(abs(out["median"][index]-y)),
                    bs1=macro((out["p1"][index]-(y >= 1))**2),
                    bs50=macro((out["p50"][index]-(y >= 50))**2)))
    return pd.DataFrame(rows)


def load_holdout_examples():
    record_holdout_opening()
    f = pd.read_parquet(EXTENDED, filters=[("recommended_sample", "=", True),
        ("in_frozen_57_cohort", "=", True), ("split", "in", ["reserved2025", "external2026"])])
    cohort = set(pd.read_csv(OLD / "cohort_private.csv").canonical_id)
    if not set(f.station_id) <= cohort or f.duplicated(["station_id", "issue_utc", "horizon"]).any():
        raise ValueError("Holdout cohort changed or source alternatives duplicated")
    year = f.issue_utc.dt.tz_convert("Asia/Ho_Chi_Minh").dt.year
    if not (year.isin([2025, 2026])).all() or not f.sample_ready.all():
        raise ValueError("Unexpected holdout roles or incomplete examples")
    if not f.loc[year.eq(2025), "gauge_namespace"].eq("legacy").all():
        raise ValueError("Unexpected source in final2025 test")
    if f.groupby(["station_id", "issue_utc"]).horizon.nunique().ne(3).any():
        raise ValueError("Incomplete common horizon packs")
    f["evaluation_set"] = np.where(year.eq(2025), "test2025_legacy", "external2026_"+f.gauge_namespace)
    return f.sort_values(["issue_utc", "station_id", "horizon"]).reset_index(drop=True)


def main():
    threadpool_limits(limits=4)
    p = protocol()
    freeze_manifest()
    target = BASE / "holdout_predictions_private.parquet"
    cache = BASE / "holdout_prediction_manifest.json"
    if cache.exists():
        record = json.loads(cache.read_text())
        check_manifest()
        if record["sha256"] != sha(target) or record["seed_scores_sha256"] != sha(PUBLIC / "holdout_seed_metrics.csv"):
            raise ValueError("Holdout prediction cache changed")
        if record["seed_outputs_sha256"] != sha(BASE / "holdout_seed_outputs.npz"):
            raise ValueError("Holdout seed outputs changed")
        holdout = pd.read_parquet(target)
    else:
        f = load_holdout_examples()
        progress("predict_locked_holdouts", rows=len(f), models=len(p["models"]))
        holdout, seeds = predict_all(f, callback=lambda model: progress("predict_locked_holdouts", model=model))
        holdout.to_parquet(target, index=False, compression="zstd")
        seed_scores(holdout, seeds).to_csv(PUBLIC / "holdout_seed_metrics.csv", index=False, lineterminator="\n")
        np.savez_compressed(BASE / "holdout_seed_outputs.npz", **{
            f"{model}__{seed}__{head}": output[head]
            for model, values in seeds.items() for seed, output in zip(SEEDS, values) for head in output})
        write_json(cache, dict(sha256=sha(target), seed_scores_sha256=sha(PUBLIC / "holdout_seed_metrics.csv"),
            seed_outputs_sha256=sha(BASE / "holdout_seed_outputs.npz"),
            final_manifest_sha256=sha(PUBLIC / "final_manifest.json")))
    dev = pd.read_parquet(BASE / "development_predictions_private.parquet")
    dev = dev[dev.split.eq("dev")].copy()
    dev["gauge_namespace"] = "legacy"
    dev["evaluation_set"] = "dev2024_legacy"
    frame = pd.concat([dev, holdout], ignore_index=True)
    for scope, f in frame.groupby("evaluation_set"):
        if f.groupby(["station_id", "issue_utc"]).size().ne(3).any():
            raise ValueError("Lost paired horizon examples")
        for model in p["models"]:
            if not (f[model+"_p50"] <= f[model+"_p1"]+1e-12).all():
                raise ValueError("Probability ordering failed")
            for h, s in f.groupby("horizon"):
                cutoff = cutoffs().get((model, h), .5)
                if ((s[model+"_p50"] >= cutoff) & (s[model+"_p1"] < cutoff)).any():
                    raise ValueError("Contradictory event decisions")
    progress("score_locked_models", rows=len(frame), models=len(p["models"]))
    for name, table in summary_tables(frame, model_names(), cutoffs()).items():
        path = BASE if name.endswith("private") else PUBLIC
        table.to_csv(path / (name+".csv"), index=False, lineterminator="\n")
    progress("paired_calendar_bootstrap", draws=p["uncertainty"]["draws"])
    ci = bootstrap_comparisons(frame, model_names(), p,
        callback=lambda scope, h: progress("paired_calendar_bootstrap", evaluation_set=scope, horizon=h))
    ci.to_csv(PUBLIC / "paired_bootstrap.csv", index=False, lineterminator="\n")
    point = pd.read_csv(PUBLIC / "point_metrics.csv")
    selected = point[(point.model.eq("LGB_N3") & point.functional.eq("mean")) |
                     (point.model.eq("GRU_N5") & point.functional.eq("median"))]
    result = dict(status="scored_not_yet_independently_verified", models=model_names(),
        final_manifest_sha256=sha(PUBLIC / "final_manifest.json"),
        holdout_prediction_sha256=sha(target), holdout_scored=True, new_fits_after_holdout_opened=0,
        evaluation_sets=sorted(frame.evaluation_set.unique().tolist()),
        source2026_continuity_confirmed=False, primary_predictions=selected.to_dict("records"),
        primary_feature_comparisons=ci[ci.evaluation_set.eq("test2025_legacy") & ci.family.eq("feature")].to_dict("records"),
        primary_skill_comparisons=ci[ci.evaluation_set.eq("test2025_legacy") & ci.family.eq("skill")].to_dict("records"),
        protected_artifacts=unchanged())
    write_json(PUBLIC / "result_summary.json", result)
    progress("holdouts_scored_pending_verification", holdout_scored=True, rows=len(holdout))
    print(json.dumps(dict(status=result["status"], holdout_rows=len(holdout), models=len(model_names()))), flush=True)


if __name__ == "__main__":
    main()
