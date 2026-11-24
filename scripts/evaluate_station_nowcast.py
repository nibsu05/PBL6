"""Verify frozen models on aligned hourly forecasts for 2024 and held-out 2025."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import lightgbm as lgb
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import station_nowcast as ns
from src.verification import contingency_scores, continuous_scores


SEEDS = ns.PROTOCOL["bilstm"]["seeds"]
MODELS = ("Zero", "Persistence", "BiLSTM_R", "BiLSTM_E0", "BiLSTM_E2", "LightGBM_R")
COMPARISONS = [
    ("BiLSTM_E2", "BiLSTM_E0"),
    ("BiLSTM_E0", "BiLSTM_R"),
    ("BiLSTM_R", "Persistence"),
    ("LightGBM_R", "Persistence"),
]


def read_fit(out: Path):
    path = out / "fit_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for name, digest in manifest["training"]["hashes"].items():
        if ns.sha256(ns.ROOT / name) != digest:
            raise ValueError(f"Frozen training code differs: {name}")
    for name, digest in manifest["artifacts"].items():
        if ns.sha256(out / name) != digest:
            raise ValueError(f"Frozen model artifact differs: {name}")
    transform = json.loads((out / "scaler.json").read_text(encoding="utf-8"))
    if transform["features"] != ns.ALL:
        raise ValueError("Model input order differs from the feature contract")
    return manifest, transform


def bilstm_forecasts(out, data, idx, roster, only=tuple(ns.FEATURES)):
    forecasts = {}
    for experiment in only:
        base = "BiLSTM_" + experiment
        preds = []
        for seed in SEEDS:
            ckpt = torch.load(out / f"{experiment}_seed{seed}.pt", map_location="cpu", weights_only=True)
            if (ckpt["mode"], ckpt["seed"]) != (experiment, seed):
                raise ValueError("Checkpoint keys differ from file name")
            model = ns.PooledBiLSTM(len(roster)).to(data.device)
            model.load_state_dict(ckpt["state_dict"])
            forecasts[f"{base}_s{seed}"] = ns.predict(model, data, idx, experiment)
            preds.append(forecasts[f"{base}_s{seed}"])
        forecasts[base] = np.mean(preds, axis=0, dtype=np.float32)
    return forecasts


def rain_tree_forecasts(out, x, idx, station_index):
    lag = ns.rain_tree_features(x, idx, station_index)
    return np.column_stack([
        lgb.Booster(model_file=str(out / f"LightGBM_R_h{h}.txt")).predict(lag, num_threads=8)
        for h in ns.LEADS
    ]).clip(min=0).astype("float32")


def bundles(out, samples, transform, idx, device):
    x = samples.x[idx, 0]
    prediction = dict(Zero=np.zeros_like(samples.y[idx]),
                      Persistence=np.broadcast_to(x[:, None], (len(x), ns.HORIZON)),
                      LightGBM_R=rain_tree_forecasts(out, samples.x, idx, samples.station_index))
    d = ns.WindowTensors(samples.x, samples.y, samples.station_index,
                         np.asarray(transform["mean"], np.float32), np.asarray(transform["std"], np.float32),
                         device)
    prediction.update(bilstm_forecasts(out, d, idx, transform["roster"]))
    return prediction


def series_scores(y, prediction):
    base = continuous_scores(y, prediction)
    return [dict(**base, **contingency_scores(y, prediction, threshold),
                 MAE_event=float(np.mean(np.abs(y[y >= threshold] - prediction[y >= threshold])))
                 if (y >= threshold).any() else float("nan"))
            for threshold in ns.PROTOCOL["event_thresholds_mm"]]


def score(role, station, y, forecasts):
    rows, seeds, station_scores = [], [], []
    pilot = np.isin(station, ns.PROTOCOL["pilot_stations"])
    for name in MODELS:
        for j, h in enumerate(ns.LEADS):
            p = forecasts[name][:, j]
            for scope, mask in (("all_micro", slice(None)), ("pilot3_micro", pilot)):
                rows.extend({**record, "role": role, "scope": scope, "model": name, "lead_hour": h}
                            for record in series_scores(y[mask, j], p[mask]))
            for sid in np.unique(station):
                mask = station == sid
                station_scores.extend({**record, "role": role, "station_id": sid, "model": name, "lead_hour": h}
                                      for record in series_scores(y[mask, j], p[mask]))
    for name, values in forecasts.items():
        if name in MODELS:
            continue
        for j, h in enumerate(ns.LEADS):
            seeds.extend({**record, "role": role, "model_seed": name, "lead_hour": h}
                         for record in series_scores(y[:, j], values[:, j]))
    per_station = pd.DataFrame(station_scores)
    for scope, view in (("all_macro", per_station),
                        ("pilot3_macro", per_station[per_station.station_id.isin(ns.PROTOCOL["pilot_stations"])])):
        for (model, lead, threshold), g in view.groupby(["model", "lead_hour", "threshold"]):
            avgs = g[["MAE", "RMSE", "bias", "POD", "FAR", "CSI", "MAE_event"]].mean().to_dict()
            rows.append(dict(**avgs, role=role, scope=scope, model=model, lead_hour=lead,
                             threshold=threshold, n=int(g.n.sum()), n_stations=len(g),
                             n_obs_events=int(g.n_obs_events.sum())))
    return pd.DataFrame(rows), pd.DataFrame(seeds), per_station


def block_sums(daily, length, sampled):
    """A sampled calendar block includes every station and every hour of its days."""
    days = len(daily)
    whole, rest = divmod(days, length)
    ext = np.concatenate([daily, daily[:length - 1]], axis=0)
    cumulative = np.concatenate([np.zeros_like(ext[:1]), ext.cumsum(0)], axis=0)
    starts = sampled[:, :whole]
    total = (cumulative[starts + length] - cumulative[starts]).sum(axis=1)
    if rest:
        start = sampled[:, -1]
        total += cumulative[start + rest] - cumulative[start]
    return total


def paired_blocks(role, times, y, predictions):
    local = pd.to_datetime(times, utc=True).tz_convert(ns.ZONE).tz_localize(None)
    ordinals = local.to_numpy(dtype="datetime64[D]").astype(np.int64)
    day = ordinals - ordinals.min()
    n_days = int(day.max()) + 1
    selected = ns.PROTOCOL["primary_comparison"]
    policy = ns.PROTOCOL["block_bootstrap"]
    all_counts = np.bincount(day, minlength=n_days)
    rng = np.random.default_rng(policy["seed"])
    indices = {length: rng.integers(n_days, size=(policy["replicates"], (n_days + length - 1) // length))
               for length in policy["block_days"]}
    rows = []
    for name, reference in COMPARISONS:
        for j, h in enumerate(ns.LEADS):
            threshold = selected["threshold_mm"]
            truth = y[:, j].astype(np.float64)
            a, b = (predictions[k][:, j].astype(np.float64) for k in (name, reference))
            event = truth >= threshold
            aw = a >= threshold
            bw = b >= threshold
            daily = np.column_stack([np.bincount(day, weights=w, minlength=n_days) for w in
                                     ((a - truth) ** 2, (b - truth) ** 2,
                                      event & aw, event | aw, event & bw, event | bw)] + [all_counts])
            observed = daily.sum(axis=0)
            csi_delta = observed[2] / observed[3] - observed[4] / observed[5]
            rmse_delta = np.sqrt(observed[0] / observed[6]) - np.sqrt(observed[1] / observed[6])
            for length, sampled in indices.items():
                totals = block_sums(daily, length, sampled)
                csi = totals[:, 2] / totals[:, 3] - totals[:, 4] / totals[:, 5]
                rmse = np.sqrt(totals[:, 0] / totals[:, 6]) - np.sqrt(totals[:, 1] / totals[:, 6])
                for metric, value, distribution in (("CSI", csi_delta, csi), ("RMSE", rmse_delta, rmse)):
                    lo, hi = np.quantile(distribution, (.025, .975))
                    primary = (name == selected["candidate"] and reference == selected["reference"]
                               and h == selected["lead_hour"] and metric == selected["metric"])
                    rows.append(dict(role=role, candidate=name, reference=reference, lead_hour=h,
                                     metric=metric, threshold_mm=threshold if metric == "CSI" else np.nan,
                                     observed_delta=value, ci_lo=lo, ci_hi=hi, calendar_days=n_days,
                                     block_days=length, primary=primary))
    return pd.DataFrame(rows)


def store_predictions(out, role, stations, times, y, forecasts):
    payload = {"station_id": stations, "issue_time_utc": pd.to_datetime(times, utc=True)}
    payload.update({f"obs_h{h}": y[:, i] for i, h in enumerate(ns.LEADS)})
    for model, values in forecasts.items():
        if values.shape != y.shape or not np.isfinite(values).all() or (values < 0).any():
            raise ValueError(f"Invalid paired forecasts: {model}/{role}")
        payload.update({f"{model}_h{h}": values[:, j] for j, h in enumerate(ns.LEADS)})
    rows = pd.DataFrame(payload)
    key = ["station_id", "issue_time_utc"]
    if rows.duplicated(key).any():
        raise ValueError("Duplicate station-issue forecast")
    target = out / f"predictions_{role}.parquet"
    pending = target.with_suffix(".pending")
    rows.to_parquet(pending, index=False, compression="zstd")
    pending.replace(target)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ns.PRIVATE)
    parser.add_argument("--source", type=Path, default=ns.SOURCE)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--roles", choices=["dev", "reserved2025"], nargs="+",
                        default=["dev", "reserved2025"])
    args = parser.parse_args()
    manifest, transform = read_fit(args.out)
    if ns.sha256(args.source) != manifest["training"]["dataset_sha256"]:
        raise ValueError("Dataset no longer matches the locked fit")
    frozen = dict(fit_manifest_sha256=ns.sha256(args.out / "fit_manifest.json"),
                  evaluation_sha256=ns.sha256(Path(__file__)),
                  metrics_code_sha256=ns.sha256(ns.ROOT / "src/verification.py"),
                  primary_comparison=ns.PROTOCOL["primary_comparison"])
    lock = args.out / "score_lock.json"
    if lock.exists() and json.loads(lock.read_text(encoding="utf-8")) != frozen:
        raise ValueError("Evaluation configuration no longer matches the locked run")
    ns.write_json(lock, frozen)
    device = torch.device(args.device)
    torch.set_num_threads(8)
    for role in args.roles:
        print(f"Rebuilding aligned sample keys for {role}", flush=True)
        samples = ns.read_samples(args.source, (role,), transform["roster"])
        idx, y = samples.origins[role], samples.y[samples.origins[role]]
        stations, times = samples.ids(idx), samples.times[idx]
        print(f"Scoring {len(idx):,} common origins across {len(np.unique(stations))} stations in {role}",
              flush=True)
        forecasts = bundles(args.out, samples, transform, idx, device)
        archive = store_predictions(args.out, role, stations, times, y, forecasts)
        metrics, seeds, per_station = score(role, stations, y, forecasts)
        ci = paired_blocks(role, times, y, forecasts)
        outputs = [archive]
        for frame, file in ((metrics, "metrics"), (seeds, "seed_metrics"),
                            (per_station, "station_metrics"), (ci, "paired_blocks"),
                            (samples.coverage, "coverage")):
            path = args.out / f"{file}_{role}.csv"
            frame.to_csv(path, index=False)
            outputs.append(path)
        locks = {path.name: ns.sha256(path) for path in outputs}
        ns.write_json(args.out / f"evaluation_{role}.json",
                      dict(role=role, score_lock_sha256=ns.sha256(lock), n_origins=len(idx),
                           n_stations=len(np.unique(stations)), n_outputs=len(idx) * ns.HORIZON,
                           models=list(forecasts), artifacts=locks))
        print(ci[ci.primary].to_string(index=False), flush=True)
        del samples, y, forecasts, metrics, seeds, per_station, ci


if __name__ == "__main__":
    main()
