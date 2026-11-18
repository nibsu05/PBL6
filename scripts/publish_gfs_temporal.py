"""Readable research report, slides and an aggregate-only release manifest."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from datetime import datetime,timezone
import json
import re
import subprocess
import zipfile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Inches as DocInches,Pt as DocPt
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from PIL import Image
from src.gfs_temporal import BASE,PUBLIC,CATALOG,sha,write_json
from scripts.score_gfs_temporal import assert_freeze,MODELS
from src.gfs_station_dataset import macro_metrics

def textfile(path,text):
    with Path(path).open('w',encoding='utf-8',newline='\n') as f:f.write(text.rstrip()+'\n')

def number(x):return '—' if pd.isna(x) else f'{float(x):.3f}'.replace('.',',')

def readable(value):
    value=re.sub(r'(?<=\d)(?=[a-zA-ZÀ-ỹ])',' ',str(value))
    value=re.sub(r'([a-zà-ỹ])(?=\d)',r'\1 ',value)
    value=re.sub(r'\s*([≥≤])\s*',r' \1 ',value)
    for a,b in [('mưaGFS','mưa GFS'),('nhãn09','nhãn 09'),('sốtham','số tham'),('trạm/ngày','trạm/ngày')]:value=value.replace(a,b)
    return value

def markdown_table(frame,columns,labels=None,bold_min=(),bold_max=()):
    labels=labels or columns
    lines=['| '+' | '.join(labels)+' |','| '+' | '.join('---' for _ in labels)+' |']
    minima={c:frame[c].min() for c in bold_min}
    minima.update({c:frame[c].max() for c in bold_max})
    for _,row in frame.iterrows():
        values=[]
        for c in columns:
            x=row[c];value=number(x) if isinstance(x,(float,np.floating)) else str(x)
            if c in minima and np.isclose(x,minima[c]):value='**'+value+'**'
            values.append(value)
        lines.append('| '+' | '.join(values)+' |')
    return '\n'.join(lines)

def point_table(points,scope,functional):
    metric='macro_rmse' if functional=='mean' else 'macro_mae'
    t=points[points.evaluation_set.eq(scope)&points.functional.eq(functional)].pivot(index='model',columns='horizon',values=metric).reindex(MODELS)
    t.columns=[f'D{h}' for h in t.columns];return t.reset_index()

def feature_catalog():
    raw=dict(gfs_t850_c=('°C','Nhiệt độ850hPa'),gfs_rh850_pct=('%','Độ ẩm tương đối850hPa'),
        gfs_u850=('m/s','Gió850hPa hướng Đông'),gfs_v850=('m/s','Gió850hPa hướng Bắc'),
        gfs_pwat=('kg/m²','Hơi nước toàn cột'))
    fixed=dict(gfs_rain_mm=('Mưa GFS','mm/24h','Tổng mưa dự báo đúng cửa sổ đích'),
        sin_doy=('Lịch','1','Sin chu kỳ ngày trong năm'),cos_doy=('Lịch','1','Cos chu kỳ ngày trong năm'),
        latitude=('Vị trí/ID','độ','Vĩ độ trạm'),longitude=('Vị trí/ID','độ','Kinh độ trạm'),
        station_code=('Vị trí/ID','mã phân loại','ID cho mô hình chung, không là phép đo khí tượng'),
        dem_elev_m=('Địa hình','m','Cao độ DEM tại tọa độ, không phải đo cao độ cảm biến'),
        dem_mean_5km_m=('Địa hình','m','Cao độ DEM trung bình trong5km'),
        dem_std_5km_m=('Địa hình','m','Độ lệch chuẩn cao độ DEM trong5km'),
        dem_slope_east=('Địa hình','m/m','Gradient DEM về Đông'),dem_slope_north=('Địa hình','m/m','Gradient DEM về Bắc'),
        gfs_rain6h_max_mm=('Diễn biến mưa','mm/6h','Tổng6h lớn nhất trong bốn khoảng'),
        gfs_rain6h_max_fraction=('Diễn biến mưa','1','Tỷ trọng của khoảng6h có mưa lớn nhất'),
        gfs_rain_centroid=('Diễn biến mưa','1','Trọng tâm thời gian với tâm khoảng0,125/0,375/0,625/0,875'),
        gfs_rain_first_half_fraction=('Diễn biến mưa','1','Tỷ trọng mưa trong12h đầu cửa sổ đích'))
    for k in range(1,8):fixed[f'rain_lag_day{k}_mm']=('Mưa quá khứ','mm/24h',f'Ngày mưa19–19h thứ{k} trước ngày issue')
    for k in (1,6,24):fixed[f'rain_recent{k}h_mm']=('Mưa quá khứ',f'mm/{k}h',f'Tổng{k}h kết thúc trước issue1h')
    for k in range(1,5):fixed[f'gfs_rain6h_{k}_mm']=('Diễn biến mưa','mm/6h',f'Mưa dự báo từ{(k-1)*6}đến{k*6}h trong cửa sổ đích')
    for name,(unit,description) in raw.items():
        fixed[name]=('Khí tượng giữa ngày',unit,description+' tại giữa cửa sổ đích')
        for suffix,explain in [('sample_mean','Trung bình ba mẫu +6/+12/+18h'),('sample_range','Max−min của ba mẫu'),('late_minus_early','Mẫu +18h trừ mẫu +6h')]:
            u='điểm phần trăm' if name=='gfs_rh850_pct' and suffix!='sample_mean' else unit
            fixed[name+'_'+suffix]=('Diễn biến khí tượng',u,description+': '+explain)
    rows=[dict(feature=name,group=fixed[name][0],unit=fixed[name][1],meaning=readable(fixed[name][2])) for name in CATALOG['T3']]
    pd.DataFrame(rows).to_csv(PUBLIC/'feature_catalog.csv',index=False,lineterminator='\n')

def previous_reference():
    """Match the old GRU_N5 predictions to the exact new evaluation rows."""
    keys=['issue_utc','station_id','horizon','gauge_namespace']
    current=pd.read_parquet(BASE/'evaluation_predictions_private.parquet',columns=keys+['y_mm','evaluation_set'])
    folder=ROOT/'data/operational/gfs_station_final_2026_11_17'
    columns=['issue_utc','station_id','horizon','y_mm','GRU_N5_mean','GRU_N5_median']
    dev=pd.read_parquet(folder/'development_predictions_private.parquet',columns=columns,filters=[('split','==','dev')]);dev['gauge_namespace']='legacy'
    other=pd.read_parquet(folder/'holdout_predictions_private.parquet',columns=columns+['gauge_namespace'])
    old=pd.concat([dev,other],ignore_index=True)
    matched=current.merge(old,on=keys,suffixes=('','_old'),validate='one_to_one',how='left')
    np.testing.assert_allclose(matched.y_mm,matched.y_mm_old,atol=1e-6,rtol=0)
    if matched[['GRU_N5_mean','GRU_N5_median']].isna().any().any():raise ValueError('Old reference missing on new common rows')
    rows=[]
    for (scope,h),sub in matched.groupby(['evaluation_set','horizon']):
        for functional in ('mean','median'):
            score,_=macro_metrics(pd.DataFrame(dict(station_id=sub.station_id,y=sub.y_mm,pred=sub['GRU_N5_'+functional])))
            rows.append(dict(evaluation_set=scope,horizon=int(h),model='GRU_N5_previous',functional=functional,**score))
    result=pd.DataFrame(rows);result.to_csv(PUBLIC/'previous_model_reference.csv',index=False,lineterminator='\n');return result

def handoff_bundle():
    filename='PBL6_NGAN_HAN_GFS_VRAIN_2021_2026.parquet'
    guide='''# Một bộ dữ liệu cho nghiên cứu ngắn hạn tại trạm

Mở file Parquet trong gói. Một hàng là một trạm × một issue × một hạn; mỗi mẫu hoàn chỉnh có ba hàng horizon=1/2/3. Nhãn y_mm là tổng24giờ Vrain tại chính trạm, ba cửa sổ liên tiếp từ19h Việt Nam. Có57trạm trong cohort cố định; không phải đã huấn luyện đủ86vị trí danh mục.

Danh sách chính xác X ở protocol.json → features → T0/T1/T2/T3; xem feature_catalog.csv để hiểu từng biến và đơn vị. T0/T1/T2/T3 có26/34/41/49biến. File có thêm cột nguồn/kiểmtra và các biến cũ để truy vết; không đưa tất cả cột còn lại vào X. Không dùng y_mm hoặc số đo tương lai làm đặc trưng.

Giữ split: train2021–22; cal2023; dev2024. reserved2025 và external2026 là dữ liệu đã được đánh giá ở vòng trước, không phải test mới chưa dùng; không trộn toàn bộ file để train. Hai API chưa được xác nhận liên tục, giữ gauge_namespace khi kiểm tra. Ba hàng của một mẫu phải cùng trạm, issue và API.

Ví dụ lấy dữ liệu LightGBM ngày1:

```python
import json
import pandas as pd
df = pd.read_parquet("PBL6_NGAN_HAN_GFS_VRAIN_2021_2026.parquet")
features = json.load(open("protocol.json", encoding="utf-8"))["features"]["T3"]
train = df[(df["split"] == "train") & (df["horizon"] == 1)]
X_train, y_train = train[features], train["y_mm"]
```

Horizon2/3 làm tương tự. GRU hiện tại dùng bảy ngày mưa quá khứ và ba context dự báo; xem mã nghiên cứu để dựng đúng pack, không cắt chuỗi từ những hàng đã trộn thời gian/trạm. Fit mọi scaler trên train; hiệu chỉnh xác suất/chọn ngưỡng chỉ trên cal. Chấm cùng mẫu, từng trạm/hạn và trung bình giữa trạm.

Đây là dữ liệu đã ghép X/y để huấn luyện lại. Gói không chứa checkpoint, toàn bộ raw cache hoặc thông tin đăng nhập; các tệp đó không cần cho một thành viên bắt đầu từ Parquet. Muốn tái hiện toàn bộ kiểm chứng nguồn và đối chứng cũ, dùng các kho nguồn/manifest của dự án. Nhánh Bi-LSTM theo giờ là bộ khác.
'''
    guide=readable(guide)
    path=BASE/'PBL6_NGAN_HAN_GFS_VRAIN_2021_2026.zip'
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_STORED) as archive:
        archive.write(BASE/'dataset_private.parquet',filename)
        for name in ('BAO_CAO_CAI_TIEN_NGAN_HAN.docx','feature_catalog.csv','protocol.json'):archive.write(PUBLIC/name,name)
        archive.writestr('HUONG_DAN_NGAN.md',guide)
        archive.writestr('SHA256.txt',sha(BASE/'dataset_private.parquet')+'  '+filename+'\n')
    return dict(path=str(path.relative_to(ROOT)),sha256=sha(path),bytes=path.stat().st_size,files=6,
                dataset_sha256=sha(BASE/'dataset_private.parquet'))

def plots(points,pairs,tail):
    plt.rcParams.update({'font.size':14})
    selected=['GFS','MOS','LGB_T0','LGB_T1','LGB_T2','LGB_T3','GRU_T0','GRU_T3','GRU_LINEAR23']
    fig,ax=plt.subplots(figsize=(10,6.5));positions=np.arange(len(selected))
    for h,color in [(1,'#147a82'),(2,'#536aa0'),(3,'#ad7444')]:
        t=points[points.evaluation_set.eq('retrospective2025_legacy')&points.functional.eq('mean')&points.horizon.eq(h)].set_index('model').reindex(selected)
        ax.barh(positions+(h-2)*.24,t.macro_rmse.to_numpy(),height=.23,color=color,label=f'Ngày {h}')
    ax.set_yticks(positions,selected);ax.invert_yaxis();ax.legend();ax.set_xlabel('RMSE (mm/24h), nhỏ hơn tốt hơn');ax.grid(axis='x',alpha=.2)
    ax.set_title('Hồi cứu 2025 — cùng mẫu, dữ liệu đã được xem',fontsize=15)
    fig.tight_layout();fig.savefig(PUBLIC/'rmse_2025.png',dpi=175);plt.close(fig)
    q=pairs[pairs.evaluation_set.eq('retrospective2025_legacy')&pairs.primary].copy()
    labels=[f'{r.model} − {r.reference} | D{r.horizon}' for r in q.itertuples()]
    fig,ax=plt.subplots(figsize=(10,8));pos=np.arange(len(q))
    ax.hlines(pos,q.simultaneous_ci_low,q.simultaneous_ci_high,color='#147a82')
    ax.scatter(q.difference,pos,color='#147a82',s=30)
    ax.axvline(0,color='#b14545',lw=1);ax.set_yticks(pos,labels);ax.invert_yaxis();ax.set_xlabel('Chênh lệch RMSE (mm); âm nghiêng về mô hình thêm biến')
    ax.set_title('2025 đã xem: so sánh thăm dò, CI đồng thời cho 12 phép so');ax.grid(axis='x',alpha=.2)
    fig.tight_layout();fig.savefig(PUBLIC/'feature_intervals_2025.png',dpi=175);plt.close(fig)
    q=tail[tail.evaluation_set.eq('retrospective2025_legacy')&tail.functional.eq('mean')&tail.observed_bin.eq('ge50')&tail.model.isin(['LGB_T0','LGB_T3','GRU_T0','GRU_T3'])]
    fig,ax=plt.subplots(figsize=(9,4.5))
    for model,g in q.groupby('model'):ax.plot(g.horizon,100*g.fraction_squared_error,marker='o',label=model)
    ax.set_xticks([1,2,3],['Ngày 1','Ngày 2','Ngày 3']);ax.set_ylabel('% tổng bình phương sai số');ax.set_ylim(0,100);ax.legend();ax.grid(alpha=.2)
    ax.set_title('Bao nhiêu sai số lượng mưa đến từ các mẫu thực đo ≥50 mm?')
    fig.tight_layout();fig.savefig(PUBLIC/'tail_error_share.png',dpi=175);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.6));x=np.arange(4)
    ax.bar(x-.18,[0,0,80,0],width=.35,label='Mưa dồn: tổng 80 mm',color='#147a82')
    ax.bar(x+.18,[20,20,20,20],width=.35,label='Mưa đều: tổng 80 mm',color='#ad7444')
    ax.set_xticks(x,['0–6h','6–12h','12–18h','18–24h']);ax.set_ylabel('Lượng mưa GFS giả định (mm)');ax.legend(fontsize=12)
    ax.set_title('Ví dụ minh họa — cùng tổng ngày, khác diễn biến');ax.grid(axis='y',alpha=.2)
    fig.tight_layout();fig.savefig(PUBLIC/'temporal_example_illustrative.png',dpi=175);plt.close(fig)

def docx_from_markdown(text):
    doc=Document();section=doc.sections[0];section.top_margin=DocInches(.65);section.bottom_margin=DocInches(.65)
    style=doc.styles['Normal'];style.font.name='Calibri';style.font.size=DocPt(10)
    def runs(paragraph,value):
        for i,part in enumerate(re.split(r'\*\*(.*?)\*\*',value)):
            run=paragraph.add_run(part);run.bold=i%2==1
    lines=text.splitlines();i=0
    while i<len(lines):
        line=lines[i]
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                row=[x.strip() for x in lines[i].strip('|').split('|')]
                if not all(re.fullmatch('[: -]+',x) for x in row):rows.append(row)
                i+=1
            table=doc.add_table(rows=0,cols=len(rows[0]));table.style='Light Shading Accent 1'
            for j,row in enumerate(rows):
                cells=table.add_row().cells
                for cell,value in zip(cells,row):runs(cell.paragraphs[0],value)
                if j==0:
                    for cell in cells:
                        for run in cell.paragraphs[0].runs:run.bold=True
            continue
        if line.startswith('!['):
            name=re.search(r'\]\((.*?)\)',line).group(1);doc.add_picture(str(PUBLIC/name),width=DocInches(6.35))
        elif line.startswith('#'):
            level=min(len(line)-len(line.lstrip('#')),3);doc.add_heading(line.lstrip('# ').strip(),level=level-1)
        elif line.strip():runs(doc.add_paragraph(),line)
        i+=1
    doc.save(PUBLIC/'BAO_CAO_CAI_TIEN_NGAN_HAN.docx')

def slides(points,counts,pairs,events,summary,seed_variation=None,reference_context=None,bss_table=None,decision_table=None):
    prs=Presentation();prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
    def slide(title,body=None,table=None,notes='',picture=None,higher_is_better=False,caption=None):
        s=prs.slides.add_slide(prs.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=RGBColor(246,248,251)
        box=s.shapes.add_textbox(Inches(.55),Inches(.35),Inches(12.2),Inches(.8));tf=box.text_frame;tf.word_wrap=True
        r=tf.paragraphs[0].add_run();r.text=readable(title);r.font.size=Pt(29);r.font.bold=True;r.font.color.rgb=RGBColor(21,49,76)
        if body:
            box=s.shapes.add_textbox(Inches(.65),Inches(1.4),Inches(12.1),Inches(5.4));tf=box.text_frame;tf.word_wrap=True
            for j,line in enumerate(body):
                p=tf.paragraphs[0] if j==0 else tf.add_paragraph();p.text=readable(line);p.font.size=Pt(22);p.space_after=Pt(16)
        if table is not None:
            rows,cols=table.shape;shape=s.shapes.add_table(rows+1,cols,Inches(.55),Inches(1.45),Inches(12.2),Inches(min(5.2,max(3,.6*(rows+1)))))
            t=shape.table
            if cols==3 and table.columns[-1]=='Nội dung':widths=[1.35,1.2,9.65]
            elif cols==3 and table.columns[0]=='Chỉ số':widths=[2.6,7.6,2.0]
            elif cols==2:widths=[3.2,9.0]
            elif cols==4:widths=[3.8,2.8,2.8,2.8]
            elif cols==5:widths=[4.2,2.,2.,2.,2.]
            else:widths=[12.2/cols]*cols
            for column,width in zip(t.columns,widths):column.width=Inches(width)
            for j,c in enumerate(table.columns):t.cell(0,j).text=readable(c)
            for i,(_,row) in enumerate(table.iterrows(),1):
                for j,value in enumerate(row):t.cell(i,j).text=number(value) if isinstance(value,(float,np.floating)) else readable(value)
            for i in range(rows+1):
                for j in range(cols):
                    cell=t.cell(i,j);cell.margin_left=Inches(.06);cell.margin_right=Inches(.05)
                    for p in cell.text_frame.paragraphs:
                        p.font.size=Pt(17 if rows>8 else 20);p.font.bold=i==0
                    if i==0:
                        cell.fill.solid();cell.fill.fore_color.rgb=RGBColor(21,49,76)
                        for p in cell.text_frame.paragraphs:p.font.color.rgb=RGBColor(255,255,255)
            for j,c in enumerate(table.columns):
                if (c.startswith('D') or c in ('POD','FAR','CSI')) and pd.api.types.is_numeric_dtype(table[c]):
                    minimum=table[c].max() if c in ('POD','CSI') or higher_is_better else table[c].min()
                    for i,value in enumerate(table[c],1):
                        if np.isclose(value,minimum):
                            for p in t.cell(i,j).text_frame.paragraphs:p.font.bold=True
        if picture:
            with Image.open(PUBLIC/picture) as im:ratio=im.width/im.height
            width=min(11.8,5.6*ratio);height=width/ratio
            s.shapes.add_picture(str(PUBLIC/picture),Inches((13.333-width)/2),Inches(1.25+(5.6-height)/2),width=Inches(width))
        if caption:
            box=s.shapes.add_textbox(Inches(.7),Inches(5.1 if table is not None else 6.7),Inches(12),Inches(.8 if table is not None else .35))
            box.text_frame.word_wrap=True
            paragraph=box.text_frame.paragraphs[0];paragraph.text=readable(caption);paragraph.font.size=Pt(19 if table is not None else 14)
        footer=s.shapes.add_textbox(Inches(.6),Inches(7.08),Inches(12),Inches(.25));footer.text_frame.margin_top=0;footer.text_frame.margin_bottom=0
        footer.text_frame.paragraphs[0].text=f'PBL6 | Nghiên cứu tại trạm | Cập nhật 18/11/2026 | {len(prs.slides)}';footer.text_frame.paragraphs[0].font.size=Pt(11)
        s.notes_slide.notes_text_frame.text=readable(notes or '\n'.join(body or []))
    slide('Cải tiến dự báo mưa 1–3 ngày tại trạm',body=['57 trạm • một mô hình chung • phát dự báo hằng ngày lúc 19h Việt Nam',
        'Bổ sung diễn biến GFS bên trong mỗi ngày; giữ nguyên nhãn mưa đo Vrain.',
        '2025–2026: đánh giá hồi cứu vì kết quả đã được xem trước.'])
    slide('Dự đoán chính xác điều gì?',table=pd.DataFrame([
        ['Ngày 1','0–24h','19h hôm nay → 19h ngày mai'],['Ngày 2','24–48h','19h ngày mai → 19h ngày kia'],['Ngày 3','48–72h','Cửa sổ 24h thứ ba']],columns=['Nhãn','Tính từ issue','Khoảng lấy tổng mưa']),
        notes='Ba tổng riêng, không phải tổng tích lũy 24/48/72h. Nhãn tại chính trạm. 10:00 là mưa09:00–10:00 giờ Việt Nam do người dùng xác nhận.')
    slide('Một mẫu và những thông tin được phép dùng',body=['Một mẫu = một trạm × một ngày phát dự báo; có ba nhãn ngày1/2/3.',
        'Bảy ngày mưa quá khứ + tổng gần nhất 1/6/24h, với giả định trễ trạm 1h.',
        'GFS dự báo tương lai từ cycle00UTC trước issue; không đưa mưa thực đo tương lai vào đầu vào.',
        'GFS trích từ bốn nút0,25° quanh trạm. Nội suy không tạo độ phân giải đo tại trạm.'])
    slide('Vì sao cần thử diễn biến trong ngày?',body=['Cùng tổng80mm: mưa dồn trong6h khác mưa rải đều24h.',
        'Một trạng thái khí tượng giữa ngày có thể bỏ qua độ ẩm tăng hoặc gió đổi hướng.',
        'Giả thuyết: diễn biến có thể giúp hiệu chỉnh mưa GFS tại trạm. Cần đo, chưa mặc định tốt hơn.'])
    slide('Bốn cấu hình dữ liệu: T0–T3',table=pd.DataFrame([
        ['T0',26,'N3 cũ: mưaGFS, lịch/vị trí, mưa quá khứ, khí tượng giữa ngày, DEM'],
        ['T1',34,'T0 + 8 biến phân bố mưa6h'],['T2',41,'T0 + 15 biến diễn biến khí tượng'],['T3',49,'T0 + cả hai nhóm']],columns=['Cấu hình','Số biến','Nội dung']),
        notes='Nhóm khí tượng T/RH/u/v850 và PWAT. DEM có cao độ, mean/std5km, hai gradient dốc. Trạm, lịch và lịch sử mưa giữ nguyên giữa các cấu hình.')
    slide('T0 có 26 biến nền như thế nào?',table=pd.DataFrame([
        ['Mưa GFS',1,'Tổng mưa dự báo 24h trong cửa sổ đích'],['Lịch',2,'sin/cos của ngày trong năm'],
        ['Vị trí / ID',3,'Vĩ độ, kinh độ, mã trạm'],['Mưa quá khứ',10,'Bảy ngày trước + tổng gần nhất1/6/24h'],
        ['Khí tượng',5,'T/RH/u/v850 và PWAT, một trạng thái giữa ngày'],['DEM',5,'Cao độ; mean/std5km; hai thành phần độ dốc']],columns=['Nhóm','Số biến','Nội dung']))
    slide('8 biến mưa6h là gì?',body=['Bốn lượng mưa GFS6h trong ngày đích: 0–6,6–12,12–18,18–24h.',
        'Bốn tóm tắt: lượng6h lớn nhất; tỷ trọng lớn nhất; trọng tâm theo thời gian; tỷ trọng nửa đầu.',
        'Lấy hiệu tích lũy GFS cùngcycle. Đây là dự báo, không nội suy nhãn mưa trạm.'])
    slide('Ví dụ giả định: cùng80mm nhưng khác thông tin',picture='temporal_example_illustrative.png',
        notes='Chỉ là số giả định để giải thích đặc trưng, không phải số đo hoặc kết quả mô hình. Bốn khoảng6h là một lựa chọn thiết kế gọn, chưa khẳng định tối ưu hơn3h/1h. Nhãn đầu ra vẫn là tổng24giờ Vrain thực đo.')
    slide('15 biến khí tượng là gì?',body=['T/RH/u/v850 và PWAT: năm trường khí tượng.',
        'Mỗi trường có ba trạng thái dự báo ở +6,+12,+18h trong cửa sổ đích.',
        'Tính trung bình ba mẫu, biên độ và chênh lệch cuối–đầu: 5×3=15.',
        'Trung bình ba trạng thái tức thời không phải trung bình toàn ngày.'])
    slide('So sánh thế nào để công bằng?',body=['LightGBM: đủ T0,T1,T2,T3 trên cùng mẫu và ngân sách cây.',
        'GRU: T0,T3 và LINEAR23; giữ hidden16,head24,17epoch.',
        'LINEAR23 chỉ thêm tổ hợp tuyến tính từ T0, có cùng số tham số với T3.',
        'Mọi mô hình giữ ba seed17/29/43; không coi ba seed là ba bộ dữ liệu độc lập.'])
    slide('Đầu vào T3 và đầu ra của mô hình',body=['LightGBM: bảng [số mẫu của một hạn,49biến]; học riêng ngày1/2/3.',
        'GRU: mưa quá khứ [số mẫu,7ngày,1] + context [số mẫu,3ngày,41] + ID trạm.',
        '41=49trừ bảy biến mưa đã đưa qua nhánh chuỗi và một ID đã đưa qua embedding.',
        'Đầu ra: ba mean,ba median,ba P(mưa≥1mm),ba P(mưa≥50mm). Nhãn vẫn là ba tổng24h tại trạm.'])
    slide('Chia năm và vai trò thật của dữ liệu',table=pd.DataFrame([
        ['2021–2022','Fit mô hình, scaler và projection'],['2023','Hiệu chỉnh xác suất, chọn cutoff qua cross-fit'],
        ['2024','Phát triển đã được phân tích'],['2025','Hồi cứu, đã chấm ở vòng trước'],['2026 hiện có','Hồi cứu, tách API, chưa đủ năm']],columns=['Thời gian','Vai trò']),
        notes='Không fit/tuning bằng nhãn2025/2026. Nhưng đã xem kết quả các năm này nên không được gọi là kiểm định độc lập mới. Cần dữ liệu sau thời điểm đóng băng tương lai để xác nhận tiếp.')
    slide('Số mẫu thực tế sau khi ghép đủ',table=counts.rename(columns={'evaluation_set':'Giai đoạn','gauge_namespace':'API','packs':'Mẫu','stations':'Trạm','issues':'Ngày issue'}))
    slide('Hai đầu lượng mưa: mean và median',body=['Đầu mean ước lượng lượng mưa trung bình có điều kiện; chấm chính bằng RMSE.',
        'Đầu median ước lượng trung vị có điều kiện; chấm chính bằng MAE.',
        'Hai đầu phục vụ hai mục tiêu khác nhau; không chọn đầu thuận lợi sau khi nhìn điểm.'])
    slide('Metrics lượng mưa',table=pd.DataFrame([
        ['RMSE','Phạt mạnh dự báo sai lượng lớn','Nhỏ hơn'],['MAE','Sai tuyệt đối trung bình, đơn vịmm','Nhỏ hơn'],['Bias','Dự báo thừa hay thiếu trung bình','Gần0']],columns=['Chỉ số','Ý nghĩa','Chiều tốt']))
    slide('Metrics xác suất và phát hiện mưa',table=pd.DataFrame([
        ['BS / BSS','Sai xác suất / hơn khí hậu tham chiếu','BS↓; BSS↑'],['POD=H/(H+M)','Bắt được bao nhiêu sự kiện thực tế','↑, đọc cùngFAR'],
        ['FAR=F/(H+F)','Bao nhiêu lần báo có bị nhầm','↓'],['CSI=H/(H+M+F)','Cân nhắc đúng, bỏ sót, báo nhầm','↑']],columns=['Chỉ số','Ý nghĩa','Chiều tốt']),
        notes='H báo đúng, M bỏ sót, F báo nhầm. Ngưỡng1/50mm24h là ngưỡng phân tích nghiên cứu. BSS<0 nghĩa xác suất còn kém khí hậu tham chiếu. Không có POD0,4 tốt chung cho mọi bài toán.')
    slide('Kiểm tra nhãn trước khi kết luận',body=['Nhãn vẫn là tổng24giờ Vrain, giữ nguồn/QC và tách hai API.',
        '2025: cả136 ngày–trạm≥200mm đều có ít nhất một trạm trong30km cũng≥50mm.',
        'GSMaP chưa hiệu chỉnh trạm ghi nhận≥50mm ở128/136 trường hợp.',
        'Đây là hỗ trợ bối cảnh, chưa chứng nhận cảm biến; không sửa hoặc loại nhãn.'])
    slide('Điểm yếu cần xử lý: mưa lớn',body=['Trong2025, mẫu≥50mm chiếm khoảng5,6% số mẫu.',
        'Với LightGBM N3 cũ, nhóm này chiếm88–92% tổng bình phương sai số.',
        'Vì vậy cần đọc cả dự báo thiếu mưa lớn và FAR, ngoài điểm trung bình.'])
    for scope,label in [('dev2024','Phát triển2024'),('retrospective2025_legacy','Hồi cứu2025'),('retrospective2026_modern','Hồi cứu2026 — API hiện hành')]:
        slide(label+' | RMSE đầu mean (mm)',table=point_table(points,scope,'mean').rename(columns={'model':'Mô hình'}),notes='Cùng mẫu trong mỗi giai đoạn. Số in đậm là nhỏ nhất mỗi cột. Chỉ là điểm ước lượng; khoảng tin cậy và tính ổn định qua năm cần xem riêng.')
    slide('Hồi cứu2025 | MAE đầu median (mm)',table=point_table(points,'retrospective2025_legacy','median').rename(columns={'model':'Mô hình'}))
    if reference_context is not None:
        slide('2025 | RMSE đầu mean: thêm GRU N5 cũ (mm)',table=reference_context.rename(columns={'model':'Mô hình'}),
            notes='RMSE đầu mean. GRU_N5_previous là mô hình cũ, không fit lại. Đã khớp đúng trạm/issue/hạn/API và nhãn với tập mới. Đây là tham chiếu mô tả bổ sung, không là phép so chính đã định trước và không đổi mô hình chính của nghiên cứu trước.')
    if seed_variation is not None:
        small=seed_variation[seed_variation.evaluation_set.eq('retrospective2025_legacy')&seed_variation.metric.eq('macro_rmse')&seed_variation.model.isin(['LGB_T3','GRU_T3'])]
        slide('Ba seed: kết quả thay đổi bao nhiêu?',table=small[['model','horizon','mean','std']].rename(columns={
            'model':'Mô hình','horizon':'Ngày','mean':'RMSE trung bình','std':'Độ lệch chuẩn'}),
            notes='Trung bình và độ lệch chuẩn RMSE của ba lần fit riêng, không phải CI hay ba bộ dữ liệu độc lập. Điểm ensemble trong các bảng chính được tính sau khi lấy trung bình ba dự báo, nên khác trung bình ba RMSE.')
    slide('2025 | Đồ thị sai số các mô hình',picture='rmse_2025.png')
    slide('2025 | Thêm biến có tín hiệu ổn định không?',picture='feature_intervals_2025.png',caption='Thanh còn đi qua0: chưa tách được cải thiện và giảm sút với mức tin cậy đã chọn.',notes='Âm nghiêng về mô hình thêm biến. CI đồng thời12so sánh, bootstrap khối14ngày. Dữ liệu2025đãxem; hiệu chỉnh nhiều so sánh không khôi phục vai trò test độc lập.')
    heavy=events[events.evaluation_set.eq('retrospective2025_legacy')&events.threshold_mm.eq(50)&events.decision_rule.eq('calibration_selected')&events.model.isin(['MOS','LGB_T0','LGB_T3','GRU_T0','GRU_T3','GRU_LINEAR23'])]
    for h in (1,2,3):
        t=heavy[heavy.horizon.eq(h)][['model','macro_pod','macro_far','macro_csi']].rename(columns={'model':'Mô hình','macro_pod':'POD','macro_far':'FAR','macro_csi':'CSI'})
        slide(f'2025 | Mưa≥50mm — ngày{h}',table=t,notes='Cutoff chọn chỉ trên cross-fit2023. POD/FAR là trung bình giữa trạm với mẫu có định nghĩa. Không đọc POD một mình. Số lần sự kiện và hits/misses/falsealarms có trong CSV đầy đủ.')
    if bss_table is not None:
        slide('2025 | BSS mưa≥50mm: so với khí hậu',table=bss_table.rename(columns={'model':'Mô hình'}),higher_is_better=True,
            notes='Lớn hơn tốt hơn, in đậm giá trị lớn nhất. BSS dương cho thấy hơn khí hậu tham chiếu; T3 không tốt hơn T0 đồng đều. BSS không phụ thuộc cutoff báo có/không. Các khác biệt này là mô tả, không đổi mục tiêu RMSE chính.')
    if decision_table is not None:
        slide('Cùng mô hình, đổi ngưỡng thì POD/FAR đổi',table=decision_table,caption='Mưa≥50mm/24h • ngày1 • hồi cứu2025. POD cao hơn có thể đi cùng nhiều báo nhầm hơn.',
            notes='Mưa≥50mm ngày1 năm2025. Cutoff0,5 và cutoff chọn2023 đều đã định trước. POD cao hơn có thể đi cùng nhiều báo nhầm hơn. Không chọn cutoff sau khi thấy2025. So sánh thêmBS/BSS để phân biệt chất lượng xác suất và điểm vận hành.')
    slide('Kết quả nào đang có cơ sở để giữ?',body=['Bản kiểm định trước: khí tượng GFS thô cải thiện RMSE ngày2–3 so với chỉ mưa dự báo/lịch sử.',
        'Vòng này: chưa có cải thiện RMSE ổn định khi thêm diễn biến trong ngày.',
        'Một vài CSI/FAR thay đổi, đi cùng thay đổi POD và cutoff; chưa đủ để chốt thêm cả nhóm biến.',
        'Giữ hướng NWP + mưa trạm và các đối chứng chặt chẽ, tiếp tục kiểm định bằng dữ liệu tương lai.'])
    slide('Sai số vẫn tập trung ở nhóm nào?',picture='tail_error_share.png')
    conclusion=summary
    if summary[0].startswith('Trong thiết kế'):
        conclusion=['Chưa có bằng chứng ổn định để dùng đủ49biến làm cấu hình chính.',
            'Cả12phép so chính đều chưa đủ bằng chứng cải thiện đáng tin cậy trên2025.',
            'Giữ cấu hình gọn và phương án đã kiểm chứng trước đó làm tham chiếu.',
            '2025–2026 đã được xem. Cần một giai đoạn tương lai mới để xác nhận tiếp.']
    slide('Kết luận và giới hạn',body=conclusion,notes='\n'.join(summary)+'\nĐọc báo cáo và CSV đầy đủ. Kết quả âm cũng được giữ. Không tuyên bố SOTA hay sẵn sàng realtime.')
    slide('Bước tiếp theo có giá trị nghiên cứu',body=['Giữ đầy đủ kết quả và đối chứng; chọn hướng theo mục tiêu lượng mưa/cảnh báo đã định trước.',
        'Đo thực tế độ trễ nguồn, ghi log bản GFS và số đo có sẵn tại issue.',
        'Đóng băng ứng viên trước khi thu thập một giai đoạn tương lai mới; chấm từng trạm/mùa/hạn.',
        'Tiếp tục xác minh API/cảm biến với nhà cung cấp; nhánh Bi-LSTM để sau.'])
    path=PUBLIC/'PBL6_CAI_TIEN_DU_BAO_NGAN_HAN.pptx';prs.save(path)
    return len(prs.slides)

def main():
    assert_freeze();verification=json.loads((PUBLIC/'model_verification.json').read_text())
    if verification['status']!='passed':raise ValueError('Verification required')
    feature_catalog()
    points=pd.read_csv(PUBLIC/'point_metrics.csv');pairs=pd.read_csv(PUBLIC/'paired_comparisons.csv');events=pd.read_csv(PUBLIC/'event_metrics.csv')
    previous=previous_reference()
    context=pd.concat([points[points.model.isin(['LGB_T0','LGB_T3','GRU_T0','GRU_T3'])],previous],ignore_index=True)
    context=context[context.evaluation_set.eq('retrospective2025_legacy')&context.functional.eq('mean')].pivot(index='model',columns='horizon',values='macro_rmse')
    context.columns=[f'D{h}' for h in context.columns];context=context.reset_index()
    selected_models=['LGB_T0','LGB_T3','GRU_T0','GRU_T3']
    probability=pd.read_csv(PUBLIC/'probability_metrics.csv')
    bss=probability[probability.evaluation_set.eq('retrospective2025_legacy')&probability.threshold_mm.eq(50)&probability.model.isin(selected_models)].pivot(index='model',columns='horizon',values='macro_bss').reindex(selected_models)
    bss.columns=[f'D{h}' for h in bss.columns];bss=bss.reset_index()
    heavy=events[events.evaluation_set.eq('retrospective2025_legacy')&events.threshold_mm.eq(50)&events.decision_rule.eq('calibration_selected')&events.model.isin(selected_models)]
    decisions=events[events.evaluation_set.eq('retrospective2025_legacy')&events.threshold_mm.eq(50)&events.horizon.eq(1)&events.model.isin(['LGB_T0','LGB_T3'])].copy()
    decisions['label']=decisions.model+' / '+decisions.decision_rule.map({'fixed_0.5':'cố định','calibration_selected':'chọn2023'})
    decisions=decisions[['label','cutoff','macro_pod','macro_far','macro_csi']].rename(columns={'label':'Mô hình / quy tắc','cutoff':'Cutoff','macro_pod':'POD','macro_far':'FAR','macro_csi':'CSI'})
    seeds=pd.read_csv(PUBLIC/'seed_metrics.csv')
    seed_variation=seeds.groupby(['evaluation_set','horizon','model','metric']).value.agg(['mean','std','min','max']).reset_index()
    seed_variation.to_csv(PUBLIC/'seed_variation.csv',index=False,lineterminator='\n')
    counts=pd.read_csv(PUBLIC/'sample_counts.csv');tail=pd.read_csv(PUBLIC/'error_contribution.csv');plots(points,pairs,tail)
    q=pairs[pairs.evaluation_set.eq('retrospective2025_legacy')&pairs.primary]
    signals=q[q.adjusted_exploratory_signal]
    t3=q[q.model.eq('LGB_T3')];gru=q[q.model.eq('GRU_T3')]
    delta=lambda table:', '.join(f'D{int(r.horizon)}: {number(r.difference)} mm' for r in table.sort_values('horizon').itertuples())
    summary=[f'LightGBM T3−T0, chênh lệch RMSE năm 2025: {delta(t3)}.',
             f'GRU T3−LINEAR23: {delta(gru)}.',
             f'Có {len(signals)}/12 phép so chính có tín hiệu qua cả CI đồng thời và Holm; vẫn là thăm dò vì 2025 đã được xem.',
             'Không thay kết luận kiểm chứng cũ. Chưa chứng minh vận hành realtime hoặc tính liên tục hai API.']
    if len(signals)==0:
        summary.insert(0,'Trong thiết kế và ngân sách hiện tại, chưa có bằng chứng ổn định để chốt bộ 49 biến làm đầu vào chính. Giữ cấu hình gọn và phương án đã kiểm chứng trước đó làm tham chiếu.')
    method=(PUBLIC/'PHUONG_AN_THUC_HIEN.md').read_text(encoding='utf-8')
    method=method[method.index('## 1.'):method.index('## 8.')]
    sections=['# Báo cáo cải tiến dự báo mưa ngắn hạn tại trạm',
        'Cập nhật ngày 18/11/2026; phiên bản thí nghiệm khởi tạo ngày 17/11. Giữ nguyên bản kiểm định trước đó.',
        '## Kết quả đọc trước','\n\n'.join(summary),
        'Số âm trong chênh lệch RMSE nghiêng về cấu hình thêm biến. Điểm thấp hơn chưa đủ để khẳng định tăng chất lượng ổn định: cần đọc khoảng tin cậy, tính nhất quán giữa năm và hạn dự báo, sai số mưa lớn và báo nhầm. Các kết quả 2025–2026 của vòng này là hồi cứu vì những năm này đã được phân tích trước đó.',
        '## Thiết kế đã định trước',method,
        '## 8. Số mẫu và ngân sách huấn luyện thực tế',
        markdown_table(counts,list(counts.columns),['Giai đoạn','API','Mẫu trạm–issue','Trạm','Ngày issue']),
        'LightGBM chạy đủ T0–T3: mỗi cấu hình có 3 hạn × 3 seed × 4 đầu, tổng cộng 144 estimator. Giữ số cây và siêu tham số đã được chọn qua cross-validation chỉ trên train ở vòng trước. GRU có T0, T3 và LINEAR23, mỗi cấu hình ba seed, tổng cộng 9 lần fit. Giữ 17 epoch, hidden 16 và head 24. Không tìm thêm cấu hình theo điểm 2025–2026.',
        'T0 được huấn luyện lại để kiểm tra đối chiếu với bản cũ. Xem `baseline_refit_parity.json` về độ khớp. Ngưỡng quyết định sự kiện vẫn chỉ chọn trên cross-fit năm 2023. Mỗi mô hình được chấm trên cùng các mẫu trong từng giai đoạn.',
        '## 9. Bảng kết quả đầy đủ',
        '**In đậm là điểm nhỏ nhất mỗi cột**, không đồng nghĩa khác biệt có ý nghĩa thống kê. Đơn vị lượng mưa: mm/24h. Đầu mean được đánh giá chính bằng RMSE; đầu median được đánh giá chính bằng MAE.']
    for scope,title in [('dev2024','Phát triển 2024'),('retrospective2025_legacy','Hồi cứu 2025'),('retrospective2026_modern','Hồi cứu 2026 — API hiện hành'),('retrospective2026_legacy','Hồi cứu 2026 — API cũ, ít sự kiện mưa lớn')]:
        for functional,label in [('mean','RMSE của đầu mean'),('median','MAE của đầu median')]:
            table=point_table(points,scope,functional)
            sections.extend([f'### {title} — {label}',markdown_table(table,['model','D1','D2','D3'],['Mô hình','Ngày 1','Ngày 2','Ngày 3'],['D1','D2','D3'])])
    sections.extend(['![RMSE 2025](rmse_2025.png)',
        '### Tham chiếu bổ sung với GRU N5 đã có',
        markdown_table(context,['model','D1','D2','D3'],['Mô hình','Ngày 1','Ngày 2','Ngày 3'],['D1','D2','D3']),
        'GRU_N5_previous là mô hình cũ, không được fit lại. Dự báo cũ đã được khớp đúng trạm, issue, hạn và API với các hàng của tập đánh giá mới. Bảng này giúp đọc kết quả mới trong bối cảnh phương án đã có; đây là so sánh mô tả bổ sung, không phải phép so chính định trước hay bằng chứng chọn lại mô hình theo test. Bảng `previous_model_reference.csv` có cả đầu median và các giai đoạn còn lại.',
        '## 10. Hiệu quả đặc trưng và bất định',
        markdown_table(q,['model','reference','horizon','difference','simultaneous_ci_low','simultaneous_ci_high','holm_p'],
                       ['Mô hình','Đối chứng','Ngày','ΔRMSE','CI thấp','CI cao','p Holm']),
        'Khoảng tin cậy trên đã hiệu chỉnh đồng thời cho 12 phép so. Chỉ ghi nhận tín hiệu khi chênh lệch âm, cận trên CI đồng thời âm và p Holm < 0,05. Đây vẫn là kết quả thăm dò sau khi đã xem 2025 ở vòng trước; không dùng từ “kiểm định độc lập mới”.',
        '### Biến thiên giữa ba seed',
        markdown_table(seed_variation[seed_variation.evaluation_set.eq('retrospective2025_legacy')&seed_variation.metric.eq('macro_rmse')&seed_variation.model.isin(['LGB_T3','GRU_T3'])],
                       ['model','horizon','mean','std'],['Mô hình','Ngày','RMSE trung bình','Độ lệch chuẩn']),
        'Đây là biến thiên giữa ba lần fit, không phải khoảng tin cậy theo dữ liệu khí hậu. Bảng chính chấm ensemble sau khi lấy trung bình dự báo; trung bình ba RMSE là một đại lượng khác. Xem đầy đủ từng seed trong `seed_metrics.csv` và thống kê trong `seed_variation.csv`.',
        '![Khoảng tin cậy](feature_intervals_2025.png)','## 11. Mưa lớn và nguồn nhãn',
        'Trong bản cũ, các mẫu từ 50 mm/24h chỉ chiếm khoảng 5,6% số mẫu năm 2025 nhưng đóng góp 88–92% tổng bình phương sai số của LGB N3. Các bảng mới `error_contribution.csv` và `conditional_amount_metrics.csv` báo riêng mức dự báo thiếu và tỷ trọng sai số của nhóm này. Bảng `event_metrics.csv` có POD/FAR/CSI cùng số báo đúng, bỏ sót và báo nhầm; báo cả ngưỡng xác suất 0,5 và ngưỡng được chọn trên 2023.',
        '### BSS đối với mưa từ 50 mm/24h',
        markdown_table(bss,['model','D1','D2','D3'],['Mô hình','Ngày 1','Ngày 2','Ngày 3'],bold_max=['D1','D2','D3']),
        'BSS lớn hơn tốt hơn. Các giá trị dương cho thấy hơn khí hậu tham chiếu, nhưng T3 không hơn T0 đồng đều. Những khác biệt nhỏ này là mô tả, chưa phải kết luận có ý nghĩa thống kê.',
        '### POD/FAR/CSI tại cutoff đã chọn trên 2023',
        markdown_table(heavy,['model','horizon','cutoff','macro_pod','macro_far','macro_csi'],['Mô hình','Ngày','Cutoff','POD','FAR','CSI']),
        '### Cùng một mô hình, đổi ngưỡng thì các chỉ số đổi',
        markdown_table(decisions,list(decisions.columns)),
        'Bảng này là mưa từ 50 mm/24h ở ngày 1 năm 2025. T0 có POD khoảng 0,680 và FAR 0,569 ở cutoff chọn trên 2023; dùng cutoff cố định 0,5 thì POD khoảng 0,476 và FAR 0,254. Vì thế không đánh giá “POD 0,4 tốt hay xấu” nếu chưa biết ngưỡng và mức báo nhầm. Cả hai quy tắc đã định trước; không chọn lại cutoff theo năm 2025.',
        'Một vài CSI/FAR của T3 tốt hơn ở cutoff riêng, đi cùng thay đổi POD. Ở ngày 1, BSS của LightGBM T3 lại thấp hơn nhẹ T0. Đây là lý do cần phân biệt chất lượng xác suất và lựa chọn điểm vận hành; chưa đủ cơ sở kết luận thêm biến giúp mọi mục tiêu.',
        'Dòng từ 200 mm trong bảng đóng góp sai số là tập con của dòng từ 50 mm, không cộng hai tỷ trọng đó với nhau. Năm 2026 thiếu phần cuối năm và thay đổi độ phủ API; không so riêng điểm thấp hơn giữa 2026 và 2025 để kết luận mô hình tự tốt lên.',
        '![Đóng góp sai số mưa lớn](tail_error_share.png)',
        markdown_table(pd.read_csv(PUBLIC/'label_context_summary.csv'),['evaluation_set','days_ge200','extreme_with_neighbor_ge50','extreme_with_gsmap_context','extreme_with_gsmap_ge50'],
                       ['Giai đoạn','Số ≥200','Có trạm gần ≥50','Có GSMaP','GSMaP ≥50']),
        'Đã đối chiếu tổng giờ với nhãn ngày, trạm trong bán kính 30 km và GSMaP thô chưa hiệu chỉnh trạm. Trong 2025, cả 136 ngày–trạm từ 200 mm/24h đều có ít nhất một trạm gần ghi nhận từ 50 mm; 128/136 trường hợp có GSMaP từ 50 mm. Điều này hỗ trợ bối cảnh mưa lớn nhưng chưa chứng nhận cảm biến. Không sửa hoặc loại nhãn. Mưa ước tính trên ô vệ tinh có thể thấp hơn số đo tại một điểm; cờ rà soát không phải tiêu chuẩn loại trạm.',
        'Hai API cùng thuộc Vrain, chưa được nhà cung cấp xác nhận nguyên nhân khác độ phủ và tính liên tục. Nhóm API cũ trong 2026 có rất ít mưa lớn, chưa đủ kết luận cảnh báo ổn định. GSOD dùng ngày UTC khác cửa sổ 19h–19h Việt Nam nên không được đối chiếu trực tiếp cùng nhãn hiện tại. Bảng đối chiếu GSMaP là so sánh sản phẩm quan trắc, không phải điểm dự báo mô hình.',
        '## 12. Kiểm chứng và khuyến nghị',
        f'Đã kiểm chứng độc lập {verification["rows"]:,} hàng đánh giá, {verification["metric_values_independently_checked"]:,} giá trị metric và replay {verification["replay_rows"]} hàng. Thay nhãn tương lai không làm đổi dự báo. Scaler và projection chỉ dùng train. Giữ nguyên {verification["protected_artifacts_unchanged"]} artifact cũ.',
        'Giữ kết quả kiểm chứng trước đó làm bằng chứng chính. Vòng mới bổ sung phép so thông tin trong ngày. Chỉ đề nghị dùng thêm nhóm biến khi tín hiệu nhất quán giữa hạn dự báo và giai đoạn, đồng thời không đánh đổi bất lợi với mục tiêu cảnh báo. Dù điểm tốt hơn, cần khóa ứng viên trước một giai đoạn tương lai chưa dùng để xác nhận tiếp. Đo độ trễ thực tế và xác minh nguồn API/cảm biến trước khi tuyên bố dùng được trong vận hành.',
        'Với kết quả vòng này, không chốt mặc định T3 chỉ vì có nhiều biến. Kết luận chỉ áp dụng cho cấu hình, dữ liệu và ngân sách đã thử; chưa chứng minh diễn biến GFS luôn vô ích. Tuning hoặc mở rộng số năm huấn luyện cần một protocol riêng, ghi lại vai trò dữ liệu và kiểm định bằng giai đoạn mới chưa sử dụng.',
        'Cơ sở tích cực đã có từ nghiên cứu trước: khi bổ sung khí tượng GFS thô, N1 so với N0 giảm RMSE ngày 2 khoảng 0,829 mm và ngày 3 khoảng 0,833 mm, đạt tiêu chí đã khóa sau hiệu chỉnh nhiều so sánh. [Bản kiểm định trước](../gfs_station_final_2026_11_17/KET_LUAN.md) giữ nguyên bằng chứng đó. Vòng mới chưa chứng minh thêm lợi ích RMSE ổn định từ diễn biến trong ngày; kết quả này giúp thu gọn cấu hình nghiên cứu.',
        'Dữ liệu, tọa độ/registry, checkpoint và dự báo từng thời điểm nằm riêng ngoài Git. GitHub chỉ chứa mã và thống kê tổng hợp. Nhánh Bi-LSTM để sau theo yêu cầu.',
        '## 13. Nguồn và tệp kiểm tra',
        '[NOAA GFS](https://www.nco.ncep.noaa.gov/pmb/products/gfs/); [JAXA bin giờ](https://sharaku.eorc.jaxa.jp/GSMaP/faq/GSMaP_faq03.html); [JAXA raw/GC](https://www.eorc.jaxa.jp/GPM/doc/product/format/en/07.GPM_GSMaP_Product_Format_E.pdf); [NOAA GSOD](https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc%3AC00516).',
        'Đọc cùng `protocol.json`, `feature_catalog.csv`, `source_verification.json`, `dataset_verification.json`, `baseline_refit_parity.json`, `model_verification.json`, `seed_metrics.csv`, `paired_comparisons.csv` và các bảng metrics. [Đối chiếu phương pháp với nghiên cứu](DOI_CHIEU_PHUONG_PHAP.md) giải thích phạm vi có thể so sánh, chưa tuyên bố vượt bài báo.'] )
    text='\n\n'.join(sections);textfile(PUBLIC/'BAO_CAO_CAI_TIEN_NGAN_HAN.md',text);docx_from_markdown(text)
    nslides=slides(points,counts,pairs,events,summary,seed_variation,context,bss,decisions)
    subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/render_gfs_temporal.ps1')],cwd=ROOT,check=True)
    textfile(PUBLIC/'KET_LUAN.md','# Kết luận vòng cải tiến ngắn hạn\n\n'+'\n\n'.join(summary)+'\n\nĐọc báo cáo đầy đủ để đánh giá bất định, mưa lớn, FAR và nguồn nhãn.')
    textfile(PUBLIC/'README.md','# Diễn biến GFS trong ngày — đã hoàn thành\n\n'+
        '[Báo cáo Word](BAO_CAO_CAI_TIEN_NGAN_HAN.docx) · [Markdown](BAO_CAO_CAI_TIEN_NGAN_HAN.md) · [Slide](PBL6_CAI_TIEN_DU_BAO_NGAN_HAN.pptx) · [Kết luận](KET_LUAN.md)\n\n'+
        '57 trạm; LightGBM T0–T3, GRU T0/T3/LINEAR23, ba seed và năm đối chứng. Dữ liệu2025–2026 đã xem nên vòng mới là hồi cứu; không fit/tuning bằng các năm này. [Phương án](PHUONG_AN_THUC_HIEN.md) và protocol ghi đầy đủ cách chia mẫu/đầu vào/đầu ra. Kết quả cũ được giữ nguyên.\n\n'+
        'Mọi dữ liệu trạm và checkpoint nằm ngoài Git tại `data/operational/gfs_temporal_2026_11_17/`. Gói riêng gửi nhóm là `PBL6_NGAN_HAN_GFS_VRAIN_2021_2026.zip` trong thư mục đó, gồm một Parquet đã ghép X/y và năm tệp hướng dẫn/kiểm tra. Các CSV công khai chỉ chứa thống kê tổng hợp.')
    lock=json.loads((BASE/'training_lock.json').read_text());freeze=json.loads((BASE/'model_freeze.json').read_text())
    write_json(PUBLIC/'model_manifest.json',dict(status='frozen_and_verified',frozen_utc=freeze['frozen_utc'],
        protocol_sha256=lock['protocol'],dataset_sha256=lock['dataset'],software_versions=lock['environment'],
        code_sha256=lock['code'],baseline_dependencies_sha256=lock['baseline_dependencies'],artifact_sha256=freeze['artifacts'],train_years=[2021,2022],calibration_years=[2023],
        amount_models_primary_in_old_study_unchanged=True,retrospective_years=[2025,2026],weights_and_observations_not_public=True))
    bundle=handoff_bundle()
    files={p.name:sha(p) for p in sorted(PUBLIC.iterdir()) if p.is_file() and p.name!='release.json'}
    code={str(p.relative_to(ROOT)):sha(p) for pattern,folder in [('gfs_temporal*.py',ROOT/'src'),('*gfs_temporal*.py',ROOT/'scripts'),('test_gfs_temporal*.py',ROOT/'tests')] for p in folder.glob(pattern)}
    code['scripts/render_gfs_temporal.ps1']=sha(ROOT/'scripts/render_gfs_temporal.ps1')
    code['scripts/monitor_gfs_temporal.ps1']=sha(ROOT/'scripts/monitor_gfs_temporal.ps1')
    write_json(PUBLIC/'release.json',dict(status='complete',created_utc=datetime.now(timezone.utc).isoformat(),
        slides=nslides,report_sha256=files,code_sha256=code,model_freeze_sha256=sha(BASE/'model_freeze.json'),
        retrospective=True,raw_data_or_checkpoints_public=False,private_handoff_bundle=bundle))
    print(json.dumps(dict(status='complete',slides=nslides,files=len(files))))

if __name__=='__main__':main()
