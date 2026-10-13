"""Chốt phép căn giờ và hợp đồng nguồn của pilot ECMWF."""
import unittest

import pandas as pd

from scripts.pilot_ecmwf_single_runs import forecast_six_hours, validate_response


class ECMWFPilotTest(unittest.TestCase):
    def setUp(self):
        self.run = pd.Timestamp('2024-10-01T00:00:00Z')
        self.payload = dict(latitude=16.05, longitude=108.15, utc_offset_seconds=0,
                            hourly_units={'precipitation': 'mm'},
                            hourly=dict(time=[t.strftime('%Y-%m-%dT%H:%M')
                                              for t in pd.date_range(self.run, periods=48, freq='h')],
                                        precipitation=list(range(48))))
        self.cells = pd.DataFrame([dict(lat=16.05, lon=108.15)], index=['c16.05_108.15'])

    def test_precipitation_is_previous_hour_sum(self):
        issue = self.run + pd.Timedelta(hours=12)
        self.assertEqual(forecast_six_hours(self.payload, issue).tolist(), [13, 14, 15, 16, 17, 18])
        self.assertEqual(len(validate_response([self.payload], self.run, self.cells)), 1)

    def test_rejects_wrong_unit_and_order(self):
        self.payload['hourly_units']['precipitation'] = 'inch'
        with self.assertRaises(ValueError):
            validate_response([self.payload], self.run, self.cells)
        self.payload['hourly_units']['precipitation'] = 'mm'
        self.payload['latitude'] = 18.0
        with self.assertRaises(ValueError):
            validate_response([self.payload], self.run, self.cells)


if __name__ == '__main__':
    unittest.main()
