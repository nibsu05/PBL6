# ==============================================================================
# download_openmeteo.py — Thu thập dữ liệu thời tiết bề mặt từ Open-Meteo API
# ==============================================================================
"""
Module tải dữ liệu hourly từ Open-Meteo Historical Weather API cho Đà Nẵng.

Các biến thu thập:
  - temperature_2m          (°C)
  - relative_humidity_2m    (%)
  - surface_pressure        (hPa)
  - wind_speed_10m          (km/h)
  - wind_direction_10m      (°)
  - precipitation           (mm) — Biến TARGET

Sử dụng:
  python download_openmeteo.py

Output:
  raw_data/openmeteo_danang_2015_2023.csv
"""

import sys
import logging
import pandas as pd
import numpy as np

# --- Thư viện Open-Meteo chuyên dụng ---
import openmeteo_requests
import requests_cache
from retry_requests import retry

# --- Cấu hình từ config.py ---
from config import (
    DANANG_LAT, DANANG_LON,
    START_YEAR, END_YEAR,
    OPENMETEO_HOURLY_VARS, OPENMETEO_URL,
    OPENMETEO_OUTPUT,
    OPENMETEO_CACHE_DB, OPENMETEO_CACHE_TTL,
    RETRY_MAX_ATTEMPTS, RETRY_BACKOFF_FACTOR,
)

# ==============================================================================
# CẤU HÌNH LOGGING
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def create_openmeteo_client():
    """
    Tạo Open-Meteo API client với:
      - requests-cache: Cache response vào SQLite để tránh gọi lại API khi re-run
      - retry-requests: Tự động retry khi gặp lỗi mạng / HTTP 5xx
    """
    # Tạo cached session (lưu response vào SQLite DB)
    cache_session = requests_cache.CachedSession(
        OPENMETEO_CACHE_DB,
        expire_after=OPENMETEO_CACHE_TTL,  # Cache hết hạn sau 1 ngày
    )
    
    # Wrap session với retry logic
    retry_session = retry(
        cache_session,
        retries=RETRY_MAX_ATTEMPTS,
        backoff_factor=RETRY_BACKOFF_FACTOR,
    )
    
    # Tạo Open-Meteo client sử dụng session đã cấu hình
    client = openmeteo_requests.Client(session=retry_session)
    
    logger.info("Đã tạo Open-Meteo client (cache=%s, retries=%d)",
                OPENMETEO_CACHE_DB, RETRY_MAX_ATTEMPTS)
    return client


def fetch_year(client, year: int) -> pd.DataFrame:
    """
    Tải dữ liệu hourly cho 1 năm cụ thể.
    
    Chia theo năm để:
      - Tránh vượt giới hạn payload của API
      - Dễ theo dõi tiến độ
      - Nếu 1 năm fail, không ảnh hưởng các năm khác
    
    Args:
        client: Open-Meteo API client
        year: Năm cần tải (VD: 2015)
        
    Returns:
        pd.DataFrame với cột datetime + 6 biến thời tiết
    """
    start_date = f"{year}-01-01"
    # Cho năm cuối cùng (VD: 2026), chỉ lấy đến END_DATE thay vì 31/12
    from config import END_DATE
    if year == END_YEAR:
        end_date = END_DATE
    else:
        end_date = f"{year}-12-31"
    
    params = {
        "latitude": DANANG_LAT,
        "longitude": DANANG_LON,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": OPENMETEO_HOURLY_VARS,
        "timezone": "GMT",  # Lấy dữ liệu theo UTC, chuyển timezone ở bước merge
    }
    
    logger.info("Đang tải dữ liệu Open-Meteo cho năm %d ...", year)
    
    # Gọi API — trả về list responses (1 response cho mỗi location)
    responses = client.weather_api(OPENMETEO_URL, params=params)
    response = responses[0]  # Chỉ có 1 location
    
    # Log thông tin response
    logger.info(
        "  → Tọa độ thực tế: %.4f°N, %.4f°E | Elevation: %.1fm | Timezone: %s",
        response.Latitude(), response.Longitude(),
        response.Elevation(), response.Timezone(),
    )
    
    # Trích xuất dữ liệu hourly
    hourly = response.Hourly()
    
    # Tạo chuỗi datetime từ Unix timestamp
    # hourly.Time() = timestamp bắt đầu, hourly.TimeEnd() = timestamp kết thúc
    # hourly.Interval() = khoảng cách giữa 2 bản ghi (3600s = 1 giờ)
    datetime_range = pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(value=int(hourly.Interval()), unit="s"),
        inclusive="left",  # Không bao gồm TimeEnd
    )
    
    # Trích xuất giá trị từng biến (theo thứ tự đã request)
    # Variables(i) → biến thứ i trong danh sách OPENMETEO_HOURLY_VARS
    hourly_data = {"datetime": datetime_range}
    for i, var_name in enumerate(OPENMETEO_HOURLY_VARS):
        values = hourly.Variables(i).ValuesAsNumpy()
        hourly_data[var_name] = values
    
    df = pd.DataFrame(data=hourly_data)
    
    logger.info("  → Năm %d: %d bản ghi, từ %s đến %s",
                year, len(df), df["datetime"].iloc[0], df["datetime"].iloc[-1])
    
    return df


def main():
    """
    Hàm chính: Tải toàn bộ dữ liệu 2015–2023 và lưu ra CSV.
    """
    logger.info("=" * 70)
    logger.info("BẮT ĐẦU TẢI DỮ LIỆU OPEN-METEO CHO ĐÀ NẴNG")
    logger.info("  Tọa độ: %.4f°N, %.4f°E", DANANG_LAT, DANANG_LON)
    logger.info("  Khoảng thời gian: %d – %d", START_YEAR, END_YEAR)
    logger.info("  Biến: %s", ", ".join(OPENMETEO_HOURLY_VARS))
    logger.info("=" * 70)
    
    # Tạo client với cache và retry
    client = create_openmeteo_client()
    
    # Tải từng năm và gom lại
    all_dfs = []
    for year in range(START_YEAR, END_YEAR + 1):
        try:
            df_year = fetch_year(client, year)
            all_dfs.append(df_year)
        except Exception as e:
            logger.error("LỖI khi tải năm %d: %s", year, e)
            logger.error("Bỏ qua năm %d và tiếp tục...", year)
            continue
    
    if not all_dfs:
        logger.error("Không tải được dữ liệu nào! Dừng chương trình.")
        sys.exit(1)
    
    # Ghép tất cả các năm thành 1 DataFrame
    df_all = pd.concat(all_dfs, ignore_index=True)
    
    # Sắp xếp theo thời gian và loại bỏ duplicate (nếu có do overlap)
    df_all = df_all.sort_values("datetime").drop_duplicates(subset="datetime").reset_index(drop=True)
    
    # --- Thống kê tổng quan ---
    logger.info("=" * 70)
    logger.info("THỐNG KÊ DỮ LIỆU OPEN-METEO")
    logger.info("  Tổng bản ghi: %d", len(df_all))
    logger.info("  Khoảng thời gian: %s → %s",
                df_all["datetime"].iloc[0], df_all["datetime"].iloc[-1])
    
    # Kiểm tra missing values
    missing = df_all.isnull().sum()
    if missing.any():
        logger.warning("  Missing values:")
        for col, count in missing.items():
            if count > 0:
                pct = count / len(df_all) * 100
                logger.warning("    %s: %d (%.2f%%)", col, count, pct)
    else:
        logger.info("  Không có missing values ✓")
    
    # Lưu ra CSV
    df_all.to_csv(OPENMETEO_OUTPUT, index=False)
    logger.info("  Đã lưu: %s (%.2f MB)",
                OPENMETEO_OUTPUT, OPENMETEO_OUTPUT.stat().st_size / 1e6)
    
    logger.info("=" * 70)
    logger.info("HOÀN TẤT TẢI DỮ LIỆU OPEN-METEO!")
    logger.info("=" * 70)
    
    return df_all


if __name__ == "__main__":
    main()
