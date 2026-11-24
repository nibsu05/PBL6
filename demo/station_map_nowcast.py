"""Serving the frozen hourly replay without exposing observations to visitors."""

import json
from pathlib import Path


REPLAY = (Path(__file__).resolve().parents[1] / "data/operational/station_nowcast_2026_11_24"
          / "station_nowcast_replay_private.json")


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
