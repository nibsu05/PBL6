# ==============================================================================
# download_era5_features.py — Thu thập bổ sung ERA5 theo QUÝ (2026 -> 2015)
# Biến: CAPE, CIN, TCWV, Soil Moisture (volumetric_soil_water_layer_1)
# ==============================================================================
"""
Script tải dữ liệu ERA5 Reanalysis từ Copernicus CDS API:
  - 4 biến trong cùng 1 request:
      1. convective_available_potential_energy (CAPE) [J/kg]
      2. convective_inhibition                 (CIN)  [J/kg]
      3. total_column_water_vapour            (TCWV) [kg/m^2]
      4. volumetric_soil_water_layer_1        (swvl1) [m^3/m^3] (Độ ẩm đất tầng mặt 0-7cm)
  - Ưu tiên từ mới nhất (2026) lùi dần về quá khứ (2015).
  - Gom theo QUÝ (3 tháng/request) — Đây là mức tối đa nằm trong Cost Limit của CDS API,
    giúp giảm từ 140 request xuống chỉ còn ~46 request (tiết kiệm 70% thời gian queue).
  - Giữ nguyên độ phân giải theo TỪNG GIỜ (hourly) cho mọi ngày trong quý.
  - Tự động bỏ qua các file đã tải xong (Resume mode).
  - Trích xuất điểm đất liền Đà Nẵng (16.00°N, 108.25°E) lưu lũy kế vào CSV.

Sử dụng:
  python data/download_era5_features.py [--extract]
"""

from __future__ import annotations
import os
import sys
import time
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone

import cdsapi
import numpy as np
import pandas as pd
import xarray as xr

# Đảm bảo UTF-8 cho console Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "data" / "raw_data" / "era5_nc_features"
PROCESSED_CSV = ROOT_DIR / "data" / "raw_data" / "era5_thermo_soil_2015_2026.csv"

# Tọa độ Đà Nẵng và ô lưới đất liền gần nhất
DANANG_LAT = 16.0544
DANANG_LON = 108.2022
TARGET_GRID_LAT = 16.00
TARGET_GRID_LON = 108.25

# Bounding box nhỏ quanh Đà Nẵng (~16 ô lưới 0.25x0.25 độ)
BBOX_AREA = [16.5, 107.75, 15.75, 108.5]  # North, West, South, East

VARIABLES = [
    "convective_available_potential_energy",
    "convective_inhibition",
    "total_column_water_vapour",
    "volumetric_soil_water_layer_1",
]

ALL_DAYS = [f"{d:02d}" for d in range(1, 32)]
ALL_HOURS = [f"{h:02d}:00" for h in range(24)]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ERA5_Downloader")


def check_cdsapi_config() -> bool:
    """Kiểm tra cấu hình CDS API."""
    home_rc = Path.home() / ".cdsapirc"
    if (home_rc.exists() and home_rc.stat().st_size > 10) or os.environ.get("CDSAPI_KEY"):
        logger.info("✓ Tìm thấy file cấu hình CDS API hợp lệ.")
        return True
    logger.error("Chưa tìm thấy file cấu hình CDS API!")
    return False


def get_quarters_plan(start_year: int = 2015, end_year: int = 2026) -> list[tuple[int, str, list[str]]]:
    """
    Tạo danh sách các quý từ mới nhất 2026 lùi dần về 2015.
    Mỗi phần tử: (năm, tên quý, danh sách các tháng)
    """
    quarters_def = [
        ("Q4", ["10", "11", "12"]),
        ("Q3", ["07", "08", "09"]),
        ("Q2", ["04", "05", "06"]),
        ("Q1", ["01", "02", "03"]),
    ]
    
    plan = []
    for year in range(end_year, start_year - 1, -1):
        for q_name, months in quarters_def:
            if year == 2026:
                if q_name == "Q4":
                    continue  # Q4/2026 chưa có
                if q_name == "Q3":
                    # Dữ liệu 2026 hiện có đến tháng 08
                    plan.append((year, q_name, ["07", "08"]))
                    continue
            plan.append((year, q_name, months))
            
    return plan


def download_quarter(client: cdsapi.Client, year: int, q_name: str, months: list[str]) -> Path | None:
    """Tải 1 quý dữ liệu NetCDF chứa cả 4 biến theo từng giờ."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    nc_path = OUTPUT_DIR / f"era5_thermo_soil_{year}_{q_name}.nc"

    # Kiểm tra nếu file đã tồn tại và hợp lệ (>100KB)
    if nc_path.exists() and nc_path.stat().st_size > 102400:
        logger.info("  [SKIP] %s đã tồn tại (%.2f MB)", nc_path.name, nc_path.stat().st_size / 1e6)
        return nc_path

    request = {
        "product_type": ["reanalysis"],
        "variable": VARIABLES,
        "year": [str(year)],
        "month": months,
        "day": ALL_DAYS,
        "time": ALL_HOURS,
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": BBOX_AREA,
    }

    logger.info("→ Gửi request %d-%s (Tháng: %s, 4 biến, BBox Đà Nẵng)...", year, q_name, ",".join(months))
    
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            temp_path = nc_path.with_suffix(".part")
            client.retrieve("reanalysis-era5-single-levels", request, str(temp_path))
            temp_path.replace(nc_path)
            logger.info("  ✓ Tải thành công %s (%.2f MB)", nc_path.name, nc_path.stat().st_size / 1e6)
            return nc_path
        except Exception as exc:
            err = str(exc)
            logger.warning("  [Lỗi lần %d/%d] %d-%s: %s", attempt, max_retries, year, q_name, err)
            if attempt < max_retries:
                sleep_s = attempt * 30
                logger.info("  Đợi %d giây trước khi thử lại...", sleep_s)
                time.sleep(sleep_s)
            else:
                logger.error("  ❌ Bỏ qua %d-%s sau %d lần thử thất bại.", year, q_name, max_retries)
                return None


def extract_point_from_nc(nc_path: Path) -> pd.DataFrame:
    """
    Trích xuất chuỗi thời gian 1D theo giờ tại ô đất liền Đà Nẵng (16.00, 108.25).
    """
    with xr.open_dataset(nc_path) as ds:
        time_dim = "valid_time" if "valid_time" in ds.coords else "time"
        point = ds.sel(latitude=TARGET_GRID_LAT, longitude=TARGET_GRID_LON, method="nearest")
        
        df = point.to_dataframe().reset_index()
        if time_dim in df.columns:
            df = df.rename(columns={time_dim: "time"})
            
        keep_cols = ["time"]
        rename_map = {
            "convective_available_potential_energy": "cape",
            "convective_inhibition": "cin",
            "total_column_water_vapour": "tcwv",
            "volumetric_soil_water_layer_1": "swvl1",
        }
        for orig, new_name in rename_map.items():
            if orig in df.columns:
                keep_cols.append(orig)
            elif new_name in df.columns:
                keep_cols.append(new_name)
                
        df = df[keep_cols].rename(columns=rename_map)
        df["time"] = pd.to_datetime(df["time"], utc=True)
        return df


def update_master_csv(new_df: pd.DataFrame):
    """Cập nhật lũy kế vào master CSV để có dữ liệu dùng ngay mà không cần đợi xong hết."""
    PROCESSED_CSV.parent.mkdir(parents=True, exist_ok=True)
    if PROCESSED_CSV.exists() and PROCESSED_CSV.stat().st_size > 0:
        try:
            existing_df = pd.read_csv(PROCESSED_CSV)
            existing_df["time"] = pd.to_datetime(existing_df["time"], utc=True)
            combined = pd.concat([existing_df, new_df], ignore_index=True)
        except Exception:
            combined = new_df
    else:
        combined = new_df
        
    combined = combined.drop_duplicates(subset=["time"]).sort_values("time").reset_index(drop=True)
    combined.to_csv(PROCESSED_CSV, index=False, encoding="utf-8-sig")
    logger.info("  ✓ Đã cập nhật lũy kế vào CSV: %s (Hiện có %d mốc giờ: %s -> %s)",
                PROCESSED_CSV.name, len(combined),
                combined['time'].min().strftime('%Y-%m-%d %H:%M'),
                combined['time'].max().strftime('%Y-%m-%d %H:%M'))


def main():
    parser = argparse.ArgumentParser(description="Tải ERA5 theo từng quý (2026 -> 2015)")
    parser.add_argument("--start-year", type=int, default=2015, help="Năm bắt đầu (mặc định 2015)")
    parser.add_argument("--end-year", type=int, default=2026, help="Năm kết thúc (mặc định 2026)")
    parser.add_argument("--extract", action="store_true", default=True, help="Tự động trích xuất lũy kế ra CSV sau mỗi quý")
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("ERA5 QUARTERLY COLLECTOR (CAPE, CIN, TCWV, Soil Moisture)")
    logger.info("Thứ tự ưu tiên: %d -> %d (Mới nhất quay về quá khứ)", args.end_year, args.start_year)
    logger.info("Tọa độ trích xuất ô lưới đất liền: (%.2f°N, %.2f°E)", TARGET_GRID_LAT, TARGET_GRID_LON)
    logger.info("=" * 70)

    if not check_cdsapi_config():
        sys.exit(1)

    try:
        client = cdsapi.Client()
        logger.info("✓ Kết nối CDS API client thành công.")
    except Exception as exc:
        logger.error("Không thể khởi tạo CDS API client: %s", exc)
        sys.exit(1)

    plan = get_quarters_plan(args.start_year, args.end_year)
    total_q = len(plan)
    logger.info("Tổng số quý cần thu thập: %d quý", total_q)

    for idx, (year, q_name, months) in enumerate(plan, 1):
        logger.info("\n[%d/%d] Đang xử lý: %d - %s (Tháng: %s) ...", idx, total_q, year, q_name, ",".join(months))
        nc_file = download_quarter(client, year, q_name, months)
        
        if nc_file and args.extract:
            try:
                df_q = extract_point_from_nc(nc_file)
                update_master_csv(df_q)
            except Exception as e:
                logger.error("  Lỗi trích xuất %s: %s", nc_file.name, e)

        # Nghỉ nhẹ giữa các request để máy chủ CDS giải phóng queue
        time.sleep(2)

    logger.info("\n" + "=" * 70)
    logger.info("🎉 HOÀN TẤT THU THẬP VÀ TRÍCH XUẤT TOÀN BỘ ERA5 2015-2026!")
    logger.info("File kết quả: %s", PROCESSED_CSV)
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
