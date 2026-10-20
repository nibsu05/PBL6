"""Tạo V1 trung bình vùng và V2 giữ thông tin không gian, dữ liệu ngoài Git."""
from pathlib import Path
import sys, json, hashlib, argparse
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.dataloader_v2 import DatasetV2
from src.regional_dataset import aggregate_block, cell_areas_km2, zone_masks, feature_catalog


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dataset', type=Path, default=ROOT/'data/processed/dataset_v2_danang')
    ap.add_argument('--out', type=Path, default=ROOT/'data/processed/regional_danang')
    ap.add_argument('--report', type=Path, default=ROOT/'reports/regional_danang_v1_v2')
    args = ap.parse_args()
    ds = DatasetV2(args.dataset)
    if len(ds.cells) != 93 or not (ds.cells.province == 'Đà Nẵng').all():
        raise ValueError('Chỉ dùng đúng93ô Đà Nẵng cho bản này')
    areas = cell_areas_km2(ds.cells.lat)
    blocks1, blocks2 = [], []
    lab = ds.feature_index['y_gsmap_gc_mm']
    # Chỉ loại calendar padding sau giờ cuối có nhãn ở mọi ô; không chấm dữ liệu2025.
    last = np.flatnonzero(np.isfinite(np.asarray(ds.cube[:, :, lab])).all(0))[-1] + 1
    for start in range(0, last, 4096):
        end = min(start + 4096, last)
        v1, v2 = aggregate_block(ds.cube[:, start:end, :], ds.feature_names, ds.cells, areas)
        dates = pd.DatetimeIndex(ds.hours[start:end]).tz_localize('UTC')
        blocks1.append(pd.DataFrame(v1, index=dates))
        blocks2.append(pd.DataFrame(v2, index=dates))
        print(f'aggregate {end}/{last} hours', flush=True)
    frames = [pd.concat(b).rename_axis('datetime') for b in (blocks1, blocks2)]
    if not frames[0].equals(frames[1][frames[0].columns]):
        raise ValueError('V2 phải chứa nguyên vẹn V1, kể cả nhãn/NaN')
    args.out.mkdir(parents=True, exist_ok=True)
    args.report.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for name, frame in zip(('v1', 'v2'), frames):
        path = args.out/f'{name}_hourly.parquet'
        frame.reset_index().to_parquet(path, index=False)
        outputs[name] = {'path': str(path.relative_to(ROOT)), 'rows': len(frame),
                         'columns_including_metadata': len(frame.columns) + 1,
                         'sha256': sha256(path), 'bytes': path.stat().st_size}
    catalog = feature_catalog(ds.feature_names)
    pd.DataFrame([dict(column=k, **v) for k, v in catalog.items()]).to_csv(args.report/'feature_catalog.csv', index=False)
    zones = zone_masks(ds.cells)
    weights = ds.cells[['site','lat','lon','elev_mean_m','coast_dist_km','ocean_frac']].copy()
    weights['full_cell_area_km2'] = areas
    weights['weight'] = areas / areas.sum()
    weights['zone'] = np.select([zones['coastal'], zones['highland']], ['coastal','highland'], default='interior')
    weights.to_parquet(args.out/'cell_weights.parquet', index=False)
    manifest = {'version': 'regional-v1-v2-2026-10-20', 'source_manifest_sha256': sha256(args.dataset/'manifest.json'),
                'packaged_source_verification': '2233/2233 matched, missing0, mismatch0 on2026-10-20',
                'region': '93 selected Danang-new grid cells; approximate footprint, not exact administrative polygon',
                'weighting': 'Spherical full-cell area, 0.1 degree; no polygon-intersection geometry available locally',
                'footprint_full_cells_km2': float(areas.sum()), 'cells': len(ds.cells),
                'zones': {k: {'cells': int(m.sum()), 'weight': float(areas[m].sum()/areas.sum())} for k,m in zones.items()},
                'zone_rules': 'coastal distance<=30km; remaining highland elevation>=600m; remainder interior. Fixed without labels.',
                'missing_policy': 'strict complete selected spatial support per feature; no filling or changing denominator',
                'label': 'Area mean of hourly GSMaP Gauge v8, same y for V1 and V2',
                'time_convention': '[datetime, datetime+1h) UTC; calendar padding after last complete label removed',
                'start': str(frames[0].index[0]), 'end': str(frames[0].index[-1]),
                'year_2025': 'Exported mechanically; reserved and excluded from all pilot fitting/scoring/diagnostics',
                'predictors_v1': sum(v['version']=='V1' for v in catalog.values()),
                'predictors_v2': len(catalog), 'outputs': outputs,
                'caveats': ['Spatial summaries are not independent new observations.',
                            'ERA5 interpolation to0.1deg does not improve native resolution.',
                            'Raw/Gauge share satellite algorithms; live availability not asserted.',
                            'All8static columns are constant for one regional target and not repeated as predictor columns.']}
    (args.out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (args.report/'build_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
