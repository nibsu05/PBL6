"""Cổng dữ liệu NRT không cho AI nhìn tệp đến sau giờ phát hành."""
import unittest

import pandas as pd

from scripts.audit_jaxa_nrt_history import coverage, required_intervals


class NRTHistoryGateTest(unittest.TestCase):
    def test_lagged_window_and_late_file(self):
        issue = pd.Timestamp('2026-10-13T15:00:00Z')
        hours = required_intervals(issue)
        self.assertEqual(len(hours), 24)
        self.assertEqual(hours[0], pd.Timestamp('2026-10-12T11:00:00Z'))
        self.assertEqual(hours[-1], pd.Timestamp('2026-10-13T10:00:00Z'))
        rows = {hour.isoformat(): {'recorded_at': issue - pd.Timedelta(minutes=1)} for hour in hours}
        rows[hours[-1].isoformat()]['recorded_at'] = issue + pd.Timedelta(minutes=2)
        _, _, present, received = coverage(rows, issue)
        self.assertEqual((present, received), (24, 23))
        issue_next = issue + pd.Timedelta(hours=2)
        later_hours = required_intervals(issue_next, lag_h=5)
        self.assertEqual(later_hours[0], pd.Timestamp('2026-10-12T12:00:00Z'))
        self.assertEqual(later_hours[-1], pd.Timestamp('2026-10-13T11:00:00Z'))
        rows[later_hours[-1].isoformat()] = {'recorded_at': issue_next - pd.Timedelta(hours=1)}
        _, _, present_later, received_later = coverage(rows, issue_next, latency_h=5)
        self.assertEqual((present_later, received_later), (24, 24))
        rows.pop(hours[0].isoformat())
        _, _, present, received = coverage(rows, issue)
        self.assertEqual((present, received), (23, 22))


if __name__ == '__main__':
    unittest.main()
