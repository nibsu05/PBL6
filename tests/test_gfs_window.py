"""Temporal and scientific-contract tests for the new study, not copies of fit loops."""
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from src.gfs_window import (protocol,fit_mask,cv_masks,calibration_masks,calibrate,
    apply_calibration,macro_rmse,FEATURES)
from src.gfs_window_models import fit_mean
from src.gfs_window_live import assert_preissue,parse_live_day,input_frame


class WindowTests(unittest.TestCase):
    def test_new_year_roles_do_not_fit_calibration_or_retrospective(self):
        f=pd.DataFrame(dict(role=['fit2021_22','fit2023','fit2024','calibration2025','retrospective2026'],
            target_end_utc=pd.to_datetime(['2022-07-01','2023-07-01','2024-07-01','2025-07-01','2026-07-01'],utc=True)))
        self.assertEqual(fit_mask(f,'short').tolist(),[True,False,False,False,False])
        self.assertEqual(fit_mask(f,'long').tolist(),[True,True,True,False,False])
        f.loc[0,'target_end_utc']=pd.Timestamp('2025-01-01',tz='UTC')
        with self.assertRaises(ValueError):fit_mask(f,'long')

    def test_cv_has_full_target_purge_and_unseen_station_guard(self):
        f=pd.DataFrame(dict(issue_utc=pd.to_datetime(['2021-12-01','2021-12-28','2022-01-10','2022-03-31','2022-01-11'],utc=True),
            role=['fit2021_22']*5,station_id=['A','A','A','A','NEW']))
        a,b=cv_masks(f,dict(start='2022-01-01',end='2022-04-01'))
        self.assertEqual(a.tolist(),[True,False,False,False,False])
        self.assertEqual(b.tolist(),[False,False,True,False,False])

    def test_calibration_quarter_and_7day_neighborhood_are_held_out(self):
        f=pd.DataFrame(dict(role=['calibration2025']*5+['retrospective2026'],issue_utc=pd.to_datetime([
            '2025-03-20','2025-03-28','2025-04-02','2025-07-04','2025-07-12','2026-01-01'],utc=True)))
        fit,hold=calibration_masks(f,2)
        self.assertEqual(fit.tolist(),[True,False,False,False,True,False])
        self.assertEqual(hold.tolist(),[False,False,True,False,False,False])

    def test_calibration_nests_probabilities_and_rejects_foreign_year_role(self):
        dates=pd.date_range('2025-01-05','2025-12-20',freq='2D',tz='UTC');n=len(dates)
        y=np.resize([0.,2.,60.,5.,0.,100.],n)
        f=pd.DataFrame(dict(issue_utc=dates,role='calibration2025',station_id=np.resize(['A','B'],n),y_mm=y))
        wet=np.where(y>=1,.7,.2);conditional=np.where(y>=50,.5,.1)
        artifact,full,oof=calibrate(f,[wet],[conditional])
        self.assertTrue(np.isfinite(oof).all());self.assertTrue((oof[:,1]<=oof[:,0]).all())
        np.testing.assert_allclose(full,apply_calibration(artifact,[(wet,conditional)]))
        f.loc[0,'role']='retrospective2026'
        with self.assertRaises(ValueError):calibrate(f,[wet],[conditional])

    def test_macro_metric_does_not_reward_more_rows_at_easy_station(self):
        score=macro_rmse([0,0,0,0],[0,0,0,10],['A','A','A','B'])
        self.assertEqual(score,5.)

    def test_both_mean_objectives_fit_same_explicit_tree_budget(self):
        rng=np.random.default_rng(12);n=150
        f=pd.DataFrame(dict(station_code=np.arange(n)%3,x=rng.normal(size=n),y_mm=rng.gamma(1,8,n)))
        candidate=dict(num_leaves=7,max_depth=3,min_child_samples=10,reg_lambda=5.)
        for objective in ('tweedie','l2'):
            m=fit_mean(f,['station_code','x'],np.ones(n,bool),None,objective,candidate,17,12)
            self.assertEqual(m.n_estimators,12);self.assertTrue(np.isfinite(m.predict(f[['station_code','x']])).all())

    def test_factorial_has_fixed_features_and_separate_mean_target(self):
        p=protocol();self.assertEqual(len(p['cases']),4)
        self.assertEqual({v['features'] for v in p['cases'].values()},{26})
        self.assertEqual([len(FEATURES[x]) for x in ('N0','N1','N3')],[16,21,26])
        self.assertEqual(p['calibration_year'],2025);self.assertEqual(p['no_fit_years'],[2025,2026])

    def test_live_forecast_cannot_be_backdated_or_use_future_retrieval(self):
        issue=pd.Timestamp('2026-11-18T12:00Z')
        assert_preissue(issue,['2026-11-18T11:40Z'],'2026-11-18T11:50Z')
        with self.assertRaises(ValueError):assert_preissue(issue,[],'2026-11-18T12:00Z')
        with self.assertRaises(ValueError):assert_preissue(issue,['2026-11-18T11:59Z'],'2026-11-18T11:50Z')

    def test_live_parser_preserves_missing_values_and_sum_qc(self):
        times=pd.date_range('2026-11-17 20:00',periods=24,freq='h')
        payload=dict(stats=[dict(timePoint=t.strftime('%H:%M %d/%m'),stations=[dict(id=1,depth=1.)]) for t in times])
        payload['stats'].append(dict(timePoint='Total',stations=[dict(id=1,depth=24.)]))
        a=parse_live_day(payload,'2026-11-18',{'1':'A'},['A'])
        self.assertTrue(a['valid'].all())
        payload['stats'][-1]['stations'][0]['depth']=25.
        self.assertFalse(parse_live_day(payload,'2026-11-18',{'1':'A'},['A'])['valid'].any())
        payload['stats'][23]['stations'][0]['depth']='-'
        a=parse_live_day(payload,'2026-11-18',{'1':'A'},['A'])
        self.assertTrue(a['valid'][:23].all());self.assertFalse(a['valid'][23,0]);self.assertTrue(np.isnan(a['raw'][23,0]))
        partial=dict(stats=payload['stats'][:6]+[payload['stats'][-1]])
        b=parse_live_day(partial,'2026-11-18',{'1':'A'},['A'])
        self.assertTrue(b['valid'][:6].all());self.assertFalse(b['valid'][6:].any())

    def test_live_features_ignore_hours_after_observation_cutoff(self):
        issue=pd.Timestamp('2026-11-18T12:00Z')
        registry=pd.DataFrame(dict(canonical_id=['ST001'],latitude=[16.],longitude=[108.]))
        parsed={}
        for day in pd.date_range('2026-11-11','2026-11-18'):
            times=pd.date_range(day-pd.Timedelta(hours=4),periods=24,freq='h')
            for channel in ('legacy','modern'):
                parsed[(channel,day.strftime('%Y-%m-%d'))]=dict(times=times,raw=np.ones((24,1),dtype='float32'),
                    valid=np.full((24,1),channel=='legacy'))
        terrain=pd.DataFrame([dict(canonical_id='ST001',**{c:0. for c in FEATURES['N3'] if c.startswith('dem_')})])
        gfs=dict(met_names=['rh850','t850_k','u850','v850','pwat'],met=np.tile([80.,290.,1.,2.,30.],(3,1,1)),rain_day_mm=np.ones((3,1)))
        with patch('src.gfs_window_live.pd.read_csv',return_value=terrain):
            a=input_frame(issue,registry,registry,parsed,gfs,pd.Timestamp('2026-11-18T11:45Z'))
            parsed[('legacy','2026-11-18')]['raw'][-1,0]=123456.
            b=input_frame(issue,registry,registry,parsed,gfs,pd.Timestamp('2026-11-18T11:45Z'))
        pd.testing.assert_frame_equal(a,b)
        self.assertTrue(a.rain_recent1h_mm.eq(1.).all())
        self.assertTrue(a.rain_recent24h_mm.eq(24.).all())


if __name__=='__main__':unittest.main()
