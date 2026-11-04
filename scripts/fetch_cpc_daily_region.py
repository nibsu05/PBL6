"""Fetch 2015--2023 CPC daily analyses; retain station provenance and EOD.

All source files and per-day values stay under data/operational, outside Git.
The region is the existing 93-cell footprint, not a new administrative mask.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import hashlib
import json
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from netCDF4 import Dataset, num2date

PRIVATE = ROOT / 'data/operational/daily_gauge_2026_11_04'
REPORT = ROOT / 'reports/daily_gauge_2026_11_04'
PROBE = PRIVATE / 'source_probe'
BASE = 'https://downloads.psl.noaa.gov/Datasets/cpc_global_precip/'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def fetch_year(year):
    assert 2015 <= year <= 2023, 'Development only; never download test years'
    folder = PRIVATE / 'cpc_annual'; folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'precip.{year}.nc'; url = BASE + path.name
    if not path.exists():
        error = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'PBL6-daily-rainfall-research'})
                with urllib.request.urlopen(req, timeout=50) as r, path.with_suffix('.part').open('wb') as f:
                    expected = int(r.headers.get('Content-Length', '0')); actual = 0
                    while block := r.read(1024 * 1024):
                        f.write(block); actual += len(block)
                assert not expected or actual == expected, 'Incomplete download'
                path.with_suffix('.part').replace(path); break
            except Exception as exc:
                error = exc
                if attempt == 2: raise RuntimeError(f'Cannot fetch {year}: {error}') from error
                time.sleep(2 * (attempt + 1))
    print(f'CPC source ready: {year}, {path.stat().st_size} bytes', flush=True)
    return dict(year=year, url=url, bytes=path.stat().st_size, sha256=sha(path))


def ensure_probe_sources():
    PROBE.mkdir(parents=True, exist_ok=True)
    base = 'https://ftp.cpc.ncep.noaa.gov/precip/CPC_UNI_PRCP/GAUGE_GLB/'
    jobs = {
        'ghcnd-stations.txt': 'https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt',
        'ghcnd-inventory.txt': 'https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-inventory.txt',
        'cpc_readme.txt': base+'DOCU/PRCP_CU_GAUGE_V1.0GLB_0.50deg_README.txt',
        'cpc_eod.lnx': base+'DOCU/PRCP_CU_GAUGE_V1.0GLB_0.50deg_EOD.lnx',
        'cpc_eod.ctl': base+'DOCU/PRCP_CU_GAUGE_V1.0GLB_0.50deg_EOD.lnx.ctl'}
    dates = [str(y)+md for y in [2015,2019,2023] for md in ['0101','0401','0701','1001']] + ['20221014']
    for d in dates: jobs['cpc_'+d+'.bin'] = base+'RT/'+d[:4]+'/PRCP_CU_GAUGE_V1.0GLB_0.50deg.lnx.'+d+'.RT'
    records = []
    for name, url in jobs.items():
        path = PROBE/name
        if not path.exists():
            with urllib.request.urlopen(url, timeout=50) as r: path.write_bytes(r.read())
        records.append(dict(file=name,url=url,bytes=path.stat().st_size,sha256=sha(path)))
    (REPORT/'source_probe_manifest.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf8',newline='\n')


def main():
    PRIVATE.mkdir(parents=True, exist_ok=True); REPORT.mkdir(parents=True, exist_ok=True)
    ensure_probe_sources()
    weights_path = ROOT / 'data/processed/regional_danang/cell_weights.parquet'
    w = pd.read_parquet(weights_path)
    assert len(w) == 93 and np.isclose(w.weight.sum(), 1)
    w['cpc_lat'] = np.floor(w.lat / .5) * .5 + .25
    w['cpc_lon'] = np.floor(w.lon / .5) * .5 + .25
    support = w.groupby(['cpc_lat', 'cpc_lon']).agg(
        fine_cells=('site', 'size'), weight=('weight', 'sum'),
        footprint_area_km2=('full_cell_area_km2', 'sum')).reset_index()
    # Fine-cell edges and CPC edges share the 0.0/0.5-degree boundaries.
    assert len(support) == 9
    eod = np.fromfile(PROBE / 'cpc_eod.lnx', dtype='<f4').reshape(360, 720)
    xi = np.rint((support.cpc_lon - .25) / .5).astype(int)
    yi = np.rint((support.cpc_lat + 89.75) / .5).astype(int)
    support['eod_utc_hours'] = eod[yi, xi]
    assert (support.eod_utc_hours == 12).all(), 'Mixed EOD requires a different protocol'
    support.to_csv(REPORT / 'cpc_spatial_support.csv', index=False, lineterminator='\n')
    sources = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(fetch_year, year) for year in range(2015, 2024)]):
            sources.append(future.result())
    cells, region, attrs = [], [], []
    for year in range(2015, 2024):
        path = PRIVATE / 'cpc_annual' / f'precip.{year}.nc'
        with Dataset(path) as ds:
            lat, lon = ds.variables['lat'][:], ds.variables['lon'][:]
            timevar = ds.variables['time']; rain = ds.variables['precip']
            dates = pd.DatetimeIndex([pd.Timestamp(d.isoformat()) for d in num2date(
                timevar[:], timevar.units, only_use_cftime_datetimes=False)])
            assert dates.equals(pd.date_range(f'{year}-01-01', f'{year}-12-31', freq='D'))
            assert str(rain.units).lower() in ['mm', 'mm/day', 'mm/d'], rain.units
            series = []
            for row in support.itertuples():
                iy = np.flatnonzero(np.isclose(lat, row.cpc_lat)); ix = np.flatnonzero(np.isclose(lon, row.cpc_lon))
                assert len(iy) == len(ix) == 1
                value = np.ma.asarray(rain[:, iy[0], ix[0]]).filled(np.nan).astype(float)
                assert np.all(value[np.isfinite(value)] >= 0)
                series.append(value)
                cells.append(pd.DataFrame(dict(marked_date=dates, cpc_lat=row.cpc_lat,
                    cpc_lon=row.cpc_lon, rain_mm=value, weight=row.weight)))
            a = np.stack(series, axis=1)
            total = a @ support.weight.to_numpy()
            total[~np.isfinite(a).all(1)] = np.nan
            region.append(pd.DataFrame(dict(marked_date=dates,
                period_end=dates.tz_localize('UTC') + pd.Timedelta(hours=12), y_cpc_region_mm=total)))
            attrs.append(dict(year=year, units=rain.units,
                dataset_attributes={k: str(ds.getncattr(k)) for k in ds.ncattrs()}))
    cell_data = pd.concat(cells, ignore_index=True)
    regional = pd.concat(region, ignore_index=True)
    # Cross-check the PSL archive against original NOAA binary files at all 13 probes.
    probes = []
    for path in sorted(PROBE.glob('cpc_????????.bin')):
        marked = pd.Timestamp(path.stem.split('_')[-1]); raw = np.fromfile(path, dtype='<f4').reshape(2, 360, 720)
        original, gauges = raw[:, yi, xi]
        sub = cell_data[cell_data.marked_date == marked].sort_values(['cpc_lat', 'cpc_lon'])
        np.testing.assert_allclose(sub.rain_mm, original / 10., atol=2e-4, rtol=1e-6)
        probes.append(dict(date=str(marked.date()), cells_with_gauge=int((gauges > 0).sum()),
            weight_in_boxes_with_gauge=float(support.weight[gauges > 0].sum()),
            gauge_counts=gauges.tolist(), psl_vs_original='passed'))
    assert len(probes) == 13
    cell_data.to_parquet(PRIVATE / 'cpc_daily_cells.parquet', index=False)
    regional.to_parquet(PRIVATE / 'cpc_daily_region.parquet', index=False)
    inventory = []
    lines = (PROBE / 'ghcnd-stations.txt').read_text().splitlines()
    nearby = {}
    for line in lines:
        if not line.startswith('VM'): continue
        la, lo = float(line[12:20]), float(line[21:30])
        if 14.8 <= la <= 16.6 and 106.8 <= lo <= 109:
            nearby[line[:11]] = dict(station=line[:11], name=line[41:71].strip(), lat=la, lon=lo)
    for line in (PROBE / 'ghcnd-inventory.txt').read_text().splitlines():
        if line[:11] in nearby and line[31:35] == 'PRCP':
            inventory.append(dict(nearby[line[:11]], first_year=int(line[36:40]), last_year=int(line[41:45])))
    report = dict(status='passed', source='CPC Unified daily gauge-based gridded analysis, PSL archive',
        label_kind='station-based spatial analysis, not direct area observation', development_years=[2015, 2023],
        regional_days=len(regional), missing_region_days=int(regional.y_cpc_region_mm.isna().sum()),
        region='Existing 93 full-cell approximate footprint of Danang-new; not exact administrative boundary',
        regional_weights_sha256=sha(weights_path), cpc_boxes=9, eod_utc_hours=12,
        eod_scope='Nominal provider EOD file; README warns EOD information is not fully checked',
        issue_time='12 UTC; y1/y2/y3 are three following, separate 24-hour intervals',
        station_inventory_near_region=inventory, original_binary_probes=probes,
        probe_scope='13 predetermined dates only; zero gauges in a box does not mean zero information or invalid interpolation',
        sources=sorted(sources, key=lambda x: x['year']), attributes=attrs,
        private_output_hashes={name: sha(PRIVATE / name) for name in ['cpc_daily_cells.parquet', 'cpc_daily_region.parquet']},
        test2025_read=False)
    (REPORT / 'source_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf8', newline='\n')
    print(json.dumps({k: report[k] for k in ['status', 'regional_days', 'missing_region_days', 'cpc_boxes', 'eod_utc_hours']}))


if __name__ == '__main__': main()
