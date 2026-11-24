"""Read the authorized Vrain web hourly report and preserve its source pages."""

from datetime import date
import math

from src.vrain_download import ORIGIN
from src.vrain_export_audit import identifier, inventory_from_groups


def json_response(response):
    response.raise_for_status()
    if response.status_code != 200 or "json" not in response.headers.get("Content-Type", "").lower():
        raise ValueError("Vrain did not return a JSON report")
    return response.json()


def fetch_station_inventory(session, timeout=(6, 15)):
    return json_response(session.get(ORIGIN + "/api/vrain/private/v2/stats/summary", timeout=timeout))


def current_modern_aliases(registry, groups, organization, group_id=29):
    """Accept a changed report ID only for a known UUID at its original coordinates."""
    if not isinstance(groups, list):
        raise ValueError("Unexpected authenticated inventory")
    selected = [row for group in groups if isinstance(group, dict) and group.get("groupOrgUuid") == organization
                for row in group.get("stats", []) if isinstance(row, dict) and str(row.get("groupId")) == str(group_id)]
    inventory = inventory_from_groups([{"stats": selected}])
    known = {str(row.modern_uuid): row for row in registry.itertuples()}
    aliases = {str(row.modern_id): row.canonical_id for row in known.values()}
    matched = set()
    for item in inventory:
        source_id = item["station_id"]
        original = known.get(item["station_uuid"])
        if original is None or (original.latitude, original.longitude) != (item["latitude"], item["longitude"]):
            if source_id in aliases:
                raise ValueError("A known Vrain report ID has different station metadata")
            continue
        canonical = original.canonical_id
        if canonical in matched or aliases.get(source_id, canonical) != canonical:
            raise ValueError("Ambiguous Vrain station alias")
        matched.add(canonical)
        aliases[source_id] = canonical
    return aliases


def rain_value(value):
    if value is None:
        return "-"
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("Invalid hourly rain depth")
    return value


def hourly_table(pages):
    """Adapt the paged layout to the existing time and missing-value checks."""
    first = pages[0]
    ids = [identifier(value, "report station ID") for value in first["ids"]]
    stations = first["stations"]
    if (len(set(ids)) != len(ids) or [identifier(s["id"], "station metadata ID") for s in stations] != ids):
        raise ValueError("Vrain report columns do not match station metadata")
    count = first["total"]
    if type(count) is not int or not 0 <= count <= 24:
        raise ValueError("Invalid number of rows for a one-day hourly report")
    totals = [0.] * len(ids)
    present = [False] * len(ids)
    rows = []
    for page in pages:
        if (page.get("interval", "_1h") != "_1h" or page.get("total", count) != count
                or page.get("offset", len(rows)) != len(rows)
                or (page.get("ids") and [str(v) for v in page["ids"]] != ids)):
            raise ValueError("Vrain hourly pages have inconsistent reporting metadata")
        sums = page["sums"]
        if not isinstance(sums, list) or len(sums) != len(ids):
            raise ValueError("Vrain page totals do not match its stations")
        totals = [total + (0. if value is None else rain_value(value)) for total, value in zip(totals, sums)]
        for row in page["rows"]:
            values = row["v"]
            if not isinstance(values, list) or len(values) != len(ids):
                raise ValueError("Vrain hourly row has an invalid station count")
            present = [seen or value is not None for seen, value in zip(present, values)]
            rows.append({"timePoint": row["t"], "ts": row.get("ts"),
                         "stations": [{"id": sid, "depth": rain_value(value)} for sid, value in zip(ids, values)]})
    if len(rows) != count or len({row["timePoint"] for row in rows}) != count:
        raise ValueError("Vrain hourly report has duplicate or missing page rows")
    closing = {"timePoint": "Tổng", "stations": [
        {"id": sid, "depth": total if has_value else "-"} for sid, total, has_value in zip(ids, totals, present)]}
    return {"stats": [closing, *rows]}


def fetch_station_hours(session, day, channel, organization, timeout=(6, 16)):
    """Fetch one reporting day from the current web routes within the user session."""
    day = date.fromisoformat(day).isoformat()
    params = {"from": day, "to": day}
    if channel == "modern":
        route = "/d/kttv/private/v1/organizations/details"
        headers = {"x-org-uuid": organization}
        params["i"] = "_1h"
    elif channel == "legacy":
        route = "/d/vrain/private/v1/groups/29/stats/details"
        headers = {}
    else:
        raise ValueError("Unknown Vrain report namespace")
    pages, raw, seen = [], [], set()
    for _ in range(24):
        response = session.get(ORIGIN + route, params=params, headers=headers, timeout=timeout)
        payload = json_response(response)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected Vrain hourly page")
        pages.append(payload)
        raw.append(response.content)
        cursor = payload.get("next")
        if not cursor:
            return hourly_table(pages), raw
        if not isinstance(cursor, str) or cursor in seen or not payload.get("rows"):
            raise ValueError("Invalid or repeated Vrain page cursor")
        seen.add(cursor)
        params["cursor"] = cursor
    raise ValueError("Vrain hourly report exceeded its page limit")
