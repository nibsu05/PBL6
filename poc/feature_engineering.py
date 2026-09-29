# ==============================================================================
# feature_engineering.py — Tạo đặc trưng cho tập PoC
# ==============================================================================
"""
Module 3: Feature Engineering cho tập PoC.
Áp dụng trên file datasets/dataset_poc_2025_2026.parquet

Các đặc trưng được tạo:
1. Mã hóa chu kỳ: sin_hour, cos_hour, sin_month, cos_month
2. Biến trễ (Lag): 1h, 2h, 3h, 6h, 12h, 24h cho precipitation
3. Thống kê cuộn: precip_roll_sum_3h, 6h, 24h
4. Đặc trưng vật lý: wind_speed_850, sst_air_temp_diff

* Lưu ý: CAPE, CIN, TCWV đang được bỏ qua trong PoC hiện tại (do ERA5 chưa tải).

Sử dụng:
  python feature_engineering.py
"""

import sys
import logging
from pathlib import Path
import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATASETS_DIR = BASE_DIR / "datasets"
POC_DATASET = DATASETS_DIR / "dataset_poc_2025_2026.parquet"

def apply_feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Applying Feature Engineering...")
    initial_cols = len(df.columns)
    
    # --- 1. Mã hóa chu kỳ (Cyclical Encoding) ---
    logger.info("  1. Cyclical Encoding (hour, month)...")
    # Đảm bảo datetime index
    if "datetime" not in df.columns:
        raise ValueError("DataFrame must contain 'datetime' column.")
    
    hour = df["datetime"].dt.hour
    month = df["datetime"].dt.month
    
    df["sin_hour"] = np.sin(2 * np.pi * hour / 24)
    df["cos_hour"] = np.cos(2 * np.pi * hour / 24)
    df["sin_month"] = np.sin(2 * np.pi * month / 12)
    df["cos_month"] = np.cos(2 * np.pi * month / 12)
    
    # --- 2. Biến trễ (Lag) cho precipitation ---
    logger.info("  2. Lag Features (precipitation)...")
    target_col = "precipitation"
    if target_col in df.columns:
        lags = [1, 2, 3, 6, 12, 24]
        for lag in lags:
            df[f"precip_lag_{lag}h"] = df[target_col].shift(lag)
            
        # Thống kê cuộn (Rolling Sum)
        logger.info("  3. Rolling Statistics...")
        windows = [3, 6, 24]
        for w in windows:
            # Dùng shift(1) để tránh data leakage (chỉ tính tổng của các giờ TRƯỚC đó)
            df[f"precip_roll_sum_{w}h"] = df[target_col].shift(1).rolling(window=w).sum()
    else:
        logger.warning("  Target column '%s' not found! Skipping lag features.", target_col)
        
    # --- 3. Đặc trưng vật lý khí hậu địa phương ---
    logger.info("  4. Physical Features...")
    
    # Vận tốc gió tầng 850hPa
    if "u_wind_850hpa" in df.columns and "v_wind_850hpa" in df.columns:
        df["wind_speed_850"] = np.sqrt(df["u_wind_850hpa"]**2 + df["v_wind_850hpa"]**2)
        logger.info("    + wind_speed_850 created")
    else:
        logger.warning("    - Missing u/v wind_850hpa")
        
    # Chênh lệch nhiệt độ biển - không khí
    if "sea_surface_temperature" in df.columns and "temperature_2m" in df.columns:
        df["sst_air_temp_diff"] = df["sea_surface_temperature"] - df["temperature_2m"]
        logger.info("    + sst_air_temp_diff created")
    else:
        logger.warning("    - Missing SST or temperature_2m")
        
    # * Ghi chú: CAPE, CIN, TCWV đang bị thiếu trong dataset hiện tại

    # Bỏ các hàng có giá trị NaN do lag và rolling tạo ra
    rows_before = len(df)
    df = df.dropna().reset_index(drop=True)
    rows_after = len(df)
    logger.info("  Dropped %d rows containing NaNs from Lag/Rolling features.", rows_before - rows_after)
    
    logger.info("Feature Engineering Complete. Added %d features.", len(df.columns) - initial_cols)
    return df


def main():
    logger.info("=" * 70)
    logger.info("FEATURE ENGINEERING (Module 3)")
    logger.info("=" * 70)
    
    if not POC_DATASET.exists():
        logger.error("PoC dataset not found: %s", POC_DATASET)
        logger.info("Please run build_datasets.py first.")
        sys.exit(1)
        
    df = pd.read_parquet(POC_DATASET)
    logger.info("Loaded PoC dataset: %s", df.shape)
    
    df_engineered = apply_feature_engineering(df)
    
    # Ghi đè lại hoặc lưu file mới (ở đây chọn ghi đè để tiện cho pipeline)
    df_engineered.to_parquet(POC_DATASET, index=False, engine="pyarrow")
    logger.info("Saved engineered dataset to %s", POC_DATASET.name)
    logger.info("New shape: %s", df_engineered.shape)

if __name__ == "__main__":
    main()
