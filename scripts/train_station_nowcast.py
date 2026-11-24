"""Train the three paired station configurations; never read the test labels."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from time import perf_counter

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import lightgbm as lgb
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import station_nowcast as ns


def amount_rmse(y, f):
    return float(np.sqrt(np.mean(np.square(y - f), dtype=np.float64)))


def fit_bilstm(data, samples, mode, seed, out):
    hp = ns.PROTOCOL["bilstm"]
    torch.manual_seed(seed)
    torch.backends.cudnn.deterministic = True
    model = ns.PooledBiLSTM(len(samples.stations)).to(data.device)
    opt = torch.optim.AdamW(model.parameters(), lr=hp["learning_rate"], fused=data.device.type == "cuda")
    train = torch.as_tensor(samples.origins["train"], device=data.device)
    cal = samples.origins["cal"]
    best, best_state, stalls, best_epoch = float("inf"), None, 0, 0
    history = []
    log_targets = torch.log1p(data.y)
    for epoch in range(1, hp["max_epochs"] + 1):
        start = perf_counter()
        model.train()
        total = torch.zeros((), device=data.device)
        shuffled = train[torch.randperm(len(train), device=data.device)]
        for batch in shuffled.split(hp["batch_size"]):
            x, sid = data.window(batch, mode)
            opt.zero_grad(set_to_none=True)
            loss = torch.nn.functional.mse_loss(model(x, sid), log_targets[batch])
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            total += loss.detach() * len(batch)
        error = amount_rmse(samples.y[cal], ns.predict(model, data, cal, mode, hp["batch_size"]))
        elapsed = perf_counter() - start
        history.append(dict(epoch=epoch, loss=float(total) / len(train), cal_rmse=error, seconds=elapsed))
        print(f"{mode} seed={seed} epoch={epoch:02} cal_RMSE={error:.5f} s={elapsed:.1f}", flush=True)
        ns.write_json(out / "progress.json", dict(mode=mode, seed=seed, epoch=epoch, cal_RMSE=error))
        if error < best:
            best, best_epoch, stalls = error, epoch, 0
            best_state = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}
        else:
            stalls += 1
        if epoch >= hp["min_epochs"] and stalls >= hp["patience"]:
            break
    ckpt = out / f"{mode}_seed{seed}.pt"
    pending = ckpt.with_suffix(".pending")
    torch.save(dict(state_dict=best_state, mode=mode, seed=seed, epoch=best_epoch,
                    cal_rmse=best, history=history), pending)
    pending.replace(ckpt)
    return ckpt


def fit_trees(samples, out):
    hp = ns.PROTOCOL["rain_lightgbm"]
    train, cal = (samples.origins[role] for role in ("train", "cal"))
    args = dict(objective="regression", metric="rmse", learning_rate=0.07,
                num_leaves=hp["num_leaves"], min_data_in_leaf=hp["min_data_in_leaf"],
                max_bin=63, seed=hp["seed"], num_threads=8, verbosity=-1,
                deterministic=True, force_col_wise=True)
    paths = [out / f"LightGBM_R_h{hour}.txt" for hour in ns.LEADS]
    if all(path.is_file() for path in paths):
        return paths
    a, b = [ns.rain_tree_features(samples.x, ix, samples.station_index) for ix in (train, cal)]
    for j, path in enumerate(paths):
        if path.is_file():
            continue
        start = perf_counter()
        columns = [a.shape[1] - 1]
        tree = lgb.train(
            args, lgb.Dataset(a, label=samples.y[train, j], categorical_feature=columns),
            num_boost_round=hp["num_boost_round"],
            valid_sets=[lgb.Dataset(b, label=samples.y[cal, j], categorical_feature=columns)],
            callbacks=[lgb.early_stopping(hp["early_stopping_rounds"], verbose=False)],
        )
        pending = path.with_suffix(".pending")
        tree.save_model(str(pending), num_iteration=tree.best_iteration)
        pending.replace(path)
        print(f"LightGBM_R h{j + 1}: trees={tree.best_iteration} s={perf_counter() - start:.1f}", flush=True)
        ns.write_json(out / "progress.json", dict(mode="LightGBM_R", lead_hour=j + 1, trees=tree.best_iteration))
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ns.SOURCE)
    parser.add_argument("--out", type=Path, default=ns.PRIVATE)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    inp = ns.sha256(args.source)
    if inp != ns.PROTOCOL["dataset_sha256"]:
        raise ValueError("Hourly Parquet digest differs from the registered release")
    lock_path = args.out / "train_lock.json"
    frozen = dict(dataset_sha256=inp, hashes={
        str(p.relative_to(ns.ROOT).as_posix()): ns.sha256(p)
        for p in (Path(__file__).resolve(), Path(ns.__file__), ns.REPORT / "protocol.json",
                  ns.ROOT / "src/hourly_station_update.py", ns.ROOT / "src/station_forecast_data.py")
    })
    if lock_path.exists() and json.loads(lock_path.read_text(encoding="utf-8")) != frozen:
        raise ValueError("Existing training artifacts use a different registered configuration")
    ns.write_json(lock_path, frozen)
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA unavailable. Select --device cpu to run on a CPU.")
    torch.set_num_threads(min(8, os.cpu_count() or 1))
    print("Reading verified training and calibration windows", flush=True)
    samples = ns.read_samples(args.source, ("train", "cal"), fit_scaler=True)
    samples.coverage.to_csv(args.out / "train_station_coverage.csv", index=False)
    mean, std = ns.fit_scaling(samples)
    roster_path = args.out / "scaler.json"
    active = samples.coverage.loc[samples.coverage.train.gt(0), "station_id"].tolist()
    ns.write_json(roster_path, dict(mean=mean.tolist(), std=std.tolist(), features=ns.ALL,
                                  roster=samples.stations, train_stations=active))
    print(f"{len(active)} stations: {len(samples.origins['train']):,} train / "
          f"{len(samples.origins['cal']):,} calibration samples", flush=True)
    data = ns.WindowTensors(samples.x, samples.y, samples.station_index, mean, std, device)
    artifacts = [roster_path, args.out / "train_station_coverage.csv"]
    cal = samples.origins["cal"]
    y = samples.y[cal]
    rmse = {"Persistence": amount_rmse(y, samples.x[cal, 0, None])}
    runs = []
    for mode in ns.FEATURES:
        bag = np.zeros_like(y)
        for seed in ns.PROTOCOL["bilstm"]["seeds"]:
            ckpt = args.out / f"{mode}_seed{seed}.pt"
            if not ckpt.is_file():
                fit_bilstm(data, samples, mode, seed, args.out)
            payload = torch.load(ckpt, map_location="cpu", weights_only=True)
            model = ns.PooledBiLSTM(len(samples.stations)).to(device)
            model.load_state_dict(payload["state_dict"])
            bag += ns.predict(model, data, cal, mode)
            artifacts.append(ckpt)
            runs.append({k: payload[k] for k in ("mode", "seed", "epoch", "cal_rmse", "history")})
        rmse["BiLSTM_" + mode] = amount_rmse(y, bag / len(ns.PROTOCOL["bilstm"]["seeds"]))
    del data, model, bag
    if device.type == "cuda":
        torch.cuda.empty_cache()
    trees = fit_trees(samples, args.out)
    artifacts.extend(trees)
    x = ns.rain_tree_features(samples.x, cal, samples.station_index)
    tree_pred = np.column_stack([lgb.Booster(model_file=str(path)).predict(x, num_threads=8)
                                for path in trees]).clip(0)
    rmse["LightGBM_R"] = amount_rmse(y, tree_pred)
    replay = min(("Persistence", "BiLSTM_R", "LightGBM_R"), key=rmse.__getitem__)
    print("2023 calibration pooled RMSE", rmse, "Vrain-only replay choice", replay, flush=True)
    manifest = dict(training=frozen, n_train=len(samples.origins["train"]), n_cal=len(cal),
                    n_train_stations=len(active), device=torch.cuda.get_device_name(device)
                    if device.type == "cuda" else "CPU", torch_version=str(torch.__version__),
                    lightgbm_version=lgb.__version__, cal_rmse=rmse, replay_method=replay, runs=runs,
                    artifacts={p.name: ns.sha256(p) for p in artifacts})
    final = args.out / "fit_manifest.json"
    if final.exists():
        # Keep the original complete fit bundle immutable on retries.
        previous = json.loads(final.read_text(encoding="utf-8"))
        if (previous["artifacts"] != manifest["artifacts"] or previous["replay_method"] != replay):
            raise ValueError("Existing fit manifest does not match checkpoint bundle")
    else:
        ns.write_json(final, manifest)
    ns.write_json(args.out / "progress.json", dict(status="fit_complete", replay_method=replay))


if __name__ == "__main__":
    main()
