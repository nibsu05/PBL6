"""Kiểm tra dataloader v2 trên dữ liệu thật: số mẫu theo phần/mùa, tốc độ đọc batch, căn chỉnh thời gian.

Tạo ``cube_cell_major.npy`` nếu chưa có, lưu bộ chuẩn hóa của từng cấu hình vào
``data/processed/dataset_v2/normalizers/`` và tóm tắt vào ``reports/dataloader_v2/summary.json``.

Chạy:
    python scripts/inspect_dataloader_v2.py
"""

from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import argparse
import logging
import time

import numpy as np
import pandas as pd

from src.dataloader_v2 import (CUBE, DATASET_DIR, DEFAULT_SPLIT, LABEL, DatasetV2, Normalizer, WindowSampler,
                               build_cell_major, product_a, product_b, sample_index, season_of)

CACHE = DATASET_DIR / "index_cache"
NORMS = DATASET_DIR / "normalizers"
OUT = ROOT / "reports" / "dataloader_v2"
CONFIGS = {
    "A: S0 (A0)": product_a(["A0"], latency_h=None),
    "A: S1 (A0+A1, trễ 4 h)": product_a(["A0", "A1"], latency_h=4),
    "A: đầy đủ (A0–A5, trễ 4 h)": product_a(["A0", "A1", "A2", "A3", "A4", "A5"], latency_h=4),
    "B: đầy đủ (B0–B5, trễ 4 h)": product_b(["B0", "B1", "B2", "B3", "B4", "B5"], latency_h=4),
}

LOGGER = logging.getLogger("inspect_dataloader")


def check_alignment(ds: DatasetV2, sampler: WindowSampler, index: np.ndarray, n: int = 50, seed: int = 0) -> int:
    """So nhãn trong batch với cube gốc tại đúng giờ đích; trả về số mẫu lệch."""
    rng = np.random.default_rng(seed)
    pick = index[rng.choice(len(index), min(n, len(index)), replace=False)]
    lab = ds.feature_index[LABEL]
    bad = 0
    for c, t in pick:
        y = sampler.get(int(c), int(t))["y"]
        ref = np.asarray(ds.cube[c, t:t + sampler.cfg.horizon, lab])
        bad += int(not np.allclose(y, ref, equal_nan=True))
    return bad


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DATASET_DIR)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    dataset_dir, out = args.dataset_dir, args.out
    cache, norms = dataset_dir / "index_cache", dataset_dir / "normalizers"
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not (dataset_dir / CUBE).exists():
        LOGGER.info("Tạo %s …", CUBE)
        build_cell_major(dataset_dir)
    ds = DatasetV2(dataset_dir)
    norms.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, cfg in CONFIGS.items():
        t0 = time.time()
        splits = {s: sample_index(ds, cfg, years, cache_dir=cache) for s, years in DEFAULT_SPLIT.items()}
        t_index = time.time() - t0
        norm = Normalizer.fit(ds, cfg, DEFAULT_SPLIT["train"])
        norm.save(norms / f"{cfg.key()}.json")
        sampler = WindowSampler(ds, cfg, norm)
        rng = np.random.default_rng(0)
        train = splits["train"]
        batch_idx = train[rng.choice(len(train), 256, replace=False)]
        t0 = time.time()
        batch = sampler.batch(batch_idx)
        t_batch = time.time() - t0
        finite = all(np.isfinite(batch[k]).all() for k in ("x_past", "x_future", "static", "y"))
        info = {
            "config_key": cfg.key(),
            "groups": list(cfg.groups), "latency_h": cfg.latency_h,
            "input_len": cfg.input_len, "horizon": cfg.horizon,
            "n_features": {"x_past": int(batch["x_past"].shape[-1]), "x_future": int(batch["x_future"].shape[-1]),
                           "static": int(batch["static"].shape[-1])},
            "samples": {s: int(len(ix)) for s, ix in splits.items()},
            "samples_by_season_test": pd.Series(season_of(ds, splits["test"])).value_counts().to_dict(),
            "cells": int(len(np.unique(train[:, 0]))),
            "index_seconds": round(t_index, 1), "batch256_seconds": round(t_batch, 3),
            "batch_all_finite": bool(finite),
            "alignment_mismatches_of_50": check_alignment(ds, sampler, splits["test"]),
            "train_label_mean_mm_h": round(float(batch["y"].mean()), 3),
            "x_past_names": sampler.x_past_names, "x_future_names": sampler.future_names,
        }
        summary[name] = info
        LOGGER.info("%s: train %d · val %d · val_ops %d · test %d mẫu; %d ô; đặc trưng past/future/static = %s; "
                    "batch 256 mất %.2f s; hữu hạn=%s; lệch=%d", name, *info["samples"].values(), info["cells"],
                    tuple(info["n_features"].values()), t_batch, finite, info["alignment_mismatches_of_50"])
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGGER.info("Ghi %s", out / "summary.json")
    if any(not info["batch_all_finite"] or info["alignment_mismatches_of_50"] for info in summary.values()):
        raise SystemExit("Dataloader không đạt kiểm tra hữu hạn/căn chỉnh")


if __name__ == "__main__":
    main()
