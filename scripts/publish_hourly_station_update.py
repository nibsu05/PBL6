"""Publish a small, explicit hourly handoff after successful full verification."""
from pathlib import Path
import json
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from docx import Document
from docx.shared import Cm, Pt
from src.hourly_station_update import BASE, OUT, PUBLIC, VERSION, DATASET
from src.station_forecast_data import GROUPS, EXPERIMENTS, feature_names
from src.station_archive_update import sha, write_json


def number(value):
    return f"{value:,}".replace(",", ".")


def main():
    summary = json.loads((PUBLIC / "dataset_summary.json").read_text(encoding="utf8"))
    verification = json.loads((PUBLIC / "verification.json").read_text(encoding="utf8"))
    if verification["status"] != "passed" or sha(OUT / DATASET) != verification["dataset_sha256"]:
        raise ValueError("Cannot publish an unverified dataset")
    groups = dict(groups=GROUPS, experiments=EXPERIMENTS,
        features={e: feature_names("1h", e, use_rain=True) for e in EXPERIMENTS},
        labels=[f"y_h{h}_mm" for h in range(1, 7)],
        static=["latitude", "longitude", "station_code"],
        sample_mask="sample_ready_r1", split_column="split",
        paired_r0_r1=True, history_hours=24, horizon_hours=6)
    write_json(PUBLIC / "feature_groups.json", groups)
    rows = []
    labels = {"train": "2021–2022: huấn luyện", "cal": "2023: lựa chọn/hiệu chỉnh",
              "dev": "2024: đánh giá phát triển", "reserved2025": "2025: dành kiểm định",
              "external2026": "2026: kiểm tra trên nguồn chuyển tiếp"}
    for role, counts in summary["ready_counts"].items():
        rows.append(f"| {labels[role]} | {number(counts['sample_ready'])} | {counts['stations_with_ready_samples']} |")
    text = f"""# Bộ dữ liệu giờ cho Bi-LSTM — bàn giao 17/11/2026

**Tệp dùng chính: `{DATASET}`**, khoảng {summary['bytes']/1_000_000:.0f} MB, {number(summary['rows'])} hàng. File đã ghép mưa Vrain với khí tượng ERA5 tại tọa độ từng trạm, có sáu nhãn tương lai và cờ mẫu hợp lệ. Đây là bản mới; không ghi đè bộ V1 hay kết quả nghiên cứu cũ.

## 1. Gửi file nào cho thành viên?

Gửi ZIP `PBL6_BILSTM_GIO_2021_2026.zip`. Trong ZIP chỉ có năm file:

- `{DATASET}`: dữ liệu đầy đủ để dựng chuỗi.
- `MO_TA_DU_LIEU.docx`: bản mô tả này.
- `HUONG_DAN_TRAIN.md`: ví dụ đọc bằng loader của repo.
- `feature_groups.json`: danh sách đầu vào E0–E7, nhãn và mask.
- `SHA256.json`: kiểm tra các file có bị thay đổi khi chuyển hay không.

Không cần ghép thêm với file mưa giờ thuần của gói 16/11. File mới đã chứa mưa nguồn, các cột sau QC, khí tượng và nhãn. Chỉ chia sẻ nội bộ nhóm có quyền sử dụng dữ liệu; không đưa Parquet lên GitHub công khai.

## 2. Phạm vi và thời gian

Danh mục có **86 vị trí thuộc nhóm Đà Nẵng mà tài khoản truy cập**, không phải toàn Việt Nam và không bảo đảm phủ kín diện tích hành chính. Có **{summary['stations_seen_train']} trạm có cửa sổ huấn luyện hợp lệ** theo split 2021–2022 hiện hành. Các vị trí thiếu lịch sử vẫn được giữ trong file; không tự sinh quan trắc cho chúng.

- Mưa nguồn: ngày được đánh dấu 01/01/2021–15/11/2026, khoảng thực từ **19h ngày 31/12/2020 đến 19h ngày 15/11/2026**, giờ Việt Nam.
- ERA5 hiện tải được đến trạng thái **06h ngày 11/11/2026 giờ Việt Nam**, tương ứng 23h ngày 10/11 UTC.
- Hàng cuối có thể ghép khí tượng đầu khoảng là **mưa 06–07h ngày 11/11/2026**. Trạng thái ERA5 06h đi với khoảng mưa này.
- **{number(summary['weather_unavailable_tail_rows'])} hàng trạm–giờ ở phần cuối chưa có ERA5**: giữ NaN, mask không cho vào huấn luyện. Có mưa tới 15/11 không có nghĩa đầu vào khí tượng đã tới 15/11.
- Mọi trạm không nhất thiết có số đo suốt giai đoạn. Năm 2026 chưa đủ năm. Không chia mưa ngày thành mưa giờ.

## 3. Một mẫu đầu vào/đầu ra là gì?

Một mẫu là một trạm tại một thời điểm phát dự báo. Đầu vào E7+R có dạng **24 giờ × 45 kênh**; đầu ra là **6 lượng mưa giờ riêng tiếp theo**, đơn vị mm, tại chính trạm đó. Tọa độ/mã trạm đi nhánh tĩnh riêng. Có thể dùng một mô hình chung cho nhiều trạm.

Ví dụ phát dự báo lúc 10h: hàng cuối lịch sử chứa mưa 09–10h và trạng thái ERA5 09h. Nhãn là mưa 10–11h, 11–12h, …, 15–16h. Trong file thời gian chính lưu UTC, có thêm `period_end_vn` để đọc giờ Việt Nam. `10:00` của Vrain đã được người dùng xác nhận là tổng 09:00–10:00 UTC+7.

| Nhóm | Số kênh | Thông tin |
| --- | ---: | --- |
| B — nền | 11 | Nhiệt độ, điểm sương, RH 2m; áp suất bề mặt/mực biển; gió u/v 10m; sin/cos giờ và ngày trong năm |
| A — đối lưu, mây, đất | 12 | CAPE, CIN, has_lfc, TCWV, K-index, Total Totals, lớp biên, bốn loại mây và ẩm đất lớp 1 |
| M — hoàn lưu, vận chuyển ẩm | 20 | Trường 850/500 hPa, đứt gió, IVT/VIMD, bối cảnh TCWV/IVT và hai chênh áp |
| C — biển | 1 | SST trung bình hộp biển đã chọn; chưa phải ENSO/MJO |
| R — mưa quá khứ | 1 | Mưa Vrain tại chính trạm, sau QC |

44 kênh khí tượng/lịch + 1 kênh mưa quá khứ = 45. E0=B; E1=BA; E2=BM; E3=BC; E4=BAM; E5=BAC; E6=BMC; E7=BAMC. Khi so sánh E hoặc có/không R, giữ cùng mask R1 và cùng cách dùng static/ID.

Đơn vị chính: mưa mm; nhiệt độ °C; RH %; áp suất hPa; gió m/s; q g/kg; CAPE/CIN J/kg; TCWV kg/m²; BLH m; IVT kg/m/s; VIMD mm/h; mây là tỷ lệ 0–1; omega Pa/s; độ ẩm đất m³/m³. Các biến dẫn xuất giữ công thức của bộ V1 để so sánh nhất quán.

## 4. Vì sao đặc trưng ứng với từng trạm?

Từ tọa độ hiện tại của từng trạm, xác định bốn nút ERA5 0,25° bao quanh. Tính trọng số song tuyến riêng cho trạm rồi kết hợp bốn giá trị tại đúng giờ. Thiếu một nút có trọng số dương thì giữ thiếu; không bỏ nút rồi chuẩn hóa lại. Cả 86 vị trí đều có nút bao quanh. Không chép trung bình vùng 93 ô cho từng trạm.

Nội suy không tạo thêm độ phân giải thật: ERA5 là trường khí tượng lưới, **không phải số đo nhiệt/ẩm/gió trực tiếp tại trạm Vrain**. Trạm gần nhau có thể có đặc trưng gần giống. Context lấy miền lân cận; SST và chênh áp dùng miền lớn có chủ đích. Tọa độ là metadata hiện có, chưa chứng minh mọi trạm không di chuyển trong lịch sử.

## 5. Hai cột legacy và modern có nghĩa gì?

**Cả hai đều từ Vrain.** Đây là hai đường API của cùng dịch vụ; `legacy`/`modern` là nhãn kỹ thuật do dự án đặt, không phải hai cấp chất lượng hay xác nhận hai loại cảm biến.

- `legacy_rain_raw_mm`: số gốc API thứ nhất.
- `modern_rain_raw_mm`: số gốc API thứ hai.
- Các cột `*_rain_qc_mm`: số sau kiểm tra cấu trúc/tổng ngày của từng API.
- `rain_mm`: giá trị tiện dụng đã chọn nguồn. Ưu tiên legacy hợp lệ, dùng modern khi legacy thiếu; hai số xung đột thì NaN.
- `gauge_source_code`: 0=legacy, 1=modern, -1=thiếu, 3=xung đột.

Kho đã kiểm tra: API thứ nhất có số cả 365 ngày năm 2025; API thứ hai không có số năm 2025 và bắt đầu trả số từ 08/01/2026. Trong phần giao chỉ có 367 cặp giờ tại một vị trí, 46 cặp khác số. Độ phủ khác nhau chưa chứng minh độ chính xác khác nhau.

**Chưa có xác nhận chính thức vì sao hai API có độ phủ khác nhau, hoặc số đo có liên tục/tương đương hay không.** Chuyển hệ thống là giả thuyết, không phải quy chuẩn Vrain được xác nhận. Không cộng/trung bình hai cột và không tự coi toàn bộ chuỗi là đồng nhất. Mask mới yêu cầu **cả 24 giờ lịch sử và 6 giờ nhãn cùng một mã nguồn hợp lệ**. `cross_channel_continuity_unverified=True` được giữ để nhắc giới hạn này.

## 6. Chọn mẫu và chia dữ liệu

| Vai trò theo giờ Việt Nam | Mẫu dùng được ở trạm đã có train | Trạm |
| --- | ---: | ---: |
{chr(10).join(rows)}

Một mẫu chứa 24 hàng lịch sử và 6 nhãn; số mẫu không phải số trận mưa độc lập. `sample_complete` xác nhận đủ X/y và cùng nguồn, kể cả vị trí chưa có train. `sample_ready_r1`/`recommended_sample` còn yêu cầu trạm có mẫu hợp lệ trong train. `sample_ready_r0` cố ý dùng cùng mask bảo thủ R1 cho so sánh có/không R; không phải nhóm weather-only mở rộng của V1.

Giữ mọi hàng thời gian khi cắt chuỗi. **Không lọc `sample_ready_r1=True` hay `dropna()` rồi mới lấy 24 hàng liên tiếp**, vì sẽ nối những giờ không liền nhau. Dùng loader và chỉ lọc chỉ số issue. Các cột raw của API không có số sẽ NaN một cách bình thường; không dropna toàn bộ schema. Không lấy toàn bộ cột số làm X vì file có nhãn tương lai và cờ QC.

Fit scaler/imputer/climatology chỉ trên train. Không tự đưa reserved2025/external2026 vào train; muốn đổi giai đoạn huấn luyện cần thiết kế thí nghiệm mới. Bộ này chưa fit, tuning hoặc chấm mô hình. Năm 2026 phải báo riêng giới hạn thay đổi API; mask cùng nguồn trong từng mẫu chưa chứng minh phân phối giữa các năm không thay đổi.

## 7. Đã kiểm tra và những giới hạn còn lại

Đã kiểm tra {number(verification['all_rows_checked'])} hàng, {number(verification['all_ready_windows_checked'])} cửa sổ: khoảng giờ, đúng trạm, nguồn, nhãn, đủ lịch sử và không băng ranh split. Khí tượng/mưa trên {number(verification['old_v1_hourly_rows_identical'])} hàng giờ V1 cũ được tái hiện; toàn bộ {number(verification['old_v1_ready_windows_preserved'])} cửa sổ cũ giữ nguyên. Có thêm {verification['additional_windows_at_old_truncated_tail']} cửa sổ ở đuôi 2024 nhờ nay có đủ các giờ nhãn trước nửa đêm; không thay kết quả V1 đã đóng băng.

Replay độc lập {number(verification['source_field_replays'])} giá trị khí tượng từ raw và tải lại {verification['fresh_gee_source_cells']} ô nguồn GEE để so khớp. Loader thực được kiểm tra ở cả năm vai trò. Các artifact cũ và slide người dùng được giữ nguyên. Không coi các kiểm tra này là chứng nhận cảm biến.

ERA5 là tái phân tích hồi cứu, thường công bố trễ; timestamp khí tượng trước issue **chưa chứng minh dữ liệu đã có sẵn vào đúng issue**. Phù hợp nghiên cứu hồi cứu với giới hạn công bố rõ; chưa chứng minh vận hành dự báo realtime. Nguồn GEE không cho biết expver trong tệp này, nên chưa xác nhận riêng bản final/ERA5T của phần gần đây; snapshot và checksum được giữ để tái lập.

Nguồn: [ERA5 trên Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_HOURLY), [tài liệu cập nhật ECMWF](https://confluence.ecmwf.int/spaces/CKB/pages/76414402/ERA5%2Bdata%2Bdocumentation). Các cột mưa ERA5/GSMaP/CPC không được dùng làm nhãn hay lấp mưa thiếu.
"""
    (PUBLIC / "MO_TA_DU_LIEU.md").write_text(text, encoding="utf8", newline="\n")
    doc = Document()
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Cm(1.8)
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(10)
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("| "):
            block = []
            while i < len(lines) and lines[i].startswith("| "):
                block.append([s.strip() for s in lines[i].strip("|").split("|")])
                i += 1
            table = doc.add_table(rows=1, cols=len(block[0]))
            table.style = "Light Shading Accent 1"
            for cell, value in zip(table.rows[0].cells, block[0]):
                cell.text = value
            for row in block[2:]:
                for cell, value in zip(table.add_row().cells, row):
                    cell.text = value
            continue
        clean = line.replace("**", "").replace("`", "")
        if line.startswith("# "):
            doc.add_heading(clean[2:], 0)
        elif line.startswith("## "):
            doc.add_heading(clean[3:], 1)
        elif line.startswith("- "):
            doc.add_paragraph(clean[2:], style="List Bullet")
        elif line.strip():
            doc.add_paragraph(clean)
        i += 1
    doc.save(PUBLIC / "MO_TA_DU_LIEU.docx")
    guide = f'''# Đọc bộ giờ mới bằng loader

Từ thư mục gốc repo; dùng loader mới `src/hourly_station_update.py` và loader nền
`src/station_forecast_data.py`. Loader V1 cũ vẫn giữ chặn đọc năm2025; dùng lớp mới
để chọn rõ reserved2025/external2026 của bản cập nhật được người dùng cho phép.
Không lọc bỏ hàng thời gian trước khi đưa vào loader.

```python
from src.hourly_station_update import HourlyStationData

path = "data/processed/{VERSION}/{DATASET}"
train = HourlyStationData(path, "train", "E7", use_rain=True,
                            stations=["ST001"])
sample = train[0]
print(sample["x"].shape)  # (24, 45)
print(sample["y"].shape)  # (6,)
```

`stations` là mã trong file, chọn từ lịch sử train. Bỏ tham số để lấy mọi
trạm đủ điều kiện; có thể tốn RAM vì loader đọc toàn bộ các hàng của trạm.
Đổi split sang cal/dev/reserved2025/external2026 để đọc riêng vai trò.
Không lấy các tập để dành làm train chỉ vì chúng đã có trong file.
Các E dùng cùng `sample_ready_r1`, chỉ thay danh sách đầu vào.

Muốn xem bảng: `pd.read_parquet(path, filters=[("station_id", "=", "ST001")])`.
`sample_complete` khác `sample_ready_r1`: cột sau thêm điều kiện trạm có train.
Đọc `MO_TA_DU_LIEU.docx` trước khi chia lại năm hoặc dùng số mưa hai API.
File mới chỉ chứa resolution 1h; nhánh ngày GFS dùng file riêng của gói 16/11.
'''
    (PUBLIC / "HUONG_DAN_TRAIN.md").write_text(guide, encoding="utf8", newline="\n")
    readme = f"""# Dữ liệu giờ ERA5 + Vrain đến 2026

Bản 17/11/2026 đã ghép và kiểm chứng. File chính private: `{OUT.relative_to(ROOT).as_posix()}/{DATASET}`.
Gửi nhóm ZIP `PBL6_BILSTM_GIO_2021_2026.zip` trong cùng thư mục dữ liệu; chỉ có năm file.

Đọc [mô tả](MO_TA_DU_LIEU.md), [Word](MO_TA_DU_LIEU.docx), [cách đọc để train](HUONG_DAN_TRAIN.md).
Mưa tới 19h15/11, khí tượng ghép tới hàng kết thúc07h11/11/2026 giờ Việt Nam. Giữ thiếu ở đuôi.
86 vị trí; 79 có train theo split cố định. 44 khí tượng/lịch + mưa quá khứ; X24×45, y6.
Hai API đều Vrain, chưa xác nhận liên tục; mẫu yêu cầu cùng nguồn cả lịch sử/nhãn.
Đây là dữ liệu hồi cứu, không phải bằng chứng khả dụng realtime hay kết quả train mới.
Mô tả và số liệu kiểm chứng là aggregate; raw/registry/Parquet không nằm trên GitHub.
"""
    (PUBLIC / "README.md").write_text(readme, encoding="utf8", newline="\n")
    members = [OUT / DATASET]
    for name in ["MO_TA_DU_LIEU.docx", "HUONG_DAN_TRAIN.md", "feature_groups.json"]:
        shutil.copyfile(PUBLIC/name, OUT/name)
        members.append(OUT/name)
    hashes = {p.name: sha(p) for p in members}
    write_json(OUT / "SHA256.json", hashes)
    members.append(OUT / "SHA256.json")
    archive = OUT / "PBL6_BILSTM_GIO_2021_2026.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as z:
        for path in members:
            z.write(path, arcname=path.name)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None or len(z.namelist()) != 5:
            raise ValueError("Invalid handoff ZIP")
        import hashlib
        for name, digest in hashes.items():
            h = hashlib.sha256()
            with z.open(name) as stream:
                for chunk in iter(lambda: stream.read(4*1024*1024), b""):
                    h.update(chunk)
            if h.hexdigest() != digest:
                raise ValueError("Handoff member checksum mismatch")
    release = dict(status="complete_with_documented_gaps_and_source_transition",
        dataset_sha256=summary["sha256"], handoff_zip_sha256=sha(archive),
        handoff_zip_bytes=archive.stat().st_size, zip_members=hashes,
        models_trained=False, models_scored=False,
        code_sha256={p: sha(ROOT/p) for p in ["src/hourly_station_update.py",
            "scripts/collect_hourly_era5_update.py", "scripts/build_hourly_station_update.py",
            "scripts/verify_hourly_station_update.py", "scripts/publish_hourly_station_update.py",
            "tests/test_hourly_station_update.py"]})
    write_json(PUBLIC / "release.json", release)
    print(json.dumps(release), flush=True)


if __name__ == "__main__":
    main()
