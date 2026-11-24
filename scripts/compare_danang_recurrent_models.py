"""Compare recurrent encoders on the frozen Da Nang hourly and daily samples."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from time import perf_counter

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import pandas as pd
import torch
from threadpoolctl import threadpool_limits
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_station_nowcast import block_sums, read_fit
from scripts.train_station_nowcast import amount_rmse
from src import gfs_final, station_nowcast as hourly
from src.gfs_daily import FEATURES, choose_cutoff, crossfit_calibration
from src.gfs_daily_gru import DailyGRU, arrays, loss_function, normalizers, predict, tensors
from src.gfs_final_inference import apply_calibrators, cutoffs
from src.gfs_final_metrics import bootstrap_comparisons, summary_tables
from src.verification import contingency_scores, continuous_scores

VERSION = "danang_system_2026_11_24"
PUBLIC = ROOT / "reports" / VERSION
PRIVATE = ROOT / "data/operational" / VERSION
PROTOCOL_PATH = PUBLIC / "protocol.json"
PROTOCOL = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
SEEDS = PROTOCOL["seeds"]
DAY_CANDIDATE = "BiLSTM_N3"
HOUR_CANDIDATE = "GRU_R"
DAILY_MODELS = ("ZERO", "GFS", "MOS", "LGB_N3", "GRU_N3", "GRU_N5", DAY_CANDIDATE)


class HourlyGRU(nn.Module):
    def __init__(self, n_stations):
        super().__init__()
        hp = hourly.PROTOCOL["bilstm"]
        hidden = PROTOCOL["hour"]["hidden"]
        embedding = hp["station_embedding_size"]
        width = hp["head_size"]
        self.station_embedding = nn.Embedding(n_stations, embedding)
        self.recurrent = nn.GRU(len(hourly.ALL), hidden, batch_first=True)
        self.head = nn.Sequential(nn.Linear(hidden + embedding, width), nn.ReLU(),
                                  nn.Dropout(hp["dropout"]), nn.Linear(width, hourly.HORIZON),
                                  nn.Softplus())
        nn.init.constant_(self.head[-2].bias, -2)

    def forward(self, x, station):
        _, hidden = self.recurrent(x)
        return self.head(torch.cat((hidden[-1], self.station_embedding(station)), dim=1))


class BidirectionalHistory(nn.Module):
    """Present both final states to the existing daily forecast heads."""

    def __init__(self, width):
        super().__init__()
        self.lstm = nn.LSTM(1, width, bidirectional=True, batch_first=True)

    def forward(self, history):
        outputs, (hidden, _) = self.lstm(history)
        return outputs, torch.cat((hidden[0], hidden[1]), dim=1).unsqueeze(0)


def day_model(channels, head):
    width = PROTOCOL["day"]["hidden_per_direction"]
    model = DailyGRU(channels, hidden=2 * width, head=head)
    model.encoder = BidirectionalHistory(width)
    return model


def fit_hour(data, samples, seed):
    hp = hourly.PROTOCOL["bilstm"]
    torch.manual_seed(seed)
    model = HourlyGRU(len(samples.stations)).to(data.device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=hp["learning_rate"], fused=data.device.type == "cuda")
    train = torch.as_tensor(samples.origins["train"], device=data.device)
    cal = samples.origins["cal"]
    log_targets = torch.log1p(data.y)
    best_rmse, best_epoch, best_state, stale = np.inf, 0, None, 0
    started = perf_counter()
    for epoch in range(1, hp["max_epochs"] + 1):
        model.train()
        shuffled = train[torch.randperm(len(train), device=data.device)]
        for batch in shuffled.split(hp["batch_size"]):
            window, station = data.window(batch, "R")
            optimizer.zero_grad(set_to_none=True)
            loss = nn.functional.mse_loss(model(window, station), log_targets[batch])
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.)
            optimizer.step()
        error = amount_rmse(samples.y[cal], hourly.predict(model, data, cal, "R", hp["batch_size"]))
        if error < best_rmse:
            best_rmse, best_epoch, stale = error, epoch, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            stale += 1
        print(f"{HOUR_CANDIDATE} seed={seed} epoch={epoch}: calibration RMSE {error:.5f}", flush=True)
        if epoch >= hp["min_epochs"] and stale >= hp["patience"]:
            break
    return dict(state=best_state, epoch=best_epoch, epochs_run=epoch, calibration_rmse=best_rmse,
                parameters=sum(p.numel() for p in model.parameters()), seconds=perf_counter() - started)


def fit_day(raw, train, cal, hp, epochs, seed, device):
    torch.manual_seed(seed)
    started = perf_counter()
    norm = normalizers(raw, train)
    values = tensors(raw, norm)
    model = day_model(len(raw["names"]), hp["head"]).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=hp["lr"], weight_decay=.001)
    loader = DataLoader(TensorDataset(*[v[train] for v in values]), batch_size=256, shuffle=True,
                        generator=torch.Generator().manual_seed(seed), num_workers=0)
    for epoch in range(1, epochs + 1):
        model.train()
        for batch in loader:
            history, context, station, target, events = [v.to(device) for v in batch]
            optimizer.zero_grad(set_to_none=True)
            point, logits = model(history, context, station)
            loss = loss_function(point, logits, target, events)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.)
            optimizer.step()
        print(f"{DAY_CANDIDATE} seed={seed} epoch={epoch}/{epochs}", flush=True)
    cal_output = predict(model, [v[cal] for v in values], norm["target_scale"], device)
    return dict(state={k: v.detach().cpu() for k, v in model.state_dict().items()},
                normalizers=norm, features=raw["names"], calibration=cal_output,
                epochs_run=epochs, parameters=sum(p.numel() for p in model.parameters()),
                seconds=perf_counter() - started)


def checkpoint(task, seed, lock, train):
    path = PRIVATE / f"{task}_seed{seed}.pt"
    if path.is_file():
        payload = torch.load(path, map_location="cpu", weights_only=False)
        if payload["training_lock_sha256"] != lock:
            raise ValueError(f"Checkpoint {path.name} uses a different protocol or input")
        return payload
    payload = dict(**train(), training_lock_sha256=lock, seed=seed)
    temporary = path.with_suffix(".pending")
    torch.save(payload, temporary)
    temporary.replace(path)
    return payload


def hourly_data(samples, scaler, device):
    mean, std = (np.array(scaler[name], dtype=np.float32) for name in ("mean", "std"))
    return hourly.WindowTensors(samples.x, samples.y, samples.station_index, mean, std, device)


def train_candidates(scaler, lock, device):
    samples = hourly.read_samples(hourly.SOURCE, ("train", "cal"), scaler["roster"])
    if len(samples.origins["train"]) != 1032811 or len(samples.origins["cal"]) != 676870:
        raise ValueError("Hourly training/calibration counts changed")
    data = hourly_data(samples, scaler, device)
    hour = [checkpoint("hour", s, lock, lambda: fit_hour(data, samples, s)) for s in SEEDS]
    del data, samples
    if device.type == "cuda":
        torch.cuda.empty_cache()

    torch.use_deterministic_algorithms(True, warn_only=True)
    daily_protocol = gfs_final.protocol()
    hp = daily_protocol["candidate_linear6"]
    daily = development_examples()
    raw = arrays(daily, "N3")
    roles = daily.split.iloc[::3]
    train, cal = (roles.eq(role).to_numpy() for role in ("train", "cal"))
    if (train.sum(), cal.sum()) != (35116, 18365):
        raise ValueError("Daily training/calibration counts changed")
    day = [checkpoint("day", s, lock, lambda: fit_day(raw, train, cal, hp, daily_protocol["epochs"], s, device))
           for s in SEEDS]
    return hour, day


def development_examples():
    cols = list(dict.fromkeys(["issue_utc", "station_id", "horizon", "split", "y_mm", *FEATURES["N3"]]))
    return pd.read_parquet(gfs_final.OLD / "predictions_private.parquet", columns=cols,
                           filters=[("split", "in", ["train", "cal"])]).sort_values(
                               ["issue_utc", "station_id", "horizon"]).reset_index(drop=True)


def paired_hour_intervals(times, y, candidate, reference):
    config = PROTOCOL["bootstrap"]
    date = pd.to_datetime(times, utc=True).tz_convert(hourly.ZONE).tz_localize(None).to_numpy(dtype="datetime64[D]")
    day = (date - date.min()).astype("int64")
    count = int(day.max() + 1)
    length = config["days"]
    draws = np.random.default_rng(config["seed"]).integers(
        count, size=(config["draws"], (count + length - 1) // length))
    denom = block_sums(np.bincount(day, minlength=count), length, draws)
    out = []
    for index, lead in enumerate(hourly.LEADS):
        errors = [(p[:, index] - y[:, index]).astype(np.float64) ** 2 for p in (candidate, reference)]
        boots = [np.sqrt(block_sums(np.bincount(day, weights=e, minlength=count), length, draws) / denom)
                 for e in errors]
        lo, hi = np.quantile(boots[0] - boots[1], [.025, .975])
        delta = np.sqrt(errors[0].mean()) - np.sqrt(errors[1].mean())
        out.append(dict(task="hour", lead=lead, candidate=HOUR_CANDIDATE, reference="BiLSTM_R",
                        delta_rmse=float(delta), ci95_low=float(lo), ci95_high=float(hi)))
    return out


def score_hour(artifacts, scaler, device):
    samples = hourly.read_samples(hourly.SOURCE, ("reserved2025",), scaler["roster"])
    idx = samples.origins["reserved2025"]
    y = samples.y[idx]
    times = pd.to_datetime(samples.times[idx], utc=True)
    keys = pd.MultiIndex.from_arrays([samples.ids(idx), times], names=["station_id", "issue_time_utc"])
    refs = ("Zero", "Persistence", "LightGBM_R", "BiLSTM_R")
    old = hourly.PRIVATE / "predictions_reserved2025.parquet"
    base = pd.read_parquet(old, columns=[*keys.names, *[f"{m}_h{h}" for m in (*refs, "obs") for h in hourly.LEADS]])
    base = base.set_index(keys.names, verify_integrity=True).reindex(keys)
    if len(base) != 679461 or not np.array_equal(y, base[[f"obs_h{h}" for h in hourly.LEADS]].to_numpy()):
        raise ValueError("Hourly comparison failed exact key/label alignment")
    data = hourly_data(samples, scaler, device)
    runs = []
    for artifact in artifacts:
        model = HourlyGRU(len(samples.stations)).to(device)
        model.load_state_dict(artifact["state"])
        runs.append(hourly.predict(model, data, idx, "R"))
    new = np.mean(runs, axis=0, dtype=np.float32)
    forecasts = {m: base[[f"{m}_h{h}" for h in hourly.LEADS]].to_numpy() for m in refs}
    forecasts[HOUR_CANDIDATE] = new
    rows = []
    for model, p in forecasts.items():
        if not np.isfinite(p).all():
            raise ValueError(f"Nonfinite forecasts for {model}")
        for j, lead in enumerate(hourly.LEADS):
            amount = continuous_scores(y[:, j], p[:, j])
            rows.extend(dict(model=model, lead=lead, **amount, **contingency_scores(y[:, j], p[:, j], threshold))
                        for threshold in (1, 5))
    pd.DataFrame(rows).to_csv(PUBLIC / "hourly_metrics.csv", index=False, lineterminator="\n")
    return len(y), len(np.unique(samples.ids(idx))), paired_hour_intervals(times, y, new, forecasts["BiLSTM_R"])


def score_day(artifacts, device):
    development = development_examples()
    calibration = development[development.split.eq("cal")]
    old = gfs_final.BASE / "holdout_predictions_private.parquet"
    frame = pd.read_parquet(old, filters=[("evaluation_set", "=", "test2025_legacy")]).sort_values(
        ["issue_utc", "station_id", "horizon"]).reset_index(drop=True)
    keys = ["station_id", "issue_utc", "horizon"]
    if len(frame) != 18723 * 3 or frame.duplicated(keys).any() or frame.station_id.nunique() != 57:
        raise ValueError("Daily paired evaluation rows changed")
    frame["evaluation_set"] = "retrospective2025_legacy"
    raw = arrays(frame, "N3")
    outputs = []
    hp = gfs_final.protocol()["candidate_linear6"]
    for artifact in artifacts:
        if artifact["features"] != raw["names"]:
            raise ValueError("Feature order differs between daily fit and scoring")
        model = day_model(len(raw["names"]), hp["head"]).to(device)
        model.load_state_dict(artifact["state"])
        norm = artifact["normalizers"]
        outputs.append(predict(model, tensors(raw, norm), norm["target_scale"], device))
    for name in ("mean", "median"):
        frame[f"{DAY_CANDIDATE}_{name}"] = np.mean([out[name] for out in outputs], axis=0).ravel()
    thresholds = cutoffs()
    for j in range(3):
        h = j + 1
        mask = frame.horizon.eq(h)
        cal = calibration[calibration.horizon.eq(h)].reset_index(drop=True)
        _, oof, calibrators = crossfit_calibration(
            cal, [a["calibration"]["wet"][:, j] for a in artifacts],
            [a["calibration"]["conditional"][:, j] for a in artifacts])
        thresholds[(DAY_CANDIDATE, h)], _ = choose_cutoff(cal, oof, np.arange(.05, 1., .05).round(2))
        prob = np.mean([apply_calibrators(o["wet"][:, j], o["conditional"][:, j], c)
                        for o, c in zip(outputs, calibrators)], axis=0)
        if not np.isfinite(prob).all() or not ((prob[:, 1] <= prob[:, 0]) & (prob[:, 1] >= 0) & (prob[:, 0] <= 1)).all():
            raise ValueError("Daily probability nesting invalid")
        frame.loc[mask, [f"{DAY_CANDIDATE}_p1", f"{DAY_CANDIDATE}_p50"]] = prob
    scores = summary_tables(frame, DAILY_MODELS, thresholds)
    for name in ("point_metrics", "probability_metrics", "event_metrics"):
        scores[name].to_csv(PUBLIC / f"daily_{name}.csv", index=False, lineterminator="\n")
    cfg = PROTOCOL["bootstrap"]
    policy = dict(primary_feature_contrasts=[], primary_skill_contrasts=[],
                  secondary_contrasts=[[DAY_CANDIDATE, "GRU_N3"]],
                  uncertainty=dict(draws=cfg["draws"], block_days=cfg["days"], seed=cfg["seed"]))
    intervals = bootstrap_comparisons(frame, (DAY_CANDIDATE, "GRU_N3"), policy)
    result = intervals.loc[intervals.metric.eq("mean_rmse"), ["horizon", "model", "reference",
                                                              "difference", "ci95_low", "ci95_high"]].rename(
        columns={"horizon": "lead", "model": "candidate", "difference": "delta_rmse"})
    return len(frame)//3, frame.station_id.nunique(), result.assign(task="day").to_dict("records")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args = parser.parse_args()
    device = torch.device(args.device)
    torch.set_num_threads(4)
    torch.backends.cudnn.deterministic = True
    threadpool_limits(limits=4)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    manifest, scaler = read_fit(hourly.PRIVATE)
    hourly_digest = hourly.sha256(hourly.SOURCE)
    if hourly_digest != manifest["training"]["dataset_sha256"]:
        raise ValueError("Hourly input digest differs from reference")
    old_day = gfs_final.OLD / "predictions_private.parquet"
    identity = dict(protocol=hourly.sha256(PROTOCOL_PATH), script=hourly.sha256(Path(__file__)),
                    device=args.device, hourly_input=hourly_digest,
                    daily_development=hourly.sha256(old_day))
    lock_path = PRIVATE / "architecture_training_lock.json"
    if lock_path.is_file() and json.loads(lock_path.read_text(encoding="utf-8")) != identity:
        raise ValueError("Private comparison already contains fits with a different contract")
    hourly.write_json(lock_path, identity)
    hour, day = train_candidates(scaler, hourly.sha256(lock_path), device)
    artifacts = {p.name: hourly.sha256(p) for p in sorted(PRIVATE.glob("*_seed*.pt"))}
    hourly.write_json(PRIVATE / "architecture_model_freeze.json", artifacts)

    n_hour, stations_hour, hourly_ci = score_hour(hour, scaler, device)
    n_day, stations_day, daily_ci = score_day(day, device)
    pd.DataFrame(hourly_ci + daily_ci).to_csv(PUBLIC / "paired_rmse.csv", index=False, lineterminator="\n")
    details = {skill: [{k: v for k, v in run.items() if isinstance(v, (float, int))} for run in values]
               for skill, values in (("hour", hour), ("day", day))}
    hourly.write_json(PUBLIC / "verification.json", dict(
        status="completed", run_device=torch.cuda.get_device_name(device) if device.type == "cuda" else "CPU",
        n_hour_origs=n_hour, hourly_stations=stations_hour, n_daily_origs=n_day, daily_stations=stations_day,
        fit_details=details, checkpoints=artifacts, probability_nesting_checked=True,
        interpretation="Retroactive paired comparison on the already examined 2025 samples"))
    print(f"Completed: {n_hour:,} hourly and {n_day:,} daily station-issue pairs.", flush=True)


if __name__ == "__main__":
    main()
