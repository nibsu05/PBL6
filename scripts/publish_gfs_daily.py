"""Create a Vietnamese, shareable report from verified daily-v2 outputs."""
from pathlib import Path
import json
import re
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from src.gfs_daily import PUBLIC,BASE,FEATURES,write_json


def read(name):return json.loads((PUBLIC/(name+'.json')).read_text(encoding='utf8'))


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(str(v) for v in row)+' |' for row in rows])


def number(v):return '—' if pd.isna(v) else f'{v:.3f}'


def document(text,path):
    from docx import Document
    from docx.shared import Inches,Pt
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    doc=Document();style=doc.styles['Normal'];style.font.name='Calibri';style.font.size=Pt(10)
    sec=doc.sections[0];sec.top_margin=sec.bottom_margin=Inches(.65);sec.left_margin=sec.right_margin=Inches(.65)
    def inline(paragraph,value):
        for i,part in enumerate(re.split(r'(\*\*.*?\*\*)',value)):
            bold=part.startswith('**');part=part[2:-2] if bold else part.replace('`','')
            for token in re.split(r'(\[[^\]]+\]\([^)]+\))',part):
                link=re.fullmatch(r'\[([^\]]+)\]\(([^)]+)\)',token)
                if link:
                    hyperlink=OxmlElement('w:hyperlink');hyperlink.set(qn('r:id'),paragraph.part.relate_to(link[2],RT.HYPERLINK,is_external=True))
                    run=OxmlElement('w:r');style=OxmlElement('w:rPr');color=OxmlElement('w:color');color.set(qn('w:val'),'0563C1');style.append(color);run.append(style)
                    content=OxmlElement('w:t');content.text=link[1];run.append(content);hyperlink.append(run);paragraph._p.append(hyperlink)
                else:paragraph.add_run(token).bold=bold
    lines=text.splitlines();i=0
    while i<len(lines):
        line=lines[i]
        if line.startswith('| '):
            rows=[]
            while i<len(lines) and lines[i].startswith('| '):
                cells=[v.strip() for v in lines[i].strip('|').split('|')]
                if not all(set(v)<=set('-: ') for v in cells):rows.append(cells)
                i+=1
            t=doc.add_table(rows=1,cols=len(rows[0]));t.style='Light Shading Accent 1'
            header=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(header)
            for j,c in enumerate(rows[0]):inline(t.rows[0].cells[j].paragraphs[0],c)
            for row in rows[1:]:
                cells=t.add_row().cells
                for j,c in enumerate(row):inline(cells[j].paragraphs[0],c)
            for row in t.rows:
                row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
                for cell in row.cells:
                    for par in cell.paragraphs:
                        for run in par.runs:run.font.size=Pt(9)
            continue
        if line.startswith('!['):
            filename=re.search(r'\]\(([^)]+)\)',line).group(1)
            doc.add_picture(str(PUBLIC/filename),width=Inches(6.8))
        elif line.startswith('#'):doc.add_heading(line.lstrip('# ').strip(),level=min(len(line)-len(line.lstrip('#')),3))
        elif line.strip():inline(doc.add_paragraph(style='List Bullet' if line.startswith('- ') else None),line[2:] if line.startswith('- ') else line)
        i+=1
    footer=sec.footer.paragraphs[0];footer.alignment=2
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
    doc.save(path)


def main():
    verification=read('model_verification');assert verification['status']=='passed'
    audit=read('dataset_audit');latency=read('source_latency_audit');selection=read('tree_selection');gru=read('gru_selection')
    result=read('result_summary');point=pd.read_csv(PUBLIC/'point_metrics.csv');prob=pd.read_csv(PUBLIC/'probability_metrics.csv')
    event=pd.read_csv(PUBLIC/'event_metrics.csv');ci=pd.read_csv(PUBLIC/'paired_bootstrap.csv');conditional=pd.read_csv(PUBLIC/'conditional_amount_metrics.csv')
    seed=pd.read_csv(PUBLIC/'seed_metrics.csv');dev=point[point.fold.eq('dev')];pr=prob[prob.fold.eq('dev')]
    labels=pd.read_csv(PUBLIC/'label_distribution.csv');ld=labels[labels.fold.eq('dev')]
    distribution=table(['Hạn','Mẫu','Tỷ lệ <1 mm','Trung vị','P99','Mẫu ≥50 mm','Ngày issue ≥50'],
        [[r.horizon,r.samples,f'{r.fraction_under1:.1%}',number(r.median_mm),number(r.p99_mm),r.events_ge50,r.issue_dates_ge50] for r in ld.itertuples()])
    order=['ZERO','PERSISTENCE','GFS','CLIM','MOS']+[f'LGB_N{i}' for i in range(6)]+['GRU_N3','GRU_N5']
    def metric(m,h,fun,column):return float(dev.loc[dev.model.eq(m)&dev.horizon.eq(h)&dev.functional.eq(fun),column].iloc[0])
    best={(h,fun):min(metric(m,h,fun,col) for m in order) for h in (1,2,3) for fun,col in [('mean','macro_rmse'),('median','macro_mae')]}
    mainrows=[]
    for m in order:
        vals=[]
        for fun,col in [('mean','macro_rmse'),('median','macro_mae')]:
            for h in (1,2,3):
                v=metric(m,h,fun,col);vals.append('**'+number(v)+'**' if abs(v-best[h,fun])<1e-10 else number(v))
        mainrows.append([m]+vals)
    forecast_table=table(['Mô hình','RMSE mean D1','D2','D3','MAE median D1','D2','D3'],mainrows)
    count_table=table(['Tập','Mục đích','Mẫu trạm–issue','Hàng × 3 hạn','Ngày issue','Trạm'],
        [[k,desc,audit['counts'][k]['station_issues'],audit['counts'][k]['rows'],audit['counts'][k]['issue_dates'],audit['counts'][k]['stations']]
         for k,desc in [('train','2021–22: học + tuning nội bộ'),('cal','2023: hiệu chỉnh xác suất/ngưỡng'),('dev','2024: đánh giá phát triển')]])
    feature_table=table(['Cấu hình','Số biến','Nội dung','So sánh có ý nghĩa'],[
        ['N0',16,'Mưa GFS, lịch, tọa độ/ID, lịch sử mưa Vrain','Nền chung'],
        ['N1',21,'N0 + T/RH/u/v ở 850 hPa + PWAT','N1 − N0: thêm khí tượng dự báo'],
        ['N2',25,'N1 + q850, q×u, q×v, tốc độ gió','N2 − N1: dẫn xuất khí tượng'],
        ['N3',26,'N1 + cao độ, trung bình/độ lệch địa hình, hai độ dốc','N3 − N1: thêm địa hình'],
        ['N4',30,'N3 + bốn dẫn xuất khí tượng của N2','N4 − N3: dẫn xuất, cùng dữ liệu gốc'],
        ['N5',32,'N4 + gió theo dốc + ẩm theo dốc','N5 − N4: tương tác gió–ẩm–địa hình']])
    tuning_table=table(['Đầu dự đoán','Cấu hình chọn từ 2022','Số cây D1 / D2 / D3'],
        [[head,selection['selected'][head]['candidate']['name'],' / '.join(str(selection['selected'][head]['trees'][str(h)]) for h in (1,2,3))]
        for head in ('mean','median','wet','conditional')])
    probrows=[]
    for m in order:
        vals=[]
        for threshold in (1,50):
            for h in (1,2,3):vals.append(number(pr.loc[pr.model.eq(m)&pr.horizon.eq(h)&pr.threshold_mm.eq(threshold),'macro_bss'].iloc[0]))
        probrows.append([m]+vals)
    probtable=table(['Mô hình','BSS ≥1 D1','D2','D3','BSS ≥50 D1','D2','D3'],probrows)
    ev=event[event.fold.eq('dev')&event.threshold_mm.eq(50)&event.model.isin(['GFS','MOS','LGB_N3','LGB_N5','GRU_N3','GRU_N5'])]
    ev=ev[(ev.model.eq('GFS')&ev.decision_rule.eq('fixed_0.5'))|(~ev.model.eq('GFS')&ev.decision_rule.eq('calibration_selected'))]
    eventtable=table(['Mô hình','Ngày','Ngưỡng p','CSI','POD','FAR','Sự kiện trạm'],
        [[r.model,r.horizon,number(r.cutoff),number(r.macro_csi),number(r.macro_pod),number(r.macro_far),r.events] for r in ev.itertuples()])
    contrasts=ci[((ci.functional.eq('mean')&ci.metric.eq('rmse'))|(ci.functional.eq('median')&ci.metric.eq('mae'))|
        (ci.functional.eq('prob_ge50')&ci.metric.eq('bs')))&ci.model.isin(['LGB_N1','LGB_N2','LGB_N3','LGB_N4','LGB_N5','GRU_N5'])]
    pairs=[('LGB_N1','LGB_N0'),('LGB_N2','LGB_N1'),('LGB_N3','LGB_N1'),('LGB_N4','LGB_N3'),('LGB_N5','LGB_N4'),('GRU_N5','GRU_N3')]
    rows=[]
    for a,b in pairs:
        s=contrasts[contrasts.model.eq(a)&contrasts.reference.eq(b)]
        for h in (1,2,3):
            vals=[]
            for fun,metricname in [('mean','rmse'),('median','mae'),('prob_ge50','bs')]:
                r=s[s.horizon.eq(h)&s.functional.eq(fun)&s.metric.eq(metricname)].iloc[0]
                digits=5 if metricname=='bs' else 3
                value=f'{r.difference:.{digits}f} [{r.ci95_low:.{digits}f}; {r.ci95_high:.{digits}f}]'
                vals.append('**'+value+'**' if r.ci95_high<0 else value)
            rows.append([a+' − '+b,h]+vals)
    contrasttable=table(['So sánh','Ngày','Δ RMSE mean [CI95%]','Δ MAE median [CI95%]','Δ BS50 [CI95%]'],rows)
    latencyrows=[]
    for delay in (1,3,6):
        model='LGB_N3'+('' if delay==1 else f'_delay{delay}')
        latencyrows.append([str(delay)+' giờ']+[number(metric(model,h,fun,col)) for fun,col in [('mean','macro_rmse'),('median','macro_mae')] for h in (1,2,3)])
    latencytable=table(['Trễ Vrain','RMSE D1','D2','D3','MAE median D1','D2','D3'],latencyrows)
    heavy=conditional[conditional.fold.eq('dev')&conditional.observed_rain_bin.eq('ge50')&conditional.functional.eq('mean')&conditional.model.isin(['ZERO','GFS','MOS','LGB_N3','LGB_N5','GRU_N3','GRU_N5'])]
    heavytable=table(['Mô hình (mean)','Ngày','MAE ≥50','Bias ≥50','Số mẫu','Số ngày issue'],
        [[r.model,r.horizon,number(r.micro_mae),number(r.micro_bias),r.n,r.issue_dates] for r in heavy.itertuples()])
    compare=ci[ci.reference.eq('MOS')&ci.model.isin(['LGB_N3','LGB_N5','GRU_N3','GRU_N5'])&
        ((ci.functional.eq('mean')&ci.metric.eq('rmse'))|(ci.functional.eq('median')&ci.metric.eq('mae')))]
    mostable=table(['Mô hình − MOS','Ngày','Mục tiêu','Chênh lệch [CI95%]'],
        [[r.model,r.horizon,r.functional+' / '+r.metric,f'{r.difference:.3f} [{r.ci95_low:.3f}; {r.ci95_high:.3f}]'] for r in compare.itertuples()])
    seedrows=[]
    for (model,h),s in seed.groupby(['model','horizon']):
        if 'delay' in model:continue
        seedrows.append([model,h]+[f'{s[c].min():.{5 if c=="bs50" else 3}f}–{s[c].max():.{5 if c=="bs50" else 3}f}' for c in ('mean_rmse','median_mae','bs50')])
    seedtable=table(['Mô hình','Ngày','RMSE mean qua 3 seed','MAE median qua 3 seed','BS50 qua 3 seed'],seedrows)
    text=f'''# Kết quả thí nghiệm dự báo mưa tại trạm — lịch hằng ngày v2

Cập nhật 11/11/2026. Đây là kết quả **phát triển trên năm 2024**, chưa phải kiểm định cuối. Năm 2025 vẫn giữ kín. Báo cáo này là một thí nghiệm riêng, không thay số liệu của pilot lịch tuần đã công bố.

## 1. Bài toán được thực hiện

Mỗi ngày lúc **19:00 Việt Nam**, dự báo lượng mưa tại từng trạm cho ba cửa sổ riêng: 19:00 hôm nay → 19:00 ngày mai; 19:00 ngày mai → 19:00 ngày kế; và 24 giờ kế tiếp nữa. Đây là **ba tổng 24 giờ**, không phải ba tổng tích lũy 24/48/72 giờ và không phải mưa trung bình toàn Đà Nẵng.

Một mẫu là một cặp **trạm–thời điểm phát hành**. Mô hình học chung nhiều trạm; LightGBM có mô hình theo từng hạn/đầu dự đoán, GRU trả ba hạn cùng lúc. Có 57 trạm đủ điều kiện train, thuộc danh mục tài khoản nhóm Đà Nẵng. Không khẳng định đủ 86 trạm hay phủ toàn bộ ranh giới hành chính.

Nhãn là tổng 24 số đo giờ Vrain sau QC tại chính trạm. Người dùng đã xác nhận: 10:00 là mưa 09:00–10:00 UTC+7. Không phân rã mưa ngày vệ tinh, không điền nhãn thiếu bằng 0 hoặc GFS. GFS cung cấp **dự báo khí tượng tương lai có khởi tạo trước issue**; không đưa ERA5 của ngày cần dự báo vào đầu vào.

## 2. Bốn đề xuất đã chuyển thành các phép thử cụ thể

| Đề xuất | Mục đích | Đã thực hiện |
| --- | --- | --- |
| Lịch issue hằng ngày + độ trễ | Đánh giá nhiều ngày/thời tiết hơn, tránh dùng thông tin chưa đến | 1.449 chu kỳ hợp lệ; kiểm tra metadata GFS và API Vrain; trễ trạm 1/3/6 giờ |
| ZERO + hậu xử lý GFS đơn giản | Biết mô hình có ích hơn đoán khô hoặc hiệu chỉnh đơn giản không | ZERO, CLIM, persistence, GFS thô, MOS; tách mean/median |
| Khí tượng thô và dẫn xuất | Đo phần lợi ích do cách biểu diễn vật lý, tránh gán lợi ích dữ liệu mới cho công thức | N0–N5 cùng mẫu; các cặp đối chiếu nguyên liệu tương ứng |
| Xác suất + mưa lớn + tuning | Xác suất không mâu thuẫn; nhìn được bỏ sót/báo nhầm; tránh chọn theo dev | Tuning trong 2021–22, calibration 2023, p50=p1×q50, chẩn đoán ≥50 mm |

## 3. Thu thập và chia dữ liệu

Lịch cố định 08/01/2021–28/12/2024, **1.451 chu kỳ dự kiến**. Có **1.449 chu kỳ dùng được**: 02/02/2021 không có chỉ mục trong hai bố cục kho chính thức; 30/11/2022 nội dung GRIB không khớp offset của chỉ mục ở lead 36/84, đã tải lại xác nhận. Loại cả issue cho mọi mô hình bằng bằng chứng nguồn, trước fit và không dựa trên lượng mưa hay điểm dự báo. Không gọi đây là kho đủ 100%.

{count_table}

Phân bố nhãn dev 2024 (thống kê micro để mô tả tập, không dùng chọn hyperparameter):

{distribution}

Mỗi mẫu có ba nhãn nên số hàng dài bằng ba lần số mẫu. Ngày/trạm thiếu bất kỳ nhãn, lịch sử hoặc đặc trưng cần thiết đều không vào phép so sánh. Mask chung còn yêu cầu hợp lệ ở cả ba kịch bản trễ 1/3/6 giờ. **Không loại cả mạng chỉ vì một trạm thiếu**. Các cửa sổ có nhãn vượt ranh train/cal/dev bị bỏ.

57 trạm giữ nguyên điều kiện từ pilot: tối thiểu 365 ngày train đầy đủ và 30 ngày train có mưa ≥1 mm. Không chọn lại trạm theo điểm 2024. Trong tuning cuốn chiếu, trạm validation phải đã xuất hiện trong phần train của fold. Cohort tổng thể vẫn là cohort chọn trên 2021–22, nên diễn giải CV có điều kiện trên cohort này, không phải thử tổng quát hóa sang trạm chưa thấy.

## 4. Dữ liệu có sẵn tại thời điểm dự báo không?

GFS dùng chu kỳ **00UTC = 07:00 Việt Nam**, issue 12UTC = 19:00 Việt Nam. Giả định độ trễ nguồn 8 giờ; có 12 giờ từ khởi tạo đến issue. Bốn tổng mưa tích lũy GFS ở lead 12/36/60/84 giờ được lấy hiệu để khớp ba cửa sổ 19–19. Khí tượng ở lead 24/48/72 là **trạng thái tại giữa cửa sổ**, chưa đại diện toàn bộ diễn biến 24 giờ.

Audit hiện tại của chu kỳ 10/11/2026 cho Last-Modified khoảng 3,65–4,04 giờ sau khởi tạo. Audit lịch sử kiểm tra {latency['historical_gfs']['messages_with_timestamp']:,} message; có {latency['historical_gfs']['cycles_modified_after_issue']} chu kỳ đầu 2021 mang thời điểm sửa archive sau issue. Timestamp sửa/chuyển kho **không chứng minh giờ phát hành gốc**; cũng không được diễn giải là chắc chắn nguồn phát hành trễ. Bản v2 này chưa có phép retrain loại riêng 48 chu kỳ đó. Không thể kết luận đã chứng minh vận hành realtime. [Trạng thái sản xuất NOAA](https://www.nco.ncep.noaa.gov/pmb/nwprod/prodstat/production_status.html).

Kiểm tra API Vrain đăng nhập thành công tại thời điểm audit; kênh hiện hành trả hàng giờ nhưng nhãn khoảng giờ không phải timestamp tiếp nhận. Chưa đo được độ trễ tiếp nhận lịch sử của từng số đo. Lịch sử ngày và nhãn giờ đã xác định; **độ trễ vận hành là một câu hỏi khác**. Dữ liệu hiện tại 2026 chỉ dùng kiểm tra API, không fit.

Kịch bản GFS trễ 8 hoặc 12 giờ còn đủ thời gian dùng cùng chu kỳ; trễ 16 giờ thì chu kỳ này chưa sẵn sàng tại 19:00, không có dự báo cùng chu kỳ hợp lệ. Thay bằng chu kỳ trước cần dữ liệu/protocol riêng, chưa tự thay trong thí nghiệm này. Trễ Vrain được đánh giá bằng retrain N3 ở 1/3/6 giờ, giữ nguyên mẫu, cấu hình tuning và nhãn.

## 5. Đặc trưng và cách kiểm tra giá trị bổ sung

{feature_table}

N0 gồm: một lượng mưa GFS đúng hạn, sin/cos ngày trong năm, vĩ độ/kinh độ/ID trạm; bảy tổng ngày 19–19 đã hoàn thành trước hôm nay; tổng mưa 1/6/24 giờ gần nhất kết thúc ở 18:00 trong kịch bản trễ 1 giờ. N0 giữ mưa trạm trong mọi cấu hình; thí nghiệm này chưa tách riêng giá trị của từng lag mưa.

q850 suy từ nhiệt độ/độ ẩm bằng cùng công thức Magnus ở mọi năm; q×u và q×v là **proxy vận chuyển ẩm một mực**, không gọi là IVT tích phân cột khí quyển. DEM là proxy địa hình từ Mapzen tại tọa độ hiện có, không phải cao độ khảo sát tại trạm. Mean/std địa hình lấy từ chín điểm trong ô ±5 km, không phải thống kê mọi pixel của một vùng tròn bán kính 5 km. Gió theo dốc là u×độ dốc đông + v×độ dốc bắc; nhân q tạo proxy ẩm theo dốc. Đây là giả thuyết đặc trưng, không phải bằng chứng quan hệ nhân quả.

GFS gốc 0,25° được nội suy bốn nút về vị trí trạm. Nội suy không tạo độ phân giải khí tượng thật ngang khoảng cách giữa các trạm. Độ dốc/địa hình hỗ trợ hiệu chỉnh nhưng không tự khôi phục đối lưu địa phương.

## 6. Vì sao có hai đầu lượng mưa?

**Mean** ước lượng lượng mưa kỳ vọng có điều kiện; đánh giá chính bằng RMSE. **Median** ước lượng trung vị có điều kiện; đánh giá chính bằng MAE. Với nhiều ngày khô, median có thể gần 0 dù mean vẫn dương. Đây là hai câu hỏi thống kê khác nhau, không được chọn đầu tốt nhất theo từng metric sau khi xem dev rồi gọi là một dự báo duy nhất.

Ví dụ giả định: 80% khả năng 0 mm, 20% khả năng 50 mm. Mean =10 mm, median =0 mm. Dự báo 0 có thể tốt về MAE nhưng không mô tả kỳ vọng hay cảnh báo trận mưa. Vì vậy ZERO là phép chẩn đoán cần có; nó không phải hệ cảnh báo hữu ích. Cơ sở về gắn hàm mất mát với đại lượng cần dự đoán: [Gneiting, Making and Evaluating Point Forecasts](https://arxiv.org/abs/0912.0902).

LightGBM mean dùng Tweedie p=1,5, median dùng quantile α=0,5; early stopping của mean theo RMSE và median theo MAE trong fold tuning. Tweedie là lựa chọn huấn luyện cho dữ liệu không âm/lệch, không đảm bảo tối ưu RMSE trong mọi mẫu hữu hạn. [Tài liệu LightGBM 4.5](https://lightgbm.readthedocs.io/en/v4.5.0/Parameters.html).

MOS là đối chứng hậu xử lý đơn giản: chỉ mưa GFS + sin/cos mùa; Ridge cho mean, hồi quy phân vị tuyến tính cho median, logistic cho các xác suất lồng nhau. Không có địa hình/ID/lịch sử mưa. Vượt GFS thô nhưng không vượt MOS thì chưa đủ nói cần mô hình nhiều biến/phức tạp.

## 7. Tuning và calibration đã tách như thế nào?

Tuning trên bốn quý 2022. Mỗi fold chỉ train phần quá khứ; toàn bộ nhãn train kết thúc ít nhất bảy ngày trước đầu quý validation, toàn bộ ba nhãn validation nằm trong quý. Không random các cửa sổ. Ba ứng viên LightGBM: 7/15/31 lá, depth 3/4/5, min leaf 40/40/80, L2 5/2/5; learning rate 0,04, tối đa 600 cây, patience 50. N3 là cấu hình chung dùng tuning, sau đó chia sẻ tham số đã chọn cho N0–N5 và các kịch bản độ trễ.

{tuning_table}

Số cây final là trung vị best iteration qua bốn fold, theo từng đầu/hạn. Fit cuối chỉ trên 2021–22, không dùng 2023 để early stop. Mean chọn theo RMSE tương đối GFS; median theo MAE tương đối GFS; hai classifier cùng chọn theo Brier tương đối tần suất train, trung bình hai ngưỡng.

GRU thử ba cấu hình nhỏ, cũng trên bốn fold và N3, tối đa 60 epoch/patience 10. Cấu hình được chọn: **{gru['candidate']['name']}**, hidden={gru['candidate']['hidden']}, head={gru['candidate']['head']}, learning rate={gru['candidate']['lr']}, **{gru['epochs']} epoch final**. GRU nhận lịch sử bảy ngày theo thứ tự thời gian, context GFS/tĩnh theo từng hạn, embedding trạm. Loss gồm Tweedie mean + pinball median + 0,5×(BCE mưa + BCE mưa lớn điều kiện đã có mưa); lựa chọn bằng trung bình bốn điểm chuẩn hóa RMSE/MAE/BS1/BS50.

Final LightGBM và GRU dùng seed **17, 29, 43**; lấy trung bình đầu lượng và xác suất đã calibration của ba seed. Ba seed đo một phần biến thiên huấn luyện, không thay ba năm test. GRU được chạy **N3 và N5** để kiểm tra tác dụng toàn bộ dẫn xuất trên cùng mô hình; chưa chạy GRU N0/N1/N2/N4, không tuyên bố ma trận đầy đủ sáu cấu hình × hai kiến trúc.

Năm 2023 dành cho Platt calibration và chọn ngưỡng quyết định. Khi chọn ngưỡng, dùng xác suất cross-fit để từng quý được hiệu chỉnh bằng ba quý khác, bỏ lân cận bảy ngày. Đây là validation cho tuning calibration, không phải mô phỏng forecast lịch sử tại chính năm 2023. Calibrator cuối fit toàn 2023 rồi áp dụng 2024. Đầu lượng và xác suất được ước lượng riêng; ràng buộc lồng nhau không biến chúng thành một phân phối chung nhất quán hoàn toàn.

## 8. Các metric cần đọc

| Chỉ số | Ý nghĩa dễ hiểu | Cách sử dụng | Chiều tốt |
| --- | --- | --- | --- |
| RMSE, mm/24h | Sai số lượng, phạt mạnh lỗi lớn | Chính cho đầu mean; vẫn báo cả hai đầu | Nhỏ |
| MAE, mm/24h | Sai lệch tuyệt đối trung bình | Chính cho đầu median; đối chiếu ZERO | Nhỏ |
| Bias, mm/24h | Dự báo thừa (+) hay thiếu (−) trung bình | Phát hiện thiếu lượng mưa | Gần 0 |
| BS | Trung bình (xác suất − nhãn 0/1)² | Chấm xác suất trước khi chọn cutoff | Nhỏ |
| BSS | 1 − BS/BS của khí hậu tham chiếu | >0 tốt hơn CLIM; <0 kém hơn CLIM | Lớn |
| CSI | H/(H+M+F) | Cân bằng trúng, bỏ sót, báo nhầm | Lớn |
| POD | H/(H+M) | Bắt được bao nhiêu sự kiện thật | Lớn, phải đọc cùng FAR |
| FAR | F/(H+F) | Bao nhiêu cảnh báo là báo nhầm | Nhỏ |

H=trúng, M=bỏ sót, F=báo nhầm; FAR ở đây là false alarm **ratio**, không phải F/(F+correct negatives). Macro tính từng trạm rồi trung bình đều; micro gộp mọi mẫu. RMSE macro là trung bình RMSE trạm, không phải căn của MSE trung bình toàn mạng. BSS macro là trung bình BSS trạm, không nhất thiết bằng 1−macroBS/macroBSref. Trạm không có mẫu/sự kiện thích hợp làm POD/FAR không xác định được báo số hỗ trợ trong CSV, không gán 0 tùy ý.

Tham chiếu CLIM dùng tần suất và mean/median theo trạm–tháng từ các ngày train 2021–22 hợp lệ; shrink về trung bình mạng cùng tháng với trọng số tương đương 20 ngày. Có hai ngưỡng **≥1 và ≥50 mm/24h**. 50 mm là ngưỡng khảo sát mưa lớn của thí nghiệm, chưa khẳng định là ngưỡng cảnh báo chính thức.

Không có ngưỡng POD=0,4 chung để gọi mọi bài toán là tốt. POD phụ thuộc ngưỡng mưa, cutoff xác suất, hạn, địa bàn, số sự kiện và FAR. Luôn dự báo có mưa có thể nâng POD lên 1 nhưng làm báo nhầm lớn. Không so trực tiếp POD ngày tại trạm ở đây với POD mưa giờ/vùng trong một paper khác.

## 9. Kết quả lượng mưa trên dev 2024

{forecast_table}

![So sánh hai đầu lượng mưa trên dev 2024](luong_mua.png)

**In đậm là giá trị điểm thấp nhất trong cột giữa các mô hình chính cùng mẫu**, không phải kết luận hơn có ý nghĩa thống kê. Đơn vị mm/24h. Các đầu mean/median của ZERO/GFS/persistence dùng cùng giá trị dự báo; CLIM/MOS/ML có hai giá trị phù hợp hai mục tiêu. Toàn bộ MAE, RMSE, Bias cho cả hai đầu và các split ở `point_metrics.csv`.

Đối chiếu quan trọng hơn chỉ GFS thô: mô hình nhiều biến có vượt **MOS đơn giản** không?

{mostable}

Chênh âm có lợi cho mô hình đầu. CI95% bao gồm 0 nghĩa là dữ liệu/ước lượng chưa phân biệt rõ trong phép so sánh đó; không có nghĩa hai mô hình chắc chắn bằng nhau. CI không gồm 0 vẫn chỉ là bằng chứng phát triển trên một năm, không phải chứng minh vượt mọi nghiên cứu.

## 10. Xác suất và phát hiện mưa lớn

Mọi seed và ensemble tuân thủ **P(mưa≥50)=P(mưa≥1)×P(mưa≥50 | mưa≥1)**, kể cả sau calibration. Bộ kiểm tra xác nhận không có trường hợp p50>p1. Chọn cùng cutoff cho hai ngưỡng trong từng mô hình/hạn giúp tránh cảnh báo mưa lớn nhưng không cảnh báo có mưa.

{probtable}

GFS/ZERO/persistence trong bảng dùng xác suất suy từ dự báo quyết định 0/1, **không phải dự báo ensemble đã hiệu chỉnh**. BSS so CLIM và đối chứng MOS phù hợp hơn khi đánh giá chất lượng xác suất ML. BSS âm vẫn có thể đi kèm POD cao: mô hình bắt được sự kiện bằng nhiều cảnh báo nhưng xác suất tổng thể kém tham chiếu.

Bảng phát hiện **≥50 mm/24h**, cutoff của MOS/ML được chọn từ 2023, giữ cố định khi chấm 2024; GFS dùng lượng dự báo vượt ngưỡng:

{eventtable}

Không chọn model chỉ bằng POD. Xem đồng thời CSI/FAR/BS/BSS, số sự kiện và độ tin cậy calibration. CSV còn báo cutoff cố định 0,5, ngưỡng ≥1 và số trạm có POD/FAR xác định; không chỉ giữ bảng cho điểm đẹp.

## 11. Dẫn xuất vật lý có giúp không?

{contrasttable}

![Chênh lệch RMSE khi thêm các nhóm biến và CI95%](dan_xuat_ci.png)

Mỗi ô là chênh lệch mô hình đầu trừ mô hình sau. In đậm khi toàn bộ CI95% dưới 0 trong phép so sánh này. N1−N0 là **thêm dữ liệu khí tượng**; N2−N1 và N4−N3 mới trực tiếp hỏi giá trị biểu diễn từ cùng biến gốc. N5−N4 hỏi tương tác gió–ẩm–địa hình. Không lấy N5−N0 rồi gán toàn bộ cải thiện cho công thức vật lý.

Bootstrap lấy khối **14 ngày lịch**, 1.000 lần, ghép cặp cùng mẫu và giữ các trạm trong cùng đợt thời tiết; lấy khối kiểu vòng tròn để xử lý biên chuỗi. Không lấy từng trạm–ngày như quan sát độc lập. CI giữ mô hình đã fit cố định, phản ánh việc lấy mẫu các ngày đánh giá, không bao trùm mọi bất định của huấn luyện/cảm biến. Các khoảng là thăm dò, chưa hiệu chỉnh kiểm định nhiều so sánh; chưa kiểm tra độ nhạy độ dài khối. Lịch hằng ngày vẫn chỉ trải bốn năm nguồn và một năm dev, không biến số mẫu lớn thành hàng chục mùa khí hậu độc lập.

## 12. Khi số đo trạm đến trễ hơn

{latencytable}

Đây là N3 retrain với input bị cắt sớm 1/3/6 giờ, giữ siêu tham số đã chọn, cùng nhãn/mẫu. Có thể điểm tăng hoặc giảm do thông tin và nhiễu huấn luyện; không lấy biến động điểm nhỏ làm bằng chứng nguồn trễ tốt hơn. CI ghép cặp nằm trong `paired_bootstrap.csv` (model `LGB_N3_delay3`/`delay6`). Độ trễ là kịch bản, chưa phải phân bố độ trễ Vrain đo thực tế.

## 13. Nhìn riêng các ngày mưa lớn

{heavytable}

Bảng này **micro**, chỉ chọn mẫu theo mưa thực đo ≥50 mm để chẩn đoán. Bias âm là thiếu lượng. Các mẫu cùng trận có thể phụ thuộc; số ngày issue không phải số trận độc lập và chưa có CI cho bảng này. Không được dùng điều kiện biết trước y để quyết định lúc nào dùng mô hình nào trong vận hành. Toàn bộ các dải <1, 1–10, 10–50, ≥50 và các tháng nằm trong CSV.

Vì nhóm được chọn theo **y thực tế lớn**, ngay cả một dự báo mean được hiệu chỉnh tốt cũng có thể có bias âm trong nhóm này do bất định chưa giải thích được. Do đó, bias có điều kiện là dấu hiệu mô tả hạn chế ở các trận lớn, không tự chứng minh mô hình sai calibration. Cần đọc cùng bias toàn tập, xác suất và đối chứng trên đúng các mẫu.

## 14. Độ dao động giữa ba seed

{seedtable}

Khoảng trên là min–max của **ba mô hình đơn** sau calibration, không phải CI và không phải điểm ensemble. Bảng chính dùng trung bình ba dự báo rồi mới tính metric. Tính trung bình metric của các seed sẽ không cho đúng cùng kết quả.

## 15. Đã kiểm chứng và còn giới hạn gì?

- {verification['lightgbm_estimators_replayed']} estimator LightGBM và {verification['gru_models_replayed']} GRU final được nạp lại để đối chiếu dự báo; scaler GRU/MOS kiểm tra chỉ fit train. Calibrator được fit lại đúng 2023; xác suất và quyết định không mâu thuẫn ngưỡng.
- Dữ liệu đối chiếu toàn bộ {audit['long_horizon_rows']:,} hàng bằng timestamp giờ Vrain, nhãn 24 giờ và các kịch bản trễ; kiểm tra độc lập một mẫu GRIB bằng bốn tọa độ nút. Đây là kiểm tra ghép và tính toán, không phải chứng nhận cảm biến tại trạm.
- Protocol, dữ liệu, chính sách nguồn và mã training có SHA khóa trước fit. Kết quả cũ và slide người dùng sửa đã kiểm tra không đổi. Bộ kiểm thử repository 179 test đã đạt trong đợt triển khai; bằng chứng chi tiết ở log private.
- Tập 2024 đã dùng phát triển ở pilot trước. Giữ nó làm dev là trung thực hơn gọi là test mới. **Chưa mở 2025**; không kết luận thắng nghiên cứu gần đây từ các metric khác miền/nhãn/split.
- GFS thay đổi phiên bản qua năm; nội suy 0,25° và metadata trạm/DEM có giới hạn. Chưa kiểm định trạm chưa thấy, chưa xác nhận cập nhật/cảm biến lịch sử, chưa thử nhiều mùa test độc lập.
- Chỉ chấm phần dữ liệu đầy đủ sau QC. Nếu trạm dễ mất dữ liệu khi mưa lớn, phần bị loại có thể khó hơn phần được chấm; chưa chứng minh thiếu dữ liệu là ngẫu nhiên. Cùng 57 trạm không có nghĩa mỗi issue đều có đủ 57 mẫu.
- Bản mới thay đồng thời lịch mẫu, mục tiêu mean/median, tuning và calibration. Không quy toàn bộ chênh lệch với pilot tuần cho riêng việc tăng tần suất issue.

## 16. Nhóm nên dùng kết quả này như thế nào?

Dùng các bảng đầy đủ để quyết định liệu phần nhiều biến có đáng giữ so với MOS; xem giá trị dẫn xuất bằng các cặp N2−N1, N4−N3, N5−N4; kiểm tra mưa lớn bằng cả lượng lẫn xác suất. Nếu CI chưa phân biệt, ghi “chưa có bằng chứng rõ” thay vì cố chọn một bảng đẹp. Chưa dùng độ trễ giả định để khẳng định triển khai realtime.

Bước tiếp theo trước kiểm định cuối: chốt mô hình/cấu hình/cutoff/metric sau khi xem dev, xác định quy tắc xử lý nguồn trễ hoặc thiếu trong vận hành, ghi quyết định đóng băng, rồi mới cho phép đánh giá 2025 một lần. Mọi thay đổi sau khi thấy test phải được công bố là phát triển tiếp và cần holdout mới. Thí nghiệm hiện tại **chưa tự thực hiện bước mở test**.

## 17. Tệp bàn giao và tái lập

- Báo cáo này: `BAO_CAO_HANG_NGAY_V2.md` và bản Word cùng tên. `README.md` giải thích các bảng số.
- Các bảng CSV công khai chỉ chứa tổng hợp; không chứa mã/tọa độ trạm hay chuỗi số đo/dự báo từng thời điểm. `protocol.json`, `training_provenance.json`, `dataset_verification.json`, `model_verification.json` lưu bằng chứng.
- Dataset private: `data/processed/gfs_station_daily_v2_2026_11_10/dataset.parquet`. Một hàng là một trạm–issue–hạn; ba hàng liên tiếp tạo một mẫu. Feature N0–N5 được liệt kê chính xác trong protocol. Không dùng tên `full_features` cũ để thay file này.
- GFS cache, checkpoint, calibrator và dự báo private: `data/operational/gfs_station_daily_v2_2026_11_10/`. Không đưa dữ liệu trạm/thông tin đăng nhập lên GitHub công khai.
- Chuỗi lệnh: prepare → collect → audit sources → build → validate → trees → GRU → evaluate → verify models → publish. `scripts/run_gfs_daily_pipeline.py` chạy phần build đến evaluate và dừng nếu có lỗi. Chạy verify/publish sau đó. Không tái tune bằng cách xóa khóa hoặc ghi đè kết quả cũ.
'''
    interpretation=PUBLIC/'KET_LUAN.md'
    if interpretation.exists():
        marker='## 1. Bài toán được thực hiện'
        text=text.replace(marker,interpretation.read_text(encoding='utf8')+'\n\n'+marker)
    (PUBLIC/'BAO_CAO_HANG_NGAY_V2.md').write_text(text,encoding='utf8')
    from scripts.plot_gfs_daily import main as plot
    plot()
    document(text,PUBLIC/'BAO_CAO_HANG_NGAY_V2.docx')
    readme='''# Thí nghiệm GFS–Vrain hằng ngày v2

Đọc [báo cáo đầy đủ](BAO_CAO_HANG_NGAY_V2.md) hoặc [bản Word](BAO_CAO_HANG_NGAY_V2.docx). 57 trạm, ba tổng 24 giờ; LightGBM N0–N5, GRU N3/N5, ba seed; train 2021–22/cal 2023/dev 2024, chưa mở 2025.

| Tệp | Nội dung |
| --- | --- |
| point_metrics.csv | MAE/RMSE/Bias macro và micro cho mean/median, tất cả split/hạn |
| probability_metrics.csv | BS/BSS và số sự kiện; BSS tham chiếu CLIM |
| event_metrics.csv | CSI/POD/FAR tại p=0,5 và cutoff chọn từ cal; số trúng/bỏ sót/báo nhầm |
| paired_bootstrap.csv | Chênh ghép cặp và CI95%, khối 14 ngày, 1.000 lần, chưa chỉnh nhiều so sánh |
| conditional_amount_metrics.csv | Sai số theo dải mưa thực đo, micro; chỉ chẩn đoán |
| monthly_point_metrics.csv | Sai số theo tháng năm dev |
| station_improvement_summary.csv | Số/tỷ lệ trạm cải thiện so ZERO/GFS/CLIM/MOS, không công khai ID |
| reliability.csv | Tần suất thực so xác suất dự báo theo bin, hạn và ngưỡng |
| seed_metrics.csv | Điểm từng seed; không thay điểm ensemble |
| label_distribution.csv | Tỷ lệ khô, phân vị và số sự kiện theo split/hạn |
| tree_tuning_trials.csv / gru_tuning_trials.csv | Tuning theo các fold 2022 |
| tree_selection.json / gru_selection.json | Tham số chọn trước dev |
| source_latency_audit.json / source_coverage_policy.json | Bằng chứng nguồn, hai ngày loại và giới hạn độ trễ |
| dataset_audit.json / dataset_verification.json | Số mẫu, split, QC và replay timestamp |
| protocol.json / training_provenance.json / model_verification.json | Khóa thí nghiệm và kiểm chứng kết quả |
| runtime_environment.json | Phiên bản thư viện và GPU quan sát khi replay checkpoint |

Các ngày/predictor/nhãn trạm/checkpoint nằm ngoài Git; đây là tệp tổng hợp để chia sẻ. Các kết quả 2024 là phát triển, không phải test cuối.
'''
    (PUBLIC/'README.md').write_text(readme,encoding='utf8')
    print(json.dumps(dict(status='published',markdown=str(PUBLIC/'BAO_CAO_HANG_NGAY_V2.md'),word=str(PUBLIC/'BAO_CAO_HANG_NGAY_V2.docx'))),flush=True)


if __name__=='__main__':main()
