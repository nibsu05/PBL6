r"""Nhập file mưa trạm CSV/XLSX, kiểm tra chất lượng và lưu giờ chuẩn UTC+7.

Ví dụ:
    .venv\Scripts\python.exe prepare_gauge_observations.py --input data/raw_data/vrain.xlsx \
      --station-name 'Hai Chau' --lat 16.067 --lon 108.22 \
      --source-name Vrain --source-timezone Asia/Ho_Chi_Minh \
      --timestamp-means end --accumulation-hours 1 \
      --datetime-column 'Thời gian' --rain-column 'Lượng mưa'
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from src.gauge_observations import GaugeConfig, normalize_gauge_export

ROOT = Path(__file__).resolve().parent


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Chuẩn hóa và kiểm toán dữ liệu mưa trạm theo giờ")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--station-name", required=True)
    parser.add_argument("--lat", required=True, type=float)
    parser.add_argument("--lon", required=True, type=float)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--source-timezone", required=True)
    parser.add_argument("--timestamp-means", required=True, choices=("start", "end"))
    parser.add_argument("--accumulation-hours", required=True, type=float,
                        help="Kỳ tích lũy do đơn vị trạm xác nhận; chỉ chấp nhận 1")
    parser.add_argument("--datetime-column", default="datetime")
    parser.add_argument("--rain-column", default="precipitation_mm_h")
    parser.add_argument("--station-column")
    parser.add_argument("--station-value")
    parser.add_argument("--quality-column")
    parser.add_argument("--accepted-quality", nargs="+", default=[])
    parser.add_argument("--datetime-format")
    parser.add_argument("--sheet-name", default=0)
    parser.add_argument("--max-distance-km", type=float, default=30.0)
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "data" / "processed" / "independent_gauge")
    args = parser.parse_args()
    config = GaugeConfig(
        station_name=args.station_name, latitude=args.lat, longitude=args.lon,
        source_name=args.source_name, source_timezone=args.source_timezone,
        timestamp_means=args.timestamp_means, accumulation_hours=args.accumulation_hours,
        datetime_column=args.datetime_column,
        rain_column=args.rain_column, station_column=args.station_column,
        station_value=args.station_value, quality_column=args.quality_column,
        accepted_quality=tuple(args.accepted_quality), datetime_format=args.datetime_format,
        sheet_name=args.sheet_name, max_distance_km=args.max_distance_km,
    )
    normalized, metadata = normalize_gauge_export(args.input, config)
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    normalized_path = out / "observations.csv"
    normalized.to_csv(normalized_path, index=False, date_format="%Y-%m-%dT%H:%M:%S%z")
    metadata["normalized_sha256"] = hashlib.sha256(normalized_path.read_bytes()).hexdigest()
    (out / "station_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"saved_hours={len(normalized)}; "
          f"missing_hours_in_span={metadata['missing_calendar_hours_in_span']}; output={out}")


if __name__ == "__main__":
    main()
