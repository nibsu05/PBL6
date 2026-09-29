# ==============================================================================
# config.py — Cấu hình tập trung cho pipeline thu thập dữ liệu khí tượng Đà Nẵng
# ==============================================================================
"""
Tập trung tất cả hằng số, đường dẫn, và cấu hình cho các module:
  - download_openmeteo.py
  - download_era5.py
  - download_enso.py
  - merge_and_clean.py
"""

import os
from pathlib import Path

# ==============================================================================
# 1. VỊ TRÍ ĐỊA LÝ
# ==============================================================================

# Tọa độ trung tâm Đà Nẵng
DANANG_LAT = 16.0544
DANANG_LON = 108.2022

# Bounding Box khu vực Biển Đông kề bên (cho ERA5)
# Dùng để lấy đặc trưng biển & khí quyển khu vực
BBOX = {
    "north": 18.0,
    "west": 107.0,
    "south": 14.0,
    "east": 111.0,
}

# ==============================================================================
# 2. KHUNG THỜI GIAN
# ==============================================================================

START_DATE = "2015-01-01"
END_DATE = "2026-08-31"
START_YEAR = 2015
END_YEAR = 2026
TIMEZONE = "Asia/Ho_Chi_Minh"  # UTC+7

# ==============================================================================
# 3. CÁC BIẾN DỮ LIỆU
# ==============================================================================

# Biến Open-Meteo (thời tiết bề mặt, hourly)
OPENMETEO_HOURLY_VARS = [
    "temperature_2m",           # Nhiệt độ 2m (°C)
    "relative_humidity_2m",     # Độ ẩm tương đối 2m (%)
    "surface_pressure",         # Áp suất bề mặt (hPa)
    "wind_speed_10m",           # Tốc độ gió 10m (km/h)
    "wind_direction_10m",       # Hướng gió 10m (°)
    "precipitation",            # Lượng mưa (mm) — BIẾN TARGET
]

# Biến ERA5 - Single Levels (bề mặt biển)
ERA5_SINGLE_LEVEL_VARS = [
    "sea_surface_temperature",  # SST (K → chuyển sang °C)
]

# Biến ERA5 - Pressure Levels (tầng khí quyển 850 hPa)
ERA5_PRESSURE_LEVEL_VARS = [
    "u_component_of_wind",      # Thành phần gió U (m/s)
    "v_component_of_wind",      # Thành phần gió V (m/s)
    "specific_humidity",        # Độ ẩm riêng (kg/kg)
]
ERA5_PRESSURE_LEVEL = "850"     # hPa — tầng đặc trưng gió mùa & dòng ẩm

# ==============================================================================
# 4. ĐƯỜNG DẪN THƯ MỤC & FILE OUTPUT
# ==============================================================================

# Thư mục gốc của dự án (thư mục chứa config.py)
BASE_DIR = Path(__file__).resolve().parent

# Thư mục lưu dữ liệu thô (raw)
RAW_DATA_DIR = BASE_DIR / "raw_data"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Thư mục lưu dữ liệu ERA5 NetCDF tạm thời
ERA5_NC_DIR = RAW_DATA_DIR / "era5_netcdf"
ERA5_NC_DIR.mkdir(parents=True, exist_ok=True)

# --- File output trung gian ---
OPENMETEO_OUTPUT = RAW_DATA_DIR / "openmeteo_danang_2015_2026.csv"
ERA5_SST_OUTPUT = RAW_DATA_DIR / "era5_sst_2015_2026.csv"
ERA5_PRESSURE_OUTPUT = RAW_DATA_DIR / "era5_pressure_levels_2015_2026.csv"
ENSO_OUTPUT = RAW_DATA_DIR / "enso_oni_2015_2026.csv"

# --- File output cuối cùng ---
FINAL_CSV = BASE_DIR / "danang_rain_dataset_2015_2026.csv"
FINAL_PARQUET = BASE_DIR / "danang_rain_dataset_2015_2026.parquet"

# ==============================================================================
# 5. API ENDPOINTS
# ==============================================================================

# Open-Meteo Historical Weather API
OPENMETEO_URL = "https://archive-api.open-meteo.com/v1/archive"

# NOAA CPC — Oceanic Niño Index (ONI)
NOAA_ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"

# CDS API — Dataset names
ERA5_SINGLE_LEVELS_DATASET = "reanalysis-era5-single-levels"
ERA5_PRESSURE_LEVELS_DATASET = "reanalysis-era5-pressure-levels"

# ==============================================================================
# 6. THAM SỐ KỸ THUẬT
# ==============================================================================

# Giới hạn nội suy linear (max số giờ liên tiếp bị khuyết được phép nội suy)
INTERPOLATION_LIMIT = 6

# Cache cho Open-Meteo requests (giảm tải lên API khi chạy lại)
OPENMETEO_CACHE_DB = str(RAW_DATA_DIR / ".openmeteo_cache.sqlite")
OPENMETEO_CACHE_TTL = 86400  # 1 ngày (seconds)

# Retry cho requests bị lỗi
RETRY_MAX_ATTEMPTS = 5
RETRY_BACKOFF_FACTOR = 0.5
