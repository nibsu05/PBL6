"""Lấy mưa tái phân tích và dự báo số lưu trữ tại vị trí trạm, gộp thành tổng ngày UTC.

Nguồn:
- ``era5_om``: Open-Meteo Historical Weather (mặc định ``best_match``), giống
  cách tạo nhãn hiện tại của đồ án.
- ``ecmwf_d{N}``, ``gfs_d{N}``: Open-Meteo Previous Runs, ``precipitation_previous_dayN``
  của ECMWF IFS 0,25° và GFS — dự báo phát hành sớm hơn khoảng N ngày.
  ``gfs_d5`` thấp hơn khoảng một nửa so với d1–d3 ở *mọi* quý (lỗi xử lý phía
  nguồn, không phải tín hiệu), nên bị loại khỏi bảng đối chiếu.

Open-Meteo ghi mưa giờ ở *cuối* khoảng tích lũy; dịch lùi 1 giờ trước khi cộng
theo ngày UTC để khớp ngày GSOD. Ngày thiếu giờ nào thì để NaN. Phản hồi thô
được lưu đệm trong ``data/raw_data/openmeteo_baselines`` để chạy lại không tốn
lượt gọi API (bản miễn phí: 10.000 lượt/ngày, chỉ phi thương mại, ghi nguồn CC BY 4.0).
"""

from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd

from src.station_registry import STATIONS, Station

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
PREVIOUS = "https://previous-runs-api.open-meteo.com/v1/forecast"
CACHE = ROOT / "data" / "raw_data" / "openmeteo_baselines"
OUT = ROOT / "data" / "processed" / "stations" / "openmeteo_daily.parquet"
NWP_MODELS = {"ecmwf": "ecmwf_ifs025", "gfs": "gfs_seamless"}
LEAD_DAYS = (1, 2, 3, 5)

LOGGER = logging.getLogger("fetch_openmeteo")


def get_json(url: str, params: dict, cache: Path) -> dict:
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    full = f"{url}?{urllib.parse.urlencode(params)}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(full, timeout=120) as resp:
                payload = json.loads(resp.read())
            if payload.get("error"):
                raise RuntimeError(payload.get("reason"))
            cache.write_text(json.dumps(payload), encoding="utf-8")
            time.sleep(0.5)
            return payload
        except (urllib.error.URLError, TimeoutError) as exc:
            LOGGER.warning("Lỗi %s (lần %d): %s", url, attempt + 1, exc)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Không lấy được {full}")


def hourly_series(payload: dict, column: str) -> pd.Series:
    """Mưa giờ, chỉ số là *đầu* khoảng tích lũy (Open-Meteo ghi ở cuối khoảng)."""
    hourly = payload["hourly"]
    start = pd.to_datetime(hourly["time"]) - pd.Timedelta(hours=1)
    return pd.Series(pd.to_numeric(pd.Series(hourly[column]), errors="coerce").to_numpy(), index=start)


def hourly_to_daily(series: pd.Series) -> pd.Series:
    """Tổng ngày UTC; ngày nào thiếu giờ thì NaN."""
    return series.resample("D").sum(min_count=24)


def fetch_station(station: Station, start: str, end: str, nwp_start: str) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    yearly = []
    for year in range(int(start[:4]), int(end[:4]) + 1):
        y0, y1 = max(start, f"{year}-01-01"), min(end, f"{year}-12-31")
        payload = get_json(ARCHIVE, {
            "latitude": station.lat, "longitude": station.lon, "start_date": y0, "end_date": y1,
            "hourly": "precipitation", "timezone": "GMT",
        }, CACHE / f"archive_{station.usaf}_{year}.json")
        yearly.append(hourly_series(payload, "precipitation"))
    # Ghép giờ của mọi năm trước khi cộng ngày: giờ 00 UTC ngày 1/1 thuộc ngày 31/12 năm trước.
    hourly = pd.concat(yearly).sort_index()
    hourly = hourly[~hourly.index.duplicated()]
    parts.append(hourly_to_daily(hourly).rename("precip_mm").to_frame().assign(source="era5_om"))
    for short, model in NWP_MODELS.items():
        variables = [f"precipitation_previous_day{d}" for d in LEAD_DAYS]
        payload = get_json(PREVIOUS, {
            "latitude": station.lat, "longitude": station.lon, "start_date": nwp_start, "end_date": end,
            "hourly": ",".join(variables), "models": model, "timezone": "GMT",
        }, CACHE / f"previous_{model}_{station.usaf}_{nwp_start}_{end}.json")
        for d, var in zip(LEAD_DAYS, variables):
            daily = hourly_to_daily(hourly_series(payload, var))
            parts.append(daily.rename("precip_mm").to_frame().assign(source=f"{short}_d{d}"))
    frame = pd.concat(parts).rename_axis("date").reset_index()
    frame["usaf"] = station.usaf
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default="2025-08-31")
    parser.add_argument("--nwp-start", default="2024-02-01", help="Previous Runs ECMWF 0,25° có từ khoảng 02/2024")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    CACHE.mkdir(parents=True, exist_ok=True)
    frames = []
    for station in STATIONS:
        LOGGER.info("Trạm %s", station.name)
        frames.append(fetch_station(station, args.start, args.end, args.nwp_start))
    data = pd.concat(frames, ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data.to_parquet(OUT, index=False)
    coverage = data.dropna().groupby("source")["date"].agg(["min", "max", "count"])
    LOGGER.info("Ghi %s:\n%s", OUT.relative_to(ROOT), coverage.to_string())


if __name__ == "__main__":
    main()
