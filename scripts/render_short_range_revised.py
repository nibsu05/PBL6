"""Preview revised shared slide scene in Chromium; native PPTX remains editable."""
from pathlib import Path
import hashlib,json,re,subprocess
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/short_range_revised_2026_10_21'
PRIVATE=ROOT/'data/operational/short_range/revised_preview_2026_10_21'


def main():
    PRIVATE.mkdir(parents=True,exist_ok=True)
    browser=next(p for p in [Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe'),Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')] if p.exists())
    scene=json.loads((OUT/'slide_scene.json').read_text(encoding='utf8'))
    target=OUT/'PBL6_BAO_CAO_DE_HIEU.html';uri=target.as_uri()+'?all=1'
    args=[str(browser),'--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--allow-file-access-from-files',
          '--hide-scrollbars','--virtual-time-budget=3000','--user-data-dir='+str(PRIVATE/'browser_profile')]
    r=subprocess.run(args+['--dump-dom',uri],capture_output=True,timeout=50)
    match=re.search(r'<pre id="layout-status">(.*?)</pre>',r.stdout.decode('utf8',errors='replace'),re.S)
    assert match,'No browser layout status';layout=json.loads(match[1]);print(json.dumps(layout,ensure_ascii=False,indent=2))
    assert layout['checked'] and not layout['overflows'],layout
    full=PRIVATE/'all_slides.png'
    subprocess.run(args+[f'--window-size=1280,{720*len(scene)}','--screenshot='+str(full),uri],capture_output=True,timeout=50,check=True)
    img=Image.open(full);assert img.size==(1280,720*len(scene))
    cols=4;thumb=(400,225);overview=Image.new('RGB',(1600,225*((len(scene)+3)//4)),(226,232,240))
    for index in range(len(scene)):
        tile=img.crop((0,index*720,1280,(index+1)*720));tile.thumbnail(thumb)
        overview.paste(tile,((index%cols)*400,(index//cols)*225))
    overview.save(OUT/'XEM_TRUOC.png',optimize=True)
    def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    record=dict(status='passed',method='HTML shared scene, not native Office rendering',slides=len(scene),overflows=[],
        html_sha256=sha(target),pptx_sha256=sha(OUT/'PBL6_BAO_CAO_DE_HIEU.pptx'),scene_sha256=sha(OUT/'slide_scene.json'),preview_sha256=sha(OUT/'XEM_TRUOC.png'))
    (OUT/'render_manifest.json').write_text(json.dumps(record,indent=2),encoding='utf8',newline='\n')


if __name__=='__main__':main()
