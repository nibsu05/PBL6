"""Kiểm toán dữ liệu NOAA độc lập và đối chiếu phụ tổng mưa 6 giờ.

NOAA GHCNh tại VMW00041003 chỉ có mưa tích lũy 6/12/24 giờ năm 2025.
Không đổi những số tích lũy này thành nhãn mưa từng giờ hoặc coi giờ không
có bản ghi là 0 mm. Đối chiếu 6 giờ dưới đây chỉ dùng các kỳ có báo cáo.
"""

from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw_data"
OUT = ROOT / "reports" / "independent_observations"
GHCNH = RAW / "ghcnh_danang_2025.psv"
ISD = RAW / "noaa_isd_danang_2025.gz"
PREDICTIONS = ROOT / "reports" / "surface_only" / "test_predictions.parquet"


def _error_metrics(truth: pd.Series, forecast: pd.Series) -> dict[str, float | None]:
    actual = truth.to_numpy(dtype=float)
    predicted = forecast.to_numpy(dtype=float)
    if not len(actual) or not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise ValueError("Thiếu cặp tổng mưa 6 giờ hợp lệ")
    residual = predicted - actual
    return {
        "MAE_mm_6h": float(np.abs(residual).mean()),
        "RMSE_mm_6h": float(np.sqrt(np.square(residual).mean())),
        "mean_bias_mm_6h": float(residual.mean()),
        "CC": (float(np.corrcoef(actual, predicted)[0, 1])
               if np.std(actual) > 0 and np.std(predicted) > 0 else None),
    }


def main() -> None:
    for path in (GHCNH, ISD, PREDICTIONS):
        if not path.exists():
            raise FileNotFoundError(path)
    OUT.mkdir(parents=True, exist_ok=True)
    columns = [
        "STATION", "DATE", "LATITUDE", "LONGITUDE", "precipitation",
        "precipitation_6_hour", "precipitation_6_hour_Quality_Code",
        "precipitation_6_hour_Measurement_Code", "precipitation_6_hour_Source_Station_ID",
        "precipitation_12_hour", "precipitation_24_hour",
    ]
    frame = pd.read_csv(GHCNH, sep="|", usecols=columns, low_memory=False)
    if frame["STATION"].nunique() != 1 or frame["STATION"].iloc[0] != "VMW00041003":
        raise ValueError("Tệp GHCNh không phải trạm VMW00041003")
    for col in ("precipitation", "precipitation_6_hour", "precipitation_12_hour",
                "precipitation_24_hour"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    gauge = frame.loc[frame["precipitation_6_hour"].notna()].copy()
    quality = gauge["precipitation_6_hour_Quality_Code"].value_counts(dropna=False).to_dict()
    gauge = gauge.loc[gauge["precipitation_6_hour_Quality_Code"] == 1].copy()
    gauge["valid_datetime"] = pd.to_datetime(gauge["DATE"], utc=True, errors="raise")
    if gauge["valid_datetime"].duplicated().any() or (gauge["precipitation_6_hour"] < 0).any():
        raise ValueError("NOAA có giờ trùng hoặc tổng mưa âm")

    isd_periods: dict[str, int] = {}
    with gzip.open(ISD, "rt", encoding="ascii", errors="replace") as handle:
        isd_records = 0
        for line in handle:
            isd_records += 1
            for match in re.finditer(r"AA[1-4](\d{2})(\d{4})(.)(.)", line[105:]):
                period = match.group(1)
                isd_periods[period] = isd_periods.get(period, 0) + 1

    predictions = pd.read_parquet(PREDICTIONS)
    needed = {"last_input_datetime", "valid_datetime", "horizon_h", "actual_mm",
              "predicted_mm", "persistence_mm"}
    if needed - set(predictions):
        raise ValueError("Dự báo thiếu cột cần cho tổng 6 giờ")
    window = predictions.groupby("last_input_datetime", sort=False).agg(
        n_hours=("horizon_h", "size"),
        openmeteo_6h_mm=("actual_mm", "sum"),
        bilstm_6h_mm=("predicted_mm", "sum"),
        persistence_6h_mm=("persistence_mm", "sum"),
    ).reset_index()
    end_hours = predictions.loc[predictions["horizon_h"] == 6,
                                ["last_input_datetime", "valid_datetime"]]
    window = window.merge(end_hours, on="last_input_datetime", validate="one_to_one")
    window = window.loc[window["n_hours"] == 6].copy()
    matched = gauge[["valid_datetime", "precipitation_6_hour"]].merge(
        window, on="valid_datetime", how="inner", validate="one_to_one"
    ).rename(columns={"precipitation_6_hour": "noaa_6h_mm"})
    matched.to_csv(OUT / "matched_noaa_6h_2025.csv", index=False)
    metrics = {
        col: _error_metrics(matched["noaa_6h_mm"], matched[col])
        for col in ("openmeteo_6h_mm", "bilstm_6h_mm", "persistence_6h_mm")
    }
    report = {
        "station": "VMW00041003 - DA NANG, NOAA GHCNh",
        "station_coordinates": {"latitude": float(frame["LATITUDE"].median()),
                                "longitude": float(frame["LONGITUDE"].median())},
        "year": 2025,
        "ghcnh_rows": len(frame),
        "ghcnh_hourly_precipitation_values": int(frame["precipitation"].notna().sum()),
        "ghcnh_6h_reports": int(frame["precipitation_6_hour"].notna().sum()),
        "ghcnh_12h_reports": int(frame["precipitation_12_hour"].notna().sum()),
        "ghcnh_24h_reports": int(frame["precipitation_24_hour"].notna().sum()),
        "ghcnh_6h_quality_codes": {str(key): int(value) for key, value in quality.items()},
        "ghcnh_6h_trace_reports": int((gauge["precipitation_6_hour_Measurement_Code"] == "T").sum()),
        "ghcnh_6h_positive_reports": int((gauge["precipitation_6_hour"] > 0).sum()),
        "ghcnh_6h_matched_test_reports": len(matched),
        "isd_rows": isd_records,
        "isd_AA_period_hours_counts": isd_periods,
        "paired_6h_diagnostic": metrics,
        "caution": (
            "GHCNh thiếu lượng mưa 1 giờ; bản ghi 6 giờ không đều và chủ yếu xuất hiện khi có mưa. "
            "Các metric 6 giờ chỉ có điều kiện trên các bản ghi được báo, không đo recall/FAR "
            "trên mọi giờ. Giả định DATE là cuối kỳ tích lũy 6 giờ; cần xác nhận với đơn vị trạm."
        ),
        "sources": {
            "ghcnh": "https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly",
            "isd_format": "https://www.ncei.noaa.gov/pub/data/noaa/isd-format-document.pdf",
            "openmeteo_hour_definition": "https://open-meteo.com/en/docs/historical-weather-api",
        },
    }
    (OUT / "noaa_audit_2025.json").write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                                encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
