"""Validate final artifacts, report links and editable slide layout; preview locally."""
from pathlib import Path
from io import BytesIO
import json
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from PIL import Image,ImageDraw,ImageFont
from pptx import Presentation
from docx import Document
from src.short_range_dataset import file_hash

REPORT=ROOT/'reports/short_range_ablation_2026_10_21'
PRIVATE=ROOT/'data/operational/short_range/ablation_2026_10_21'


def previews(prs):
    directory=PRIVATE/'slide_preview';directory.mkdir(exist_ok=True)
    width,height=960,540;scale=width/prs.slide_width;overflow=[];images=[]
    for number,slide in enumerate(prs.slides,1):
        canvas=Image.new('RGB',(width,height),'#f8fafc');draw=ImageDraw.Draw(canvas)
        for shape in slide.shapes:
            x,y,w,h=[int(round(v*scale)) for v in [shape.left,shape.top,shape.width,shape.height]]
            if shape.shape_type==13:
                picture=Image.open(BytesIO(shape.image.blob)).convert('RGB').resize((w,h),Image.Resampling.LANCZOS)
                canvas.paste(picture,(x,y))
            elif shape.has_text_frame:
                cursor=y
                for p in shape.text_frame.paragraphs:
                    size=p.font.size.pt if p.font.size else 20
                    font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf' if p.font.bold else 'C:/Windows/Fonts/arial.ttf',max(1,int(round(size))))
                    line='';lines=[]
                    for word in p.text.split():
                        candidate=(line+' '+word).strip()
                        if line and draw.textlength(candidate,font=font)>w:
                            lines.append(line);line=word
                        else:line=candidate
                    lines.append(line)
                    color='#123047'
                    try:
                        if p.font.color.rgb:color='#'+str(p.font.color.rgb)
                    except (AttributeError,TypeError):pass
                    for line in lines:
                        draw.text((x,cursor),line,font=font,fill=color)
                        cursor+=int(round(size*1.16))
                    cursor+=int(round(p.space_after.pt)) if p.space_after else 0
                if cursor>y+h+8:overflow.append(dict(slide=number,text=shape.text[:80],extra_pixels=cursor-y-h))
        path=directory/f'slide_{number:02}.png';canvas.save(path);images.append(canvas)
    sheet=Image.new('RGB',(960*2,540*int(np.ceil(len(images)/2))),'white')
    for i,img in enumerate(images):sheet.paste(img,((i%2)*960,(i//2)*540))
    sheet.save(directory/'contact_sheet.png')
    return overflow


def main():
    build=json.loads((REPORT/'build_manifest.json').read_text(encoding='utf-8'))
    for name,record in build['files'].items():
        assert (REPORT/name).stat().st_size==record['bytes'],name
        assert file_hash(REPORT/name)==record['sha256'],name
    # Also ensure extension has not altered the original pilot artifacts/code.
    original=ROOT/'reports/short_range_pilot_2026_10_21'
    prior=json.loads((original/'run.json').read_text(encoding='utf-8'))
    for name,expected in prior['worktree_code_sha256'].items():assert file_hash(ROOT/name)==expected,name
    old_build=json.loads((original/'build_manifest.json').read_text(encoding='utf-8'))
    # The pilot build schema stores either a mapping or a list of records.
    old_files=old_build.get('files',{})
    if isinstance(old_files,dict):
        for name,record in old_files.items():
            expected=record['sha256'] if isinstance(record,dict) else record
            assert file_hash(original/name)==expected,name
    broken=[]
    for name in ['README.md','BAO_CAO_MO_RONG.md']:
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',(REPORT/name).read_text(encoding='utf-8')):
            if '://' not in target and not (REPORT/target.split('#')[0]).exists():broken.append(target)
    assert not broken,broken
    pred=pd.read_parquet(PRIVATE/'predictions_ensemble.parquet')
    seed=pd.read_parquet(PRIVATE/'predictions_seed.parquet')
    assert len(pred)==58050 and len(seed)==109650
    assert pred.groupby(['model','experiment','year','lead_day']).size().min()>0
    assert not pred.duplicated(['model','experiment','issue','lead_day']).any()
    assert np.isfinite(pred[['obs','amount','p16','p50','p100']]).all().all()
    assert pred.issue.max().year==2023 and pred.amount.min()>=0
    assert (pred.p16>=pred.p50-1e-12).all() and (pred.p50>=pred.p100-1e-12).all()
    assert pred[['p16','p50','p100']].min().min()>=0 and pred[['p16','p50','p100']].max().max()<=1
    ci=pd.read_csv(REPORT/'paired_bootstrap.csv')
    assert len(ci)==252 and ci.primary_family.sum()==18
    assert (ci.replicates==20000).all() and set(ci.block_days)=={7,14}
    test_summary=PRIVATE/'tests_summary.json'
    if not test_summary.exists():
        import unittest
        suite=unittest.defaultTestLoader.loadTestsFromNames(['tests.test_short_range','tests.test_short_range_ablation','tests.test_verification'])
        result=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
        tests=dict(status='passed' if result.wasSuccessful() else 'failed',tests=result.testsRun,
            failures=len(result.failures),errors=len(result.errors))
        test_summary.write_text(json.dumps(tests),encoding='utf-8')
    else:
        tests=json.loads(test_summary.read_text())
    assert tests['status']=='passed' and tests['tests']==27
    document=Document(REPORT/'BAO_CAO_MO_RONG.docx')
    assert len(document.inline_shapes)==4 and len(document.tables)>=8
    deck=Presentation(REPORT/'PBL6_TFT_24_72h_mo_rong_2026_10_21.pptx')
    assert len(deck.slides)==8
    for number,slide in enumerate(deck.slides,1):
        assert slide.notes_slide.notes_text_frame.text.strip()
        for shape in slide.shapes:
            assert shape.left>=0 and shape.top>=0
            assert shape.left+shape.width<=deck.slide_width+10 and shape.top+shape.height<=deck.slide_height+10,number
    overflow=previews(deck)
    result=dict(status='passed',tests=tests,public_artifacts=len(build['files']),
        private_seed_rows=len(seed),private_ensemble_rows=len(pred),bootstrap_rows=len(ci),
        bootstrap_repeats=20000,slides=8,word_tables=len(document.tables),broken_links=[],
        original_pilot_code_unchanged=True,original_pilot_artifacts_unchanged=True,
        approximate_slide_text_overflow=overflow,test2025_read=False,
        preview='slide_preview/contact_sheet.png',validation_code_sha256=file_hash(Path(__file__)))
    (PRIVATE/'final_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8',newline='\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
