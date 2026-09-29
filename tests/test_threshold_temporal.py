"""Kiểm tra chọn ngưỡng và ranh giới train/calibration/assessment."""
import unittest
import numpy as np
import pandas as pd
from run_threshold_temporal_study import choose_precision_thresholds, policy_mask, explicit_datasets


class ThresholdTemporalTest(unittest.TestCase):
    def test_precision_constraint_and_abstention(self):
        y = np.zeros((40,2)); y[:10,0] = 8
        p = np.full((40,2), .1); p[:10,0] = .8; p[10:35,0] = .5
        policy, _ = choose_precision_thresholds(y,p)
        self.assertTrue(policy['horizons'][0]['enabled'])
        self.assertFalse(policy['horizons'][1]['enabled'])
        mask = policy_mask(p,policy)
        self.assertEqual(int(mask[:,0].sum()),10)
        self.assertEqual(int(mask[:,1].sum()),0)

    def test_calendar_boundaries_and_train_only_scaler(self):
        t = pd.date_range('2025-01-01',periods=400,freq='h',tz='Asia/Ho_Chi_Minh')
        values = np.ones(400); values[200:] = 100
        frame = pd.DataFrame({'datetime':t,'precipitation':values,'feature':values})
        ds, _, scaler = explicit_datasets(frame,['precipitation','feature'],t[200],t[300],t[-1]+pd.Timedelta(hours=1))
        np.testing.assert_allclose(scaler.center_,1.)
        self.assertTrue((ds[0].target_datetimes.iloc[:,-1] < t[200]).all())
        self.assertTrue((ds[1].target_datetimes.iloc[:,0] >= t[200]).all())
        self.assertTrue((ds[1].target_datetimes.iloc[:,-1] < t[300]).all())
        self.assertTrue((ds[2].target_datetimes.iloc[:,0] >= t[300]).all())


if __name__ == '__main__':
    unittest.main()
