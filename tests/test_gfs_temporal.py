"""Behavioral checks for the new temporal contract, separate from frozen code."""
import numpy as np
import unittest
from src.gfs_temporal import temporal_summaries,select_records,CATALOG,RAIN_FEATURES,MET_FEATURES
from src.gfs_station import IndexRecord

def synthetic():
    rain=np.arange(13,dtype=float)[:,None]*np.ones((1,2))*2
    met=np.empty((9,2,5))
    met[:,:,0]=80;met[:,:,1]=283.15;met[:,:,2]=3;met[:,:,3]=-2;met[:,:,4]=40
    return rain,np.zeros(13),met

def test_target_windows_and_weather_feature_order():
    rain,q,met=synthetic();out,flags=temporal_summaries(rain,q,met)
    assert out.shape==(3,2,23)
    np.testing.assert_allclose(out[...,:4],2)
    np.testing.assert_allclose(out[...,4:8],np.broadcast_to([2,.25,.5,.5],(3,2,4)))
    # RH is source channel0 but temperature must be first in feature catalog.
    np.testing.assert_allclose(out[...,8:11],np.broadcast_to([10,0,0],(3,2,3)),atol=1e-5)
    np.testing.assert_allclose(out[...,11:14],np.broadcast_to([80,0,0],(3,2,3)))
    assert not flags.any()
    assert len(CATALOG['T3'])==49 and len(RAIN_FEATURES)==8 and len(MET_FEATURES)==15

def test_timing_information_changes_without_changing_daily_total():
    rain,q,met=synthetic();rain[1:4]=np.array([0,0,8])[:,None]
    out,_=temporal_summaries(rain,q,met)
    np.testing.assert_allclose(out[0,:,0:4],np.broadcast_to([0,0,8,0],(2,4)))
    np.testing.assert_allclose(out[0,:,5],1)
    np.testing.assert_allclose(out[0,:,6],.625)
    np.testing.assert_allclose(out[0,:,7],0)

def test_dry_period_is_finite_without_fake_timing():
    rain,q,met=synthetic();out,_=temporal_summaries(rain*0,q,met)
    assert np.isfinite(out).all() and (out[...,:8]==0).all()

def test_three_instant_samples_are_not_label_dependent():
    rain,q,met=synthetic();met[:3,:,0]=np.array([60,80,90])[:,None]
    out,_=temporal_summaries(rain,q,met)
    np.testing.assert_allclose(out[0,:,11:14],np.broadcast_to([230/3,30,30],(2,3)),atol=1e-5)
    np.testing.assert_allclose(out[1,:,11:14],np.broadcast_to([80,0,0],(2,3)))

def test_nonmonotone_source_is_rejected_not_silently_clipped():
    rain,q,met=synthetic();rain[1]=-4
    with unittest.TestCase().assertRaisesRegex(ValueError,'Nonmonotone'):temporal_summaries(rain,q,met)

def test_only_tiny_packing_rounding_can_be_clipped():
    rain,q,met=synthetic();rain[1]=-.005
    out,flags=temporal_summaries(rain,q,met)
    assert flags[0].all() and np.isfinite(out).all()

def test_no_short_accumulation_or_wrong_level_selected():
    r=[IndexRecord(0,9,'APCP','surface','12-18 hour acc fcst')]
    with unittest.TestCase().assertRaisesRegex(ValueError,'Expected cumulative'):select_records(r,18)
    r=[IndexRecord(0,9,'APCP','surface','0-24 hour acc fcst')]
    assert list(select_records(r,24))==['rain_cumulative']

def test_unknown_shape_rejected():
    rain,q,met=synthetic()
    with unittest.TestCase().assertRaisesRegex(ValueError,'shape'):temporal_summaries(rain,q,met[:3])

def load_tests(loader,tests,pattern):
    return unittest.TestSuite(unittest.FunctionTestCase(value) for name,value in sorted(globals().items()) if name.startswith('test_'))

if __name__=='__main__':unittest.main()
