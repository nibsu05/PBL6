"""Pilot ECMWF Single Runs 01–14/10/2024 trên đúng 30 ô domain screen.

Run chính khởi tạo trước giờ phát hành 12 h (giả định bảo thủ, chưa có
thời điểm công bố lịch sử). Run trước 6 h chỉ là phân tích độ nhạy.
Lưu phản hồi/dự báo từng ô ngoài Git; báo cáo công khai chỉ số tổng hợp.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.dataloader_v2 import DatasetV2
from src.verification import continuous_scores, contingency_scores

URL = 'https://single-runs-api.open-meteo.com/v1/forecast'
START = pd.Timestamp('2024-10-01T00:00:00Z')
STOP = pd.Timestamp('2024-10-15T00:00:00Z')
ISSUES = pd.date_range(START, STOP, freq='6h', inclusive='left')
PRIVATE = ROOT / 'data/operational/ecmwf_pilot_20241001_14'
PUBLIC = ROOT / 'reports/research_rainfall/ecmwf_pilot_14d'


def sites_and_cells():
    ds = DatasetV2(ROOT / 'data/processed/dataset_v2_danang')
    screen = json.loads((ROOT / 'reports/domain_screen_danang/run.json').read_text(encoding='utf-8'))
    sites = [x['site'] for x in screen['cells']]
    if len(sites) != 30 or len(set(sites)) != 30:
        raise ValueError('Domain screen không có đúng 30 ô duy nhất')
    cells = ds.cells.set_index('site').loc[sites]
    return ds, sites, cells


def run_filename(run):
    return run.strftime('run_%Y%m%dT%H00Z.json')


def validate_response(body, run, cells):
    if not isinstance(body, list) or len(body) != len(cells):
        raise ValueError('API không trả đúng số ô theo thứ tự request')
    for payload, (_, cell) in zip(body, cells.iterrows()):
        if abs(float(payload['latitude']) - float(cell.lat)) > .6 or abs(float(payload['longitude']) - float(cell.lon)) > .6:
            raise ValueError('Tọa độ API lệch quá 0,6° so request')
        if payload.get('utc_offset_seconds') != 0 or payload['hourly_units'].get('precipitation') != 'mm':
            raise ValueError('Sai timezone hoặc đơn vị mưa')
        hourly = payload['hourly']
        dates = pd.to_datetime(hourly['time'], utc=True)
        amounts = np.asarray([np.nan if x is None else float(x) for x in hourly['precipitation']])
        if len(dates) != 48 or len(amounts) != 48 or dates[0] != run:
            raise ValueError('Run không phủ đúng 48 giờ kể từ lúc khởi tạo')
        if np.any(np.isfinite(amounts) & (amounts < 0)):
            raise ValueError('Lượng mưa âm trong forecast')
    return body


def fetch_run(session, run, cells):
    PRIVATE.mkdir(parents=True, exist_ok=True)
    path = PRIVATE / run_filename(run)
    meta_path = path.with_suffix('.meta.json')
    if path.exists() and meta_path.exists():
        payload = path.read_bytes()
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        if hashlib.sha256(payload).hexdigest() != meta['sha256']:
            raise ValueError('Cache forecast bị sửa so SHA-256')
        return validate_response(json.loads(payload), run, cells), False
    params = dict(latitude=','.join(map(str, cells.lat)), longitude=','.join(map(str, cells.lon)),
                  models='ecmwf_ifs', hourly='precipitation',
                  run=run.strftime('%Y-%m-%dT%H:%M'), forecast_days=2, timezone='UTC')
    error = None
    for attempt in range(5):
        try:
            response = session.get(URL, params=params, timeout=35)
            if response.status_code == 429:
                print(f'RATE_LIMIT run={run:%Y-%m-%dT%H} wait=30s', flush=True)
                time.sleep(30)
                error = RuntimeError('Open-Meteo HTTP 429')
                continue
            response.raise_for_status()
            body = validate_response(response.json(), run, cells)
            payload = response.content
            meta = dict(run_init_utc=run.isoformat(), retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                        request_url=response.url, sha256=hashlib.sha256(payload).hexdigest(),
                        cell_count=len(cells), actual_available_at_known=False)
            path.write_bytes(payload)
            meta_path.write_text(json.dumps(meta, indent=2) + '\n', encoding='utf-8')
            return body, True
        except (requests.RequestException, ValueError) as exc:
            error = exc
            if attempt < 4:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f'Run {run.isoformat()} không tải/kiểm tra được: {type(error).__name__}') from error


def forecast_six_hours(payload, issue):
    """Open-Meteo ghi mưa ở cuối khoảng; hàng API t+1 ứng với [t,t+1)."""
    hourly = payload['hourly']
    lookup = {pd.Timestamp(t, tz='UTC'): value for t, value in zip(hourly['time'], hourly['precipitation'])}
    values = [lookup.get(issue + pd.Timedelta(hours=h + 1)) for h in range(6)]
    return np.asarray([np.nan if value is None else float(value) for value in values], dtype=float)


def bootstrap_metric(frame, metric, *, draws=1000, block_days=5, seed=42):
    days = pd.DatetimeIndex(pd.to_datetime(frame.issue_utc, utc=True).dt.floor('D').unique()).sort_values()
    grouped = [frame.index[pd.to_datetime(frame.issue_utc, utc=True).dt.floor('D') == day].to_numpy() for day in days]
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(draws):
        positions = []
        while len(positions) < len(days):
            start = int(rng.integers(0, max(1, len(days) - block_days + 1)))
            positions.extend(range(start, min(start + block_days, len(days))))
        rows = np.concatenate([grouped[i] for i in positions[:len(days)]])
        sample = frame.loc[rows]
        value = metric(sample)
        if np.isfinite(value):
            values.append(value)
    return [float(x) for x in np.quantile(values, [.025, .975])] if values else [None, None]


def json_safe(value):
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def score_window(frame, window, reference):
    lo, hi = window
    y = np.stack(frame.obs6.to_numpy())[:, lo:hi].sum(1)
    f = np.stack(frame.fcst12.to_numpy())[:, lo:hi].sum(1)
    ok = np.isfinite(y) & np.isfinite(f)
    valid = frame.loc[ok].copy()
    valid['obs'] = y[ok]
    valid['fcst'] = f[ok]
    if valid.empty:
        return dict(n=0)
    metric = continuous_scores(valid.obs, valid.fcst)
    event_threshold = 10 if hi - lo == 3 else 25
    metric.update({k: v for k, v in contingency_scores(valid.obs, valid.fcst, event_threshold).items()
                   if k in ('CSI', 'POD', 'FAR', 'FBI', 'n_obs_events', 'hits', 'misses', 'false_alarms')})
    metric['threshold_mm'] = event_threshold
    metric['valid_fraction'] = len(valid) / len(frame)
    metric['rmse_ci95_5day'] = bootstrap_metric(valid, lambda x: continuous_scores(x.obs, x.fcst)['RMSE'])
    metric['csi_ci95_5day'] = bootstrap_metric(valid, lambda x: contingency_scores(x.obs, x.fcst, event_threshold)['CSI'])
    metric['event_days'] = int(pd.to_datetime(valid.loc[valid.obs >= event_threshold, 'issue_utc'], utc=True).dt.floor('D').nunique())
    metric['zero_rmse_same_rows'] = continuous_scores(valid.obs, np.zeros(len(valid)))['RMSE']
    metric['delta_rmse_vs_zero_ci95_5day'] = bootstrap_metric(valid, lambda x:
        continuous_scores(x.obs, x.fcst)['RMSE'] - continuous_scores(x.obs, np.zeros(len(x)))['RMSE'])
    if reference == 'lag12':
        f6 = np.stack(valid.fcst6.to_numpy())[:, lo:hi].sum(1)
        common = np.isfinite(f6)
        if common.any():
            a = valid.loc[common].copy()
            a['fcst6_amount'] = f6[common]
            metric['lag6_sensitivity_common_n'] = len(a)
            metric['lag12_rmse_common'] = continuous_scores(a.obs, a.fcst)['RMSE']
            metric['lag6_rmse_common'] = continuous_scores(a.obs, a.fcst6_amount)['RMSE']
            metric['lag6_minus_lag12_rmse_ci95_5day'] = bootstrap_metric(a, lambda x:
                continuous_scores(x.obs, x.fcst6_amount)['RMSE'] - continuous_scores(x.obs, x.fcst)['RMSE'])
    return metric


def evaluate(ds, sites, cells, catalog):
    hours = ds.hours
    label_idx = ds.feature_index['y_gsmap_gc_mm']
    perm_idx = ds.feature_index['label_permanent']
    site_index = {site: int(ds.cells.index[ds.cells.site == site][0]) for site in sites}
    records = []
    for issue in ISSUES:
        run12 = issue - pd.Timedelta(hours=12)
        run6 = issue - pd.Timedelta(hours=6)
        body12 = catalog[run12]
        body6 = catalog.get(run6)
        t = hours.get_indexer(pd.DatetimeIndex([issue.tz_localize(None)]))[0]
        if t < 0:
            raise ValueError('Dataset thiếu giờ issue 2024')
        for i, site in enumerate(sites):
            c = site_index[site]
            obs = np.asarray(ds.cube[c, t:t+6, label_idx], dtype=float)
            perm = np.asarray(ds.cube[c, t:t+6, perm_idx], dtype=float)
            if len(obs) != 6 or not np.isfinite(obs).all() or not np.all(perm == 1):
                continue
            records.append(dict(site=site, issue_utc=issue.isoformat(), run12_utc=run12.isoformat(),
                                obs6=obs, fcst12=forecast_six_hours(body12[i], issue),
                                fcst6=forecast_six_hours(body6[i], issue) if body6 is not None else np.full(6, np.nan)))
    frame = pd.DataFrame(records)
    if len(frame) != len(ISSUES) * len(sites):
        raise ValueError('Nhãn không phủ đủ 14 ngày × 30 ô; cần báo riêng thiếu mẫu')
    PRIVATE.mkdir(parents=True, exist_ok=True)
    store = frame.copy()
    for col in ('obs6', 'fcst12', 'fcst6'):
        store[col] = store[col].map(list)
    store.to_parquet(PRIVATE / 'paired_predictions.parquet', index=False)
    results = dict(period_start_utc=START.isoformat(), period_end_exclusive_utc=STOP.isoformat(),
                   sites=len(sites), issues=len(ISSUES), candidate_issue_cells=len(frame),
                   source='Open-Meteo ECMWF IFS Single Runs', model='ecmwf_ifs',
                   api_processing_note='Hourly precipitation and spatial mapping supplied by Open-Meteo; not native ECMWF GRIB',
                   assumed_run_age_h=12, actual_historical_available_at_attested=False,
                   lag6_is_optimistic_sensitivity_only=True, open_meteo_rain_time='end of hourly interval',
                   source_documentation='https://open-meteo.com/en/docs/single-runs-api',
                   no_ai_comparison=True, test_2025_scored=False,
                   scores_0_3h=score_window(frame, (0,3), 'lag12'),
                   scores_3_6h=score_window(frame, (3,6), 'lag12'),
                   scores_0_6h=score_window(frame, (0,6), 'lag12'))
    PUBLIC.mkdir(parents=True, exist_ok=True)
    results = json_safe(results)
    (PUBLIC / 'summary.json').write_text(json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return results


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--limit', type=int, default=0, help='chỉ thử N run đầu; 0 = toàn bộ 56 run')
    ap.add_argument('--min-interval', type=float, default=8, help='giây nghỉ sau mỗi request mới để tránh HTTP 429')
    args = ap.parse_args()
    if args.limit < 0 or args.min_interval < 6:
        ap.error('--limit phải ≥0 và --min-interval phải ≥6 giây')
    ds, sites, cells = sites_and_cells()
    runs = [issue - pd.Timedelta(hours=12) for issue in ISSUES]
    if len(runs) != 56 or len(set(runs)) != 56:
        raise AssertionError('Sai tập run thí điểm')
    chosen = runs[:args.limit] if args.limit else runs
    catalog = {}
    fresh = 0
    session = requests.Session()
    failure = None
    try:
        for n, run in enumerate(chosen, 1):
            body, downloaded = fetch_run(session, run, cells)
            catalog[run] = body
            fresh += int(downloaded)
            print(f'RUN {n}/{len(chosen)} {run:%Y-%m-%dT%H} {"downloaded" if downloaded else "cached"}', flush=True)
            if downloaded and n < len(chosen):
                time.sleep(args.min_interval)
    except Exception as exc:
        failure = exc
    finally:
        session.close()
    PUBLIC.mkdir(parents=True, exist_ok=True)
    status = dict(period_start_utc=START.isoformat(), period_end_exclusive_utc=STOP.isoformat(),
                  sites=len(sites), requested_runs=len(runs), cached_runs=len(catalog),
                  fresh_runs_this_call=fresh, collection_complete=len(catalog)==len(runs),
                  rate_limit_min_interval_s=args.min_interval, failure_type=type(failure).__name__ if failure else None,
                  actual_historical_available_at_attested=False, test_2025_scored=False)
    (PUBLIC / 'collection_status.json').write_text(json.dumps(status, indent=2) + '\n', encoding='utf-8')
    print('COLLECTION ' + json.dumps(status), flush=True)
    if failure is not None:
        raise failure
    if len(catalog)==len(runs):
        results = evaluate(ds, sites, cells, catalog)
        print('SCORES_0_3H ' + json.dumps(results['scores_0_3h'], allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
