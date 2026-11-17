"""Isolated final-study contracts; frozen daily-v2 remains read-only."""
from pathlib import Path
import json
import os
from datetime import datetime, timezone
from src.gfs_daily import sha, write_json

ROOT = Path(__file__).resolve().parents[1]
NAME = "gfs_station_final_2026_11_17"
BASE = ROOT / "data/operational" / NAME
PUBLIC = ROOT / "reports" / NAME
OLD = ROOT / "data/operational/gfs_station_daily_v2_2026_11_10"
OLD_PUBLIC = ROOT / "reports/gfs_station_daily_v2_2026_11_10"
OLD_DATA = ROOT / "data/processed/gfs_station_daily_v2_2026_11_10/dataset.parquet"
EXTENDED = ROOT / "data/processed/station_update_2026_11_16/PBL6_GFS_VRAIN_NGAY_2021_2026.parquet"
CONTROLS = ("GRU_N3_LINEAR6", "GRU_N3_WIDE")
SEEDS = (17, 29, 43)


def progress(stage, **details):
    write_json(BASE / "progress.json", dict(stage=stage, pid=os.getpid(),
        updated_utc=datetime.now(timezone.utc).isoformat(), **details))


def protocol():
    p = PUBLIC / "protocol.json"
    lock = json.loads((BASE / "protocol_lock.json").read_text(encoding="utf8"))
    if sha(p) != lock["sha256"]:
        raise ValueError("Final-study protocol changed after freeze")
    return json.loads(p.read_text(encoding="utf8"))


def unchanged():
    snapshot = json.loads((BASE / "protected_before.json").read_text(encoding="utf8"))
    for path, digest in snapshot.items():
        if sha(ROOT/path) != digest:
            raise ValueError("Protected artifact changed: "+path)
    return len(snapshot)


def model_names():
    return json.loads((OLD_PUBLIC / "result_summary.json").read_text(encoding="utf8"))["models"] + list(CONTROLS)


def assert_control_lock():
    lock = json.loads((BASE / "control_training_lock.json").read_text(encoding="utf8"))
    for path, digest in lock["code_sha256"].items():
        if sha(ROOT/path) != digest:
            raise ValueError("Control training implementation changed after fitting began")
    if sha(OLD_DATA) != lock["dataset_sha256"]:
        raise ValueError("Frozen development dataset changed")
    protocol()
    return lock
