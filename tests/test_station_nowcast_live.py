from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd

from demo.station_map_forecast import combine_forecasts
from demo.station_map_nowcast import hourly_status, live_hourly
from scripts import run_station_nowcast_hourly as worker
from src.gfs_window import sha, write_json


ORIGIN = datetime(2026, 11, 24, 16, tzinfo=timezone.utc)


def saved_issue(state):
    folder = state / "issuances" / worker.issue_id(ORIGIN)
    end = ORIGIN + timedelta(hours=6)
    forecast = {
        sid: {"forecasts": {name: [float(i) for i in range(1, 7)] for name in worker.MODELS}}
        for sid in ("A", "B")
    }
    payload = dict(schema_version=1, issue_time=ORIGIN.isoformat(), valid_until=end.isoformat(),
                   stations=[dict(id=sid, name=sid, lat=16, lon=108) for sid in forecast],
                   by_station=forecast)
    file = folder / "forecast_private.json"
    write_json(file, payload)
    write_json(folder / "issuance.json", dict(schema_version=1, status="recorded", stations=2, stations_expected=3,
               issue_utc=ORIGIN.isoformat(), truth_due_utc=end.isoformat(),
               received_utc=(ORIGIN + timedelta(minutes=5)).isoformat(),
               recorded_utc=(ORIGIN + timedelta(minutes=6)).isoformat(), forecast_sha256=sha(file)))
    return folder


class HourlyTrialTests(unittest.TestCase):
    def test_report_day_rollover_and_time_limit(self):
        self.assertEqual(worker.report_day(pd.Timestamp("2026-12-31T19:00:00+07:00")), "2026-12-31")
        self.assertEqual(worker.report_day(pd.Timestamp("2026-12-31T20:00:00+07:00")), "2027-01-01")
        received = ORIGIN + timedelta(minutes=2)
        stored = ORIGIN + timedelta(minutes=14)
        self.assertTrue(worker.eligible_for_release(ORIGIN, [received], stored))
        self.assertFalse(worker.eligible_for_release(ORIGIN, [received], ORIGIN + timedelta(minutes=15)))
        self.assertFalse(worker.eligible_for_release(ORIGIN, [stored], received))

    def test_input_requires_a_complete_hourly_history_per_station(self):
        clocks = pd.date_range(end=ORIGIN, periods=24, freq="h")
        history = pd.DataFrame({"A": [0.] * 24, "B": [0.] * 23 + [np.nan]}, index=clocks)
        scaler = dict(train_stations=["A", "B"], roster=["B", "A"])
        stations, values, codes = worker.model_inputs(history, scaler)
        self.assertEqual(stations, ["A"])
        self.assertEqual(values[0].shape[0], 24)
        self.assertTrue(np.all(codes == 1))
        shifted = history.copy()
        shifted.index = clocks[:-1].append(clocks[-1:] + pd.Timedelta(hours=1))
        with self.assertRaises(ValueError):
            worker.model_inputs(shifted, scaler)

    def test_pilot_visibility_and_later_verification(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp)
            folder = saved_issue(state)
            source = Mock()
            source.folder = state / "attempts/test"
            start = ORIGIN + timedelta(hours=1)
            clocks = pd.date_range(start=start, periods=6, freq="h")
            truth = pd.DataFrame({"A": [1.] * 6, "B": [None] + [2.] * 5}, index=clocks)
            source.matrix.return_value = (truth, [])
            early = ORIGIN + timedelta(hours=5, minutes=55)
            self.assertEqual(worker.verify_due(state, source, early), 0)
            source.matrix.assert_not_called()
            self.assertFalse(live_hourly(state, False, early)["issues"])
            self.assertEqual(hourly_status(state, early)["last_recorded"]["stations"], 2)
            due = ORIGIN + timedelta(hours=6, minutes=5)
            with patch.object(worker, "utcnow", return_value=due):
                self.assertEqual(worker.verify_due(state, source, due), 1)
                self.assertEqual(worker.verify_due(state, source, due), 0)
            recorded = worker.read_optional(folder / "verification_private.json")
            self.assertEqual(recorded["observed_cells"], 11)
            self.assertEqual(len(recorded["metrics"]), 36)
            self.assertEqual(hourly_status(state, due)["last_verified"]["observed_cells"], 11)
            write_json(state / "display.json", {"enabled": True})
            guest = live_hourly(state, False, due)
            member = live_hourly(state, True, due)
            self.assertNotIn("observed", guest["issues"][0]["by_station"]["A"])
            self.assertIsNone(member["issues"][0]["by_station"]["B"]["observed"][0])
            combined = combine_forecasts({"stations": [], "snapshots": []}, member, True)
            window = combined["snapshots"][0]["windows"][0]
            self.assertEqual(window["mode"], "prospective")
            self.assertEqual(window["recorded_utc"], (ORIGIN + timedelta(minutes=6)).isoformat())
            (folder / "forecast_private.json").write_text("{}", encoding="utf-8")
            self.assertFalse(live_hourly(state, False, due)["issues"])


if __name__ == "__main__":
    unittest.main()
