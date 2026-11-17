"""Frozen checkpoint inference, with no fitting or test-dependent routing."""
import json
import joblib
import numpy as np
import pandas as pd
import torch
from src.gfs_final import BASE, PUBLIC, OLD, OLD_PUBLIC, CONTROLS, SEEDS, model_names
from src.gfs_daily import FEATURES, with_delay, nested_probabilities
from src.gfs_daily_models import predict_tree, climatology
from src.gfs_daily_gru import replay
from src.gfs_capacity_control import replay_control


def apply_calibrators(wet, conditional, calibrator):
    return nested_probabilities(calibrator[0].predict(wet), calibrator[1].predict(conditional))


def predict_all(frame, callback=None):
    torch.set_num_threads(4)
    frame = frame.sort_values(["issue_utc", "station_id", "horizon"]).reset_index(drop=True).copy()
    n = len(frame)//3
    if len(frame) % 3 or not np.array_equal(frame.horizon.to_numpy().reshape(n, 3), np.tile([1, 2, 3], (n, 1))):
        raise ValueError("Inference requires sorted complete horizon packs")
    seeds = {}
    labels = model_names()
    for label in [m for m in labels if m.startswith("LGB_")]:
        config = label.split("_")[1]
        delay = int(label.split("delay")[1]) if "delay" in label else 1
        values = [dict(mean=np.zeros(len(frame)), median=np.zeros(len(frame)),
                       p1=np.zeros(len(frame)), p50=np.zeros(len(frame))) for _ in SEEDS]
        for h in (1, 2, 3):
            mask = frame.horizon.eq(h).to_numpy()
            f = with_delay(frame.loc[mask].reset_index(drop=True), delay)
            calibrators = joblib.load(OLD / "models" / f"{label}_d{h}_calibrators.joblib")
            for j, seed in enumerate(SEEDS):
                artifact = joblib.load(OLD / "models" / f"{label}_d{h}_seed{seed}.joblib")
                if artifact["features"] != FEATURES[config] or artifact["delay"] != delay:
                    raise ValueError("Frozen tree input contract changed")
                out = {head: predict_tree(estimator, artifact["features"], f, head)
                       for head, estimator in artifact["models"].items()}
                prob = apply_calibrators(out["wet"], out["conditional"], calibrators[j])
                for name in ("mean", "median"):
                    values[j][name][mask] = out[name]
                values[j]["p1"][mask] = prob[:, 0]
                values[j]["p50"][mask] = prob[:, 1]
        seeds[label] = values
        for head in values[0]:
            frame[label+"_"+head] = np.mean([v[head] for v in values], axis=0)
        if callback:
            callback(label)
    reference = climatology(frame)
    for name in reference:
        frame["CLIM_"+name] = reference[name].to_numpy()
    for label, amount in [("ZERO", np.zeros(len(frame))), ("GFS", frame.gfs_rain_mm.to_numpy()),
                          ("PERSISTENCE", frame.rain_recent24h_mm.to_numpy())]:
        for head in ("mean", "median"):
            frame[label+"_"+head] = amount
        for threshold in (1, 50):
            frame[f"{label}_p{threshold}"] = (amount >= threshold).astype(float)
    for h in (1, 2, 3):
        mask = frame.horizon.eq(h).to_numpy()
        f = frame.loc[mask]
        artifact = joblib.load(OLD / "models" / f"MOS_d{h}.joblib")
        x = artifact["scaler"].transform(f[artifact["features"]])
        for head in ("mean", "median"):
            frame.loc[mask, "MOS_"+head] = np.maximum(artifact[head].predict(x), 0.)
        wet, cond = [v.predict_proba(x)[:, 1] for v in artifact["classifiers"]]
        probability = apply_calibrators(wet, cond, artifact["calibrators"][0])
        frame.loc[mask, "MOS_p1"] = probability[:, 0]
        frame.loc[mask, "MOS_p50"] = probability[:, 1]
    for label in ["GRU_N3", "GRU_N5", *CONTROLS]:
        folder = BASE if label in CONTROLS else OLD
        values = []
        for j, seed in enumerate(SEEDS):
            artifact = torch.load(folder / "models" / f"{label}_seed{seed}.pt", map_location="cpu", weights_only=False)
            out = replay_control(frame, artifact) if label in CONTROLS else replay(frame, artifact)
            value = dict(mean=out["mean"].ravel(), median=out["median"].ravel(),
                         p1=np.zeros(len(frame)), p50=np.zeros(len(frame)))
            for h in (1, 2, 3):
                mask = frame.horizon.eq(h).to_numpy()
                calibrators = joblib.load(folder / "models" / f"{label}_d{h}_calibrators.joblib")
                prob = apply_calibrators(out["wet"][:, h-1], out["conditional"][:, h-1], calibrators[j])
                value["p1"][mask] = prob[:, 0]
                value["p50"][mask] = prob[:, 1]
            values.append(value)
        seeds[label] = values
        for name in values[0]:
            frame[label+"_"+name] = np.mean([v[name] for v in values], axis=0)
        if callback:
            callback(label)
    for label in labels:
        values = frame[[label+"_"+head for head in ("mean", "median", "p1", "p50")]].to_numpy()
        if not np.isfinite(values).all() or (values < 0).any() or (values[:, 2:] > 1).any() or (values[:, 3] > values[:, 2]+1e-12).any():
            raise ValueError("Invalid or incoherent frozen predictions: "+label)
    return frame, seeds


def cutoffs():
    original = json.loads((OLD_PUBLIC / "decision_cutoffs.json").read_text())
    controls = json.loads((PUBLIC / "control_cutoffs.json").read_text())
    return {(r["model"], int(r["horizon"])): float(r["cutoff"]) for r in original+controls}
