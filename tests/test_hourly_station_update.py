import unittest
import numpy as np
import pandas as pd
from src.hourly_station_update import extended_splits, source_windows, hourly_flags


class HourlyUpdateTests(unittest.TestCase):
    def test_change_of_api_inside_history_or_target_is_excluded(self):
        codes = np.r_[np.zeros(50, int), np.ones(50, int)]
        actual = source_windows(codes)
        expected = np.zeros(100, bool)
        for i in range(23, 94):
            expected[i] = len(set(codes[i-23:i+7])) == 1
        np.testing.assert_array_equal(actual, expected)
        self.assertTrue(actual[43])
        self.assertFalse(actual[44])
        self.assertFalse(actual[72])
        self.assertTrue(actual[73])

    def test_missing_and_conflict_are_never_valid_source(self):
        for code in (-1, 3):
            values = np.zeros(70, int)
            values[30] = code
            self.assertFalse(source_windows(values)[24:54].any())

    def test_splits_extend_without_changing_old_training_boundary(self):
        times = pd.DatetimeIndex(["2022-12-31 11:00Z", "2022-12-31 12:00Z",
                                  "2024-12-31 17:00Z", "2025-12-31 17:00Z"])
        self.assertEqual(extended_splits(times).tolist(),
                         ["train", "boundary", "reserved2025", "external2026"])

    def test_weather_tail_missing_does_not_become_ready(self):
        end = pd.date_range("2022-01-01", periods=100, freq="h", tz="UTC")
        weather = np.ones((100, 44))
        weather[70:] = np.nan
        flags = hourly_flags(weather, np.ones(100), np.zeros(100), end)
        self.assertTrue(flags["sample_ready_r1"][69])
        self.assertFalse(flags["sample_ready_r1"][70:].any())
        self.assertEqual(flags["labels"][69].tolist(), [1.]*6)

    def test_new_station_has_technical_samples_without_known_station_eligibility(self):
        end = pd.date_range("2026-02-01", periods=100, freq="h", tz="UTC")
        flags = hourly_flags(np.ones((100, 44)), np.ones(100), np.ones(100), end)
        self.assertTrue(flags["sample_complete"].any())
        self.assertFalse(flags["station_seen_train"])
        self.assertFalse(flags["sample_ready_r1"].any())

    def test_future_labels_and_paired_mask(self):
        end = pd.date_range("2022-01-01", periods=100, freq="h", tz="UTC")
        flags = hourly_flags(np.ones((100, 44)), np.arange(100), np.zeros(100), end)
        self.assertEqual(flags["labels"][40].tolist(), list(range(41, 47)))
        np.testing.assert_array_equal(flags["sample_ready_r0"], flags["sample_ready_r1"])


if __name__ == "__main__":
    unittest.main()
