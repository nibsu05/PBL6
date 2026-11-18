import unittest
import numpy as np
import pandas as pd
from src.gfs_daily import FEATURES
from src.gfs_daily_gru import DailyGRU, normalizers
from src.gfs_capacity_control import control_arrays, fixed_projection, PROJECTION_NAMES, fit_control


def frame():
    rng = np.random.default_rng(9)
    f = pd.DataFrame({name: rng.uniform(1, 5, size=36) for name in FEATURES["N3"]})
    f["station_code"] = 0
    f["horizon"] = [1, 2, 3]*12
    f["y_mm"] = rng.uniform(0, 70, len(f))
    f["target_end_utc"] = pd.Timestamp("2024-05-01", tz="UTC")
    return f


class CapacityTests(unittest.TestCase):
    def test_counts_and_nearest_width_are_determined_without_labels(self):
        count = lambda c, h: sum(p.numel() for p in DailyGRU(c, 16, h).parameters())
        self.assertEqual(count(18, 24), 4364)
        self.assertEqual(count(24, 24), 4796)
        self.assertEqual(count(18, 27), 4751)
        self.assertEqual(min(range(1, 49), key=lambda h: abs(count(18, h)-4796)), 27)

    def test_projection_is_fixed_and_uses_no_targets_or_derived_variables(self):
        np.testing.assert_array_equal(fixed_projection(), fixed_projection())
        self.assertEqual(np.linalg.matrix_rank(fixed_projection()), 6)
        self.assertFalse(set(PROJECTION_NAMES) & {"y_mm", "gfs_q850_gkg", "wind_upslope", "station_code"})

    def test_projection_scaling_ignores_nontraining_weather_and_labels(self):
        f = frame()
        train = np.arange(12) < 6
        a, p = control_arrays(f, "GRU_N3_LINEAR6", train)
        changed = f.copy()
        changed.loc[18:, PROJECTION_NAMES] = 1e8
        changed.loc[18:, "y_mm"] = 1e7
        b, q = control_arrays(changed, "GRU_N3_LINEAR6", train)
        for name in p:
            np.testing.assert_array_equal(p[name], q[name])
        np.testing.assert_array_equal(a["context"][train], b["context"][train])
        first, second = normalizers(a, train), normalizers(b, train)
        for name in first:
            np.testing.assert_array_equal(first[name], second[name])

    def test_linear_inputs_are_exact_redundant_combinations(self):
        f = frame()
        raw, p = control_arrays(f, "GRU_N3_LINEAR6", np.arange(12) < 6)
        source = f[PROJECTION_NAMES].to_numpy("float32").reshape(12, 3, 10)
        expected = ((source-p["mean"])/p["std"]) @ p["matrix"].T
        np.testing.assert_allclose(raw["context"][:, :, -6:], expected)
        self.assertEqual(raw["context"].shape, (12, 3, 24))

    def test_replay_projection_never_refits_on_new_rows(self):
        f = frame()
        _, p = control_arrays(f, "GRU_N3_LINEAR6", np.arange(12) < 6)
        subset = f.iloc[18:].copy()
        raw, actual = control_arrays(subset, "GRU_N3_LINEAR6", projection=p)
        self.assertIs(actual, p)
        self.assertEqual(raw["context"].shape, (6, 3, 24))

    def test_holdout_targets_cannot_enter_control_training(self):
        f = frame()
        f["target_end_utc"] = pd.Timestamp("2025-01-02", tz="UTC")
        with self.assertRaisesRegex(ValueError, "holdout"):
            fit_control(f, "GRU_N3_WIDE", np.arange(12) < 6,
                        dict(hidden=16, head=27, lr=.001), 1, 17)

    def test_unknown_control_and_missing_fit_mask_rejected(self):
        with self.assertRaises(ValueError):
            control_arrays(frame(), "unknown")
        with self.assertRaises(ValueError):
            control_arrays(frame(), "GRU_N3_LINEAR6")


if __name__ == "__main__":
    unittest.main()
