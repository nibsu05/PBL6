"""Freeze audited sources and station aliases, not an approved training label.

Private bundle contains station data. Public output contains aggregate counts
only. No network, credentials, 2025 observations or model fitting.
"""
from pathlib import Path
from collections import Counter
import gzip
import hashlib
import json
import re
import sqlite3
import shutil
import sys
import zipfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.vrain_export_audit import inventory_from_groups, depth
from src.vrain_station_identity import canonical_inventory

BASE = ROOT / 'data/operational/vrain_2026_11_09'
OUT = BASE / 'handoff_v1'
PUBLIC = ROOT / 'docs/vrain_data_freeze.json'
CLOCK = re.compile(r'^\d{2}:\d{2} \d{2}/\d{2}$')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def verify_archive(path, expected):
    db = sqlite3.connect(f'file:{(path / "manifest.sqlite").as_posix()}?mode=ro', uri=True)
    records = [json.loads(row[0]) for row in db.execute('SELECT record FROM days')]
    db.close()
    if len(records) != expected:
        raise ValueError('Archive not complete')
    counts = Counter()
    for record in records:
        if record['day'][:4] == '2025':
            raise ValueError('2025 must remain unopened')
        file = path / record['relative_path']
        raw = gzip.decompress(file.read_bytes())
        if digest(file) != record['gzip_sha256'] or hashlib.sha256(raw).hexdigest() != record['raw_sha256']:
            raise ValueError('Checksum mismatch')
        if record['status'] == 'structure_flag':
            raise ValueError('Source schema requires review')
        numeric_count = record.get('valid_numeric_cells')
        if numeric_count is None:
            payload = json.loads(raw)
            numeric_count = sum(depth(station['depth']) is not None
                                for row in payload['stats'] if CLOCK.fullmatch(row['timePoint'])
                                for station in row['stations'])
        counts['responses'] += 1
        counts['days_with_clock_rows'] += bool(record.get('hourly_rows', 0))
        counts['days_with_numeric_values'] += numeric_count > 0
        counts['sum_mismatches'] += record.get('sum_mismatches', 0)
    return dict(counts), records


def observations(payload, aliases):
    result = {}
    for row in payload['stats']:
        if not CLOCK.fullmatch(row['timePoint']):
            continue
        for station in row['stations']:
            value = depth(station['depth'])
            sid = str(station['id'])
            if sid not in aliases:
                raise ValueError('History station absent from canonical aliases')
            if value is not None:
                result[(row['timePoint'], aliases[sid])] = value
    return result


def main():
    progress = json.loads((BASE / 'recent_archive/progress.json').read_text(encoding='utf8'))
    if progress['state'] != 'download_complete' or progress['downloaded_responses'] != 622:
        raise ValueError('Wait for the 2026 collector to finish')
    OUT.mkdir(exist_ok=True)
    inventories = [inventory_from_groups(json.loads((BASE / name).read_text(encoding='utf8')))
                   for name in ['groups_private.json', 'groups_v2_private.json']]
    canonical = canonical_inventory(*inventories)
    pd.DataFrame(canonical).to_csv(OUT / 'station_registry_private.csv', index=False)
    aliases = {key: {r[key + '_id']: r['canonical_id'] for r in canonical if r[key + '_id'] is not None}
               for key in ['legacy', 'modern']}
    legacy = np.load(BASE / 'freeze_work/station_matrices.npz')
    columns = [aliases['legacy'][sid] for sid in legacy['station_ids']]
    clocks = pd.to_datetime(legacy['clock_end_naive']).strftime('%Y-%m-%d %H:%M:%S')
    values = np.where(legacy['valid'], legacy['rain'], np.nan).reshape(-1, len(columns))
    frame = pd.DataFrame(values, columns=columns).reindex(columns=[r['canonical_id'] for r in canonical])
    frame.insert(0, 'source_clock_naive_unconfirmed_timezone', clocks)
    frame.to_parquet(OUT / 'station_source_values_2021_2024.parquet', index=False)
    # Keep original values and station-day sum flags to make every exclusion reversible.
    np.savez_compressed(OUT / 'legacy_qc_source_matrix.npz', **{key: legacy[key] for key in legacy.files})
    legacy_archive, legacy_records = verify_archive(BASE / 'download', 3653)
    write_json(OUT / 'legacy_raw_manifest.json', legacy_records)
    recent = {}
    paths = []
    for key in ['legacy', 'modern']:
        recent[key], records = verify_archive(BASE / 'recent_archive' / key, 311)
        write_json(OUT / ('recent_' + key + '_raw_manifest.json'), records)
        paths.extend((BASE / 'recent_archive' / key / r['relative_path'],
                      'recent_2026/' + key + '/' + r['relative_path']) for r in records)
    overlap = Counter()
    overlap_sites, overlap_days = set(), set()
    numeric_by_station = {key: Counter() for key in ['legacy', 'modern']}
    recent_daily = []
    for day in pd.date_range('2026-01-02', '2026-11-08').strftime('%Y-%m-%d'):
        data = {}
        for key in ['legacy', 'modern']:
            path = BASE / 'recent_archive' / key / 'raw/2026' / (day + '.json.gz')
            data[key] = observations(json.loads(gzip.decompress(path.read_bytes())), aliases[key])
            numeric_by_station[key].update(sid for _, sid in data[key])
        both = data['legacy'].keys() & data['modern'].keys()
        overlap_sites.update(key[1] for key in both)
        if both:
            overlap_days.add(day)
        overlap['compared_numeric_cells'] += len(both)
        overlap['wet_in_either'] += sum(max(data['legacy'][k], data['modern'][k]) > 0 for k in both)
        overlap['different_over_1e_minus_6'] += sum(abs(data['legacy'][k] - data['modern'][k]) > 1e-6 for k in both)
        overlap['legacy_wet_modern_zero'] += sum(data['legacy'][k] > 0 and data['modern'][k] == 0 for k in both)
        recent_daily.append(dict(date=day, legacy_numeric_cells=len(data['legacy']),
                                 modern_numeric_cells=len(data['modern']), compared_cells=len(both)))
    pd.DataFrame(recent_daily).to_csv(OUT / 'recent_daily_availability.csv', index=False)
    overlap['stations_compared'] = len(overlap_sites)
    overlap['days_compared'] = len(overlap_days)
    write_json(OUT / 'recent_numeric_counts_private.json', numeric_by_station)
    # Select predictors only, before the reserved year. Never open future label columns.
    groups = json.loads((ROOT / 'reports/regional_research_plan_2026_10_20/feature_groups.json').read_text(encoding='utf8'))
    selected = {g: [name if name.startswith(('sin_', 'cos_')) else 'mean__' + name for name in groups[g]]
                for g in ['B', 'A', 'M', 'C']}
    feature_columns = sum(selected.values(), [])
    x = pd.read_parquet(ROOT / 'data/processed/regional_danang/v1_hourly.parquet',
                        columns=['datetime'] + feature_columns,
                        filters=[('datetime', '>=', pd.Timestamp('2020-12-01', tz='UTC').as_unit('ns')),
                                 ('datetime', '<', pd.Timestamp('2025-01-01', tz='UTC').as_unit('ns'))])
    if pd.to_datetime(x['datetime']).dt.year.eq(2025).any():
        raise ValueError('Unexpected holdout read')
    x.to_parquet(OUT / 'era5_predictors_hourly_44.parquet', index=False)
    write_json(OUT / 'feature_groups.json', dict(hourly=selected,
               daily={g: [name for name in names if name not in ['sin_hour', 'cos_hour']] for g, names in selected.items()},
               experiments=groups['experiments'], daily_aggregation_status='not_materialized_pending_time_contract'))
    spatial = json.loads((BASE / 'freeze_work/spatial_panel_inspection.json').read_text(encoding='utf8'))
    coverage = json.loads((BASE / 'freeze_work/full_network_coverage.json').read_text(encoding='utf8'))
    summary = dict(
        release='VRAIN_SOURCE_V1_2026_11_09', status='audited_sources_not_training_ready',
        legacy_stations=len(inventories[0]), modern_stations=len(inventories[1]),
        canonical_stations=len(canonical), exact_unique_coordinate_matches=len(aliases['legacy']),
        unchanged_names=sum(r['name_equal'] is True for r in canonical),
        renamed_matches=sum(r['name_equal'] is False for r in canonical),
        modern_only_locations=sum(r['legacy_id'] is None for r in canonical),
        coordinate_identity_scope='current metadata only; historical sensor/location continuity unconfirmed',
        legacy_archive_verification=legacy_archive,
        legacy_observation_days=1461, legacy_clock_rows=35064,
        legacy_observation_marked_dates=['2021-01-01', '2024-12-31'],
        recent_requested_marked_dates=['2026-01-02', '2026-11-08'], recent=recent,
        recent_source_comparison=dict(overlap), observations_merged=False,
        era5_predictor_rows=len(x), era5_hourly_channels=44, era5_daily_channels_planned=42,
        era5_rows_with_missing_predictors=int(x[feature_columns].isna().any(axis=1).sum()),
        era5_missing_cells_by_feature={name: int(count) for name, count in x[feature_columns].isna().sum().items() if count},
        regional_footprint='R93: union of 93 full 0.1-degree cells; approximate administrative extent',
        spatial_panel_diagnostics=spatial, full_network_coverage_diagnostics=coverage,
        diagnostics_note='Voronoi diagnostics conditional on R93/current station coordinates; sample counts are NOT final split-guarded training counts',
        source_timezone_interval_semantics_confirmed=False, regional_label_frozen=False,
        test2025_read=False, training_performed=False, training_ready=False,
        blockers=['Verify source clock timezone and interval start/end/units',
                  'Resolve missing mountain observations versus stable-label spatial representativeness',
                  'Confirm final footprint and use identical support for X and y'],
    )
    write_json(PUBLIC, summary)
    write_json(OUT / 'release_summary.json', summary)
    report = ROOT / 'reports/vrain_data_handoff_2026_11_09/CHOT_DU_LIEU_GUI_NHOM.md'
    marker = '\n<!-- GENERATED_RECENT_AUDIT -->\n'
    text = report.read_text(encoding='utf8').split(marker)[0].rstrip()
    text += marker + '\n## 7. Kiểm kê bổ sung 2026 sau khi tải xong\n\n'
    text += '| Kênh | Phản hồi đã kiểm tra SHA | Ngày có hàng giờ | Ngày có ít nhất một số đo |\n| --- | ---: | ---: | ---: | ---: |\n'
    for key, label in [('legacy', 'Cũ'), ('modern', 'Hiện hành')]:
        r = recent[key]
        text += f'| {label} | {r["responses"]} | {r["days_with_clock_rows"]} | {r["days_with_numeric_values"]} |\n'
    text += (f'\nĐối chiếu hai kênh tại cùng ngày, nhãn đồng hồ và mã chuẩn: **{overlap["compared_numeric_cells"]:,}** '
             f'cặp có số ở cả hai phía; **{overlap["wet_in_either"]:,}** cặp có mưa ở ít nhất một phía; '
             f'**{overlap["different_over_1e_minus_6"]:,}** cặp khác nhau quá 1e-6 đơn vị nguồn. '
             f'Phần trùng chỉ thuộc **{len(overlap_sites)} vị trí** trên **{len(overlap_days)} ngày**; '
             f'**{overlap["legacy_wet_modern_zero"]}** cặp có mưa ở kênh cũ nhưng bằng 0 ở kênh mới. '
             'Đây chưa phải kiểm chứng tương đương số đo cho cả 82 cặp vị trí. '
             'Phép so này chỉ bao phủ các cặp cùng có số, không xác nhận các khoảng không trùng, lịch sử vị trí hoặc ngữ nghĩa thời gian. '
             'Gói này vẫn giữ hai nguồn riêng, chưa tự nối thành chuỗi huấn luyện.\n')
    report.write_text(text, encoding='utf8')
    from scripts.build_final_regional_plan import word_copy
    from docx import Document
    word = word_copy(report)
    doc = Document(word)
    for section in doc.sections:
        for paragraph in section.footer.paragraphs:
            for run in paragraph.runs:
                run.text = run.text.replace('20/10/2026', '09/11/2026')
    doc.core_properties.title = 'Bàn giao dữ liệu Vrain và ERA5 — 09/11/2026'
    doc.core_properties.subject = 'Nguồn đã kiểm kê; 86 mã chuẩn; nhãn vùng chưa chốt'
    doc.save(word)
    shutil.copy2(report, OUT / report.name)
    shutil.copy2(word, OUT / word.name)
    pd.read_parquet(ROOT / 'data/processed/regional_danang/cell_weights.parquet').to_parquet(OUT / 'r93_cells.parquet', index=False)
    (OUT / 'README.txt').write_text(
        'PRIVATE GROUP HANDOFF - DO NOT COMMIT OR PUBLISH STATION DATA\n'
        '86 canonical stations = 82 exact-coordinate legacy aliases + 4 modern-only locations.\n'
        '2021-2024 values: source clocks, timezone/interval interpretation NOT confirmed.\n'
        'QC excludes 3 station-days with inconsistent reported daily sums; original matrix preserved.\n'
        '2026: both raw namespaces preserved separately, no automatic rainfall merge.\n'
        'ERA5: 44 hourly predictor channels only. No old GSMaP target included.\n'
        'This is a SOURCE release, NOT a frozen regional training target.\n'
        '2025 remains unopened. Do not train or tune on 2026 before future evaluation design is agreed.\n'
        'See release_summary.json and the public handoff document for measured spatial coverage limits.\n', encoding='utf8')
    files = [p for p in OUT.rglob('*') if p.is_file() and p.name != 'manifest.json']
    write_json(OUT / 'manifest.json', dict(release=summary['release'], files={
        p.relative_to(OUT).as_posix(): dict(bytes=p.stat().st_size, sha256=digest(p)) for p in sorted(files)}))
    zip_path = BASE / 'PBL6_VRAIN_SOURCE_V1.zip'
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():
                bundle.write(p, 'handoff/' + p.relative_to(OUT).as_posix())
        for path, arcname in paths:
            bundle.write(path, arcname, compress_type=zipfile.ZIP_STORED)
        # Only immutable raw files/checksum records; never session, cookies or private access context.
        for path in sorted((BASE / 'download/raw').rglob('*.json.gz')):
            if path.stem.startswith('2025'):
                raise ValueError('Holdout file must not enter the release')
            bundle.write(path, 'legacy_2015_2024/' + path.relative_to(BASE / 'download').as_posix(), compress_type=zipfile.ZIP_STORED)
    with zipfile.ZipFile(zip_path) as bundle:
        if bundle.testzip() is not None:
            raise ValueError('ZIP verification failed')
    print(json.dumps({k: summary[k] for k in ['release', 'canonical_stations', 'recent', 'recent_source_comparison', 'era5_predictor_rows', 'training_ready']}, indent=2))
    print('Private ZIP:', zip_path, 'bytes:', zip_path.stat().st_size)


if __name__ == '__main__':
    main()
