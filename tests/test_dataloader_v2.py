"""Kiểm tra dataloader v2 trên một khối dữ liệu giả lập nhỏ (không cần dữ liệu thật)."""

from __future__ import annotations

import json
import gc
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.dataloader_v2 import (FEATURE_GROUPS, LABEL, STATIC_FEATURES, TIME_FEATURES, DatasetV2, Normalizer,
                               WindowConfig, WindowSampler, build_cell_major, sample_index, season_of)

NAMES = [LABEL, "label_permanent", *FEATURE_GROUPS["A0"]["past"], *FEATURE_GROUPS["A1"]["obs"], *TIME_FEATURES]


def _identity_normalizer(names: list[str]) -> Normalizer:
    norm = Normalizer({n: 0.0 for n in names}, {n: 1.0 for n in names},
                      {n: 0.0 for n in STATIC_FEATURES}, {n: 1.0 for n in STATIC_FEATURES})
    return norm


class DataloaderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        cls.n_cells = 3
        offset = 0
        for year in (2020, 2021):
            hours = pd.date_range(f"{year}-01-01", f"{year + 1}-01-01", freq="h", inclusive="left")
            t = np.arange(len(hours), dtype=np.float32) + offset
            X = np.zeros((len(hours), cls.n_cells, len(NAMES)), dtype=np.float32)
            for c in range(cls.n_cells):
                for k, name in enumerate(NAMES):
                    X[:, c, k] = t + 1000 * c        # giá trị = chỉ số giờ toàn cục (+ mã ô)
            X[:, :, NAMES.index("label_permanent")] = 1
            np.save(d / f"{year}.npy", X)
            np.save(d / f"{year}_hours.npy", hours.values.astype("datetime64[ns]"))
            offset += len(hours)
        manifest = {"features": [{"name": n} for n in NAMES]}
        (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        cells = pd.DataFrame({"site": ["a", "b", "c"], "province": ["Đà Nẵng", "Huế", None],
                              **{n: [1.0, 2.0, 3.0] for n in STATIC_FEATURES}})
        cells.to_parquet(d / "cells.parquet", index=False)
        build_cell_major(d)
        cls.ds = DatasetV2(d)

    @classmethod
    def tearDownClass(cls) -> None:
        del cls.ds
        gc.collect()  # Windows không cho xóa file memmap còn mở.
        cls.tmp.cleanup()

    def test_cell_major_cube_matches_yearly_files(self) -> None:
        self.assertEqual(self.ds.cube.shape, (3, 8784 + 8760, len(NAMES)))
        self.assertEqual(float(self.ds.cube[2, 8784, 0]), 8784 + 2000)

    def test_window_alignment_with_observation_latency(self) -> None:
        cfg = WindowConfig(groups=("A0", "A1"), input_len=24, horizon=6, latency_h=4)
        sampler = WindowSampler(self.ds, cfg, _identity_normalizer(NAMES))
        t, raw = 9000, sampler.get(0, 9000)
        n_past = len(sampler.past_names)
        np.testing.assert_array_equal(raw["x_past"][:, 0], np.arange(t - 24, t))              # khí quyển: t−24…t−1
        obs_col = n_past + sampler.obs_names.index("gsmap_mm")
        np.testing.assert_allclose(raw["x_past"][:, obs_col], np.log1p(np.arange(t - 28, t - 4)), rtol=1e-6)  # trễ 4 h
        np.testing.assert_array_equal(raw["y"], np.arange(t, t + 6))                         # nhãn: t…t+5
        self.assertEqual(raw["x_future"].shape, (6, len(TIME_FEATURES)))
        self.assertEqual(raw["static"].shape, (len(STATIC_FEATURES),))

    def test_no_latency_drops_observation_group(self) -> None:
        cfg = WindowConfig(groups=("A0", "A1"), latency_h=None)
        self.assertEqual(cfg.feature_lists()["obs"], [])

    def test_index_respects_years_nan_and_foreign_cells(self) -> None:
        cfg = WindowConfig(groups=("A0", "A1"), input_len=24, horizon=6, latency_h=4)
        idx = sample_index(self.ds, cfg, [2021])
        self.assertEqual(set(idx[:, 0]), {0, 1})                       # ô "c" không thuộc Việt Nam
        first_target_year = self.ds.hours[idx[:, 1]].year
        self.assertTrue((first_target_year == 2021).all())
        self.assertEqual(idx[:, 1].min(), 8784)                         # đầu vào được nhìn lùi sang 2020
        self.assertEqual(idx[:, 1].max(), 8784 + 8760 - 6)              # 6 nhãn phải nằm trong dữ liệu
        # Chèn NaN vào nhãn một giờ → mọi cửa sổ có giờ đó trong phần nhãn bị loại
        cube = np.load(self.ds.dir / "cube_cell_major.npy", mmap_mode="r+")
        cube[0, 10000, 0] = np.nan
        cube.flush()
        try:
            ds = DatasetV2(self.ds.dir)
            idx2 = sample_index(ds, cfg, [2021])
            cell0 = idx2[idx2[:, 0] == 0, 1]
            self.assertFalse(np.any((cell0 > 10000 - 6) & (cell0 <= 10000)))
            self.assertIn(10001, cell0)
        finally:
            cube[0, 10000, 0] = 10000
            cube.flush()

    def test_targets_do_not_cross_train_validation_boundary(self) -> None:
        cfg = WindowConfig(groups=("A0",), horizon=6, latency_h=None)
        idx = sample_index(self.ds, cfg, [2020])
        self.assertEqual(idx[:, 1].max(), 8784 - 6)
        last_target_year = self.ds.hours[idx[:, 1] + cfg.horizon - 1].year
        self.assertTrue((last_target_year == 2020).all())

    def test_issue_hours_and_season(self) -> None:
        cfg = WindowConfig(groups=("A0",), input_len=168, horizon=72, latency_h=None, issue_stride_h=6,
                           issue_hours_utc=(0, 12))
        idx = sample_index(self.ds, cfg, [2021])
        self.assertTrue(set(self.ds.hours[idx[:, 1]].hour) <= {0, 12})
        seasons = season_of(self.ds, idx[:3])
        self.assertTrue(set(seasons) <= {"winter", "summer", "spring"})
        self.assertEqual(seasons[0], "winter")

    def test_normalizer_is_fit_on_train_years_only(self) -> None:
        cfg = WindowConfig(groups=("A0",), latency_h=None)
        norm = Normalizer.fit(self.ds, cfg, [2020], max_rows_per_cell=500)
        self.assertLess(norm.mean["t2m_c"], 1000 + 8784)               # chỉ thấy giá trị của năm 2020
        z = norm.transform(np.array([[norm.mean["t2m_c"]]]), ["t2m_c"])
        self.assertAlmostEqual(float(z[0, 0]), 0.0, places=5)


if __name__ == "__main__":
    unittest.main()
