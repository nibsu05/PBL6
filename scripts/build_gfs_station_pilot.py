"""Merge verified GFS days with a frozen pilot cohort and causal Vrain windows."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd

from src.gfs_station import issue_contract
from src.gfs_station_dataset import FEATURES, gauge_history, forecast_met, add_calendar
from src.station_forecast_data import target_splits

BASE = ROOT / "data/operational/gfs_station_pilot_2026_11_10"
VRAIN = ROOT / "data/operational/vrain_2026_11_09"
OUT = ROOT / "data/processed/gfs_station_pilot"
PUBLIC = ROOT / "reports/gfs_station_pilot_2026_11_10"


def main():
    protocol = json.loads((PUBLIC / "protocol.json").read_text())
    cohort = pd.read_csv(BASE / "pilot_stations_private.csv", dtype={"legacy_id": str})
    if hashlib.sha256((BASE / "pilot_stations_private.csv").read_bytes()).hexdigest() != protocol["station_manifest_sha256"]:
        raise ValueError("Frozen cohort changed")
    z = np.load(VRAIN / "freeze_work/station_matrices.npz")
    hourly = np.where(z["valid"], z["rain"], np.nan).reshape(-1, 82)
    daily = hourly.reshape(-1, 24, 82).sum(1)
    days = pd.DatetimeIndex(z["marked_day"])
    source_order = {s:j for j,s in enumerate(z["station_ids"])}
    expected = pd.date_range(protocol["first_issue_day"], protocol["last_issue_day"], freq=f"{protocol['pilot_cadence_days']}D").strftime("%Y%m%d")
    missing = [d for d in expected if not (BASE / "days" / (d+".npz")).exists()]
    if missing:
        raise ValueError(f"Wait for complete fixed-cadence archive: {len(missing)} issues missing")
    rows = []; rejected = dict(boundary=0, incomplete_station_issue=0)
    for name in expected:
        path = BASE / "days" / (name+".npz")
        meta = json.loads(path.with_suffix(".json").read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest() != meta["sha256"]:
            raise ValueError("GFS day checksum mismatch")
        init, issue = issue_contract(pd.Timestamp(name).strftime("%Y-%m-%d"))
        fold = target_splits(pd.DatetimeIndex([issue]), 72)[0]
        if fold == "unused":
            rejected["boundary"] += 1
            continue
        j = days.get_loc(pd.Timestamp(name))
        g = np.load(path)
        g_order = {s:i for i,s in enumerate(g["station_ids"])}
        for station in cohort.itertuples():
            si = source_order[station.legacy_id]; gi = g_order[station.canonical_id]
            history = gauge_history(hourly, daily, j, si)
            targets = daily[j+1:j+4, si]
            if len(targets) != 3 or not np.isfinite(list(history.values())+targets.tolist()).all():
                rejected["incomplete_station_issue"] += 1
                continue
            local_rows = []
            for h in range(1, 4):
                a = issue+pd.Timedelta(hours=24*(h-1)); b = a+pd.Timedelta(hours=24)
                met = forecast_met(g["met_names"].tolist(), g["met"][h-1, gi])
                terrain = {n:getattr(station,n) for n in FEATURES["A3"] if n.startswith("dem_")}
                upslope = met["gfs_u850"]*terrain["dem_slope_east"] + met["gfs_v850"]*terrain["dem_slope_north"]
                row = dict(station_id=station.canonical_id, station_code=int(station.canonical_id[2:])-1,
                    latitude=station.latitude, longitude=station.longitude, issue_utc=issue,
                    gfs_init_utc=init, gfs_midpoint_valid_utc=init+pd.Timedelta(hours=24*h),
                    target_start_utc=a, target_end_utc=b, observation_cutoff_utc=issue-pd.Timedelta(hours=1),
                    horizon=h, split=fold, y_mm=float(targets[h-1]), gfs_rain_mm=float(g["rain_day_mm"][h-1,gi]),
                    **history, **met, **terrain, **add_calendar(b), wind_upslope=upslope,
                    moist_upslope=upslope*met["gfs_q850_gkg"])
                if not np.isfinite([row[n] for n in FEATURES["A3"]]+[row["y_mm"]]).all():
                    raise ValueError("Missing field in a supposedly ready NWP sample")
                local_rows.append(row)
            rows.extend(local_rows)
    f = pd.DataFrame(rows).sort_values(["issue_utc","station_id","horizon"]).reset_index(drop=True)
    if f.duplicated(["station_id", "issue_utc", "horizon"]).any():
        raise ValueError("Duplicate sample")
    for fold in ["train", "cal", "dev"]:
        if not f.split.eq(fold).any():
            raise ValueError("Pilot must contain all chronological folds")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "gfs_vrain_pilot.parquet"
    f.to_parquet(path, index=False, compression="zstd")
    report = dict(status="merged", station_count=f.station_id.nunique(), fixed_issues=len(expected),
        available_complete_station_issues=len(f)//3, long_horizon_rows=len(f),
        split_rows=f.groupby("split").size().to_dict(), split_issues=f.groupby("split").issue_utc.nunique().to_dict(),
        rejected=rejected, features={k:len(v) for k,v in FEATURES.items()},
        feature_names=FEATURES, dataset_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        observation_delay_assumed_hours=1, gfs_init_before_issue_hours=12,
        test2025_read=False, recent2026_used=False, ERA5_input_used=False)
    (PUBLIC / "dataset_audit.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2),flush=True)


if __name__ == "__main__":
    main()
