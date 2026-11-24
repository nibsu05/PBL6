from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from demo.station_map_alerts import AdminAlerts
from demo.station_map_live import VIETNAM
from demo.station_map_status import SourceMonitor


class AdminNotificationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.state = Path(temporary.name)
        self.path = self.state / 'admin_alerts.sqlite'
        self.inbox = AdminAlerts(self.path)
        self.started = datetime(2026, 11, 24, 9, tzinfo=timezone.utc)

    def probe(self, when, code):
        self.inbox.sources({'sources': {'vrain': {
            'checked_at': when.isoformat(), 'status': 'error', 'http_status': code,
            'channels': {c: {'status': 'error', 'http_status': code} for c in ['modern', 'legacy']},
        }}})

    def test_source_dedup_persistence_and_changed_error(self):
        self.probe(self.started, 404)
        self.probe(self.started, 404)
        first = self.inbox.inbox()['items'][0]
        self.assertEqual(first['occurrences'], 1)
        self.assertIn('HTTP 404', first['detail'])
        self.inbox.mark_read(first['id'])
        self.probe(self.started + timedelta(minutes=3), 404)
        persisted = AdminAlerts(self.path).inbox()
        self.assertEqual(persisted['unread'], 0)
        self.assertEqual(persisted['items'][0]['occurrences'], 2)
        self.probe(self.started + timedelta(minutes=7), 403)
        changed = self.inbox.inbox()
        self.assertEqual(changed['unread'], 1)
        self.assertEqual(len(changed['items']), 1)
        self.assertIn('HTTP 403', changed['items'][0]['detail'])

    def test_incomplete_forecast_and_verification(self):
        self.inbox.job(dict(job='forecast', status='recorded', stations=42, stations_expected=57,
                            finished_utc=self.started.isoformat()))
        self.inbox.job(dict(job='verify', status='waiting', reason='no_due_issue'))
        self.assertEqual(self.inbox.inbox()['unread'], 1)
        self.assertIn('42/57', self.inbox.inbox()['items'][0]['detail'])
        self.inbox.job(dict(job='verify', status='pending',
                            finished_utc=(self.started + timedelta(hours=1)).isoformat()))
        self.assertEqual(self.inbox.inbox()['unread'], 2)
        self.inbox.mark_read()
        self.assertEqual(self.inbox.inbox(summary=True), {'unread': 0})

    def test_missed_schedule_after_publication_and_repeated_view(self):
        daily = self.state / 'daily'
        daily.mkdir()
        (daily / 'schedule.json').write_text(json.dumps(dict(
            task_state='Ready', registered_at=self.started.isoformat(),
        )), encoding='utf-8')
        monitor = SourceMonitor(self.state)
        with patch('demo.station_map_status.recorded_issue', return_value=None), patch('demo.station_map_status.datetime') as clock:
            clock.now.return_value = (self.started + timedelta(hours=2)).astimezone(VIETNAM)
            self.assertEqual(monitor.alert_inbox()['unread'], 0)
            clock.now.return_value = (self.started + timedelta(hours=4)).astimezone(VIETNAM)
            self.assertEqual(monitor.alert_inbox()['unread'], 1)
            second = monitor.alert_inbox()
        self.assertEqual(second['items'][0]['occurrences'], 1)


if __name__ == '__main__':
    unittest.main()
