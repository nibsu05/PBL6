# ==============================================================================
# download_era5_quarterly.py — Thu thập bổ sung ERA5 theo từng QUÝ (2026 -> 2015)
# Biến: CAPE, CIN, TCWV, Soil Moisture (volumetric_soil_water_layer_1)
# ==============================================================================
"""
Script tải dữ liệu ERA5 Reanalysis gộp theo từng QUÝ (Quarterly) từ CDS API:
  - 4 biến trong cùng 1 request:
      1. convective_available_potential_energy (CAPE) [J/kg]
      2. convective_inhibition                 (CIN)  [J/kg]
      3. total_column_water_vapour            (TCWV) [kg/m^2]
      4. volumetric_soil_water_layer_1        (swvl1) [m^3/m^3] (Độ ẩm đất tầng mặt 0-7cm)
  - Ưu tiên từ mới nhất (2026) lùi dần về quá khứ (2015).
  - Gộp theo quý để giảm số lần xếp hàng (queue time) trên máy chủ Copernicus.
  - Vẫn giữ nguyên độ phân giải theo TỪNG GIỜ (hourly) cho mọi ngày trong quý.
  - Tự động bỏ qua các quý đã tải xong (Resume mode).

Sử dụng:
  python data/download_era5_quarterly.py [--key YOUR_CDS_KEY] [--extract-point]
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
OUTPUT_DIR = ROOT_DIR / "data" / "raw_data" / "era5_quarterly"
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
logger = logging.getLogger("ERA5_Quarterly")


def check_or_setup_cdsapi(key_arg: str | None = None) -> bool:
    """Kiểm tra và thiết lập file ~/.cdsapirc nếu người dùng truyền key."""
    home_rc = Path.home() / ".cdsapirc"
    
    if key_arg:
        key = key_arg.strip()
        content = f"url: https://cds.climate.copernicus.eu/api\nkey: {key}\n"
        home_rc.write_text(content, encoding="utf-8")
        logger.info("✓ Đã lưu cấu hình CDS API tại: %s", home_rc)
        return True

    if home_rc.exists() and home_rc.stat().st_size > 10:
        logger.info("✓ Tìm thấy file cấu hình CDS API: %s", home_rc)
        return True
        
    env_key = os.environ.get("CDSAPI_KEY")
    if env_key:
        logger.info("✓ Tìm thấy CDSAPI_KEY trong biến môi trường.")
        return True

    logger.error("=" * 70)
    logger.error("CHƯA CÓ CẤU HÌNH CDS API!")
    logger.error("Để tải dữ liệu tự động từ Copernicus ECMWF, bạn cần có tài khoản:")
    logger.error("1. Đăng ký/Đăng nhập tại: https://cds.climate.copernicus.eu/")
    logger.error("2. Lấy Personal Access Token tại mục Profile.")
    logger.error("3. Chạy lệnh sau để tự động tạo cấu hình:")
    logger.error("   python data/download_era5_quarterly.py --key <TOKEN_CỦA_BẠN>")
    logger.error("   hoặc tạo file: %s với nội dung:", home_rc)
    logger.error("   url: https://cds.climate.copernicus.eu/api")
    logger.error("   key: <TOKEN_CỦA_BẠN>")
    logger.error("=" * 70)
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
    # Duyệt ngược từ end_year về start_year
    for year in range(end_year, start_year - 1, -1):
        for q_name, months in quarters_def:
            if year == 2026:
                # Năm 2026: Dữ liệu hiện tại đến tháng 08 hoặc 09
                if q_name == "Q4":
                    continue  # Q4/2026 chưa có
                if q_name == "Q3":
                    # Đến tháng 08/2026 (hoặc 09 nếu đã phát hành)
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
    Trích xuất chuỗi thời gian 1D theo giờ tại ô lưới đất liền gần Đà Nẵng (16.00, 108.25).
    """
    with xr.open_dataset(nc_path) as ds:
        time_dim = "valid_time" if "valid_time" in ds.coords else "time"
        point = ds.sel(latitude=TARGET_GRID_LAT, longitude=TARGET_GRID_LON, method="nearest")
        
        df = point.to_dataframe().reset_index()
        # Chuẩn hóa tên cột thời gian
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


def main():
    parser = argparse.ArgumentParser(description="Tải ERA5 theo từng quý (2026 -> 2015)")
    parser.add_argument("--key", type=str, default=None, help="Personal Access Token của CDS API")
    parser.add_argument("--start-year", type=int, default=2015, help="Năm bắt đầu (mặc định 2015)")
    parser.add_argument("--end-year", type=int, default=2026, help="Năm kết thúc (mặc định 2026)")
    parser.add_argument("--extract", action="store_true", help="Trích xuất luôn ra CSV sau khi tải")
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("ERA5 QUARTERLY COLLECTOR (CAPE, CIN, TCWV, Soil Moisture)")
    logger.info("Thứ tự ưu tiên: %d -> %d (Mới nhất quay về quá khứ)", args.end_year, args.start_year)
    logger.info("Vùng trích xuất: BBox Đà Nẵng %s", BBOX_AREA)
    logger.info("=" * 70)

    if not check_or_setup_cdsapi(args.key):
        sys.exit(1)

    try:
        client = cdsapi.Client()
        logger.info("✓ Kết nối CDS API thành công.")
    except Exception as exc:
        logger.error("Không thể khởi tạo CDS API client: %s", exc)
        sys.exit(1)

    plan = get_quarters_plan(args.start_year, args.end_year)
    total_q = len(plan)
    logger.info("Tổng số quý cần thu thập: %d quý", total_q)

    all_dfs = []
    for idx, (year, q_name, months) in enumerate(plan, 1):
        logger.info("\n[%d/%d] Xử lý %d - %s (Tháng: %s)", idx, total_q, year, q_name, ",".join(months))
        nc_file = download_quarter(client, year, q_name, months)
        
        if nc_file and args.extract:
            try:
                df_q = extract_point_from_nc(nc_file)
                all_dfs.append(df_q)
                logger.info("  ✓ Đã trích xuất %d mốc giờ từ %s", len(df_q), nc_file.name)
            except Exception as e:
                logger.error("  Lỗi trích xuất %s: %s", nc_file.name, e)

        # Nghỉ nhẹ giữa các request để máy chủ CDS giải phóng queue
        time.sleep(2)

    if args.extract and all_dfs:
        full_df = pd.concat(all_dfs, ignore_index=True)
        # Sắp xếp lại xuôi dòng thời gian trước khi lưu CSV
        full_df = full_df.drop_duplicates(subset=["time"]).sort_values("time").reset_index(drop=True)
        full_df.to_csv(PROCESSED_CSV, index=False, encoding="utf-8-sig")
        logger.info("\n" + "=" * 70)
        logger.info("✓ ĐÃ HOÀN TẤT VÀ XUẤT CSV: %s", PROCESSED_CSV)
        logger.info("Tổng số mốc giờ thu thập: %d mốc", len(full_df))
        logger.info("Khoảng thời gian: %s -> %s", full_df['time'].min(), full_df['time'].max())
        logger.info("=" * 70)


if __name__ == "__main__":
    main()
