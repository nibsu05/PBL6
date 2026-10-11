r"""Trích mưa vệ tinh IMERG V07 và GSMaP v8 từ Google Earth Engine tại trạm hoặc trên lưới ô.

Dùng cho Thí nghiệm 0 (chọn nhãn) và để dựng dataset ô lưới:

- ``imerg``: ``NASA/GPM_L3/IMERG_V07``, nửa giờ, band ``precipitation`` (đã hiệu
  chỉnh theo trạm hằng tháng ở bản permanent) và ``precipitationUncal``. Trên
  GEE, bản permanent (Final) chỉ có đến 30/09/2025; sau đó là provisional.
- ``gsmap``: ``JAXA/GPM_L3/GSMaP/v8/operational``, 1 giờ, band ``hourlyPrecipRate``
  và ``hourlyPrecipRateGC`` (hiệu chỉnh theo trạm CPC). Ảnh provisional (NRT) được
  thay bằng permanent khi có bản chuẩn.

Mỗi ảnh được gắn band ``permanent`` (1 = permanent, 0 = provisional, −1 = không
rõ) từ thuộc tính ``status``. Đơn vị gốc mm/h; độ sâu của một khoảng = tốc độ ×
độ dài khoảng (0,5 h với IMERG, 1 h với GSMaP). Thời gian lưu là *đầu* khoảng, UTC.

Chuẩn bị một lần:
    pip install earthengine-api
    earthengine authenticate
    # cần một Google Cloud project đã đăng ký Earth Engine (miễn phí cho phi thương mại)

Chạy (tải có thể dừng và chạy lại, khối nào đã có sẽ bỏ qua):
    python scripts/extract_gee_precip.py --project MY_PROJECT --target stations --dataset imerg gsmap --start 2015-01 --end 2025-09
    python scripts/extract_gee_precip.py --target stations --combine
    python scripts/extract_gee_precip.py --project MY_PROJECT --target grid --dataset gsmap --start 2015-01 --end 2025-12
    python scripts/extract_gee_precip.py --target grid --dataset gsmap --combine
"""

from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import logging
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.station_registry import STATIONS

RAW = ROOT / "data" / "raw_data" / "gee"
PROCESSED = ROOT / "data" / "processed"
STATION_DAILY = PROCESSED / "stations" / "gee_daily.parquet"
DEFAULT_BBOX = (14.6, 16.5, 107.0, 109.0)  # Nam, Bắc, Tây, Đông: Đà Nẵng mới + biên 0,2° cho đặc trưng lân cận
MAX_VALUES_PER_CALL = 600_000              # dưới giới hạn ~1 triệu giá trị của getRegion
META_COLUMNS = ("id", "longitude", "latitude", "time")

LOGGER = logging.getLogger("extract_gee")


@dataclass(frozen=True)
class Dataset:
    key: str
    collection: str
    bands: tuple[str, ...]
    step_hours: float
    sources: dict[str, str]  # band -> tên nguồn khi gộp theo ngày


DATASETS = {
    "imerg": Dataset("imerg", "NASA/GPM_L3/IMERG_V07", ("precipitation", "precipitationUncal"), 0.5,
                     {"precipitation": "imerg", "precipitationUncal": "imerg_uncal"}),
    "gsmap": Dataset("gsmap", "JAXA/GPM_L3/GSMaP/v8/operational", ("hourlyPrecipRate", "hourlyPrecipRateGC"), 1.0,
                     {"hourlyPrecipRate": "gsmap", "hourlyPrecipRateGC": "gsmap_gc"}),
}


# ------------------------------------------------------------ hàm thuần --

def station_points() -> pd.DataFrame:
    return pd.DataFrame({"site": [s.usaf for s in STATIONS], "lat": [s.lat for s in STATIONS],
                         "lon": [s.lon for s in STATIONS]})


def grid_points(bbox: tuple[float, float, float, float], res: float = 0.1) -> pd.DataFrame:
    """Tâm ô lưới 0,1° của IMERG/GSMaP (tâm ở x,x5°) nằm trong bbox."""
    south, north, west, east = bbox
    lats = np.round(np.arange(np.floor(south / res) * res + res / 2, north, res), 3)
    lons = np.round(np.arange(np.floor(west / res) * res + res / 2, east, res), 3)
    lat_grid, lon_grid = np.meshgrid(lats[lats >= south], lons[lons >= west], indexing="ij")
    frame = pd.DataFrame({"lat": lat_grid.ravel(), "lon": lon_grid.ravel()})
    frame.insert(0, "site", [f"c{la:.2f}_{lo:.2f}" for la, lo in zip(frame["lat"], frame["lon"])])
    return frame


def time_chunks(start: pd.Timestamp, end: pd.Timestamp, step_hours: float, n_points: int,
                n_columns: int) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Chia [start, end) thành các khối không vượt MAX_VALUES_PER_CALL và không vắt qua tháng."""
    images_per_call = max(1, MAX_VALUES_PER_CALL // (n_points * n_columns))
    span = pd.Timedelta(hours=step_hours * images_per_call)
    chunks = []
    month_start = start
    while month_start < end:
        month_end = min(month_start + pd.offsets.MonthBegin(1), end)
        cursor = month_start
        while cursor < month_end:
            nxt = min(cursor + span, month_end)
            chunks.append((cursor, nxt))
            cursor = nxt
        month_start = month_end
    return chunks


def rows_to_frame(rows: list[list], points: pd.DataFrame, dataset: Dataset) -> pd.DataFrame:
    """Đổi kết quả ``getRegion`` thành bảng dài; gán mỗi pixel về điểm yêu cầu gần nhất."""
    header, body = rows[0], rows[1:]
    expected = [*META_COLUMNS, *dataset.bands, "permanent"]
    if list(header) != expected:
        raise ValueError(f"Header getRegion không như mong đợi: {header}")
    frame = pd.DataFrame(body, columns=header)
    if frame.empty:
        return frame
    lat_req, lon_req = points["lat"].to_numpy(), points["lon"].to_numpy()
    dist = np.hypot(frame["latitude"].to_numpy()[:, None] - lat_req[None, :],
                    frame["longitude"].to_numpy()[:, None] - lon_req[None, :])
    nearest = dist.argmin(axis=1)
    if np.any(dist[np.arange(len(frame)), nearest] > 0.08):
        raise ValueError("Pixel trả về cách điểm yêu cầu quá 0,08°")
    out = pd.DataFrame({
        "time_start_utc": pd.to_datetime(frame["time"], unit="ms"),
        "site": points["site"].to_numpy()[nearest],
        "pixel_lat": frame["latitude"].astype(float), "pixel_lon": frame["longitude"].astype(float),
        "permanent": frame["permanent"].astype(float),
    })
    for band in dataset.bands:
        out[f"{band}_mm"] = pd.to_numeric(frame[band], errors="coerce") * dataset.step_hours
    return out.sort_values(["site", "time_start_utc"]).reset_index(drop=True)


def daily_totals(frame: pd.DataFrame, dataset: Dataset, *, permanent_only: bool = True) -> pd.DataFrame:
    """Tổng ngày UTC theo trạm; chỉ giữ ngày đủ mọi khoảng (48 nửa giờ hoặc 24 giờ)."""
    data = frame if not permanent_only else frame[frame["permanent"] == 1]
    need = int(round(24 / dataset.step_hours))
    data = data.assign(date=data["time_start_utc"].dt.floor("D"))
    out = []
    for band, source in dataset.sources.items():
        col = f"{band}_mm"
        grp = data.groupby(["site", "date"])[col].agg(["sum", "count"]).reset_index()
        grp = grp[grp["count"] == need]
        out.append(pd.DataFrame({"date": grp["date"], "usaf": grp["site"], "source": source,
                                 "precip_mm": grp["sum"].astype(float)}))
    return pd.concat(out, ignore_index=True)


def hourly_depth(frame: pd.DataFrame, dataset: Dataset) -> pd.DataFrame:
    """Độ sâu mưa từng giờ (đầu khoảng, UTC) cho dataset ô lưới; giờ thiếu nửa giờ thì NaN."""
    data = frame.assign(hour=frame["time_start_utc"].dt.floor("h"))
    cols = [f"{b}_mm" for b in dataset.bands]
    agg = data.groupby(["site", "hour"]).agg(**{c: (c, "sum") for c in cols}, n=("permanent", "size"),
                                              permanent=("permanent", "min"))
    need = int(round(1 / dataset.step_hours))
    agg.loc[agg["n"] < need, cols] = np.nan
    return agg.drop(columns="n").reset_index().rename(columns={"hour": "time_start_utc"})


# --------------------------------------------------------- Earth Engine --

def _collection(ee, dataset: Dataset, start: pd.Timestamp, end: pd.Timestamp):
    def with_status(img):
        status = ee.String(ee.Algorithms.If(img.propertyNames().contains("status"), img.get("status"), "unknown"))
        flag = ee.Number(ee.Algorithms.If(status.equals("permanent"), 1,
                                          ee.Algorithms.If(status.equals("provisional"), 0, -1)))
        return img.select(list(dataset.bands)).toFloat().addBands(ee.Image.constant(flag).toFloat().rename("permanent"))
    return (ee.ImageCollection(dataset.collection)
            .filterDate(start.strftime("%Y-%m-%dT%H:%M:%S"), end.strftime("%Y-%m-%dT%H:%M:%S"))
            .map(with_status))


def fetch_chunk(ee, dataset: Dataset, points: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    geometry = ee.Geometry.MultiPoint([[float(lo), float(la)] for la, lo in zip(points["lat"], points["lon"])])
    for attempt in range(4):
        try:
            rows = _collection(ee, dataset, start, end).getRegion(geometry, 11132).getInfo()
            return rows_to_frame(rows, points, dataset)
        except Exception as exc:  # GEE trả nhiều loại lỗi tạm thời (quá tải, hết giờ tính toán)
            LOGGER.warning("Lỗi GEE %s %s–%s (lần %d): %s", dataset.key, start, end, attempt + 1, exc)
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"GEE thất bại liên tục cho {dataset.key} {start}–{end}")


def extract(args: argparse.Namespace, points: pd.DataFrame) -> None:
    import ee  # chỉ cần khi tải

    ee.Initialize(project=args.project)
    start, end = pd.Timestamp(args.start + "-01"), pd.Timestamp(args.end + "-01") + pd.offsets.MonthBegin(1)
    for key in args.dataset:
        dataset = DATASETS[key]
        folder = RAW / key / args.target
        folder.mkdir(parents=True, exist_ok=True)
        chunks = time_chunks(start, end, dataset.step_hours, len(points), len(META_COLUMNS) + len(dataset.bands) + 1)
        LOGGER.info("%s/%s: %d điểm, %d khối", key, args.target, len(points), len(chunks))
        for c0, c1 in chunks:
            path = folder / f"{c0:%Y%m%dT%H}_{c1:%Y%m%dT%H}.parquet"
            if path.exists():
                continue
            frame = fetch_chunk(ee, dataset, points, c0, c1)
            frame.to_parquet(path, index=False)
            LOGGER.info("  %s: %d hàng", path.name, len(frame))


def combine(args: argparse.Namespace) -> None:
    if args.target == "stations":
        parts = []
        for key, dataset in DATASETS.items():
            files = sorted((RAW / key / "stations").glob("*.parquet"))
            if not files:
                continue
            frame = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True).drop_duplicates(["site", "time_start_utc"])
            parts.append(daily_totals(frame, dataset, permanent_only=not args.allow_provisional))
        if not parts:
            raise FileNotFoundError("Chưa có khối trích xuất nào cho trạm")
        out = pd.concat(parts, ignore_index=True)
        STATION_DAILY.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(STATION_DAILY, index=False)
        LOGGER.info("Ghi %s:\n%s", STATION_DAILY.relative_to(ROOT),
                    out.groupby("source")["date"].agg(["min", "max", "count"]).to_string())
        return
    for key in args.dataset:
        dataset = DATASETS[key]
        files = sorted((RAW / key / "grid").glob("*.parquet"))
        frame = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True).drop_duplicates(["site", "time_start_utc"])
        hourly = hourly_depth(frame, dataset)
        out = PROCESSED / "gee" / f"{key}_grid_hourly.parquet"
        out.parent.mkdir(parents=True, exist_ok=True)
        hourly.to_parquet(out, index=False)
        LOGGER.info("Ghi %s (%d ô, %d giờ)", out.relative_to(ROOT), hourly["site"].nunique(), hourly["time_start_utc"].nunique())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", help="Google Cloud project đã bật Earth Engine (bắt buộc khi tải)")
    parser.add_argument("--target", choices=["stations", "grid"], default="stations")
    parser.add_argument("--dataset", nargs="+", choices=sorted(DATASETS), default=["imerg", "gsmap"])
    parser.add_argument("--start", default="2015-01", help="Tháng đầu, YYYY-MM")
    parser.add_argument("--end", default="2025-09", help="Tháng cuối (bao gồm), YYYY-MM")
    parser.add_argument("--bbox", nargs=4, type=float, default=DEFAULT_BBOX, metavar=("S", "N", "W", "E"))
    parser.add_argument("--combine", action="store_true", help="Gộp các khối đã tải thay vì tải")
    parser.add_argument("--allow-provisional", action="store_true", help="Giữ ảnh provisional khi gộp ngày trạm")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if args.combine:
        combine(args)
        return
    if not args.project:
        parser.error("--project là bắt buộc khi tải từ Earth Engine")
    points = station_points() if args.target == "stations" else grid_points(tuple(args.bbox))
    extract(args, points)


if __name__ == "__main__":
    main()
