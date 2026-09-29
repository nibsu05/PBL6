# ==============================================================================
# download_era5_background.py — Tải ERA5 2015-2024 chạy ngầm (year-by-year)
# ==============================================================================
"""
Script tự động tải dữ liệu ERA5 cho các năm 2015-2024 còn thiếu.
Chia request theo TỪNG NĂM (thay vì từng tháng) để giảm overhead queue CDS.

Chạy độc lập, song song với pipeline PoC:
  python download_era5_background.py

Output:
  ../data/raw_data/era5_netcdf/era5_sst_YYYY_MM.nc
  ../data/raw_data/era5_netcdf/era5_pl850_YYYY_MM.nc
"""

import sys
import os
import time
import logging
from pathlib import Path
from datetime import datetime

import cdsapi
import xarray as xr
import numpy as np
import pandas as pd

# Thêm data/ vào path để import config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))

from config import (
    BBOX,
    ERA5_SINGLE_LEVEL_VARS, ERA5_PRESSURE_LEVEL_VARS, ERA5_PRESSURE_LEVEL,
    ERA5_SINGLE_LEVELS_DATASET, ERA5_PRESSURE_LEVELS_DATASET,
    ERA5_NC_DIR,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

ALL_HOURS = [f"{h:02d}:00" for h in range(24)]
ALL_DAYS = [f"{d:02d}" for d in range(1, 32)]

BACKGROUND_START = 2015
BACKGROUND_END = 2024  # 2025-2026 đã tải bởi download_era5_quick.py


def download_year_sst(client: cdsapi.Client, year: int):
    """Tải SST cho toàn bộ 1 năm, chia theo tháng."""
    for month in range(1, 13):
        output_file = ERA5_NC_DIR / f"era5_sst_{year}_{month:02d}.nc"
        if output_file.exists() and output_file.stat().st_size > 0:
            logger.info("  [SKIP] %s", output_file.name)
            continue

        request = {
            "product_type": ["reanalysis"],
            "variable": ERA5_SINGLE_LEVEL_VARS,
            "year": [str(year)],
            "month": [f"{month:02d}"],
            "day": ALL_DAYS,
            "time": ALL_HOURS,
            "data_format": "netcdf",
            "area": [BBOX["north"], BBOX["west"], BBOX["south"], BBOX["east"]],
        }
        logger.info("  Tải SST %d-%02d ...", year, month)
        try:
            client.retrieve(ERA5_SINGLE_LEVELS_DATASET, request, str(output_file))
            logger.info("  → %s (%.2f MB)", output_file.name,
                        output_file.stat().st_size / 1e6)
        except Exception as e:
            logger.error("  LỖI SST %d-%02d: %s", year, month, e)
        time.sleep(3)


def download_year_pl850(client: cdsapi.Client, year: int):
    """Tải Pressure Levels 850hPa cho toàn bộ 1 năm, chia theo tháng."""
    for month in range(1, 13):
        output_file = ERA5_NC_DIR / f"era5_pl850_{year}_{month:02d}.nc"
        if output_file.exists() and output_file.stat().st_size > 0:
            logger.info("  [SKIP] %s", output_file.name)
            continue

        request = {
            "product_type": ["reanalysis"],
            "variable": ERA5_PRESSURE_LEVEL_VARS,
            "pressure_level": [ERA5_PRESSURE_LEVEL],
            "year": [str(year)],
            "month": [f"{month:02d}"],
            "day": ALL_DAYS,
            "time": ALL_HOURS,
            "data_format": "netcdf",
            "area": [BBOX["north"], BBOX["west"], BBOX["south"], BBOX["east"]],
        }
        logger.info("  Tải PL850 %d-%02d ...", year, month)
        try:
            client.retrieve(ERA5_PRESSURE_LEVELS_DATASET, request, str(output_file))
            logger.info("  → %s (%.2f MB)", output_file.name,
                        output_file.stat().st_size / 1e6)
        except Exception as e:
            logger.error("  LỖI PL850 %d-%02d: %s", year, month, e)
        time.sleep(3)


def main():
    logger.info("=" * 70)
    logger.info("TẢI NGẦM ERA5 REANALYSIS: %d – %d", BACKGROUND_START, BACKGROUND_END)
    logger.info("  Bounding Box: N=%.1f, W=%.1f, S=%.1f, E=%.1f",
                BBOX["north"], BBOX["west"], BBOX["south"], BBOX["east"])
    logger.info("=" * 70)

    # Kiểm tra .cdsapirc
    cdsapirc = Path.home() / ".cdsapirc"
    if not cdsapirc.exists():
        logger.error("Chưa cấu hình CDS API! Tạo file ~/.cdsapirc trước.")
        sys.exit(1)

    client = cdsapi.Client()
    logger.info("CDS API connected ✓")

    total_years = BACKGROUND_END - BACKGROUND_START + 1
    for i, year in enumerate(range(BACKGROUND_START, BACKGROUND_END + 1), 1):
        logger.info("")
        logger.info("═" * 50)
        logger.info("[%d/%d] NĂM %d — SST", i, total_years, year)
        logger.info("═" * 50)
        download_year_sst(client, year)

        logger.info("[%d/%d] NĂM %d — PL850", i, total_years, year)
        download_year_pl850(client, year)

    logger.info("")
    logger.info("=" * 70)
    logger.info("HOÀN TẤT TẢI NGẦM ERA5 2015-2024!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
