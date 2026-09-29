"""Đánh giá tập test và xuất bốn hình PNG 300 DPI cho báo cáo."""

from __future__ import annotations

import logging
import os
import json
from pathlib import Path
from typing import Sequence

# Tránh ghi font cache vào thư mục người dùng bị khóa trong môi trường chạy.
_MPL_CACHE = Path(__file__).resolve().parents[1] / ".cache" / "matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))

import matplotlib

matplotlib.use("Agg")  # Chạy được trên máy không có cửa sổ đồ họa.

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

LOGGER = logging.getLogger(__name__)


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    actual = np.asarray(actual, dtype=float).ravel()
    predicted = np.asarray(predicted, dtype=float).ravel()
    valid = np.isfinite(actual) & np.isfinite(predicted)
    actual, predicted = actual[valid], predicted[valid]
    if len(actual) == 0:
        raise ValueError("Không có dự báo hợp lệ để đánh giá")
    residual = predicted - actual
    mae = float(np.mean(np.abs(residual)))
    rmse = float(np.sqrt(np.mean(residual**2)))
    denominator = float(np.sum((actual - actual.mean()) ** 2))
    r2 = float(1 - np.sum(residual**2) / denominator) if denominator > 0 else float("nan")
    cc = (
        float(np.corrcoef(actual, predicted)[0, 1])
        if len(actual) > 1 and np.std(actual) > 0 and np.std(predicted) > 0
        else float("nan")
    )
    return {"MAE": mae, "RMSE": rmse, "R2": r2, "CC": cc}


def _save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    LOGGER.info("Đã lưu %s", path)


def _plot_correlation(df: pd.DataFrame, path: Path) -> None:
    # Chỉ vẽ biến có thật và có đủ phương sai; CAPE/CIN/TCWV có thể chưa tải.
    candidates = [
        "precipitation",
        "wind_speed_850",
        "sea_surface_temperature",
        "sst_air_temp_diff",
        "cape",
        "cin",
        "tcwv",
        "specific_humidity_850",
        "relative_humidity_2m",
        "oni", "oni_anom",
        "precip_lag_1h",
        "precip_lag_3h",
        "precip_lag_6h",
        "precip_lag_24h",
        "precip_roll_sum_6h",
        "precip_roll_sum_24h",
    ]
    columns = [
        name for name in candidates
        if name in df and pd.api.types.is_numeric_dtype(df[name]) and df[name].nunique(dropna=True) > 1
    ]
    if "precipitation" not in columns or len(columns) < 2:
        raise ValueError("Không đủ đặc trưng để vẽ ma trận tương quan")
    corr = df[columns].corr(numeric_only=True)
    fig, ax = plt.subplots(figsize=(max(9, len(columns) * 0.65), max(7, len(columns) * 0.58)))
    sns.heatmap(
        corr, ax=ax, cmap="RdBu_r", center=0, vmin=-1, vmax=1,
        square=True, linewidths=0.3, annot=len(columns) <= 14,
        fmt=".2f", cbar_kws={"label": "Pearson r"},
    )
    ax.set_title("Tương quan đặc trưng vật lý và lượng mưa (toàn bộ dữ liệu có sẵn)")
    ax.tick_params(axis="x", rotation=55, labelsize=8)
    ax.tick_params(axis="y", labelsize=8)
    _save(fig, path)


def _plot_loss(history: Sequence[dict[str, float]], path: Path) -> None:
    frame = pd.DataFrame(history)
    if frame.empty:
        raise ValueError("Lịch sử huấn luyện trống")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(frame["epoch"], frame["train_loss"], marker="o", ms=3, label="Train")
    ax.plot(frame["epoch"], frame["val_loss"], marker="o", ms=3, label="Validation")
    ax.set(xlabel="Epoch", ylabel="Weighted MSE (mm²/h²)", title="Loss Bi-LSTM qua các epoch")
    ax.grid(alpha=0.25)
    ax.legend()
    _save(fig, path)


def _plot_heavy_event(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    target_datetimes: Sequence[Sequence[object]],
    path: Path,
) -> None:
    # Horizon +1 tạo một giá trị dự báo duy nhất cho mỗi giờ trên trục thời gian.
    if isinstance(target_datetimes, pd.DataFrame):
        hours = pd.DatetimeIndex(target_datetimes.iloc[:, 0])
    else:
        hours = pd.DatetimeIndex([row[0] for row in target_datetimes])
    frame = pd.DataFrame(
        {"actual": y_true[:, 0], "predicted": y_pred[:, 0]}, index=hours,
    ).sort_index()
    frame = frame[~frame.index.duplicated(keep="first")]
    if frame.empty:
        raise ValueError("Không có dữ liệu test để chọn đợt mưa")

    # Chỉ chọn cửa sổ đủ 72 giờ liền mạch; NaN ở gap khiến tổng cuộn không hợp lệ.
    hourly = frame.asfreq("h")
    width = 72 if len(hourly) >= 72 else max(1, len(hourly))
    totals = hourly["actual"].rolling(width, min_periods=width).sum()
    if totals.notna().any():
        end = totals.idxmax()
        start = end - pd.Timedelta(hours=width - 1)
        event = hourly.loc[start:end]
    else:
        # Dataset test rất ngắn: vẫn chọn vùng quanh giờ mưa lớn nhất.
        peak = frame["actual"].idxmax()
        event = frame.loc[peak - pd.Timedelta(hours=36):peak + pd.Timedelta(hours=35)]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(event.index, event["actual"], label="Thực tế", lw=1.7, color="#176b99")
    ax.plot(event.index, event["predicted"].clip(lower=0), label="Bi-LSTM +1h", lw=1.5, color="#df6b2d")
    ax.set(xlabel="Thời gian (Asia/Ho_Chi_Minh)", ylabel="Lượng mưa (mm/h)",
           title="Đợt mưa lớn nhất trong tập test (tổng 72 giờ)")
    ax.grid(alpha=0.2)
    ax.legend()
    fig.autofmt_xdate()
    _save(fig, path)


def _plot_parity(y_true: np.ndarray, y_pred: np.ndarray, path: Path) -> None:
    # Mọi horizon đều góp vào đánh giá. Lấy mẫu có seed khi dữ liệu quá dày.
    actual = np.asarray(y_true).ravel()
    predicted = np.asarray(y_pred).ravel()
    valid = np.isfinite(actual) & np.isfinite(predicted)
    actual, predicted = actual[valid], predicted[valid]
    if len(actual) > 20_000:
        indices = np.random.default_rng(42).choice(len(actual), size=20_000, replace=False)
        actual, predicted = actual[indices], predicted[indices]
    residual = predicted - actual
    upper = max(float(np.max(actual)), float(np.max(predicted)), 1.0)
    fig, ax = plt.subplots(figsize=(7, 6))
    scatter = ax.scatter(actual, predicted, c=residual, cmap="coolwarm", s=9, alpha=0.5,
                         vmin=-max(abs(residual.min()), abs(residual.max())),
                         vmax=max(abs(residual.min()), abs(residual.max())))
    ax.plot([0, upper], [0, upper], color="black", linestyle="--", lw=1.2, label="Dự báo hoàn hảo (45°)")
    ax.set(xlabel="Lượng mưa thực tế (mm/h)", ylabel="Lượng mưa dự báo (mm/h)",
           title="Thực tế, dự báo và sai số trên tập test", xlim=(-0.02 * upper, upper * 1.02),
           ylim=(-0.02 * upper, upper * 1.02))
    fig.colorbar(scatter, ax=ax, label="Sai số dự báo − thực tế (mm/h)")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.2)
    _save(fig, path)


def evaluate_and_visualize(
    engineered_df: pd.DataFrame,
    history: Sequence[dict[str, float]],
    y_true: np.ndarray,
    y_pred: np.ndarray,
    target_datetimes: Sequence[Sequence[object]],
    *,
    output_dir: str | Path = "plots",
) -> dict[str, float]:
    """Xuất báo cáo và trả metric gộp của tất cả horizon 1–6."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    if y_true.shape != y_pred.shape or y_true.ndim != 2:
        raise ValueError("y_true/y_pred phải cùng dạng (số mẫu, số horizon)")
    if len(target_datetimes) != len(y_true):
        raise ValueError("Timestamp test không khớp số mẫu dự báo")

    metrics = _metrics(y_true, y_pred)
    per_horizon = [
        {"horizon_h": h + 1, **_metrics(y_true[:, h], y_pred[:, h])}
        for h in range(y_true.shape[1])
    ]
    pd.DataFrame(per_horizon).to_csv(output_dir / "test_metrics_by_horizon.csv", index=False)
    pd.DataFrame(history).to_csv(output_dir / "training_history.csv", index=False)
    heavy = y_true > 5.0
    if heavy.any():
        heavy_report = {
            "threshold_mm_per_hour": 5.0,
            "count_horizon_hour_pairs": int(heavy.sum()),
            "fraction_horizon_hour_pairs": float(heavy.mean()),
            "mean_actual_mm_per_hour": float(y_true[heavy].mean()),
            "mean_predicted_mm_per_hour": float(y_pred[heavy].mean()),
            **_metrics(y_true[heavy], y_pred[heavy]),
        }
        (output_dir / "test_metrics_heavy_rain.json").write_text(
            json.dumps(heavy_report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    else:
        heavy_report = None
    # Console Windows có thể dùng cp1252; giữ dòng metric ở ASCII để không lỗi.
    print("\nTEST METRICS (horizons t+1 to t+6)")
    print(f"MAE:  {metrics['MAE']:.4f} mm/h")
    print(f"RMSE: {metrics['RMSE']:.4f} mm/h")
    print(f"R2:   {metrics['R2']:.4f}")
    print(f"CC:   {metrics['CC']:.4f}")
    if heavy_report is not None:
        print(f"Heavy rain >5 mm/h: n={heavy_report['count_horizon_hour_pairs']}, "
              f"MAE={heavy_report['MAE']:.4f} mm/h, "
              f"mean actual={heavy_report['mean_actual_mm_per_hour']:.2f}, "
              f"mean predicted={heavy_report['mean_predicted_mm_per_hour']:.2f}")

    _plot_correlation(engineered_df, output_dir / "plot1_feature_correlation.png")
    _plot_loss(history, output_dir / "plot2_loss_curve.png")
    _plot_heavy_event(y_true, y_pred, target_datetimes,
                      output_dir / "plot3_actual_vs_predicted_timeseries.png")
    _plot_parity(y_true, y_pred, output_dir / "plot4_residuals_scatter.png")
    return metrics
