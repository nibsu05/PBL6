from datetime import date
import json
import unittest
from unittest.mock import Mock

import pandas as pd
from requests import Response

from src.gfs_window_live import parse_live_day
from src.vrain_station_hours import current_modern_aliases, fetch_station_hours, hourly_table


def page(offset, values, sums, cursor=None):
    return dict(ids=["meter-a", "meter-b"], stations=[{"id": "meter-a"}, {"id": "meter-b"}],
                total=2, interval="_1h", offset=offset, next=cursor, sums=sums,
                rows=[{"t": f"{18 + offset}:00 24/11", "v": values}])


def response(payload):
    result = Response()
    result.status_code = 200
    result.headers["Content-Type"] = "application/json"
    result._content = json.dumps(payload).encode("utf-8")
    return result


class PagedVrainTests(unittest.TestCase):
    def test_reads_both_pages_and_preserves_missing_rain(self):
        a = response(page(0, [0., None], [0., 0.], "next-page"))
        b = response(page(1, [1.4, None], [1.4, 0.]))
        session = Mock()
        requests = []

        def get(url, params, **_):
            requests.append((url, dict(params)))
            return [a, b][len(requests)-1]

        session.get.side_effect = get
        day = date(2026, 11, 24).isoformat()
        payload, raw = fetch_station_hours(session, day, "modern", "test-org")
        self.assertIn("/d/kttv/", requests[0][0])
        self.assertNotIn("cursor", requests[0][1])
        self.assertEqual(requests[1][1]["cursor"], "next-page")
        self.assertEqual(raw, [a.content, b.content])
        parsed = parse_live_day(payload, day, {"meter-a": "A", "meter-b": "B"}, ["A", "B"])
        self.assertEqual(int(parsed["valid"].sum()), 2)
        self.assertEqual(float(parsed["raw"][-2, 0]), 0.)
        self.assertAlmostEqual(float(parsed["raw"][-1, 0]), 1.4)
        self.assertFalse(parsed["valid"][:, 1].any())

    def test_rejects_disordered_or_incomplete_pages(self):
        a = page(0, [0., None], [0., 0.], "next-page")
        with self.assertRaises(ValueError):
            hourly_table([a])
        with self.assertRaises(ValueError):
            hourly_table([a, page(0, [1.4, None], [1.4, 0.])])

    def test_html_success_cannot_be_parsed_as_rain(self):
        session = Mock()
        r = response({})
        r.headers["Content-Type"] = "text/html"
        session.get.return_value = r
        with self.assertRaisesRegex(ValueError, "JSON report"):
            fetch_station_hours(session, "2026-11-24", "legacy", "test-org")

    def test_checks_uuid_and_coordinates_before_accepting_new_id(self):
        registry = pd.DataFrame([dict(modern_id="old", modern_uuid="sensor-1", canonical_id="A",
                                      latitude=16.25, longitude=108.25)])
        station = dict(groupId=29, stationID="new", stationUuid="sensor-1", lat=16.25, lng=108.25)
        groups = [{"groupOrgUuid": "test-org", "stats": [station]}]
        self.assertEqual(current_modern_aliases(registry, groups, "test-org"), {"old": "A", "new": "A"})
        station["lat"] = 16.5
        self.assertEqual(current_modern_aliases(registry, groups, "test-org"), {"old": "A"})
        with self.assertRaises(ValueError):
            current_modern_aliases(registry, groups, "other-org")
