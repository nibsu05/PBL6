"""Chế độ ít dung lượng phải giữ đúng tensor của pipeline mặc định."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
import scripts.build_dataset_v2 as builder
from src.dataloader_v2 import build_cell_major


class StorageTest(unittest.TestCase):
    def test_direct_cube_equals_yearly_conversion(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            direct, reference = root / "direct", root / "reference"
            reference.mkdir()
            cells = pd.DataFrame({"lat": [15., 16.], "lon": [108., 108.], "ocean_frac": [0., 0.],
                                  "province": ["Đà Nẵng", "Huế"]})
            source = root / "static.parquet"
            cells.to_parquet(source)
            def fake_year(year, cells, mask, sink=None):
                hours = pd.date_range(f"{year}-01-01", f"{year+1}-01-01", freq="h", inclusive="left")
                rng = np.random.default_rng(year)
                values = rng.normal(size=(len(hours), int(mask.sum()), len(builder.NAMES))).astype(np.float32)
                values[10, 0, 0] = np.nan
                np.save(reference / f"{year}.npy", values)
                np.save(reference / f"{year}_hours.npy", hours.values.astype("datetime64[ns]"))
                sink(year, values, hours)
                return {"year": year, "hours": len(hours), "cells": int(mask.sum()),
                        "danang_label_total_mm": 0, "danang_era5_tp_total_mm": 0, "nan_frac": {}}
            with patch.object(builder, "STATIC", source), patch.object(builder, "OUT", direct), \
                 patch.object(builder, "build_year", fake_year), \
                 patch("sys.argv", ["build", "--years", "2020", "2021", "--cell-major-only", "--provinces", "Đà Nẵng"]):
                builder.main()
            build_cell_major(reference)
            actual = np.load(direct / "cube_cell_major.npy")
            np.testing.assert_array_equal(actual, np.load(reference / "cube_cell_major.npy"))
            np.testing.assert_array_equal(np.load(direct / "hours_all.npy"), np.load(reference / "hours_all.npy"))
            self.assertEqual(actual.shape[0], 1)
            self.assertFalse((direct / "2020.npy").exists())
            self.assertFalse((direct / "cube_cell_major.partial.npy").exists())


if __name__ == "__main__":
    unittest.main()
