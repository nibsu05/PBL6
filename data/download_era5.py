# ==============================================================================
# download_era5.py — Thu thập dữ liệu ERA5 Reanalysis qua CDS API
# ==============================================================================
"""
Module tải dữ liệu ERA5 Reanalysis từ Copernicus Climate Data Store (CDS)
cho khu vực Biển Đông kề bên Đà Nẵng.

Datasets & biến thu thập:
  1. ERA5 Single Levels:
     - sea_surface_temperature (SST, K → °C)
     
  2. ERA5 Pressure Levels (850 hPa):
     - u_component_of_wind     (m/s)
     - v_component_of_wind     (m/s)  
     - specific_humidity        (kg/kg)

Bounding Box: [14°N–18°N, 107°E–111°E]

Pipeline:
  1. Gửi request tải NetCDF qua CDS API (chia theo năm × tháng)
  2. Đọc NetCDF bằng xarray
  3. Tính spatial mean trên bounding box → chuỗi thời gian 1D
  4. Ghép thành DataFrame, lưu CSV

QUAN TRỌNG — Cấu hình CDS API trước khi chạy:
  1. Đăng ký tài khoản: https://cds.climate.copernicus.eu/
  2. Lấy Personal Access Token từ trang profile
  3. Tạo file ~/.cdsapirc (Linux/Mac) hoặc %USERPROFILE%\\.cdsapirc (Windows):
  
     url: https://cds.climate.copernicus.eu/api
     key: <YOUR_PERSONAL_ACCESS_TOKEN>
     
  4. Chấp nhận Terms of Use cho cả 2 dataset trên CDS web:
     - reanalysis-era5-single-levels
     - reanalysis-era5-pressure-levels

Sử dụng:
  python download_era5.py

Output:
  raw_data/era5_sst_2015_2023.csv
  raw_data/era5_pressure_levels_2015_2023.csv
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime

import cdsapi
import xarray as xr
import numpy as np
import pandas as pd

from config import (
    DANANG_LAT, DANANG_LON,
    BBOX,
    START_DATE, START_YEAR, END_YEAR, END_DATE,
    ERA5_SINGLE_LEVEL_VARS, ERA5_PRESSURE_LEVEL_VARS, ERA5_PRESSURE_LEVEL,
    ERA5_SINGLE_LEVELS_DATASET, ERA5_PRESSURE_LEVELS_DATASET,
    ERA5_NC_DIR,
    ERA5_SST_OUTPUT, ERA5_PRESSURE_OUTPUT,
)

# Đảm bảo UTF-8 cho console Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ==============================================================================
# CẤU HÌNH LOGGING
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Danh sách tất cả các giờ trong ngày (00:00 → 23:00)
ALL_HOURS = [f"{h:02d}:00" for h in range(24)]

# Danh sách tất cả các ngày trong tháng (01 → 31, CDS sẽ bỏ qua ngày không tồn tại)
ALL_DAYS = [f"{d:02d}" for d in range(1, 32)]


def check_cdsapi_config():
    """
    Kiểm tra xem file .cdsapirc đã được cấu hình chưa.
    Hiển thị hướng dẫn nếu chưa cấu hình.
    """
    # Kiểm tra cả 2 vị trí phổ biến
    home = Path.home()
    cdsapirc_path = home / ".cdsapirc"
    
    if not cdsapirc_path.exists():
        logger.error("=" * 70)
        logger.error("CHƯA CẤU HÌNH CDS API!")
        logger.error("=" * 70)
        logger.error("")
        logger.error("Hãy thực hiện các bước sau:")
        logger.error("")
        logger.error("1. Đăng ký tài khoản CDS:")
        logger.error("   https://cds.climate.copernicus.eu/")
        logger.error("")
        logger.error("2. Lấy Personal Access Token từ trang profile")
        logger.error("")
        logger.error("3. Tạo file: %s", cdsapirc_path)
        logger.error("   Với nội dung:")
        logger.error("   url: https://cds.climate.copernicus.eu/api")
        logger.error("   key: <YOUR_PERSONAL_ACCESS_TOKEN>")
        logger.error("")
        logger.error("4. Chấp nhận Terms of Use cho các dataset trên CDS web:")
        logger.error("   - reanalysis-era5-single-levels")
        logger.error("   - reanalysis-era5-pressure-levels")
        logger.error("=" * 70)
        sys.exit(1)
    else:
        logger.info("Tìm thấy file cấu hình CDS API: %s ✓", cdsapirc_path)


def download_era5_single_levels(client: cdsapi.Client, year: int, month: int) -> Path:
    """
    Tải dữ liệu ERA5 Single Levels (SST) cho 1 tháng cụ thể.
    
    Args:
        client: CDS API client
        year: Năm (VD: 2015)
        month: Tháng (VD: 1)
        
    Returns:
        Path đến file NetCDF đã tải
    """
    output_file = ERA5_NC_DIR / f"era5_sst_{year}_{month:02d}.nc"
    
    # Bỏ qua nếu file đã tồn tại (resume sau khi bị gián đoạn)
    if output_file.exists() and output_file.stat().st_size > 0:
        logger.info("  [SKIP] File đã tồn tại: %s", output_file.name)
        return output_file
    
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
    
    logger.info("  Đang tải SST %d-%02d ...", year, month)
    
    for attempt in range(1, 4):
        try:
            client.retrieve(
                ERA5_SINGLE_LEVELS_DATASET,
                request,
                str(output_file),
            )
            break
        except Exception as e:
            if output_file.exists() and output_file.stat().st_size == 0:
                try:
                    output_file.unlink()
                except Exception:
                    pass
            if attempt < 3:
                wait_s = attempt * 10
                logger.warning("  [RETRY %d/3] Lỗi tải SST %d-%02d: %s. Thử lại sau %ds...", attempt, year, month, e, wait_s)
                time.sleep(wait_s)
            else:
                logger.error("  [FAILED] Thất bại tải SST %d-%02d sau 3 lần thử: %s", year, month, e)
                raise
    
    logger.info("  → Đã lưu: %s (%.2f MB)",
                output_file.name, output_file.stat().st_size / 1e6)
    
    return output_file


def download_era5_pressure_levels(client: cdsapi.Client, year: int, month: int) -> Path:
    """
    Tải dữ liệu ERA5 Pressure Levels (wind U/V, specific humidity) ở 850 hPa
    cho 1 tháng cụ thể.
    
    Args:
        client: CDS API client
        year: Năm (VD: 2015)
        month: Tháng (VD: 1)
        
    Returns:
        Path đến file NetCDF đã tải
    """
    output_file = ERA5_NC_DIR / f"era5_pl850_{year}_{month:02d}.nc"
    
    # Bỏ qua nếu file đã tồn tại
    if output_file.exists() and output_file.stat().st_size > 0:
        logger.info("  [SKIP] File đã tồn tại: %s", output_file.name)
        return output_file
    
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
    
    logger.info("  Đang tải Pressure Levels 850hPa %d-%02d ...", year, month)
    
    for attempt in range(1, 4):
        try:
            client.retrieve(
                ERA5_PRESSURE_LEVELS_DATASET,
                request,
                str(output_file),
            )
            break
        except Exception as e:
            if output_file.exists() and output_file.stat().st_size == 0:
                try:
                    output_file.unlink()
                except Exception:
                    pass
            if attempt < 3:
                wait_s = attempt * 10
                logger.warning("  [RETRY %d/3] Lỗi tải PL850 %d-%02d: %s. Thử lại sau %ds...", attempt, year, month, e, wait_s)
                time.sleep(wait_s)
            else:
                logger.error("  [FAILED] Thất bại tải PL850 %d-%02d sau 3 lần thử: %s", year, month, e)
                raise
    
    logger.info("  → Đã lưu: %s (%.2f MB)",
                output_file.name, output_file.stat().st_size / 1e6)
    
    return output_file


def download_era5_pressure_levels_batch(client: cdsapi.Client, year: int, months: list, max_chunk_size: int = 3) -> list:
    """
    Tải gộp dữ liệu ERA5 Pressure Levels 850 hPa cho nhiều tháng trong cùng năm
    qua CDS API request theo từng cụm (tối đa max_chunk_size tháng mỗi request)
    để không vượt quá giới hạn cost limit của CDS, sau đó tách thành từng file NetCDF theo tháng.
    
    Args:
        client: CDS API client
        year: Năm cần tải
        months: Danh sách các tháng còn thiếu (VD: [11, 12] hoặc [1, 2, ..., 12])
        max_chunk_size: Số tháng tối đa cho mỗi request (mặc định 3 tháng)
        
    Returns:
        List các Path đến file NetCDF đã lưu
    """
    # Lọc chỉ những tháng thực sự còn thiếu
    missing_months = []
    saved_files = []
    for m in sorted(months):
        target_file = ERA5_NC_DIR / f"era5_pl850_{year}_{m:02d}.nc"
        if target_file.exists() and target_file.stat().st_size > 0:
            logger.info("  [SKIP] File đã tồn tại: %s", target_file.name)
            saved_files.append(target_file)
        else:
            missing_months.append(m)
            
    if not missing_months:
        logger.info("  Tất cả các tháng năm %d đã có sẵn ✓", year)
        return saved_files

    # Chia danh sách tháng còn thiếu thành các cụm nhỏ (<= max_chunk_size tháng)
    chunks = [missing_months[i:i + max_chunk_size] for i in range(0, len(missing_months), max_chunk_size)]

    for chunk_idx, chunk in enumerate(chunks, 1):
        if len(chunk) == 1:
            f = download_era5_pressure_levels(client, year, chunk[0])
            saved_files.append(f)
            continue

        month_strs = [f"{m:02d}" for m in chunk]
        temp_file = ERA5_NC_DIR / f"temp_batch_pl_{year}_{chunk[0]:02d}_{chunk[-1]:02d}.nc"
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass

        request = {
            "product_type": ["reanalysis"],
            "variable": ERA5_PRESSURE_LEVEL_VARS,
            "pressure_level": [ERA5_PRESSURE_LEVEL],
            "year": [str(year)],
            "month": month_strs,
            "day": ALL_DAYS,
            "time": ALL_HOURS,
            "data_format": "netcdf",
            "area": [BBOX["north"], BBOX["west"], BBOX["south"], BBOX["east"]],
        }

        logger.info("  [BATCH %d/%d] Gửi request CDS năm %d (%d tháng: %s) ...",
                    chunk_idx, len(chunks), year, len(chunk), ", ".join(month_strs))

        batch_success = False
        for attempt in range(1, 4):
            try:
                client.retrieve(
                    ERA5_PRESSURE_LEVELS_DATASET,
                    request,
                    str(temp_file),
                )
                batch_success = True
                break
            except Exception as e:
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except Exception:
                        pass
                err_msg = str(e).lower()
                if "cost limits exceeded" in err_msg or "too large" in err_msg:
                    logger.warning("  [COST LIMIT] Batch vượt giới hạn CDS. Tự động chuyển sang tải từng tháng lẻ...")
                    for m in chunk:
                        f = download_era5_pressure_levels(client, year, m)
                        saved_files.append(f)
                        time.sleep(2)
                    batch_success = False
                    break

                if attempt < 3:
                    wait_s = attempt * 15
                    logger.warning("  [RETRY %d/3] Lỗi tải batch PL850 năm %d (%s): %s. Thử lại sau %ds...",
                                   attempt, year, ", ".join(month_strs), e, wait_s)
                    time.sleep(wait_s)
                else:
                    logger.error("  [FAILED] Thất bại tải batch PL850 năm %d (%s) sau 3 lần: %s",
                                 year, ", ".join(month_strs), e)
                    raise

        if not batch_success:
            if chunk_idx < len(chunks):
                time.sleep(3)
            continue

        logger.info("  [BATCH %d/%d] Đã nhận dữ liệu năm %d (%s) (%.2f MB). Đang tách thành từng tháng...",
                    chunk_idx, len(chunks), year, ", ".join(month_strs), temp_file.stat().st_size / 1e6)

        # Đọc batch NetCDF và tách theo từng tháng
        try:
            with xr.open_dataset(temp_file) as ds:
                time_dim = "valid_time" if "valid_time" in ds.dims else "time"
                time_vals = pd.to_datetime(ds[time_dim].values)

                for m in chunk:
                    m_file = ERA5_NC_DIR / f"era5_pl850_{year}_{m:02d}.nc"
                    mask = (time_vals.year == year) & (time_vals.month == m)
                    if not mask.any():
                        logger.warning("  Không tìm thấy dữ liệu cho tháng %d-%02d trong file batch!", year, m)
                        continue
                    ds_m = ds.isel({time_dim: mask})
                    ds_m.to_netcdf(m_file)
                    ds_m.close()
                    logger.info("  → Đã tách và lưu: %s (%.2f MB)", m_file.name, m_file.stat().st_size / 1e6)
                    saved_files.append(m_file)
        finally:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass

        if chunk_idx < len(chunks):
            time.sleep(3)

    return saved_files


def extract_spatial_mean(nc_file: Path, variables: list, convert_kelvin: bool = False) -> pd.DataFrame:
    """
    Đọc file NetCDF và tính spatial mean trên toàn bounding box cho mỗi timestep.
    
    Spatial mean (trung bình không gian) phù hợp vì:
    - Đại diện cho điều kiện khí tượng khu vực xung quanh Đà Nẵng
    - Giảm nhiễu từ grid cells riêng lẻ
    - Đưa dữ liệu gridded về dạng chuỗi thời gian 1D cho deep learning
    
    Args:
        nc_file: Đường dẫn file NetCDF
        variables: Danh sách tên biến cần trích xuất
        convert_kelvin: Nếu True, chuyển từ Kelvin → Celsius
        
    Returns:
        pd.DataFrame với cột datetime + các biến (spatial mean)
    """
    try:
        ds = xr.open_dataset(nc_file)
    except Exception as e:
        logger.error("  LỖI file NetCDF bị hỏng: %s (%s). Xóa file để tải lại lần sau...", nc_file.name, e)
        if nc_file.exists():
            try:
                nc_file.unlink()
            except Exception:
                pass
        raise e
    
    results = {}
    
    for var in variables:
        # Bản đồ ánh xạ tên chuẩn ERA5 request -> tên biến viết tắt trong NetCDF
        short_name_map = {
            "sea_surface_temperature": "sst",
            "u_component_of_wind": "u",
            "v_component_of_wind": "v",
            "specific_humidity": "q",
        }
        
        actual_var = None
        short = short_name_map.get(var, var)
        
        # 1. Tìm trực tiếp theo tên biến gốc hoặc tên viết tắt (sst, u, v, q)
        if var in ds.data_vars:
            actual_var = var
        elif short in ds.data_vars:
            actual_var = short
        else:
            # 2. Tìm theo thuộc tính long_name hoặc standard_name
            for dv in ds.data_vars:
                attrs_text = " ".join([
                    str(ds[dv].attrs.get("long_name", "")),
                    str(ds[dv].attrs.get("standard_name", "")),
                ]).lower()
                if var.lower() in attrs_text:
                    actual_var = dv
                    break
        
        if actual_var is None:
            logger.warning("  Không tìm thấy biến '%s' trong %s. Data vars: %s",
                           var, nc_file.name, list(ds.data_vars))
            continue
        
        data = ds[actual_var]
        
        # Loại bỏ chiều pressure_level nếu có (squeeze)
        if "level" in data.dims:
            data = data.sel(level=int(ERA5_PRESSURE_LEVEL))
        elif "pressure_level" in data.dims:
            data = data.sel(pressure_level=int(ERA5_PRESSURE_LEVEL))
        
        # Tính trung bình không gian (mean trên latitude & longitude)
        # Weighted mean theo cosine latitude cho chính xác hơn
        weights = np.cos(np.deg2rad(data.latitude if "latitude" in data.coords else data.lat))
        weights = weights / weights.mean()
        
        lat_dim = "latitude" if "latitude" in data.dims else "lat"
        lon_dim = "longitude" if "longitude" in data.dims else "lon"
        
        # Weighted spatial mean
        spatial_mean = (data * weights).mean(dim=[lat_dim, lon_dim])
        
        results[var] = spatial_mean.values
    
    # Lấy time coordinate
    time_coord = ds["valid_time"] if "valid_time" in ds.coords else ds["time"]
    times = pd.to_datetime(time_coord.values, utc=True)
    
    ds.close()
    
    # Tạo DataFrame
    df = pd.DataFrame(results)
    df.insert(0, "datetime", times)
    
    # Chuyển Kelvin → Celsius nếu cần
    if convert_kelvin and "sea_surface_temperature" in df.columns:
        df["sea_surface_temperature"] = df["sea_surface_temperature"] - 273.15
        logger.info("  → Đã chuyển SST từ Kelvin sang Celsius")
    
    return df


def check_status():
    """
    Kiểm tra và báo cáo chi tiết hiện trạng các file NetCDF và CSV trong hệ thống.
    """
    logger.info("=" * 70)
    logger.info("BÁO CÁO HIỆN TRẠNG DỮ LIỆU ERA5")
    logger.info("=" * 70)
    
    end_month_last_year = datetime.strptime(END_DATE, "%Y-%m-%d").month
    expected_months = []
    for y in range(START_YEAR, END_YEAR + 1):
        last_m = end_month_last_year if y == END_YEAR else 12
        for m in range(1, last_m + 1):
            expected_months.append((y, m))
            
    total_expected = len(expected_months)
    logger.info("Khung thời gian mục tiêu: %s -> %s (Tổng: %d tháng)", START_DATE, END_DATE, total_expected)
    logger.info("Thư mục lưu NetCDF: %s", ERA5_NC_DIR)
    
    # 1. SST
    sst_files = sorted(ERA5_NC_DIR.glob("era5_sst_*.nc"))
    sst_available = set()
    for f in sst_files:
        if f.stat().st_size > 0:
            parts = f.stem.replace("era5_sst_", "").split("_")
            if len(parts) == 2:
                try:
                    sst_available.add((int(parts[0]), int(parts[1])))
                except ValueError:
                    pass
    sst_missing = [ym for ym in expected_months if ym not in sst_available]
    logger.info("")
    logger.info("1. ERA5 Single Levels - SST (sea_surface_temperature):")
    logger.info("   - Số file NetCDF hiện có: %d / %d", len(sst_available), total_expected)
    if sst_missing:
        logger.warning("   - Còn thiếu %d tháng: %s", len(sst_missing), sst_missing)
    else:
        logger.info("   - Tình trạng: Đầy đủ 100%% (140/140 file) ✓")
    if ERA5_SST_OUTPUT.exists():
        logger.info("   - File CSV: %s (%.2f MB)", ERA5_SST_OUTPUT.name, ERA5_SST_OUTPUT.stat().st_size / 1e6)
    else:
        logger.info("   - File CSV: Chưa tạo")

    # 2. PL850
    pl_files = sorted(ERA5_NC_DIR.glob("era5_pl850_*.nc"))
    pl_available = set()
    for f in pl_files:
        if f.stat().st_size > 0:
            parts = f.stem.replace("era5_pl850_", "").split("_")
            if len(parts) == 2:
                try:
                    pl_available.add((int(parts[0]), int(parts[1])))
                except ValueError:
                    pass
    pl_missing = [ym for ym in expected_months if ym not in pl_available]
    logger.info("")
    logger.info("2. ERA5 Pressure Levels 850 hPa (u_wind, v_wind, specific_humidity):")
    logger.info("   - Số file NetCDF hiện có: %d / %d", len(pl_available), total_expected)
    if pl_missing:
        logger.warning("   - Còn thiếu %d tháng NetCDF:", len(pl_missing))
        from collections import defaultdict
        miss_by_year = defaultdict(list)
        for y, m in pl_missing:
            miss_by_year[y].append(m)
        for y, ms in sorted(miss_by_year.items()):
            logger.warning("       * Năm %d: thiếu %d tháng (tháng %s)", y, len(ms), ", ".join(map(str, ms)))
    else:
        logger.info("   - Tình trạng: Đầy đủ 100%% (140/140 file) ✓")
    if ERA5_PRESSURE_OUTPUT.exists():
        logger.info("   - File CSV: %s (%.2f MB)", ERA5_PRESSURE_OUTPUT.name, ERA5_PRESSURE_OUTPUT.stat().st_size / 1e6)
    else:
        logger.info("   - File CSV: Chưa tạo")
    logger.info("=" * 70)


def download_and_extract_sst(
    client: cdsapi.Client = None,
    extract_only: bool = False,
    target_year: int = None,
) -> pd.DataFrame:
    """
    Tải và trích xuất toàn bộ dữ liệu SST (2015–2026).
    Tái sử dụng file CSV đã có nếu đầy đủ để tiết kiệm thời gian.
    
    Args:
        client: CDS API client
        extract_only: Nếu True, chỉ trích xuất từ NetCDF có sẵn
        target_year: Chỉ xử lý 1 năm cụ thể nếu được chỉ định
        
    Returns:
        pd.DataFrame hourly SST (spatial mean, °C)
    """
    logger.info("=" * 50)
    logger.info("THU THẬP SEA SURFACE TEMPERATURE (SST)")
    logger.info("=" * 50)
    
    # Kiểm tra nếu file CSV đã tồn tại và đầy đủ (102264 records)
    if not target_year and ERA5_SST_OUTPUT.exists() and ERA5_SST_OUTPUT.stat().st_size > 0:
        try:
            df_existing = pd.read_csv(ERA5_SST_OUTPUT)
            if len(df_existing) >= 102264:
                logger.info("✓ File SST CSV đã đầy đủ (%d bản ghi): %s",
                            len(df_existing), ERA5_SST_OUTPUT)
                return df_existing
        except Exception as e:
            logger.warning("Không thể đọc file SST CSV cũ (%s), tiến hành xử lý lại...", e)

    all_dfs = []
    end_month_last_year = datetime.strptime(END_DATE, "%Y-%m-%d").month
    year_range = [target_year] if target_year else range(START_YEAR, END_YEAR + 1)
    
    for year in year_range:
        last_month = end_month_last_year if year == END_YEAR else 12
        for month in range(1, last_month + 1):
            nc_file = ERA5_NC_DIR / f"era5_sst_{year}_{month:02d}.nc"
            was_downloaded = False
            
            if not nc_file.exists() or nc_file.stat().st_size == 0:
                if extract_only:
                    logger.warning("  [BỎ QUA] Không tìm thấy file NetCDF SST %d-%02d (chế độ --extract-only)", year, month)
                    continue
                if client is None:
                    client = cdsapi.Client()
                logger.info("  Đang tải SST %d-%02d...", year, month)
                nc_file = download_era5_single_levels(client, year, month)
                was_downloaded = True
            else:
                logger.info("  [CÓ SẴN] SST %d-%02d", year, month)
            
            try:
                # Trích xuất spatial mean
                df = extract_spatial_mean(
                    nc_file,
                    variables=ERA5_SINGLE_LEVEL_VARS,
                    convert_kelvin=True,
                )
                all_dfs.append(df)
            except Exception as e:
                logger.error("  LỖI khi xử lý SST %d-%02d: %s", year, month, e)
                continue
            
            if was_downloaded:
                time.sleep(3)
    
    if not all_dfs:
        logger.error("Không trích xuất được dữ liệu SST nào!")
        return pd.DataFrame()
    
    df_all = pd.concat(all_dfs, ignore_index=True)
    df_all = df_all.sort_values("datetime").drop_duplicates(subset="datetime").reset_index(drop=True)
    
    return df_all


def download_and_extract_pressure_levels(
    client: cdsapi.Client = None,
    extract_only: bool = False,
    target_year: int = None,
    max_chunk_size: int = 3,
) -> pd.DataFrame:
    """
    Tải và trích xuất dữ liệu Pressure Levels 850hPa (2015–2026).
    Sử dụng batch download theo năm để tối ưu tốc độ.
    
    Args:
        client: CDS API client
        extract_only: Nếu True, chỉ trích xuất từ các file NetCDF có sẵn
        target_year: Chỉ xử lý 1 năm cụ thể nếu được chỉ định
        max_chunk_size: Số tháng tối đa cho mỗi request CDS API
        
    Returns:
        pd.DataFrame hourly U-wind, V-wind, Specific Humidity (spatial mean)
    """
    logger.info("=" * 50)
    logger.info("THU THẬP & TRÍCH XUẤT PRESSURE LEVELS 850 hPa (U, V, Q)")
    logger.info("=" * 50)
    
    end_month_last_year = datetime.strptime(END_DATE, "%Y-%m-%d").month
    total_expected_records = 102264
    
    # Kiểm tra nếu file CSV đã tồn tại và đầy đủ
    if not target_year and ERA5_PRESSURE_OUTPUT.exists() and ERA5_PRESSURE_OUTPUT.stat().st_size > 0:
        try:
            df_existing = pd.read_csv(ERA5_PRESSURE_OUTPUT)
            if len(df_existing) >= total_expected_records:
                logger.info("✓ File Pressure Levels CSV đã đầy đủ (%d bản ghi): %s",
                            len(df_existing), ERA5_PRESSURE_OUTPUT)
                return df_existing
        except Exception as e:
            logger.warning("Không thể đọc file PL CSV cũ (%s), tiến hành xử lý lại...", e)

    year_range = [target_year] if target_year else range(START_YEAR, END_YEAR + 1)

    # -------------------------------------------------------------
    # BƯỚC 1: Quét và tải các tháng còn thiếu theo từng năm (Batch)
    # -------------------------------------------------------------
    if not extract_only:
        if client is None:
            client = cdsapi.Client()
        logger.info("BƯỚC 1: Kiểm tra và tải các file NetCDF còn thiếu...")
        for year in year_range:
            last_month = end_month_last_year if year == END_YEAR else 12
            missing_months = []
            for month in range(1, last_month + 1):
                nc_file = ERA5_NC_DIR / f"era5_pl850_{year}_{month:02d}.nc"
                if not nc_file.exists() or nc_file.stat().st_size == 0:
                    missing_months.append(month)
                    
            if missing_months:
                logger.info("Năm %d: Thiếu %d tháng (%s). Đang tải batch qua CDS API...",
                            year, len(missing_months),
                            ", ".join(f"{m:02d}" for m in missing_months))
                download_era5_pressure_levels_batch(client, year, missing_months, max_chunk_size=max_chunk_size)
                time.sleep(3)
            else:
                logger.info("Năm %d: Đã đầy đủ tất cả các tháng ✓", year)
    else:
        logger.info("BƯỚC 1: Bỏ qua tải về (chế độ --extract-only) ✓")

    # -------------------------------------------------------------
    # BƯỚC 2: Trích xuất spatial mean từ toàn bộ file NetCDF hiện có
    # -------------------------------------------------------------
    logger.info("")
    logger.info("BƯỚC 2: Trích xuất spatial mean từ các file NetCDF...")
    all_dfs = []
    
    for year in year_range:
        last_month = end_month_last_year if year == END_YEAR else 12
        for month in range(1, last_month + 1):
            nc_file = ERA5_NC_DIR / f"era5_pl850_{year}_{month:02d}.nc"
            if not nc_file.exists() or nc_file.stat().st_size == 0:
                logger.warning("  [CHƯA CÓ] File chưa tồn tại: %s (bỏ qua)", nc_file.name)
                continue
                
            try:
                df = extract_spatial_mean(
                    nc_file,
                    variables=ERA5_PRESSURE_LEVEL_VARS,
                    convert_kelvin=False,
                )
                all_dfs.append(df)
            except Exception as e:
                logger.error("  LỖI khi xử lý PL850 %d-%02d: %s", year, month, e)
                continue
    
    if not all_dfs:
        logger.error("Không trích xuất được dữ liệu Pressure Levels nào!")
        return pd.DataFrame()
    
    df_all = pd.concat(all_dfs, ignore_index=True)
    df_all = df_all.sort_values("datetime").drop_duplicates(subset="datetime").reset_index(drop=True)
    
    # Đổi tên cột cho đúng chuẩn của pipeline
    rename_map = {
        "u_component_of_wind": "u_wind_850hpa",
        "v_component_of_wind": "v_wind_850hpa",
        "specific_humidity": "specific_humidity_850hpa",
    }
    df_all = df_all.rename(columns=rename_map)
    
    return df_all


def main():
    """
    Hàm chính: Hỗ trợ cấu hình linh hoạt qua tham số dòng lệnh.
    """
    parser = argparse.ArgumentParser(
        description="Thu thập và trích xuất dữ liệu ERA5 Reanalysis (SST & Pressure Levels 850hPa) cho Đà Nẵng",
    )
    parser.add_argument("--check", action="store_true", help="Kiểm tra trạng thái các file NetCDF và CSV hiện có")
    parser.add_argument("--only-pl850", action="store_true", help="Chỉ tải và trích xuất Pressure Levels 850 hPa (bỏ qua SST)")
    parser.add_argument("--only-sst", action="store_true", help="Chỉ tải và trích xuất SST (bỏ qua PL850)")
    parser.add_argument("--extract-only", action="store_true", help="Chỉ trích xuất các file NetCDF có sẵn ra CSV (không gọi CDS API)")
    parser.add_argument("--year", type=int, default=None, help="Chỉ xử lý riêng một năm cụ thể (VD: 2024)")
    parser.add_argument("--chunk-size", type=int, default=3, help="Số tháng tối đa trong mỗi batch request PL850 (mặc định 3)")
    
    args = parser.parse_args()
    
    # 1. Chế độ kiểm tra trạng thái
    if args.check:
        check_status()
        return

    logger.info("=" * 70)
    logger.info("BẮT ĐẦU PIPELINE DỮ LIỆU ERA5 REANALYSIS")
    logger.info("  Bounding Box: N=%.1f, W=%.1f, S=%.1f, E=%.1f",
                BBOX["north"], BBOX["west"], BBOX["south"], BBOX["east"])
    logger.info("  Khoảng thời gian: %d – %d", START_YEAR, END_YEAR)
    logger.info("  Thư mục NetCDF: %s", ERA5_NC_DIR)
    if args.year:
        logger.info("  Năm chỉ định: %d", args.year)
    if args.extract_only:
        logger.info("  Chế độ: CHỈ TRÍCH XUẤT NetCDF -> CSV (không tải mới)")
    logger.info("=" * 70)
    
    client = None
    if not args.extract_only:
        check_cdsapi_config()
        client = cdsapi.Client()
        logger.info("Đã kết nối CDS API ✓")
    
    # ---- 1. Tải & Trích xuất SST ----
    if not args.only_pl850:
        df_sst = download_and_extract_sst(client, extract_only=args.extract_only, target_year=args.year)
        if not df_sst.empty:
            df_sst.to_csv(ERA5_SST_OUTPUT, index=False)
            logger.info("Đã lưu SST: %s (%d bản ghi, %.2f MB)",
                        ERA5_SST_OUTPUT, len(df_sst),
                        ERA5_SST_OUTPUT.stat().st_size / 1e6)
    
    # ---- 2. Tải & Trích xuất Pressure Levels 850 hPa ----
    if not args.only_sst:
        df_pl = download_and_extract_pressure_levels(
            client=client,
            extract_only=args.extract_only,
            target_year=args.year,
            max_chunk_size=args.chunk_size,
        )
        if not df_pl.empty:
            df_pl.to_csv(ERA5_PRESSURE_OUTPUT, index=False)
            logger.info("Đã lưu Pressure Levels: %s (%d bản ghi, %.2f MB)",
                        ERA5_PRESSURE_OUTPUT, len(df_pl),
                        ERA5_PRESSURE_OUTPUT.stat().st_size / 1e6)
    
    # --- Thống kê tổng hợp ---
    logger.info("=" * 70)
    logger.info("HOÀN TẤT XỬ LÝ ERA5!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
