"""Hash-lock models and evaluation implementation before holdout inference."""
import json
from datetime import datetime, timezone
from src.gfs_final import ROOT, BASE, PUBLIC, OLD, OLD_PUBLIC, OLD_DATA, EXTENDED, protocol, assert_control_lock
from src.gfs_daily import sha, write_json
from src.gfs_daily_lock import training_lock

EVALUATION_CODE = ["src/gfs_final.py", "src/gfs_capacity_control.py", "src/gfs_final_gate.py",
    "src/gfs_final_inference.py", "src/gfs_final_metrics.py", "scripts/score_gfs_final.py",
    "src/gfs_daily.py", "src/gfs_daily_models.py", "src/gfs_daily_gru.py",
    "src/gfs_daily_evaluation.py", "src/gfs_station_dataset.py"]


def check_manifest():
    path = PUBLIC / "final_manifest.json"
    lock = json.loads((BASE / "final_manifest_lock.json").read_text())
    if sha(path) != lock["sha256"]:
        raise ValueError("Final manifest changed after freeze")
    manifest = json.loads(path.read_text())
    for key in ("artifacts_sha256", "code_sha256"):
        for name, digest in manifest[key].items():
            if sha(ROOT/name) != digest:
                raise ValueError("Locked evaluation dependency changed: "+name)
    if sha(PUBLIC / "protocol.json") != manifest["protocol_sha256"]:
        raise ValueError("Protocol changed after final freeze")
    return manifest


def freeze_manifest():
    if (PUBLIC / "final_manifest.json").exists():
        return check_manifest()
    if (BASE / "holdout_opened.json").exists():
        raise ValueError("Cannot backdate freeze after holdout opened")
    p = protocol()
    assert_control_lock()
    training_lock()
    checked = json.loads((PUBLIC / "control_verification.json").read_text())
    tests = json.loads((PUBLIC / "unit_test_verification.json").read_text())
    if checked["status"] != "passed" or tests["status"] != "passed":
        raise ValueError("Verify controls and tests before opening holdout")
    artifacts = [OLD_DATA, EXTENDED, OLD / "cohort_private.csv", OLD_PUBLIC / "decision_cutoffs.json",
                 PUBLIC / "control_cutoffs.json", PUBLIC / "control_verification.json"]
    artifacts += [path for folder in (OLD / "models", BASE / "models")
                  for path in sorted(folder.iterdir()) if path.suffix in (".pt", ".joblib")]
    manifest = dict(status="frozen_before_holdout_inference", locked_utc=datetime.now(timezone.utc).isoformat(),
        protocol_sha256=sha(PUBLIC / "protocol.json"), models=p["models"],
        primary_amount_model=p["primary_amount_model"], secondary_median_model=p["secondary_median_model"],
        no_refit_on_2025_or_2026=True, no_post_test_selection=True,
        artifacts_sha256={path.relative_to(ROOT).as_posix(): sha(path) for path in artifacts},
        code_sha256={path: sha(ROOT/path) for path in EVALUATION_CODE})
    write_json(PUBLIC / "final_manifest.json", manifest)
    write_json(BASE / "final_manifest_lock.json", dict(sha256=sha(PUBLIC / "final_manifest.json")))
    return manifest


def record_holdout_opening():
    manifest = check_manifest()
    path = BASE / "holdout_opened.json"
    if not path.exists():
        write_json(path, dict(first_model_evaluation_opened_utc=datetime.now(timezone.utc).isoformat(),
            final_manifest_sha256=sha(PUBLIC / "final_manifest.json"),
            user_authorized=True, models_locked=True, data_QC_already_performed_in_previous_release=True))
    return manifest
