"""Build the full hourly ERA5/Vrain handoff, retaining all missing time bins."""
from pathlib import Path
import argparse
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from build_station_forecast_data import weather_at_stations
from src.hourly_station_update import (BASE, OUT, PUBLIC, RAIN_BASE, VERSION,
    DATASET, ROLES, hourly_flags)
from src.station_forecast_data import (GROUPS, EXPERIMENTS, PHYSICAL_FEATURES,
    calendar_at_end, feature_names, label_names)
from src.station_archive_update import sha, write_json, combine_hourly


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse-weather", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    collection = json.loads((BASE / "era5_collection_progress.json").read_text(encoding="utf8"))
    if collection["state"] != "complete":
        raise ValueError("ERA5 collection has not completed")
    previous = json.loads((BASE / "protected_before.json").read_text(encoding="utf8"))
    for path in [RAIN_BASE / "rain_channels.npz", RAIN_BASE / "station_registry_private.csv"]:
        if sha(path) != previous[path.relative_to(ROOT).as_posix()]:
            raise ValueError("Gauge inputs changed after snapshot")
    registry = pd.read_csv(RAIN_BASE / "station_registry_private.csv")
    z = np.load(RAIN_BASE / "rain_channels.npz")
    if registry.canonical_id.tolist() != z["station_ids"].tolist():
        raise ValueError("Registry and rainfall station order differ")
    days = pd.DatetimeIndex(z["marked_day"])
    end = pd.date_range(days[0]-pd.Timedelta(hours=4), periods=len(days)*24,
                        freq="h", tz="Asia/Ho_Chi_Minh").tz_convert("UTC").as_unit("ns")
    start = end-pd.Timedelta(hours=1)
    last_weather = pd.Timestamp(collection["end_exclusive_utc"], tz="UTC")-pd.Timedelta(hours=1)
    available = start <= last_weather
    work = BASE / "full_weather"
    work.mkdir(exist_ok=True)
    weather, weather_meta = weather_at_stations(registry, start[available], work, args.reuse_weather)
    contract = dict(version=VERSION, resolution="1h", history_hours=24, horizon_hours=6,
        source_rain="Vrain, two API namespaces retained with provenance",
        source_weather="ECMWF/ERA5/HOURLY via Google Earth Engine",
        time_semantics="10:00 Vietnam is rainfall 09:00--10:00 UTC+7",
        hourly_weather="instantaneous ERA5 at period_start_utc; never future ERA5",
        weather_last_valid_utc=str(last_weather), gauge_last_period_end_utc=str(end[-1]),
        weather_release="GEE does not expose expver here; recent ERA5T/final status unverified",
        source_update_cutoff="fixed collection snapshot, not continuous realtime ingestion",
        spatial_method="strict bilinear at current station coordinates, native 0.25-degree nodes",
        spatial_missing_policy="all positive-weight corners required, no reweighting",
        regional_features=["ctx_tcwv", "ctx_ivt_mag", "cold_surge_dp_hpa", "dp_tonkin_south_hpa", "sst_region_c"],
        coordinate_history_verified=False, sensor_accuracy_certified=False,
        source_code={"0": "legacy API", "1": "modern API", "-1": "missing", "3": "conflict"},
        sample_rule="24 hourly X and 6 future y complete; same API source for the entire 30-hour window",
        sample_complete="technical completeness, including candidate stations with no train history",
        sample_ready_r1="sample_complete and at least one valid train sample at that station",
        sample_ready_r0="same conservative paired mask as R1; not a larger weather-only cohort",
        split={"train": "2021--2022", "cal": "2023", "dev": "2024",
               "reserved2025": "2025, models not scored", "external2026": "2026, source transition"},
        feature_groups=GROUPS, experiments=EXPERIMENTS, input_features=feature_names("1h"),
        static_features=["latitude", "longitude", "station_code"], labels=label_names("1h"),
        no_future_weather=True, no_temporal_interpolation=True, no_rain_imputation=True,
        no_model_training=True, no_model_evaluation=True, no_scaler_fitted=True,
        source_continuity_confirmed=False, operational_availability_proven=False,
        gauge_matrix_sha256=sha(RAIN_BASE / "rain_channels.npz"),
        weather_input_signature=weather_meta["input_signature"])
    write_json(PUBLIC / "data_contract.json", contract)
    full_path = OUT / DATASET
    temporary = full_path.with_suffix(".partial.parquet")
    writer = None
    records = []
    began = time.perf_counter()
    cal = calendar_at_end(end)
    for j, station in enumerate(registry.itertuples()):
        raw = z["raw"].reshape(2, -1, len(registry))[:, :, j]
        valid = z["valid"].reshape(2, -1, len(registry))[:, :, j]
        rain, codes, conflict = combine_hourly(raw[0], raw[1], valid[0], valid[1])
        physical = np.full((len(end), len(PHYSICAL_FEATURES)), np.nan, dtype="float32")
        physical[available] = weather[:, j]
        features = np.concatenate([physical, cal], axis=1)
        # PHYSICAL_FEATURES retain group order; calendar is explicitly named below.
        flags = hourly_flags(features, rain, codes, end)
        frame = pd.DataFrame(dict(station_id=station.canonical_id, resolution="1h",
            station_code=int(station.canonical_id[2:])-1,
            latitude=float(station.latitude), longitude=float(station.longitude),
            period_start_utc=start, period_end_utc=end,
            period_end_vn=end.tz_convert("Asia/Ho_Chi_Minh"), weather_last_time_utc=start,
            source_marked_day=np.repeat(days.values, 24),
            legacy_rain_raw_mm=raw[0], modern_rain_raw_mm=raw[1],
            legacy_rain_qc_mm=np.where(valid[0], raw[0], np.nan),
            modern_rain_qc_mm=np.where(valid[1], raw[1], np.nan),
            legacy_sum_flag=np.repeat(z["bad_daily_sum"][0, :, j], 24),
            modern_sum_flag=np.repeat(z["bad_daily_sum"][1, :, j], 24),
            legacy_requested=np.repeat(z["queried"][0], 24),
            modern_requested=np.repeat(z["queried"][1], 24),
            cross_channel_conflict=conflict, rain_mm=rain, gauge_source_code=codes,
            cross_channel_continuity_unverified=True,
            weather_timestamp_available=available))
        frame["rain_qc_code"] = np.where(np.isfinite(rain), 0, np.where(conflict, 3,
            np.where(frame.legacy_sum_flag | frame.modern_sum_flag, 2, 1))).astype("uint8")
        for k, name in enumerate(PHYSICAL_FEATURES):
            frame[name] = physical[:, k]
        for k, name in enumerate(["sin_hour", "cos_hour", "sin_doy", "cos_doy"]):
            frame[name] = cal[:, k]
        for name, values in flags.items():
            if name != "labels":
                frame[name] = values
        for k, name in enumerate(label_names("1h")):
            frame[name] = flags["labels"][:, k]
        table = pa.Table.from_pandas(frame, preserve_index=False)
        table = table.replace_schema_metadata({**(table.schema.metadata or {}),
            b"pbl6_contract": json.dumps(contract, ensure_ascii=False).encode("utf8")})
        if writer is None:
            writer = pq.ParquetWriter(temporary, table.schema, compression="zstd")
        writer.write_table(table)
        for role in ROLES:
            mask = frame.split.eq(role).to_numpy()
            records.append(dict(station_id=station.canonical_id, split=role,
                station_seen_train=flags["station_seen_train"],
                sample_complete=int((flags["sample_complete"] & mask).sum()),
                sample_ready=int((flags["sample_ready_r1"] & mask).sum()),
                ready_legacy=int((flags["sample_ready_r1"] & mask & (codes == 0)).sum()),
                ready_modern=int((flags["sample_ready_r1"] & mask & (codes == 1)).sum())))
        if j % 10 == 0 or j == len(registry)-1:
            print(json.dumps(dict(stage="write_stations", completed=j+1, total=len(registry),
                seconds=round(time.perf_counter()-began, 1))), flush=True)
    writer.close()
    temporary.replace(full_path)
    stats = pd.DataFrame(records)
    stats.to_csv(BASE / "station_sample_counts_private.csv", index=False)
    aggregate = stats.groupby("split", sort=False).agg(
        sample_complete=("sample_complete", "sum"), sample_ready=("sample_ready", "sum"),
        ready_legacy=("ready_legacy", "sum"), ready_modern=("ready_modern", "sum"))
    aggregate["stations_with_ready_samples"] = stats.groupby("split", sort=False).sample_ready.apply(lambda v: int((v > 0).sum()))
    aggregate.reset_index().to_csv(PUBLIC / "sample_counts.csv", index=False, lineterminator="\n")
    summary = dict(version=VERSION, status="built_not_yet_verified", dataset=DATASET,
        sha256=sha(full_path), bytes=full_path.stat().st_size, rows=len(end)*len(registry),
        candidate_stations=len(registry), stations_seen_train=int(stats.groupby("station_id").station_seen_train.first().sum()),
        weather_channels=44, weather_physical_channels=40, with_rain_channels=45,
        first_period_start_local=str(start[0].tz_convert("Asia/Ho_Chi_Minh")),
        last_rain_period_end_local=str(end[-1].tz_convert("Asia/Ho_Chi_Minh")),
        last_weather_state_utc=str(last_weather),
        last_complete_weather_row_end_local=str((last_weather+pd.Timedelta(hours=1)).tz_convert("Asia/Ho_Chi_Minh")),
        weather_unavailable_tail_rows=int((~available).sum()*len(registry)),
        no_model_training=True, no_model_evaluation=True, ready_counts=aggregate.to_dict("index"))
    write_json(PUBLIC / "dataset_summary.json", summary)
    write_json(BASE / "build_complete.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
