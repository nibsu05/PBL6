"""Tạo hình 300 DPI và số liệu có thể truy vết cho báo cáo tiến độ."""
from __future__ import annotations
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".cache/matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyBboxPatch
from run_rain_alert_experiment import _jsonable

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports/professor_report"
FIG = OUT / "figures"
STUDY = ROOT / "reports/threshold_temporal_study"
COLORS = {"standard":"#224C7A", "dual_global":"#138579", "dual_precision30":"#C96E28", "persistence":"#6C7680"}
NAMES = {"standard":"Bi-LSTM chuẩn", "dual_global":"Hai đầu ngưỡng chung", "dual_precision30":"Hai đầu ngưỡng theo horizon", "persistence":"Persistence"}
plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":11, "axes.spines.top":False,
                     "axes.spines.right":False, "axes.titleweight":"bold", "figure.facecolor":"white"})


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def diagram():
    fig, ax = plt.subplots(figsize=(11,3.7)); ax.set(xlim=(0,11),ylim=(0,3.7)); ax.axis("off")
    items = [(0.2,2.3,2.25,"Nguồn dữ liệu\nOpen-Meteo · ERA5 · ONI"),
             (3,2.3,2.25,"Chuẩn hóa\nUTC+7 · đơn vị · ô lưới"),
             (5.8,2.3,2.25,"Đặc trưng\nLag · rolling · chu kỳ"),
             (8.6,2.3,2.15,"Cửa sổ\n24 giờ → 6 giờ"),
             (1,0.45,3.1,"Train 70%\nFit RobustScaler và trọng số"),
             (4.45,0.45,2.6,"Validation 15%\nCheckpoint và ngưỡng"),
             (7.4,0.45,2.6,"Test 15%\nĐánh giá hồi cứu")]
    for x,y,w,s in items:
        ax.add_patch(FancyBboxPatch((x,y),w,.9,boxstyle="round,pad=.09",fc="#ECF2F7",ec="#224C7A"))
        ax.text(x+w/2,y+.45,s,ha="center",va="center",fontsize=10)
    for x1,x2 in [(2.5,2.85),(5.3,5.65),(8.1,8.45)]:
        ax.annotate("",xy=(x2,2.75),xytext=(x1,2.75),arrowprops={"arrowstyle":"->","color":"#224C7A"})
    ax.text(5.5,1.8,"Giữ khoảng trống thời gian · không nội suy nhãn mưa · không fit scaler trên val/test",ha="center",fontsize=10)
    save(fig,"fig02_pipeline.png")


def main():
    FIG.mkdir(parents=True,exist_ok=True)
    features = pd.read_parquet(ROOT / "data/processed/surface_only/features.parquet")
    split = read_json("models/surface_only/comparison.json")["split"]
    train_end, val_end = pd.Timestamp(split["train_end"]), pd.Timestamp(split["val_end"])
    train = features.loc[features.datetime < train_end].copy()
    rain = train.precipitation
    counts = [int((rain==0).sum()), int(((rain>0)&(rain<=1)).sum()),
              int(((rain>1)&(rain<=5)).sum()), int((rain>5).sum())]
    stats = {"train_hours":len(train), "train_rain_counts":counts,
             "train_heavy_fraction":float((rain>5).mean()), "train_max_rain":float(rain.max()),
             "train_zero_fraction":float((rain==0).mean()), "split":split}
    months = pd.period_range("2015-01","2026-08",freq="M")
    cover=np.ones((3,len(months)))
    for i,m in enumerate(months.astype(str)):
        if "2024-04" <= m <= "2024-12" or "2026-03" <= m <= "2026-08": cover[1,i]=0
    fig,ax=plt.subplots(figsize=(11,2.9))
    from matplotlib.colors import ListedColormap
    ax.imshow(cover,aspect="auto",cmap=ListedColormap(["#E6A370","#477CA7"]),vmin=0,vmax=1)
    ax.set(yticks=[0,1,2],yticklabels=["Open-Meteo","ERA5 PL850","ERA5 SST"],
           xticks=list(range(0,len(months),12)),xticklabels=list(range(2015,2027)),
           title="Độ phủ tháng của dữ liệu hiện có")
    ax.text(.01,-.25,"Xanh: có dữ liệu    Cam: thiếu PL850 (15 tháng, 11.016 giờ)",transform=ax.transAxes)
    save(fig,"fig01_data_coverage.png"); diagram()

    fig,axes=plt.subplots(1,2,figsize=(11,4.2))
    bars=axes[0].bar(["0","(0; 1]","(1; 5]",">5"],counts,color=["#8D9EAC","#6492B1","#224C7A","#C96E28"])
    axes[0].set(yscale="log",ylim=(1,max(counts)*4),xlabel="Lượng mưa (mm/h)",ylabel="Số giờ (thang log)",title="Mất cân bằng trong train")
    for b,n in zip(bars,counts):axes[0].text(b.get_x()+b.get_width()/2,n*1.2,f"{n:,}\n{100*n/len(train):.2f}%",ha="center",fontsize=9)
    monthly=train.groupby(train.datetime.dt.month).precipitation.agg(["mean","count"])
    axes[1].bar(monthly.index,monthly["mean"],color="#224C7A")
    axes[1].set(xticks=range(1,13),xlabel="Tháng địa phương",ylabel="Mưa trung bình (mm/giờ quan trắc)",title="Biến thiên theo tháng trong train")
    save(fig,"fig03_train_rainfall_eda.png")

    selected={"precipitation":"Mưa hiện tại", "temperature_2m":"Nhiệt độ 2m", "relative_humidity_2m":"Độ ẩm 2m",
              "surface_pressure":"Áp suất", "wind_speed_10m":"Tốc độ gió 10m", "precip_lag_1h":"Mưa trễ 1h",
              "precip_lag_6h":"Mưa trễ 6h", "precip_lag_24h":"Mưa trễ 24h",
              "precip_roll_sum_3h":"Tổng mưa 3h trước", "precip_roll_sum_24h":"Tổng mưa 24h trước"}
    correlations=[]
    for col in selected:
        correlations.append([train[col].corr(train.precipitation.shift(-h)) for h in (1,6)])
    corr=np.array(correlations)
    fig,ax=plt.subplots(figsize=(8.5,5))
    im=ax.imshow(corr,aspect="auto",cmap="RdBu_r",vmin=-1,vmax=1)
    ax.set(yticks=range(len(selected)),yticklabels=list(selected.values()),xticks=[0,1],
           xticklabels=["Mưa t+1","Mưa t+6"],title="Tương quan đặc trưng với nhãn tương lai trên train")
    for i in range(len(selected)):
        for j in range(2):ax.text(j,i,f"{corr[i,j]:.2f}",ha="center",va="center",color="white" if abs(corr[i,j])>.55 else "black")
    fig.colorbar(im,ax=ax,label="Pearson r")
    save(fig,"fig04_train_feature_correlations.png")

    fig,ax=plt.subplots(figsize=(11,3.5)); ax.axis("off"); ax.set(xlim=(0,11),ylim=(0,3.5))
    for x,y,w,h,label in [(0.1,1.2,2.2,1.1,"Input 24 × 22\nChỉ dữ liệu quá khứ"),(3,1.2,3,1.1,"Bi-LSTM 2 tầng\n50 hidden mỗi chiều\nDropout 0,2"),(7,2,3.7,.8,"Đầu lượng mưa\n6 giá trị không âm"),(7,.35,3.7,.8,"Đầu cảnh báo ở giai đoạn 2\n6 xác suất mưa >5 mm/h")]:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=.08",fc="#F1F5F8",ec="#224C7A"));ax.text(x+w/2,y+h/2,label,ha="center",va="center",fontsize=11)
    for start,end in [((2.4,1.75),(2.9,1.75)),((6.1,1.9),(6.9,2.4)),((6.1,1.55),(6.9,.75))]:
        ax.annotate("",xy=end,xytext=start,arrowprops={"arrowstyle":"->","color":"#224C7A"})
    save(fig,"fig05_architecture.png")

    fig,axes=plt.subplots(1,2,figsize=(11,4.2))
    for ax,path,title,valkey in [(axes[0],"plots/surface_only/standard/training_history.csv","Giai đoạn 1 — Weighted MSE","val_loss"),
                                (axes[1],"reports/rain_alert_experiment/training_history.csv","Giai đoạn 2 — Huber + BCE","validation_loss")]:
        h=pd.read_csv(ROOT/path);ax.plot(h.epoch,h.train_loss,"o-",label="Train",color="#224C7A");ax.plot(h.epoch,h[valkey],"o-",label="Validation",color="#C96E28")
        best=int(h.loc[h[valkey].idxmin(),"epoch"]);ax.axvline(best,color="#138579",ls="--",label=f"Chọn epoch {best}")
        ax.set(xlabel="Epoch",ylabel="Loss theo hàm riêng",title=title);ax.legend(fontsize=9);ax.grid(alpha=.2)
    save(fig,"fig06_training_curves.png")

    metrics=pd.read_csv(STUDY/"test_metrics.csv"); horizon=pd.read_csv(STUDY/"test_metrics_by_horizon.csv")
    fig,axes=plt.subplots(1,3,figsize=(12,4.2))
    for policy in ("standard","dual_global","dual_precision30","persistence"):
        s=horizon[horizon.policy==policy]
        # Hai chính sách ngưỡng có cùng lượng mưa; chỉ vẽ một đường hồi quy.
        if policy!="dual_precision30":axes[0].plot(s.horizon_h,s.RMSE,"o-",color=COLORS[policy],label=NAMES[policy])
        axes[1].plot(s.horizon_h,s.POD_recall,"o-",color=COLORS[policy],label=NAMES[policy])
        axes[2].plot(s.horizon_h,s.precision,"o-",color=COLORS[policy],label=NAMES[policy])
    for ax in axes:ax.set(xlabel="Horizon (giờ)",xticks=range(1,7));ax.grid(alpha=.2)
    axes[0].set(title="RMSE lượng mưa",ylabel="mm/h")
    axes[1].set(title="Recall giờ mưa >5",ylim=(0,.65));axes[2].set(title="Precision giờ mưa >5",ylim=(0,.65))
    axes[1].legend(fontsize=8,loc="upper right")
    save(fig,"fig07_test_horizon_skill.png")

    fig,axes=plt.subplots(1,2,figsize=(11,4.2))
    policies=["dual_global","dual_precision30","standard","persistence"]
    subset=metrics.set_index("policy").loc[policies]
    x=np.arange(4)
    axes[0].bar(x-.18,subset.TP,width=.36,label="Phát hiện đúng (TP)",color="#138579")
    axes[0].bar(x+.18,subset.FP,width=.36,label="Cảnh báo sai (FP)",color="#C96E28")
    for k,(tp,fp) in enumerate(zip(subset.TP,subset.FP)):
        axes[0].text(k-.18,tp+18,str(tp),ha="center",fontsize=9);axes[0].text(k+.18,fp+18,str(fp),ha="center",fontsize=9)
    axes[0].set(xticks=x,xticklabels=["Hai đầu\nngưỡng 0,40","Hai đầu\nngưỡng riêng","Bi-LSTM\nchuẩn","Persistence"],ylabel="Số cặp horizon–giờ",title="Đánh đổi trên test cũ");axes[0].legend(fontsize=9)
    cfg=read_json("reports/threshold_temporal_study/selected_thresholds.json")
    axes[1].plot(range(1,7),[h["threshold"] for h in cfg["horizons"]],"o-",color="#C96E28",lw=2)
    axes[1].axhline(.4,ls="--",color="#138579",label="Ngưỡng chung 0,40")
    axes[1].set(xticks=range(1,7),ylim=(.3,.9),xlabel="Horizon (giờ)",ylabel="Ngưỡng xác suất",title="Ngưỡng chọn chỉ bằng validation");axes[1].legend(fontsize=9)
    save(fig,"fig08_threshold_tradeoff.png")

    table=pd.read_parquet(STUDY/"test_predictions.parquet")
    first=table[table.horizon_h==1].sort_values("valid_datetime")
    peak=first.loc[first.actual_mm.idxmax(),"valid_datetime"]
    fig,axes=plt.subplots(2,1,figsize=(11,6.4),sharex=True)
    peak_stats=[]
    for ax,h in zip(axes,(1,6)):
        s=table[(table.horizon_h==h)&table.valid_datetime.between(peak-pd.Timedelta(hours=36),peak+pd.Timedelta(hours=36))].sort_values("valid_datetime")
        ax.plot(s.valid_datetime,s.actual_mm,color="black",lw=2,label="Nhãn Open-Meteo")
        for col,c,label in [("standard_amount_mm","#224C7A","Bi-LSTM chuẩn"),("dual_amount_mm","#138579","Hai đầu"),("persistence_mm","#6C7680","Persistence")]:
            ax.plot(s.valid_datetime,s[col],color=c,label=label,alpha=.9)
        ax.set(title=f"Dự báo t+{h}",ylabel="mm/h");ax.grid(alpha=.2)
        at_peak=s.loc[s.valid_datetime==peak].iloc[0]
        peak_stats.append({"horizon":h,"actual":float(at_peak.actual_mm),"standard":float(at_peak.standard_amount_mm),"dual":float(at_peak.dual_amount_mm),"persistence":float(at_peak.persistence_mm)})
    axes[0].legend(ncol=2,fontsize=9)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %Hh",tz=peak.tzinfo))
    axes[-1].set_xlabel("Giờ địa phương UTC+7")
    save(fig,"fig09_heavy_event_example.png")
    stats["example_peak_time"]=peak.isoformat();stats["example_peak_predictions"]=peak_stats

    temporal=pd.read_csv(STUDY/"temporal_metrics.csv")
    fig,axes=plt.subplots(1,2,figsize=(11,4.4))
    for j,policy in enumerate(policies):
        s=temporal[temporal.policy==policy].set_index("period").loc[["F1","F2","F3"]]
        for ax,col in zip(axes,["event_F1","recall"]):ax.bar(np.arange(3)+(j-1.5)*.19,s[col],width=.18,label=NAMES[policy],color=COLORS[policy])
    for ax in axes:ax.set(xticks=range(3),xticklabels=["F1\n07–12/2023","F2\n01–06/2024","F3\n07–11/2024"],ylim=(0,.65));ax.grid(axis="y",alpha=.2)
    axes[1].set_ylim(0,1)
    axes[0].set(title="F1 theo đợt trên giai đoạn kế tiếp");axes[1].set(title="Recall giờ mưa lớn trên giai đoạn kế tiếp")
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc="lower center",ncol=2,fontsize=9,bbox_to_anchor=(.5,0),frameon=False)
    fig.tight_layout(rect=(0,.16,1,1))
    fig.savefig(FIG / "fig10_temporal_stability.png",dpi=300,bbox_inches="tight",facecolor="white")
    plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(10.5,4.5))
    for ax,h in zip(axes,(1,6)):
        s=table[table.horizon_h==h]
        ax.scatter(s.actual_mm,s.dual_amount_mm,s=9,alpha=.22,c="#138579",edgecolors="none")
        upper=float(max(s.actual_mm.max(),s.dual_amount_mm.max()))*1.03
        ax.plot([0,upper],[0,upper],"--",color="black",lw=1)
        ax.set(xlim=(0,upper),ylim=(0,upper),aspect="equal",xlabel="Nhãn Open-Meteo (mm/h)",ylabel="Dự báo hai đầu (mm/h)",title=f"Test cũ tại t+{h}")
    save(fig,"fig11_actual_prediction_scatter.png")

    stats["test_metrics"]=metrics.to_dict("records")
    stats["validation_metrics"]=pd.read_csv(STUDY/"validation_metrics.csv").to_dict("records")
    stats["temporal_metrics"]=temporal.to_dict("records")
    stats["folds"]=read_json("reports/threshold_temporal_study/fold_summary.json")
    stats["thresholds"]=cfg
    stats["baseline"]=read_json("models/surface_only/comparison.json")
    stats["noaa"]=read_json("reports/independent_observations/noaa_audit_2025.json")
    stats["availability"]=read_json("reports/realtime_readiness/availability_audit.json")
    stats["merge"]=read_json("data/processed/merge_diagnostics.json")
    stats["multisource_test"]=read_json("plots/test_metrics.json")
    stats["matched_surface_ablation"]=read_json("models/ablation_surface_only_results.json")
    (OUT/"report_data.json").write_text(json.dumps(_jsonable(stats),ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    print(f"saved={FIG}; figures=11")


if __name__=="__main__":main()
