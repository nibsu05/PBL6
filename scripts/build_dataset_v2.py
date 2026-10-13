r"""Dựng dataset v2: mảng ``[giờ, ô, đặc trưng]`` theo từng năm cho các ô đất 0,1° quanh Đà Nẵng mới.

Đầu vào (đã tải bằng các script ``extract_gee_*``):
- ``data/raw_data/gee/gsmap/grid/*.parquet``: nhãn (``hourlyPrecipRateGC``) và quan trắc thô.
- ``data/raw_data/gee/era5/grid/*.parquet``: ERA5 0,25°, nội suy song tuyến về tâm ô.
- ``data/processed/gee/static_cells.parquet``: đặc trưng tĩnh và tỉnh của từng ô.

Đầu ra trong ``data/processed/dataset_v2/``:
- ``{năm}.npy``: float32 ``[giờ, ô, đặc trưng]``, hàng ``t`` = khoảng ``[t, t+1h)`` UTC.
- ``{năm}_hours.npy``: mốc giờ ``datetime64[ns]`` (UTC, không gắn múi giờ).
- ``cells.parquet``: thứ tự ô, toạ độ, tỉnh, đặc trưng tĩnh.
- ``manifest.json``: tên/đơn vị/nhóm của đặc trưng, quy ước, thống kê QC từng năm, commit git.

Không tạo đặc trưng trễ hay cửa sổ ở đây; dataloader làm việc đó để thí nghiệm độ trễ
quan trắc chỉ cần đổi một tham số. Chạy:
    python scripts/build_dataset_v2.py --years 2015 2026
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
for p in (ROOT, SCRIPTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import argparse
import json
import logging
import subprocess
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from extract_gee_era5 import BANDS as ERA5_BANDS, era5_points
from src.dataset_v2 import (bilinear_weights, encode_cin, interpolate, neighbourhood_stats, relative_humidity,
                            time_features, to_cube)

GSMAP_DIR = ROOT / "data" / "raw_data" / "gee" / "gsmap" / "grid"
ERA5_DIR = ROOT / "data" / "raw_data" / "gee" / "era5" / "grid"
STATIC = ROOT / "data" / "processed" / "gee" / "static_cells.parquet"
OUT = ROOT / "data" / "processed" / "dataset_v2"
OCEAN_MAX = 0.5

# (tên, đơn vị, nhóm trong plan v2, mô tả)
FEATURES: list[tuple[str, str, str, str]] = [
    ("y_gsmap_gc_mm", "mm/h", "label", "Nhãn: GSMaP v8 hiệu chỉnh trạm"),
    ("label_permanent", "0/1", "meta", "1 nếu ảnh GSMaP là bản permanent"),
    ("gsmap_mm", "mm/h", "A1", "GSMaP thô tại ô (đầu vào quan trắc; dịch trễ ở dataloader)"),
    ("gsmap_nb5_mean_mm", "mm/h", "A1", "GSMaP thô, trung bình 5×5 ô"),
    ("gsmap_nb5_max_mm", "mm/h", "A1", "GSMaP thô, lớn nhất 5×5 ô"),
    ("t2m_c", "°C", "A0", "Nhiệt độ 2 m"), ("td2m_c", "°C", "A0", "Điểm sương 2 m"),
    ("rh2m_pct", "%", "A0", "Độ ẩm tương đối 2 m"), ("sp_hpa", "hPa", "A0", "Áp suất bề mặt"),
    ("mslp_hpa", "hPa", "A0", "Áp suất mực biển"), ("u10", "m/s", "A0", "Gió u 10 m"),
    ("v10", "m/s", "A0", "Gió v 10 m"), ("wspd10", "m/s", "A0", "Tốc độ gió 10 m"),
    ("tcc", "0-1", "A0", "Mây tổng"), ("lcc", "0-1", "A0", "Mây thấp"),
    ("mcc", "0-1", "A0", "Mây trung"), ("hcc", "0-1", "A0", "Mây cao"),
    ("cape", "J/kg", "A2", "CAPE"), ("cin_capped", "J/kg", "A2", "CIN, NaN→500 (không có LFC)"),
    ("has_lfc", "0-1", "A2", "Tỷ lệ nút có mực đối lưu tự do"), ("tcwv", "kg/m²", "A2", "Hơi nước cột"),
    ("kx", "K", "A2", "K-index"), ("tt", "K", "A2", "Total Totals"), ("blh", "m", "A2", "Độ cao lớp biên"),
    ("ivt_u", "kg/m/s", "A3", "Thông lượng ẩm tích phân, thành phần đông"),
    ("ivt_v", "kg/m/s", "A3", "Thông lượng ẩm tích phân, thành phần bắc"),
    ("ivt_mag", "kg/m/s", "A3", "Độ lớn IVT"),
    ("vimd_mmh", "mm/h", "A3", "Phân kỳ thông lượng ẩm (âm = hội tụ)"),
    ("u850", "m/s", "A3", "Gió u 850 hPa"), ("v850", "m/s", "A3", "Gió v 850 hPa"),
    ("q850_gkg", "g/kg", "A3", "Độ ẩm riêng 850 hPa"), ("t850_c", "°C", "A3", "Nhiệt độ 850 hPa"),
    ("w850_pas", "Pa/s", "A3", "Omega 850 hPa (âm = thăng)"), ("rh850_pct", "%", "A3", "RH 850 hPa"),
    ("u500", "m/s", "A3", "Gió u 500 hPa"), ("v500", "m/s", "A3", "Gió v 500 hPa"),
    ("q500_gkg", "g/kg", "A3", "Độ ẩm riêng 500 hPa"), ("t500_c", "°C", "A3", "Nhiệt độ 500 hPa"),
    ("w500_pas", "Pa/s", "A3", "Omega 500 hPa"), ("shear_850_500", "m/s", "A3", "Đứt gió 850–500 hPa"),
    ("era5_tp_mm", "mm/h", "G4", "Mưa ERA5 trong khoảng [t, t+1h) (mưa của mô hình số, không phải nhãn)"),
    ("swvl1", "m³/m³", "slow", "Độ ẩm đất lớp 1"),
    ("ctx_tcwv", "kg/m²", "B5", "TCWV trung bình 3×3 nút ERA5 (~0,75°)"),
    ("ctx_ivt_mag", "kg/m/s", "B5", "IVT trung bình 3×3 nút ERA5"),
    ("cold_surge_dp_hpa", "hPa", "B1", "MSLP Hà Nội − MSLP Đà Nẵng (chỉ số không khí lạnh)"),
    ("dp_tonkin_south_hpa", "hPa", "B1", "MSLP vịnh Bắc Bộ − MSLP Nam Trung Bộ"),
    ("sst_region_c", "°C", "B4", "SST trung bình vùng biển 15,5–16,5°B, 108,75–109,5°Đ"),
    ("sin_hour", "", "A0", "sin giờ địa phương"), ("cos_hour", "", "A0", "cos giờ địa phương"),
    ("sin_doy", "", "A0", "sin ngày-trong-năm"), ("cos_doy", "", "A0", "cos ngày-trong-năm"),
]
NAMES = [f[0] for f in FEATURES]
LOGGER = logging.getLogger("build_dataset_v2")


def files_overlapping(folder: Path, start: pd.Timestamp, end: pd.Timestamp) -> list[Path]:
    """Các khối có khoảng [đầu, cuối) giao [start, end]."""
    picked = []
    for path in sorted(folder.glob("*.parquet")):
        c0, c1 = (pd.Timestamp(datetime.strptime(s, "%Y%m%dT%H")) for s in path.stem.split("_"))
        if c0 <= end and c1 > start:
            picked.append(path)
    return picked


def era5_node_features(cube: np.ndarray) -> tuple[np.ndarray, list[str]]:
    """``[giờ+1, nút, băng ERA5]`` (đơn vị gốc) → biến dẫn xuất tại nút cho các giờ của năm.

    Giờ cuối của ``cube`` chỉ dùng để lấy mưa ERA5 của khoảng cuối cùng.
    """
    b = {name: cube[..., k] for k, name in enumerate(ERA5_BANDS)}
    now = slice(0, cube.shape[0] - 1)
    nxt = slice(1, cube.shape[0])
    cin_capped, has_lfc = encode_cin(b["convective_inhibition"][now])
    # CIN mask chỉ có nghĩa "không có LFC" khi giờ đó có dữ liệu ERA5; giờ thiếu hẳn thì giữ NaN.
    missing = ~np.isfinite(b["convective_available_potential_energy"][now])
    cin_capped[missing] = np.nan
    has_lfc[missing] = np.nan
    out = {
        "t2m_c": b["temperature_2m"][now] - 273.15, "td2m_c": b["dewpoint_temperature_2m"][now] - 273.15,
        "rh2m_pct": relative_humidity(b["temperature_2m"][now], b["dewpoint_temperature_2m"][now]),
        "sp_hpa": b["surface_pressure"][now] / 100, "mslp_hpa": b["mean_sea_level_pressure"][now] / 100,
        "u10": b["u_component_of_wind_10m"][now], "v10": b["v_component_of_wind_10m"][now],
        "wspd10": np.hypot(b["u_component_of_wind_10m"][now], b["v_component_of_wind_10m"][now]),
        "tcc": b["total_cloud_cover"][now], "lcc": b["low_cloud_cover"][now],
        "mcc": b["medium_cloud_cover"][now], "hcc": b["high_cloud_cover"][now],
        "cape": b["convective_available_potential_energy"][now], "cin_capped": cin_capped, "has_lfc": has_lfc,
        "tcwv": b["total_column_water_vapour"][now], "kx": b["k_index"][now], "tt": b["total_totals_index"][now],
        "blh": b["boundary_layer_height"][now],
        "ivt_u": b["vertical_integral_of_eastward_water_vapour_flux"][now],
        "ivt_v": b["vertical_integral_of_northward_water_vapour_flux"][now],
        "vimd_mmh": b["vertical_integral_of_divergence_of_moisture_flux"][now] * 3600,
        "u850": b["u_component_of_wind_850hPa"][now], "v850": b["v_component_of_wind_850hPa"][now],
        "q850_gkg": b["specific_humidity_850hPa"][now] * 1000, "t850_c": b["temperature_850hPa"][now] - 273.15,
        "w850_pas": b["vertical_velocity_850hPa"][now], "rh850_pct": b["relative_humidity_850hPa"][now],
        "u500": b["u_component_of_wind_500hPa"][now], "v500": b["v_component_of_wind_500hPa"][now],
        "q500_gkg": b["specific_humidity_500hPa"][now] * 1000, "t500_c": b["temperature_500hPa"][now] - 273.15,
        "w500_pas": b["vertical_velocity_500hPa"][now],
        # tp tại mốc T là tích lũy (T−1h, T] → thuộc hàng T−1h
        "era5_tp_mm": np.maximum(b["total_precipitation"][nxt], 0) * 1000,
        "swvl1": b["volumetric_soil_water_layer_1"][now],
    }
    out["ivt_mag"] = np.hypot(out["ivt_u"], out["ivt_v"])
    out["shear_850_500"] = np.hypot(out["u500"] - out["u850"], out["v500"] - out["v850"])
    names = list(out)
    return np.stack([out[n] for n in names], axis=-1).astype(np.float32), names


def node_context(field: np.ndarray, node_lat: np.ndarray, node_lon: np.ndarray) -> np.ndarray:
    """Trung bình 3×3 nút ERA5 quanh mỗi nút; ``field`` dạng ``[giờ, nút]``."""
    mean, _ = neighbourhood_stats(field, node_lat, node_lon, radius=1, res=0.25)
    return mean


def build_year(year: int, cells: pd.DataFrame, out_mask: np.ndarray,
               sink: Callable[[int, np.ndarray, pd.DatetimeIndex], None] | None = None) -> dict:
    hours = pd.date_range(f"{year}-01-01", f"{year + 1}-01-01", freq="h", inclusive="left")
    gs_files = files_overlapping(GSMAP_DIR, hours[0], hours[-1])
    era_files = files_overlapping(ERA5_DIR, hours[0], hours[-1] + pd.Timedelta(hours=1))
    if not gs_files or not era_files:
        raise FileNotFoundError(f"Thiếu dữ liệu GSMaP/ERA5 cho năm {year}")

    # GSMaP trên toàn lưới (cần cho thống kê lân cận)
    gs = pd.concat([pd.read_parquet(f) for f in gs_files], ignore_index=True)
    gs = gs.drop_duplicates(["site", "time_start_utc"])
    gcube = to_cube(gs, "time_start_utc", hours, cells["site"].tolist(),
                    ["hourlyPrecipRateGC_mm", "hourlyPrecipRate_mm", "permanent"])
    nb_mean, nb_max = neighbourhood_stats(gcube[..., 1], cells["lat"].to_numpy(), cells["lon"].to_numpy())

    # ERA5 tại nút → biến dẫn xuất → nội suy về ô
    pts = era5_points()
    nodes = pts[pts["site"].str.startswith("e")].reset_index(drop=True)
    hours_ext = hours.append(pd.DatetimeIndex([hours[-1] + pd.Timedelta(hours=1)]))
    era = pd.concat([pd.read_parquet(f) for f in era_files], ignore_index=True).drop_duplicates(["site", "time_utc"])
    ecube = to_cube(era, "time_utc", hours_ext, pts["site"].tolist(), list(ERA5_BANDS))
    node_idx = np.arange(len(nodes))
    node_feat, node_names = era5_node_features(ecube[:, node_idx, :])
    nlat, nlon = nodes["lat"].to_numpy(), nodes["lon"].to_numpy()
    ctx = np.stack([node_context(node_feat[..., node_names.index("tcwv")], nlat, nlon),
                    node_context(node_feat[..., node_names.index("ivt_mag")], nlat, nlon)], axis=-1)
    node_all = np.concatenate([node_feat, ctx], axis=-1)
    all_names = node_names + ["ctx_tcwv", "ctx_ivt_mag"]
    idx, w = bilinear_weights(cells["lat"].to_numpy(), cells["lon"].to_numpy(), nlat, nlon)
    cell_era = interpolate(node_all, idx, w)

    # chuỗi vùng (giống nhau cho mọi ô)
    site_pos = {s: k for k, s in enumerate(pts["site"])}
    mslp = ecube[:-1, :, ERA5_BANDS.index("mean_sea_level_pressure")] / 100
    sst = ecube[:-1, :, ERA5_BANDS.index("sea_surface_temperature")] - 273.15
    sea_box = [site_pos[s] for s, la, lo in zip(pts["site"], pts["lat"], pts["lon"])
               if s.startswith("e") and 15.5 <= la <= 16.5 and 108.75 <= lo <= 109.5]
    regional = {
        "cold_surge_dp_hpa": mslp[:, site_pos["syn_hanoi"]] - mslp[:, site_pos["e16.00_108.25"]],
        "dp_tonkin_south_hpa": mslp[:, site_pos["syn_tonkin"]] - mslp[:, site_pos["syn_south"]],
        "sst_region_c": np.nanmean(sst[:, sea_box], axis=1),
    }
    tfeat = time_features(hours)

    n_out = int(out_mask.sum())
    X = np.empty((len(hours), n_out, len(NAMES)), dtype=np.float32)
    sources = {
        "y_gsmap_gc_mm": gcube[..., 0], "label_permanent": gcube[..., 2], "gsmap_mm": gcube[..., 1],
        "gsmap_nb5_mean_mm": nb_mean, "gsmap_nb5_max_mm": nb_max,
    }
    for k, name in enumerate(NAMES):
        if name in sources:
            X[..., k] = sources[name][:, out_mask]
        elif name in all_names:
            X[..., k] = cell_era[:, out_mask, all_names.index(name)]
        elif name in regional:
            X[..., k] = regional[name][:, None]
        else:
            X[..., k] = tfeat[:, ["sin_hour", "cos_hour", "sin_doy", "cos_doy"].index(name)][:, None]

    if sink is None:
        np.save(OUT / f"{year}.npy", X)
        np.save(OUT / f"{year}_hours.npy", hours.values.astype("datetime64[ns]"))
    else:
        sink(year, X, hours)
    out_cells = cells[out_mask]
    dn = (out_cells["province"] == "Đà Nẵng").to_numpy()
    label = X[..., NAMES.index("y_gsmap_gc_mm")]
    return {
        "year": year, "hours": len(hours), "cells": n_out,
        "nan_frac": {n: round(float(np.isnan(X[..., k]).mean()), 5) for k, n in enumerate(NAMES)
                     if np.isnan(X[..., k]).any()},
        "label_permanent_frac": round(float(np.nanmean(X[..., NAMES.index("label_permanent")])), 4),
        "danang_label_total_mm": round(float(np.nansum(label[:, dn]) / max(dn.sum(), 1)), 1),
        "danang_era5_tp_total_mm": round(float(np.nansum(X[..., NAMES.index("era5_tp_mm")][:, dn]) / max(dn.sum(), 1)), 1),
        "label_max_mm_h": round(float(np.nanmax(label)), 1),
    }


def main() -> None:
    global OUT
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", nargs=2, type=int, default=[2015, 2026])
    parser.add_argument("--out", type=Path, default=OUT, help="Thư mục dataset đầu ra")
    parser.add_argument("--provinces", nargs="+", help="Chỉ lưu ô thuộc các tỉnh này; vẫn tính lân cận trên toàn lưới")
    parser.add_argument("--cell-major-only", action="store_true",
                        help="Ghi trực tiếp memmap [ô, giờ, đặc trưng], không lưu thêm mảng từng năm (~6 GB)")
    args = parser.parse_args()
    if args.years[0] > args.years[1]:
        parser.error("Năm bắt đầu phải <= năm kết thúc")
    OUT = args.out
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    OUT.mkdir(parents=True, exist_ok=True)
    cells = pd.read_parquet(STATIC).sort_values(["lat", "lon"]).reset_index(drop=True)
    out_mask = (cells["ocean_frac"] < OCEAN_MAX).to_numpy()
    if args.provinces:
        out_mask = out_mask & cells["province"].isin(args.provinces).to_numpy()
    if not out_mask.any():
        parser.error("Không có ô đất trong vùng đã chọn")
    cells[out_mask].reset_index(drop=True).to_parquet(OUT / "cells.parquet", index=False)

    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"years": {}}
    sink = None
    cube = None
    if args.cell_major_only:
        # Giữ nguyên phép biến đổi; chỉ đổi đích lưu để máy ít dung lượng không cần hai bản cube.
        hours_all = pd.date_range(f"{args.years[0]}-01-01", f"{args.years[1] + 1}-01-01",
                                  freq="h", inclusive="left")
        cube = np.lib.format.open_memmap(OUT / "cube_cell_major.partial.npy", mode="w+", dtype=np.float32,
                                        shape=(int(out_mask.sum()), len(hours_all), len(NAMES)))
        def sink(year: int, values: np.ndarray, hours: pd.DatetimeIndex) -> None:
            start = hours_all.get_loc(hours[0])
            cube[:, start:start + len(hours), :] = values.transpose(1, 0, 2)
            cube.flush()
    for year in range(args.years[0], args.years[1] + 1):
        try:
            qc = build_year(year, cells, out_mask, sink=sink)
        except FileNotFoundError as exc:
            if args.cell_major_only:
                raise
            LOGGER.warning("%s", exc)
            continue
        manifest["years"][str(year)] = qc
        LOGGER.info("Năm %d: %d giờ × %d ô; mưa nhãn TB Đà Nẵng %.0f mm (ERA5 %.0f mm); NaN: %s", year, qc["hours"],
                    qc["cells"], qc["danang_label_total_mm"], qc["danang_era5_tp_total_mm"],
                    {k: v for k, v in qc["nan_frac"].items() if v > 0.001})
    if args.cell_major_only:
        cube.flush()
        del cube
        (OUT / "cube_cell_major.partial.npy").replace(OUT / "cube_cell_major.npy")
        np.save(OUT / "hours_all.npy", hours_all.values.astype("datetime64[ns]"))
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = None
    manifest.update({
        "version": "v2", "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git_commit": commit,
        "time_convention": "hàng t = khoảng [t, t+1h) UTC; biến tức thời ERA5 lấy tại t; mưa ERA5 dịch từ mốc t+1h",
        "label": "y_gsmap_gc_mm (GSMaP v8 hiệu chỉnh trạm, quyết định Cổng 1 ngày 11/10/2026)",
        "cells": f"{int(out_mask.sum())} ô đất (tỷ lệ biển < {OCEAN_MAX}) trong hộp 14,6–16,5°B × 107–109°Đ",
        "selected_provinces": args.provinces,
        "features": [{"name": n, "unit": u, "group": g, "description": d} for n, u, g, d in FEATURES],
    })
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
