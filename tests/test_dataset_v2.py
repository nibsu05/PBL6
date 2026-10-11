"""Kiểm tra các biến đổi thuần của dataset v2."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.dataset_v2 import (CIN_CAP, bilinear_weights, encode_cin, interpolate, neighbourhood_stats,
                            relative_humidity, time_features, to_cube)


class Era5ToCellTest(unittest.TestCase):
    def setUp(self) -> None:
        lats, lons = np.meshgrid([16.0, 16.25], [108.0, 108.25], indexing="ij")
        self.node_lat, self.node_lon = lats.ravel(), lons.ravel()  # thứ tự: (16,108),(16,108.25),(16.25,108),(16.25,108.25)

    def test_bilinear_reproduces_a_plane_and_skips_nan_nodes(self) -> None:
        idx, w = bilinear_weights(np.array([16.05, 16.15]), np.array([108.15, 108.05]), self.node_lat, self.node_lon)
        np.testing.assert_allclose(w.sum(axis=1), 1.0)
        field = (2 * self.node_lat + 3 * self.node_lon)[None, :, None]   # mặt phẳng tuyến tính
        out = interpolate(field, idx, w)[0, :, 0]
        np.testing.assert_allclose(out, [2 * 16.05 + 3 * 108.15, 2 * 16.15 + 3 * 108.05], rtol=1e-6)
        sst = np.array([np.nan, 30.0, np.nan, 30.0])[None, :, None]       # nút đất bị NaN
        self.assertAlmostEqual(float(interpolate(sst, idx, w)[0, 0, 0]), 30.0, places=5)
        all_nan = np.full((1, 4, 1), np.nan)
        self.assertTrue(np.isnan(interpolate(all_nan, idx, w)).all())

    def test_missing_node_is_an_error(self) -> None:
        with self.assertRaises(ValueError):
            bilinear_weights(np.array([16.35]), np.array([108.05]), self.node_lat, self.node_lon)


class EncodingTest(unittest.TestCase):
    def test_masked_cin_means_strong_inhibition_not_zero(self) -> None:
        capped, has_lfc = encode_cin(np.array([np.nan, 0.0, 80.0, 900.0]))
        np.testing.assert_array_equal(capped, [CIN_CAP, 0.0, 80.0, CIN_CAP])
        np.testing.assert_array_equal(has_lfc, [0, 1, 1, 1])

    def test_relative_humidity(self) -> None:
        self.assertAlmostEqual(float(relative_humidity(np.array([300.0]), np.array([300.0]))[0]), 100.0, places=3)
        self.assertLess(float(relative_humidity(np.array([303.15]), np.array([293.15]))[0]), 60)

    def test_time_features_use_local_mid_hour(self) -> None:
        tf = time_features(pd.DatetimeIndex(["2024-01-01T17:00"]))  # 00:00–01:00 giờ VN ngày 2/1
        np.testing.assert_allclose(tf[0, :2], [np.sin(2 * np.pi * 0.5 / 24), np.cos(2 * np.pi * 0.5 / 24)], rtol=1e-6)


class CubeAndNeighbourhoodTest(unittest.TestCase):
    def test_to_cube_places_values_and_leaves_gaps(self) -> None:
        hours = pd.date_range("2024-01-01", periods=3, freq="h")
        frame = pd.DataFrame({"t": [hours[0], hours[2]], "site": ["b", "a"], "x": [1.0, 2.0]})
        cube = to_cube(frame, "t", hours, ["a", "b"], ["x"])
        self.assertEqual(cube[0, 1, 0], 1.0)
        self.assertEqual(cube[2, 0, 0], 2.0)
        self.assertTrue(np.isnan(cube[1]).all())

    def test_neighbourhood_mean_and_max(self) -> None:
        lat, lon = np.meshgrid(np.round(np.arange(16.05, 16.55, 0.1), 2), np.round(np.arange(108.05, 108.55, 0.1), 2), indexing="ij")
        lat, lon = lat.ravel(), lon.ravel()
        field = np.zeros((1, len(lat)), dtype=np.float32)
        centre = np.where((lat == 16.25) & (lon == 108.25))[0][0]
        field[0, centre] = 25.0
        mean, mx = neighbourhood_stats(field, lat, lon, radius=2)
        self.assertAlmostEqual(float(mean[0, centre]), 1.0)
        corner = np.where((lat == 16.05) & (lon == 108.05))[0][0]
        self.assertEqual(float(mx[0, corner]), 25.0)            # trung tâm nằm trong cửa sổ 5×5 của góc
        self.assertAlmostEqual(float(mean[0, corner]), 25.0 / 9, places=5)  # góc chỉ có 3×3 ô thật


if __name__ == "__main__":
    unittest.main()
