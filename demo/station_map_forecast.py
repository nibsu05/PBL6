"""Combine issued station products by exact issue time and preserve each period."""

import csv
from datetime import datetime, timedelta, timezone
import io
import math
from pathlib import Path

from demo.station_map_nowcast import REPLAY, nowcast_replay
from demo.station_map_status import available_forecasts, forecast_payload


ALIGNED = (Path(__file__).resolve().parents[1] / "data/operational/station_map_unified_2026_11_24"
           / "station_map_hourly_private.json")
PERIODS = tuple((f"h{h}", h, 1) for h in range(1, 7)) + tuple((f"d{d}", d, 24) for d in range(1, 4))
HOURLY_FIELDS = {"LightGBM_R": "predicted_mm", "BiLSTM_R": "bilstm_mm", "Persistence": "persistence_mm"}
DAILY_FIELDS = ("predicted_mm", "gfs_mm", "probability_ge50")


def at(value):
    time = datetime.fromisoformat(value)
    if time.tzinfo is None:
        raise ValueError("An issue time must include a time zone")
    return time.astimezone(timezone.utc)


def number(value):
    return value if type(value) in (float, int) and math.isfinite(value) else None


def collect_replays(authenticated):
    archive = None
    for path in (ALIGNED, REPLAY):
        try:
            archive = nowcast_replay(path, authenticated)
        except (OSError, ValueError, KeyError):
            continue
        break
    return archive or {"stations": [], "issues": []}


def combine_forecasts(daily, hourly, authenticated):
    daily_stations = {row["station_id"]: row for row in daily["stations"]}
    hourly_stations = {row["id"]: row for row in hourly["stations"]}
    common = sorted(daily_stations.keys() & hourly_stations.keys())
    stations = []
    for sid in sorted(daily_stations.keys() | hourly_stations.keys()):
        h = hourly_stations.get(sid)
        d = daily_stations.get(sid)
        stations.append(dict(station_id=sid, name=(h or {}).get("name") or sid,
                             latitude=d["latitude"] if d else h["lat"],
                             longitude=d["longitude"] if d else h["lon"],
                             hourly=h is not None, daily=d is not None))

    daily_by_time = {}
    for case in daily["snapshots"]:
        # The daily loader yields a verified live issuance before a historical one.
        daily_by_time.setdefault(at(case["issue_utc"]), case)
    hourly_by_time = {}
    for case in hourly["issues"]:
        timestamp = at(case["issue_time"])
        if timestamp + timedelta(hours=6) != at(case["valid_until"]):
            raise ValueError("Hourly replay has an inconsistent validity interval")
        if timestamp in hourly_by_time:
            raise ValueError("Duplicate hourly replay issue time")
        hourly_by_time[timestamp] = case

    result = []
    for when in sorted(daily_by_time.keys() | hourly_by_time.keys(), reverse=True):
        d, h = daily_by_time.get(when), hourly_by_time.get(when)
        id_ = d["id"] if d else "hour-" + when.strftime("%Y%m%dT%H%M%S")
        windows = []
        for lead, n, hours in PERIODS:
            start = when + timedelta(hours=(n - 1) * hours)
            end = start + timedelta(hours=hours)
            points = []
            mode = "missing"
            if hours == 1 and h is not None:
                for sid, sample in h["by_station"].items():
                    if sid not in hourly_stations:
                        raise ValueError("Hourly point is outside its roster")
                    series = sample["forecasts"]
                    point = {"station_id": sid}
                    for source, field in HOURLY_FIELDS.items():
                        values = series.get(source) or []
                        point[field] = number(values[n - 1]) if len(values) == 6 else None
                    if authenticated:
                        truth = sample.get("observed") or []
                        point["observed_mm"] = number(truth[n - 1]) if len(truth) == 6 else None
                    points.append(point)
                mode = "historical_replay"
            if hours == 24 and d is not None:
                window = next((item for item in d["windows"] if item["horizon"] == n), None)
                if window is not None:
                    if (at(window["start_utc"]), at(window["end_utc"])) != (start, end):
                        raise ValueError("Daily forecast is associated with the wrong start or end")
                    fields = (*DAILY_FIELDS, "observed_mm") if authenticated else DAILY_FIELDS
                    for sample in window["points"]:
                        if sample["station_id"] not in daily_stations:
                            raise ValueError("Daily point is outside its roster")
                        points.append({"station_id": sample["station_id"],
                                       **{name: number(sample.get(name)) for name in fields}})
                    mode = d["mode"]
            if len({point["station_id"] for point in points}) != len(points):
                raise ValueError("Duplicate station in a forecast period")
            windows.append(dict(lead=lead, horizon=n, hours=hours, start_utc=start.isoformat(),
                                end_utc=end.isoformat(), mode=mode, points=points,
                                has_truth=any(point.get("observed_mm") is not None for point in points)))
        result.append(dict(id=id_, issue_utc=when.isoformat(), mode=d["mode"] if d else "historical_replay",
                           label=d["label"] if d else "Phát lại giờ", gfs_init_utc=d.get("gfs_init_utc") if d else None,
                           windows=windows))
    return dict(schema_version=1, product="station_forecast", viewer="member" if authenticated else "guest",
                stations=stations, shared_stations=common, snapshots=result)


def station_forecasts(authenticated):
    try:
        daily = forecast_payload(available_forecasts(), authenticated)
    except FileNotFoundError:
        daily = {"stations": [], "snapshots": []}
    hourly = collect_replays(authenticated)
    return combine_forecasts(daily, hourly, authenticated)


def export_period(data, issue_id, lead, scope):
    period = next((p for p in PERIODS if p[0] == lead), None)
    case = next((s for s in data["snapshots"] if s["id"] == issue_id), None)
    if period is None or case is None or scope not in ("all", "common"):
        raise ValueError("Unknown forecast period")
    window = next(w for w in case["windows"] if w["lead"] == lead)
    if window["mode"] == "missing":
        raise ValueError("This forecast period is unavailable")
    fields = (*HOURLY_FIELDS.values(), "observed_mm") if period[2] == 1 else (*DAILY_FIELDS, "observed_mm")
    shared = set(data["shared_stations"])
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(("issue_utc", "start_utc", "end_utc", "period_hours", "station_id", *fields))
    for point in window["points"]:
        if scope == "all" or point["station_id"] in shared:
            writer.writerow((case["issue_utc"], window["start_utc"], window["end_utc"], window["hours"],
                             point["station_id"], *(point.get(name) for name in fields)))
    suffix = at(case["issue_utc"]).strftime("%Y%m%dT%H%M")
    return output.getvalue().encode("utf-8-sig"), f"pbl6-{suffix}-{lead}.csv"
