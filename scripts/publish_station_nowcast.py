"""Publish aggregate hourly results and fill the final report's hourly sections."""

import argparse
import json
from pathlib import Path
import shutil
import sys

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import station_nowcast as ns


DOCS = ns.ROOT / "data/operational/pbl6_bao_cao_cuoi_ky_2026_11_24"
BASE_DOC = DOCS / "PBL6_BAO_CAO_CUOI_KY_NGAN_HAN_CAP_NHAT.docx"
FINAL_DOC = DOCS / "PBL6_BAO_CAO_CUOI_KY_NGAN_HAN_VA_CUC_NGAN.docx"
DAILY_MAP = ns.ROOT / "data/operational/gfs_short_range_closeout_2026_11_24/station_map_private.json"
NAMES = {
    "Zero": "0 mm", "Persistence": "Giữ mưa", "LightGBM_R": "LightGBM R",
    "BiLSTM_R": "Bi-LSTM R", "BiLSTM_E0": "Bi-LSTM E0", "BiLSTM_E2": "Bi-LSTM E2",
}


def number(value, places=3):
    return f"{value:.{places}f}".replace(".", ",")


def count(value):
    return f"{value:,}".replace(",", ".")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def report_data(out, daily_map):
    fit = load(out / "fit_manifest.json")
    verified = load(out / "verification.json")
    if verified["status"] != "passed":
        raise ValueError("Verify the archived forecasts first")
    yearly = pd.concat([pd.read_csv(out / f"metrics_{role}.csv") for role in ("dev", "reserved2025")])
    paired = pd.concat([pd.read_csv(out / f"paired_blocks_{role}.csv") for role in ("dev", "reserved2025")])
    test = yearly.query("role == 'reserved2025' and scope == 'all_micro'")
    event = test[test.threshold.eq(1)].set_index(["model", "lead_hour"])
    heavy = test[test.threshold.eq(5)].set_index(["model", "lead_hour"])
    primary = paired.loc[paired.role.eq("reserved2025") & paired.primary].set_index("block_days")
    by_station = pd.read_csv(out / "station_metrics_reserved2025.csv")
    station_rmse = by_station.loc[by_station.threshold.eq(1)].pivot(
        index=["station_id", "lead_hour"], columns="model", values="RMSE")
    winners = station_rmse.LightGBM_R.lt(station_rmse.Persistence).groupby("lead_hour").sum()
    train = pd.read_csv(out / "train_station_coverage.csv")
    ids = set(train.loc[train.train.gt(0), "station_id"])
    old = {row["station_id"] for row in load(daily_map)["stations"]} if daily_map.exists() else set()
    coverage = dict(catalogue=len(train), training=len(ids), minimum_train=int(train.loc[train.train.gt(0), "train"].min()))
    if old:
        coverage.update(daily=len(old), overlap=len(old & ids), hourly_only=len(ids - old))
    return dict(fit=fit, verified=verified, yearly=yearly, paired=paired, event=event, heavy=heavy,
                primary=primary, winners=winners, coverage=coverage)


def table(data, metric):
    view = data["event"]
    names = list(NAMES)
    descending = metric == "CSI"
    rows = [[("Giờ đích", False), *[(NAMES[model], False) for model in names]]]
    for h in ns.LEADS:
        values = [view.loc[(model, h), metric] for model in names]
        best = max(values) if descending else min(values)
        rows.append([(f"Giờ {h}", False), *[(number(value), value == best) for value in values]])
    return rows


def markdown_table(rows):
    formatted = [[f"**{label}**" if best else label for label, best in row] for row in rows]
    header = "| " + " | ".join(formatted[0]) + " |\n"
    sep = "| " + " | ".join(["---"] * len(rows[0])) + " |\n"
    return header + sep + "\n".join("| " + " | ".join(row) + " |" for row in formatted[1:])


def write_report(out, report, data):
    f, v, c = (data[key] for key in ("fit", "verified", "coverage"))
    point, heavy, primary = (data[key] for key in ("event", "heavy", "primary"))
    held = v["checks"]["reserved2025"]
    params = ns.PROTOCOL["bilstm"]
    reduction = 100 * (1 - point.loc[("LightGBM_R", 6), "RMSE"] / point.loc[("Persistence", 6), "RMSE"])
    gain = primary.loc[7, "observed_delta"]
    dev_gain = data["paired"].loc[data["paired"].role.eq("dev") & data["paired"].primary,
                                   "observed_delta"].iloc[0]
    elapsed = sum(item["seconds"] for run in f["runs"] for item in run["history"]) / 60
    intervals = ", ".join(
        f"khối {b} ngày [{number(row.ci_lo, 4)}, {number(row.ci_hi, 4)}]"
        for b, row in primary.iterrows()
    )
    conclusion = ("Cả hai khoảng còn chứa 0, vì vậy chưa xác nhận lợi ích của riêng nhóm gió."
                  if ((primary.ci_lo <= 0) & (primary.ci_hi >= 0)).all()
                  else "Đọc cả hai độ dài khối khi diễn giải hiệu quả của riêng nhóm gió.")
    overlap = (f" Phạm vi bao gồm cả {c['overlap']} trạm của nhánh ngày và thêm {c['hourly_only']} trạm."
               if "overlap" in c else "")
    text = f"""# Dự báo mưa 1–6 giờ tại trạm

Đã huấn luyện và kiểm định trên **{c['training']}/{c['catalogue']} vị trí trong danh mục Vrain**.{overlap} Một mô hình Bi-LSTM học chung giữa các trạm, giữ sáu nhãn mưa riêng cho mỗi thời điểm phát. Gói thử nghiệm trước của nhóm dùng ba trạm và ba giờ đích. Bản này đối chiếu thêm trên đúng ba trạm đó trong các bảng `pilot3`, đồng thời kiểm định toàn bộ tập trạm đã học.

## Dữ liệu và huấn luyện

| Vai trò | Thời gian | Mẫu trạm–giờ đủ điều kiện |
| --- | --- | ---: |
| Huấn luyện | 2021–2022 | {count(f['n_train'])} |
| Chọn epoch, số cây và phương án phát lại | 2023 | {count(f['n_cal'])} |
| Phát triển | 2024 | {count(v['checks']['dev']['origins_verified'])} |
| Kiểm định sau khóa | 2025 | {count(held['origins_verified'])} |

- Mỗi đầu vào dùng 24 giờ kết thúc tại lúc phát. Đầu ra gồm lượng mưa tại cùng trạm trong từng khoảng 1 giờ từ hạn 1 đến 6, đơn vị mm. Ví dụ, phát 19h thì giờ 1 là 19h–20h, giờ 6 là 00h–01h hôm sau theo giờ Việt Nam.
- Mẫu dự báo cần lịch sử 24 giờ hoàn chỉnh. Để chấm, cần thêm sáu quan trắc cùng nguồn Vrain ở giờ đích. Thí nghiệm dùng chung tập đủ khí tượng lịch sử để so các mô hình. Dữ liệu khí tượng ERA5 được ghép theo tọa độ từng trạm. Không điền số 0 vào mưa thiếu.
- **R (3 biến)** gồm mưa trạm, chênh mưa so giờ trước trong cửa sổ và tháng. **E0 (11 biến)** thêm nhiệt độ, tốc độ gió gần mặt đất, độ ẩm, áp suất và bốn chênh lệch tương ứng. **E2 (13 biến)** thêm đúng hai thành phần gió ở 850 hPa. Nhãn E0 và E2 ở đây bám theo thí nghiệm Bi-LSTM ba trạm. Cách chia nhóm của bộ ERA5 gốc rộng hơn.
- Bi-LSTM có một lớp hai chiều, {params['hidden_size_per_direction']} nút mỗi chiều và mã trạm học được. Hai chiều đều đọc 24 giờ đã xảy ra. Dùng MSE trên log(1 + mm), chuẩn hóa chỉ từ train và chọn epoch theo RMSE đơn vị mm năm 2023. Chạy ba seed {', '.join(map(str, params['seeds']))} cho mỗi cấu hình, rồi lấy trung bình ba dự báo đã đổi về mm. Tổng thời gian trong các epoch Bi-LSTM khoảng {number(elapsed, 1)} phút trên RTX 4060 Laptop, chưa tính bước dựng mẫu và chấm.
- Mốc **Giữ mưa** dùng lượng đo gần nhất cho cả sáu giờ. Mốc **0 mm** kiểm tra lợi ích khi số giờ khô chiếm nhiều. **LightGBM R** dùng cùng lịch sử mưa và tháng, thêm các tổng/cực đại tính từ chính 24 giờ đó. Mô hình cây dùng L2 theo mm và một bộ cây mỗi hạn dùng chung các trạm.

## Kiểm định 2025

RMSE tính theo mm trong từng khoảng một giờ, càng thấp càng tốt.

{markdown_table(table(data, 'RMSE'))}

CSI phát hiện mưa từ 1 mm trong giờ đích. CSI là số báo đúng chia cho tổng số báo đúng, bỏ sót và báo nhầm.

{markdown_table(table(data, 'CSI'))}

**Mốc hữu ích nhất để phát lại** là {NAMES[f['replay_method']]}, đã chọn bằng RMSE năm 2023. Năm 2025, LightGBM R giảm RMSE giờ 6 khoảng **{number(reduction, 1)}%** so với giữ nguyên mưa. Số trạm giảm RMSE ở các hạn 1–6 lần lượt là **{', '.join(str(int(data['winners'].loc[h])) for h in ns.LEADS)}** trên {c['training']}.

**Giá trị của gió 850 hPa.** Chênh CSI giờ 6 của E2 so với E0 là {number(dev_gain, 4)} trên 2024 và **{number(gain, 4)}** trên 2025. Khoảng tin cậy 95% ghép theo {intervals}. {conclusion}

**MAE cho một cách đọc khác.** Ở giờ 6, dự báo 0 mm có MAE {number(point.loc[('Zero', 6), 'MAE'])} mm, thấp hơn LightGBM R ({number(point.loc[('LightGBM_R', 6), 'MAE'])} mm). Các giờ khô xuất hiện thường xuyên, còn RMSE phạt mạnh lỗi lớn. Vì vậy tiêu chí chọn phương án phát lại được đặt theo RMSE từ năm 2023.

**Giờ mưa mạnh vẫn khó.** Trong {count(int(heavy.loc[('LightGBM_R', 6), 'n_obs_events']))} mẫu có mưa ít nhất 5 mm ở giờ 6, POD của LightGBM R là {number(heavy.loc[('LightGBM_R', 6), 'POD'])} và FAR là {number(heavy.loc[('LightGBM_R', 6), 'FAR'])}. Mốc giữ nguyên mưa có POD {number(heavy.loc[('Persistence', 6), 'POD'])} và FAR {number(heavy.loc[('Persistence', 6), 'FAR'])}. POD là tỷ lệ số giờ mưa thực tế được phát hiện. FAR là tỷ lệ báo nhầm trong những giờ dự báo có sự kiện. Ngưỡng 1 và 5 mm là ngưỡng thí nghiệm theo giờ.

## Phạm vi và trình diễn

- {c['catalogue'] - c['training']} vị trí chưa có cửa sổ huấn luyện đủ điều kiện trong 2021–2022. Trong tập đã học, trạm ít mẫu nhất có {count(c['minimum_train'])} mẫu. Tập kiểm định 2025 là các thời điểm mới ở những trạm đã học. Đánh giá khả năng chuyển sang trạm mới cần giữ riêng trạm trong thiết kế thí nghiệm.
- Thí nghiệm chứng minh có thể huấn luyện và chấm trên mạng trạm lớn bằng một Bi-LSTM dùng chung. Để đo riêng lợi ích của huấn luyện chung so với huấn luyện mỗi trạm một mô hình, cần thêm đối chứng cùng kiến trúc, cửa sổ và tập mẫu.
- Web cục bộ có trang **1–6 giờ** với bảy lượt phát lại từ 04 đến 10/11/2026. Mỗi lượt chọn mốc 19h để trình diễn và có 78/79 trạm có số. Màu là lượng tại trạm theo từng giờ đích. Đăng nhập để xem số đo Vrain đã ghi nhận. Năm 2026 dùng kênh Vrain khác giai đoạn huấn luyện, nên bản phát lại không xác nhận hiệu năng vận hành.
- Phương án chỉ dùng Vrain và lịch có thể chạy với 24 giờ quan trắc đạt kiểm tra. Để phát theo giờ thực tế, cần xác nhận nguồn cung cấp kịp giờ, ghi đầu vào và dự báo ngay lúc phát, rồi đối chiếu khi đủ nhãn. ERA5T có độ trễ khoảng năm ngày theo [tài liệu ECMWF](https://confluence.ecmwf.int/pages/viewpage.action?pageId=301966210).

## Kiểm chứng và tái chạy

Đã đối chiếu toàn bộ khóa trạm–giờ và sáu nhãn của {count(v['checks']['dev']['origins_verified'] + held['origins_verified'])} mẫu. Kiểm lại điểm gộp từ Parquet và nạp lại các trọng số để đối chiếu dự báo trên mẫu lấy ở mọi trạm. Bảng theo trạm, dự báo theo giờ, scaler, trọng số và bản ghi khóa nằm trong thư mục nội bộ `data/operational/{report.name}/`.

```powershell
.venv\\Scripts\\python.exe -X utf8 scripts/train_station_nowcast.py
.venv\\Scripts\\python.exe -X utf8 scripts/evaluate_station_nowcast.py
.venv\\Scripts\\python.exe -X utf8 scripts/prepare_station_nowcast_replay.py
.venv\\Scripts\\python.exe -X utf8 scripts/verify_station_nowcast.py
.venv\\Scripts\\python.exe -X utf8 demo/station_map.py
```

Mở trang [1–6 giờ](http://127.0.0.1:8766/cuc-ngan). Dữ liệu đầu vào lấy từ [bộ ghép Vrain–ERA5 ngày 17/11](../station_hourly_era5_2026_11_17/README.md). Giao thức, điểm gộp, độ nhạy theo seed và các khoảng tin cậy đi cùng báo cáo.
"""
    (report / "README.md").write_text(text, encoding="utf-8")
    for role in ("dev", "reserved2025"):
        for name in ("metrics", "paired_blocks", "seed_metrics"):
            shutil.copyfile(out / f"{name}_{role}.csv", report / f"{name}_{role}.csv")
    ns.write_json(report / "verification.json", v)
    ns.write_json(report / "coverage_summary.json", c)


def insert_paragraph(doc, anchor, text, style="Normal"):
    p = doc.add_paragraph(text, style=style)
    anchor.addnext(p._p)
    return p._p


def insert_caption(doc, anchor, group, cached_number, text):
    prefix = {"Table": "Bảng", "Figure": "Hình"}[group]
    p = doc.add_paragraph(f"{prefix} ", style="Caption")
    for part in ("begin", "instruction", "separate", "number", "end"):
        if part == "number":
            p.add_run(str(cached_number))
            continue
        if part == "instruction":
            field = OxmlElement("w:instrText")
            field.set(qn("xml:space"), "preserve")
            field.text = f" SEQ {group} \\* ARABIC "
        else:
            field = OxmlElement("w:fldChar")
            field.set(qn("w:fldCharType"), part)
        p.add_run()._r.append(field)
    p.add_run(f". {text}")
    anchor.addnext(p._p)
    return p._p


def insert_table(doc, anchor, rows):
    result = doc.add_table(rows=len(rows), cols=len(rows[0]), style="Table Grid")
    for i, row in enumerate(rows):
        for j, (label, best) in enumerate(row):
            run = result.cell(i, j).paragraphs[0].add_run(label)
            run.bold = best or i == 0
        trpr = result.rows[i]._tr.get_or_add_trPr()
        trpr.append(OxmlElement("w:cantSplit"))
        if i == 0:
            trpr.append(OxmlElement("w:tblHeader"))
    anchor.addnext(result._tbl)
    return result._tbl


def publish_word(source, path, out, data):
    doc = Document(source)
    f, c, v = (data[key] for key in ("fit", "coverage", "verified"))
    held = v["checks"]["reserved2025"]
    anchors = {}
    for p in doc.paragraphs:
        if p.text.startswith("Báo cáo trình bày bài toán"):
            p.text = ("Báo cáo trình bày hai bài toán tại trạm. Dự báo cực ngắn ước lượng sáu lượng mưa "
                      "từng giờ. Dự báo ngắn hạn ước lượng ba tổng mưa 24 giờ. Hai nhánh dùng quan trắc "
                      "Vrain làm nhãn, chia dữ liệu theo thời gian và kiểm định trên các kỳ đã định.")
        elif p.text.startswith("Phần này dành để nhóm bổ sung phương pháp dự báo cực ngắn"):
            anchors["method"] = p
        elif p.text.startswith("Dành để nhóm bổ sung kết quả, hình và bảng kiểm chứng"):
            anchors["result"] = p
        elif p.text.startswith("Nhánh cực ngắn sẽ được ghép"):
            p.text = ("Dự báo cực ngắn đã có cấu hình phát lại dùng mưa Vrain. Bước vận hành cần đo "
                      "độ trễ quan trắc theo giờ và ghi dự báo trước khi kiểm chứng. Cần một thử nghiệm "
                      "giữ riêng trạm để đánh giá khả năng mở rộng đến các vị trí thiếu lịch sử.")
        elif p.text.startswith("Bước tiếp theo là thu và ghi dự báo") and "conclusion" not in anchors:
            anchors["conclusion"] = p._p.getprevious().getprevious()
        elif p.text.startswith("[15] NOAA National Centers"):
            anchors["sources"] = p._p
    if set(anchors) != {"method", "result", "conclusion", "sources"}:
        raise ValueError("Final report placeholders differ from expected template")
    method = anchors["method"]
    method.text = (f"Mỗi mẫu là một trạm và một giờ phát, gồm 24 giờ đầu vào và sáu lượng mưa giờ tiếp theo. "
                   f"Có {count(f['n_train'])} mẫu huấn luyện của {c['training']} trạm trong 2021–2022. "
                   f"Dùng {count(f['n_cal'])} mẫu năm 2023 để chọn epoch và số cây. "
                   "Năm 2024 dùng để đánh giá phát triển. Năm 2025 được chấm sau khi khóa mô hình và phép so.")
    anchor = method._p
    for paragraph in (
        "Đồng hồ được hiểu theo giờ Việt Nam. Quan trắc 10h là lượng mưa tích lũy 09h–10h. "
        "Tại 10h, nhãn giờ 1 là 10h–11h, nhãn giờ 6 là 15h–16h. Cửa sổ đầu vào chỉ kiểm tra các "
        "giờ đã qua. Sáu giờ tương lai được kiểm tra khi ghép nhãn để huấn luyện và chấm điểm.",
        "Mô hình Bi-LSTM một lớp đọc 24 giờ quá khứ từ hai hướng [16], dùng 64 nút mỗi hướng và mã trạm "
        "học được. R có mưa, chênh mưa và tháng. E0 thêm nhiệt độ, tốc độ gió, độ ẩm, áp suất gần mặt đất "
        "và các chênh lệch theo giờ. E2 thêm hai thành phần gió 850 hPa. Khí tượng lấy từ ERA5 [17] "
        "ghép theo tọa độ trạm.",
        "Chuẩn hóa được tính từ train. Huấn luyện dùng MSE trên log(1 + mm) với ba seed 17, 29, 43. "
        "Chọn epoch theo RMSE năm 2023, rồi trung bình ba dự báo sau đổi về mm. Các đối chứng gồm "
        "0 mm, giữ mưa giờ vừa đo và LightGBM học từ lịch sử mưa trạm cùng tháng.",
    ):
        anchor = insert_paragraph(doc, anchor, paragraph)
    result = anchors["result"]
    result.text = (f"Tập kiểm định 2025 gồm {count(held['origins_verified'])} mẫu trạm–giờ ở {held['stations']} trạm. "
                   "Mọi mô hình được so trên cùng tập mẫu và sáu giờ đích. Số đo Vrain là mốc đối chiếu.")
    anchor = insert_caption(doc, result._p, "Table", 18, "RMSE (mm) của dự báo 1–6 giờ trên kiểm định 2025")
    anchor = insert_table(doc, anchor, table(data, "RMSE"))
    anchor = insert_caption(doc, anchor, "Table", 19, "CSI phát hiện từ 1 mm trong giờ đích trên kiểm định 2025")
    anchor = insert_table(doc, anchor, table(data, "CSI"))
    primary = data["primary"].loc[7]
    rain_heavy = data["heavy"].loc[("LightGBM_R", 6)]
    direction = ("Khoảng chứa 0 nên chưa xác nhận lợi ích độc lập của nhóm gió."
                 if primary.ci_lo <= 0 <= primary.ci_hi else
                 "Cần đọc cả kiểm tra độ nhạy theo độ dài khối ngày.")
    anchor = insert_paragraph(
        doc, anchor, f"Ở phép so chính, CSI giờ 6 của E2 trừ E0 bằng {number(primary.observed_delta, 4)} "
        f"với khoảng 95% [{number(primary.ci_lo, 4)}, {number(primary.ci_hi, 4)}] khi lấy mẫu theo khối 7 ngày. "
        f"{direction} Với ngưỡng 5 mm ở giờ 6, LightGBM R có POD {number(rain_heavy.POD)} "
        f"và FAR {number(rain_heavy.FAR)}. Kết quả mưa mạnh cần được đọc riêng khi đánh giá ứng dụng.")
    anchor = insert_paragraph(
        doc, anchor, f"Web có chế độ phát lại cực ngắn bằng {NAMES[f['replay_method']]}, được chọn theo điểm 2023. "
        "Bảy lượt 19h từ ngày 04 đến 10/11/2026 hiển thị đến 78 trạm có số, bộ chọn sáu giờ và đối chiếu "
        "Vrain sau đăng nhập. Chế độ này thể hiện việc suy luận từ mưa trạm đã lưu.")
    frame = out / "web_qa/desktop.png"
    if frame.is_file():
        p = doc.add_paragraph()
        p.add_run().add_picture(str(frame), width=Cm(15))
        anchor.addnext(p._p)
        insert_caption(doc, p._p, "Figure", 7, "Phát lại dự báo 1–6 giờ và bảng mưa tại một trạm")
    point = data["event"]
    reduction = 100 * (1 - point.loc[("LightGBM_R", 6), "RMSE"] / point.loc[("Persistence", 6), "RMSE"])
    insert_paragraph(doc, anchors["conclusion"],
                     f"Nhánh cực ngắn đã huấn luyện và kiểm định dự báo sáu giờ trên {c['training']} trạm. "
                     f"Ở năm 2025, LightGBM dùng mưa trạm giảm RMSE giờ 6 khoảng {number(reduction, 1)}% "
                     "so với giữ mưa giờ vừa đo. Khả năng phát hiện giờ mưa mạnh còn hạn chế. "
                     "Lợi ích của hai thành phần gió tầng 850 hPa chưa được xác nhận.")
    sources = insert_paragraph(doc, anchors["sources"],
                               "[16] Schuster, M. và Paliwal, K. K. (1997). Bidirectional recurrent neural networks. "
                               "IEEE Transactions on Signal Processing, 45(11), 2673–2681. "
                               "https://doi.org/10.1109/78.650093")
    insert_paragraph(doc, sources, "[17] ECMWF. ERA5 data documentation. "
                     "https://confluence.ecmwf.int/pages/viewpage.action?pageId=301966210")
    doc.save(path)
    print(path, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ns.PRIVATE)
    parser.add_argument("--daily-map", type=Path, default=DAILY_MAP)
    parser.add_argument("--word-template", type=Path, default=BASE_DOC)
    parser.add_argument("--word-output", type=Path, default=FINAL_DOC)
    args = parser.parse_args()
    data = report_data(args.out, args.daily_map)
    write_report(args.out, ns.REPORT, data)
    publish_word(args.word_template, args.word_output, args.out, data)


if __name__ == "__main__":
    main()
