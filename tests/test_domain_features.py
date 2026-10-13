"""Kiểm tra giả thuyết vật lý, thiếu dữ liệu và ranh giới thời gian domain."""
import unittest
from types import SimpleNamespace
import numpy as np
import pandas as pd
from src.domain_features import DomainSampler,physical_indices,RAW_NAMES
from src.dataloader_v2 import product_a

class FakeSampler:
    def __init__(self):
        self.cfg=product_a(('A0','A1','D_RAW'))
        self.past_names=['q850_gkg','u850','v850','sp_hpa']
        self.x_past_names=self.past_names
        self.future_names=['sin_hour']
        self.norm=SimpleNamespace(mean=dict.fromkeys(self.past_names,0.),std=dict.fromkeys(self.past_names,1.))
        self.ds=SimpleNamespace(cells=pd.DataFrame(dict(ne_upslope_m=[100.],lat=[16.])),
                                hours=pd.date_range('2020-12-30',periods=96,freq='h'))
        self.future=1.
    def batch(self,index):
        n=len(index)
        past=np.broadcast_to(np.array([10.,-3.,-3.,1000.],np.float32),(n,24,4)).copy()
        return dict(x_past=past,x_future=np.full((n,6,1),self.future,np.float32),
                    static=np.zeros((n,8),np.float32),y=np.full((n,6),self.future,np.float32),
                    cell=index[:,0],issue=index[:,1])

class DomainFeatureTest(unittest.TestCase):
    def test_ne_flux_changes_with_wind_and_humidity(self):
        q=np.array([[10.,20.,10.]])
        out=physical_indices(q,np.array([[-3.,-3.,3.]]),np.array([[-3.,-3.,3.]]),
                             np.full((1,3),1000.),np.array([100.]),np.array([16.]))
        self.assertAlmostEqual(float(out[0,1,0]),2*float(out[0,0,0]),places=6)
        self.assertEqual(out[0,2,0],0)
        self.assertGreater(out[0,0,1],0)
    def test_below_ground_and_leeward_do_not_create_positive_flux(self):
        out=physical_indices(np.full((2,1),10.),np.full((2,1),-3.),np.full((2,1),-3.),
                             np.array([[800.],[1000.]]),np.array([100.,-100.]),np.array([16.,16.]))
        self.assertEqual(out[0,0,0],0)
        self.assertEqual(out[0,0,3],0)
        self.assertEqual(out[1,0,1],0)
    def test_equal_dimensions_raw_and_domain_and_no_future_dependence(self):
        base=FakeSampler();ix=np.array([[0,30]],dtype=np.int32)
        raw=DomainSampler(base).batch(ix)
        domain=DomainSampler(base,'domain').batch(ix)
        self.assertEqual(raw['x_past'].shape,domain['x_past'].shape)
        np.testing.assert_array_equal(raw['x_past'][...,-4:],0)
        base.future=1000.
        np.testing.assert_array_equal(domain['x_past'],DomainSampler(base,'domain').batch(ix)['x_past'])
    def test_missing_static_is_rejected(self):
        base=FakeSampler();base.ds.cells.loc[0,'ne_upslope_m']=np.nan
        with self.assertRaises(ValueError):DomainSampler(base,'domain').batch(np.array([[0,30]]))
    def test_fit_rejects_labels_crossing_train_year(self):
        base=FakeSampler()
        with self.assertRaises(ValueError):
            DomainSampler.fit_derived(base,np.array([[0,46]]),[2020])
        norm=DomainSampler.fit_derived(base,np.array([[0,30],[0,36]]),[2020])
        self.assertTrue(np.isfinite(norm.transform(np.asarray(norm.mean))).all())
    def test_raw_recipe_contains_ingredients_and_no_future_weather(self):
        cfg=product_a(('A0','A1','D_RAW'))
        self.assertTrue(set(RAW_NAMES)<=set(cfg.feature_lists()['past']))
        self.assertEqual(set(cfg.feature_lists()['future']),{'sin_hour','cos_hour','sin_doy','cos_doy'})

if __name__=='__main__':unittest.main()
