r"""Đánh giá ba mô hình trên cùng những giờ trạm có số đo, không huấn luyện lại.

Đầu vào phải qua prepare_gauge_observations.py. Nếu chưa có file trạm,
không chạy script này và không tạo chỉ số đánh giá độc lập giả.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.event_evaluation import detection_scores, score_episodes, score_pairs

ROOT = Path(__file__).resolve().parent
THRESHOLD = 5.0
MODELS = ("dual_head", "standard", "persistence")


def _clean(value: object) -> object:
    if isinstance(value, dict):
        return {key: _clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean(item) for item in value]
    if isinstance(value, np.generic):
        return _clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _aware(series: pd.Series, name: str) -> pd.Series:
    parsed = pd.to_datetime(series, errors="raise")
    if not isinstance(parsed.dtype, pd.DatetimeTZDtype):
        raise ValueError(f"{name} phải có UTC offset rõ ràng")
    if parsed.isna().any():
        raise ValueError(f"{name} không được khuyết")
    return parsed.dt.tz_convert("Asia/Ho_Chi_Minh")


def _cutoff(value: str | None) -> pd.Timestamp | None:
    if value is None:
        return None
    cut = pd.Timestamp(value)
    if cut.tzinfo is None:
        raise ValueError("--start-after phải có UTC offset")
    return cut.tz_convert("Asia/Ho_Chi_Minh")


def _validate_and_join(predictions: pd.DataFrame, observations: pd.DataFrame,
                       probability_threshold: float, start_after: pd.Timestamp | None
                       ) -> tuple[pd.DataFrame, dict]:
    needed = {"last_input_datetime", "valid_datetime", "horizon_h",
              "dual_amount_mm", "dual_heavy_probability", "standard_amount_mm", "persistence_mm"}
    if needed - set(predictions):
        raise ValueError(f"Dự báo thiếu cột: {sorted(needed - set(predictions))}")
    if {"datetime", "precipitation_mm_h"} - set(observations):
        raise ValueError("CSV trạm chưa chuẩn hóa: cần datetime và precipitation_mm_h")
    p = predictions.copy()
    p["valid_datetime"] = _aware(p["valid_datetime"], "valid_datetime dự báo")
    p["last_input_datetime"] = _aware(p["last_input_datetime"], "last_input_datetime")
    if p.duplicated(["horizon_h", "valid_datetime"]).any():
        raise ValueError("Mỗi horizon phải chỉ có một dự báo cho mỗi giờ hiệu lực")
    if not p["horizon_h"].isin(range(1, 7)).all():
        raise ValueError("Horizon phải từ 1 tới 6")
    if not ((p["valid_datetime"] - p["last_input_datetime"])
            == pd.to_timedelta(p["horizon_h"], unit="h")).all():
        raise ValueError("Giờ hiệu lực không khớp anchor + horizon; kiểm tra lệch múi giờ")
    numeric = ["dual_amount_mm", "dual_heavy_probability",
               "standard_amount_mm", "persistence_mm"]
    if "actual_mm" in p:
        numeric.append("actual_mm")
    amount_columns = ["dual_amount_mm", "standard_amount_mm", "persistence_mm"]
    if "actual_mm" in p:
        amount_columns.append("actual_mm")
    if (not np.isfinite(p[numeric].to_numpy(dtype=float)).all()
            or (p[amount_columns] < 0).any().any()
            or not p["dual_heavy_probability"].between(0, 1).all()):
        raise ValueError("Dự báo chứa lượng mưa/xác suất không hợp lệ")
    if start_after is not None:
        p = p.loc[p["valid_datetime"] > start_after].copy()
    o = observations.copy()
    if o.empty:
        raise ValueError("CSV trạm rỗng")
    o["valid_datetime"] = _aware(o["datetime"], "datetime trạm")
    if o["valid_datetime"].duplicated().any():
        raise ValueError("Dữ liệu trạm có giờ trùng")
    o["observed_mm"] = pd.to_numeric(o["precipitation_mm_h"], errors="coerce")
    if (not np.isfinite(o["observed_mm"].to_numpy(dtype=float)).all()
            or (o["observed_mm"] < 0).any()):
        raise ValueError("Dữ liệu trạm có mưa khuyết, âm hoặc vô hạn")
    if p.empty:
        return p, {"status": "no_predictions_after_cutoff", "forecast_pairs": 0,
                   "matched_pairs": 0}
    joined = p.merge(o[["valid_datetime", "observed_mm"]], on="valid_datetime",
                     how="inner", validate="many_to_one")
    # Tỷ lệ phủ chỉ xét các giờ dự báo nằm trong khoảng đầu-cuối của file trạm.
    first, last = o["valid_datetime"].min(), o["valid_datetime"].max()
    within = p["valid_datetime"].between(first, last)
    denominator = int(within.sum())
    summary = {
        "status": "evaluated" if not joined.empty else "no_overlap",
        "forecast_pairs": len(p),
        "forecast_pairs_in_gauge_span": denominator,
        "matched_pairs": len(joined),
        "matched_unique_hours": int(joined["valid_datetime"].nunique()),
        "pair_coverage_in_gauge_span": len(joined) / denominator if denominator else None,
        "gauge_first_hour": first.isoformat(),
        "gauge_last_hour": last.isoformat(),
        "model_probability_threshold_frozen": probability_threshold,
        "test_label_role": "independent_gauge; không fit mô hình hoặc chọn ngưỡng ở đây",
        "availability_warning": "Chỉ là đánh giá dự báo hồi cứu nếu chưa có issued_at và available_at thực tế.",
        "missing_hour_warning": "Giờ trạm không có bản ghi không được tính 0 mm; metrics chỉ trên giờ giao nhau.",
    }
    if not joined.empty:
        joined["dual_alert"] = joined["dual_heavy_probability"] >= probability_threshold
        if "actual_mm" in joined:
            summary["openmeteo_vs_gauge"] = score_pairs(joined["observed_mm"], joined["actual_mm"])
    return joined, summary


def _scores(joined: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    hourly_rows, event_rows = [], []
    for horizon, group in joined.groupby("horizon_h", sort=True):
        group = group.sort_values("valid_datetime")
        y = group["observed_mm"].to_numpy(dtype=float)
        for model in MODELS:
            amount_col = {"dual_head": "dual_amount_mm", "standard": "standard_amount_mm",
                          "persistence": "persistence_mm"}[model]
            amount = group[amount_col].to_numpy(dtype=float)
            alerts = (group["dual_alert"].to_numpy(dtype=bool) if model == "dual_head"
                      else amount > THRESHOLD)
            metrics = score_pairs(y, amount)
            metrics.update(detection_scores(y, np.where(alerts, 6.0, 0.0), THRESHOLD))
            hourly_rows.append({"horizon_h": horizon, "model": model, **metrics})
            event, _ = score_episodes(pd.DatetimeIndex(group["valid_datetime"]), y,
                                      np.where(alerts, 6.0, 0.0), threshold=THRESHOLD)
            event_rows.append({"horizon_h": horizon, "model": model, **event})
    return pd.DataFrame(hourly_rows), pd.DataFrame(event_rows)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="So sánh mô hình bằng nhãn mưa trạm đã chuẩn hóa")
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--station-metadata", type=Path, required=True)
    parser.add_argument("--predictions", type=Path,
                        default=ROOT / "reports" / "rain_alert_experiment" / "test_predictions.parquet")
    parser.add_argument("--model-summary", type=Path,
                        default=ROOT / "reports" / "rain_alert_experiment" / "test_summary.json")
    parser.add_argument("--start-after", help="Chỉ đánh giá giờ sau mốc có UTC offset này")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "reports" / "independent_observations" / "gauge_evaluation")
    args = parser.parse_args()
    metadata = json.loads(args.station_metadata.read_text(encoding="utf-8"))
    if not metadata.get("station_name") or "station_latitude" not in metadata:
        raise ValueError("Metadata trạm thiếu tên hoặc tọa độ")
    if metadata.get("normalized_sha256") and (
        hashlib.sha256(args.observations.read_bytes()).hexdigest() != metadata["normalized_sha256"]
    ):
        raise ValueError("CSV trạm đã thay đổi so với metadata; chuẩn hóa lại trước khi đánh giá")
    frozen = json.loads(args.model_summary.read_text(encoding="utf-8"))
    threshold = float(frozen["selected_probability_threshold"])
    if not 0 < threshold < 1:
        raise ValueError("Ngưỡng xác suất của model không hợp lệ")
    if args.predictions.is_dir():
        files = sorted(args.predictions.glob("*.parquet"))
        if not files:
            raise ValueError("Thư mục dự báo chưa có file .parquet")
        predictions = pd.concat([pd.read_parquet(file) for file in files], ignore_index=True)
    else:
        predictions = pd.read_parquet(args.predictions)
    observations = pd.read_csv(args.observations)
    matched, summary = _validate_and_join(predictions, observations, threshold,
                                          _cutoff(args.start_after))
    summary.update({"station": metadata["station_name"],
                    "station_source": metadata.get("source_name"),
                    "predictions_file": str(args.predictions.resolve()),
                    "start_after": args.start_after})
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not matched.empty:
        hourly, events = _scores(matched)
        matched.to_parquet(out / "matched_predictions.parquet", index=False)
        hourly.to_csv(out / "metrics_by_horizon.csv", index=False)
        events.to_csv(out / "event_metrics_by_horizon.csv", index=False)
    (out / "evaluation_summary.json").write_text(
        json.dumps(_clean(summary), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )
    print(f"status={summary['status']}; matched_pairs={summary['matched_pairs']}")


if __name__ == "__main__":
    main()
