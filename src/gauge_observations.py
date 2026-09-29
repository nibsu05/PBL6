"""Chuẩn hóa mưa trạm theo giờ; không tự tạo giờ khô hoặc nội suy nhãn.

Mỗi hàng phải là tổng lượng mưa của một khoảng đúng 60 phút. Cột thời gian
có thể là đầu hoặc cuối khoảng, nhưng quy ước đó phải được khai báo rõ.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

LOCAL_TZ = "Asia/Ho_Chi_Minh"
DANANG_LAT, DANANG_LON = 16.0544, 108.2022


@dataclass(frozen=True)
class GaugeConfig:
    station_name: str
    latitude: float
    longitude: float
    source_name: str
    source_timezone: str
    timestamp_means: str  # "end": nhãn là cuối giờ; "start": cộng 1 giờ.
    accumulation_hours: float  # Phải do đơn vị trạm xác nhận là đúng 1 giờ.
    datetime_column: str = "datetime"
    rain_column: str = "precipitation_mm_h"
    station_column: str | None = None
    station_value: str | None = None
    quality_column: str | None = None
    accepted_quality: tuple[str, ...] = ()
    datetime_format: str | None = None
    sheet_name: str | int = 0
    max_distance_km: float = 30.0


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(np.deg2rad, (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    hav = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return float(6371.0 * 2 * np.arcsin(np.sqrt(hav)))


def _read_export(path: Path, sheet: str | int) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, encoding="utf-8-sig")
    if path.suffix.lower() == ".xlsx":
        try:
            return pd.read_excel(path, sheet_name=sheet)
        except ImportError as exc:
            raise ImportError("Cần cài openpyxl (xem requirements.txt) để đọc .xlsx") from exc
    raise ValueError("Chỉ hỗ trợ .csv hoặc .xlsx; hãy xuất dữ liệu trạm sang một trong hai định dạng")


def _parse_hour(values: pd.Series, config: GaugeConfig) -> pd.Series:
    try:
        ZoneInfo(config.source_timezone)
    except Exception as exc:
        raise ValueError(f"Múi giờ nguồn không hợp lệ: {config.source_timezone}") from exc
    times = pd.to_datetime(values, errors="raise", format=config.datetime_format)
    if not isinstance(times, pd.Series):
        times = pd.Series(times, index=values.index)
    if isinstance(times.dtype, pd.DatetimeTZDtype):
        times = times.dt.tz_convert(LOCAL_TZ)
    else:
        # File Excel/CSV không có offset chỉ được hiểu theo source_timezone đã khai báo.
        times = times.dt.tz_localize(config.source_timezone).dt.tz_convert(LOCAL_TZ)
    if config.timestamp_means == "start":
        times = times + pd.Timedelta(hours=1)
    if times.isna().any() or not times.eq(times.dt.floor("h")).all():
        raise ValueError("Timestamp phải đúng đầu giờ; không tự làm tròn giờ trạm")
    return times


def normalize_gauge_export(path: str | Path, config: GaugeConfig) -> tuple[pd.DataFrame, dict]:
    """Trả CSV chuẩn và metadata QC; thiếu số đo được bỏ có ghi số lượng."""
    path = Path(path)
    if not path.is_file() or not config.station_name.strip() or not config.source_name.strip():
        raise ValueError("Cần file hiện có, tên trạm và tên nguồn rõ ràng")
    if config.timestamp_means not in {"start", "end"}:
        raise ValueError("timestamp_means phải là start hoặc end")
    if config.accumulation_hours != 1:
        raise ValueError("Chỉ nhận tổng mưa đúng 1 giờ; không phân bổ mưa 6/12/24 giờ")
    if not (-90 <= config.latitude <= 90 and -180 <= config.longitude <= 180):
        raise ValueError("Tọa độ trạm không hợp lệ")
    distance = _distance_km(DANANG_LAT, DANANG_LON, config.latitude, config.longitude)
    if not np.isfinite(distance) or distance > config.max_distance_km:
        raise ValueError(f"Trạm cách điểm nghiên cứu {distance:.1f} km, vượt giới hạn "
                         f"{config.max_distance_km:.1f} km; kiểm tra tọa độ")
    if bool(config.station_column) != bool(config.station_value):
        raise ValueError("station_column và station_value phải đi cùng nhau")
    if bool(config.quality_column) != bool(config.accepted_quality):
        raise ValueError("quality_column và accepted_quality phải đi cùng nhau")
    raw = _read_export(path, config.sheet_name)
    required = {config.datetime_column, config.rain_column}
    if config.station_column:
        required.add(config.station_column)
    if config.quality_column:
        required.add(config.quality_column)
    if raw.empty or required - set(raw):
        raise ValueError(f"File trạm rỗng hoặc thiếu cột: {sorted(required - set(raw))}")
    if not config.station_column:
        station_aliases = {"station", "station_id", "station_name", "ten_tram", "tên trạm",
                           "ma_tram", "mã trạm"}
        mixed = [name for name in raw if name.strip().lower() in station_aliases
                 and raw[name].dropna().nunique() > 1]
        if mixed:
            raise ValueError(f"File có nhiều trạm trong cột {mixed}; cần --station-column/--station-value")
    total_rows = len(raw)
    if config.station_column:
        raw = raw.loc[raw[config.station_column].astype(str) == config.station_value].copy()
        if raw.empty:
            raise ValueError("Không có hàng thuộc trạm đã chọn")
    station_rows = len(raw)
    quality_counts = None
    if config.quality_column:
        quality = raw[config.quality_column].astype("string").str.strip()
        quality_counts = {str(k): int(v) for k, v in quality.value_counts(dropna=False).items()}
        raw = raw.loc[quality.isin(config.accepted_quality)].copy()
        if raw.empty:
            raise ValueError("Không còn hàng đạt mã chất lượng đã chấp nhận")
    quality_rows = len(raw)

    times = _parse_hour(raw[config.datetime_column], config)
    rain_original = raw[config.rain_column]
    rain = pd.to_numeric(rain_original, errors="coerce")
    invalid_text = rain.isna() & rain_original.notna() & rain_original.astype(str).str.strip().ne("")
    if invalid_text.any():
        raise ValueError(f"Có {int(invalid_text.sum())} giá trị mưa không phải số; xử lý thủ công trước")
    if np.isinf(rain.to_numpy(dtype=float)).any() or (rain < 0).any():
        raise ValueError("Lượng mưa âm hoặc vô hạn")
    missing_rain = int(rain.isna().sum())
    normalized = pd.DataFrame({"datetime": times, "precipitation_mm_h": rain})
    normalized = normalized.dropna(subset=["precipitation_mm_h"]).sort_values("datetime")
    if normalized.empty:
        raise ValueError("Không còn giờ có lượng mưa hợp lệ")
    if normalized["datetime"].duplicated().any():
        raise ValueError("Có giờ trạm trùng; cần giải quyết bản ghi trùng trước khi đánh giá")
    first, last = normalized["datetime"].iloc[0], normalized["datetime"].iloc[-1]
    span_hours = int((last - first) / pd.Timedelta(hours=1)) + 1
    metadata = {
        "station_name": config.station_name,
        "station_latitude": config.latitude,
        "station_longitude": config.longitude,
        "distance_to_danang_km": round(distance, 3),
        "source_name": config.source_name,
        "source_file": str(path.resolve()),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_timezone": config.source_timezone,
        "timestamp_means": config.timestamp_means,
        "accumulation_hours_confirmed": config.accumulation_hours,
        "normalized_timestamp_means": "end_of_preceding_hour",
        "row_count_raw": total_rows,
        "row_count_selected_station": station_rows,
        "row_count_after_quality_filter": quality_rows,
        "row_count_with_rain": len(normalized),
        "quality_codes": quality_counts,
        "missing_rain_rows": missing_rain,
        "missing_calendar_hours_in_span": span_hours - len(normalized),
        "first_hour_local": first.isoformat(),
        "last_hour_local": last.isoformat(),
        "hours_over_5_mm": int((normalized["precipitation_mm_h"] > 5).sum()),
        "max_mm_h": float(normalized["precipitation_mm_h"].max()),
        "caution": "Giờ không có bản ghi không được coi là 0 mm; cần xác nhận kỳ tích lũy với đơn vị trạm.",
    }
    return normalized.reset_index(drop=True), metadata
