r"""Trích ERA5 theo giờ từ Google Earth Engine (``ECMWF/ERA5/HOURLY``) trên lưới 0,25°.

Phủ hộp Đà Nẵng mới cộng biên 0,5° (bối cảnh vùng cho nhóm A5/B5) và vài điểm
synop phía bắc để tính chỉ số không khí lạnh (nhóm B1). Giữ **đơn vị gốc ERA5**;
quy đổi làm ở bước dựng dataset:

- nhiệt độ K; áp suất Pa; gió m/s; mây 0–1; CAPE/CIN J/kg; TCWV kg/m²; BLH m;
  thông lượng ẩm kg/m/s; phân kỳ ẩm kg/m²/s; độ ẩm riêng kg/kg; RH %; omega Pa/s;
  ``total_precipitation`` m, tích lũy trong giờ *kết thúc* tại mốc thời gian.
- CIN bị mask khi không có mực đối lưu tự do: lưu NaN, **không** điền 0.
- Trên GEE chỉ có tầng 850 và 500 hPa; K-index và Total Totals đã tính sẵn từ cả tầng 700.

Chạy (có thể dừng/chạy lại; chia năm để chạy song song):
    python scripts/extract_gee_era5.py --project MY_PROJECT --start 2015-01 --end 2026-09
    python scripts/extract_gee_era5.py --combine
"""

from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import argparse
import logging
import time

import numpy as np
import pandas as pd

from extract_gee_precip import META_COLUMNS, time_chunks

COLLECTION = "ECMWF/ERA5/HOURLY"
ERA5_TRANSFORM = [0.25, 0, -180.125, 0, -0.25, 90.125]  # lưới gốc của collection trên GEE
RAW = ROOT / "data" / "raw_data" / "gee" / "era5" / "grid"
OUT = ROOT / "data" / "processed" / "gee" / "era5_grid_hourly.parquet"
DEFAULT_BBOX = (14.0, 17.0, 106.5, 109.5)  # Nam, Bắc, Tây, Đông
SYNOPTIC_POINTS = {  # điểm thêm cho chỉ số không khí lạnh / hình thế
    "syn_hanoi": (21.0, 105.75), "syn_tonkin": (20.0, 107.5), "syn_hainan": (20.0, 110.25), "syn_south": (12.0, 109.25),
}
BANDS = (
    # bề mặt
    "temperature_2m", "dewpoint_temperature_2m", "surface_pressure", "mean_sea_level_pressure",
    "u_component_of_wind_10m", "v_component_of_wind_10m",
    "total_cloud_cover", "low_cloud_cover", "medium_cloud_cover", "high_cloud_cover",
    # đối lưu – nhiệt động
    "convective_available_potential_energy", "convective_inhibition", "total_column_water_vapour",
    "k_index", "total_totals_index", "boundary_layer_height",
    # dòng ẩm tích phân
    "vertical_integral_of_eastward_water_vapour_flux", "vertical_integral_of_northward_water_vapour_flux",
    "vertical_integral_of_divergence_of_moisture_flux",
    # mưa mô hình (đầu vào nhóm "mưa của mô hình số", không phải nhãn)
    "total_precipitation",
    # tầng cao
    "u_component_of_wind_850hPa", "v_component_of_wind_850hPa", "specific_humidity_850hPa",
    "temperature_850hPa", "vertical_velocity_850hPa", "relative_humidity_850hPa",
    "u_component_of_wind_500hPa", "v_component_of_wind_500hPa", "specific_humidity_500hPa",
    "temperature_500hPa", "vertical_velocity_500hPa",
    # biến chậm
    "sea_surface_temperature", "volumetric_soil_water_layer_1",
)

LOGGER = logging.getLogger("extract_era5")


def era5_points(bbox: tuple[float, float, float, float] = DEFAULT_BBOX, res: float = 0.25) -> pd.DataFrame:
    """Tâm ô ERA5 (bội số 0,25°) trong bbox, cộng các điểm synop."""
    south, north, west, east = bbox
    lats = np.round(np.arange(np.ceil(south / res) * res, north + 1e-9, res), 2)
    lons = np.round(np.arange(np.ceil(west / res) * res, east + 1e-9, res), 2)
    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing="ij")
    grid = pd.DataFrame({"lat": lat_grid.ravel(), "lon": lon_grid.ravel()})
    grid.insert(0, "site", [f"e{la:.2f}_{lo:.2f}" for la, lo in zip(grid["lat"], grid["lon"])])
    syn = pd.DataFrame([{"site": k, "lat": v[0], "lon": v[1]} for k, v in SYNOPTIC_POINTS.items()])
    return pd.concat([grid, syn], ignore_index=True)


def rows_to_frame(rows: list[list], points: pd.DataFrame) -> pd.DataFrame:
    """Kết quả ``getRegion`` → bảng rộng (thời gian × điểm); pixel bị mask thành NaN."""
    header, body = rows[0], rows[1:]
    if list(header) != [*META_COLUMNS, *BANDS]:
        raise ValueError(f"Header getRegion không như mong đợi: {header[:6]}…")
    frame = pd.DataFrame(body, columns=header)
    if frame.empty:
        return frame
    lat_req, lon_req = points["lat"].to_numpy(), points["lon"].to_numpy()
    dist = np.hypot(frame["latitude"].to_numpy(float)[:, None] - lat_req[None, :],
                    frame["longitude"].to_numpy(float)[:, None] - lon_req[None, :])
    nearest = dist.argmin(axis=1)
    if np.any(dist[np.arange(len(frame)), nearest] > 0.01):
        raise ValueError("Pixel ERA5 trả về không trùng tâm ô yêu cầu (lệch > 0,01°)")
    out = pd.DataFrame({"time_utc": pd.to_datetime(frame["time"], unit="ms"),
                        "site": points["site"].to_numpy()[nearest]})
    for band in BANDS:
        out[band] = pd.to_numeric(frame[band], errors="coerce").astype("float32")
    return out.sort_values(["site", "time_utc"]).reset_index(drop=True)


def fetch_chunk(ee, points: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    geometry = ee.Geometry.MultiPoint([[float(lo), float(la)] for la, lo in zip(points["lat"], points["lon"])])
    coll = (ee.ImageCollection(COLLECTION)
            .filterDate(start.strftime("%Y-%m-%dT%H:%M:%S"), end.strftime("%Y-%m-%dT%H:%M:%S"))
            .select(list(BANDS)))
    for attempt in range(4):
        try:
            # Lấy đúng lưới gốc ERA5 (tâm ô ở bội số 0,25°); dùng `scale` sẽ lấy mẫu trên lưới lệch nửa ô.
            rows = coll.getRegion(geometry, crs="EPSG:4326", crsTransform=ERA5_TRANSFORM).getInfo()
        except Exception as exc:  # lỗi tạm thời của GEE
            LOGGER.warning("Lỗi GEE %s–%s (lần %d): %s", start, end, attempt + 1, exc)
            time.sleep(10 * (attempt + 1))
            continue
        return rows_to_frame(rows, points)  # lỗi dữ liệu ở đây không thử lại
    raise RuntimeError(f"GEE thất bại liên tục cho ERA5 {start}–{end}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project")
    parser.add_argument("--start", default="2015-01")
    parser.add_argument("--end", default="2026-09")
    parser.add_argument("--combine", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    points = era5_points()
    if args.combine:
        files = sorted(RAW.glob("*.parquet"))
        frame = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
        frame = frame.drop_duplicates(["site", "time_utc"]).merge(points, on="site", how="left")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(OUT, index=False)
        hours = frame["time_utc"].nunique()
        expected = int((frame["time_utc"].max() - frame["time_utc"].min()) / pd.Timedelta(hours=1)) + 1
        LOGGER.info("Ghi %s: %d điểm, %d/%d giờ, CIN NaN %.0f %%", OUT.relative_to(ROOT), frame["site"].nunique(),
                    hours, expected, 100 * frame["convective_inhibition"].isna().mean())
        return
    if not args.project:
        parser.error("--project là bắt buộc khi tải")
    import ee
    ee.Initialize(project=args.project)
    RAW.mkdir(parents=True, exist_ok=True)
    start, end = pd.Timestamp(args.start + "-01"), pd.Timestamp(args.end + "-01") + pd.offsets.MonthBegin(1)
    chunks = time_chunks(start, end, 1.0, len(points), len(META_COLUMNS) + len(BANDS))
    LOGGER.info("ERA5: %d điểm, %d biến, %d khối", len(points), len(BANDS), len(chunks))
    for c0, c1 in chunks:
        path = RAW / f"{c0:%Y%m%dT%H}_{c1:%Y%m%dT%H}.parquet"
        if path.exists():
            continue
        frame = fetch_chunk(ee, points, c0, c1)
        frame.to_parquet(path, index=False)
        LOGGER.info("  %s: %d hàng", path.name, len(frame))


if __name__ == "__main__":
    main()
