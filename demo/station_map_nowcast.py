"""Serve hourly replay and recorded forecasts, with observations for members."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

from demo.station_map_live import read_optional, timestamp


REPLAY = (Path(__file__).resolve().parents[1] / "data/operational/station_nowcast_2026_11_24"
          / "station_nowcast_replay_private.json")
HOURLY = REPLAY.parents[1] / "station_map_web/hourly"
ISSUE_DELAY = timedelta(minutes=15)


def hourly_display(state):
    return (read_optional(state / "display.json") or {}).get("enabled") is True


def hourly_index(folder, now):
    index = read_optional(folder / "issuance.json")
    if not index or index.get("schema_version") != 1 or index.get("status") != "recorded":
        return None
    try:
        origin = timestamp(index["issue_utc"])
        recorded = timestamp(index["recorded_utc"])
        received = timestamp(index["received_utc"])
        expected, available = index["stations_expected"], index["stations"]
        if type(expected) is not int or type(available) is not int or not 0 < available <= expected:
            return None
        if not origin <= received <= recorded <= now or recorded >= origin + ISSUE_DELAY:
            return None
        if (origin.minute or origin.second or origin.microsecond
                or timestamp(index["truth_due_utc"]) != origin + timedelta(hours=6)
                or folder.name != origin.strftime("%Y%m%dT%H%M%SZ")):
            return None
    except (KeyError, TypeError, ValueError):
        return None
    return index


def hourly_truth(folder, index, now):
    data = read_optional(folder / "verification_private.json")
    if data and data.get("forecast_sha256") == index.get("forecast_sha256"):
        try:
            if (data["issue_utc"] == index["issue_utc"]
                    and timestamp(index["truth_due_utc"]) <= timestamp(data["verified_utc"]) <= now
                    and type(data.get("observed_cells")) is int
                    and isinstance(data["by_station"], dict)):
                return data
        except (KeyError, TypeError, ValueError):
            pass
    return None


def recent_hourly(state, now=None):
    now = now or datetime.now(timezone.utc)
    first = (now - timedelta(days=8)).strftime("%Y%m%dT%H%M%SZ")
    return [(p, index) for p in sorted((state / "issuances").glob("*"), reverse=True)
            if p.name >= first and (index := hourly_index(p, now))]


def hourly_status(state, now):
    records = recent_hourly(state, now)
    verified = next((truth for folder, index in records if (truth := hourly_truth(folder, index, now))), None)
    last = records[0][1] if records else None
    fields = ("issue_utc", "recorded_utc", "received_utc", "stations", "stations_expected", "truth_due_utc")
    return dict(schedule=read_optional(state / "schedule.json"), latest=read_optional(state / "latest.json"),
                display_enabled=hourly_display(state), recent_issues=len(records),
                last_recorded={field: last[field] for field in fields} if last else None,
                last_verified={k: verified[k] for k in ("issue_utc", "verified_utc", "observed_cells")} if verified else None)


def live_hourly(state, authenticated, now=None):
    if not hourly_display(state):
        return {"stations": [], "issues": []}
    now = now or datetime.now(timezone.utc)
    stations, issues = {}, []
    for folder, index in recent_hourly(state, now):
        try:
            raw = (folder / "forecast_private.json").read_bytes()
            if hashlib.sha256(raw).hexdigest() != index.get("forecast_sha256"):
                continue
            data = json.loads(raw)
            if (data["schema_version"] != 1 or data["issue_time"] != index["issue_utc"]
                    or data["valid_until"] != index["truth_due_utc"]):
                continue
            roster = {s["id"]: s for s in data["stations"]}
            if len(roster) != len(data["stations"]) or not set(data["by_station"]) <= roster.keys():
                continue
            if not data["by_station"] or len(data["by_station"]) != index["stations"]:
                continue
            truth = hourly_truth(folder, index, now) if authenticated else None
            observed = (truth or {}).get("by_station", {})
            rows = {sid: dict(forecasts=row["forecasts"], **({"observed": observed.get(sid)} if authenticated else {}))
                    for sid, row in data["by_station"].items()}
        except (OSError, KeyError, TypeError, ValueError):
            continue
        for sid, station in roster.items():
            stations.setdefault(sid, station)
        issues.append(dict(issue_time=data["issue_time"], valid_until=data["valid_until"], by_station=rows,
                           recorded_utc=index["recorded_utc"], mode="prospective"))
    return dict(stations=list(stations.values()), issues=issues)


def nowcast_replay(path: Path, authenticated: bool) -> dict:
    archive = json.loads(path.read_text(encoding="utf-8"))
    if (archive.get("schema_version"), archive.get("mode"), archive.get("lead_hours")) != (
        1, "historical_replay", [1, 2, 3, 4, 5, 6]
    ):
        raise ValueError("Unknown hourly replay format")
    result = {name: archive[name] for name in ("mode", "time_zone", "unit", "lead_hours", "source",
                                               "default_method", "methods", "stations")}
    result["issues"] = [
        dict(issue_time=issue["issue_time"], valid_until=issue["valid_until"],
             by_station={
                 sid: ({"forecasts": row["forecasts"], "observed": row["observed"]} if authenticated
                       else {"forecasts": row["forecasts"]})
                 for sid, row in issue["by_station"].items()})
        for issue in archive["issues"]
    ]
    return result
