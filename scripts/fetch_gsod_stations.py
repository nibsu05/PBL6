"""Tải mưa ngày NOAA GSOD cho các trạm synop Việt Nam và kiểm soát chất lượng.

Ngày GSOD tính theo UTC (00Z–24Z, tức 07h–07h giờ Việt Nam). Cờ PRCP:
D/F/G = đủ 24 giờ (4×6 h, 2×12 h, 1×24 h); I = trạm không báo mưa và không
ghi nhận hiện tượng mưa, coi là ngày khô; A/B/C/E = chỉ một phần ngày; H = báo 0
nhưng có hiện tượng mưa. Mặc định chỉ giữ D/F/G và I; ngày một phần bị loại vì
tổng mưa có thể thiếu.

Chạy:
    python scripts/fetch_gsod_stations.py --start-year 2015 --end-year 2025
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
import urllib.request

import numpy as np
import pandas as pd

from src.station_registry import STATIONS, Station

URL = "https://www.ncei.noaa.gov/data/global-summary-of-the-day/access/{year}/{sid}.csv"
RAW_DIR = ROOT / "data" / "raw_data" / "gsod"
OUT = ROOT / "data" / "processed" / "stations" / "gsod_daily.parquet"
REPORT = ROOT / "reports" / "station_benchmark" / "gsod_coverage.json"

COMPLETE_FLAGS = {"D", "F", "G"}
DRY_FLAGS = {"I"}
PARTIAL_FLAGS = {"A", "B", "C", "E"}
MIN_COVERAGE = 0.8          # tỷ lệ ngày dùng được tối thiểu trong một năm-trạm
MIN_WET_COMPLETE_DAYS = 10  # loại năm-trạm báo toàn 0 (như Nội Bài 2025)

LOGGER = logging.getLogger("fetch_gsod")


def download(station: Station, year: int, refresh: bool) -> Path | None:
    path = RAW_DIR / f"{station.gsod_id}_{year}.csv"
    if path.exists() and not refresh:
        return path
    url = URL.format(year=year, sid=station.gsod_id)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                path.write_bytes(resp.read())
            return path
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                LOGGER.warning("Không có file %s năm %s", station.name, year)
                return None
            LOGGER.warning("HTTP %s khi tải %s (lần %d)", exc.code, url, attempt + 1)
        except urllib.error.URLError as exc:
            LOGGER.warning("Lỗi mạng %s (lần %d): %s", url, attempt + 1, exc)
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Không tải được {url}")


def classify(flag: str, raw: float) -> str:
    if not np.isfinite(raw):
        return "missing"
    if flag in COMPLETE_FLAGS:
        return "complete"
    if flag in DRY_FLAGS:
        return "assumed_dry"
    if flag in PARTIAL_FLAGS:
        return "partial"
    return "incomplete"


def load_station_year(path: Path, station: Station) -> pd.DataFrame:
    raw = pd.read_csv(path, usecols=["DATE", "PRCP", "PRCP_ATTRIBUTES"], dtype={"PRCP_ATTRIBUTES": str})
    prcp = raw["PRCP"].where(raw["PRCP"] < 99.0)
    frame = pd.DataFrame({
        "date": pd.to_datetime(raw["DATE"]),
        "usaf": station.usaf,
        "precip_mm_raw": prcp * 25.4,
        "flag": raw["PRCP_ATTRIBUTES"].fillna("").str.strip(),
    })
    frame["quality"] = [classify(f, v) for f, v in zip(frame["flag"], frame["precip_mm_raw"])]
    keep = frame["quality"].isin(["complete", "assumed_dry"])
    frame["precip_mm"] = np.where(keep, np.where(frame["quality"] == "assumed_dry", 0.0, frame["precip_mm_raw"]), np.nan)
    return frame


def year_coverage(frame: pd.DataFrame, data_end: pd.Timestamp) -> dict[str, float | int | bool]:
    year = int(frame["date"].dt.year.iloc[0])
    span_end = min(pd.Timestamp(f"{year}-12-31"), data_end)
    n_days = (span_end - pd.Timestamp(f"{year}-01-01")).days + 1
    counts = frame["quality"].value_counts().to_dict()
    usable_days = counts.get("complete", 0) + counts.get("assumed_dry", 0)
    wet_complete = int(((frame["quality"] == "complete") & (frame["precip_mm"] > 0)).sum())
    return {
        "year": year, "calendar_days": int(n_days), "usable_days": int(usable_days),
        **{f"n_{q}": int(counts.get(q, 0)) for q in ("complete", "assumed_dry", "partial", "incomplete", "missing")},
        "wet_complete_days": wet_complete,
        "total_mm": float(frame["precip_mm"].sum()),
        "usable": bool(usable_days >= MIN_COVERAGE * n_days and wet_complete >= MIN_WET_COMPLETE_DAYS),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start-year", type=int, default=2015)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--refresh", action="store_true", help="Tải lại kể cả khi đã có file")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    frames: list[pd.DataFrame] = []
    for station in STATIONS:
        for year in range(args.start_year, args.end_year + 1):
            path = download(station, year, args.refresh)
            if path is not None:
                frames.append(load_station_year(path, station))
    data = pd.concat(frames, ignore_index=True)
    data_end = data["date"].max()

    coverage: dict[str, list[dict]] = {}
    usable_keys: set[tuple[str, int]] = set()
    for (usaf, year), grp in data.groupby(["usaf", data["date"].dt.year]):
        cov = year_coverage(grp, data_end)
        coverage.setdefault(usaf, []).append(cov)
        if cov["usable"]:
            usable_keys.add((usaf, int(year)))
    data["usable_year"] = [(u, d.year) in usable_keys for u, d in zip(data["usaf"], data["date"])]
    meta = pd.DataFrame([vars(s) for s in STATIONS])
    data = data.merge(meta[["usaf", "name", "province", "region", "lat", "lon", "elev_m"]], on="usaf", how="left")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    data.to_parquet(OUT, index=False)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "source": "NOAA GSOD", "day_definition": "UTC 00Z-24Z",
        "kept_flags": sorted(COMPLETE_FLAGS | DRY_FLAGS), "dropped_flags": sorted(PARTIAL_FLAGS | {"H"}),
        "usable_rule": f"usable_days >= {MIN_COVERAGE} * calendar_days and wet_complete_days >= {MIN_WET_COMPLETE_DAYS}",
        "data_end": str(data_end.date()),
        "stations": {u: {"name": meta.set_index("usaf").loc[u, "name"], "years": v} for u, v in coverage.items()},
    }
    REPORT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    table = (data[data["usable_year"]].groupby("name")
             .agg(years=("date", lambda d: d.dt.year.nunique()), days=("precip_mm", "count"),
                  mean_annual_mm=("precip_mm", lambda s: s.mean() * 365.25),
                  days_ge_50=("precip_mm", lambda s: int((s >= 50).sum()))))
    LOGGER.info("Ghi %s (%d hàng). Năm-trạm dùng được:\n%s", OUT.relative_to(ROOT), len(data), table.round(0).to_string())
    dropped = sorted({(meta.set_index("usaf").loc[u, "name"], c["year"]) for u, v in coverage.items() for c in v if not c["usable"]})
    if dropped:
        LOGGER.info("Năm-trạm bị loại: %s", dropped)


if __name__ == "__main__":
    main()
