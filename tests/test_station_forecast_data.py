import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.station_forecast_data import (StationForecastData, calendar_at_end, feature_names,
    future_labels, history_complete, label_names, sample_flags, strict_bilinear,
    target_splits, utc_intervals)


class ContractTests(unittest.TestCase):
    def test_vietnam_end_clock_and_leap_day(self):
        a, b = utc_intervals(np.array([pd.Timestamp('2024-02-29 10:00').value,
                                      pd.Timestamp('2024-02-29 11:00').value]))
        self.assertEqual(str(a[0]), '2024-02-29 02:00:00+00:00')
        self.assertEqual(str(b[0]), '2024-02-29 03:00:00+00:00')
        with self.assertRaises(ValueError):
            utc_intervals(np.array([0, 2*3600_000_000_000]))

    def test_daily_anchor_and_exact_future_days(self):
        a, b = utc_intervals(pd.date_range('2024-02-28 20:00', periods=48, freq='h').as_unit('ns').asi8)
        self.assertEqual(a[0].tz_convert('Asia/Ho_Chi_Minh').hour, 19)
        self.assertEqual(b[23].tz_convert('Asia/Ho_Chi_Minh').hour, 19)
        rain = np.arange(1, 49).reshape(2, 24).sum(1).astype('float32')
        self.assertEqual(rain[0], 300)
        self.assertEqual(future_labels(rain, 1)[0, 0], rain[1])

    def test_no_missing_or_future_in_history(self):
        rain = np.arange(50, dtype='float32'); rain[5] = np.nan
        issue = pd.date_range('2022-01-01', periods=50, freq='h', tz='UTC')
        weather = np.ones((50, 2)); weather[10, 1] = np.nan
        flags = sample_flags(weather, rain, issue, '1h')
        self.assertFalse(flags['sample_ready_r1'][23])
        self.assertFalse(flags['sample_ready_r1'][33])
        self.assertTrue(flags['sample_ready_r1'][34])
        self.assertFalse(flags['sample_ready_r1'][44])  # Last future value is absent.
        self.assertEqual(flags['labels'][24].tolist(), list(range(25, 31)))
        self.assertFalse(history_complete(np.array([1, 0, 1, 1], bool), 3).any())

    def test_entire_target_must_stay_in_fold(self):
        t = pd.DatetimeIndex(['2022-12-31 10:00Z', '2022-12-31 12:00Z',
                              '2022-12-31 17:00Z', '2024-12-31 17:00Z'])
        self.assertEqual(target_splits(t, 6).tolist(), ['train', 'unused', 'cal', 'unused'])
        days = pd.DatetimeIndex(['2022-12-28 12:00Z', '2022-12-29 12:00Z'])
        self.assertEqual(target_splits(days, 72).tolist(), ['train', 'unused'])

    def test_missing_corners_not_reweighted_and_zero_weight_nan_allowed(self):
        nodes = np.array([[[1.], [3.], [5.], [np.nan]]])
        idx = np.array([[0, 1, 2, 3], [0, 1, 2, 3]])
        weights = np.array([[.25, .25, .25, .25], [1, 0, 0, 0]])
        out = strict_bilinear(nodes, idx, weights)
        self.assertTrue(np.isnan(out[0, 0, 0]))
        self.assertEqual(out[0, 1, 0], 1)

    def test_feature_whitelist_never_selects_target_or_other_sources(self):
        self.assertEqual(len(feature_names('1h', 'E7', False)), 44)
        self.assertEqual(len(feature_names('24h', 'E7', True)), 43)
        self.assertEqual(len(feature_names('24h', 'E0', False)), 9)
        self.assertNotIn('era5_tp_mm', feature_names('1h'))
        self.assertFalse(set(feature_names('1h')) & set(label_names('1h')))

    def test_station_without_train_history_not_selected(self):
        t = pd.date_range('2024-01-01', periods=60, freq='h', tz='UTC')
        flags = sample_flags(np.ones((60, 1)), np.ones(60), t, '1h')
        self.assertFalse(flags['station_seen_train'])
        self.assertFalse(flags['sample_ready_r0'].any())

    def test_loader_keeps_gap_rows_and_station_boundaries(self):
        t = pd.date_range('2022-01-01', periods=70, freq='h', tz='UTC')
        frames = []
        for sid in ['ST001', 'ST002']:
            rain = np.arange(70, dtype='float32'); rain[30] = np.nan
            f = pd.DataFrame(dict(station_id=sid, resolution='1h', period_end_utc=t,
                                  latitude=16., longitude=108., rain_mm=rain))
            for name in feature_names('1h', 'E0', False):
                f[name] = 1.
            flags = sample_flags(f[feature_names('1h', 'E0', False)].to_numpy(), rain, t, '1h')
            for key in ['sample_ready_r0', 'sample_ready_r1', 'split']:
                f[key] = flags[key]
            for h, name in enumerate(label_names('1h')):
                f[name] = flags['labels'][:, h]
            frames.append(f)
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder)/'data.parquet'
            table = pa.Table.from_pandas(pd.concat(frames, ignore_index=True), preserve_index=False)
            table = table.replace_schema_metadata({b'pbl6_contract': b'{}'})
            pq.write_table(table, file)
            ds = StationForecastData(file, '1h', experiment='E0')
            self.assertEqual(len(ds), 22)
            self.assertEqual(ds[0]['x'].shape, (24, 12))
            self.assertEqual(ds[0]['y'].tolist(), list(range(24, 30)))
            self.assertTrue(all(np.isfinite(ds[i]['x']).all() for i in range(len(ds))))
            r0 = StationForecastData(file, '1h', experiment='E0', use_rain=False)
            self.assertEqual(len(r0), len(ds))
            self.assertEqual(r0[0]['x'].shape, (24, 11))
            with self.assertRaises(ValueError):
                StationForecastData(file, '1h', split='2025')


if __name__ == '__main__':
    unittest.main()
