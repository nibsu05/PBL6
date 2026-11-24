"""Editable Vietnamese teaching slides from verified daily CPC aggregates only."""
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Patch
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Pt
from presentation_layout import Deck,NAVY,TEAL,RED,MUTED
from daily_gauge_slide_notes import apply_notes

DATA=ROOT/'reports/daily_gauge_2026_11_04'
OUT=ROOT/'reports/daily_gauge_slides_2026_11_04'
STEM='PBL6_DU_LIEU_NGAY_3_MO_HINH'
MODELS=['lgbm','tft','informer'];LABELS=['LightGBM','TFT','Informer']
METRICS=['RMSE','MAE','bias','BS','BSS','CSI','POD','FAR']
HEADERS=['RMSE ↓','MAE ↓','Bias ≈0','BS ↓','BSS ↑','CSI ↑','POD ↑','FAR ↓']
LOWER={'RMSE','MAE','bias','BS','FAR'}
FOOT='CPC vùng xấp xỉ • Phát triển 2021–2023 • Ngưỡng chính 16 mm/24h • Test 2025 giữ kín'
URLS=dict(cpc='https://ftp.cpc.ncep.noaa.gov/precip/CPC_UNI_PRCP/GAUGE_GLB/DOCU/PRCP_CU_GAUGE_V1.0GLB_0.50deg_README.txt',
    era='https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_HOURLY',
    isd='https://www.ncei.noaa.gov/pub/data/noaa/isd-format-document.pdf',
    pham='https://doi.org/10.1016/j.atmosres.2020.104845',
    iran='https://rmets.onlinelibrary.wiley.com/doi/full/10.1002/met.70143',
    tft_daily='https://juti.if.its.ac.id/index.php/juti/article/view/1518')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def fmt(value):return f'{value:.3f}'.replace('.',',')
def signed(value):return f'{value:+.3f}'.replace('.',',')
def write(name,value):(OUT/name).write_text(value.rstrip()+'\n',encoding='utf8',newline='\n')


def spatial_figure(audit):
    w=pd.read_parquet(ROOT/'data/processed/regional_danang/cell_weights.parquet')
    coarse=pd.read_csv(DATA/'cpc_spatial_support.csv')
    counts=audit['original_binary_probes'][0]['gauge_counts']
    assert len(w)==93 and len(coarse)==9 and len(counts)==9
    assert all(p['gauge_counts']==counts for p in audit['original_binary_probes'])
    fig,ax=plt.subplots(figsize=(8.8,5.5))
    for row,count in zip(coarse.itertuples(),counts):
        ax.add_patch(Rectangle((row.cpc_lon-.25,row.cpc_lat-.25),.5,.5,
            facecolor='#FFF1D5' if count>0 else '#F3F5F7',edgecolor='#536877',lw=1.4,zorder=1))
    for row in w.itertuples():
        ax.add_patch(Rectangle((row.lon-.05,row.lat-.05),.1,.1,facecolor='#087E8B',
            edgecolor='white',lw=.45,alpha=.75,zorder=2))
    for row in coarse.itertuples():
        ax.add_patch(Rectangle((row.cpc_lon-.25,row.cpc_lat-.25),.5,.5,fill=False,edgecolor='#123047',lw=1.2,zorder=3))
    ax.set_xlim(coarse.cpc_lon.min()-.32,coarse.cpc_lon.max()+.32)
    ax.set_ylim(coarse.cpc_lat.min()-.30,coarse.cpc_lat.max()+.30)
    ax.set_aspect(1/np.cos(np.deg2rad(15.75)));ax.set_xlabel('Kinh độ (°E)');ax.set_ylabel('Vĩ độ (°N)')
    ax.legend(handles=[Patch(facecolor='#087E8B',label='93 ô của footprint hiện tại'),
        Patch(facecolor='#FFF1D5',edgecolor='#'+NAVY,label='Ô CPC có báo số trạm ở các ngày probe'),
        Patch(facecolor='#F3F5F7',edgecolor='#'+NAVY,label='Ô CPC không báo trạm bên trong ở probe')],
        loc='upper left',fontsize=9,framealpha=.96)
    ax.set_title('Footprint dữ liệu và lưới CPC; chưa phải ranh hành chính',fontsize=12)
    fig.tight_layout();fig.savefig(OUT/'FOOTPRINT_VA_CPC.png',dpi=180);plt.close(fig)


def finalize_editable_tables(deck):
    """Style all paragraphs; frozen shared renderer styles only the first."""
    path=OUT/(STEM+'.pptx');prs=Presentation(path)
    for native,slide in zip(prs.slides,deck.slides):
        for shape,spec in zip(native.shapes,slide['shapes']):
            if spec['kind']!='table':continue
            for ri,row in enumerate([spec['headers']]+spec['rows']):
                for ci,_ in enumerate(row):
                    st=spec['styles'].get(f'{ri},{ci}',{})
                    for p in shape.table.cell(ri,ci).text_frame.paragraphs:
                        p.alignment=PP_ALIGN.CENTER;p.space_before=p.space_after=Pt(0);p.line_spacing=1.
                        for run in p.runs:
                            run.font.name='Arial';run.font.size=Pt(spec['size'])
                            run.font.bold=ri==0 or st.get('bold',False)
                            run.font.color.rgb=RGBColor.from_string('FFFFFF' if ri==0 else st.get('color',NAVY))
    prs.core_properties.title='Dự đoán mưa vùng 1–3 ngày: ERA5 ngày và nhãn CPC'
    prs.core_properties.author='Nhóm PBL6';prs.save(path)
    html=OUT/(STEM+'.html');text=html.read_text(encoding='utf8')
    assert '.ct{overflow:visible}' in text
    html.write_text(text.replace('.ct{overflow:visible}', '.ct{overflow:visible;white-space:pre-line}'),encoding='utf8',newline='\n')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    published=json.loads((DATA/'publication_manifest.json').read_text(encoding='utf8'))
    for name,meta in published['files'].items():assert sha(DATA/name)==meta['sha256'],name
    validation=json.loads((DATA/'validation.json').read_text(encoding='utf8'))
    assert validation['status']=='passed' and validation['models_replayed']==168
    run=json.loads((DATA/'run.json').read_text(encoding='utf8'))
    source=json.loads((DATA/'source_audit.json').read_text(encoding='utf8'))
    scores=pd.read_csv(DATA/'KET_QUA_72.csv');assert len(scores)==72
    paired=pd.read_csv(DATA/'paired_bootstrap.csv');absolute=pd.read_csv(DATA/'absolute_bss_ci.csv')
    catalog=pd.read_csv(DATA/'feature_catalog_daily.csv')
    protocol=json.loads((DATA/'protocol_frozen.json').read_text(encoding='utf8'))
    spatial_figure(source)
    deck=Deck();roles={}
    def slide(title,section='THÍ NGHIỆM DỮ LIỆU NGÀY',note='',source_line=FOOT,role=None):
        s=deck.slide(title,section,source_line,note)
        if role:roles[role]=s['number']
        return s
    def text(s,value,y=1.6,size=22,x=.7,w=11.95,h=3.8,bold=False,color=NAVY):
        return deck.text(s,x,y,w,h,value,size,bold,color)
    def band(s,value,color=TEAL):deck.band(s,value,color=color,size=18)
    def get(model,e,day):
        p=scores[(scores.model==model)&(scores.experiment==e)&(scores.lead_day==day)]
        assert len(p)==1;return p.iloc[0]
    def styles_for(rows,keys,start_col=1):
        result={}
        for col,key in enumerate(keys,start_col):
            values=[float(r[key]) for r in rows];a=np.abs(values) if key=='bias' else np.asarray(values)
            target=min(a) if key in LOWER else max(a)
            for ri,value in enumerate(values,1):
                compare=abs(value) if key=='bias' else value
                win=round(compare,3)==round(float(target),3)
                result[f'{ri},{col}']=dict(bold=win,color=RED if key=='BSS' and value<0 else TEAL if win else NAVY)
        return result

    s=slide('Dự đoán mưa vùng trong ba ngày tới',note='Báo cáo nghiên cứu, không phải giới thiệu app. Đầu ra trực tiếp của vùng xấp xỉ Đà Nẵng mới; lần này dùng ERA5 ngày và nhãn CPC từ phân tích trạm. Đủ ba mô hình/E0–E7. Kết quả ngày 2–3 còn hạn chế; chưa mở 2025.',role='title')
    text(s,'ERA5 theo ngày → nhãn mưa CPC của vùng',1.60,29,bold=True)
    deck.card(s,.6,2.65,3.95,2.6,'Đã hoàn thành','LightGBM · TFT · Informer\nĐủ E0–E7\n168 lượt mô hình/pipeline',21)
    deck.card(s,4.7,2.65,3.95,2.6,'Câu hỏi nghiên cứu','Thêm nhóm thông tin nào\ngiúp dự đoán tốt hơn,\nở ngày nào?',21)
    deck.card(s,8.8,2.65,3.95,2.6,'Kết luận cần giữ','Có tín hiệu ở ngày 1\nChưa xác nhận ích lợi\ntới ngày 2–3',21)
    band(s,'Một mẫu là một thời điểm của cả vùng; test 2025 vẫn giữ kín.')

    s=slide('Đầu ra là ba tổng mưa 24 giờ riêng',note='Tại mốc t, dự báo đồng thời ba tổng lượng mưa CPC trung bình vùng: [t,t+24), [t+24,t+48), [t+48,t+72). Không phải ba tổng tích lũy 24/48/72h, không phải 72 lượng giờ. Mưa trung bình vùng không có nghĩa mọi vị trí đều nhận cùng lượng. Ví dụ 12/35/8 chỉ để minh họa.',role='target')
    for x,title,body in [( .6,'Ngày 1','t → t+24 giờ\nVí dụ: 12 mm'),(4.7,'Ngày 2','t+24 → t+48 giờ\nVí dụ: 35 mm'),(8.8,'Ngày 3','t+48 → t+72 giờ\nVí dụ: 8 mm')]:deck.card(s,x,1.75,3.95,2.5,title,body,24)
    text(s,'Đơn vị: mm/24h trung bình theo diện tích của vùng.',4.70,24,h=.65)
    band(s,'Ví dụ 12 / 35 / 8 không phải 12 / 47 / 55 mm tích lũy.')

    s=slide('Đầu vào X và nhãn y đến từ hai nguồn',note='Đầu vào thí nghiệm cũ đã là khí tượng ERA5 quá khứ, không có mưa vệ tinh. GSMaP là nhãn cũ. Thí nghiệm ngày mới giữ ERA5 làm predictor nhưng thay nhãn bằng CPC; ERA5 ngày vẫn là tái phân tích, không tự thành số đo trạm. Không có mưa quá khứ CPC/GSMaP hoặc ERA5 giờ đích trong X. '+URLS['era']+' '+URLS['cpc'],role='sources')
    deck.card(s,.65,1.7,5.95,3.65,'X — Khí tượng ERA5','Nhiệt độ, ẩm, gió, áp suất…\nĐã tổng hợp theo vùng\nLấy trung bình mỗi 24 giờ\nChỉ dùng quá khứ',22)
    deck.card(s,6.8,1.7,5.9,3.65,'y — Mưa ngày CPC','Phân tích lưới từ trạm\nTổng hợp thành mưa vùng\nBa tổng 24 giờ tiếp theo\nDùng để dạy và chấm mô hình',22)
    band(s,'Chuyển sang bước ngày không biến ERA5 thành quan trắc trạm.')

    s=slide('CPC dựa trên trạm, vẫn là sản phẩm lưới',note='CPC nội suy/phân tích quan trắc trạm lên lưới 0,5°. Không gọi là toàn bộ số đo trạm hay đo trực tiếp trung bình địa giới. Một trạm chỉ đại diện vị trí của nó. Bộ NOAA hiện có một trạm mưa hiện đại ở vùng; danh mục gần vùng có các chuỗi khác chủ yếu từ thập niên1960–1970. Vrain đang xin, chưa có trong huấn luyện. '+URLS['cpc'],role='cpc')
    deck.table(s,['Dữ liệu','Đại diện cho điều gì?'],[
        ['Trạm đo mưa','Lượng mưa tại vị trí trạm'],['CPC 0,5°','Phân tích mưa trên ô từ mạng trạm'],['Nhãn vùng đang dùng','Trung bình có trọng số của các ô CPC']],y=1.6,row_h=.85,widths=[3.5,8.75],size=22,tag='label_meaning')
    text(s,'Vrain chưa được dùng; mạng NOAA đã kiểm tra chưa phủ đủ toàn vùng.',5.25,20,h=.6)
    band(s,'Dùng được làm nhãn nghiên cứu; vẫn cần kiểm chứng mưa thực của vùng.')

    s=slide('93 ô footprint giao với chín ô CPC',note='Hình chỉ vẽ footprint dữ liệu, không vẽ ranh hành chính. Diện tích 93 toàn ô khoảng11.074km² còn xấp xỉ Đà Nẵng mới. Mỗi ô CPC khoảng0,5°, không tạo93 quan trắc trạm độc lập. Trong13probe, ba trong chín ô báo gnum1; các ô có thể chỉ giao một phần vùng nên không suy thành ba trạm trong địa giới. gnum0 không nghĩa là không có thông tin từ trạm lân cận. Source: cpc_spatial_support.csv, source_audit.json.',role='spatial')
    deck.image(s,OUT/'FOOTPRINT_VA_CPC.png',.55,1.55,7.2,4.5)
    text(s,'93 ô nhỏ: vùng dữ liệu\nđang nghiên cứu.\n\n9 ô lớn: nguồn nhãn CPC.\n\n3/9 ô có báo số trạm\nở 13 ngày kiểm tra.',1.65,21,x=8.0,w=4.6,h=4.2)
    band(s,'Mặt nạ vùng hiện còn xấp xỉ địa giới Đà Nẵng mới.')

    s=slide('Lần này thay đổi những gì?',note='Không so trực tiếp điểm số hai thí nghiệm để kết luận dữ liệu ngày tốt hơn. Cùng lịch sử168h và cùng ý nghĩa ba tổng24h, nhưng đổi nhãn, mốc phát hành, bước chuỗi, calendar và daily readout. Muốn cô lập cadence phải cùng CPC/issue12UTC/mẫu rồi so6h và24h. Không chạy phép đó trong lượt làm slide.',role='old_new')
    deck.table(s,['Thành phần','Trước: GSMaP','Mới: CPC'],[
        ['Nguồn khí tượng X','ERA5 Hourly','Cùng ERA5 Hourly'],['Bước đầu vào','6 giờ → 28 bước','24 giờ → 7 bước'],
        ['Nhãn mưa','GSMaP cộng 24 giờ','CPC đã là tổng ngày'],['Mốc dự báo','00 UTC','12 UTC'],
        ['Số biến tối đa','44','42'],['Đầu ra','Ba tổng 24 giờ riêng','Vẫn ba tổng 24 giờ riêng']],y=1.55,row_h=.59,widths=[3.2,4.525,4.525],size=20,tag='old_new')
    band(s,'Không dùng điểm khác nhãn làm bằng chứng cải thiện trực tiếp.')

    s=slide('Từ dữ liệu giờ thành bảy bước ngày',note='Ở mỗi giờ đã tổng hợp khí tượng vùng, sau đó lấy trung bình đủ24giờ trong khối12–12UTC. MưaCPC đã là tổng24h nên giữ nguyên, không chia sang giờ và không nhân24. Gió lấy trung bình thành phần u/v. Ngày thiếu giờ hoặc có predictor không hữu hạn bị loại theo maskE7 chung; không điền0/đổi mẫu theo E. Lịch sửbảy ngày giữ cùng168h trước, chưa được chứng minh tối ưu.',role='daily_steps')
    deck.card(s,.65,1.70,5.95,3.65,'Khí tượng đầu vào','168 giờ của 7 ngày vừa qua\nMỗi 24 giờ lấy trung bình\n→ 7 bước × số đặc trưng\nCần đủ giờ và đủ vùng',23)
    deck.card(s,6.8,1.70,5.9,3.65,'Mưa làm nhãn','CPC đã có tổng ngày\nLấy ba khoảng ngày sau t\n→ 3 lượng mưa cần học\nKhông nội suy từ ngày xuống giờ',22)
    band(s,'Trung bình ngày có thể làm mất đỉnh khí tượng; chưa mặc định là tốt hơn.')

    s=slide('Mô hình nhận gì và xuất ra những gì?',note='TFT/Informer nhận x[B,7,F] và calendar[B,3,2]. Hai biến lịch sin_doy/cos_doy biểu diễn vị trí trong năm; không phải hai nguồn khí tượng hay hai mốc dự báo. Hai biến giờ bỏ vì hằng. Có3amount và9prob=3ngày×3ngưỡng16/50/100. Xác suất các ngưỡng lồng nhau, không cộng thành100%, không phải phần trăm diện tích mưa. Mô hình không nhận khí tượng tương lai.',role='shapes')
    deck.table(s,['Thành phần','Kích thước / ý nghĩa'],[
        ['Lịch sử khí tượng','7 ngày × F biến, F = 9…42'],['Lịch tương lai đã biết','3 ngày × 2 biến: sin/cos ngày trong năm'],
        ['Lượng mưa dự đoán','3 giá trị mm/24h'],['Xác suất đạt ngưỡng','3 ngày × 3 ngưỡng = 9 xác suất']],y=1.55,row_h=.8,widths=[3.5,8.75],size=22,tag='shapes')
    band(s,'Ngưỡng nghiên cứu 16 / 50 / 100 mm; không tự là cấp cảnh báo hành chính.')

    s=slide('Vì sao dùng mốc 12 UTC, tức 19 giờ VN?',note='MetadataEOD chínôCPC đều12UTC. AuditISDgốcID488550-99999 trong2015/2019/2021/2022/2023:1364/1365bản ghi24hđộ sâu khôngthiếu có timestamp12UTC; một trace00UTC.1151cặpGSODcờG cùngDATEkhớp≤0,3mm, không chứng nhận tất cả lượng mưa hoặc toànmạngCPC. Các condition/quality vẫn lưu. Giả định GSOD luôn00–00UTC trước đây cần rà soát; không tự ghi đè bảngcũ. '+URLS['isd'],role='eod')
    deck.card(s,.65,1.7,5.95,3.55,'Thông tin từ CPC','Chín ô ghi EOD = 12 UTC\nMột ngày mưa: 12 → 12 UTC\nTương đương 19 → 19 giờ VN',22)
    deck.card(s,6.8,1.7,5.9,3.55,'Kiểm tra NOAA gốc','1.364 / 1.365 bản ghi 24h\ncó timestamp 12 UTC\nTrong năm năm được kiểm tra',22)
    band(s,'Bằng chứng ở một trạm; chưa xác nhận EOD của toàn bộ mạng CPC.')

    s=slide('Bốn nhóm thông tin: B, A, M và C',note='Danh mục đủ42biến ở feature_catalog_daily.csv; bảybiếnbề mặt vàhaimã hóa mùa củaB. A gồmCAPE,CIN,has_lfc,TCWV,K-index,TotalTotals,BLH,tcc/lcc/mcc/hcc,swvl1. M gồm20biến:6ở850hPa,5ở500hPa,shear,IVTu/v/mag,VIMD,2bối cảnh,2chênháp. C chỉSSThộpbiển, không phải đầyđủENSO/MJO. has_lfc là tỷ phần theo vùng/thời gian sau tổng hợp.',role='groups')
    deck.table(s,['Nhóm','Số biến','Bao gồm những thông tin gì?'],[
        ['B — Nền','9','Nhiệt độ, điểm sương, ẩm gần mặt đất; áp suất bề mặt/mực biển; u/v gió 10 m; sin/cos ngày trong năm.'],
        ['A — Đối lưu, mây, đất','12','CAPE, CIN, has_lfc, hơi nước TCWV, K-index, Total Totals; độ cao lớp biên, bốn loại mây và ẩm đất lớp 1.'],
        ['M — Hoàn lưu và ẩm','20','Gió, ẩm, nhiệt độ, chuyển động đứng 850/500 hPa; đứt gió, IVT, phân kỳ dòng ẩm; bối cảnh hơi nước/dòng ẩm và chênh áp.'],
        ['C — Nhiệt độ biển','1','SST trung bình hộp biển đã chọn; chưa kiểm tra đầy đủ ENSO/MJO.']],y=1.43,row_h=.94,widths=[3.1,.9,8.25],size=18,tag='groups')
    deck.band(s,'M là nhóm hoàn lưu/ẩm; C chỉ có SST. Không suy rộng thành chỉ số khí hậu đầy đủ.',y=6.30,h=.44,size=16)

    s=slide('E0–E7: giữ nền, thêm từng tổ hợp nhóm',note='Factorial ba nhómA/M/C trên nềnB cố định; sốbiến9,21,29,10,41,22,30,42. Mỗi E có đủLightGBM/TFT/Informer. Tất cảchungmaskE7 vàmốc/thamchiếu/nhãn. Thêm biến làm đổi sốtham số mạng, không quy mọi chênh lệchthuầncho thôngtinvậtlý.',role='experiments')
    combos=['B','B + A','B + M','B + C','B + A + M','B + A + C','B + M + C','B + A + M + C']
    deck.table(s,['ID','Nhóm thông tin','Số biến'],[[f'E{i}',c,protocol['feature_counts'][f'E{i}']] for i,c in enumerate(combos)],
        y=1.55,row_h=.47,widths=[1.3,7.4,3.55],size=22,tag='experiments')
    band(s,'Thêm hết biến chưa chắc có điểm cao nhất; phải đọc đủ E0–E7.')

    s=slide('Có nghiên cứu dùng đặc trưng theo ngày',note='Pham2020PDFdo người dùng cung cấp mục2.2 dùng năm biến khí tượngngày, dữliệuthờitiếtGlobalWeatherDataforSWAT; mục3chiangẫu nhiên70/30, chưa là bằngchứng dựbáo ngoài thời gian1–3ngày. Neyestani2025mục2:5trạmIran,10ngày quákhứ→ngày kế. Amir2026TFTdaily:history30,OpenMeteo,đa hạn1/3/...ngày; không phải stationtruth ở Đà Nẵng. Không mang điểmpaper khác sang xếp hạngcùng bảng. '+URLS['pham']+' '+URLS['iran']+' '+URLS['tft_daily'],role='literature')
    deck.table(s,['Nghiên cứu','Thiết kế liên quan','Giới hạn khi tham khảo'],[
        ['Pham và cs. · 2020','Năm biến khí tượng ngày\nDự đoán mưa ngày ở Hòa Bình','Chia ngẫu nhiên 70/30;\nchưa là mẫu cho forecast 1–3 ngày'],
        ['Neyestani và cs. · 2025','Mười ngày quá khứ\n→ mưa ngày kế tại trạm','Năm trạm ở Iran;\nchưa kiểm chứng hạn ba ngày tại VN'],
        ['Amir và cs. · 2026','TFT dùng bước ngày\nCó hạn một và ba ngày','Khí tượng Open-Meteo;\nkhông thay kiểm chứng trạm/vùng']],y=1.55,row_h=1.15,widths=[3.,4.3,4.95],size=18,tag='literature')
    band(s,'Bước ngày là thiết kế có cơ sở để thử; hiệu quả phải đo trên dữ liệu của nhóm.')

    s=slide('Vì sao so cả LightGBM, TFT và Informer?',note='Ba pipeline học cùng nguyên liệu/ngày/nhãn; LGBM tóm tắt lịch sử còn mạng nhậnchuỗi. TFT/Informer là cácbảnđiềuchỉnh của dựán:khôngstaticcontext/phânvịTFT, readoutngàyTweedie/BCE; Informerprefix3ngày vàencoder7bước nên lợi thếchuỗidài chưa phảiđiểmthửchính. Không bắtTFTthắngLGBM, không chạyInformerchỉđểchứngminhkhôngkhảthi.',role='models')
    deck.table(s,['Mô hình','Cách nhận lịch sử','Vai trò trong phép so'],[
        ['LightGBM','Ngày cuối, trung bình 3/7 ngày,\nchênh lệch hai ngày cuối','Mô hình cây để so công bằng;\nkhông bắt buộc mạng phải thắng'],
        ['TFT','Chuỗi bảy ngày; cơ chế\nlựa chọn biến và attention','Thử học nhiều nhóm biến\nvà nhiều hạn cùng lúc'],
        ['Informer','Chuỗi bảy ngày; encoder/decoder\nvà attention ProbSparse','Thử một kiến trúc khác;\nchưa kiểm tra lợi thế chuỗi dài']],y=1.55,row_h=1.15,widths=[1.7,5.05,5.5],size=20,tag='models')
    band(s,'Cùng nguyên liệu nhưng khác biểu diễn/loss; chưa là phép so chỉ đổi kiến trúc.')

    s=slide('Chia theo thời gian, không chia ngẫu nhiên',note='Train/cal/eval cuốnchiếutheonăm; scaler/climatology chỉfittrain. Early stoppingBS16vàPlatt/thresholdCSI chỉdùngcal. Eval2021–2023đãlàdevelopmentkhámphá, khônggọiholdoutđộclập. DữliệucùngE7mask; nhãn3ngàykhôngvượtranhfold. Test2025giữkín. Folds đúngrun.json:1804/363/362;2167/362/348;2529/348/362.',role='folds')
    fold_rows=[]
    for year in [2021,2022,2023]:
        m=next(m for m in run['models'] if m['year']==year)
        fold_rows.append([year,f'2015–{year-2}',year-1,m['n_train'],m['n_cal'],m['n_eval']])
    deck.table(s,['Năm chấm','Train','Hiệu chỉnh','Số train','Số cal','Số chấm'],fold_rows,y=1.7,row_h=.7,widths=[1.8,2.25,2.0,2.1,2.0,2.1],size=21,tag='folds')
    text(s,'Train: học mô hình.\nHiệu chỉnh: chọn epoch, sửa xác suất, chọn ngưỡng quyết định.\nChấm: chỉ tính kết quả, không chọn lại cấu hình theo điểm đẹp.',4.9,20,h=1.0)
    band(s,'1.072 mốc chung mỗi hạn; dữ liệu nhãn 2025 chưa dùng để fit hoặc chấm.')

    s=slide('Ba seed khác ba năm và ba ngày dự đoán',note='Seed42/43/44đổi khởi tạo,shuffle/dropoutvàlấymẫuattentiontrongtrain, cùngdữliệuvàtham số. Ba seedkhông tạo thêmngày thời tiết. Trung bình dựđoánba seed rồitínhmetrics; không lấyseedđẹpnhất. MỗiE:mạng3năm×3seed=9; LGBM3năm xác định=3;8E×(9+9+3)=168pipeline/lượt. Có72dòngmetrics=8E×3model×3day, khôngnhầmvới168fits.',role='seeds')
    deck.card(s,.6,1.7,3.95,2.7,'3 seed: 42 / 43 / 44','Ba lần học ngẫu nhiên\ncùng cấu hình và dữ liệu\n→ lấy trung bình dự đoán',21)
    deck.card(s,4.7,1.7,3.95,2.7,'3 năm: 2021 / 22 / 23','Ba lần đánh giá\ntheo thời gian khác nhau\n→ kiểm tra độ bền',21)
    deck.card(s,8.8,1.7,3.95,2.7,'3 ngày: 1 / 2 / 3','Ba khoảng 24 giờ\ntrong tương lai\n→ ba nhãn dự đoán',21)
    text(s,'72 TFT + 72 Informer + 24 LightGBM = 168 lượt.',4.95,24,h=.65,bold=True)
    band(s,'Ba seed không làm số ngày thời tiết tăng gấp ba.')

    s=slide('Đọc đủ tám chỉ số trước khi chọn mô hình',note='Tất cảamountmetricmm/24h; biasdựbáotrừnhãn. BrierScorechấmxácsuất; BSSsoBSkhíhậuthángfittrain. CSI/POD/FARchấmsựkiện từxácsuấtvớitauchọncal; khôngđồngnhấtvớisựkiệntừlượngmưa. Hhit,Mmiss,Ffalsealarm; FARlàfalsealarmratio, khôngphảifalsepositiverate. BSS=0đồngsai sốBrierthanchieu, âmchưa tốt. PODkhôngcóngưỡng0.4tốtchung.',role='metrics')
    deck.table(s,['Chỉ số','Ý nghĩa dễ hiểu','Vì sao dùng?','Chiều tốt'],[
        ['RMSE','Sai số mm; phạt mạnh lỗi lớn','Không để sai số nặng bị che khuất','Nhỏ hơn'],
        ['MAE','Trung bình lệch tuyệt đối bao nhiêu mm','Đọc mức sai số lượng mưa','Nhỏ hơn'],
        ['Bias','Dự báo thừa hay thiếu trung bình','Phát hiện xu hướng lệch lượng mưa','Gần 0'],
        ['BS','Sai số của xác suất dự báo','Chấm xác suất trước khi chọn có/không','Nhỏ hơn'],
        ['BSS','BS cải thiện so khí hậu bao nhiêu','Kiểm tra hơn tham chiếu theo mùa không','Lớn hơn'],
        ['CSI','H / (H + M + F)','Cân bằng trúng, bỏ sót và báo nhầm','Lớn hơn'],
        ['POD','H / (H + M)','Bắt được bao nhiêu sự kiện thực tế','Lớn hơn'],
        ['FAR','F / (H + F)','Trong lần báo có, bao nhiêu lần nhầm','Nhỏ hơn']],
        y=1.45,row_h=.53,widths=[1.0,4.5,5.35,1.4],size=16.5,tag='metrics')
    deck.band(s,'H: báo trúng · M: bỏ sót · F: báo nhầm. POD cần đọc cạnh FAR và CSI.',y=6.36,h=.4,size=16)

    s=slide('BSS dương, bằng 0 và âm nghĩa là gì?',note='Ví dụ minh họa vớiBSkhíhậu0.10, không phải điểm môhìnhhiện tại. MôhìnhBS.08→BSS.20=giảm20%saiBrier;BS.10→0;BS.11→−.10=tăng10%. Không phải tỷ lệngàyđoánđúng. BSSphụthuộcngưỡng/hạn/mùa/nhãn/reference; khôngsodirectGSMaPCPC. Khí hậu thángfittrain, nhãn/dựđoán/referencechấmcùngmẫu.',role='bss_meaning')
    text(s,'BSS = 1 − BS mô hình / BS khí hậu',1.6,28,h=.7,bold=True)
    for x,title,body in [(.6,'BSS = +0,20','BS: 0,10 → 0,08\nGiảm 20% sai số Brier'),(4.7,'BSS = 0','BS: 0,10 → 0,10\nBằng khí hậu tham chiếu'),(8.8,'BSS = −0,10','BS: 0,10 → 0,11\nTăng 10% sai số Brier')]:deck.card(s,x,2.8,3.95,2.45,title,body,21)
    band(s,'Đây là ví dụ minh họa. BSS không phải phần trăm ngày dự đoán đúng.')

    s=slide('POD phải đọc cùng FAR và CSI',note='Số đếm tái tạo từmetricsđãkiểmchứng E7ngày1q16,116sựkiện:LGH61M55F59,TFT59/57/147,IF64/52/91. Đây làngưỡng quyếtđịnhxácsuất chọncal, khôngchọnlạitrêneval. POD0.4khônglàchuẩnchung:ngưỡngmưa,hạn,vùng,mùa,baselineđềukhác. KhôngmangPODpaperkhácsovớiPODdựánnếukhácgiao thức.',role='event_counts')
    rows=[]
    for model,label in zip(MODELS,LABELS):
        r=get(model,'E7',1);h=int(round(r.POD*r.events));miss=int(r.events)-h;false=int(round(h*r.FAR/(1-r.FAR)))
        np.testing.assert_allclose([h/(h+miss),false/(h+false),h/(h+miss+false)],[r.POD,r.FAR,r.CSI],rtol=1e-10)
        rows.append([label,h,miss,false,fmt(r.POD),fmt(r.FAR),fmt(r.CSI)])
    deck.table(s,['Mô hình','Trúng H','Bỏ sót M','Nhầm F','POD ↑','FAR ↓','CSI ↑'],rows,y=1.65,row_h=.72,widths=[2.2,1.55,1.75,1.75,1.65,1.7,1.65],size=20,tag='event_counts')
    text(s,'Cùng 116 sự kiện ở E7 ngày 1, ngưỡng 16 mm/24h.\nBắt thêm sự kiện nhưng báo nhầm nhiều chưa chắc tốt hơn.',4.95,22,h=1.0)
    band(s,'Không có chuẩn “POD 0,4 là tốt” áp dụng cho mọi bài toán.')

    s=slide('Các bảng sau chấm trên cùng mẫu nào?',note='1072issue/hạn=362+348+362năm2021/22/23; ba horizonnhãndịchtheongàynênsựkiện116/117/118khácnhau. GiữmaskE7choE0–E7; nguồnCPCcó3287ngày, mẫu pháttriểnhợp lệ3239sauwindow/QC; nguồn đủkhôngđồngnghĩamọicửasổhợplệ. Khíhậuvàluôn0baselineđãcótrongExcel. Mùađượctínhngàyđích theoendnominal. Thresholds50/100ít sựkiệnhơn, xem phụlụcExcelchứkhôngđọc q16nhưmứcmưa≥100.',role='sample_counts')
    event_rows=[]
    full=pd.read_csv(DATA/'scores_pooled.csv')
    for day in [1,2,3]:
        p=full[(full.model=='lgbm')&(full.experiment=='E7')&(full.lead_day==day)&(full.season=='all')].set_index('threshold_mm')
        event_rows.append([f'Ngày {day}',int(p.loc[16,'n']),int(p.loc[16,'events']),int(p.loc[50,'events']),int(p.loc[100,'events'])])
    deck.table(s,['Hạn','Số mốc chung','Sự kiện ≥16','Sự kiện ≥50','Sự kiện ≥100'],event_rows,y=1.7,row_h=.75,widths=[1.65,2.65,2.65,2.65,2.65],size=22,tag='sample_counts')
    text(s,'Bảng chính: toàn năm, xác suất mưa vùng ≥16 mm/24h.\nChi tiết mùa/năm/ngưỡng có trong Excel 11 sheet.',5.0,21,h=1.)
    band(s,'Không dùng số lượng seed hoặc số ô để nhân số ngày thời tiết.')

    for day in [1,2,3]:
        s=slide(f'BSS ngày {day}: đủ E0–E7 và ba mô hình',note='Mỗi hàng cùngE/ngày/mẫu/nhãn/reference. Đậm làđiểm tốt hơn tronghàng theođộchínhxácthiểnthị; màuđỏBSSâm, khôngtựlàkiểmđịnh. Ngày1LGđiểmcao;ngày2chỉLGE2/E6dươngrấtnhỏ;ngày3mọicặpmôhình/Eâm. KhôngchọnEđẹpnhấtrồicoilàđãtốiưu/holdout.',role=f'bss_day{day}')
        rows=[];styles={}
        for ei in range(8):
            e=f'E{ei}';r=[get(m,e,day) for m in MODELS];rows.append([e,*[fmt(q.BSS) for q in r]])
            for key,st in styles_for(r,['BSS']).items():
                ri,ci=map(int,key.split(','));styles[f'{ei+1},{ri}']=st
        deck.table(s,['Cấu hình',*LABELS],rows,y=1.55,row_h=.47,widths=[1.9,3.45,3.45,3.45],size=22,styles=styles,tag=f'bss_day{day}')
        caption={1:'Bổ sung M có điểm tăng; vẫn cần đọc CI của chênh lệch.',2:'Điểm dương rất nhỏ chưa chứng minh hơn khí hậu tham chiếu.',3:'Cả 24 cặp mô hình/cấu hình đều có điểm BSS âm.'}[day]
        band(s,caption)

    for day in [1,2,3]:
        s=slide(f'E7 ngày {day}: đọc đủ tám metrics',note='Ba môhìnhcùngE7vàcùngngày. Amountmetricmm/24h; BS/BSS/CSI/POD/FARtạingưỡng16. Đậmtheochiềutốt, biaslấytrị tuyệtđối; hòaở3chữsốđượcđậmnhưnhau. BSSâmvẫnđỏdùđiểmítâmhơn. Cầntách lượngvàxácsuất: ngày3TFTcóRMSEnhỏhơnnhẹkhôngđồngnghĩaBSSdương. SốliệutấtcảEtrongphụlục.',role=f'e7_day{day}')
        r=[get(m,'E7',day) for m in MODELS]
        deck.table(s,['Mô hình',*HEADERS],[[label,*[fmt(q[k]) for k in METRICS]] for label,q in zip(LABELS,r)],
            y=1.75,row_h=.85,widths=[1.85]+[1.3]*8,size=19,styles=styles_for(r,METRICS),tag=f'e7_day{day}')
        text(s,'Đậm: điểm tốt hơn cùng E/ngày; chưa tự là kết luận kiến trúc luôn thắng.',5.4,19,h=.5)
        band(s,'BSS âm: xác suất chưa tốt hơn khí hậu tham chiếu trong phép chấm này.')

    s=slide('E7: BSS và khoảng tin cậy 95%',note='Mỗi ôđiểmBSScùngCI95%môtả,20000bootstrappairedkhốibảyngày. Cóđộnhạy14ngàytrongCSV/Excel. CInằmtrên0hỗtrợskilldươngmôtả; chứa0chưaphânbiệtrõ. E7ngày1LGvàIFCItrên0,TFchứa0. Không dùng2CIgiao nhauđểthayCIchênhlệchmodel. CácCIchưa làholdout vàcóđiềukiệntrênmodelđãfit.',role='absolute_ci')
    rows=[]
    for model,label in zip(MODELS,LABELS):
        cells=[label]
        for day in [1,2,3]:
            r=absolute[(absolute.model==model)&(absolute.experiment=='E7')&(absolute.lead_day==day)&(absolute.block_days==7)].iloc[0]
            cells.append(signed(r.estimate)+'\n['+signed(r.ci_low)+'; '+signed(r.ci_high)+']')
        rows.append(cells)
    deck.table(s,['Mô hình','Ngày 1','Ngày 2','Ngày 3'],rows,y=1.6,row_h=.90,widths=[1.75,3.5,3.5,3.5],size=20,tag='absolute_ci')
    text(s,'Khoảng chứa 0: chưa phân biệt rõ với khí hậu trong phân tích này.',5.4,21,h=.5)
    band(s,'CI mô tả trên development; chưa bao trùm bất định nhãn hoặc toàn bộ huấn luyện.')

    s=slide('Thêm riêng A/M/C: điểm tăng đã đủ rõ chưa?',note='Ngày1ΔBSS củaE1/E2/E3soE0cùngmodel. Mđiểmtăngcảba .057/.008/.024nhưngCI95%đềuchứa0. NhữngCIởđâylà95%điểmchưahiệuchỉnh63phép. Tấ t cả nhóm/A/M/Cđượctrìnhbàytránhchọnôđẹp; khôngnóiđãchứngminhMchắcchắncảithiệnCPCngày1.',role='feature_ci')
    rows=[]
    for model,label in zip(MODELS,LABELS):
        cells=[label]
        for e in ['E1','E2','E3']:
            r=paired[(paired.kind=='feature')&(paired.model==model)&(paired.experiment==e)&(paired.lead_day==1)&(paired.metric=='BSS16')&(paired.block_days==7)].iloc[0]
            cells.append(signed(r.estimate)+'\n['+signed(r.ci_low)+'; '+signed(r.ci_high)+']')
        rows.append(cells)
    deck.table(s,['Mô hình','Thêm A','Thêm M','Thêm C'],rows,y=1.6,row_h=.9,widths=[1.75,3.5,3.5,3.5],size=20,tag='feature_ci')
    text(s,'Mỗi ô: ΔBSS ngày 1 so E0 và CI95% mô tả.',5.4,21,h=.5)
    band(s,'Thêm M tăng điểm, nhưng CI95% chứa 0 ở cả ba mô hình.')

    s=slide('Tốt hơn E0 chưa chắc đã vượt khí hậu',note='SoE6vE0ngày2. ChênhlệchBSSLG≈+.06976CIđiềuchỉnh63phéptrên0ởcả7/14ngày; BSS tuyệtđốiE6≈+.00186CI95%[-.05473,.05489]vẫnchứa0. TFT/IFcùngngàyvàEhiểnthịcạnhnhauđểgiữđủba. CIΔlàBonferroni63phép,CIabs95%môtả; khôngnóilàmộtloạiCI. LGE2ngày2chỉvượt0ởkhối7chưabền14. Đây làví dụđọckếtquảâm/trungtínhtrungthực.',role='relative_absolute')
    rows=[]
    for model,label in zip(MODELS,LABELS):
        c=paired[(paired.kind=='feature')&(paired.model==model)&(paired.experiment=='E6')&(paired.lead_day==2)&(paired.metric=='BSS16')&(paired.block_days==7)].iloc[0]
        a=absolute[(absolute.model==model)&(absolute.experiment=='E6')&(absolute.lead_day==2)&(absolute.block_days==7)].iloc[0]
        rows.append([label,fmt(get(model,'E0',2).BSS),fmt(get(model,'E6',2).BSS),
            signed(c.estimate)+'\n['+signed(c.ci_low_family63)+'; '+signed(c.ci_high_family63)+']',
            '['+signed(a.ci_low)+'; '+signed(a.ci_high)+']'])
    deck.table(s,['Mô hình','BSS E0','BSS E6','Δ E6−E0\nCI điều chỉnh 63 phép','BSS E6\nCI95% tuyệt đối'],rows,
        y=1.65,row_h=.90,widths=[1.7,1.3,1.3,4.0,3.95],size=18,tag='relative_absolute')
    text(s,'LightGBM E6 ngày 2: đã bớt sai so E0,\nnhưng BSS chỉ khoảng +0,002 và CI tuyệt đối vẫn chứa 0.',5.40,19,h=.65)
    band(s,'Hai câu hỏi khác nhau: hơn E0 chưa? Và hơn khí hậu chưa?')

    s=slide('Có thể kết luận đến đâu từ thí nghiệm này?',note='KếtluậntrongphạmviCPC/footprint/cấuhìnhđãfit: ngày1cótínhiệu,LGpipelineđiểmBSSngày1E7hơnhaimạngvàCIchênhlệch95%môtảtrên0. Mngày1CIchứ a0. Ngày2–3chưaxácnhậnhữuích. Khôngsuydữliệungàytốthơnsáugiờvìđổi4yếutố. Khôngnóidựbáomưathựctoànđịagiớichínhxác,khôngloạiTFT/Informerchung.',role='conclusions')
    deck.card(s,.65,1.7,5.95,3.65,'Có bằng chứng trong phạm vi này','Ngày 1 có tín hiệu dự đoán\nLightGBM E7 có BSS cao hơn hai mạng\nKhông phải mọi nhóm thêm đều có lợi',21)
    deck.card(s,6.8,1.7,5.9,3.65,'Còn phải kiểm chứng','Kỹ năng ở ngày 2–3\nMưa thực toàn địa giới\nHiệu quả riêng của bước ngày\nKhí tượng có sẵn tại mốc dự báo?',21)
    band(s,'Kết quả của một pipeline chưa là kết luận kiến trúc luôn thắng.')

    s=slide('Việc tiếp theo phục vụ mục tiêu nghiên cứu',note='Đãđủma trận,khôngcầnchạychỉđểđiềnE. ƯutiênVrain:tọađộ,chấtlượng,lịchsử,độphủđịahình,vùngcốđịnh,EOD; khôngthaytậptrạmtheongàylàmgiảbiếnđộng. Chuẩnhóaranh/trọngsố. Sauđócontrolled cadence sameCPCissue12mask so6h/day. Khóathiếtkếtrướcholdout2025,khôngtuningtheotest. NếuđềxuấtforecastNWP,phảicósẵntrướcissue,khôngERA5giờđích. Khôngtựchuyểnsangapp.',role='next_steps')
    text(s,'1. Khi có Vrain: kiểm tra lịch sử, tọa độ, chất lượng và độ phủ trạm.\n\n2. Chốt ranh/trọng số vùng và giờ tích lũy mưa.\n\n3. Muốn đo riêng bước ngày: so 6h/24h cùng nhãn CPC và cùng mẫu.\n\n4. Khóa thiết kế trước khi mở holdout 2025.',1.65,23,h=4.3)
    band(s,'Đã đủ 168 lượt; bước quan trọng tiếp theo là kiểm chứng dữ liệu và thiết kế.')
    assert len(deck.slides)==30

    # Full 72 rows / eight metrics, with all three models adjacent in every E.
    for day in [1,2,3]:
        for bi,exps in enumerate([['E0','E1','E2'],['E3','E4','E5'],['E6','E7']],1):
            s=slide(f'Ngày {day}: bảng đầy đủ {" / ".join(exps)}','PHỤ LỤC · TRA CỨU',
                'Mỗi E có đủ ba mô hình. Tám metrics lấy trực tiếp aggregate đã kiểm chứng. Đậm cùng E/ngày, Bias gần0, BSSâmđỏ. Đây làtoàn nămq16; chi tiếtmùa/năm/ngưỡngtrongExcel. Giữđủ72dòngchính=8E×3model×3day.',role=f'full_{day}_{bi}')
            rows=[];styles={}
            for ei,e in enumerate(exps):
                source_rows=[get(m,e,day) for m in MODELS]
                local=styles_for(source_rows,METRICS,start_col=2)
                for mi,(label,r) in enumerate(zip(LABELS,source_rows),1):
                    rows.append([e,label,*[fmt(r[k]) for k in METRICS]])
                    ri=ei*3+mi
                    for ci in range(10):styles[f'{ri},{ci}']=dict(fill='FFFFFF' if ei%2==0 else 'EDF2F7')
                for key,st in local.items():
                    ri,ci=map(int,key.split(','));styles[f'{ei*3+ri},{ci}'].update(st)
            deck.table(s,['E','Mô hình',*HEADERS],rows,y=1.65,row_h=.42,widths=[.6,1.65]+[1.25]*8,size=17,styles=styles,tag=f'full_{day}_{bi}')
            band(s,'Đậm: điểm tốt hơn trong cùng E/ngày; chưa tự là ý nghĩa thống kê.')

    s=slide('Nguồn nhãn và bằng chứng kiểm tra dữ liệu','PHỤ LỤC · NGUỒN',note='CPCREADME:resolution0.5°,gauge network density varies,EOD khácquốcgiavàmetadataunchecked. source_auditđủ3287 ngày9ô,13probesameNOAAbinary. GHCNDinventorychưacótạitrạmmớiphủtới2023gầnvùngngoài488550. station_eod_auditbổsung5nămnhưđãtrìnhbày. '+URLS['cpc']+' '+URLS['isd'],role='data_references')
    deck.table(s,['Nguồn','Điều cần kiểm tra'],[
        ['NOAA/CPC README','Lưới 0,5°, mật độ trạm và giờ kết thúc ngày'],['PSL + NOAA nhị phân','13 ngày probe khớp giá trị và đơn vị'],
        ['Danh mục GHCN-Daily','Chuỗi mưa hiện đại có thật sự phủ vùng không?'],['NOAA ISD gốc','Timestamp mưa tích lũy 24 giờ ở trạm']],y=1.55,row_h=.8,widths=[3.6,8.65],size=21,tag='data_references')
    band(s,'URL và nguồn chi tiết nằm trong ghi chú slide và tài liệu Word.')

    s=slide('Tài liệu mô hình và nghiên cứu theo ngày','PHỤ LỤC · NGUỒN',note='TFToriginalLim2021https://arxiv.org/abs/1912.09363; InformeroriginalZhou2021https://arxiv.org/abs/2012.07436; mô hìnhLGBMpaperKe2017NeurIPS. Đây lànguồnkiếntrúc; bảncủadựánthayđầura/loss/timefeatures,khôngreproducepaperbenchmark. Ví dụdailynghiêncứu: '+URLS['pham']+' '+URLS['iran']+' '+URLS['tft_daily'],role='model_references')
    deck.table(s,['Tài liệu','Cách sử dụng trong báo cáo'],[
        ['Lim và cs. · TFT','Cơ sở thiết kế nhiều hạn / lựa chọn biến'],['Zhou và cs. · Informer','Cơ sở encoder–decoder và ProbSparse'],
        ['Ke và cs. · LightGBM','Cơ sở thuật toán cây tăng cường'],['Các bài mưa ngày','Cơ sở thử bước ngày; không chuyển điểm paper sang dự án']],y=1.55,row_h=.8,widths=[3.6,8.65],size=21,tag='model_references')
    band(s,'Ba mô hình hiện là các pipeline đã điều chỉnh cho cùng bài toán vùng.')

    for groups,role in [(['B','A'],'variables_BA'),(['M','C'],'variables_MC')]:
        s=slide('Danh mục biến: '+ ' và '.join(groups),'PHỤ LỤC · ĐẶC TRƯNG',
            'Têncộtnguồntrongfeature_catalog_daily.csv. Mỗi biếnvậtlýlàmean__... sauarea mean theo giờvàmean24h. Lịchtsin_doy/cos_doyđược tính từtimestampkhôngtừkhítượngtươnglai. M20đếm6ở850,5ở500,shear,3IVT,VIMD,2context,2chênháp. CchỉSST.',role=role)
        rows=[]
        for g in groups:
            names=catalog[catalog.group==g].source_feature.tolist()
            rows.append([f'{g} — {len(names)} biến','; '.join(names)])
        deck.table(s,['Nhóm','Tên biến nguồn'],rows,y=1.55,row_h=1.42,widths=[2.5,9.75],size=19,tag=role)
        band(s,'Danh mục đủ 42 biến; không cộng thêm hai mã hóa giờ hằng.')

    s=slide('Kiểm chứng đã thực hiện đến mức nào?','PHỤ LỤC · KIỂM CHỨNG',note='Aggregatekhông phải sốgiả. validation.json:144NNcheckpoint,288đầuraLG,336split; train scalers/calibration/ensemble/scores reproduced;3mẫu504 giờ kiểmtra lại rawpredictor. Nămunittest mớiđạt. Bootstrap20000khối7/14mô tảvàfamily63. Đầytập2025khôngchấm, Vrainchưa nhận. Lượt nàychỉdựngslideđọcthốngkê,khôngfitmới/mởtest. NativeOfficerendernếuchưacókhônggọiđãkiểmquaOffice.',role='verification')
    deck.table(s,['Kiểm tra','Trạng thái'],[
        ['168 lượt mô hình/pipeline','Đã hoàn thành'],['144 checkpoint mạng + 288 đầu ra LightGBM','Đã phát lại độc lập'],
        ['336 split hiệu chỉnh/đánh giá','Chuẩn hóa, hiệu chỉnh và điểm số tái tạo đạt'],['Năm kiểm tra code dữ liệu/mạng mới','Đạt'],
        ['Test 2025 / dữ liệu Vrain','Chưa dùng trong huấn luyện và chấm']],y=1.55,row_h=.68,widths=[6.0,6.25],size=20,tag='verification')
    band(s,'Code chạy đúng chưa tự chứng minh nhãn đúng hoặc dự báo vận hành tốt.')
    assert len(deck.slides)==44
    apply_notes(deck.slides,roles)
    deck.save(OUT/(STEM+'.pptx'),OUT/(STEM+'.html'),OUT/'slide_scene.json')
    finalize_editable_tables(deck)
    write('LOI_DAN.md','# Lời dẫn và nguồn cho bộ slide dữ liệu ngày\n\n'+ '\n\n'.join(
        f"## Slide {s['number']}: {s['title']}\n\n{s['note']}" for s in deck.slides))
    write('README.md',f'''# Slide mới: ERA5 ngày → mưa CPC vùng 1–3 ngày

- [PowerPoint chỉnh sửa được, 44 slide]({STEM}.pptx).
- [HTML xem bằng trình duyệt]({STEM}.html), [lời dẫn từng slide](LOI_DAN.md).
- [Word và Excel 11 sheet của thí nghiệm](../daily_gauge_2026_11_04/README.md).

30 slide chính và 14 phụ lục. Bốn nhóm biến ở slide 10, E0–E7 ở 11, tám metrics ở 16; ba bảng BSS ở 20–22; E7 đủ metrics ở 23–25; khoảng tin cậy ở 26–28. Phụ lục 31–39 tra đủ 72 dòng E0–E7, luôn đủ ba mô hình cạnh nhau.

Gợi ý trình bày 12–15 phút: 1–3, 6–8, 10–11, 14–16, 20–22, 26–30. Các trang còn lại dùng giải thích khi cần. Đậm chỉ là điểm tốt hơn cùng E/ngày; đỏ là BSS âm. CPC là phân tích lưới từ trạm, footprint còn xấp xỉ, Vrain chưa có. Không dùng điểm khác nhãn so với bộ GSMaP trước để kết luận bước ngày tốt hơn.

Chỉ dựng báo cáo từ aggregate đã kiểm chứng; không train thêm hoặc mở 2025. Giữ nguyên các báo cáo đã công bố và slide người dùng chỉnh sửa. Tái lập: build_daily_gauge_slides.py → render_daily_gauge_slides.py → validate_daily_gauge_slides.py.
''')
    inputs=[DATA/n for n in ['publication_manifest.json','KET_QUA_72.csv','scores_pooled.csv','paired_bootstrap.csv',
        'absolute_bss_ci.csv','feature_catalog_daily.csv','cpc_spatial_support.csv','source_audit.json',
        'station_eod_audit.json','run.json','protocol_frozen.json','validation.json']]
    inputs.append(ROOT/'data/processed/regional_danang/cell_weights.parquet')
    inputs.append(ROOT/'scripts/daily_gauge_slide_notes.py')
    write('build_manifest.json',json.dumps(dict(status='complete',slides=44,main_slides=30,appendix_slides=14,
        roles=roles,complete_score_rows=72,models=MODELS,training_performed=False,test2025_read=False,
        code_sha256=sha(__file__),sources={p.relative_to(ROOT).as_posix():sha(p) for p in inputs},
        files={p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in OUT.iterdir() if p.is_file()
            and p.name not in ['build_manifest.json','render_manifest.json','validation.json','XEM_TRUOC.png']}),ensure_ascii=False,indent=2))
    print(json.dumps(dict(slides=44,main=30,appendix=14,roles=roles),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
