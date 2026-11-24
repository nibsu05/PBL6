"""Package the beginner report only after evidence and native rendering pass."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import json
import zipfile
from datetime import datetime,timezone
from pypdf import PdfReader
from scripts.build_short_range_explained_v2 import PUBLIC,PRIVATE,NAME
from scripts.short_range_overview_data import sha,write_json
from scripts.validate_short_range_explained_v2 import main as validate


def main():
    validate()
    pptx=PUBLIC/'PBL6_NGAN_HAN_GIAI_THICH_DE_HIEU.pptx'
    audit=json.loads((PUBLIC/'slide_render_verification.json').read_text(encoding='utf-8'))
    content=json.loads((PUBLIC/'content_verification.json').read_text(encoding='utf-8'))
    assert audit['status']=='passed' and audit['overflows']==[] and audit['slides']==content['slides']
    assert audit['pptx_sha256']==sha(pptx)
    pdf=PRIVATE/'native_render/report.pdf'
    reader=PdfReader(pdf);assert len(reader.pages)==content['slides']
    text='\n'.join(p.extract_text() for p in reader.pages[:content['main_slides']])
    for token in ('15,68','23,3%','275','325','123','494','Tweedie','L2'):
        assert token in text,token
    payload=[pptx,PUBLIC/'GIAI_THICH_TU_DAU.docx',PUBLIC/'GIAI_THICH_TU_DAU.md',PUBLIC/'NGUON_TAI_LIEU.md',PUBLIC/'README.md',pdf]
    archive=PRIVATE/'PBL6_BAO_CAO_DE_HIEU.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in payload:z.write(p,'PBL6_NGAN_HAN_DE_HIEU.pdf' if p==pdf else p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None and len(z.namelist())==len(payload)
    files={p.relative_to(ROOT).as_posix():sha(p) for p in PUBLIC.rglob('*') if p.is_file() and p.name!='release.json'}
    code={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in [ROOT/'scripts/build_short_range_explained_v2.py',ROOT/'scripts/validate_short_range_explained_v2.py',ROOT/'scripts/finalize_short_range_explained_v2.py',ROOT/'scripts/render_short_range_explained_v2.ps1']}
    write_json(PUBLIC/'release.json',dict(status='complete',created_utc=datetime.now(timezone.utc).isoformat(),
       slides=content['slides'],main_slides=content['main_slides'],appendix_slides=content['appendix_slides'],
       talk_minutes=content['talk_minutes'],models_refit=False,files=files,code=code,
       private_pdf_sha256=sha(pdf),private_package_sha256=sha(archive),package_members=len(payload)))
    print(json.dumps(dict(status='complete',slides=content['slides'],zip_bytes=archive.stat().st_size)))


if __name__=='__main__':main()
