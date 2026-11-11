"""Meaningful safeguards for new daily targets, time boundaries and networks."""
import unittest
import numpy as np
import pandas as pd
import torch

from src.daily_gauge_dataset import aggregate_daily, samples_from_daily, feature_groups, TIME
from src.daily_gauge_models import DailyTFT, DailyInformer
from src.short_range_dataset import train_scaler


def fixture(start='2019-01-01', days=35):
    dates = pd.date_range(start, periods=days*24, freq='h', tz='UTC')
    frame = pd.DataFrame({'datetime': dates})
    for i, name in enumerate(feature_groups()['E7']):
        if name not in TIME: frame[name] = np.arange(len(dates), dtype=float) + i
    ends = pd.date_range(dates[0].normalize()+pd.Timedelta(hours=12), periods=days, freq='D')
    labels = pd.DataFrame({'period_end': ends, 'y_cpc_region_mm': np.arange(days, dtype=float)})
    return frame, labels


class DailyDataTests(unittest.TestCase):
    def test_exact_24h_mean_and_disjoint_targets(self):
        h, labels = fixture(); daily = aggregate_daily(h, labels); s = samples_from_daily(daily)
        i = 2; issue = s.dates[i]
        for j in range(7):
            start = issue + pd.Timedelta(days=j-7)
            values = h.loc[(h.datetime >= start) & (h.datetime < start+pd.Timedelta(days=1)), s.features[0]]
            self.assertEqual(len(values), 24)
            self.assertAlmostEqual(float(s.x[i, j, 0]), values.mean())
        for lead in range(3):
            end = issue + pd.Timedelta(days=lead+1)
            self.assertEqual(s.y[i, lead], labels.loc[labels.period_end == end, 'y_cpc_region_mm'].iloc[0])
        self.assertEqual(s.x.shape[1:], (7, 42)); self.assertEqual(s.future.shape[1:], (3, 2))

    def test_future_weather_and_labels_cannot_change_input(self):
        h, labels = fixture(); a = samples_from_daily(aggregate_daily(h, labels)); issue = a.dates[3]
        changed = h.copy(); names = [c for c in a.features if c not in TIME]
        changed.loc[changed.datetime >= issue, names] += 10000
        labels = labels.copy(); labels.loc[labels.period_end > issue, 'y_cpc_region_mm'] += 10000
        b = samples_from_daily(aggregate_daily(changed, labels)); j = b.dates.get_loc(issue)
        np.testing.assert_array_equal(a.x[3], b.x[j]); np.testing.assert_array_equal(a.future[3], b.future[j])
        self.assertTrue((b.y[j] > a.y[3]).all())

    def test_missing_hour_does_not_shrink_daily_denominator(self):
        h, labels = fixture(); name = feature_groups()['E7'][0]
        h.loc[h.datetime == pd.Timestamp('2019-01-12T15:00Z'), name] = np.nan
        daily = aggregate_daily(h, labels)
        self.assertTrue(np.isnan(daily.loc[pd.Timestamp('2019-01-12T12:00Z'), name]))
        s = samples_from_daily(daily)
        for issue in s.dates:
            self.assertFalse(issue-pd.Timedelta(days=7) <= pd.Timestamp('2019-01-12T12:00Z') < issue)

    def test_targets_never_cross_year_and_groups_match(self):
        h, labels = fixture('2019-12-15', 45); s = samples_from_daily(aggregate_daily(h, labels))
        np.testing.assert_array_equal(s.dates.year, (s.dates+pd.Timedelta(days=3)).year)
        self.assertEqual([len(feature_groups()[f'E{i}']) for i in range(8)], [9,21,29,10,41,22,30,42])


class DailyNetworkTests(unittest.TestCase):
    def test_both_daily_networks_forward_gradient_and_reproducible_eval(self):
        torch.set_num_threads(2); torch.manual_seed(42)
        past = torch.randn(4, 7, 9); future = torch.randn(4, 3, 2)
        for cls in [DailyTFT, DailyInformer]:
            kw = dict(input_features=9)
            if cls is DailyInformer: kw['time_indices'] = [7,8]
            model = cls(**kw)
            if cls is DailyInformer: model.set_scaler(train_scaler(past.numpy()))
            amount, logits = model(past, future)
            self.assertEqual(tuple(amount.shape), (4,3)); self.assertEqual(tuple(logits.shape), (4,3,3))
            self.assertTrue(torch.isfinite(amount).all() and (amount > 0).all())
            (amount.mean()+logits.square().mean()).backward()
            self.assertTrue(all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None))
            model.eval()
            with torch.no_grad():
                a, p = model(past, future); b, q = model(past, future)
            torch.testing.assert_close(a,b,rtol=0,atol=0); torch.testing.assert_close(p,q,rtol=0,atol=0)


if __name__ == '__main__': unittest.main()
