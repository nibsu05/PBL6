"""Verify the Vrain plan, workbook and sanitized evidence without model access."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

from docx import Document
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'reports/vrain_research_plan_2026_11_09'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def main():
    m=read(OUT/'publication_manifest.json')
    assert m['status']=='published_plan_not_training' and not m['training_performed'] and not m['test2025_read']
    for key in ('code_hashes','sources'):
        for p,digest in m[key].items():assert sha(ROOT/p)==digest,p
    for p,digest in m['shared_code_lf_normalized_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==digest,p
    for p,meta in m['files'].items():assert sha(OUT/p)==meta['sha256'],p
    audit=read(OUT/'access_audit.json');web=read(OUT/'web_access_check.json')
    assert audit['probe_count']==len(audit['probes'])==10
    assert audit['probes_with_24_hourly_rows']==7 and audit['probes_without_hourly_rows']==3
    assert audit['historical_ids_match_v1_inventory'] and not audit['historical_to_v2_crosswalk_confirmed']
    assert web['web_session_authenticated'] and not web['partner_open_api_key_verified']
    assert web['file_export']['file_downloaded'] and web['xlsx_structure']['opened']
    assert not web['units_confirmed'] and not web['timezone_confirmed'] and not web['training_performed']
    assert web['xlsx_structure']['sheets'][0]['clock_headers']==24
    for src in audit['sources']:
        path=ROOT/src['path']
        if path.exists():assert sha(path)==src['sha256']
    assert sum(r['complete_station_summary_comparisons'] for r in audit['probes'])==490
    assert sum(r['complete_station_sum_mismatches'] for r in audit['probes'])==0
    assert all(not r['measurement_units_confirmed'] for r in audit['probes'])
    for r in audit['probes']:
        assert 'sum_tolerance_source_units' in r and 'sum_tolerance_mm' not in r
        assert r['all24_complete_station_count']+r['partial_station_count']+r['no_hourly_values_station_count']==82
    wb=load_workbook(OUT/'DU_LIEU_VRAIN_VA_PHAN_CONG.xlsx',data_only=True)
    assert len(wb.sheetnames)==8
    for row,r in zip(list(wb['PROBE_THUC_TE'].values)[1:],audit['probes']):
        assert tuple(row)==(r['probe_date'],r['hourly_rows'],82,r['all24_complete_station_count'],r['partial_station_count'],r['no_hourly_values_station_count'],r['valid_numeric_cells'],r['missing_cells'])
    assert wb['PROBE_THUC_TE'].max_row==11
    catalog=list(wb['DANH_MUC_BIEN'].values)[1:]
    assert len(catalog)==45 and sum(r[2]=='Có' for r in catalog)==44 and sum(r[3]=='Có' for r in catalog)==42
    assert list(wb['METRICS'].values)[1:][0][0]=='RMSE' and wb['METRICS'].max_row==9
    expected_day=[9,21,29,10,41,22,30,42]
    for row,day in zip(list(wb['E0_E7_VA_R'].values)[1:],expected_day):
        assert tuple(row[2:])==(day+2,day,day+3,day+1)
    contract=read(OUT/'dataset_contract.json')
    assert contract['status']=='proposed_not_materialized' and len(contract['fields'])==65
    assert wb['HOP_DONG_COT'].max_row==66
    main_doc=Document(OUT/'PHUONG_AN_VRAIN_GUI_NHOM.docx')
    probe_table=next(t for t in main_doc.tables if t.cell(0,0).text=='Ngày được chọn')
    assert len(probe_table.rows)==11
    for row,r in zip(probe_table.rows[1:],audit['probes']):
        yyyy,mm,dd=r['probe_date'].split('-')
        assert [c.text for c in row.cells]==[f'{dd}/{mm}/{yyyy}',str(r['hourly_rows']),str(r['all24_complete_station_count']),str(r['partial_station_count']),str(r['no_hourly_values_station_count'])]
    for file in OUT.glob('*.docx'):
        doc=Document(file)
        assert any('09/11/2026' in s.footer.paragraphs[0].text for s in doc.sections)
        assert all('20/10/2026' not in p.text for s in doc.sections for p in s.footer.paragraphs)
    for file in OUT.iterdir():
        if file.suffix in ('.docx','.xlsx'):
            with zipfile.ZipFile(file) as z:
                assert z.testzip() is None
                for name in z.namelist():
                    if name.endswith(('.xml','.rels')):
                        text=z.read(name).decode('utf8')
                        assert '\ufffd' not in text
                        assert not re.search(r'(?i)"(?:password|sessionToken|x-vrain-token)"\s*:\s*"[^\"]+"',text)
                        assert 'X-Amz-Signature=' not in text
        elif file.suffix in ('.md','.csv','.json'):
            text=file.read_text(encoding='utf8')
            assert '\ufffd' not in text and 'X-Amz-Signature=' not in text
            assert not re.search(r'(?i)"(?:password|sessionToken|x-vrain-token)"\s*:\s*"[^\"]+"',text)
        if file.suffix=='.md':
            for target in re.findall(r'\]\(([^)]+)\)',file.read_text(encoding='utf8')):
                if not target.startswith(('http://','https://','#')):assert (OUT/target).exists(),target
    snapshot=ROOT/'data/operational/vrain_2026_11_09/user_artifact_snapshot.json'
    user_files=0
    if snapshot.exists():
        for item in read(snapshot):
            assert sha(ROOT/item['path'])==item['sha256'],item['path']
            user_files+=1
    result=dict(status='passed',probes=10,hourly_probes=7,no_hourly_data_probes=3,
                complete_station_sum_checks=490,inventory_v1=82,inventory_v2=86,
                workbook_sheets=8,contract_fields=65,feature_rows_including_R_proposal=45,
                docx_probe_table_matches_source=True,unit_semantics_still_unconfirmed=True,
                user_files_unchanged=user_files,training_performed=False,test2025_read=False,
                native_office_rendered=False)
    (OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
