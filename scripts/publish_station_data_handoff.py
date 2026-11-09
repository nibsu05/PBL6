"""Publish a short Vietnamese handoff using aggregate, validated counts only."""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from docx import Document
from docx.shared import Cm, Pt, RGBColor

REPORT = ROOT / "reports/station_data_handoff_2026_11_09"


def number(n):
    return f"{n:,}".replace(",", ".")


def readable(text):
    # Keep code identifiers/resolution values intact while separating prose.
    text = re.sub(r"(\d)(giờ|ngày|kênh|trạm|mẫu|hàng|cửa|là|giữ|chưa|để|theo|năm|phần|kèm|đạt)", r"\1 \2", text)
    text = re.sub(r"(ngày|trạm|mẫu|đủ|vùng|có|từ|giữ|nguồn)(\d)", r"\1 \2", text)
    for before, after in [("kín.2026", "kín. 2026"),
        ("hômtrước", "hôm trước"), ("mãtrạm", "mã trạm"),
        ("24hriêng", "24h riêng"), ("mặtđất", "mặt đất"), ("nămtrain", "năm train")]:
        text = text.replace(before, after)
    return text


def table(doc, headings, rows):
    t = doc.add_table(rows=1, cols=len(headings))
    t.style = "Light Shading Accent 1"
    for cell, value in zip(t.rows[0].cells, headings):
        cell.text = value
    for row in rows:
        for cell, value in zip(t.add_row().cells, row):
            cell.text = str(value)
    return t


def main():
    s = json.loads((REPORT / "dataset_summary.json").read_text(encoding="utf8"))
    v = json.loads((REPORT / "verification.json").read_text(encoding="utf8"))
    assert v["status"] == "passed" and v["dataset_sha256"] == s["sha256"]
    hourly = s["resolutions"]["1h"]; daily = s["resolutions"]["24h"]
    size = s["bytes"] / 1_000_000
    text = f"""# Dữ liệu dùng chung — dự báo mưa tại trạm

Ngày bàn giao: 09/11/2026. Gửi cùng file **PBL6_TRAM_GIO_NGAY_V1.parquet** ({size:.1f} MB).

## 1. Dữ liệu này là gì?

Một file đã ghép mưa Vrain tại trạm với khí tượng ERA5 theo tọa độ trạm; có hai độ phân giải `1h` và `24h`. Mục tiêu là dự báo tại từng trạm, không phải mưa trung bình toàn Đà Nẵng. Mỗi kiến trúc học một mô hình chung cho nhiều trạm.

Danh mục tài khoản nhóm Đà Nẵng có **86 vị trí**; file có **82 trạm với lịch sử**. Trong đó **79 trạm có cửa sổ train hợp lệ**; ba trạm chưa có cửa sổ train bị loại khỏi đánh giá mặc định. Bốn vị trí chỉ có ở danh mục mới chưa có lịch sử trong nguồn này.

Nguồn có ngày đánh dấu 01/01/2021–31/12/2024. Khoảng đo thực: **19:00 ngày31/12/2020 đến19:00 ngày31/12/2024, giờ Việt Nam**; không có nghĩa mọi trạm đủ suốt giai đoạn. **10:00 = tổng mưa09:00–10:00 (UTC+7)**. Nhãn ngày cộng đủ24giờ từ19:00 hôm trước đến19:00 ngày được đánh dấu.

## 2. Hai nhánh dùng cùng file

| Nhánh | Chọn resolution | Đầu vào E7 + mưa quá khứ | Nhãn tương lai tại cùng trạm |
| --- | --- | --- | --- |
| Bi-LSTM, cực ngắn | `1h` | 24giờ ×45kênh | `y_h1_mm`…`y_h6_mm`: sáu lượng mưa giờ riêng |
| LightGBM/TFT/Informer, ngắn | `24h` | 7ngày ×43kênh | `y_d1_mm`…`y_d3_mm`: ba tổng24h riêng |

45/43kênh đã gồm một kênh mưa quá khứ; tọa độ/mãtrạm đi nhánh tĩnh riêng. Không lấy các cột nhãn hoặc QC làm đầu vào. Cột `rain_mm` là mưa đã quan trắc trong khoảng của hàng hiện tại; nhãn tương lai nằm ở các cột `y_*`.

## 3. Đặc trưng và nguồn

| Nhóm | Kênh giờ/ngày | Bao gồm |
| --- | --- | --- |
| B — nền | 11/9 | Nhiệt độ, điểm sương, độ ẩm2m; áp suất mặt đất/mực biển; gió u/v10m; lịch sin/cos giờ và ngày-trong-năm, bỏ hai kênh giờ ở bản ngày |
| A — đối lưu/mây/đất | 12/12 | CAPE, CIN, has_lfc, TCWV, K-index, Total Totals, độ cao lớp biên, bốn loại độ phủ mây, ẩm đất lớp1 |
| M — hoàn lưu/dòng ẩm | 20/20 | Gió/nhiệt/ẩm/chuyển động đứng850/500hPa; shear; IVT/VIMD; context TCWV/IVT; hai chênh áp |
| C — biển | 1/1 | SST trung bình hộp biển; chưa phải ENSO/MJO |
| R — tùy chọn | 1/1 | Mưa quá khứ của chính trạm, không dùng mưa tương lai |

Khí tượng: ERA5 gốc0,25° nội suy từ bốn nút quanh tọa độ trạm; không chép trung bình vùng93ô. Đây vẫn là trường khí tượng lưới, không phải khí tượng đo tại trạm. Giờ dùng ERA5 lúc đầu khoảng mưa; ngày lấy trung bình đủ24trạng thái giờ. Context/SST/chênháp có miền vùng có chủ đích. Không dùng mưa ERA5, GSMaP hoặc CPC làm nhãn hay lấp mưa thiếu.

## 4. Chia dữ liệu và dùng đúng

| Phần | Vai trò | Mẫu giờ | Mẫu ngày |
| --- | --- | ---: | ---: |
| train —2021–2022 | Học mô hình/scaler | {number(hourly['samples_r1']['train'])} | {number(daily['samples_r1']['train'])} |
| cal —2023 | Chọn cấu hình, earlystop/calibration | {number(hourly['samples_r1']['cal'])} | {number(daily['samples_r1']['cal'])} |
| dev —2024 | Đánh giá phát triển, chưa là test cuối | {number(hourly['samples_r1']['dev'])} | {number(daily['samples_r1']['dev'])} |

Toàn bộ nhãn phải nằm trong phần chia theo giờ Việt Nam. Mọi E/model dùng cùng `sample_ready_r1`; khi so R0/R1 cũng giữ mask này. **Không lọc bỏ các hàng thời gian thiếu rồi mới cắt chuỗi** vì sẽ nối sai lịch sử. Dùng loader trong repo `src/station_forecast_data.py`; chỉ cần file Parquet này, không phải ghép lại nguồn.

E0=B; E1=BA; E2=BM; E3=BC; E4=BAM; E5=BAC; E6=BMC; E7=BAMC. R và metadata tĩnh giữ giống nhau khi so E. LightGBM làm phẳng cùng lịch sử; TFT/Informer nhận chuỗi tương ứng. Chỉ lịch tương lai biết trước được dùng ở decoder; không khí tượng kỳ đích.

## 5. Đã kiểm tra và giới hạn

Đã kiểm tra **{number(v['all_rows_checked'])} dòng**, **{number(v['all_ready_windows_checked'])} cửa sổ**: đúng trạm/giờ/nhãn; tổng ngày đủ24giờ; không thiếu X/y trong cửa sổ đã đánh dấu; không vượt ranh nhãn giữa các phần chia. Ba station-day lệch tổng bị loại khỏi nhãn. NaN vẫn được giữ ở các hàng không dùng được; không điền thiếu thành0. CIN có mã500kèm has_lfc theo quy ước nguồn, không phải phép điền mưa.

Đạt kiểm tra ghép/cấu trúc, **chưa phải chứng nhận độ chính xác cảm biến hoặc kỹ năng dự báo**. 24trạm có dưới180mẫu ngày train; dùng mô hình chung và báo điểm riêng từng trạm. Tọa độ là metadata hiện có, chưa có lịch sử di chuyển/cao độ trạm. ERA5 là dữ liệu hồi cứu, chưa chứng minh khả dụng ngay tại lúc phát dự báo.

**2025 giữ kín. 2026 đã tải riêng nhưng chưa nhập bản train**, vì hai kênh chưa chứng minh tương đương và khí tượng chưa phủ hết giai đoạn mới. Bộ này dùng cho bước huấn luyện tiếp theo; chưa có kết quả mô hình trạm. Chỉ chia sẻ nội bộ nhóm có quyền dữ liệu, không đẩy Parquet lên GitHub công khai.

Hướng dẫn chạy loader: [HUONG_DAN_TRAIN.md](HUONG_DAN_TRAIN.md). SHA256 dữ liệu: `{s['sha256']}`.
"""
    text = "".join(part if i % 2 else readable(part) for i, part in enumerate(re.split(r"(`[^`]*`)", text)))
    (REPORT / "MO_TA_DU_LIEU.md").write_text(text, encoding="utf8")
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21); section.page_height = Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(1.4)
    section.left_margin = section.right_margin = Cm(1.6)
    style = doc.styles["Normal"]
    style.font.name = "Calibri"; style.font.size = Pt(10)
    style.paragraph_format.space_after = Pt(4)
    style.paragraph_format.line_spacing = 1.0
    doc.add_heading("DỮ LIỆU CHUNG — MƯA TẠI TRẠM", 0)
    doc.add_paragraph(f"09/11/2026 · PBL6_TRAM_GIO_NGAY_V1.parquet · {size:.1f} MB")
    doc.add_heading("1. Phạm vi và thời gian", 1)
    doc.add_paragraph("Một file đã ghép mưa Vrain tại trạm và khí tượng ERA5 theo tọa độ trạm; có cả bản giờ và ngày. Mục tiêu là dự báo tại từng trạm trong nhóm Đà Nẵng của tài khoản. Mỗi kiến trúc học một mô hình chung cho nhiều trạm.")
    doc.add_paragraph("86 vị trí trong danh mục → 82 trạm có lịch sử → 79 trạm có cửa sổ train hợp lệ. Ba trạm chưa có train bị loại khỏi đánh giá mặc định; bốn vị trí mới chưa có lịch sử ở nguồn này. Không phải mạng trạm toàn Việt Nam.")
    doc.add_paragraph("Ngày nguồn: 01/01/2021–31/12/2024. Khoảng đo thực: 19:00 ngày31/12/2020 đến19:00 ngày31/12/2024 (UTC+7); không phải mọi trạm đều đủ suốt thời gian này. Quy ước: 10:00 = tổng mưa09:00–10:00. Ngày = đủ24giờ từ19:00 hôm trước đến19:00 ngày được đánh dấu.")
    doc.add_heading("2. Hai nhánh dự báo", 1)
    table(doc, ["Nhánh / chọn resolution", "Đầu vào E7+R", "Đầu ra tại cùng trạm"], [
        ("Bi-LSTM / 1h", "24giờ ×45kênh", "y_h1_mm…y_h6_mm: sáu lượng mưa giờ riêng"),
        ("LightGBM/TFT/Informer / 24h", "7ngày ×43kênh", "y_d1_mm…y_d3_mm: ba tổng24h riêng")])
    doc.add_paragraph("45/43kênh đã gồm một kênh mưa quá khứ; tọa độ/mãtrạm đi nhánh tĩnh riêng. rain_mm là mưa đã quan trắc trong khoảng hiện tại. Các cột y_* là nhãn tương lai, không đưa vào X.")
    doc.add_heading("3. Có những đặc trưng gì?", 1)
    table(doc, ["Nhóm", "Giờ/ngày", "Thông tin"], [
        ("B — nền", "11/9", "Nhiệt độ, điểm sương, RH2m; áp suất mặt đất/mực biển; gió u/v10m; sin/cos giờ và ngày trong năm, bản ngày bỏ hai kênh giờ"),
        ("A — đối lưu/mây/đất", "12/12", "CAPE, CIN, has_lfc, TCWV, K-index, Total Totals, lớp biên, bốn loại mây, ẩm đất lớp1"),
        ("M — hoàn lưu/dòng ẩm", "20/20", "Trường850/500hPa; shear; IVT/VIMD; context TCWV/IVT; hai chênh áp"),
        ("C — biển", "1/1", "SST hộp biển; chưa phải ENSO/MJO"),
        ("R — tùy chọn", "1/1", "Mưa quá khứ tại chính trạm")])
    doc.add_paragraph("ERA5 gốc0,25° nội suy từ bốn nút quanh trạm, không chép trung bình vùng93ô. Khí tượng vẫn là sản phẩm lưới, không phải số đo tại trạm. Bản giờ dùng ERA5 lúc đầu khoảng; bản ngày trung bình đủ24trạng thái giờ. Context/SST/chênháp có miền vùng có chủ đích.")
    doc.add_page_break()
    doc.add_heading("4. Cách dùng và chia dữ liệu", 1)
    table(doc, ["Phần / vai trò", "Mẫu giờ", "Mẫu ngày"], [
        ("train:2021–2022 / học mô hình, scaler", number(hourly['samples_r1']['train']), number(daily['samples_r1']['train'])),
        ("cal:2023 / cấu hình, earlystop, calibration", number(hourly['samples_r1']['cal']), number(daily['samples_r1']['cal'])),
        ("dev:2024 / đánh giá phát triển, chưa test cuối", number(hourly['samples_r1']['dev']), number(daily['samples_r1']['dev']))])
    doc.add_paragraph("Toàn bộ nhãn của mỗi mẫu phải nằm trong cùng phần chia theo giờ Việt Nam. Dùng sample_ready_r1 chung cho mọi E/model, cả so sánh R0/R1. Không xóa các hàng thiếu rồi mới cắt chuỗi; loader giữ trục thời gian và chỉ chọn cửa sổ hợp lệ.")
    p = doc.add_paragraph()
    p.add_run("Dùng loader từ repo, không phải ghép lại dữ liệu:").bold = True
    code = 'from src.station_forecast_data import StationForecastData\nds = StationForecastData("PBL6_TRAM_GIO_NGAY_V1.parquet",\n    resolution="24h", split="train", experiment="E7", use_rain=True)\nsample = ds[0]  # x:(7,43); y:(3,); static:(2,)'
    p = doc.add_paragraph(code)
    for run in p.runs:
        run.font.name = "Consolas"; run.font.size = Pt(8)
    doc.add_paragraph('Đổi resolution="1h" cho Bi-LSTM: x=(24,45), y=(6,). Các nhóm ít biến hơn có số kênh tương ứng. LightGBM làm phẳng đúng cùng lịch sử; TFT/Informer dùng chuỗi. Chuẩn hóa chỉ fit trên train. Chỉ lịch tương lai biết trước được dùng ở decoder.')
    doc.add_paragraph("E0=B; E1=BA; E2=BM; E3=BC; E4=BAM; E5=BAC; E6=BMC; E7=BAMC. Giữ R và metadata tĩnh giống nhau giữa các E. Không chọn tất cả cột số trong file làm X: file có cả nhãn, QC và thông tin thời gian.")
    doc.add_heading("5. Đảm bảo ở mức nào?", 1)
    doc.add_paragraph(f"Đã kiểm tra {number(v['all_rows_checked'])} dòng và {number(v['all_ready_windows_checked'])} cửa sổ: đúng trạm, đúng giờ/nhãn, tổng ngày đủ24giờ; không thiếu X/y trong cửa sổ được đánh dấu; không vượt ranh nhãn giữa các phần chia. Đối chiếu lại số gốc Vrain và các nút ERA5.")
    doc.add_paragraph("Giữ NaN ở hàng không dùng được; không điền thiếu thành0. Ba station-day lệch tổng được gắn cờ và loại khỏi nhãn. Không lấy mưa ERA5/CPC/GSMaP lấp nhãn trạm. CIN có mã500kèm has_lfc theo quy ước nguồn, không phải phép điền mưa.")
    doc.add_paragraph("Đạt kiểm tra ghép/cấu trúc; chưa chứng nhận độ chính xác cảm biến hay kỹ năng dự báo. 24trạm có dưới180mẫu ngày train: nên pilot trước và báo điểm riêng từng trạm. Tọa độ là metadata hiện có; chưa có lịch sử di chuyển/cao độ trạm. ERA5 hồi cứu chưa chứng minh có sẵn ngay khi phát dự báo.")
    p = doc.add_paragraph()
    p.add_run("2025 giữ kín. 2026 để riêng, chưa nhập bản train. ").bold = True
    p.add_run("Hai kênh2026 chưa chứng minh tương đương và khí tượng chưa phủ hết phần mới. Bộ này sẵn sàng cho bước train với loader; chưa có kết quả mô hình trạm.")
    doc.add_paragraph("Gửi hai file: Parquet + tài liệu này. Dữ liệu chia sẻ nội bộ nhóm có quyền truy cập; không đẩy Parquet lên GitHub công khai.")
    p = doc.add_paragraph("SHA256: "+s["sha256"])
    p.runs[0].font.size = Pt(7)
    doc.core_properties.title = "Dữ liệu chung dự báo mưa tại trạm — v1"
    doc.core_properties.subject = "Vrain + ERA5, dữ liệu giờ và ngày, 2021–2024"
    paragraphs = list(doc.paragraphs) + [p for t in doc.tables for row in t.rows for cell in row.cells for p in cell.paragraphs]
    for paragraph in paragraphs:
        for run in paragraph.runs:
            if run.font.name != "Consolas":
                run.text = readable(run.text)
    doc.save(REPORT / "MO_TA_DU_LIEU.docx")
    print(json.dumps({"description_docx": str(REPORT / 'MO_TA_DU_LIEU.docx'),
                      "dataset_mb": round(size, 1), "dataset_sha256": s['sha256']}))


if __name__ == "__main__":
    main()
