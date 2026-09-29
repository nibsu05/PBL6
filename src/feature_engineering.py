"""Tạo đặc trưng khí tượng theo giờ cho bài toán dự báo mưa Đà Nẵng.

Hàm công khai ``engineer_features`` không tự điền các giờ thiếu. Các giờ này
được giữ với NaN để bước tạo cửa sổ có thể loại toàn bộ chuỗi đi qua lỗ hổng
ERA5, thay vì vô tình coi hai mốc xa nhau là hai giờ liên tiếp.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)
TIMEZONE = "Asia/Ho_Chi_Minh"

_ALIASES = {
    "u_850": ("u850", "u_wind_850hpa"),
    "v_850": ("v850", "v_wind_850hpa"),
    "specific_humidity_850": ("specific_humidity_850hpa", "q850"),
    "oni": ("oni_anom", "oni_index"),
    "cape": ("CAPE",),
    "cin": ("CIN",),
    "tcwv": ("TCWV",),
}


def _canonicalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Đổi các tên cũ của dữ liệu PoC sang tên thống nhất."""
    rename = {}
    for canonical, alternatives in _ALIASES.items():
        if canonical in frame.columns:
            continue
        for alternative in alternatives:
            if alternative in frame.columns:
                rename[alternative] = canonical
                break
    return frame.rename(columns=rename)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Bổ sung đặc trưng trên trục giờ UTC+7, không dùng thông tin tương lai.

    ``precipitation`` tại giờ hiện tại có thể là đầu vào vì mô hình chỉ dự báo
    các giờ *sau* cuối cửa sổ quan sát. Các lag và tổng cuộn ở giờ t chỉ dùng
    dữ liệu đến t-1. Hàm không xóa NaN: việc lọc chuỗi thiếu do dataset xử lý.
    """
    if "datetime" not in df.columns:
        raise ValueError("Dữ liệu phải có cột 'datetime'.")
    if "precipitation" not in df.columns:
        raise ValueError("Dữ liệu phải có cột mục tiêu 'precipitation'.")
    if df.empty:
        raise ValueError("Không có bản ghi để tạo đặc trưng.")

    frame = _canonicalize_columns(df.copy())
    timestamps = pd.DatetimeIndex(pd.to_datetime(frame["datetime"], errors="raise"))
    # NetCDF/CSV chuẩn phải ghi rõ timezone. Với mốc naive do người dùng truyền,
    # quy ước đó là giờ địa phương; không tự gán UTC rồi dịch sai 7 giờ.
    if timestamps.tz is None:
        LOGGER.warning("Datetime chưa có timezone; hiểu là giờ Asia/Ho_Chi_Minh.")
        timestamps = timestamps.tz_localize(TIMEZONE)
    else:
        timestamps = timestamps.tz_convert(TIMEZONE)
    if not (timestamps == timestamps.floor("h")).all():
        raise ValueError("Tất cả datetime phải nằm đúng đầu giờ.")

    frame["datetime"] = timestamps
    frame = frame.sort_values("datetime")
    if frame["datetime"].duplicated().any():
        raise ValueError("Datetime bị trùng; cần giải quyết trước khi tạo đặc trưng.")

    # asfreq tạo hàng NaN tại các giờ bị thiếu; shift/rolling sau đó mang đúng
    # ý nghĩa giờ thực, không bị trượt qua ngày/tháng thiếu ERA5.
    frame = frame.set_index("datetime").asfreq("h")
    inserted_hours = len(frame) - len(df)
    if inserted_hours:
        LOGGER.warning("Phát hiện %d giờ không có bản ghi; giữ NaN để loại cửa sổ qua gap.", inserted_hours)

    for column in frame.columns:
        if column in {"source", "quality_flag"}:
            continue
        if pd.api.types.is_numeric_dtype(frame[column]) or column in {
            "temperature_2m", "relative_humidity_2m", "surface_pressure",
            "wind_speed_10m", "wind_direction_10m", "precipitation",
            "sea_surface_temperature", "u_850", "v_850",
            "specific_humidity_850", "cape", "cin", "tcwv", "oni",
        }:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    hours = frame.index.hour
    months = frame.index.month
    frame["sin_hour"] = np.sin(2 * np.pi * hours / 24)
    frame["cos_hour"] = np.cos(2 * np.pi * hours / 24)
    frame["sin_month"] = np.sin(2 * np.pi * months / 12)
    frame["cos_month"] = np.cos(2 * np.pi * months / 12)

    # Lags dùng đúng mốc giờ vì toàn bộ trục thời gian đã được chuẩn hóa.
    for lag in (1, 2, 3, 6, 12, 24):
        frame[f"precip_lag_{lag}h"] = frame["precipitation"].shift(lag)
    for variable in ("relative_humidity_2m", "specific_humidity_850"):
        if variable not in frame:
            LOGGER.warning("Thiếu %s; bỏ qua các lag tương ứng.", variable)
            continue
        for lag in (1, 3, 6):
            frame[f"{variable}_lag_{lag}h"] = frame[variable].shift(lag)
    for window in (3, 6, 24):
        frame[f"precip_roll_sum_{window}h"] = (
            frame["precipitation"].shift(1).rolling(window, min_periods=window).sum()
        )

    if {"u_850", "v_850"}.issubset(frame.columns):
        frame["wind_speed_850"] = np.hypot(frame["u_850"], frame["v_850"])
    else:
        LOGGER.warning("Thiếu u_850/v_850; không tạo wind_speed_850.")
    if {"sea_surface_temperature", "temperature_2m"}.issubset(frame.columns):
        # Hai nhiệt độ đầu vào phải cùng đơn vị độ C (được chuẩn hóa ở merge).
        frame["sst_air_temp_diff"] = (
            frame["sea_surface_temperature"] - frame["temperature_2m"]
        )
    else:
        LOGGER.warning("Thiếu SST/nhiệt độ không khí; không tạo sst_air_temp_diff.")

    return frame.reset_index()


# Tên quen thuộc từ PoC cũ; giữ để dễ chuyển đổi mã huấn luyện hiện có.
apply_feature_engineering = engineer_features
