"""Append complete native ERA5 chunks; keep the prior source archive immutable."""
from pathlib import Path
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import numpy as np
import pandas as pd
import ee
from extract_gee_era5 import RAW, BANDS, era5_points, fetch_chunk
from extract_gee_precip import META_COLUMNS, time_chunks
from src.hourly_station_update import BASE
from src.station_archive_update import sha, write_json


def check(frame, points, start, stop):
    hours = pd.date_range(start, stop, freq="h", inclusive="left")
    if set(frame.columns) != {"time_utc", "site", *BANDS}:
        raise ValueError("Unexpected ERA5 chunk schema")
    if frame.duplicated(["time_utc", "site"]).any():
        raise ValueError("Duplicate ERA5 key")
    if len(frame) != len(hours)*len(points) or set(frame.site) != set(points.site):
        raise ValueError("Incomplete ERA5 node/time coverage")
    actual = pd.DatetimeIndex(sorted(frame.time_utc.unique()))
    if not actual.equals(hours):
        raise ValueError("Unexpected ERA5 timestamps")
    if not frame.groupby("time_utc").size().eq(len(points)).all():
        raise ValueError("Incomplete hourly node coverage")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    BASE.mkdir(parents=True, exist_ok=True)
    snapshot = BASE / "era5_source_before.json"
    if not snapshot.exists():
        write_json(snapshot, {p.name: sha(p) for p in sorted(RAW.glob("*.parquet"))})
    old = json.loads(snapshot.read_text(encoding="utf8"))
    for name, digest in old.items():
        if sha(RAW/name) != digest:
            raise ValueError("Historical ERA5 source changed")
    ee.Initialize(project=args.project)
    ee.data.setDeadline(120000)
    prior_progress = BASE / "era5_collection_progress.json"
    if prior_progress.exists():
        bounds = json.loads(prior_progress.read_text(encoding="utf8"))
        latest = pd.Timestamp(bounds["latest_source_utc"])
    else:
        collection = ee.ImageCollection("ECMWF/ERA5/HOURLY").filterDate("2026-10-01", "2026-11-18")
        latest = pd.Timestamp(collection.aggregate_max("system:time_start").getInfo(), unit="ms")
    # The gauge archive ends 2026-11-15 12UTC; its last weather state is 11UTC.
    stop = min(latest + pd.Timedelta(hours=1), pd.Timestamp("2026-11-15 12:00"))
    start = max(pd.to_datetime(Path(n).stem.split("_")[1], format="%Y%m%dT%H") for n in old)
    points = era5_points()
    chunks = time_chunks(start, stop, 1., len(points), len(META_COLUMNS)+len(BANDS))
    manifest_path = BASE / "era5_new_sources.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf8")) if manifest_path.exists() else {}
    def progress(state):
        write_json(BASE / "era5_collection_progress.json", dict(state=state,
            start_utc=str(start), end_exclusive_utc=str(stop), latest_source_utc=str(latest),
            expected_chunks=len(chunks), completed_chunks=len(manifest),
            updated_utc=pd.Timestamp.now(tz="UTC").isoformat()))
    progress("running")
    def job(a, b):
        name = f"{a:%Y%m%dT%H}_{b:%Y%m%dT%H}.parquet"
        path = RAW/name
        if name in manifest:
            if sha(path) != manifest[name]["sha256"]:
                raise ValueError("Resumed ERA5 checksum mismatch")
            return name, manifest[name]
        if path.exists():
            frame = pd.read_parquet(path)
        else:
            frame = fetch_chunk(ee, points, a, b)
            check(frame, points, a, b)
            temporary = path.with_suffix(".partial.parquet")
            frame.to_parquet(temporary, index=False)
            temporary.replace(path)
        check(frame, points, a, b)
        return name, dict(sha256=sha(path), rows=len(frame), bytes=path.stat().st_size,
                         first_utc=str(a), end_exclusive_utc=str(b))
    began = time.perf_counter()
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(job, a, b) for a, b in chunks]
        for future in as_completed(futures):
            name, record = future.result()
            manifest[name] = record
            write_json(manifest_path, manifest)
            progress("running")
            print(json.dumps(dict(chunk=name, completed=len(manifest), expected=len(chunks),
                                  elapsed_seconds=round(time.perf_counter()-began, 1))), flush=True)
    for name, digest in old.items():
        if sha(RAW/name) != digest:
            raise ValueError("Historical ERA5 changed during collection")
    progress("complete")


if __name__ == "__main__":
    main()
