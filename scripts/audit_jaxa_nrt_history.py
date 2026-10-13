"""Kiểm tra cửa sổ GSMaP NRT raw 24 giờ, trễ 4 giờ, trước giờ phát hành.

Chỉ dùng manifest do fetch_gsmap_nrt.py tạo; không đọc/lưu credential.
Ghi đặc trưng 93 ô ngoài Git và báo cáo trạng thái tổng hợp công khai.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.gsmap_nrt import decode_nrt_binary, features_for_context, interval_from_filename
from scripts.ingest_gsmap_nrt import check_source_uri

INPUT_ROOT = ROOT / 'data/operational/jaxa_downloads'
OUTPUT_ROOT = ROOT / 'data/operational/gsmap_nrt_v8_history'
REPORT = ROOT / 'reports/followup_danang/nrt_history_readiness.json'
WINDOW_H = 24
LAG_H = 4


def required_intervals(issue: pd.Timestamp, window_h=WINDOW_H, lag_h=LAG_H):
    """Mưa của [issue-W-L, issue-L); giờ mới nhất kết thúc issue-L."""
    issue = pd.Timestamp(issue)
    if issue.tzinfo is None:
        raise ValueError('Issue phải kèm UTC offset')
    issue = issue.tz_convert('UTC')
    return pd.date_range(issue - pd.Timedelta(hours=window_h + lag_h),
                         periods=window_h, freq='h')


def records():
    rows = {}
    conflicts = []
    for manifest_path in sorted(INPUT_ROOT.glob('*/manifest.json')):
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest.get('product') != 'GSMaP_NRT' or manifest.get('algorithm_version') != 8:
            continue
        if not manifest.get('authenticated') or manifest.get('credential_persisted') is not False:
            raise ValueError('Manifest raw NRT không xác thực hoặc credential không đúng hợp đồng')
        for item in manifest.get('files', []):
            check_source_uri(item['source_uri'], item['file'])
            lo, hi = interval_from_filename(item['file'])
            path = manifest_path.parent / item['file']
            if path.name != item['file'] or not path.is_file():
                raise ValueError('Thiếu tệp hoặc tên không khớp manifest')
            body = path.read_bytes()
            sha = hashlib.sha256(body).hexdigest()
            if len(body) != item['bytes'] or sha != item['sha256']:
                raise ValueError('Tệp NRT sai SHA-256/size')
            recorded = pd.Timestamp(item['first_recorded_at_utc']).tz_convert('UTC')
            if recorded < hi:
                raise ValueError('Thời điểm tải sớm hơn cuối khoảng mưa')
            key = lo.isoformat()
            value = dict(interval_start=lo, recorded_at=recorded, sha256=sha, path=path)
            if key in rows:
                if rows[key]['sha256'] != sha:
                    conflicts.append(key)
                if recorded < rows[key]['recorded_at']:
                    rows[key] = value
            else:
                rows[key] = value
    return rows, sorted(set(conflicts))


def coverage(rows, issue, latency_h=LAG_H):
    required = required_intervals(issue, lag_h=latency_h)
    present = [rows.get(t.isoformat()) for t in required]
    present_count = sum(item is not None for item in present)
    received_count = sum(item is not None and item['recorded_at'] <= issue for item in present)
    return required, present, present_count, received_count


def audit(issue=None, latency_h=LAG_H):
    if not 0 <= latency_h <= 24:
        raise ValueError('latency_h phải 0–24')
    rows, conflicts = records()
    if not rows:
        raise ValueError('Chưa có manifest/tệp raw NRT đã tải')
    latest = max(pd.Timestamp(x) for x in rows)
    issue = pd.Timestamp(issue) if issue is not None else latest + pd.Timedelta(hours=latency_h + 1)
    if issue.tzinfo is None:
        raise ValueError('Giờ issue phải có UTC offset')
    issue = issue.tz_convert('UTC')
    required, present, present_count, received_count = coverage(rows, issue, latency_h=latency_h)
    context = pd.read_parquet(ROOT / 'data/processed/dataset_v2/cells.parquet')
    target = pd.read_parquet(ROOT / 'data/processed/dataset_v2_danang/cells.parquet')
    series = []
    finite_counts = []
    for t, item in zip(required, present):
        if item is None:
            continue
        grid = decode_nrt_binary(item['path'].read_bytes())
        frame = features_for_context(grid, context, target.site)
        count = int(frame.drop(columns='site').notna().all(axis=1).sum())
        finite_counts.append(count)
        frame.insert(0, 'interval_start_utc', t.isoformat())
        frame['first_recorded_at_utc'] = item['recorded_at'].isoformat()
        series.append(frame)
    if series:
        out = OUTPUT_ROOT / (issue.strftime('%Y%m%dT%H00Z') + '_lag' + str(latency_h))
        out.mkdir(parents=True, exist_ok=True)
        pd.concat(series, ignore_index=True).to_parquet(out / 'features_danang.parquet', index=False)
    audited = pd.Timestamp(datetime.now(timezone.utc))
    report = dict(audited_at_utc=audited.isoformat(),
                  candidate_issue_utc=issue.isoformat(), candidate_issue_in_future=bool(issue > audited),
                  actual_forecast_issued=False,
                  required_first_interval_utc=required[0].isoformat(),
                  required_last_interval_utc=required[-1].isoformat(),
                  required_hours=WINDOW_H, observation_lag_hours=latency_h,
                  available_unique_raw_hours=len(rows), required_files_present=present_count,
                  required_files_received_by_issue=received_count,
                  target_cells=len(target), min_finite_target_cells=min(finite_counts) if finite_counts else 0,
                  conflicting_versions=len(conflicts),
                  nrt_history_contract_passed=(present_count==WINDOW_H and received_count==WINDOW_H
                                               and not conflicts and len(finite_counts)==WINDOW_H
                                               and min(finite_counts)==len(target)),
                  ready_for_ml=False,
                  receipt_provenance='Giờ máy nhận file; tải backlog không chứng thực giờ JAXA công bố',
                  reason='Cần parity NRT→train, nguồn khí tượng forecast as-of và đánh giá T-OPS trước AI live.')
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--issue', help='giờ phát hành UTC ISO8601; mặc định giờ đầu đủ trễ của tệp mới nhất')
    parser.add_argument('--latency-h', type=int, default=4, help='độ trễ NRT theo giờ, mặc định 4')
    args = parser.parse_args()
    print(json.dumps(audit(args.issue, args.latency_h), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
