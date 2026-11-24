"""Check publication hashes, all table cells and three-model comparison scope."""
from pathlib import Path
import hashlib
import json
import re
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from docx import Document
from openpyxl import load_workbook
from scripts.run_daily_gauge_matrix import REPORT,PRIVATE,sha,MODELS

METRICS=['RMSE','MAE','bias','BS','BSS','CSI','POD','FAR']
LABELS=['LightGBM','TFT','Informer']


def main():
    pub=json.loads((REPORT/'publication_manifest.json').read_text(encoding='utf8'))
    for name,info in pub['files'].items():assert sha(REPORT/name)==info['sha256'],name
    for name,digest in pub['code_hashes'].items():assert sha(ROOT/name)==digest,name
    val=json.loads((REPORT/'validation.json').read_text(encoding='utf8'))
    assert val['status']=='passed' and val['models_replayed']==168 and val['neural_checkpoints_replayed']==144
    run=json.loads((REPORT/'run.json').read_text(encoding='utf8'))
    assert {m:sum(x['model']==m for x in run['models']) for m in MODELS}=={'lgbm':24,'tft':72,'informer':72}
    main=pd.read_csv(REPORT/'scores_main_72.csv');assert len(main)==72 and main[METRICS].notna().all().all()
    assert not main.duplicated(['model','experiment','lead_day']).any()
    pooled=pd.read_csv(REPORT/'scores_pooled.csv')
    pd.testing.assert_frame_equal(main,pooled[(pooled.season=='all')&(pooled.threshold_mm==16)].reset_index(drop=True),check_dtype=False)
    display=pd.read_csv(REPORT/'KET_QUA_72.csv')
    keys=['experiment','lead_day','model']
    pd.testing.assert_frame_equal(display.sort_values(keys).reset_index(drop=True),main.sort_values(keys).reset_index(drop=True),check_dtype=False)
    for _,group in display.groupby(['experiment','lead_day'],sort=False):assert group.model.tolist()==MODELS
    ci=pd.read_csv(REPORT/'paired_bootstrap.csv');absolute=pd.read_csv(REPORT/'absolute_bss_ci.csv')
    assert len(ci)==432 and len(absolute)==144
    assert (ci.ci_low<=ci.ci_high).all() and (absolute.ci_low<=absolute.ci_high).all()
    adjusted=ci[(ci.kind=='feature')&(ci.metric=='BSS16')]
    assert len(adjusted)==126 and (adjusted.family_size==63).all()
    assert (adjusted.ci_low_family63<=adjusted.ci_low+1e-12).all()
    assert (adjusted.ci_high_family63>=adjusted.ci_high-1e-12).all()
    for r in ci.itertuples():
        a=main[(main.model==r.model)&(main.experiment==r.experiment)&(main.lead_day==r.lead_day)].iloc[0]
        b=main[(main.model==r.reference_model)&(main.experiment==r.reference)&(main.lead_day==r.lead_day)].iloc[0]
        key={'BSS16':'BSS','CSI16':'CSI','RMSE':'RMSE'}[r.metric]
        assert abs(r.estimate-(a[key]-b[key]))<1e-10
    for r in absolute.itertuples():
        a=main[(main.model==r.model)&(main.experiment==r.experiment)&(main.lead_day==r.lead_day)].iloc[0]
        assert abs(r.estimate-a.BSS)<1e-10
    workbook=load_workbook(REPORT/'BANG_KET_QUA_NGAY.xlsx',read_only=False,data_only=True)
    assert len(workbook.sheetnames)==11
    ws=workbook['KET_QUA_72'];assert ws.max_row==73
    assert [c.value for c in ws[1]]==list(display.columns)
    checked=0
    for ri,row in enumerate(display.itertuples(index=False,name=None),2):
        for ci,(actual,expected) in enumerate(zip(ws[ri],row),1):
            if isinstance(expected,float):assert abs(actual.value-expected)<1e-10;checked+=1
            else:assert actual.value==expected
    assert workbook['NGUONG_XAC_SUAT'].max_row==649
    assert workbook['DANH_MUC_42_BIEN'].max_row==43 and workbook['CHIN_O_CPC'].max_row==10
    workbook.close()
    doc=Document(REPORT/'PHUONG_AN_VA_KET_QUA.docx')
    bss=[t for t in doc.tables if [c.text for c in t.rows[0].cells]==['Cấu hình',*LABELS]]
    assert len(bss)==3;word_cells=0;bold_checked=0
    for day,t in enumerate(bss,1):
        for ei in range(8):
            values=[]
            for ci,model in enumerate(MODELS,1):
                r=main[(main.model==model)&(main.experiment==f'E{ei}')&(main.lead_day==day)].iloc[0]
                cell=t.cell(ei+1,ci);assert cell.text==f'{r.BSS:.3f}';word_cells+=1;values.append(float(r.BSS))
            for ci,value in enumerate(values,1):
                bold=any(run.bold for p in t.cell(ei+1,ci).paragraphs for run in p.runs)
                assert bold==(round(value,3)==round(max(values),3));bold_checked+=1
    e7=[t for t in doc.tables if t.rows[0].cells[0].text=='Mô hình' and len(t.columns)==9]
    assert len(e7)==3
    for day,t in enumerate(e7,1):
        assert [t.cell(ri,0).text for ri in range(1,4)]==LABELS
        for ri,model in enumerate(MODELS,1):
            r=main[(main.model==model)&(main.experiment=='E7')&(main.lead_day==day)].iloc[0]
            for ci,key in enumerate(METRICS,1):assert t.cell(ri,ci).text==f'{r[key]:.3f}';word_cells+=1
    assert '04/11/2026' in ''.join(p.text for s in doc.sections for p in s.footer.paragraphs)
    for path in REPORT.glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf8')):
            if not target.startswith(('http://','https://','#')):assert (REPORT/target).exists(),target
    for suffix in ['*.docx','*.xlsx']:
        for p in REPORT.glob(suffix):
            with zipfile.ZipFile(p) as z:assert z.testzip() is None
    snapshots=PRIVATE/'user_slide_snapshot.json'
    for item in json.loads(snapshots.read_text(encoding='utf8')):
        assert hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest()==item['sha256']
    # Verify all previous publications without touching the user's renamed slide.
    for folder,manifest_name in [('informer_regional_matrix_2026_10_28','publication_manifest.json'),
                                 ('short_range_complete_2026_10_28','build_manifest.json')]:
        root=ROOT/'reports'/folder;old=json.loads((root/manifest_name).read_text(encoding='utf8'))
        for name,info in old['files'].items():assert sha(root/name)==info['sha256']
    result=dict(status='passed',models=168,main_rows=72,excel_sheets=11,
        workbook_numeric_cells_checked=checked,word_metric_cells_checked=word_cells,bold_cells_checked=bold_checked,
        complete_three_model_tables=True,ci_rows_checked=576,old_publications_and_user_slide_preserved=True,
        native_office_rendered=False,test2025_read=False,validator_sha256=sha(__file__))
    (REPORT/'report_validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
