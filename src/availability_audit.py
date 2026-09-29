"""Kiểm tra 24 giờ đầu vào đã có sẵn khi phát hành từng dự báo hay chưa.

`available_at` của mỗi hàng phải là thời điểm *muộn nhất* mà tất cả biến
đầu vào của hàng đó đã có thể sử dụng, gồm cả mưa quan trắc. Không suy
available_at từ datetime của số đo hay thời điểm tải file archive.
"""

from __future__ import annotations

import pandas as pd


def _aware(series: pd.Series, name: str) -> pd.Series:
    result = pd.to_datetime(series, errors="raise")
    if not isinstance(result.dtype, pd.DatetimeTZDtype):
        raise ValueError(f"{name} phải có UTC offset")
    if result.isna().any():
        raise ValueError(f"{name} không được khuyết")
    return result.dt.tz_convert("Asia/Ho_Chi_Minh")


def audit_asof_windows(predictions: pd.DataFrame, availability: pd.DataFrame,
                       input_hours: int = 24) -> tuple[dict, pd.DataFrame]:
    """Xác nhận mỗi cửa sổ có đủ 24 hàng và mọi hàng sẵn có trước issued_at."""
    if input_hours < 1:
        raise ValueError("input_hours phải dương")
    need_p = {"last_input_datetime", "issued_at"}
    need_a = {"datetime", "available_at"}
    missing_p, missing_a = need_p - set(predictions), need_a - set(availability)
    if missing_p or missing_a:
        return ({"status": "unverified_missing_provenance",
                 "missing_prediction_columns": sorted(missing_p),
                 "missing_availability_columns": sorted(missing_a),
                 "verified_windows": 0}, pd.DataFrame())
    if predictions.empty or availability.empty:
        raise ValueError("Không có dự báo hoặc bản ghi availability để kiểm tra")
    p = predictions[["last_input_datetime", "issued_at"]].copy()
    p["last_input_datetime"] = _aware(p["last_input_datetime"], "last_input_datetime")
    p["issued_at"] = _aware(p["issued_at"], "issued_at")
    p = p.drop_duplicates().reset_index(drop=True)
    p["window_id"] = p.index
    a = availability[["datetime", "available_at"]].copy()
    a["datetime"] = _aware(a["datetime"], "datetime đầu vào")
    a["available_at"] = _aware(a["available_at"], "available_at")
    if (not p["last_input_datetime"].eq(p["last_input_datetime"].dt.floor("h")).all()
            or not a["datetime"].eq(a["datetime"].dt.floor("h")).all()):
        raise ValueError("Giờ đầu vào và anchor phải đúng đầu giờ")
    if a["datetime"].duplicated().any():
        raise ValueError("Availability có giờ đầu vào trùng")
    if (a["available_at"] < a["datetime"]).any():
        raise ValueError("available_at trước thời điểm số đo; kiểm tra metadata")
    offsets = pd.DataFrame({"offset_h": range(input_hours)})
    expanded = p.merge(offsets, how="cross")
    expanded["datetime"] = (expanded["last_input_datetime"]
                             - pd.to_timedelta(expanded["offset_h"], unit="h"))
    expanded = expanded.merge(a, on="datetime", how="left", validate="many_to_one")
    expanded["missing_input"] = expanded["available_at"].isna()
    expanded["late_input"] = (expanded["available_at"] > expanded["issued_at"]).fillna(False)
    by_window = expanded.groupby("window_id", sort=True).agg(
        missing_input_hours=("missing_input", "sum"),
        late_input_hours=("late_input", "sum"),
        latest_input_available_at=("available_at", "max"),
    ).reset_index().merge(p, on="window_id", validate="one_to_one")
    by_window["issue_after_first_target"] = (
        by_window["issued_at"] >= by_window["last_input_datetime"] + pd.Timedelta(hours=1)
    )
    by_window["ready"] = ((by_window["missing_input_hours"] == 0)
                           & (by_window["late_input_hours"] == 0)
                           & ~by_window["issue_after_first_target"])
    summary = {
        "status": "verified" if by_window["ready"].all() else "failed_asof_gate",
        "total_windows": len(by_window),
        "verified_windows": int(by_window["ready"].sum()),
        "windows_with_missing_input": int((by_window["missing_input_hours"] > 0).sum()),
        "windows_with_late_input": int((by_window["late_input_hours"] > 0).sum()),
        "windows_issued_after_first_target": int(by_window["issue_after_first_target"].sum()),
        "input_hours_per_window": input_hours,
        "rule": "Mỗi giờ của cửa sổ phải có available_at <= issued_at; issued_at < t+1.",
    }
    return summary, by_window
