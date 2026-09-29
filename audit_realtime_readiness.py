r"""Kiểm tra khả năng gọi thí nghiệm là dự báo thời gian thực.

Mặc định sẽ đánh dấu baseline archive là chưa kiểm chứng, vì các file hiện
có không ghi issued_at và available_at. Có thể truyền file as-of thật sau này.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from src.availability_audit import audit_asof_windows

ROOT = Path(__file__).resolve().parent


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Kiểm toán thời điểm có sẵn của input 24 giờ")
    parser.add_argument("--predictions", type=Path,
                        default=ROOT / "reports" / "rain_alert_experiment" / "test_predictions.parquet")
    parser.add_argument("--availability", type=Path,
                        default=ROOT / "data" / "raw_data" / "openmeteo_danang_2015_2026.csv")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "reports" / "realtime_readiness")
    args = parser.parse_args()
    predictions = (pd.read_parquet(args.predictions) if args.predictions.suffix.lower() == ".parquet"
                   else pd.read_csv(args.predictions))
    availability = (pd.read_parquet(args.availability) if args.availability.suffix.lower() == ".parquet"
                    else pd.read_csv(args.availability))
    summary, windows = audit_asof_windows(predictions, availability)
    summary.update({"predictions_file": str(args.predictions.resolve()),
                    "availability_file": str(args.availability.resolve()),
                    "current_source": "Open-Meteo Historical Weather API (archive)"
                    if args.availability.name == "openmeteo_danang_2015_2026.csv" else "user supplied",
                    "operational_claim_supported": summary["status"] == "verified",
                    "caution": "Giờ cuối đầu vào không chứng minh dữ liệu đã sẵn có tại giờ phát hành. "
                               "Cần lưu issued_at của dự báo và available_at của mọi biến đầu vào."})
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "availability_audit.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not windows.empty:
        windows.to_csv(out / "window_asof_checks.csv", index=False)
    print(f"status={summary['status']}; verified_windows={summary['verified_windows']}")


if __name__ == "__main__":
    main()
