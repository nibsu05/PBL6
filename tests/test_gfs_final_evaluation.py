import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from src.gfs_final_metrics import holm, summary_tables, bootstrap_comparisons

MODELS = ["LGB_N0", "LGB_N1", "LGB_N3", "GRU_N5", "GRU_N3_LINEAR6", "MOS", "CLIM"]


def examples():
    rows = []
    for i, date in enumerate(pd.date_range("2025-01-01", periods=40, tz="UTC")):
        for station in ("A", "B"):
            for h in (1, 2, 3):
                y = 80. if (i+int(station == "B")) % 4 == 0 else 2.
                row = dict(evaluation_set="test2025_legacy", issue_utc=date,
                    target_end_utc=date+pd.Timedelta(hours=24*h), station_id=station, horizon=h, y_mm=y)
                for model, error in zip(MODELS, [5, 3, 2, 1, 3, 4, 6]):
                    row[model+"_mean"] = y+error
                    row[model+"_median"] = y+error
                    row[model+"_p1"] = .7
                    row[model+"_p50"] = .2
                rows.append(row)
    return pd.DataFrame(rows)


def protocol():
    return dict(primary_feature_contrasts=[["LGB_N1", "LGB_N0"], ["LGB_N3", "LGB_N1"], ["GRU_N5", "GRU_N3_LINEAR6"]],
        primary_skill_contrasts=[["LGB_N3", "MOS", "mean_rmse"], ["GRU_N5", "MOS", "median_mae"]],
        secondary_contrasts=[], uncertainty=dict(draws=500, block_days=14, seed=1701))


class FinalEvaluationTests(unittest.TestCase):
    def test_holm_monotone_adjustment_and_missing_hypothesis(self):
        np.testing.assert_allclose(holm([.01, .04, .03]), [.03, .06, .06])
        actual = holm([.01, np.nan, .04])
        np.testing.assert_allclose(actual[[0, 2]], [.03, .08])
        self.assertTrue(np.isnan(actual[1]))

    def test_point_metrics_are_station_macro_and_functionals_separate(self):
        f = examples()
        f.loc[f.station_id.eq("B"), "LGB_N0_mean"] = f.loc[f.station_id.eq("B"), "y_mm"]+9
        tables = summary_tables(f, MODELS, {})
        row = tables["point_metrics"].query("model == 'LGB_N0' and horizon == 1 and functional == 'mean'").iloc[0]
        self.assertEqual(row.macro_rmse, 7.)
        other = tables["point_metrics"].query("model == 'LGB_N0' and horizon == 1 and functional == 'median'").iloc[0]
        self.assertEqual(other.macro_mae, 5.)

    def test_probability_reports_keep_undefined_far_and_counts(self):
        tables = summary_tables(examples(), MODELS, {})
        row = tables["event_metrics"].query("model == 'LGB_N0' and horizon == 1 and threshold_mm == 50").iloc[0]
        self.assertEqual(row.hits, 0)
        self.assertEqual(row.false_alarms, 0)
        self.assertTrue(np.isnan(row.macro_far))
        self.assertGreater(row.misses, 0)

    def test_primary_families_and_adjusted_intervals_are_predeclared(self):
        table = bootstrap_comparisons(examples(), MODELS, protocol())
        features = table[table.family.eq("feature")]
        skill = table[table.family.eq("skill")]
        self.assertEqual(len(features), 9)
        self.assertEqual(len(skill), 6)
        self.assertTrue(features.family_size.eq(9).all())
        self.assertTrue(skill.family_size.eq(6).all())
        self.assertTrue(features.primary_improvement_supported.all())
        self.assertTrue((features.holm_p >= features.approximate_p).all())
        target = features.query("model == 'LGB_N1' and horizon == 1").iloc[0]
        self.assertAlmostEqual(target.difference, -2.)
        self.assertEqual(target.full_station_support_fraction, 1.)

    def test_development_cannot_be_declared_confirmatory(self):
        f = examples()
        f["evaluation_set"] = "dev2024_legacy"
        p = protocol()
        p["uncertainty"]["draws"] = 30
        result = bootstrap_comparisons(f, MODELS, p)
        self.assertFalse(result.primary_improvement_supported.any())

    def test_gate_checked_before_any_holdout_parquet_read(self):
        from scripts.score_gfs_final import load_holdout_examples
        with patch("scripts.score_gfs_final.record_holdout_opening", side_effect=ValueError("gate closed")):
            with patch("scripts.score_gfs_final.pd.read_parquet") as read:
                with self.assertRaisesRegex(ValueError, "gate closed"):
                    load_holdout_examples()
                read.assert_not_called()

    def test_seed_scores_preserve_global_row_positions_and_station_macro(self):
        from scripts.score_gfs_final import seed_scores
        f = examples()
        f.loc[f.station_id.eq("B"), "LGB_N0_mean"] = f.loc[f.station_id.eq("B"), "y_mm"]+9
        values = {head: f["LGB_N0_"+head].to_numpy() for head in ("mean", "median", "p1", "p50")}
        result = seed_scores(f, {"LGB_N0": [values, values, values]})
        self.assertEqual(len(result), 9)
        np.testing.assert_allclose(result.mean_rmse, 7.)
        np.testing.assert_allclose(result.median_mae, 5.)


if __name__ == "__main__":
    unittest.main()
