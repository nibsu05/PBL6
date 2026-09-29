# ==============================================================================
# create_merged_datasets.py — Tạo 2 bản merge dữ liệu theo yêu cầu
# Bản 1: Dữ liệu cơ sở 2015-2026 (Chưa có CIN, CAPE, TCWV, độ ẩm đất)
# Bản 2: Dữ liệu đầy đủ 2023-2026 (CÓ ĐỦ CIN, CAPE, TCWV, độ ẩm đất)
# ==============================================================================

from pathlib import Path
import logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DataMerger")

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw_data"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

LOCAL_TZ = "Asia/Ho_Chi_Minh"


def load_raw_sources():
    """Đọc toàn bộ các nguồn dữ liệu thô và chuẩn hóa trục thời gian UTC."""
    logger.info("Đang đọc các nguồn dữ liệu thô...")
    
    # 1. Open-Meteo
    om_file = RAW_DIR / "openmeteo_danang_2015_2026.csv"
    om = pd.read_csv(om_file)
    om["datetime"] = pd.to_datetime(om["datetime"], utc=True)
    om = om.drop_duplicates(subset=["datetime"]).set_index("datetime").sort_index()
    logger.info("  ✓ Open-Meteo: %d mốc giờ (%s -> %s)", len(om), om.index.min(), om.index.max())

    # 2. ERA5 SST
    sst_file = RAW_DIR / "era5_sst_2015_2026.csv"
    sst = pd.read_csv(sst_file)
    sst["datetime"] = pd.to_datetime(sst["datetime"], utc=True)
    sst = sst.drop_duplicates(subset=["datetime"]).set_index("datetime").sort_index()
    logger.info("  ✓ ERA5 SST: %d mốc giờ (%s -> %s)", len(sst), sst.index.min(), sst.index.max())

    # 3. ERA5 PL850
    pl_file = RAW_DIR / "era5_pressure_levels_2015_2026.csv"
    pl = pd.read_csv(pl_file)
    pl["datetime"] = pd.to_datetime(pl["datetime"], utc=True)
    pl = pl.rename(columns={
        "u_wind_850hpa": "u_850",
        "v_wind_850hpa": "v_850",
        "specific_humidity_850hpa": "specific_humidity_850",
    })
    pl = pl.drop_duplicates(subset=["datetime"]).set_index("datetime").sort_index()
    logger.info("  ✓ ERA5 PL850: %d mốc giờ (%s -> %s)", len(pl), pl.index.min(), pl.index.max())

    # 4. NOAA ONI
    oni_file = RAW_DIR / "enso_oni_2015_2026.csv"
    oni = pd.read_csv(oni_file)
    oni["datetime"] = pd.to_datetime(oni["datetime"], utc=True)
    oni = oni.drop_duplicates(subset=["datetime"]).set_index("datetime").sort_index()
    logger.info("  ✓ NOAA ONI: %d mốc giờ", len(oni))

    # 5. ERA5 Thermo & Soil Moisture (MỚI)
    thermo_file = RAW_DIR / "era5_thermo_soil_2015_2026.csv"
    thermo = pd.read_csv(thermo_file)
    thermo["time"] = pd.to_datetime(thermo["time"], utc=True)
    thermo = thermo.rename(columns={"time": "datetime"})
    thermo = thermo.drop_duplicates(subset=["datetime"]).set_index("datetime").sort_index()
    logger.info("  ✓ ERA5 Thermo & Soil: %d mốc giờ (%s -> %s)", len(thermo), thermo.index.min(), thermo.index.max())

    return om, sst, pl, oni, thermo


def interpolate_short_gaps(df: pd.DataFrame, max_hours: int = 2) -> pd.DataFrame:
    """Nội suy ngắn tối đa 2 giờ đối với biến thời tiết, không nội suy precipitation."""
    result = df.copy()
    for col in result.columns:
        if col in ("precipitation", "oni_anom"):
            continue
        missing = result[col].isna()
        if not missing.any():
            continue
        groups = missing.ne(missing.shift(fill_value=False)).cumsum()
        short = missing & missing.groupby(groups).transform("sum").le(max_hours)
        candidate = result[col].interpolate(method="time", limit_area="inside")
        result[col] = result[col].where(~short, candidate)
    return result


def create_dataset_1_baseline(om, sst, pl, oni):
    """
    Bản 1: Bản merge toàn bộ dữ liệu 2015-2026 CHƯA CÓ CIN, CAPE, TCWV, độ ẩm đất.
    """
    logger.info("\n" + "=" * 60)
    logger.info("TẠO BẢN 1: Dữ liệu cơ sở 2015-2026 (Không có 4 biến mới)")
    logger.info("=" * 60)

    # Khung giờ chuẩn từ Open-Meteo
    ref_idx = pd.date_range(om.index.min(), om.index.max(), freq="h", tz="UTC")
    merged = om.reindex(ref_idx).join(sst, how="left").join(pl, how="left").join(oni, how="left")
    
    # Nội suy ngắn tối đa 2 giờ
    merged = interpolate_short_gaps(merged, max_hours=2)

    # Bản 1A: Giữ toàn bộ giờ có đầy đủ cả tầng 850 hPa (loại bỏ gap PL850)
    strict_df = merged.dropna(subset=["precipitation", "temperature_2m", "u_850", "sea_surface_temperature"]).copy()
    strict_df.index = strict_df.index.tz_convert(LOCAL_TZ)
    strict_df.index.name = "datetime"
    
    out_csv = PROCESSED_DIR / "danang_baseline_2015_2026_no_thermo_soil.csv"
    out_parquet = PROCESSED_DIR / "danang_baseline_2015_2026_no_thermo_soil.parquet"
    strict_df.reset_index().to_csv(out_csv, index=False)
    strict_df.reset_index().to_parquet(out_parquet, index=False)
    
    logger.info("✓ Đã lưu Bản 1 (Strict PL850): %s", out_csv.name)
    logger.info("  Số dòng: %d mốc giờ (%s -> %s)", len(strict_df), strict_df.index.min(), strict_df.index.max())
    logger.info("  Các cột (%d): %s", len(strict_df.columns), list(strict_df.columns))


def create_dataset_2_full_features_2023_2026(om, sst, pl, oni, thermo):
    """
    Bản 2: Bản merge ĐẦY ĐỦ từ 2023 đến 2026 (CÓ ĐỦ cả CIN, CAPE, TCWV, Độ ẩm đất).
    """
    logger.info("\n" + "=" * 60)
    logger.info("TẠO BẢN 2: Dữ liệu đầy đủ 2023-2026 (CÓ ĐỦ CIN, CAPE, TCWV, Độ ẩm đất)")
    logger.info("=" * 60)

    start_date = pd.Timestamp("2023-01-01 00:00:00", tz="UTC")
    end_date = pd.Timestamp("2026-08-31 23:00:00", tz="UTC")
    ref_idx = pd.date_range(start_date, end_date, freq="h", tz="UTC")

    # Ghép toàn bộ
    merged = om.reindex(ref_idx).join(sst, how="left").join(thermo, how="left").join(pl, how="left").join(oni, how="left")
    
    # Nội suy ngắn <= 2 giờ cho các biến liên tục
    merged = interpolate_short_gaps(merged, max_hours=2)

    # Đổi timezone sang Asia/Ho_Chi_Minh
    merged.index = merged.index.tz_convert(LOCAL_TZ)
    merged.index.name = "datetime"
    res = merged.reset_index()

    out_csv = PROCESSED_DIR / "danang_full_features_2023_2026.csv"
    out_parquet = PROCESSED_DIR / "danang_full_features_2023_2026.parquet"
    res.to_csv(out_csv, index=False)
    res.to_parquet(out_parquet, index=False)

    logger.info("✓ Đã lưu Bản 2: %s", out_csv.name)
    logger.info("  Số dòng: %d mốc giờ (%s -> %s)", len(res), res["datetime"].min(), res["datetime"].max())
    logger.info("  Các cột (%d): %s", len(res.columns), list(res.columns))
    
    # Kiểm tra tỷ lệ đầy đủ của từng cột
    logger.info("\n  Tỷ lệ dữ liệu hợp lệ (Non-null count):")
    for col in res.columns:
        valid_cnt = res[col].notna().sum()
        pct = (valid_cnt / len(res)) * 100
        logger.info("    * %-25s: %6d / %6d (%.2f%%)", col, valid_cnt, len(res), pct)


def create_dataset_3_full_features_2021_2026(om, sst, pl, oni, thermo):
    """
    Bản 3: Bản merge ĐẦY ĐỦ từ 2021 đến 2026 (CÓ ĐỦ cả CIN, CAPE, TCWV, Độ ẩm đất).
    """
    logger.info("\n" + "=" * 60)
    logger.info("TẠO BẢN 3: Dữ liệu đầy đủ 2021-2026 (CÓ ĐỦ CIN, CAPE, TCWV, Độ ẩm đất)")
    logger.info("=" * 60)

    start_date = pd.Timestamp("2021-01-01 00:00:00", tz="UTC")
    end_date = pd.Timestamp("2026-08-31 23:00:00", tz="UTC")
    ref_idx = pd.date_range(start_date, end_date, freq="h", tz="UTC")

    # Ghép toàn bộ
    merged = om.reindex(ref_idx).join(sst, how="left").join(thermo, how="left").join(pl, how="left").join(oni, how="left")
    
    # Nội suy ngắn <= 2 giờ cho các biến liên tục
    merged = interpolate_short_gaps(merged, max_hours=2)

    # Đổi timezone sang Asia/Ho_Chi_Minh
    merged.index = merged.index.tz_convert(LOCAL_TZ)
    merged.index.name = "datetime"
    res = merged.reset_index()

    out_csv = PROCESSED_DIR / "danang_full_features_2021_2026.csv"
    out_parquet = PROCESSED_DIR / "danang_full_features_2021_2026.parquet"
    res.to_csv(out_csv, index=False)
    res.to_parquet(out_parquet, index=False)

    logger.info("✓ Đã lưu Bản 3: %s", out_csv.name)
    logger.info("  Số dòng: %d mốc giờ (%s -> %s)", len(res), res["datetime"].min(), res["datetime"].max())
    logger.info("  Các cột (%d): %s", len(res.columns), list(res.columns))
    
    # Kiểm tra tỷ lệ đầy đủ của từng cột
    logger.info("\n  Tỷ lệ dữ liệu hợp lệ (Non-null count):")
    for col in res.columns:
        valid_cnt = res[col].notna().sum()
        pct = (valid_cnt / len(res)) * 100
        logger.info("    * %-25s: %6d / %6d (%.2f%%)", col, valid_cnt, len(res), pct)


def main():
    om, sst, pl, oni, thermo = load_raw_sources()
    create_dataset_1_baseline(om, sst, pl, oni)
    create_dataset_2_full_features_2023_2026(om, sst, pl, oni, thermo)
    create_dataset_3_full_features_2021_2026(om, sst, pl, oni, thermo)
    logger.info("\n🎉 ĐÃ TẠO XONG CÁC BẢN MERGE THÀNH CÔNG!")


if __name__ == "__main__":
    main()

