"""Unequal station coverage and seen-year interpretation are part of the contract."""
import unittest
import numpy as np
import pandas as pd
from src.gfs_temporal_evaluation import paired_comparisons,amount_error_diagnostics

class TemporalEvaluationTests(unittest.TestCase):
    def sample(self):
        rows=[]
        for day in pd.date_range('2025-01-01',periods=30,tz='UTC'):
            for station in ('A','B'):
                if station=='B' and day.day%2==0:continue
                for h in (1,2,3):
                    rows.append(dict(issue_utc=day,station_id=station,horizon=h,y_mm=5 if station=='A' else 10,evaluation_set='retrospective2025_legacy'))
        f=pd.DataFrame(rows)
        for model in ('LGB_T0','LGB_T1','LGB_T2','LGB_T3','GRU_T3','GRU_T0','GRU_LINEAR23','MOS'):
            for head in ('mean','median'):
                f[model+'_'+head]=f.y_mm+(1 if model in ('LGB_T3','GRU_T3') else 3)
        return f

    def test_pairing_macro_and_multiple_comparison_family(self):
        f=self.sample();p=dict(primary_comparisons=[['LGB_T1','LGB_T0'],['LGB_T2','LGB_T0'],['LGB_T3','LGB_T0'],['GRU_T3','GRU_LINEAR23']],
                              uncertainty=dict(draws=500,block_days=14,seed=1701))
        result=paired_comparisons(f,p);primary=result[result.primary]
        self.assertEqual(len(primary),12)
        self.assertTrue(primary.family_size.eq(12).all())
        x=primary[primary.model.eq('LGB_T3')]
        np.testing.assert_allclose(x.difference,-2)
        self.assertTrue(result.interpretation.str.contains('not untouched').all())
        self.assertTrue((primary.holm_p>=primary.approximate_p).all())

    def test_tail_share_is_squared_error_contribution(self):
        f=self.sample();f.loc[f.station_id.eq('B'),'y_mm']=100
        result=amount_error_diagnostics(f,['LGB_T3'])
        sub=result[result.functional.eq('mean')&result.horizon.eq(1)]
        exclusive=sub[sub.observed_bin.isin(['under1','1_to_10','10_to_50','ge50'])]
        self.assertAlmostEqual(exclusive.fraction_samples.sum(),1)
        self.assertAlmostEqual(exclusive.fraction_squared_error.sum(),1)
        tail=sub[sub.observed_bin.eq('ge50')].iloc[0]
        self.assertGreater(tail.fraction_squared_error,.99)

if __name__=='__main__':unittest.main()
