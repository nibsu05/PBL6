"""Check published slide values against frozen daily aggregates and native PPTX."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

import pandas as pd
from pptx import Presentation
from pptx.util import Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/daily_gauge_slides_2026_11_04'
DATA = ROOT / 'reports/daily_gauge_2026_11_04'
STEM = 'PBL6_DU_LIEU_NGAY_3_MO_HINH'
MODELS = ['lgbm', 'tft', 'informer']
LABELS = ['LightGBM', 'TFT', 'Informer']
METRICS = ['RMSE', 'MAE', 'bias', 'BS', 'BSS', 'CSI', 'POD', 'FAR']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def fmt(value):
    return f'{value:.3f}'.replace('.', ',')


def signed(value):
    return f'{value:+.3f}'.replace('.', ',')


def main():
    manifest = read(OUT / 'build_manifest.json')
    assert manifest['models'] == MODELS
    assert not manifest['training_performed'] and not manifest['test2025_read']
    assert sha(ROOT / 'scripts/build_daily_gauge_slides.py') == manifest['code_sha256']
    for name, digest in manifest['sources'].items():
        assert sha(ROOT / name) == digest, name
    for name, meta in manifest['files'].items():
        assert sha(OUT / name) == meta['sha256'], name
    # Check immutable prior publications, except the user's acknowledged rename.
    preserved = 0
    for pattern in ('short_range_*', 'informer_regional_*', 'daily_gauge_2026_11_04'):
        for directory in (ROOT / 'reports').glob(pattern):
            if not directory.is_dir():
                continue
            marker = directory / 'publication_manifest.json'
            if not marker.exists():
                marker = directory / 'build_manifest.json'
            if not marker.exists():
                continue
            for name, meta in read(marker)['files'].items():
                path = directory / name
                if not path.exists() and path.relative_to(ROOT).as_posix() == 'reports/short_range_three_models_2026_10_21/PBL6_SO_SANH_3_MO_HINH.pptx':
                    continue
                digest = meta['sha256'] if isinstance(meta, dict) else meta
                assert sha(path) == digest, str(path)
                preserved += 1
    snapshot = ROOT / 'data/operational/daily_gauge_2026_11_04/user_slide_snapshot.json'
    user_files = 0
    if snapshot.exists():
        for item in read(snapshot):
            assert sha(ROOT / item['path']) == item['sha256']
            user_files += 1

    scene = read(OUT / 'slide_scene.json')
    prs = Presentation(OUT / (STEM + '.pptx'))
    assert len(scene) == len(prs.slides) == manifest['slides'] == 44
    assert manifest['main_slides'] == 30 and manifest['appendix_slides'] == 14
    tables, specs = {}, {}
    for native, slide in zip(prs.slides, scene):
        assert len(native.shapes) == len(slide['shapes'])
        assert native.notes_slide.notes_text_frame.text == slide['note']
        assert len(slide['note'].split()) >= 45
        assert '\ufffd' not in slide['note']
        for shape, spec in zip(native.shapes, slide['shapes']):
            assert shape.left >= 0 and shape.top >= 0
            assert shape.left + shape.width <= prs.slide_width + 100
            assert shape.top + shape.height <= prs.slide_height + 100
            if spec['kind'] == 'text':
                assert shape.text == spec['text'].replace('**', '')
                assert '\ufffd' not in shape.text
            if spec['kind'] != 'table':
                continue
            all_rows = [spec['headers']] + spec['rows']
            labels = {v for row in all_rows for v in row if v in LABELS}
            if len(labels) >= 2:
                assert labels == set(LABELS), (slide['number'], labels)
            for ri, row in enumerate(all_rows):
                for ci, value in enumerate(row):
                    cell = shape.table.cell(ri, ci)
                    assert cell.text == str(value)
                    style = spec['styles'].get(f'{ri},{ci}', {})
                    for paragraph in cell.text_frame.paragraphs:
                        for run in paragraph.runs:
                            assert run.font.name == 'Arial' and run.font.size == Pt(spec['size'])
                            assert run.font.bold == (ri == 0 or style.get('bold', False))
                            assert str(run.font.color.rgb) == ('FFFFFF' if ri == 0 else style.get('color', '123047'))
            tables[spec['tag']] = shape.table
            specs[spec['tag']] = spec

    source = pd.read_csv(DATA / 'KET_QUA_72.csv')
    assert len(source) == 72 and not source[METRICS].isna().any().any()
    indexed = source.set_index(['model', 'experiment', 'lead_day'])
    def record(model, e, day):
        return indexed.loc[(model, e, day)]
    def check_metric_cell(tag, ri, ci, r, key):
        assert tables[tag].cell(ri, ci).text == fmt(r[key])
        peers = [record(m, r.experiment, r.lead_day)[key] for m in MODELS]
        values = [abs(v) for v in peers] if key == 'bias' else peers
        best = min(values) if key in ('RMSE', 'MAE', 'bias', 'BS', 'FAR') else max(values)
        v = abs(r[key]) if key == 'bias' else r[key]
        bold = round(float(v), 3) == round(float(best), 3)
        style = specs[tag]['styles'][f'{ri},{ci}']
        assert style['bold'] == bold
        assert style['color'] == ('AD3434' if key == 'BSS' and r[key] < 0 else '087E8B' if bold else '123047')
    checked, keys = 0, set()
    for day in (1, 2, 3):
        for block in (1, 2, 3):
            tag = f'full_{day}_{block}'
            for ri, row in enumerate(specs[tag]['rows'], 1):
                e, label = row[:2]
                model = MODELS[LABELS.index(label)]
                # Retain identifiers as columns for independent peer grouping.
                r = record(model, e, day).copy()
                r['experiment'], r['lead_day'] = e, day
                assert (model, e, day) not in keys
                keys.add((model, e, day))
                for ci, key in enumerate(METRICS, 2):
                    check_metric_cell(tag, ri, ci, r, key)
                    checked += 1
        for mi, model in enumerate(MODELS, 1):
            r = record(model, 'E7', day).copy()
            r['experiment'], r['lead_day'] = 'E7', day
            for ci, key in enumerate(METRICS, 1):
                check_metric_cell(f'e7_day{day}', mi, ci, r, key)
                checked += 1
            for ei in range(8):
                r = record(model, f'E{ei}', day).copy()
                r['experiment'], r['lead_day'] = f'E{ei}', day
                check_metric_cell(f'bss_day{day}', ei + 1, mi, r, 'BSS')
                checked += 1
    assert len(keys) == 72

    assert [tables['groups'].cell(i, 1).text for i in range(1, 5)] == ['9', '12', '20', '1']
    assert [tables['experiments'].cell(i, 2).text for i in range(1, 9)] == ['9', '21', '29', '10', '41', '22', '30', '42']
    assert [tables['metrics'].cell(i, 0).text for i in range(1, 9)] == ['RMSE', 'MAE', 'Bias', 'BS', 'BSS', 'CSI', 'POD', 'FAR']
    run = read(DATA / 'run.json')
    for i, year in enumerate((2021, 2022, 2023), 1):
        r = next(x for x in run['models'] if x['year'] == year)
        assert [tables['folds'].cell(i, j).text for j in (3, 4, 5)] == [str(r[k]) for k in ('n_train', 'n_cal', 'n_eval')]
    pooled = pd.read_csv(DATA / 'scores_pooled.csv')
    for day in (1, 2, 3):
        p = pooled[(pooled.model == 'lgbm') & (pooled.experiment == 'E7') & (pooled.lead_day == day) & (pooled.season == 'all')].set_index('threshold_mm')
        assert [tables['sample_counts'].cell(day, j).text for j in (1, 2, 3, 4)] == [str(int(p.loc[16, 'n'])), *[str(int(p.loc[q, 'events'])) for q in (16, 50, 100)]]
    for i, model in enumerate(MODELS, 1):
        r = record(model, 'E7', 1)
        h = int(round(r.POD * r.events)); miss = int(r.events) - h; false = int(round(h * r.FAR / (1 - r.FAR)))
        assert [tables['event_counts'].cell(i, j).text for j in range(1, 7)] == [str(h), str(miss), str(false), fmt(r.POD), fmt(r.FAR), fmt(r.CSI)]

    absolute = pd.read_csv(DATA / 'absolute_bss_ci.csv')
    paired = pd.read_csv(DATA / 'paired_bootstrap.csv')
    ci_cells = 0
    for i, model in enumerate(MODELS, 1):
        for day in (1, 2, 3):
            a = absolute[(absolute.model == model) & (absolute.experiment == 'E7') & (absolute.lead_day == day) & (absolute.block_days == 7)].iloc[0]
            assert tables['absolute_ci'].cell(i, day).text == signed(a.estimate) + '\n[' + signed(a.ci_low) + '; ' + signed(a.ci_high) + ']'
            ci_cells += 1
        for col, e in enumerate(('E1', 'E2', 'E3'), 1):
            p = paired[(paired.kind == 'feature') & (paired.model == model) & (paired.experiment == e) & (paired.lead_day == 1) & (paired.metric == 'BSS16') & (paired.block_days == 7)].iloc[0]
            assert tables['feature_ci'].cell(i, col).text == signed(p.estimate) + '\n[' + signed(p.ci_low) + '; ' + signed(p.ci_high) + ']'
            ci_cells += 1
        p = paired[(paired.kind == 'feature') & (paired.model == model) & (paired.experiment == 'E6') & (paired.lead_day == 2) & (paired.metric == 'BSS16') & (paired.block_days == 7)].iloc[0]
        a = absolute[(absolute.model == model) & (absolute.experiment == 'E6') & (absolute.lead_day == 2) & (absolute.block_days == 7)].iloc[0]
        assert [tables['relative_absolute'].cell(i, j).text for j in (1, 2)] == [fmt(record(model, e, 2).BSS) for e in ('E0', 'E6')]
        assert tables['relative_absolute'].cell(i, 3).text == signed(p.estimate) + '\n[' + signed(p.ci_low_family63) + '; ' + signed(p.ci_high_family63) + ']'
        assert tables['relative_absolute'].cell(i, 4).text == '[' + signed(a.ci_low) + '; ' + signed(a.ci_high) + ']'
        ci_cells += 2
    render = read(OUT / 'render_manifest.json')
    assert render['status'] == 'passed' and render['slides'] == 44 and not render['overflows']
    for name, digest in render['files'].items():
        assert sha(OUT / name) == digest, name
    for file in OUT.glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)', file.read_text(encoding='utf8')):
            if not target.startswith(('https://', 'http://', '#')):
                assert (OUT / target).exists(), target
    with zipfile.ZipFile(OUT / (STEM + '.pptx')) as archive:
        assert archive.testzip() is None
    result = dict(status='passed', slides=44, main_slides=30, appendix_slides=14,
                  complete_score_rows=72, metric_cells_checked=checked, ci_cells_checked=ci_cells,
                  complete_model_set_in_comparison_tables=True, native_tables_and_notes_verified=True,
                  previous_publication_files_unchanged=preserved, user_files_unchanged=user_files,
                  html_text_overflows=0, native_office_rendered=False, training_performed=False, test2025_read=False)
    (OUT / 'validation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8', newline='\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
