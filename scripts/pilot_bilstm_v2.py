r"""Pilot S0/S1/S4 tại Đà Nẵng, 2 seed, train 2015–21 / chọn epoch + hiệu chỉnh 2022 / so cặp 2023.

Không chấm mô hình trên test 2025. Mọi cấu hình dùng cùng chỉ số cửa sổ hợp lệ của S4.
Chạy: .venv\Scripts\python.exe scripts/pilot_bilstm_v2.py
Checkpoint/dự báo riêng tư ở data/processed/pilot_bilstm_v2; báo cáo ở reports/pilot_bilstm_v2.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
import random
import sys
import subprocess
import time
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression
from src.bilstm_v2 import AGG_WINDOWS, THRESHOLDS, BiLSTMV2, pilot_loss
from src.dataloader_v2 import DATASET_DIR, DatasetV2, Normalizer, WindowSampler, epoch_subset, product_a, sample_index
from src.verification import (brier_skill_score, brier_score, continuous_scores, contingency_scores,
                              metric_csi, paired_block_bootstrap)

LOGGER = logging.getLogger("pilot")
GROUPS = {"S0": ("A0",), "S1": ("A0", "A1"), "S4": ("A0", "A1", "A2", "A3", "A4")}


def choose_cells(ds, n, seed=42):
    cells = ds.cells[ds.cells.province == "Đà Nẵng"].copy()
    if not 1 <= n <= len(cells):
        raise ValueError(f"Số ô phải từ 1 đến {len(cells)}")
    # Chọn trước khi xem nhãn: phân tầng theo độ cao và khoảng cách tới biển.
    cells["stratum"] = (pd.qcut(cells.elev_mean_m.rank(method="first"), 3, labels=False) * 3 +
                        pd.qcut(cells.coast_dist_km.rank(method="first"), 3, labels=False))
    rng = np.random.default_rng(seed)
    pools = [list(rng.permutation(g.index)) for _, g in cells.groupby("stratum")]
    selected = []
    while len(selected) < n:
        for pool in pools:
            if pool and len(selected) < n:
                selected.append(pool.pop())
    return np.array(sorted(selected), dtype=int)


def totals(y):
    return np.stack([y[:, lo:hi].sum(1) for lo, hi in AGG_WINDOWS], axis=1)


def labels(ds, index):
    out = np.empty((len(index), 6), dtype=np.float32)
    for c in np.unique(index[:, 0]):
        rows = np.flatnonzero(index[:, 0] == c)
        t = index[rows, 1]
        out[rows] = ds.cube[c, t[:, None] + np.arange(6), ds.feature_index["y_gsmap_gc_mm"]]
    return out


def iterate(sampler, index, batch_size, device):
    for start in range(0, len(index), batch_size):
        batch = sampler.batch(index[start:start + batch_size])
        yield {k: torch.from_numpy(batch[k]).to(device) for k in ("x_past", "x_future", "static", "y")}


@torch.no_grad()
def predict(model, sampler, index, batch_size, device):
    model.eval()
    amounts, logits = [], []
    for batch in iterate(sampler, index, batch_size, device):
        amount, logit = model(batch["x_past"], batch["x_future"], batch["static"])
        amounts.append(torch.expm1(amount).cpu().numpy())
        logits.append(logit.cpu().numpy())
    return np.concatenate(amounts), np.concatenate(logits)


def calibrate(logits_cal, y_cal, logits_eval):
    events = (totals(y_cal)[:, :, None] >= np.array(THRESHOLDS)).reshape(-1, 9)
    probs, params = np.empty_like(logits_eval), []
    for j in range(9):
        target = events[:, j].astype(int)
        if len(np.unique(target)) == 2:
            clf = LogisticRegression(C=1.0, max_iter=200).fit(logits_cal[:, [j]], target)
            probs[:, j] = clf.predict_proba(logits_eval[:, [j]])[:, 1]
            params.append({"coef": float(clf.coef_[0, 0]), "intercept": float(clf.intercept_[0])})
        else:
            prob = float((target.sum() + 1) / (len(target) + 2))
            probs[:, j] = prob
            params.append({"constant": prob})
    return np.minimum.accumulate(probs.reshape(-1, 3, 3), axis=2), params


def climatology(ds, train, evaluation):
    # Cùng cửa sổ train, theo ô × tháng; chỉ dùng nhãn 2015–21.
    train_month = (ds.hours[train[:, 1]] + pd.Timedelta(hours=7)).month.to_numpy() - 1
    eval_month = (ds.hours[evaluation[:, 1]] + pd.Timedelta(hours=7)).month.to_numpy() - 1
    key = train[:, 0] * 12 + train_month
    eval_key = evaluation[:, 0] * 12 + eval_month
    n_bins = len(ds.cells) * 12
    count = np.bincount(key, minlength=n_bins)
    y = totals(labels(ds, train))
    amounts = np.stack([np.bincount(key, weights=y[:, j], minlength=n_bins) / np.maximum(count, 1)
                        for j in range(3)], axis=1)[eval_key]
    probs = np.empty((len(evaluation), 3, 3))
    for j in range(3):
        for k, threshold in enumerate(THRESHOLDS):
            hits = np.bincount(key, weights=y[:, j] >= threshold, minlength=n_bins)
            probs[:, j, k] = ((hits + 1) / (count + 2))[eval_key]
    return amounts, probs


def evaluate(ds, index, y, amounts, probabilities, reference):
    months = (ds.hours[index[:, 1]] + pd.Timedelta(hours=7)).month.to_numpy()
    seasons = np.where(np.isin(months, [11, 12, 1, 2]), "winter", np.where((months >= 5) & (months <= 10), "summer", "spring"))
    observed = totals(y)
    rows = []
    for source in amounts:
        for season in ("summer", "winter", "spring"):
            mask = seasons == season
            # Mùa đông chỉ chấm tổng 6 h; không gán thời điểm mưa nhãn thành sự thật theo giờ.
            for j in ([2] if season == "winter" else [0, 1, 2]):
                row = {"source": source, "season": season, "window": f"{AGG_WINDOWS[j][0]}-{AGG_WINDOWS[j][1]}h",
                       **continuous_scores(observed[mask, j], amounts[source][mask, j])}
                for k, threshold in enumerate(THRESHOLDS):
                    row[f"CSI>={threshold:g}"] = contingency_scores(observed[mask, j], amounts[source][mask, j], threshold)["CSI"]
                    row[f"BSS>={threshold:g}"] = brier_skill_score(observed[mask, j] >= threshold,
                        probabilities[source][mask, j, k], reference[mask, j, k])
                rows.append(row)
    return pd.DataFrame(rows), seasons


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DATASET_DIR)
    parser.add_argument("--cells", type=int, default=30)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43])
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--samples-per-epoch", type=int, default=30000)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--patience", type=int, default=4)
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--output-name", default="pilot_bilstm_v2")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    torch.set_num_threads(4)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.backends.cudnn.benchmark = False
    private = ROOT / "data/processed" / args.output_name
    report = ROOT / "reports" / args.output_name
    private.mkdir(parents=True, exist_ok=True)
    report.mkdir(parents=True, exist_ok=True)
    ds = DatasetV2(args.dataset_dir)
    selected = choose_cells(ds, args.cells)
    excluded = tuple(ds.cells.loc[~ds.cells.index.isin(selected), "site"])
    configs = {name: product_a(groups, latency_h=None if name == "S0" else 4,
                               provinces=("Đà Nẵng",), exclude_sites=excluded, issue_stride_h=6)
               for name, groups in GROUPS.items()}
    common_cfg = configs["S4"]
    train = sample_index(ds, common_cfg, range(2015, 2022))
    calibration = sample_index(ds, common_cfg, [2022])
    evaluation = sample_index(ds, common_cfg, [2023])
    if any(len(ix) == 0 for ix in (train, calibration, evaluation)):
        raise ValueError("Thiếu cửa sổ train/validation")
    for name, ix in (("train", train), ("calibration_2022", calibration), ("evaluation_2023", evaluation)):
        np.save(private / f"index_{name}.npy", ix)
    y_cal, y_eval = labels(ds, calibration), labels(ds, evaluation)
    clim_amount, clim_prob = climatology(ds, train, evaluation)
    amounts, probabilities = {"climatology": clim_amount}, {"climatology": clim_prob}
    for name, feature, offset in (("ERA5_perfect_prog", "era5_tp_mm", 0), ("persistence_L4", "gsmap_mm", -5)):
        yy = np.empty_like(y_eval)
        for c in selected:
            rows = np.flatnonzero(evaluation[:, 0] == c)
            t = evaluation[rows, 1]
            positions = t[:, None] + (np.arange(6) if offset == 0 else np.full(6, offset))
            yy[rows] = ds.cube[c, positions, ds.feature_index[feature]]
        amounts[name] = totals(yy)
        probabilities[name] = (amounts[name][:, :, None] >= np.array(THRESHOLDS)).astype(float)
    metadata = {"args": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}, "device": str(device), "torch": torch.__version__, "cuda": torch.version.cuda,
                "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
                "source_manifest_sha256": hashlib.sha256((ROOT / "data/DATA_MANIFEST_v2.json").read_bytes()).hexdigest(),
                "gpu": torch.cuda.get_device_name() if device.type == "cuda" else None,
                "cells": ds.cells.iloc[selected][["site", "elev_mean_m", "coast_dist_km"]].to_dict("records"),
                "samples": {"train": len(train), "calibration_2022": len(calibration), "evaluation_2023": len(evaluation)},
                "history": [], "test_2025_scored": False,
                "mode": "T-ERA5: ERA5 là tham chiếu perfect prog; chưa có đối chứng ECMWF vận hành"}
    LOGGER.info("%s; %d ô; train/cal/eval=%d/%d/%d", device, len(selected), len(train), len(calibration), len(evaluation))
    cal_subset = epoch_subset(calibration, 12000, 2022)
    for name, cfg in configs.items():
        norm = Normalizer.fit(ds, cfg, range(2015, 2022))
        norm.save(private / f"normalizer_{name}.json")
        sampler = WindowSampler(ds, cfg, norm)
        for seed in args.seeds:
            random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
            model = BiLSTMV2(len(sampler.x_past_names), len(sampler.future_names)).to(device)
            optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
            best_loss, best, stale = float("inf"), None, 0
            history = []
            t_start = time.perf_counter()
            for epoch in range(args.epochs):
                t_epoch = time.perf_counter()
                model.train()
                train_loss, n = 0.0, 0
                ix = epoch_subset(train, args.samples_per_epoch, seed * 1000 + epoch)
                for batch in iterate(sampler, ix, args.batch_size, device):
                    optimizer.zero_grad(set_to_none=True)
                    amount, logits = model(batch["x_past"], batch["x_future"], batch["static"])
                    loss = pilot_loss(amount, logits, batch["y"])
                    if not torch.isfinite(loss):
                        raise ValueError("Loss không hữu hạn")
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                    optimizer.step()
                    train_loss += loss.item() * len(batch["y"]); n += len(batch["y"])
                model.eval()
                cal_loss, n_cal = 0.0, 0
                with torch.no_grad():
                    for batch in iterate(sampler, cal_subset, args.batch_size, device):
                        aa, ll = model(batch["x_past"], batch["x_future"], batch["static"])
                        cal_loss += pilot_loss(aa, ll, batch["y"]).item() * len(batch["y"])
                        n_cal += len(batch["y"])
                cal_loss /= n_cal
                info = {"epoch": epoch + 1, "train_loss": train_loss / n, "val_2022_loss": cal_loss,
                        "seconds": time.perf_counter() - t_epoch}
                history.append(info)
                LOGGER.info("%s seed%d epoch%d train=%.4f val2022=%.4f %.1fs", name, seed, epoch + 1, train_loss / n, cal_loss, info["seconds"])
                if cal_loss < best_loss:
                    best_loss, best, stale = cal_loss, copy.deepcopy(model.state_dict()), 0
                else:
                    stale += 1
                    if stale >= args.patience:
                        break
            model.load_state_dict(best)
            run = f"{name}_seed{seed}"
            torch.save({"model": best, "config": cfg.__dict__, "seed": seed}, private / f"{run}.pt")
            _, cal_logits = predict(model, sampler, calibration, args.batch_size, device)
            pred, eval_logits = predict(model, sampler, evaluation, args.batch_size, device)
            prob, params = calibrate(cal_logits, y_cal, eval_logits)
            np.savez_compressed(private / f"{run}.npz", y=y_eval, amount=pred, probability=prob)
            amounts[run], probabilities[run] = totals(pred), prob
            metadata["history"].append({"run": run, "epochs": history, "calibration": params,
                                         "seconds_total": time.perf_counter() - t_start})
            (report / "run.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
            del model, optimizer
            if device.type == "cuda":
                torch.cuda.empty_cache()
        runs = [f"{name}_seed{s}" for s in args.seeds]
        amounts[name] = np.mean([amounts[r] for r in runs], axis=0)
        probabilities[name] = np.mean([probabilities[r] for r in runs], axis=0)
    table, seasons = evaluate(ds, evaluation, y_eval, amounts, probabilities, clim_prob)
    table.to_csv(report / "scores.csv", index=False)
    # So cặp trung bình dự báo 2 seed. CI đo bất định khối ngày; biến thiên seed nằm ở scores.csv.
    mask = seasons == "summer"
    frame = pd.DataFrame({"date": ds.hours[evaluation[mask, 1]], "obs": totals(y_eval)[mask, 0],
                          **{name: amounts[name][mask, 0] for name in GROUPS},
                          **{f"p_{name}": probabilities[name][mask, 0, 0] for name in GROUPS}})
    def bs_metric(obs, prob):
        return brier_score(obs >= 1, prob)
    bs_metric.lower_is_better = True
    bs_metric.__name__ = "BS>=1mm/3h"
    comparisons = []
    for a, b in combinations(GROUPS, 2):
        comparisons.append(paired_block_bootstrap(frame, "obs", a, b, metric_csi(10), n_boot=args.bootstrap))
        comparisons.append(paired_block_bootstrap(frame, "obs", f"p_{a}", f"p_{b}", bs_metric, n_boot=args.bootstrap))
    (report / "paired_bootstrap.json").write_text(json.dumps(comparisons, ensure_ascii=False, indent=2), encoding="utf-8")
    (report / "run.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGGER.info("Xong. Báo cáo %s", report)


if __name__ == "__main__":
    main()
