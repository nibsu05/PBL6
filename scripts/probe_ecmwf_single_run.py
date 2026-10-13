"""Thử một run ECMWF lịch sử; lưu phản hồi riêng tư và chỉ công khai metadata."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
URL = 'https://single-runs-api.open-meteo.com/v1/forecast'


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', default='2024-10-01T00:00', help='giờ khởi tạo UTC YYYY-MM-DDTHH:MM')
    parser.add_argument('--lat', type=float, default=16.05)
    parser.add_argument('--lon', type=float, default=108.15)
    args = parser.parse_args()
    run = pd.Timestamp(args.run)
    if run.tzinfo is not None:
        run = run.tz_convert('UTC').tz_localize(None)
    if run.minute or run.second or run.hour not in (0, 6, 12, 18):
        parser.error('run phải là 00/06/12/18 UTC, phút 00')
    params = dict(latitude=args.lat, longitude=args.lon, models='ecmwf_ifs',
                  hourly='precipitation', run=run.strftime('%Y-%m-%dT%H:%M'),
                  forecast_days=2, timezone='UTC')
    response = requests.get(URL, params=params, timeout=25)
    response.raise_for_status()
    payload = response.content
    body = response.json()
    hourly = body['hourly']
    times = pd.to_datetime(hourly['time'], utc=True)
    values = pd.to_numeric(pd.Series(hourly['precipitation']), errors='coerce')
    if len(times) != 48 or len(values) != 48 or times[0] != run.tz_localize('UTC'):
        raise ValueError('Single Runs không trả đủ 48 giờ từ run yêu cầu')
    if body.get('utc_offset_seconds') != 0 or body['hourly_units']['precipitation'] != 'mm':
        raise ValueError('UTC/đơn vị ECMWF không như hợp đồng')
    stamp = run.strftime('%Y%m%dT%H%MZ')
    private = ROOT / 'data/operational/ecmwf_single_run_probe' / stamp
    private.mkdir(parents=True, exist_ok=True)
    (private / 'response.json').write_bytes(payload)
    meta = dict(request_url=response.url, retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                sha256=hashlib.sha256(payload).hexdigest(), requested_lat=args.lat,
                requested_lon=args.lon, returned_lat=body['latitude'], returned_lon=body['longitude'],
                run_init_utc=run.tz_localize('UTC').isoformat(), hours=len(times),
                finite_precip_hours=int(values.notna().sum()), unit='mm',
                run_initialisation_known=True, actual_available_at_known=False,
                grid_cells_collected=1, evaluation_year_2024_collected=False,
                ready_for_tops_comparison=False)
    (private / 'manifest.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    public = {key: meta[key] for key in ('retrieved_at_utc', 'sha256', 'requested_lat',
              'requested_lon', 'run_init_utc', 'hours', 'finite_precip_hours', 'unit',
              'run_initialisation_known', 'actual_available_at_known',
              'grid_cells_collected', 'evaluation_year_2024_collected',
              'ready_for_tops_comparison')}
    public['source_documentation'] = 'https://open-meteo.com/en/docs/single-runs-api'
    report = ROOT / 'reports/research_rainfall/ecmwf_single_run_probe.json'
    report.write_text(json.dumps(public, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(public, indent=2))


if __name__ == '__main__':
    main()
