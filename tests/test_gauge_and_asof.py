"""Kiểm tra nhãn trạm, ghép giờ hiệu lực và cổng thời gian phát hành."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from evaluate_gauge_predictions import _scores, _validate_and_join
from src.availability_audit import audit_asof_windows
from src.gauge_observations import GaugeConfig, normalize_gauge_export


class GaugeAndAsofTest(unittest.TestCase):
    def _config(self, **updates) -> GaugeConfig:
        values = dict(station_name="Hai Chau", latitude=16.06, longitude=108.20,
                      source_name="Gauge export", source_timezone="Asia/Ho_Chi_Minh",
                      timestamp_means="start", accumulation_hours=1,
                      datetime_column="time", rain_column="rain")
        values.update(updates)
        return GaugeConfig(**values)

    def test_start_hour_is_shifted_and_gap_is_not_zero_filled(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "gauge.csv"
            path.write_text("time,rain,quality\n2025-01-01 00:00,2,OK\n"
                            "2025-01-01 01:00,,OK\n2025-01-01 03:00,7,BAD\n"
                            "2025-01-01 04:00,6,OK\n", encoding="utf-8")
            data, meta = normalize_gauge_export(
                path, self._config(quality_column="quality", accepted_quality=("OK",))
            )
            self.assertEqual(data["datetime"].dt.hour.tolist(), [1, 5])
            self.assertEqual(data["precipitation_mm_h"].tolist(), [2, 6])
            self.assertEqual(meta["missing_rain_rows"], 1)
            self.assertEqual(meta["missing_calendar_hours_in_span"], 3)
            self.assertEqual(meta["hours_over_5_mm"], 1)

    def test_duplicate_hour_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "gauge.csv"
            path.write_text("time,rain\n2025-01-01 00:00,1\n2025-01-01 00:00,2\n",
                            encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "trùng"):
                normalize_gauge_export(path, self._config())
            with self.assertRaisesRegex(ValueError, "đúng 1 giờ"):
                normalize_gauge_export(path, self._config(accumulation_hours=6))

    def test_excel_export_is_read(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "gauge.xlsx"
            pd.DataFrame({"time": ["2025-01-01 00:00"], "rain": [1.2]}).to_excel(
                path, index=False
            )
            data, _ = normalize_gauge_export(path, self._config())
            self.assertEqual(len(data), 1)
            self.assertAlmostEqual(float(data["precipitation_mm_h"].iloc[0]), 1.2)

    def test_join_uses_valid_hour_and_only_observed_hours(self) -> None:
        tz = "Asia/Ho_Chi_Minh"
        valid = pd.date_range("2025-01-01 01:00", periods=4, freq="h", tz=tz)
        predictions = pd.DataFrame({
            "last_input_datetime": valid - pd.Timedelta(hours=1),
            "valid_datetime": valid,
            "horizon_h": 1,
            "actual_mm": [0, 0, 0, 0],
            "dual_amount_mm": [0, 2, 0, 7],
            "dual_heavy_probability": [0.1, 0.2, 0.3, 0.8],
            "standard_amount_mm": [0, 1, 0, 3],
            "persistence_mm": [0, 0, 0, 0],
        })
        gauge = pd.DataFrame({"datetime": [valid[1].isoformat(), valid[3].isoformat()],
                              "precipitation_mm_h": [1, 8]})
        matched, summary = _validate_and_join(predictions, gauge, 0.4, None)
        self.assertEqual(summary["matched_pairs"], 2)
        self.assertEqual(summary["pair_coverage_in_gauge_span"], 2 / 3)
        self.assertEqual(matched["dual_alert"].tolist(), [False, True])
        hourly, _ = _scores(matched)
        self.assertEqual(int(hourly.loc[hourly.model == "dual_head", "TP"].iloc[0]), 1)
        future, future_summary = _validate_and_join(
            predictions.drop(columns="actual_mm"), gauge, 0.4, None
        )
        self.assertEqual(len(future), 2)
        self.assertNotIn("openmeteo_vs_gauge", future_summary)

    def test_asof_gate_rejects_late_feature_and_missing_provenance(self) -> None:
        anchor = pd.Timestamp("2025-01-02 00:00", tz="Asia/Ho_Chi_Minh")
        predictions = pd.DataFrame({"last_input_datetime": [anchor],
                                    "issued_at": [anchor + pd.Timedelta(minutes=10)]})
        hours = pd.date_range(anchor - pd.Timedelta(hours=23), anchor, freq="h")
        available = pd.DataFrame({"datetime": hours,
                                  "available_at": hours + pd.Timedelta(minutes=5)})
        summary, _ = audit_asof_windows(predictions, available)
        self.assertEqual(summary["status"], "verified")
        available.loc[available.index[-1], "available_at"] = anchor + pd.Timedelta(minutes=20)
        summary, details = audit_asof_windows(predictions, available)
        self.assertEqual(summary["windows_with_late_input"], 1)
        self.assertFalse(bool(details["ready"].iloc[0]))
        summary, _ = audit_asof_windows(predictions.drop(columns="issued_at"), available)
        self.assertEqual(summary["status"], "unverified_missing_provenance")


if __name__ == "__main__":
    unittest.main()
