# ==============================================================================
# download_enso.py — Thu thập chỉ số ONI/ENSO từ NOAA CPC
# ==============================================================================
"""
Module tải và xử lý chỉ số Oceanic Niño Index (ONI) từ NOAA Climate
Prediction Center.

Chỉ số ONI là chỉ báo chính của hiện tượng El Niño / La Niña, ảnh hưởng
đáng kể đến lượng mưa tại miền Trung Việt Nam.

Nguồn dữ liệu:
  https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt

Format gốc:
  - Dữ liệu theo mùa 3 tháng trượt (DJF, JFM, FMA, ...)
  - Cột: SEAS, YR, TOTAL, ANOM
  - ANOM = Anomaly so với trung bình khí hậu (giá trị chính cần dùng)

Pipeline xử lý:
  1. Tải file text từ NOAA
  2. Parse thành DataFrame
  3. Map mùa → tháng giữa (DJF→Jan, JFM→Feb, ...)
  4. Filter 2015–2023
  5. Resample từ monthly → hourly (forward-fill)

Sử dụng:
  python download_enso.py

Output:
  raw_data/enso_oni_2015_2023.csv
"""

import sys
import logging
import requests
import pandas as pd
import numpy as np
from io import StringIO

from config import (
    START_YEAR, END_YEAR, END_DATE,
    NOAA_ONI_URL,
    ENSO_OUTPUT,
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

# ==============================================================================
# MAPPING MÙA → THÁNG
# ==============================================================================
# Mỗi mùa 3 tháng trượt (3-month rolling season)
# Ta map mỗi mùa về tháng GIỮA của nó.
# VD: DJF (Dec-Jan-Feb) → tháng giữa = January
#     JFM (Jan-Feb-Mar) → tháng giữa = February
#     ...
#     NDJ (Nov-Dec-Jan) → tháng giữa = December

SEASON_TO_MONTH = {
    "DJF": 1,   # Dec-Jan-Feb → January
    "JFM": 2,   # Jan-Feb-Mar → February
    "FMA": 3,   # Feb-Mar-Apr → March
    "MAM": 4,   # Mar-Apr-May → April
    "AMJ": 5,   # Apr-May-Jun → May
    "MJJ": 6,   # May-Jun-Jul → June
    "JJA": 7,   # Jun-Jul-Aug → July
    "JAS": 8,   # Jul-Aug-Sep → August
    "ASO": 9,   # Aug-Sep-Oct → September
    "SON": 10,  # Sep-Oct-Nov → October
    "OND": 11,  # Oct-Nov-Dec → November
    "NDJ": 12,  # Nov-Dec-Jan → December
}


def download_oni_raw() -> pd.DataFrame:
    """
    Tải file ONI text từ NOAA và parse thành DataFrame.
    
    Returns:
        pd.DataFrame với cột: SEAS, YR, TOTAL, ANOM
    """
    logger.info("Đang tải chỉ số ONI từ NOAA CPC...")
    logger.info("  URL: %s", NOAA_ONI_URL)
    
    response = requests.get(NOAA_ONI_URL, timeout=30)
    response.raise_for_status()
    
    logger.info("  Tải thành công (%d bytes)", len(response.content))
    
    # Parse fixed-width format
    # Header: "SEAS  YR   TOTAL   ANOM"
    # Data:   " DJF 1950  25.01  -1.32"
    df = pd.read_fwf(
        StringIO(response.text),
        colspecs=[(0, 5), (5, 10), (10, 18), (18, 25)],
        names=["SEAS", "YR", "TOTAL", "ANOM"],
        skiprows=1,  # Bỏ header
    )
    
    # Clean up: strip whitespace, convert types
    df["SEAS"] = df["SEAS"].str.strip()
    df["YR"] = pd.to_numeric(df["YR"], errors="coerce")
    df["TOTAL"] = pd.to_numeric(df["TOTAL"], errors="coerce")
    df["ANOM"] = pd.to_numeric(df["ANOM"], errors="coerce")
    
    # Loại bỏ rows không hợp lệ
    df = df.dropna(subset=["YR", "ANOM"]).reset_index(drop=True)
    df["YR"] = df["YR"].astype(int)
    
    logger.info("  Tổng bản ghi ONI: %d (từ %d đến %d)",
                len(df), df["YR"].min(), df["YR"].max())
    
    return df


def process_oni_to_monthly(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Chuyển đổi dữ liệu ONI từ format theo mùa sang chuỗi thời gian monthly.
    
    1. Map mùa → tháng giữa
    2. Tạo datetime từ (YR, month)
    3. Filter khoảng thời gian cần thiết
    4. Giữ lại cột oni_anom
    
    Args:
        df_raw: DataFrame gốc từ NOAA
        
    Returns:
        pd.DataFrame với cột: datetime (monthly), oni_anom
    """
    logger.info("Đang xử lý ONI theo tháng...")
    
    # Map mùa → tháng
    df = df_raw.copy()
    df["month"] = df["SEAS"].map(SEASON_TO_MONTH)
    
    # Kiểm tra mapping thành công
    unmapped = df[df["month"].isna()]
    if not unmapped.empty:
        logger.warning("  Có %d mùa không nhận dạng được: %s",
                       len(unmapped), unmapped["SEAS"].unique())
        df = df.dropna(subset=["month"])
    
    df["month"] = df["month"].astype(int)
    
    # Tạo datetime (ngày 1 của mỗi tháng, UTC)
    df["datetime"] = pd.to_datetime(
        df["YR"].astype(str) + "-" + df["month"].astype(str).str.zfill(2) + "-01",
        utc=True,
    )
    
    # Filter khoảng thời gian: mở rộng thêm vài tháng trước/sau để forward-fill không bị thiếu
    filter_start = f"{START_YEAR - 1}-01-01"
    filter_end = f"{END_YEAR + 1}-12-31"
    df = df[(df["datetime"] >= filter_start) & (df["datetime"] <= filter_end)]
    
    # Nếu có nhiều giá trị cho cùng 1 tháng (do mùa trượt), lấy trung bình
    df = df.groupby("datetime").agg({"ANOM": "mean"}).reset_index()
    df = df.rename(columns={"ANOM": "oni_anom"})
    df = df.sort_values("datetime").reset_index(drop=True)
    
    logger.info("  ONI monthly: %d bản ghi, từ %s đến %s",
                len(df), df["datetime"].iloc[0], df["datetime"].iloc[-1])
    
    return df


def resample_to_hourly(df_monthly: pd.DataFrame) -> pd.DataFrame:
    """
    Chuyển đổi ONI từ monthly → hourly bằng forward-fill.
    
    Vì ONI là chỉ số khí hậu vĩ mô (biến đổi chậm, theo tháng/mùa),
    việc forward-fill từ monthly sang hourly là hợp lý:
    - Giá trị ONI của tháng 1/2015 sẽ được áp dụng cho tất cả các giờ trong tháng 1/2015
    
    Args:
        df_monthly: DataFrame ONI theo tháng
        
    Returns:
        pd.DataFrame với cột: datetime (hourly, UTC), oni_anom
    """
    logger.info("Đang resample ONI từ monthly → hourly (forward-fill)...")
    
    # Set datetime làm index
    df = df_monthly.set_index("datetime")
    
    # Resample sang hourly và forward-fill
    # 'h' = hourly frequency
    df_hourly = df.resample("h").ffill()
    
    # Filter chính xác khoảng thời gian cần thiết
    start = pd.Timestamp(f"{START_YEAR}-01-01", tz="UTC")
    end = pd.Timestamp(f"{END_DATE} 23:00:00", tz="UTC")
    df_hourly = df_hourly[start:end]
    
    # Reset index để datetime thành cột
    df_hourly = df_hourly.reset_index()
    
    logger.info("  ONI hourly: %d bản ghi, từ %s đến %s",
                len(df_hourly), df_hourly["datetime"].iloc[0],
                df_hourly["datetime"].iloc[-1])
    
    return df_hourly


def main():
    """
    Hàm chính: Tải ONI, xử lý, forward-fill hourly, lưu CSV.
    """
    logger.info("=" * 70)
    logger.info("BẮT ĐẦU TẢI CHỈ SỐ ONI/ENSO TỪ NOAA")
    logger.info("  Khoảng thời gian: %d – %d", START_YEAR, END_YEAR)
    logger.info("=" * 70)
    
    # Bước 1: Tải raw data từ NOAA
    df_raw = download_oni_raw()
    
    # Bước 2: Xử lý thành monthly time series
    df_monthly = process_oni_to_monthly(df_raw)
    
    # Bước 3: Forward-fill sang hourly
    df_hourly = resample_to_hourly(df_monthly)
    
    # --- Thống kê ---
    logger.info("=" * 70)
    logger.info("THỐNG KÊ CHỈ SỐ ONI/ENSO")
    logger.info("  Tổng bản ghi hourly: %d", len(df_hourly))
    logger.info("  Missing values: %d", df_hourly["oni_anom"].isna().sum())
    logger.info("  ONI range: [%.2f, %.2f]",
                df_hourly["oni_anom"].min(), df_hourly["oni_anom"].max())
    logger.info("  ONI mean:  %.3f", df_hourly["oni_anom"].mean())
    
    # Phân loại ENSO phases (thông tin tham khảo)
    el_nino_count = (df_hourly["oni_anom"] >= 0.5).sum()
    la_nina_count = (df_hourly["oni_anom"] <= -0.5).sum()
    neutral_count = len(df_hourly) - el_nino_count - la_nina_count
    logger.info("  El Niño (≥+0.5): %d giờ (%.1f%%)",
                el_nino_count, el_nino_count / len(df_hourly) * 100)
    logger.info("  La Niña (≤-0.5): %d giờ (%.1f%%)",
                la_nina_count, la_nina_count / len(df_hourly) * 100)
    logger.info("  Neutral:         %d giờ (%.1f%%)",
                neutral_count, neutral_count / len(df_hourly) * 100)
    
    # Lưu ra CSV
    df_hourly.to_csv(ENSO_OUTPUT, index=False)
    logger.info("  Đã lưu: %s (%.2f KB)",
                ENSO_OUTPUT, ENSO_OUTPUT.stat().st_size / 1e3)
    
    logger.info("=" * 70)
    logger.info("HOÀN TẤT TẢI CHỈ SỐ ONI/ENSO!")
    logger.info("=" * 70)
    
    return df_hourly


if __name__ == "__main__":
    main()
