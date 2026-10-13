"""Watcher chỉ ghi tệp JAXA mới, provenance và không có credential."""
import gzip
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np

from scripts import watch_gsmap_nrt as watch


class FakeFTP:
    def __init__(self, body):
        self.body = body

    def nlst(self):
        return ['gsmap_gauge.20261013.1000.dat.gz',
                'gsmap_nrt.20261013.1000.dat.gz', 'other.txt']

    def retrbinary(self, command, callback):
        if command != 'RETR gsmap_nrt.20261013.1000.dat.gz':
            raise ValueError('wrong product')
        callback(self.body)


class WatcherTest(unittest.TestCase):
    def test_raw_file_manifest_without_credential(self):
        payload = gzip.compress(np.zeros((1200,3600), dtype='<f4').tobytes())
        ftp = FakeFTP(payload)
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            folder = Path(temporary)
            self.assertTrue(folder.resolve().is_relative_to(Path.cwd().resolve()))
            with patch.object(watch, 'PRIVATE', folder):
                names, seen = watch.list_raw_files(ftp)
                self.assertEqual(names, ['gsmap_nrt.20261013.1000.dat.gz'])
                rows = watch.download_new(ftp, names, seen, 'FTP_PLAINTEXT')
                self.assertEqual(len(rows), 1)
                manifest = json.loads(next(folder.glob('*/manifest.json')).read_text(encoding='utf-8'))
                self.assertEqual(manifest['product'], 'GSMaP_NRT')
                self.assertFalse(manifest['credential_persisted'])
                self.assertEqual(manifest['files'][0]['sha256'], rows[0]['sha256'])
                self.assertNotIn('@', manifest['files'][0]['source_uri'])
                self.assertLessEqual(datetime.fromisoformat(rows[0]['first_seen_at_utc']),
                                     datetime.fromisoformat(rows[0]['first_recorded_at_utc']))


if __name__ == '__main__':
    unittest.main()
