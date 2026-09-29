r"""Đánh giá lại checkpoint Bi-LSTM bề mặt, không huấn luyện lại.

    .venv\Scripts\python.exe evaluate_surface_baseline.py --device auto

File quan trắc độc lập (nếu có) phải chứa datetime có UTC offset và cột
precipitation_mm_h đã quy về cùng giờ hiệu lực với Open-Meteo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
from pathlib import Path

import joblib
_MPL_CACHE = Path(__file__).resolve().parent / ".cache" / "matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

from src.bilstm_model import BiLSTM
from src.dataset_prep import prepare_datasets
from src.event_evaluation import score_by_horizon, score_episodes
from src.train_bilstm import predict

ROOT = Path(__file__).resolve().parent
LOGGER = logging.getLogger(__name__)
FORECAST_COLS = ("predicted_mm", "persistence_mm", "zero_mm")
THRESHOLD = 5.0


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Đánh giá chi tiết checkpoint Bi-LSTM bề mặt")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--observations-csv", type=Path,
                        help="CSV quan trắc độc lập có datetime kèm UTC offset và precipitation_mm_h")
    parser.add_argument("--observations-source", help="Tên nguồn/trạm quan trắc độc lập")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports" / "surface_only")
    return parser.parse_args()


def _clean_json(value: object) -> object:
    if isinstance(value, dict):
        return {key: _clean_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_clean_json(item) for item in value]
    if isinstance(value, np.generic):
        return _clean_json(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Path):
        return str(value)
    return value


def _write_json(path: Path, content: object) -> None:
    path.write_text(json.dumps(_clean_json(content), ensure_ascii=False, indent=2, allow_nan=False),
                    encoding="utf-8")


def _load_model(checkpoint_path: Path, features: list[str], device: torch.device) -> BiLSTM:
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if checkpoint["feature_cols"] != features or checkpoint["input_dim"] != len(features):
        raise ValueError("Đặc trưng checkpoint không khớp dữ liệu đánh giá")
    if checkpoint["output_dim"] != 6:
        raise ValueError("Checkpoint không dự báo 6 giờ")
    model = BiLSTM(input_dim=checkpoint["input_dim"], output_dim=6)
    model.load_state_dict(checkpoint["model_state_dict"])
    return model.to(device).eval()


def _prediction_table(dataset, actual: np.ndarray, predicted: np.ndarray) -> pd.DataFrame:
    hours = dataset.target_datetimes
    if actual.shape != predicted.shape or actual.shape != (len(dataset), 6):
        raise ValueError("Kích thước dự báo không khớp test dataset")
    last_observed = dataset.targets[dataset.starts + dataset.input_length - 1]
    anchors = dataset.anchor_datetimes
    rows = []
    for horizon in range(1, 7):
        rows.append(pd.DataFrame({
            # Đây là giờ cuối của input, chưa phải thời điểm dữ liệu archive sẵn có.
            "last_input_datetime": anchors,
            "valid_datetime": pd.DatetimeIndex(hours[f"t+{horizon}"]),
            "horizon_h": horizon,
            "actual_mm": actual[:, horizon - 1],
            "predicted_mm": predicted[:, horizon - 1],
            "persistence_mm": last_observed,
            "zero_mm": np.zeros(len(dataset), dtype=np.float32),
        }))
    return pd.concat(rows, ignore_index=True).sort_values(
        ["horizon_h", "valid_datetime"]
    ).reset_index(drop=True)


def _event_tables(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries, first_hour_events = [], None
    for horizon, group in frame.groupby("horizon_h", sort=True):
        group = group.sort_values("valid_datetime")
        hours = pd.DatetimeIndex(group["valid_datetime"])
        if hours.has_duplicates:
            raise ValueError(f"Horizon +{horizon} chứa valid_datetime trùng")
        for column in FORECAST_COLS:
            summary, events = score_episodes(
                hours, group["actual_mm"].to_numpy(), group[column].to_numpy(),
                threshold=THRESHOLD,
            )
            summaries.append({"horizon_h": horizon, "forecast": column, **summary})
            if horizon == 1 and column == "predicted_mm":
                first_hour_events = events
    return pd.DataFrame(summaries), (first_hour_events if first_hour_events is not None
                                     else pd.DataFrame())


def _load_observations(path: Path, source: str) -> pd.DataFrame:
    if not source or not source.strip():
        raise ValueError("Cần --observations-source để ghi nguồn quan trắc")
    if path.resolve() == (ROOT / "data" / "raw_data" / "openmeteo_danang_2015_2026.csv").resolve():
        raise ValueError("Open-Meteo hiện tại không phải bộ quan trắc độc lập")
    raw = pd.read_csv(path)
    required = {"datetime", "precipitation_mm_h"}
    if required - set(raw):
        raise ValueError(f"CSV quan trắc cần cột: {sorted(required)}")
    if raw.empty:
        raise ValueError("CSV quan trắc rỗng")
    timestamps = pd.to_datetime(raw["datetime"], errors="raise")
    if not isinstance(timestamps.dtype, pd.DatetimeTZDtype):
        raise ValueError("datetime quan trắc phải có UTC offset, ví dụ +07:00 hoặc Z")
    timestamps = timestamps.dt.tz_convert("Asia/Ho_Chi_Minh")
    if timestamps.isna().any() or timestamps.duplicated().any() or not timestamps.eq(timestamps.dt.floor("h")).all():
        raise ValueError("Giờ quan trắc phải duy nhất, hợp lệ và đúng đầu giờ")
    values = pd.to_numeric(raw["precipitation_mm_h"], errors="coerce")
    if not np.isfinite(values.to_numpy(dtype=float)).all() or (values < 0).any():
        raise ValueError("Lượng mưa quan trắc phải là mm/h không âm, không khuyết")
    return pd.DataFrame({"valid_datetime": timestamps, "observed_mm": values.to_numpy(dtype=float)})


def _plot_by_horizon(horizon_scores: pd.DataFrame, event_scores: pd.DataFrame,
                     path: Path) -> None:
    names = {"predicted_mm": "Bi-LSTM", "persistence_mm": "Persistence", "zero_mm": "Zero"}
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.3))
    for column in FORECAST_COLS:
        sub = horizon_scores[horizon_scores["forecast"] == column].sort_values("horizon_h")
        axes[0].plot(sub["horizon_h"], sub["RMSE"], marker="o", label=names[column])
        axes[1].plot(sub["horizon_h"], sub["POD_recall"], marker="o", label=names[column])
        ev = event_scores[event_scores["forecast"] == column].sort_values("horizon_h")
        axes[2].plot(ev["horizon_h"], ev["event_recall"], marker="o", label=names[column])
    axes[0].set(ylabel="RMSE (mm/h)", title="Sai số theo horizon")
    axes[1].set(ylabel="Recall giờ mưa >5 mm/h", title="Phát hiện theo giờ", ylim=(-0.03, 1.03))
    axes[2].set(ylabel="Recall đợt mưa >5 mm/h", title="Phát hiện theo đợt", ylim=(-0.03, 1.03))
    for ax in axes:
        ax.set(xlabel="Giờ dự báo", xticks=range(1, 7))
        ax.grid(alpha=0.25)
    axes[0].legend()
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    args = _arguments()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if args.observations_source and not args.observations_csv:
        raise ValueError("--observations-source cần đi cùng --observations-csv")
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)

    feature_path = ROOT / "data" / "processed" / "surface_only" / "features.parquet"
    checkpoint_path = ROOT / "models" / "surface_only" / "best_surface_model.pth"
    scaler_path = ROOT / "models" / "surface_only" / "scaler.pkl"
    for path in (feature_path, checkpoint_path, scaler_path):
        if not path.exists():
            raise FileNotFoundError(path)
    engineered = pd.read_parquet(feature_path)
    prepared = prepare_datasets(engineered, batch_size=512, scaler_path=None,
                                shuffle_train=False)
    saved_scaler = joblib.load(scaler_path)
    if (not np.allclose(saved_scaler.center_, prepared.scaler.center_)
            or not np.allclose(saved_scaler.scale_, prepared.scaler.scale_)):
        raise ValueError("Scaler đã lưu không khớp với dữ liệu train hiện tại")
    device = torch.device("cuda" if args.device == "auto" and torch.cuda.is_available()
                          else "cpu" if args.device == "auto" else args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("Máy hiện không có CUDA")
    model = _load_model(checkpoint_path, prepared.feature_cols, device)
    LOGGER.info("Dự báo %d cửa sổ test trên %s, không huấn luyện lại", len(prepared.test_dataset), device)
    actual, predicted = predict(model, prepared.test_loader, device)
    table = _prediction_table(prepared.test_dataset, actual, predicted)
    table.to_parquet(out / "test_predictions.parquet", index=False)
    by_horizon, by_season, by_month = score_by_horizon(table, forecast_cols=FORECAST_COLS)
    events, first_hour_events = _event_tables(table)
    by_horizon.to_csv(out / "metrics_by_horizon.csv", index=False)
    by_season.to_csv(out / "metrics_by_season.csv", index=False)
    by_month.to_csv(out / "metrics_by_month.csv", index=False)
    events.to_csv(out / "event_metrics_by_horizon.csv", index=False)
    first_hour_events.to_csv(out / "observed_events_t_plus_1.csv", index=False)
    _plot_by_horizon(by_horizon, events, out / "plot_horizon_and_event_skill.png")

    raw_files = sorted(p.name for p in (ROOT / "data" / "raw_data").rglob("*")
                       if p.is_file() and p.suffix.lower() in {".csv", ".txt", ".xlsx", ".parquet"})
    observation_audit: dict[str, object] = {
        "raw_tabular_files_checked": raw_files,
        "independent_observation_file_supplied": args.observations_csv is not None,
        "independent_observation_evaluated": False,
        "limitation": "Open-Meteo Historical là dữ liệu mô hình/tái phân tích; cần trạm hoặc radar độc lập để kiểm chứng lượng mưa tại điểm.",
    }
    if args.observations_csv is not None:
        obs = _load_observations(args.observations_csv, args.observations_source)
        joined = table.merge(obs, on="valid_datetime", how="inner", validate="many_to_one")
        observation_audit.update({
            "source": args.observations_source,
            "file": str(args.observations_csv.resolve()),
            "total_observation_hours": len(obs),
            "matched_horizon_hour_pairs": len(joined),
            "matched_unique_hours": int(joined["valid_datetime"].nunique()),
        })
        if joined.empty:
            observation_audit["limitation"] = "File quan trắc không trùng giờ với tập test."
        else:
            joined["openmeteo_actual_mm"] = joined["actual_mm"]
            joined["actual_mm"] = joined["observed_mm"]
            independent_horizon, independent_season, independent_month = score_by_horizon(
                joined, forecast_cols=FORECAST_COLS
            )
            independent_horizon.to_csv(out / "independent_metrics_by_horizon.csv", index=False)
            independent_season.to_csv(out / "independent_metrics_by_season.csv", index=False)
            independent_month.to_csv(out / "independent_metrics_by_month.csv", index=False)
            independent_events, _ = _event_tables(joined)
            independent_events.to_csv(out / "independent_event_metrics_by_horizon.csv", index=False)
            observation_audit["independent_observation_evaluated"] = True
            observation_audit["limitation"] = (
                "Cần xác minh vị trí trạm/radar, độ phân giải và quy ước giờ tích lũy trước khi diễn giải."
            )
    _write_json(out / "observation_audit.json", observation_audit)
    _write_json(out / "evaluation_manifest.json", {
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
        "device": str(device),
        "test_windows": len(prepared.test_dataset),
        "horizons_h": [1, 2, 3, 4, 5, 6],
        "threshold_mm_h_strictly_greater_than": THRESHOLD,
        "event_gap_hours": 6,
        "event_match": "Ghép cực đại một-đối-một khi khoảng giờ mưa lớn đầu-cuối giao nhau",
        "seasons": "DJF/MAM/JJA/SON là quý khí tượng, không mặc định là mùa mưa/khô Đà Nẵng",
        "season_and_month_metrics": "Gộp các cặp horizon–giờ; một valid hour có thể xuất hiện ở nhiều horizon",
        "test_first_valid_local": str(table["valid_datetime"].min()),
        "test_last_valid_local": str(table["valid_datetime"].max()),
        "raw_observation_status": observation_audit,
    })
    LOGGER.info("Đã lưu báo cáo tại %s", out)


if __name__ == "__main__":
    main()
