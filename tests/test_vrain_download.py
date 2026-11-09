from pathlib import Path
import gzip
import json
import tempfile
import unittest

from src.vrain_download import Archive, planned_dates
from src.vrain_export_audit import inventory_from_groups


def inventory():
    return inventory_from_groups([{'groupName':'region','stats':[dict(stationID='A',stationUuid='uuid-A',stationName='one',lat=16,lng=108,alt=None)]}])


def payload(hourly=True):
    def row(label,value):return dict(timePoint=label,stations=[dict(id='A',sid='uuid-A',name='one',depth=value)])
    return dict(stats=[row('summary','24' if hourly else '0')]+([row(f'{h:02d}:00 15/01','1') for h in range(24)] if hourly else []))


class DownloadTests(unittest.TestCase):
    def test_scope_and_leap_days(self):
        self.assertEqual(len(planned_dates('2015-01-01','2024-12-31')),3653)
        for first,last in [('2024-12-31','2025-01-01'),('2025-01-01','2025-01-02'),('2024-01-02','2024-01-01')]:
            with self.assertRaises(ValueError):planned_dates(first,last)

    def test_round_trip_and_corruption_requires_fetch(self):
        with tempfile.TemporaryDirectory() as directory:
            archive=Archive(directory,'2023-01-15','2023-01-15')
            raw=json.dumps(payload()).encode();r=archive.store('2023-01-15',raw,inventory(),inventory(),'test',.2)
            self.assertEqual(r['status'],'hourly_rows_present')
            self.assertEqual(gzip.decompress(archive.path('2023-01-15').read_bytes()),raw)
            self.assertTrue(archive.verified('2023-01-15'))
            archive.path('2023-01-15').write_bytes(b'corrupted')
            self.assertFalse(archive.verified('2023-01-15'))
            archive.database.close()

    def test_no_hours_is_not_dry_day_and_not_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            archive=Archive(directory,'2023-01-15','2023-01-15')
            r=archive.store('2023-01-15',json.dumps(payload(False)).encode(),inventory(),inventory(),'test',.1)
            self.assertEqual(r['status'],'no_hourly_data');self.assertFalse(r['training_ready'])
            progress=archive.progress('downloading');self.assertEqual(progress['days_without_hourly_rows'],1)
            self.assertEqual(progress['days_with_hourly_rows'],0)
            archive.database.close()

    def test_invalid_source_preserved_but_flagged(self):
        with tempfile.TemporaryDirectory() as directory:
            archive=Archive(directory,'2023-01-15','2023-01-15')
            data=payload();data['stats'][1]['stations'][0]['depth']='-2'
            raw=json.dumps(data).encode();r=archive.store('2023-01-15',raw,inventory(),inventory(),'test',.1)
            self.assertEqual(r['status'],'structure_flag')
            self.assertEqual(gzip.decompress(archive.path('2023-01-15').read_bytes()),raw)
            archive.database.close()

    def test_login_page_not_saved_as_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            archive=Archive(directory,'2023-01-15','2023-01-15')
            with self.assertRaises(ValueError):archive.store('2023-01-15',b'{"code":"accessDenied"}',inventory(),inventory(),'test',.1)
            self.assertIsNone(archive.record('2023-01-15'))
            self.assertFalse(archive.path('2023-01-15').exists())
            archive.database.close()


if __name__=='__main__':unittest.main()
