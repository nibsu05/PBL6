"""Freeze a train-only pilot cohort/protocol and sample a static DEM.

No Vrain 2025/2026, model fitting or evaluation-based station selection.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import requests

BASE = ROOT / "data/operational/gfs_station_pilot_2026_11_10"
VRAIN = ROOT / "data/operational/vrain_2026_11_09"
PUBLIC = ROOT / "reports/gfs_station_pilot_2026_11_10"


def terrain(registry):
    folder = BASE / "terrain"; folder.mkdir(parents=True, exist_ok=True)
    tiles = sorted({f"N{math.floor(r.latitude):02}E{math.floor(r.longitude):03}" for r in registry.itertuples()})
    def load(tile):
        path = folder / (tile+".hgt.gz")
        url = f"https://elevation-tiles-prod.s3.amazonaws.com/skadi/{tile[:3]}/{tile}.hgt.gz"
        if not path.exists():
            response = requests.get(url, timeout=90); response.raise_for_status()
            tmp = path.with_suffix(".tmp"); tmp.write_bytes(response.content); tmp.replace(path)
        compressed = path.read_bytes(); data = gzip.decompress(compressed)
        values = np.frombuffer(data, dtype=">i2")
        size = math.isqrt(len(values))
        if size*size != len(values) or size not in (1201, 3601):
            raise ValueError("Unexpected HGT geometry")
        return tile, values.reshape(size, size), dict(url=url, sha256=hashlib.sha256(compressed).hexdigest(), size=size)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(load, tiles))
    arrays = {tile: array for tile, array, _ in results}
    manifest = {tile: meta for tile, _, meta in results}
    def sample(lat, lon):
        south = math.floor(lat); west = math.floor(lon)
        tile = f"N{south:02}E{west:03}"
        a = arrays[tile]; step = a.shape[0]-1
        y = (south+1-lat)*step; x = (lon-west)*step
        i = int(y); j = int(x); fy = y-i; fx = x-j
        v = a[i:i+2, j:j+2].astype(float)
        if v.shape != (2, 2) or np.any(v == -32768):
            raise ValueError("Missing DEM neighborhood")
        return float(v[0, 0]*(1-fy)*(1-fx)+v[0, 1]*(1-fy)*fx+v[1, 0]*fy*(1-fx)+v[1, 1]*fy*fx)
    records = []
    for row in registry.itertuples():
        lat, lon = row.latitude, row.longitude
        dy = 5000/111195; dx = dy/np.cos(np.radians(lat))
        nine = np.array([[sample(lat+y*dy, lon+x*dx) for x in [-1, 0, 1]] for y in [-1, 0, 1]])
        records.append(dict(canonical_id=row.canonical_id, dem_elev_m=sample(lat, lon),
            dem_mean_5km_m=float(nine.mean()), dem_std_5km_m=float(nine.std()),
            dem_slope_east=float((nine[1, 2]-nine[1, 0])/10000),
            dem_slope_north=float((nine[2, 1]-nine[0, 1])/10000)))
    result = registry.merge(pd.DataFrame(records), on="canonical_id", validate="one_to_one")
    (folder / "manifest.json").write_text(json.dumps(dict(tiles=manifest,
        attribution="Mapzen/Terrain Tiles, https://github.com/tilezen/joerd/blob/master/docs/attribution.md",
        note="Static terrain proxy sampled at current station coordinate; not surveyed gauge elevation"), indent=2)+"\n")
    return result


def main():
    BASE.mkdir(parents=True, exist_ok=True); PUBLIC.mkdir(parents=True, exist_ok=True)
    registry = pd.read_csv(VRAIN / "handoff_v1/station_registry_private.csv", dtype={"legacy_id": str})
    z = np.load(VRAIN / "freeze_work/station_matrices.npz")
    order = {sid: j for j, sid in enumerate(z["station_ids"])}
    registry = registry[registry.legacy_id.isin(order)].sort_values("canonical_id").reset_index(drop=True)
    registry = terrain(registry)
    rain = np.where(z["valid"], z["rain"], np.nan).sum(1)
    train = pd.DatetimeIndex(z["marked_day"]).year <= 2022
    registry["complete_train_days"] = [int(np.isfinite(rain[train, order[sid]]).sum()) for sid in registry.legacy_id]
    registry["wet_train_days_ge1"] = [int((rain[train, order[sid]] >= 1).sum()) for sid in registry.legacy_id]
    candidates = registry[(registry.complete_train_days >= 365) & (registry.wet_train_days_ge1 >= 30)].copy()
    if len(candidates) < 12:
        raise ValueError("Fewer than 12 stations meet frozen train-only eligibility")
    # Deterministic farthest-first coverage in geography and log-terrain height.
    values = candidates[["latitude", "longitude"]].to_numpy()
    values = np.column_stack([values, np.log1p(np.maximum(candidates.dem_elev_m, 0))])
    values = (values-values.mean(0))/np.maximum(values.std(0), 1e-6)
    chosen = [int(np.square(values).sum(1).argmin())]
    while len(chosen) < min(20, len(candidates)):
        distance = np.square(values[:, None, :]-values[chosen][None, :, :]).sum(2).min(1)
        distance[chosen] = -1
        chosen.append(int(distance.argmax()))
    selected = candidates.iloc[chosen].sort_values("canonical_id").reset_index(drop=True)
    selected_bytes=selected.to_csv(index=False).encode()
    cohort_path=BASE / "pilot_stations_private.csv"
    trained=any((BASE / "models").glob("*.joblib"))
    if trained and (not cohort_path.exists() or cohort_path.read_bytes()!=selected_bytes):
        raise ValueError("Pilot cohort is frozen after fitting; use a new experiment version")
    registry["selected_pilot"] = registry.canonical_id.isin(selected.canonical_id)
    registry.to_csv(BASE / "station_terrain_private.csv", index=False)
    selected.to_csv(BASE / "pilot_stations_private.csv", index=False)
    protocol = dict(version="gfs_station_pilot_v1", approved_date="2026-11-10",
        task="same-station three separate next 24h rainfall totals and threshold probabilities",
        pilot_cadence_days=7, first_issue_day="2021-01-08", last_issue_day="2024-12-28",
        cadence_reason="initial pipeline/skill pilot, not full daily experiment; dates fixed independently of rain",
        forecast_init_hour_utc=0, issue_hour_utc=12, issue_hour_vietnam=19,
        rain_cumulative_leads=[12, 36, 60, 84], meteorological_midpoint_leads=[24, 48, 72],
        gfs_availability_assumed_delay_hours=8, init_to_issue_margin_hours=12,
        actual_historical_release_availability_proven=False,
        gauge_availability_assumed_delay_hours=1,
        daily_rain_history="seven full 19--19 days ending yesterday, before observation cutoff",
        recent_rain="1/6/24h totals ending at 18:00 Vietnam, one hour before issue",
        station_selection="train2021--2022 >=365 complete days and >=30 days >=1mm; farthest-first latitude/longitude/log DEM",
        eligible_cohort_candidates=len(candidates), selected_stations=len(selected),
        station_manifest_sha256=hashlib.sha256((BASE / "pilot_stations_private.csv").read_bytes()).hexdigest(),
        split=dict(train="2021--2022", cal="2023", dev="2024, development only; not final test"),
        full_target_interval_must_stay_within_fold=True,
        thresholds_mm_per24h=[1., 50.],
        thresholds_note="1mm event and exploratory 50mm amount, not asserted universal warning standards",
        decision_probability_cutoff=.5, tuning_probability_cutoff=False,
        configurations=dict(A0="GFS rain + future calendar + coordinates/station code",
            A1="A0 + seven gauge-day lags + 1/6/24h recent rainfall",
            A2="A1 + GFS midpoint T850/RH850/u850/v850/PWAT, q850 derived consistently from T/RH, and transport proxies",
            A3="A2 + DEM neighborhood/elevation/slope and wind-upslope proxies"),
        meteorology_note="3 forecast midpoint states, not complete daily atmospheric means",
        common_mask="all A0--A3 use identical complete station/issue/horizon samples",
        model_seeds=[17, 29, 43], main_amount_objective="Tweedie p=1.5",
        models=["monthly_shrunk_climatology", "available_rain_persistence", "raw_GFS", "LightGBM_A0_A1_A2_A3"],
        neural_gate="A2 cal macro-MAE below both raw GFS and climatology, >=50% stations improve over raw GFS, at least one horizon; then small GRU A2",
        reference_fit="all QC-valid train-period daily gauge observations, no future folds",
        main_report="macro station MAE/RMSE/bias, per horizon; Brier/BSS and CSI/POD/FAR at defined thresholds",
        uncertainty="paired bootstrap by blocks of 4 consecutive weekly issue dates; keep all stations/horizons together",
        test2025_read=False, recent2026_used=False, ERA5_as_operational_current_input=False)
    protocol_path=PUBLIC / "protocol.json"
    if trained and protocol_path.exists() and json.loads(protocol_path.read_text())!=protocol:
        raise ValueError("Pilot protocol is frozen after fitting; use a new experiment version")
    protocol_path.write_text(json.dumps(protocol, indent=2)+"\n", encoding="utf8")
    print(json.dumps(dict(eligible_candidates=len(candidates), selected=len(selected),
        min_selected_train_days=int(selected.complete_train_days.min()),
        max_selected_train_days=int(selected.complete_train_days.max()),
        terrain_elevation_range_m=[round(float(selected.dem_elev_m.min()),1), round(float(selected.dem_elev_m.max()),1)])), flush=True)


if __name__ == "__main__":
    main()
