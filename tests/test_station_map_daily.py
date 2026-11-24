import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from demo.station_map_live import recent_snapshots
from demo.station_map_status import compare_window, forecast_payload
from scripts.run_station_map_daily import publication_day, source_block


class MapPublicationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.live = self.root / 'live'
        self.issue = datetime(2026, 11, 24, 12, tzinfo=timezone.utc)
        self.folder = self.live / 'issuances' / '20261124T120000Z'
        self.folder.mkdir(parents=True)
        self.freeze = hashlib.sha256(b'frozen model').hexdigest()
        (self.root / 'model_freeze.json').write_bytes(b'frozen model')
        self.data = pd.DataFrame([
            dict(station_id='ST001', horizon=h, issue_utc=self.issue,
                 target_start_utc=self.issue + timedelta(days=h-1),
                 target_end_utc=self.issue + timedelta(days=h), gfs_init_utc=self.issue.replace(hour=0),
                 B_mean=12.0, GFS_mean=21., MOS_LONG_mean=15., B_p50=.3, B_p1=.9)
            for h in (1, 2, 3)
        ])
        self.forecast_file = self.folder / 'predictions_private.parquet'
        self.data.to_parquet(self.forecast_file, index=False)
        self.manifest = dict(status='recorded_before_issue', issue_utc=self.issue.isoformat(),
                             recorded_utc=(self.issue - timedelta(minutes=5)).isoformat(),
                             truth_due_utc=(self.issue + timedelta(days=3)).isoformat(),
                             selected_case='B', stations=1, rows=3, station_count=1,
                             model_freeze_sha256=self.freeze,
                             forecast_sha256=hashlib.sha256(self.forecast_file.read_bytes()).hexdigest())
        self.write_manifest()

    def write_manifest(self):
        (self.folder / 'issuance.json').write_text(json.dumps(self.manifest), encoding='utf-8')

    def published(self, at):
        return recent_snapshots({'ST001'}, {1: .35, 2: .35, 3: .20}, now=at, live=self.live)

    def test_prospective_visibility_and_integrity(self):
        self.assertEqual(self.published(self.issue - timedelta(seconds=1)), [])
        saved = self.published(self.issue)
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]['mode'], 'prospective')
        self.assertEqual(len(saved[0]['windows']), 3)
        self.assertIsNone(saved[0]['windows'][0]['points'][0]['observed_mm'])
        self.manifest['recorded_utc'] = self.issue.isoformat()
        self.write_manifest()
        self.assertEqual(self.published(self.issue + timedelta(hours=1)), [])
        self.manifest['recorded_utc'] = (self.issue - timedelta(minutes=5)).isoformat()
        self.manifest['forecast_sha256'] = 'bad checksum'
        self.write_manifest()
        self.assertEqual(self.published(self.issue + timedelta(hours=1)), [])

    def test_truth_enters_only_after_verification_and_login(self):
        verified = self.issue + timedelta(hours=73, minutes=5)
        truth = self.live / 'verification' / self.folder.name
        truth.mkdir(parents=True)
        self.data.assign(y_mm=[54., 17., 1.]).to_parquet(truth / 'verified_private.parquet', index=False)
        report = dict(status='truth_observed', forecast_rows=3, valid_common_rows=3,
                      forecast_sha256=self.manifest['forecast_sha256'], labels_after_forecast=True,
                      issue_utc=self.issue.isoformat(),
                      verified_utc=(self.issue + timedelta(hours=72)).isoformat())
        (truth / 'verification.json').write_text(json.dumps(report), encoding='utf-8')
        self.assertFalse(self.published(verified)[0]['has_truth'])
        report['verified_utc'] = verified.isoformat()
        (truth / 'verification.json').write_text(json.dumps(report), encoding='utf-8')
        snapshot = self.published(verified)[0]
        self.assertTrue(snapshot['has_truth'])
        summary = compare_window(snapshot['windows'][0])
        self.assertEqual(summary['misses'], 1)
        self.assertEqual(summary['largest_errors'][0]['error'], -42.)
        guest = forecast_payload(dict(snapshots=[snapshot]), signed_in=False)
        point = guest['snapshots'][0]['windows'][0]['points'][0]
        self.assertNotIn('observed_mm', point)
        self.assertNotIn('mos_mm', point)

    def test_source_deadline_and_missing_hour(self):
        at = publication_day(self.issue)
        cutoff = at - timedelta(hours=1)
        vrain = dict(channels={'modern': {'http_status': 404}, 'legacy': {'http_status': 200}})
        sources = dict(vrain=vrain, gfs={'status': 'ok'})
        self.assertEqual(source_block(sources, cutoff), 'vrain_unavailable')
        vrain['channels']['modern']['http_status'] = 200
        vrain['last_hour'] = (cutoff - timedelta(hours=1)).isoformat()
        self.assertEqual(source_block(sources, cutoff), 'vrain_18h_pending')
        vrain['last_hour'] = cutoff.isoformat()
        self.assertIsNone(source_block(sources, cutoff))


if __name__ == '__main__':
    unittest.main()
