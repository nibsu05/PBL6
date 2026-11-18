"""Independently replay hourly clocks, labels, source selection and ERA5 fields."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from src.hourly_station_update import BASE, OUT, PUBLIC, RAIN_BASE, DATASET, ROLES, HourlyStationData
from src.station_forecast_data import PHYSICAL_FEATURES, feature_names, label_names, StationForecastData
from src.station_archive_update import sha, write_json
from extract_gee_era5 import RAW, BANDS, era5_points, fetch_chunk


def equal(a, b, tolerance=0):
    if np.asarray(a).dtype.kind in "mM" or np.asarray(b).dtype.kind in "mM":
        np.testing.assert_array_equal(a, b)
        return
    np.testing.assert_allclose(a, b, rtol=tolerance, atol=tolerance, equal_nan=True)


def full_windows(valid, width, leading=True):
    out = np.zeros(len(valid), bool)
    if len(valid) >= width:
        values = np.lib.stride_tricks.sliding_window_view(valid, width).all(1)
        if leading:
            out[width-1:] = values
        else:
            out[:len(values)] = values
    return out


def raw_for_time(t):
    files = []
    for path in RAW.glob("*.parquet"):
        a, b = [pd.to_datetime(s, format="%Y%m%dT%H") for s in path.stem.split("_")]
        if a <= t < b:
            files.append(path)
    if len(files) != 1:
        raise ValueError("Need exactly one source file per ERA5 timestamp")
    return pd.read_parquet(files[0], filters=[("time_utc", "=", t)]).set_index("site")


def independent_physics(raw, points):
    """Explicit raw-unit formulas, independent of the builder's transform."""
    nodes = points[points.site.str.startswith("e")]
    node = raw.loc[nodes.site, list(BANDS)].astype("float64")
    out = pd.DataFrame(index=node.index)
    mapping = dict(t2m_c="temperature_2m", td2m_c="dewpoint_temperature_2m",
        sp_hpa="surface_pressure", mslp_hpa="mean_sea_level_pressure",
        u10="u_component_of_wind_10m", v10="v_component_of_wind_10m",
        cape="convective_available_potential_energy", tcwv="total_column_water_vapour",
        kx="k_index", tt="total_totals_index", blh="boundary_layer_height",
        tcc="total_cloud_cover", lcc="low_cloud_cover", mcc="medium_cloud_cover", hcc="high_cloud_cover",
        swvl1="volumetric_soil_water_layer_1", u850="u_component_of_wind_850hPa",
        v850="v_component_of_wind_850hPa", q850_gkg="specific_humidity_850hPa",
        t850_c="temperature_850hPa", rh850_pct="relative_humidity_850hPa", w850_pas="vertical_velocity_850hPa",
        u500="u_component_of_wind_500hPa", v500="v_component_of_wind_500hPa",
        q500_gkg="specific_humidity_500hPa", t500_c="temperature_500hPa", w500_pas="vertical_velocity_500hPa",
        ivt_u="vertical_integral_of_eastward_water_vapour_flux",
        ivt_v="vertical_integral_of_northward_water_vapour_flux",
        vimd_mmh="vertical_integral_of_divergence_of_moisture_flux")
    for output, source in mapping.items():
        value = node[source]
        if output in ("t2m_c", "td2m_c", "t850_c", "t500_c"):
            value = value-273.15
        elif output in ("sp_hpa", "mslp_hpa"):
            value = value/100
        elif output.startswith("q"):
            value = value*1000
        elif output == "vimd_mmh":
            value = value*3600
        out[output] = value
    out["rh2m_pct"] = 100*np.exp(17.625*out.td2m_c/(243.04+out.td2m_c)-17.625*out.t2m_c/(243.04+out.t2m_c))
    cin = node.convective_inhibition
    out["cin_capped"] = np.minimum(cin.fillna(500), 500)
    out["has_lfc"] = cin.notna().astype(float)
    out.loc[node.convective_available_potential_energy.isna(), ["cin_capped", "has_lfc"]] = np.nan
    out["ivt_mag"] = np.hypot(out.ivt_u, out.ivt_v)
    out["shear_850_500"] = np.hypot(out.u500-out.u850, out.v500-out.v850)
    for name, feature in [("ctx_tcwv", "tcwv"), ("ctx_ivt_mag", "ivt_mag")]:
        result = []
        for point in nodes.itertuples():
            neighbors = nodes[(nodes.lat-point.lat).abs().le(.25001) & (nodes.lon-point.lon).abs().le(.25001)]
            result.append(out.loc[neighbors.site, feature].mean())
        out[name] = result
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    summary = json.loads((PUBLIC / "dataset_summary.json").read_text(encoding="utf8"))
    file = OUT / DATASET
    if sha(file) != summary["sha256"]:
        raise ValueError("Dataset checksum mismatch")
    pf = pq.ParquetFile(file)
    contract = json.loads(pf.schema_arrow.metadata[b"pbl6_contract"])
    registry = pd.read_csv(RAIN_BASE / "station_registry_private.csv")
    z = np.load(RAIN_BASE / "rain_channels.npz")
    days = pd.DatetimeIndex(z["marked_day"])
    count = len(days)*24
    end = pd.date_range(days[0]-pd.Timedelta(hours=4), periods=count, freq="h",
                        tz="Asia/Ho_Chi_Minh").tz_convert("UTC").as_unit("ns")
    start = end-pd.Timedelta(hours=1)
    collection = json.loads((BASE / "era5_collection_progress.json").read_text(encoding="utf8"))
    latest = pd.Timestamp(collection["latest_source_utc"], tz="UTC")
    available = start <= latest
    raw = z["raw"].reshape(2, count, len(registry))
    valid = z["valid"].reshape(raw.shape)
    cache = np.load(BASE / "full_weather/weather_station_native.npy", mmap_mode="r")
    wxmeta = json.loads((BASE / "full_weather/weather_station_native.json").read_text(encoding="utf8"))
    if sha(BASE / "full_weather/weather_station_native.npy") != wxmeta["sha256"]:
        raise ValueError("Weather cache hash mismatch")
    for name, digest in wxmeta["source_sha256"].items():
        if sha(RAW/name) != digest:
            raise ValueError("Native ERA5 source hash mismatch")
    old_path = ROOT / "data/processed/station_v1/PBL6_TRAM_GIO_NGAY_V1.parquet"
    old_ids = set(pd.read_csv(ROOT / "data/operational/vrain_2026_11_09/handoff_v1/station_registry_private.csv").query("legacy_id.notna()").canonical_id)
    replay_dates = ["2020-12-31 12:00", "2022-10-14 02:00", "2024-12-31 11:00",
                    "2025-09-15 12:00", "2026-01-08 02:00", "2026-09-30 23:00",
                    "2026-10-01 00:00", "2026-11-10 23:00"]
    sample_time_index = [start.get_loc(pd.Timestamp(t, tz="UTC")) for t in replay_dates]
    saved_weather = np.empty((len(replay_dates), len(registry), len(PHYSICAL_FEATURES)))
    rows = 0
    ready_count = 0
    old_rows = 0
    old_ready_windows = 0
    new_tail_windows = 0
    last_ready = {}
    for group in range(pf.num_row_groups):
        f = pf.read_row_group(group).to_pandas()
        sid = f.station_id.iloc[0]
        if len(f) != count or not f.station_id.eq(sid).all():
            raise ValueError("Unexpected station row group")
        j = registry.index[registry.canonical_id.eq(sid)][0]
        equal(pd.DatetimeIndex(f.period_end_utc).asi8, end.asi8)
        equal(pd.DatetimeIndex(f.period_start_utc).asi8, start.asi8)
        equal(pd.DatetimeIndex(f.weather_last_time_utc).asi8, start.asi8)
        equal(f.source_marked_day.to_numpy(), np.repeat(days.values, 24))
        equal(f.legacy_rain_raw_mm, raw[0, :, j])
        equal(f.modern_rain_raw_mm, raw[1, :, j])
        l, m = valid[0, :, j], valid[1, :, j]
        cf = l & m & (np.abs(raw[0, :, j]-raw[1, :, j]) > 1e-6)
        codes = np.full(count, -1, dtype="int8")
        codes[m] = 1
        codes[l] = 0
        codes[cf] = 3
        rain = np.full(count, np.nan, dtype="float32")
        rain[codes == 0] = raw[0, codes == 0, j]
        rain[codes == 1] = raw[1, codes == 1, j]
        equal(f.rain_mm, rain)
        equal(f.gauge_source_code, codes)
        equal(f.cross_channel_conflict, cf)
        equal(f.legacy_rain_qc_mm, np.where(l, raw[0, :, j], np.nan))
        equal(f.modern_rain_qc_mm, np.where(m, raw[1, :, j], np.nan))
        expected = np.full((count, len(PHYSICAL_FEATURES)), np.nan, dtype="float32")
        expected[available] = cache[:, j]
        equal(f[PHYSICAL_FEATURES].to_numpy(), expected)
        local = end.tz_convert("Asia/Ho_Chi_Minh")
        cal = np.stack([np.sin(2*np.pi*local.hour/24), np.cos(2*np.pi*local.hour/24),
                        np.sin(2*np.pi*local.dayofyear/365.25), np.cos(2*np.pi*local.dayofyear/365.25)], 1).astype("float32")
        equal(f[["sin_hour", "cos_hour", "sin_doy", "cos_doy"]].to_numpy(), cal)
        equal(f.weather_timestamp_available, available)
        y = f[label_names("1h")].to_numpy()
        for h in range(1, 7):
            equal(y[:-h, h-1], rain[h:])
            if not np.isnan(y[-h:, h-1]).all():
                raise ValueError("Future label extends beyond gauge source")
        split = np.full(count, "boundary", dtype=object)
        for role, a, b in [("train", 2021, 2023), ("cal", 2023, 2024), ("dev", 2024, 2025),
                            ("reserved2025", 2025, 2026), ("external2026", 2026, 2027)]:
            lo = pd.Timestamp(f"{a}-01-01", tz="Asia/Ho_Chi_Minh")
            hi = pd.Timestamp(f"{b}-01-01", tz="Asia/Ho_Chi_Minh")
            split[(local >= lo) & (local+pd.Timedelta(hours=6) <= hi)] = role
        if not np.array_equal(split, f.split):
            raise ValueError("Chronological role mismatch")
        complete = np.isfinite(f[feature_names("1h", use_rain=False)].to_numpy()).all(1)
        same = np.zeros(count, bool)
        rolling = np.lib.stride_tricks.sliding_window_view(codes, 30)
        same[23:count-6] = (rolling == 0).all(1) | (rolling == 1).all(1)
        technical = (full_windows(complete, 24) & full_windows(np.isfinite(rain), 24) &
                     np.isfinite(y).all(1) & same & (split != "boundary"))
        seen = bool((technical & (split == "train")).any())
        ready = technical & seen
        for name, value in [("weather_complete", complete), ("source_consistent_window", same),
                            ("sample_complete", technical), ("sample_ready_r1", ready),
                            ("sample_ready_r0", ready), ("recommended_sample", ready)]:
            equal(f[name], value)
        if not f.station_seen_train.eq(seen).all():
            raise ValueError("Station eligibility differs from training-only rule")
        for role in ROLES:
            indices = np.flatnonzero(ready & (split == role))
            if len(indices):
                last_ready[role] = max(last_ready.get(role, ""), str(local[indices[-1]]))
        if sid in old_ids:
            old = pd.read_parquet(old_path, columns=["period_end_utc", "rain_mm", "sample_ready_r1", *feature_names("1h", use_rain=False), *label_names("1h")],
                                  filters=[("station_id", "=", sid), ("resolution", "=", "1h")])
            n = len(old)
            equal(pd.DatetimeIndex(old.period_end_utc).asi8, end[:n].asi8)
            equal(old[feature_names("1h", use_rain=False)].to_numpy(), f.iloc[:n][feature_names("1h", use_rain=False)].to_numpy())
            equal(old.rain_mm, rain[:n])
            equal(old.sample_ready_r1.iloc[:-6], ready[:n-6])
            # The old gauge archive stopped at 19h, before the local year ended.
            # New gauge hours can complete up to six previously truncated labels.
            if (old.sample_ready_r1.to_numpy() & ~ready[:n]).any():
                raise ValueError("An old valid window disappeared")
            old_y = old[label_names("1h")].to_numpy()
            finite = np.isfinite(old_y)
            equal(old_y[finite], y[:n][finite])
            old_ready_windows += int(old.sample_ready_r1.sum())
            new_tail_windows += int((ready[:n] & ~old.sample_ready_r1.to_numpy()).sum())
            old_rows += n
        saved_weather[:, j] = f.iloc[sample_time_index][PHYSICAL_FEATURES].to_numpy()
        rows += len(f)
        ready_count += int(ready.sum())
        if group % 15 == 0:
            print(json.dumps(dict(stage="verify_full_rows", station_groups=group+1, rows=rows)), flush=True)
    if pf.num_row_groups != 86 or rows != summary["rows"]:
        raise ValueError("Row/station count differs from handoff")
    points = era5_points()
    fields_checked = 0
    for ti, timestamp in enumerate(replay_dates):
        t = pd.Timestamp(timestamp)
        raw_frame = raw_for_time(t)
        physics = independent_physics(raw_frame, points)
        sea = points[points.site.str.startswith("e") & points.lat.between(15.5, 16.5) & points.lon.between(108.75, 109.5)]
        regional = dict(cold_surge_dp_hpa=(raw_frame.loc["syn_hanoi", "mean_sea_level_pressure"]-raw_frame.loc["e16.00_108.25", "mean_sea_level_pressure"])/100,
            dp_tonkin_south_hpa=(raw_frame.loc["syn_tonkin", "mean_sea_level_pressure"]-raw_frame.loc["syn_south", "mean_sea_level_pressure"])/100,
            sst_region_c=(raw_frame.loc[sea.site, "sea_surface_temperature"].to_numpy(dtype="float32")-np.float32(273.15)).mean())
        for j, station in enumerate(registry.itertuples()):
            la = np.floor(station.latitude/.25)*.25
            lo = np.floor(station.longitude/.25)*.25
            fy = (station.latitude-la)/.25
            fx = (station.longitude-lo)/.25
            corners = [(la, lo, (1-fy)*(1-fx)), (la, lo+.25, (1-fy)*fx),
                       (la+.25, lo, fy*(1-fx)), (la+.25, lo+.25, fy*fx)]
            for k, feature in enumerate(PHYSICAL_FEATURES):
                if feature in regional:
                    value = regional[feature]
                else:
                    values = [physics.loc[f"e{a:.2f}_{b:.2f}", feature] for a, b, w in corners if w > 1e-10]
                    value = sum(physics.loc[f"e{a:.2f}_{b:.2f}", feature]*w for a, b, w in corners if w > 1e-10) if np.isfinite(values).all() else np.nan
                np.testing.assert_allclose(saved_weather[ti, j, k], value, rtol=2e-5, atol=5e-4, equal_nan=True,
                                           err_msg=f"Independent raw ERA5 replay: {timestamp} {feature}")
                fields_checked += 1
    import ee
    ee.Initialize(project=args.project)
    ee.data.setDeadline(60000)
    fresh_cells = 0
    fresh_points = points[points.site.isin(["e15.00_107.00", "e16.00_108.25", "e17.00_109.50", "syn_hanoi"])].reset_index(drop=True)
    for timestamp in ["2025-09-15 12:00", "2026-10-01 00:00", "2026-11-10 23:00"]:
        t = pd.Timestamp(timestamp)
        downloaded = fetch_chunk(ee, fresh_points, t, t+pd.Timedelta(hours=1)).set_index("site")
        source = raw_for_time(t)
        equal(downloaded.loc[fresh_points.site, list(BANDS)].to_numpy(), source.loc[fresh_points.site, list(BANDS)].to_numpy())
        fresh_cells += len(fresh_points)*len(BANDS)
    loader_samples = 0
    for role in ROLES:
        loader = HourlyStationData(file, role, "E7", stations=["ST001", "ST041", "ST086"])
        if len(loader):
            for i in np.unique(np.linspace(0, len(loader)-1, 10).astype(int)):
                sample = loader[int(i)]
                if sample["x"].shape != (24, 45) or sample["y"].shape != (6,):
                    raise ValueError("Consumer window shape mismatch")
                loader_samples += 1
    before = json.loads((BASE / "protected_before.json").read_text(encoding="utf8"))
    for path, digest in before.items():
        if sha(ROOT/path) != digest:
            raise ValueError("Protected artifact changed: "+path)
    verification = dict(status="passed", dataset_sha256=sha(file), all_rows_checked=rows,
        all_ready_windows_checked=ready_count, old_v1_hourly_rows_identical=old_rows,
        old_v1_identical_scope="all hourly weather/rain values and old finite labels; new edge labels recorded separately",
        old_v1_ready_windows_preserved=old_ready_windows,
        additional_windows_at_old_truncated_tail=new_tail_windows,
        source_field_replays=fields_checked, fresh_gee_source_cells=fresh_cells,
        loader_samples_checked=loader_samples, protected_artifacts_unchanged=len(before),
        last_ready_issue_local=last_ready, native_source_chunks_checked=len(wxmeta["source_sha256"]),
        models_trained=False, models_scored=False)
    write_json(PUBLIC / "verification.json", verification)
    summary["status"] = "verified_with_documented_gaps_and_source_transition"
    summary["last_ready_issue_local"] = last_ready
    write_json(PUBLIC / "dataset_summary.json", summary)
    print(json.dumps(verification), flush=True)


if __name__ == "__main__":
    main()
