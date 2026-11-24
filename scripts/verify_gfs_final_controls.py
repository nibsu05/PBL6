"""Verify controls, original inference parity and absence of future-label input."""
from pathlib import Path
import sys
import json
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import torch
import joblib
from threadpoolctl import threadpool_limits
from src.gfs_final import BASE, PUBLIC, OLD, OLD_DATA, CONTROLS, SEEDS, protocol, assert_control_lock, unchanged, progress
from src.gfs_capacity_control import control_arrays, replay_control
from src.gfs_daily_gru import normalizers
from src.gfs_daily import calibrate_nested, nested_probabilities, sha, write_json
from src.gfs_final_inference import predict_all


def equal(a, b):
    np.testing.assert_allclose(a, b, rtol=1e-5, atol=3e-5)


def main():
    threadpool_limits(limits=4)
    torch.set_num_threads(4)
    p = protocol()
    assert_control_lock()
    trained = json.loads((PUBLIC / "control_summary.json").read_text())
    assert len(trained["models"]) == 6
    f = pd.read_parquet(BASE / "development_predictions_private.parquet")
    original = pd.read_parquet(OLD / "predictions_private.parquet")
    pd.testing.assert_frame_equal(f[original.columns], original)
    train = f.iloc[::3].split.eq("train").to_numpy()
    selected = np.unique(np.linspace(0, len(f)//3-1, 20).astype(int))
    positions = (selected[:, None]*3+np.arange(3)).ravel()
    sample = f.iloc[positions].reset_index(drop=True)
    altered = sample.copy()
    altered["y_mm"] = np.arange(len(sample))*10000.
    checked = 0
    for label in CONTROLS:
        outs = []
        probabilities = []
        for j, seed in enumerate(SEEDS):
            artifact = torch.load(BASE / "models" / f"{label}_seed{seed}.pt", map_location="cpu", weights_only=False)
            assert artifact["parameter_count"] == p["parameter_counts"][label]
            assert artifact["epochs"] == 17 and artifact["dataset_sha256"] == sha(OLD_DATA)
            raw, projection = control_arrays(f, label, train)
            norm = normalizers(raw, train)
            for name in norm:
                equal(norm[name], artifact["normalizers"][name])
            if projection is not None:
                for name in projection:
                    equal(projection[name], artifact["projection"][name])
            saved = dict(np.load(BASE / f"{label}_seed{seed}_development_outputs.npz"))
            replayed = replay_control(sample, artifact, cpu=True)
            changed = replay_control(altered, artifact, cpu=True)
            for name in replayed:
                equal(replayed[name], saved[name][selected])
                equal(replayed[name], changed[name])
                checked += 2
            outs.append(saved)
            probability = np.zeros((len(f), 2))
            for h in (1, 2, 3):
                mask = f.horizon.eq(h).to_numpy()
                part = f.loc[mask]
                wet, cond = saved["wet"][:, h-1], saved["conditional"][:, h-1]
                calibrator = joblib.load(BASE / "models" / f"{label}_d{h}_calibrators.joblib")[j]
                actual = nested_probabilities(calibrator[0].predict(wet), calibrator[1].predict(cond))
                expected, _ = calibrate_nested(wet, cond, part.y_mm.to_numpy(), part.split.eq("cal").to_numpy())
                equal(actual, expected)
                probability[mask] = actual
                checked += 1
            probabilities.append(probability)
        for name in ("mean", "median"):
            equal(np.mean([v[name] for v in outs], axis=0).ravel(), f[label+"_"+name])
        equal(np.mean(probabilities, axis=0), f[[label+"_p1", label+"_p50"]])
    replayed, _ = predict_all(f, callback=lambda name: progress("verify_frozen_inference", model=name))
    predictions = [name+"_"+head for name in p["models"] for head in ("mean", "median", "p1", "p50")]
    for column in predictions:
        equal(replayed[column], f[column])
        checked += 1
    result = dict(status="passed", protocol_sha256=sha(PUBLIC / "protocol.json"),
        all_development_rows_replayed=len(f), prediction_columns_replayed=len(predictions),
        control_checkpoints_replayed=6, normalizers_train_only=True,
        future_label_perturbation_does_not_change_predictions=True, original_models_reproduce_saved_predictions=True,
        numeric_checks=checked, old_artifacts_preserved=unchanged(), holdout_scored=False)
    write_json(PUBLIC / "control_verification.json", result)
    trained["status"] = "verified"
    write_json(PUBLIC / "control_summary.json", trained)
    progress("controls_verified", **{k: v for k, v in result.items() if k != "status"})
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
