import unittest

import numpy as np
import pandas as pd

from scripts.inspect_vrain_spatial_panel import spatial_weights


class SpatialDiagnosticsTests(unittest.TestCase):
    def test_symmetric_two_gauges_split_area_and_far_site_has_zero_weight(self):
        cells = pd.DataFrame(dict(lat=[15.7, 15.7], lon=[107.95, 108.05],
                                  weight=[.5, .5], zone=['test', 'test']))
        stations = pd.DataFrame(dict(latitude=[15.7, 15.7, 30.],
                                     longitude=[107.95, 108.05, 120.]))
        weights, summary, *_ = spatial_weights(cells, stations)
        np.testing.assert_allclose(weights, [.5, .5, 0], atol=.002)
        self.assertEqual(summary['stations_with_positive_weight'], 2)
        self.assertAlmostEqual(weights.sum(), 1., places=8)

    def test_duplicate_station_location_requires_identity_resolution(self):
        cells = pd.DataFrame(dict(lat=[15.7], lon=[108.], weight=[1.], zone=['test']))
        stations = pd.DataFrame(dict(latitude=[15.7, 15.7], longitude=[108., 108.]))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            spatial_weights(cells, stations)


if __name__ == '__main__':
    unittest.main()
