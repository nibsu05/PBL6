"""Kiểm tra bộ chỉ số dùng chung và baseline không học."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.baselines import apply_climatology, doy_climatology, persistence
from src.verification import (brier_skill_score, contingency_scores, continuous_scores, metric_csi,
                              metric_mae, paired_block_bootstrap, rolling_origin_folds, score_table,
                              skill_score)


class ContingencyTest(unittest.TestCase):
    def test_threshold_is_inclusive_and_scores_match_hand_count(self) -> None:
        obs = np.array([16, 0, 20, 5, 60, 0])
        fcst = np.array([16, 18, 0, 5, 55, 0])
        cs = contingency_scores(obs, fcst, 16)
        self.assertEqual((cs["hits"], cs["misses"], cs["false_alarms"], cs["correct_negatives"]), (2, 1, 1, 2))
        self.assertAlmostEqual(cs["POD"], 2 / 3)
        self.assertAlmostEqual(cs["FAR"], 1 / 3)
        self.assertAlmostEqual(cs["CSI"], 0.5)
        self.assertAlmostEqual(cs["FBI"], 1.0)
        hits_random = 3 * 3 / 6
        self.assertAlmostEqual(cs["ETS"], (2 - hits_random) / (4 - hits_random))

    def test_no_observed_event_gives_nan_not_zero(self) -> None:
        cs = contingency_scores([0, 1, 2], [0, 0, 0], 16)
        self.assertTrue(np.isnan(cs["POD"]) and np.isnan(cs["CSI"]))

    def test_nan_pairs_are_dropped(self) -> None:
        sc = continuous_scores([1, np.nan, 3], [2, 5, np.nan])
        self.assertEqual(sc["n"], 1)
        self.assertEqual(sc["bias"], 1.0)


class ScoreTableTest(unittest.TestCase):
    def test_common_rows_make_sources_comparable(self) -> None:
        frame = pd.DataFrame({"obs": [20, 0, 30, 0], "a": [20, 0, 0, np.nan], "b": [0, 0, 30, 0]})
        table = score_table(frame, "obs", ["a", "b"], thresholds=[16])
        self.assertEqual(set(table["n"]), {3})
        self.assertAlmostEqual(table.loc["a", "CSI>=16"], 0.5)
        self.assertAlmostEqual(table.loc["b", "CSI>=16"], 0.5)

    def test_bss_of_deterministic_forecast(self) -> None:
        event = np.array([1, 0, 0, 1], dtype=float)
        perfect = brier_skill_score(event, event, np.full(4, 0.5))
        self.assertAlmostEqual(perfect, 1.0)

    def test_skill_score_orientation(self) -> None:
        self.assertAlmostEqual(skill_score(2.0, 4.0, 0.0), 0.5)   # MAE giảm một nửa
        self.assertAlmostEqual(skill_score(0.4, 0.2, 1.0), 0.25)  # CSI


class BootstrapTest(unittest.TestCase):
    def test_identical_sources_have_zero_width_interval(self) -> None:
        rng = np.random.default_rng(1)
        dates = pd.date_range("2020-01-01", periods=200, freq="D")
        obs = rng.gamma(0.5, 10, 200)
        frame = pd.DataFrame({"date": dates, "obs": obs, "a": obs + 1, "b": obs + 1})
        res = paired_block_bootstrap(frame, "obs", "a", "b", metric_mae, n_boot=50)
        self.assertEqual((res["diff"], res["ci_low"], res["ci_high"]), (0.0, 0.0, 0.0))

    def test_clearly_better_source_wins_every_resample(self) -> None:
        rng = np.random.default_rng(2)
        dates = pd.date_range("2020-01-01", periods=300, freq="D")
        obs = rng.gamma(0.5, 10, 300)
        frame = pd.DataFrame({"date": dates, "obs": obs, "good": obs + rng.normal(0, 0.5, 300),
                              "bad": obs + rng.normal(0, 5, 300)})
        res = paired_block_bootstrap(frame, "obs", "good", "bad", metric_mae, n_boot=200)
        self.assertLess(res["ci_high"], 0)
        self.assertEqual(res["frac_a_better"], 1.0)

    def test_rows_of_same_day_move_together(self) -> None:
        dates = np.repeat(pd.date_range("2021-01-01", periods=30, freq="D"), 3)
        obs = np.tile([20.0, 0.0, 0.0], 30)
        frame = pd.DataFrame({"date": dates, "obs": obs, "a": obs, "b": np.zeros(90)})
        res = paired_block_bootstrap(frame, "obs", "a", "b", metric_csi(16), n_boot=20)
        self.assertEqual(res["n_days"], 30)
        self.assertEqual(res["ci_low"], 1.0)


class FoldTest(unittest.TestCase):
    def test_rolling_origin(self) -> None:
        folds = rolling_origin_folds(range(2015, 2026), 2021, 2023)
        self.assertEqual(folds[0], {"train": list(range(2015, 2020)), "val": [2020], "test": 2021})
        self.assertEqual(folds[-1]["test"], 2023)
        with self.assertRaises(ValueError):
            rolling_origin_folds(range(2020, 2023), 2021, 2021)


class BaselineTest(unittest.TestCase):
    def test_climatology_and_persistence(self) -> None:
        idx = pd.date_range("2015-01-01", "2018-12-31", freq="D")
        daily = pd.Series(np.where(idx.month == 10, 30.0, 0.0), index=idx)
        clim = doy_climatology(daily, thresholds=[16], window_days=1)
        oct15 = clim.loc[pd.Timestamp("2019-10-15").dayofyear]
        self.assertEqual((oct15["clim_mean"], oct15["clim_p>=16"]), (30.0, 1.0))
        applied = apply_climatology(pd.DatetimeIndex(["2019-10-15", "2019-03-01"]), clim)
        self.assertEqual(applied["clim_mean"].tolist(), [30.0, 0.0])
        gappy = daily.drop(pd.Timestamp("2015-01-02"))
        pers = persistence(gappy)
        self.assertTrue(np.isnan(pers.loc["2015-01-03"]))
        self.assertEqual(pers.loc["2015-10-02"], 30.0)


if __name__ == "__main__":
    unittest.main()
