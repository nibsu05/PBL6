"""Kiểm tra phần xử lý thuần của script trích xuất Earth Engine (không gọi GEE)."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from extract_gee_precip import (DATASETS, MAX_VALUES_PER_CALL, daily_totals, grid_points, hourly_depth,
                                rows_to_frame, time_chunks)

IMERG = DATASETS["imerg"]
GSMAP = DATASETS["gsmap"]


def _ms(ts: str) -> int:
    return int(pd.Timestamp(ts).value // 1_000_000)


class GridAndChunkTest(unittest.TestCase):
    def test_grid_centres_sit_on_native_pixels(self) -> None:
        grid = grid_points((16.0, 16.3, 108.0, 108.2))
        self.assertEqual(sorted(grid["lat"].unique().tolist()), [16.05, 16.15, 16.25])
        self.assertEqual(sorted(grid["lon"].unique().tolist()), [108.05, 108.15])
        self.assertEqual(grid["site"].iloc[0], "c16.05_108.05")

    def test_chunks_cover_range_without_crossing_months_or_limit(self) -> None:
        start, end = pd.Timestamp("2020-01-20"), pd.Timestamp("2020-03-01")
        chunks = time_chunks(start, end, 0.5, n_points=400, n_columns=7)
        self.assertEqual(chunks[0][0], start)
        self.assertEqual(chunks[-1][1], end)
        for (a0, a1), (b0, _) in zip(chunks, chunks[1:]):
            self.assertEqual(a1, b0)
        for c0, c1 in chunks:
            self.assertEqual(c0.month, (c1 - pd.Timedelta(seconds=1)).month)
            n_images = (c1 - c0) / pd.Timedelta(minutes=30)
            self.assertLessEqual(n_images * 400 * 7, MAX_VALUES_PER_CALL)


class ParseTest(unittest.TestCase):
    def _rows(self, n_steps: int, step_min: int, bands: tuple[str, ...], rate: float, permanent: int = 1):
        header = ["id", "longitude", "latitude", "time", *bands, "permanent"]
        body = []
        for i in range(n_steps):
            t = _ms("2024-10-01") + i * step_min * 60_000
            body.append([f"img{i}", 108.15, 16.05, t, *([rate] * len(bands)), permanent])
            body.append([f"img{i}", 108.25, 16.05, t, *([0.0] * len(bands)), permanent])
        return [header, *body]

    def test_imerg_rates_become_half_hour_depths_and_full_days(self) -> None:
        points = pd.DataFrame({"site": ["A", "B"], "lat": [16.044, 16.06], "lon": [108.199, 108.24]})
        frame = rows_to_frame(self._rows(48, 30, IMERG.bands, 2.0), points, IMERG)
        self.assertEqual(set(frame["site"]), {"A", "B"})
        self.assertAlmostEqual(frame.loc[frame["site"] == "A", "precipitation_mm"].iloc[0], 1.0)
        daily = daily_totals(frame, IMERG)
        imerg_a = daily[(daily["usaf"] == "A") & (daily["source"] == "imerg")]
        self.assertEqual(imerg_a["precip_mm"].tolist(), [48.0])
        partial = daily_totals(frame.iloc[:-4], IMERG)
        self.assertNotIn("B", set(partial["usaf"]))

    def test_provisional_images_are_dropped_by_default(self) -> None:
        points = pd.DataFrame({"site": ["A", "B"], "lat": [16.05, 16.05], "lon": [108.15, 108.25]})
        frame = rows_to_frame(self._rows(24, 60, GSMAP.bands, 1.5, permanent=0), points, GSMAP)
        self.assertTrue(daily_totals(frame, GSMAP).empty)
        kept = daily_totals(frame, GSMAP, permanent_only=False)
        self.assertEqual(sorted(kept["source"].unique()), ["gsmap", "gsmap_gc"])
        self.assertAlmostEqual(kept[(kept["usaf"] == "A")]["precip_mm"].iloc[0], 36.0)

    def test_hourly_depth_needs_both_half_hours(self) -> None:
        points = pd.DataFrame({"site": ["A", "B"], "lat": [16.05, 16.05], "lon": [108.15, 108.25]})
        frame = rows_to_frame(self._rows(3, 30, IMERG.bands, 4.0), points, IMERG)
        hourly = hourly_depth(frame, IMERG)
        a = hourly[hourly["site"] == "A"].set_index("time_start_utc")["precipitation_mm"]
        self.assertEqual(a.iloc[0], 4.0)
        self.assertTrue(np.isnan(a.iloc[1]))

    def test_unexpected_header_or_far_pixel_is_rejected(self) -> None:
        points = pd.DataFrame({"site": ["A"], "lat": [16.05], "lon": [108.15]})
        with self.assertRaises(ValueError):
            rows_to_frame([["id", "longitude", "latitude", "time", "x"]], points, GSMAP)
        far = [["id", "longitude", "latitude", "time", *GSMAP.bands, "permanent"],
               ["i", 109.0, 16.05, _ms("2024-01-01"), 1.0, 1.0, 1]]
        with self.assertRaises(ValueError):
            rows_to_frame(far, points, GSMAP)


if __name__ == "__main__":
    unittest.main()
