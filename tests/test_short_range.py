import io
import unittest

import numpy as np
import pandas as pd
import torch

from src.short_range_dataset import daily_samples, train_scaler, scale_inputs, fit_climatology, predict_climatology
from src.tft_regional import RegionalTFT, daily_joint_loss, daily_tweedie_deviance
from src.short_range_evaluation import (monotone_probabilities, fit_calibration,
    apply_calibration, prediction_frame, paired_pilot_bootstrap)


def hourly_fixture(start='2020-01-01', periods=600):
    dates = pd.date_range(start, periods=periods, freq='h', tz='UTC')
    return pd.DataFrame({'datetime': dates, 'a': np.arange(periods, dtype=float),
                         'b': np.ones(periods), 'y_region_gc_mm': np.ones(periods),
                         'label_permanent': True, 'label_valid_weight_fraction': 1.})


class DailyDatasetTests(unittest.TestCase):
    def test_exact_intervals_and_history(self):
        frame = hourly_fixture()
        frame['y_region_gc_mm'] = np.arange(len(frame))
        data = daily_samples(frame, ['a', 'b'])
        self.assertEqual(data.x.shape[1:], (28, 2))
        self.assertEqual(data.future.shape[1:], (12, 4))
        issue = data.positions[0]
        np.testing.assert_allclose(data.x[0, -1, 0], np.arange(issue-6, issue).mean())
        np.testing.assert_allclose(data.y[0], [np.arange(issue+k, issue+k+24).sum() for k in [0,24,48]])

    def test_future_meteorology_cannot_change_current_inputs(self):
        frame = hourly_fixture()
        before = daily_samples(frame, ['a', 'b'])
        issue = before.positions[0]
        frame.loc[issue:issue+71, ['a', 'b']] = 999999.
        after = daily_samples(frame, ['a', 'b'])
        np.testing.assert_array_equal(before.x[0], after.x[0])
        np.testing.assert_array_equal(before.future[0], after.future[0])

    def test_missing_label_not_zero_filled(self):
        frame = hourly_fixture()
        first = daily_samples(frame, ['a', 'b']).positions[0]
        frame.loc[first+3, 'y_region_gc_mm'] = np.nan
        after = daily_samples(frame, ['a', 'b'])
        self.assertNotIn(first, after.positions)

    def test_coverage_and_permanent_and_history(self):
        for column, value, offset in [('label_valid_weight_fraction', .9, 2),
                                      ('label_permanent', False, 3), ('b', np.nan, -1)]:
            frame = hourly_fixture()
            first = daily_samples(frame, ['a', 'b']).positions[0]
            frame.loc[first+offset, column] = value
            after = daily_samples(frame, ['a', 'b'])
            self.assertNotIn(first, after.positions)

    def test_disallow_cross_year_target(self):
        data = daily_samples(hourly_fixture('2020-12-15', 900), ['a', 'b'])
        for date in data.dates:
            self.assertEqual(date.year, (date + pd.Timedelta(hours=71)).year)

    def test_train_only_scaling_and_unseen_month_climatology(self):
        x = np.arange(2*28*2, dtype=np.float32).reshape(2,28,2)
        scale = train_scaler(x)
        np.testing.assert_allclose(scale_inputs(x, scale).mean((0,1)), 0., atol=1e-6)
        dates = pd.date_range('2020-01-01', periods=10, freq='D', tz='UTC')
        y = np.full((10,3), 24.)
        fitted = fit_climatology(dates, y)
        a, p = predict_climatology(pd.date_range('2021-08-01', periods=2, tz='UTC'), fitted)
        np.testing.assert_array_equal(a, 24.)
        np.testing.assert_array_equal(p[:,:,0], 1.)
        np.testing.assert_array_equal(p[:,:,1:], 0.)


class TFTTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(2)
        torch.manual_seed(42)

    def test_shapes_attention_mask_and_selection(self):
        model = RegionalTFT(11, hidden=16, dropout=0).eval()
        a, logits, details = model(torch.randn(2,28,11), torch.randn(2,12,4), True)
        self.assertEqual(tuple(a.shape), (2,3))
        self.assertEqual(tuple(logits.shape), (2,3,3))
        self.assertTrue((a > 0).all())
        torch.testing.assert_close(details['past_weights'].sum(-1), torch.ones(2,28))
        self.assertEqual(float(details['attention'][:, :, 0, 29:].abs().max()), 0.)

    def test_causal_future_calendar_and_checkpoint_roundtrip(self):
        model = RegionalTFT(11, hidden=16, dropout=0).eval()
        x, c = torch.randn(2,28,11), torch.randn(2,12,4)
        first = model(x, c)
        changed = c.clone(); changed[:,4:] += 100
        second = model(x, changed)
        torch.testing.assert_close(first[0][:,0], second[0][:,0])
        torch.testing.assert_close(first[1][:,0], second[1][:,0])
        stream = io.BytesIO(); torch.save(model.state_dict(), stream); stream.seek(0)
        restored = RegionalTFT(11, hidden=16, dropout=0).eval()
        restored.load_state_dict(torch.load(stream, weights_only=True))
        torch.testing.assert_close(restored(x,c)[0], first[0], rtol=0, atol=0)

    def test_daily_loss_units_thresholds_and_finite_backward(self):
        model = RegionalTFT(11, hidden=16, dropout=0)
        target = torch.tensor([[0.,16.,100.], [1.,50.,150.]])
        amount, logits = model(torch.randn(2,28,11),torch.randn(2,12,4))
        loss = daily_joint_loss(amount, logits, target, torch.ones(3))
        self.assertTrue(torch.isfinite(loss))
        loss.backward()
        self.assertTrue(all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None))
        torch.testing.assert_close(daily_tweedie_deviance(target.clamp_min(.001),target)[target>0],
                                   torch.zeros_like(target)[target>0], atol=1e-4, rtol=0)


class CalibrationTests(unittest.TestCase):
    def test_nested_probability_projection(self):
        p=np.array([[[.2,.8,.6],[.9,.1,.3]]])
        projected=monotone_probabilities(p)
        np.testing.assert_allclose(projected[0,0],np.repeat(1.6/3,3))
        np.testing.assert_allclose(projected[0,1],[.9,.2,.2])
        np.testing.assert_array_equal(p[0,0],[.2,.8,.6])

    def test_rare_calibration_keeps_identity_no_target_leak(self):
        target=np.zeros((10,3)); raw=np.broadcast_to([.3,.2,.1],(10,3,3)).copy()
        params=fit_calibration(target,raw)
        self.assertTrue(all(not r['platt_fitted'] for r in params))
        np.testing.assert_allclose(apply_calibration(raw,params),raw)
        self.assertTrue(all(r['decision_threshold']==.5 for r in params))

    def test_paired_bootstrap_resamples_reference_with_case(self):
        dates=pd.date_range('2021-01-01',periods=28,freq='D',tz='UTC')
        obs=np.tile(np.array([0.,20.,0.,50.]*7)[:,None],(1,3))
        ref=np.broadcast_to(np.array([.2,.1,.05]),(28,3,3)).copy()
        p0=np.full((28,3,3),.1); p7=p0.copy(); p7[:,:,0]=(obs>=16)*.8+.1
        a=prediction_frame(dates,obs,np.zeros_like(obs),p0,ref,[],'test','E0',2021,42)
        b=prediction_frame(dates,obs,obs,p7,ref,[],'test','E7',2021,42)
        ci=paired_pilot_bootstrap(pd.concat([a,b]),'test',repeats=40)
        rmse=ci[ci.metric=='RMSE']; bss=ci[ci.metric=='BSS16']
        self.assertTrue((rmse.ci_high<0).all())
        self.assertTrue((bss.ci_low>0).all())
        self.assertTrue((ci.n==28).all())


if __name__ == '__main__':
    unittest.main()
