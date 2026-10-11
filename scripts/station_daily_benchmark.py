"""Đối chiếu tổng mưa ngày của mọi nguồn với trạm synop: bảng baseline và Thí nghiệm 0.

Một script cho cả hai việc, để nhãn ứng viên và baseline được chấm bằng đúng
một giao thức (``src/verification.py``):

- Giai đoạn A (mặc định 2021–2024): khí hậu, persistence, nhãn hiện tại
  ``era5_om`` và — nếu đã chạy ``extract_gee_precip.py --combine`` — các ứng
  viên nhãn vệ tinh (imerg, imerg_uncal, gsmap, gsmap_gc).
- Giai đoạn B (02/2024–08/2025): thêm dự báo ECMWF/GFS phát hành trước 1, 2, 3, 5 ngày.

Khí hậu và xác suất khí hậu của mỗi trạm chỉ fit trên dữ liệu trạm *trước*
ngày đầu giai đoạn. Mọi nguồn trong một bảng được chấm trên cùng tập (trạm, ngày).
Ngày tính theo UTC (07h–07h giờ Việt Nam) như GSOD.

Chạy (sau ``fetch_gsod_stations.py`` và ``fetch_openmeteo_baselines.py``):
    python scripts/station_daily_benchmark.py
"""

from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import json
import logging

import numpy as np
import pandas as pd

from src.baselines import apply_climatology, doy_climatology, persistence
from src.station_registry import BY_USAF
from src.verification import (VN_DAILY_THRESHOLDS, common_rows, metric_csi, metric_mae,
                              paired_block_bootstrap, score_table)

STATIONS_DIR = ROOT / "data" / "processed" / "stations"
OUT = ROOT / "reports" / "station_benchmark"
THRESHOLDS = tuple(VN_DAILY_THRESHOLDS)  # 16 / 50 / 100 mm
LABEL_CANDIDATES = ("imerg", "imerg_uncal", "gsmap", "gsmap_gc")
SHOW = ["n", "obs_mean", "fcst_mean", "MAE", "bias", "CC", "CSI>=16", "FBI>=16", "BSS>=16",
        "CSI>=50", "POD>=50", "FAR>=50", "FBI>=50", "BSS>=50", "n_obs>=50"]
LABELS = {
    "clim_mean": "Khí hậu (TB theo ngày-năm)", "persistence": "Persistence (trạm hôm trước)",
    "era5_om": "Nhãn hiện tại (Open-Meteo ≈ ERA5)", "imerg": "IMERG Final V07", "imerg_uncal": "IMERG V07 chưa hiệu chỉnh",
    "gsmap": "GSMaP v8", "gsmap_gc": "GSMaP v8 hiệu chỉnh trạm",
    **{f"{m}_d{d}": f"{'ECMWF IFS' if m == 'ecmwf' else 'GFS'} trước {d} ngày" for m in ("ecmwf", "gfs") for d in (1, 2, 3, 5)},
}

LOGGER = logging.getLogger("station_benchmark")


def load_wide() -> pd.DataFrame:
    gsod = pd.read_parquet(STATIONS_DIR / "gsod_daily.parquet")
    gsod = gsod[gsod["usable_year"]]
    wide = gsod[["date", "usaf", "precip_mm"]].rename(columns={"precip_mm": "station"})
    others = [pd.read_parquet(STATIONS_DIR / "openmeteo_daily.parquet")]
    gee = STATIONS_DIR / "gee_daily.parquet"
    if gee.exists():
        others.append(pd.read_parquet(gee))
        LOGGER.info("Có dữ liệu vệ tinh từ Earth Engine: chạy kèm Thí nghiệm 0")
    long = pd.concat(others, ignore_index=True)
    long["date"] = pd.to_datetime(long["date"]).dt.tz_localize(None).dt.normalize()
    sources = long.pivot_table(index=["date", "usaf"], columns="source", values="precip_mm", aggfunc="first")
    wide = wide.merge(sources.reset_index(), on=["date", "usaf"], how="left")
    wide["region"] = wide["usaf"].map(lambda u: BY_USAF[u].region)
    wide["name"] = wide["usaf"].map(lambda u: BY_USAF[u].name)
    return wide.sort_values(["usaf", "date"]).reset_index(drop=True)


def add_reference_forecasts(wide: pd.DataFrame, period_start: pd.Timestamp) -> pd.DataFrame:
    parts = []
    for _, grp in wide.groupby("usaf"):
        grp = grp.copy()
        series = grp.set_index("date")["station"]
        clim = doy_climatology(series[series.index < period_start], THRESHOLDS)
        applied = apply_climatology(pd.DatetimeIndex(grp["date"]), clim)
        grp[applied.columns] = applied.to_numpy()
        grp["persistence"] = persistence(series).to_numpy()
        parts.append(grp)
    return pd.concat(parts, ignore_index=True)


def fmt(value: object) -> str:
    if isinstance(value, (float, np.floating)):
        return "—" if not np.isfinite(value) else f"{value:.2f}"
    return str(value)


def to_markdown(frame: pd.DataFrame, index_label: str) -> str:
    cols = list(frame.columns)
    lines = ["| " + " | ".join([index_label, *cols]) + " |", "|" + "---|" * (len(cols) + 1)]
    for idx, row in frame.iterrows():
        lines.append("| " + " | ".join([LABELS.get(str(idx), str(idx)), *(fmt(row[c]) for c in cols)]) + " |")
    return "\n".join(lines)


def evaluate_period(wide: pd.DataFrame, name: str, start: str, end: str, sources: list[str],
                    n_boot: int) -> dict[str, pd.DataFrame]:
    t0, t1 = pd.Timestamp(start), pd.Timestamp(end)
    data = add_reference_forecasts(wide, t0)
    data = data[(data["date"] >= t0) & (data["date"] <= t1)]
    sources = [s for s in sources if s in data.columns and data[s].notna().any()]
    clim_probs = {thr: f"clim_p>={thr:g}" for thr in THRESHOLDS}
    pooled = score_table(data, "station", sources, THRESHOLDS, clim_prob_cols=clim_probs)

    region_rows, station_rows = [], []
    for key, col, rows in (("region", "region", region_rows), ("station", "name", station_rows)):
        for group, sub in data.groupby(col):
            table = score_table(sub, "station", sources, THRESHOLDS, clim_prob_cols=clim_probs)
            for src, row in table.iterrows():
                rows.append({key: group, "source": src, "n": row["n"], "n_obs>=50": row["n_obs>=50"],
                             "MAE": row["MAE"], "bias": row["bias"], "CC": row["CC"],
                             "CSI>=16": row["CSI>=16"], "CSI>=50": row["CSI>=50"]})

    common = common_rows(data, ["station", *sources, *clim_probs.values()])
    pairs = [(s, "clim_mean") for s in sources if s != "clim_mean"]
    if "ecmwf_d1" in sources and "era5_om" in sources:
        pairs.append(("ecmwf_d1", "era5_om"))
    pairs += [(c, "era5_om") for c in LABEL_CANDIDATES if c in sources]
    boots = []
    for a, b in pairs:
        for metric in (metric_mae, metric_csi(16), metric_csi(50)):
            boots.append(paired_block_bootstrap(common, "station", a, b, metric, n_boot=n_boot))
    LOGGER.info("Giai đoạn %s: %d hàng chung, %d trạm, %d ngày", name, len(common),
                common["usaf"].nunique(), common["date"].nunique())
    return {"pooled": pooled, "by_region": pd.DataFrame(region_rows), "by_station": pd.DataFrame(station_rows),
            "bootstrap": pd.DataFrame(boots), "n_common": len(common), "n_stations": common["usaf"].nunique(),
            "start": str(common["date"].min().date()), "end": str(common["date"].max().date())}


def write_report(results: dict[str, dict]) -> None:
    lines = [
        "# Đối chiếu tổng mưa ngày với trạm synop (baseline và Thí nghiệm 0)",
        "",
        "Sinh tự động bởi `scripts/station_daily_benchmark.py`; đừng sửa tay.",
        "Ngày tính theo UTC (07h–07h giờ Việt Nam). Trạm: NOAA GSOD sau kiểm soát chất lượng",
        "(chỉ ngày đủ 24 h hoặc ngày khô; năm-trạm báo toàn 0 bị loại — xem `gsod_coverage.json`).",
        "Mọi nguồn trong một bảng được chấm trên cùng tập (trạm, ngày). Ngưỡng tính `>=`.",
        "BSS so với xác suất khí hậu của trạm, coi dự báo tất định là xác suất 0/1.",
        "Điểm trạm khác giá trị trung bình ô lưới (25 km với ERA5/ECMWF, 11 km với vệ tinh),",
        "nên mọi nguồn lưới đều bị phạt một phần do khác biệt quy mô — so sánh *giữa các nguồn* vẫn công bằng.",
    ]
    for name, res in results.items():
        lines += ["", f"## Giai đoạn {name}: {res['start']} → {res['end']} ({res['n_stations']} trạm, {res['n_common']} trạm-ngày)",
                  "", "### Gộp mọi trạm", "", to_markdown(res["pooled"][[c for c in SHOW if c in res["pooled"]]], "Nguồn")]
        boot = res["bootstrap"].copy()
        boot["so_sánh"] = boot["source_a"].map(lambda s: LABELS.get(s, s)) + " − " + boot["source_b"].map(lambda s: LABELS.get(s, s))
        boot = boot.set_index("so_sánh")[["metric", "a", "b", "diff", "ci_low", "ci_high"]]
        lines += ["", "### Hiệu số theo cặp, khoảng tin cậy 95 % (bootstrap khối 5 ngày)", "",
                  "MAE: âm là A tốt hơn. CSI: dương là A tốt hơn. Khoảng chứa 0 nghĩa là chưa phân biệt được.", "",
                  to_markdown(boot, "A − B")]
        reg = res["by_region"].pivot_table(index="source", columns="region", values="CSI>=50")
        lines += ["", "### CSI ≥50 mm theo vùng", "", to_markdown(reg, "Nguồn")]
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--period-a", nargs=2, default=["2021-01-01", "2024-12-31"])
    parser.add_argument("--period-b", nargs=2, default=["2024-02-04", "2025-08-24"])
    parser.add_argument("--n-boot", type=int, default=1000)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    OUT.mkdir(parents=True, exist_ok=True)
    wide = load_wide()

    base = ["clim_mean", "persistence", "era5_om"]
    # gfs_d5 bị loại: tổng mưa thấp ~50 % ở mọi quý, lỗi dữ liệu nguồn (xem fetch_openmeteo_baselines.py).
    nwp = [f"ecmwf_d{d}" for d in (1, 2, 3, 5)] + [f"gfs_d{d}" for d in (1, 2, 3)]
    results = {
        "A": evaluate_period(wide, "A", *args.period_a, base + list(LABEL_CANDIDATES), args.n_boot),
        "B": evaluate_period(wide, "B", *args.period_b, base + nwp + list(LABEL_CANDIDATES), args.n_boot),
    }
    summary = {}
    for name, res in results.items():
        for key in ("pooled", "by_region", "by_station", "bootstrap"):
            res[key].to_csv(OUT / f"{name}_{key}.csv", index=key == "pooled")
        summary[name] = {k: res[k] for k in ("start", "end", "n_common", "n_stations")}
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(results)
    LOGGER.info("Ghi %s", (OUT / "README.md").relative_to(ROOT))


if __name__ == "__main__":
    main()
