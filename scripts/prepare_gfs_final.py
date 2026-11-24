"""Freeze the approved final research plan before new fits or holdout scoring."""
from pathlib import Path
import json
import sys
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.gfs_final import BASE, PUBLIC, OLD, OLD_PUBLIC, OLD_DATA, EXTENDED, CONTROLS, SEEDS
from src.gfs_daily import sha, write_json
from src.gfs_daily_lock import training_lock
from src.gfs_capacity_control import fixed_projection, PROJECTION_NAMES, PROJECTION_SEED
import hashlib


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (BASE / "models").mkdir(exist_ok=True)
    if (PUBLIC / "protocol.json").exists():
        from src.gfs_final import protocol, assert_control_lock
        protocol()
        assert_control_lock()
        print("Existing final-study freeze verified")
        return
    training_lock()
    selected = json.loads((OLD_PUBLIC / "gru_selection.json").read_text())
    assert selected["candidate"] == dict(name="small", hidden=16, head=24, lr=.001)
    assert selected["epochs"] == 17
    preserved = [OLD_DATA, OLD / "predictions_private.parquet", EXTENDED]
    preserved += list((OLD / "models").glob("*"))
    preserved += [p for p in OLD_PUBLIC.iterdir() if p.is_file() and not p.name.startswith("~$")]
    preserved += list((ROOT / "reports/station_update_2026_11_16").glob("*"))
    preserved += list((ROOT / "reports/station_hourly_era5_2026_11_17").glob("*"))
    user = json.loads((ROOT / "data/operational/workspace_cleanup_2026_11_09/user_files.json").read_text(encoding="utf8"))
    preserved += [ROOT / item["path"] for item in user]
    write_json(BASE / "protected_before.json", {p.relative_to(ROOT).as_posix(): sha(p) for p in preserved if p.is_file()})
    original = json.loads((OLD_PUBLIC / "result_summary.json").read_text())
    p = dict(version=PUBLIC.name, authorized_date="2026-11-17",
        authorization="User approved the five-step proposal, including lock then independent 2025 and separate 2026 scoring",
        original_protocol_sha256=sha(OLD_PUBLIC / "protocol.json"),
        original_dataset_sha256=sha(OLD_DATA), extended_dataset_sha256=sha(EXTENDED),
        station_cohort="unchanged train-only 57 stations from daily-v2", station_count=57,
        station_manifest_sha256=sha(OLD / "cohort_private.csv"),
        task="three separate next-24h amounts at stations, issue19h Vietnam daily",
        controls=list(CONTROLS), seeds=list(SEEDS), epochs=17, batch=256,
        candidate_linear6=selected["candidate"],
        candidate_wide=dict(name="capacity_nearest", hidden=16, head=27, lr=.001),
        parameter_counts=dict(GRU_N3=4364, GRU_N5=4796, GRU_N3_LINEAR6=4796, GRU_N3_WIDE=4751),
        wide_selection="nearest integer head width to N5 parameter count at fixed hidden16; no target-based tuning",
        linear_control=dict(source_names=PROJECTION_NAMES, seed=PROJECTION_SEED,
            matrix=fixed_projection().tolist(), matrix_sha256=hashlib.sha256(fixed_projection().tobytes()).hexdigest(),
            scaling="fit only on 2021--2022; deterministic six redundant linear combinations of raw met/terrain",
            interpretation="same nominal parameter count as N5, tests nonlinear representation beyond linear redundancy; not a proof of physical causality"),
        fit_years=[2021, 2022], calibration_year=2023, development_year=2024,
        dev2024_status="already explored; new controls are development analyses",
        tuning="reuse train-only CV-selected hyperparameters and 17 fixed epochs for all controls; no new search",
        calibration="same nested Platt and quarter-crossfit cutoff method as original, using only2023",
        models=original["models"]+list(CONTROLS),
        primary_amount_model="LGB_N3", secondary_median_model="GRU_N5",
        primary_feature_contrasts=[["LGB_N1", "LGB_N0"], ["LGB_N3", "LGB_N1"], ["GRU_N5", "GRU_N3_LINEAR6"]],
        primary_feature_metric="mean-head station-macro RMSE, each of three horizons; one family of9 comparisons",
        primary_skill_contrasts=[["LGB_N3", "MOS", "mean_rmse"], ["GRU_N5", "MOS", "median_mae"]],
        primary_skill_family_size=6,
        secondary_contrasts=[["GRU_N5", "GRU_N3"], ["GRU_N5", "GRU_N3_WIDE"], ["GRU_N3_LINEAR6", "GRU_N3"]],
        thresholds_mm24h=[1, 50], threshold50_status="exploratory, not an asserted warning standard",
        metrics=["RMSE mean", "MAE median", "Bias", "BS", "BSS", "CSI", "POD", "FAR"],
        uncertainty=dict(draws=5000, block_days=14, seed=1701,
            method="paired circular calendar-date blocks, all stations and horizons together",
            primary_decision="negative difference and Bonferroni simultaneous interval upper<0 within each fixed family",
            additional_p="one-sided centered-bootstrap approximate p with Holm correction; not an exact randomization test",
            scope="fixed trained three-seed ensembles; does not include sensor uncertainty or training-seed uncertainty"),
        test2025=dict(source="legacy API", cohort="same57", mask="recommended_sample & in_frozen_57_cohort & reserved2025",
            policy="no refitting, retuning, recalibration, cutoff changes or winner selection after opening"),
        external2026=dict(source="legacy and modern reported separately", cohort="same57", partial_year=True,
            continuity_confirmed=False, policy="descriptive robustness with source caveats; never used to tune or select models"),
        holdout_gate="controls verified, all artifacts and inference/evaluation code SHA locked before reading test rows",
        future_fit_policy="further model changes after test require a new development protocol and cannot reuse2025 as untouched test",
        original_availability_proven=False, no_new_observation_download_required=True)
    write_json(PUBLIC / "protocol.json", p)
    write_json(BASE / "protocol_lock.json", dict(sha256=sha(PUBLIC / "protocol.json"), locked_utc=datetime.now(timezone.utc).isoformat()))
    paths = ["src/gfs_final.py", "src/gfs_capacity_control.py", "scripts/run_gfs_capacity_controls.py"]
    write_json(BASE / "control_training_lock.json", dict(dataset_sha256=sha(OLD_DATA),
        code_sha256={name: sha(ROOT/name) for name in paths}, locked_utc=datetime.now(timezone.utc).isoformat()))
    write_json(PUBLIC / "preparation.json", dict(status="protocol_frozen_before_new_fit_and_holdout_scoring",
        protocol_sha256=sha(PUBLIC / "protocol.json"), protected_artifacts=len(preserved), holdout_scored=False))
    print(json.dumps(dict(state="prepared", controls=list(CONTROLS), holdout_scored=False)), flush=True)


if __name__ == "__main__":
    main()
