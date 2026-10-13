"""Baseline pilot phải tính chu kỳ ngày và chỉ dùng nhãn train."""
import unittest
from types import SimpleNamespace
import numpy as np
import pandas as pd
from scripts.pilot_bilstm_v2 import climatology


class PilotBaselineTest(unittest.TestCase):
    def test_climatology_conditions_on_hour_without_evaluation_labels(self):
        hours = pd.date_range("2015-01-01", "2016-01-02", freq="h", inclusive="left")
        cube = np.zeros((1, len(hours), 1), dtype=np.float32)
        train = np.array([[0, 0], [0, 6], [0, 24], [0, 30]], dtype=np.int32)
        for _, t in train:
            cube[0, t:t+3, 0] = 1 if t % 24 == 0 else 10
        evaluation = np.array([[0, 8760], [0, 8766]], dtype=np.int32)
        ds = SimpleNamespace(cube=cube, hours=hours, cells=pd.DataFrame(index=[0]),
                             feature_index={"y_gsmap_gc_mm": 0})
        amount, prob = climatology(ds, train, evaluation)
        np.testing.assert_allclose(amount[:, 0], [3, 30])
        np.testing.assert_allclose(prob[:, 0, 1], [0.25, 0.75])
        cube[0, 8760:, 0] = 1000
        amount2, prob2 = climatology(ds, train, evaluation)
        np.testing.assert_array_equal(amount, amount2)
        np.testing.assert_array_equal(prob, prob2)


if __name__ == "__main__":
    unittest.main()
