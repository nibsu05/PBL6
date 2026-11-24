"""Check presentation against its frozen inputs, worked examples and native render."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import json
import re
import zipfile
import math
import numpy as np
import pandas as pd
from pptx import Presentation
from docx import Document
from scripts.build_short_range_explained_v2 import PUBLIC, PRIVATE, NAME
from scripts.short_range_overview_data import sha, write_json
from scripts.build_short_range_overview import readable


def plain(value):
    return re.sub(r'\s+',' ',readable(value).replace('**','')).strip()


def main():
    items=json.loads((PUBLIC/'slide_manifest.json').read_text(encoding='utf-8'))
    path=PUBLIC/'PBL6_NGAN_HAN_GIAI_THICH_DE_HIEU.pptx'
    deck=Presentation(path);nmain=sum(x['main'] for x in items)
    assert len(items)==len(deck.slides) and 30<=nmain<=35
    assert 25<=sum(x['minutes'] for x in items)<=30
    counts=dict(tables=0,cells=0,bold_cells=0,notes=0)
    for item,slide in zip(items,deck.slides):
        assert plain(item['title']) in plain('\n'.join(z.text for z in slide.shapes if z.has_text_frame))
        assert plain(item['notes']) in plain(slide.notes_slide.notes_text_frame.text)
        assert len(item['notes'].split())>=30, item['number']
        counts['notes']+=1
        for z in slide.shapes:
            assert z.left>=0 and z.top>=0 and z.left+z.width<=deck.slide_width+9144 and z.top+z.height<=deck.slide_height+9144
        if item['kind']=='table':
            actual=[z.table for z in slide.shapes if z.has_table]
            assert len(actual)==1
            t=actual[0];expected=[item['headers']]+item['rows']
            assert len(t.rows)==len(expected)
            for i,row in enumerate(expected):
                for j,value in enumerate(row):
                    assert plain(t.cell(i,j).text)==plain(value),(item['number'],i,j)
                    if '**' in str(value):
                        assert any(r.font.bold for p in t.cell(i,j).text_frame.paragraphs for r in p.runs)
                        counts['bold_cells']+=1
                    counts['cells']+=1
            counts['tables']+=1
    inputs=json.loads((PUBLIC/'evidence_inputs.json').read_text(encoding='utf-8'))
    for rel,digest in inputs['files'].items():assert sha(ROOT/rel)==digest, rel
    frames={}
    bindings=json.loads((PUBLIC/'numeric_bindings.json').read_text(encoding='utf-8'))
    for b in bindings:
        if b['file'] not in frames:frames[b['file']]=pd.read_csv(ROOT/b['file'])
        frame=frames[b['file']];mask=pd.Series(True,index=frame.index)
        for k,v in b['filters'].items():mask &= frame[k].eq(v)
        found=frame.loc[mask,b['column']]
        assert len(found)==1 and np.isclose(float(found.iloc[0]),float(b['numeric_value']),equal_nan=True)
        assert b['display']==f"{float(found.iloc[0]):.{b['digits']}f}".replace('.',',')
    derived=json.loads((PUBLIC/'derived_bindings.json').read_text(encoding='utf-8'))
    for b in derived:
        assert b['operation']=='100*numerator/denominator'
        assert np.isclose(b['value'],100*b['numerator']/b['denominator'])
        assert b['display']==f"{b['value']:.{b['digits']}f}".replace('.',',')+'%'
    # Worked, explicitly hypothetical example must remain arithmetically correct.
    obs=np.array([0,10,30]);pred=np.array([2,7,20]);error=pred-obs
    assert np.isclose(np.abs(error).mean(),5)
    assert np.isclose(np.sqrt((error**2).mean()),math.sqrt(113/3))
    assert np.isclose(error.mean(),-11/3)
    # Verify the event denominators, not just copied percentages.
    events=pd.read_csv(ROOT/'reports/gfs_training_window_2026_11_18/event_metrics.csv')
    rows=events[events.evaluation_set.eq('retrospective2026_modern') & events.model.eq('B') & events.threshold_mm.eq(50) & events.decision_rule.eq('calibration_selected')]
    assert len(rows)==3
    for _,r in rows.iterrows():
        assert r.events==r.hits+r.misses
        assert np.isclose(r.micro_pod,r.hits/(r.hits+r.misses))
        assert np.isclose(r.micro_far,r.false_alarms/(r.hits+r.false_alarms))
    # Summary statements cannot silently gain statistical support.
    comparisons=pd.read_csv(ROOT/'reports/gfs_training_window_2026_11_18/paired_comparisons.csv')
    current=comparisons[comparisons.evaluation_set.eq('retrospective2026_modern')]
    supported=current[current.family.eq('factorial') & current.supported_exploratory_improvement]
    assert len(supported)==1 and supported.iloc[0]['first']=='D' and supported.iloc[0].reference=='C' and supported.iloc[0].horizon==3
    assert not current[current.family.eq('ablation')].supported_exploratory_improvement.any()
    old=json.loads((PRIVATE/'protected_before.json').read_text(encoding='utf-8'))
    for rel,digest in old.items():assert sha(ROOT/rel)==digest,rel
    assert not (ROOT/'reports/short_range_three_models_2026_10_21/PBL6_SO_SANH_3_MO_HINH.pptx').exists()
    doc=Document(PUBLIC/'GIAI_THICH_TU_DAU.docx')
    assert len([p for p in doc.paragraphs if p.style.name=='Heading 1'])==len(items)
    with zipfile.ZipFile(path) as z:assert z.testzip() is None
    forbidden={'.pdf','.parquet','.zip','.npz','.pt','.joblib','.dpapi'}
    assert not [p for p in PUBLIC.rglob('*') if p.suffix.lower() in forbidden]
    result=dict(status='passed',slides=len(items),main_slides=nmain,appendix_slides=len(items)-nmain,
                talk_minutes=round(sum(x['minutes'] for x in items),1),numeric_bindings=len(bindings),
                derived_percentages=len(derived),event_denominators_checked=3,worked_example_checked=True,
                evidence_hashes=len(inputs['files']),protected_files=len(old),models_refit=False,
                metrics_rescored=False,pptx_sha256=sha(path),**counts)
    write_json(PUBLIC/'content_verification.json',result)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
