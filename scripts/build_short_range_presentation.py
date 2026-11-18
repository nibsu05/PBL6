"""Build a sourced, editable teaching deck from audited development aggregates.

No model fitting, individual predictions or held-out observations are read.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from presentation_layout import Deck, NAVY, TEAL, RED, MUTED

SOURCE=ROOT/"reports/short_range_ablation_2026_10_21"
OUT=ROOT/"reports/short_range_presentation_2026_10_21"
GROUPS={"E0":"B","E1":"B+A","E2":"B+M","E3":"B+C","E4":"B+A+M",
        "E5":"B+A+C","E6":"B+M+C","E7":"B+A+M+C"}


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,value):
    (OUT/name).write_text(value,encoding="utf8",newline="\n")


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    run=json.loads((SOURCE/"run.json").read_text(encoding="utf8"))
    audit=json.loads((SOURCE/"checkpoint_audit.json").read_text(encoding="utf8"))
    assert run["status"]=="complete" and audit["full_runs_replayed"]==96
    assert not run["test2025_read"]
    scores=pd.read_csv(SOURCE/"scores_ensemble_pooled.csv")
    p=scores[(scores.season=="all")&(scores.threshold_mm==16)&scores.model.isin(["tft","lgbm"])].copy()
    assert len(p)==48 and (p.n==1075).all() and (p.events==114).all()
    ci=pd.read_csv(SOURCE/"paired_bootstrap.csv")
    catalog=pd.read_csv(SOURCE/"feature_catalog.csv")
    refs=json.loads((OUT/"literature.json").read_text(encoding="utf8"))["sources"]
    dev=json.loads((OUT/"dev_metrics_audit.json").read_text(encoding="utf8"))
    def row(m,e,d):return p[(p.model==m)&(p.experiment==e)&(p.lead_day==d)].iloc[0]
    def effect(e):return ci[(ci.model=="tft")&(ci.contrast==e+"-E0")&(ci.lead_day==1)&(ci.metric=="BSS16")&(ci.block_days==7)].iloc[0]
    counts=[]
    for r in p[p.experiment=="E7"].sort_values(["lead_day","model"]).itertuples():
        hits=round(r.POD*r.events);miss=int(r.events)-hits
        false=round(hits*r.FAR/(1-r.FAR));tn=int(r.n)-hits-miss-false
        assert abs(hits/(hits+miss)-r.POD)<1e-12
        assert abs(false/(hits+false)-r.FAR)<1e-12
        assert abs(hits/(hits+miss+false)-r.CSI)<1e-12
        counts.append(dict(model=r.model,lead_day=r.lead_day,n=int(r.n),events=int(r.events),
                           hits=hits,miss=miss,false_alarm=false,correct_nonevent=tn))
    pd.DataFrame(counts).to_csv(OUT/"E7_CONTINGENCY_COUNTS.csv",index=False,lineterminator="\n")
    # A performance diagram, not a ROC curve: horizontal axis uses 1-FAR, not FPR.
    fig,ax=plt.subplots(figsize=(5.3,4.5))
    a=np.linspace(.001,1,200);xx,yy=np.meshgrid(a,a)
    z=1/(1/xx+1/yy-1)
    contours=ax.contour(xx,yy,z,levels=[.1,.2,.3,.4,.5,.6,.7,.8],colors="#bdcbd5",linewidths=.8)
    ax.clabel(contours,fmt="%.1f",fontsize=8)
    for m,color in [("tft","#087E8B"),("lgbm","#B5682B")]:
        for day in [1,2,3]:
            r=row(m,"E7",day)
            ax.scatter(1-r.FAR,r.POD,c=color,s=75,marker="o" if m=="tft" else "s",zorder=4,
                       label=("TFT" if m=="tft" else "LightGBM") if day==1 else None)
            offset=(6,7) if m=="tft" and day!=3 else (6,-13)
            if m=="lgbm" and day==3:offset=(-13,6)
            ax.annotate(str(day),(1-r.FAR,r.POD),xytext=offset,textcoords="offset points",fontsize=10,color=color)
    ax.set(xlim=(0,1),ylim=(0,1),xlabel="1 − FAR: tỷ lệ báo đúng trong các lần báo có →",
           ylabel="POD: tỷ lệ bắt được sự kiện thực →",title="E7 · số 1/2/3 là ngày · đường xám là CSI")
    ax.legend(loc="upper left",frameon=False,fontsize=9)
    ax.grid(alpha=.15);fig.tight_layout();fig.savefig(OUT/"performance_E7.png",dpi=180);plt.close(fig)
    shutil.copyfile(ROOT/"reports/short_range_explained_2026_10_21/dinh_nghia_han_du_bao.png",OUT/"target_timeline.png")
    shutil.copyfile(SOURCE/"primary_family_ci.png",OUT/"primary_family_ci.png")
    deck=Deck()
    default="Nguồn dự án: scores_ensemble_pooled.csv • Ngưỡng 16 mm/24h • Development, chưa phải test 2025"
    def new(title,source="",note="",section="NỘI DUNG CHÍNH"):
        return deck.slide(title,section,source,note)
    def txt(s,x,y,w,h,t,size=21,bold=False,color=NAVY):return deck.text(s,x,y,w,h,t,size,bold,color)

    s=new("Đặc trưng nào giúp dự đoán mưa vùng?",note="Phần này nghiên cứu dữ liệu cho dự đoán trực tiếp lượng mưa trung bình vùng trong ba khoảng 24 giờ. Ba điều cần giữ: đã có đủ E0–E7; POD và FAR phải đọc cùng nhau; kết quả tích cực tập trung ở ngày 1, chưa chứng minh dự đoán tốt toàn bộ 72 giờ. Các slide phụ lục chứa đủ 48 dòng chính để kiểm tra. Đây là development, không phải kết quả test 2025.")
    txt(s,.65,1.63,12,1.0,"TFT và LightGBM · ngày 1, 2, 3\nBằng chứng, cách đọc chỉ số và giới hạn",26,True,TEAL)
    deck.card(s,.65,3.05,3.85,2.45,"Đã chạy đủ","72 lượt TFT\n24 pipeline LightGBM\n96/96 lượt tái lập",21)
    deck.card(s,4.72,3.05,3.85,2.45,"Cần đọc đủ","Lượng mưa: RMSE/MAE/Bias\nXác suất: BS/BSS\nSự kiện: CSI + POD + FAR",19)
    deck.card(s,8.79,3.05,3.85,2.45,"Kết quả trung thực","A/M có tín hiệu ngày 1\nNgày 3 chưa vượt khí hậu\nVùng/nhãn còn cần kiểm chứng",19)
    deck.band(s,"24 slide chính + 10 slide tra cứu • 21/10/2026 • Năm 2025 giữ kín",size=18)

    s=new("Đầu ra: ba tổng mưa 24 giờ riêng của cả vùng",note="Một lần phát hành lúc 07 giờ Việt Nam tạo ba số lượng mưa trung bình vùng. Ngày 1 là khoảng 0–24 giờ, ngày 2 là 24–48 giờ, ngày 3 là 48–72 giờ. Ví dụ 12, 35, 5 mm chỉ là minh họa. Không cộng 93 giá trị mm để làm nhãn vùng; lấy trung bình theo diện tích rồi cộng 24 giờ. Dự đoán một số trung bình vùng không suy ra tất cả xã hoặc ô đều nhận lượng mưa đó.")
    deck.image(s,OUT/"target_timeline.png",.55,1.65,12.25,3.16)
    txt(s,.75,5.02,11.85,.95,"Ví dụ minh họa: [12, 35, 5] mm/24h cho ba ngày.\nMột mẫu đại diện cho một mốc của vùng; không phải một ô.",22)
    deck.band(s,"Ngày 2/3 không phải tổng tích lũy 48/72 giờ; chưa có đầu ra từng giờ.",size=19)

    s=new("Dữ liệu: ERA5 làm đầu vào, GSMaP Gauge làm nhãn",note="Đầu vào gồm khí tượng quá khứ từ ERA5 và đại lượng suy ra; lịch được tính từ timestamp. Nhãn là y_region_gc_mm từ GSMaP Gauge, tổng hợp theo diện tích các ô rồi cộng 24 giờ. Mưa ERA5 không phải nhãn trong nhánh ngày. Độ đầy đủ hoặc checksum không bảo đảm biến khí tượng hay nhãn vệ tinh chính xác về vật lý. Các biến SST/bối cảnh/chênh áp có hỗ trợ không gian riêng theo mã dựng nguồn, không phải mọi trường đều là 93 phép đo độc lập.")
    deck.card(s,.65,1.65,6,3.67,"Đầu vào trước giờ phát hành","Nhiệt độ, ẩm, gió, áp suất…\nĐối lưu, mây, dòng ẩm, SST\nLịch trong năm và trong ngày\nHiện không dùng mưa quá khứ",23)
    deck.card(s,6.88,1.65,5.8,3.67,"Nhãn và phạm vi","GSMaP Gauge → mưa vùng\n93 ô, tổng hợp trước mô hình\nDiện tích toàn ô ≈11.074 km²\nFootprint xấp xỉ Đà Nẵng mới",22)
    deck.band(s,"Chưa có giao ranh hành chính chính xác; nhãn vệ tinh vẫn có sai số.",color=RED)

    s=new("Một mẫu TFT được tạo như thế nào?",note="Lấy 168 giờ khí tượng trước thời điểm phát hành, tính trung bình theo khối 6 giờ, thành 28 bước. Với F biến, tensor quá khứ có dạng N×28×F. Decoder chỉ nhận 12 bước lịch tương lai với 4 biến lịch; không nhận ERA5 ở giờ cần dự đoán. Đầu lượng mưa gồm 3 số, đầu sự kiện gồm 3 ngày nhân 3 ngưỡng. Mọi cấu hình dùng mask chung E7: đủ lịch sử và nhãn 72 giờ, không thay mẫu khi bớt biến.")
    deck.table(s,["Bước","Thao tác","Kết quả"],[
        ["1","Tổng hợp ô → vùng","Một chuỗi vùng"],
        ["2","168 giờ quá khứ → gộp 6 giờ","28 bước × F biến"],
        ["3","Thêm lịch tương lai đã biết","12 bước × 4 biến lịch"],
        ["4","TFT dự đoán lượng + sự kiện","3 lượng mm + 9 xác suất"]],row_h=.78,widths=[1.1,5.7,5.45],size=22)
    txt(s,.75,5.72,11.9,.76,"E0: F=11; E7: F=44. Cùng các mốc hợp lệ cho mọi E.\nERA5 hồi cứu chưa chứng minh dữ liệu đến kịp lúc chạy thật.",20)

    s=new("Bốn nhóm đặc trưng: cùng cột nguồn, khác vai trò",note="B gồm 7 trường bề mặt và 4 mã lịch. A gồm đối lưu, mây, lớp biên và ẩm đất. M gồm khí tượng trên cao và dòng ẩm. C chỉ có một biến nhiệt độ biển tại hộp biển. Các nhóm không lặp cột nhưng có thể tương quan vật lý và thống kê. A là tên quy ước: B/M cũng mô tả khí quyển. M chưa là một chỉ số gió mùa đã được kiểm định; C chưa là cả ENSO/MJO. Danh mục 44 biến ở phụ lục.")
    deck.table(s,["Nhóm","Số biến","Thông tin"],[
        ["B — Nền","11","Bề mặt và lịch"],
        ["A — Bổ sung","12","Đối lưu, mây, lớp biên, ẩm đất"],
        ["M — Hoàn lưu","20","Gió/ẩm trên cao, dòng ẩm, chênh áp"],
        ["C — Biển","1","SST vùng biển đã chọn"]],row_h=.78,widths=[3.1,1.4,7.75],size=22)
    deck.band(s,"44 biến ≠ 44 thông tin độc lập; thêm nhiều biến chưa chắc tốt hơn.")

    s=new("E0–E7: giữ mô hình, thay tổ hợp đầu vào",note="Ba nhóm bổ sung A/M/C tạo 2 mũ 3 bằng tám tổ hợp. Mỗi E đã chạy trên ba fold phát triển và ba seed TFT, tổng 9 lượt TFT; LightGBM xác định có 3 pipeline. E0 là bộ biến nền, không phải tên một thuật toán. Tăng số biến cũng làm tăng tham số đầu vào TFT; giữ hidden/epoch không đồng nghĩa cùng số tham số. Factorial giúp đo từng tổ hợp trong pipeline, chưa chứng minh nhân quả vật lý.")
    variables=[11,23,31,12,43,24,32,44]
    deck.table(s,["E","Đầu vào","Biến","TFT / LGBM"],[[e,GROUPS[e],variables[i],"9 / 3"] for i,e in enumerate(GROUPS)],
               row_h=.48,widths=[.8,4.5,1.5,5.45],size=21)
    deck.band(s,"Đã hoàn thành: 72 TFT + 24 LightGBM; 96/96 lượt tái lập kết quả.",y=6.17,h=.53,size=19)

    s=new("Vì sao thử TFT? Informer đã bị loại chưa?",source="Cơ sở: [A2] TFT • [A3–A4] Informer • Chưa có phép so Informer cùng giao thức",note="TFT được chọn như một giả thuyết kiến trúc có lựa chọn biến/gating và dự đoán nhiều hạn. Bản vùng điều chỉnh dùng LSTM/attention và đầu Tweedie/BCE, chưa có static context hoặc phân vị. Informer thiết kế cho chuỗi dài; mã tác giả có time marks. Với encoder 28 bước, hiệu quả chuỗi cực dài chưa phải nút thắt rõ. Chưa có phép so cùng giao thức, vì vậy R² cũ hay benchmark khác không đủ kết luận Informer kém hoặc không khả thi. Nếu so kiến trúc, cần cùng input/target/ngân sách và chấp nhận mọi kết quả.")
    deck.card(s,.65,1.65,6,3.95,"TFT: có cơ sở để thử","Học trọng số cho các biến\nKết hợp chuỗi và attention\nDự đoán nhiều hạn cùng lúc\nBản hiện tại là adaptation",22)
    deck.card(s,6.88,1.65,5.8,3.95,"Informer: chưa có kết luận","Chưa chạy cùng giao thức vùng\nCó đầu vào thông tin thời gian\nChuỗi hiện tại chỉ 28 bước\nĐiểm R² cũ không loại được nó",21)
    deck.band(s,"Lý do lựa chọn là giả thuyết để đo; chưa phải bằng chứng TFT thắng.",size=19)

    s=new("LightGBM đối chứng: cùng nguyên liệu, khác cách học",source="[A1] Ke et al. 2017 + cấu hình LightGBM đã lưu trong run.json",note="LightGBM là thuật toán cây boosting được huấn luyện, không phải nguồn mưa khác. TFT thấy chuỗi 28 bước; cây thấy thống kê của cùng lịch sử: khối cuối, trung bình 24/72/168 giờ và thay đổi hai khối cuối, cộng lịch. Vì thế E0 có 87 cột bảng, E7 có 252 cột. So E0/E2 trong một họ đo đóng góp M; so TFT/LightGBM tại cùng E đo hai pipeline. Còn khác biểu diễn, loss và số seed, nên chưa phải chỉ thay một kiến trúc. Với vài nghìn nhãn ngày, đối chứng cây là phép đo cần thiết; không có định lý cây luôn thắng.")
    deck.table(s,["Nội dung","TFT","LightGBM"],[
        ["Nguyên liệu","Khí tượng quá khứ + lịch","Cùng nguyên liệu"],
        ["Biểu diễn","Chuỗi 28 bước","Thống kê lịch sử thành bảng"],
        ["Mô hình","Mạng neural","Tổ hợp cây boosting"],
        ["Đầu ra / mẫu chấm","Ba ngày, cùng nhãn/mốc","Ba ngày, cùng nhãn/mốc"]],row_h=.77,widths=[3.0,4.625,4.625],size=20)
    deck.band(s,"E0/E7 là cách chọn biến; TFT/LightGBM là cách học từ những biến đó.",size=19)

    s=new("LightGBM có cơ sở ứng dụng trong dự đoán mưa",source="Nguồn sơ cấp [R1–R3]; tiêu đề, DOI và giới hạn ở phụ lục tài liệu tham khảo",note="R1 là nghiên cứu mưa ngày kế tiếp tại Cairns, trong đó LightGBM học thành phần dư của mô hình lai. R2 dùng LightGBM cho lượng mưa tại vùng núi Nhật Bản với forecast lân cận và quan trắc. R3 nghiên cứu dự đoán mùa, nên chỉ hỗ trợ bối cảnh phương pháp. Những bài này chứng minh thuật toán đã được dùng trong nghiên cứu giáng thủy, không chứng minh cấu hình của nhóm tốt ở Đà Nẵng. Không nhập điểm giữa các bài vì khác nhãn, hạn và không gian. Phân biệt cơ sở thuật toán A1 với cơ sở ứng dụng R1/R2.")
    deck.table(s,["Nghiên cứu","LightGBM làm gì?","Giới hạn khi vận dụng"],[
        ["R1 · He và cs.\n2022 · KBS","Học phần dư trong mô hình lai\ndự đoán mưa ngày kế tiếp","Cairns; có mưa quá khứ;\nkhông phải cây đơn lẻ"],
        ["R2 · Iwase & Takenawa\n2024 · JIP","Dự đoán lượng mưa vùng núi\ntừ forecast và quan trắc","Dự đoán tại điểm;\ncó forecast đầu vào"],
        ["R3 · Qian & Jia\n2023 · Atmos. Research","Dự đoán giáng thủy mùa đông\nbằng LightGBM/XGBoost","Hạn mùa; không chứng minh\nkỹ năng ở 24–72 giờ"]],
        row_h=1.02,widths=[3.15,4.7,4.4],size=18)
    deck.band(s,"Paper tạo cơ sở thử nghiệm; kết quả cùng giao thức mới quyết định giá trị.",size=19)

    s=new("Nhánh dev có POD/FAR; có thực sự chọn model bằng nó?",source=f"Read-only origin/dev {dev['ref'][:7]} • LOCAL.py + Tweedie COLAB.ipynb • Chi tiết: dev_metrics_audit.json",note="Trong script LOCAL, hàm evaluate báo POD/FAR cho tổng 6 giờ đạt 10 mm cùng CSI/RMSE/MAE. Notebook Tweedie bổ sung chỉ số 1 giờ, 3/6 giờ và max giờ. Tuy nhiên early stopping của hai tệp được rà soát so RMSE phần tử trên đầu ra giờ; tên biến val_rmse_6h không tự làm nó thành RMSE tổng 6 giờ. evaluate xác suất trong notebook ghi BS và CSI_prob ở p>=0.5, dù docstring nhắc BSS. Do đó không đồng nhất bảng báo cáo POD/FAR với việc tối ưu POD/FAR, hoặc BS với BSS. Phạm vi audit là commit này, chưa xác nhận mã riêng chưa push của thành viên.")
    deck.table(s,["Nội dung","Dev đã rà soát","TFT vùng hiện tại"],[
        ["Nhãn","precipitation, full_features cũ","GSMaP Gauge, vùng 93 ô"],
        ["Sự kiện","Tổng 6h / max giờ; nhiều ngưỡng","Tổng 24h vùng; 16/50/100 mm"],
        ["Quyết định","Nhiều cột từ lượng mm ≥ q","Bảng chính: xác suất p ≥ τ cal"],
        ["Chọn epoch","RMSE phần tử đầu ra giờ","Brier calibration, 3 ngày"]],
        row_h=.78,widths=[2.5,4.9,4.85],size=18.5)
    deck.band(s,"Cùng công thức POD/FAR chưa đủ để so điểm: phải cùng nhãn, khoảng giờ và quy tắc.",size=18)

    s=new("Ba câu hỏi đánh giá cần ba nhóm chỉ số",source="[V1] Kiểm chứng sự kiện • [V2] Kiểm chứng xác suất • src/short_range_evaluation.py",note="Lượng mm, xác suất và quyết định là ba sản phẩm liên quan nhưng khác nhau. RMSE/MAE/Bias đo lượng. BS/BSS đánh giá xác suất với nhãn sự kiện 0/1. CSI/POD/FAR đo quyết định có/không sau khi chọn ngưỡng xác suất. BSS tốt không tự bảo đảm RMSE tốt; POD cao không bảo đảm ít báo nhầm. Tập dữ liệu ít sự kiện làm accuracy dễ bị ngày khô chi phối. Đầu lượng mưa và xác suất hiện không thuộc một phân phối duy nhất, nên không thay CSI của hai loại đầu ra cho nhau.")
    deck.card(s,.65,1.72,3.85,3.65,"1 · Lượng mưa","Sai bao nhiêu mm?\nRMSE: chú ý lỗi lớn\nMAE: lỗi tuyệt đối\nBias: thừa hay thiếu",22)
    deck.card(s,4.72,1.72,3.85,3.65,"2 · Xác suất","Xác suất có ích không?\nBS: lỗi xác suất\nBSS: hơn khí hậu?\nReliability: có đúng mức?",21)
    deck.card(s,8.79,1.72,3.85,3.65,"3 · Quyết định","Báo có/không thế nào?\nPOD: bắt được bao nhiêu\nFAR: báo nhầm bao nhiêu\nCSI: tổng hợp ba số đếm",20)
    deck.band(s,"RMSE/MAE nhỏ hơn; Bias gần 0; BSS/CSI/POD lớn hơn; FAR nhỏ hơn.",size=18.5)

    s=new("Lượng mưa: vì sao cần cả RMSE, MAE và Bias?",source="Ví dụ tự tạo để giải thích; không phải kết quả mô hình",note="Nhãn [0,10,40] mm và dự đoán [0,15,25] mm tạo lỗi [0,+5,-15] mm. MAE=(0+5+15)/3=6,67 mm. RMSE=sqrt((0+25+225)/3)=9,13 mm. Bias=(0+5-15)/3=−3,33 mm. RMSE phạt lỗi 15 mm mạnh, MAE mô tả trung bình trị tuyệt đối và Bias chỉ ra xu hướng thiếu. Bias có thể triệt tiêu khi có lỗi dương/âm, vì vậy gần 0 chưa bảo đảm tốt. Đây là tổng mưa 24 giờ trung bình vùng, không so trực tiếp với RMSE giờ hoặc tại điểm.")
    deck.table(s,["Ví dụ 3 ngày","Ngày A","Ngày B","Ngày C"],[
        ["Mưa nhãn y (mm)","0","10","40"],
        ["Dự đoán f (mm)","0","15","25"],
        ["Sai số f−y (mm)","0","+5","−15"]],row_h=.63,widths=[4.0,2.75,2.75,2.75],size=23)
    txt(s,.75,4.55,11.85,1.14,"MAE = trung bình |f−y| = **6,67 mm**\nRMSE = căn trung bình (f−y)² = **9,13 mm**\nBias = trung bình (f−y) = **−3,33 mm**: dự đoán thiếu",21)
    deck.band(s,"Bias có thể triệt tiêu lỗi dương/âm; một chỉ số riêng không mô tả đủ sai số lượng.",size=18)

    s=new("Xác suất: BSS so với khí hậu, không phải accuracy",source="Định nghĩa BS/BSS [V2]; số minh họa tự tạo",note="Với o=1 khi mưa đạt ngưỡng và o=0 khi không, Brier score là trung bình (p-o)^2. Nếu sự kiện xảy ra, dự báo 0,8 có lỗi 0,04, dự báo 0,2 có lỗi 0,64. BSS=1-BS_model/BS_ref. Ví dụ BS_model=0,06 và BS_ref=0,08 thì BSS=0,25, tương đương giảm 25% lỗi Brier so tham chiếu, không phải 25% ngày đúng. Khí hậu trong dự án học từ train theo tháng/lead. BSS có thể âm; nó không đo sai số mm và không cần ngưỡng quyết định tau. Reliability là chẩn đoán bổ sung, không thay BSS.")
    deck.card(s,.65,1.65,6,3.95,"BS · lỗi xác suất","Nhãn o: 1 nếu mưa đạt ngưỡng\nBS = trung bình (p−o)²\nThực có mưa: p=0,8 → lỗi 0,04\nThực có mưa: p=0,2 → lỗi 0,64",21)
    deck.card(s,6.88,1.65,5.8,3.95,"BSS · hơn khí hậu bao nhiêu?","BSS = 1 − BS / BS_khí_hậu\nVí dụ: 1 − 0,06/0,08 = 0,25\nGiảm 25% lỗi Brier so tham chiếu\nDương: hơn; âm: kém tham chiếu",20)
    deck.band(s,"BSS = 0,25 không có nghĩa dự đoán đúng 25% số ngày; không có đơn vị mm.",size=18.5)

    s=new("POD, FAR, CSI: cùng xuất phát từ bảng đếm",source="Công thức [V1]; ví dụ tự tạo, không phải kết quả mô hình",note="Ví dụ 100 ngày có 10 ngày đạt ngưỡng. Báo trúng 7, bỏ sót 3, báo nhầm 5 và đúng không sự kiện 85. POD=7/(7+3)=0.700. FAR=5/(7+5)=0.417. CSI=7/(7+3+5)=0.467. FAR chia cho tổng lần báo có, khác false positive rate chia cho tổng ngày không sự kiện. Không báo lần nào thì FAR không xác định, không tự điền 0. Nếu luôn báo khô, accuracy đạt 90% nhưng không bắt được một sự kiện nào.")
    deck.table(s,["Ví dụ 100 ngày","Thực có sự kiện","Thực không có"],[
        ["Mô hình báo có","H = 7 · báo trúng","F = 5 · báo nhầm"],
        ["Mô hình báo không","M = 3 · bỏ sót","TN = 85 · đúng không"]],
        row_h=.83,widths=[4.0,4.125,4.125],size=22)
    txt(s,.75,4.52,11.8,1.20,"POD = H/(H+M) = 0,700       FAR = F/(H+F) = 0,417\nCSI = H/(H+M+F) = 0,467       FAR khác FPR = F/(F+TN)",23)
    deck.band(s,"Luôn báo khô có accuracy 90% trong ví dụ; POD = 0 và CSI = 0.",color=RED,size=19)

    s=new("POD cao hơn có đủ để kết luận tốt hơn?",source=default,note="Đây là E7 ngày 1 thật, cùng 1075 mốc và 114 sự kiện. TFT bắt được 73, bỏ sót 41 và báo nhầm 66. LightGBM bắt được 60, bỏ sót 54 và báo nhầm 32. TFT bắt thêm 13 sự kiện nhưng có thêm 34 báo nhầm. Không nói mô hình nào tốt hơn chỉ từ một chỉ số. Ưu tiên bỏ sót hay báo nhầm cần mục tiêu sử dụng và chi phí rõ; chưa có yêu cầu đó để tự đặt POD tối thiểu. Các số đếm được tái tạo từ aggregate đầy đủ độ chính xác và kiểm tra khớp CSI, không dùng nhãn mới.")
    c={r["model"]:r for r in counts if r["lead_day"]==1}
    deck.table(s,["E7 · ngày 1","Trúng H","Bỏ sót M","Báo nhầm F","POD ↑","FAR ↓"],[
        ["TFT",c["tft"]["hits"],c["tft"]["miss"],c["tft"]["false_alarm"],f'{row("tft","E7",1).POD:.3f}',f'{row("tft","E7",1).FAR:.3f}'],
        ["LightGBM",c["lgbm"]["hits"],c["lgbm"]["miss"],c["lgbm"]["false_alarm"],f'{row("lgbm","E7",1).POD:.3f}',f'{row("lgbm","E7",1).FAR:.3f}']],
        row_h=.82,widths=[2.4,1.8,2.0,2.25,1.9,1.9],size=22,
        styles={"1,1":{"bold":True},"1,4":{"bold":True,"color":TEAL},"2,3":{"bold":True},"2,5":{"bold":True,"color":TEAL}},tag="counts_E7_day1")
    txt(s,.75,4.46,11.8,1.20,"TFT bắt thêm **13 sự kiện**, đồng thời thêm **34 lần báo nhầm**.\nPOD/FAR phải đọc thành một cặp, cùng CSI và số lượng sự kiện.",23)
    deck.band(s,"In đậm: số để đối chiếu trong bảng; chưa phải kết luận khác biệt có ý nghĩa thống kê.",size=17.5)

    s=new("Nên ưu tiên metrics thế nào trong nghiên cứu hiện tại?",source="Giữ protocol đã khóa; đây là khuyến nghị cách báo cáo, không đổi tiêu chí sau khi thấy điểm",note="Giao thức hiện có gia đình kiểm định chính cho BSS16 và báo CSI. Giữ giao thức để không đổi mục tiêu theo điểm đẹp. POD/FAR là chẩn đoán bắt buộc cạnh CSI; lượng mm phải xuất hiện rõ bằng RMSE/MAE/Bias vì đó là đầu ra nghiên cứu. Nếu bài báo xác định cải thiện lượng mm là câu hỏi chính, cần chốt tiêu chí định lượng trước holdout, không dùng BSS như bằng chứng duy nhất. Nếu mục tiêu là cảnh báo ít bỏ sót, đặt yêu cầu POD và đánh đổi FAR từ nhu cầu sử dụng, chọn ngưỡng trên calibration rồi khóa. Không có một thứ tự phổ quát chỉ do dự báo là ngắn hạn.")
    deck.table(s,["Mục đích","Vai trò đề nghị"],[
        ["Đóng góp đặc trưng trong protocol hiện tại","BSS16 chính; CSI + POD + FAR luôn đi cùng"],
        ["Đánh giá lượng mưa vùng dự đoán","RMSE + MAE + Bias hiển thị ngang phần kết quả"],
        ["Nếu ưu tiên cảnh báo ít bỏ sót","Cần chốt yêu cầu POD và mức FAR chấp nhận"],
        ["Nếu đổi mục tiêu chọn mô hình","Khóa lại trước holdout; chưa tự đổi trong lượt này"]],
        row_h=.82,widths=[5.0,7.25],size=19)
    deck.band(s,"POD/FAR cần thiết; chưa có cơ sở ưu tiên riêng một chỉ số lên trên mọi mục tiêu.",size=18)

    s=new("Chia theo thời gian, cùng mẫu, giữ kín năm 2025",note="Train học scaler, mô hình và khí hậu. Calibration chọn epoch/iteration, hiệu chỉnh xác suất và ngưỡng, nên không phải một tập đánh giá độc lập. Evaluation của ba fold là 2021–2023 và đã được xem trong development. Có 1075 mốc mỗi lead, 114 sự kiện16, 37 sự kiện50, 15 sự kiện100. Ba lead có ngày mưa trùng nhau, không cộng thành số đợt độc lập. Nếu đổi ranh/nhãn, phải chạy lại phần phát triển trước khóa thiết kế. Không lấy kết quả 2026 để chọn mô hình chấm 2025.")
    deck.table(s,["Fold","Train","Calibration","Evaluation"],[
        ["F1","2015–2019","2020","2021"],["F2","2015–2020","2021","2022"],
        ["F3","2015–2021","2022","2023"]],row_h=.7,widths=[1,4.0,3.625,3.625],size=23)
    txt(s,.75,4.85,11.85,1.0,"1.075 mốc / ngày dự đoán · 114 sự kiện ≥16 mm\nChỉ 37 / 15 sự kiện ≥50 / ≥100 mm: độ bất định cao.",23,True)
    deck.band(s,"Ba seed không nhân ba số ngày thời tiết. Development chưa thay kiểm định cuối.",size=18.5)

    s=new("Hai ngưỡng khác nhau: lượng mưa q và xác suất τ",source="src/short_range_evaluation.py + ensemble_calibration_thresholds.csv • Không chọn τ bằng evaluation",note="Ngưỡng q=16/50/100 mm xác định nhãn sự kiện từ lượng mưa vùng. Ngưỡng tau xác định báo có từ xác suất. Calibration hiện chọn tau bằng CSI; các điểm POD/FAR trong bảng là ở những ngưỡng đó, không phải tại cùng POD hoặc cùng FAR giữa hai mô hình. Khi hạ tau, có thể bắt thêm sự kiện và thêm báo nhầm; FAR không nhất thiết đơn điệu trong mẫu hữu hạn. BS/BSS không cần tau. CSI từ đầu lượng mưa>=q là amount_CSI, khác CSI chính từ xác suất>=tau. Các ngưỡng mưa là giao thức nghiên cứu, không tự là cấp cảnh báo từng xã.")
    deck.card(s,.65,1.65,6,3.9,"q · định nghĩa sự kiện","Mưa thực vùng ≥16 mm/24h?\nCó → nhãn 1; không → nhãn 0\n50/100 mm: các mức hiếm hơn\nKhông phải cấp cảnh báo tại điểm",21)
    deck.card(s,6.88,1.65,5.8,3.9,"τ · quyết định báo có","Xác suất dự báo p ≥ τ?\nτ chọn trên calibration\nGiữ cố định khi chấm evaluation\nBSS không cần chọn τ",22)
    deck.band(s,"POD/FAR giữa hai mô hình hiện chưa ở cùng mức POD hoặc cùng mức FAR.",size=19)

    s=new("BSS toàn ma trận: ngày 1 có ích, ngày 3 chưa vượt khí hậu",source=default,note="BSS=1-BS/BSref. Dương tốt hơn khí hậu, âm kém hơn; không phải accuracy. Bảng cho đủ E0–E7, ba ngày và hai mô hình, mỗi cột in đậm điểm tốt nhất ở độ chính xác hiển thị. Chữ đỏ đánh dấu BSS âm; điểm ít âm nhất vẫn kém khí hậu. TFT E2/E6 có điểm cao ngày1, LightGBM E4 cao ngày1; chưa có kiểm định mọi cặp để tuyên bố cấu hình thắng ngoài mẫu. Không trung bình các BSS năm để thay BSS pooled đã tính từ các dự đoán/reference ghép.")
    rows=[];styles={}
    for i,e in enumerate(GROUPS,1):rows.append([e]+[f'{row(m,e,d).BSS:.4f}' for m in ["tft","lgbm"] for d in [1,2,3]])
    for col in range(1,7):
        vals=[float(v[col]) for v in rows];best=max(vals)
        for i,v in enumerate(vals,1):styles[f"{i},{col}"]={"bold":v==best,"color":RED if v<0 else TEAL if v==best else NAVY}
    deck.table(s,["E","TFT N1","TFT N2","TFT N3","LGBM N1","LGBM N2","LGBM N3"],rows,
        row_h=.48,widths=[.7]+[1.925]*6,size=19,styles=styles,tag="bss_matrix")
    deck.band(s,"Đậm: tốt nhất trong cột; đỏ: kém khí hậu. BSS 0,246 không phải accuracy 24,6%.",y=6.17,h=.53,size=17.5)

    s=new("E7: đọc POD, FAR, CSI và BSS cùng nhau",source=default,note="Mỗi hàng dùng cùng ngưỡng mưa16, nhưng tau quyết định được chọn riêng trên calibration của từng fold/mô hình. Bảng in đậm điểm tốt hơn giữa TFT và LightGBM cùng ngày ở độ chính xác hiển thị; chưa là kiểm định khác biệt giữa hai mô hình. Biểu đồ dùng success ratio=1-FAR trên trục ngang, POD trên trục dọc và đường CSI. Đây là performance diagram, không phải ROC vì trục ngang không phải FPR. Điểm gộp đại diện các fold có tau riêng, không phải một ngưỡng xác suất toàn cục. Ngày3 BSS âm dù POD vẫn khoảng0.4–0.5, nên chỉ nhìn POD sẽ che lỗi xác suất.")
    erows=[];estyles={}
    for day in [1,2,3]:
        for m,label in [("tft","TFT"),("lgbm","LGBM")]:
            r=row(m,"E7",day);erows.append([str(day),label,*[f'{r[k]:.3f}' for k in ["POD","FAR","CSI","BSS"]]])
        for col,metric in enumerate(["POD","FAR","CSI","BSS"],2):
            vals=[float(erows[-2][col]),float(erows[-1][col])];best=min(vals) if metric=="FAR" else max(vals)
            for offset,value in enumerate(vals):
                estyles[f"{2*day-1+offset},{col}"]={"bold":value==best,"color":RED if metric=="BSS" and value<0 else TEAL if value==best else NAVY}
    deck.table(s,["Ngày","Model","POD ↑","FAR ↓","CSI ↑","BSS ↑"],erows,
        x=.55,y=1.8,w=7.1,row_h=.53,widths=[.6,1.3,1.3,1.3,1.3,1.3],size=17,styles=estyles,tag="e7_decisions")
    deck.image(s,OUT/"performance_E7.png",7.86,1.65,4.92,4.18)
    deck.band(s,"Đậm: điểm tốt hơn giữa hai model cùng ngày; chưa có CI cho phép so model này.",size=17.5)

    s=new("Lượng mm vẫn phải báo rõ: RMSE, MAE và Bias",source=default,note="RMSE phạt lỗi lớn; MAE là lỗi tuyệt đối trung bình; Bias âm là dự báo thiếu. Bảng E7 cho thấy LightGBM có RMSE/MAE ngày1 thấp hơn, còn ngày3 TFT RMSE thấp hơn nhưng MAE cao hơn. Chọn một chỉ số có thể dẫn đến nhận xét khác nhau; không nói thắng mọi mặt. Mỗi cột in đậm điểm tốt hơn cùng ngày, Bias theo trị tuyệt đối. BSS tốt hơn không tự suy ra RMSE tốt hơn. RMSE khoảng20mm là mức lỗi tổng hợp, không phải khoảng chắc chắn mọi ngày sai trong ±20mm.")
    arows=[];astyles={}
    for day in [1,2,3]:
        for m,label in [("tft","TFT"),("lgbm","LightGBM")]:
            r=row(m,"E7",day);arows.append([day,label,*[f'{r[k]:.3f}' for k in ["RMSE","MAE","bias"]]])
        for col,metric in enumerate(["RMSE","MAE","bias"],2):
            vals=[float(arows[-2][col]),float(arows[-1][col])]
            best=min(abs(v) if metric=="bias" else v for v in vals)
            for offset,v in enumerate(vals):
                if (abs(v) if metric=="bias" else v)==best:astyles[f"{2*day-1+offset},{col}"]={"bold":True,"color":TEAL}
    deck.table(s,["Ngày","E7","RMSE ↓","MAE ↓","Bias ≈0"],arows,row_h=.61,
        widths=[.8,3.35,2.7,2.7,2.7],size=23,styles=astyles,tag="e7_amount")
    deck.band(s,"Đơn vị mm/24h • In đậm theo cặp cùng ngày • Bias âm: dự báo thiếu.",size=18.5)

    s=new("Thêm A/M có tín hiệu xác suất ngày 1; SST chưa rõ",source="paired_bootstrap.csv • 20.000 paired bootstrap • Gia đình 9 phép BSS16 • Khối 7/14 ngày",note="Gia đình chính gồm E1-E0, E2-E0, E3-E0 trên ba ngày, tổng9phép. CI99.44% điều chỉnh theo Bonferroni cho từng phép. A ngày1 delta khoảng0.0853, CI[0.0022,0.1607]; M khoảng0.1443, CI[0.0681,0.2329]; C chứa0. Khối14ngày cho cùng phân loại. Bootstrap lấy chung trọng số cho nhãn, dự đoán và reference, điều kiện trên mô hình đã fit; không bao phủ mọi bất định nhãn, khởi tạo, ranh và lựa chọn mô hình. Chưa kiểm định trực tiếp M-A. Các năm development đã xem trước nên không thay holdout độc lập.")
    deck.image(s,OUT/"primary_family_ci.png",.55,1.50,12.25,4.75)
    deck.band(s,"Chỉ A/M ngày 1 có CI chính trên 0; chưa có bằng chứng tương tự ở ngày 2–3.",y=6.28,h=.45,size=17.8)

    s=new("Khả thi về tính toán; còn cổng dữ liệu và kiểm định",note="Ma trận96lượt hiện chạy khoảng27.9phút trên4060Laptop8GB; đó là thời gian tiến trình, không phải mọi công việc nghiên cứu. Ưu tiên tiếp theo là ranh/trọng số vùng và kiểm chứng nhãn ngày, gồm các biến mã hóa/proxy cần xác nhận. Nếu dữ liệu thay đổi, chạy lại development liên quan rồi khóa. Ngày3 có thể cần forecast thật hoặc cách học khác, nhưng ma trận hiện chưa cô lập nguyên nhân. Không lấy kết quả âm để kết luận toàn bộ bài toán72giờ không khả thi. Chưa cần thêm kiến trúc chỉ để chứng minh kiến trúc đó thua.")
    deck.card(s,.65,1.65,6,3.95,"Đã có bằng chứng","Đủ E0–E7; 96 lượt tái lập\nTiến trình ma trận ≈28 phút\nTín hiệu ngày 1 với A/M\nCó đối chứng và kết quả âm",22)
    deck.card(s,6.88,1.65,5.8,3.95,"Việc tiếp theo","Chốt ranh/trọng số vùng\nKiểm chứng nhãn và biến\nKhóa mục tiêu/metrics/ngưỡng\nSau đó mới chấm năm 2025",22)
    deck.band(s,"Kết quả phát triển ≠ đã bảo đảm vận hành hoặc dự đoán tốt mọi ngày tới 72 giờ.",color=RED,size=18)

    s=new("Thông điệp có thể dùng khi báo cáo giảng viên",note="Có cơ sở ứng dụng LightGBM trong các bài nghiên cứu mưa, nhưng phép đo tại dự án mới quyết định giá trị. POD và FAR vẫn cần ở hạnngày, luôn đọc cùng CSI, BSS và lượng mm; chưa có yêu cầu chi phí để ưu tiên riêng POD hoặc FAR. Đã chạy đủE0–E7 và có tín hiệuA/Mngày1; ngày3chưa vượt khí hậu. Phần tiếp theo là hoàn thiện định nghĩa vùng, nhãn, giao thức rồi holdout. Khi bị hỏi TFTsao chưa thắngLightGBM, trả lời mục tiêu nghiên cứu đặc trưng, không đặt trước thuật toán phải thắng.")
    txt(s,.75,1.70,11.85,3.95,"1. LightGBM có cơ sở nghiên cứu mưa và là đối chứng đã huấn luyện.\n\n2. POD/FAR cần thiết, nhưng phải đi cùng CSI, BSS và sai số lượng mm.\n\n3. A/M có tín hiệu ngày 1; ngày 3 hiện chưa vượt khí hậu tham chiếu.",25)
    deck.band(s,"Phụ lục tiếp theo: đủ 48 dòng kết quả, 44 biến và nguồn sơ cấp.",size=20)

    # Six full tables: same 48 rows and seven metrics as the original aggregates.
    metrics=["RMSE","MAE","bias","BSS","CSI","POD","FAR"]
    appendix_slides=[]
    for day in [1,2,3]:
        for m,label in [("tft","TFT ensemble 3 seed"),("lgbm","LightGBM xác định")]:
            s=new(f"Ngày {day} · {label} · đủ E0–E7",source=default,section="PHỤ LỤC · BẢNG KẾT QUẢ ĐẦY ĐỦ",
                  note="Bảng chứa đúng tám cấu hình và bảy chỉ số từ aggregate gốc. Đậm là điểm tốt nhất ở độ chính xác hiển thị trong cùng cột; RMSE/MAE/FAR lấy nhỏ nhất, Bias lấy gần0nhất, BSS/CSI/POD lấy lớn nhất. Đỏ là BSSâm; ítâmnhất vẫn kém khí hậu. Đây không phải kiểm định mọi cặp. TFT ensemble3seed, không phải trung bình metric3seed. Cùng1075mốc/114sự kiện16cho mọiE. Lượngmưa có đơn vịmm/24h; chỉ số sự kiện không đơn vị.")
            rows=[[e]+[f'{row(m,e,day)[k]:.3f}' for k in metrics] for e in GROUPS];styles={}
            for col,k in enumerate(metrics,1):
                vals=[float(r[col]) for r in rows]
                compare=[abs(v) if k=="bias" else v for v in vals]
                best=min(compare) if k in ["RMSE","MAE","bias","FAR"] else max(compare)
                for ri,(v,c) in enumerate(zip(vals,compare),1):
                    styles[f"{ri},{col}"]={"bold":c==best,"color":RED if k=="BSS" and v<0 else TEAL if c==best else NAVY}
            deck.table(s,["E","RMSE ↓","MAE ↓","Bias ≈0","BSS ↑","CSI ↑","POD ↑","FAR ↓"],rows,
                row_h=.48,widths=[.63]+[1.66]*7,size=18.5,styles=styles,tag=f"full_{m}_{day}")
            deck.band(s,"Đậm: tốt nhất trong cột ở số hiển thị, cùng đậm nếu bằng nhau; chưa là ý nghĩa thống kê.",y=6.17,h=.53,size=16.6)
            appendix_slides.append(dict(slide=s["number"],model=m,lead_day=day))

    # Feature identifiers remain exact; descriptions use native-source metadata.
    for groups,title in [(["B","A"],"Danh mục B và A: 23 biến"),(["M","C"],"Danh mục M và C: 21 biến")]:
        s=new(title,section="PHỤ LỤC · TRA CỨU ĐẶC TRƯNG",source="Nguồn: feature_catalog.csv • Có tên cột V1 và đơn vị trong Excel 18 sheet",
              note="Tên biến giữ đúng theo feature_catalog.csv. Trường khí tượng V1 thường có tiền tốmean__; lịch không có tiền tố. Mỗi nhóm là danh mục cột, không độc lập thống kê. CINNaNđược mã hóa500vàhas_lfc được dựng theo nguồn, cần audit vật lý; hữu hạn không tự bảo đảm đúng. Các trườngcontext/SST/chênh áp có miền không gian riêng. Không suy ra93quantrắcERA5độc lập từ lưới đích0.1độ.")
        part=catalog[catalog.group.isin(groups)]
        split=(len(part)+1)//2
        for left,frame in [(True,part.iloc[:split]),(False,part.iloc[split:])]:
            vals=[]
            for r in frame.itertuples():vals.append([r.group,r.native_variable,r.unit])
            deck.table(s,["Nhóm","Biến gốc","Đơn vị"],vals,x=.55 if left else 6.80,y=1.60,w=6.0,
                row_h=.35,widths=[.62,3.95,1.43],size=15)
        deck.band(s,"Xem mô tả từng biến và giới hạn nguồn ở DANH_MUC_BIEN trong Excel.",y=6.32,h=.40,size=14)

    s=new("Nguồn ứng dụng: LightGBM đã được dùng trong mưa",section="PHỤ LỤC · TÀI LIỆU THAM KHẢO",
          source="Đường dẫn trên slide có thể bấm; hồ sơ đối chiếu và giới hạn ở literature.json",
          note="Ba nguồn sơ cấp được đối chiếu đến ngày21/10/2026. R1vàR3được đọc qua phần công khai từ nhà xuất bản; không khẳng định đã auditfulltextphương pháp. R2có trang bài báo vàPDFchính thức. Không sao chépPDF hoặc điểm của paper vào repo. Đây là cơ sở chọn phép thử, không là bảo đảm kết quả cho ViệtNam.")
    for i,r in enumerate(refs[:3]):
        y=1.57+i*1.52
        deck.text(s,.75,y,11.85,.38,f'{r["id"]} · {r["authors"]} ({r["year"]}) · DOI {r["doi"]}',18,True,TEAL,url=r["url"])
        deck.text(s,.75,y+.44,11.85,.87,r["title"]+"\n"+r["venue"],18,url=r["url"])

    s=new("Nguồn thuật toán và kiểm chứng dự báo",section="PHỤ LỤC · TÀI LIỆU THAM KHẢO",
          source="Nguồn dự án: run.json, checkpoint_audit.json, scores_ensemble_pooled.csv, paired_bootstrap.csv",
          note="A1làpaperthuật toánLightGBM, A2TFT, A3/A4Informer. V1làhướng dẫn kiểm chứng phân loại, V2làkiểm chứng xác suất. Các nhận định áp dụng cho dữ liệu28bước/vùng xấp xỉ là suy luận của dự án, không trích như kết luận bài gốc. Chi tiết lịch sử nhánhdevđược đóng dấu bằngcommitvàSHA; không chấm lại mô hình hoặc mở2025trong lượt làm slide.")
    for i,r in enumerate(refs[3:]):
        y=1.53+i*.77
        deck.text(s,.75,y,11.85,.30,f'{r["id"]} · {r["authors"]} ({r["year"]})',16.5,True,TEAL,url=r["url"])
        deck.text(s,.75,y+.31,11.85,.42,r["title"],15.5,url=r["url"])

    assert len(deck.slides)==34
    # Speaker notes are also supplied separately for rehearsal and review.
    # Add spaces to a few compact metadata phrases without touching identifiers.
    for sl in deck.slides:
        note=sl["note"]
        for a,b in {"9phép":"9 phép","20mm":"20 mm","72giờ":"72 giờ","96lượt":"96 lượt",
                    "27.9phút":"27,9 phút","4060Laptop8GB":"4060 Laptop 8 GB","A/Mngày1":"A/M ngày 1",
                    "ngày3":"ngày 3","ngày1":"ngày 1","A2TFT":"A2 TFT","A1là":"A1 là",
                    "A3/A4Informer":"A3/A4 Informer","V1là":"V1 là","V2là":"V2 là",
                    "TFTsao":"TFT sao","thắngLightGBM":"thắng LightGBM","đủE0":"đủ E0",
                    "tính từaggregate":"tính từ aggregate","seed,":"seed,","3seed":"3 seed",
                    "1075mốc":"1075 mốc","114sự":"114 sự","cho mọiE":"cho mọi E",
                    "0nhất":"0 nhất","ítâmnhất":"ít âm nhất","BSSâm":"BSS âm",
                    "khí hậu. ":"khí hậu. ","Lượngmưa":"Lượng mưa","mm/24h":"mm/24h",
                    "tiền tốmean__":"tiền tố mean__","CINNaN":"CIN NaN","hóa500":"hóa 500",
                    "500vàhas_lfc":"500 và has_lfc","trườngcontext":"trường context",
                    "93quantrắcERA5":"93 quan trắc ERA5","0.1độ":"0,1 độ",
                    "ngày21/10/2026":"ngày 21/10/2026","R1vàR3":"R1 và R3",
                    "auditfulltextphương":"audit full text phương","R2có":"R2 có","vàPDFchính":"và PDF chính",
                    "sao chépPDF":"sao chép PDF","ViệtNam":"Việt Nam","paperthuật":"paper thuật",
                    "toánLightGBM":"toán LightGBM","28bước/vùng":"28 bước/vùng",
                    "nhánhdevđược":"nhánh dev được","bằngcommitvàSHA":"bằng commit và SHA",
                    "mở2025trong":"mở 2025 trong","PODvẫn":"POD vẫn","0.4–0.5":"0,4–0,5",
                    "khối14ngày":"khối 14 ngày","Khối14ngày":"Khối 14 ngày",
                    "tổng9phép":"tổng 9 phép","tổng9 phép":"tổng 9 phép","20.000paired":"20.000 paired",
                    "Ngày3":"Ngày 3","khoảng0":"khoảng 0","khoảng20":"khoảng 20",
                    "gần0":"gần 0","ensemble3":"ensemble 3","metric3":"metric 3",
                    "Cùng1075":"Cùng 1075","kiện16cho":"kiện 16 cho","kiện16":"kiện 16",
                    "mưa16":"mưa 16","kiện50":"kiện 50","kiện100":"kiện 100",
                    "đơn vịmm":"đơn vị mm","trên4060":"trên 4060","Ma trận96":"Ma trận 96",
                    "bài toán72":"bài toán 72","hạnngày":"hạn ngày","tín hiệuA/M":"tín hiệu A/M",
                    "3chưa":"3 chưa","C chứa0":"C chứa 0","CI99.44%":"CI 99,44%","CI[":"CI ["}.items():
            note=note.replace(a,b)
        sl["note"]=note
    deck.save(OUT/"PBL6_TFT_DAY_DU.pptx",OUT/"PBL6_TFT_DAY_DU.html",OUT/"slide_scene.json")
    write("LOI_DAN_TRINH_BAY.md","# Lời dẫn báo cáo TFT vùng\n\n24 slide chính (~25 phút) và 10 slide tra cứu. Có thể bỏ qua phụ lục khi trình bày, mở khi được hỏi.\n\n"+
          "\n\n".join(f'## Slide {sl["number"]}: {sl["title"]}\n\n{sl["note"]}' for sl in deck.slides))
    analysis=analysis_text(refs,dev,row,effect,counts)
    write("PHAN_TICH_LIGHTGBM_POD_FAR.md",analysis)
    write("README.md","""# Báo cáo đầy đủ TFT vùng: cơ sở LightGBM và vai trò POD/FAR

- [PowerPoint 34 slide chỉnh sửa được](PBL6_TFT_DAY_DU.pptx): 24 slide chính và 10 slide tra cứu; có notes.
- [Bản trình chiếu HTML độc lập](PBL6_TFT_DAY_DU.html): mở trình duyệt, dùng phím trái/phải hoặc nút; không cần Internet.
- [Lời dẫn từng slide](LOI_DAN_TRINH_BAY.md), [phân tích và nguồn](PHAN_TICH_LIGHTGBM_POD_FAR.md).
- [Ảnh xem trước toàn bộ slide](XEM_TRUOC.png).
- [Excel 18 sheet và Word giải thích đầy đủ](../short_range_explained_2026_10_21/README.md).
- [Hồ sơ paper](literature.json), [audit dev theo commit](dev_metrics_audit.json), [số đếm E7](E7_CONTINGENCY_COUNTS.csv).

In đậm theo phép so ghi dưới bảng: tốt nhất trong cột hoặc số cần đối chiếu; không tự đồng nghĩa ý nghĩa thống kê. BSS âm màu đỏ. Sáu bảng phụ lục có đủ 48 dòng E0–E7 × hai mô hình × ba ngày, với RMSE/MAE/Bias/BSS/CSI/POD/FAR. Có cả giới hạn ngày 3, vùng xấp xỉ và nhãn vệ tinh.

Kết luận: LightGBM có cơ sở ứng dụng dự đoán mưa; POD/FAR cần đi cùng CSI, BSS và sai số lượng mm. Chưa có lý do ưu tiên riêng POD hoặc FAR cho mọi mục tiêu. Giữ protocol hiện tại, chưa đổi tiêu chí sau khi xem development. Chưa mở test 2025 hoặc fit mô hình mới.

Tái lập: `python scripts/build_short_range_presentation.py`; kiểm tra bằng `python scripts/validate_short_range_presentation.py`. Cần môi trường dự án và requirements-reports. Slide đọc bảng tổng hợp đã công bố, không cần raw data/checkpoint. Hồ sơ dev là ảnh chụp commit fe27756, không đại diện mã thành viên chưa push.

Có thể dựng ảnh/kiểm tra tràn chữ bằng `python scripts/render_short_range_presentation.py` với Chrome/Edge đã cài. Đây là render bản HTML từ cùng bố cục/số liệu, chưa phải render PowerPoint bằng Office. Ảnh toàn bộ kích thước lớn và hồ sơ trình duyệt ở data/operational ngoài Git; chỉ ảnh tổng quan và biên bản kiểm tra được công bố.
""")
    source_paths=[SOURCE/n for n in ["run.json","checkpoint_audit.json","scores_ensemble_pooled.csv",
                 "paired_bootstrap.csv","feature_catalog.csv","primary_family_ci.png"]]
    source_paths.append(ROOT/"reports/short_range_explained_2026_10_21/dinh_nghia_han_du_bao.png")
    manifest=dict(status="built_from_audited_aggregates",date="2026-10-21",slides=34,main_slides=24,
                  appendix_slides=10,full_result_tables=appendix_slides,training_runs_added=0,test2025_read=False,
                  source_sha256={str(f.relative_to(ROOT)).replace("\\","/"):sha(f) for f in source_paths},
                  code_sha256={str(f.relative_to(ROOT)).replace("\\","/"):sha(f) for f in
                               [Path(__file__),ROOT/"scripts/presentation_layout.py"]},
                  dev_ref=dev["ref"],files={})
    for f in OUT.iterdir():
        if f.is_file() and f.name not in ["build_manifest.json","validation.json","render_manifest.json","layout_validation.json","XEM_TRUOC.png","browser_dom.html"]:
            manifest["files"][f.name]=dict(bytes=f.stat().st_size,sha256=sha(f))
    write("build_manifest.json",json.dumps(manifest,ensure_ascii=False,indent=2))
    print("PRESENTATION_BUILT",len(deck.slides),"slides; 48 result rows; no new model training")


def analysis_text(refs,dev,row,effect,counts):
    a,m,c=effect("E1"),effect("E2"),effect("E3")
    text=f'''# Phân tích cơ sở LightGBM và cách ưu tiên POD/FAR cho dự đoán mưa vùng

Ngày 21/10/2026. Đây là rà soát và trình bày lại bằng chứng phát triển đã có; không đổi mô hình, dữ liệu hoặc tiêu chí, không chấm năm 2025.

## 1. Có paper ứng dụng LightGBM trong dự đoán mưa không?

Có. Cần phân biệt paper thuật toán (A1) với paper ứng dụng mưa, và phân biệt dự đoán tương lai với ước lượng mưa đồng thời. Ba nguồn sơ cấp đã đối chiếu:

| Nguồn | Nội dung liên quan | Giới hạn khi dùng làm cơ sở |
| --- | --- | --- |
| R1, He và cs., 2022 | Mưa ngày kế tiếp ở Cairns; LightGBM học thành phần dư trong mô hình lai STL-ML. | Có mưa quá khứ; không phải LightGBM đơn lẻ hoặc vùng 93 ô. |
| R2, Iwase & Takenawa, 2024 | LightGBM dự đoán lượng mưa vùng núi Nhật Bản từ forecast lân cận và quan trắc. | Dự đoán tại điểm; có forecast đầu vào. |
| R3, Qian & Jia, 2023 | LightGBM/XGBoost dự đoán giáng thủy mùa đông ở Trung Quốc. | Hạn mùa, không chứng minh hiệu quả 24–72 giờ. |

R1/R3 được đối chiếu bằng phần công khai của nhà xuất bản; không gọi là đã audit toàn bộ phương pháp. R2 có bài/PDF chính thức. Tài liệu literature.json lưu DOI, đường dẫn và phạm vi. Không sao chép PDF hoặc điểm của paper vào bảng dự án. Một mô hình được dùng trong paper là cơ sở hợp lý để thử, chưa bảo đảm phù hợp dữ liệu/nhãn/vùng/lead của nhóm.

Trong dự án, LightGBM học từ cùng nguyên liệu khí tượng quá khứ và lịch với TFT, qua thống kê lịch sử. Hai bên chấm cùng nhãn/mốc/lead. Đây là đối chứng thật; còn khác biểu diễn chuỗi/bảng, loss và số seed, nên không gọi là kiểm định chỉ thay duy nhất kiến trúc. Câu hỏi chính về đóng góp biến vẫn có giá trị nếu cây tốt hơn mạng neural.

## 2. Dev trước đó có ưu tiên POD/FAR không?

Đã đọc trực tiếp blob tại origin/dev commit `{dev['ref']}`, không checkout hoặc chạy notebook. Hai tệp triển khai được rà soát là LOCAL.py và Tweedie COLAB.ipynb; có đối chiếu notebook LOCAL và bảng summary. Hồ sơ SHA ở dev_metrics_audit.json.

- LOCAL.py báo POD/FAR cho tổng 6 giờ ≥10 mm, cùng CSI và RMSE/MAE.
- Notebook Tweedie bổ sung nhiều cột 1h, tổng 3/6h và max giờ; không lấy nhóm max giờ thay tổng 24h vùng.
- Các POD/FAR lượng mưa được tính bằng quy tắc lượng dự đoán ≥ngưỡng mưa. Bảng chính TFT hiện dùng xác suất ≥ngưỡng τ chọn trên calibration.
- Việc bảng có POD/FAR nổi bật không đồng nghĩa early stopping tối ưu POD/FAR. Mã hai tệp chọn bằng RMSE phần tử trên đầu ra giờ; biến tên val_rmse_6h nhưng chưa cộng tổng 6h tại phép tính đó.
- Trong evaluate xác suất của notebook Tweedie, thấy BS và CSI_prob với p≥0,5; chưa thấy BSS được tính trong hàm ấy, dù docstring nhắc BSS. Không đồng nhất BS và BSS hoặc coi tên cột là bằng chứng tính đúng.

Đây là audit có phạm vi, không khẳng định mọi mã của dev hoặc bản thành viên chưa push đều giống vậy. Nhãn cũ precipitation/full_features tại điểm khác nhãn vùng GSMaP hiện tại; ngưỡng 10mm/6h không tương đương 16mm/24h vùng. Không so trực tiếp POD/FAR hai nhánh để nói mô hình nào tốt hơn.

## 3. POD/FAR có cần ở hạn 24–72 giờ không?

Có. Chúng áp dụng cho sự kiện được định nghĩa rõ ở mọi hạn, không riêng nowcasting. Với y là tổng mưa trung bình vùng trong một khoảng 24 giờ và q là ngưỡng mưa, đặt o=1 nếu y≥q. Sau đó đặt quyết định d=1 nếu xác suất p≥τ. Từ d/o đếm:

- H: báo có và thực có; M: báo không nhưng thực có.
- F: báo có nhưng thực không; TN: báo không và thực không.
- POD=H/(H+M): tỷ lệ bắt được sự kiện thực, lớn hơn tốt hơn.
- FAR=F/(H+F): tỷ lệ báo nhầm trong những lần báo có, nhỏ hơn tốt hơn.
- CSI=H/(H+M+F): gộp trúng, bỏ sót, báo nhầm, lớn hơn tốt hơn.

FAR ở đây là false alarm ratio, không phải false positive rate F/(F+TN). Nếu không báo có lần nào, FAR không xác định; không tự điền 0. POD/FAR phụ thuộc ngưỡng và tần suất sự kiện; cần báo n/events, lead, mùa và quy tắc chọn τ. Khi ngưỡng làm bắt thêm sự kiện, thường có đánh đổi báo nhầm; FAR không nhất thiết đơn điệu trên một tập hữu hạn. CSI liên hệ toán học với POD/FAR, không phải một nguồn bằng chứng độc lập thứ ba.

## 4. Vì sao không tối ưu riêng POD hoặc FAR?

Ví dụ tự tạo 100 ngày có 10 sự kiện: luôn báo có đạt POD=1 nhưng FAR=0,90, CSI=0,10. Luôn báo không có POD=0, CSI=0 và FAR không xác định. Vì thế một con số đơn lẻ có thể thưởng cho hành vi không hữu ích.

Ví dụ thực E7 ngày 1, cùng 1.075 mốc/114 sự kiện:

| Mô hình | Trúng | Bỏ sót | Báo nhầm | POD | FAR | CSI | BSS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TFT | **73** | 41 | 66 | **{row('tft','E7',1).POD:.3f}** | {row('tft','E7',1).FAR:.3f} | {row('tft','E7',1).CSI:.3f} | {row('tft','E7',1).BSS:.3f} |
| LightGBM | 60 | 54 | **32** | {row('lgbm','E7',1).POD:.3f} | **{row('lgbm','E7',1).FAR:.3f}** | {row('lgbm','E7',1).CSI:.3f} | {row('lgbm','E7',1).BSS:.3f} |

TFT bắt thêm 13 sự kiện nhưng thêm 34 báo nhầm. POD cao hơn chưa đủ để gọi là mô hình tốt hơn. Cả hai đang ở τ chọn CSI trên calibration riêng; chưa phải so tại cùng POD, cùng FAR hoặc cùng chi phí. Các số đếm được tái tạo từ n/events/POD/FAR full precision trong aggregate, kiểm tra khớp CSI; không đọc nhãn hoặc dự đoán từng mốc.

## 5. Đề nghị vai trò từng nhóm metric

| Câu hỏi | Nhóm metric | Vai trò trong báo cáo hiện tại |
| --- | --- | --- |
| Lượng mưa vùng dự đoán lệch bao nhiêu? | RMSE, MAE, Bias | Hiển thị rõ và đọc cùng; không bỏ vì BSS tăng. |
| Xác suất sự kiện tốt hơn tham chiếu không? | BS/BSS, reliability | BSS16 là phép kiểm định chính đã khóa; reference chỉ học train. |
| Quyết định báo có bỏ sót/báo nhầm thế nào? | CSI + POD + FAR | Luôn báo cả ba cùng n/events và quy tắc τ. |
| Cải thiện có chắc trong tập ngày hiện tại? | Paired block CI | Kiểm định hiệu số đúng phép so, không suy từ in đậm. |

Giữ protocol đang khóa, chưa tự nâng POD hoặc FAR lên thành tiêu chí duy nhất sau khi thấy điểm. POD/FAR là chẩn đoán thiết yếu cạnh CSI. Ngay cả CSI cũng không thay thế được mục tiêu sử dụng và đánh giá xác suất/lượng mưa.

Nếu mục tiêu chính bài báo được chốt là cải thiện lượng mm, nên đăng ký RMSE cùng MAE/Bias cho câu hỏi đó trước holdout, và xử lý đa so sánh nếu thêm phép kiểm định chính. Hiện epoch TFT được chọn bằng Brier calibration, nên kết quả lượng mm thuộc pipeline được chọn theo tiêu chí xác suất; không mô tả như đã tối ưu RMSE riêng.

Nếu mục tiêu là cảnh báo hạn chế bỏ sót, trước hết cần yêu cầu về POD tối thiểu và mức báo nhầm chấp nhận từ người dùng/nghiệp vụ; sau đó chọn τ trên calibration theo ràng buộc rồi khóa. Chưa có yêu cầu chi phí để tự đặt một mức như POD≥70% làm tiêu chuẩn thật. Thời hạn 24–72h tự nó không quyết định POD quan trọng hơn FAR.

## 6. BSS và sai số lượng mm cần được đọc ra sao?

BS=mean((p-o)^2); BSS=1-BS/BS_reference. BSS>0 tốt hơn khí hậu tham chiếu, BSS<0 kém hơn. BSS0,246 không phải accuracy24,6%. Khí hậu hiện theo tháng đích/lead học từ train. Reliability đọc xác suất so tần suất thực, kèm số mẫu trong bin.

RMSE=sqrt(mean((f-y)^2)), MAE=mean(abs(f-y)), Bias=mean(f-y). RMSE/MAE nhỏ hơn tốt hơn, Bias gần0; Bias âm là dự báo thiếu. BSS/POD tốt không tự chứng minh lượng mm tốt. Không dùng MAPE với nhiều ngày mưa0 hoặc accuracy bị ngày khô chi phối làm bằng chứng chính. Đầu mm và xác suất hiện chưa chung một phân phối thống nhất; CSI của f≥q khác CSI chính của p≥τ.

## 7. Tín hiệu hiện có và phạm vi kết luận

Đã chạy72TFT/24LightGBM; 96/96replay. Ngày1, thêm riêng A/M vào TFT tăng BSS lần lượt {a.estimate:+.4f}/{m.estimate:+.4f}; CI99,44%điều chỉnh [+{a.family_adjusted_low:.4f};+{a.family_adjusted_high:.4f}] và [+{m.family_adjusted_low:.4f};+{m.family_adjusted_high:.4f}]. C chưa rõ. Đây là9phép chính, khối7ngày/20.000bootstrap; khối14ngày cùng phân loại. Chưa kiểm định M−A. Ngày2chưa có CI chính tương tự trên0; ngày3mọiE/họ có BSSâm.

Giới hạn: footprint93ô xấp xỉ, nhãn vệ tinh chưa kiểm chứng đầy đủ, ít sự kiện50/100, development đã xem trước, không chắc đầu vào ERA5 có sẵn lúc phát hành thật. Chỉ nhìn POD ngày3vẫn có thể che BSSâm. Bootstrap điều kiện mô hình đã fit, không bao phủ mọi bất định nhãn/vùng/huấn luyện.

## 8. Quy tắc in đậm trong slide

- Bảng so hai mô hình cùng ngày: đậm điểm tốt hơn trong cặp theo chiều đã ghi.
- Bảng tám E trong cùng mô hình/ngày: đậm điểm tốt nhất theo số hiển thị; bằng nhau cùng đậm. Bias chọn trị tuyệt đối nhỏ nhất.
- BSS âm màu đỏ; ít âm nhất vẫn kém khí hậu. In đậm không có nghĩa kết quả đã có ý nghĩa thống kê.
- Bảng số đếm nêu các số cần đối chiếu; chú thích rõ. Phép kiểm định A/M có CI riêng, không suy CI từ tô màu.
- Sáu bảng phụ lục có đủ48dòng và7metrics; Excel có chi tiết ngưỡng/năm/mùa/seed, không giấu điểm kém.

## 9. Nguồn tham khảo

'''
    text+='\n'.join(f'- [{r["id"]}] {r["authors"]} ({r["year"]}). [{r["title"]}]({r["url"]}).' for r in refs)
    # Keep prose spacing clear; native identifiers and formulas stay literal.
    for a,b in {"BSS0,246":"BSS 0,246","accuracy24,6%":"accuracy 24,6%","gần0":"gần 0",
                "mưa0":"mưa 0","chạy72TFT/24LightGBM":"chạy 72 TFT/24 LightGBM","96/96replay":"96/96 replay",
                "Ngày1":"Ngày 1","CI99,44%điều":"CI 99,44% điều","là9phép":"là 9 phép",
                "khối7ngày/20.000bootstrap":"khối 7 ngày/20.000 bootstrap","khối14ngày":"khối 14 ngày",
                "Ngày2chưa":"Ngày 2 chưa","trên0":"trên 0","ngày3mọiE/họ":"ngày 3 mọi E/họ",
                "BSSâm":"BSS âm","footprint93ô":"footprint 93 ô","kiện50/100":"kiện 50/100",
                "ngày3vẫn":"ngày 3 vẫn","đủ48dòng":"đủ 48 dòng","và7metrics":"và 7 metrics"}.items():text=text.replace(a,b)
    return text


if __name__=="__main__":main()
