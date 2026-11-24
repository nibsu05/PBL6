"""Compare frozen forecasts on the same station and issue keys across branches."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from demo.station_map_forecast import station_forecasts
from src.verification import contingency_scores, continuous_scores


PRIVATE = ROOT / "data/operational"
REPORTS = ROOT / "reports"
PUBLIC = REPORTS / "station_forecast_unified_2026_11_24"
NOWCAST = "station_nowcast_2026_11_24"
DAILY = "gfs_station_final_2026_11_17"
GAUGE_UPDATE = "station_update_2026_11_16"
DAILY_DATA = "PBL6_GFS_VRAIN_NGAY_2021_2026.parquet"
KEY = ["station_id", "issue_utc"]
HOURLY_MODELS = ("Zero", "Persistence", "BiLSTM_R", "BiLSTM_E0", "BiLSTM_E2", "LightGBM_R")
DAILY_MODELS = ("ZERO", "PERSISTENCE", "GFS", "MOS", "LGB_N0", "LGB_N1", "LGB_N3", "GRU_N3", "GRU_N5")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verified(path, expected):
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if digest != expected:
        raise ValueError(f"Source differs from its verified archive: {path.name}")
    return digest


def matched_archives(shared):
    hp = PRIVATE / NOWCAST / "predictions_reserved2025.parquet"
    dp = PRIVATE / DAILY / "holdout_predictions_private.parquet"
    evidence = {
        "hourly_2025": verified(hp, read_json(PRIVATE / NOWCAST / "evaluation_reserved2025.json")["artifacts"][hp.name]),
        "daily_holdout": verified(dp, read_json(REPORTS / DAILY / "final_verification.json")["holdout_predictions_sha256"]),
    }
    hours = [*range(1, 7)]
    truth = [f"obs_h{h}" for h in hours]
    hourly = pd.read_parquet(
        hp, columns=["station_id", "issue_time_utc", *truth,
                     *[f"{m}_h{h}" for m in HOURLY_MODELS for h in hours]],
        filters=[("station_id", "in", sorted(shared))],
    ).rename(columns={"issue_time_utc": "issue_utc"})
    hourly = hourly.loc[hourly.issue_utc.dt.hour.eq(12)].copy()
    daily = pd.read_parquet(
        dp, columns=[*KEY, "evaluation_set", "horizon", "target_start_utc", "target_end_utc", "y_mm",
                     *[f"{m}_mean" for m in DAILY_MODELS], "GRU_N5_median", "MOS_median"],
        filters=[("split", "=", "reserved2025"), ("gauge_namespace", "=", "legacy")],
    )
    if (hourly.duplicated(KEY).any() or daily.duplicated([*KEY, "horizon"]).any()
            or set(daily.station_id) != shared or not daily.issue_utc.dt.hour.eq(12).all()
            or not daily.evaluation_set.eq("test2025_legacy").all()):
        raise ValueError("Unexpected station, time or split keys in locked forecasts")
    expected_start = daily.issue_utc + pd.to_timedelta((daily.horizon - 1) * 24, unit="h")
    if (not (daily.target_start_utc == expected_start).all()
            or not (daily.target_end_utc == expected_start + pd.Timedelta(hours=24)).all()
            or not daily.groupby(KEY).horizon.nunique().eq(3).all()):
        raise ValueError("Daily target times differ from the 19h window contract")
    day1 = daily.loc[daily.horizon.eq(1), [*KEY, "y_mm", "LGB_N3_mean"]]
    overlap = hourly.merge(day1, on=KEY, how="inner", validate="one_to_one")
    aligned_day = daily.merge(overlap[KEY], on=KEY, how="inner", validate="many_to_one")
    if (len(aligned_day) != 3 * len(overlap) or set(overlap.station_id) != shared
            or not np.isfinite(overlap.select_dtypes(include="number")).all().all()):
        raise ValueError("The aligned comparison is incomplete")
    return overlap, aligned_day, len(hourly), len(day1), evidence


def scores(frame, branch):
    hourly = branch == "hourly"
    methods = HOURLY_MODELS if hourly else DAILY_MODELS
    selection = ("mean",) if hourly else ("mean", "median")
    rows = []
    for horizon in range(1, 7 if hourly else 4):
        view = frame if hourly else frame.loc[frame.horizon.eq(horizon)]
        observed = view[f"obs_h{horizon}" if hourly else "y_mm"].to_numpy()
        reference = view[f"Persistence_h{horizon}" if hourly else "MOS_mean"].to_numpy()
        baseline = continuous_scores(observed, reference)["RMSE"]
        for functional in selection:
            for method in methods if functional == "mean" else ("MOS", "GRU_N5"):
                forecast = view[f"{method}_h{horizon}" if hourly else f"{method}_{functional}"].to_numpy()
                if not np.isfinite(forecast).all():
                    raise ValueError(f"Nonfinite forecast in {branch}/{method}")
                model = continuous_scores(observed, forecast)
                row = dict(branch=branch, horizon=horizon, hours=1 if hourly else 24,
                           model=method, functional="point" if hourly else functional,
                           n=model["n"], rmse=model["RMSE"], mae=model["MAE"], bias=model["bias"],
                           rmse_reduction_percent=(100 * (1 - model["RMSE"] / baseline)
                                                   if functional == "mean" else None))
                for threshold in ((1, 5) if hourly else (1, 50)):
                    event = contingency_scores(observed, forecast, threshold)
                    rows.append(dict(**row, threshold_mm=threshold,
                                     csi=event["CSI"], pod=event["POD"], far=event["FAR"],
                                     hits=event["hits"], misses=event["misses"],
                                     false_alarms=event["false_alarms"], events=event["n_obs_events"]))
    return rows


def depth_consistency(sum6, total24, observed6, observed24):
    excess = np.asarray(sum6) - np.asarray(total24)
    observed_excess = np.asarray(observed6) - np.asarray(observed24)
    return dict(n=len(excess), forecasts_exceed=float(np.mean(excess > 1e-3)),
                forecasts_exceed_count=int(np.count_nonzero(excess > 1e-3)),
                forecasts_exceed_by_1mm=int(np.count_nonzero(excess > 1)),
                max_forecast_excess_mm=float(max(0, np.max(excess))),
                observations_exceed_by_tolerance=int(np.count_nonzero(observed_excess > 1e-3)))


def reconciliation(hourly, daily, truth_hours, truth_day, sample):
    """Two deterministic projections assessed on already used forecasts."""
    hourly = np.asarray(hourly, dtype="float64")
    daily = np.asarray(daily, dtype="float64")
    truth_hours = np.asarray(truth_hours, dtype="float64")
    truth_day = np.asarray(truth_day, dtype="float64")
    total = hourly.sum(axis=1)
    fraction = np.ones_like(total)
    np.divide(daily, total, out=fraction, where=total > daily)
    variants = {
        "original": (hourly, daily),
        "raise_day1": (hourly, np.maximum(total, daily)),
        "scale_hours": (hourly * fraction[:, None], daily),
    }
    rows = []
    for variant, (hours, day) in variants.items():
        sum6 = hours.sum(axis=1)
        exceed = int(np.count_nonzero(sum6 - day > 1e-3))
        values = {"h1": (truth_hours[:, 0], hours[:, 0]),
                  "h6": (truth_hours[:, 5], hours[:, 5]),
                  "sum6": (truth_hours.sum(axis=1), sum6), "d1": (truth_day, day)}
        for lead, (truth, prediction) in values.items():
            threshold = {"h1": 5, "h6": 5, "sum6": 15, "d1": 50}[lead]
            result = continuous_scores(truth, prediction)
            event = contingency_scores(truth, prediction, threshold)
            rows.append(dict(sample=sample, variant=variant, lead=lead, n=result["n"],
                             rmse=result["RMSE"], mae=result["MAE"], bias=result["bias"],
                             threshold_mm=threshold, csi=event["CSI"], pod=event["POD"], far=event["FAR"],
                             forecast_inconsistencies=exceed))
    return rows


def replay_summary(data, shared):
    rows = []
    paired = []
    for case in data["snapshots"]:
        if case["mode"] != "historical_replay":
            continue
        h1, d1 = case["windows"][0], case["windows"][6]
        hh = [{p["station_id"]: p for p in w["points"]} for w in case["windows"][:6]]
        day = {p["station_id"]: p for p in d1["points"]}
        rows.append(dict(issue_utc=case["issue_utc"], day_available=len(day),
                         hourly_available=len(hh[0]),
                         day_common=sum(k in shared for k in day),
                         hourly_common=sum(k in shared for k in hh[0]),
                         both=bool(h1["points"] and day)))
        for sid in shared & day.keys():
            if sid not in hh[0]:
                continue
            record = [p[sid] for p in hh]
            y6 = [p["observed_mm"] for p in record]
            y24 = day[sid]["observed_mm"]
            if any(value is None for value in y6) or y24 is None:
                continue
            paired.append(([p["predicted_mm"] for p in record], day[sid]["predicted_mm"], y6, y24))
    ph, pd1, yh, yd1 = (np.asarray(x) for x in zip(*paired))
    consistency = depth_consistency(ph.sum(axis=1), pd1, yh.sum(axis=1), yd1)
    return pd.DataFrame(rows), consistency, reconciliation(ph, pd1, yh, yd1, "replay2026")


def daily_capacity(shared, active):
    path = ROOT / "data/processed" / GAUGE_UPDATE / DAILY_DATA
    release = read_json(REPORTS / GAUGE_UPDATE / "release.json")
    evidence = verified(path, release["data_files"][DAILY_DATA])
    frame = pd.read_parquet(path, columns=["station_id", "split", "recommended_sample"],
                            filters=[("horizon", "=", 1), ("split", "=", "train")])
    counted = frame.loc[frame.recommended_sample].groupby("station_id").size()
    extra = counted.reindex(sorted(active - shared), fill_value=0)
    history = pd.read_csv(PRIVATE / "gfs_station_pilot_2026_11_10/station_expansion_eligibility_private.csv",
                          usecols=["canonical_id", "complete_train_days", "wet_train_days_ge1"]).set_index("canonical_id")
    extra_history = history.loc[sorted(active - shared)]
    locked = history.index[(history.complete_train_days.ge(365)) & history.wet_train_days_ge1.ge(30)]
    if set(locked) != shared:
        raise ValueError("Published shared roster differs from the historical daily selection")
    return evidence, dict(stations_with_structural_window=int(len(counted)),
                          extra_hourly_station_count=len(extra),
                          extra_with_structural_daily_train=int(extra.gt(0).sum()),
                          extra_daily_train_windows=int(extra.sum()),
                          extra_min_windows=int(extra.min()), extra_max_windows=int(extra.max()),
                          extra_min_complete_days=int(extra_history.complete_train_days.min()),
                          extra_max_complete_days=int(extra_history.complete_train_days.max()),
                          extra_below_365_days=int(extra_history.complete_train_days.lt(365).sum()),
                          extra_below_30_wet_days=int(extra_history.wet_train_days_ge1.lt(30).sum()))


def main():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    data = station_forecasts(True)
    shared = set(data["shared_stations"])
    active = {r["station_id"] for r in data["stations"] if r["hourly"]}
    paired, daily, hour_pool, day_pool, evidence = matched_archives(shared)
    metrics = scores(paired, "hourly") + scores(daily, "daily")
    pd.DataFrame(metrics).to_csv(PUBLIC / "so_sanh_2025_cung_tram_gio.csv", index=False)
    consistency = depth_consistency(paired[[f"LightGBM_R_h{h}" for h in range(1, 7)]].sum(axis=1),
                                    paired.LGB_N3_mean, paired[[f"obs_h{h}" for h in range(1, 7)]].sum(axis=1),
                                    paired.y_mm)
    coverage, replay_test, replay_trials = replay_summary(data, shared)
    coverage.to_csv(PUBLIC / "do_phu_phat_lai.csv", index=False)
    trials = reconciliation(paired[[f"LightGBM_R_h{h}" for h in range(1, 7)]].to_numpy(), paired.LGB_N3_mean,
                            paired[[f"obs_h{h}" for h in range(1, 7)]].to_numpy(), paired.y_mm, "paired2025")
    pd.DataFrame(trials + replay_trials).to_csv(PUBLIC / "thu_rang_buoc_gio_ngay.csv", index=False)
    daily_digest, capacity = daily_capacity(shared, active)
    audit = dict(status="verified_locked_inputs_and_paired_keys", stations=len(shared),
                 hourly_19h_origins=hour_pool, daily_19h_origins=day_pool, aligned_origins=len(paired),
                 aligned_issues=paired.issue_utc.nunique(), aligned_hourly_outputs=len(paired) * 6,
                 aligned_daily_outputs=len(daily), replay_count=len(coverage),
                 replay_joint=int(coverage.both.sum()), daily_capacity=capacity,
                 consistency_2025=consistency, consistency_replay_2026=replay_test,
                 source_sha256={**evidence, "daily_full_candidate_data": daily_digest})
    if consistency["observations_exceed_by_tolerance"] or replay_test["observations_exceed_by_tolerance"]:
        raise ValueError("Observed hour and day products do not agree on the paired subset")
    (PUBLIC / "verification.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2), flush=True)


if __name__ == "__main__":
    main()
