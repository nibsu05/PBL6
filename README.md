# PBL6: Dự Báo Lượng Mưa

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-orange.svg)](https://pytorch.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Dự án nghiên cứu đóng góp của các nhóm đặc trưng dữ liệu cho dự đoán mưa vùng trực tiếp tại Đà Nẵng mới (Đà Nẵng cũ + Quảng Nam).

**Phạm vi hiện tại — 21/10/2026:** tổng hợp đầu vào và nhãn theo vùng trước mô hình, nghiên cứu thêm/bớt đặc trưng E0–E7. Nhóm triển khai hai nhánh: Bi-LSTM 1–6 giờ và TFT 24–72 giờ; mỗi nhánh có LightGBM đối chứng và giao thức riêng. Người dùng phụ trách TFT, thành viên khác phụ trách Bi-LSTM. App chưa phải trọng tâm. [Phương án vùng nền ngày 20/10](reports/regional_research_plan_2026_10_20/README.md) có Word và ma trận 18 quyết định × 6 tiêu chí; [báo cáo V1/V2](reports/regional_danang_v1_v2/README.md) và [rà soát Bi-LSTM trên dev](reports/research_rainfall/dev_bilstm_review_2026_10_20.md) lưu bằng chứng trước nhánh ngày. Chưa xác nhận Bi-LSTM vùng mới đã được thành viên hoàn tất; test 2025 tiếp tục giữ kín.

**Nhánh ngày 21/10, đã có ma trận phát triển:** [TFT/LightGBM 24–72 giờ, E0–E7, ba seed](reports/short_range_ablation_2026_10_21/README.md) có Word, 8 slide, FAQ, danh mục 44 biến, CI 20.000 bootstrap và kiểm chứng 96/96 lượt. TFT thêm riêng A hoặc M có tín hiệu cải thiện ngày 1 sau hiệu chỉnh 9 phép so; chưa có bằng chứng tương tự ở ngày 2–3 hoặc SST. Giữ nguyên [pilot](reports/short_range_pilot_2026_10_21/README.md). [Kế hoạch đầy đủ](reports/short_range_plan_2026_10_21/README.md) còn ranh/QC nhãn và kiểm định cuối; footprint 93 ô vẫn xấp xỉ, năm 2025 chưa mở.

**Chuẩn bị báo cáo trong 30 phút:** [bản ngắn Word, 5 slide và lời trình bày 5 phút](reports/short_range_brief_2026_10_21/README.md) tổng hợp từ số liệu đã kiểm chứng. Mã/báo cáo trên `research/tft-regional`, [PR #1 vào main](https://github.com/nibsu05/PBL6/pull/1) đang mở.

**Giải thích đầy đủ cho thành viên nhóm:** [tài liệu Word/Markdown và Excel 18 sheet](reports/short_range_explained_2026_10_21/README.md) giải thích mục tiêu ba tổng mưa vùng 24 giờ, đủ 44 đặc trưng và E0–E7, lý do thử TFT, giới hạn so Informer, vai trò LightGBM, công thức/ví dụ đọc từng metric. Có đủ 48 dòng chính, chi tiết năm/mùa/seed/ngưỡng và bằng chứng 96 lượt; đây là tổng hợp development, không mở test 2025.

---

## 🚀 Pipeline v2 (từ 11/10/2026) — bắt đầu từ đây

**Thành viên nhóm, đọc trước:** [`KE_HOACH_DU_AN.md`](KE_HOACH_DU_AN.md) (dự án làm gì, quy trình, đang ở giai đoạn nào, lộ trình, phân công).
Chi tiết kỹ thuật: [`project_plan_v2.md`](project_plan_v2.md). Bối cảnh cho AI agent: [`CLAUDE.md`](CLAUDE.md).

- Pipeline nguồn và cấu hình trước đây: Bi-LSTM (0–6 h), TFT (1–3 ngày), nhãn GSMaP v8 hiệu chỉnh trạm và lưới 0,1°, 2015 → 09/2026. Nghiên cứu hiện tại dùng các ô để tạo chuỗi vùng; cần chốt giao ranh và kiểm chứng nhãn trước huấn luyện đầy đủ.
- Kiểm chứng: 10 trạm synop NOAA GSOD. Bảng baseline và Thí nghiệm 0 ở [`reports/station_benchmark/README.md`](reports/station_benchmark/README.md).
- Dữ liệu nguồn v2 (khoảng 2,9 GB, file `pbl6_data_v2_2026-10-11.tar`) nằm trên Google Drive (đường dẫn bên dưới). Giải nén ở thư mục gốc repo rồi chạy:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
tar -xf pbl6_data_v2_2026-10-11.tar
.venv/bin/python scripts/package_data.py verify
.venv/bin/python scripts/build_dataset_v2.py --years 2015 2026
.venv/bin/python -c "from src.dataloader_v2 import build_cell_major; build_cell_major()"
.venv/bin/python scripts/inspect_dataloader_v2.py
```

Các tài liệu và kết quả trước 11/10/2026 (`project_master_plan.md`, `SURFACE_BASELINE_REPORT.md`, `reports/informer_baseline_report.md`…) được giữ lại để tham khảo lịch sử. Chúng dùng nhãn ERA5/Open-Meteo, mà nhãn này đã được chứng minh là bỏ sót mưa to.

---

## 📌 Cấu Trúc Thư Mục Dự Án

```text
├── data/                                  # Dữ liệu mẫu & script thu thập dữ liệu
│   ├── config.py                          # Cấu hình tập trung (tọa độ, bbox, tham số)
│   ├── download_openmeteo.py              # Script thu thập dữ liệu bề mặt trạm
│   ├── download_era5_features.py          # Script tải bổ sung CAPE, CIN, TCWV, Soil Moisture
│   ├── create_merged_datasets.py          # Script hợp nhất dữ liệu (Bản baseline & Bản full features)
│   ├── samples/                           # Dữ liệu mẫu kiểm thử nhanh cho code
│   └── processed/                         # Báo cáo chẩn đoán (merge_diagnostics.json)
├── demo/                                  # Web demo dự báo thời tiết Đà Nẵng
├── experiments/                           # Cấu hình & kết quả thực nghiệm mô hình
├── models/                                # Các mô hình đã huấn luyện (.pth, scaler.pkl)
│   ├── best_bilstm_model.pth              # Model Bi-LSTM đa nguồn tốt nhất
│   ├── informer/                          # Checkpoints mô hình Informer
│   └── surface_only/                      # Các mô hình đối chứng nhánh bề mặt
├── plots/                                 # Đồ thị đánh giá độ phân giải cao 300 DPI
├── reports/                               # Báo cáo PDF 18 trang & slide PowerPoint
├── scripts/                               # Các script đánh giá, kiểm toán & thực nghiệm
├── src/                                   # Mã nguồn module pipeline cốt lõi
├── tests/                                 # Unit tests
├── run_full_pipeline.py                   # Script chạy trọn vẹn toàn bộ pipeline
├── requirements.txt                       # Thư viện phụ thuộc
├── DATA_GAP_PLAN.md                       # Kế hoạch và nhật ký xử lý dữ liệu khuyết
└── SURFACE_BASELINE_REPORT.md             # Báo cáo đánh giá các mô hình cơ sở
```

---

Data: [Google Drive](https://drive.google.com/drive/folders/1FQtUt-nV7P2UCDxUuN5Poeub0Cc01pVl?usp=sharing)
