r"""Ghi một lần phát hành dự báo từ dữ liệu bề mặt có thời điểm sẵn có.

File input cần 48 giờ liên tục kết thúc ở anchor, mỗi hàng có `datetime`,
`available_at` và 6 biến bề mặt. Không lấy file Open-Meteo Historical cũ làm
luồng thời gian thực. Mỗi lần phát hành lưu một file bất biến để đánh giá sau.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch

from src.availability_audit import audit_asof_windows
from src.bilstm_model import BiLSTM
from src.feature_engineering import engineer_features
from src.rain_alert_model import RainAlertBiLSTM

ROOT = Path(__file__).resolve().parent
SURFACE = ("temperature_2m", "relative_humidity_2m", "surface_pressure",
           "wind_speed_10m", "wind_direction_10m", "precipitation")


def _aware(values: pd.Series, name: str) -> pd.Series:
    parsed = pd.to_datetime(values, errors="raise")
    if not isinstance(parsed.dtype, pd.DatetimeTZDtype) or parsed.isna().any():
        raise ValueError(f"{name} phải có UTC offset và không khuyết")
    return parsed.dt.tz_convert("Asia/Ho_Chi_Minh")


def prepare_issue_input(raw: pd.DataFrame, issued_at: pd.Timestamp,
                        feature_cols: list[str], scaler) -> tuple[np.ndarray, pd.Timestamp, dict]:
    """Trả input 24xF sau khi chứng minh 48 giờ nguyên liệu đã sẵn có."""
    needed = {"datetime", "available_at", *SURFACE}
    if raw.empty or needed - set(raw):
        raise ValueError(f"Input rỗng hoặc thiếu cột: {sorted(needed - set(raw))}")
    frame = raw.copy()
    frame["datetime"] = _aware(frame["datetime"], "datetime")
    frame["available_at"] = _aware(frame["available_at"], "available_at")
    if frame["datetime"].duplicated().any() or not frame["datetime"].eq(frame["datetime"].dt.floor("h")).all():
        raise ValueError("Giờ đầu vào phải duy nhất và đúng đầu giờ")
    for name in SURFACE:
        frame[name] = pd.to_numeric(frame[name], errors="raise")
    if (not np.isfinite(frame[list(SURFACE)].to_numpy(dtype=float)).all()
            or (frame["precipitation"] < 0).any()):
        raise ValueError("Input bề mặt có giá trị khuyết, âm hoặc vô hạn")
    eligible = frame.loc[(frame["datetime"] <= issued_at)
                         & (frame["available_at"] <= issued_at)]
    if eligible.empty:
        raise ValueError("Chưa có giờ quan trắc nào sẵn có tại thời điểm phát hành")
    anchor = eligible["datetime"].max()
    if issued_at >= anchor + pd.Timedelta(hours=1):
        raise ValueError("Giờ đầu vào mới nhất đã quá cũ cho dự báo +1 giờ")
    first = anchor - pd.Timedelta(hours=47)
    window = frame.loc[frame["datetime"].between(first, anchor)].sort_values("datetime")
    expected = pd.date_range(first, anchor, freq="h")
    if len(window) != 48 or not pd.DatetimeIndex(window["datetime"]).equals(expected):
        raise ValueError("Cần 48 giờ bề mặt liên tục để tạo 24 giờ input và lag 24h")
    summary, _ = audit_asof_windows(
        pd.DataFrame({"last_input_datetime": [anchor], "issued_at": [issued_at]}),
        window[["datetime", "available_at"]], input_hours=48,
    )
    if summary["status"] != "verified":
        raise ValueError(f"Cửa sổ chưa đạt điều kiện as-of: {summary}")
    engineered = engineer_features(window[["datetime", *SURFACE]])
    if len(engineered) != 48 or set(feature_cols) - set(engineered):
        raise ValueError("Không tạo đủ đặc trưng đúng checkpoint")
    x = engineered.loc[24:47, feature_cols]
    if x.shape != (24, len(feature_cols)) or not np.isfinite(x.to_numpy(dtype=float)).all():
        raise ValueError("24 giờ input cuối có lag/rolling thiếu")
    if hasattr(scaler, "feature_names_in_") and list(scaler.feature_names_in_) != feature_cols:
        raise ValueError("Thứ tự đặc trưng scaler không khớp checkpoint")
    transformed = scaler.transform(x).astype(np.float32)
    return transformed, anchor, summary


def record_forecast(input_path: Path, source_name: str, issued_at: pd.Timestamp,
                    output_dir: Path, device: torch.device) -> tuple[Path, dict]:
    if not source_name.strip():
        raise ValueError("Cần tên nguồn dữ liệu bề mặt")
    if input_path.resolve() == (ROOT / "data" / "raw_data" / "openmeteo_danang_2015_2026.csv").resolve():
        raise ValueError("File Open-Meteo Historical hiện tại thiếu available_at; không dùng làm feed vận hành")
    if issued_at.tzinfo is None:
        raise ValueError("issued_at phải có UTC offset")
    issued_at = issued_at.tz_convert("Asia/Ho_Chi_Minh")
    recorded_at = pd.Timestamp.now(tz="UTC")
    if issued_at > recorded_at + pd.Timedelta(minutes=5):
        raise ValueError("issued_at ở tương lai so với đồng hồ máy")
    stem = issued_at.tz_convert("UTC").strftime("%Y%m%dT%H%M%SZ")
    forecast_path = output_dir / f"forecast_{stem}.parquet"
    manifest_path = output_dir / f"forecast_{stem}.json"
    snapshot_path = output_dir / "input_snapshots" / f"input_{stem}.parquet"
    if any(path.exists() for path in (forecast_path, manifest_path, snapshot_path)):
        raise FileExistsError("Lần phát hành này đã được lưu; không ghi đè sổ dự báo")
    standard_path = ROOT / "models" / "surface_only" / "best_surface_model.pth"
    dual_path = ROOT / "models" / "surface_only" / "rain_alert_dual_head.pth"
    scaler_path = ROOT / "models" / "surface_only" / "scaler.pkl"
    standard_ckpt = torch.load(standard_path, map_location="cpu", weights_only=True)
    dual_ckpt = torch.load(dual_path, map_location="cpu", weights_only=True)
    features = standard_ckpt["feature_cols"]
    if dual_ckpt["feature_cols"] != features or len(features) != standard_ckpt["input_dim"]:
        raise ValueError("Hai checkpoint không dùng cùng bộ đặc trưng")
    scaler = joblib.load(scaler_path)
    raw = pd.read_parquet(input_path) if input_path.suffix.lower() == ".parquet" else pd.read_csv(input_path)
    x, anchor, asof_summary = prepare_issue_input(raw, issued_at, features, scaler)
    standard = BiLSTM(len(features), 6).to(device).eval()
    standard.load_state_dict(standard_ckpt["model_state_dict"])
    dual = RainAlertBiLSTM(len(features), 6).to(device).eval()
    dual.load_state_dict(dual_ckpt["model_state_dict"])
    with torch.no_grad():
        tensor = torch.from_numpy(x[None, :, :]).to(device)
        standard_amount = standard(tensor).cpu().numpy()[0]
        dual_amount, dual_logit = dual(tensor)
        dual_amount = dual_amount.cpu().numpy()[0]
        probability = dual_logit.sigmoid().cpu().numpy()[0]
    frozen = json.loads((ROOT / "reports" / "rain_alert_experiment" / "test_summary.json")
                        .read_text(encoding="utf-8"))
    threshold = float(frozen["selected_probability_threshold"])
    last_rain = float(raw.loc[_aware(raw["datetime"], "datetime") == anchor,
                              "precipitation"].iloc[0])
    table = pd.DataFrame({
        "last_input_datetime": [anchor] * 6,
        "issued_at": [issued_at] * 6,
        "valid_datetime": [anchor + pd.Timedelta(hours=h) for h in range(1, 7)],
        "horizon_h": range(1, 7),
        "dual_amount_mm": dual_amount,
        "dual_heavy_probability": probability,
        "dual_alert": probability >= threshold,
        "standard_amount_mm": standard_amount,
        "persistence_mm": [last_rain] * 6,
    })
    # Lưu 48 hàng nguồn đã dùng để có thể đối chiếu với hash sau này khi feed xoay vòng.
    source_hours = _aware(raw["datetime"], "datetime")
    snapshot = raw.loc[source_hours.between(anchor - pd.Timedelta(hours=47), anchor)].copy()
    snapshot = snapshot.assign(datetime=source_hours.loc[snapshot.index]).sort_values("datetime")
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot.to_parquet(snapshot_path, index=False)
    manifest = {
        "source_name": source_name,
        "input_file": str(input_path.resolve()),
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "input_snapshot": str(snapshot_path.resolve()),
        "input_snapshot_sha256": hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
        "issued_at": issued_at.isoformat(),
        "recorded_at_utc": recorded_at.isoformat(),
        "last_input_datetime": anchor.isoformat(),
        "captured_before_first_target": bool(recorded_at <= (anchor + pd.Timedelta(hours=1)).tz_convert("UTC")),
        "asof_check": asof_summary,
        "standard_checkpoint_sha256": hashlib.sha256(standard_path.read_bytes()).hexdigest(),
        "dual_checkpoint_sha256": hashlib.sha256(dual_path.read_bytes()).hexdigest(),
        "frozen_probability_threshold": threshold,
        "note": "available_at phải xuất phát từ log nguồn thực, không được dựng lại từ archive.",
    }
    table.to_parquet(forecast_path, index=False)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return forecast_path, manifest


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Ghi dự báo 1–6 giờ có kiểm tra as-of")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--issued-at", required=True, help="ISO timestamp có UTC offset")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "reports" / "prospective" / "issuances")
    args = parser.parse_args()
    issued = pd.Timestamp(args.issued_at)
    if issued.tzinfo is None:
        raise ValueError("--issued-at phải có UTC offset")
    device = torch.device("cuda" if args.device == "auto" and torch.cuda.is_available()
                          else "cpu" if args.device == "auto" else args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA hiện không có")
    forecast_path, manifest = record_forecast(args.input, args.source_name, issued,
                                             args.output_dir, device)
    print(f"saved={forecast_path}; captured_before_first_target="
          f"{manifest['captured_before_first_target']}")


if __name__ == "__main__":
    main()
