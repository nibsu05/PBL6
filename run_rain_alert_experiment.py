r"""Thử Bi-LSTM hai đầu mưa lớn/lượng mưa, chọn ngưỡng trên validation.

    .venv\Scripts\python.exe run_rain_alert_experiment.py --device cuda

Checkpoint Bi-LSTM chuẩn giữ nguyên; test chỉ được suy luận sau khi chốt
checkpoint và ngưỡng cảnh báo theo validation.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import average_precision_score, brier_score_loss

_MPL_CACHE = Path(__file__).resolve().parent / ".cache" / "matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.bilstm_model import BiLSTM
from src.dataset_prep import prepare_datasets
from src.event_evaluation import detection_scores, score_episodes
from src.rain_alert_model import RainAlertConfig
from src.train_bilstm import predict as predict_standard
from src.train_rain_alert import fit_alert_model, predict_alert
from src.visualize_and_evaluate import _metrics

ROOT = Path(__file__).resolve().parent
LOGGER = logging.getLogger(__name__)
THRESHOLD_MM_H = 5.0
MODEL_NAMES = ("dual_head", "standard", "persistence")


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Thí nghiệm Bi-LSTM hai đầu cảnh báo mưa lớn")
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    parser.add_argument("--max-epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--pos-weight", type=float, default=12.0)
    return parser.parse_args()


def _jsonable(item: object) -> object:
    if isinstance(item, dict):
        return {key: _jsonable(value) for key, value in item.items()}
    if isinstance(item, (list, tuple)):
        return [_jsonable(value) for value in item]
    if isinstance(item, np.generic):
        return _jsonable(item.item())
    if isinstance(item, float) and not math.isfinite(item):
        return None
    return item


def _write_json(path: Path, content: object) -> None:
    path.write_text(json.dumps(_jsonable(content), ensure_ascii=False, indent=2, allow_nan=False),
                    encoding="utf-8")


def _load_standard(path: Path, feature_cols: list[str], device: torch.device) -> BiLSTM:
    saved = torch.load(path, map_location="cpu", weights_only=True)
    if saved["feature_cols"] != feature_cols:
        raise ValueError("Checkpoint chuẩn không khớp đặc trưng")
    model = BiLSTM(saved["input_dim"], saved["output_dim"])
    model.load_state_dict(saved["model_state_dict"])
    return model.to(device).eval()


def _persistence(dataset) -> np.ndarray:
    previous = dataset.targets[dataset.starts + dataset.input_length - 1]
    return np.repeat(previous[:, None], dataset.output_length, axis=1)


def _alert_metrics(y: np.ndarray, alerts: np.ndarray, hours: pd.DataFrame) -> dict:
    hourly = detection_scores(y, np.where(alerts, 6.0, 0.0), THRESHOLD_MM_H)
    count_true = count_forecast = count_hit = 0
    per_horizon = []
    for h in range(y.shape[1]):
        event, _ = score_episodes(pd.DatetimeIndex(hours.iloc[:, h]), y[:, h],
                                  np.where(alerts[:, h], 6.0, 0.0), threshold=THRESHOLD_MM_H)
        count_true += event["observed_events"]
        count_forecast += event["forecast_events"]
        count_hit += event["detected_observed_events"]
        per_horizon.append({"horizon_h": h + 1, **event})
    event_f1 = 2 * count_hit / (count_true + count_forecast) if count_true + count_forecast else None
    return {
        "hourly": hourly,
        "events_micro": {
            "observed": count_true,
            "forecast": count_forecast,
            "matched": count_hit,
            "precision": count_hit / count_forecast if count_forecast else None,
            "recall": count_hit / count_true if count_true else None,
            "F1": event_f1,
        },
        "events_by_horizon": per_horizon,
    }


def select_threshold(y: np.ndarray, probabilities: np.ndarray,
                     hours: pd.DataFrame) -> tuple[float, pd.DataFrame]:
    """Chỉ nhận validation; tối đa event F1, hòa thì chọn ngưỡng cao hơn."""
    if y.shape != probabilities.shape:
        raise ValueError("Nhãn và xác suất phải có cùng kích thước")
    rows = []
    for threshold in np.arange(0.05, 1.0, 0.05):
        metrics = _alert_metrics(y, probabilities >= threshold, hours)
        rows.append({
            "probability_threshold": round(float(threshold), 2),
            "event_F1": metrics["events_micro"]["F1"],
            "event_precision": metrics["events_micro"]["precision"],
            "event_recall": metrics["events_micro"]["recall"],
            "forecast_events": metrics["events_micro"]["forecast"],
            "hourly_precision": metrics["hourly"]["precision"],
            "hourly_recall": metrics["hourly"]["POD_recall"],
            "hourly_F1": metrics["hourly"]["F1"],
        })
    sweep = pd.DataFrame(rows)
    winner = max(rows, key=lambda row: (
        -1 if row["event_F1"] is None else row["event_F1"],
        row["probability_threshold"],
    ))
    return winner["probability_threshold"], sweep


def _evaluate_split(name: str, dataset, y: np.ndarray, amount: np.ndarray,
                    probability: np.ndarray, standard_amount: np.ndarray,
                    threshold: float) -> tuple[dict, pd.DataFrame]:
    if y.shape != amount.shape or y.shape != probability.shape or y.shape != standard_amount.shape:
        raise ValueError(f"Kích thước dự báo {name} không khớp")
    persistence = _persistence(dataset)
    rain_amounts = {"dual_head": amount, "standard": standard_amount,
                    "persistence": persistence}
    alert_masks = {"dual_head": probability >= threshold,
                   "standard": standard_amount > THRESHOLD_MM_H,
                   "persistence": persistence > THRESHOLD_MM_H}
    times = dataset.target_datetimes
    result = {}
    for model_name in MODEL_NAMES:
        full = _alert_metrics(y, alert_masks[model_name], times)
        full["amount_metrics"] = _metrics(y, rain_amounts[model_name])
        full["amount_metrics_by_horizon"] = [
            {"horizon_h": h + 1, **_metrics(y[:, h], rain_amounts[model_name][:, h])}
            for h in range(y.shape[1])
        ]
        if model_name == "dual_head":
            labels = (y.ravel() > THRESHOLD_MM_H).astype(int)
            full["probability_metrics"] = {
                "average_precision": float(average_precision_score(labels, probability.ravel())),
                "brier_score": float(brier_score_loss(labels, probability.ravel())),
                "heavy_fraction": float(labels.mean()),
            }
        result[model_name] = full
    rows = []
    for h in range(y.shape[1]):
        rows.append(pd.DataFrame({
            "last_input_datetime": dataset.anchor_datetimes,
            "valid_datetime": pd.DatetimeIndex(times.iloc[:, h]),
            "horizon_h": h + 1,
            "actual_mm": y[:, h],
            "dual_amount_mm": amount[:, h],
            "dual_heavy_probability": probability[:, h],
            "dual_alert": alert_masks["dual_head"][:, h],
            "standard_amount_mm": standard_amount[:, h],
            "persistence_mm": persistence[:, h],
        }))
    table = pd.concat(rows, ignore_index=True)
    return result, table


def _plot_skill(results: dict, out: Path) -> None:
    names = {"dual_head": "Hai đầu", "standard": "Bi-LSTM chuẩn", "persistence": "Persistence"}
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    for model_name in MODEL_NAMES:
        info = results[model_name]
        h = np.arange(1, 7)
        axes[0].plot(h, [row["RMSE"] for row in info["amount_metrics_by_horizon"]],
                     marker="o", label=names[model_name])
        axes[1].plot(h, [row["event_recall"] for row in info["events_by_horizon"]],
                     marker="o", label=names[model_name])
        axes[2].plot(h, [row["event_precision"] for row in info["events_by_horizon"]],
                     marker="o", label=names[model_name])
    for ax in axes:
        ax.set(xlabel="Horizon (giờ)", xticks=range(1, 7))
        ax.grid(alpha=0.25)
    axes[0].set(ylabel="RMSE lượng mưa (mm/h)", title="Dự báo lượng mưa")
    axes[1].set(ylabel="Recall đợt mưa >5 mm/h", title="Phát hiện đợt", ylim=(-0.02, 1.02))
    axes[2].set(ylabel="Precision đợt mưa", title="Cảnh báo đúng", ylim=(-0.02, 1.02))
    axes[0].legend()
    fig.tight_layout()
    fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    args = _args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.batch_size < 1 or args.max_epochs < 1 or args.pos_weight < 1:
        raise ValueError("batch-size, max-epochs và pos-weight phải dương")
    report_dir = ROOT / "reports" / "rain_alert_experiment"
    report_dir.mkdir(parents=True, exist_ok=True)
    feature_path = ROOT / "data" / "processed" / "surface_only" / "features.parquet"
    features = pd.read_parquet(feature_path)
    prepared = prepare_datasets(features, batch_size=args.batch_size, scaler_path=None)
    saved_scaler = joblib.load(ROOT / "models" / "surface_only" / "scaler.pkl")
    if (not np.allclose(saved_scaler.center_, prepared.scaler.center_)
            or not np.allclose(saved_scaler.scale_, prepared.scaler.scale_)):
        raise ValueError("Scaler không khớp với dữ liệu train")
    device = torch.device("cuda" if args.device == "auto" and torch.cuda.is_available()
                          else "cpu" if args.device == "auto" else args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA hiện không có")
    config = RainAlertConfig(max_epochs=args.max_epochs, classification_pos_weight=args.pos_weight)
    checkpoint_path = ROOT / "models" / "surface_only" / "rain_alert_dual_head.pth"
    model, history, best_epoch = fit_alert_model(
        prepared.train_loader, prepared.val_loader, feature_cols=prepared.feature_cols,
        checkpoint_path=checkpoint_path, device=device, config=config,
    )
    pd.DataFrame(history).to_csv(report_dir / "training_history.csv", index=False)

    # Toàn bộ lựa chọn chốt ở validation; test chưa được suy luận tới thời điểm này.
    val_y, val_amount, val_probability = predict_alert(model, prepared.val_loader, device)
    standard = _load_standard(ROOT / "models" / "surface_only" / "best_surface_model.pth",
                              prepared.feature_cols, device)
    standard_val_y, standard_val_amount = predict_standard(standard, prepared.val_loader, device)
    if not np.array_equal(val_y, standard_val_y):
        raise ValueError("Validation của hai model không cùng nhãn/giờ")
    probability_threshold, sweep = select_threshold(
        val_y, val_probability, prepared.val_dataset.target_datetimes
    )
    sweep.to_csv(report_dir / "validation_threshold_sweep.csv", index=False)
    validation, _ = _evaluate_split("validation", prepared.val_dataset, val_y, val_amount,
                                   val_probability, standard_val_amount, probability_threshold)
    LOGGER.info("Chốt ngưỡng xác suất %.2f trên validation (event F1 %.3f)",
                probability_threshold, validation["dual_head"]["events_micro"]["F1"])
    _write_json(report_dir / "validation_summary.json", {
        "selected_probability_threshold": probability_threshold,
        "selection_uses_validation_only": True,
        "best_epoch_by_validation_loss": best_epoch,
        "models": validation,
    })

    test_y, test_amount, test_probability = predict_alert(model, prepared.test_loader, device)
    standard_test_y, standard_test_amount = predict_standard(standard, prepared.test_loader, device)
    if not np.array_equal(test_y, standard_test_y):
        raise ValueError("Test của hai model không cùng nhãn/giờ")
    test, table = _evaluate_split("test", prepared.test_dataset, test_y, test_amount,
                                  test_probability, standard_test_amount, probability_threshold)
    table.to_parquet(report_dir / "test_predictions.parquet", index=False)
    _write_json(report_dir / "test_summary.json", {
        "selected_probability_threshold": probability_threshold,
        "checkpoint": str(checkpoint_path),
        "device": str(device),
        "test_windows": len(prepared.test_dataset),
        "event_gap_hours": 6,
        "event_matching": "Một-đối-một, tối đa số đợt có khoảng giờ giao nhau",
        "models": test,
    })
    _plot_skill(test, report_dir / "plot_rain_alert_skill.png")
    LOGGER.info("TEST: event F1 hai đầu %.3f, chuẩn %.3f, persistence %.3f", 
                test["dual_head"]["events_micro"]["F1"],
                test["standard"]["events_micro"]["F1"],
                test["persistence"]["events_micro"]["F1"])
    LOGGER.info("TEST: RMSE hai đầu %.3f, chuẩn %.3f, persistence %.3f",
                test["dual_head"]["amount_metrics"]["RMSE"],
                test["standard"]["amount_metrics"]["RMSE"],
                test["persistence"]["amount_metrics"]["RMSE"])


if __name__ == "__main__":
    main()
