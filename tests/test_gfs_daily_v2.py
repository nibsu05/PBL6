import unittest
import numpy as np
import pandas as pd
from src.gfs_daily import (FEATURES,N0,RAW_MET,DERIVED_MET,TERRAIN,INTERACTION,HISTORY,
    gauge_history,cv_masks,nested_probabilities,calibrate_nested,crossfit_calibration,choose_cutoff,
    TREE_CANDIDATES)
from src.gfs_daily_models import fit_tree,predict_tree
from src.gfs_daily_evaluation import block_draw_counts,paired_uncertainty


class DailyContractTests(unittest.TestCase):
    def test_feature_comparisons_hold_raw_ingredients_fixed(self):
        self.assertEqual(set(FEATURES['N2'])-set(FEATURES['N1']),set(DERIVED_MET))
        self.assertEqual(set(FEATURES['N5'])-set(FEATURES['N4']),set(INTERACTION))
        self.assertTrue(set(RAW_MET+TERRAIN)<=set(FEATURES['N4']))
        for names in FEATURES.values():
            self.assertEqual(len(names),len(set(names)))
            self.assertFalse(set(names)&{'y_mm','target_end_utc','split'})

    def test_gauge_delays_exclude_unavailable_bins_and_keep_calendar_lags(self):
        hourly=np.arange(24*12,dtype=float)[:,None];daily=hourly.reshape(12,24,1).sum(1)
        for delay in (1,3,6):
            got=gauge_history(hourly,daily,8,0,delay);last=24*8+23-delay
            self.assertEqual(got['rain_recent1h_mm'],hourly[last,0])
            self.assertEqual(got['rain_recent24h_mm'],hourly[last-23:last+1,0].sum())
            self.assertEqual(got['rain_lag_day1_mm'],daily[7,0])
        with self.assertRaises(ValueError):gauge_history(hourly,daily,8,0,2)

    def test_missing_older_bin_cannot_be_zero_imputed_in_delay_sensitivity(self):
        hourly=np.ones((24*12,1));daily=hourly.reshape(12,24,1).sum(1)
        hourly[8*24-5,0]=np.nan
        self.assertTrue(np.isfinite(gauge_history(hourly,daily,8,0,1)['rain_recent24h_mm']))
        self.assertTrue(np.isnan(gauge_history(hourly,daily,8,0,6)['rain_recent24h_mm']))

    def test_train_only_cv_purges_target_overlap_and_excludes_unseen_stations(self):
        when=pd.to_datetime(['2021-06-01','2021-12-20','2021-12-26','2022-01-01','2022-01-02','2022-03-31','2023-01-01','2024-01-01'],utc=True)+pd.Timedelta(hours=12)
        f=pd.DataFrame(dict(issue_utc=when,station_id=['A','A','A','A','B','A','A','A'],split=['train']*6+['cal','dev']))
        train,valid=cv_masks(f,dict(start='2022-01-01',end='2022-04-01'))
        self.assertEqual(np.flatnonzero(train).tolist(),[0,1])
        self.assertEqual(np.flatnonzero(valid).tolist(),[3])
        self.assertFalse((train&valid).any())

    def test_nested_probabilities_remain_ordered_after_seed_average(self):
        rng=np.random.default_rng(9)
        outputs=[nested_probabilities(rng.random(200),rng.random(200)) for _ in range(3)]
        p=np.mean(outputs,axis=0)
        self.assertTrue((p[:,1]<=p[:,0]).all())
        self.assertTrue(((p>=0)&(p<=1)).all())
        with self.assertRaises(ValueError):nested_probabilities([np.nan],[.5])
        with self.assertRaises(ValueError):nested_probabilities([1.1],[.5])

    def test_calibration_never_fits_development_labels(self):
        y=np.array([0,2,70,0,5,60,0,80],float);cal=np.array([True]*6+[False]*2)
        wet=np.linspace(.1,.9,8);conditional=np.linspace(.05,.8,8)
        first,_=calibrate_nested(wet,conditional,y,cal)
        y[~cal]=1000-y[~cal]
        second,_=calibrate_nested(wet,conditional,y,cal)
        np.testing.assert_allclose(first,second)
        self.assertTrue((first[:,1]<=first[:,0]).all())

    def test_quarter_crossfit_does_not_use_held_out_labels(self):
        dates=pd.to_datetime(['2023-01-10','2023-01-20','2023-04-10','2023-04-20','2023-07-10','2023-07-20','2023-10-10','2023-10-20','2024-01-10'],utc=True)
        f=pd.DataFrame(dict(issue_utc=dates,split=['cal']*8+['dev'],y_mm=[0,70,2,80,0,60,1,90,5]))
        wet=[np.linspace(.1,.9,len(f))];conditional=[np.linspace(.05,.8,len(f))]
        _,first,_=crossfit_calibration(f,wet,conditional)
        changed=f.copy();changed.loc[:1,'y_mm']=[1000,0]
        _,second,_=crossfit_calibration(changed,wet,conditional)
        np.testing.assert_allclose(first[:2],second[:2])

    def test_cutoff_uses_calibration_labels_and_one_rule_for_both_events(self):
        f=pd.DataFrame(dict(split=['cal']*4+['dev']*2,station_id=['A']*6,y_mm=[0,2,80,0,4,100]))
        probability=np.array([[.1,.01],[.7,.1],[.9,.7],[.2,.05],[.9,.1],[.8,.5]])
        first,grid=choose_cutoff(f,probability,[.2,.5,.8])
        f.loc[f.split.eq('dev'),'y_mm']=0
        second,_=choose_cutoff(f,probability,[.2,.5,.8])
        self.assertEqual(first,second)
        self.assertFalse(((probability[:,1]>=first)&(probability[:,0]<first)).any())

    def test_tree_fitting_ignores_labels_outside_train_and_validation(self):
        rng=np.random.default_rng(18);n=300
        f=pd.DataFrame({name:rng.normal(size=n) for name in FEATURES['N3']})
        f['station_code']=np.arange(n)%3;f['y_mm']=np.maximum(0,5+3*f.gfs_rain_mm+rng.normal(size=n))
        train=np.arange(n)<200;valid=(np.arange(n)>=200)&(np.arange(n)<250)
        candidate=dict(TREE_CANDIDATES[0],min_child_samples=5)
        model=fit_tree(f,FEATURES['N3'],train,valid,'mean',candidate,trees=25)
        changed=f.copy();changed.loc[~(train|valid),'y_mm']=10000
        other=fit_tree(changed,FEATURES['N3'],train,valid,'mean',candidate,trees=25)
        np.testing.assert_allclose(predict_tree(model,FEATURES['N3'],f,'mean'),predict_tree(other,FEATURES['N3'],f,'mean'))

    def test_gru_normalizers_and_target_scale_are_train_only(self):
        from src.gfs_daily_gru import arrays,normalizers
        f=pd.DataFrame({name:np.ones(18) for name in FEATURES['N3']})
        f['station_code']=0;f['horizon']=[1,2,3]*6;f['y_mm']=2.
        tr=np.array([True]*3+[False]*3)
        first=normalizers(arrays(f,'N3'),tr)
        f.loc[9:,'y_mm']=1e7;f.loc[9:,'gfs_rain_mm']=1e6;f.loc[9:,HISTORY]=1e5
        second=normalizers(arrays(f,'N3'),tr)
        for key in first:np.testing.assert_allclose(first[key],second[key])

    def test_gru_zero_rain_batch_has_finite_gradients_and_dual_functionals(self):
        import torch
        from src.gfs_daily_gru import DailyGRU,loss_function
        torch.set_num_threads(2);model=DailyGRU(18)
        point,logits=model(torch.zeros(4,7,1),torch.zeros(4,3,18),torch.tensor([0,1,50,85]))
        self.assertEqual(tuple(point.shape),(4,3,2));self.assertEqual(tuple(logits.shape),(4,3,2))
        self.assertTrue((point>0).all())
        loss=loss_function(point,logits,torch.zeros(4,3),torch.zeros(4,3,2));loss.backward()
        self.assertTrue(torch.isfinite(loss))
        self.assertTrue(all(torch.isfinite(v.grad).all() for v in model.parameters() if v.grad is not None))

    def test_calendar_block_bootstrap_preserves_paired_station_errors(self):
        weights=block_draw_counts(7,draws=20,block=14)
        np.testing.assert_allclose(weights,np.ones((20,7)))
        rows=[]
        for date in pd.date_range('2024-01-01',periods=7,tz='UTC'):
            for station in ('A','B'):
                for h in (1,2,3):
                    rows.append(dict(issue_utc=date,station_id=station,horizon=h,split='dev',y_mm=1.,
                        ZERO_mean=0.,ZERO_median=0.,ZERO_p1=0.,ZERO_p50=0.,
                        GFS_mean=1.,GFS_median=1.,GFS_p1=1.,GFS_p50=0.))
        result=paired_uncertainty(pd.DataFrame(rows),['ZERO','GFS'],[],draws=20)
        selected=result[result.model.eq('GFS')&result.reference.eq('ZERO')&result.metric.eq('mae')]
        np.testing.assert_allclose(selected.difference,-1)
        np.testing.assert_allclose(selected.ci95_low,-1);np.testing.assert_allclose(selected.ci95_high,-1)


if __name__=='__main__':unittest.main()
