# PBL6: Dự Báo Lượng Mưa

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-orange.svg)](https://pytorch.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Dự án nghiên cứu và xây dựng hệ thống dự báo lượng mưa hạn ngắn (1–6 giờ) và hạn vừa (24–72 giờ) tại khu vực

---

## 📌 Cấu Trúc Thư Mục Dự Án

```text
├── data/
│   ├── config.py                          # Cấu hình tập trung (tọa độ, bbox, tham số)
│   ├── download_openmeteo.py              # Script thu thập dữ liệu bề mặt trạm
│   ├── download_era5_features.py          # Script tải bổ sung CAPE, CIN, TCWV, Soil Moisture
│   ├── download_missing_pl850.py          # Script tải bù các tháng thiếu của tầng 850 hPa
│   ├── create_merged_datasets.py          # Script hợp nhất dữ liệu (Bản baseline & Bản full features)
│   ├── samples/                           # Dữ liệu mẫu kiểm thử nhanh cho code
│   └── processed/                         # Báo cáo chẩn đoán (merge_diagnostics.json)
├── models/                                # Các mô hình đã huấn luyện (.pth, scaler.pkl)
│   ├── best_bilstm_model.pth              # Model Bi-LSTM đa nguồn tốt nhất
│   ├── surface_only/                      # Các mô hình đối chứng nhánh bề mặt
│   │   ├── best_surface_model.pth
│   │   ├── rain_alert_dual_head.pth       # Mô hình dự báo lượng mưa kết hợp cảnh báo dông
│   │   └── event_balanced.pth             # Mô hình huấn luyện cân bằng sự kiện mưa lớn
├── plots/                                 # Đồ thị đánh giá độ phân giải cao 300 DPI
│   ├── plot1_feature_correlation.png      # Tương quan giữa các đặc trưng
│   ├── plot2_loss_curve.png               # Đường cong suy giảm hàm mất mát (Loss curve)
│   ├── plot3_actual_vs_predicted_timeseries.png # So sánh thực tế vs Dự báo chuỗi thời gian
│   └── plot4_residuals_scatter.png        # Phân tán phần dư sai số
├── src/                                   # Mã nguồn module pipeline cốt lõi
│   ├── merge_raw_data.py                  # Module tiền xử lý và nối chuỗi thời gian
│   └── ...
├── run_full_pipeline.py                   # Script chạy trọn vẹn toàn bộ pipeline
├── requirements.txt                       # Thư viện phụ thuộc
├── DATA_GAP_PLAN.md                       # Kế hoạch và nhật ký xử lý dữ liệu khuyết
└── SURFACE_BASELINE_REPORT.md             # Báo cáo đánh giá các mô hình cơ sở
```

---

