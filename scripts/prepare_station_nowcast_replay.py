"""Export seven historical hourly issues using the frozen Vrain-only models."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import station_nowcast as ns
from scripts.evaluate_station_nowcast import bilstm_forecasts, rain_tree_forecasts, read_fit


REGISTRY = ns.ROOT / "data/operational/vrain_update_2026_11_16/station_registry_private.csv"
METHODS = {
    "BiLSTM_R": "Bi-LSTM · mưa trạm",
    "LightGBM_R": "LightGBM · mưa trạm",
    "Persistence": "Giữ nguyên mưa giờ vừa đo",
}


def to_depth(values):
    return [round(float(value), 3) if np.isfinite(value) else None for value in values]


def export(source, out, registry, device):
    fit, transform = read_fit(out)
    if ns.sha256(source) != fit["training"]["dataset_sha256"]:
        raise ValueError("Replay requires the verified hourly archive")
    config = ns.PROTOCOL["replay"]
    knots = pd.DatetimeIndex(config["dates_local"]).tz_localize(ns.ZONE).tz_convert("UTC")
    issues = knots + pd.Timedelta(hours=config["issue_hour_local"])
    active = transform["train_stations"]
    columns = ["station_id", "period_end_utc", "latitude", "longitude", "rain_mm", "gauge_source_code"]
    frame = pd.read_parquet(source, columns=columns, filters=[
        ("period_end_utc", ">=", issues[0] - pd.Timedelta(hours=ns.HISTORY - 1)),
        ("period_end_utc", "<=", issues[-1] + pd.Timedelta(hours=ns.HORIZON)),
        ("station_id", "in", active),
    ])
    meta = pd.read_csv(registry, usecols=["canonical_id", "modern_name", "legacy_name"]).set_index("canonical_id")
    names = meta.modern_name.combine_first(meta.legacy_name).to_dict()
    view = []
    by_issue = {t: {} for t in issues}
    x_blocks, y_blocks, s_blocks, key = [], [], [], []
    training_roster = transform["roster"]
    offset = 0
    for station, group, ticks in ns._station_blocks(frame):
        code = config["gauge_source_code"]
        rain, source_code = group.rain_mm.to_numpy("float32"), group.gauge_source_code.to_numpy()
        available = ns.supported_history(rain, source_code, code)
        compatible_truth = np.where(source_code == code, rain, np.nan)
        targets = ns.future_labels(compatible_truth, ns.HORIZON)
        rain_features = ns.feature_rows(group, ns.FEATURES["R"])
        x = np.zeros((len(group), len(ns.ALL)), dtype="float32")
        x[:, :rain_features.shape[1]] = rain_features
        x_blocks.append(x)
        y_blocks.append(targets)
        s_blocks.append(np.full(len(x), training_roster.index(station), np.int16))
        first = group.iloc[0]
        name = names.get(station)
        view.append(dict(id=station, name=str(name) if pd.notna(name) and name else station,
                         lat=float(first.latitude), lon=float(first.longitude)))
        for issue in issues:
            i = np.searchsorted(ticks, issue.value)
            if i < len(ticks) and ticks[i] == issue.value and available[i]:
                key.append((issue, station, offset + i))
        offset += len(x)
    if {s["id"] for s in view} != set(active) or not key:
        raise ValueError("Replay roster does not match eligible training stations")
    idx = np.array([pos for _, _, pos in key], dtype=np.int64)
    features, truth, station_index = (np.concatenate(p) for p in (x_blocks, y_blocks, s_blocks))
    d = ns.WindowTensors(features, truth, station_index,
                         np.asarray(transform["mean"], np.float32), np.asarray(transform["std"], np.float32),
                         device)
    forecast = dict(
        BiLSTM_R=bilstm_forecasts(out, d, idx, training_roster, ("R",))["BiLSTM_R"],
        LightGBM_R=rain_tree_forecasts(out, features, idx, station_index),
        Persistence=np.repeat(features[idx, 0, None], ns.HORIZON, axis=1),
    )
    for i, (issue, station, pos) in enumerate(key):
        by_issue[issue][station] = dict(
            forecasts={method: to_depth(values[i]) for method, values in forecast.items()},
            observed=to_depth(truth[pos]),
        )
    snapshots = [dict(issue_time=issue.isoformat(),
                      valid_until=(issue + pd.Timedelta(hours=ns.HORIZON)).isoformat(),
                      by_station=by_issue[issue]) for issue in issues]
    payload = dict(schema_version=1, mode=config["mode"], time_zone=ns.ZONE, unit="mm",
                   lead_hours=ns.LEADS, source="Vrain modern",
                   default_method=fit["replay_method"], methods=METHODS, stations=view, issues=snapshots)
    path = out / "station_nowcast_replay_private.json"
    ns.write_json(path, payload)
    summary = dict(sha256=ns.sha256(path), fit_manifest_sha256=ns.sha256(out / "fit_manifest.json"),
                   source="Vrain modern", mode=config["mode"], method=fit["replay_method"],
                   training_station_count=len(active),
                   coverage=[dict(issue_time=issue.isoformat(), stations=len(rows),
                                  observed_hours=sum(sum(value is not None for value in r["observed"])
                                                     for r in rows.values()))
                             for issue, rows in by_issue.items()])
    ns.write_json(out / "replay_summary.json", summary)
    print("Vrain-only historical replay", [(item["issue_time"], item["stations"])
                                          for item in summary["coverage"]], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ns.SOURCE)
    parser.add_argument("--out", type=Path, default=ns.PRIVATE)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cpu")
    args = parser.parse_args()
    torch.set_num_threads(8)
    export(args.source, args.out, args.registry, torch.device(args.device))


if __name__ == "__main__":
    main()
