# PBL6: Dự Báo Lượng Mưa và Cảnh Báo Mưa Cực Đoan Tại Đà Nẵng Sử Dụng Machine Learning & Deep Learning

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-orange.svg)](https://pytorch.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Dự án nghiên cứu và xây dựng hệ thống dự báo lượng mưa hạn ngắn (1–6 giờ) và hạn vừa (24–72 giờ) tại khu vực thành phố Đà Nẵng dựa trên chuỗi thời gian đa nguồn (Multivariate Time Series) kết hợp giữa:
1. **Dữ liệu khí tượng bề mặt trạm:** Open-Meteo & Trạm quan trắc mặt đất (Nhiệt độ, Độ ẩm, Áp suất, Gió 10m, Lượng mưa thực tế).
2. **Dữ liệu tái phân tích khí quyển ERA5 (Copernicus ECMWF):** 
   - Trường nhiệt độ mặt biển (SST) vùng Biển Đông kề bên.
   - Trường gió U, V và độ ẩm riêng tầng đối lưu thấp 850 hPa.
   - **Các chỉ số nhiệt động học đối lưu:** Thế năng đối lưu khả dụng (**CAPE**), Năng lượng ức chế đối lưu (**CIN**), và Tổng lượng hơi nước toàn cột khí quyển (**TCWV**).
   - **Độ ẩm đất tầng mặt:** Lớp đất $0 - 7\text{ cm}$ (`swvl1`) mang bộ nhớ nhiệt động bề mặt đệm.
3. **Chỉ số dao động hoàn lưu đại dương quy mô lớn:** Oceanic Niño Index (**ONI / ENSO**).

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

## 🚀 Hướng Dẫn Cài Đặt và Chạy

### 1. Cài đặt môi trường

```bash
# Clone repository
git clone https://github.com/nibsu05/PBL6.git
cd PBL6

# Tạo môi trường ảo
python -m venv .venv
source .venv/bin/activate  # Trên Linux/macOS
# hoặc .\.venv\Scripts\Activate.ps1 trên Windows

# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

### 2. Sử dụng mô hình đã huấn luyện (Inference)

Các checkpoint mô hình đã được huấn luyện sẵn và lưu trực tiếp trong thư mục `models/`. Bạn có thể chạy đánh giá ngay mà không cần huấn luyện lại:

```bash
python evaluate_surface_baseline.py
```

### 3. Huấn luyện lại toàn bộ Pipeline

```bash
# Tiền xử lý dữ liệu và tạo cửa sổ trượt (Sliding Windows)
python run_full_pipeline.py --prepare-only

# Huấn luyện mô hình Bi-LSTM với dữ liệu đã chuẩn bị
python run_full_pipeline.py --reuse-merged
```

---

## 📊 Tóm Tắt Kết Quả Mô Hình Baseline

* **Kiến trúc:** Bidirectional LSTM (Bi-LSTM) với cửa sổ đầu vào 24 giờ $\rightarrow$ Dự báo đa bước 1–6 giờ tiếp theo ($t+1 \to t+6$).
* **Đánh giá trên tập Test gộp (Horizon 1–6h):**
  * **MAE:** $0.3812\text{ mm/h}$
  * **RMSE:** $1.1464\text{ mm/h}$
  * **Hệ số tương quan (CC):** $0.5323$
  * **Hệ số xác định ($R^2$):** $0.2480$
* **Chi tiết theo từng Horizon:** Sai số tăng dần từ $\text{MAE } 0.3378\text{ mm/h}$ ở $t+1$ lên $0.4234\text{ mm/h}$ ở $t+6$.

---

## 📦 Về Bộ Dữ Liệu Lớn (Full Dataset)

Do các file NetCDF tái phân tích khí quyển ERA5 và file chuỗi thời gian đầy đủ 11.5 năm (2015–2026) có dung lượng hàng gigabyte, dữ liệu thô lớn được lưu trữ trên Cloud Storage:
* Toàn bộ mã nguồn tự động thu thập từ **Copernicus CDS API** và **Open-Meteo API** được cung cấp đầy đủ trong thư mục `data/`.
* Các file cấu hình mẫu và báo cáo chẩn đoán chất lượng dữ liệu được lưu tại `data/processed/merge_diagnostics.json`.

---

## 📝 Bản Quyền

Dự án phục vụ mục đích nghiên cứu học thuật trong khuôn khổ đồ án PBL6.
Mọi đóng góp và câu hỏi vui lòng mở issue trên repository!
