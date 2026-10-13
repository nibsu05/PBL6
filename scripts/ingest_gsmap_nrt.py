"""Nhập binary raw GSMaP NRT v8 đã tải; kiểm tra provenance và giữ ngoài Git."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from src.gsmap_nrt import decode_nrt_binary, features_for_context, interval_from_filename


def from_fetch_manifest(manifest_path: Path):
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not manifest.get('authenticated') or manifest.get('product') != 'GSMaP_NRT' or manifest.get('algorithm_version') != 8:
        raise ValueError('Cần manifest tải raw GSMaP_NRT v8 đã xác thực')
    rows = manifest.get('files', [])
    if len(rows) != 1:
        raise ValueError('Mỗi lần ingest cần manifest đúng một tệp; tải bằng --hours 1')
    row = rows[0]
    path = manifest_path.parent / row['file']
    if path.name != row['file'] or not path.is_file():
        raise ValueError('Tên/đường dẫn tệp không khớp manifest')
    payload = path.read_bytes()
    if len(payload) != row['bytes'] or hashlib.sha256(payload).hexdigest() != row['sha256']:
        raise ValueError('Tệp JAXA bị đổi hoặc tải thiếu so với SHA-256 trong manifest')
    recorded = pd.Timestamp(row['first_recorded_at_utc'])
    if recorded.tzinfo is None:
        raise ValueError('Thời điểm tải phải có UTC offset')
    return path, row['source_uri'], recorded.tz_convert('UTC'), payload


def check_source_uri(uri: str, filename: str):
    parsed = urlparse(uri)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Source URI không được chứa credential/query/fragment')
    if parsed.scheme not in ('ftp', 'https') or parsed.hostname not in ('hokusai.eorc.jaxa.jp', 'sharaku.eorc.jaxa.jp'):
        raise ValueError('Cần nguồn FTP/HTTPS JAXA')
    if '/realtime_ver/v8/' not in parsed.path or not parsed.path.endswith('/' + filename):
        raise ValueError('Source URI phải trỏ đúng tệp raw NRT v8')


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(description=__doc__)
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument('--fetch-manifest', type=Path, help='manifest do fetch_gsmap_nrt.py tạo')
    source.add_argument('--file', type=Path, help='tệp raw NRT tải thủ công')
    ap.add_argument('--source-uri', help='bắt buộc nếu dùng --file; không chứa credential')
    args = ap.parse_args()
    if args.fetch_manifest:
        if args.source_uri:
            ap.error('--source-uri chỉ dùng cùng --file')
        path, uri, recorded, payload = from_fetch_manifest(args.fetch_manifest)
        local_receipt_attested = True
    else:
        if not args.source_uri:
            ap.error('--source-uri bắt buộc nếu dùng --file')
        path, uri = args.file, args.source_uri
        payload = path.read_bytes()
        recorded = None
        local_receipt_attested = False
    check_source_uri(uri, path.name)
    lo, hi = interval_from_filename(path.name)
    ingested = pd.Timestamp(datetime.now(timezone.utc))
    if ingested < hi or (recorded is not None and not hi <= recorded <= ingested):
        raise ValueError('Mốc thời gian quan trắc/tải/ingest không hợp lệ')
    grid = decode_nrt_binary(payload)
    context = pd.read_parquet(ROOT / 'data/processed/dataset_v2/cells.parquet')
    cells = pd.read_parquet(ROOT / 'data/processed/dataset_v2_danang/cells.parquet')
    frame = features_for_context(grid, context, cells.site)
    out = ROOT / 'data/operational/gsmap_nrt_v8' / lo.strftime('%Y%m%dT%H00Z')
    out.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out / 'features_danang.parquet', index=False)
    manifest = dict(
        product='GSMaP_NRT', algorithm_version=8, source_uri=uri,
        interval_start_utc=lo.isoformat(), interval_end_utc=hi.isoformat(),
        first_recorded_at_utc=recorded.isoformat() if recorded is not None else None,
        local_receipt_attested=local_receipt_attested,
        ingested_at_utc=ingested.isoformat(),
        source_publication_time_attested=False,
        sha256=hashlib.sha256(payload).hexdigest(),
        context_cells=len(context), target_cells=len(cells),
        finite_target_rows=int(frame.drop(columns='site').notna().all(axis=1).sum()),
        ready_for_ml=False,
        reason='Cần đủ lịch sử as-of và kiểm định khác biệt MVK/raw lưu trữ → NRT; một tệp không đủ chạy forecast.',
        missing_policy='Giá trị âm/không hữu hạn → NaN; 5x5 dùng đúng context mask dataset v2.',
    )
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(product=manifest['product'], target_cells=len(cells),
                          finite_rows=manifest['finite_target_rows'],
                          interval_start_utc=lo.isoformat(),
                          local_receipt_attested=local_receipt_attested,
                          ready_for_ml=False), indent=2))


if __name__ == '__main__':
    main()
