"""Fit the two predeclared GRU controls; do not read 2025/2026 examples."""
from pathlib import Path
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import joblib
import numpy as np
import pandas as pd
import torch
from threadpoolctl import threadpool_limits
from src.gfs_final import BASE, PUBLIC, OLD, OLD_DATA, CONTROLS, SEEDS, protocol, progress, assert_control_lock, unchanged
from src.gfs_daily import write_json, sha, crossfit_calibration, choose_cutoff
from src.gfs_capacity_control import fit_control, replay_control


def main():
    threadpool_limits(limits=4)
    p = protocol()
    assert_control_lock()
    if (BASE / "holdout_opened.json").exists():
        raise ValueError("Holdout already opened; no additional control fitting allowed")
    frame = pd.read_parquet(OLD / "predictions_private.parquet").sort_values(["issue_utc", "station_id", "horizon"]).reset_index(drop=True)
    if frame.target_end_utc.dt.tz_convert("Asia/Ho_Chi_Minh").dt.year.max() != 2024:
        raise ValueError("Unexpected development frame")
    first = frame.iloc[::3].reset_index(drop=True)
    train = first.split.eq("train").to_numpy()
    details = []
    cutoffs = []
    curves = []
    for label in CONTROLS:
        outputs = []
        for seed in SEEDS:
            path = BASE / "models" / f"{label}_seed{seed}.pt"
            candidate = p["candidate_linear6"] if label.endswith("LINEAR6") else p["candidate_wide"]
            if path.exists():
                artifact = torch.load(path, map_location="cpu", weights_only=False)
                if artifact["protocol_sha256"] != sha(PUBLIC / "protocol.json"):
                    raise ValueError("Control checkpoint is from another protocol")
                out = replay_control(frame, artifact)
            else:
                def update(row):
                    progress("fit_capacity_controls", model=label, seed=seed, **row)
                artifact, out = fit_control(frame, label, train, candidate, p["epochs"], seed, update)
                artifact.update(dataset_sha256=sha(OLD_DATA), protocol_sha256=sha(PUBLIC / "protocol.json"))
                temporary = path.with_suffix(".partial.pt")
                torch.save(artifact, temporary)
                temporary.replace(path)
            if artifact["parameter_count"] != p["parameter_counts"][label]:
                raise ValueError("Control parameter count differs from predeclared count")
            outputs.append(out)
            np.savez_compressed(BASE / f"{label}_seed{seed}_development_outputs.npz", **out)
            details.append(dict(model=label, seed=seed, parameter_count=artifact["parameter_count"],
                epochs=artifact["epochs"], training_samples=artifact["training_rows"], device=artifact["device"]))
            curves.extend(dict(model=label, seed=seed, **row) for row in artifact["curves"])
            print(json.dumps(details[-1]), flush=True)
        for name in ("mean", "median"):
            frame[label+"_"+name] = np.mean([out[name] for out in outputs], axis=0).ravel()
        for h in (1, 2, 3):
            mask = frame.horizon.eq(h).to_numpy()
            part = frame.loc[mask].reset_index(drop=True)
            probability, oof, calibrators = crossfit_calibration(part,
                [out["wet"][:, h-1] for out in outputs], [out["conditional"][:, h-1] for out in outputs])
            cutoff, grid = choose_cutoff(part, oof, np.arange(.05, 1., .05).round(2))
            cutoffs.append(dict(model=label, horizon=h, cutoff=cutoff,
                selection="quarter-crossfit calibration2023, unchanged method", grid=grid))
            frame.loc[mask, label+"_p1"] = probability[:, 0]
            frame.loc[mask, label+"_p50"] = probability[:, 1]
            joblib.dump(calibrators, BASE / "models" / f"{label}_d{h}_calibrators.joblib", compress=3)
    frame.to_parquet(BASE / "development_predictions_private.parquet", index=False, compression="zstd")
    pd.DataFrame(curves).to_csv(PUBLIC / "control_learning_curves.csv", index=False, lineterminator="\n")
    write_json(PUBLIC / "control_cutoffs.json", cutoffs)
    write_json(PUBLIC / "control_summary.json", dict(status="trained_not_yet_verified", models=details,
        holdout_scored=False, preserved_artifacts=unchanged()))
    progress("capacity_controls_trained", models=len(details), holdout_scored=False)


if __name__ == "__main__":
    main()
