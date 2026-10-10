# PBL6: Dự Báo Lượng Mưa

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-orange.svg)](https://pytorch.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Dự án nghiên cứu và xây dựng hệ thống dự báo lượng mưa hạn ngắn (1–6 giờ) và hạn vừa (24–72 giờ) tại khu vực

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

## 📦 Dữ Liệu Dự Án (Google Drive)

Link tải dữ liệu: [Google Drive](https://drive.google.com/drive/folders/1FQtUt-nV7P2UCDxUuN5Poeub0Cc01pVl?usp=sharing)
