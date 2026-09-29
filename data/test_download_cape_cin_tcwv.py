# ==============================================================================
# test_download_cape_cin_tcwv.py — Thử nghiệm tải CAPE, CIN, TCWV/TCW từ ERA5
# ==============================================================================
"""
Script thử nghiệm tải và trích xuất các chỉ số bất ổn định nhiệt động lực học
và tổng lượng nước trong cột khí quyển từ ERA5 Single Levels:
  1. convective_available_potential_energy (CAPE) [J/kg]
  2. convective_inhibition                 (CIN)  [J/kg]
  3. total_column_water_vapour            (TCWV) [kg/m^2]
  4. total_column_water                   (TCW)  [kg/m^2]

Khu vực: Bounding Box Đà Nẵng [14°N–18°N, 107°E–111°E]
"""

import sys
import logging
from pathlib import Path
import cdsapi
import xarray as xr
import pandas as pd
import numpy as np

from config import BBOX

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def download_sample_thermodynamic(year="2024", month="08", day="31", time_str="12:00"):
    """
    Tải thử nghiệm 1 mốc thời gian cho CAPE, CIN, TCWV, TCW qua CDS API.
    """
    client = cdsapi.Client()
    out_nc = Path(f"sample_cape_cin_{year}_{month}_{day}_{time_str.replace(':', '')}.nc")

    request = {
        "product_type": ["reanalysis"],
        "variable": [
            "convective_available_potential_energy",
            "convective_inhibition",
            "total_column_water_vapour",
            "total_column_water",
        ],
        "year": [str(year)],
        "month": [f"{int(month):02d}"],
        "day": [f"{int(day):02d}"],
        "time": [time_str],
        "data_format": "netcdf",
        "area": [BBOX["north"], BBOX["west"], BBOX["south"], BBOX["east"]],
    }

    logger.info("Đang gửi yêu cầu đến CDS API: Mốc %s-%s-%s %s UTC...", year, month, day, time_str)
    
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            client.retrieve("reanalysis-era5-single-levels", request, str(out_nc))
            break
        except Exception as e:
            err_str = str(e)
            if "temporarily limited" in err_str or "rejected" in err_str:
                wait_s = attempt * 20
                logger.warning("  [HÀNG ĐỢI ĐẦY] ECMWF tạm giới hạn số request (lần %d/%d). Đợi %d giây rồi thử lại...", attempt, max_retries, wait_s)
                import time
                time.sleep(wait_s)
            else:
                logger.error("  Lỗi không mong muốn: %s", e)
                raise e
    else:
        logger.error("Đã thử %d lần nhưng hàng đợi CDS vẫn đầy. Vui lòng thử lại sau vài phút!", max_retries)
        return None

    logger.info("✓ Tải thành công: %s (%.2f KB)", out_nc.name, out_nc.stat().st_size / 1024)

    # Đọc NetCDF và hiển thị số liệu
    with xr.open_dataset(out_nc) as ds:
        logger.info("\n--- THÔNG TIN CÁC BIẾN TRONG FILE NETCDF ---")
        for v in ds.data_vars:
            long_name = ds[v].attrs.get("long_name", "")
            units = ds[v].attrs.get("units", "")
            logger.info("  * Biến '%s' (%s): đơn vị [%s], shape=%s", v, long_name, units, ds[v].shape)

        # Tính trung bình không gian trên Bounding Box Đà Nẵng
        logger.info("\n--- GIÁ TRỊ TRUNG BÌNH KHÔNG GIAN (SPATIAL MEAN) ---")
        weights = np.cos(np.deg2rad(ds.latitude if "latitude" in ds.coords else ds.lat))
        weights = weights / weights.mean()
        lat_dim = "latitude" if "latitude" in ds.dims else "lat"
        lon_dim = "longitude" if "longitude" in ds.dims else "lon"

        for v in ds.data_vars:
            mean_val = float((ds[v] * weights).mean(dim=[lat_dim, lon_dim]).values.ravel()[0])
            logger.info("  * %s: %.2f %s", v, mean_val, ds[v].attrs.get("units", ""))

    return out_nc


if __name__ == "__main__":
    download_sample_thermodynamic(year="2024", month="08", day="31", time_str="12:00")
