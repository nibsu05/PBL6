# ==============================================================================
# run_poc_pipeline.py — Chạy tự động toàn bộ quy trình PoC
# ==============================================================================
"""
Module 6: Pipeline Orchestrator

Thực thi tuần tự:
1. build_datasets.py -> Tạo Dataset
2. feature_engineering.py -> Tạo Đặc trưng
3. baseline_model.py -> Train & Eval Bi-LSTM
4. visualize_poc_reports.py -> Xuất 4 Đồ thị

Sử dụng:
  python run_poc_pipeline.py
"""

import sys
import logging
from pathlib import Path
import time
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

def run_module(module_name: str) -> bool:
    script_path = BASE_DIR / module_name
    logger.info("*" * 60)
    logger.info("ĐANG CHẠY: %s", module_name)
    logger.info("*" * 60)
    
    start_time = time.time()
    try:
        # Chạy script như một sub-process để đảm bảo memory/state cô lập
        result = subprocess.run([sys.executable, str(script_path)], check=True, capture_output=True, text=True)
        # In output ra console
        print(result.stdout)
        
        elapsed = time.time() - start_time
        logger.info("✅ HOÀN THÀNH %s trong %.2f giây", module_name, elapsed)
        return True
    except subprocess.CalledProcessError as e:
        logger.error("❌ LỖI KHI CHẠY %s", module_name)
        logger.error("Mã lỗi: %s", e.returncode)
        logger.error("Chi tiết lỗi:\n%s", e.stderr)
        return False
    except Exception as e:
        logger.error("❌ LỖI KHÔNG XÁC ĐỊNH KHI CHẠY %s: %s", module_name, e)
        return False

def main():
    logger.info("=" * 70)
    logger.info("BẮT ĐẦU CHẠY PIPELINE PoC DỰ ĐOÁN MƯA ĐÀ NẴNG")
    logger.info("=" * 70)
    
    total_start_time = time.time()
    
    # Danh sách các module cần chạy
    modules = [
        "build_datasets.py",
        "feature_engineering.py",
        "baseline_model.py",
        "visualize_poc_reports.py"
    ]
    
    for mod in modules:
        success = run_module(mod)
        if not success:
            logger.error("Dừng pipeline do module %s thất bại.", mod)
            sys.exit(1)
            
    total_elapsed = time.time() - total_start_time
    
    logger.info("=" * 70)
    logger.info("🎉 TẤT CẢ MODULE ĐÃ CHẠY THÀNH CÔNG!")
    logger.info("Tổng thời gian thực thi: %.2f giây (%.2f phút)", total_elapsed, total_elapsed / 60)
    logger.info("Vui lòng kiểm tra thư mục 'datasets', 'checkpoints' và 'plots'")
    logger.info("=" * 70)

if __name__ == "__main__":
    main()
