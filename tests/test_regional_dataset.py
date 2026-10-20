"""Kiểm tra trọng số, đơn vị và thông tin tương lai của dữ liệu vùng."""
import unittest
import numpy as np
import pandas as pd
from src.regional_dataset import (weighted_summary, cell_areas_km2,
                                 legacy_predictors, supervised_windows, LABEL,
                                 aggregate_block, feature_catalog, SPATIAL_NAMES, TIME_NAMES)


class RegionalDatasetTest(unittest.TestCase):
    def test_spatial_features_do_not_use_target_and_v2_keeps_v1(self):
        names = list(dict.fromkeys(['y_gsmap_gc_mm','label_permanent',
                                    *SPATIAL_NAMES,*TIME_NAMES]))
        cells = pd.DataFrame({'lat':[16.,16.,16.], 'coast_dist_km':[10.,50.,90.],
                              'elev_mean_m':[10.,300.,1000.], 'ne_upslope_m':[0.,100.,200.]})
        cube = np.ones((3,4,len(names)),dtype=float)
        cube[:,:,names.index('sp_hpa')] = 1000.
        cube[:,:,names.index('u850')] = -3.
        cube[:,:,names.index('v850')] = -3.
        cube[:,:,names.index('tcwv')] = np.array([10.,20.,40.])[:,None]
        a,b = aggregate_block(cube,names,cells,[1.,1.,2.])
        self.assertEqual(a['mean__tcwv'][0],27.5)
        self.assertEqual(b['coastal__tcwv'][0],10.)
        self.assertEqual(b['highland__tcwv'][0],40.)
        for k in a: np.testing.assert_array_equal(a[k],b[k])
        changed = cube.copy();changed[:,:,names.index('y_gsmap_gc_mm')] = 999.
        _,other = aggregate_block(changed,names,cells,[1.,1.,2.])
        for k in feature_catalog(names): np.testing.assert_array_equal(b[k],other[k])
        self.assertNotIn(LABEL,feature_catalog(names))

    def test_area_average_preserves_depth_not_sum_and_rejects_missing_support(self):
        s = weighted_summary(np.array([[10., 30.], [10., np.nan]]), [1., 3.])
        self.assertEqual(s['mean'][0], 25.)
        self.assertAlmostEqual(s['std'][0], np.sqrt(75.))
        self.assertEqual(s['p90'][0], 30.)
        self.assertEqual(s['coverage'][1], .25)
        self.assertTrue(np.isnan(s['mean'][1]))
        self.assertTrue(np.isnan(s['max'][1]))
        self.assertGreater(cell_areas_km2([15.])[0], cell_areas_km2([16.])[0])

    def test_legacy_units_wind_direction_and_timezone_are_not_silently_reused(self):
        f = pd.DataFrame({'datetime':['2023-01-01 07:00:00+07:00'],
                          'temperature_2m':[20.], 'relative_humidity_2m':[80.],
                          'surface_pressure':[1000.], 'sea_surface_temperature':[26.],
                          'cape':[100.], 'tcwv':[40.], 'swvl1':[.3], 'u_850':[-3.],
                          'v_850':[-4.], 'specific_humidity_850':[.01],
                          'wind_speed_10m':[36.], 'wind_direction_10m':[90.],
                          'oni_anom':[9.], 'precipitation':[999.]})
        out = legacy_predictors(f)
        self.assertEqual(out.index[0], pd.Timestamp('2023-01-01', tz='UTC'))
        self.assertAlmostEqual(out.mean__u10.iloc[0], -10.)
        self.assertAlmostEqual(out.mean__v10.iloc[0], 0., places=10)
        self.assertEqual(out.mean__q850_gkg.iloc[0], 10.)
        self.assertNotIn('oni_anom', out)
        self.assertNotIn('precipitation', out)

    def test_windows_do_not_read_future_predictors_or_cross_label_year(self):
        dates = pd.date_range('2020-12-30', periods=80, freq='h', tz='UTC')
        f = pd.DataFrame({'x':np.arange(80.), LABEL:np.ones(80),
                          'label_permanent':True}, index=dates)
        out = supervised_windows(f, ['x'], stride=1)
        k = np.where(out['issue']==24)[0][0]
        self.assertTrue(out['valid'][k])
        self.assertEqual(out['x'][k, 0], 23.)
        np.testing.assert_array_equal(out['y'][k], [3.,6.])
        changed = f.copy(); changed.loc[dates[24]:,'x'] = 10000.
        after = supervised_windows(changed, ['x'], stride=1)
        np.testing.assert_array_equal(out['x'][k], after['x'][k])
        crossing = np.where(out['issue']==47)[0][0]
        self.assertFalse(out['valid'][crossing])
        missing = f.copy();missing.loc[dates[3], 'x'] = np.nan
        self.assertFalse(supervised_windows(missing,['x'],stride=1)['valid'][k])


if __name__ == '__main__':
    unittest.main()
