"""Capture an hourly Da Nang forecast and verify it after all six periods end."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import sqlite3
import sys
from time import sleep
from uuid import uuid4

import numpy as np
import pandas as pd
import requests
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from demo.station_map_alerts import AdminAlerts
from demo.station_map_live import read_optional, timestamp
from demo.station_map_nowcast import HOURLY, ISSUE_DELAY, hourly_index
from scripts.evaluate_station_nowcast import bilstm_forecasts, rain_tree_forecasts, read_fit
from scripts.prepare_station_nowcast_replay import to_depth
from src import station_nowcast as ns
from src.gfs_window import VRAIN, save_parquet, sha, write_json
from src.gfs_window_live import fetch_gauge, load_live_sources, parse_live_day
from src.verification import contingency_scores, continuous_scores
from src.vrain_download import load_session, process_lock

MODELS = ("LightGBM_R", "BiLSTM_R", "Persistence")
SOURCE = "modern"


def utcnow():
    return datetime.now(timezone.utc)


def hour_at(when):
    return when.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def issue_id(when):
    return when.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def report_day(hour):
    local = hour.tz_convert(ns.ZONE)
    return (local.date() + timedelta(days=int(local.hour >= 20))).isoformat()


class Observations:
    """Cache the raw Vrain reporting days read during a single job."""

    def __init__(self, folder):
        self.folder = folder
        self.session = None
        self.registry = None
        self.days = {}

    def connect(self):
        self.session = load_session(VRAIN / "session.dpapi")
        self.registry, self.aliases, self.org = load_live_sources(self.session)

    def matrix(self, clocks):
        if self.registry is None:
            self.connect()
        ids = self.registry.canonical_id.tolist()
        tables, records = [], []
        for day in sorted({report_day(t) for t in clocks}):
            if day not in self.days:
                payload, record = fetch_gauge(self.session, self.org, SOURCE, day, self.folder)
                parsed = parse_live_day(payload, day, self.aliases[SOURCE], ids)
                ticks = parsed["times"].tz_localize(ns.ZONE).tz_convert("UTC")
                rain = np.where(parsed["valid"], parsed["raw"], np.nan)
                available = ticks <= pd.Timestamp(record["retrieved_utc"])
                self.days[day] = pd.DataFrame(rain[available], index=ticks[available], columns=ids), record
            frame, record = self.days[day]
            tables.append(frame)
            records.append(record)
        return pd.concat(tables, verify_integrity=True).reindex(clocks), records

    def close(self):
        if self.session is not None:
            self.session.close()


def model_inputs(matrix, scaler):
    if (len(matrix) != ns.HISTORY or not isinstance(matrix.index, pd.DatetimeIndex)
            or matrix.index.tz is None
            or not matrix.index.equals(pd.date_range(end=matrix.index[-1], periods=ns.HISTORY, freq="h"))):
        raise ValueError("Hourly inference needs 24 completed hours")
    matrix = matrix.reindex(columns=scaler["train_stations"])
    eligible = matrix.columns[(matrix.notna() & matrix.ge(0)).all()].tolist()
    prepared, station_index = [], []
    roster = {sid: i for i, sid in enumerate(scaler["roster"])}
    for sid in eligible:
        station = pd.DataFrame({"period_end_utc": matrix.index, "rain_mm": matrix[sid].to_numpy("float32")})
        row = np.zeros((ns.HISTORY, len(ns.ALL)), dtype=np.float32)
        features = ns.feature_rows(station, ns.FEATURES["R"])
        row[:, :features.shape[1]] = features
        prepared.append(row)
        station_index.extend([roster[sid]] * ns.HISTORY)
    return eligible, prepared, np.asarray(station_index)


def forecast_values(features, station_index, scaler):
    x = np.concatenate(features)
    idx = np.arange(ns.HISTORY - 1, len(x), ns.HISTORY)
    device = torch.device("cpu")
    tensors = ns.WindowTensors(x, np.zeros((len(x), ns.HORIZON), np.float32), station_index,
                               np.asarray(scaler["mean"], np.float32),
                               np.asarray(scaler["std"], np.float32), device)
    return dict(
        LightGBM_R=rain_tree_forecasts(ns.PRIVATE, x, idx, station_index),
        BiLSTM_R=bilstm_forecasts(ns.PRIVATE, tensors, idx, scaler["roster"], ("R",))["BiLSTM_R"],
        Persistence=np.repeat(x[idx, 0, None], ns.HORIZON, axis=1),
    )


def eligible_for_release(origin, received, recorded):
    return origin <= recorded < origin + ISSUE_DELAY and all(t <= recorded for t in received)


def record_forecast(state, folder, source, origin, probe):
    clocks = pd.date_range(end=origin, periods=ns.HISTORY, freq="h")
    window, records = source.matrix(clocks)
    fit, scaler = read_fit(ns.PRIVATE)
    stations, features, indices = model_inputs(window, scaler)
    summary = dict(stations=len(stations), stations_expected=len(scaler["train_stations"]),
                   received_utc=max(record["retrieved_utc"] for record in records))
    if not stations:
        return dict(status="blocked", reason="incomplete_24h_history", **summary)

    forecasts = forecast_values(features, indices, scaler)
    if any(not np.isfinite(values).all() or (values < 0).any() for values in forecasts.values()):
        raise ValueError("Invalid rainfall depths")
    if probe:
        return dict(status="checked", lead_count=ns.HORIZON, **summary)
    if fit["replay_method"] != "LightGBM_R":
        raise ValueError("Unexpected default hourly model")
    series = {sid: {"forecasts": {m: to_depth(forecasts[m][i]) for m in MODELS}}
              for i, sid in enumerate(stations)}
    by_id = source.registry.set_index("canonical_id")
    roster = [dict(id=sid, name=str(by_id.loc[sid, "modern_name"]),
                   lat=float(by_id.loc[sid, "latitude"]), lon=float(by_id.loc[sid, "longitude"]))
              for sid in scaler["train_stations"]]
    data = dict(schema_version=1, issue_time=origin.isoformat(), stations=roster, by_station=series,
                valid_until=(origin + timedelta(hours=6)).isoformat())
    predictions = folder / "forecast_private.json"
    inputs = folder / "inputs_private.parquet"
    write_json(predictions, data)
    frame = window[stations].rename_axis(index="period_end_utc", columns="station_id").stack().rename("rain_mm")
    save_parquet(frame.reset_index(), inputs)
    recorded = utcnow()
    received = [timestamp(record["retrieved_utc"]) for record in records]
    if not eligible_for_release(origin, received, recorded):
        return dict(status="blocked", reason="late_source", **summary)
    index = dict(schema_version=1, status="recorded", issue_utc=origin.isoformat(), recorded_utc=recorded.isoformat(),
                 source=SOURCE, truth_due_utc=data["valid_until"], forecast_sha256=sha(predictions),
                 input_sha256=sha(inputs), model_manifest_sha256=sha(ns.PRIVATE / "fit_manifest.json"),
                 gauge_sources=records, **summary)
    write_json(folder / "issuance.json", index)
    if not eligible_for_release(origin, received, utcnow()):
        return dict(status="blocked", reason="late_source", **summary)
    destination = state / "issuances" / issue_id(origin)
    destination.parent.mkdir(parents=True, exist_ok=True)
    folder.rename(destination)
    return dict(status="recorded", recorded_utc=recorded.isoformat(), lead_count=ns.HORIZON, **summary)


def score_forecast(frame, forecasts):
    results = []
    for model in MODELS:
        for lead, (_, target) in enumerate(frame.iterrows(), 1):
            prediction = np.asarray([forecasts[s]["forecasts"][model][lead - 1] for s in frame.columns])
            valid = target.notna().to_numpy()
            if not valid.any():
                continue
            observed = target.to_numpy()[valid]
            predicted = prediction[valid]
            amount = continuous_scores(observed, predicted)
            for threshold in (1, 5):
                record = dict(model=model, lead=lead, **amount, **contingency_scores(observed, predicted, threshold))
                results.append({k: None if isinstance(v, float) and not np.isfinite(v) else v for k, v in record.items()})
    return results


def verify_due(state, source, now):
    checked = 0
    for folder in sorted((state / "issuances").glob("*")):
        index = hourly_index(folder, now)
        result = folder / "verification_private.json"
        if not index or result.exists() or now < timestamp(index["truth_due_utc"]):
            continue
        origin = timestamp(index["issue_utc"])
        path = folder / "forecast_private.json"
        data = read_optional(path)
        if not data or sha(path) != index["forecast_sha256"] or data.get("issue_time") != index["issue_utc"]:
            continue
        hours = pd.date_range(start=origin + timedelta(hours=1), periods=ns.HORIZON, freq="h")
        truth, records = source.matrix(hours)
        truth = truth.reindex(columns=list(data["by_station"]))
        if not truth.notna().any(axis=1).all():
            continue
        write_json(result, dict(
            issue_utc=origin.isoformat(), verified_utc=utcnow().isoformat(),
            forecast_sha256=index["forecast_sha256"], gauge_sources=records,
            source_folder=source.folder.relative_to(state).as_posix(),
            by_station={sid: to_depth(truth[sid]) for sid in truth},
            observed_cells=int(truth.notna().sum().sum()),
            metrics=score_forecast(truth, data["by_station"])))
        checked += 1
    return checked


def fresh_attempt(state, origin):
    folder = state / "attempts" / f"{issue_id(origin)}_{uuid4().hex[:8]}"
    folder.mkdir(parents=True)
    return folder


def run_forecast(state, origin, probe):
    deadline = origin + ISSUE_DELAY
    if not probe and (state / "issuances" / issue_id(origin) / "issuance.json").is_file():
        return dict(status="already_recorded")
    if not probe and utcnow() >= deadline:
        return dict(status="skipped", reason="outside_hourly_window")
    attempts = []
    for attempt in range(1 if probe else 3):
        started = utcnow()
        source = Observations(fresh_attempt(state, origin))
        try:
            result = record_forecast(state, source.folder, source, origin, probe)
        except PermissionError:
            result = dict(status="blocked", reason="vrain_session")
            if attempt == 0:
                from scripts.track_gfs_window_issue import refresh_authorized_session
                try:
                    refresh_authorized_session()
                except (OSError, ValueError, RuntimeError) as error:
                    result["renewal_error"] = type(error).__name__
        except (requests.RequestException, ValueError, KeyError, OSError) as error:
            status = error.response.status_code if isinstance(error, requests.HTTPError) and error.response is not None else None
            result = dict(status="failed", reason="hourly_source_or_inference_error", error_type=type(error).__name__,
                          http_status=status)
        finally:
            source.close()
        attempts.append(dict(started_utc=started.isoformat(), finished_utc=utcnow().isoformat(), **result))
        if result["status"] in ("recorded", "checked") or result.get("http_status") == 429:
            break
        if attempt < 2 and not probe and utcnow() + timedelta(minutes=2) < deadline:
            sleep(120)
        else:
            break
    return dict(**result, attempts=attempts)


def notify(state, report, at):
    if report["status"] in ("recorded", "already_recorded", "checked"):
        return
    if report["status"] not in ("blocked", "failed", "skipped"):
        return
    try:
        AdminAlerts(state.parent / "admin_alerts.sqlite").add(
            "hourly_nowcast", at, "Chưa ghi được lượt dự báo 1–6 giờ",
            f"Lượt {at.astimezone(timezone(timedelta(hours=7))):%Hh %d/%m} · "
            f"{report.get('reason', 'hourly_job_error')}.",
            "Xem độ trễ và số trạm đủ 24 giờ trong mục Dự báo theo giờ.")
    except (OSError, sqlite3.Error) as error:
        logging.warning("Cannot save hourly admin notification: %s", type(error).__name__)


def run(state, probe=False):
    state.mkdir(parents=True, exist_ok=True)
    started = utcnow()
    origin = hour_at(started)
    with process_lock(state / "jobs.lock"):
        try:
            forecast = run_forecast(state, origin, probe)
        except Exception as error:
            forecast = dict(status="failed", reason="hourly_job_error", error_type=type(error).__name__)
        report = dict(issue_utc=origin.isoformat(), started_utc=started.isoformat(), **forecast)
        if not probe:
            # No truth is loaded into a forecast. A verification problem can be retried
            # without changing the result of the issue we have just saved.
            source = Observations(fresh_attempt(state, origin))
            try:
                report["verified_issues"] = verify_due(state, source, utcnow())
            except (requests.RequestException, ValueError, OSError, KeyError) as error:
                report["verification_error"] = type(error).__name__
            finally:
                source.close()
            notify(state, report, origin)
        report["finished_utc"] = utcnow().isoformat()
        write_json(state / ("probe.json" if probe else "latest.json"), report)
        if not probe:
            write_json(state / "history" / f"{started:%Y%m%dT%H%M%S%fZ}.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true", help="Run CPU inference without saving an issuance")
    args = parser.parse_args()
    torch.set_num_threads(4)
    report = run(HOURLY, args.probe)
    if sys.stdout:
        print(report, flush=True)
    return int(report["status"] == "failed")


if __name__ == "__main__":
    sys.exit(main())
