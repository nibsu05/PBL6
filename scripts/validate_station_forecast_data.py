"""Independently replay source values, windows, folds and native ERA5 samples."""
from pathlib import Path
from collections import Counter
import gzip
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT, ROOT / "scripts"):
    sys.path.insert(0, str(folder))

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.station_forecast_data import (PHYSICAL_FEATURES, SPECS, StationForecastData,
                                      feature_names, label_names)

BASE = ROOT / "data/operational/vrain_2026_11_09"
OUT = ROOT / "data/processed/station_v1"
PUBLIC = ROOT / "reports/station_data_handoff_2026_11_09"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def equal(a, b):
    np.testing.assert_allclose(a, b, rtol=1e-6, atol=2e-5, equal_nan=True)


def main():
    file = OUT / "PBL6_TRAM_GIO_NGAY_V1.parquet"
    summary = json.loads((OUT / "validation_summary.json").read_text(encoding="utf8"))
    assert digest(file) == summary["sha256"]
    pf = pq.ParquetFile(file)
    contract = json.loads(pf.schema_arrow.metadata[b"pbl6_contract"])
    assert contract["test2025_read"] is False
    assert not set(["precipitation", "era5_tp_mm", "gsmap_mm", "y_region_gc_mm"]) & set(pf.schema_arrow.names)
    registry = pd.read_csv(BASE / "handoff_v1/station_registry_private.csv", dtype={"legacy_id": str})
    z = np.load(BASE / "freeze_work/station_matrices.npz")
    raw = z["rain"].reshape(-1, 82)
    valid = z["valid"].reshape(-1, 82)
    aliases = dict(zip(registry.canonical_id, registry.legacy_id))
    source_pos = {sid: j for j, sid in enumerate(z["station_ids"])}
    target_weather = np.load(BASE / "station_forecast_work/weather_station_native.npy", mmap_mode="r")
    ordered = registry[registry.legacy_id.isin(source_pos)].sort_values("canonical_id").reset_index(drop=True)
    weather_pos = dict(zip(ordered.canonical_id, range(len(ordered))))
    weather_meta = json.loads((BASE / "station_forecast_work/weather_station_native.json").read_text())
    row_count, sample_count, station_count = Counter(), Counter(), Counter()
    checked = 0
    for group in range(pf.num_row_groups):
        f = pf.read_row_group(group).to_pandas()
        sid = f.station_id.iloc[0]; resolution = f.resolution.iloc[0]
        assert f.station_id.eq(sid).all() and f.resolution.eq(resolution).all()
        spec = SPECS[resolution]
        n = len(f); h = spec["history"]; horizon = spec["horizon"]
        end = pd.DatetimeIndex(f.period_end_utc)
        start = pd.DatetimeIndex(f.period_start_utc)
        assert not end.has_duplicates and end.is_monotonic_increasing
        assert (np.diff(end.as_unit('ns').asi8) == pd.Timedelta(hours=spec["hours"]).value).all()
        assert ((end-start) == pd.Timedelta(hours=spec["hours"])).all()
        assert (pd.DatetimeIndex(f.weather_last_time_utc) == end-pd.Timedelta(hours=1)).all()
        local = end.tz_convert("Asia/Ho_Chi_Minh")
        assert local.year.max() <= 2024
        assert (pd.DatetimeIndex(f.period_end_vn) == end).all()
        j = source_pos[aliases[sid]]
        expected_rain = np.where(valid[:, j], raw[:, j], np.nan)
        expected_raw = raw[:, j]
        expected_weather = target_weather[:, weather_pos[sid], :]
        if resolution == "24h":
            assert (local.hour == 19).all()
            expected_rain = expected_rain.reshape(-1, 24).sum(1)
            expected_raw = expected_raw.reshape(-1, 24).sum(1)
            expected_weather = expected_weather.reshape(-1, 24, len(PHYSICAL_FEATURES)).mean(1)
        equal(f.rain_mm, expected_rain)
        equal(f.rain_raw_mm, expected_raw)
        equal(f[PHYSICAL_FEATURES], expected_weather)
        assert not (f.rain_mm.dropna() < 0).any()
        assert f.loc[f.rain_qc_code.ne(0), "rain_mm"].isna().all()
        x = f[feature_names(resolution, use_rain=False)].to_numpy()
        current_complete = np.isfinite(x).all(1)
        assert np.array_equal(current_complete, f.weather_complete)
        y = f[label_names(resolution)].to_numpy()
        for k in range(1, horizon+1):
            equal(y[:-k, k-1], expected_rain[k:])
            assert np.isnan(y[-k:, k-1]).all()
        expected_split = np.full(n, "unused", dtype=object)
        target_stop = local + pd.Timedelta(hours=spec["hours"]*horizon)
        for fold, first, stop in [("train", 2021, 2023), ("cal", 2023, 2024), ("dev", 2024, 2025)]:
            ok = (local >= pd.Timestamp(f"{first}-01-01", tz="Asia/Ho_Chi_Minh")) & (target_stop <= pd.Timestamp(f"{stop}-01-01", tz="Asia/Ho_Chi_Minh"))
            expected_split[ok] = fold
        assert np.array_equal(expected_split, f.split.to_numpy())
        hist_weather = np.r_[np.zeros(h-1, bool), np.lib.stride_tricks.sliding_window_view(current_complete, h).all(1)]
        hist_rain = np.r_[np.zeros(h-1, bool), np.lib.stride_tricks.sliding_window_view(np.isfinite(expected_rain), h).all(1)]
        raw_r0 = hist_weather & np.isfinite(y).all(1) & (expected_split != "unused")
        raw_r1 = raw_r0 & hist_rain
        seen = bool((raw_r1 & (expected_split == "train")).any())
        assert f.station_seen_train.eq(seen).all()
        assert np.array_equal(f.sample_ready_r0, raw_r0 & seen)
        assert np.array_equal(f.sample_ready_r1, raw_r1 & seen)
        row_count[resolution] += n
        for fold in ("train", "cal", "dev"):
            count = int((f.sample_ready_r1 & f.split.eq(fold)).sum())
            sample_count[(resolution, fold)] += count
            station_count[(resolution, fold)] += int(count > 0)
        checked += 1
    assert checked == 164
    for resolution, report in summary["resolutions"].items():
        assert row_count[resolution] == report["rows"]
        for fold, count in report["samples_r1"].items():
            assert sample_count[(resolution, fold)] == count
            assert station_count[(resolution, fold)] == report["stations_r1"][fold]

    # Replay selected station-hour surface fields independently from native raw
    # units/coordinates, rather than merely comparing to the builder's cache.
    from extract_gee_era5 import era5_points
    points = era5_points(); nodes = points[points.site.str.startswith("e")].reset_index(drop=True)
    source_replays = 0
    for timestamp in ["2020-12-31 12:00", "2022-10-14 02:00", "2024-12-31 11:00"]:
        t = pd.Timestamp(timestamp)
        candidates = []
        for name in weather_meta["source_sha256"]:
            a, b = [pd.to_datetime(s, format="%Y%m%dT%H") for s in Path(name).stem.split("_")]
            if a <= t < b:
                candidates.append(ROOT / "data/raw_data/gee/era5/grid" / name)
        assert len(candidates) == 1
        source = candidates[0]
        assert digest(source) == weather_meta["source_sha256"][source.name]
        native = pd.read_parquet(source, filters=[("time_utc", "=", t)]).set_index("site")
        ti = int((t-pd.Timestamp("2020-12-31 12:00"))/pd.Timedelta(hours=1))
        for station_position in [0, 20, 40, 60, 81]:
            station = ordered.iloc[station_position]
            a = np.floor(station.latitude/.25)*.25
            b = np.floor(station.longitude/.25)*.25
            fy = (station.latitude-a)/.25; fx = (station.longitude-b)/.25
            corners = [(a, b, (1-fy)*(1-fx)), (a, b+.25, (1-fy)*fx),
                       (a+.25, b, fy*(1-fx)), (a+.25, b+.25, fy*fx)]
            for output, column, subtract, divisor in [("t2m_c", "temperature_2m", 273.15, 1),
                ("sp_hpa", "surface_pressure", 0, 100), ("u10", "u_component_of_wind_10m", 0, 1)]:
                value = sum(((native.loc[f"e{la:.2f}_{lo:.2f}", column]-subtract)/divisor)*w for la, lo, w in corners)
                np.testing.assert_allclose(target_weather[ti, station_position, PHYSICAL_FEATURES.index(output)], value, rtol=3e-5, atol=3e-5)
                source_replays += 1

    # Check original source clocks and depths in one raw response per year.
    raw_rain_replays = 0
    for day in ["2021-10-14", "2022-10-14", "2023-10-14", "2024-10-14"]:
        payload = json.loads(gzip.decompress((BASE / "download/raw" / day[:4] / f"{day}.json.gz").read_bytes()))
        row = next(r for r in payload["stats"] if r["timePoint"] == f"10:00 {day[8:10]}/{day[5:7]}")
        ti = int((pd.Timestamp(day+" 10:00")-pd.Timestamp("2020-12-31 20:00"))/pd.Timedelta(hours=1))
        for measurement in row["stations"]:
            value = np.nan if measurement["depth"] == "-" else float(measurement["depth"])
            equal(raw[ti, source_pos[measurement["id"]]], value)
            raw_rain_replays += 1

    # Exercise actual consumer windows in both tasks/folds, including whitelist.
    loader_samples = 0
    for resolution in SPECS:
        for fold in ("train", "cal", "dev"):
            ds = StationForecastData(file, resolution, fold, stations=["ST001", "ST041", "ST086"])
            if len(ds):
                for i in np.unique(np.linspace(0, len(ds)-1, 12).astype(int)):
                    sample = ds[int(i)]
                    assert sample["x"].shape == (SPECS[resolution]["history"], 45 if resolution == "1h" else 43)
                    assert sample["y"].shape == (SPECS[resolution]["horizon"],)
                    assert np.isfinite(sample["x"]).all() and np.isfinite(sample["y"]).all()
                    loader_samples += 1
    report = dict(status="passed", dataset_sha256=summary["sha256"],
        station_resolution_groups_checked=checked, all_rows_checked=sum(row_count.values()),
        all_ready_windows_checked=sum(sample_count.values()),
        native_surface_field_replays=source_replays, raw_rain_clock_replays=raw_rain_replays,
        loader_sample_replays=loader_samples, no_target_or_future_weather_in_X=True,
        no_missing_values_in_ready_windows=True, exact_daily_24_hour_sums=True,
        no_station_or_time_gap_crossing=True, whole_targets_within_time_folds=True,
        no_2025_vrain_read=True, no_2026_model_selection=True,
        caveat="Structural/merge checks do not certify instrument accuracy or operational data latency")
    for path in [OUT / "verification.json", PUBLIC / "verification.json"]:
        path.write_text(json.dumps(report, indent=2)+"\n", encoding="utf8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
