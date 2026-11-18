"""Publish understandable aggregate-only report and editable presentation."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import re
import zipfile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Inches as DI,Pt as DP
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from src.gfs_window import BASE,PUBLIC,FEATURES,now,sha,read_json,write_json,save_csv,load_frame,save_parquet
from scripts.run_gfs_window import check_freeze

NAVY='16354B';TEAL='087F8C';GRAY='566975';BG='F7FAFC'
SCOPE='retrospective2026_modern'
LABELS={'A':'A · 2 năm/Tweedie','B':'B · 4 năm/Tweedie','C':'C · 2 năm/L2','D':'D · 4 năm/L2',
    'N0':'N0 · 16 biến','N1':'N1 · 21 biến','N3':'N3 · 26 biến',
    'GFS':'GFS nguyên bản','MOS_LONG':'MOS · 4 năm','MOS_SHORT':'MOS · 2 năm',
    'CLIM_LONG':'Khí hậu · 4 năm','CLIM_SHORT':'Khí hậu · 2 năm','ZERO':'Luôn 0 mm','PERSIST':'Lặp mưa ngày trước'}


def num(value,digits=3):
    return '—' if pd.isna(value) else f'{float(value):.{digits}f}'.replace('.',',')


def textfile(path,value):
    Path(path).write_text(value.rstrip()+'\n',encoding='utf-8',newline='\n')


def readable(value):
    value=str(value)
    prefixes='ngày|Ngày|năm|Năm|modern|Modern|train|fit|CV|quý|gap|cutoff|sau|trước|trên|bằng|họ|tổng|khối|issue|cùng|đủ|Có|có'
    value=re.sub(r'\b('+prefixes+r')(?=\d)',r'\1 ',value)
    for a,b in [('đại diệnA/C','đại diện A/C'),('đại diệnB/D','đại diện B/D'),('bí danhB','bí danh B'),
                ('bằngCV','bằng CV'),('từCV','từ CV'),('chunghead','chung head'),('replaycheckpoint','replay checkpoint')]:
        value=value.replace(a,b)
    return value


def table_md(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(str(v) for v in row)+' |' for row in rows])


def wide(points,models,metric='macro_rmse',functional='mean',scope=SCOPE):
    t=points[points.evaluation_set.eq(scope)&points.functional.eq(functional)].pivot(index='model',columns='horizon',values=metric).reindex(models)
    rows=[]
    minima=t.min(axis=0)
    for model,row in t.iterrows():
        values=[]
        for h in (1,2,3):
            value=num(row[h]);values.append('**'+value+'**' if np.isclose(row[h],minima[h]) else value)
        rows.append([LABELS.get(model,model)]+values)
    return rows


class Slides:
    def __init__(self):
        self.p=Presentation();self.p.slide_width=Inches(13.333);self.p.slide_height=Inches(7.5)
    def text(self,s,x,y,w,h,value,size=22,color=NAVY,bold=False):
        box=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=box.text_frame
        tf.word_wrap=True;tf.margin_left=0;tf.margin_right=0;tf.margin_top=0;tf.margin_bottom=0
        for i,line in enumerate(str(value).split('\n')):
            p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.space_after=Pt(12)
            self.rich(p,line,size,color,bold)
        return box
    @staticmethod
    def rich(p,value,size,color,bold=False):
        for part in re.split(r'(\*\*.*?\*\*)',readable(value)):
            if not part:continue
            r=p.add_run();r.text=part[2:-2] if part.startswith('**') and part.endswith('**') else part
            r.font.name='Aptos';r.font.size=Pt(size);r.font.bold=bold or (part.startswith('**') and part.endswith('**'));r.font.color.rgb=RGBColor.from_string(color)
    def add(self,title,body='',note=''):
        s=self.p.slides.add_slide(self.p.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=RGBColor.from_string(BG)
        self.text(s,.55,.22,12.2,.23,'PBL6  •  NGHIÊN CỨU DỰ BÁO MƯA TẠI TRẠM',11,TEAL,True)
        self.text(s,.55,.70,12.2,.85,title,29,bold=True)
        if body:self.text(s,.65,1.85,12.,4.4,body,23)
        self.text(s,.55,7.04,12.2,.22,f'18/11/2026 • 57 trạm • 2026: hồi cứu đã xem • {len(self.p.slides):02d}',10.5,GRAY)
        s.notes_slide.notes_text_frame.text=note or body
        return s
    def table(self,s,headers,rows,widths=None,y=1.8,size=20,row_h=.55):
        n=len(headers);widths=widths or ([4.3]+[7.8/(n-1)]*(n-1))
        shape=s.shapes.add_table(len(rows)+1,n,Inches(.65),Inches(y),Inches(12.1),Inches(row_h*(len(rows)+1)))
        table=shape.table
        for j,w in enumerate(widths):table.columns[j].width=Inches(w)
        for i,row in enumerate([headers]+rows):
            table.rows[i].height=Inches(row_h)
            for j,v in enumerate(row):
                cell=table.cell(i,j);cell.margin_top=Inches(.06);cell.margin_bottom=Inches(.03);cell.margin_left=Inches(.1);cell.margin_right=Inches(.06)
                cell.fill.solid();cell.fill.fore_color.rgb=RGBColor.from_string(NAVY if i==0 else ('EAF2F5' if i%2 else 'FFFFFF'))
                tf=cell.text_frame;tf.word_wrap=True;p=tf.paragraphs[0];p.space_after=Pt(0)
                self.rich(p,v,size,'FFFFFF' if i==0 else NAVY,i==0)
        return shape
    def caption(self,s,value,y=6.35):self.text(s,.65,y,12.05,.48,value,17,GRAY)


def document(markdown,path):
    doc=Document();normal=doc.styles['Normal'];normal.font.name='Calibri';normal.font.size=DP(11)
    section=doc.sections[0];section.left_margin=DI(.8);section.right_margin=DI(.8)
    lines=markdown.splitlines();i=0
    def rich(par,text):
        for part in re.split(r'(\*\*.*?\*\*)',text):
            run=par.add_run(part[2:-2] if part.startswith('**') and part.endswith('**') else part)
            run.bold=part.startswith('**') and part.endswith('**')
    while i<len(lines):
        line=lines[i]
        if line.startswith('|'):
            block=[]
            while i<len(lines) and lines[i].startswith('|'):
                values=[x.strip() for x in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r'[-: ]+',x) for x in values):block.append(values)
                i+=1
            t=doc.add_table(rows=1,cols=len(block[0]));t.style='Light Shading Accent 1'
            for j,v in enumerate(block[0]):rich(t.rows[0].cells[j].paragraphs[0],v)
            for row in block[1:]:
                cells=t.add_row().cells
                for j,v in enumerate(row):rich(cells[j].paragraphs[0],v)
            continue
        if line.startswith('#'):doc.add_heading(line.lstrip('# '),min(3,len(line)-len(line.lstrip('#'))))
        elif line.strip():rich(doc.add_paragraph(),line)
        i+=1
    for image in ['rmse_factorial.png','factorial_differences.png','dry_heavy.png']:
        doc.add_picture(str(PUBLIC/image),width=DI(6.6))
    doc.save(path)


def figures(points,pairs,tail):
    plt.rcParams.update({'font.size':12})
    models=['GFS','MOS_LONG','A','B','C','D']
    fig,ax=plt.subplots(figsize=(10,5.5));x=np.arange(len(models))
    for h,c in [(1,'#147F86'),(2,'#466DA2'),(3,'#B07A43')]:
        s=points[points.evaluation_set.eq(SCOPE)&points.functional.eq('mean')&points.horizon.eq(h)].set_index('model')
        ax.bar(x+(h-2)*.24,s.loc[models,'macro_rmse'],.23,color=c,label=f'Ngày {h}')
    ax.set_xticks(x,['GFS','MOS 4yr','A: 2yr TW','B: 4yr TW','C: 2yr L2','D: 4yr L2']);ax.set_ylabel('Station-macro RMSE (mm/24h)');ax.legend();ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(PUBLIC/'rmse_factorial.png',dpi=180);plt.close(fig)
    s=pairs[pairs.evaluation_set.eq(SCOPE)&pairs.family.eq('factorial')].reset_index(drop=True)
    fig,ax=plt.subplots(figsize=(10,6));y=np.arange(len(s))
    ax.errorbar(s.difference,y,xerr=np.array([s.difference-s.simultaneous_ci_low,s.simultaneous_ci_high-s.difference]),fmt='o',color='#147F86',capsize=3)
    ax.set_yticks(y,[f'{r.first}-{r.reference} / D{r.horizon}' for r in s.itertuples()]);ax.axvline(0,color='#A43434',ls='--');ax.set_xlabel('RMSE difference (mm/24h); negative favors first model\nExploratory simultaneous95%CI, family12');ax.grid(axis='x',alpha=.2);fig.tight_layout();fig.savefig(PUBLIC/'factorial_differences.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.8))
    for ax,bin_name,title in zip(axes,['under1','ge50'],['Observed dry (<1mm)','Observed heavy (>=50mm)']):
        z=tail[tail.evaluation_set.eq(SCOPE)&tail.horizon.eq(1)&tail.observed_bin.eq(bin_name)].set_index('model')
        ax.bar(['A','B','C','D'],z.loc[['A','B','C','D'],'micro_bias'],color=['#6D9FA4','#147F86','#A1AEC4','#466DA2']);ax.axhline(0,color='black',lw=.8);ax.set_title(title);ax.set_ylabel('Mean prediction - observation (mm)');ax.grid(axis='y',alpha=.2)
    fig.suptitle('Day1 conditional bias: retrospective2026 modern');fig.tight_layout();fig.savefig(PUBLIC/'dry_heavy.png',dpi=180);plt.close(fig)


def main():
    check_freeze();verify=read_json(PUBLIC/'verification.json')
    if verify['status']!='passed':raise ValueError('Independent verification required')
    points=pd.read_csv(PUBLIC/'point_metrics.csv');pairs=pd.read_csv(PUBLIC/'paired_comparisons.csv');tail=pd.read_csv(PUBLIC/'dry_heavy_metrics.csv')
    protected=read_json(BASE/'protected_before.json')
    protected_files=len({str((ROOT/rel).resolve()).lower() for rel in protected})
    write_json(PUBLIC/'verification_notes.json',dict(protected_checksum_entries=len(protected),
        protected_distinct_files=protected_files,explanation='Some old manifests use Windows backslashes and newer entries use forward slashes; both checks refer to the same preserved file.'))
    events=pd.read_csv(PUBLIC/'event_metrics.csv');prob=pd.read_csv(PUBLIC/'probability_metrics.csv');labels=pd.read_csv(PUBLIC/'label_distribution.csv')
    seeds=pd.read_csv(PUBLIC/'seed_metrics.csv');selection=read_json(PUBLIC/'selection.json');freeze=read_json(PUBLIC/'model_freeze_summary.json');tests=read_json(PUBLIC/'tests_verification.json')
    figures(points,pairs,tail)
    catalog=pd.read_csv(ROOT/'reports/gfs_temporal_2026_11_17/feature_catalog.csv');catalog=catalog[catalog.feature.isin(FEATURES['N3'])].copy()
    catalog['config']=catalog.feature.map(lambda n:'N0/N1/N3' if n in FEATURES['N0'] else 'N1/N3' if n in FEATURES['N1'] else 'N3')
    save_csv(catalog,PUBLIC/'feature_catalog.csv')
    modern=points[points.evaluation_set.eq(SCOPE)&points.functional.eq('mean')].set_index(['model','horizon'])
    differences=[]
    for a,b in [('B','A'),('D','C'),('C','A'),('D','B')]:
        values=[modern.loc[(a,h),'macro_rmse']-modern.loc[(b,h),'macro_rmse'] for h in (1,2,3)]
        differences.append([f'{a} − {b}']+[num(v) for v in values])
    selected=read_json(PUBLIC/'model_catalog.json')['selected_prospective_case']
    claim=pairs[pairs.evaluation_set.eq(SCOPE)&pairs.family.eq('factorial')]
    supported=int(claim.supported_exploratory_improvement.sum())
    ablation=pairs[pairs.evaluation_set.eq(SCOPE)&pairs.family.eq('ablation')]
    supported_a=int(ablation.supported_exploratory_improvement.sum())
    outcome=f'Trong 12 phép so A–D trên modern 2026, {supported} phép đạt tiêu chí cải thiện thăm dò đã định; ablation có {supported_a}/6. Đây không phải xác nhận trên test chưa dùng.'
    delta_b=[modern.loc[('B',h),'macro_rmse']-modern.loc[('A',h),'macro_rmse'] for h in (1,2,3)]
    passing=claim[claim.supported_exploratory_improvement]
    passing_text='; '.join(f'{r.first}−{r.reference}, ngày {r.horizon}: {num(r.difference)} mm/24h' for r in passing.itertuples()) or 'chưa có'
    explanation=(f'Tweedie train dài (B) so với train ngắn (A) đổi RMSE ngày 1/2/3 lần lượt '
        f'{num(delta_b[0])}/{num(delta_b[1])}/{num(delta_b[2])} mm/24h. Cả ba điểm giảm, nhưng chưa phép nào đạt đồng thời hai tiêu chí suy luận đã định. '
        f'Phép đạt tiêu chí thăm dò: {passing_text}. Đổi sang L2 không cho lợi ích nhất quán qua các hạn, nên chưa có cơ sở thay mặc định Tweedie bằng L2. '
        'Khí tượng thô có điểm cải thiện ở cả ba hạn so với N0, nhưng chưa đạt tiêu chí suy luận ở vòng 2026 này; địa hình chỉ thay đổi rất nhỏ. '
        'Đây là tín hiệu để theo dõi tiếp, không phải chứng minh đã cải thiện chắc chắn trên một tập kiểm định mới.')
    metrics=[['RMSE','Phạt mạnh những lần sai lượng mưa lớn; mm/24h','Chính cho đầu mean','Nhỏ hơn'],
        ['MAE','Trung bình sai lệch tuyệt đối; mm/24h','Chính cho đầu median','Nhỏ hơn'],
        ['Bias','Dự báo trừ quan trắc; âm: dự báo thiếu','Theo dõi thiếu/thừa','Gần 0'],
        ['BS','Sai số bình phương xác suất so với có/không','Chấm xác suất trước khi chọn cutoff','Nhỏ hơn'],
        ['BSS','1 − BS/BS khí hậu cùng mẫu','Âm: kém khí hậu tham chiếu','Lớn hơn'],
        ['CSI','H/(H+M+F)','Cân bằng trúng, bỏ sót, báo nhầm','Lớn hơn'],
        ['POD','H/(H+M)','Bắt được bao nhiêu sự kiện thực','Lớn hơn'],
        ['FAR','F/(H+F)','Bao nhiêu lần báo có là báo nhầm','Nhỏ hơn']]
    feature_rows=[['N0','16','Mưa GFS + lịch/vị trí/ID + 7 ngày mưa và tổng 1/6/24h'],
        ['N1','21','N0 + T/RH/u/v tại 850 hPa và hơi nước toàn cột'],
        ['N3','26','N1 + 5 biến địa hình DEM; không thêm dẫn xuất gió–ẩm']]
    case_rows=[['A','2021–2022','Tweedie p=1,5','26'],['B','2021–2024','Tweedie p=1,5','26'],
        ['C','2021–2022','L2 bình phương sai số','26'],['D','2021–2024','L2 bình phương sai số','26']]
    count_rows=[]
    for r in labels[labels.horizon.eq(1)].itertuples():
        count_rows.append([r.evaluation_set.replace('retrospective2026_',''),str(r.samples),str(r.stations),str(r.issue_dates),str(r.events_ge50)])
    mainrows=wide(points,['A','B','C','D','GFS','MOS_LONG'])
    abrows=wide(points,['N0','N1','N3','GFS','MOS_LONG'])
    medianrows=wide(points,['A','B','N0','N1','GFS','MOS_LONG'],'macro_mae','median')
    probability_rows=[]
    for model in ['A','B','N0','N1','GFS','MOS_LONG']:
        z=prob[prob.evaluation_set.eq(SCOPE)&prob.model.eq(model)&prob.threshold_mm.eq(50)].set_index('horizon')
        probability_rows.append([LABELS[model]]+[num(z.loc[h,'macro_bss']) for h in (1,2,3)])
    warning_rows={}
    for h in (1,2,3):
        rows=[]
        for model in ['A','B','N0','N1','GFS','MOS_LONG']:
            rule='calibration_selected' if model!='GFS' else 'fixed_0.5'
            r=events[events.evaluation_set.eq(SCOPE)&events.horizon.eq(h)&events.model.eq(model)&events.threshold_mm.eq(50)&events.decision_rule.eq(rule)].iloc[0]
            rows.append([LABELS[model],num(r.cutoff,2),num(r.macro_pod),num(r.macro_far),num(r.macro_csi)])
        warning_rows[h]=rows
    seedrows=[]
    for model in ['A','B','C','D']:
        cells=[]
        for h in (1,2,3):
            z=seeds[seeds.evaluation_set.eq(SCOPE)&seeds.model.eq(model)&seeds.horizon.eq(h)].macro_rmse
            cells.append(num(z.min())+'–'+num(z.max()))
        seedrows.append([LABELS[model]]+cells)
    tail_rows=[]
    for model in ['A','B','C','D']:
        z=tail[tail.evaluation_set.eq(SCOPE)&tail.horizon.eq(1)&tail.model.eq(model)].set_index('observed_bin')
        tail_rows.append([model,num(z.loc['under1','micro_bias']),num(z.loc['ge50','micro_bias']),num(z.loc['ge50','fraction_total_squared_error']*100,1)+'%'])
    header=['Mô hình','Ngày 1','Ngày 2','Ngày 3']
    summary=f'''# Thêm năm huấn luyện và đổi hàm mất mát: kết quả nghiên cứu mới

Ngày hoàn thành: 18/11/2026. Phiên bản: gfs_training_window_2026_11_18.

## Kết luận đọc trước

{outcome}

{explanation}

Phương án đưa vào ghi dự báo tương lai là {selected}: cửa sổ train dài đã định trước, loss {selection['selected_loss']} được chọn chỉ từ CV 2022. Không chọn lại mô hình bằng kết quả 2026. Mô hình có điểm tốt nhất trên bảng hồi cứu có thể khác lựa chọn này; cần báo trung thực cả hai.

Mục tiêu là mưa tại từng trạm trong ba ngày tới, không phải mưa trung bình toàn Đà Nẵng. Một mô hình chung phục vụ 57 trạm; mỗi trạm–issue có ba nhãn 24h riêng. Khí tượng là dự báo GFS, nhãn là số đo Vrain sau QC.

## Bốn cấu hình và dữ liệu

{table_md(['Mã','Năm fit','Hàm mất mát mean','Số biến'],case_rows)}

Train ngắn: 35.116 mẫu trạm–issue; train dài: 72.886; calibration 2025: 18.723. Mỗi mẫu có ba hạn, không coi ba hàng là ba trạm độc lập. Chỉ B/D thêm 2023–2024 vào fit; 2025 chỉ hiệu chỉnh xác suất/cutoff. Mọi trọng số cây và tham số khí hậu/MOS đều dừng ở 2024. Các phiên bản cũ giữ nguyên split và kết quả cũ.

{table_md(['Tập 2026','Mẫu D1','Trạm','Issue','Sự kiện ≥50 D1'],count_rows)}

2026 chưa đủ năm và đã được xem ở vòng trước, vì vậy toàn bộ điểm mới là hồi cứu. Hai API không được nối thành chuỗi đồng nhất. Legacy có rất ít mưa lớn; không kết luận chất lượng cảnh báo từ nhóm này một mình. Các bảng chính dưới đây dùng modern 2026; CSV báo cả hai nhóm, từng hạn.

## Đầu vào và thời gian

{table_md(['Cấu hình','Số biến','Nội dung'],feature_rows)}

GFS được nội suy song tuyến tính từ bốn nút lưới 0,25° bao quanh tọa độ trạm, không phải ô đo mưa quanh cảm biến. Nhiều trạm gần nhau có thể chia sẻ trường khí tượng quy mô lớn. Mưa quá khứ lấy tại chính trạm; metadata/địa hình mô tả vị trí. DEM không phải cao độ cảm biến đã khảo sát. Xem feature_catalog.csv để biết tên và đơn vị từng biến.

Issue 19h Việt Nam dùng GFS khởi tạo 00 UTC cùng ngày và mưa gần nhất kết thúc trước 18h. GFS mưa đích là thông tin dự báo đã có trước issue, không phải quan trắc tương lai. Khí tượng T/RH/u/v/PWAT là trạng thái dự báo giữa mỗi cửa sổ, không gọi là trung bình ngày. Ba nhãn: 19h hôm nay→19h mai; 19h mai→19h ngày kế; tiếp tục một ngày nữa. Mỗi nhãn cần đủ 24 giờ cùng API, không điền thiếu bằng 0/vệ tinh.

## Tuning và ba seed

Đã chạy {selection['cv_estimators']} fit CV: ba ứng viên × hai loss × bốn quý 2022 × ba hạn. Fold chỉ dùng quá khứ, purge toàn bộ 72h nhãn và gap 7 ngày. Metric early stopping là RMSE trung bình đều giữa các trạm. Candidate chung được chọn: {selection['candidate']['name']}, số lá {selection['candidate']['num_leaves']}; số cây ngày 1/2/3: {selection['trees']['1']}/{selection['trees']['2']}/{selection['trees']['3']}. Ngân sách này áp dụng chung cho A–D và ablation, không tìm lại trên 2025/2026.

Điểm CV chuẩn hóa trung bình của hai loss tại candidate chung: Tweedie {num(selection['objective_scores']['tweedie'],5)}, L2 {num(selection['objective_scores']['l2'],5)}. Điểm nhỏ hơn tốt hơn; đây là trung bình tỷ lệ RMSE so với GFS theo fold/hạn, không phải số mm.

Seed 17/29/43 là ba lần chạy với khởi tạo nguồn số ngẫu nhiên khác nhau cho việc lấy mẫu hàng/biến trong LightGBM. Cùng dữ liệu và cấu hình vẫn có thể cho cây khác nhau. Dự báo chính là trung bình ba lần; bảng sau là khoảng RMSE của từng lần, không phải khoảng tin cậy và không phải ba lần chia lại dữ liệu.

{table_md(header,seedrows)}

Đã fit {freeze['total_lightgbm_estimators']} estimator LightGBM cuối cùng: 54 đầu mean và 108 đầu phụ. Không có GRU/TFT/Informer mới ở vòng này. A/C dùng chung median/xác suất, B/D dùng chung median/xác suất; vì vậy đổi loss mean không tự tạo ra khác biệt cảnh báo. Ngoài ra có hai bộ khí hậu và các đối chứng MOS fit riêng theo cửa sổ.

A là mốc của protocol mới, không phải tái sử dụng nguyên checkpoint N3 cũ: ngân sách cây đã được chọn chung lại qua cả hai loss. Xác suất cũng được hiệu chỉnh bằng năm 2025 thay cho 2023. Vì vậy để tách tác động số năm/loss, dùng các phép so trong bảng A–D; không ghép điểm cũ với điểm mới rồi quy toàn bộ chênh lệch cho một thay đổi.

## Các metric và mục tiêu đầu ra

{table_md(['Chỉ số','Ý nghĩa','Vai trò','Chiều tốt'],metrics)}

H là báo trúng; M là bỏ sót; F là báo nhầm. Không có mốc POD 0,4 hay 0,6 tốt chung cho mọi bài toán. POD tăng có thể đi cùng FAR tăng khi hạ cutoff. BSS âm nghĩa là xác suất kém khí hậu tham chiếu trên cùng mẫu; không nói trực tiếp lượng mưa sai bao nhiêu mm. Ở vòng này mọi BSS dùng cùng khí hậu fit 2021–2024 để so sánh công bằng.

Đầu mean nhằm dự báo mức mưa kỳ vọng, phù hợp RMSE; đầu median nhằm giá trị trung vị, phù hợp MAE và có thể gần 0 trong ngày ít khả năng mưa. Không dùng MAE của median để khẳng định đầu mean tốt hơn, hoặc ngược lại. Điểm macro cho mỗi trạm trọng số như nhau; micro gộp mọi mẫu và được báo riêng trong CSV.

Vì sao thử L2? L2 phạt bình phương sai số lượng mưa, gần trực tiếp với mục tiêu RMSE đang ưu tiên. Tweedie p=1,5 là lựa chọn hiện có cho lượng mưa không âm, có nhiều số 0 và giá trị dương lệch mạnh. Cả hai đầu đều nhằm dự báo mean; không phải một bên dự báo mean còn bên kia dự báo median. Với dữ liệu hữu hạn và cây giới hạn, hai loss tạo cách cập nhật khác nhau. L2 có thể tập trung hơn vào sai số lớn nhưng cũng nhạy với các đợt mưa cực đoan; cần đo thực tế, không mặc định phù hợp tên metric là sẽ tốt hơn.

## Kết quả lượng mưa — modern 2026

RMSE đầu mean, đơn vị mm/24h; in đậm giá trị nhỏ nhất trong mỗi cột của bảng này, không hàm ý có ý nghĩa thống kê.

{table_md(header,mainrows)}

GFS là dự báo khí tượng nguyên bản. MOS là hậu xử lý đơn giản từ mưa GFS và lịch mùa (Ridge cho mean, hồi quy phân vị cho median, logistic cho xác suất), giúp kiểm tra liệu LightGBM có hơn hiệu chỉnh đơn giản cùng nguồn hay không. ZERO và khí hậu/ngày trước là những mốc tối thiểu; xem bảng CSV đầy đủ để tránh chỉ so với đối chứng yếu.

Chênh lệch RMSE: âm có lợi cho cấu hình đứng trước, dương là xấu hơn.

{table_md(['Phép so','Ngày 1','Ngày 2','Ngày 3'],differences)}

B−A/D−C: tác động thêm năm với loss giữ nguyên. C−A/D−B: tác động đổi loss với số năm giữ nguyên. Không diễn giải một chênh lệch nhỏ ở riêng một hạn thành tiến bộ chắc chắn.

## Giá trị đặc trưng với cửa sổ dài

Loss {selection['selected_loss']} được chọn từ CV2022, dùng chung candidate/số cây/ba seed và cùng mẫu.

{table_md(header,abrows)}

N1−N0 kiểm tra khí tượng thô, N3−N1 kiểm tra địa hình. N3 là bí danh của {selected}, không fit thêm. Kết quả phản ánh thiết kế và ngân sách này, không chứng minh một nhóm biến vô ích ở mọi mô hình.

## Trung vị và xác suất

MAE đầu median, mm/24h. A đại diện A/C; B đại diện B/D vì chung đầu phụ.

{table_md(header,medianrows)}

BSS cho mưa ≥50 mm/24h; lớn hơn tốt hơn, 0 ngang khí hậu, âm kém khí hậu. Khí hậu tham chiếu chung fit2021–2024.

{table_md(header,probability_rows)}

Hiệu chỉnh dùng Platt trên năm 2025 theo từng seed. Cutoff chọn bằng cách giữ riêng từng quý, có khoảng cách 7 ngày, sau đó fit calibrator trên toàn năm 2025. Xác suất p50=p1×P(y≥50|y≥1), nên không có mưa lớn với xác suất cao hơn mưa ≥1. Hai ngưỡng 1/50 dùng chung cutoff mỗi cấu hình/hạn để quyết định cảnh báo lồng nhau. Đây là ngưỡng nghiên cứu cho tổng 24h tại trạm, không tự nhận là quy chuẩn vận hành.

'''
    for h in (1,2,3):summary+=f"\n### Cảnh báo ≥50 mm/24h — ngày {h}\n\n"+table_md(['Mô hình','Cutoff','POD','FAR','CSI'],warning_rows[h])+"\n\nGFS dùng quyết định xác định từ lượng mưa, thể hiện bằng xác suất 0/1; các mô hình khác dùng cutoff chọn bằng2025. CSV cũng báo cutoff0,5 để kiểm tra độ nhạy.\n"
    summary+=f'''
## Ngày khô, mưa lớn và độ chắc chắn

Ngày1 modern2026; Bias theo nhóm quan trắc và phần trăm tổng sai số bình phương thuộc nhóm ≥50. Các nhóm này chỉ dùng hậu kiểm, không được biết trước khi dự báo.

{table_md(['Cấu hình','Bias ngày khô','Bias mưa ≥50','% sai số bình phương từ ≥50'],tail_rows)}

Ví dụ đổi từ B sang D (cùng train bốn năm, chỉ đổi loss đầu mean) ở ngày 1: L2 dự báo bớt thiếu trong nhóm mưa ≥50 nhưng báo thừa nhiều hơn trong ngày khô; RMSE chung của D vẫn cao hơn B. Vì thế không chọn loss chỉ theo một nhóm mưa hoặc một chỉ số thuận lợi. Các xác suất của B/D là giống nhau, nên phần đánh đổi này là của lượng mưa mean, không phải thay đổi cảnh báo xác suất.

Không có nhãn nào bị bỏ vì mưa quá lớn hoặc vì mô hình dự báo sai. Kiểm tra nguồn/QC không chứng nhận tuyệt đối cảm biến. Mưa lớn hiếm, các trạm và các cửa sổ trong cùng đợt mưa phụ thuộc nhau.

Bootstrap ghép khối 14 ngày, 5.000 lần; khoảng 95% đồng thời Bonferroni theo họ 12 phép A–D và họ 6 phép ablation; p bootstrap định tâm/Holm là xấp xỉ. “Đạt tiêu chí” đòi hỏi cả CI đồng thời nằm dưới 0 và Holm p<0,05. {outcome} Xem paired_comparisons.csv cho từng hiệu ứng, CI và số ngày có dữ liệu. Hiệu chỉnh nhiều so sánh không xóa được việc đã xem năm 2026 trước khi thiết kế nghiên cứu mới.

## Ghi dự báo tương lai

Đã lấy snapshot nguồn trực tiếp, chưa coi đó là kiểm chứng dự báo. Tệp live_availability_snapshot.json ghi thời điểm và độ phủ thực tế, không dùng Last-Modified lịch sử để giả định nguồn đã có sẵn. Phiên đăng nhập hết hạn đã được làm mới riêng; không đưa thông tin đăng nhập vào báo cáo/Git.

Tiến trình theo dõi giới hạn một issue tương lai lúc 19h Việt Nam, thử lấy dữ liệu trước issue. Chỉ ghi dự báo nếu có đủ lịch sử cùng API và hoàn tất trước issue; không dùng giờ đo sau cutoff 18h. Máy và mạng cần còn hoạt động; nếu nguồn chậm/thiếu thì đánh dấu không phát. Tất cả A–D được ghi để kiểm tra, lựa chọn {selected} được định trước bằng CV.

Nhận nhãn sau 72h cộng độ trễ, lưu riêng với hash của dự báo đã phát. Một issue không đủ kết luận kỹ năng dự báo; cần theo dõi nhiều đợt mưa và cả ngày khô. Các lần hồi phát, nguồn lấy sau issue hoặc mô hình chọn bằng nhãn tương lai không được gọi là kiểm chứng dự báo trước sự kiện.

## Kiểm chứng và giới hạn

{tests['tests']} bài kiểm tra đạt. Đã đối chiếu độc lập {verify['evaluation_rows']:,} hàng đánh giá, {verify['independent_metric_values']:,} giá trị metric và {verify['replayed_prediction_values']:,} giá trị dự báo từ checkpoint. Thay nhãn tương lai không làm đổi dự báo. Đã kiểm tra trực tiếp bootstrap theo ngày, ngân sách 54 đầu mean và xác suất lồng nhau. Có {len(protected)} mục checksum đã khớp, tương ứng {protected_files} tệp riêng biệt được giữ nguyên, gồm mô hình/báo cáo cũ và slide người dùng.

Không có tập kiểm định mới chưa xem cho vòng này. Năm2026 chưa đủ năm, có thay API và chưa xác nhận tính liên tục; lịch sử trạm và độ trễ chưa được xác nhận đầy đủ. Điểm khác nhau giữa hai API có thể do mùa, độ phủ hoặc nguồn, không quy hết cho mô hình. Các phép so giữ cùng 57 trạm trong train và đánh giá, nên chưa chứng minh khả năng dự báo tại trạm chưa gặp hoặc khu vực mới. Muốn kết luận khả năng mở rộng cần kiểm định giữ riêng trạm/khu vực.

Không tuyên bố vượt nghiên cứu khác khi khác dữ liệu, kỳ mưa, ngưỡng hoặc thời hạn. Không ép dùng mô hình sâu nếu chưa có bằng chứng cần thiết; Bi-LSTM tiếp tục để sau.

## Cách dùng lại dữ liệu

Gói nội bộ mới giữ một Parquet đã ghép X/y, có cột role, fit_short, fit_long, calibration_2025 và retrospective_2026. Các cờ không phải đặc trưng mô hình. Chỉ chọn X theo danh sách N0/N1/N3 ở feature_sets.json, không đưa y_mm, role hoặc số đo tương lai vào X. Giữ station_id/issue/horizon/gauge_namespace để ghép đúng và chấm cùng mẫu. Gói không chứa checkpoint, dữ liệu nguồn thô hoặc thông tin đăng nhập.

Nguồn, quyết định và số liệu đầy đủ: protocol.json, selection.json, train_only_cv.csv, cutoffs.csv, point_metrics.csv, probability_metrics.csv, event_metrics.csv, seed_metrics.csv, paired_comparisons.csv, verification.json. PHUONG_AN.md giải thích thiết kế trước fit.
'''
    # Clean compressed spacing in explanatory prose while leaving machine identifiers alone.
    summary=re.sub(r'(?<=\d)(?=[A-Za-zÀ-ỹ])',' ',summary)
    for a,b in [('artifactcũ','artifact cũ'),('đầumean','đầu mean'),('đầuphụ','đầu phụ'),('độtrễ','độ trễ'),('môhình','mô hình'),('dữliệu','dữ liệu'),('tươnglai','tương lai'),('đặctrưng','đặc trưng'),('kiểmchứng','kiểm chứng'),('và sốliệu','và số liệu'),('sốliệu','số liệu'),('đầyđủ','đầy đủ'),('trướcf','trước f')]:summary=summary.replace(a,b)
    summary=readable(summary)
    textfile(PUBLIC/'BAO_CAO_MO_RONG_TRAIN.md',summary)
    document(summary,PUBLIC/'BAO_CAO_MO_RONG_TRAIN.docx')
    # Slides use short, self-contained explanations and speaker notes with full context.
    deck=Slides()
    deck.add('Thêm năm dữ liệu hay đổi loss?',f'57 trạm • Dự báo ba lượng mưa 24 giờ riêng\nBốn cấu hình LightGBM: A/B/C/D\n{outcome}',summary[:2500])
    deck.add('Kết quả chính nên trình bày như thế nào?',
        'Thêm hai năm giúp Tweedie giảm điểm RMSE ở cả ba hạn, nhưng chưa đủ chắc chắn.\nVới L2, thêm năm có cải thiện thăm dò đạt tiêu chí ở ngày3.\nL2 không thắng Tweedie nhất quán; cần đọc cả ngày khô và mưa lớn.\nKhí tượng thô có tín hiệu ở mức điểm; địa hình thay đổi rất nhỏ.\nGiữ giới hạn: 2026 đã xem, chưa phải xác nhận bằng dữ liệu tương lai.',explanation)
    deck.add('Chúng ta dự báo chính xác điều gì?',
        'Phát lúc 19h Việt Nam mỗi ngày, cho từng trạm.\nNgày 1: 19h hôm nay → 19h ngày mai.\nNgày 2: 19h ngày mai → 19h ngày kế tiếp.\nNgày 3: tiếp tục một cửa sổ 24 giờ.\nBa lượng mưa riêng; một mô hình chung cho 57 trạm.')
    s=deck.add('Đầu vào gồm những gì?');deck.table(s,['Nhóm','Số biến','Thông tin'],feature_rows,[1.0,1.3,9.8],size=20,row_h=.85);deck.caption(s,'Xem catalogue để biết đúng tên và đơn vị. Nhãn y_mm không được nằm trong X.')
    deck.add('Dữ liệu tại trạm được ghép như thế nào?',
        'Vrain: mưa đo tại điểm, đủ 24 giờ cùng API cho mỗi nhãn.\nGFS: dự báo khí tượng; nội suy bốn nút 0,25° quanh tọa độ trạm.\nMưa quá khứ: bảy ngày + tổng 1/6/24h trước cutoff 18h.\nGFS tương lai đã được dự báo trước issue, không phải quan trắc tương lai.\nKhông lấy trung bình các trạm thành nhãn toàn vùng.')
    s=deck.add('Chia năm: đây là một phiên bản mới');deck.table(s,['Năm','Vai trò'],[
        ['2021–2022','Fit A/C; phần đầu của B/D; tuning bằng các quý2022'],['2023–2024','Thêm vào fit B/D, không còn là cal/dev ở phiên bản này'],
        ['2025','Chỉ hiệu chỉnh xác suất và cutoff; không fit cây'],['2026 hiện có','Hồi cứu đã xem; tách legacy/modern, chưa đủ năm'],['Sau khóa mới','Lưu dự báo trước sự kiện, đối chiếu nhãn đến sau']], [2.3,9.8],size=19,row_h=.67);deck.caption(s,'Giữ nguyên toàn bộ split, checkpoint và kết quả của các nghiên cứu cũ.')
    s=deck.add('Bốn cấu hình tách hai tác động');deck.table(s,['Mã','Năm fit','Loss đầu mean','Số biến'],case_rows,[.8,2.5,6.6,2.2],row_h=.7);deck.caption(s,'B−A/D−C: thêm năm. C−A/D−B: đổi loss. Các điều kiện khác giữ giống nhau.')
    deck.add('Chọn tham số công bằng trước khi chấm 2026',
        f'72 fit CV: 3 ứng viên × 2 loss × 4 quý2022 × 3 hạn.\nChỉ học quá khứ; purge đủ72h nhãn + gap7ngày.\nChọn chung cấu hình {selection["candidate"]["name"]}, {selection["candidate"]["num_leaves"]} lá.\nSố cây chung D1/D2/D3: {selection["trees"]["1"]}/{selection["trees"]["2"]}/{selection["trees"]["3"]}.\nKhông tuning bằng2025 hoặc2026; cùng ngân sách không phải tuning tối đa riêng mỗi loss.')
    deck.add('Ba seed là gì?',
        'Seed 17, 29, 43: ba trạng thái nguồn số ngẫu nhiên.\nLightGBM lấy mẫu hàng/biến khi tạo cây; đổi seed có thể cho cây khác.\nKhông phải ba bộ dữ liệu hoặc ba lần chia train/test.\nDự báo chính lấy trung bình ba lần chạy.\nKhoảng min–max theo seed cho thấy độ nhạy, không phải khoảng tin cậy.')
    deck.add('Mean và median phục vụ hai mục tiêu',
        'Mean: lượng mưa kỳ vọng, ưu tiên chấm bằng RMSE.\nMedian: trung vị, ưu tiên chấm bằng MAE; có thể gần0 khi mưa ít xảy ra.\nTweedie và L2 chỉ thay đầu mean ở phép so A–D.\nA/C chung median và xác suất; B/D cũng chung các đầu phụ.\nKhông suy ra POD tốt hơn chỉ vì đổi loss dự báo lượng mưa.')
    deck.add('Vì sao kiểm tra L2 bên cạnh Tweedie?',
        'L2 phạt bình phương sai số, gần mục tiêu RMSE của nghiên cứu.\nTweedie p=1,5 phù hợp đầu ra không âm, nhiều số0 và lượng mưa dương lệch mạnh.\nCả hai đều nhằm dự báo mean, nhưng cách cập nhật cây khác nhau.\nL2 có thể nhạy hơn với các lần sai lớn và mưa cực đoan.\nCần kiểm tra ngày khô, mưa lớn và độ ổn định; không mặc định L2 sẽ thắng.')
    for i in (0,4):
        s=deck.add('Đọc metric: '+('lượng mưa và xác suất' if i==0 else 'xác suất và cảnh báo'))
        deck.table(s,['Chỉ số','Hiểu đơn giản','Dùng để','Chiều tốt'],metrics[i:i+4],[1.0,4.7,4.9,1.5],size=18,row_h=.92)
        deck.caption(s,'H: trúng; M: bỏ sót; F: báo nhầm. Macro: mỗi trạm có trọng số như nhau.')
    s=deck.add('2026 có bao nhiêu mẫu thực sự được chấm?');deck.table(s,['API','Mẫu D1','Trạm','Issue','Mưa ≥50 D1'],count_rows,[2.5,2.4,1.7,1.7,3.8],size=20,row_h=.8);deck.caption(s,'Cùng các mẫu cho mọi mô hình. Legacy ít mưa lớn, không dùng riêng để kết luận cảnh báo.')
    s=deck.add('RMSE đầu mean: bốn cấu hình và đối chứng');deck.table(s,header,mainrows,size=21,row_h=.56);deck.caption(s,'Modern2026; mm/24h, nhỏ hơn tốt hơn. In đậm: nhỏ nhất trong bảng, chưa hàm ý ý nghĩa thống kê.')
    deck.add('Vì sao vẫn phải so với GFS và MOS?',
        'GFS: dự báo khí tượng nguyên bản, trước mọi hiệu chỉnh của nhóm.\nMOS: hiệu chỉnh đơn giản từ mưa GFS và lịch mùa, fit cùng số năm.\nLightGBM cần chứng minh giá trị ngoài một phép hiệu chỉnh đơn giản.\nLuôn0, khí hậu và lặp ngày trước là những mốc tối thiểu khác.\nBảng đầy đủ mọi đối chứng nằm trong CSV, tránh chỉ chọn đối chứng yếu.')
    s=deck.add('Bổ sung năm và đổi loss đã thay đổi bao nhiêu?');deck.table(s,['Chênh RMSE','Ngày 1','Ngày 2','Ngày 3'],differences,size=21,row_h=.7);deck.caption(s,'Âm: cấu hình đứng trước tốt hơn. B−A/D−C thêm năm; C−A/D−B đổi loss.')
    s=deck.add('Khác biệt có chắc chắn không?');s.shapes.add_picture(str(PUBLIC/'factorial_differences.png'),Inches(2.1),Inches(1.6),height=Inches(4.8));deck.caption(s,f'{supported}/12 phép đạt tiêu chí thăm dò. CI đồng thời theo họ12; không biến2026 thành test chưa dùng.',6.55)
    s=deck.add('Lặp kiểm tra nhóm biến với cửa sổ train dài');deck.table(s,header,abrows,size=21,row_h=.62);deck.caption(s,f'Loss chọn bằngCV2022: {selection["selected_loss"]}. N3 là bí danh{selected}; {supported_a}/6 phép đạt tiêu chí thăm dò.')
    s=deck.add('MAE đầu median: cùng mẫu, mục tiêu khác');deck.table(s,header,medianrows,size=21,row_h=.56);deck.caption(s,'mm/24h; nhỏ hơn tốt hơn. A đại diệnA/C, B đại diệnB/D vì chung đầu phụ.')
    s=deck.add('BSS mưa ≥50: xác suất có hơn khí hậu không?');deck.table(s,header,probability_rows,size=21,row_h=.56);deck.caption(s,'Lớn hơn tốt hơn. BSS=0 ngang khí hậu; âm kém khí hậu. Tham chiếu chung fit2021–2024.')
    for h in (1,2,3):
        s=deck.add(f'Cảnh báo mưa ≥50 mm/24h: ngày {h}');deck.table(s,['Mô hình','Cutoff','POD ↑','FAR ↓','CSI ↑'],warning_rows[h],[4.1,1.4,2.2,2.2,2.2],size=20,row_h=.56)
        deck.caption(s,'Cutoff chọn bằng2025; GFS là quyết định từ lượng mưa. POD phải đọc cùng FAR/CSI; không có mốc tốt chung.')
    s=deck.add('Đổi loss có đánh đổi ngày khô với mưa lớn?');deck.table(s,['Mã','Bias ngày khô','Bias ≥50','% SSE từ≥50'],tail_rows,[1.0,3.4,3.4,4.3],size=21,row_h=.7);deck.caption(s,'Modern2026, ngày1; Bias âm là dự báo thiếu. Không loại nhãn vì mưa lớn hoặc sai số cao.')
    s=deck.add('Kết quả giữa ba seed có ổn định không?');deck.table(s,header,seedrows,size=20,row_h=.7);deck.caption(s,'Khoảng RMSE của từng seed; điểm chính dùng ensemble ba seed. Khoảng này không phải CI.')
    deck.add('Mô hình nào được ghi dự báo tương lai?',
        f'Lựa chọn định trước: {selected}, train2021–2024, loss {selection["selected_loss"]}.\nLoss chọn chỉ từCV2022, không chọn lại theo điểm2026.\nGhi thêm cả A–D để giữ phép so có kiểm soát.\nLưu thời điểm nhận dữ liệu và dự báo trước19h; thiếu thì không phát.\nNhận nhãn sau72h + độ trễ; một issue chưa đủ chứng minh skill.')
    deck.add('Đã kiểm chứng gì, còn thiếu gì?',
        f'{tests["tests"]} tests đạt; {verify["evaluation_rows"]:,} hàng đánh giá được đối chiếu.\n{verify["independent_metric_values"]:,} giá trị metric kiểm tra độc lập; replay checkpoint và bootstrap theo ngày.\nGiữ {protected_files} tệp cũ cùng slide người dùng; không sửa nhãn theo lỗi mô hình.\nCòn thiếu: kiểm định tương lai dài hơn, xác nhận độ trễ/cảm biến/API.\nKhông tuyên bố thắng nghiên cứu khác từ các bảng khác dữ liệu/ngưỡng.')
    deck.p.save(PUBLIC/'PBL6_MO_RONG_NAM_TRAIN_VA_LOSS.pptx')
    # One shareable dataset, with explicit version-specific role flags.
    f=load_frame();f['fit_short']=f.role.eq('fit2021_22');f['fit_long']=f.role.isin(['fit2021_22','fit2023','fit2024'])
    f['calibration_2025']=f.role.eq('calibration2025');f['retrospective_2026']=f.role.eq('retrospective2026')
    dataset=BASE/'PBL6_NGAN_HAN_57_TRAM_2021_2026.parquet';save_parquet(f,dataset)
    feature_sets={c:FEATURES[c] for c in ('N0','N1','N3')};write_json(PUBLIC/'feature_sets.json',feature_sets)
    guide='''# Gửi nhóm một gói, dùng một Parquet

Mở PBL6_NGAN_HAN_57_TRAM_2021_2026.parquet. Một hàng = một trạm × issue × horizon; nhãn y_mm là tổng mưa 24h của chính trạm. Mỗi mẫu đủ ba hàng horizon 1/2/3. Có 57 trạm; một mô hình chung dự báo cho nhiều trạm.

Phiên bản mới: fit_short chọn 2021–22; fit_long chọn 2021–24; calibration_2025 chỉ Platt/cutoff; retrospective_2026 đã xem, không dùng chọn tham số rồi gọi test mới. Cột split giữ tên vai trò của nguồn cũ để truy vết; ưu tiên role/các cờ mới khi tái hiện phiên bản này. Không trộn toàn bộ file để train.

Lấy đúng danh sách X từ feature_sets.json: N0=16, N1=21, N3=26. Không dùng mọi cột còn lại làm X; loại y_mm, role, split và các cờ chia năm khỏi X. station_code là biến phân loại trong LightGBM. Giữ station_id/issue_utc/horizon/gauge_namespace để ghép và chấm; không nối hai API trong một cửa sổ.

Ví dụ: d=df[df.fit_long & df.horizon.eq(1)]; X=d[feature_sets['N3']]; y=d.y_mm. Nhãn quan trắc có thể thiếu ở kho nguồn nhưng tất cả hàng bàn giao ở đây đã qua mask chung và đủ X/y. Điều đó không chứng nhận cảm biến hoặc nguồn đã sẵn tại thời điểm phát dự báo.

Gói gồm dataset, báo cáo Word, catalogue, protocol, feature_sets, hướng dẫn và SHA. Không chứa dữ liệu thô, checkpoint hoặc thông tin đăng nhập. Đọc báo cáo để hiểu bốn cấu hình và giới hạn của đánh giá hồi cứu 2026. Nhánh Bi-LSTM theo giờ dùng bộ riêng.
'''
    bundle=BASE/'PBL6_NGAN_HAN_TRAIN_MOI.zip'
    with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_STORED) as archive:
        archive.write(dataset,dataset.name)
        for name in ['BAO_CAO_MO_RONG_TRAIN.docx','feature_catalog.csv','feature_sets.json','protocol.json']:archive.write(PUBLIC/name,name)
        archive.writestr('HUONG_DAN.md',guide);archive.writestr('SHA256.txt',sha(dataset)+'  '+dataset.name+'\n')
    with zipfile.ZipFile(bundle) as archive:
        if archive.testzip() is not None:raise ValueError('Handoff archive CRC failed')
    readback=pd.read_parquet(dataset)
    if len(readback)!=323466 or len(readback.columns)!=len(f.columns):raise ValueError('Handoff roundtrip failed')
    textfile(PUBLIC/'KET_LUAN.md','# Kết quả vòng mới\n\n'+outcome+'\n\n'+explanation+'\n\n'+table_md(header,mainrows)+
        '\n\nA/C: train 2021–22; B/D: train 2021–24. A/B Tweedie; C/D L2. Cùng 26 biến, 57 trạm, ngân sách và ba seed.\n\n'+
        f'Lựa chọn để ghi dự báo tương lai: {selected}, theo CV 2022 và cửa sổ dài định trước. Năm 2025 chỉ hiệu chỉnh xác suất/cutoff, không fit cây. Năm 2026 là hồi cứu đã xem, không phải test mới.\n\n'+
        'Đọc báo cáo Word/Markdown, slide và CSV đầy đủ. Không loại nhãn theo sai số. Kiểm chứng tương lai cần máy còn hoạt động và chờ nhãn sau 72h. Bi-LSTM tiếp tục để sau.')
    textfile(PUBLIC/'README.md','''# Vòng mới về số năm huấn luyện và hàm mất mát

- [Kết luận và bảng chính](KET_LUAN.md).
- [Báo cáo đầy đủ](BAO_CAO_MO_RONG_TRAIN.docx), [bản Markdown](BAO_CAO_MO_RONG_TRAIN.md).
- [Slide có thể chỉnh sửa](PBL6_MO_RONG_NAM_TRAIN_VA_LOSS.pptx).
- [Thiết kế trước fit](PHUONG_AN.md), [protocol](protocol.json), [kiểm chứng](verification.json).
- Các CSV báo đầy đủ hai API, ba hạn, lượng mưa/xác suất/cảnh báo/seed/CI.

Năm 2025 được hiệu chỉnh theo phê duyệt mới, không fit cây; năm 2026 đã xem, chỉ hồi cứu. Phiên bản cũ giữ nguyên. Chọn mô hình để ghi dự báo tương lai bằng CV 2022, không chọn bằng điểm 2026.

Gói nội bộ gửi nhóm: data/operational/gfs_training_window_2026_11_18/PBL6_NGAN_HAN_TRAIN_MOI.zip, chỉ một Parquet và các tệp mô tả; không đưa gói, dữ liệu hoặc checkpoint lên Git. Tiến trình theo dõi ghi một issue tương lai, cần máy và mạng còn hoạt động; kiểm chứng nhãn sau 72h cộng độ trễ, không có kết quả thực tế ngay.
''')
    doc=Document(PUBLIC/'BAO_CAO_MO_RONG_TRAIN.docx')
    release=dict(status='complete',published_utc=now(),slides=len(deck.p.slides),word_paragraphs=len(doc.paragraphs),word_tables=len(doc.tables),
        verification_sha256=sha(PUBLIC/'verification.json'),training_lock_sha256=sha(BASE/'training_lock.json'),
        report_files={p.name:sha(p) for p in PUBLIC.iterdir() if p.is_file() and p.name!='release.json'},
        code={rel:sha(ROOT/rel) for rel in ['scripts/publish_gfs_window.py']},
        private_handoff=dict(path=str(bundle.relative_to(ROOT)).replace('\\','/'),sha256=sha(bundle),bytes=bundle.stat().st_size,
            files=7,dataset_rows=len(f),dataset_columns=len(f.columns),dataset_sha256=sha(dataset)))
    write_json(PUBLIC/'release.json',release)
    print(dict(published=True,slides=len(deck.p.slides),tables=len(doc.tables),bundle_MB=round(bundle.stat().st_size/1e6,2)),flush=True)


if __name__=='__main__':main()
