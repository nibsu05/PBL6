from datetime import datetime, timedelta, timezone
import unittest

from demo.station_map_forecast import combine_forecasts, export_period


def synthetic():
    issued = datetime(2026, 11, 12, 12, tzinfo=timezone.utc)
    daily = {
        "stations": [dict(station_id="A", latitude=16, longitude=108)],
        "snapshots": [dict(
            id="live", issue_utc=issued.isoformat(), label="Saved", mode="prospective",
            gfs_init_utc=issued.replace(hour=0).isoformat(),
            windows=[
                dict(horizon=h, start_utc=(issued + timedelta(days=h - 1)).isoformat(),
                     end_utc=(issued + timedelta(days=h)).isoformat(),
                     points=[dict(station_id="A", predicted_mm=16, gfs_mm=17, mos_mm=11,
                                  probability_ge50=.3, observed_mm=12)])
                for h in range(1, 4)
            ],
        )],
    }
    hourly_station = [dict(id=k, name=k, lat=16, lon=108) for k in ("A", "B")]
    hourly_forecasts = {
        k: dict(forecasts={"LightGBM_R": [1, 2, 3, 4, 5, 6],
                           "BiLSTM_R": [2] * 6, "Persistence": [3] * 6}, observed=[4] * 6)
        for k in ("A", "B")
    }
    hourly = dict(stations=hourly_station,
                  issues=[dict(issue_time=issued.isoformat(),
                               valid_until=(issued + timedelta(hours=6)).isoformat(),
                               by_station=hourly_forecasts)])
    return daily, hourly, issued


class UnifiedMapTests(unittest.TestCase):
    def test_intersection_and_nine_periods_preserve_issue_and_units(self):
        daily, hours, issued = synthetic()
        data = combine_forecasts(daily, hours, True)
        windows = data["snapshots"][0]["windows"]
        self.assertEqual(data["shared_stations"], ["A"])
        self.assertEqual(len(data["stations"]), 2)
        self.assertEqual([w["lead"] for w in windows], [f"h{i}" for i in range(1, 7)] + ["d1", "d2", "d3"])
        self.assertEqual([w["hours"] for w in windows], [1] * 6 + [24] * 3)
        self.assertEqual(windows[0]["start_utc"], windows[6]["start_utc"])
        self.assertEqual(windows[5]["end_utc"], (issued + timedelta(hours=6)).isoformat())
        self.assertEqual(windows[6]["end_utc"], (issued + timedelta(hours=24)).isoformat())
        self.assertEqual(windows[0]["mode"], "historical_replay")
        self.assertEqual(windows[6]["mode"], "prospective")
        self.assertEqual(windows[5]["points"][0]["predicted_mm"], 6)
        self.assertEqual(windows[6]["points"][0]["predicted_mm"], 16)

    def test_same_local_day_at_different_hours_is_not_joined(self):
        daily, hourly, issued = synthetic()
        shifted = issued - timedelta(hours=1)
        hourly["issues"][0].update(issue_time=shifted.isoformat(), valid_until=(shifted + timedelta(hours=6)).isoformat())
        data = combine_forecasts(daily, hourly, False)
        day, hour = data["snapshots"]
        self.assertEqual(day["windows"][0]["mode"], "missing")
        self.assertEqual(hour["windows"][6]["mode"], "missing")
        self.assertEqual(hour["windows"][6]["points"], [])
        with self.assertRaises(ValueError):
            export_period(data, hour["id"], "d1", "common")

    def test_guest_payload_and_member_export(self):
        daily, hourly, _ = synthetic()
        guest = combine_forecasts(daily, hourly, False)
        points = [p for w in guest["snapshots"][0]["windows"] for p in w["points"]]
        self.assertTrue(all("observed_mm" not in p and "mos_mm" not in p for p in points))
        member = combine_forecasts(daily, hourly, True)
        raw, name = export_period(member, "live", "h1", "common")
        self.assertTrue(name.endswith("-h1.csv"))
        text = raw.decode("utf-8-sig")
        self.assertIn("period_hours,station_id,predicted_mm,bilstm_mm", text)
        self.assertIn(",1,A,1,2,3,4", text)
        self.assertNotIn(",1,B,", text)

    def test_misplaced_daily_starts_are_detected(self):
        daily, hourly, issued = synthetic()
        daily["snapshots"][0]["windows"][0]["start_utc"] = (issued + timedelta(hours=6)).isoformat()
        with self.assertRaisesRegex(ValueError, "wrong start or end"):
            combine_forecasts(daily, hourly, False)


if __name__ == "__main__":
    unittest.main()
