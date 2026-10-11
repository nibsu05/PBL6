r"""Đặc trưng tĩnh cho từng ô 0,1° (cùng lưới với nhãn GSMaP), từ Copernicus DEM trên Earth Engine.

Mỗi ô: độ cao trung bình / độ lệch chuẩn / lớn nhất, tỷ lệ biển và tỷ lệ mặt nước
(band ``WBM``). Tính thêm tại máy:

- ``coast_dist_km``: khoảng cách từ tâm ô tới tâm ô biển gần nhất (ô có tỷ lệ
  biển ≥ 0,5); ô biển nhận giá trị âm theo khoảng cách tới ô đất gần nhất.
- ``ne_upslope_m``: chênh độ cao trung bình giữa ô và ô lân cận phía đông bắc
  (hướng gió mùa đông bắc thổi tới); dương nghĩa là sườn đón gió.

Chạy:
    python scripts/extract_gee_static.py --project MY_PROJECT
"""

from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
for p in (ROOT, SCRIPTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import argparse
import logging

import numpy as np
import pandas as pd

from extract_gee_precip import DEFAULT_BBOX, grid_points
from src.admin_regions import OLD_TO_NEW

DEM_COLLECTION = "COPERNICUS/DEM/GLO30_2024_1"
GAUL = "FAO/GAUL/2015/level1"  # ranh giới cũ, đủ để ghép thành tỉnh mới
OUT = ROOT / "data" / "processed" / "gee" / "static_cells.parquet"
EARTH_KM_PER_DEG = 111.32

LOGGER = logging.getLogger("extract_static")


def _km(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Khoảng cách xấp xỉ phẳng (đủ chính xác ở quy mô vài trăm km)."""
    dlat = (lat2 - lat1) * EARTH_KM_PER_DEG
    dlon = (lon2 - lon1) * EARTH_KM_PER_DEG * np.cos(np.deg2rad((lat1 + lat2) / 2))
    return np.hypot(dlat, dlon)


def derived_features(cells: pd.DataFrame, res: float = 0.1) -> pd.DataFrame:
    out = cells.copy()
    sea = out["ocean_frac"].to_numpy() >= 0.5
    lat, lon = out["lat"].to_numpy(), out["lon"].to_numpy()
    dist = _km(lat[:, None], lon[:, None], lat[None, :], lon[None, :])
    to_sea = np.where(sea[None, :], dist, np.inf).min(axis=1) if sea.any() else np.full(len(out), np.nan)
    to_land = np.where(~sea[None, :], dist, np.inf).min(axis=1) if (~sea).any() else np.full(len(out), np.nan)
    out["coast_dist_km"] = np.where(sea, -to_land, to_sea)
    key = {(round(a, 2), round(b, 2)): e for a, b, e in zip(lat, lon, out["elev_mean_m"])}
    out["ne_upslope_m"] = [e - key.get((round(a + res, 2), round(b + res, 2)), np.nan)
                           for a, b, e in zip(lat, lon, out["elev_mean_m"])]
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", required=True)
    parser.add_argument("--bbox", nargs=4, type=float, default=DEFAULT_BBOX, metavar=("S", "N", "W", "E"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import ee
    ee.Initialize(project=args.project)

    cells = grid_points(tuple(args.bbox))
    half = 0.05
    features = ee.FeatureCollection([
        ee.Feature(ee.Geometry.Rectangle([lo - half, la - half, lo + half, la + half]), {"site": s})
        for s, la, lo in zip(cells["site"], cells["lat"], cells["lon"])
    ])
    coll = ee.ImageCollection(DEM_COLLECTION)
    dem = coll.select("DEM").mosaic().rename("elev")
    wbm = coll.select("WBM").mosaic()
    image = (dem.unmask(0)
             .addBands(wbm.eq(1).unmask(1).rename("ocean"))      # ngoài phạm vi DEM coi là biển
             .addBands(wbm.gt(0).unmask(1).rename("water")))
    reducer = (ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True)
               .combine(ee.Reducer.max(), sharedInputs=True))
    stats = image.reduceRegions(features, reducer, scale=90).getInfo()["features"]

    # Tỉnh chứa tâm ô (ranh giới cũ GAUL 2015 → tỉnh mới); ô ngoài đất liền để trống.
    centres = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([lo, la]), {"site": s})
                                    for s, la, lo in zip(cells["site"], cells["lat"], cells["lon"])])
    gaul = ee.FeatureCollection(GAUL).filter(ee.Filter.eq("ADM0_NAME", "Viet Nam"))
    joined = ee.Join.saveFirst("prov").apply(centres, gaul, ee.Filter.intersects(leftField=".geo", rightField=".geo"))
    prov_rows = joined.map(lambda f: ee.Feature(None, {"site": f.get("site"),
                                                       "province_old": ee.Feature(f.get("prov")).get("ADM1_NAME")}))
    provinces = {p["properties"]["site"]: p["properties"].get("province_old") for p in prov_rows.getInfo()["features"]}
    rows = []
    for f in stats:
        p = f["properties"]
        rows.append({"site": p["site"], "elev_mean_m": p["elev_mean"], "elev_std_m": p["elev_stdDev"],
                     "elev_max_m": p["elev_max"], "ocean_frac": p["ocean_mean"], "water_frac": p["water_mean"]})
    table = cells.merge(pd.DataFrame(rows), on="site", how="left")
    table["province_old"] = table["site"].map(provinces)
    unknown = set(table["province_old"].dropna()) - set(OLD_TO_NEW)
    if unknown:
        raise ValueError(f"Tên tỉnh GAUL chưa có trong bảng ánh xạ: {unknown}")
    table["province"] = table["province_old"].map(OLD_TO_NEW)
    table = derived_features(table)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(OUT, index=False)
    land = table[table["ocean_frac"] < 0.5]
    LOGGER.info("Ghi %s: %d ô (%d ô đất), độ cao đất %.0f–%.0f m", OUT.relative_to(ROOT), len(table), len(land),
                land["elev_mean_m"].min(), land["elev_mean_m"].max())


if __name__ == "__main__":
    main()
