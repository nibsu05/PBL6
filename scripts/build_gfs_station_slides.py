"""Detailed, editable Vietnamese slides from the frozen 57-station experiment.

Reads existing aggregates/checkpoints only; no fitting, forecast downloading or
2025 observations. All plotted values and tables are traceable to input hashes.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
for p in [ROOT,ROOT/'scripts']:sys.path.insert(0,str(p))
import joblib
import numpy as np
import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Pt
from presentation_layout import Deck,NAVY,TEAL,RED,MUTED
from gfs_station_slide_notes import NOTES

DATA=ROOT/'reports/gfs_station_57_2026_11_10'
PRIVATE=ROOT/'data/operational/gfs_station_57_2026_11_10'
OUT=ROOT/'reports/gfs_station_slides_2026_11_10'
STEM='PBL6_DU_BAO_MUA_57_TRAM'
FOOT='57 trạm · Issue mỗi 7 ngày · Dev 2024 · 2025 giữ kín'
MODELS=['CLIM','PERSISTENCE','GFS','A0','A1','A2','A3','GRU_A2']
LABELS={'CLIM':'Khí hậu','PERSISTENCE':'Persistence','GFS':'GFS gốc','A0':'LightGBM A0',
        'A1':'LightGBM A1','A2':'LightGBM A2','A3':'LightGBM A3','GRU_A2':'GRU A2'}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def fmt(value,n=2):return '—' if pd.isna(value) else f'{value:.{n}f}'.replace('.',',')
def signed(value,n=3):return f'{value:+.{n}f}'.replace('.',',')


def audit_training():
    records=[]
    for path in sorted((PRIVATE/'models').glob('A[0-3]_d*_seed*.joblib')):
        item=joblib.load(path);m=item['amount']
        records.append(dict(artifact=path.stem,checkpoint_sha256=sha(path),
            metric_order=list(m.evals_result_['valid_0']),best_iteration=int(m.best_iteration_),
            evaluated_rounds=len(m.evals_result_['valid_0']['l1'])))
    assert len(records)==36 and all(r['metric_order'][0]=='l1' for r in records)
    predictions=pd.read_parquet(PRIVATE/'predictions_private.parquet');dev=predictions[predictions.split.eq('dev')]
    coherence=[]
    for model in ['A0','A1','A2','A3','GRU_A2']:
        gap=dev[model+'_p50']-dev[model+'_p1'];bad=gap>1e-9
        coherence.append(dict(model=model,dev_rows=len(dev),violations=int(bad.sum()),fraction=float(bad.mean()),
            max_probability_gap=float(gap.max()),decision_contradictions=int(((dev[model+'_p50']>=.5)&(dev[model+'_p1']<.5)).sum())))
    audit=dict(amount_fits=records,all_first_metric_l1=True,best_iteration_range=[min(r['best_iteration'] for r in records),max(r['best_iteration'] for r in records)],
        evaluated_round_range=[min(r['evaluated_rounds'] for r in records),max(r['evaluated_rounds'] for r in records)],
        probability_coherence_dev=coherence,private_predictions_sha256=sha(PRIVATE/'predictions_private.parquet'),
        training_performed_for_slides=False,predictions_changed_for_slides=False,test2025_read=False)
    (OUT/'training_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    return audit


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    point=pd.read_csv(DATA/'point_metrics.csv');prob=pd.read_csv(DATA/'probability_metrics.csv')
    event=pd.read_csv(DATA/'event_metrics.csv');ci=pd.read_csv(DATA/'paired_bootstrap.csv')
    matched=pd.read_csv(DATA/'matched_original20_bootstrap.csv');scopes=pd.read_csv(DATA/'cohort_scope_metrics.csv')
    diagnostics=pd.read_csv(DATA/'fit_diagnostics.csv');seeds=pd.read_csv(DATA/'seed_point_metrics.csv')
    protocol=json.loads((DATA/'protocol.json').read_text());gru=json.loads((DATA/'gru_summary.json').read_text())
    run=json.loads((DATA/'run_summary.json').read_text());audit=audit_training()
    d=Deck();roles={};main_count=0
    def page(role,title,section,source='protocol.json'):
        s=d.slide(title,section,FOOT+' · '+source,NOTES[role])
        roles[role]=s['number'];s['role']=role
        return s
    def bullets(s,items,y=1.65,size=22,gap=.72):
        for i,item in enumerate(items):d.text(s,.70,y+i*gap,11.9,gap-.08,'• '+item,size)
    def table(s,headers,rows,tag,widths=None,y=1.65,row_h=.52,size=20,x=.55,w=12.25,styles=None):
        return d.table(s,headers,rows,x=x,y=y,w=w,row_h=row_h,widths=widths,size=size,styles=styles,tag=tag)
    def matrix(s,models,key,tag,source='point',threshold=1.,x=.55,w=12.25,y=1.65,row_h=.49,size=20):
        f=point if source=='point' else prob
        f=f[f.fold.eq('dev')]
        if source=='prob':f=f[f.threshold_mm.eq(threshold)]
        values=[[float(f[f.model.eq(m)&f.horizon.eq(h)][key].iloc[0]) for h in [1,2,3]] for m in models]
        styles={};lower=key in ['macro_mae','macro_rmse','macro_bs']
        for j in range(3):
            scores=[abs(v[j]) if key=='macro_bias' else v[j] for v in values]
            best=min(scores) if lower or key=='macro_bias' else max(scores)
            for i,v in enumerate(values):
                value=abs(v[j]) if key=='macro_bias' else v[j]
                is_best=np.isclose(value,best)
                styles[f'{i+1},{j+1}']=dict(bold=bool(is_best),color=RED if key=='macro_bss' and v[j]<0 else TEAL if is_best else NAVY)
        digits=3 if source=='prob' else 2
        rows=[[LABELS[m]]+[fmt(v,digits) for v in vals] for m,vals in zip(models,values)]
        widths=[w*.39,w*.2033,w*.2033,w*(1-.39-.2033*2)]
        return table(s,['Phương pháp','Ngày 1','Ngày 2','Ngày 3'],rows,tag,widths,y,row_h,size,x,w,styles)

    s=page('title','Dự báo mưa ngắn hạn tại 57 trạm','BÁO CÁO THỰC NGHIỆM · 10/11/2026')
    d.text(s,.75,1.7,11.8,1.1,'Từ dữ liệu → chia thời gian → huấn luyện\n→ hiệu chỉnh xác suất → đọc kết quả',31,True)
    for x,title,body in [(0.7,'57 trạm','Học chung nhiều trạm'),(4.85,'3 ngày','Ba tổng 24h riêng'),(9.0,'2021–2024','2025 vẫn giữ kín')]:d.card(s,x,3.25,3.65,1.75,title,body,20)
    d.band(s,'Đã chạy: LightGBM A0–A3 và GRU A2 · Mỗi cấu hình 3 seed',y=5.6,h=.68,size=21)

    s=page('map','Bốn câu hỏi cần trả lời','MỤC TIÊU BÁO CÁO')
    bullets(s,['Một mẫu dự báo dùng thông tin gì và cần dự báo điều gì?',
        'Chia train / cal / dev thế nào để tránh dùng nhầm tương lai?',
        'Đã cố định, lựa chọn và hiệu chỉnh những tham số nào?',
        'Mô hình tốt ở chỉ số nào; bằng chứng cải thiện chắc đến đâu?'],gap=.93)
    d.band(s,'Không gọi cấu hình đang dùng là “tối ưu” khi chưa tìm kiếm siêu tham số.')

    s=page('target','Đầu ra: ba lượng mưa riêng tại cùng trạm','I. BÀI TOÁN VÀ DỮ LIỆU')
    table(s,['Đầu ra','Khoảng mưa theo giờ Việt Nam'],[
        ['Ngày 1','19:00 D → 19:00 D+1'],['Ngày 2','19:00 D+1 → 19:00 D+2'],['Ngày 3','19:00 D+2 → 19:00 D+3']],
        'target_windows',[3.0,9.25],row_h=.84,size=24)
    d.text(s,.8,5.25,11.7,.5,'Mỗi ngày: **1 lượng mm + 2 xác suất** (≥1 và ≥50 mm/24h).',23)
    d.band(s,'Tổng cộng: 3 lượng mm + 6 xác suất; không phải 3 tổng tích lũy 0–72h.')

    s=page('stations','Vì sao là 57 trạm, không phải đủ 86?','I. BÀI TOÁN VÀ DỮ LIỆU', 'cohort_expansion_audit.json')
    table(s,['Nhóm vị trí','Số','Cách xử lý'],[['Đạt tiêu chuẩn train','57','Đưa vào bản mở rộng chính'],
        ['Có mẫu train, lịch sử ngắn hơn','22','Dành cho thí nghiệm riêng'],['Chưa có cửa sổ train hợp lệ','3','Chưa đánh giá như trạm đã biết'],
        ['Chỉ có ở danh mục mới','4','Chưa có lịch sử nguồn 2021–2024']], 'station_cohort',[5.0,1.0,6.25],row_h=.73,size=21)
    d.band(s,'Tiêu chuẩn trạm chỉ dựa trên train và metadata; không lọc theo điểm dev.')

    s=page('sources','Ba nguồn có ba vai trò khác nhau','I. BÀI TOÁN VÀ DỮ LIỆU')
    table(s,['Nguồn','Dùng cho việc gì?','Điều không được suy ra'],[
        ['Vrain','Nhãn y và mưa quá khứ tại trạm','Không phải mưa trung bình cả vùng'],
        ['GFS 0,25°','Dự báo mưa / khí tượng làm đầu vào','Không phải quan trắc khí tượng tại trạm'],
        ['DEM Mapzen','Proxy địa hình và tương tác với gió','Không phải cao độ khảo sát cảm biến']],
        'sources',[2.1,5.0,5.15],row_h=.98,size=20)
    d.band(s,'Bản 57 trạm hiện tại dùng GFS + Vrain; không dùng ERA5 kỳ đích.')

    s=page('sample','Một mẫu = một trạm + một thời điểm phát tin','I. BÀI TOÁN VÀ DỮ LIỆU')
    d.card(s,.6,1.65,5.8,3.45,'Đầu vào X tại trạm S',
        '• Bảy ngày mưa quá khứ\n• Mưa 1/6/24h đã có\n• GFS dự báo cho ngày 1–3\n• Lịch, vị trí/ID; DEM nếu A3',21)
    d.card(s,6.75,1.65,5.95,3.45,'Đầu ra y cần học / kiểm chứng',
        'Ba tổng mưa Vrain tương lai:\n[y₁, y₂, y₃]\n\nVí dụ giả định: [18, 20, 7] mm',23)
    d.band(s,'Ví dụ chỉ minh họa cấu trúc; y tương lai không xuất hiện trong đầu vào X.')

    s=page('issue_time','Mốc thời gian: 07h → 18h → 19h','I. BÀI TOÁN VÀ DỮ LIỆU')
    for x,title,body,color in [(.6,'07:00 VN','GFS00UTC\nKhởi tạo dự báo',TEAL),(4.7,'18:00 VN','Cuối số mưa trạm\nđược phép dùng',TEAL),(8.8,'19:00 VN','Phát dự báo\nBắt đầu kỳ đích',NAVY)]:
        d.card(s,x,2.05,3.9,2.35,title,body,23)
    d.text(s,.8,4.85,11.9,.9,'Giả định trễ: **GFS 8h**, **Vrain 1h**.\nChưa chứng nhận đầy đủ độ trễ vận hành lịch sử.',22)
    d.band(s,'Không giả định số đo kết thúc 19h đã có ngay lúc issue 19h.')

    s=page('labels','Nhãn ngày được cộng từ 24 giờ Vrain','I. BÀI TOÁN VÀ DỮ LIỆU')
    table(s,['Mốc nguồn','Khoảng đo tương ứng'],[['10:00 VN','09:00–10:00 VN'],
        ['24 mốc kết thúc 20h D … 19h D+1','Tổng mưa 19h D → 19h D+1'],
        ['Thiếu một giờ / station-day lỗi','y ngày = thiếu; mẫu liên quan bị loại']],
        'label_rules',[5.1,7.15],row_h=.95,size=22)
    d.band(s,'Nhãn = số đo Vrain sau QC; GFS chỉ cung cấp predictor và đối chứng.')

    s=page('gfs_acc','Mưa GFS: phải trừ đúng hai mốc tích lũy','I. BÀI TOÁN VÀ DỮ LIỆU')
    table(s,['Predictor mưa GFS','Phép tính từ chu kỳ 00UTC','Ví dụ giả định'],[
        ['Ngày 1: +12 → +36h','C36 − C12','22 − 10 = 12 mm'],
        ['Ngày 2: +36 → +60h','C60 − C36','37 − 22 = 15 mm'],
        ['Ngày 3: +60 → +84h','C84 − C60','42 − 37 = 5 mm']],
        'gfs_accumulation',[4.2,4.0,4.05],row_h=.88,size=22)
    d.band(s,'12 / 15 / 5 mm ở ví dụ là dự báo GFS; khác nhãn mưa Vrain cần học.')

    s=page('future','Vì sao được dùng khí tượng “tương lai”?','I. BÀI TOÁN VÀ DỮ LIỆU')
    d.card(s,.6,1.7,5.9,3.7,'Được dùng trong thiết kế',
        'Bản GFS khởi tạo trước issue\n→ dự báo cho ngày 1 / 2 / 3.\n\nBa trạng thái giữa cửa sổ:\n+24h / +48h / +72h.',23)
    d.card(s,6.85,1.7,5.85,3.7,'Không được đưa vào X',
        '• Mưa Vrain kỳ đích\n• Khí tượng thực đo kỳ đích\n• ERA5 kỳ đích\n• Bản GFS chưa sẵn sàng lúc issue',21)
    d.band(s,'Thông tin dự báo cho tương lai ≠ quan trắc tương lai.')

    s=page('rain_history','Lịch sử mưa: hai loại cửa sổ khác nhau','I. BÀI TOÁN VÀ DỮ LIỆU')
    table(s,['Phần lịch sử','Độ dài','Kết thúc ở đâu?'],[
        ['Bảy tổng ngày đầy đủ','7 × 24h','Ngày gần nhất kết thúc 19h D−1'],
        ['Mưa rất gần issue','1h và 6h','18h D'],['Mưa 24h gần nhất','24h','18h D']],
        'rain_history',[4.9,2.0,5.35],row_h=.86,size=22)
    d.band(s,'Tổng số cột mưa quá khứ trong A1–A3: 7 + 3 = 10.')

    s=page('spatial','GFS tại trạm là nội suy từ bốn nút','I. BÀI TOÁN VÀ DỮ LIỆU')
    table(s,['Đối tượng','Cách xử lý','Giới hạn'],[
        ['GFS 0,25°','Nội suy song tuyến 4 nút quanh trạm','Không biến thành số đo tại trạm'],
        ['DEM Mapzen','Cao độ và 9 điểm trong ô ±5km','Không phải cao độ khảo sát cảm biến'],
        ['Trạm gần nhau','Có thể nhận predictor tương tự','Không phải mẫu thời tiết độc lập']],
        'spatial_rules',[2.6,5.0,4.65],row_h=.99,size=20)
    d.band(s,'Đích vẫn là mưa tại điểm đo, không phải mưa ô lưới hoặc trung bình vùng.')

    s=page('ablation','A0–A3: bổ sung thông tin từng bước','I. BÀI TOÁN VÀ DỮ LIỆU')
    table(s,['Cấu hình','Số biến','Thông tin mới'],[['A0','6','Mưa GFS + lịch + vị trí / ID'],
        ['A1','16','A0 + 7 ngày mưa + summary 1/6/24h'],['A2','25','A1 + T/RH/gió 850, PWAT và dẫn xuất'],
        ['A3','32','A2 + DEM, gradient và tương tác với gió']],
        'feature_groups',[2.0,1.5,8.75],row_h=.78,size=22)
    d.band(s,'Cùng mẫu, split, seed và thiết lập mô hình khi so A0–A3.')

    s=page('a2_inputs','A2 có 25 biến, nhưng GRU không nhận 25 kênh chuỗi','I. BÀI TOÁN VÀ DỮ LIỆU')
    table(s,['Thông tin A2','LightGBM','GRU'],[
        ['Bảy ngày mưa','7 cột','Chuỗi [7, 1]'],['GFS + lịch + tọa độ + summary gần đây','17 cột','Ngữ cảnh [3, 17]'],
        ['ID trạm','1 biến phân loại','Embedding 86 mã × 4 chiều']],
        'a2_partition',[6.0,2.6,3.65],row_h=.98,size=21)
    d.band(s,'7 + 17 + 1 = 25 cột thông tin A2; cách biểu diễn khác theo mô hình.')

    s=page('split','Chia theo năm, đồng thời cho mọi trạm','II. CHIA DỮ LIỆU VÀ HUẤN LUYỆN')
    for x,w,title,body in [(.6,4.2,'2021–2022 · TRAIN','Học mô hình\nFit scaler / tham chiếu'),(5.05,3.5,'2023 · CAL','Chọn checkpoint\nHiệu chỉnh xác suất'),(8.8,3.9,'2024 · DEV','Đánh giá phát triển\nChưa là test cuối')]:d.card(s,x,1.95,w,2.8,title,body,22)
    d.text(s,.85,5.25,11.7,.45,'**2025 giữ kín** · 2026 chưa dùng fit/tuning trong thí nghiệm này.',22)
    d.band(s,'Chia theo thời gian; toàn bộ 72h nhãn của mỗi mẫu phải nằm cùng một tập.',size=18)

    s=page('counts','Số mẫu: đếm trạm–issue, không chỉ đếm dòng','II. CHIA DỮ LIỆU VÀ HUẤN LUYỆN', 'dataset_audit.json')
    table(s,['Phần','Mẫu trạm–issue','Dòng theo 3 hạn','Issue có mẫu'],[
        ['Train','5.032','15.096','102'],['Cal','2.582','7.746','51'],['Dev','2.782','8.346','52'],
        ['Tổng','10.396','31.188','205']], 'sample_counts',[2.3,3.4,3.5,3.05],row_h=.76,size=23)
    d.band(s,'Nhiều trạm và nhiều hạn không tạo thêm các mùa khí hậu độc lập.')

    s=page('qc','Điều kiện một cửa sổ được đưa vào học','II. CHIA DỮ LIỆU VÀ HUẤN LUYỆN')
    bullets(s,['Đủ lịch sử và đủ cả ba nhãn 24h tại chính trạm.',
        'Mọi đầu vào cần thiết hợp lệ; các A dùng cùng mask.',
        'Toàn bộ 72h nhãn nằm trong cùng train / cal / dev.',
        'Giữ đúng thời gian; không nối qua khoảng thiếu hoặc sang trạm khác.',
        '1.346 cửa sổ trạm–issue không đủ; 2 issue băng ranh bị loại.'],size=22,gap=.79)
    d.band(s,'Thiếu / lỗi → loại cửa sổ liên quan; không lấp y bằng mưa mô hình.')

    s=page('baselines','Đối chứng: mỗi phương pháp trả lời một câu hỏi','II. CHIA DỮ LIỆU VÀ HUẤN LUYỆN')
    table(s,['Phương pháp','Cách dự báo','Điều cần kiểm chứng'],[['Khí hậu','Trung bình / tần suất\ntháng–trạm từ train','Có hơn tham chiếu theo mùa?'],
        ['Persistence','Lặp lại tổng 24h khả dụng gần nhất','Có hơn cách giữ trạng thái gần đây?'],['GFS gốc','Mưa dự báo trước hậu xử lý','Học máy thêm được giá trị gì?'],
        ['LightGBM / GRU','Học từ predictor và nhãn Vrain','Dữ liệu / cách học nào hữu ích?']],
        'baselines',[2.8,5.1,4.35],row_h=.82,size=20)
    d.band(s,'Khí hậu dùng mọi ngày train hợp lệ; các mô hình pilot có lịch issue mỗi 7 ngày.')

    s=page('lgb_io','LightGBM: vector cho từng hạn, mô hình dùng chung trạm','II. CHIA DỮ LIỆU VÀ HUẤN LUYỆN')
    d.card(s,.6,1.75,5.85,2.95,'Đầu vào cho hạn h · A2','Train: [5.032, 25]\nCal: [2.582, 25]\nDev: [2.782, 25]\nID trạm là biến phân loại.',23)
    d.card(s,6.8,1.75,5.9,2.95,'Ba đầu ra riêng cho hạn h','1 regressor → lượng mm\n1 classifier → P(mưa ≥1 mm)\n1 classifier → P(mưa ≥50 mm)',22)
    d.text(s,.85,5.18,11.7,.45,'3 hạn × 3 đầu × 4 cấu hình × 3 seed = **108 estimator**.',23,True)
    d.band(s,'Không có một vector 25 biến chứa nhãn tương lai; y chỉ dùng khi fit / chấm.')

    s=page('lgb_params','LightGBM: cấu hình đã cố định','II. CHIA DỮ LIỆU VÀ HUẤN LUYỆN', 'scripts/run_gfs_station_pilot.py')
    table(s,['Tham số','Giá trị','Mục đích / cách hiểu'],[
        ['learning_rate','0,04','Bước cập nhật mỗi cây'],['num_leaves / max_depth','15 / 4','Giới hạn độ phức tạp'],
        ['min_child_samples','40','Không tạo lá quá ít mẫu'],['reg_lambda','2,0','Regularization L2'],
        ['subsample / colsample','0,9 / 0,9','Lấy mẫu hàng / đặc trưng'],['n_estimators','Tối đa 500','Số dùng thực tế do earlystop'],
        ['Amount / classifier','Tweedie p=1,5 / binary','Lượng mm / xác suất sự kiện']],
        'lgb_parameters',[4.5,3.0,4.75],row_h=.55,size=20)
    d.band(s,'Các giá trị được cố định; chưa có tìm kiếm siêu tham số rộng.',y=6.32,h=.43,size=17)

    s=page('lgb_earlystop','Chọn số cây bằng cal 2023, không bằng dev 2024','II. CHIA DỮ LIỆU VÀ HUẤN LUYỆN', 'fit_diagnostics.csv + training_audit.json')
    rows=[]
    for h in [1,2,3]:rows.append([f'Ngày {h}']+[str(int(diagnostics[(diagnostics.config=='A2')&(diagnostics.horizon==h)&(diagnostics.seed==seed)].best_iteration.iloc[0])) for seed in [17,29,43]])
    table(s,['A2 · số cây tốt nhất','Seed 17','Seed 29','Seed 43'],rows,'lgb_best_iterations',[5.2,2.35,2.35,2.35],row_h=.84,size=23)
    d.text(s,.8,5.24,11.8,.5,'Toàn bộ 36 regressor: **best 62–177 cây**, đã đánh giá 102–217 vòng.',22)
    d.band(s,'500 là trần cấu hình. Patience 40 không có nghĩa chỉ huấn luyện 40 cây.')

    s=page('calibration','Hiệu chỉnh xác suất khác chọn ngưỡng báo có','II. CHIA DỮ LIỆU VÀ HUẤN LUYỆN')
    table(s,['Bước','Dữ liệu / quy tắc'],[['Xác suất thô','Classifier riêng cho từng hạn, ngưỡng và seed'],
        ['Platt calibration','Fit sigmoid(logit(p)) bằng cal 2023'],['Gộp seed','Trung bình xác suất đã hiệu chỉnh của 3 seed'],
        ['Báo có / không','p ≥ 0,5; cutoff cố định, chưa tối ưu ngưỡng']],
        'calibration_steps',[4.0,8.25],row_h=.78,size=22)
    d.band(s,'Cal đã dùng cho earlystop + calibration; điểm cal không phải kiểm định ngoài mẫu.')

    s=page('gru_gate','Vì sao tiếp tục thử GRU? Gate chỉ dùng năm 2023','II. CHIA DỮ LIỆU VÀ HUẤN LUYỆN', 'run_summary.json')
    rows=[]
    for r in run['small_gru_gate_based_only_on_cal']:
        rows.append([f"Ngày {r['horizon']}",fmt(r['cal_mae_A2'],3),fmt(r['cal_mae_GFS'],3),fmt(r['cal_mae_CLIM'],3),f"{r['station_fraction_better_raw_gfs']*100:.1f}%",'Đạt' if r['passed'] else 'Chưa đạt'])
    table(s,['Hạn','MAE A2','MAE GFS','MAE khí hậu','Trạm tốt hơn GFS','Gate'],rows,
        'gru_gate',[1.3,2.0,2.0,2.4,2.9,1.65],row_h=.86,size=20)
    d.band(s,'Gate đạt ở ngày 3 → chạy GRU A2; không thay gate sau khi xem dev.')

    s=page('gru_shape','GRU A2: ba nhánh vào, ba đầu theo ngày','II. CHIA DỮ LIỆU VÀ HUẤN LUYỆN')
    table(s,['Nhánh','Tensor / biểu diễn','Đi tiếp'],[
        ['Mưa quá khứ','[batch, 7, 1]','GRU → vector 24'],['ID trạm','[batch]','Embedding → vector 4'],
        ['Ngữ cảnh 3 hạn','[batch, 3, 17]','17 số cho mỗi head ngày'],
        ['Ghép từng ngày','24 + 4 + 17 = 45','MLP 45 → 32 → 3']],
        'gru_shapes',[3.1,4.5,4.65],row_h=.78,size=22)
    d.band(s,'Đầu ra: lượng [batch,3] và xác suất [batch,3,2] · 7.001 tham số.')

    s=page('gru_train','GRU: chuẩn hóa và hàm mất mát thực tế','II. CHIA DỮ LIỆU VÀ HUẤN LUYỆN')
    table(s,['Thành phần','Cách làm'],[['Chuỗi 7 ngày','log1p(mưa) → chuẩn hóa bằng train'],
        ['17 biến ngữ cảnh','Chuẩn hóa mean/std chỉ từ train'],['Lượng y','Chia scale=max(mean y train,1); dự báo nhân trả scale'],
        ['Loss chung','Tweedie p=1,5 + 0,5 × BCE sự kiện'],['Đầu ra lượng','Softplus để không âm']],
        'gru_preprocess',[3.1,9.15],row_h=.73,size=21)
    d.band(s,'Cùng thông tin A2, nhưng cách biểu diễn và cơ chế loss khác LightGBM.')

    s=page('gru_params','GRU: cấu hình cố định, chọn epoch bằng cal','II. CHIA DỮ LIỆU VÀ HUẤN LUYỆN', 'scripts/run_gfs_station_gru.py + gru_summary.json')
    table(s,['Thiết lập','Giá trị'],[['GRU / head / dropout','24 / 32 / 0,1'],['AdamW: LR / weight decay','0,001 / 0,001'],
        ['Batch / clip gradient','128 / 1,0'],['Tối đa epoch / patience','80 / 12'],
        ['Chọn checkpoint','Loss chung trên cal 2023']],
        'gru_parameters',[5.1,7.15],row_h=.67,size=22)
    d.text(s,.8,5.84,11.8,.4,'Seed 17 / 29 / 43: best epoch **18 / 18 / 20**; dừng **30 / 30 / 32**.',20)

    s=page('tuning_status','“Tinh chỉnh” đã làm đến đâu?','II. CHIA DỮ LIỆU VÀ HUẤN LUYỆN')
    table(s,['Đã cố định','Đã lựa chọn bằng cal','Chưa thực hiện'],[
        ['Cửa sổ / A0–A3 / các seed','Số cây tốt nhất của LightGBM','Grid / Random Search / Optuna'],
        ['LR, depth, leaves; cấu trúc GRU','Epoch tốt nhất của GRU','Tuning loss weight / cửa sổ'],
        ['Cutoff xác suất 0,5','Platt calibration và gate GRU','Tối ưu ngưỡng / cân bằng lớp']],
        'tuning_status',[4.0,4.25,4.0],row_h=1.03,size=21)
    d.band(s,'Các lựa chọn hiện tại không được tối ưu theo kết quả dev 2024.')

    s=page('seeds','Ba seed là ba lần học, không phải ba tập dữ liệu','II. CHIA DỮ LIỆU VÀ HUẤN LUYỆN')
    for x,title,body in [(.6,'Seed 17','Fit + earlystop\n+ calibration'),(4.75,'Seed 29','Cùng dữ liệu\nđổi ngẫu nhiên'),(8.9,'Seed 43','Cùng thiết lập\nđổi ngẫu nhiên')]:d.card(s,x,1.9,3.8,2.35,title,body,23)
    d.text(s,.85,4.95,11.7,1.02,'Dự báo cuối = **trung bình 3 dự báo**.\nBiến động theo seed ≠ thêm các đợt mưa độc lập.',24)
    d.band(s,'Đã gộp seed nhất quán cho cả lượng mm và xác suất.')

    s=page('amount_metrics','Đọc sai số lượng mưa bằng ba góc nhìn','III. ĐÁNH GIÁ')
    table(s,['Chỉ số','Ý nghĩa dễ hiểu','Vì sao dùng?','Chiều tốt'],[
        ['MAE','Trung bình sai lệch tuyệt đối bao nhiêu mm','Đọc được mức sai số điển hình','Nhỏ hơn'],
        ['RMSE','Sai số nhấn mạnh các lỗi lớn','Không che những lần dự báo sai nặng','Nhỏ hơn'],
        ['Bias','Dự báo thừa hay thiếu mưa trung bình','Phát hiện lệch có hệ thống','Gần 0']],
        'amount_metric_definitions',[1.4,4.3,4.8,1.75],row_h=1.03,size=20)
    d.band(s,'MAE thấp chưa chắc RMSE thấp; cần trình bày cùng nhau.')

    s=page('prob_metrics','BS và BSS chấm chất lượng xác suất','III. ĐÁNH GIÁ')
    table(s,['Chỉ số','Công thức / cách hiểu','Chiều tốt'],[['BS','Trung bình (p − sự kiện 0/1)²','Nhỏ hơn'],
        ['BSS','1 − BS mô hình / BS khí hậu','Lớn hơn; >0 là hơn tham chiếu']],
        'probability_metric_definitions',[1.6,8.1,2.55],row_h=.95,size=23)
    d.text(s,.8,4.85,11.75,.85,'Ví dụ giả định: BS khí hậu = 0,10; BS mô hình = 0,08\n→ BSS = +0,20: giảm 20% sai số Brier, không phải đúng 20% số ngày.',22)
    d.band(s,'GFS đơn trị không được gán một BSS xác suất giả trong bảng hiện tại.')

    s=page('event_metrics','POD phải đọc cùng FAR và CSI','III. ĐÁNH GIÁ')
    table(s,['Chỉ số','Công thức','Ý nghĩa','Chiều tốt'],[['POD','H / (H+M)','Bắt được bao nhiêu sự kiện thật?','Lớn hơn'],
        ['FAR','F / (H+F)','Trong các lần báo có, bao nhiêu bị nhầm?','Nhỏ hơn'],
        ['CSI','H / (H+M+F)','Cân nhắc trúng, bỏ sót và báo nhầm','Lớn hơn']],
        'event_metric_definitions',[1.3,2.7,6.5,1.75],row_h=.95,size=21)
    d.band(s,'Báo có quá nhiều có thể làm POD cao, đồng thời FAR cũng cao.')

    s=page('macro_ci','Trạm và các đợt mưa không độc lập như số dòng','III. ĐÁNH GIÁ')
    bullets(s,['Macro: tính chỉ số từng trạm, sau đó trung bình giữa 57 trạm.',
        'Micro: gộp dòng; trạm nhiều mẫu có ảnh hưởng lớn hơn.',
        'Bootstrap: khối 4 issue, giữ các trạm cùng đợt đi cùng nhau.',
        '1.000 lần lấy mẫu → CI 95% của chênh lệch MAE.',
        'CI chứa 0: chưa đủ bằng chứng cải thiện ổn định.'],gap=.78,size=22)
    d.band(s,'Huấn luyện hiện chưa cân bằng theo trạm; đánh giá chính dùng macro đồng trọng số.')

    s=page('mae','Kết quả MAE trên 57 trạm: không có một bên thắng hết','IV. KẾT QUẢ DEV 2024', 'point_metrics.csv')
    matrix(s,MODELS,'macro_mae','result_mae',row_h=.47,size=21)
    d.band(s,'Đơn vị mm cho mỗi tổng 24h · In đậm = thấp nhất trong cột, chưa là kiểm định.',y=6.21,h=.52,size=18)

    s=page('tradeoff','MAE, RMSE và Bias có thể dẫn đến lựa chọn khác nhau','IV. KẾT QUẢ DEV 2024', 'point_metrics.csv')
    rows=[]
    for h in [1,2,3]:
        for m in ['GFS','A2','GRU_A2']:
            r=point[(point.fold=='dev')&(point.horizon==h)&(point.model==m)].iloc[0]
            rows.append([str(h),LABELS[m],fmt(r.macro_mae),fmt(r.macro_rmse),signed(r.macro_bias,2)])
    styles={}
    for h in [1,2,3]:
        group=point[(point.fold=='dev')&(point.horizon==h)&point.model.isin(['GFS','A2','GRU_A2'])]
        for j,key in enumerate(['macro_mae','macro_rmse','macro_bias'],2):
            target=group[key].abs().min() if key=='macro_bias' else group[key].min()
            for mi,m in enumerate(['GFS','A2','GRU_A2']):
                value=group[group.model.eq(m)][key].iloc[0]
                if np.isclose(abs(value) if key=='macro_bias' else value,target):
                    styles[f'{(h-1)*3+mi+1},{j}']=dict(bold=True,color=TEAL)
    table(s,['Ngày','Phương pháp','MAE ↓','RMSE ↓','Bias ≈0'],rows,'point_tradeoffs',[1.0,4.2,2.3,2.4,2.35],row_h=.43,size=20,styles=styles)
    d.band(s,'GRU ngày 3: MAE 8,00 và RMSE 17,62; A2: 8,44 và 23,77 mm.',y=6.22,h=.5,size=19)

    s=page('bss','Chất lượng xác suất phụ thuộc ngưỡng và hạn','IV. KẾT QUẢ DEV 2024', 'probability_metrics.csv')
    d.text(s,.7,1.52,5.75,.4,'BSS ≥1 mm / 24h',22,True,TEAL)
    d.text(s,7.0,1.52,5.75,.4,'BSS ≥50 mm / 24h',22,True,TEAL)
    ms=['CLIM','A0','A1','A2','A3','GRU_A2']
    matrix(s,ms,'macro_bss','bss_1',source='prob',threshold=1,x=.55,w=6,y=2.05,row_h=.48,size=18)
    matrix(s,ms,'macro_bss','bss_50',source='prob',threshold=50,x=6.8,w=6,y=2.05,row_h=.48,size=18)
    d.band(s,'BSS >0: tốt hơn tham chiếu; không phải % ngày đúng. Ngưỡng 50mm là thăm dò.',y=6.13,size=18)

    s=page('event_wet','Phát hiện mưa ≥1 mm: đọc ba mô hình cùng lúc','IV. KẾT QUẢ DEV 2024', 'event_metrics.csv')
    rows=[]
    for h in [1,2,3]:
        for m in ['GFS','A2','GRU_A2']:
            r=event[(event.fold=='dev')&(event.horizon==h)&(event.model==m)&(event.threshold_mm==1)].iloc[0]
            rows.append([str(h),LABELS[m],fmt(r.macro_csi,3),fmt(r.macro_pod,3),fmt(r.macro_far,3)])
    styles={}
    for h in [1,2,3]:
        group=event[(event.fold=='dev')&(event.horizon==h)&event.model.isin(['GFS','A2','GRU_A2'])&event.threshold_mm.eq(1)]
        for j,key in enumerate(['macro_csi','macro_pod','macro_far'],2):
            target=group[key].min() if key=='macro_far' else group[key].max()
            for mi,m in enumerate(['GFS','A2','GRU_A2']):
                if np.isclose(group[group.model.eq(m)][key].iloc[0],target):
                    styles[f'{(h-1)*3+mi+1},{j}']=dict(bold=True,color=TEAL)
    table(s,['Ngày','Phương pháp','CSI ↑','POD ↑','FAR ↓'],rows,'event_wet',[1.0,4.2,2.3,2.4,2.35],row_h=.43,size=20,styles=styles)
    d.band(s,'GFS: lượng ≥1mm. Mô hình xác suất: p≥0,5. Không đánh giá riêng POD.',y=6.22,h=.5,size=18)

    s=page('event_heavy','Ngưỡng ≥50 mm: ít đợt mưa, điểm số dễ dao động','IV. KẾT QUẢ DEV 2024', 'event_metrics.csv + probability_metrics.csv')
    rows=[]
    for h in [1,2,3]:
        for m in ['GFS','A2','GRU_A2']:
            r=event[(event.fold=='dev')&(event.horizon==h)&(event.model==m)&(event.threshold_mm==50)].iloc[0]
            rows.append([str(h),LABELS[m],fmt(r.macro_csi,3),fmt(r.macro_pod,3),fmt(r.macro_far,3),f'{int(r.stations_with_pod)}/{int(r.stations_with_far)}'])
    table(s,['Ngày','Phương pháp','CSI','POD','FAR','N POD/FAR'],rows,'event_heavy',[.95,3.3,1.8,1.8,1.8,2.6],row_h=.43,size=19)
    d.band(s,'94 / 104 / 114 sự kiện-trạm; chỉ 11 / 10 / 12 issue có sự kiện, không phải số đợt độc lập.',y=6.22,h=.5,size=17)

    s=page('ci','Điểm A2 thấp hơn GFS, nhưng CI còn chứa 0','IV. KẾT QUẢ DEV 2024', 'paired_bootstrap.csv')
    rows=[]
    for h in [1,2,3]:
        r=ci[(ci.fold=='dev')&(ci.model=='A2')&(ci.reference=='GFS')&(ci.horizon==h)].iloc[0]
        rows.append([f'Ngày {h}',signed(r.mae_difference),f'[{signed(r.ci95_low)}; {signed(r.ci95_high)}]','Có'])
    table(s,['Hạn','MAE A2 − GFS (mm)','CI 95% (mm)','Chứa 0?'],rows,'a2_gfs_ci',[1.6,4.1,4.8,1.75],row_h=.91,size=22)
    d.band(s,'Kết luận hiện tại: tín hiệu sơ bộ, chưa chứng minh hơn GFS một cách ổn định.')

    s=page('feature_ci','Thêm nhóm biến: cần xem chênh lệch và CI','IV. KẾT QUẢ DEV 2024', 'paired_bootstrap.csv')
    rows=[]
    for model,reference,label in [('A1','A0','+ Mưa trạm'),('A2','A1','+ Khí tượng GFS'),('A3','A2','+ Địa hình')]:
        for h in [1,2,3]:
            r=ci[(ci.fold=='dev')&(ci.model==model)&(ci.reference==reference)&(ci.horizon==h)].iloc[0]
            rows.append([label,str(h),signed(r.mae_difference),f'[{signed(r.ci95_low)}; {signed(r.ci95_high)}]'])
    table(s,['Thông tin thêm','Ngày','Δ MAE mm','CI 95% mm'],rows,'feature_addition_ci',[4.0,1.0,2.5,4.75],row_h=.43,size=19)
    d.band(s,'Phần lớn CI chứa 0; một ô âm chưa đủ sau nhiều phép so sánh thăm dò.',y=6.22,h=.5,size=18)

    s=page('expand','Mở 20 → 57 trạm: phải so trên cùng đối tượng','IV. KẾT QUẢ DEV 2024', 'cohort_scope_metrics.csv + matched_original20_bootstrap.csv')
    d.image(s,DATA/'matched_original20.png',.65,1.55,12.0,4.48)
    d.band(s,'MAE A2: 6,15/7,37/7,75 → 5,91/7,40/8,66 mm trên cùng 20 trạm.',y=6.21,h=.52,size=19)

    s=page('limits','Những giới hạn cần nói thẳng trong báo cáo','V. GIỚI HẠN VÀ HƯỚNG TIẾP')
    bullets(s,['Lịch issue mỗi 7 ngày; chưa kiểm chứng dự báo hằng ngày đầy đủ.',
        'Độ trễ 1h/8h và độ chính xác cảm biến chưa được chứng nhận đầy đủ.',
        'Hai trạm có ít cửa sổ train; chưa kiểm định trạm chưa thấy.',
        'Cal dùng lại cho earlystop + Platt: điểm cal có thể lạc quan.',
        'Chưa ép thứ tự xác suất: A2 có 188/8.346 dòng dev vi phạm (2,25%).'],size=21,gap=.78)
    d.band(s,'Audit không làm thay đổi dự báo, điểm số hoặc dữ liệu gốc của thí nghiệm.')

    s=page('answers','Có thể kết luận gì ở thời điểm hiện tại?','V. GIỚI HẠN VÀ HƯỚNG TIẾP')
    table(s,['Câu hỏi','Trả lời có bằng chứng'],[['Đã huấn luyện trên 57 trạm?','Có; dữ liệu, mô hình và phép chấm đã replay'],
        ['Thêm biến luôn cải thiện?','Chưa; phụ thuộc chỉ số, hạn và CI'],['GRU hay LightGBM luôn tốt hơn?','Không; ngày 3 và lượng/xác suất có đánh đổi'],
        ['Đã chứng minh hơn GFS ổn định?','Chưa; CI A2−GFS còn chứa 0']],
        'defensible_conclusions',[5.4,6.85],row_h=.85,size=21)
    d.band(s,'Kết quả nghiên cứu sơ bộ có giá trị khi trình bày đúng phạm vi.')

    s=page('next','Bước tiếp theo cần giải quyết bất định hiện có','V. GIỚI HẠN VÀ HƯỚNG TIẾP')
    bullets(s,['Protocol mới: lịch issue hằng ngày và độ nhạy trễ quan trắc/NWP.',
        'Tuning có kiểm soát trên cal / folds thời gian; không dùng dev để chọn.',
        'Thử bỏ nhóm biến; cân bằng dữ liệu và kiểm định trạm chưa thấy.',
        'Ràng buộc xác suất: P(≥50mm) ≤ P(≥1mm).',
        'Khóa thiết kế trước khi mở kiểm định cuối 2025.'],gap=.78,size=22)
    d.band(s,'Giữ nguyên thí nghiệm hiện tại để kiểm chứng và so sánh phiên bản sau.')
    main_count=len(d.slides)

    s=page('catalog_base','Phụ lục: 16 cột của A0 + lịch sử mưa','PHỤ LỤC KỸ THUẬT', 'src/gfs_station_dataset.py')
    table(s,['Khối','Tên cột','Số'],[['Mưa dự báo','gfs_rain_mm','1'],['Lịch + vị trí / ID','sin_doy, cos_doy; latitude, longitude; station_code','5'],
        ['Bảy ngày mưa','rain_lag_day1_mm … rain_lag_day7_mm','7'],
        ['Mưa gần issue','rain_recent1h_mm, rain_recent6h_mm, rain_recent24h_mm','3']],
        'catalog_A01',[2.8,8.45,1.0],row_h=.82,size=19)
    d.band(s,'Tổng A0=6; A1=16. Không lấy tất cả cột số của file làm X.')

    s=page('catalog_physical','Phụ lục: 16 cột bổ sung ở A2 và A3','PHỤ LỤC KỸ THUẬT', 'src/gfs_station_dataset.py')
    table(s,['Khối','Tên cột / công thức','Số'],[
        ['Trạng thái GFS','gfs_t850_c, gfs_rh850_pct, gfs_u850,\ngfs_v850, gfs_pwat','5'],
        ['Dẫn xuất khí tượng','gfs_q850_gkg, gfs_qflux_e,\ngfs_qflux_n, gfs_wspd850','4'],
        ['DEM / gradient','dem_elev_m, dem_mean_5km_m, dem_std_5km_m,\ndem_slope_east, dem_slope_north','5'],
        ['Tương tác','wind_upslope = u·slopeE + v·slopeN\nmoist_upslope = wind_upslope × q','2']],
        'catalog_A23',[2.8,8.45,1.0],row_h=.86,size=18)
    d.band(s,'A2 thêm 9 → 25 biến; A3 thêm 7 → 32 biến.',y=6.2,h=.5,size=19)

    s=page('all_rmse_bias','Phụ lục: RMSE và Bias đầy đủ','PHỤ LỤC KẾT QUẢ', 'point_metrics.csv')
    d.text(s,.7,1.52,5.75,.4,'RMSE ↓ · mm',22,True,TEAL);d.text(s,7.0,1.52,5.75,.4,'Bias ≈0 · mm',22,True,TEAL)
    matrix(s,MODELS,'macro_rmse','full_rmse',x=.55,w=6,y=2.05,row_h=.43,size=18)
    matrix(s,MODELS,'macro_bias','full_bias',x=6.8,w=6,y=2.05,row_h=.43,size=18)
    d.band(s,'Macro theo trạm; số in đậm chỉ thể hiện điểm tốt nhất trong cột.',y=6.2,h=.5,size=18)

    for threshold in [1.,50.]:
        s=page(f'full_prob_{threshold:g}',f'Phụ lục: BS/BSS đầy đủ ở ≥{threshold:g} mm','PHỤ LỤC KẾT QUẢ', 'probability_metrics.csv')
        d.text(s,.7,1.52,5.75,.4,'BS ↓',22,True,TEAL);d.text(s,7.0,1.52,5.75,.4,'BSS ↑',22,True,TEAL)
        ms=['CLIM','A0','A1','A2','A3','GRU_A2']
        matrix(s,ms,'macro_bs',f'full_bs_{threshold:g}',source='prob',threshold=threshold,x=.55,w=6,y=2.05,row_h=.5,size=18)
        matrix(s,ms,'macro_bss',f'full_bss_{threshold:g}',source='prob',threshold=threshold,x=6.8,w=6,y=2.05,row_h=.5,size=18)
        d.band(s,'Số BSS âm được đánh đỏ. Tham chiếu khí hậu có BSS bằng 0.',size=18)

    s=page('coherence','Phụ lục: hai xác suất chưa có ràng buộc thứ tự','PHỤ LỤC KIỂM TRA MỚI', 'training_audit.json')
    rows=[[LABELS[r['model']],str(r['violations']),fmt(r['fraction']*100)+'%',fmt(max(r['max_probability_gap'],0),3),str(r['decision_contradictions'])] for r in audit['probability_coherence_dev']]
    table(s,['Phương pháp','Dòng vi phạm','Tỷ lệ dev','Gap lớn nhất','Mâu thuẫn p≥0,5'],rows,
        'prob_coherence',[3.1,2.3,2.0,2.1,2.75],row_h=.68,size=19)
    d.band(s,'Vi phạm: P(≥50) > P(≥1). Chưa sửa xác suất trong báo cáo hiện tại.',size=19)

    s=page('release','Phụ lục: 7 chu kỳ có timestamp archive không rõ','PHỤ LỤC ĐỘ NHẠY')
    r=pd.read_csv(DATA/'release_sensitivity_metrics.csv');rows=[]
    for h in [1,2,3]:
        f=r[(r.fold=='dev')&(r.horizon==h)].set_index('model')
        rows.append([f'Ngày {h}',fmt(f.loc['A2_primary','macro_mae']),fmt(f.loc['A2_omit_ambiguous_train_cycles','macro_mae'])])
    table(s,['Hạn','A2 chính · MAE mm','Bỏ 7 chu kỳ train · MAE mm'],rows,
        'release_sensitivity',[2.2,4.7,5.35],row_h=.94,size=23)
    d.band(s,'Last-Modified ≠ thời điểm phát hành gốc. Đây là kiểm tra độ nhạy nguồn.')

    s=page('checks','Phụ lục: đã kiểm tra cái gì, chưa đảm bảo cái gì?','PHỤ LỤC TÁI TẠO')
    table(s,['Bằng chứng','Kết quả / giới hạn'],[['Tests dữ liệu / thời gian / mô hình','53 tests đã đạt'],
        ['Dữ liệu và source forecast','31.188 dòng; replay 171 mẫu nội suy GRIB'],['Checkpoint / metric','36 lượng +72 classifier +3 GRU; scaler train-only'],
        ['Chưa chứng nhận','Cảm biến, vị trí lịch sử, độ trễ, kỹ năng cuối']],
        'verification_summary',[5.0,7.25],row_h=.84,size=21)
    d.band(s,'Kiểm tra code và dữ liệu ghép đúng không đồng nghĩa dự báo đã đạt yêu cầu vận hành.')

    s=page('faq_data','Hỏi–đáp: dữ liệu và đầu ra','PHỤ LỤC BẢO VỆ BÁO CÁO')
    table(s,['Câu hỏi','Cách trả lời ngắn'],[['57 trạm hay 57 ô?','57 điểm đo; GFS là lưới nội suy làm predictor.'],
        ['Một mô hình hay 57 mô hình?','Học chung nhiều trạm, có đầu theo từng hạn.'],['Dự báo ngày, sao có đầu vào giờ?','Độ phân giải đầu vào và đầu ra không bắt buộc giống.'],
        ['Dự báo GFS đã có, học máy để làm gì?','Học chuyển dự báo lưới thành dự báo phù hợp trạm.']],
        'faq_data',[5.0,7.25],row_h=.86,size=21)
    d.band(s,'Không gọi dữ liệu lưới là quan trắc trực tiếp tại trạm.')

    s=page('faq_models','Hỏi–đáp: mô hình, tuning và kiểm định','PHỤ LỤC BẢO VỆ BÁO CÁO')
    table(s,['Câu hỏi','Cách trả lời ngắn'],[['Vì sao chưa cần TFT/Informer?','Chưa có điểm trên NWP57; ưu tiên kiểm chứng dữ liệu.'],
        ['Đã tuning tối ưu chưa?','Chưa; cố định tham số, chọn checkpoint và Platt bằng cal.'],
        ['POD 0,4 có tốt không?','Phụ thuộc ngưỡng/hạn; phải đọc kèm FAR và CSI.'],
        ['Tại sao không gọi 2024 là test cuối?','Đã dùng phân tích phát triển; 2025 vẫn giữ kín.']],
        'faq_models',[5.0,7.25],row_h=.86,size=21)
    d.band(s,'Mô tả đúng những gì đã chạy; không suy kết quả kiến trúc chưa thử.')

    s=page('references','Nguồn kiểm chứng và tài liệu phương pháp','PHỤ LỤC NGUỒN')
    refs=[('NOAA GFS','https://registry.opendata.aws/noaa-gfs-bdp-pds/'),('Mapzen DEM','https://registry.opendata.aws/terrain-tiles/'),
        ('LightGBM 4.5','https://lightgbm.readthedocs.io/en/v4.5.0/Parameters.html'),
        ('PyTorch GRU','https://github.com/pytorch/pytorch/tree/v2.5.1/torch/nn/modules'),
        ('Platt hiện thực','https://github.com/scikit-learn/scikit-learn/tree/1.6.1/sklearn/linear_model')]
    for i,(label,url) in enumerate(refs):
        d.text(s,.8,1.65+i*.8,2.45,.55,label,21,True,TEAL)
        d.text(s,3.4,1.65+i*.8,9.15,.64,url,17,url=url)
    d.band(s,'Kết quả: reports/gfs_station_57_2026_11_10 · Mã và aggregate được version hóa.',size=18)
    s['note']+='\n\n'+'\n'.join(label+': '+url for label,url in refs)

    s=page('files','Đọc thêm / tái tạo mà không cần đoán cách làm','PHỤ LỤC NGUỒN')
    table(s,['Muốn xem gì?','File trong reports/gfs_station_57_2026_11_10/'],[
        ['Chia dữ liệu / mô hình','protocol.json, dataset_audit.json, fit_diagnostics.csv'],
        ['Lượng / xác suất / sự kiện','point_metrics.csv, probability_metrics.csv, event_metrics.csv'],
        ['Bất định / mở rộng trạm','paired_bootstrap.csv, matched_original20_bootstrap.csv'],
        ['Tái tạo và kiểm tra','verification.json, model_verification.json, gru_summary.json']],
        'source_files',[3.5,8.75],row_h=.88,size=19)
    d.band(s,f'Thuyết trình chính: slide 1–{main_count}; phụ lục: chi tiết biến, bảng số và hỏi–đáp.',size=18)

    assert set(roles)==set(NOTES), 'Every slide must have reviewed speaker notes.'
    d.save(OUT/(STEM+'.pptx'),OUT/(STEM+'.html'),OUT/'slide_scene.json')
    # The shared renderer only styles the first paragraph of multiline table
    # cells. Apply the same style to every native paragraph, without touching
    # any prior/user-authored presentation.
    prs=Presentation(OUT/(STEM+'.pptx'))
    for native,slide in zip(prs.slides,d.slides):
        for shape,spec in zip(native.shapes,slide['shapes']):
            if spec['kind']!='table':continue
            for ri,row in enumerate([spec['headers']]+spec['rows']):
                for cj,_ in enumerate(row):
                    style=spec['styles'].get(f'{ri},{cj}',{})
                    cell_frame=shape.table.cell(ri,cj).text_frame
                    cell_frame.word_wrap=True
                    for p in cell_frame.paragraphs:
                        p.alignment=PP_ALIGN.CENTER;p.space_before=p.space_after=Pt(0);p.line_spacing=1.
                        for r in p.runs:
                            r.font.name='Arial';r.font.size=Pt(spec['size']);r.font.bold=ri==0 or style.get('bold',False)
                            r.font.color.rgb=RGBColor.from_string('FFFFFF' if ri==0 else style.get('color',NAVY))
    prs.core_properties.title='Dự báo mưa ngắn hạn tại 57 trạm: dữ liệu, huấn luyện và kết quả'
    prs.core_properties.author='Nhóm PBL6';prs.core_properties.subject='GFS + Vrain, LightGBM và GRU; dev2024, 2025 giữ kín'
    prs.save(OUT/(STEM+'.pptx'))
    html_path=OUT/(STEM+'.html')
    html_path.write_text(html_path.read_text(encoding='utf8').replace('PBL6 — Báo cáo mưa vùng','PBL6 — Dự báo mưa tại 57 trạm'),encoding='utf8')
    guide=['# Ghi chú thuyết trình — GFS + Vrain, 57 trạm','',
        f'**{main_count} slide chính + {len(d.slides)-main_count} phụ lục.** Dùng ghi chú để giải thích, không cần đọc hết chữ trên slide. '
        'Đây là báo cáo kết quả đã có; không huấn luyện lại mô hình.','']
    for slide in d.slides:
        guide += [f"## Slide {slide['number']:02d} — {slide['title']}",'',slide['note'],'',f"Nguồn: {slide['source']}",'']
    (OUT/'GHI_CHU_THUYET_TRINH.md').write_text('\n'.join(guide),encoding='utf8')
    sources={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in DATA.glob('*') if p.suffix in ['.json','.csv','.png']}
    for path in ['scripts/run_gfs_station_pilot.py','scripts/run_gfs_station_gru.py','src/gfs_station_dataset.py']:
        sources[path]=sha(ROOT/path)
    manifest=dict(slides=len(d.slides),main_slides=main_count,appendix_slides=len(d.slides)-main_count,roles=roles,
        experiment='gfs_station_57_2026_11_10',station_count=57,training_performed_for_slides=False,test2025_read=False,
        code_sha256=sha(Path(__file__)),notes_sha256=sha(ROOT/'scripts/gfs_station_slide_notes.py'),sources=sources,
        private_pdf_expected='data/operational/gfs_station_slides_2026_11_10/'+STEM+'.pdf',
        metric_tables={spec['tag']:dict(slide=slide['number'],headers=spec['headers'],rows=spec['rows']) for slide in d.slides for spec in slide['shapes'] if spec['kind']=='table' and spec.get('tag')},
        files={name:dict(sha256=sha(OUT/name),bytes=(OUT/name).stat().st_size) for name in [STEM+'.pptx',STEM+'.html','slide_scene.json','GHI_CHU_THUYET_TRINH.md','training_audit.json']})
    (OUT/'build_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:manifest[k] for k in ['slides','main_slides','appendix_slides','station_count','training_performed_for_slides']},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
