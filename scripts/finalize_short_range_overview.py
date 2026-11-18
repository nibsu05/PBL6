"""Package the verified report; retain PDF outside the public repository."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from datetime import datetime,timezone
import json
import subprocess
import zipfile
from pypdf import PdfReader
from scripts.short_range_overview_data import PUBLIC,PRIVATE,sha,write_json


def main():
    result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/validate_short_range_overview.py')],cwd=ROOT)
    if result.returncode:raise ValueError('Presentation content validation failed')
    render=json.loads((PUBLIC/'slide_render_verification.json').read_text())
    pptx=PUBLIC/'PBL6_BAO_CAO_DAY_DU_DU_BAO_MUA_NGAN_HAN.pptx'
    if render['status']!='passed' or render['pptx_sha256']!=sha(pptx):raise ValueError('Latest deck not verified by native PowerPoint')
    pdf=PRIVATE/'native_render/report.pdf';reader=PdfReader(pdf)
    if len(reader.pages)!=62:raise ValueError('Incomplete PDF')
    pdf_text=reader.pages[19].extract_text().replace(' ','')
    if not all(value in pdf_text for value in ['2025','26,035','30,233']):raise ValueError('Native PDF does not match the results slide')
    bundle=PRIVATE/'PBL6_BAO_CAO_NGAN_HAN_DAY_DU.zip'
    names=['PBL6_BAO_CAO_DAY_DU_DU_BAO_MUA_NGAN_HAN.pptx','THUYET_MINH_SLIDE.docx',
        'BAN_DOC_OFFLINE.html','GHI_CHU_THUYET_TRINH.md','NGUON_TAI_LIEU.md','README.md']
    with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in names:archive.write(PUBLIC/name,name)
        archive.write(pdf,'PBL6_BAO_CAO_DAY_DU_DU_BAO_MUA_NGAN_HAN.pdf')
    with zipfile.ZipFile(bundle) as archive:
        if archive.testzip() is not None or len(archive.namelist())!=7:raise ValueError('Report bundle invalid')
    code=['scripts/short_range_overview_data.py','scripts/short_range_overview_content.py',
        'scripts/short_range_overview_notes.py','scripts/build_short_range_overview.py',
        'scripts/validate_short_range_overview.py','scripts/render_short_range_overview.ps1',
        'scripts/finalize_short_range_overview.py']
    release=dict(status='complete',published_utc=datetime.now(timezone.utc).isoformat(),
        slides=62,main_slides=31,appendix_slides=31,planned_talk_minutes=28.3,
        native_render='Microsoft PowerPoint;no text overflow',pdf_pages=62,
        content_verification_sha256=sha(PUBLIC/'content_verification.json'),
        code={rel:sha(ROOT/rel) for rel in code},
        files={p.name:sha(p) for p in PUBLIC.iterdir() if p.is_file() and p.name!='release.json' and not p.name.startswith('~$')},
        private_pdf=dict(path=str(pdf.relative_to(ROOT)).replace('\\','/'),sha256=sha(pdf)),
        report_bundle=dict(path=str(bundle.relative_to(ROOT)).replace('\\','/'),sha256=sha(bundle),bytes=bundle.stat().st_size,files=7),
        models_trained=False,old_studies_modified=False)
    write_json(PUBLIC/'release.json',release)
    print(dict(status='complete',slides=62,main=31,appendix=31,pdf_pages=62,bundle_MB=round(bundle.stat().st_size/1e6,2)),flush=True)


if __name__=='__main__':main()
