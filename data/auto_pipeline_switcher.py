# ==============================================================================
# auto_pipeline_switcher.py — Tự động chuyển tiếp tiến trình
# Chờ hoàn thành lấp gap PL850 -> Cập nhật Bản merge -> Tự động tải tiếp Single-Levels
# ==============================================================================

import os
import sys
import time
import subprocess
import logging
from pathlib import Path
import pandas as pd

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw_data"
LAST_CHUNK_NC = RAW_DIR / "era5_nc_features" / "era5_pl850_gap_2024_10_to_12.nc"
PL_CSV = RAW_DIR / "era5_pressure_levels_2015_2026.csv"
PYTHON_EXE = sys.executable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("AutoSwitcher")


def is_pl850_complete() -> bool:
    """Kiểm tra xem chunk cuối cùng đã tải xong và CSV đã được ghi chưa."""
    if not (LAST_CHUNK_NC.exists() and LAST_CHUNK_NC.stat().st_size > 100000):
        return False
    try:
        # Kiểm tra file CSV đã có mốc cuối 2026-08 chưa
        df = pd.read_csv(PL_CSV, nrows=5)
        # Đọc 10 dòng cuối
        total_rows = sum(1 for _ in open(PL_CSV, encoding='utf-8', errors='ignore')) - 1
        last_df = pd.read_csv(PL_CSV, skiprows=max(1, total_rows - 10), header=None, names=df.columns)
        last_date = str(last_df['datetime'].iloc[-1])
        if "2026-08" in last_date:
            return True
    except Exception:
        pass
    return False


def main():
    logger.info("=" * 65)
    logger.info("BẮT ĐẦU GIÁM SÁT TỰ ĐỘNG CHUYỂN TIẾP TIẾN TRÌNH")
    logger.info("Đang theo dõi Chunk cuối [5/5] PL850 (2024_10_to_12)...")
    logger.info("=" * 65)

    check_interval = 20  # kiểm tra mỗi 20 giây
    while not is_pl850_complete():
        time.sleep(check_interval)

    logger.info("\n" + "★" * 65)
    logger.info("🎉 TẤT CẢ 15 THÁNG GAP CỦA TẦNG 850 hPa ĐÃ TẢI XONG!")
    logger.info("BƯỚC 1: Tự động chạy cập nhật lại 2 bản merge dữ liệu...")
    logger.info("★" * 65)

    merge_script = ROOT_DIR / "data" / "create_merged_datasets.py"
    subprocess.run([PYTHON_EXE, str(merge_script)], check=True)
    logger.info("✓ Đã cập nhật xong Bản 1 và Bản 2 (đầy đủ 100% các cột)!")

    logger.info("\n" + "★" * 65)
    logger.info("BƯỚC 2: Tự động kích hoạt lại tiến trình tải 4 biến nhiệt động")
    logger.info("(CIN, CAPE, TCWV, Độ ẩm đất) cho các năm cũ hơn (2021 -> 2015)...")
    logger.info("★" * 65)

    features_script = ROOT_DIR / "data" / "download_era5_features.py"
    # Chạy script tải single levels (tự động skip các quý 2022-2026 đã có sẵn)
    subprocess.run([PYTHON_EXE, str(features_script)], check=True)
    logger.info("🎉 TOÀN BỘ DỮ LIỆU ĐÃ ĐƯỢC THU THẬP VÀ XỬ LÝ HOÀN TẤT!")


if __name__ == "__main__":
    main()
