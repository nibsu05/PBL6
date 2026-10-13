"""Provenance của file quan trắc JAXA trước khi thành đầu vào ML."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.ingest_gsmap_nrt import check_source_uri, from_fetch_manifest


class IngestProvenanceTest(unittest.TestCase):
    def test_fetch_manifest_rejects_changed_payload(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            folder = Path(temporary)
            self.assertTrue(folder.resolve().is_relative_to(Path.cwd().resolve()))
            name = 'gsmap_nrt.20261013.1000.dat.gz'
            payload = folder / name
            payload.write_bytes(b'official-bytes')
            manifest = folder / 'manifest.json'
            info = {
                'authenticated': True,
                'product': 'GSMaP_NRT',
                'algorithm_version': 8,
                'files': [{
                    'file': name, 'bytes': payload.stat().st_size,
                    'sha256': hashlib.sha256(payload.read_bytes()).hexdigest(),
                    'source_uri': 'ftp://hokusai.eorc.jaxa.jp/realtime_ver/v8/latest/' + name,
                    'first_recorded_at_utc': '2026-10-13T15:02:14+00:00',
                }],
            }
            manifest.write_text(json.dumps(info), encoding='utf-8')
            actual, uri, recorded, body = from_fetch_manifest(manifest)
            self.assertEqual(actual, payload)
            self.assertEqual(body, b'official-bytes')
            self.assertEqual(recorded.hour, 15)
            check_source_uri(uri, name)
            payload.write_bytes(b'changed-bytes')
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                from_fetch_manifest(manifest)

    def test_rejects_credential_and_wrong_product_uri(self):
        name = 'gsmap_nrt.20261013.1000.dat.gz'
        with self.assertRaises(ValueError):
            check_source_uri('ftp://someone@hokusai.eorc.jaxa.jp/realtime_ver/v8/latest/' + name, name)
        with self.assertRaises(ValueError):
            check_source_uri('ftp://hokusai.eorc.jaxa.jp/realtime_ver/v8/latest/gsmap_gauge.20261013.1000.dat.gz', name)


if __name__ == '__main__':
    unittest.main()
