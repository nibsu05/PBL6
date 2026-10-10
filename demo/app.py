"""One-hour, dependency-free operational rainfall demo for Da Nang.

Run: python demo/app.py --refresh-once
     python demo/app.py --port 8765

The public API serves ECMWF IFS forecast output via Open-Meteo. This is not a
rain-gauge observation and does not execute the repository's ML checkpoints.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
INDEX = Path(__file__).with_name("index.html")
CACHE = ROOT / ".cache" / "demo_forecast.json"
ARCHIVE = ROOT / "data" / "operational" / "forecast_snapshots"
HISTORY_CACHE = ROOT / ".cache" / "demo_history.json"
LATITUDE = 16.0544
LONGITUDE = 108.2022
MODEL = "ecmwf_ifs"
MODEL_NAME = "ECMWF IFS HRES 9 km qua Open-Meteo"
FRESH_FOR = timedelta(minutes=30)
MAX_STALE = timedelta(hours=12)
REFRESH_EVERY = timedelta(minutes=30)
HISTORY_REFRESH_EVERY = timedelta(hours=24)
HISTORY_MAX_STALE = timedelta(days=3)
VIETNAM_TIME = timezone(timedelta(hours=7))
LOG = logging.getLogger("rain_demo")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def forecast_url() -> str:
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "precipitation,temperature_2m,relative_humidity_2m,wind_speed_10m",
        "forecast_hours": 80,
        "timezone": "GMT",
        "models": MODEL,
    }
    return "https://api.open-meteo.com/v1/forecast?" + urlencode(params)


def fetch_forecast() -> dict:
    request = Request(forecast_url(), headers={"User-Agent": "PBL6-DaNang-Demo/1.0"})
    with urlopen(request, timeout=15) as response:
        payload = json.load(response)

    hourly = payload.get("hourly", {})
    columns = (
        "time", "precipitation", "temperature_2m",
        "relative_humidity_2m", "wind_speed_10m",
    )
    if any(name not in hourly for name in columns):
        raise ValueError("Open-Meteo thiếu một hoặc nhiều biến dự báo bắt buộc")
    count = len(hourly["time"])
    if count < 73 or any(len(hourly[name]) != count for name in columns):
        raise ValueError("Chuỗi giờ trả về thiếu hoặc có độ dài không khớp")

    hours = []
    for index in range(count):
        values = {name: hourly[name][index] for name in columns[1:]}
        if any(value is None for value in values.values()):
            continue
        valid_at = datetime.fromisoformat(hourly["time"][index]).replace(tzinfo=timezone.utc)
        rain = float(values["precipitation"])
        if rain < 0:
            raise ValueError("Open-Meteo trả về lượng mưa âm")
        hours.append({
            "valid_at": utc_iso(valid_at),
            "precipitation_mm": rain,
            "temperature_c": float(values["temperature_2m"]),
            "relative_humidity_pct": float(values["relative_humidity_2m"]),
            "wind_speed_kmh": float(values["wind_speed_10m"]),
        })
    if len(hours) < 73:
        raise ValueError("Không đủ giờ dự báo hữu hạn để tạo biểu đồ 72 giờ")

    return {
        "fetched_at": utc_iso(utc_now()),
        "source": "Open-Meteo Forecast API",
        "model": MODEL,
        "model_name": MODEL_NAME,
        "requested_location": {"latitude": LATITUDE, "longitude": LONGITUDE},
        "grid_location": {
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
        },
        "hours": hours,
    }


def fetch_history() -> dict:
    """Get 30 completed local days of model-based historical estimates."""
    end = (utc_now().astimezone(VIETNAM_TIME).date() - timedelta(days=1))
    start = end - timedelta(days=29)
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": start.isoformat(),
        # Include 00:00 of the following day: its precipitation belongs to
        # the final completed local day (Open-Meteo uses preceding-hour sums).
        "end_date": (end + timedelta(days=1)).isoformat(),
        "hourly": "precipitation,temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m",
        "timezone": "Asia/Ho_Chi_Minh",
        "models": MODEL,
    }
    url = "https://archive-api.open-meteo.com/v1/archive?" + urlencode(params)
    request = Request(url, headers={"User-Agent": "PBL6-DaNang-Demo/1.0"})
    with urlopen(request, timeout=25) as response:
        payload = json.load(response)

    hourly = payload.get("hourly", {})
    columns = (
        "time", "precipitation", "temperature_2m",
        "relative_humidity_2m", "surface_pressure", "wind_speed_10m",
    )
    expected = 31 * 24
    if any(name not in hourly or len(hourly[name]) != expected for name in columns):
        raise ValueError("Dữ liệu lịch sử thiếu giờ hoặc biến bắt buộc")

    rows = []
    buckets = {
        (start + timedelta(days=offset)).isoformat(): {
            "precipitation_mm": 0.0, "rain_hours": 0,
            "temperature_c": 0.0, "relative_humidity_pct": 0.0,
            "surface_pressure_hpa": 0.0, "wind_speed_kmh": 0.0,
            "instant_hours": 0,
        }
        for offset in range(30)
    }
    for index in range(expected):
        values = {name: hourly[name][index] for name in columns[1:]}
        if any(value is None for value in values.values()):
            continue
        local_time = datetime.fromisoformat(hourly["time"][index]).replace(tzinfo=VIETNAM_TIME)
        rain = float(values["precipitation"])
        if rain < 0:
            raise ValueError("Lượng mưa lịch sử âm")
        row = {
            "valid_at": utc_iso(local_time),
            "precipitation_mm": rain,
            "temperature_c": float(values["temperature_2m"]),
            "relative_humidity_pct": float(values["relative_humidity_2m"]),
            "surface_pressure_hpa": float(values["surface_pressure"]),
            "wind_speed_kmh": float(values["wind_speed_10m"]),
        }
        rain_day = (local_time - timedelta(microseconds=1)).date().isoformat()
        if rain_day in buckets:
            bucket = buckets[rain_day]
            bucket["precipitation_mm"] += rain
            bucket["rain_hours"] += 1
            for name in ("temperature_c", "relative_humidity_pct", "surface_pressure_hpa", "wind_speed_kmh"):
                bucket[name] += row[name]
            bucket["instant_hours"] += 1
            row["date_local"] = rain_day
            rows.append(row)

    if len(rows) != 30 * 24 or any(
        bucket["rain_hours"] != 24 or bucket["instant_hours"] != 24
        for bucket in buckets.values()
    ):
        raise ValueError("Dữ liệu lịch sử thiếu giờ để cộng đúng ngày địa phương")
    daily = []
    for day, bucket in buckets.items():
        daily.append({
            "date_local": day,
            "precipitation_mm": round(bucket["precipitation_mm"], 3),
            **{
                name: round(bucket[name] / 24, 3)
                for name in ("temperature_c", "relative_humidity_pct", "surface_pressure_hpa", "wind_speed_kmh")
            },
        })
    return {
        "fetched_at": utc_iso(utc_now()),
        "source": "Open-Meteo Historical Weather API",
        "model": MODEL,
        "model_name": "ECMWF IFS historical estimates",
        "start_date_local": start.isoformat(),
        "end_date_local": end.isoformat(),
        "grid_location": {
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
        },
        "rows": rows,
        "daily": daily,
    }


class ForecastStore:
    def __init__(self, cache_path: Path = CACHE):
        self.cache_path = cache_path
        self.lock = threading.Lock()
        self.refresh_lock = threading.Lock()
        self.cached = self._load_cache()
        self.last_attempt_at: str | None = None
        self.last_success_at: str | None = self.cached["fetched_at"] if self.cached else None
        self.next_scheduled_at: str | None = None
        self.last_error: str | None = None
        self.last_snapshot_at: str | None = None
        self.last_storage_error: str | None = None

    def _load_cache(self) -> dict | None:
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if payload.get("model") == MODEL and payload.get("hours"):
                parse_utc(payload["fetched_at"])
                return payload
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return None

    def _save_cache(self, payload: dict) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.cache_path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temp.replace(self.cache_path)

    @staticmethod
    def _archive_snapshot(payload: dict) -> None:
        fetched = parse_utc(payload["fetched_at"])
        folder = ARCHIVE / fetched.strftime("%Y") / fetched.strftime("%m") / fetched.strftime("%d")
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / (fetched.strftime("%Y%m%dT%H%M%SZ") + ".json")
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temp.replace(target)

    def _collection_status_unlocked(self, now: datetime) -> dict:
        fetched = parse_utc(self.cached["fetched_at"]) if self.cached else None
        return {
            "interval_minutes": int(REFRESH_EVERY.total_seconds() / 60),
            "last_attempt_at": self.last_attempt_at,
            "last_success_at": self.last_success_at,
            "next_scheduled_at": self.next_scheduled_at,
            "last_error": self.last_error,
            "last_snapshot_at": self.last_snapshot_at,
            "last_storage_error": self.last_storage_error,
            "cache_age_minutes": round((now - fetched).total_seconds() / 60, 1) if fetched else None,
            "cached_hours": len(self.cached["hours"]) if self.cached else 0,
        }

    def collection_status(self) -> dict:
        with self.lock:
            return self._collection_status_unlocked(utc_now())

    def set_next_scheduled(self, value: datetime) -> None:
        with self.lock:
            self.next_scheduled_at = utc_iso(value)

    def refresh(self) -> bool:
        """Fetch on a background schedule, independent of page views."""
        with self.refresh_lock:
            with self.lock:
                self.last_attempt_at = utc_iso(utc_now())
            try:
                fresh = fetch_forecast()
                with self.lock:
                    self.cached = fresh
                    self.last_success_at = fresh["fetched_at"]
                    self.last_error = None
                    self.last_storage_error = None
                    try:
                        self._save_cache(fresh)
                    except OSError as exc:
                        LOG.warning("Không lưu được cache: %s", exc)
                        self.last_storage_error = "Không lưu được cache hiển thị"
                    try:
                        self._archive_snapshot(fresh)
                        self.last_snapshot_at = fresh["fetched_at"]
                    except OSError as exc:
                        LOG.warning("Không lưu được snapshot: %s", exc)
                        self.last_storage_error = "Không lưu được snapshot lịch sử"
                LOG.info("Đã thu thập %d giờ dự báo lúc %s", len(fresh["hours"]), fresh["fetched_at"])
                return True
            except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
                LOG.warning("Không tải được dự báo mới: %s", exc)
                with self.lock:
                    self.last_error = "Không tải được dữ liệu mới từ Open-Meteo"
                return False

    def _project(self, payload: dict, status: str, now: datetime) -> dict:
        future = [hour for hour in payload["hours"] if parse_utc(hour["valid_at"]) > now][:72]
        if not future:
            raise RuntimeError("Bản dự báo đã hết giờ hiệu lực")

        result = {key: value for key, value in payload.items() if key != "hours"}
        result.update({
            "status": status,
            "served_at": utc_iso(now),
            "hours": future,
            "available_hours": len(future),
            "totals_mm": {
                str(span): round(sum(hour["precipitation_mm"] for hour in future[:span]), 2)
                for span in (6, 24, 72)
            },
            "notice": "Nguồn tạm thời không khả dụng; đang hiển thị bản đã lưu." if status == "stale" and self.last_error else None,
            "collection": self._collection_status_unlocked(now),
            "measurement_note": "Lượng mưa dự báo trên ô lưới; không phải số đo trạm mưa.",
        })
        return result

    def get(self) -> dict:
        with self.lock:
            cached = self.cached
            now = utc_now()
            age = now - parse_utc(cached["fetched_at"]) if cached else None
            if not cached or age is None or age >= MAX_STALE:
                raise RuntimeError("Chưa có dự báo còn hiệu lực; backend sẽ tự thử thu thập lại")
            status = "stale" if age >= FRESH_FOR or self.last_error else "cached"
            return self._project(cached, status, now)


class HistoricalStore:
    def __init__(self, cache_path: Path = HISTORY_CACHE):
        self.cache_path = cache_path
        self.lock = threading.Lock()
        self.cached = self._load_cache()
        self.last_attempt_at: str | None = None
        self.last_success_at: str | None = self.cached["fetched_at"] if self.cached else None
        self.next_scheduled_at: str | None = None
        self.last_error: str | None = None

    def _load_cache(self) -> dict | None:
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if payload.get("model") == MODEL and payload.get("rows") and payload.get("daily"):
                parse_utc(payload["fetched_at"])
                return payload
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return None

    def set_next_scheduled(self, value: datetime) -> None:
        with self.lock:
            self.next_scheduled_at = utc_iso(value)

    def refresh(self) -> bool:
        with self.lock:
            self.last_attempt_at = utc_iso(utc_now())
        try:
            fresh = fetch_history()
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.cache_path.with_suffix(".tmp")
            temp.write_text(json.dumps(fresh, ensure_ascii=False), encoding="utf-8")
            temp.replace(self.cache_path)
            with self.lock:
                self.cached = fresh
                self.last_success_at = fresh["fetched_at"]
                self.last_error = None
            LOG.info("Đã thu thập %d giờ lịch sử tới %s", len(fresh["rows"]), fresh["end_date_local"])
            return True
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            LOG.warning("Không tải được dữ liệu lịch sử: %s", exc)
            with self.lock:
                self.last_error = "Không tải được dữ liệu lịch sử mới"
            return False

    def get(self, days: int) -> dict:
        if days not in (7, 30):
            raise ValueError("Chỉ hỗ trợ 7 hoặc 30 ngày")
        with self.lock:
            cached = self.cached
            now = utc_now()
            if not cached or now - parse_utc(cached["fetched_at"]) >= HISTORY_MAX_STALE:
                raise RuntimeError("Chưa có dữ liệu lịch sử còn phù hợp")
            end = datetime.fromisoformat(cached["end_date_local"]).date()
            first = (end - timedelta(days=days - 1)).isoformat()
            rows = [row for row in cached["rows"] if row["date_local"] >= first]
            daily = [day for day in cached["daily"] if day["date_local"] >= first]
            return {
                "source": cached["source"],
                "model": cached["model"],
                "model_name": cached["model_name"],
                "fetched_at": cached["fetched_at"],
                "end_date_local": cached["end_date_local"],
                "start_date_local": first,
                "grid_location": cached["grid_location"],
                "days": days,
                "rows": rows,
                "daily": daily,
                "status": "stale" if self.last_error or now - parse_utc(cached["fetched_at"]) >= HISTORY_REFRESH_EVERY else "cached",
                "last_attempt_at": self.last_attempt_at,
                "next_scheduled_at": self.next_scheduled_at,
                "notice": "Dữ liệu lịch sử mới chưa tải được; đang dùng bản đã lưu." if self.last_error else None,
                "measurement_note": "Ước tính lịch sử theo mô hình ECMWF IFS; không phải số đo trạm.",
            }


STORE = ForecastStore()
HISTORY = HistoricalStore()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, content_type: str, filename: str | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            self._send(200, INDEX.read_bytes(), "text/html; charset=utf-8")
        elif url.path == "/api/forecast":
            try:
                force = parse_qs(url.query).get("refresh", ["0"])[0] == "1"
                if force:
                    STORE.refresh()
                result = STORE.get()
                self._send(200, json.dumps(result, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
            except RuntimeError as exc:
                self._send(503, json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
        elif url.path == "/api/collection":
            self._send(200, json.dumps(STORE.collection_status(), ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
        elif url.path == "/api/history":
            try:
                days = int(parse_qs(url.query).get("days", ["7"])[0])
                result = HISTORY.get(days)
                self._send(200, json.dumps(result, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
            except ValueError as exc:
                self._send(400, json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
            except RuntimeError as exc:
                self._send(503, json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
        elif url.path == "/api/forecast.csv":
            try:
                result = STORE.get()
                output = io.StringIO(newline="")
                writer = csv.writer(output)
                writer.writerow(("valid_at_utc", "precipitation_mm", "temperature_c", "relative_humidity_pct", "wind_speed_kmh"))
                for hour in result["hours"]:
                    writer.writerow((hour["valid_at"], hour["precipitation_mm"], hour["temperature_c"], hour["relative_humidity_pct"], hour["wind_speed_kmh"]))
                filename = "danang_ecmwf_forecast_" + result["fetched_at"][:10] + ".csv"
                self._send(200, ("\ufeff" + output.getvalue()).encode("utf-8"), "text/csv; charset=utf-8", filename)
            except RuntimeError as exc:
                self._send(503, str(exc).encode("utf-8"), "text/plain; charset=utf-8")
        elif url.path == "/api/health":
            self._send(200, b'{"status":"ok"}', "application/json; charset=utf-8")
        else:
            self._send(404, b"Not found", "text/plain; charset=utf-8")


def refresh_loop(stop: threading.Event, store: ForecastStore | HistoricalStore, interval: timedelta) -> None:
    """Update each data source even when nobody has the website open."""
    while not stop.is_set():
        success = store.refresh()
        next_interval = interval if success else min(interval, timedelta(hours=1))
        store.set_next_scheduled(utc_now() + next_interval)
        stop.wait(next_interval.total_seconds())


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo dự báo mưa Đà Nẵng không cần VRain")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--refresh-once", action="store_true", help="Tải một lần, in tóm tắt rồi thoát")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if args.refresh_once:
        STORE.refresh()
        result = STORE.get()
        print(json.dumps({key: result[key] for key in ("status", "fetched_at", "model_name", "available_hours", "totals_mm")}, ensure_ascii=False, indent=2))
        return
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    stop = threading.Event()
    STORE.set_next_scheduled(utc_now())
    HISTORY.set_next_scheduled(utc_now())
    collectors = [
        threading.Thread(target=refresh_loop, args=(stop, STORE, REFRESH_EVERY), daemon=True, name="forecast-collector"),
        threading.Thread(target=refresh_loop, args=(stop, HISTORY, HISTORY_REFRESH_EVERY), daemon=True, name="history-collector"),
    ]
    for collector in collectors:
        collector.start()
    LOG.info("Demo đang chạy: http://%s:%s", args.host, args.port)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()


if __name__ == "__main__":
    main()
