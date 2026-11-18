"""Readable research report and figures from independently verified results."""
from pathlib import Path
import json
import sys
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Cm, Pt
from src.gfs_final import BASE, PUBLIC, protocol, progress
from src.gfs_daily import sha, write_json
from src.gfs_final_gate import check_manifest

SCOPES = {"dev2024_legacy": "Phát triển 2024 — legacy",
          "test2025_legacy": "Kiểm định 2025 — legacy",
          "external2026_legacy": "Kiểm tra 2026 — legacy",
          "external2026_modern": "Kiểm tra 2026 — modern"}
ORDER = ["ZERO", "CLIM", "PERSISTENCE", "GFS", "MOS", *[f"LGB_N{k}" for k in range(6)],
         "LGB_N3_delay3", "LGB_N3_delay6", "GRU_N3", "GRU_N5", "GRU_N3_LINEAR6", "GRU_N3_WIDE"]


def fmt(x, places=3):
    return "—" if not np.isfinite(x) else f"{x:.{places}f}".replace(".", ",")


def number(x):
    return f"{int(x):,}".replace(",", ".")


def md_table(headings, rows):
    return "\n".join(["| "+" | ".join(headings)+" |", "| "+" | ".join(["---"]*len(headings))+" |"] +
                     ["| "+" | ".join(map(str, row))+" |" for row in rows])


def amount_table(point, scope):
    part = point[point.evaluation_set.eq(scope)]
    matrix = []
    for model in ORDER:
        row = []
        for fun, metric in [("mean", "macro_rmse"), ("median", "macro_mae")]:
            for h in (1, 2, 3):
                selected = part[part.model.eq(model) & part.functional.eq(fun) & part.horizon.eq(h)]
                row.append(float(selected.iloc[0][metric]))
        matrix.append(row)
    values = np.asarray(matrix)
    best = values.min(0)
    rows = []
    for model, row in zip(ORDER, values):
        cells = [f"**{fmt(v)}**" if abs(v-best[j]) < 1e-9 else fmt(v) for j, v in enumerate(row)]
        rows.append([model, *cells])
    return md_table(["Phương án", "RMSE mean D1", "D2", "D3", "MAE median D1", "D2", "D3"], rows)


def main():
    p = protocol()
    check_manifest()
    verification = json.loads((PUBLIC / "final_verification.json").read_text())
    if verification["status"] != "passed":
        raise ValueError("Independent verification is required before publishing")
    point = pd.read_csv(PUBLIC / "point_metrics.csv")
    prob = pd.read_csv(PUBLIC / "probability_metrics.csv")
    event = pd.read_csv(PUBLIC / "event_metrics.csv")
    ci = pd.read_csv(PUBLIC / "paired_bootstrap.csv")
    labels = pd.read_csv(PUBLIC / "label_distribution.csv")
    manifest = json.loads((PUBLIC / "final_manifest.json").read_text())
    opening = json.loads((BASE / "holdout_opened.json").read_text())
    test = ci[ci.evaluation_set.eq("test2025_legacy")]
    feature = test[test.family.eq("feature")]
    skill = test[test.family.eq("skill")]
    descriptions = {("LGB_N1", "LGB_N0"): "Khí tượng thô N1–N0 (LightGBM)",
                    ("LGB_N3", "LGB_N1"): "Địa hình N3–N1 (LightGBM)",
                    ("GRU_N5", "GRU_N3_LINEAR6"): "Dẫn xuất N5–LINEAR6 (GRU)"}
    conclusions = []
    for pair, title in descriptions.items():
        s = feature[feature.model.eq(pair[0]) & feature.reference.eq(pair[1])].sort_values("horizon")
        days = s.loc[s.primary_improvement_supported, "horizon"].astype(str).tolist()
        conclusions.append(f"- **{title}:** đủ tiêu chí cải thiện trên test ở ngày {', '.join(days)}." if days else
                           f"- **{title}:** chưa đủ tiêu chí xác nhận cải thiện trên test sau hiệu chỉnh nhiều so sánh.")
    for model, fun, metric in [("LGB_N3", "mean", "RMSE mean"), ("GRU_N5", "median", "MAE median")]:
        s = skill[skill.model.eq(model)].sort_values("horizon")
        days = s.loc[s.primary_improvement_supported, "horizon"].astype(str).tolist()
        conclusions.append(f"- **{model} so MOS, {metric}:** đủ tiêu chí cải thiện ở ngày {', '.join(days)}." if days else
                           f"- **{model} so MOS, {metric}:** chưa đủ tiêu chí xác nhận cải thiện sau hiệu chỉnh.")
    findings = "\n".join(conclusions)
    coverage_rows = []
    coverage_notes = []
    for scope in SCOPES:
        s = labels[labels.evaluation_set.eq(scope)].sort_values("horizon")
        first = s.iloc[0]
        coverage_rows.append([SCOPES[scope], number(first.samples), int(first.stations), int(first.issue_dates),
            "/".join(str(int(v)) for v in s.events_ge50), "/".join(str(int(v)) for v in s.issue_dates_ge50)])
        a = pd.Timestamp(first.first_issue_utc).tz_convert("Asia/Ho_Chi_Minh").strftime("%d/%m/%Y")
        b = pd.Timestamp(first.last_issue_utc).tz_convert("Asia/Ho_Chi_Minh").strftime("%d/%m/%Y")
        coverage_notes.append(f"- {SCOPES[scope]}: các issue hợp lệ từ {a} đến {b}.")
    dev_label = labels[labels.evaluation_set.eq("dev2024_legacy") & labels.horizon.eq(1)].iloc[0]
    test_label = labels[labels.evaluation_set.eq("test2025_legacy") & labels.horizon.eq(1)].iloc[0]
    peak_audit = json.loads((PUBLIC / "peak_label_audit.json").read_text())
    comparisons = []
    for row in pd.concat([feature, skill]).sort_values(["family", "model", "reference", "horizon"]).itertuples():
        comparisons.append([f"{row.model} − {row.reference}", int(row.horizon), row.metric,
            fmt(row.difference), f"[{fmt(row.ci95_low)}; {fmt(row.ci95_high)}]",
            f"[{fmt(row.simultaneous_ci_low)}; {fmt(row.simultaneous_ci_high)}]",
            "Có" if row.primary_improvement_supported else "Chưa đủ"])
    event_rows = []
    for model in ("GFS", "MOS", "LGB_N3", "GRU_N5"):
        for h in (1, 2, 3):
            s = event[event.evaluation_set.eq("test2025_legacy") & event.model.eq(model) & event.horizon.eq(h) & event.threshold_mm.eq(50)]
            s = s[s.decision_rule.eq("calibration_selected")] if s.decision_rule.eq("calibration_selected").any() else s[s.decision_rule.eq("fixed_0.5")]
            e = s.iloc[0]
            b = prob[prob.evaluation_set.eq("test2025_legacy") & prob.model.eq(model) & prob.horizon.eq(h) & prob.threshold_mm.eq(50)].iloc[0]
            event_rows.append([model, h, fmt(b.macro_bss), fmt(e.macro_csi), fmt(e.macro_pod), fmt(e.macro_far), fmt(e.cutoff, 2)])
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    names = ["GFS", "MOS", "LGB_N3", "GRU_N5", "GRU_N3_LINEAR6"]
    fig, ax = plt.subplots(figsize=(10, 4.7))
    for j, model in enumerate(names):
        sub = point[point.evaluation_set.eq("test2025_legacy") & point.model.eq(model) & point.functional.eq("mean")].sort_values("horizon")
        ax.bar(np.arange(3)+(j-2)*.15, sub.macro_rmse, width=.14, label=model)
    ax.set_xticks(np.arange(3), ["Ngày 1", "Ngày 2", "Ngày 3"])
    ax.set_ylabel("RMSE đầu mean (mm), thấp hơn tốt hơn")
    ax.set_title("Kiểm định 2025 — cùng mẫu và 57 trạm")
    ax.legend(fontsize=8, ncol=3)
    ax.grid(axis="y", alpha=.2)
    fig.tight_layout()
    fig.savefig(PUBLIC / "rmse_test2025.png", dpi=180)
    plt.close(fig)
    f = feature.sort_values(["model", "reference", "horizon"]).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(10.5, 6))
    for i, row in enumerate(f.itertuples()):
        color = "#157347" if row.primary_improvement_supported else "#9b5b15"
        ax.plot([row.simultaneous_ci_low, row.simultaneous_ci_high], [i, i], color=color, linewidth=2)
        ax.scatter([row.difference], [i], color=color, s=32)
    ax.axvline(0, color="#666666", linestyle="--")
    ax.set_yticks(np.arange(len(f)), [descriptions[(r.model, r.reference)]+f" · D{r.horizon}" for r in f.itertuples()])
    ax.invert_yaxis()
    ax.set_xlabel("Chênh RMSE mean (mm); âm có lợi cho mô hình đứng trước")
    ax.set_title("Ba câu hỏi đặc trưng trên test 2025 — khoảng đồng thời Bonferroni")
    fig.tight_layout()
    fig.savefig(PUBLIC / "feature_test_ci.png", dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
    for model in ("MOS", "LGB_N3", "GRU_N5"):
        s = event[event.evaluation_set.eq("test2025_legacy") & event.model.eq(model) & event.threshold_mm.eq(50) & event.decision_rule.eq("calibration_selected")].sort_values("horizon")
        axes[0].plot(s.horizon, s.macro_pod, marker="o", label=model)
        axes[1].plot(s.horizon, s.macro_far, marker="o", label=model)
    for ax, title in zip(axes, ["POD: bắt được sự kiện thực tế", "FAR: báo nhầm trong các lần cảnh báo"]):
        ax.set_title(title)
        ax.set_xticks([1, 2, 3], ["D1", "D2", "D3"])
        ax.set_ylim(0, 1)
        ax.grid(alpha=.2)
    axes[1].legend(fontsize=8)
    fig.suptitle("Test 2025, ngưỡng nghiên cứu 50mm/24h; cutoff chọn từ 2023")
    fig.tight_layout()
    fig.savefig(PUBLIC / "heavy_event_test2025.png", dpi=180)
    plt.close(fig)
    lock_time = pd.Timestamp(manifest["locked_utc"]).tz_convert("Asia/Ho_Chi_Minh").strftime("%H:%M:%S %d/%m/%Y")
    test_time = pd.Timestamp(opening["first_model_evaluation_opened_utc"]).tz_convert("Asia/Ho_Chi_Minh").strftime("%H:%M:%S %d/%m/%Y")
    report = f"""# Báo cáo kiểm chứng cuối — dự báo mưa ngắn hạn tại trạm

Bản công bố 17/11/2026. Đã thực hiện đối chứng dung lượng mạng, khóa mô hình và kiểm định 2025; đánh giá 2026 tách theo API. Dữ liệu/chấm điểm thuộc nhánh GFS–Vrain, độc lập với bộ ERA5 giờ của Bi-LSTM. Kết quả cũ được giữ nguyên.

## 1. Kết luận đọc trước

{findings}

Các kết luận trên áp dụng cho mô hình và 57 trạm đã khóa, theo tiêu chí định trước. Một chênh lệch điểm số nhỏ hơn 0 chưa đủ để kết luận cải thiện: cần xem khoảng bất định và hiệu chỉnh nhiều so sánh. Không đổi mô hình chính sau khi xem bảng test.

## 2. Đầu vào, đầu ra và cách chia dữ liệu

Mỗi ngày lúc 19h Việt Nam, mỗi trạm có một mẫu; nhãn là ba tổng mưa Vrain riêng trong 0–24h, 24–48h và 48–72h. Ví dụ phát lúc 19h thứ hai, nhãn ngày 1 kết thúc 19h thứ ba; ngày 2 là từ 19h thứ ba đến 19h thứ tư. Mưa thiếu không được thay bằng 0 hay lấp bằng GFS/ERA5/vệ tinh.

Đầu vào gồm bảy tổng mưa ngày quá khứ, tổng 1/6/24h gần nhất kết thúc trước thời điểm phát tin theo giả định trễ 1h, lịch/vị trí/ID, mưa và khí tượng dự báo GFS, địa hình. GFS 00UTC khởi tạo trước issue 12UTC; trạng thái khí tượng +24/+48/+72h là giữa cửa sổ, không phải trung bình ngày. Nội suy 0,25° tới trạm không tạo thêm độ phân giải thật.

| Cấu hình | Số biến | Bổ sung |
| --- | ---: | --- |
| N0 | 16 | Mưa GFS, lịch/vị trí/ID và lịch sử mưa trạm |
| N1 | 21 | N0 + nhiệt, RH, u/v850 và PWAT |
| N2 | 25 | N1 + q850, q×u, q×v và tốc độ gió |
| N3 | 26 | N1 + năm biến địa hình |
| N4 | 30 | N3 + bốn dẫn xuất gió–ẩm |
| N5 | 32 | N4 + gió·độ dốc và dòng ẩm·độ dốc |

Train 2021–2022 có 35.116 mẫu trạm–issue, cal 2023 có 18.365, dev 2024 có 19.405, mỗi mẫu ba hạn. Mọi biến đổi có học được fit chỉ trên train. Cal 2023 chỉ hiệu chỉnh xác suất và cutoff; không dùng early stopping. Tập 57 trạm được chọn bằng train, không chọn lại theo điểm 2025/2026.

{md_table(['Tập đánh giá', 'Mẫu trạm–issue', 'Trạm', 'Ngày issue', 'Sự kiện≥50 D1/D2/D3', 'Ngày issue có≥50 D1/D2/D3'], coverage_rows)}

{chr(10).join(coverage_notes)}

Sự kiện trong bảng là trạm–ngày, không phải số cơn bão hay các mẫu độc lập. Cùng một đợt mưa có thể xuất hiện ở nhiều trạm và hạn. Số mẫu giữa hai API 2026 khác nhau; không so trực tiếp hai trung bình rồi quy nguyên nhân cho mô hình hay API. Riêng legacy 2026 chỉ có hai sự kiện trạm–ngày ≥50mm ở một ngày issue cho mỗi hạn, nên không đủ để đánh giá ổn định khả năng cảnh báo mưa lớn.

Phân phối nhãn cũng khác giữa hai năm: ở ngày 1, mưa trung bình từ nguồn là {fmt(dev_label.mean_mm)}mm trên dev 2024 và {fmt(test_label.mean_mm)}mm trên test 2025; nhãn lớn nhất là {fmt(dev_label.maximum_mm, 1)} và {fmt(test_label.maximum_mm, 1)}mm. Đã đối chiếu hậu nghiệm {peak_audit['labels_checked']} nhãn lớn với đủ 24 giờ và tổng ngày gốc của Vrain: khớp về cấu trúc/tổng, chưa xác nhận được độ chính xác cảm biến. Không bỏ các nhãn lớn hoặc thay đổi điểm test sau kiểm tra này. Không quy toàn bộ chênh lệch điểm giữa hai năm thành overfitting hay thay đổi khí hậu từ riêng các thống kê này.

## 3. Đối chứng dung lượng GRU

N3 gốc có 4.364 tham số, N5 gốc có 4.796. Hai đối chứng mới là N3_LINEAR6 có đúng 4.796 tham số và N3_WIDE có 4.751 (head 27, lệch 45 tham số so N5). LINEAR6 thêm sáu tổ hợp tuyến tính cố định của 10 biến khí tượng thô/địa hình, chuẩn hóa chỉ bằng train; không thêm quan trắc hoặc thông tin nhãn. Ma trận tổ hợp và seed đã ghi trong protocol trước fit.

Cả hai đối chứng dùng ba seed 17/29/43, hidden 16, learning rate 0,001, batch 256, 17 epoch cố định, cùng loss và optimizer với GRU cũ. Không tìm thêm siêu tham số. N3_WIDE được chọn head 27 chỉ vì gần số tham số N5 nhất tại hidden 16; không chọn theo điểm phát triển/test. Seed là số khởi tạo quá trình ngẫu nhiên; ba seed giúp thấy dao động khi khởi tạo và xáo trộn mẫu khác nhau, không phải ba bộ dữ liệu độc lập.

Phép so N5 với LINEAR6 kiểm tra giá trị của dẫn xuất phi tuyến vượt việc thêm các kênh tuyến tính dư thừa, trong cùng kích thước mạng. Phép so với WIDE kiểm tra độ nhạy với số tham số gần tương đương. Các mạng vẫn khác cách biểu diễn và tối ưu; kết quả không phải chứng minh nhân quả vật lý.

## 4. Mô hình và nguyên tắc khóa trước kiểm định

Có 17 phương án trong bảng: ZERO, khí hậu CLIM, persistence, GFS, MOS, LightGBM N0–N5 và N3 trễ 3/6h, GRU N3/N5 và hai đối chứng mới. MOS là hiệu chỉnh thống kê đơn giản của GFS, giúp kiểm tra ML có hơn một cách sửa sai số dễ triển khai hay không. Persistence lặp lại lượng mưa 24h gần nhất; CLIM dùng thống kê khí hậu theo trạm/tháng chỉ từ train; ZERO luôn dự báo 0mm.

Mô hình lượng mưa chính được chốt là **LightGBM N3**, ứng viên đầu trung vị là **GRU N5**. Các checkpoint, chuẩn hóa, calibrator, cutoff và mã suy luận/chấm đã được khóa SHA lúc **{lock_time}** giờ Việt Nam; lần mở đánh giá mô hình trên hàng kiểm định bắt đầu **{test_time}**. Việc nguồn 2025 đã được tải/QC trước đó được ghi rõ; không gọi toàn kho chưa từng đọc 2025.

Sau khóa không có fit/tuning/hiệu chỉnh/cutoff mới hoặc đổi mô hình chính dựa trên test. Dự báo mean và median là hai đại lượng khác nhau: đầu mean đánh giá chính bằng RMSE, đầu median bằng MAE. Không chọn đầu có điểm đẹp hơn cho từng metric sau khi nhìn kết quả. Xác suất ≥50 bằng xác suất ≥1 nhân xác suất ≥50 khi đã mưa ≥1; hiệu chỉnh và ensemble vẫn giữ p50≤p1.

## 5. Kết quả lượng mưa trên kiểm định 2025

Đơn vị mm, macro là trung bình đều giữa các trạm. Chữ đậm chỉ điểm thấp nhất trong từng cột của bảng, không thay đổi lựa chọn mô hình chính đã khóa. ZERO có thể cạnh tranh về MAE khi nhiều ngày khô nhưng không vì thế trở thành dự báo mưa lớn hữu ích.

{amount_table(point, 'test2025_legacy')}

![RMSE trên test2025](rmse_test2025.png)

## 6. Bằng chứng cải thiện và bất định

Ba phép so đặc trưng ở ba hạn tạo một họ 9 so sánh; hai phép so kỹ năng với MOS ở ba hạn tạo một họ 6 so sánh. Bootstrap ghép cặp khối 14 ngày, 5.000 lần, giữ các trạm/hạn cùng lịch. Khoảng đồng thời Bonferroni được hiệu chỉnh trong từng họ, không phải một tuyên bố kiểm soát chung cho mọi bảng và mọi metric. P từ bootstrap định tâm và hiệu chỉnh Holm là xấp xỉ, không phải kiểm định hoán vị chính xác.

Trong bảng dưới, chênh âm có lợi cho mô hình đứng trước. “Có” yêu cầu đồng thời chênh âm, cận trên khoảng đồng thời <0 và p Holm <0,05. “Chưa đủ” có thể gồm cải thiện điểm nhưng bất định lớn, không cải thiện, hoặc kết quả ngược chiều. Khoảng percentile và p bootstrap định tâm không phải hai cách diễn đạt tương đương trong phân phối bất đối xứng; tiêu chí đã khóa yêu cầu cả hai cùng đạt. Các bảng khác được ghi thăm dò.

{md_table(['Mô hình − tham chiếu', 'Ngày', 'Metric', 'Chênh', 'CI95%', 'Khoảng đồng thời', 'Đủ tiêu chí'], comparisons)}

![Đối chiếu đặc trưng](feature_test_ci.png)

Khoảng này điều kiện theo ensemble ba seed đã fit, chưa bao gồm sai số cảm biến hoặc mọi lần huấn luyện có thể xảy ra. Dao động theo seed được báo riêng trong `holdout_seed_metrics.csv`. Tập 2024 đã được xem trước, nên các khoảng trên 2024 vẫn là phân tích phát triển dù đã hiệu chỉnh nhiều phép so sánh.

## 7. Xác suất và mưa lớn

Ngưỡng 50mm/24h là ngưỡng nghiên cứu thăm dò, chưa nhận là chuẩn cảnh báo chính thức. Cutoff xác suất chọn bằng cross-fit 2023, giữ nguyên cho 2025 và 2026. BS là sai số bình phương của xác suất dự báo; thấp hơn tốt hơn. BSS dương nghĩa BS tốt hơn khí hậu tham chiếu chỉ fit bằng train; BSS âm nghĩa kém hơn tham chiếu theo cách tính đã nêu.

POD là tỷ lệ sự kiện thực tế bắt được. FAR là tỷ lệ cảnh báo bị nhầm trong các lần đã cảnh báo. Ví dụ FAR 0,6 nghĩa khoảng 60% lần cảnh báo không có sự kiện theo ngưỡng đó. CSI cân nhắc cả trúng/bỏ sót/báo nhầm. Không có mốc POD 0,4 tốt chung cho mọi ngưỡng, hạn và khu vực. Các chỉ số dưới là macro; xem CSV để có micro và số đếm H/M/F.

{md_table(['Mô hình', 'Ngày', 'BSS50', 'CSI50', 'POD50', 'FAR50', 'Cutoff'], event_rows)}

![POD và FAR](heavy_event_test2025.png)

## 8. Tái hiện phát triển 2024 và kiểm tra 2026

Hai API đều thuộc Vrain; legacy/modern là tên dự án đặt cho đường truy xuất, không phải xác nhận hai cảm biến hoặc hai cấp chất lượng. Chưa có xác nhận chính thức về nguyên nhân khác độ phủ hay tính liên tục. Các mẫu giữ cùng API cho lịch sử và nhãn; điều này không chứng minh phân phối giữa các năm không thay đổi.

### Phát triển 2024

{amount_table(point, 'dev2024_legacy')}

### Năm 2026 — legacy

{amount_table(point, 'external2026_legacy')}

### Năm 2026 — modern

{amount_table(point, 'external2026_modern')}

Năm 2026 chỉ đến issue 12/11, chưa đủ năm và độ phủ từng API thay đổi theo tháng. Đây là kiểm tra độ bền kèm giới hạn nguồn; không tự quy thay đổi điểm cho riêng mô hình, khí hậu hay API. Có bảng theo tháng/từng trạm riêng; số mẫu và số sự kiện phải đọc kèm mọi phép so sánh. Bảng theo trạm và dự báo từng thời điểm nằm private.

## 9. Những gì đã kiểm chứng và chưa chứng minh

Đã tái hiện toàn bộ 218.658 hàng phát triển và 68 cột dự báo, chuẩn hóa/projection chỉ fit trên train, sáu checkpoint mới, các calibrator 2023, và thử đổi nhãn tương lai mà không đổi dự báo. Kiểm tra độc lập cuối gồm {number(verification['holdout_rows_checked'])} hàng kiểm định, {number(verification['independent_metric_checks'])} đối chiếu metric, {number(verification['seed_metric_checks'])} đối chiếu seed và {number(verification['primary_bootstrap_checks'])} đối chiếu bootstrap. {verification['old_artifacts_preserved']} artifact cũ/slide được giữ nguyên. Có 26 tests liên quan đạt trước mở test.

Chưa chứng minh độ chính xác cảm biến, lịch sử di chuyển tọa độ, tính liên tục hai API hoặc dữ liệu lịch sử đã có sẵn đúng thời điểm phát tin. Trễ GFS 8h/Vrain 1h vẫn là giả định; kết quả trễ 3/6h trong bảng không tự giải quyết độ trễ thật. Không tuyên bố vượt paper khác khi khác khu vực/nhãn/hạn/split. Cả 2025 và phần 2026 này nay đã được chấm: thí nghiệm tiếp theo dùng chúng để chỉnh mô hình phải gọi đúng là phát triển mới, và cần giai đoạn/địa bàn chưa sử dụng nếu muốn có kiểm định độc lập mới.

## 10. Tái lập và bàn giao

Protocol: `protocol.json`; khóa cuối: `final_manifest.json`; kiểm tra độc lập: `control_verification.json`, `final_verification.json`; toàn bộ bảng ở CSV cùng thư mục. Checkpoint, dự báo theo trạm/thời điểm và raw ở `data/operational/{PUBLIC.name}/`, không đưa lên GitHub công khai. Các script prepare/runcontrols/verifycontrols/score/verifyresults/publish mang tiền tố gfs_final hoặc gfs_capacity_controls; scripts cũ không bị ghi đè.

Tham khảo nguyên tắc không dùng test để chọn mô hình: [scikit-learn](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage). Định nghĩa BS/BSS/CSI/POD/FAR giữ cùng thí nghiệm daily-v2 để so sánh nhất quán.
"""
    (PUBLIC / "BAO_CAO_KIEM_DINH.md").write_text(report, encoding="utf8", newline="\n")
    conclusion = "# Kết quả kiểm chứng cuối\n\n"+findings+"\n\n" + (
        "Các tiêu chí và mô hình đã khóa trước test. Xem chênh lệch và khoảng đồng thời trong báo cáo; "
        "không suy ra mọi dẫn xuất đều hữu ích hoặc một mô hình thắng mọi mục tiêu. "
        "Năm 2026 báo riêng hai API Vrain vì chưa xác nhận liên tục, không đủ năm.\n\n"
        "[Báo cáo đầy đủ](BAO_CAO_KIEM_DINH.md) · [Word](BAO_CAO_KIEM_DINH.docx) · "
        "[Bảng kết quả](point_metrics.csv) · [Các đối chiếu](paired_bootstrap.csv).\n")
    (PUBLIC / "KET_LUAN.md").write_text(conclusion, encoding="utf8", newline="\n")
    doc = Document()
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Cm(1.6)
    section.left_margin = section.right_margin = Cm(1.5)
    doc.styles["Normal"].font.name = "Arial"
    doc.styles["Normal"].font.size = Pt(9)
    lines = report.splitlines()
    i = 0
    def add_rich(paragraph, text):
        for j, part in enumerate(text.replace("`", "").split("**")):
            paragraph.add_run(part).bold = bool(j % 2)
    while i < len(lines):
        line = lines[i]
        if line.startswith("| "):
            block = []
            while i < len(lines) and lines[i].startswith("| "):
                block.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            table = doc.add_table(rows=1, cols=len(block[0]))
            table.style = "Light Shading Accent 1"
            from docx.oxml import OxmlElement
            table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
            for cell, text in zip(table.rows[0].cells, block[0]):
                add_rich(cell.paragraphs[0], text)
            for row in block[2:]:
                for cell, text in zip(table.add_row().cells, row):
                    add_rich(cell.paragraphs[0], text)
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.font.size = Pt(8)
            continue
        if line.startswith("!["):
            path = PUBLIC / line.split("(", 1)[1].rstrip(")")
            doc.add_picture(str(path), width=Cm(17))
        elif line.startswith("# "):
            doc.add_heading(line[2:], 0)
        elif line.startswith("## "):
            doc.add_heading(line[3:], 1)
        elif line.startswith("### "):
            doc.add_heading(line[4:], 2)
        elif line.startswith("- "):
            add_rich(doc.add_paragraph(style="List Bullet"), line[2:])
        elif line.strip():
            add_rich(doc.add_paragraph(), line)
        i += 1
    doc.save(PUBLIC / "BAO_CAO_KIEM_DINH.docx")
    readme = f"""# Kiểm chứng cuối dự báo mưa ngắn hạn — 17/11/2026

Đã hoàn thành đối chứng GRU, khóa mô hình trước test 2025 và chấm riêng 2026 theo nguồn.
Mô hình chính/tiêu chí không đổi sau khi xem test; 17 phương án cùng mẫu, 57 trạm cố định.

Đọc [kết luận](KET_LUAN.md), [báo cáo](BAO_CAO_KIEM_DINH.md), [Word gửi nhóm](BAO_CAO_KIEM_DINH.docx).
Phương án chốt trước fit nằm ở [đây](PHUONG_AN_KIEM_DINH.md), [protocol](protocol.json), [khóa cuối](final_manifest.json).

{findings}

Nguồn 2026 chưa xác nhận liên tục giữa hai API; các bảng đó là kiểm tra độ bền kèm giới hạn nguồn.
Raw/checkpoint/dự báo từng thời điểm là private. [Kiểm chứng cuối](final_verification.json) và các CSV ghi rõ metric/mẫu/hạn.
"""
    (PUBLIC / "README.md").write_text(readme, encoding="utf8", newline="\n")
    report_files = [path for path in PUBLIC.iterdir() if path.is_file() and path.name != "release.json"]
    code = ["src/gfs_final.py", "src/gfs_capacity_control.py", "src/gfs_final_gate.py", "src/gfs_final_inference.py",
            "src/gfs_final_metrics.py", "scripts/prepare_gfs_final.py", "scripts/run_gfs_capacity_controls.py",
            "scripts/verify_gfs_final_controls.py", "scripts/score_gfs_final.py", "scripts/verify_gfs_final_results.py",
            "scripts/audit_gfs_final_peaks.py",
            "scripts/publish_gfs_final.py", "tests/test_gfs_capacity_control.py", "tests/test_gfs_final_evaluation.py"]
    write_json(PUBLIC / "release.json", dict(status="complete_verified_final_test_and_source_separated_external",
        completed_utc=datetime.now(timezone.utc).isoformat(), holdout_scored=True,
        final_manifest_sha256=sha(PUBLIC / "final_manifest.json"),
        report_sha256={path.name: sha(path) for path in sorted(report_files)},
        code_sha256={path: sha(ROOT/path) for path in code}, raw_data_public=False,
        checkpoint_public=False, no_post_test_tuning=True))
    progress("complete", holdout_scored=True, final_verification="passed", reports_published=True)
    print(json.dumps(dict(status="complete", report=str(PUBLIC / "BAO_CAO_KIEM_DINH.docx"))), flush=True)


if __name__ == "__main__":
    main()
