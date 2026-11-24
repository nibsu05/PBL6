"""Validate displayed cells, evidence, notes, scope and preservation without refitting."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from datetime import datetime,timezone
import json
import re
import zipfile
import numpy as np
import pandas as pd
from pptx import Presentation
from docx import Document
from scripts.short_range_overview_data import PUBLIC,PRIVATE,REFERENCES,sha,write_json
from scripts.build_short_range_overview import readable


def plain(value):
    return re.sub(r'\s+',' ',readable(value).replace('**','')).strip()


def main():
    items=json.loads((PUBLIC/'slide_manifest.json').read_text(encoding='utf-8'))
    deckpath=PUBLIC/'PBL6_BAO_CAO_DAY_DU_DU_BAO_MUA_NGAN_HAN.pptx';deck=Presentation(deckpath)
    if len(items)!=62 or len(deck.slides)!=62 or sum(i['main'] for i in items)!=31:raise ValueError('Wrong talk/appendix count')
    minutes=sum(i['minutes'] for i in items)
    if not 25<=minutes<=30:raise ValueError('Wrong main talk duration')
    tables=0;cells=0;notes=0;bold_cells=0
    for item,slide in zip(items,deck.slides):
        body=plain('\n'.join(s.text for s in slide.shapes if s.has_text_frame))
        if plain(item['title']) not in body:raise ValueError('Missing slide title '+str(item['number']))
        if plain(item['notes']) not in plain(slide.notes_slide.notes_text_frame.text):raise ValueError('Speaker notes missing')
        if len(item['notes'].split())<30:raise ValueError('Explanatory notes too short')
        notes+=1
        if item['kind']=='table':
            actual=[s.table for s in slide.shapes if s.has_table]
            if len(actual)!=1:raise ValueError('Expected exactly one data table')
            t=actual[0];expected=[item['headers']]+item['rows']
            if len(t.rows)!=len(expected):raise ValueError('Wrong table row count')
            for i,row in enumerate(expected):
                for j,value in enumerate(row):
                    if plain(t.cell(i,j).text)!=plain(value):raise ValueError(f'Table differs on slide{item["number"]}/{i}/{j}')
                    if '**' in str(value):
                        if not any(r.font.bold for p in t.cell(i,j).text_frame.paragraphs for r in p.runs):raise ValueError('Important value not bold')
                        bold_cells+=1
                    cells+=1
            tables+=1
        for shape in slide.shapes:
            if shape.left<0 or shape.top<0 or shape.left+shape.width>deck.slide_width+9144 or shape.top+shape.height>deck.slide_height+9144:
                raise ValueError('Shape outside slide '+str(item['number']))
    inputs=json.loads((PUBLIC/'evidence_inputs.json').read_text())
    for rel,digest in inputs['files'].items():
        if sha(ROOT/rel)!=digest:raise ValueError('Evidence changed: '+rel)
    bindings=json.loads((PUBLIC/'numeric_bindings.json').read_text())
    frames={}
    for b in bindings:
        if b['file'] not in frames:frames[b['file']]=pd.read_csv(ROOT/b['file'])
        frame=frames[b['file']];mask=pd.Series(True,index=frame.index)
        for k,v in b['filters'].items():mask &= frame[k].eq(v)
        values=frame.loc[mask,b['column']]
        if len(values)!=1 or not np.isclose(float(values.iloc[0]),float(b['numeric_value']),equal_nan=True):raise ValueError('Numeric binding changed')
        expected=f"{float(values.iloc[0]):.{b['digits']}f}".replace('.',',')
        if b['display']!=expected:raise ValueError('Displayed rounding differs')
    # Scientific statements used in the main narrative.
    w=pd.read_csv(ROOT/'reports/gfs_training_window_2026_11_18/paired_comparisons.csv')
    modern=w[w.evaluation_set.eq('retrospective2026_modern')]
    good=modern[modern.family.eq('factorial')&modern.supported_exploratory_improvement]
    if len(good)!=1 or good.iloc[0]['first']!='D' or good.iloc[0].reference!='C' or good.iloc[0].horizon!=3:
        raise ValueError('Summary1/12 no longer matches evidence')
    if modern[modern.family.eq('ablation')].supported_exploratory_improvement.sum()!=0:raise ValueError('Ablation summary differs')
    t=pd.read_csv(ROOT/'reports/gfs_temporal_2026_11_17/paired_comparisons.csv')
    # The source table also reports other scopes: only the2025 primary family is cited.
    primary=t[t.evaluation_set.eq('retrospective2025_legacy')&t.primary&t.metric.eq('mean_rmse')]
    if len(primary)!=12 or primary.adjusted_exploratory_signal.sum()!=0:raise ValueError('Temporal0/12 summary differs')
    protected=json.loads((PRIVATE/'protected_before.json').read_text())
    for rel,digest in protected.items():
        if sha(ROOT/rel)!=digest:raise ValueError('Old evidence/user presentation changed: '+rel)
    if (ROOT/'reports/short_range_three_models_2026_10_21/PBL6_SO_SANH_3_MO_HINH.pptx').exists():raise ValueError('User-deleted slide restored')
    doc=Document(PUBLIC/'THUYET_MINH_SLIDE.docx')
    headings=[p for p in doc.paragraphs if p.style.name=='Heading 1']
    if len(headings)!=62:raise ValueError('Incomplete Word explanation')
    with zipfile.ZipFile(deckpath) as archive:
        if archive.testzip() is not None:raise ValueError('PPTX container invalid')
    public_forbidden=[]
    for p in PUBLIC.iterdir():
        if p.suffix.lower() in ('.pdf','.parquet','.npz','.zip','.pt','.joblib','.dpapi'):public_forbidden.append(p.name)
    if public_forbidden:raise ValueError('Private artifact in public folder')
    required={'P1','P2','P3','P4','D1','D2','D3','P5','P6'}
    if set(REFERENCES)!=required:raise ValueError('Incomplete references')
    report=dict(status='passed',verified_utc=datetime.now(timezone.utc).isoformat(),slides=len(items),main_slides=31,
        appendix_slides=31,talk_minutes=round(minutes,1),speaker_notes_checked=notes,tables_checked=tables,
        displayed_cells_checked=cells,bold_cells_checked=bold_cells,numeric_bindings_checked=len(bindings),
        evidence_files_sha_checked=len(inputs['files']),old_files_preserved=len(protected),word_sections=62,
        scientific_scope_checks=True,models_refit=False,private_payload_absent=True,pptx_sha256=sha(deckpath))
    write_json(PUBLIC/'content_verification.json',report);print(report,flush=True)


if __name__=='__main__':main()
