"""Independently recompute published scores and replay checkpoints at sampled keys."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.evaluate_station_nowcast import MODELS, bundles, read_fit
from src import station_nowcast as ns


def verify_role(out, source, transform, role, device):
    manifest = json.loads((out / f"evaluation_{role}.json").read_text(encoding="utf-8"))
    for name, digest in manifest["artifacts"].items():
        if ns.sha256(out / name) != digest:
            raise ValueError(f"Evaluation artifact changed: {name}")
    scores = pd.read_csv(out / f"metrics_{role}.csv")
    scores = scores[scores.scope.eq("all_micro")].set_index(["model", "lead_hour", "threshold"])
    path = out / f"predictions_{role}.parquet"
    parts = ["station_id", "issue_time_utc", *[f"obs_h{h}" for h in ns.LEADS]]
    archive = pq.ParquetFile(path)
    obs = archive.read(columns=parts).to_pandas()
    if len(obs) != manifest["n_origins"] or obs.duplicated(parts[:2]).any():
        raise ValueError("Invalid archived sample keys")
    y = obs[parts[2:]].to_numpy(dtype=np.float64)
    metrics_checked = 0
    for method in MODELS:
        names = [f"{method}_h{h}" for h in ns.LEADS]
        values = archive.read(columns=names).to_pandas().to_numpy(dtype=np.float64)
        for i, h in enumerate(ns.LEADS):
            delta = values[:, i] - y[:, i]
            for threshold in ns.PROTOCOL["event_thresholds_mm"]:
                wet = y[:, i] >= threshold
                said_wet = values[:, i] >= threshold
                hits = np.count_nonzero(wet & said_wet)
                misses = np.count_nonzero(wet & ~said_wet)
                false = np.count_nonzero(~wet & said_wet)
                target = scores.loc[(method, h, threshold)]
                expected = [hits, misses, false, len(wet) - hits - misses - false, len(wet)]
                actual = target[["hits", "misses", "false_alarms", "correct_negatives", "n"]].to_numpy(float)
                np.testing.assert_array_equal(actual, expected)
                csi = hits / (hits + misses + false)
                far = false / (hits + false) if hits + false else np.nan
                pod = hits / (hits + misses)
                regression = [np.sqrt(delta @ delta / len(delta)), np.abs(delta).mean(), delta.mean()]
                np.testing.assert_allclose(target[["CSI", "POD", "FAR", "RMSE", "MAE", "bias"]].to_numpy(float),
                                           [csi, pod, far, *regression], rtol=1e-9, atol=1e-9, equal_nan=True)
                metrics_checked += 1
    target = ns.PROTOCOL["primary_comparison"]
    idx = (target["lead_hour"], target["threshold_mm"])
    gain = scores.loc[(target["candidate"], *idx), "CSI"] - scores.loc[(target["reference"], *idx), "CSI"]
    ci = pd.read_csv(out / f"paired_blocks_{role}.csv")
    np.testing.assert_allclose(ci.loc[ci.primary, "observed_delta"], gain, atol=1e-12)
    samples = ns.read_samples(source, (role,), transform["roster"])
    indices = samples.origins[role]
    np.testing.assert_array_equal(samples.ids(indices), obs.station_id.to_numpy())
    np.testing.assert_array_equal(samples.times[indices],
                                  pd.DatetimeIndex(obs.issue_time_utc).as_unit("ns").asi8)
    np.testing.assert_array_equal(samples.y[indices], y)
    rng = np.random.default_rng(811)
    by_station = obs.groupby("station_id", sort=False).indices
    chosen = np.sort(np.concatenate([rng.choice(positions, 16, replace=False)
                                     for positions in by_station.values()]))
    outputs = bundles(out, samples, transform, indices[chosen], device)
    max_diff = 0.0
    for method, predictions in outputs.items():
        columns = [f"{method}_h{h}" for h in ns.LEADS]
        saved = archive.read(columns=columns).to_pandas().iloc[chosen].to_numpy()
        diff = float(np.max(np.abs(saved - predictions)))
        max_diff = max(max_diff, diff)
        np.testing.assert_allclose(saved, predictions, atol=1e-5, rtol=1e-5)
    summary = dict(origins_verified=len(obs), rows_of_metrics_verified=metrics_checked,
                   stations=len(by_station), replay_origins=len(chosen),
                   model_versions=len(outputs), max_abs_forecast_difference_mm=max_diff)
    print(role, summary, flush=True)
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=ns.PRIVATE)
    p.add_argument("--source", type=Path, default=ns.SOURCE)
    p.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    args = p.parse_args()
    fit, transform = read_fit(args.out)
    if ns.sha256(args.source) != fit["training"]["dataset_sha256"]:
        raise ValueError("Data checksum differs from the trained snapshot")
    torch.set_num_threads(8)
    replay = json.loads((args.out / "replay_summary.json").read_text(encoding="utf-8"))
    if ns.sha256(args.out / "station_nowcast_replay_private.json") != replay["sha256"]:
        raise ValueError("Historical replay changed")
    records = {role: verify_role(args.out, args.source, transform, role, torch.device(args.device))
               for role in ("dev", "reserved2025")}
    ns.write_json(args.out / "verification.json", dict(status="passed", checks=records, replay=replay))


if __name__ == "__main__":
    main()
