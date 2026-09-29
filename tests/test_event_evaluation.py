"""Kiểm tra định nghĩa đợt mưa và cách đếm giờ dự báo."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from evaluate_surface_baseline import _load_observations
from src.event_evaluation import detection_scores, find_episodes, score_episodes


class EventEvaluationTest(unittest.TestCase):
    def test_event_hit_can_differ_from_exact_hour_hit(self) -> None:
        hours = pd.date_range("2025-01-01", periods=16, freq="h", tz="Asia/Ho_Chi_Minh")
        actual = np.zeros(16)
        actual[[1, 3, 12]] = [8, 7, 10]
        forecast = np.zeros(16)
        forecast[[2, 9]] = 6
        hourly = detection_scores(actual, forecast)
        self.assertEqual((hourly["TP"], hourly["FP"], hourly["FN"]), (0, 2, 3))
        summary, episodes = score_episodes(hours, actual, forecast)
        self.assertEqual(summary["observed_events"], 2)
        self.assertEqual(summary["forecast_events"], 2)
        self.assertEqual(summary["detected_observed_events"], 1)
        self.assertEqual(summary["false_alarm_forecast_events"], 1)
        self.assertEqual(summary["event_F1"], 0.5)
        self.assertEqual(episodes["detected"].tolist(), [True, False])

    def test_gap_in_timeline_breaks_event(self) -> None:
        hours = pd.date_range("2025-01-01", periods=6, freq="h", tz="UTC").delete(3)
        actual = np.array([0, 0, 8, 9, 0], dtype=float)
        self.assertEqual(len(find_episodes(hours, actual)), 2)

    def test_one_long_warning_cannot_count_as_two_detected_events(self) -> None:
        hours = pd.date_range("2025-01-01", periods=20, freq="h", tz="UTC")
        actual = np.zeros(20)
        actual[[2, 15]] = 9
        predicted = np.zeros(20)
        predicted[2:16] = 6
        summary, _ = score_episodes(hours, actual, predicted)
        self.assertEqual(summary["observed_events"], 2)
        self.assertEqual(summary["forecast_events"], 1)
        self.assertEqual(summary["detected_observed_events"], 1)
        self.assertEqual(summary["event_recall"], 0.5)

    def test_no_observed_heavy_rain_has_undefined_recall(self) -> None:
        metrics = detection_scores(np.zeros(3), np.zeros(3))
        self.assertIsNone(metrics["POD_recall"])
        self.assertIsNone(metrics["F1"])

    def test_independent_observations_require_explicit_timezone(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "gauge.csv"
            path.write_text("datetime,precipitation_mm_h\n2025-01-01 00:00,2\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "UTC offset"):
                _load_observations(path, "Test gauge")
            path.write_text("datetime,precipitation_mm_h\n2025-01-01T00:00:00+07:00,2\n",
                            encoding="utf-8")
            loaded = _load_observations(path, "Test gauge")
            self.assertEqual(float(loaded["observed_mm"].iloc[0]), 2.0)


if __name__ == "__main__":
    unittest.main()
