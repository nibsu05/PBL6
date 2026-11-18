"""Leakage and capacity checks independent of the real held-out observations."""
import unittest
import numpy as np
import pandas as pd
import torch
from src.gfs_temporal import CATALOG
from src.gfs_temporal_models import arrays,make_projection,replay_gru
from src.gfs_daily_gru import DailyGRU,normalizers

def frame():
    rng=np.random.default_rng(7);n=12
    f=pd.DataFrame({name:rng.uniform(1,8,n*3) for name in CATALOG['T3']})
    f['station_code']=np.repeat(np.arange(n)%3,3);f['station_id']=np.repeat(['A','B','C','A']*3,3)
    f['horizon']=np.tile([1,2,3],n);f['y_mm']=rng.uniform(0,50,n*3)
    for k in range(1,8):f[f'rain_lag_day{k}_mm']=np.repeat(rng.uniform(0,20,n),3)
    return f,np.arange(n)<6

class TemporalModelTests(unittest.TestCase):
    def test_same_parameter_count_control(self):
        f,train=frame();projection=make_projection(f,train)
        a=arrays(f,'T3');b=arrays(f,'LINEAR23',projection)
        self.assertEqual(a['context'].shape,b['context'].shape)
        self.assertEqual(sum(p.numel() for p in DailyGRU(len(a['names']),16,24).parameters()),
                         sum(p.numel() for p in DailyGRU(len(b['names']),16,24).parameters()))
        self.assertEqual(len(a['names']),41)

    def test_projection_and_scaler_are_train_only(self):
        f,train=frame();a=make_projection(f,train);raw=arrays(f,'LINEAR23',a);norm=normalizers(raw,train)
        changed=f.copy();changed.loc[np.repeat(~train,3),CATALOG['T3']]=99999
        changed.loc[np.repeat(~train,3),'y_mm']=100000
        b=make_projection(changed,train);raw2=arrays(changed,'LINEAR23',b);norm2=normalizers(raw2,train)
        for name in a:np.testing.assert_array_equal(a[name],b[name])
        for name in norm:np.testing.assert_array_equal(norm[name],norm2[name])

    def test_future_labels_do_not_change_saved_model_predictions(self):
        f,train=frame();projection=make_projection(f,train)
        raw=arrays(f,'LINEAR23',projection);norm=normalizers(raw,train)
        torch.manual_seed(4);model=DailyGRU(len(raw['names']),16,24)
        artifact=dict(config='LINEAR23',projection=projection,features=raw['names'],normalizers=norm,
                      hidden=16,head=24,state=model.state_dict())
        first=replay_gru(f,artifact,'cpu');changed=f.copy();changed['y_mm']=987654
        second=replay_gru(changed,artifact,'cpu')
        for name in first:np.testing.assert_array_equal(first[name],second[name])

    def test_incomplete_pack_rejected(self):
        f,train=frame()
        with self.assertRaisesRegex(ValueError,'packs'):arrays(f.iloc[:-1],'T0')

    def test_horizons_cannot_join_different_stations(self):
        f,train=frame();f.loc[1,'station_id']='OTHER'
        with self.assertRaisesRegex(ValueError,'Mixed station'):arrays(f,'T0')

if __name__=='__main__':unittest.main()
