"""Thử ghi dự báo bất biến từ 48 giờ input có metadata as-of."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd
import torch

from record_surface_forecast import record_forecast


class ProspectiveRecordTest(unittest.TestCase):
    def test_forecast_record_requires_available_input_and_keeps_issue(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            hours = pd.date_range("2025-01-01 00:00", periods=48, freq="h",
                                  tz="Asia/Ho_Chi_Minh")
            raw = pd.DataFrame({
                "datetime": hours,
                "available_at": hours + pd.Timedelta(minutes=5),
                "temperature_2m": 27.0,
                "relative_humidity_2m": 80.0,
                "surface_pressure": 1010.0,
                "wind_speed_10m": 6.0,
                "wind_direction_10m": 90.0,
                "precipitation": 0.0,
            })
            path = base / "live_surface.csv"
            raw.to_csv(path, index=False)
            issued = hours[-1] + pd.Timedelta(minutes=10)
            output, manifest = record_forecast(path, "synthetic test", issued,
                                               base / "issuances", torch.device("cpu"))
            saved = pd.read_parquet(output)
            self.assertEqual(len(saved), 6)
            self.assertEqual(saved["horizon_h"].tolist(), list(range(1, 7)))
            self.assertEqual(manifest["asof_check"]["status"], "verified")
            self.assertFalse(manifest["captured_before_first_target"])
            self.assertTrue(Path(manifest["input_snapshot"]).exists())
            with self.assertRaises(FileExistsError):
                record_forecast(path, "synthetic test", issued,
                                base / "issuances", torch.device("cpu"))


if __name__ == "__main__":
    unittest.main()
