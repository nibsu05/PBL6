"""Synthetic end-to-end checkpoint wiring; never creates public model scores."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.dummy import DummyRegressor
from sklearn.preprocessing import StandardScaler
from src.gfs_temporal import CATALOG,SEEDS
from src.gfs_temporal_models import arrays,make_projection
from src.gfs_daily import Platt
from src.gfs_daily_gru import DailyGRU,normalizers
from src.gfs_daily_models import fit_tree,ConstantBinary
from scripts import score_gfs_temporal as scorer
from tests.test_gfs_temporal_models import frame

class TemporalIntegrationTests(unittest.TestCase):
    def test_all_twelve_models_replay_with_nested_probabilities_without_labels(self):
        f,train=frame();f['issue_utc']=np.repeat(pd.date_range('2023-01-01',periods=12,tz='UTC'),3)
        trainlong=np.repeat(train,3);y=f.y_mm.to_numpy();cal=~trainlong
        pairs=[(Platt().fit(np.full(cal.sum(),.5),y[cal]>=1),
                Platt().fit(np.full((cal&(y>=1)).sum(),.2),y[cal&(y>=1)]>=50)) for _ in SEEDS]
        candidate=dict(num_leaves=3,max_depth=2,min_child_samples=2,reg_lambda=1.)
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);(base/'models').mkdir();old=base/'old';(old/'models').mkdir(parents=True)
            for config,names in CATALOG.items():
                label='LGB_'+config
                for h in (1,2,3):
                    sub=f[f.horizon.eq(h)].reset_index(drop=True)
                    for seed in SEEDS:
                        models={head:fit_tree(sub,names,train,None,head,candidate,seed,trees=3)
                                for head in ('mean','median','wet','conditional')}
                        joblib.dump(dict(features=names,models=models),base/'models'/f'{label}_d{h}_seed{seed}.joblib')
                    joblib.dump(pairs,base/'models'/f'{label}_d{h}_calibrators.joblib')
            for config in ('T0','T3','LINEAR23'):
                projection=make_projection(f,train) if config=='LINEAR23' else None
                raw=arrays(f,config,projection);norm=normalizers(raw,train)
                for seed in SEEDS:
                    torch.manual_seed(seed);net=DailyGRU(len(raw['names']),16,24)
                    a=dict(config=config,projection=projection,normalizers=norm,features=raw['names'],
                           hidden=16,head=24,state=net.state_dict())
                    torch.save(a,base/'models'/f'GRU_{config}_seed{seed}.pt')
                for h in (1,2,3):joblib.dump(pairs,base/'models'/f'GRU_{config}_d{h}_calibrators.joblib')
            names=['gfs_rain_mm','sin_doy','cos_doy'];scale=StandardScaler().fit(f.loc[trainlong,names]);x=scale.transform(f[names])
            reg=DummyRegressor().fit(x[trainlong],y[trainlong])
            for h in (1,2,3):
                joblib.dump(dict(scaler=scale,features=names,mean=reg,median=reg,
                    classifiers=[ConstantBinary(y[trainlong]>=1),ConstantBinary(y[trainlong]>=50)],calibrators=[pairs[0]]),old/'models'/f'MOS_d{h}.joblib')
            def climate(rows):return pd.DataFrame({name:np.full(len(rows),value) for name,value in [('mean',2.),('median',0.),('p1',.3),('p50',.02)]},index=rows.index)
            with patch.object(scorer,'BASE',base),patch.object(scorer,'OLD',old),patch.object(scorer,'climatology',climate):
                first,seeds=scorer.predict_all(f);changed=f.copy();changed['y_mm']=1234567
                second,_=scorer.predict_all(changed)
            self.assertEqual(len(seeds),7)
            for model in scorer.MODELS:
                names=[model+'_'+h for h in ('mean','median','p1','p50')]
                np.testing.assert_array_equal(first[names],second[names])
                self.assertTrue(np.isfinite(first[names]).all().all())
                self.assertTrue(first[model+'_p50'].le(first[model+'_p1']).all())

if __name__=='__main__':unittest.main()
