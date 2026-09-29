"""Hợp nhất dữ liệu khí tượng Đà Nẵng theo giờ, kèm kiểm tra độ phủ dữ liệu.

Chạy từ thư mục dự án::

    python -m src.merge_raw_data --raw-dir data/raw_data

Mặc định ưu tiên NetCDF ERA5 và lấy ô lưới gần Đà Nẵng nhất. Với SST, nếu ô
lưới gần nhất nằm trên đất (toàn giá trị NaN), chọn ô biển hợp lệ gần nhất.
Các CSV ERA5 cũ là *trung bình không gian*, nên chỉ dùng khi không có NetCDF
hoặc khi người chạy chủ động chọn ``--era5-source csv``.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


LOGGER = logging.getLogger(__name__)
LOCAL_TZ = "Asia/Ho_Chi_Minh"
DANANG_LAT = 16.0544
DANANG_LON = 108.2022

SURFACE_COLUMNS = (
    "temperature_2m",
    "relative_humidity_2m",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "precipitation",
)
CORE_ERA5_COLUMNS = (
    "sea_surface_temperature",
    "u_850",
    "v_850",
    "specific_humidity_850",
)
OPTIONAL_ERA5_COLUMNS = ("cape", "cin", "tcwv")

# Tên biến viết ngắn của CDS/ERA5 và tên từ các CSV đã trích xuất trước đây.
ERA5_ALIASES = {
    "sea_surface_temperature": ("sea_surface_temperature", "sst"),
    "u_850": ("u_850", "u850", "u_wind_850hpa", "u_component_of_wind", "u"),
    "v_850": ("v_850", "v850", "v_wind_850hpa", "v_component_of_wind", "v"),
    "specific_humidity_850": (
        "specific_humidity_850", "specific_humidity_850hpa", "specific_humidity", "q"
    ),
    "cape": ("cape", "convective_available_potential_energy"),
    "cin": ("cin", "convective_inhibition"),
    "tcwv": ("tcwv", "total_column_water_vapour", "total_column_water_vapor"),
}
SEASON_TO_MONTH = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4,
    "AMJ": 5, "MJJ": 6, "JJA": 7, "JAS": 8,
    "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
}


def _resolve_raw_dir(raw_dir: str | Path) -> Path:
    path = Path(raw_dir)
    if path.exists():
        return path
    # Repo hiện có đặt dữ liệu ở data/raw_data; giữ API mặc định theo đề bài.
    if str(path).replace("\\", "/") == "raw_data" and Path("data/raw_data").exists():
        return Path("data/raw_data")
    raise FileNotFoundError(f"Không tìm thấy thư mục dữ liệu thô: {path}")


def _find_file(raw_dir: Path, exact: str, patterns: tuple[str, ...]) -> Path:
    preferred = raw_dir / exact
    if preferred.exists():
        return preferred
    for pattern in patterns:
        matches = sorted(raw_dir.glob(pattern))
        if matches:
            if len(matches) > 1:
                LOGGER.warning("Có %d file %s; chọn %s", len(matches), pattern, matches[-1].name)
            return matches[-1]
    raise FileNotFoundError(f"Không tìm thấy {exact} hoặc {patterns} trong {raw_dir}")


def _to_hourly_index(frame: pd.DataFrame, source: str) -> pd.DataFrame:
    """Giữ mốc UTC thật; datetime không có timezone được hiểu là UTC."""
    if "datetime" not in frame:
        raise ValueError(f"{source}: thiếu cột datetime")
    result = frame.copy()
    result["datetime"] = pd.to_datetime(result["datetime"], utc=True, errors="coerce")
    if result["datetime"].isna().any():
        raise ValueError(f"{source}: có timestamp không đọc được")
    if result["datetime"].ne(result["datetime"].dt.floor("h")).any():
        raise ValueError(f"{source}: có mốc không nằm đúng đầu giờ; cần xử lý nguồn trước")
    result = result.set_index("datetime").sort_index()
    if result.index.has_duplicates:
        conflicted = result.groupby(level=0).nunique(dropna=False).gt(1).any(axis=1)
        if conflicted.any():
            raise ValueError(f"{source}: {int(conflicted.sum())} timestamp trùng nhưng khác giá trị")
        LOGGER.warning("%s: bỏ %d bản ghi trùng hệt", source, int(result.index.duplicated().sum()))
        result = result.loc[~result.index.duplicated(keep="first")]
    return result


def _read_surface(raw_dir: Path) -> pd.DataFrame:
    path = _find_file(raw_dir, "openmeteo_surface.csv", ("openmeteo*.csv",))
    frame = pd.read_csv(path)
    absent = sorted(set(SURFACE_COLUMNS) - set(frame.columns))
    if absent:
        raise ValueError(f"{path}: thiếu cột Open-Meteo {absent}")
    frame = _to_hourly_index(frame[["datetime", *SURFACE_COLUMNS]], str(path))
    for column in SURFACE_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame.empty:
        raise ValueError(f"{path}: dữ liệu rỗng")
    return frame


def _lookup_alias(names: Any, canonical: str) -> str | None:
    by_lower = {str(name).lower(): str(name) for name in names}
    for alias in ERA5_ALIASES[canonical]:
        if alias in by_lower:
            return by_lower[alias]
    return None


def _choose_850_level(array: Any) -> Any:
    """Loại chiều áp suất, không vô tình lấy một tầng khác 850 hPa."""
    for dimension in ("pressure_level", "level", "isobaricInhPa", "plev"):
        if dimension not in array.dims:
            continue
        values = np.asarray(array[dimension].values, dtype=float)
        target = 85000.0 if np.nanmax(values) > 2000 else 850.0
        index = int(np.nanargmin(abs(values - target)))
        if not np.isclose(values[index], target):
            raise ValueError(f"Không có tầng 850 hPa trong chiều {dimension}: {values.tolist()}")
        array = array.isel({dimension: index})
    return array


def _choose_expver(array: Any) -> Any:
    """Ghép bản ERA5 expver=1/5 theo giá trị có sẵn, không lấy trung bình."""
    if "expver" not in array.dims:
        return array
    versions = np.asarray(array["expver"].values)
    order = sorted(range(len(versions)), key=lambda i: 0 if str(versions[i]) == "1" else 1)
    combined = array.isel(expver=order[0], drop=True)
    for position in order[1:]:
        combined = combined.combine_first(array.isel(expver=position, drop=True))
    return combined


def _nearest_valid_point(
    array: Any, canonical: str, preferred: dict[str, float] | None = None
) -> tuple[Any, dict[str, float]]:
    lat_dim = next((name for name in ("latitude", "lat") if name in array.dims), None)
    lon_dim = next((name for name in ("longitude", "lon") if name in array.dims), None)
    if lat_dim is None or lon_dim is None:
        raise ValueError(f"{canonical}: thiếu chiều latitude/longitude trong NetCDF")
    latitudes = np.asarray(array[lat_dim].values, dtype=float)
    longitudes = np.asarray(array[lon_dim].values, dtype=float)
    if latitudes.ndim != 1 or longitudes.ndim != 1:
        raise ValueError(f"{canonical}: chỉ hỗ trợ lưới ERA5 latitude/longitude 1D")
    lat_grid, lon_grid = np.meshgrid(latitudes, longitudes, indexing="ij")
    lon_delta = ((lon_grid - DANANG_LON + 180.0) % 360.0) - 180.0
    distance2 = (lat_grid - DANANG_LAT) ** 2 + (lon_delta * np.cos(np.deg2rad(DANANG_LAT))) ** 2

    # SST ở ngay điểm thành phố thường là NaN vì đất liền. Chọn ô biển gần nhất
    # có ít nhất một quan trắc, rồi ghi lại tọa độ thực sự đã dùng.
    valid = array.notnull().any(dim=[d for d in array.dims if d not in (lat_dim, lon_dim)])
    valid_grid = np.asarray(valid.transpose(lat_dim, lon_dim).values, dtype=bool)
    if preferred is not None:
        prior_lat = int(np.argmin(abs(latitudes - preferred["latitude"])))
        prior_lon = int(np.argmin(abs(longitudes - preferred["longitude"])))
        if valid_grid[prior_lat, prior_lon]:
            selected = array.isel({lat_dim: prior_lat, lon_dim: prior_lon})
            point = {"latitude": float(latitudes[prior_lat]), "longitude": float(longitudes[prior_lon])}
            return selected, point
    if valid_grid.any():
        distance2 = np.where(valid_grid, distance2, np.inf)
    else:
        LOGGER.warning("%s: tất cả ô lưới đều NaN; lấy ô gần nhất để ghi nhận khoảng trống", canonical)
    lat_pos, lon_pos = np.unravel_index(int(np.argmin(distance2)), distance2.shape)
    selected = array.isel({lat_dim: int(lat_pos), lon_dim: int(lon_pos)})
    point = {"latitude": float(latitudes[lat_pos]), "longitude": float(longitudes[lon_pos])}
    return selected, point


def _extract_nc_file(path: Path, xr: Any, selected_points: dict[str, dict[str, float]]) -> dict[str, pd.Series]:
    fields: dict[str, pd.Series] = {}
    with xr.open_dataset(path, engine="netcdf4") as dataset:
        time_dim = next((name for name in ("valid_time", "time") if name in dataset.dims), None)
        if time_dim is None:
            raise ValueError(f"{path}: thiếu chiều valid_time/time")
        times = pd.DatetimeIndex(pd.to_datetime(dataset[time_dim].values, utc=True))
        for canonical in (*CORE_ERA5_COLUMNS, *OPTIONAL_ERA5_COLUMNS):
            original = _lookup_alias(dataset.data_vars, canonical)
            if original is None:
                continue
            array = dataset[original]
            if canonical in ("u_850", "v_850", "specific_humidity_850"):
                array = _choose_850_level(array)
            array = _choose_expver(array)
            array, point = _nearest_valid_point(array, canonical, selected_points.get(canonical))
            previous = selected_points.setdefault(canonical, point)
            if previous != point:
                LOGGER.warning("%s: ô lưới %s khác tháng trước %s", path.name, point, previous)
            for dimension in tuple(array.dims):
                if dimension != time_dim:
                    if array.sizes[dimension] != 1:
                        raise ValueError(f"{path}: chiều ngoài thời gian {dimension} có >1 phần tử")
                    array = array.isel({dimension: 0}, drop=True)
            values = np.asarray(array.transpose(time_dim).values, dtype=float)
            if canonical == "sea_surface_temperature":
                unit = str(array.attrs.get("units", "")).lower()
                median = float(np.nanmedian(values)) if np.isfinite(values).any() else np.nan
                if unit in ("k", "kelvin") or (not unit and 200 < median < 350):
                    values = values - 273.15  # K -> °C; Open-Meteo cũng dùng °C.
            fields[canonical] = pd.Series(values, index=times, name=canonical)
    return fields


def _read_era5_nc(raw_dir: Path, diagnostics: dict[str, Any]) -> pd.DataFrame:
    try:
        import netCDF4  # noqa: F401 - kiểm tra engine NetCDF4 có sẵn
        import xarray as xr
    except ImportError as exc:
        raise ImportError(
            "Đọc ERA5 NetCDF cần xarray và netCDF4. Cài data/requirements.txt "
            "hoặc chọn --era5-source csv (CSV cũ là trung bình không gian)."
        ) from exc

    paths = sorted(raw_dir.rglob("*.nc"))
    if not paths:
        raise FileNotFoundError(f"Không có file .nc trong {raw_dir}")
    streams: dict[str, list[pd.Series]] = {}
    selected_points: dict[str, dict[str, float]] = {}
    for number, path in enumerate(paths, start=1):
        fields = _extract_nc_file(path, xr, selected_points)
        if not fields:
            LOGGER.warning("Bỏ qua %s: không có biến ERA5 đã biết", path)
        for name, values in fields.items():
            streams.setdefault(name, []).append(values)
        if number % 25 == 0 or number == len(paths):
            LOGGER.info("Đã đọc %d/%d file NetCDF", number, len(paths))
    if not streams:
        raise ValueError("Không tìm thấy biến ERA5 phù hợp trong các file NetCDF")
    columns = {}
    for name, parts in streams.items():
        values = pd.concat(parts).sort_index()
        if values.index.has_duplicates:
            conflicts = values.groupby(level=0).nunique(dropna=False).gt(1)
            if conflicts.any():
                raise ValueError(f"ERA5 {name}: {int(conflicts.sum())} timestamp trùng khác giá trị")
            values = values.loc[~values.index.duplicated(keep="first")]
        columns[name] = values
    diagnostics["era5_mode"] = "netcdf_nearest_grid_point"
    diagnostics["era5_files"] = len(paths)
    diagnostics["era5_selected_grid_points"] = selected_points
    return pd.DataFrame(columns).sort_index()


def _read_era5_csv(raw_dir: Path, diagnostics: dict[str, Any]) -> pd.DataFrame:
    """Chỉ dùng fallback chủ động: các CSV của repo là trung bình cả vùng."""
    paths = sorted(raw_dir.glob("era5*.csv"))
    if not paths:
        raise FileNotFoundError(f"Không có ERA5 CSV trong {raw_dir}")
    columns: dict[str, pd.Series] = {}
    for path in paths:
        frame = _to_hourly_index(pd.read_csv(path), str(path))
        for canonical in (*CORE_ERA5_COLUMNS, *OPTIONAL_ERA5_COLUMNS):
            original = _lookup_alias(frame.columns, canonical)
            if original is None:
                continue
            if canonical in columns:
                raise ValueError(f"Hai CSV ERA5 cùng cung cấp {canonical}; cần chọn một nguồn")
            columns[canonical] = pd.to_numeric(frame[original], errors="coerce")
    if not columns:
        raise ValueError("Các CSV ERA5 không có cột đã biết")
    diagnostics["era5_mode"] = "csv_spatial_mean_not_point"
    diagnostics["era5_files"] = len(paths)
    LOGGER.warning("Đang dùng ERA5 CSV trung bình không gian; khác với trích xuất ô lưới Đà Nẵng")
    return pd.DataFrame(columns).sort_index()


def _read_oni_monthly(raw_dir: Path) -> pd.Series:
    path = _find_file(raw_dir, "oni_index.txt", (
        "oni_index.csv", "enso_oni*.csv", "*oni*.txt", "*oni*.csv"
    ))
    frame = pd.read_csv(path, sep=r"\s+" if path.suffix.lower() == ".txt" else ",")
    names = {str(column).lower(): column for column in frame.columns}
    value_col = next((names[name] for name in ("oni_anom", "anom", "oni", "oni_index") if name in names), None)
    if value_col is None:
        raise ValueError(f"{path}: thiếu cột ANOM/oni_anom")
    values = pd.to_numeric(frame[value_col], errors="coerce")

    if {"seas", "yr"}.issubset(names):
        month = frame[names["seas"]].astype(str).str.upper().map(SEASON_TO_MONTH)
        year = pd.to_numeric(frame[names["yr"]], errors="coerce")
        valid = year.notna() & month.notna() & values.notna()
        year = year.loc[valid].astype(int)
        month = month.loc[valid].astype(int)
        values = values.loc[valid]
        periods = pd.PeriodIndex.from_fields(year=year, month=month, freq="M")
    elif {"year", "month"}.issubset(names):
        year = pd.to_numeric(frame[names["year"]], errors="coerce")
        month = pd.to_numeric(frame[names["month"]], errors="coerce")
        valid = year.notna() & month.notna() & values.notna()
        year = year.loc[valid].astype(int)
        month = month.loc[valid].astype(int)
        values = values.loc[valid]
        periods = pd.PeriodIndex.from_fields(year=year, month=month, freq="M")
    else:
        time_col = next((names[name] for name in ("datetime", "date", "time") if name in names), None)
        if time_col is None:
            raise ValueError(f"{path}: cần SEAS/YR, year/month hoặc datetime")
        # File ONI đã được trải ra theo giờ có mốc UTC. Lấy tháng UTC gốc,
        # rồi gán ONI theo tháng lịch địa phương từ 00:00 ngày đầu tháng.
        dates = pd.to_datetime(frame[time_col], utc=True, errors="coerce")
        if dates.isna().any():
            raise ValueError(f"{path}: ngày ONI không hợp lệ")
        periods = dates.dt.tz_localize(None).dt.to_period("M")

    monthly = pd.DataFrame({"period": periods, "oni_anom": values}).dropna()
    if monthly.empty:
        raise ValueError(f"{path}: không có giá trị ONI hợp lệ")
    conflicts = monthly.groupby("period")["oni_anom"].nunique().gt(1)
    if conflicts.any():
        raise ValueError(f"{path}: {int(conflicts.sum())} tháng ONI có nhiều giá trị khác nhau")
    return monthly.groupby("period")["oni_anom"].first().sort_index()


def _missing_blocks(index: pd.DatetimeIndex, reference: pd.DatetimeIndex) -> dict[str, Any]:
    observed = pd.DatetimeIndex(index.unique()).sort_values()
    missing = reference.difference(observed)
    if missing.empty:
        return {"missing_hours": 0, "blocks": []}
    group = pd.Series(missing).diff().ne(pd.Timedelta(hours=1)).cumsum()
    table = pd.Series(missing).groupby(group).agg(["min", "max", "size"])
    blocks = [
        {"start_utc": row["min"].isoformat(), "end_utc": row["max"].isoformat(),
         "hours": int(row["size"])}
        for _, row in table.iterrows()
    ]
    return {"missing_hours": len(missing), "blocks": blocks}


def _interpolate_short(series: pd.Series, max_hours: int) -> pd.Series:
    """Chỉ nội suy lỗ trống có 2 đầu và độ dài <= ngưỡng; không lấp mép/gap dài."""
    if max_hours <= 0 or not series.isna().any():
        return series
    missing = series.isna()
    groups = missing.ne(missing.shift(fill_value=False)).cumsum()
    short = missing & missing.groupby(groups).transform("sum").le(max_hours)
    candidate = series.interpolate(method="time", limit_area="inside")
    return series.where(~short, candidate)


def _interpolate_direction(series: pd.Series, max_hours: int) -> pd.Series:
    """Nội suy hướng gió trên đường tròn (ví dụ 359° -> 1°, không qua 180°)."""
    radians = np.deg2rad(series)
    sine = _interpolate_short(pd.Series(np.sin(radians), index=series.index), max_hours)
    cosine = _interpolate_short(pd.Series(np.cos(radians), index=series.index), max_hours)
    filled = np.rad2deg(np.arctan2(sine, cosine)) % 360.0
    filled = filled.mask(np.isclose(filled, 360.0), 0.0)
    return series.fillna(filled)


def merge_raw_data(
    raw_dir: str | Path = "raw_data",
    output_dir: str | Path = "data/processed",
    max_interp_hours: int = 2,
    *,
    era5_source: str = "auto",
) -> pd.DataFrame:
    """Hợp nhất Open-Meteo, ERA5 và ONI; lưu Parquet, CSV và JSON chẩn đoán.

    Sau nội suy ngắn, chỉ giữ những giờ có đủ mọi cột thực sự xuất hiện.
    CAPE/CIN/TCWV chưa có trong nguồn sẽ bị bỏ, không tạo cột toàn NaN.
    ``datetime`` đầu ra mang múi giờ Asia/Ho_Chi_Minh.
    """
    if max_interp_hours < 0:
        raise ValueError("max_interp_hours phải >= 0")
    if era5_source not in ("auto", "nc", "csv"):
        raise ValueError("era5_source phải là auto, nc hoặc csv")
    raw_path = _resolve_raw_dir(raw_dir)
    output_path = Path(output_dir)
    diagnostics: dict[str, Any] = {
        "raw_dir": str(raw_path.resolve()),
        "timezone": LOCAL_TZ,
        "naive_datetime_assumption": "UTC",
        "max_interp_hours": max_interp_hours,
    }

    surface = _read_surface(raw_path)
    nc_available = any(raw_path.rglob("*.nc"))
    if era5_source == "nc" or (era5_source == "auto" and nc_available):
        era5 = _read_era5_nc(raw_path, diagnostics)
    else:
        era5 = _read_era5_csv(raw_path, diagnostics)
    absent_core = sorted(set(CORE_ERA5_COLUMNS) - set(era5.columns))
    if absent_core:
        raise ValueError(f"ERA5 thiếu biến lõi {absent_core}; chưa thể huấn luyện baseline")
    absent_optional = sorted(set(OPTIONAL_ERA5_COLUMNS) - set(era5.columns))
    if absent_optional:
        LOGGER.warning("ERA5 chưa có %s; bỏ các cột này khỏi baseline", ", ".join(absent_optional))
    diagnostics["missing_optional_era5_variables"] = absent_optional
    oni = _read_oni_monthly(raw_path)

    # Khung thời gian chuẩn lấy từ Open-Meteo. reindex giữ cả giờ vắng mặt để
    # báo cáo; precipitation không bao giờ được nội suy vì là nhãn dự báo.
    reference = pd.date_range(surface.index.min(), surface.index.max(), freq="h", tz="UTC")
    diagnostics["source_gaps"] = {
        "openmeteo": _missing_blocks(surface.index, reference),
        **{name: _missing_blocks(era5[name].dropna().index, reference) for name in era5.columns},
    }
    diagnostics["oni_months"] = {"first": str(oni.index.min()), "last": str(oni.index.max()), "count": len(oni)}
    merged = surface.reindex(reference).join(era5, how="left")
    local_month = pd.PeriodIndex(merged.index.tz_convert(LOCAL_TZ).tz_localize(None), freq="M")
    merged["oni_anom"] = oni.reindex(local_month).to_numpy()

    filled_counts: dict[str, int] = {}
    for name in merged.columns:
        if name in ("precipitation", "oni_anom"):
            continue
        before = int(merged[name].isna().sum())
        if name == "wind_direction_10m":
            merged[name] = _interpolate_direction(merged[name], max_interp_hours)
        else:
            merged[name] = _interpolate_short(merged[name], max_interp_hours)
        filled_counts[name] = before - int(merged[name].isna().sum())
    diagnostics["interpolated_hours_by_variable"] = filled_counts

    before_drop = len(merged)
    merged = merged.dropna(subset=list(merged.columns))
    if merged.empty:
        raise ValueError("Không có giờ giao nhau đầy đủ giữa Open-Meteo, ERA5 và ONI")
    merged.index = merged.index.tz_convert(LOCAL_TZ)
    merged.index.name = "datetime"
    result = merged.reset_index()
    diagnostics["output"] = {
        "rows": len(result), "first_local": result["datetime"].iloc[0].isoformat(),
        "last_local": result["datetime"].iloc[-1].isoformat(),
        "hours_removed_incomplete": before_drop - len(result),
        "columns": result.columns.tolist(),
    }

    output_path.mkdir(parents=True, exist_ok=True)
    parquet_path = output_path / "danang_master_merged.parquet"
    csv_path = output_path / "danang_master_merged.csv"
    diagnostics_path = output_path / "merge_diagnostics.json"
    result.to_parquet(parquet_path, index=False)
    result.to_csv(csv_path, index=False)
    diagnostics_path.write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGGER.info("Đã lưu %d giờ tại %s và %s", len(result), parquet_path, csv_path)
    LOGGER.info("Báo cáo khoảng trống: %s", diagnostics_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Hợp nhất dữ liệu mưa Đà Nẵng theo giờ")
    parser.add_argument("--raw-dir", default="raw_data", help="Thư mục dữ liệu nguồn (mặc định tự tìm data/raw_data)")
    parser.add_argument("--output-dir", default="data/processed")
    parser.add_argument("--max-interp-hours", type=int, default=2)
    parser.add_argument("--era5-source", choices=("auto", "nc", "csv"), default="auto")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    merge_raw_data(args.raw_dir, args.output_dir, args.max_interp_hours, era5_source=args.era5_source)


if __name__ == "__main__":
    main()
