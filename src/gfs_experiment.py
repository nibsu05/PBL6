"""Isolate station experiments while sharing the immutable GFS source cache."""
from dataclasses import dataclass
import os
from pathlib import Path
import re

SOURCE_NAME = "gfs_station_pilot_2026_11_10"


@dataclass(frozen=True)
class ExperimentPaths:
    name: str
    base: Path
    public: Path
    data: Path
    source: Path

    @property
    def dataset(self):
        return self.data / "gfs_vrain_pilot.parquet"


def experiment_paths(root: Path, name: str | None = None) -> ExperimentPaths:
    name = name or os.environ.get("PBL6_GFS_EXPERIMENT", SOURCE_NAME)
    if not re.fullmatch(r"gfs_station_[a-z0-9_]+", name):
        raise ValueError("Experiment must be a simple gfs_station_* identifier")
    data_name = "gfs_station_pilot" if name == SOURCE_NAME else name
    return ExperimentPaths(name=name, base=root / "data/operational" / name,
        public=root / "reports" / name, data=root / "data/processed" / data_name,
        source=root / "data/operational" / SOURCE_NAME)
