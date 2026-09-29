"""Ngưỡng riêng theo horizon và kiểm định theo thời gian mở rộng.

Toàn bộ cấu hình được ghi trước khi đọc test. Ba fold chỉ dùng dữ liệu
trước test cũ; mỗi fold fit scaler/model trên quá khứ, chọn checkpoint và
ngưỡng trên calibration, rồi đánh giá giai đoạn kế tiếp.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import RobustScaler
from torch.utils.data import DataLoader

from src.dataset_prep import TimeSeriesWindowDataset, _window_starts, prepare_datasets
from src.event_evaluation import detection_scores, score_episodes
from src.rain_alert_model import RainAlertBiLSTM, RainAlertConfig
from src.train_rain_alert import fit_alert_model, predict_alert
from src.train_bilstm import TrainingConfig, train_bilstm, predict
from src.visualize_and_evaluate import _metrics
from run_rain_alert_experiment import _jsonable, _evaluate_split, _load_standard, select_threshold

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "threshold_temporal_study"
LOG = logging.getLogger(__name__)
POLICY_NAMES = ("dual_global", "dual_precision30", "standard", "persistence")
FOLDS = (
    ("F1", "2023-01-01", "2023-07-01", "2024-01-01"),
    ("F2", "2023-07-01", "2024-01-01", "2024-07-01"),
    ("F3", "2024-01-01", "2024-07-01", "2024-12-01"),
)


def save_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(_jsonable(obj), ensure_ascii=False, indent=2, allow_nan=False),
                    encoding="utf-8")


def choose_precision_thresholds(y: np.ndarray, probability: np.ndarray,
                                floor: float = .30, min_alerts: int = 10) -> tuple[dict, pd.DataFrame]:
    """Tối đa recall dưới ràng buộc precision; không đủ bằng chứng thì tắt horizon."""
    if y.shape != probability.shape or y.ndim != 2:
        raise ValueError("Nhãn/xác suất phải là ma trận cùng kích thước")
    if not np.isfinite(y).all() or not np.isfinite(probability).all():
        raise ValueError("Không chấp nhận nhãn hoặc xác suất khuyết")
    rows, chosen = [], []
    for h in range(y.shape[1]):
        candidates = []
        for threshold in np.r_[np.arange(.40, .951, .05), .99]:
            threshold = round(float(threshold), 2)
            s = detection_scores(y[:, h], np.where(probability[:, h] >= threshold, 6., 0.))
            row = {"horizon_h": h + 1, "threshold": threshold, **s}
            row["n_alerts"] = s["TP"] + s["FP"]
            row["eligible"] = (s["precision"] is not None and s["precision"] >= floor
                               and row["n_alerts"] >= min_alerts and s["TP"] > 0)
            rows.append(row)
            if row["eligible"]:
                candidates.append(row)
        if candidates:
            best = max(candidates, key=lambda r: (r["POD_recall"], r["precision"], r["threshold"]))
            chosen.append({"horizon_h": h + 1, "threshold": best["threshold"], "enabled": True,
                           "calibration_precision": best["precision"],
                           "calibration_recall": best["POD_recall"], "n_alerts": best["n_alerts"]})
        else:
            chosen.append({"horizon_h": h + 1, "threshold": 1., "enabled": False,
                           "calibration_precision": None, "calibration_recall": 0., "n_alerts": 0})
    return {"precision_floor": floor, "minimum_calibration_alerts": min_alerts,
            "selection_rule": "Max recall, then precision, then threshold; abstain if infeasible",
            "horizons": chosen}, pd.DataFrame(rows)


def policy_mask(probability: np.ndarray, policy: dict) -> np.ndarray:
    values = policy["horizons"]
    if len(values) != probability.shape[1]:
        raise ValueError("Số ngưỡng không khớp horizon")
    return ((probability >= np.array([h["threshold"] for h in values]))
            & np.array([h["enabled"] for h in values]))


def evaluate_table(table: pd.DataFrame, policy: dict, global_threshold: float,
                   tag: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    table = table.copy()
    detail = []
    for h, group in table.groupby("horizon_h", sort=True):
        group = group.sort_values("valid_datetime")
        y = group.actual_mm.to_numpy()
        p = group.dual_heavy_probability.to_numpy()
        chosen = policy["horizons"][int(h) - 1]
        masks = {"dual_global": p >= global_threshold,
                 "dual_precision30": (p >= chosen["threshold"]) & chosen["enabled"],
                 "standard": group.standard_amount_mm.to_numpy() > 5,
                 "persistence": group.persistence_mm.to_numpy() > 5}
        table.loc[group.index, "precision30_alert"] = masks["dual_precision30"]
        for name in POLICY_NAMES:
            amount = group[{"dual_global": "dual_amount_mm", "dual_precision30": "dual_amount_mm",
                            "standard": "standard_amount_mm", "persistence": "persistence_mm"}[name]].to_numpy()
            scores = detection_scores(y, np.where(masks[name], 6., 0.))
            events, _ = score_episodes(pd.DatetimeIndex(group.valid_datetime), y,
                                       np.where(masks[name], 6., 0.))
            detail.append({"period": tag, "horizon_h": int(h), "policy": name,
                           "n_pairs": len(y), **_metrics(y, amount), **scores, **events})
    detailed = pd.DataFrame(detail)
    aggregate = []
    for name, g in detailed.groupby("policy", sort=False):
        tp, fp, fn, tn = (int(g[c].sum()) for c in ("TP", "FP", "FN", "TN"))
        observed, forecast, hit = (int(g[c].sum()) for c in
                                  ("observed_events", "forecast_events", "detected_observed_events"))
        amount_col = {"dual_global": "dual_amount_mm", "dual_precision30": "dual_amount_mm",
                      "standard": "standard_amount_mm", "persistence": "persistence_mm"}[name]
        aggregate.append({"period": tag, "policy": name, **_metrics(table.actual_mm, table[amount_col]),
                          "TP": tp, "FP": fp, "FN": fn, "TN": tn,
                          "precision": tp/(tp+fp) if tp+fp else None,
                          "recall": tp/(tp+fn) if tp+fn else None,
                          "hourly_F1": 2*tp/(2*tp+fp+fn) if tp+fn else None,
                          "event_observed": observed, "event_forecast": forecast, "event_hit": hit,
                          "event_precision": hit/forecast if forecast else None,
                          "event_recall": hit/observed if observed else None,
                          "event_F1": 2*hit/(observed+forecast) if observed else None})
    table["precision30_alert"] = table["precision30_alert"].astype(bool)
    return pd.DataFrame(aggregate), detailed, table


def explicit_datasets(frame: pd.DataFrame, feature_cols: list[str], train_end: pd.Timestamp,
                      calibration_end: pd.Timestamp, assessment_end: pd.Timestamp):
    """Fit scaler trên các hàng train; cả 6 giờ nhãn phải thuộc cùng một khoảng."""
    frame = frame.loc[frame.datetime < assessment_end].sort_values("datetime").reset_index(drop=True)
    times = pd.DatetimeIndex(frame.datetime)
    if not times[0] < train_end < calibration_end < assessment_end:
        raise ValueError("Ranh giới thời gian không hợp lệ")
    values = frame[feature_cols].to_numpy(dtype=float)
    target = frame.precipitation.to_numpy(dtype=float)
    valid = np.isfinite(values).all(axis=1) & np.isfinite(target) & (target >= 0)
    fit = valid & (times < train_end)
    scaler = RobustScaler().fit(frame.loc[fit, feature_cols])
    transformed = np.full(values.shape, np.nan, dtype=np.float32)
    transformed[valid] = scaler.transform(frame.loc[valid, feature_cols]).astype(np.float32)
    starts, _ = _window_starts(times.as_unit("ns").asi8, valid, 30)
    first, last = times.take(starts+24), times.take(starts+29)
    parts = [starts[last < train_end], starts[(first >= train_end) & (last < calibration_end)],
             starts[(first >= calibration_end) & (last < assessment_end)]]
    datasets = [TimeSeriesWindowDataset(transformed, target.astype(np.float32), times, s, 24, 6)
                for s in parts]
    if any(len(ds) == 0 for ds in datasets):
        raise ValueError("Khoảng thời gian không đủ cửa sổ")
    loaders = [DataLoader(ds, batch_size=256, shuffle=i == 0, num_workers=0,
                          pin_memory=torch.cuda.is_available()) for i, ds in enumerate(datasets)]
    return datasets, loaders, scaler


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="cuda", choices=("cpu", "cuda"))
    parser.add_argument("--skip-folds", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA không khả dụng")
    OUT.mkdir(parents=True, exist_ok=True)
    protocol = {"precision_floor": .30, "minimum_calibration_alerts": 10,
                "threshold_candidates": [round(float(t),2) for t in np.r_[np.arange(.4,.951,.05),.99]],
                "seed": 42, "max_epochs": 30, "patience": 7, "folds": FOLDS,
                "old_test_is_exploratory": True,
                "calibration_rule": "Checkpoint by calibration loss; thresholds by calibration labels only",
                "fold_scope": "All fold labels precede 2024-12-01; original test excluded"}
    save_json(OUT / "protocol.json", protocol)
    features = pd.read_parquet(ROOT / "data/processed/surface_only/features.parquet")
    prepared = prepare_datasets(features, batch_size=512, scaler_path=None, shuffle_train=False)
    dual_path = ROOT / "models/surface_only/rain_alert_dual_head.pth"
    saved = torch.load(dual_path, map_location="cpu", weights_only=True)
    if saved["feature_cols"] != prepared.feature_cols:
        raise ValueError("Checkpoint không khớp đặc trưng")
    old_scaler = joblib.load(ROOT / "models/surface_only/scaler.pkl")
    if not np.allclose(old_scaler.center_, prepared.scaler.center_) or not np.allclose(old_scaler.scale_, prepared.scaler.scale_):
        raise ValueError("Scaler không khớp")
    dual = RainAlertBiLSTM(len(prepared.feature_cols), 6).to(device)
    dual.load_state_dict(saved["model_state_dict"])
    standard = _load_standard(ROOT / "models/surface_only/best_surface_model.pth", prepared.feature_cols, device)
    y, a, p = predict_alert(dual, prepared.val_loader, device)
    sy, sa = predict(standard, prepared.val_loader, device)
    if not np.array_equal(y, sy):
        raise ValueError("Validation không cùng thứ tự")
    policy, sweep = choose_precision_thresholds(y, p)
    policy["checkpoint_sha256"] = hashlib.sha256(dual_path.read_bytes()).hexdigest()
    policy["fitted_on"] = "original_validation_only"
    save_json(OUT / "selected_thresholds.json", policy)
    sweep.to_csv(OUT / "validation_threshold_sweep.csv", index=False)
    _, val_table = _evaluate_split("validation", prepared.val_dataset, y,a,p,sa,.4)
    val_table.to_parquet(OUT / "validation_predictions.parquet", index=False)
    va, vd, _ = evaluate_table(val_table, policy, .4, "original_validation")
    va.to_csv(OUT / "validation_metrics.csv", index=False)
    # Ngưỡng đã được ghi trước khi mở tập test cũ; đánh giá này là chẩn đoán.
    test_table = pd.read_parquet(ROOT / "reports/rain_alert_experiment/test_predictions.parquet")
    ta, td, test_table = evaluate_table(test_table, policy, .4, "old_test_exploratory")
    ta.to_csv(OUT / "test_metrics.csv", index=False)
    td.to_csv(OUT / "test_metrics_by_horizon.csv", index=False)
    test_table.to_parquet(OUT / "test_predictions.parquet", index=False)
    LOG.info("Ngưỡng validation đã chốt: %s", [r["threshold"] if r["enabled"] else "OFF" for r in policy["horizons"]])
    if args.skip_folds:
        return
    aggregates, details, fold_summaries = [], [], []
    for name, tr_end, cal_end, assess_end in FOLDS:
        fold_dir = OUT / name
        fold_dir.mkdir(exist_ok=True)
        dates = [pd.Timestamp(t, tz="Asia/Ho_Chi_Minh") for t in (tr_end, cal_end, assess_end)]
        datasets, loaders, scaler = explicit_datasets(features, prepared.feature_cols, *dates)
        joblib.dump(scaler, fold_dir / "scaler.pkl")
        LOG.info("%s train/calibration/assessment=%s", name, [len(ds) for ds in datasets])
        standard_fit = train_bilstm(loaders[0], loaders[1], None, feature_cols=prepared.feature_cols,
                                    checkpoint_path=fold_dir / "standard.pth",
                                    config=TrainingConfig(max_epochs=30, device=args.device))
        dual_fit, history, best_epoch = fit_alert_model(loaders[0], loaders[1], feature_cols=prepared.feature_cols,
                                                       checkpoint_path=fold_dir / "dual.pth", device=device,
                                                       config=RainAlertConfig())
        pd.DataFrame(standard_fit.history).to_csv(fold_dir / "standard_history.csv", index=False)
        pd.DataFrame(history).to_csv(fold_dir / "dual_history.csv", index=False)
        cy, ca, cp = predict_alert(dual_fit, loaders[1], device)
        global_threshold, _ = select_threshold(cy, cp, datasets[1].target_datetimes)
        fold_policy, fold_sweep = choose_precision_thresholds(cy, cp)
        save_json(fold_dir / "thresholds.json", {"global_threshold": global_threshold, **fold_policy})
        fold_sweep.to_csv(fold_dir / "calibration_threshold_sweep.csv", index=False)
        # Assessment chỉ được suy luận sau khi chốt policy của fold.
        ey, ea, ep = predict_alert(dual_fit, loaders[2], device)
        sey, sea = predict(standard_fit.model, loaders[2], device)
        if not np.array_equal(ey, sey):
            raise ValueError("Hai model không cùng mẫu assessment")
        _, table = _evaluate_split(name, datasets[2], ey,ea,ep,sea,global_threshold)
        agg, det, table = evaluate_table(table, fold_policy, global_threshold, name)
        table.to_parquet(fold_dir / "assessment_predictions.parquet", index=False)
        aggregates.append(agg); details.append(det)
        fold_summaries.append({"fold": name, "train_end_exclusive": dates[0].isoformat(),
                               "calibration_end_exclusive": dates[1].isoformat(),
                               "assessment_end_exclusive": dates[2].isoformat(),
                               "windows": [len(ds) for ds in datasets],
                               "standard_best_epoch": standard_fit.best_epoch,
                               "dual_best_epoch": best_epoch, "global_threshold": global_threshold,
                               "precision_thresholds": fold_policy["horizons"]})
        LOG.info("%s hoàn tất", name)
    pd.concat(aggregates, ignore_index=True).to_csv(OUT / "temporal_metrics.csv", index=False)
    pd.concat(details, ignore_index=True).to_csv(OUT / "temporal_metrics_by_horizon.csv", index=False)
    save_json(OUT / "fold_summary.json", fold_summaries)


if __name__ == "__main__":
    main()
