"""Guard against seed/sample inflation and evaluation-tuned decision thresholds."""
import unittest
import numpy as np
import pandas as pd

from src.short_range_ablation import seed_mean,ensemble_thresholds,calendar_block_weights,paired_matrix_bootstrap
from src.short_range_evaluation import score_predictions


def example(seed=42,experiment='E0'):
    dates=pd.date_range('2021-01-01',periods=30,tz='UTC')
    rows=[]
    for lead in [1,2,3]:
        event=np.arange(30)%3==0
        part=pd.DataFrame(dict(issue=dates,lead_day=lead,year=2021,seed=seed,model='tft',
            experiment=experiment,obs=np.where(event,20.,0.),amount=np.where(event,12.,4.)))
        for threshold in [16,50,100]:
            part[f'p{threshold}']=np.where(event,.7,.2) if threshold==16 else .01
            part[f'ref{threshold}']=.3 if threshold==16 else .02
            part[f'tau{threshold}']=.5
        rows.append(part)
    return pd.concat(rows,ignore_index=True)


class AblationIntegrity(unittest.TestCase):
    def test_seed_ensemble_keeps_one_issue_and_rejects_duplicates_or_changed_truth(self):
        frames=[example(seed=s) for s in [42,43,44]]
        frames[1]['amount']+=3
        merged=seed_mean(frames)
        self.assertEqual(len(merged),90)
        np.testing.assert_allclose(merged.amount,example().sort_values(['issue','lead_day']).amount.to_numpy()+1)
        with self.assertRaises(ValueError):seed_mean([frames[0],frames[0],frames[2]])
        frames[2].loc[0,'obs']=999
        with self.assertRaises(ValueError):seed_mean(frames)

    def test_thresholds_ignore_evaluation_truth_and_fallback_for_rare_events(self):
        cal=example();ev=example()
        _,params=ensemble_thresholds(cal,ev,min_events=1)
        ev['obs']=1000
        _,changed=ensemble_thresholds(cal,ev,min_events=1)
        self.assertEqual(params,changed)
        _,rare=ensemble_thresholds(cal,ev,min_events=20)
        self.assertTrue(all(p['fallback'] and p['decision_threshold']==.5 for p in rare))

    def test_calendar_gaps_stay_missing_and_year_strata_stay_separate(self):
        dates=pd.to_datetime(['2021-01-01','2021-01-03','2022-01-01','2022-01-02'],utc=True)
        weights=calendar_block_weights(dates,[2021,2021,2022,2022],7,14)
        np.testing.assert_array_equal(weights,np.ones((7,4)))
        dates=pd.date_range('2021-01-01',periods=30,tz='UTC')
        weights=calendar_block_weights(dates,np.repeat(2021,30),100,7)
        np.testing.assert_array_equal(weights.sum(1),np.full(100,30))

    def test_paired_points_match_independent_score_functions(self):
        a=example();b=example(experiment='E1');b['amount']*=.7;b['p16']*=.8
        frame=pd.concat([a,b],ignore_index=True)
        boot=paired_matrix_bootstrap(frame,repeats=101,block_days=7)
        scores=score_predictions(frame)
        scores=scores[(scores.season=='all')&(scores.threshold_mm==16)]
        for lead in [1,2,3]:
            e0=scores[(scores.experiment=='E0')&(scores.lead_day==lead)].iloc[0]
            e1=scores[(scores.experiment=='E1')&(scores.lead_day==lead)].iloc[0]
            for metric,score in [('RMSE','RMSE'),('BSS16','BSS'),('CSI16','CSI')]:
                point=boot[(boot.lead_day==lead)&(boot.metric==metric)].iloc[0].estimate
                self.assertAlmostEqual(point,float(e1[score]-e0[score]),places=12)
        b.loc[0,'ref16']=.123
        with self.assertRaises(ValueError):paired_matrix_bootstrap(pd.concat([a,b]),repeats=10)


if __name__=='__main__':unittest.main()
