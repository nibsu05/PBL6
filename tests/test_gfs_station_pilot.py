import unittest
from unittest.mock import Mock
import numpy as np
import pandas as pd

from src.gfs_station import (accumulated_hours, choose_records, issue_contract,
    parse_index, rainfall_windows, range_groups, regular_grid_weights, sample_field)
from src.gfs_station_dataset import FEATURES, event_metrics, forecast_met, gauge_history, macro_metrics


class GfsContractTests(unittest.TestCase):
    def test_accumulation_disambiguates_six_hour_and_cycle_total(self):
        s = '1:0:d=2021010100:APCP:surface:6-12 hour acc fcst:\n2:100:d=2021010100:APCP:surface:0-12 hour acc fcst:\n3:250:d=2021010100:TMP:2 m above ground:12 hour fcst:\n'
        chosen = choose_records(parse_index(s), 12)
        self.assertEqual(chosen['rain_cumulative'].start, 100)
        self.assertEqual(chosen['rain_cumulative'].stop, 249)
        self.assertEqual(accumulated_hours('0-1 day acc fcst'), (0, 24))
        with self.assertRaises(ValueError):
            choose_records(parse_index(s.replace('0-12 hour', '0-11 hour')), 12)

    def test_duplicate_offsets_and_open_ended_ranges_rejected(self):
        with self.assertRaises(ValueError):
            parse_index('1:0:d:x:y:z:\n2:0:d:x:y:z:')
        with self.assertRaises(ValueError):
            choose_records(parse_index('1:0:d:APCP:surface:0-12 hour acc fcst:'), 12)

    def test_only_adjacent_messages_coalesced(self):
        from src.gfs_station import IndexRecord
        chosen = dict(a=IndexRecord(10,19,'a','a','a'), b=IndexRecord(20,29,'b','b','b'),
                      c=IndexRecord(100,109,'c','c','c'))
        self.assertEqual([len(g) for g in range_groups(chosen)], [2,1])

    def test_exact_http_range_required_before_reading_body(self):
        from scripts.collect_gfs_station_pilot import range_bytes
        response = Mock(status_code=200, headers={})
        session = Mock(); session.get.return_value = response
        with self.assertRaises(ValueError):
            range_bytes(session,'https://example.invalid/grib',100,199)
        response.close.assert_called_once()

    def test_three_nonoverlapping_days_and_no_large_negative_clipping(self):
        v = np.array([[2,0],[12,0],[32,.01],[62,0]],float)
        rain, flags = rainfall_windows(v,np.array([.01]*4))
        np.testing.assert_allclose(rain[:,0],[10,20,30])
        self.assertEqual(int(flags.sum()),1)
        with self.assertRaises(ValueError):
            rainfall_windows(np.array([[5],[4],[6],[9]],float),np.array([.01]*4))

    def test_initialization_issue_and_reserved_year(self):
        init, issue = issue_contract('2024-02-29')
        self.assertEqual(issue.tz_convert('Asia/Ho_Chi_Minh').hour,19)
        self.assertEqual((issue-init)/pd.Timedelta(hours=1),12)
        with self.assertRaises(ValueError):
            issue_contract('2024-12-29')
        with self.assertRaises(ValueError):
            issue_contract('2025-01-01')

    def test_bilinear_sampling_uses_native_north_south_geometry(self):
        lat=np.array([15.81,16.02]);lon=np.array([108.11,107.81])
        idx,w=regular_grid_weights(lat,lon)
        values=np.zeros(1440*721)
        for k in np.unique(idx):
            la=90-(k//1440)*.25;lo=(k%1440)*.25
            values[k]=la+2*lo
        np.testing.assert_allclose(sample_field(values,idx,w),lat+2*lon,rtol=1e-6)
        values[idx[0,0]]=np.nan
        self.assertTrue(np.isnan(sample_field(values,idx,w)[0]))

    def test_gauge_latency_excludes_current_19h_observation(self):
        hourly=np.arange(24*12,dtype=float)[:,None]
        daily=hourly.reshape(12,24,1).sum(1)
        result=gauge_history(hourly,daily,8,0)
        self.assertEqual(result['rain_lag_day1_mm'],daily[7,0])
        self.assertEqual(result['rain_lag_day7_mm'],daily[1,0])
        self.assertEqual(result['rain_recent1h_mm'],hourly[8*24+22,0])
        expected=hourly[8*24-1:8*24+23,0].sum()
        self.assertEqual(result['rain_recent24h_mm'],expected)
        hourly[8*24+23,0]=1e9
        self.assertEqual(gauge_history(hourly,daily,8,0)['rain_recent24h_mm'],expected)

    def test_missing_rain_not_zero_filled(self):
        h=np.ones((24*12,1));d=h.reshape(12,24,1).sum(1);h[8*24+22,0]=np.nan
        self.assertTrue(np.isnan(gauge_history(h,d,8,0)['rain_recent24h_mm']))

    def test_humidity_derived_consistently_and_features_whitelisted(self):
        met=forecast_met(['t850_k','rh850','u850','v850','pwat'],[293.15,80,3,4,40])
        self.assertTrue(10<met['gfs_q850_gkg']<20)
        self.assertEqual(met['gfs_wspd850'],5)
        for names in FEATURES.values():
            self.assertNotIn('y_mm',names)
            self.assertNotIn('rain_raw_mm',names)
            self.assertEqual(len(names),len(set(names)))

    def test_macro_metric_gives_each_station_equal_weight(self):
        f=pd.DataFrame(dict(station_id=['A']*100+['B'],y=[0]*101,pred=[1]*100+[10]))
        report,_=macro_metrics(f)
        self.assertEqual(report['macro_mae'],5.5)
        self.assertAlmostEqual(report['micro_mae'],110/101)

    def test_high_pod_can_coexist_with_high_false_alarm_and_negative_bss(self):
        r=event_metrics([1,0,0,0],np.ones(4),np.full(4,.25))
        self.assertEqual(r['pod'],1)
        self.assertEqual(r['far'],.75)
        self.assertLess(r['bss'],0)

    def test_small_gru_handles_three_horizons_zero_rain_and_backpropagation(self):
        import torch
        from scripts.run_gfs_station_gru import RainGRU,loss_fn
        torch.set_num_threads(2)
        model=RainGRU(17)
        mu,logits=model(torch.ones(4,7,1),torch.zeros(4,3,17),torch.tensor([0,1,20,85]))
        self.assertEqual(tuple(mu.shape),(4,3))
        self.assertEqual(tuple(logits.shape),(4,3,2))
        self.assertTrue((mu>0).all())
        loss=loss_fn(mu,logits,torch.zeros(4,3),torch.zeros(4,3,2))
        loss.backward()
        self.assertTrue(torch.isfinite(loss))
        self.assertTrue(all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None))


if __name__ == '__main__':
    unittest.main()
