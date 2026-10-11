"""Kiểm tra kiểm soát chất lượng GSOD và quy ước giờ mưa Open-Meteo."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from fetch_gsod_stations import classify, load_station_year, year_coverage
from fetch_openmeteo_baselines import hourly_series, hourly_to_daily
from src.station_registry import BY_USAF


class GsodQualityTest(unittest.TestCase):
    def test_flags_decide_which_days_are_kept(self) -> None:
        self.assertEqual(classify("G", 10.0), "complete")
        self.assertEqual(classify("I", 0.0), "assumed_dry")
        self.assertEqual(classify("A", 3.0), "partial")
        self.assertEqual(classify("H", 0.0), "incomplete")
        self.assertEqual(classify("G", np.nan), "missing")

    def test_partial_days_are_dropped_and_dry_days_become_zero(self) -> None:
        csv = ("DATE,PRCP,PRCP_ATTRIBUTES\n2020-01-01,1.00,G\n2020-01-02,0.20,A\n"
               "2020-01-03,0.00,I\n2020-01-04,99.99, \n")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "s.csv"
            path.write_text(csv, encoding="utf-8")
            frame = load_station_year(path, BY_USAF["488550"])
        self.assertAlmostEqual(frame["precip_mm"].iloc[0], 25.4)
        self.assertTrue(np.isnan(frame["precip_mm"].iloc[1]))
        self.assertEqual(frame["precip_mm"].iloc[2], 0.0)
        self.assertTrue(np.isnan(frame["precip_mm"].iloc[3]))

    def test_all_zero_station_year_is_not_usable(self) -> None:
        dates = pd.date_range("2021-01-01", "2021-12-31", freq="D")
        frame = pd.DataFrame({"date": dates, "quality": "assumed_dry", "precip_mm": 0.0})
        self.assertFalse(year_coverage(frame, dates[-1])["usable"])


class OpenMeteoConventionTest(unittest.TestCase):
    def test_hour_ending_at_midnight_belongs_to_previous_day_across_years(self) -> None:
        times_2020 = pd.date_range("2020-12-31T00:00", "2020-12-31T23:00", freq="h")
        times_2021 = pd.date_range("2021-01-01T00:00", "2021-01-01T23:00", freq="h")
        y2020 = hourly_series({"hourly": {"time": times_2020.strftime("%Y-%m-%dT%H:%M").tolist(), "p": [1.0] * 24}}, "p")
        y2021 = hourly_series({"hourly": {"time": times_2021.strftime("%Y-%m-%dT%H:%M").tolist(), "p": [1.0] * 24}}, "p")
        separate = hourly_to_daily(y2020)
        self.assertTrue(np.isnan(separate.loc["2020-12-31"]))  # thiếu giờ 23–24 nếu cộng riêng từng năm
        joined = hourly_to_daily(pd.concat([y2020, y2021]))
        self.assertEqual(joined.loc["2020-12-31"], 24.0)


if __name__ == "__main__":
    unittest.main()
