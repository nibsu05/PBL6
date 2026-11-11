"""Check published slide values against source CSVs and both slide renderers.

No model fitting and no 2025 observations. Native PowerPoint rendering must have
been run first. All row-level data remain outside this validation report.
"""
from pathlib import Path
import hashlib
import html
import json
import math
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont
import pandas as pd
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/gfs_station_slides_2026_11_10'
DATA = ROOT / 'reports/gfs_station_57_2026_11_10'
PRIVATE = ROOT / 'data/operational/gfs_station_slides_2026_11_10'
STEM = 'PBL6_DU_BAO_MUA_57_TRAM'
LABELS = {'CLIM': 'Khí hậu', 'PERSISTENCE': 'Persistence', 'GFS': 'GFS gốc',
          'A0': 'LightGBM A0', 'A1': 'LightGBM A1', 'A2': 'LightGBM A2',
          'A3': 'LightGBM A3', 'GRU_A2': 'GRU A2'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def formatted(value, digits=2, signed=False):
    return format(float(value), ('+' if signed else '') + f'.{digits}f').replace('.', ',')


def main():
    manifest = json.loads((OUT / 'build_manifest.json').read_text(encoding='utf-8'))
    scene = json.loads((OUT / 'slide_scene.json').read_text(encoding='utf-8'))
    prs = Presentation(OUT / (STEM + '.pptx'))
    tables = manifest['metric_tables']
    numeric_cells = 0
    assert len(scene) == len(prs.slides) == manifest['slides'] == 55
    assert manifest['main_slides'] == 43 and manifest['appendix_slides'] == 12
    assert manifest['station_count'] == 57
    assert not manifest['training_performed_for_slides'] and not manifest['test2025_read']
    assert sha(ROOT / 'scripts/build_gfs_station_slides.py') == manifest['code_sha256']
    assert sha(ROOT / 'scripts/gfs_station_slide_notes.py') == manifest['notes_sha256']
    for path, expected in manifest['sources'].items():
        assert sha(ROOT / path) == expected, f'Source changed: {path}'
    for path, expected in manifest['files'].items():
        assert sha(OUT / path) == expected['sha256'], f'Built file changed: {path}'

    # Check editable PPTX contents and styles, rather than just trusting its ZIP.
    for native, slide in zip(prs.slides, scene):
        assert native.notes_slide.notes_text_frame.text == slide['note']
        assert len(slide['note'].split()) >= 75
        assert '\ufffd' not in slide['note'] and 'Đâylà' not in slide['note']
        assert len(native.shapes) == len(slide['shapes'])
        assert '2025 giữ kín' in slide['source']
        for shape, spec in zip(native.shapes, slide['shapes']):
            assert spec['x'] >= 0 and spec['y'] >= 0
            assert spec['x'] + spec['w'] <= 13.334
            assert spec['y'] + spec['h'] <= 7.5
            if spec['kind'] == 'table':
                for row_no, row in enumerate([spec['headers']] + spec['rows']):
                    for col_no, text in enumerate(row):
                        cell = shape.table.cell(row_no, col_no)
                        assert cell.text == str(text)
                        style = spec['styles'].get(f'{row_no},{col_no}', {})
                        for para in cell.text_frame.paragraphs:
                            for run in para.runs:
                                assert run.font.bold == (row_no == 0 or style.get('bold', False))
                                assert run.font.size.pt == spec['size']
            elif spec['kind'] == 'text':
                assert shape.text == spec['text'].replace('**', '')
        foreground = [s for s in slide['shapes'] if s['kind'] != 'rect']
        for i, a in enumerate(foreground):
            for b in foreground[:i]:
                dx = min(a['x'] + a['w'], b['x'] + b['w']) - max(a['x'], b['x'])
                dy = min(a['y'] + a['h'], b['y'] + b['h']) - max(a['y'], b['y'])
                assert dx <= .03 or dy <= .03, f'Foreground overlap slide {slide["number"]}'

    point = pd.read_csv(DATA / 'point_metrics.csv').query("fold == 'dev'")
    probability = pd.read_csv(DATA / 'probability_metrics.csv').query("fold == 'dev'")
    event = pd.read_csv(DATA / 'event_metrics.csv').query("fold == 'dev'")
    label_to_model = {value: key for key, value in LABELS.items()}

    # Independently select original CSV rows and verify every displayed metric.
    def matrix(tag, source, key, digits=2, threshold=None):
        nonlocal numeric_cells
        for row in tables[tag]['rows']:
            model = label_to_model[row[0]]
            subset = source[source.model.eq(model)]
            if threshold is not None:
                subset = subset[subset.threshold_mm.eq(threshold)]
            for h in range(1, 4):
                raw = subset[subset.horizon.eq(h)].iloc[0][key]
                assert row[h] == formatted(raw, digits), (tag, model, h)
                numeric_cells += 1

    matrix('result_mae', point, 'macro_mae')
    matrix('full_rmse', point, 'macro_rmse')
    matrix('full_bias', point, 'macro_bias')
    for threshold in (1, 50):
        matrix(f'bss_{threshold}', probability, 'macro_bss', 3, threshold)
        for key in ('bs', 'bss'):
            matrix(f'full_{key}_{threshold}', probability, 'macro_' + key, 3, threshold)
    for row in tables['point_tradeoffs']['rows']:
        h = int(row[0]); model = label_to_model[row[1]]
        raw = point[point.horizon.eq(h) & point.model.eq(model)].iloc[0]
        for j, metric in enumerate(('macro_mae', 'macro_rmse', 'macro_bias'), 2):
            assert row[j] == formatted(raw[metric], 2, signed=(metric == 'macro_bias'))
            numeric_cells += 1
    for tag, threshold in [('event_wet', 1), ('event_heavy', 50)]:
        for row in tables[tag]['rows']:
            h = int(row[0]); model = label_to_model[row[1]]
            raw = event[event.horizon.eq(h) & event.model.eq(model) & event.threshold_mm.eq(threshold)].iloc[0]
            for j, metric in enumerate(('macro_csi', 'macro_pod', 'macro_far'), 2):
                assert row[j] == formatted(raw[metric], 3)
                numeric_cells += 1
            if threshold == 50:
                assert row[5] == f'{int(raw.stations_with_pod)}/{int(raw.stations_with_far)}'

    ci = pd.read_csv(DATA / 'paired_bootstrap.csv').query("fold == 'dev'")
    def check_ci(row, model, reference, h, delta_col, interval_col):
        nonlocal numeric_cells
        raw = ci[ci.model.eq(model) & ci.reference.eq(reference) & ci.horizon.eq(h)].iloc[0]
        assert row[delta_col] == formatted(raw.mae_difference, 3, signed=(delta_col == 2))
        interval = '[' + formatted(raw.ci95_low, 3, True) + '; ' + formatted(raw.ci95_high, 3, True) + ']'
        assert row[interval_col] == interval
        numeric_cells += 3
    for row in tables['a2_gfs_ci']['rows']:
        check_ci(row, 'A2', 'GFS', int(row[0][-1]), 1, 2)
    for group_no, (model, reference) in enumerate([('A1', 'A0'), ('A2', 'A1'), ('A3', 'A2')]):
        for h in range(1, 4):
            check_ci(tables['feature_addition_ci']['rows'][group_no * 3 + h - 1], model, reference, h, 2, 3)
    fit = pd.read_csv(DATA / 'fit_diagnostics.csv')
    for h, row in enumerate(tables['lgb_best_iterations']['rows'], 1):
        for j, seed in enumerate((17, 29, 43), 1):
            raw = fit[fit.config.eq('A2') & fit.horizon.eq(h) & fit.seed.eq(seed)].iloc[0]
            assert row[j] == str(int(raw.best_iteration))
            numeric_cells += 1
    audit = json.loads((DATA / 'dataset_audit.json').read_text())
    for row, fold in zip(tables['sample_counts']['rows'], ('train', 'cal', 'dev')):
        assert int(row[1].replace('.', '')) * 3 == audit['split_rows'][fold]
        assert int(row[2].replace('.', '')) == audit['split_rows'][fold]
        assert int(row[3]) == audit['split_issues'][fold]
    assert audit['features'] == {'A0': 6, 'A1': 16, 'A2': 25, 'A3': 32}
    for feature_set in ('A0', 'A1', 'A2', 'A3'):
        assert len(audit['feature_names'][feature_set]) == audit['features'][feature_set]

    # Check the protected presentations by their original user-file snapshots.
    protected = json.loads((ROOT / 'data/operational/workspace_cleanup_2026_11_09/user_files.json').read_text(encoding='utf-8'))
    for item in protected:
        assert sha(ROOT / item['path']) == item['sha256'], 'Protected user file changed'
    assert not (ROOT / 'reports/short_range_three_models_2026_10_21/PBL6_SO_SANH_3_MO_HINH.pptx').exists()
    assert not list(OUT.glob('*.pdf')), 'Public PDF not allowed by repository rules'
    render = json.loads((OUT / 'native_render_audit.json').read_text(encoding='utf-8-sig'))
    assert render['pptx_sha256'] == sha(OUT / (STEM + '.pptx'))
    assert render['slide_count'] == 55 and not render['overflows']
    assert render['pdf_exported']
    pdf = PRIVATE / (STEM + '.pdf')
    assert pdf.read_bytes().startswith(b'%PDF-') and pdf.stat().st_size > 100_000

    chrome = Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
    cmd = [str(chrome), '--headless', '--disable-gpu', '--no-first-run',
           '--no-default-browser-check', '--allow-file-access-from-files',
           '--user-data-dir=' + str(PRIVATE / 'chrome_layout_profile'),
           '--virtual-time-budget=3000', '--dump-dom', (OUT / (STEM + '.html')).as_uri() + '?all=1']
    result = subprocess.run(cmd, capture_output=True, timeout=60, creationflags=0x08000000)
    assert result.returncode == 0
    dom = result.stdout.decode('utf-8')
    (PRIVATE / 'rendered_dom.html').write_text(dom, encoding='utf-8')
    match = re.search(r'<pre id="layout-status">(.*?)</pre>', dom, re.S)
    assert match, 'Browser layout audit did not run'
    browser = json.loads(html.unescape(match.group(1)))
    assert browser['checked'] and not browser['overflows'], browser

    # Contact sheets contain actual native slide exports, not browser approximations.
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 17)
    preview_files = []
    for sheet_no, start in enumerate(range(1, 56, 20), 1):
        numbers = list(range(start, min(start + 20, 56)))
        canvas = Image.new('RGB', (1680, math.ceil(len(numbers) / 4) * 257), '#DFE7EF')
        draw = ImageDraw.Draw(canvas)
        for i, number in enumerate(numbers):
            image = Image.open(PRIVATE / 'native_png' / f'slide_{number:02d}.png').convert('RGB')
            assert image.size == (1600, 900)
            image = image.resize((400, 225), Image.Resampling.LANCZOS)
            x = (i % 4) * 420 + 10; y = (i // 4) * 257 + 25
            canvas.paste(image, (x, y))
            draw.text((x, y - 22), f'Slide {number:02d}', font=font, fill='#123047')
        name = f'XEM_TRUOC_{sheet_no:02d}.png'
        canvas.save(OUT / name)
        preview_files.append(name)
    report = dict(status='passed', slides=55, main_slides=43, appendix_slides=12,
                  csv_numeric_cells_checked=numeric_cells, source_hashes_checked=len(manifest['sources']),
                  editable_pptx_and_notes_checked=True, foreground_geometry_checked=True,
                  native_powerpoint_text_boxes=render['text_boxes_checked'], native_overflows=[],
                  browser_layout=browser, protected_user_files_unchanged=True,
                  training_performed=False, test2025_read=False,
                  pdf_private_sha256=sha(pdf), previews=preview_files)
    (OUT / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
