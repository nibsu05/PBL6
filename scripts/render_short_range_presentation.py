"""Render the HTML companion with an installed browser and check text overflow.

This previews the shared slide scene, not a native Office rendering of PPTX.
Large screenshots and browser state stay in ignored operational storage.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess

from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/"reports/short_range_presentation_2026_10_21"
PRIVATE=ROOT/"data/operational/short_range/presentation_preview_2026_10_21"


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    candidates=[shutil.which("google-chrome"),shutil.which("chromium"),shutil.which("msedge"),
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]
    browser=next((str(p) for p in candidates if p and Path(p).exists()),None)
    if not browser:raise RuntimeError("No installed Chromium browser found for optional preview")
    PRIVATE.mkdir(parents=True,exist_ok=True)
    scene=json.loads((REPORT/"slide_scene.json").read_text(encoding="utf8"))
    source=REPORT/"PBL6_TFT_DAY_DU.html"
    uri=source.as_uri()+"?all=1"
    args=[browser,"--headless=new","--disable-gpu","--no-first-run","--no-default-browser-check",
          "--allow-file-access-from-files","--hide-scrollbars","--virtual-time-budget=3000",
          "--user-data-dir="+str(PRIVATE/"browser_profile")]
    result=subprocess.run(args+["--dump-dom",uri],capture_output=True,timeout=50)
    match=re.search(r'<pre id="layout-status">(.*?)</pre>',result.stdout.decode("utf8",errors="replace"),re.S)
    assert match,"Browser did not return layout status"
    layout=json.loads(match[1]);assert layout["checked"] and not layout["overflows"],layout
    full=PRIVATE/"all_slides.png"
    subprocess.run(args+[f"--window-size=1280,{720*len(scene)}","--screenshot="+str(full),uri],
                   capture_output=True,timeout=50,check=True)
    raw=Image.open(full);assert raw.size==(1280,720*len(scene)),raw.size
    cols=4;rows=(len(scene)+cols-1)//cols;tw,th=400,225
    contact=Image.new("RGB",(cols*tw,rows*th),(226,232,240))
    for i in range(len(scene)):
        piece=raw.crop((0,i*720,1280,(i+1)*720));piece.thumbnail((tw,th))
        contact.paste(piece,((i%cols)*tw,(i//cols)*th))
    target=REPORT/"XEM_TRUOC.png";contact.save(target,optimize=True)
    record=dict(status="passed",method="Chromium render of shared HTML slide scene; not native PPTX rendering",
                slides=len(scene),text_overflows=[],html_sha256=sha(source),pptx_sha256=sha(REPORT/"PBL6_TFT_DAY_DU.pptx"),
                scene_sha256=sha(REPORT/"slide_scene.json"),preview_sha256=sha(target),preview_bytes=target.stat().st_size)
    (REPORT/"render_manifest.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf8",newline="\n")
    print(json.dumps(record,indent=2))


if __name__=="__main__":main()
