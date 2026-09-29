r"""Bi-LSTM bề mặt phủ đủ thời gian và thí nghiệm lấy mẫu đợt mưa lớn.

Chạy từ thư mục dự án::

    .venv\Scripts\python.exe run_surface_baseline.py

Hai biến thể dùng cùng split thời gian, scaler, validation và test. Chỉ
DataLoader của train thay đổi; kết quả đa nguồn cũ được giữ nguyên.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.dataset_prep import prepare_datasets
from src.event_sampling import build_event_sampled_loader
from src.feature_engineering import engineer_features
from src.merge_raw_data import SURFACE_COLUMNS
from src.train_bilstm import TrainingConfig, predict, train_bilstm
from src.visualize_and_evaluate import _metrics, evaluate_and_visualize

ROOT = Path(__file__).resolve().parent
LOGGER = logging.getLogger(__name__)
HEAVY_THRESHOLD = 5.0


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Baseline Bi-LSTM chỉ dùng Open-Meteo bề mặt")
    parser.add_argument("--surface-csv", type=Path,
                        default=ROOT / "data" / "raw_data" / "openmeteo_danang_2015_2026.csv")
    parser.add_argument("--variant", choices=("both", "standard", "event_balanced"), default="both")
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--max-epochs", type=int, default=40)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--heavy-draw-fraction", type=float, default=0.25)
    parser.add_argument("--prepare-only", action="store_true")
    return parser.parse_args()


def _load_surface(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path)
    required = {"datetime", *SURFACE_COLUMNS}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Open-Meteo thiếu cột: {missing}")
    frame = frame[["datetime", *SURFACE_COLUMNS]].copy()
    frame["datetime"] = pd.to_datetime(frame["datetime"], utc=True, errors="raise").dt.tz_convert(
        "Asia/Ho_Chi_Minh"
    )
    frame = frame.sort_values("datetime").reset_index(drop=True)
    if frame["datetime"].duplicated().any():
        raise ValueError("Open-Meteo có timestamp trùng; cần xử lý trước")
    if frame["datetime"].isna().any():
        raise ValueError("Open-Meteo có timestamp không hợp lệ")
    for name in SURFACE_COLUMNS:
        frame[name] = pd.to_numeric(frame[name], errors="coerce")
    return frame


def _detection_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float | int]:
    """Đo mưa >5 mm/h trên từng cặp horizon–giờ của tập test."""
    truth = np.asarray(y_true).ravel() > HEAVY_THRESHOLD
    predicted = np.asarray(y_pred).ravel() > HEAVY_THRESHOLD
    tp = int(np.sum(truth & predicted))
    fp = int(np.sum(~truth & predicted))
    fn = int(np.sum(truth & ~predicted))
    tn = int(np.sum(~truth & ~predicted))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "threshold_mm_per_hour": HEAVY_THRESHOLD,
        "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "precision": precision, "recall": recall, "F1": f1,
    }


def _write_json(path: Path, value: object) -> None:
    """Ghi JSON chuẩn; chỉ số không xác định (ví dụ CC của dự báo 0) là null."""
    def finite_json(item: object) -> object:
        if isinstance(item, dict):
            return {key: finite_json(entry) for key, entry in item.items()}
        if isinstance(item, (list, tuple)):
            return [finite_json(entry) for entry in item]
        if isinstance(item, (float, np.floating)) and not np.isfinite(item):
            return None
        if isinstance(item, np.generic):
            return item.item()
        return item

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(finite_json(value), ensure_ascii=False, indent=2, allow_nan=False),
                    encoding="utf-8")


def _naive_baselines(dataset) -> dict[str, dict]:
    """Đối chứng trên đúng các cửa sổ test của Bi-LSTM."""
    target_positions = (
        dataset.starts[:, None] + dataset.input_length
        + np.arange(dataset.output_length)[None, :]
    )
    actual = dataset.targets[target_positions]
    last_observed = dataset.targets[dataset.starts + dataset.input_length - 1]
    forecasts = {
        "zero": np.zeros_like(actual),
        "persistence": np.repeat(last_observed[:, None], dataset.output_length, axis=1),
    }
    heavy = actual > HEAVY_THRESHOLD
    return {
        name: {
            "metrics": _metrics(actual, prediction),
            "detection": _detection_metrics(actual, prediction),
            "heavy_mae": float(np.mean(np.abs(actual[heavy] - prediction[heavy]))) if heavy.any() else None,
        }
        for name, prediction in forecasts.items()
    }


def _select_variant(results: dict[str, dict]) -> tuple[str, str]:
    """Chọn model CHỈ bằng validation, giữ test để báo cáo độc lập."""
    if len(results) == 1:
        return next(iter(results)), "Chỉ chạy một biến thể."
    standard = results["standard"]
    sampled = results["event_balanced"]
    # Ngưỡng 10% được công bố trước: không đổi hiệu quả mưa lớn lấy suy giảm
    # quá lớn trên toàn tập validation. Test không xuất hiện trong hàm này.
    std_val, sampled_val = standard["validation"], sampled["validation"]
    if std_val["heavy_count"] == 0:
        choice = min(results, key=lambda name: results[name]["validation"]["metrics"]["RMSE"])
        return choice, "Validation không có mưa >5 mm/h; chọn RMSE validation thấp hơn."
    if (sampled_val["metrics"]["RMSE"] > std_val["metrics"]["RMSE"] * 1.10 or
            sampled_val["metrics"]["MAE"] > std_val["metrics"]["MAE"] * 1.10):
        return "standard", "Lấy mẫu sự kiện làm MAE hoặc RMSE validation tăng quá 10%."
    if sampled_val["detection"]["F1"] > std_val["detection"]["F1"]:
        return "event_balanced", "F1 mưa >5 mm/h trên validation cao hơn, MAE/RMSE trong giới hạn 10%."
    if (sampled_val["detection"]["F1"] == std_val["detection"]["F1"] and
            sampled_val["heavy_mae"] < std_val["heavy_mae"]):
        return "event_balanced", "F1 validation bằng nhau và MAE mưa lớn thấp hơn."
    return "standard", "Lấy mẫu sự kiện chưa cải thiện F1 mưa lớn trên validation."


def main() -> None:
    args = _arguments()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.batch_size < 1 or args.max_epochs < 1:
        raise ValueError("batch-size và max-epochs phải dương")

    processed_dir = ROOT / "data" / "processed" / "surface_only"
    models_dir = ROOT / "models" / "surface_only"
    plots_dir = ROOT / "plots" / "surface_only"
    for directory in (processed_dir, models_dir, plots_dir):
        directory.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Đọc Open-Meteo bề mặt: %s", args.surface_csv)
    raw = _load_surface(args.surface_csv)
    engineered = engineer_features(raw)
    engineered.to_parquet(processed_dir / "features.parquet", index=False)
    prepared = prepare_datasets(
        engineered,
        input_length=24,
        output_length=6,
        batch_size=args.batch_size,
        scaler_path=models_dir / "scaler.pkl",
    )
    split_report = {
        **prepared.diagnostics,
        "first_local": str(engineered["datetime"].iloc[0]),
        "last_local": str(engineered["datetime"].iloc[-1]),
        "train_end": str(prepared.split_boundaries["train_end"]),
        "val_end": str(prepared.split_boundaries["val_end"]),
        "features": prepared.feature_cols,
    }
    _write_json(processed_dir / "window_diagnostics.json", split_report)
    naive_baselines = _naive_baselines(prepared.test_dataset)
    _write_json(plots_dir / "naive_baselines.json", naive_baselines)
    LOGGER.info("Độ phủ: %d giờ; cửa sổ train/val/test: %d/%d/%d", len(engineered),
                prepared.diagnostics["train_windows"], prepared.diagnostics["val_windows"],
                prepared.diagnostics["test_windows"])
    if args.prepare_only:
        return

    variants = ("standard", "event_balanced") if args.variant == "both" else (args.variant,)
    results: dict[str, dict] = {}
    trained = {}
    for variant in variants:
        train_loader = prepared.train_loader
        sample_info = None
        if variant == "event_balanced":
            train_loader, sample_info = build_event_sampled_loader(
                prepared.train_dataset,
                batch_size=args.batch_size,
                heavy_threshold=HEAVY_THRESHOLD,
                target_draw_fraction=args.heavy_draw_fraction,
            )
            LOGGER.info("Lấy mẫu đợt mưa lớn: %s", sample_info)

        LOGGER.info("Huấn luyện biến thể %s", variant)
        checkpoint_path = models_dir / f"{variant}.pth"
        training = train_bilstm(
            train_loader,
            prepared.val_loader,
            None,  # Chưa đọc nhãn test trước khi chốt biến thể bằng validation.
            feature_cols=prepared.feature_cols,
            checkpoint_path=checkpoint_path,
            config=TrainingConfig(max_epochs=args.max_epochs, device=args.device),
        )
        val_true, val_pred = predict(training.model, prepared.val_loader, training.device)
        val_heavy = val_true > HEAVY_THRESHOLD
        validation = {
            "metrics": _metrics(val_true, val_pred),
            "detection": _detection_metrics(val_true, val_pred),
            "heavy_count": int(val_heavy.sum()),
            "heavy_mae": (
                float(np.mean(np.abs(val_true[val_heavy] - val_pred[val_heavy])))
                if val_heavy.any() else None
            ),
        }
        result = {
            "validation": validation,
            "checkpoint": str(checkpoint_path),
            "best_epoch": training.best_epoch,
            "epochs_ran": len(training.history),
            "best_val_loss": training.best_val_loss,
            "device": training.device,
            "sampler": vars(sample_info) if sample_info else None,
        }
        results[variant] = result
        trained[variant] = training
        LOGGER.info("%s: validation RMSE %.4f, heavy MAE %s, F1 %.4f", variant,
                    validation["metrics"]["RMSE"], validation["heavy_mae"],
                    validation["detection"]["F1"])

    # Chốt lựa chọn trước khi mở metric test. Các con số test chỉ để báo cáo.
    selected, reason = _select_variant(results)
    shutil.copyfile(models_dir / f"{selected}.pth", models_dir / "best_surface_model.pth")
    LOGGER.info("Chọn %s bằng validation: %s", selected, reason)

    for variant in variants:
        training = trained[variant]
        training.y_true, training.y_pred = predict(
            training.model, prepared.test_loader, training.device
        )
        variant_plots = plots_dir / variant
        metrics = evaluate_and_visualize(
            engineered,
            training.history,
            training.y_true,
            training.y_pred,
            prepared.test_dataset.target_datetimes,
            output_dir=variant_plots,
        )
        heavy_rain = json.loads((variant_plots / "test_metrics_heavy_rain.json").read_text(encoding="utf-8"))
        detection = _detection_metrics(training.y_true, training.y_pred)
        _write_json(variant_plots / "heavy_rain_detection.json", detection)
        results[variant].update({
            "metrics": metrics,
            "heavy_rain": heavy_rain,
            "detection": detection,
        })
        _write_json(models_dir / f"{variant}_summary.json", results[variant])
        LOGGER.info("%s TEST: RMSE %.4f, heavy MAE %.4f, F1 %.4f", variant,
                    metrics["RMSE"], heavy_rain["MAE"], detection["F1"])

    _write_json(models_dir / "comparison.json", {
        "selected_variant": selected,
        "selection_reason": reason,
        "selection_uses_validation_only": True,
        "same_train_val_test_split": True,
        "split": split_report,
        "naive_test_baselines": naive_baselines,
        "variants": results,
    })


if __name__ == "__main__":
    main()
