"""Đánh giá mưa lớn theo giờ dự báo và theo đợt, không nhân bản giờ thật.

Một đợt gồm các giờ vượt ngưỡng liên tiếp hoặc cách nhau tối đa 6 giờ, với
điều kiện chuỗi quan trắc ở giữa đầy đủ. Đợt dự báo trúng khi khoảng từ giờ
vượt ngưỡng đầu đến cuối giao với một đợt thật. Đây là kiểm tra phát hiện
đợt, không đánh giá độ chính xác thời điểm đỉnh mưa.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .visualize_and_evaluate import _metrics

HOUR_NS = 3_600_000_000_000
SEASON_NAMES = {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM",
                6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"}


def detection_scores(actual: np.ndarray, predicted: np.ndarray,
                     threshold: float = 5.0) -> dict[str, float | int | None]:
    """POD=recall, FAR là tỷ lệ cảnh báo sai, CSI loại true negative."""
    true = np.asarray(actual, dtype=float).ravel()
    pred = np.asarray(predicted, dtype=float).ravel()
    if true.shape != pred.shape or not np.isfinite(true).all() or not np.isfinite(pred).all():
        raise ValueError("Nhãn và dự báo phải cùng kích thước, không có NaN/inf")
    yes, forecast_yes = true > threshold, pred > threshold
    tp = int(np.sum(yes & forecast_yes))
    fp = int(np.sum(~yes & forecast_yes))
    fn = int(np.sum(yes & ~forecast_yes))
    tn = int(np.sum(~yes & ~forecast_yes))
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    if recall is None:
        f1 = None  # Không có giờ mưa thật: F1 cảnh báo mưa không xác định.
    elif precision is None:
        f1 = 0.0  # Có mưa thật nhưng không phát cảnh báo nào.
    else:
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "precision": precision,
        "POD_recall": recall,
        "F1": f1,
        "FAR": fp / (tp + fp) if tp + fp else None,
        "CSI": tp / (tp + fp + fn) if tp + fp + fn else None,
    }


def score_pairs(actual: np.ndarray, predicted: np.ndarray,
                threshold: float = 5.0) -> dict[str, float | int | None]:
    """Chỉ số hồi quy và cảnh báo trên cùng các giờ hợp lệ."""
    true = np.asarray(actual, dtype=float).ravel()
    pred = np.asarray(predicted, dtype=float).ravel()
    if len(true) == 0 or true.shape != pred.shape:
        raise ValueError("Không có cặp nhãn/dự báo hợp lệ")
    heavy = true > threshold
    return {
        "n_pairs": len(true),
        "n_heavy": int(heavy.sum()),
        "heavy_mae": float(np.abs(true[heavy] - pred[heavy]).mean()) if heavy.any() else None,
        **_metrics(true, pred),
        **detection_scores(true, pred, threshold),
    }


@dataclass(frozen=True)
class Episode:
    first: int
    last: int


def find_episodes(hours: pd.DatetimeIndex, rain: np.ndarray, *,
                  threshold: float = 5.0, gap_hours: int = 6) -> list[Episode]:
    """Nhóm giờ vượt ngưỡng; không nối qua lỗ thời gian dù cách <= gap_hours."""
    hours = pd.DatetimeIndex(hours)
    values = np.asarray(rain, dtype=float)
    if (hours.tz is None or len(hours) != len(values) or hours.has_duplicates
            or not hours.is_monotonic_increasing or gap_hours < 1):
        raise ValueError("Giờ phải có múi giờ, tăng dần, không trùng và khớp lượng mưa")
    if not np.isfinite(values).all():
        raise ValueError("Lượng mưa chứa NaN/inf")
    positions = np.flatnonzero(values > threshold)
    if not len(positions):
        return []
    ns = hours.as_unit("ns").asi8
    episodes: list[Episode] = []
    first = last = int(positions[0])
    for position in positions[1:]:
        current = int(position)
        elapsed = int(ns[current] - ns[last])
        # Khoảng cách chỉ hợp lệ nếu mọi timestamp giữa hai giờ đều có mặt.
        if elapsed > gap_hours * HOUR_NS or elapsed != (current - last) * HOUR_NS:
            episodes.append(Episode(first, last))
            first = current
        last = current
    episodes.append(Episode(first, last))
    return episodes


def score_episodes(hours: pd.DatetimeIndex, actual: np.ndarray,
                   predicted: np.ndarray, *, threshold: float = 5.0,
                   gap_hours: int = 6) -> tuple[dict[str, float | int | None], pd.DataFrame]:
    """Mỗi horizon chỉ có một dự báo cho một giờ hợp lệ.

    Các đợt dự báo/thật được ghép tối đa một-đối-một nếu khoảng từ giờ mưa
    lớn đầu đến cuối giao nhau. Ghép cực đại theo số đợt trúng, để một cảnh
    báo dài không thể được tính trúng nhiều đợt thật.
    """
    hours = pd.DatetimeIndex(hours)
    true = np.asarray(actual, dtype=float)
    pred = np.asarray(predicted, dtype=float)
    if true.shape != pred.shape or len(true) != len(hours):
        raise ValueError("Giờ, nhãn và dự báo phải cùng kích thước")
    observed = find_episodes(hours, true, threshold=threshold, gap_hours=gap_hours)
    forecast = find_episodes(hours, pred, threshold=threshold, gap_hours=gap_hours)
    adjacency = []
    for event in observed:
        candidates = [
            (index, min(event.last, predicted_event.last) - max(event.first, predicted_event.first) + 1)
            for index, predicted_event in enumerate(forecast)
            if predicted_event.first <= event.last and event.first <= predicted_event.last
        ]
        adjacency.append([index for index, _ in sorted(candidates, key=lambda item: -item[1])])
    forecast_to_true: dict[int, int] = {}

    def augment(true_index: int, seen: set[int]) -> bool:
        for forecast_index in adjacency[true_index]:
            if forecast_index in seen:
                continue
            seen.add(forecast_index)
            if forecast_index not in forecast_to_true or augment(forecast_to_true[forecast_index], seen):
                forecast_to_true[forecast_index] = true_index
                return True
        return False

    for true_index in range(len(observed)):
        augment(true_index, set())
    matched_true = set(forecast_to_true.values())
    true_hits = [index in matched_true for index in range(len(observed))]
    matches = len(forecast_to_true)
    recall = matches / len(observed) if observed else None
    precision = matches / len(forecast) if forecast else None
    if recall is None:
        f1 = None
    elif precision is None:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    rows = [{
        "event_id": index,
        "first_heavy_hour": hours[e.first],
        "last_heavy_hour": hours[e.last],
        "duration_span_h": int((hours[e.last] - hours[e.first]) / pd.Timedelta(hours=1)) + 1,
        "peak_actual_mm_h": float(true[e.first:e.last + 1].max()),
        "peak_predicted_in_event_mm_h": float(pred[e.first:e.last + 1].max()),
        "detected": hit,
    } for index, (e, hit) in enumerate(zip(observed, true_hits), start=1)]
    return ({
        "observed_events": len(observed),
        "forecast_events": len(forecast),
        "detected_observed_events": matches,
        "false_alarm_forecast_events": len(forecast) - matches,
        "event_precision": precision,
        "event_recall": recall,
        "event_F1": f1,
        "mean_peak_actual_mm_h": float(np.mean([r["peak_actual_mm_h"] for r in rows])) if rows else None,
        "mean_peak_predicted_in_event_mm_h": (
            float(np.mean([r["peak_predicted_in_event_mm_h"] for r in rows])) if rows else None
        ),
    }, pd.DataFrame(rows))


def score_by_horizon(predictions: pd.DataFrame, *,
                     forecast_cols: tuple[str, ...]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Trả chỉ số theo horizon, theo mùa khí tượng và theo tháng địa phương."""
    expected = {"horizon_h", "valid_datetime", "actual_mm", *forecast_cols}
    if expected - set(predictions):
        raise ValueError(f"Thiếu cột: {sorted(expected - set(predictions))}")
    frame = predictions.copy()
    frame["valid_datetime"] = pd.to_datetime(frame["valid_datetime"], utc=True).dt.tz_convert(
        "Asia/Ho_Chi_Minh"
    )
    frame["month"] = frame["valid_datetime"].dt.month
    frame["season"] = frame["month"].map(SEASON_NAMES)

    def grouped(keys: list[str]) -> pd.DataFrame:
        rows = []
        for group_key, subset in frame.groupby(keys, sort=True):
            values = group_key if isinstance(group_key, tuple) else (group_key,)
            for name in forecast_cols:
                rows.append({**dict(zip(keys, values)), "forecast": name,
                             **score_pairs(subset["actual_mm"], subset[name])})
        return pd.DataFrame(rows)

    return grouped(["horizon_h"]), grouped(["season"]), grouped(["month"])
