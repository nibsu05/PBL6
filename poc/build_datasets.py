# ==============================================================================
# build_datasets.py — Tạo 2 tập dữ liệu: Baseline + PoC
# ==============================================================================
"""
Module 2: Xây dựng 2 tập dữ liệu phục vụ huấn luyện mô hình.

1. Dataset Baseline (2015–2026): Chỉ biến bề mặt Open-Meteo
2. Dataset PoC (01/2025–09/2026): Merge đa nguồn (Open-Meteo + ERA5 + ENSO)

Sử dụng:
  python build_datasets.py

Output:
  datasets/dataset_baseline_2015_2026.parquet
  datasets/dataset_poc_2025_2026.parquet
"""

import sys
import logging
from pathlib import Path

import pandas as pd
import numpy as np
import xarray as xr

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"
RAW_DIR = DATA_DIR / "raw_data"
ERA5_NC_DIR = RAW_DIR / "era5_netcdf"
DATASETS_DIR = BASE_DIR / "datasets"
DATASETS_DIR.mkdir(parents=True, exist_ok=True)

# Thêm data/ vào path để import config
sys.path.insert(0, str(DATA_DIR))
from config import TIMEZONE, ERA5_PRESSURE_LEVEL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# File paths
OPENMETEO_CSV = RAW_DIR / "openmeteo_danang_2015_2026.csv"
ENSO_CSV = RAW_DIR / "enso_oni_2015_2026.csv"
ERA5_SST_CSV = RAW_DIR / "era5_sst_2015_2026.csv"
ERA5_PL_CSV = RAW_DIR / "era5_pressure_levels_2015_2026.csv"

# Output paths
BASELINE_OUTPUT = DATASETS_DIR / "dataset_baseline_2015_2026.parquet"
POC_OUTPUT = DATASETS_DIR / "dataset_poc_2025_2026.parquet"

# PoC date range
POC_START = "2025-01-01"
POC_END = "2026-08-31"


def load_openmeteo() -> pd.DataFrame:
    """Load dữ liệu Open-Meteo và chuyển timezone."""
    logger.info("Loading Open-Meteo data...")
    df = pd.read_csv(OPENMETEO_CSV, parse_dates=["datetime"])
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True).dt.tz_convert(TIMEZONE)
    df["datetime"] = df["datetime"].dt.floor("h")
    df = df.sort_values("datetime").drop_duplicates(subset="datetime").reset_index(drop=True)
    logger.info("  Open-Meteo: %d records, %s → %s",
                len(df), df["datetime"].iloc[0], df["datetime"].iloc[-1])
    return df


def load_enso() -> pd.DataFrame:
    """Load ENSO/ONI data."""
    if not ENSO_CSV.exists():
        logger.warning("  ENSO file not found: %s", ENSO_CSV)
        return pd.DataFrame()
    logger.info("Loading ENSO data...")
    df = pd.read_csv(ENSO_CSV, parse_dates=["datetime"])
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True).dt.tz_convert(TIMEZONE)
    df["datetime"] = df["datetime"].dt.floor("h")
    df = df.sort_values("datetime").drop_duplicates(subset="datetime").reset_index(drop=True)
    logger.info("  ENSO: %d records", len(df))
    return df


def extract_era5_from_netcdf(year_start: int, year_end: int) -> tuple:
    """
    Trích xuất SST và PL850 từ các file NetCDF đã tải.
    Tính spatial mean trên bounding box cho mỗi timestep.

    Returns:
        (df_sst, df_pl850): Tuple of DataFrames
    """
    logger.info("Extracting ERA5 from NetCDF files (%d-%d)...", year_start, year_end)

    sst_dfs = []
    pl_dfs = []

    for year in range(year_start, year_end + 1):
        for month in range(1, 13):
            # --- SST ---
            sst_file = ERA5_NC_DIR / f"era5_sst_{year}_{month:02d}.nc"
            if sst_file.exists() and sst_file.stat().st_size > 0:
                try:
                    ds = xr.open_dataset(sst_file)
                    # Tìm biến SST
                    sst_var = None
                    for v in ds.data_vars:
                        if "sst" in v.lower() or "sea" in v.lower():
                            sst_var = v
                            break
                    if sst_var is None:
                        sst_var = list(ds.data_vars)[0]

                    data = ds[sst_var]
                    lat_dim = "latitude" if "latitude" in data.dims else "lat"
                    lon_dim = "longitude" if "longitude" in data.dims else "lon"

                    # Weighted spatial mean
                    lat_coord = data[lat_dim]
                    weights = np.cos(np.deg2rad(lat_coord))
                    weights = weights / weights.mean()
                    spatial_mean = (data * weights).mean(dim=[lat_dim, lon_dim])

                    time_coord = ds["valid_time"] if "valid_time" in ds.coords else ds["time"]
                    times = pd.to_datetime(time_coord.values, utc=True)

                    df_tmp = pd.DataFrame({
                        "datetime": times,
                        "sea_surface_temperature": spatial_mean.values - 273.15,  # K → °C
                    })
                    sst_dfs.append(df_tmp)
                    ds.close()
                except Exception as e:
                    logger.warning("  Error reading %s: %s", sst_file.name, e)

            # --- PL850 ---
            pl_file = ERA5_NC_DIR / f"era5_pl850_{year}_{month:02d}.nc"
            if pl_file.exists() and pl_file.stat().st_size > 0:
                try:
                    ds = xr.open_dataset(pl_file)

                    # Tìm biến u, v, q
                    var_map = {}
                    for v in ds.data_vars:
                        vl = v.lower()
                        if vl == "u" or "u_component" in vl:
                            var_map["u_wind_850hpa"] = v
                        elif vl == "v" or "v_component" in vl:
                            var_map["v_wind_850hpa"] = v
                        elif vl == "q" or "specific" in vl:
                            var_map["specific_humidity_850hpa"] = v

                    lat_dim = "latitude" if "latitude" in ds.dims else "lat"
                    lon_dim = "longitude" if "longitude" in ds.dims else "lon"

                    result = {}
                    for out_name, nc_name in var_map.items():
                        data = ds[nc_name]
                        # Squeeze pressure level dimension
                        for dim_name in ["level", "pressure_level", "isobaricInhPa"]:
                            if dim_name in data.dims:
                                data = data.sel({dim_name: int(ERA5_PRESSURE_LEVEL)})
                                break

                        lat_coord = data[lat_dim] if lat_dim in data.coords else data.coords[list(data.coords)[0]]
                        weights = np.cos(np.deg2rad(lat_coord))
                        weights = weights / weights.mean()
                        spatial_mean = (data * weights).mean(dim=[lat_dim, lon_dim])
                        result[out_name] = spatial_mean.values

                    time_coord = ds["valid_time"] if "valid_time" in ds.coords else ds["time"]
                    times = pd.to_datetime(time_coord.values, utc=True)

                    df_tmp = pd.DataFrame(result)
                    df_tmp.insert(0, "datetime", times)
                    pl_dfs.append(df_tmp)
                    ds.close()
                except Exception as e:
                    logger.warning("  Error reading %s: %s", pl_file.name, e)

    # Concat
    df_sst = pd.DataFrame()
    if sst_dfs:
        df_sst = pd.concat(sst_dfs, ignore_index=True)
        df_sst["datetime"] = pd.to_datetime(df_sst["datetime"], utc=True).dt.tz_convert(TIMEZONE)
        df_sst["datetime"] = df_sst["datetime"].dt.floor("h")
        df_sst = df_sst.sort_values("datetime").drop_duplicates(subset="datetime").reset_index(drop=True)
        logger.info("  ERA5 SST: %d records", len(df_sst))

    df_pl = pd.DataFrame()
    if pl_dfs:
        df_pl = pd.concat(pl_dfs, ignore_index=True)
        df_pl["datetime"] = pd.to_datetime(df_pl["datetime"], utc=True).dt.tz_convert(TIMEZONE)
        df_pl["datetime"] = df_pl["datetime"].dt.floor("h")
        df_pl = df_pl.sort_values("datetime").drop_duplicates(subset="datetime").reset_index(drop=True)
        logger.info("  ERA5 PL850: %d records", len(df_pl))

    return df_sst, df_pl


def build_baseline_dataset() -> pd.DataFrame:
    """
    Tập Baseline (2015–2026): Chỉ biến bề mặt từ Open-Meteo.
    """
    logger.info("=" * 60)
    logger.info("BUILDING BASELINE DATASET (2015-2026)")
    logger.info("=" * 60)

    df = load_openmeteo()

    # Interpolate missing (limit 6 giờ)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    df[numeric_cols] = df[numeric_cols].interpolate(method="linear", limit=6, limit_direction="both")
    df[numeric_cols] = df[numeric_cols].ffill().bfill()

    # Verify
    missing = df.isnull().sum().sum()
    logger.info("  Missing after interpolation: %d", missing)
    if missing > 0:
        df = df.dropna().reset_index(drop=True)

    # Save
    df.to_parquet(BASELINE_OUTPUT, index=False, engine="pyarrow")
    logger.info("  → Saved: %s (%d records, %.2f MB)",
                BASELINE_OUTPUT.name, len(df),
                BASELINE_OUTPUT.stat().st_size / 1e6)

    return df


def build_poc_dataset() -> pd.DataFrame:
    """
    Tập PoC Đa nguồn (01/2025–08/2026):
    Merge Open-Meteo + ERA5 SST + ERA5 PL850 + ENSO/ONI
    """
    logger.info("=" * 60)
    logger.info("BUILDING PoC DATASET (2025-2026)")
    logger.info("=" * 60)

    # 1. Open-Meteo (nguồn chính)
    df = load_openmeteo()

    # 2. ERA5 từ NetCDF (trực tiếp, không cần CSV trung gian)
    df_sst, df_pl = extract_era5_from_netcdf(2025, 2026)

    # 3. ENSO
    df_enso = load_enso()

    # 4. Merge
    logger.info("Merging sources...")

    if not df_sst.empty:
        df = df.merge(df_sst, on="datetime", how="left")
        logger.info("  + SST merged")

    if not df_pl.empty:
        df = df.merge(df_pl, on="datetime", how="left")
        logger.info("  + PL850 merged")

    if not df_enso.empty:
        df = df.merge(df_enso, on="datetime", how="left")
        df["oni_anom"] = df["oni_anom"].ffill().bfill()
        logger.info("  + ENSO merged")

    # 5. Filter PoC time range
    poc_start = pd.Timestamp(POC_START, tz=TIMEZONE)
    poc_end = pd.Timestamp(f"{POC_END} 23:00:00", tz=TIMEZONE)
    df = df[(df["datetime"] >= poc_start) & (df["datetime"] <= poc_end)]
    df = df.sort_values("datetime").reset_index(drop=True)

    logger.info("  After filtering %s → %s: %d records",
                POC_START, POC_END, len(df))

    # 6. Interpolate missing
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    df[numeric_cols] = df[numeric_cols].interpolate(method="linear", limit=6, limit_direction="both")
    df[numeric_cols] = df[numeric_cols].ffill().bfill()

    # Report coverage
    logger.info("  Columns: %s", list(df.columns))
    for col in df.columns:
        if col != "datetime":
            non_null = df[col].notna().sum()
            pct = non_null / len(df) * 100
            logger.info("    %s: %d values (%.1f%%)", col, non_null, pct)

    # Save
    df.to_parquet(POC_OUTPUT, index=False, engine="pyarrow")
    logger.info("  → Saved: %s (%d records, %.2f MB)",
                POC_OUTPUT.name, len(df),
                POC_OUTPUT.stat().st_size / 1e6)

    return df


def main():
    logger.info("=" * 70)
    logger.info("BUILD DATASETS — PoC Pipeline Dự đoán Mưa Đà Nẵng")
    logger.info("=" * 70)

    # 1. Baseline
    df_baseline = build_baseline_dataset()

    # 2. PoC
    df_poc = build_poc_dataset()

    # Summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("TÓM TẮT")
    logger.info("  Baseline: %s — shape %s", BASELINE_OUTPUT.name, df_baseline.shape)
    logger.info("  PoC:      %s — shape %s", POC_OUTPUT.name, df_poc.shape)
    logger.info("=" * 70)

    return df_baseline, df_poc


if __name__ == "__main__":
    main()
