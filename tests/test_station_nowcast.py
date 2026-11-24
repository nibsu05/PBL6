import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import torch

from demo.station_map_nowcast import nowcast_replay
from scripts.evaluate_station_nowcast import block_sums
from src import station_nowcast as ns


class HourlyWindowTests(unittest.TestCase):
    def setUp(self):
        self.rain = np.arange(50, dtype=np.float32)
        self.code = np.zeros(len(self.rain), dtype=np.int8)
        self.weather = np.ones(len(self.rain), dtype=bool)
        self.origin = 27

    def test_future_nontarget_hours_do_not_affect_history_or_scoring(self):
        self.rain[self.origin + ns.HORIZON + 1] = np.nan
        valid, y = ns.scoring_windows(self.rain, self.code, self.weather, 0)
        self.assertTrue(valid[self.origin])
        np.testing.assert_array_equal(y[self.origin], np.arange(28, 34))

    def test_missing_past_excludes_origin_with_complete_future(self):
        self.rain[self.origin - 4] = np.nan
        valid, y = ns.scoring_windows(self.rain, self.code, self.weather, 0)
        self.assertTrue(np.isfinite(y[self.origin]).all())
        self.assertFalse(valid[self.origin])

    def test_missing_label_or_new_channel_does_not_prevent_issue(self):
        self.rain[self.origin + 2] = np.nan
        self.code[self.origin + 3] = 1
        self.assertTrue(ns.supported_history(self.rain, self.code, 0)[self.origin])
        valid, _ = ns.scoring_windows(self.rain, self.code, self.weather, 0)
        self.assertFalse(valid[self.origin])

    def test_ablation_keeps_same_base_and_omits_older_delta(self):
        x = np.arange(50 * len(ns.ALL), dtype=np.float32).reshape(50, -1)
        train = ns.WindowTensors(x, np.zeros((50, 6), np.float32), np.zeros(50),
                                np.ones(len(ns.ALL), np.float32), np.full(len(ns.ALL), 2, np.float32),
                                torch.device("cpu"))
        idx = torch.tensor([self.origin])
        base, _ = train.window(idx, "E0")
        added, _ = train.window(idx, "E2")
        self.assertEqual(tuple(added.shape), (1, 24, 13))
        torch.testing.assert_close(base[:, :, :-2], added[:, :, :-2])
        self.assertTrue((base[:, :, -2:] == 0).all())
        self.assertTrue((added[:, 0, ns.DELTA_IDX] == -.5).all())
        self.assertTrue((added[:, -1] == torch.from_numpy((x[self.origin] - 1) / 2)).all())


class ReplayAndVerificationTests(unittest.TestCase):
    def test_block_resample_keeps_station_totals_and_wraps(self):
        day = np.array([[1, 10], [2, 20], [3, 30], [4, 40], [5, 50]])
        sampled = np.array([[4, 3], [0, 3]])
        actual = block_sums(day, 3, sampled)
        np.testing.assert_array_equal(actual[0], day[[4, 0, 1, 3, 4]].sum(axis=0))
        np.testing.assert_array_equal(actual[1], day[[0, 1, 2, 3, 4]].sum(axis=0))

    def test_guest_payload_excludes_observations(self):
        bundle = dict(schema_version=1, mode="historical_replay", time_zone=ns.ZONE,
                      unit="mm", lead_hours=list(range(1, 7)), source="Vrain modern",
                      default_method="BiLSTM_R", methods={"BiLSTM_R": "Mưa trạm"}, stations=[],
                      issues=[dict(issue_time="2026-11-10T12:00:00+00:00",
                                   valid_until="2026-11-10T18:00:00+00:00",
                                   by_station={"S": {"forecasts": {"BiLSTM_R": [.2] * 6},
                                                     "observed": [4] * 6}})])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.json"
            path.write_text(json.dumps(bundle), encoding="utf-8")
            guest = nowcast_replay(path, False)["issues"][0]["by_station"]["S"]
            member = nowcast_replay(path, True)["issues"][0]["by_station"]["S"]
        self.assertEqual(set(guest), {"forecasts"})
        self.assertEqual(member["observed"], [4] * 6)


if __name__ == "__main__":
    unittest.main()
