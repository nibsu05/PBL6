import unittest
import numpy as np
from src.vrain_label_feasibility import neighbor_weights, error_metrics, weighted_quantiles


class LabelFeasibilityTests(unittest.TestCase):
    def test_heldout_zero_distance_cannot_leak_its_observation(self):
        w = neighbor_weights([[0., 1., 2.]], [[False, True, True]], k=2)
        self.assertEqual(w[0, 0], 0)
        np.testing.assert_allclose(w, [[0, .8, .2]])

    def test_constant_field_is_preserved_and_no_sources_remain_missing(self):
        w = neighbor_weights([[1., 3.], [2., 4.]], [[True, True], [False, False]])
        self.assertAlmostEqual(float(w[0] @ [7., 7.]), 7.)
        self.assertEqual(float(w[1].sum()), 0.)

    def test_exact_coordinate_and_frequency_quantiles(self):
        np.testing.assert_allclose(neighbor_weights([[0., 2.]], [True, True]), [[1., 0.]])
        self.assertEqual(weighted_quantiles([0., 10.], [9, 1], (.5,)), [0.])

    def test_metrics_do_not_make_zero_rain_relative_error_finite(self):
        self.assertIsNone(error_metrics([0, 0], [0, 1])['nrmse'])
        self.assertEqual(error_metrics([1, np.nan], [2, 0])['n'], 1)


if __name__ == '__main__':
    unittest.main()
