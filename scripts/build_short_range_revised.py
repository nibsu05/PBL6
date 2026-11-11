"""Revise the teaching deck with full tables, seed explanations and a matched pilot.

Reads prior published aggregates plus the new pilot report, not held-out data.
The original 34-slide deck and all earlier results remain unchanged.
"""
from pathlib import Path
import copy,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd
from presentation_layout import Deck,TEAL,RED,NAVY,MUTED
from build_final_regional_plan import word_copy

OUT=ROOT/'reports/short_range_revised_2026_10_21'
OLD=ROOT/'reports/short_range_presentation_2026_10_21'
MATRIX=ROOT/'reports/short_range_ablation_2026_10_21'
PILOT=ROOT/'reports/informer_regional_pilot_2026_10_21'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,value):(OUT/name).write_text(value,encoding='utf8',newline='\n')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    original=json.loads((OLD/'slide_scene.json').read_text(encoding='utf8'))
    pilot=json.loads((PILOT/'run.json').read_text(encoding='utf8'))
    assert pilot['status'] in ['complete','partial_time_budget'] and pilot['completed_seeds']
    scores=pd.read_csv(PILOT/'scores_pooled.csv');scores=scores[(scores.season=='all')&(scores.threshold_mm==16)]
    matrix=pd.read_csv(MATRIX/'scores_ensemble_pooled.csv')
    seeds=pd.read_csv(MATRIX/'scores_seed_pooled.csv')
    rules=pd.read_csv(OUT/'DECISION_RULES_E7.csv')
    sources=json.loads((OUT/'POD_SOURCES.json').read_text(encoding='utf8'))
    deck=Deck();register={}
    def reuse(number,section=None):
        sl=copy.deepcopy(original[number-1]);deck.slides.append(sl)
        if section:sl['section']=section
        return sl
    def new(title,note,source='',section='GIẢI THÍCH VÀ KẾT QUẢ'):
        return deck.slide(title,section,source,note)
    def text(s,x,y,w,h,t,size=21,bold=False,color=NAVY):deck.text(s,x,y,w,h,t,size,bold,color)
    def mainnote(s,value):s['note']=value
    def mark(role,s):register[role]=s

    s=reuse(1)
    for sh in s['shapes']:
        if sh.get('kind')=='text' and '24 slide chính' in sh.get('text',''):
            sh['text']='Lộ trình: mục tiêu → dữ liệu → cách thử → mô hình → chỉ số → kết quả'
    s['note']='Bản này trình bày theo cách giải thích trong cuộc trao đổi: định nghĩa trước, ví dụ cụ thể rồi mới đọc kết quả. Có bảng nhóm biến và bảng metrics đầy đủ, giải thích 3 seed, kiểm chứng nhận định POD 0,4 và pilot Informer cùng dữ liệu. Các kết quả chính vẫn là tập phát triển 2021–2023; năm 2025 chưa mở.'
    reuse(2);reuse(3);reuse(4)

    s=new('Bốn nhóm biến: bao gồm những thông tin gì?',
          'Đọc B là thông tin nền gần mặt đất và lịch; A bổ sung điều kiện đối lưu/mây/lớp biên/đất; M bổ sung hoàn lưu và dòng ẩm trên cao; C bổ sung nhiệt độ biển. Đây là bảng mô tả đầy đủ theo yêu cầu, còn tên 44 cột ở phụ lục. A/M cũng có các thông tin liên quan độ ẩm nên không độc lập hoàn toàn; không lặp cột không có nghĩa không tương quan. SST hiện chỉ một biến vùng biển, chưa phải cả ENSO/MJO.',
          'Nguồn: feature_groups.json và feature_catalog.csv • Số biến là số cột gốc, không phải số nguồn độc lập')
    group_rows=[
        ['B — Nền','11','Nhiệt độ, điểm sương, độ ẩm gần mặt đất; áp suất bề mặt và mực biển; hai thành phần gió 10 m; bốn biến mã hóa giờ và ngày trong năm'],
        ['A — Đối lưu, mây, lớp biên, đất','12','CAPE, CIN, has_lfc, hơi nước cột TCWV, K-index, Total Totals, độ cao lớp biên, bốn loại độ che phủ mây và độ ẩm đất lớp 1'],
        ['M — Hoàn lưu và vận chuyển ẩm','20','Gió, độ ẩm, nhiệt độ, chuyển động thẳng đứng ở 850/500 hPa; đứt gió; dòng vận chuyển ẩm IVT; phân kỳ dòng ẩm; bối cảnh hơi nước/dòng ẩm; hai biến chênh áp'],
        ['C — Nhiệt độ biển','1','SST trung bình tại hộp biển đã chọn']]
    deck.table(s,['Nhóm','Số biến','Bao gồm những thông tin gì?'],group_rows,y=1.46,row_h=1.035,
               widths=[3.15,1.0,8.1],size=17.2,styles={f'{r},1':{'bold':True,'color':TEAL} for r in range(1,5)},tag='groups_complete')
    mark('groups',s);reuse(6)

    s=new('3 seed = train cùng một cấu hình 3 lần',
          'Một mạng neural bắt đầu từ các trọng số ngẫu nhiên, thứ tự lấy mẫu và các thao tác ngẫu nhiên trong huấn luyện. Seed là số đặt trạng thái ngẫu nhiên để quản lý các lần chạy. Seed42/43/44 là ba nhãn đã chọn trước, không phải năm dữ liệu hay ba tỉnh. Mỗi lần vẫn dùng cùng dữ liệu, nhóm biến và cấu hình. Chạy ba lần giúp kiểm tra kết quả có quá phụ thuộc một khởi tạo may mắn không. Ví dụ 9,12,15mm là minh họa cách trung bình dự đoán, không phải kết quả thật.',
          'Seed dùng trong ma trận TFT: 42, 43, 44 • Không tạo thêm dữ liệu thời tiết')
    deck.table(s,['Lần train','Giữ nguyên','Thay đổi ngẫu nhiên'],[
        ['Seed 42','Dữ liệu, nhãn, nhóm biến, cấu hình','Khởi tạo mạng, thứ tự mẫu…'],
        ['Seed 43','Dữ liệu, nhãn, nhóm biến, cấu hình','Khởi tạo mạng, thứ tự mẫu…'],
        ['Seed 44','Dữ liệu, nhãn, nhóm biến, cấu hình','Khởi tạo mạng, thứ tự mẫu…']],row_h=.72,widths=[2.2,5.35,4.7],size=21)
    text(s,.75,4.78,11.85,1.0,'Ví dụ minh họa: cùng một ngày, ba lần dự đoán 9, 12, 15 mm.\nLấy trung bình dự đoán → **12 mm**; không chọn lần có điểm đẹp nhất.',22)
    deck.band(s,'Kết quả TFT đang báo là trung bình dự đoán ba seed; metric được tính lại sau đó.',size=18.5)
    mark('seeds',s)

    s=new('3 ngày, 3 seed và 3 lượt chia thời gian khác nhau',
          'Ba ngày là ba đầu ra của một mô hình tại một lần dự báo. Ba seed là ba lần huấn luyện cùng cấu hình. Ba lượt chia thời gian là ba đợt đánh giá trên các năm 2021/2022/2023, với tập huấn luyện và hiệu chỉnh riêng của từng đợt. Vì thế mỗi E có 3×3=9 lượt TFT, tám E có 72 lượt. LightGBM hiện chạy xác định nên có 3 lượt mỗi E. Thêm seed không nhân ba số ngày mưa độc lập.',
          'Mỗi ngày dự đoán vẫn có 1.075 mốc đánh giá; không biến thành 3.225 ngày độc lập')
    deck.table(s,['Số “3” nào?','Ý nghĩa'],[
        ['3 ngày dự đoán','Một mô hình trả lượng mưa ngày 1, ngày 2 và ngày 3'],
        ['3 seed','Cùng cấu hình train ba lần: seed 42, 43, 44'],
        ['3 lượt chia thời gian','Lần lượt đánh giá năm 2021, 2022 và 2023']],row_h=.82,widths=[3.7,8.55],size=22)
    text(s,.75,5.10,11.85,.95,'Mỗi E: 3 seed × 3 lượt chia = **9 lượt TFT**.\nTám E: 8 × 9 = **72 lượt TFT**; LightGBM có **24 pipeline**.',23)
    mark('three_threes',s)

    s=reuse(7)
    for sh in s['shapes']:
        if sh.get('kind')!='text':continue
        value=sh.get('text','')
        value=value.replace('Informer: chưa có kết luận','Informer: đã thử pilot vùng')
        value=value.replace('Chưa chạy cùng giao thức vùng','Đã thử E0/E7 cùng dữ liệu vùng')
        value=value.replace('Chưa có phép so Informer cùng giao thức','Pilot cùng dữ liệu; chưa đủ ma trận')
        sh['text']=value
    s['note']='TFT được thử vì có thiết kế cho nhiều nhóm biến và nhiều hạn. Informer là mô hình attention tối ưu cho chuỗi dài. Lần này đã có pilot riêng E0/E7 trên cùng dữ liệu vùng, nhãn, lịch sử, đầu ra và cách chấm. Bản này vẫn là adaptation: giữ backbone ProbSparse/encoder-distilling/decoder, thêm đầu ngày Tweedie/BCE. Chưa phải tái lập toàn bộ paper hoặc tìm cấu hình tối ưu cho Informer. Không lấy R² từ dữ liệu điểm cũ để loại nó.'
    reuse(8);reuse(9);reuse(11)

    s=new('Bảng metrics: ý nghĩa, vì sao dùng và chiều tốt',
          'Đọc từng hàng để biết con số đang đo lượng mưa, xác suất hay quyết định. RMSE/MAE/Bias có đơn vị mm/24h. BS là sai số xác suất, BSS là cải thiện BS so khí hậu. CSI/POD/FAR lấy từ số trúng, bỏ sót và báo nhầm. Không so các con số khác đơn vị với nhau. POD cao cần xem FAR; BSS cao chưa tự suy ra lượng mm tốt. Các ví dụ tính cụ thể ở các slide ngay sau.',
          'H: báo trúng · M: bỏ sót · F: báo nhầm • RMSE/MAE/Bias: mm/24h; các chỉ số còn lại không có đơn vị mm')
    metric_rows=[
        ['RMSE','Sai số lượng mưa, phạt mạnh lỗi lớn','Không để những ngày dự đoán sai nặng bị che khuất','Nhỏ hơn'],
        ['MAE','Trung bình sai lệch tuyệt đối bao nhiêu mm','Dễ đọc mức sai số lượng mưa','Nhỏ hơn'],
        ['Bias','Trung bình dự báo thừa hay thiếu','Phát hiện xu hướng dự báo thiếu hoặc thừa mưa','Gần 0'],
        ['BS','Sai số của xác suất dự báo','Chấm toàn bộ xác suất, chưa cần chọn ngưỡng báo có/không','Nhỏ hơn'],
        ['BSS','BS cải thiện bao nhiêu so với khí hậu tham chiếu','Kiểm tra có hơn cách dự báo theo mùa đơn giản không','Lớn hơn'],
        ['CSI','H / (H + M + F)','Cân nhắc đồng thời báo trúng, bỏ sót và báo nhầm','Lớn hơn'],
        ['POD','H / (H + M)','Bắt được bao nhiêu sự kiện thực tế','Lớn hơn'],
        ['FAR','F / (H + F)','Trong các lần báo có, bao nhiêu lần bị nhầm','Nhỏ hơn']]
    deck.table(s,['Chỉ số','Ý nghĩa dễ hiểu','Vì sao dùng?','Chiều tốt'],metric_rows,y=1.52,row_h=.565,
               widths=[1.0,4.15,5.25,1.85],size=16.6,
               styles={f'{r},0':{'bold':True} for r in range(1,9)},tag='metrics_complete')
    mark('metrics',s)
    reuse(12);reuse(13);reuse(14)

    s=new('POD = 0,4 có tự động được coi là tốt không?',
          'POD 0,4 nghĩa là bắt 40 trong 100 sự kiện thực. Ví dụ tự tạo 300 ngày có 100 sự kiện: A và B cùng trúng 40, bỏ sót 60 nhưng A báo nhầm 10 và B báo nhầm 160. Cùng POD 0,4 nhưng FAR và CSI rất khác. Vì vậy không có kết luận tốt chỉ từ số 0,4. Trong bài toán khó, mức này có thể hữu ích nếu hơn đối chứng và đáp ứng đánh đổi báo nhầm; cần ngữ cảnh trước khi kết luận.',
          'Ví dụ tự tạo: 300 ngày, 100 sự kiện • Hướng dẫn: JWGFVR Forecast Verification [V3]')
    deck.table(s,['Ví dụ','Trúng','Bỏ sót','Báo nhầm','POD ↑','FAR ↓','CSI ↑'],[
        ['A','40','60','10','0,400','0,200','0,364'],
        ['B','40','60','160','0,400','0,800','0,154']],row_h=.8,
        widths=[2.5,1.5,1.5,1.5,1.75,1.75,1.75],size=22,
        styles={'1,4':{'bold':True},'2,4':{'bold':True},'1,5':{'bold':True,'color':TEAL},'2,5':{'bold':True,'color':RED}})
    text(s,.75,4.45,11.85,1.15,'Cùng bắt **40/100 sự kiện**, nhưng số báo nhầm rất khác.\nMuốn đánh giá tốt hay chưa: xem FAR, CSI và mô hình đối chứng.',24)
    deck.band(s,'0,4 là mức phát hiện 40%; chưa phải một “tem đạt chuẩn” cho mọi nghiên cứu.',color=RED,size=18.8)
    mark('pod_04',s)

    s=new('Paper có POD khoảng 0,4: phải đọc trong ngữ cảnh',
          'P1 nghiên cứu IFS/WRF trên Việt Nam, phần 4.3 bàn ngưỡng 25 mm/24h. Có mô tả POD 0,3–0,4 trong bản đồ, nhưng cũng có trạm vùng R6 đạt 0,5–0,7. Không có phát biểu 0,4 là chuẩn chung. P2 là đánh giá ước lượng IMERG theo giờ, nơi POD tối đa 0,4 cùng FAR tối thiểu 0,6 được tác giả nhận xét phát hiện thấp. Dùng hai nguồn để kiểm tra cách diễn giải, không xếp hạng dự án tốt hơn hai bài. Ngưỡng, không gian, nhãn và quy tắc của dự án khác.',
          'Nguồn sơ cấp: [P1] Atmosphere 2025, 16, 224, §4.3 • [P2] Remote Sensing 2022, 14, 928, đánh giá giờ')
    deck.table(s,['Nguồn','Điểm cần đọc','Không được suy ra'],[
        ['P1 · Việt Nam\nIFS/WRF · 2025','Có POD khoảng 0,3–0,4;\nmột số trạm đạt 0,5–0,7','POD 0,4 là chuẩn chung;\ndự án POD 0,64 đã thắng paper'],
        ['P2 · IMERG\nBắc Trung Quốc · 2022','POD tối đa ≈0,4 cùng FAR ≥0,6;\ntác giả nhận xét phát hiện thấp','Chỉ nhìn POD 0,4\nlà đủ để gọi kết quả tốt']],
        row_h=1.13,widths=[3.1,4.8,4.35],size=20)
    text(s,.75,5.35,11.85,.55,'Cần cùng: hạn, ngưỡng mưa, không gian, nhãn, cách báo có và tập đánh giá.',20,True)
    deck.band(s,'Điểm POD trong paper khác giao thức không phải mốc chuẩn để xếp hạng trực tiếp.',size=18)
    mark('pod_sources',s)
    reuse(15);reuse(16);reuse(17);reuse(18)

    s=new('Vì sao POD trên slide lên 0,640? Hai cách báo khác nhau',
          'Cùng dự đoán E7 ngày 1 và cùng 114 sự kiện. Nếu báo có khi lượng mm dự đoán ≥16, TFT trúng 67 và báo nhầm 48, POD 0,588. Nếu dùng đầu xác suất ≥tau đã chọn trên tập hiệu chỉnh, TFT trúng 73 và báo nhầm 66, POD 0,640. Con số 0,640 đúng với quy tắc thứ hai; chưa đồng nghĩa tốt hơn chỉ vì cao hơn. Đây là chẩn đoán bổ sung trên dự đoán đã có, không chọn lại ngưỡng từ tập đánh giá và không thay chỉ số chính.',
          'Cùng TFT E7, ngày 1, 1.075 mốc /114 sự kiện • DECISION_RULES_E7.csv • Không đổi ngưỡng trên evaluation')
    rr=rules[(rules.model=='tft')&(rules.lead_day==1)]
    rows=[]
    for rule,label in [('amount','Lượng mm dự đoán ≥16'),('probability','Xác suất ≥τ đã chọn')]:
        r=rr[rr.rule==rule].iloc[0]
        rows.append([label,int(r.hits),int(r.false_alarm),f'{r.POD:.3f}',f'{r.FAR:.3f}',f'{r.CSI:.3f}'])
    deck.table(s,['Quy tắc báo có','Trúng','Báo nhầm','POD ↑','FAR ↓','CSI ↑'],rows,row_h=.86,
               widths=[4.30,1.35,1.65,1.65,1.65,1.65],size=22,
               styles={'1,3':{'bold':True},'2,3':{'bold':True},'2,2':{'bold':True}},tag='rule_comparison')
    text(s,.75,4.55,11.85,1.05,'Đầu xác suất bắt được nhiều sự kiện hơn, đồng thời báo nhầm nhiều hơn.\nKhông so POD này với paper dùng lượng mm mà bỏ qua khác biệt quy tắc.',22)
    deck.band(s,'POD 0,640 = 73/114, không phải “độ chính xác chung 64%”.',size=20)
    mark('rules',s)
    reuse(19)

    s=new('Đọc đủ POD, FAR, CSI và BSS: E7 ở ba ngày',
          'POD cho tỷ lệ bắt được, FAR cho tỷ lệ báo nhầm trong các lần báo có; CSI tóm tắt ba số đếm; BSS đánh giá xác suất so khí hậu. Ngày 3 vẫn có POD 0,412 ở TFT nhưng FAR 0,719 và BSS âm. Đây là lý do không gọi dự báo tốt từ một POD riêng. Số in đậm là điểm tốt hơn trong cặp mô hình cùng ngày, chưa là kiểm định thống kê; các ngưỡng tau được chọn riêng trên tập hiệu chỉnh.',
          'Ngưỡng mưa vùng ≥16 mm/24h; quyết định từ xác suất • In đậm theo cặp cùng ngày; chưa là ý nghĩa thống kê')
    oldtable=next(sh for sh in original[19]['shapes'] if sh.get('tag')=='e7_decisions')
    deck.table(s,['Ngày','Mô hình','POD ↑','FAR ↓','CSI ↑','BSS ↑'],oldtable['rows'],
               row_h=.62,widths=[.8,2.25,2.3,2.3,2.3,2.3],size=23,styles=oldtable['styles'],tag='e7_decisions')
    deck.band(s,'Ngày 3: POD còn >0,4 nhưng FAR cao và BSS âm; chưa vượt khí hậu về xác suất.',color=RED,size=18.5)
    reuse(21)

    s=new('Informer: đã chạy được; kết quả pilot cần đọc thế nào?',
          'Pilot đã khóa cấu hình trước khi huấn luyện, chỉ E0/E7, ba lượt chia 2021–2023 và cùng tập seed hoàn thành với TFT. Cùng dữ liệu vùng, nhãn, mẫu, lịch sử 168h gộp 6h, đầu ra ba tổng 24h, loss Tweedie/BCE, cách hiệu chỉnh và chọn ngưỡng. Informer là bản điều chỉnh gọn: hidden 32, heads 4, hai encoder có distilling và một decoder. Chưa tuning hoặc chạy E1–E6. Bảng là điểm phát triển; chưa kiểm định khác biệt kiến trúc từ các điểm này, không lấy R² cũ để kết luận.',
          'E7 · Cùng seed TFT/Informer · Đậm: điểm tốt hơn trong cặp; chưa kiểm định khác biệt kiến trúc')
    irows=[];styles={}
    for day in [1,2,3]:
        for model,label in [('tft','TFT'),('informer','Informer')]:
            r=scores[(scores.model==model)&(scores.experiment=='E7')&(scores.lead_day==day)].iloc[0]
            irows.append([str(day),label,*[f'{r[k]:.3f}' for k in ['RMSE','BSS','CSI','POD','FAR']]])
        for col,key in enumerate(['RMSE','BSS','CSI','POD','FAR'],2):
            vals=[float(irows[-2][col]),float(irows[-1][col])];goal=min(vals) if key in ['RMSE','FAR'] else max(vals)
            for j,v in enumerate(vals):styles[f'{day*2-1+j},{col}']={'bold':v==goal,'color':RED if key=='BSS' and v<0 else TEAL if v==goal else NAVY}
    deck.table(s,['Ngày','Mô hình','RMSE ↓','BSS ↑','CSI ↑','POD ↑','FAR ↓'],irows,row_h=.59,
               widths=[.85,2.05,1.87,1.87,1.87,1.87,1.87],size=21,styles=styles,tag='informer_matched')
    deck.band(s,f"{len(pilot['models'])} lượt Informer · {len(pilot['completed_seeds'])} seed hoàn chỉnh · {pilot['elapsed_seconds']/60:.1f} phút · E0/E7; chưa tuning",size=19)
    mark('informer',s)

    s=new('Nhóm nào cải thiện? Đọc điểm cùng khoảng tin cậy',
          'Hiệu số ở đây là BSS khi thêm nhóm trừ BSS nền. Khoảng tin cậy cho thấy mức dao động hiệu số khi lấy mẫu lại các đợt ngày trên chính tập phát triển. Nếu toàn khoảng trên 0 thì phép thử ủng hộ cải thiện; nếu chứa 0 thì chưa phân biệt chắc. Hai nhóm A/M ngày 1 có khoảng điều chỉnh trên 0, SST chưa có. Chưa suy ra M chắc chắn hơn A vì chưa kiểm định trực tiếp; chưa suy ra đã thắng năm 2025.',
          'TFT • Thêm riêng từng nhóm vào E0, ngày 1 • 20.000 bootstrap khối 7 ngày • Điều chỉnh gia đình 9 phép so')
    cis=pd.read_csv(MATRIX/'paired_bootstrap.csv');cr=[]
    for exp,label in [('E1','A: đối lưu, mây, lớp biên, đất'),('E2','M: hoàn lưu và vận chuyển ẩm'),('E3','C: SST vùng biển')]:
        r=cis[(cis.model=='tft')&(cis.contrast==exp+'-E0')&(cis.lead_day==1)&(cis.metric=='BSS16')&(cis.block_days==7)].iloc[0]
        cr.append([label,f'{r.estimate:+.3f}',f'[{r.family_adjusted_low:+.3f}; {r.family_adjusted_high:+.3f}]','Trên 0' if r.family_adjusted_low>0 else 'Chứa 0'])
    deck.table(s,['Nhóm thêm vào nền','Δ BSS ↑','Khoảng tin cậy','Cách đọc'],cr,row_h=.82,
               widths=[5.0,1.55,3.35,2.35],size=20,
               styles={f'{r},{c}':{'bold':True,'color':TEAL} for r in [1,2] for c in [1,2,3]},tag='feature_ci')
    text(s,.75,5.12,11.85,.95,'Khoảng hoàn toàn trên 0: có tín hiệu cải thiện trong phép thử này.\nKhoảng chứa 0: chưa phân biệt chắc có lợi hay không.',22)
    reuse(23);reuse(24)
    main_count=len(deck.slides)

    # Technical audit is useful to look up, not a prerequisite for understanding.
    reuse(10,'PHỤ LỤC · ĐỐI CHIẾU NHÁNH DEV')
    for n in range(25,35):reuse(n)
    s=new('Nguồn kiểm chứng nhận định POD khoảng 0,4',
          'Nguồn P1 là bài gốc trên nhà xuất bản và bản lưu tại KIT. Không sao chép PDF vào Git. Nguồn P2 là ước lượng, không phải dự báo, được ghi đúng giới hạn. V3 là hướng dẫn nhóm kiểm chứng dự báo, không áp chuẩn 0,4 chung. A5 là mã attention tác giả để đối chiếu công thức queries trong subclass pilot mới.',
          'Không dùng điểm paper khác nhãn/ngưỡng/không gian để xếp hạng trực tiếp dự án',section='PHỤ LỤC · NGUỒN SƠ CẤP')
    for i,ref in enumerate(sources['sources']):
        y=1.55+i*1.20
        deck.text(s,.75,y,11.85,.37,f"{ref['id']} · {ref.get('year','')} · {ref.get('doi','Nguồn chính thức')}",17,True,TEAL,url=ref['url'])
        deck.text(s,.75,y+.39,11.85,.80,ref['title'],16.5,url=ref['url'])

    # Translate visible jargon and regenerate page numbers after reordering.
    for index,sl in enumerate(deck.slides,1):
        sl['number']=index
        for sh in sl['shapes']:
            if sh.get('kind')=='text':
                if abs(sh['x']-12.05)<.01 and abs(sh['y']-.18)<.01:sh['text']=f'{index:02d}'
                if abs(sh['x']-.55)<.01 and abs(sh['y']-.18)<.01:sh['text']=sl['section']
                for a,b in {'TFT ensemble 3 seed':'TFT · trung bình dự đoán 3 seed','mạng neural':'mạng học sâu',
                    'Development 2021–2023':'Đánh giá 2021–2023','development 2021–2023':'đánh giá 2021–2023',
                    'Development, chưa phải test 2025':'Đánh giá 2021–2023; chưa chấm 2025',
                    '3 ngày dự đoán khác nhau':'3 khoảng dự đoán khác nhau'}.items():sh['text']=sh['text'].replace(a,b)
            if sh.get('kind')=='table':
                sh['headers']=[str(v).replace('Model','Mô hình').replace('TFT N','TFT ').replace('LGBM N','LightGBM ') for v in sh['headers']]
        # Notes are prose, not executable source; repair compact Vietnamese text.
        note=sl['note']
        repairs={'ViệtNam':'Việt Nam','phần4.3':'phần 4.3','ngày1':'ngày 1','ngày3':'ngày 3',
            'E7ngày':'E7 ngày','cùng114':'cùng 114','TFTtrúng':'TFT trúng','vàbáonhầm':'và báo nhầm',
            'POD0,':'POD 0,','FAR0,':'FAR 0,','CSI0,':'CSI 0,','BSSâm':'BSS âm','tauđã':'tau đã',
            'seedhoànthành':'seed hoàn thành','3nhân3bằng9':'3 × 3 = 9','tám E có72':'tám E có 72',
            '100sự':'100 sự','40trong100':'40 trong 100','300ngày':'300 ngày','100sự':'100 sự',
            'A vàB':'A và B','trúng40':'trúng 40','sót60':'sót 60','nhầm10vàB':'nhầm 10 và B',
            'nhầm160':'nhầm 160','số0,4':'số 0,4','0,4nhưng':'0,4 nhưng','0,4là':'0,4 là',
            'ngưỡng25mm/24h':'ngưỡng 25 mm/24h','R6đạt':'R6 đạt','P2là':'P2 là','P1nghiên':'P1 nghiên',
            'mưa16':'mưa 16','PODcho':'POD cho','FARcho':'FAR cho','ởTFT':'ở TFT','CIđiều':'CI điều',
            'BSSthêm':'BSS thêm','trừBSSnền':'trừ BSS nền','Khoảngtin':'Khoảng tin','lấy mẫu lại cácđợtngày':'lấy mẫu lại các đợt ngày'}
        for a,b in repairs.items():note=note.replace(a,b)
        sl['note']=note
    deck.save(OUT/'PBL6_BAO_CAO_DE_HIEU.pptx',OUT/'PBL6_BAO_CAO_DE_HIEU.html',OUT/'slide_scene.json')
    roles={name:sl['number'] for name,sl in register.items()}
    write('LOI_DAN.md','# Lời dẫn bản sửa theo phản hồi\n\n'+
          '\n\n'.join(f"## Slide {sl['number']}: {sl['title']}\n\n{sl['note']}" for sl in deck.slides))
    doc=explanation(group_rows,metric_rows,pilot,rules,roles,sources)
    write('GIAI_THICH_THEO_CAU_HOI.md',doc);word_copy(OUT/'GIAI_THICH_THEO_CAU_HOI.md')
    write('README.md',f'''# Báo cáo sửa theo phản hồi: dễ hiểu, đủ bảng và pilot Informer

- [PowerPoint {len(deck.slides)} slide](PBL6_BAO_CAO_DE_HIEU.pptx), [HTML trình chiếu](PBL6_BAO_CAO_DE_HIEU.html).
- [Giải thích Word](GIAI_THICH_THEO_CAU_HOI.docx), [Markdown](GIAI_THICH_THEO_CAU_HOI.md), [lời dẫn](LOI_DAN.md).
- [Kết quả pilot Informer và protocol](../informer_regional_pilot_2026_10_21/run.json), [bảng cùng seed TFT/Informer](../informer_regional_pilot_2026_10_21/scores_pooled.csv).
- [Bảng đối chiếu quy tắc báo mưa](DECISION_RULES_E7.csv), [nguồn kiểm chứng POD](POD_SOURCES.json).
- [Excel đầy đủ E0–E7 và Word trước](../short_range_explained_2026_10_21/README.md).

Có {main_count} slide chính và {len(deck.slides)-main_count} slide tra cứu. Bảng nhóm biến ở slide {roles['groups']}; seed ở {roles['seeds']}–{roles['three_threes']}; bảng metrics đầy đủ ở {roles['metrics']}; POD0,4 ở {roles['pod_04']}–{roles['pod_sources']}; hai quy tắc POD ở {roles['rules']}; Informer ở {roles['informer']}. Không phải đọc mã mới hiểu phần chính. Chữ đậm có chú thích theo phép so; không tự là ý nghĩa thống kê.

Đây là phát triển trên vùng 93 ô xấp xỉ. Informer chỉ thử E0/E7 với cùng seed hoàn chỉnh và các điều kiện đã đăng ký, chưa tuning hoặc chạy đủ E0–E7. Giữ nguyên kết quả cũ; không chấm 2025. Raw data/checkpoint/dự đoán từng mốc ở data/operational ngoài Git.

Tái lập slide: `python scripts/build_short_range_revised.py`; cần kết quả pilot đã hoàn thành và bảng quy tắc tổng hợp. Bộ slide 34 trang trước giữ nguyên để đối chiếu.
''')
    manifest=dict(status='complete',slides=len(deck.slides),main_slides=main_count,roles=roles,test2025_read=False,
        informer_runs=len(pilot['models']),completed_seeds=pilot['completed_seeds'],code_sha256=sha(Path(__file__)),
        sources={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in [OLD/'slide_scene.json',MATRIX/'scores_ensemble_pooled.csv',
                 MATRIX/'scores_seed_pooled.csv',MATRIX/'paired_bootstrap.csv',PILOT/'run.json',PILOT/'scores_pooled.csv',OUT/'DECISION_RULES_E7.csv',OUT/'POD_SOURCES.json']})
    manifest['files']={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in OUT.iterdir()
                       if p.is_file() and p.name not in ['build_manifest.json','render_manifest.json','validation.json','XEM_TRUOC.png']}
    write('build_manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    print('REVISED_COMPLETE',len(deck.slides),'slides',roles)


def explanation(groups,metrics,pilot,rules,roles,sources):
    def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(str(v) for v in row)+' |' for row in rows])
    text=f'''# Giải thích lại theo các câu hỏi của nhóm

## 1. Bốn nhóm biến gồm những gì?

{table(['Nhóm','Số biến','Thông tin'],groups)}

E0 chỉ B; E1 B+A; E2 B+M; E3 B+C; E4 B+A+M; E5 B+A+C; E6 B+M+C; E7 B+A+M+C. E0–E7 là tám bộ đầu vào, không phải tám mô hình. TFT/LightGBM là các cách học từ từng bộ đầu vào. Nhóm C hiện chỉ một biến SST, chưa đại diện đầy đủ ENSO/MJO.

## 2. Bảng metrics đầy đủ

{table(['Chỉ số','Ý nghĩa dễ hiểu','Vì sao dùng?','Chiều tốt'],metrics)}

H là số báo trúng; M bỏ sót; F báo nhầm. Sai số lượng mm, sai số xác suất và chất lượng quyết định là ba câu hỏi khác nhau. Giữ BSS/CSI theo protocol hiện tại, đồng thời phải đọc đủ POD/FAR và RMSE/MAE/Bias. Nếu muốn chọn mô hình chính theo lượng mm, cần khóa mục tiêu trước holdout, không đổi chỉ vì một bảng đang đẹp hơn.

## 3. 3 seed là gì?

Seed42/43/44 là ba trạng thái ngẫu nhiên cho ba lần train cùng dữ liệu, nhãn, nhóm biến, cấu hình. Chúng thay đổi khởi tạo, thứ tự đưa mẫu và thao tác ngẫu nhiên. Mục đích là thấy kết quả có phụ thuộc mạnh vào một lần khởi tạo không; chúng không tạo thêm ngày thời tiết.

Ví dụ minh họa: cùng ngày, ba model trả 9,12,15mm; dự đoán trung bình là12mm. Kết quả TFT đang báo dùng trung bình lượng mm và xác suất đã hiệu chỉnh của ba seed, sau đó tính metric; không lấy trung bình ba giá trị BSS/CSI để thay metric của dự đoán trung bình. Ngưỡng quyết định cho dự đoán trung bình chọn trên calibration.

Ba ngày là ba đầu ra; ba seed là ba lần train cùng cấu hình; ba lượt chia thời gian đánh giá lần lượt2021/2022/2023. Một E có3×3=9lượt TFT, tám E có72lượt; số mốc chấm mỗi lead vẫn1075. LightGBM cấu hình hiện tại chạy xác định nên không nhân ba bản giống nhau.

## 4. POD0,4 có phải là tốt?

POD0,4 nghĩa là bắt40/100sự kiện. Không tìm thấy một chuẩn chung0,4 trong hướng dẫn/nguồn đã đối chiếu. POD bỏ qua báo nhầm nên phải đọc cùng FAR/CSI, số sự kiện và baseline. Ví dụ300ngày/100sự kiện: cùngH40/M60, F10cho FAR0,2/CSI0,364; F160cho FAR0,8/CSI0,154. CùngPOD0,4nhưng hiệu quả rất khác.

Nguồn P1 tại ViệtNam có POD0,3–0,4 trong bản đồ ngưỡng25mm/24h và có trạm0,5–0,7; không phát biểu0,4làchuẩn. NguồnP2 đánh giá ước lượng IMERG theo giờ, PODtối đa0,4 đi với FARtối thiểu0,6 lại được nhận xét phát hiện thấp. Hai ngữ cảnh không tương đương nhau hoặc tương đương dự án; chúng bác bỏ việc diễn giải chỉ từ một mốc số.

POD0,640trong TFT E7ngày1là73/114 sự kiện vùng≥16mm/24h, theo đầu xác suất vớiτcalibration. Nó không phải độ chính xác chung64%. Không suy ra đã hơn paper dùng trạm, ngưỡng25/50/100, forecast số, nhãn trạm hoặc quy tắc trực tiếp từ lượngmm.

## 5. Cùng mô hình, khác quy tắc thì POD thay đổi ra sao?

'''
    rows=[]
    for r in rules[(rules.model=='tft')&(rules.lead_day==1)].itertuples():rows.append([r.rule,r.hits,r.miss,r.false_alarm,f'{r.POD:.3f}',f'{r.FAR:.3f}',f'{r.CSI:.3f}'])
    text+=table(['Quy tắc','Trúng','Bỏ sót','Báo nhầm','POD','FAR','CSI'],rows)
    text+=f'''

amount là lượng dự đoán≥16mm; probability là xác suất≥τ đã chọn trên calibration. Đây là chẩn đoán bổ sung từ dự đoán đã có, không fit/chọn lại ngưỡng evaluation hoặc thay chỉ số chính. Bảng có đủ ba ngày/hai mô hình ở DECISION_RULES_E7.csv.

## 6. Informer có kịp và khả thi không?

Đã hoàn thành {len(pilot['models'])} lượt, seed hoàn chỉnh {pilot['completed_seeds']}, khoảng {pilot['elapsed_seconds']/60:.2f} phút tiến trình. Pilot chỉ E0/E7, không phải đủ E0–E7. So TFT trên đúng cùng seed, nhãn, mẫu, lịch sử28bước6h, lịch tương lai, đầu ra3ngày, lossTweedie/BCE và cách calibration. Dữ liệu vẫn chỉ2015–2023, không mở2025.

Bản Informer là adaptation nhỏ hidden32/heads4, hai encoder có distilling, một decoder; daily heads thay đầu benchmark gốc. Subclass mới sửa số query sparse theo công thức tác giả, cố định lấy mẫu keys lúc eval để replay ổn định; không sửa mã Informer cũ. Decoder prefix lấy khí tượng quá khứ, phần khí tượng tương lai bằng0, calendar tương lai đã biết. Cùng hidden không có nghĩa cùng số tham số; không tuning riêng hoặc có kiểm định kiến trúc đầy đủ. Chạy được không tự chứng minh dự đoán tốt, điểm đẹp hơn chưa đủ khẳng định thuật toán hơn mọi cấu hình.

Nguồn số liệu trong bảng pilot: ../informer_regional_pilot_2026_10_21/scores_pooled.csv; run.json lưu protocol, epochs, thời gian, tham số, calibration và replay. Bảng slide dùng cùng tập seed với TFT để tránh so một lần Informer với ba lần TFT.

## 7. Nguồn POD và công thức Informer

'''
    text+='\n'.join(f"- [{r['id']}] [{r['title']}]({r['url']})." for r in sources['sources'])
    # Improve compact prose without altering source identifiers.
    pairs={'Seed42/43/44':'Seed 42/43/44','9,12,15mm':'9, 12, 15 mm','là12mm':'là 12 mm',
           'lần lượt2021':'lần lượt 2021','có3×3=9lượt':'có 3×3=9 lượt','có72lượt':'có 72 lượt','vẫn1075':'vẫn 1075',
           'POD0,':'POD 0,','40/100sự':'40/100 sự','chung0,4':'chung 0,4','Ví dụ300ngày/100sự':'Ví dụ 300 ngày/100 sự',
           'cùngH40/M60':'cùng H40/M60','F10cho':'F10 cho','F160cho':'F160 cho','FAR0,':'FAR 0,','CSI0,':'CSI 0,',
           'CùngPOD':'Cùng POD','0,4nhưng':'0,4 nhưng','ViệtNam':'Việt Nam','ngưỡng25mm/24h':'ngưỡng 25 mm/24h',
           'trạm0,':'trạm 0,','phát biểu0,4làchuẩn':'phát biểu 0,4 là chuẩn','NguồnP2':'Nguồn P2','PODtối':'POD tối',
           'FARtối':'FAR tối','E7ngày1là73/114':'E7 ngày 1 là 73/114','vùng≥16mm/24h':'vùng ≥16 mm/24h',
           'vớiτcalibration':'với τ calibration','chung64%':'chung 64%','lượngmm':'lượng mm','đoán≥16mm':'đoán ≥16 mm',
           'suất≥τ':'suất ≥τ','lịch sử28bước6h':'lịch sử 28 bước 6h','ra3ngày':'ra 3 ngày','lossTweedie':'loss Tweedie',
           'chỉ2015':'chỉ 2015','mở2025':'mở 2025','hidden32/heads4':'hidden 32/heads 4','bằng0':'bằng 0'}
    for a,b in pairs.items():text=text.replace(a,b)
    return text


if __name__=='__main__':main()
