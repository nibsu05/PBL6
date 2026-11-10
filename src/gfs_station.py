"""Auditable GFS byte-range selection and station sampling, without downloads."""
from __future__ import annotations

from dataclasses import dataclass
import re

import numpy as np
import pandas as pd

RAIN_LEADS = (12, 36, 60, 84)
MET_LEADS = (24, 48, 72)
MET_FIELDS = {"rh850": ("RH", "850 mb"), "t850_k": ("TMP", "850 mb"), "u850": ("UGRD", "850 mb"),
              "v850": ("VGRD", "850 mb"), "pwat": ("PWAT", "entire atmosphere (considered as a single layer)")}


@dataclass(frozen=True)
class IndexRecord:
    start: int
    stop: int | None  # inclusive HTTP range
    variable: str
    level: str
    description: str


def parse_index(text: str) -> list[IndexRecord]:
    lines = [line.split(":") for line in text.splitlines() if line.strip()]
    offsets = [int(line[1]) for line in lines]
    if len(offsets) != len(set(offsets)) or offsets != sorted(offsets):
        raise ValueError("GRIB index has duplicate/unsorted byte offsets")
    return [IndexRecord(start=offsets[i], stop=offsets[i+1]-1 if i+1 < len(lines) else None,
                        variable=p[3], level=p[4], description=p[5]) for i, p in enumerate(lines)]


def accumulated_hours(description: str) -> tuple[int, int] | None:
    m = re.fullmatch(r"(\d+)-(\d+) (hour|day) acc fcst", description)
    if m:
        scale = 24 if m[3] == "day" else 1
        return int(m[1])*scale, int(m[2])*scale
    return None


def choose_records(records: list[IndexRecord], lead: int) -> dict[str, IndexRecord]:
    selected = {}
    if lead in RAIN_LEADS:
        matches = [r for r in records if r.variable == "APCP" and r.level == "surface"
                   and accumulated_hours(r.description) == (0, lead)]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one cumulative APCP 0--{lead}, got {len(matches)}")
        selected["rain_cumulative"] = matches[0]
    elif lead in MET_LEADS:
        for name, (variable, level) in MET_FIELDS.items():
            matches = [r for r in records if r.variable == variable and r.level == level
                       and r.description == f"{lead} hour fcst"]
            if len(matches) != 1:
                raise ValueError(f"Missing/ambiguous forecast field {name} at +{lead}")
            selected[name] = matches[0]
    else:
        raise ValueError("Lead not in fixed station pilot protocol")
    if any(r.stop is None for r in selected.values()):
        raise ValueError("An open-ended byte range is forbidden")
    return selected


def range_groups(selected: dict[str, IndexRecord]) -> list[list[tuple[str, IndexRecord]]]:
    """Merge adjacent messages only; never fetch an entire global forecast file."""
    groups = []
    for item in sorted(selected.items(), key=lambda x: x[1].start):
        if groups and groups[-1][-1][1].stop+1 == item[1].start:
            groups[-1].append(item)
        else:
            groups.append([item])
    return groups


def regular_grid_weights(lat: np.ndarray, lon: np.ndarray, ni=1440, nj=721):
    """Four native 0.25 degree GFS nodes; N-to-S scanning, 0..360 longitude."""
    lat = np.asarray(lat, float); lon = np.asarray(lon, float) % 360
    if np.any((lat <= -90) | (lat >= 90)) or ni != 1440 or nj != 721:
        raise ValueError("Unsupported source grid/coordinate")
    lower_lat = np.floor(lat/.25)*.25; lower_lon = np.floor(lon/.25)*.25
    fy = (lat-lower_lat)/.25; fx = (lon-lower_lon)/.25
    r0 = np.rint((90-lower_lat)/.25).astype(int); c0 = np.rint(lower_lon/.25).astype(int)
    indices = np.stack([r0*ni+c0, r0*ni+(c0+1) % ni,
                        (r0-1)*ni+c0, (r0-1)*ni+(c0+1) % ni], 1)
    weights = np.stack([(1-fy)*(1-fx), (1-fy)*fx, fy*(1-fx), fy*fx], 1)
    return indices, weights


def sample_field(values: np.ndarray, indices, weights):
    corner = np.asarray(values)[indices]
    out = (np.where(np.isfinite(corner), corner, 0)*weights).sum(1)
    out[~(np.isfinite(corner) | (weights < 1e-10)).all(1)] = np.nan
    return out.astype("float32")


def rainfall_windows(cumulative: np.ndarray, quantums: np.ndarray):
    """Return three separate 24h totals, flagging packing-rounding corrections.

    GRIB quantization error can produce tiny negative differences in dry cells.
    Never clip a larger negative value silently.
    """
    difference = np.diff(cumulative, axis=0)
    tolerance = np.maximum(.01, (quantums[:-1]+quantums[1:])[:, None])
    serious = difference < -tolerance
    if serious.any():
        raise ValueError(f"Nonmonotone cumulative precipitation beyond packing tolerance: {difference.min()}")
    clipped = difference < 0
    return np.maximum(difference, 0).astype("float32"), clipped


def issue_contract(day: str):
    init = pd.Timestamp(day, tz="UTC")
    if init.year not in (2021, 2022, 2023, 2024) or init.hour:
        raise ValueError("Pilot may read only 00UTC cycles in 2021--2024")
    issue = init + pd.Timedelta(hours=12)  # 19:00 Vietnam
    if issue + pd.Timedelta(hours=72) > pd.Timestamp("2025-01-01", tz="Asia/Ho_Chi_Minh"):
        raise ValueError("Target would cross the reserved Vrain year")
    return init, issue
