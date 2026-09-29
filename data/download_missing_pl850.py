# ==============================================================================
# download_missing_pl850.py — Tải bù 15 tháng thiếu của ERA5 PL850
# Các đoạn thiếu: 04/2024 - 12/2024 (9 tháng) & 03/2026 - 08/2026 (6 tháng)
# ==============================================================================

from __future__ import annotations
import os
import sys
import time
import logging
from pathlib import Path
import cdsapi
import pandas as pd
import xarray as xr

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw_data"
NC_DIR = RAW_DIR / "era5_nc_features"
PL_CSV = RAW_DIR / "era5_pressure_levels_2015_2026.csv"

NC_DIR.mkdir(parents=True, exist_ok=True)

TARGET_GRID_LAT = 16.00
TARGET_GRID_LON = 108.25
BBOX_AREA = [16.5, 107.75, 15.75, 108.5]

ALL_DAYS = [f"{d:02d}" for d in range(1, 32)]
ALL_HOURS = [f"{h:02d}:00" for h in range(24)]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("PL850_GapFiller")

# 5 chunks để lấp trọn vẹn 15 tháng thiếu:
GAP_CHUNKS = [
    ("2026_03_to_05", "2026", ["03", "04", "05"]),
    ("2026_06_to_08", "2026", ["06", "07", "08"]),
    ("2024_04_to_06", "2024", ["04", "05", "06"]),
    ("2024_07_to_09", "2024", ["07", "08", "09"]),
    ("2024_10_to_12", "2024", ["10", "11", "12"]),
]


def download_pl850_chunk(client: cdsapi.Client, tag: str, year: str, months: list[str]) -> Path | None:
    nc_path = NC_DIR / f"era5_pl850_gap_{tag}.nc"
    if nc_path.exists() and nc_path.stat().st_size > 50000:
        logger.info("  [SKIP] %s đã tồn tại (%.2f KB)", nc_path.name, nc_path.stat().st_size / 1024)
        return nc_path

    request = {
        "product_type": ["reanalysis"],
        "variable": ["u_component_of_wind", "v_component_of_wind", "specific_humidity"],
        "pressure_level": ["850"],
        "year": [year],
        "month": months,
        "day": ALL_DAYS,
        "time": ALL_HOURS,
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": BBOX_AREA,
    }

    logger.info("→ Gửi request PL850 %s (Năm %s, Tháng: %s)...", tag, year, ",".join(months))
    for attempt in range(1, 4):
        try:
            part = nc_path.with_suffix(".part")
            client.retrieve("reanalysis-era5-pressure-levels", request, str(part))
            part.replace(nc_path)
            logger.info("  ✓ Tải thành công %s (%.2f KB)", nc_path.name, nc_path.stat().st_size / 1024)
            return nc_path
        except Exception as e:
            logger.warning("  [Lỗi lần %d/3] %s: %s", attempt, tag, e)
            if attempt < 3:
                time.sleep(30)
            else:
                logger.error("  ❌ Bỏ qua %s sau 3 lần thử", tag)
                return None


def extract_pl850_point(nc_path: Path) -> pd.DataFrame:
    with xr.open_dataset(nc_path) as ds:
        time_dim = "valid_time" if "valid_time" in ds.coords else "time"
        pt = ds.sel(latitude=TARGET_GRID_LAT, longitude=TARGET_GRID_LON, method="nearest")
        df = pt.to_dataframe().reset_index()
        if time_dim in df.columns:
            df = df.rename(columns={time_dim: "datetime"})
        
        rename_map = {
            "u": "u_wind_850hpa",
            "u_component_of_wind": "u_wind_850hpa",
            "v": "v_wind_850hpa",
            "v_component_of_wind": "v_wind_850hpa",
            "q": "specific_humidity_850hpa",
            "specific_humidity": "specific_humidity_850hpa",
        }
        cols = ["datetime"]
        for orig, new_col in rename_map.items():
            if orig in df.columns:
                cols.append(orig)
            elif new_col in df.columns:
                cols.append(new_col)
                
        df = df[cols].rename(columns=rename_map)
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
        return df


def update_master_pl_csv(new_rows: list[pd.DataFrame]):
    if not new_rows:
        return
    logger.info("Đang cập nhật vào %s ...", PL_CSV.name)
    existing = pd.read_csv(PL_CSV)
    existing["datetime"] = pd.to_datetime(existing["datetime"], utc=True)
    
    combined = pd.concat([existing] + new_rows, ignore_index=True)
    combined = combined.drop_duplicates(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)
    combined.to_csv(PL_CSV, index=False, encoding="utf-8-sig")
    logger.info("✓ ĐÃ CẬP NHẬT HOÀN TẤT %s:", PL_CSV.name)
    logger.info("  Tổng số dòng: %d mốc giờ", len(combined))
    logger.info("  Khoảng thời gian: %s -> %s", combined['datetime'].min(), combined['datetime'].max())


def main():
    logger.info("=" * 65)
    logger.info("TIẾN TRÌNH LẤP GAP ERA5 PL850 (15 THÁNG THIẾU)")
    logger.info("=" * 65)
    
    client = cdsapi.Client()
    extracted_dfs = []
    
    for idx, (tag, year, months) in enumerate(GAP_CHUNKS, 1):
        logger.info("\n[%d/%d] Tải bù PL850: %s ...", idx, len(GAP_CHUNKS), tag)
        nc_file = download_pl850_chunk(client, tag, year, months)
        if nc_file:
            try:
                df = extract_pl850_point(nc_file)
                extracted_dfs.append(df)
                logger.info("  ✓ Đã trích xuất %d mốc giờ từ %s", len(df), nc_file.name)
            except Exception as e:
                logger.error("  Lỗi trích xuất %s: %s", nc_file.name, e)
        time.sleep(2)
        
    update_master_pl_csv(extracted_dfs)
    logger.info("\n🎉 ĐÃ LẤP KÍN HOÀN TOÀN CÁC GAP CỦA TẦNG 850 hPa!")


if __name__ == "__main__":
    main()
