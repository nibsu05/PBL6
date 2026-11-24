"""Build ONE private Parquet with hourly/daily station data and sample flags.

Only Vrain source years 2021--2024 and past ERA5 predictors are read. No network,
model fitting, 2025 Vrain, regional labels or 2026 source concatenation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import warnings
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT, ROOT / "scripts"):
    sys.path.insert(0, str(folder))

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from build_dataset_v2 import era5_node_features, node_context, FEATURES
from extract_gee_era5 import BANDS, era5_points
from src.dataset_v2 import bilinear_weights, to_cube
from src.station_forecast_data import (ALL_FEATURES, GROUPS, EXPERIMENTS, PHYSICAL_FEATURES,
    SPECS, calendar_at_end, feature_names, label_names, sample_flags, strict_bilinear, utc_intervals)

BASE = ROOT / "data/operational/vrain_2026_11_09"
OUT = ROOT / "data/processed/station_v1"


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def source_files(start, end):
    files = []
    for path in sorted((ROOT / "data/raw_data/gee/era5/grid").glob("*.parquet")):
        a, b = [pd.to_datetime(x, format="%Y%m%dT%H") for x in path.stem.split("_")]
        if a <= end and b > start:
            files.append(path)
    if not files:
        raise FileNotFoundError("Native ERA5 node chunks unavailable")
    return files


def weather_at_stations(registry, start_utc, work, reuse=False):
    """Spatial interpolation from 4 actual 0.25-degree nodes, no R93 detour."""
    hours = start_utc.tz_localize(None).as_unit("ns")
    points = era5_points()
    nodes = points[points.site.str.startswith("e")].reset_index(drop=True)
    idx, weights = bilinear_weights(registry.latitude.to_numpy(), registry.longitude.to_numpy(),
                                    nodes.lat.to_numpy(), nodes.lon.to_numpy())
    files = source_files(hours[0], hours[-1])
    source_manifest = {p.name: sha256(p) for p in files}
    signature = hashlib.sha256(json.dumps(dict(source=source_manifest,
        station_coordinates=registry[["canonical_id", "latitude", "longitude"]].to_dict("records"),
        start=str(hours[0]), stop=str(hours[-1]), version="station_strict_bilinear_v1"),
        sort_keys=True).encode()).hexdigest()
    cache = work / "weather_station_native.npy"
    meta = work / "weather_station_native.json"
    if reuse and cache.exists() and meta.exists():
        previous = json.loads(meta.read_text(encoding="utf8"))
        if previous["input_signature"] == signature and previous["sha256"] == sha256(cache):
            return np.load(cache, mmap_mode="r"), previous
        raise ValueError("Weather cache signature/checksum mismatch")
    shape = (len(hours), len(registry), len(PHYSICAL_FEATURES))
    sink = np.lib.format.open_memmap(cache, mode="w+", dtype="float32", shape=shape)
    sink[:] = np.nan
    covered = np.zeros(len(hours), bool)
    pos = {s: k for k, s in enumerate(points.site)}
    sea = np.flatnonzero(nodes.lat.between(15.5, 16.5) & nodes.lon.between(108.75, 109.5))
    used_columns = ["time_utc", "site"] + [b for b in BANDS if b != "total_precipitation"]
    for fi, path in enumerate(files):
        frame = pd.read_parquet(path, columns=used_columns,
            filters=[("time_utc", ">=", hours[0]), ("time_utc", "<=", hours[-1])])
        if frame.empty:
            continue
        if frame.duplicated(["time_utc", "site"]).any():
            raise ValueError("Duplicate native ERA5 node/time")
        t = pd.DatetimeIndex(sorted(frame.time_utc.unique())).as_unit("ns")
        ti = hours.get_indexer(t)
        if (ti < 0).any() or covered[ti].any():
            raise ValueError("Native ERA5 chunks overlap")
        # Precipitation is explicitly not read. The shared transform's unused
        # rain output is NaN; all selected atmospheric outputs use time t only.
        frame["total_precipitation"] = np.nan
        raw = to_cube(frame, "time_utc", t, points.site.tolist(), list(BANDS))
        native = raw[:, :len(nodes)]
        derived, names = era5_node_features(np.concatenate([native, native[-1:]], axis=0))
        context = np.stack([node_context(derived[..., names.index("tcwv")], nodes.lat.to_numpy(), nodes.lon.to_numpy()),
                            node_context(derived[..., names.index("ivt_mag")], nodes.lat.to_numpy(), nodes.lon.to_numpy())], -1)
        derived = np.concatenate([derived, context], -1)
        names += ["ctx_tcwv", "ctx_ivt_mag"]
        local_names = [name for name in PHYSICAL_FEATURES if name in names]
        selected = strict_bilinear(derived[..., [names.index(n) for n in local_names]], idx, weights)
        mslp = raw[..., BANDS.index("mean_sea_level_pressure")] / 100
        sst = raw[:, :len(nodes), BANDS.index("sea_surface_temperature")] - 273.15
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            regional = {
                "cold_surge_dp_hpa": mslp[:, pos["syn_hanoi"]] - mslp[:, pos["e16.00_108.25"]],
                "dp_tonkin_south_hpa": mslp[:, pos["syn_tonkin"]] - mslp[:, pos["syn_south"]],
                "sst_region_c": np.nanmean(sst[:, sea], axis=1),
            }
        block = np.empty((len(t), len(registry), len(PHYSICAL_FEATURES)), dtype="float32")
        for k, name in enumerate(PHYSICAL_FEATURES):
            block[:, :, k] = selected[:, :, local_names.index(name)] if name in local_names else regional[name][:, None]
        sink[ti] = block
        covered[ti] = True
        if fi % 40 == 0 or fi == len(files)-1:
            print(f"ERA5 chunks {fi+1}/{len(files)}; covered hours {covered.sum()}/{len(hours)}", flush=True)
    if not covered.all():
        raise ValueError(f"Missing native ERA5 timestamps: {(~covered).sum()}")
    sink.flush()
    metadata = dict(input_signature=signature, sha256=sha256(cache), shape=list(shape),
        features=PHYSICAL_FEATURES, native_grid_degrees=.25, source="ECMWF/ERA5/HOURLY via GEE",
        spatial_method="strict_bilinear_at_station_coordinates", contributing_corners=4,
        source_sha256=source_manifest, interpolated_station_count=len(registry),
        max_weight_sum_error=float(np.abs(weights.sum(1)-1).max()),
        temporal_interpolation=False, time_alignment="instantaneous ERA5 at rain interval start",
        node_indices=idx.tolist(), node_weights=weights.tolist(),
        missing_hour_feature_cells=int((~np.isfinite(sink)).sum()))
    write_json(meta, metadata)
    return sink, metadata


def make_frame(row, resolution, start, end, raw, rain, qc, physical):
    frame = pd.DataFrame({"station_id": str(row.canonical_id), "station_name": str(row.legacy_name),
        "resolution": resolution, "period_start_utc": start, "period_end_utc": end,
        "period_end_vn": end.tz_convert("Asia/Ho_Chi_Minh"),
        "weather_last_time_utc": end-pd.Timedelta(hours=1),
        "latitude": float(row.latitude), "longitude": float(row.longitude),
        "rain_raw_mm": raw, "rain_mm": rain, "rain_qc_code": qc.astype("uint8")})
    for k, name in enumerate(PHYSICAL_FEATURES):
        frame[name] = physical[:, k].astype("float32")
    cal = calendar_at_end(end)
    for k, name in enumerate(["sin_hour", "cos_hour", "sin_doy", "cos_doy"]):
        frame[name] = cal[:, k] if resolution == "1h" or k >= 2 else np.full(len(end), np.nan, dtype="float32")
    selected = feature_names(resolution, use_rain=False)
    flags = sample_flags(frame[selected].to_numpy(), rain, end, resolution)
    for name in ["weather_complete", "split", "station_seen_train", "sample_ready_r0", "sample_ready_r1"]:
        frame[name] = flags[name]
    for other in ("1h", "24h"):
        for k, name in enumerate(label_names(other)):
            frame[name] = flags["labels"][:, k] if other == resolution else np.full(len(end), np.nan, dtype="float32")
    return frame


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse-weather", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    work = BASE / "station_forecast_work"
    work.mkdir(exist_ok=True)
    z = np.load(BASE / "freeze_work/station_matrices.npz", allow_pickle=False)
    registry = pd.read_csv(BASE / "handoff_v1/station_registry_private.csv", dtype={"legacy_id": str})
    order = {sid: i for i, sid in enumerate(z["station_ids"])}
    history_registry = registry[registry.legacy_id.isin(order)].copy().sort_values("canonical_id").reset_index(drop=True)
    if len(history_registry) != 82 or history_registry.legacy_id.nunique() != 82:
        raise ValueError("Source stations must map one-to-one to the canonical registry")
    start, end = utc_intervals(z["clock_end_naive"])
    if end.year.max() >= 2025:
        raise ValueError("Reserved Vrain year must not be opened")
    weather, weather_meta = weather_at_stations(history_registry, start, work, args.reuse_weather)
    units = {name: unit for name, unit, *_ in FEATURES if name in ALL_FEATURES}
    contract = {
        "version": "station_v1", "created_utc": datetime.now(timezone.utc).isoformat(),
        "time_semantics": "clock 10:00 = rainfall 09:00--10:00 in Asia/Ho_Chi_Minh (UTC+7)",
        "time_confirmation": "user explicit confirmation 2026-11-09; provider UI mm",
        "rain_unit": "mm per represented interval", "source_channel": "legacy vrain",
        "hourly_weather": "instantaneous native ERA5 at period_start_utc, not period_end",
        "daily_anchor_local": "19:00 previous day to 19:00 marked day",
        "daily_weather": "arithmetic mean of all 24 start-of-hour states; any contributing NaN remains NaN",
        "calendar": "sin/cos local interval-end hour and day-of-year, denominator 24/365.25",
        "spatial": "strict bilinear native 0.25-degree ERA5 at each station; context and SST intentionally shared/regional",
        "interpolation_missing_policy": "all positive-weight corners required; no missing-node reweighting",
        "feature_groups": GROUPS, "experiments": EXPERIMENTS, "feature_units": units,
        "specs": SPECS, "static_features": ["latitude", "longitude", "station_code"],
        "rain_qc_codes": {"0": "numeric nonnegative; passed available structural/sum checks",
                          "1": "missing source hour, or incomplete daily total", "2": "source station-day sum discrepancy"},
        "label_names": {r: label_names(r) for r in SPECS},
        "sample_rule": "full E7 history and all future labels finite, station has R1-ready train samples",
        "common_mask": "sample_ready_r1 for all E/model/R comparisons; never filter history rows before windowing",
        "split": {"train": "whole target within local 2021-01-01 to 2023-01-01",
                  "cal": "whole target within local 2023-01-01 to 2024-01-01",
                  "dev": "whole target within local 2024-01-01 to 2025-01-01; not final test"},
        "unavailable_features": ["station altitude", "future atmospheric forecasts"],
        "not_operational_availability_proof": "ERA5 is retrospective; Vrain/report latency not established",
        "no_hidden_imputation": True, "no_scaler_fitted": True, "no_model_training": True,
        "test2025_read": False, "recent2026_merged": False,
        "candidate_registry_private": registry.astype(object).where(pd.notna(registry), None).to_dict("records"),
        "source_matrix_sha256": sha256(BASE / "freeze_work/station_matrices.npz"),
        "weather_input_signature": weather_meta["input_signature"],
    }
    target = OUT / "PBL6_TRAM_GIO_NGAY_V1.parquet"
    partial = target.with_suffix(".partial.parquet")
    records = []
    rows_by_resolution = Counter()
    raw_rain = z["rain"].reshape(-1, 82)
    valid = z["valid"].reshape(-1, 82)
    bad = np.repeat(z["bad_daily_sum"], 24, axis=0)
    writer = None
    try:
        for station_position, row in history_registry.iterrows():
            j = order[row.legacy_id]
            raw = raw_rain[:, j]
            rain = np.where(valid[:, j], raw, np.nan).astype("float32")
            qc = np.where(bad[:, j], 2, np.where(np.isfinite(raw), 0, 1)).astype("uint8")
            physical = weather[:, station_position, :]
            daily_raw = raw.reshape(-1, 24).sum(1)
            daily_rain = rain.reshape(-1, 24).sum(1)
            daily_qc = np.where(bad[:, j].reshape(-1, 24).any(1), 2,
                                np.where(np.isfinite(daily_rain), 0, 1)).astype("uint8")
            daily_physical = physical.reshape(-1, 24, len(PHYSICAL_FEATURES)).mean(1)
            frames = [make_frame(row, "1h", start, end, raw, rain, qc, physical),
                      make_frame(row, "24h", start[::24], end[23::24], daily_raw, daily_rain, daily_qc, daily_physical)]
            for frame in frames:
                resolution = frame.resolution.iloc[0]
                table = pa.Table.from_pandas(frame, preserve_index=False)
                if writer is None:
                    metadata = dict(table.schema.metadata or {})
                    metadata[b"pbl6_contract"] = json.dumps(contract, ensure_ascii=False, allow_nan=False).encode()
                    table = table.replace_schema_metadata(metadata)
                    dictionary = ["station_id", "station_name", "resolution", "split", "latitude", "longitude",
                                  "rain_qc_code", "rain_mm", "rain_raw_mm"] + label_names("1h") + label_names("24h")
                    writer = pq.ParquetWriter(partial, table.schema, compression="zstd", compression_level=5,
                        use_dictionary=dictionary, use_byte_stream_split=ALL_FEATURES, write_statistics=True)
                writer.write_table(table.cast(writer.schema), row_group_size=40000)
                rows_by_resolution[resolution] += len(frame)
                record = dict(station_id=row.canonical_id, resolution=resolution,
                    weather_missing_rows=int((~frame.weather_complete).sum()),
                    rain_valid_rows=int(frame.rain_mm.notna().sum()),
                    seen_train=bool(frame.station_seen_train.iloc[0]))
                for r in (0, 1):
                    for fold in ("train", "cal", "dev"):
                        record[f"r{r}_{fold}"] = int((frame[f"sample_ready_r{r}"] & frame.split.eq(fold)).sum())
                records.append(record)
            if station_position % 15 == 0 or station_position == len(history_registry)-1:
                print(f"Merged stations {station_position+1}/{len(history_registry)}", flush=True)
        stats = pd.DataFrame(records)
        aggregate = {}
        for resolution in SPECS:
            selected = stats[stats.resolution.eq(resolution)]
            aggregate[resolution] = {"source_stations": len(selected), "rows": rows_by_resolution[resolution],
                "stations_with_train_samples": int(selected.seen_train.sum()),
                "weather_missing_rows": int(selected.weather_missing_rows.sum()),
                "rain_valid_rows": int(selected.rain_valid_rows.sum()),
                "samples_r1": {f: int(selected[f"r1_{f}"].sum()) for f in ("train", "cal", "dev")},
                "stations_r1": {f: int((selected[f"r1_{f}"] > 0).sum()) for f in ("train", "cal", "dev")},
                "samples_r0_weather_only": {f: int(selected[f"r0_{f}"].sum()) for f in ("train", "cal", "dev")}}
        summary = dict(version="station_v1", dataset=target.name, candidate_stations=len(registry),
            historical_stations=len(history_registry), modern_only_without_legacy_history=4,
            interval_start_local=str(start[0].tz_convert("Asia/Ho_Chi_Minh")),
            first_interval_end_local=str(end[0].tz_convert("Asia/Ho_Chi_Minh")),
            last_interval_end_local=str(end[-1].tz_convert("Asia/Ho_Chi_Minh")),
            source_marked_dates="2021-01-01 through 2024-12-31",
            flagged_station_days=int(z["bad_daily_sum"].sum()), weather_channels_hourly=44,
            weather_channels_daily=42, past_rain_channel_optional=1, resolutions=aggregate,
            spatial_method="native_0.25_degree_strict_bilinear_at_station", all_history_stations_bracketed=True,
            merged=True, no_missing_values_in_ready_windows=True, test2025_read=False,
            recent2026_merged=False, station_model_training_performed=False)
        writer.add_key_value_metadata({"pbl6_summary": json.dumps(summary, ensure_ascii=False)})
        writer.close(); writer = None
        partial.replace(target)
    finally:
        if writer is not None:
            writer.close()
    stats.to_csv(work / "station_sample_counts_private.csv", index=False)
    summary.update(bytes=target.stat().st_size, sha256=sha256(target))
    write_json(OUT / "validation_summary.json", summary)
    public = ROOT / "reports/station_data_handoff_2026_11_09"
    public.mkdir(parents=True, exist_ok=True)
    write_json(public / "dataset_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=True, indent=2), flush=True)


if __name__ == "__main__":
    main()
