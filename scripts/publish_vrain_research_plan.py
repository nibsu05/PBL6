"""Publish the Vrain plan from sanitized aggregates; no login or model fitting."""
from pathlib import Path
import csv
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_final_regional_plan import word_copy
from docx import Document
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

OUT = ROOT / 'reports/vrain_research_plan_2026_11_09'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(name, value):
    (OUT / name).write_text(value.rstrip() + '\n', encoding='utf8', newline='\n')


def main():
    audit = json.loads((OUT/'access_audit.json').read_text(encoding='utf8'))
    web = json.loads((OUT/'web_access_check.json').read_text(encoding='utf8'))
    groups = json.loads((ROOT/'reports/regional_research_plan_2026_10_20/feature_groups.json').read_text(encoding='utf8'))
    assert audit['probe_count'] == 10 and not audit['test2025_read']
    assert web['web_session_authenticated'] and web['file_export']['file_downloaded']
    assert web['inventory_v1_stations'] == 82 and web['inventory_v2_stations'] == 86
    write('TOM_TAT_GUI_NHOM.md', '''# Gửi nhóm: hướng dữ liệu Vrain cho PBL6

**Ngày 09/11/2026 — đề xuất để triển khai, chưa huấn luyện Vrain.**

Mục tiêu giữ nguyên: nghiên cứu thêm/bớt đặc trưng để dự đoán trực tiếp mưa trung bình vùng Đà Nẵng mới. ERA5 tiếp tục cung cấp khí tượng; Vrain dùng để xây nhãn vùng từ trạm sau QC. Dữ liệu trạm không có nghĩa đo trực tiếp mọi điểm của tỉnh.

Đã đăng nhập/xuất được dữ liệu thật. Inventory V1 có 82 trạm và khớp mã lịch sử; V2 có 86 mục nhưng bộ mã khác, không gộp theo tên. Trong mười ngày probe, bảy ngày có 24 hàng giờ; ba ngày thử 2015/2019/2020 chỉ có hàng tổng. Ngày 15/01/2021 chỉ 50/82 trạm đủ 24 giá trị, ngày 14/10/2024 là 81/82. Chưa có kiểm kê toàn kho, chưa xác nhận đầy đủ timezone/ý nghĩa kỳ đo hoặc phủ địa hình.

**Cách tổng hợp:** chốt polygon và panel trạm lõi; chuẩn hóa khoảng đo/múi giờ; QC; dùng trọng số diện tích Thiessen cắt theo ranh để tạo một chuỗi mưa vùng. Lưu thiếu/coverage/version. Không lấy trung bình các trạm có số liệu tùy ngày, không điền thiếu bằng 0 và không coi hàng tổng 0 khi không có giờ là ngày khô. X ERA5 và y Vrain phải cùng vùng; 93 ô cũ còn là footprint xấp xỉ.

Hai nhánh dùng chung gốc: Bi-LSTM nhận lịch sử giờ, dự đoán sáu lượng mưa giờ tiếp; LightGBM/TFT/Informer nhận lịch sử ngày, dự đoán ba tổng 24h riêng. B/A/M/C giữ lại; mưa Vrain quá khứ là nhóm R mới. Thử R0/R1 cùng mẫu, sau đó giữ R cố định khi thêm/bớt A/M/C. Không so điểm Vrain mới với điểm CPC/GSMaP cũ để tuyên bố cải thiện.

**Việc trước mắt:** một người phụ trách inventory/lịch sử/QC/ranh/trọng số; một người Bi-LSTM; người phụ trách TFT chuẩn bị nhánh ngày và bảng ba mô hình. Trong 24–48h đầu cần timeline dữ liệu, coverage và số mẫu, chưa cần chạy lại toàn ma trận. Pilot E0/E2/E7 trước; chỉ chạy đủ E0–E7 sau khi dữ liệu và split đạt. Lịch sử thực quyết định fold, không mặc định train từ 2015. Giữ kín 2025.

Chi tiết nguồn, cổng bắt đầu/dừng, hợp đồng cột, cách lấy mẫu, metrics, phân công và lịch 5–10 ngày làm việc có điều kiện nằm trong tài liệu đầy đủ và workbook đi kèm. Chưa có lời hứa cải thiện tới 72h; chưa gọi đây là dự báo vận hành với đầu vào có sẵn tại mốc phát báo.
''')
    fields = []
    def add(layer, names, meaning):
        for name in names:
            fields.append(dict(layer=layer, field=name, required='Có', meaning=meaning))
    add('station_inventory', ['provider','service','id_namespace','station_id','station_uuid'], 'Khóa định danh; không nối V1/V2 bằng tên')
    add('station_inventory', ['longitude','latitude','coordinate_crs','position_valid_from','position_valid_to'], 'Tọa độ và thời kỳ hiệu lực; chưa biết thì đánh dấu unknown, không bịa')
    add('station_inventory', ['sensor_type','unit','source_timezone','timestamp_means','accumulation_semantics','reporting_interval'], 'Metadata cần xác nhận trước chuẩn hóa nhãn')
    add('source_manifest', ['relative_path','sha256','retrieved_at_utc','requested_start','requested_end','schema_version'], 'Nguồn nguyên gốc private; không token/cookie/signed URL')
    add('station_intervals', ['station_key','period_start_utc','period_end_utc','rain_mm','qc_flags','source_sha256'], 'Quan trắc theo khoảng; giữ missing khác 0')
    add('station_intervals', ['available_at_utc'], 'Chỉ ghi nếu được chứng minh; unknown không được giả thành giờ quan trắc')
    add('station_hourly_daily', ['period_start_utc','period_end_utc','rain_mm','n_expected','n_observed','valid'], 'Giờ hoặc tổng ngày đúng anchor; không cộng hàng tổng lần nữa')
    add('region_definition', ['region_version','polygon_sha256','source','crs_wkt','island_scope'], 'Cùng phạm vi cho X/y; phần chưa được mạng đại diện phải nêu rõ')
    add('station_weights', ['region_version','network_version','weights_version','station_key','area_weight'], 'Trọng số cố định, không âm, tổng bằng 1; tính trong CRS phù hợp')
    add('region_hourly_daily', ['period_start_utc','period_end_utc','vrain_areal_estimate_mm','valid','coverage_weight','network_version','weights_version'], 'Ước lượng diện tích; không tự chuẩn hóa mạng khuyết trong nhãn chính')
    add('predictors', ['period_start_utc','period_end_utc','region_version','features','source_coverage'], 'ERA5 B/A/M/C; miền SST/context riêng có provenance')
    add('sample_index', ['issue_time_utc','history_start_utc','history_end_utc','target_intervals','all_e_valid','split','dataset_version','rain_input_lag'], 'Một issue vùng; toàn bộ nhãn nằm trong split và không có tương lai trong X')
    contract = dict(status='proposed_not_materialized', region_target='direct_areal_rainfall',
                    label_name='vrain_areal_estimate_mm', primary_missing_policy='fixed core panel, no implicit renormalization',
                    time_metadata_confirmed=False, measurement_unit_confirmed=False, region_polygon_confirmed=False,
                    sample_counts_known=False, test2025_read=False, fields=fields)
    write('dataset_contract.json', json.dumps(contract, ensure_ascii=False, indent=2))
    with (OUT/'DATA_DICTIONARY.csv').open('w', encoding='utf8', newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(fields[0]),lineterminator='\n');writer.writeheader();writer.writerows(fields)
    wb=Workbook();wb.remove(wb.active)
    def sheet(name, headers, rows, widths):
        ws=wb.create_sheet(name);ws.append(headers)
        for row in rows:ws.append(list(row))
        ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
        for cell in ws[1]:cell.fill=PatternFill('solid',fgColor='123047');cell.font=Font(name='Arial',size=11,bold=True,color='FFFFFF')
        ws.row_dimensions[1].height=32
        for row in ws.iter_rows(min_row=2):
            for c in row:c.font=Font(name='Arial',size=11);c.alignment=Alignment(vertical='top',wrap_text=True)
            ws.row_dimensions[row[0].row].height=52
        for i,width in enumerate(widths,1):ws.column_dimensions[ws.cell(1,i).column_letter].width=width
        ws.sheet_view.zoomScale=85
        return ws
    sheet('DOC_DAU',['Mục','Trạng thái'],[
        ['Mục tiêu','Nghiên cứu dự đoán vùng trực tiếp; không quay lại ưu tiên app'],
        ['Dữ liệu đã thấy','V1 82 trạm; V2 86 mục; history khớp V1, không gộp namespace'],
        ['Kiểm kê','10 ngày probe, chưa phải toàn bộ lịch sử; 2025 chưa đọc'],
        ['Thời gian / ranh','Chưa xác nhận đủ ngữ nghĩa thời gian, polygon và tính đại diện'],
        ['Hợp đồng cột','Là đề xuất bàn giao, không phải dataset đã dựng'],
        ['Huấn luyện','Chưa huấn luyện Vrain; 168 lượt cũ thuộc CPC'],
        ['Bảo mật','Không tài khoản/cookie/số đo từng trạm trong workbook'],
    ],[26,110])
    sheet('PROBE_THUC_TE',['Ngày','Hàng giờ','Trạm trong bảng','Đủ 24 số','Thiếu một phần','Không có giờ','Ô số hợp lệ','Ô dấu thiếu'],[
        [r['probe_date'],r['hourly_rows'],r['nstation_union'],r['all24_complete_station_count'],r['partial_station_count'],r['no_hourly_values_station_count'],r['valid_numeric_cells'],r['missing_cells']] for r in audit['probes']],[18,14,20,16,20,20,20,20])
    sheet('HOP_DONG_COT',list(fields[0]),[r.values() for r in fields],[26,30,12,95])
    catalog=[]
    for group in ('B','A','M','C'):
        for feature in groups[group]:
            catalog.append([group,feature,'Có','Không' if feature in ('sin_hour','cos_hour') else 'Có',
                            'Lịch biết trước' if feature.startswith(('sin_','cos_')) else 'Khí tượng quá khứ; mean ngày ban đầu'])
    catalog.append(['R','vrain_areal_estimate_mm_past','Đề xuất','Đề xuất','Một kênh mưa quá khứ theo bước; không phải y tương lai'])
    sheet('DANH_MUC_BIEN',['Nhóm','Tên nguồn','Nhánh giờ','Nhánh ngày','Cách dùng'],catalog,[12,38,16,16,80])
    configs=[]
    for e,selected in groups['experiments'].items():
        hour=sum(len(groups[g]) for g in selected);day=hour-2
        configs.append([e,'+'.join(selected),hour,day,hour+1,day+1])
    sheet('E0_E7_VA_R',['E','Nhóm R0','Giờ R0','Ngày R0','Giờ R1','Ngày R1'],configs,[12,30,18,18,18,18])
    gates=[['G0','Truy cập','Đã đọc/xuất thử','Inventory/lịch sử thật/XLSX; còn cần kiểm kê kho'],
           ['G1','Thời gian/đơn vị','Chờ xác nhận','Timezone, timestamp đầu/cuối, increment/counter, missing/trace'],
           ['G2','Trạm và vùng','Chưa hoàn tất','V1 ID khớp; cần lịch sử vị trí/polygon/panel/trọng số'],
           ['G3','Lịch sử/QC','Mới có probe','Số mẫu, mùa, sự kiện và missing trên toàn lịch sử được chọn'],
           ['G4','Độ bền nhãn','Chưa làm','Rút trạm, nhạy panel, cực trị, mẫu bị loại theo mùa'],
           ['G5','Pilot','Chưa train Vrain','Chung nhãn/mask/split, baseline, chống leak'],
           ['G6','Ma trận/test','Chưa bắt đầu','Khóa protocol và review trước holdout']]
    sheet('CONG_QUYET_DINH',['Cổng','Chủ đề','Hiện trạng','Bằng chứng cần có'],gates,[12,28,26,96])
    sheet('PHAN_CONG',['Phần việc','Phụ trách đề xuất','Bàn giao','Ước lượng có điều kiện'],[
        ['Truy cập/metadata','Thành viên dữ liệu','Đơn vị/giờ/ID/quyền xuất, timeline trạm','0,5–1 ngày; phụ thuộc phản hồi nguồn'],
        ['Tải/QC','Thành viên dữ liệu','Raw manifest + interval/QC + báo cáo thiếu','1–2 ngày; đo lô nhỏ trước'],
        ['Ranh/panel/trọng số','Cả nhóm, người dữ liệu triển khai','Polygon cùng X/y, mạng lõi, độ bền nhãn','1–2 ngày'],
        ['Cực ngắn','Thành viên Bi-LSTM','Loader vùng sáu giờ, baseline và R0/R1','Sau G1–G4; đo pilot'],
        ['Ngày','Người dùng phụ trách TFT','LightGBM/TFT/Informer cùng mẫu, ba tổng24h','Sau G1–G4; đo pilot'],
        ['Pilot chung','Cả nhóm','E0/E2/E7, kiểm tra leak/CI mẫu','0,5–1 ngày'],
        ['Ma trận và báo cáo','Hai nhánh mô hình','E0–E7, metrics/mùa/seed/CI','2–4 ngày sau pilot; chưa hứa fit cố định'],
    ],[28,28,70,60])
    metrics=[['RMSE','Lỗi lượng mưa, phạt lỗi lớn','Thấp'],['MAE','Trung bình lệch tuyệt đối mm','Thấp'],['Bias','Dự báo trừ nhãn trung bình','Gần 0'],['BS','Sai số xác suất','Thấp'],['BSS','BS cải thiện so khí hậu','Cao; đọc 0 và CI'],['CSI','H/(H+M+F)','Cao'],['POD','H/(H+M), đọc cùng FAR','Cao'],['FAR','F/(H+F)','Thấp']]
    sheet('METRICS',['Chỉ số','Ý nghĩa','Chiều tốt'],metrics,[20,85,30])
    wb.save(OUT/'DU_LIEU_VRAIN_VA_PHAN_CONG.xlsx')
    for name in ('PHUONG_AN_VRAIN_GUI_NHOM.md','TOM_TAT_GUI_NHOM.md'):
        target=word_copy(OUT/name);doc=Document(target)
        for section in doc.sections:
            for paragraph in section.footer.paragraphs:
                for run in paragraph.runs:run.text=run.text.replace('20/10/2026','09/11/2026')
        doc.core_properties.title=Path(name).stem.replace('_',' ')
        doc.core_properties.subject='Kế hoạch Vrain, dữ liệu vùng, kiểm kê truy cập thực tế; chưa huấn luyện'
        doc.save(target)
    write('README.md','''# Hướng Vrain cho nghiên cứu dự đoán mưa vùng — 09/11/2026

- [Tài liệu đầy đủ gửi nhóm (Word)](PHUONG_AN_VRAIN_GUI_NHOM.docx), [bản Markdown](PHUONG_AN_VRAIN_GUI_NHOM.md).
- [Bản ngắn gửi nhóm (Word)](TOM_TAT_GUI_NHOM.docx), [nội dung có thể sao chép](TOM_TAT_GUI_NHOM.md).
- [Excel dữ liệu, probe, hợp đồng cột, đặc trưng và phân công](DU_LIEU_VRAIN_VA_PHAN_CONG.xlsx).
- [Audit cấu trúc](access_audit.json), [CSV probe](history_probe_summary.csv), [kiểm tra truy cập/xuất XLSX](web_access_check.json).
- [Hợp đồng dữ liệu đề xuất](dataset_contract.json), [từ điển cột CSV](DATA_DICTIONARY.csv).

Đã đăng nhập và xuất mẫu thật: inventory V1 82 trạm khớp history, V2 86 mục khác namespace. Mới kiểm tra mười ngày, chưa kiểm kê toàn kho; đủ 24 số không đồng nghĩa qua mọi QC. Chưa xác nhận đầy đủ thời gian/đơn vị, vị trí lịch sử, polygon và độ phủ. Chưa tạo nhãn vùng hoặc huấn luyện Vrain, chưa mở 2025. Giữ nguyên slide người dùng sửa và các báo cáo trước.

Tái lập kiểm kê với nguồn private: `scripts/audit_vrain_exports.py`. Kiểm thử parser: `python -m unittest tests.test_vrain_export_audit`. Xuất lại tài liệu từ aggregate công khai: `scripts/publish_vrain_research_plan.py`; kiểm tra bằng `scripts/validate_vrain_research_plan.py`. Các script này không đăng nhập, tải thêm hoặc học mô hình. Raw/XLSX gốc/inventory và phiên đăng nhập không nằm trong Git; cần quyền nguồn để nhận dữ liệu.
''')
    code=['src/vrain_export_audit.py','scripts/audit_vrain_exports.py','scripts/publish_vrain_research_plan.py','scripts/validate_vrain_research_plan.py','tests/test_vrain_export_audit.py']
    sources=['reports/regional_research_plan_2026_10_20/feature_groups.json']
    shared='scripts/build_final_regional_plan.py'
    manifest=dict(status='published_plan_not_training',date='2026-11-09',probe_count=10,
                  offline_report_rebuild=True,training_performed=False,test2025_read=False,
                  code_hashes={p:sha(ROOT/p) for p in code},sources={p:sha(ROOT/p) for p in sources},
                  shared_code_lf_normalized_sha256={shared:hashlib.sha256((ROOT/shared).read_bytes().replace(b'\r\n',b'\n')).hexdigest()},
                  files={p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in OUT.iterdir()
                         if p.is_file() and p.name not in ('publication_manifest.json','validation.json')})
    write('publication_manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    print(json.dumps(dict(status=manifest['status'],workbook_sheets=len(wb.sheetnames),dictionary_fields=len(fields),feature_rows=len(catalog))))


if __name__=='__main__':
    main()
