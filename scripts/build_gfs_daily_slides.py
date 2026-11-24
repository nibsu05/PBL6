"""Build an editable daily-v2 deck from verified aggregates; never read 2025."""
from pathlib import Path
import hashlib
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import numpy as np
import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Pt
from presentation_layout import Deck,NAVY,TEAL,RED,MUTED

DATA=ROOT/'reports/gfs_station_daily_v2_2026_11_10'
OUT=ROOT/'reports/gfs_daily_slides_2026_11_11'
PRIVATE=ROOT/'data/operational/gfs_daily_slides_2026_11_11'
STEM='PBL6_MUA_TRAM_HANG_NGAY_V2'
FOOT='57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025'
LABELS={'ZERO':'Luôn 0 mm','CLIM':'Khí hậu','PERSISTENCE':'Lặp mưa gần nhất','GFS':'GFS thô','MOS':'MOS đơn giản',
        **{f'LGB_N{i}':f'LGB N{i}' for i in range(6)},'GRU_N3':'GRU N3','GRU_N5':'GRU N5',
        'LGB_N3_delay3':'LGB N3 · trễ 3h','LGB_N3_delay6':'LGB N3 · trễ 6h'}
ALL=['ZERO','PERSISTENCE','GFS','CLIM','MOS']+[f'LGB_N{i}' for i in range(6)]+['GRU_N3','GRU_N5']
CORE=['ZERO','GFS','CLIM','MOS','LGB_N1','LGB_N3','GRU_N3','GRU_N5']


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def fmt(value,digits=3):return '—' if pd.isna(value) else f'{float(value):.{digits}f}'.replace('.',',')
def read(name):return json.loads((DATA/(name+'.json')).read_text(encoding='utf8'))


def main():
    OUT.mkdir(parents=True,exist_ok=True);PRIVATE.mkdir(parents=True,exist_ok=True)
    assert read('model_verification')['status']=='passed'
    files=['point_metrics','probability_metrics','event_metrics','paired_bootstrap','conditional_amount_metrics',
           'seed_metrics','tree_tuning_trials','gru_tuning_trials','label_distribution']
    csv={name:pd.read_csv(DATA/(name+'.csv')) for name in files}
    protocol=read('protocol');audit=read('dataset_audit');trees=read('tree_selection');gru=read('gru_selection')
    d=Deck();roles={};checks=[]
    def page(role,title,section,note,source='protocol.json'):
        assert role not in roles,role
        note+='\n\nBối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.'
        s=d.slide(title,section,FOOT+' · '+source,note);s['role']=role;roles[role]=s['number'];return s
    def bullets(s,items,y=1.65,gap=.83,size=23):
        for i,line in enumerate(items):d.text(s,.72,y+i*gap,11.9,gap-.09,'• '+line,size)
    def table(s,tag,headers,rows,widths=None,y=1.65,row_h=.60,size=21,x=.55,w=12.25,styles=None):
        return d.table(s,headers,rows,x=x,y=y,w=w,row_h=row_h,widths=widths,size=size,styles=styles,tag=tag)
    def select(file,filters):
        f=csv[file]
        for col,v in filters.items():f=f[f[col].eq(v)]
        assert len(f)==1,(file,filters,len(f));return f.iloc[0]
    def value(tag,row,col,file,filters,key,digits=3):
        v=select(file,filters)[key]
        checks.append(dict(tag=tag,row=row,col=col,file=file+'.csv',filters=filters,key=key,digits=digits,kind='scalar'))
        return fmt(v,digits)
    def interval(tag,row,col,model,reference,h,fun,metric):
        filters=dict(model=model,reference=reference,horizon=h,functional=fun,metric=metric)
        r=select('paired_bootstrap',filters)
        checks.append(dict(tag=tag,row=row,col=col,file='paired_bootstrap.csv',filters=filters,kind='interval',digits=3))
        return f'{fmt(r.difference)} [{fmt(r.ci95_low)}; {fmt(r.ci95_high)}]'
    def matrix(s,tag,models,file,key,fun=None,threshold=None,y=1.6,row_h=.48,size=21,x=.55,w=12.25):
        rows=[];raw=[];styles={}
        for i,m in enumerate(models):
            line=[LABELS[m]];numeric=[]
            for j,h in enumerate((1,2,3),1):
                f=dict(fold='dev',model=m,horizon=h)
                if fun:f['functional']=fun
                if threshold is not None:f['threshold_mm']=threshold
                numeric.append(float(select(file,f)[key]));line.append(value(tag,i,j,file,f,key))
            rows.append(line);raw.append(numeric)
        low=key!='macro_bss'
        for j in range(3):
            vals=[abs(v[j]) if key=='macro_bias' else v[j] for v in raw];best=(min if low else max)(vals)
            for i,v in enumerate(vals):
                bold=bool(np.isclose(v,best,rtol=1e-9,atol=1e-12));color=RED if key=='macro_bss' and raw[i][j]<0 else TEAL if bold else NAVY
                styles[f'{i+1},{j+1}']=dict(bold=bold,color=color)
        return table(s,tag,['Phương pháp','Ngày 1','Ngày 2','Ngày 3'],rows,[w*.40,w*.20,w*.20,w*.20],y,row_h,size,x,w,styles)

    s=page('title','Dự báo mưa 1–3 ngày tại 57 trạm','BÁO CÁO HẰNG NGÀY V2 · 11/11/2026',
        'Mở đầu bằng mục tiêu nghiên cứu: dùng khí tượng dự báo và lịch sử mưa tại trạm để dự báo ba lượng mưa 24 giờ. Nhóm đánh giá giá trị bổ sung đặc trưng và so với các đối chứng đơn giản. Đây là bản hằng ngày mới, có kiểm soát tuning và xác suất; không phải bộ kết quả cũ dùng 208 issue cách nhau một tuần.')
    d.text(s,.75,1.7,11.8,1.2,'GFS + Vrain → LightGBM / GRU\nDữ liệu, cách học, kết quả và giới hạn',31,True)
    for x,title,body in [(.7,'57 trạm','Dự báo tại từng điểm đo'),(4.85,'3 ngày','Ba tổng 24h riêng'),(9.,'2024: dev','2025: dành kiểm định cuối')]:d.card(s,x,3.4,3.65,1.75,title,body,19)
    d.band(s,'Báo cáo kết quả đã chạy và đã đối chiếu lại checkpoint.',y=5.8,h=.64,size=22)

    s=page('takeaways','Ba điều cần nhớ trước khi xem các bảng','KẾT QUẢ CHÍNH',
        'Tránh mở đầu bằng một loạt con số chưa có bối cảnh. Thông điệp thứ nhất là khí tượng thô dự báo có giá trị. Thứ hai, giá trị dẫn xuất không giống nhau ở LightGBM và GRU. Thứ ba, điểm trung bình cải thiện không đồng nghĩa cảnh báo mưa lớn đã đủ tin cậy. Các kết luận thống kê đều nằm trong phạm vi dev 2024 và khoảng tin cậy thăm dò.', 'KET_LUAN.md')
    bullets(s,['**Thêm khí tượng GFS thô:** giảm sai số trong phép thử này.',
        '**Thêm dẫn xuất:** có tín hiệu ở GRU ngày 1–2; chưa rõ ở LightGBM.',
        '**Mưa lớn:** xác suất có ích hơn khí hậu, nhưng báo nhầm còn nhiều.'],gap=1.12,size=25)
    d.band(s,'2024 giúp lựa chọn hướng nghiên cứu; 2025 dành cho phép kiểm tra cuối.')

    s=page('target','Dự báo điều gì tại mỗi trạm?','I. BÀI TOÁN',
        'Ngày dự báo là cửa sổ 19 giờ đến 19 giờ hôm sau, không phải ngày lịch 0–24 giờ. Mỗi nhãn là tổng 24 giờ tại đúng trạm. Ba nhãn không chồng nhau. Không dùng tổng các trạm hay mưa trung bình diện tích. Một mô hình chung học nhiều trạm, còn giá trị đầu ra vẫn riêng cho từng trạm.')
    table(s,'windows',['Nhãn','Khoảng thời gian theo giờ Việt Nam'],[
        ['y₁ · ngày 1','19:00 D → 19:00 D+1'],['y₂ · ngày 2','19:00 D+1 → 19:00 D+2'],['y₃ · ngày 3','19:00 D+2 → 19:00 D+3']],
        [3.,9.25],row_h=.9,size=24)
    d.text(s,.8,5.25,11.7,.55,'**Đơn vị: mm/24h tại trạm.** D là ngày phát dự báo.',24)
    d.band(s,'Đích là ba tổng 24h riêng; không phải tổng tích lũy 24/48/72h.')

    s=page('sample','Một mẫu = một trạm + một thời điểm phát tin','I. BÀI TOÁN',
        'Ví dụ trên slide chỉ minh họa, không phải số đo một trạm thật. Trong lúc train, nhãn tương lai dùng để tính lỗi và cập nhật mô hình. Khi phát dự báo, chỉ đưa X vào mô hình. Cùng một issue có thể có nhiều mẫu tương ứng nhiều trạm; trạm thiếu dữ liệu chỉ làm mất mẫu của trạm đó, không làm mất toàn mạng.')
    d.card(s,.6,1.7,5.9,3.8,'X: thông tin đã có ở thời điểm D',
        '• Mưa quá khứ tại chính trạm\n• GFS dự báo cho ba ngày tới\n• Lịch, tọa độ và ID trạm\n• Địa hình / dẫn xuất tùy cấu hình',22)
    d.card(s,6.85,1.7,5.85,3.8,'y: mưa trạm tương lai',
        '[y₁, y₂, y₃]\n\nVí dụ giả định: [18, 20, 7] mm\n\nBa nhãn để học và kiểm chứng.',23)
    d.band(s,'Mưa Vrain kỳ đích không nằm trong X; không cần 57 mô hình tách biệt.')

    s=page('sources','Ba nguồn dữ liệu có ba vai trò','II. DỮ LIỆU',
        'Vrain cung cấp nhãn thực đo sau QC và lịch sử mưa. GFS là dự báo khí tượng số, lấy bốn nút lưới 0,25 độ nội suy về vị trí trạm; nội suy không tạo thêm độ phân giải thật. DEM từ Mapzen chỉ là proxy địa hình tại tọa độ hiện có, không phải cao độ đo bằng khảo sát tại cảm biến. Mean/std địa hình lấy chín điểm trong ô ±5 km.')
    table(s,'sources',['Nguồn','Vai trò','Giới hạn cần nhớ'],[
        ['Vrain','Mưa quá khứ + nhãn mưa tương lai','Số đo tại điểm, có thiếu / QC'],
        ['GFS 0,25°','Mưa và khí tượng dự báo tương lai','Nội suy 4 nút, không phải số đo'],
        ['DEM Mapzen','Cao độ, địa hình và độ dốc','Proxy; không phải khảo sát trạm']],
        [2.1,5.1,5.05],row_h=1.02,size=20)
    d.band(s,'Không chia mưa vệ tinh ngày thành giờ; không lấy ERA5 làm nhãn.')

    s=page('timing','07h → 18h → 19h: đầu vào phải có trước issue','II. DỮ LIỆU',
        'Issue nghĩa là thời điểm phát hành dự báo. Chu kỳ GFS 00UTC tương ứng 07 giờ Việt Nam; khoảng cách đến issue là 12 giờ. Với giả định trễ trạm một giờ, chỉ dùng số đo kết thúc 18 giờ, không dùng số đo kết thúc 19 giờ ngay lúc phát tin. Bảy tổng ngày đầy đủ gần nhất kết thúc ở 19 giờ hôm trước. Giả định độ trễ khác với việc đã xác minh khoảng đo giờ.')
    for x,title,body in [(.6,'07:00','GFS 00UTC khởi tạo\nDự báo cho tương lai'),(4.7,'18:00','Cuối số đo Vrain\nđược dùng ở kịch bản 1h'),(8.8,'19:00','Phát dự báo\nBắt đầu kỳ mưa cần đoán')]:d.card(s,x,2.,3.9,2.35,title,body,21)
    d.text(s,.8,4.9,11.8,.85,'Mưa GFS từng ngày: **C36−C12; C60−C36; C84−C60**.\nKhí tượng ở +24/+48/+72h là trạng thái giữa mỗi cửa sổ.',22)
    d.band(s,'GFS dự báo tương lai được dùng; quan trắc / ERA5 kỳ đích thì không.')

    s=page('latency_evidence','Đã kiểm tra nguồn, nhưng chưa chứng minh realtime','II. DỮ LIỆU',
        'GFS Last-Modified chỉ là giờ sửa đối tượng trên kho, không phải lịch sử thời điểm người dùng nhận được bản tin. Có 48 chu kỳ đầu 2021 mang timestamp sửa archive sau issue, có thể do chép lại kho; không suy diễn chắc chắn là phát hành gốc muộn hoặc sớm. API Vrain hiện tại trả hàng giờ nhưng chưa chứng minh độ trễ tiếp nhận từng số đo lịch sử. Không đưa dữ liệu 2026 của lần kiểm tra API vào train.', 'source_latency_audit.json')
    table(s,'latency_evidence',['Điều kiểm tra','Bằng chứng','Diễn giải đúng'],[
        ['Kho GFS hiện tại','Last-Modified ~3,65–4,04h sau init','Hỗ trợ tính khả thi, chưa là cam kết'],
        ['Lịch sử GFS','48 chu kỳ đầu 2021 sửa kho sau issue','Chưa chứng minh giờ phát hành gốc'],
        ['API Vrain','Có các hàng giờ ở kênh hiện hành','Nhãn giờ ≠ giờ số đo đến hệ thống']],
        [2.65,4.6,5.0],row_h=1.0,size=20)
    d.band(s,'Trễ GFS 8h và Vrain 1h vẫn là giả định; đã thử thêm trễ Vrain 3h/6h.')

    s=page('coverage','57 trạm và 1.449 chu kỳ dùng được','II. DỮ LIỆU',
        'Có 86 vị trí trong danh mục nhóm Đà Nẵng của tài khoản, không phải toàn quốc hay chứng nhận phủ kín diện tích. Cohort 57 giữ điều kiện chọn chỉ bằng train: ít nhất 365 ngày đủ và 30 ngày mưa ≥1 mm. Lịch mới là mỗi ngày, không phải mỗi tuần. Hai ngày nguồn lỗi bị loại trước fit, đồng đều cho mọi mô hình, dựa trên 404 và đối chiếu byte GRIB, không dựa trên lượng mưa.', 'dataset_audit.json / source_coverage_policy.json')
    for x,title,body in [(.6,'57 trạm','Đủ điều kiện train\nKhông ép đủ danh mục 86'),(4.7,'1.451 ngày','Lịch cố định\n08/01/2021–28/12/2024'),(8.8,'1.449 chu kỳ','Có đủ trường GFS\nHai chu kỳ nguồn lỗi')]:d.card(s,x,1.8,3.9,2.05,title,body,20)
    d.text(s,.8,4.25,11.9,1.25,'• 02/02/2021: thiếu index trong hai bố cục kho nguồn.\n• 30/11/2022: index và byte GRIB không khớp khi tải lại.\n• Loại cùng issue ở mọi cấu hình, trước khi fit.',22)
    d.band(s,'Không gọi kho này là đủ 100%; không chọn ngày theo điểm dự báo.')

    s=page('split','Mỗi giai đoạn có một nhiệm vụ khác nhau','III. CHIA DỮ LIỆU',
        'Train 2021–2022 dùng học trọng số, scaler và tham chiếu khí hậu; tuning cũng chỉ diễn ra bên trong giai đoạn này. Cal 2023 dùng hiệu chỉnh xác suất và chọn cutoff, không chọn checkpoint như pilot cũ. Dev 2024 dùng đọc kết quả và định hướng phát triển, nên chưa phải test cuối. Mẫu trạm–issue có ba nhãn; dữ liệu dạng bảng dài có ba hàng cho một mẫu.', 'dataset_audit.json / protocol.json')
    rows=[]
    for part,label,purpose in [('train','2021–22 · Train','Học mô hình; tuning nội bộ'),('cal','2023 · Cal','Hiệu chỉnh xác suất / cutoff'),('dev','2024 · Dev','Đánh giá để phát triển')]:
        rows.append([label,f"{audit['counts'][part]['station_issues']:,}".replace(',','.'),purpose])
    rows.append(['2025 · Test cuối','Chưa chấm','Dành kiểm tra sau khi chốt phương án'])
    table(s,'split_counts',['Giai đoạn','Mẫu trạm–issue','Vai trò'],rows,[3.1,2.8,6.35],row_h=.82,size=22)
    d.band(s,'Tổng: 72.886 mẫu → 218.658 hàng theo ba hạn; không random chia cửa sổ.')

    s=page('holdout','“Giữ kín 2025” có nghĩa là gì?','III. CHIA DỮ LIỆU',
        'Giữ kín là giữ lại một năm để kiểm định cuối, không phải giấu một bảng kết quả đã có. Năm 2025 đã qua về lịch, nhưng chưa tham gia chọn đặc trưng, tham số, cutoff hoặc chấm điểm trong pipeline hiện tại. Nếu liên tục xem điểm 2025 rồi sửa mô hình cho đẹp, năm đó trở thành dữ liệu phát triển. Hiện dataset thí nghiệm mới chỉ được dựng và kiểm chứng cho 2021–2024; không khẳng định đã có sẵn bộ test 2025 hoàn chỉnh.', 'protocol.json · scikit-learn: cross-validation')
    d.card(s,.6,1.7,5.9,3.65,'Ví dụ như học và làm bài thi',
        '2021–22: học và luyện tập\n2023: hiệu chỉnh cách dự báo\n2024: xem lỗi để phát triển\n2025: bài kiểm tra cuối để dành',22)
    d.card(s,6.85,1.7,5.85,3.65,'Trạng thái thực tế hiện nay',
        'Chưa dùng điểm / nhãn 2025\nđể chọn hoặc chỉnh mô hình.\n\nChưa có bảng kết quả 2025\ntrong thí nghiệm này.',23)
    d.band(s,'2025 đã qua về thời gian, nhưng vẫn có thể dành làm dữ liệu kiểm định.')

    s=page('mask','So sánh công bằng và tránh nhầm tương lai','III. CHIA DỮ LIỆU',
        'Dùng cùng mẫu có đủ nhãn cả ba hạn và đủ đặc trưng cho mọi cấu hình, kể cả ba kịch bản trễ trạm. Không điền nhãn thiếu thành 0. Toàn bộ 72 giờ nhãn phải thuộc cùng split, còn lịch sử được phép lấy từ quá khứ trước ranh. Scaler chỉ fit train. Số mẫu còn lại có thể không đại diện các đợt cảm biến bị lỗi, nhất là nếu thiếu số liên quan mưa lớn.', 'dataset_verification.json')
    bullets(s,['Cùng mẫu cho N0–N5, LightGBM / GRU và trễ 1/3/6h.',
        'Cả ba nhãn và lịch sử hợp lệ; thiếu không được thay bằng 0.',
        'Toàn bộ 72h nhãn nằm cùng train / cal / dev.',
        'Trạm thiếu một cửa sổ chỉ mất mẫu của chính trạm đó.',
        'Các mẫu cùng đợt mưa không được xem là hoàn toàn độc lập.'],gap=.78,size=22)
    d.band(s,'Scalers và tham chiếu khí hậu chỉ học từ train.')

    s=page('cv','Tuning: bốn lần học quá khứ → kiểm tra quý kế','III. CHIA DỮ LIỆU',
        'Đây là rolling validation bên trong train 2021–2022, không dùng năm 2024 để early stop. Ở mỗi fold, nhãn train phải kết thúc ít nhất bảy ngày trước đầu quý validation; ba nhãn validation nằm trong quý. Bốn quý gồm các điều kiện mùa khác nhau. Sau khi chọn cấu hình, fit lại toàn train với số cây hoặc epoch cố định lấy trung vị từ CV.', 'protocol.json / tree_tuning_trials.csv')
    table(s,'cv_folds',['Fold','Phần được học','Phần dùng chọn tham số'],[
        ['1','Quá khứ trước quý 1/2022','Quý 1/2022'],['2','Quá khứ trước quý 2/2022','Quý 2/2022'],
        ['3','Quá khứ trước quý 3/2022','Quý 3/2022'],['4','Quá khứ trước quý 4/2022','Quý 4/2022']],
        [1.1,6.1,5.05],row_h=.75,size=22)
    d.text(s,.8,5.6,11.8,.45,'**Gap 7 ngày tính từ cuối nhãn train**, không chỉ từ issue.',22)
    d.band(s,'2023 chỉ calibration; 2024 không dùng để chọn số cây / epoch.',y=6.22,h=.5,size=19)

    s=page('baselines','Vì sao cần cả 0 mm, GFS thô và MOS?','IV. CÁCH HỌC VÀ ĐỐI CHỨNG',
        'ZERO kiểm tra trường hợp nhiều ngày khô khiến MAE trông dễ đạt; nó không phải cảnh báo hữu ích. Khí hậu là thông tin tháng–trạm từ train. Persistence lặp tổng 24 giờ đã có. GFS là dự báo trước học máy. MOS chỉ dùng lượng mưa GFS và sin/cos mùa, với mô hình tuyến tính/phân vị/logistic; nếu mô hình phức tạp không hơn nó thì chưa chứng minh cần sự phức tạp. LightGBM cũng là mô hình dự báo thật, không phải đối chứng được cố tình làm yếu.')
    table(s,'baselines',['Đối chứng','Cách dự báo','Câu hỏi kiểm tra'],[
        ['0 mm','Luôn dự báo khô','MAE thấp có chỉ vì nhiều ngày khô?'],
        ['Khí hậu','Tháng–trạm từ train','Có hơn thông tin mùa đơn giản?'],
        ['Persistence','Lặp mưa 24h khả dụng gần nhất','Có hơn giữ trạng thái gần đây?'],
        ['GFS thô','Lượng GFS đúng cửa sổ','Học máy có giúp hiệu chỉnh?'],
        ['MOS','Hiệu chỉnh GFS tuyến tính / logistic','Có cần mô hình nhiều biến hơn?']],
        [2.1,5.1,5.05],row_h=.70,size=20)
    d.band(s,'So trên cùng trạm, cùng issue và cùng nhãn, không làm yếu đối chứng.')

    s=page('mean_median','Vì sao có hai cách trả lời “mưa bao nhiêu mm”?','IV. CÁCH HỌC VÀ ĐỐI CHỨNG',
        'Mean là kỳ vọng, median là trung vị của lượng mưa có điều kiện theo đầu vào. Ví dụ hoàn toàn giả định: xác suất 80% không mưa và 20% mưa 50 mm; kỳ vọng là 10 mm nhưng trung vị là 0. MAE và sai số bình phương khuyến khích các đại lượng khác nhau. Vì thế hai đầu được định nghĩa trước khi chấm dev; không chọn đầu đẹp theo từng metric rồi gọi là một dự báo duy nhất. Cơ sở: Gneiting, Making and Evaluating Point Forecasts.', 'protocol.json · Gneiting (2011)')
    table(s,'functionals',['Đầu dự đoán','Cách hiểu','Học / đánh giá chính'],[
        ['Mean','Lượng mưa kỳ vọng theo thông tin X','Tweedie → RMSE'],
        ['Median','Mức mưa trung vị theo thông tin X','Quantile 0,5 → MAE']],
        [2.0,5.4,4.85],row_h=.86,size=23)
    d.text(s,.9,4.55,11.7,1.15,'Ví dụ giả định: **80% mưa 0 mm; 20% mưa 50 mm**.\nMean = 10 mm; median = 0 mm. Cả hai trả lời đúng mục tiêu riêng.',24)
    d.band(s,'Vẫn chỉ có ba nhãn thật y₁/y₂/y₃; mỗi nhãn có hai đầu lượng để ước lượng.')

    # Remaining slides are populated below.
    build_remaining(d,page,table,bullets,matrix,value,interval,csv,protocol,audit,trees,gru,roles,checks)
    pptx=OUT/(STEM+'.pptx');html=OUT/(STEM+'.html');scene=OUT/'slide_content.json'
    d.save(pptx,html,scene)
    prs=Presentation(pptx)
    for native,slide in zip(prs.slides,d.slides):
        for shape,spec in zip(native.shapes,slide['shapes']):
            if spec['kind']!='table':continue
            for ri,row in enumerate(shape.table.rows):
                for ci,cell in enumerate(row.cells):
                    style=spec['styles'].get(f'{ri},{ci}',{})
                    cell.text_frame.word_wrap=True
                    for p in cell.text_frame.paragraphs:
                        p.alignment=PP_ALIGN.CENTER;p.space_before=p.space_after=Pt(0);p.line_spacing=1
                        for run in p.runs:
                            run.font.name='Arial';run.font.size=Pt(spec['size']);run.font.bold=ri==0 or style.get('bold',False)
                            run.font.color.rgb=RGBColor.from_string('FFFFFF' if ri==0 else style.get('color',NAVY))
    prs.core_properties.title='PBL6 — Dự báo mưa hằng ngày tại 57 trạm'
    prs.core_properties.author='Nhóm PBL6'
    prs.core_properties.subject='Dev 2024; chưa chấm kiểm định 2025; daily-v2'
    prs.save(pptx)
    html.write_text(html.read_text(encoding='utf8').replace('PBL6 — Báo cáo mưa vùng','PBL6 — Dự báo mưa tại 57 trạm'),encoding='utf8',newline='\n')
    notes='# Ghi chú thuyết trình — Dự báo mưa hằng ngày v2\n\n'
    notes+='Các bảng kết quả là dev 2024. Năm 2025 chưa được chấm trong thí nghiệm này.\n\n'
    for slide in d.slides:
        notes+=f"## {slide['number']:02d}. {slide['title']}\n\n{slide['note']}\n\nNguồn: {slide['source']}\n\n"
    (OUT/'GHI_CHU_THUYET_TRINH.md').write_text(notes.rstrip()+'\n',encoding='utf8',newline='\n')
    sources={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in DATA.iterdir() if p.is_file() and p.suffix in ('.csv','.json','.md')}
    manifest=dict(experiment='gfs_station_daily_v2_2026_11_10',slides=len(d.slides),roles=roles,
                  main_slides=roles['conclusion'],test2025_read=False,training_run=False,sources=sources,numeric_checks=checks,
                  code_sha256={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in (Path(__file__),ROOT/'scripts/presentation_layout.py')},
                  files_sha256={p.name:sha(p) for p in (pptx,html,scene,OUT/'GHI_CHU_THUYET_TRINH.md')})
    (OUT/'build_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8',newline='\n')
    print(json.dumps(dict(slides=len(d.slides),main=roles['conclusion'],numeric_checks=len(checks),test2025_read=False)))


def build_remaining(d,page,table,bullets,matrix,value,interval,csv,protocol,audit,trees,gru,roles,checks):
    s=page('features','N0–N5: thêm thông tin gì vào mô hình?','IV. CÁCH HỌC VÀ ĐỐI CHỨNG',
        'Các cấu hình này thuộc thí nghiệm trạm hằng ngày v2, không phải E0–E7 của bộ vùng trước đây. N0 có 16 đặc trưng gồm mưa GFS, mùa, tọa độ, ID và 10 biến mưa lịch sử. N1 thêm khí tượng thô. N2 và N4 thêm biến được tính từ cùng T, RH, u, v, không phải nguồn quan trắc mới. N3 thêm năm biến địa hình. N5 thêm tương tác giữa gió/ẩm và độ dốc. q là độ ẩm riêng suy ra từ nhiệt độ, độ ẩm tương đối ở 850 hPa; q*u và q*v là dòng ẩm một mực, không phải tích phân vận chuyển ẩm IVT.', 'protocol.json · tree_summary.json')
    table(s,'features',['Nhóm','Số biến','Thông tin được đưa vào'],[
        ['N0',16,'Mưa GFS + mùa / vị trí / ID + lịch sử mưa trạm'],
        ['N1',21,'N0 + T, RH, u, v tại 850 hPa + hơi nước cột'],
        ['N2',25,'N1 + q, q×u, q×v, tốc độ gió'],
        ['N3',26,'N1 + cao độ, trung bình / độ lệch cao độ, hai độ dốc'],
        ['N4',30,'N3 + bốn dẫn xuất khí tượng của N2'],
        ['N5',32,'N4 + gió·độ dốc và dòng ẩm·độ dốc']],
        [1.05,1.35,9.85],row_h=.60,size=20)
    d.band(s,'N1 thêm khí tượng; N3 thêm địa hình; N2/N4/N5 kiểm tra cách biểu diễn.',y=6.12,size=19)

    s=page('contrasts','Mỗi phép so sánh trả lời một câu hỏi','IV. CÁCH HỌC VÀ ĐỐI CHỨNG',
        'Không chỉ so N0 với N5 rồi quy hết cải thiện cho các dẫn xuất. N1 so N0 tách phần thông tin khí tượng mới. N3 so N1 tách địa hình. N2 so N1 và N4 so N3 tách cách biểu diễn gió ẩm. N5 so N4 tách tương tác địa hình; N5 so N3 là hiệu quả toàn bộ gói dẫn xuất. LightGBM chạy đủ N0–N5. GRU chỉ chạy N3 và N5 để kiểm tra xem gói dẫn xuất có tác dụng trong một họ mô hình khác. Cấu hình, mẫu, seed và tiêu chí đánh giá được giữ chung trong từng họ.', 'protocol.json · paired_bootstrap.csv')
    table(s,'contrasts',['So sánh','Câu hỏi nghiên cứu'],[
        ['N1 − N0','Dự báo khí tượng thô có bổ sung ích lợi ngoài mưa GFS?'],
        ['N3 − N1','Thông tin địa hình có giúp không?'],
        ['N2 − N1; N4 − N3','Các dẫn xuất gió–ẩm có giúp biểu diễn dễ học hơn?'],
        ['N5 − N4','Tương tác gió–ẩm–độ dốc có thêm ích lợi?'],
        ['N5 − N3','Cả gói dẫn xuất có ích ở LightGBM và GRU không?']],
        [3.0,9.25],row_h=.72,size=22)
    d.band(s,'Dẫn xuất từ cùng dữ liệu không đồng nghĩa đã có thêm nguồn thông tin. ',size=19)

    s=page('models','Hai cách học trên cùng bài toán trạm','IV. CÁCH HỌC VÀ ĐỐI CHỨNG',
        'LightGBM là mô hình dự báo đầy đủ, mạnh với dữ liệu bảng và là đối chứng cần thiết. Nó học riêng từng hạn và từng đầu ra. GRU là mạng tuần tự nhỏ đọc chuỗi bảy tổng mưa ngày, ghép với ngữ cảnh dự báo khí tượng từng hạn và embedding trạm. Cả hai học chung nhiều trạm; không huấn luyện 57 mô hình độc lập. Ngữ cảnh GRU N3 có 18 số liên tục, N5 có 24; lịch sử và embedding được xử lý riêng nên không thể so số chiều này trực tiếp với 26/32 cột LightGBM. TFT/Informer cũ dùng bài toán, nhãn và protocol khác; bộ kết quả đó không thể đưa vào bảng so sánh hiện tại. Đây không phải bằng chứng TFT hay Informer không khả thi.', 'gru_summary.json · tree_summary.json')
    d.card(s,.6,1.65,5.9,3.85,'LightGBM: học bảng đặc trưng',
        'X mỗi hạn: 16–32 cột tùy nhóm\nHọc riêng ngày 1 / 2 / 3\nChạy đủ N0–N5\nBốn đầu ra mỗi hạn\nCấu hình nhỏ, dễ kiểm tra',22)
    d.card(s,6.85,1.65,5.85,3.85,'GRU: học chuỗi mưa quá khứ',
        'Lịch sử: [mẫu, 7 ngày, 1]\nNgữ cảnh N3: [mẫu, 3 hạn, 18]\nNgữ cảnh N5: [mẫu, 3 hạn, 24]\nEmbedding ID trạm\nChạy N3 và N5',22)
    d.band(s,'TFT / Informer cũ khác nhãn và protocol → chưa có so sánh công bằng ở v2.',size=18)

    s=page('tuning_tree','LightGBM: chỉnh trên train, khóa trước calibration','IV. CÁCH HỌC VÀ ĐỐI CHỨNG',
        'Mỗi đầu ra có ba ứng viên nhỏ/pilot/vừa, thử trên bốn fold thời gian trong train, với N3 làm cấu hình neo. Chọn ứng viên theo điểm CV rồi dùng trung vị số cây tối ưu giữa các fold cho fit cuối. Mỗi cấu hình N0–N5 dùng chung lựa chọn này, tránh tăng cơ hội tuning riêng cho nhóm nhiều biến. Learning rate 0,04; subsample và colsample 0,9; L2 bằng 5. Tối đa 600 cây, patience 50 chỉ trong CV train. Đầu mean dùng Tweedie power 1,5; median dùng quantile 0,5; hai đầu xác suất dùng binary loss. Tổng 144 fit CV và 288 bộ ước lượng cuối bao gồm các thí nghiệm độ trễ. Không early stopping bằng 2023 hay 2024.', 'tree_selection.json · tree_tuning_trials.csv')
    rows=[]
    for key,name in [('mean','Mean'),('median','Median'),('wet','P(mưa ≥1)'),('conditional','P(≥50 | ≥1)')]:
        item=trees['selected'][key];c=item['candidate']
        rows.append([name,str(c['num_leaves']),str(c['max_depth']),str(c['min_child_samples']),'/'.join(str(item['trees'][str(h)]) for h in (1,2,3))])
    table(s,'tree_config',['Đầu ra','Lá','Độ sâu','Mẫu/lá','Số cây ngày 1 / 2 / 3'],rows,[2.5,1.1,1.35,1.5,5.8],row_h=.73,size=22)
    d.text(s,.8,5.55,11.8,.5,'Learning rate **0,04** · L2 **5** · Ba seed **17 / 29 / 43**.',23)
    d.band(s,'Chọn trên CV 2021–2022; dùng cùng lựa chọn cho các nhóm đặc trưng.',size=19)

    s=page('gru_seeds','GRU và “ba seed”: chạy lặp để giảm may rủi','IV. CÁCH HỌC VÀ ĐỐI CHỨNG',
        'Seed điều khiển khởi tạo trọng số, trộn mẫu và các thành phần ngẫu nhiên. Ba seed không phải ba năm hay ba lần chia test. Bảng minh họa GRU N5 ngày 1; ensemble là trung bình dự báo trước khi tính metric, không phải trung bình ba metric. GRU chọn hidden 16, head 24, learning rate 0,001, fit cuối 17 epoch qua CV train; dropout 0,1, batch 256, AdamW weight decay 0,001, gradient clip 1. Loss gộp Tweedie đã chuẩn hóa, pinball và 0,5 lần hai BCE. N3 có 4.364 tham số và N5 có 4.796: gói dẫn xuất tăng 432 tham số, nên chưa tách hoàn toàn tác động biểu diễn khỏi dung lượng mạng.', 'gru_selection.json · seed_metrics.csv')
    d.text(s,.75,1.6,11.8,.95,'Hidden **16** · head **24** · learning rate **0,001** · **17 epoch**\nChọn qua CV train; chạy lại seed 17 / 29 / 43.',23)
    tag='seed_example';rows=[]
    for i,seed in enumerate((17,29,43)):
        filters=dict(model='GRU_N5',seed=seed,horizon=1)
        rows.append([str(seed),value(tag,i,1,'seed_metrics',filters,'mean_rmse'),value(tag,i,2,'seed_metrics',filters,'median_mae')])
    rows.append(['Trung bình dự báo',value(tag,3,1,'point_metrics',dict(fold='dev',model='GRU_N5',horizon=1,functional='mean'),'macro_rmse'),value(tag,3,2,'point_metrics',dict(fold='dev',model='GRU_N5',horizon=1,functional='median'),'macro_mae')])
    table(s,tag,['GRU N5 · ngày 1','RMSE mean ↓','MAE median ↓'],rows,[5.25,3.5,3.5],y=2.7,row_h=.62,size=22,styles={'4,1':dict(bold=True,color=TEAL),'4,2':dict(bold=True,color=TEAL)})
    d.band(s,'Ba seed kiểm tra biến thiên do học; không thay thế kiểm định trên năm mới.',size=19)

    s=page('probabilities','Xác suất phải hợp lý trước khi dùng cảnh báo','IV. CÁCH HỌC VÀ ĐỐI CHỨNG',
        'Hai sự kiện lồng nhau: mọi ngày mưa ít nhất 50 mm cũng phải là ngày mưa ít nhất 1 mm. Mô hình học P1 và xác suất có điều kiện Q50 trên các mẫu wet. Sau hiệu chỉnh Platt trên 2023, tính P50=P1×Q50. Cách làm giữ P50 không vượt P1 ở từng seed và cả ensemble. Ngưỡng quyết định tau được chọn bằng quarter cross-fitting trên 2023, cách ly ±7 ngày; cùng tau cho hai sự kiện tại mỗi mô hình/hạn. Quarter cross-fit chỉ là công cụ calibration lịch sử, không phải giả lập dự báo thời gian thực năm 2023. Chấm 2024 bằng calibrator fit trên toàn bộ 2023 và tau đã chọn. Mốc 50 mm ở đây là ngưỡng nghiên cứu thăm dò, không tự động là chuẩn cảnh báo hành chính.', 'probability_coherence.csv · decision_cutoffs.json')
    d.text(s,.8,1.7,11.7,1.02,'P₁ = P(mưa ≥1 mm)\nP₅₀ = P₁ × P(mưa ≥50 mm | mưa ≥1 mm)',26,True)
    d.card(s,.7,2.85,5.8,2.25,'Ví dụ giả định','P₁ = 0,60; Q₅₀ = 0,20\n→ P₅₀ = 0,12 ≤ P₁',25)
    d.card(s,6.85,2.85,5.8,2.25,'Calibration khác cảnh báo','Hiệu chỉnh xác suất: dùng 2023\nChọn tau báo có/không: 2023',21)
    d.text(s,.8,5.45,11.7,.48,'Cùng tau cho ≥1 và ≥50 giúp quyết định cảnh báo cũng nhất quán.',21)
    d.band(s,'Xác suất 0,30 không phải lượng mưa 0,30 mm.',size=21)

    s=page('metrics','Đọc các chỉ số như thế nào?','V. ĐÁNH GIÁ',
        'RMSE phạt mạnh sai số lớn và là tiêu chí chính của đầu mean; MAE dễ diễn đạt theo mm và là tiêu chí chính của đầu median. Bias là dự báo trừ quan trắc: âm nghĩa dự báo thiếu trung bình. BS là sai số bình phương giữa xác suất và nhãn 0/1. BSS=1−BS/BS khí hậu, với cùng tập mẫu và tham chiếu khí hậu học từ train; âm nghĩa kém hơn tham chiếu đó theo BS. H là báo trúng, M là bỏ sót, F là báo nhầm. POD=H/(H+M), FAR=F/(H+F), CSI=H/(H+M+F). FAR ở đây là false alarm ratio, không phải false positive rate. Không có quy tắc POD 0,4 luôn tốt; cần cùng ngưỡng mưa, hạn dự báo, mẫu và FAR/CSI để so sánh. Các bảng lượng ghi rõ đầu dự báo, các bảng sự kiện ghi rõ ngưỡng và tau.', 'MET Appendix C · protocol.json')
    table(s,'metrics',['Chỉ số','Ý nghĩa dễ hiểu','Vì sao dùng?','Chiều tốt'],[
        ['RMSE','Sai số mm; phạt mạnh lỗi lớn','Kiểm tra dự báo sai nặng','Nhỏ hơn'],
        ['MAE','Trung bình lệch bao nhiêu mm','Dễ hiểu mức sai số lượng','Nhỏ hơn'],
        ['Bias','Trung bình dự báo − thực tế','Nhận biết thừa / thiếu mưa','Gần 0'],
        ['BS','Sai số của xác suất dự báo','Chấm xác suất, chưa cần tau','Nhỏ hơn'],
        ['BSS','BS cải thiện so với khí hậu','>0: hơn; <0: kém khí hậu','Lớn hơn'],
        ['CSI','H / (H + M + F)','Cân đối trúng, sót và nhầm','Lớn hơn'],
        ['POD','H / (H + M)','Bắt được bao nhiêu mưa thật','Lớn hơn'],
        ['FAR','F / (H + F)','Trong lần báo có, bao nhiêu sai','Nhỏ hơn']],
        [1.0,4.35,5.15,1.75],y=1.58,row_h=.51,size=18)
    d.band(s,'H: báo trúng · M: bỏ sót · F: báo nhầm. Luôn đọc POD cùng FAR và CSI.',y=6.3,h=.42,size=17)

    s=page('uncertainty','Một con số chung và khoảng tin cậy nói gì?','V. ĐÁNH GIÁ',
        'Macro: tính metric tại từng trạm rồi lấy trung bình 57 trạm; mỗi trạm có trọng số bằng nhau. Macro RMSE không phải căn của MSE gộp toàn mạng. Macro BSS là trung bình skill từng trạm, không tính lại bằng tỷ số hai macro BS. So sánh cặp dùng cùng ngày và trạm, lấy mẫu lại 1.000 lần theo khối tròn 14 ngày để giữ một phần phụ thuộc thời gian và đồng biến các trạm. Chênh lệch A−B âm tốt hơn cho sai số. CI chứa 0 nghĩa chưa có bằng chứng rõ theo phép thử này, không chứng minh hai mô hình bằng nhau. Đây là CI thăm dò chưa điều chỉnh nhiều phép so sánh, điều kiện trên các mô hình đã fit; không bao quát độ bất định cảm biến hay thay đổi khi train lại.', 'paired_bootstrap.csv · protocol.json')
    bullets(s,['**Macro:** tính tại từng trạm, rồi trung bình; trạm có vai trò ngang nhau.',
        '**So sánh cặp:** A và B gặp đúng cùng mẫu, không khác độ khó.',
        '**CI 95%:** lấy mẫu lại 1.000 lần theo khối 14 ngày.',
        '**Sai số A − B:** CI nằm dưới 0 → tín hiệu A tốt hơn trong dev này.',
        '**CI chứa 0:** chưa đủ bằng chứng rõ; không kết luận “bằng nhau”.'],gap=.84,size=22)
    d.band(s,'CI thăm dò trên 2024; chưa phải chứng cứ độc lập trên 2025.',size=21)

    for role,title,file,key,fun,threshold,note in [
        ('rmse','Sai số lượng mưa: RMSE của đầu mean ↓','point_metrics','macro_rmse','mean',None,'Các giá trị có đơn vị mm/24h, macro theo trạm. In đậm giá trị thấp nhất trong những dòng đang hiển thị; bảng toàn bộ cấu hình ở phụ lục. Mô hình có điểm thấp nhất từng ngày không nhất thiết thắng có ý nghĩa thống kê. ZERO thấp ở MAE nhưng RMSE cao cho thấy tác hại của bỏ qua mưa. So với MOS, các mô hình nhiều biến có tín hiệu cải thiện trên dev.'),
        ('mae','Sai số điển hình: MAE của đầu median ↓','point_metrics','macro_mae','median',None,'Đầu median được huấn luyện để tối ưu trung vị, nên được so theo MAE chính. Không lấy MAE từ median rồi dùng như cùng một dự báo mean trong bảng RMSE. GRU N5 có MAE median thấp nhất trong các cấu hình chính, nhưng đó vẫn là kết quả dev. Phụ lục có toàn bộ N0–N5.'),
        ('bss50','Xác suất mưa ≥50 mm: BSS so với khí hậu ↑','probability_metrics','macro_bss',None,50,'BSS dương nghĩa tốt hơn khí hậu tham chiếu theo BS; âm nghĩa kém hơn. GFS thô ở đây bị chuyển thành xác suất 0 hoặc 1 từ một lượng dự báo tất định; đó không phải hệ dự báo tổ hợp GFS và không nên diễn giải là năng lực xác suất của một ensemble. MOS và CLIM là đối chứng xác suất phù hợp hơn. BSS là macro của skill từng trạm. In đậm là cao nhất trong các dòng hiển thị, không phải mọi cấu hình trong phụ lục.')]:
        s=page(role,title,'VI. KẾT QUẢ DEV 2024',note,file+'.csv')
        matrix(s,role,CORE,file,key,fun,threshold,size=21,row_h=.48)
        d.band(s,'In đậm: tốt nhất trong bảng này. Bảng đầy đủ N0–N5 nằm ở phụ lục.',y=6.18,h=.52,size=18)

    s=page('events','Bắt được mưa lớn nhiều hơn, nhưng báo nhầm còn cao','VI. KẾT QUẢ DEV 2024',
        'Bảng là sự kiện ≥50 mm/24h, với tau chọn trên calibration 2023 và đóng băng khi chấm 2024. Mỗi dòng hiển thị ngày dự báo, mô hình, cutoff, POD, FAR, CSI. Không thể so POD riêng rồi kết luận: hạ tau thường bắt được nhiều mưa hơn nhưng cũng tăng báo nhầm. Ngày 1 có 890 station-day mưa lớn trên 96 issue; ngày 2 là 886/95; ngày 3 là 884/94. Đây không phải hàng trăm trận mưa độc lập vì nhiều trạm có thể gặp cùng hệ thời tiết. Bảng dùng macro; không diễn giải phép nhân POD với tổng số sự kiện như thể đó là micro.', 'event_metrics.csv')
    rows=[];tag='events';styles={}
    for h in (1,2,3):
        for model in ('MOS','LGB_N3','GRU_N5'):
            i=len(rows);filters=dict(fold='dev',model=model,horizon=h,threshold_mm=50,decision_rule='calibration_selected')
            rows.append([str(h),LABELS[model]]+[value(tag,i,j,'event_metrics',filters,key) for j,key in enumerate(('cutoff','macro_pod','macro_far','macro_csi'),2)])
            styles[f'{i+1},4']=dict(bold=True,color=RED)
    table(s,tag,['Ngày','Mô hình','Tau','POD ↑','FAR ↓','CSI ↑'],rows,[1.0,2.5,1.8,2.25,2.25,2.45],y=1.58,row_h=.45,size=20,styles=styles)
    d.band(s,'Không có chuẩn “POD 0,4 là tốt” cho mọi bài toán. Cần xem FAR, CSI và ngưỡng.',y=6.25,h=.46,size=18)

    s=page('raw_gain','Khí tượng thô bổ sung: tín hiệu cải thiện rõ hơn','VI. KẾT QUẢ DEV 2024',
        'So LightGBM N1 với N0 giữ cùng mô hình và quy trình, chỉ thêm T/RH/u/v 850 hPa và PWAT dự báo. Các khoảng RMSE dưới 0 ở cả ba ngày cho thấy ích lợi của thông tin khí tượng dự báo ngoài lượng mưa GFS và lịch sử mưa. Bảng cũng cho chênh MAE median để người đọc không nhầm chức năng đầu ra. Đây là bằng chứng trên cùng dev 2024 và bootstrap thăm dò, không phải bằng chứng nhân quả hay đánh bại một paper khác có dữ liệu khác.', 'paired_bootstrap.csv')
    rows=[];tag='raw_gain'
    for i,h in enumerate((1,2,3)):
        rows.append([str(h),interval(tag,i,1,'LGB_N1','LGB_N0',h,'mean','rmse'),interval(tag,i,2,'LGB_N1','LGB_N0',h,'median','mae')])
    styles={}
    for i,h in enumerate((1,2,3)):
        for j,fun in ((1,'mean'),(2,'median')):
            f=csv['paired_bootstrap'];r=f[f.model.eq('LGB_N1') & f.reference.eq('LGB_N0') & f.horizon.eq(h) & f.functional.eq(fun) & f.metric.eq('rmse' if fun=='mean' else 'mae')]
            assert len(r)==1
            if r.iloc[0].ci95_high<0:styles[f'{i+1},{j}']=dict(bold=True,color=TEAL)
    table(s,tag,['Ngày','Δ RMSE mean [CI 95%]','Δ MAE median [CI 95%]'],rows,[1.1,5.55,5.6],row_h=.90,size=22,styles=styles)
    d.text(s,.8,5.55,11.7,.48,'Δ = N1 − N0; âm là giảm sai số. Đơn vị mm/24h.',23)
    d.band(s,'Có cơ sở giữ khí tượng GFS thô làm phần đầu vào quan trọng.',size=21)

    s=page('derived_gain','N5 − N3: dẫn xuất giúp ích khác nhau giữa mô hình','VI. KẾT QUẢ DEV 2024',
        'N5 so N3 giữ cùng nguồn khí tượng thô và địa hình, bổ sung sáu dẫn xuất gió–ẩm–địa hình. LightGBM chưa có chênh lệch RMSE hoặc MAE rõ ở cả ba ngày theo CI này. GRU có CI âm ở ngày 1–2, còn ngày 3 chứa 0. Không gọi mọi con số giảm nhỏ là cải thiện được chứng minh. GRU N5 đồng thời tăng 432 tham số nên cần thí nghiệm khớp dung lượng nếu muốn quy kết riêng cho cách biểu diễn. Các cấu hình được khảo sát trên dev 2024; cần kiểm định 2025 sau khi khóa lựa chọn.', 'paired_bootstrap.csv')
    rows=[];tag='derived_gain';styles={}
    for family in ('LGB','GRU'):
        for h in (1,2,3):
            i=len(rows);rows.append([f'{family} · {h}',interval(tag,i,1,f'{family}_N5',f'{family}_N3',h,'mean','rmse'),interval(tag,i,2,f'{family}_N5',f'{family}_N3',h,'median','mae')])
            if family=='GRU' and h<3:
                for j in (1,2):styles[f'{i+1},{j}']=dict(bold=True,color=TEAL)
    table(s,tag,['Mô hình · ngày','Δ RMSE mean [CI 95%]','Δ MAE median [CI 95%]'],rows,[2.2,5.0,5.05],y=1.6,row_h=.59,size=19,styles=styles)
    d.band(s,'GRU N5 cũng tăng 432 tham số: chưa tách hết tác động của dung lượng mạng.',size=18)

    s=page('latency','Nếu mưa trạm đến chậm hơn thì sao?','VI. KẾT QUẢ DEV 2024',
        'LightGBM N3 được fit và chấm lại với lịch sử mưa trạm bị cắt sớm 1, 3 hoặc 6 giờ trước issue 19h; dùng chung mẫu hoàn chỉnh giữa ba trường hợp. Tổng mưa 1/6/24h gần nhất thay theo cutoff, chuỗi bảy ngày hoàn chỉnh vẫn là thông tin trước issue. Kết quả không suy giảm lớn trong kiểm tra này; không suy ra API thực tế luôn sẵn sàng hoặc chậm luôn có lợi. Trễ GFS 8h được giả định; nếu thực tế trễ 16h thì cycle 00UTC không kịp issue 19h, protocol này chưa có fallback cycle cũ. Cần kiểm chứng receipt-time thực tế khi vận hành.', 'point_metrics.csv · source_latency_audit.json')
    matrix(s,'latency',['LGB_N3','LGB_N3_delay3','LGB_N3_delay6'],'point_metrics','macro_rmse','mean',y=1.8,row_h=.80,size=23)
    d.text(s,.8,5.25,11.6,.6,'Bảng: RMSE mean (mm) khi mưa trạm đến trễ **1 / 3 / 6 giờ**.',23)
    d.band(s,'GFS trễ 16 giờ: cycle hiện tại không kịp phát tin; chưa có thử nghiệm thay cycle.',size=18)

    s=page('heavy_amount','Mưa lớn vẫn là phần khó của bài toán','VI. KẾT QUẢ DEV 2024',
        'Bảng lọc theo lượng quan trắc ≥50 mm ở ngày 3 để chẩn đoán: 884 station-day trên 94 issue. Các sai số là micro trên tập con này, không trộn với macro của bảng toàn bộ. Bias âm cho thấy trên những ngày thực sự mưa lớn, lượng kỳ vọng thường thấp hơn quan trắc. Vì đang điều kiện trên Y lớn, ngay một dự báo kỳ vọng đúng cũng có thể có bias âm ở tập con; riêng bảng này không chứng minh xác suất đã sai calibration. Không được dùng ngưỡng quan trắc tương lai để chọn mô hình khi phát tin. Cần xem đồng thời reliability, BS/BSS và sai số theo mức mưa.', 'conditional_amount_metrics.csv')
    rows=[];tag='heavy_amount';styles={}
    heavy_bin=next(x for x in csv['conditional_amount_metrics'].observed_rain_bin.unique() if '50' in x and x!='10_to_50')
    for i,model in enumerate(('GFS','MOS','LGB_N3','GRU_N5')):
        filters=dict(fold='dev',horizon=3,model=model,functional='mean',observed_rain_bin=heavy_bin)
        rows.append([LABELS[model]]+[value(tag,i,j,'conditional_amount_metrics',filters,key) for j,key in enumerate(('micro_mae','micro_rmse','micro_bias'),1)])
        styles[f'{i+1},3']=dict(bold=True,color=RED)
    table(s,tag,['Ngày 3 · đầu mean','MAE (mm)','RMSE (mm)','Bias (mm)'],rows,[4.3,2.65,2.65,2.65],row_h=.74,size=22,styles=styles)
    d.text(s,.8,5.65,11.7,.44,'Chỉ những mẫu thực tế ≥50 mm: **884 mẫu trạm–ngày, 94 ngày issue**.',21)
    d.band(s,'Cải thiện điểm chung chưa đủ để nói đã dự báo tốt cực đoan.',size=22)

    s=page('validation','Đã kiểm tra gì, còn điều gì chưa biết?','VII. ĐỘ TIN CẬY VÀ BƯỚC TIẾP',
        'Kết quả công bố của daily-v2 đã qua 179 unit tests, đối chiếu lại 218.658 dòng station-issue-horizon, replay checkpoint 288 mô hình cây và sáu GRU, 186 calibrator và 2.106 giá trị metric; 27 đoạn GRIB được lấy mới để kiểm tra độc lập 81 phép nội suy bốn nút. Kiểm tra này hỗ trợ tính đúng của pipeline, không phải chứng nhận chất lượng cảm biến. Năm 2025 chưa nằm trong tập kết quả thí nghiệm này. Dữ liệu chỉ có hai năm train, một năm calibration, một năm dev; complete-case có thể thiên lệch khi mất số liệu trong mưa lớn. Địa hình dùng DEM và tọa độ hiện tại, không có lịch sử di dời trạm đầy đủ. Khi áp dụng nơi khác phải kiểm tra nguồn và train/validation lại.', 'release_validation.json · model_verification.json')
    d.card(s,.6,1.7,5.9,3.95,'Đã đối chiếu',
        '179 kiểm thử đã qua\n218.658 dòng được kiểm tra lại\n288 bộ cây + 6 GRU từ checkpoint\nXác suất lồng nhau sau hiệu chỉnh\nBảng số lấy từ tệp kết quả gốc',22)
    d.card(s,6.85,1.7,5.85,3.95,'Chưa thể khẳng định',
        'Chưa có điểm độc lập 2025\nChưa chứng nhận cảm biến trạm\nChưa chứng minh độ trễ lịch sử\nMất mẫu có thể không ngẫu nhiên\nChưa chứng minh chuyển vùng',22)
    d.band(s,'Kiểm tra code giúp tin vào phép tính; chưa thay được kiểm định dữ liệu và năm mới.',size=18)

    s=page('conclusion','Chốt hiện tại và cách mở kiểm định 2025','VII. ĐỘ TIN CẬY VÀ BƯỚC TIẾP',
        'Kết luận hợp lý hiện tại: thông tin khí tượng thô có ích; dẫn xuất có tín hiệu ở GRU ngày 1–2 nhưng không đồng đều giữa họ mô hình; vẫn phải cải thiện dự báo mưa lớn và báo nhầm. Không kết luận hơn các paper khác nếu chưa có cùng bài toán và protocol. Trước khi đánh giá 2025 cần đóng băng cấu hình được chọn, baseline, đầu lượng, ngưỡng sự kiện, cutoff, quy tắc QC và cách tính metric; chuẩn bị dữ liệu 2025 theo đúng quy tắc, kiểm tra độ phủ và availability không dựa trên điểm mô hình; sau đó chấm và báo cáo cả kết quả không đẹp. Nếu xem điểm 2025 rồi tiếp tục tuning theo nó, 2025 trở thành dev và phải có tập kiểm định mới. Khi replay 2025 vẫn được dùng mưa quá khứ đã có trước từng issue làm đầu vào, nhưng không được fit bằng nhãn tương lai. Bản slide này chỉ đọc các tổng hợp 2021–2024, không mở hoặc chấm test 2025.')
    bullets(s,['**Giữ:** GFS khí tượng thô + mưa quá khứ; so với MOS và khí hậu.',
        '**Chưa tuyên bố:** mọi dẫn xuất đều cải thiện, hoặc cảnh báo mưa lớn đã tốt.',
        '**Bước 1:** khóa mô hình, dữ liệu, ngưỡng và chỉ số trước khi xem điểm test.',
        '**Bước 2:** chuẩn bị / QC dữ liệu 2025 theo quy tắc đã khóa.',
        '**Bước 3:** kiểm định, báo cáo đầy đủ; không sửa mô hình theo điểm 2025.'],gap=.85,size=22)
    d.band(s,'“Giữ kín 2025” = giữ độc lập để kiểm định; không phải giấu một bảng điểm đã có.',size=19)

    # Full comparison tables remain available without crowding the main narrative.
    for role,title,file,key,fun,threshold in [
        ('full_rmse','Toàn bộ cấu hình: RMSE đầu mean (mm) ↓','point_metrics','macro_rmse','mean',None),
        ('full_mae','Toàn bộ cấu hình: MAE đầu median (mm) ↓','point_metrics','macro_mae','median',None),
        ('full_bias','Toàn bộ cấu hình: Bias đầu mean (mm) → 0','point_metrics','macro_bias','mean',None),
        ('full_bs1','Toàn bộ cấu hình: BS cho mưa ≥1 mm ↓','probability_metrics','macro_bs',None,1),
        ('full_bss1','Toàn bộ cấu hình: BSS cho mưa ≥1 mm ↑','probability_metrics','macro_bss',None,1),
        ('full_bs50','Toàn bộ cấu hình: BS cho mưa ≥50 mm ↓','probability_metrics','macro_bs',None,50),
        ('full_bss50','Toàn bộ cấu hình: BSS cho mưa ≥50 mm ↑','probability_metrics','macro_bss',None,50)]:
        s=page(role,title,'PHỤ LỤC · ĐỦ N0–N5 VÀ CÁC ĐỐI CHỨNG',
            'Bảng đủ năm đối chứng và sáu cấu hình LightGBM, hai GRU. Cùng tập mẫu dev 2024, macro theo trạm. In đậm giá trị tốt nhất trong bảng; Bias chọn giá trị gần 0 nhất. Không suy ra thắng thống kê chỉ từ in đậm. Đối chứng tất định được chuyển sang xác suất 0/1 để chấm BS, nên MOS và khí hậu là tham chiếu xác suất quan trọng hơn. Các thí nghiệm độ trễ được trình bày riêng, không lẫn vào phép so đặc trưng.',file+'.csv')
        matrix(s,role,ALL,file,key,fun,threshold,y=1.5,row_h=.37,size=18)

    s=page('cutoff_comparison','Cùng mô hình: đổi tau làm POD / FAR thay đổi','PHỤ LỤC · NGƯỠNG CẢNH BÁO',
        'Chỉ sự kiện ≥50 mm/24h. Tau 0,5 được đặt cố định; tau chọn bằng 2023 được áp dụng nguyên trạng lên 2024. Cả hai phải báo cáo để cho thấy POD cao có thể do chính sách quyết định chứ không chỉ do xác suất tốt hơn. CSI cũng chưa mô tả hết chi phí thực tế của bỏ sót và báo nhầm; protocol hiện chưa tối ưu hàm chi phí vận hành. So ngưỡng cần cùng sự kiện và hạn dự báo.', 'event_metrics.csv')
    rows=[];tag='cutoff_comparison'
    for model in ('LGB_N3','GRU_N5'):
        for h in (1,2,3):
            for rule in ('fixed_0.5','calibration_selected'):
                i=len(rows);f=dict(fold='dev',model=model,horizon=h,threshold_mm=50,decision_rule=rule)
                rows.append([LABELS[model],str(h),'Cố định' if rule=='fixed_0.5' else 'Từ 2023']+[value(tag,i,j,'event_metrics',f,key) for j,key in enumerate(('cutoff','macro_pod','macro_far','macro_csi'),3)])
    table(s,tag,['Mô hình','Ngày','Cách chọn','Tau','POD ↑','FAR ↓','CSI ↑'],rows,[2.1,.85,1.9,1.5,1.95,1.95,2.0],y=1.5,row_h=.39,size=17.5)

    s=page('references','Nguồn để kiểm tra lại phương pháp và con số','PHỤ LỤC · TÀI LIỆU',
        'Số liệu trong slide lấy từ các CSV/JSON daily-v2 được lưu cùng báo cáo; build_manifest ghi SHA-256 và ánh xạ từng ô số về dòng nguồn. Cross-validation trong tài liệu scikit-learn giải thích vì sao test phải độc lập khỏi tuning. Gneiting giải thích ghép đại lượng dự báo với hàm mất mát. MET Appendix C định nghĩa các metric kiểm định. LightGBM 4.5.0 là tài liệu tham số phù hợp môi trường đã chạy. Tài liệu phương pháp không phải bằng chứng rằng dữ liệu dự án đã đạt độ tin cậy vận hành.', 'Tài liệu gốc · bản ghi kết quả dự án')
    refs=[('Dự án: protocol, điểm số, khoảng tin cậy và audit','https://github.com/nibsu05/PBL6/tree/research/tft-regional/reports/gfs_station_daily_v2_2026_11_10'),
          ('scikit-learn: chia train / validation / test và tránh rò rỉ','https://scikit-learn.org/stable/modules/cross_validation.html'),
          ('Gneiting: Making and Evaluating Point Forecasts','https://arxiv.org/abs/0912.0902'),
          ('NCAR / DTC MET: định nghĩa các chỉ số kiểm định','https://metplus.readthedocs.io/projects/met/en/latest/Users_Guide/appendixC.html'),
          ('LightGBM 4.5.0: mục tiêu học và tham số','https://lightgbm.readthedocs.io/en/v4.5.0/Parameters.html')]
    for i,(label,url) in enumerate(refs):d.text(s,.8,1.7+i*.83,11.7,.64,label,22,False,TEAL,url=url)
    d.band(s,'Các tiêu đề là liên kết. Ghi chú thuyết trình giải thích thêm từng slide.',size=20)


if __name__=='__main__':main()
