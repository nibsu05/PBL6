"""Render shared HTML scene and check overflow; this is not native Office rendering."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/short_range_three_models_2026_10_21'
PRIVATE = ROOT / 'data/operational/short_range/three_models_preview_2026_10_21'
STEM = 'PBL6_SO_SANH_3_MO_HINH'


def main():
    PRIVATE.mkdir(parents=True, exist_ok=True)
    browser = next(p for p in [Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe'),
                              Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')] if p.exists())
    scene = json.loads((OUT / 'slide_scene.json').read_text(encoding='utf8'))
    manifest = json.loads((OUT / 'build_manifest.json').read_text(encoding='utf8'))
    uri = (OUT / (STEM + '.html')).as_uri() + '?all=1'
    args = [str(browser), '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
            '--allow-file-access-from-files', '--hide-scrollbars', '--virtual-time-budget=3000',
            '--user-data-dir=' + str(PRIVATE / 'browser_profile')]
    result = subprocess.run(args + ['--dump-dom', uri], capture_output=True, timeout=50, check=True)
    match = re.search(r'<pre id="layout-status">(.*?)</pre>', result.stdout.decode('utf8', errors='replace'), re.S)
    assert match, 'No browser layout status'
    layout = json.loads(match[1])
    print(json.dumps(layout, ensure_ascii=False, indent=2))
    assert layout['checked'] and not layout['overflows'], layout
    full = PRIVATE / 'all_slides.png'
    subprocess.run(args + [f'--window-size=1280,{720 * len(scene)}', '--screenshot=' + str(full), uri],
                   capture_output=True, timeout=50, check=True)
    img = Image.open(full)
    assert img.size == (1280, 720 * len(scene))
    overview = Image.new('RGB', (1600, 225 * ((len(scene) + 3) // 4)), (226, 232, 240))
    for i in range(len(scene)):
        tile = img.crop((0, i * 720, 1280, (i + 1) * 720))
        if i + 1 in manifest['roles'].values(): tile.save(PRIVATE / f'slide_{i+1:02d}.png')
        tile.thumbnail((400, 225))
        overview.paste(tile, ((i % 4) * 400, (i // 4) * 225))
    overview.save(OUT / 'XEM_TRUOC.png', optimize=True)
    def sha(name): return hashlib.sha256((OUT / name).read_bytes()).hexdigest()
    record = dict(status='passed', method='HTML shared scene, not native Office rendering', slides=len(scene),
                  overflows=[], files={name: sha(name) for name in [STEM+'.html', STEM+'.pptx', 'slide_scene.json', 'XEM_TRUOC.png']})
    (OUT / 'render_manifest.json').write_text(json.dumps(record, indent=2), encoding='utf8', newline='\n')


if __name__ == '__main__': main()
