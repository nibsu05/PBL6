"""Resumable small GFS forecast-field extraction for the station pilot.

Never downloads whole global files. Only fixed 2021--2024 00UTC cycles; private
coordinates and per-date values stay outside Git. Weekday cadence is fixed
before labels/results, not selected for observed rainfall.
"""
from pathlib import Path
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
import sys
import time
from threading import Lock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import requests
import eccodes as ec

from src.gfs_station import (RAIN_LEADS, MET_LEADS, MET_FIELDS, choose_records, issue_contract,
    parse_index, range_groups, regular_grid_weights, sample_field, rainfall_windows)

BASE = ROOT / "data/operational/gfs_station_pilot_2026_11_10"
BUCKET = "https://noaa-gfs-bdp-pds.s3.amazonaws.com/"
# The bundled Windows ecCodes definition parser uses shared native state.
# Parallelize HTTP only, never ecCodes message creation/decoding/release.
DECODE_LOCK = Lock()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save_json(path, value):
    tmp = path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(value, indent=2)+"\n", encoding="utf8")
    tmp.replace(path)


def get_index(session, day, lead):
    folder = BASE / "indexes" / day
    folder.mkdir(parents=True, exist_ok=True)
    cached = folder / f"f{lead:03}.json"
    if cached.exists():
        saved = json.loads(cached.read_text())
        if sha(saved["text"].encode()) != saved["sha256"]:
            raise ValueError("Cached index SHA mismatch")
        return saved
    filename = f"gfs.t00z.pgrb2.0p25.f{lead:03}"
    for layout in ("atmos/", ""):
        url = BUCKET+"gfs."+day+"/00/"+layout+filename
        response = session.get(url+".idx", timeout=(15, 40))
        if response.status_code == 404:
            continue
        response.raise_for_status()
        if not response.text.startswith("1:"):
            raise ValueError("Unexpected GFS index response")
        saved = dict(url=url, text=response.text, sha256=sha(response.text.encode()))
        save_json(cached, saved)
        return saved
    raise ValueError("GFS index unavailable in both historical layouts")


def range_bytes(session, url, first, last):
    if last-first > 8_000_000:
        raise ValueError("Refuse excessive range")
    response = session.get(url, headers={"Range": f"bytes={first}-{last}"},
                           timeout=(15, 70), stream=True)
    try:
        if response.status_code != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {first}-{last}/"):
            raise ValueError(f"HTTP server did not honor exact byte range: {response.status_code}")
        data = response.content
        if len(data) != last-first+1:
            raise ValueError("Incomplete GRIB byte range")
        return data, response.headers.get("Last-Modified")
    finally:
        response.close()


def decode(data, name, day, lead, indices, weights):
    if data[:4] != b"GRIB" or data[-4:] != b"7777":
        raise ValueError("GRIB framing invalid")
    g = ec.codes_new_from_message(data)
    try:
        keys = ["shortName", "units", "stepType", "startStep", "endStep", "dataDate", "dataTime",
                "validityDate", "validityTime", "Ni", "Nj", "gridType", "iScansNegatively",
                "jScansPositively", "latitudeOfFirstGridPointInDegrees", "longitudeOfFirstGridPointInDegrees",
                "decimalScaleFactor", "binaryScaleFactor", "generatingProcessIdentifier"]
        meta = {key: ec.codes_get(g, key) for key in keys}
        if meta["Ni"] != 1440 or meta["Nj"] != 721 or meta["gridType"] != "regular_ll" or meta["iScansNegatively"] or meta["jScansPositively"]:
            raise ValueError("Unexpected GFS geometry")
        if meta["latitudeOfFirstGridPointInDegrees"] != 90 or meta["longitudeOfFirstGridPointInDegrees"] != 0:
            raise ValueError("Unexpected GFS grid origin")
        if int(meta["dataDate"]) != int(day) or meta["dataTime"] != 0 or meta["endStep"] != lead:
            raise ValueError("Forecast initialization/lead mismatch")
        expected = pd.Timestamp(day)+pd.Timedelta(hours=lead)
        if meta["validityDate"] != int(expected.strftime("%Y%m%d")) or meta["validityTime"] != expected.hour*100:
            raise ValueError("Forecast valid time mismatch")
        if name == "rain_cumulative":
            if meta["shortName"] != "tp" or meta["units"] != "kg m**-2" or meta["stepType"] != "accum" or meta["startStep"] != 0:
                raise ValueError("Expected total precipitation from initialization, in mm")
        elif meta["stepType"] != "instant":
            raise ValueError("Meteorological covariate must be a forecast instantaneous state")
        values = ec.codes_get_values(g)
        if ec.codes_get(g, "numberOfMissing"):
            values[values == ec.codes_get(g, "missingValue")] = np.nan
        sampled = sample_field(values, indices, weights)
        expected_units={"rain_cumulative":"kg m**-2", "t850_k":"K", "rh850":"%",
                        "u850":"m s**-1", "v850":"m s**-1", "pwat":"kg m**-2"}
        if meta["units"] != expected_units[name]:
            raise ValueError(f"Forecast unit changed for {name}: {meta['units']}")
        if not np.isfinite(sampled).all():
            raise ValueError("Missing selected GFS station corners")
        meta["message_sha256"] = sha(data)
        meta["packing_quantum"] = float(2.**meta["binaryScaleFactor"] / 10.**meta["decimalScaleFactor"])
        return sampled, meta
    finally:
        ec.codes_release(g)


def collect_day(day, registry, indices, weights, signature):
    init, issue = issue_contract(pd.Timestamp(day).strftime("%Y-%m-%d"))
    path = BASE / "days" / (day+".npz")
    manifest = path.with_suffix(".json")
    if path.exists() and manifest.exists():
        record = json.loads(manifest.read_text())
        if record["station_signature"] != signature or record["sha256"] != sha(path.read_bytes()):
            raise ValueError("Day cache signature/checksum mismatch")
        return record
    with requests.Session() as session:
        session.headers["User-Agent"] = "PBL6-research-station-pilot/1.0"
        rain = np.full((4, len(registry)), np.nan, "float32")
        met = np.full((3, len(registry), len(MET_FIELDS)), np.nan, "float32")
        quantums = np.zeros(4)
        messages = []; transferred = 0
        for lead in sorted(RAIN_LEADS+MET_LEADS):
            saved = get_index(session, day, lead)
            chosen = choose_records(parse_index(saved["text"]), lead)
            for group in range_groups(chosen):
                first, last = group[0][1].start, group[-1][1].stop
                data, last_modified = range_bytes(session, saved["url"], first, last)
                transferred += len(data)
                for name, record in group:
                    message = data[record.start-first:record.stop-first+1]
                    with DECODE_LOCK:
                        sampled, metadata = decode(message, name, day, lead, indices, weights)
                    metadata.update(name=name, source_url=saved["url"], range=[record.start, record.stop],
                                    source_last_modified=last_modified, index_sha256=saved["sha256"])
                    messages.append(metadata)
                    if name == "rain_cumulative":
                        k = RAIN_LEADS.index(lead); rain[k] = sampled
                        quantums[k] = metadata["packing_quantum"]
                    else:
                        met[MET_LEADS.index(lead), :, list(MET_FIELDS).index(name)] = sampled
        daily, clipped = rainfall_windows(rain, quantums)
        tmp = path.with_suffix(".tmp.npz")
        np.savez_compressed(tmp, station_ids=registry.canonical_id.to_numpy(str), cumulative_mm=rain,
                            rain_day_mm=daily, met=met, met_names=np.asarray(list(MET_FIELDS)),
                            packing_quantums=quantums, negative_rounding_clipped=clipped)
        tmp.replace(path)
        record = dict(day=day, init_utc=str(init), issue_utc=str(issue), station_count=len(registry),
            station_signature=signature, sha256=sha(path.read_bytes()), messages=messages,
            transferred_bytes=transferred, rounding_corrections=int(clipped.sum()),
            operational_release_delay_assumed_hours=8, margin_from_init_to_issue_hours=12,
            actual_historical_release_availability_proven=False)
        save_json(manifest, record)
        return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--cadence-days", type=int, default=7)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.cadence_days < 1 or not 1 <= args.workers <= 8:
        raise ValueError("Invalid collection configuration")
    BASE.mkdir(parents=True, exist_ok=True); (BASE / "days").mkdir(exist_ok=True)
    registry = pd.read_csv(ROOT / "data/operational/vrain_2026_11_09/handoff_v1/station_registry_private.csv")
    registry = registry[registry.legacy_id.notna()].sort_values("canonical_id").reset_index(drop=True)
    signature = sha((registry[["canonical_id", "latitude", "longitude"]].to_json(orient="records", double_precision=15)
                     + json.dumps(MET_FIELDS) + str(RAIN_LEADS) + str(MET_LEADS)).encode())
    registry.to_csv(BASE / "registry_private.csv", index=False)
    indices, weights = regular_grid_weights(registry.latitude.to_numpy(), registry.longitude.to_numpy())
    dates = pd.date_range("2021-01-08", "2024-12-28", freq=f"{args.cadence_days}D").strftime("%Y%m%d").tolist()
    if args.limit:
        dates = dates[:args.limit]
    started = time.monotonic(); results = {}; errors = {}
    def progress(state):
        value = dict(state=state, pid=os.getpid(), updated_utc=datetime.now(timezone.utc).isoformat(),
            planned_issues=len(dates), completed_issues=len(results), failed_issues=len(errors),
            cadence_days=args.cadence_days, transferred_bytes=sum(r["transferred_bytes"] for r in results.values()),
            elapsed_seconds=round(time.monotonic()-started, 1), errors=errors, test2025_read=False)
        save_json(BASE / "progress.json", value)
        return value
    progress("collecting")
    def retry(day):
        for attempt in range(4):
            try:
                return collect_day(day, registry, indices, weights, signature)
            except Exception as exc:
                if attempt == 3:
                    raise
                time.sleep(min(2**attempt, 4))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        tasks = {pool.submit(retry, day): day for day in dates}
        for future in as_completed(tasks):
            day = tasks[future]
            try:
                results[day] = future.result()
            except Exception as exc:
                errors[day] = f"{type(exc).__name__}: {str(exc)[:200]}"
            value = progress("collecting")
            if (len(results)+len(errors)) % 5 == 0 or errors:
                print(json.dumps({k:v for k,v in value.items() if k != "errors"}), flush=True)
    save_json(BASE / f"collection_manifest_cadence{args.cadence_days}.json",
              dict(planned_dates=dates, completed_dates=sorted(results), errors=errors,
                   note="Forecast index/GRIB metadata verified; no holdout observations read"))
    value = progress("complete" if not errors else "incomplete")
    print(json.dumps(value), flush=True)
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
