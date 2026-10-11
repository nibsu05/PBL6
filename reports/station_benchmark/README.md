# Đối chiếu tổng mưa ngày với trạm synop (baseline và Thí nghiệm 0)

Sinh tự động bởi `scripts/station_daily_benchmark.py`; đừng sửa tay.
Ngày tính theo UTC (07h–07h giờ Việt Nam). Trạm: NOAA GSOD sau kiểm soát chất lượng
(chỉ ngày đủ 24 h hoặc ngày khô; năm-trạm báo toàn 0 bị loại — xem `gsod_coverage.json`).
Mọi nguồn trong một bảng được chấm trên cùng tập (trạm, ngày). Ngưỡng tính `>=`.
BSS so với xác suất khí hậu của trạm, coi dự báo tất định là xác suất 0/1.
Điểm trạm khác giá trị trung bình ô lưới (25 km với ERA5/ECMWF, 11 km với vệ tinh),
nên mọi nguồn lưới đều bị phạt một phần do khác biệt quy mô — so sánh *giữa các nguồn* vẫn công bằng.

## Giai đoạn A: 2021-01-01 → 2024-12-31 (10 trạm, 13836 trạm-ngày)

### Gộp mọi trạm

| Nguồn | n | obs_mean | fcst_mean | MAE | bias | CC | CSI>=16 | FBI>=16 | BSS>=16 | CSI>=50 | POD>=50 | FAR>=50 | FBI>=50 | BSS>=50 | n_obs>=50 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Khí hậu (TB theo ngày-năm) | 13836.00 | 6.44 | 5.58 | 8.07 | -0.86 | 0.31 | 0.14 | 0.68 | -0.55 | 0.00 | 0.00 | — | 0.00 | -0.09 | 437.00 |
| Persistence (trạm hôm trước) | 13836.00 | 6.44 | 6.57 | 8.48 | 0.14 | 0.37 | 0.21 | 1.03 | -0.63 | 0.14 | 0.25 | 0.75 | 1.03 | -0.65 | 437.00 |
| Nhãn hiện tại (Open-Meteo ≈ ERA5) | 13836.00 | 6.44 | 6.01 | 6.78 | -0.43 | 0.55 | 0.28 | 0.99 | -0.37 | 0.17 | 0.21 | 0.52 | 0.44 | -0.11 | 437.00 |
| IMERG Final V07 | 13836.00 | 6.44 | 6.02 | 6.89 | -0.42 | 0.56 | 0.29 | 1.01 | -0.37 | 0.22 | 0.32 | 0.59 | 0.78 | -0.25 | 437.00 |
| IMERG V07 chưa hiệu chỉnh | 13836.00 | 6.44 | 4.63 | 6.54 | -1.81 | 0.51 | 0.27 | 0.83 | -0.30 | 0.16 | 0.20 | 0.58 | 0.48 | -0.18 | 437.00 |
| GSMaP v8 | 13836.00 | 6.44 | 5.13 | 6.81 | -1.30 | 0.50 | 0.25 | 0.71 | -0.26 | 0.19 | 0.29 | 0.65 | 0.82 | -0.35 | 437.00 |
| GSMaP v8 hiệu chỉnh trạm | 13836.00 | 6.44 | 6.41 | 5.30 | -0.03 | 0.72 | 0.42 | 1.03 | -0.01 | 0.33 | 0.44 | 0.44 | 0.78 | 0.02 | 437.00 |

### Hiệu số theo cặp, khoảng tin cậy 95 % (bootstrap khối 5 ngày)

MAE: âm là A tốt hơn. CSI: dương là A tốt hơn. Khoảng chứa 0 nghĩa là chưa phân biệt được.

| A − B | metric | a | b | diff | ci_low | ci_high |
|---|---|---|---|---|---|---|
| Persistence (trạm hôm trước) − Khí hậu (TB theo ngày-năm) | MAE | 8.48 | 8.07 | 0.41 | 0.00 | 0.82 |
| Persistence (trạm hôm trước) − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.21 | 0.14 | 0.07 | 0.04 | 0.10 |
| Persistence (trạm hôm trước) − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.14 | 0.00 | 0.14 | 0.11 | 0.18 |
| Nhãn hiện tại (Open-Meteo ≈ ERA5) − Khí hậu (TB theo ngày-năm) | MAE | 6.78 | 8.07 | -1.29 | -1.59 | -1.00 |
| Nhãn hiện tại (Open-Meteo ≈ ERA5) − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.28 | 0.14 | 0.14 | 0.11 | 0.17 |
| Nhãn hiện tại (Open-Meteo ≈ ERA5) − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.17 | 0.00 | 0.17 | 0.13 | 0.21 |
| IMERG Final V07 − Khí hậu (TB theo ngày-năm) | MAE | 6.89 | 8.07 | -1.19 | -1.55 | -0.84 |
| IMERG Final V07 − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.29 | 0.14 | 0.14 | 0.11 | 0.18 |
| IMERG Final V07 − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.22 | 0.00 | 0.22 | 0.18 | 0.26 |
| IMERG V07 chưa hiệu chỉnh − Khí hậu (TB theo ngày-năm) | MAE | 6.54 | 8.07 | -1.53 | -1.86 | -1.21 |
| IMERG V07 chưa hiệu chỉnh − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.27 | 0.14 | 0.12 | 0.09 | 0.16 |
| IMERG V07 chưa hiệu chỉnh − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.16 | 0.00 | 0.16 | 0.12 | 0.19 |
| GSMaP v8 − Khí hậu (TB theo ngày-năm) | MAE | 6.81 | 8.07 | -1.27 | -1.69 | -0.84 |
| GSMaP v8 − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.25 | 0.14 | 0.11 | 0.08 | 0.14 |
| GSMaP v8 − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.19 | 0.00 | 0.19 | 0.15 | 0.23 |
| GSMaP v8 hiệu chỉnh trạm − Khí hậu (TB theo ngày-năm) | MAE | 5.30 | 8.07 | -2.77 | -3.12 | -2.43 |
| GSMaP v8 hiệu chỉnh trạm − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.42 | 0.14 | 0.28 | 0.25 | 0.31 |
| GSMaP v8 hiệu chỉnh trạm − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.33 | 0.00 | 0.33 | 0.29 | 0.38 |
| IMERG Final V07 − Nhãn hiện tại (Open-Meteo ≈ ERA5) | MAE | 6.89 | 6.78 | 0.10 | -0.17 | 0.36 |
| IMERG Final V07 − Nhãn hiện tại (Open-Meteo ≈ ERA5) | CSI>=16 | 0.29 | 0.28 | 0.00 | -0.02 | 0.03 |
| IMERG Final V07 − Nhãn hiện tại (Open-Meteo ≈ ERA5) | CSI>=50 | 0.22 | 0.17 | 0.05 | 0.01 | 0.08 |
| IMERG V07 chưa hiệu chỉnh − Nhãn hiện tại (Open-Meteo ≈ ERA5) | MAE | 6.54 | 6.78 | -0.24 | -0.48 | -0.01 |
| IMERG V07 chưa hiệu chỉnh − Nhãn hiện tại (Open-Meteo ≈ ERA5) | CSI>=16 | 0.27 | 0.28 | -0.02 | -0.05 | 0.01 |
| IMERG V07 chưa hiệu chỉnh − Nhãn hiện tại (Open-Meteo ≈ ERA5) | CSI>=50 | 0.16 | 0.17 | -0.02 | -0.05 | 0.02 |
| GSMaP v8 − Nhãn hiện tại (Open-Meteo ≈ ERA5) | MAE | 6.81 | 6.78 | 0.03 | -0.32 | 0.38 |
| GSMaP v8 − Nhãn hiện tại (Open-Meteo ≈ ERA5) | CSI>=16 | 0.25 | 0.28 | -0.03 | -0.06 | -0.00 |
| GSMaP v8 − Nhãn hiện tại (Open-Meteo ≈ ERA5) | CSI>=50 | 0.19 | 0.17 | 0.02 | -0.02 | 0.06 |
| GSMaP v8 hiệu chỉnh trạm − Nhãn hiện tại (Open-Meteo ≈ ERA5) | MAE | 5.30 | 6.78 | -1.48 | -1.71 | -1.27 |
| GSMaP v8 hiệu chỉnh trạm − Nhãn hiện tại (Open-Meteo ≈ ERA5) | CSI>=16 | 0.42 | 0.28 | 0.14 | 0.12 | 0.16 |
| GSMaP v8 hiệu chỉnh trạm − Nhãn hiện tại (Open-Meteo ≈ ERA5) | CSI>=50 | 0.33 | 0.17 | 0.16 | 0.11 | 0.21 |

### CSI ≥50 mm theo vùng

| Nguồn | Bắc Bộ | Bắc Trung Bộ | Nam Bộ | Nam Trung Bộ | Trung Trung Bộ | Tây Nguyên |
|---|---|---|---|---|---|---|
| Khí hậu (TB theo ngày-năm) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Nhãn hiện tại (Open-Meteo ≈ ERA5) | 0.15 | 0.18 | 0.04 | 0.11 | 0.26 | 0.01 |
| GSMaP v8 | 0.14 | 0.25 | 0.07 | 0.21 | 0.24 | 0.05 |
| GSMaP v8 hiệu chỉnh trạm | 0.08 | 0.41 | 0.00 | 0.30 | 0.46 | 0.12 |
| IMERG Final V07 | 0.14 | 0.27 | 0.11 | 0.22 | 0.28 | 0.06 |
| IMERG V07 chưa hiệu chỉnh | 0.12 | 0.16 | 0.10 | 0.16 | 0.21 | 0.03 |
| Persistence (trạm hôm trước) | 0.07 | 0.19 | 0.02 | 0.11 | 0.21 | 0.05 |

## Giai đoạn B: 2024-02-08 → 2025-08-24 (10 trạm, 5313 trạm-ngày)

### Gộp mọi trạm

| Nguồn | n | obs_mean | fcst_mean | MAE | bias | CC | CSI>=16 | FBI>=16 | BSS>=16 | CSI>=50 | POD>=50 | FAR>=50 | FBI>=50 | BSS>=50 | n_obs>=50 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Khí hậu (TB theo ngày-năm) | 5313.00 | 5.47 | 5.01 | 7.16 | -0.46 | 0.26 | 0.10 | 0.59 | -0.55 | 0.00 | 0.00 | — | 0.00 | -0.06 | 130.00 |
| Persistence (trạm hôm trước) | 5313.00 | 5.47 | 5.61 | 7.54 | 0.14 | 0.34 | 0.17 | 1.04 | -0.72 | 0.11 | 0.20 | 0.80 | 1.02 | -0.72 | 130.00 |
| Nhãn hiện tại (Open-Meteo ≈ ERA5) | 5313.00 | 5.47 | 5.37 | 6.06 | -0.10 | 0.57 | 0.25 | 1.03 | -0.46 | 0.17 | 0.22 | 0.55 | 0.48 | -0.11 | 130.00 |
| ECMWF IFS trước 1 ngày | 5313.00 | 5.47 | 5.86 | 6.48 | 0.38 | 0.52 | 0.25 | 1.12 | -0.53 | 0.16 | 0.21 | 0.56 | 0.47 | -0.12 | 130.00 |
| ECMWF IFS trước 2 ngày | 5313.00 | 5.47 | 5.74 | 6.62 | 0.26 | 0.49 | 0.23 | 1.02 | -0.51 | 0.12 | 0.15 | 0.67 | 0.47 | -0.23 | 130.00 |
| ECMWF IFS trước 3 ngày | 5313.00 | 5.47 | 5.97 | 6.75 | 0.49 | 0.45 | 0.25 | 1.15 | -0.53 | 0.12 | 0.15 | 0.67 | 0.46 | -0.23 | 130.00 |
| ECMWF IFS trước 5 ngày | 5313.00 | 5.47 | 5.96 | 7.14 | 0.48 | 0.34 | 0.20 | 1.10 | -0.66 | 0.09 | 0.12 | 0.73 | 0.46 | -0.29 | 130.00 |
| GFS trước 1 ngày | 5313.00 | 5.47 | 4.90 | 6.04 | -0.58 | 0.57 | 0.22 | 0.85 | -0.42 | 0.16 | 0.20 | 0.59 | 0.48 | -0.15 | 130.00 |
| GFS trước 2 ngày | 5313.00 | 5.47 | 4.91 | 6.36 | -0.57 | 0.51 | 0.19 | 0.81 | -0.48 | 0.12 | 0.15 | 0.67 | 0.46 | -0.23 | 130.00 |
| GFS trước 3 ngày | 5313.00 | 5.47 | 5.13 | 6.63 | -0.34 | 0.41 | 0.20 | 0.88 | -0.52 | 0.13 | 0.18 | 0.66 | 0.52 | -0.23 | 130.00 |
| IMERG Final V07 | 5313.00 | 5.47 | 5.35 | 6.26 | -0.12 | 0.54 | 0.25 | 1.03 | -0.47 | 0.17 | 0.25 | 0.65 | 0.72 | -0.29 | 130.00 |
| IMERG V07 chưa hiệu chỉnh | 5313.00 | 5.47 | 4.21 | 5.96 | -1.27 | 0.48 | 0.22 | 0.84 | -0.40 | 0.13 | 0.17 | 0.65 | 0.48 | -0.21 | 130.00 |
| GSMaP v8 | 5313.00 | 5.47 | 4.83 | 6.25 | -0.65 | 0.54 | 0.22 | 0.75 | -0.35 | 0.16 | 0.25 | 0.71 | 0.86 | -0.44 | 130.00 |
| GSMaP v8 hiệu chỉnh trạm | 5313.00 | 5.47 | 5.36 | 4.67 | -0.11 | 0.68 | 0.38 | 0.99 | -0.07 | 0.30 | 0.38 | 0.43 | 0.68 | 0.04 | 130.00 |

### Hiệu số theo cặp, khoảng tin cậy 95 % (bootstrap khối 5 ngày)

MAE: âm là A tốt hơn. CSI: dương là A tốt hơn. Khoảng chứa 0 nghĩa là chưa phân biệt được.

| A − B | metric | a | b | diff | ci_low | ci_high |
|---|---|---|---|---|---|---|
| Persistence (trạm hôm trước) − Khí hậu (TB theo ngày-năm) | MAE | 7.54 | 7.16 | 0.37 | -0.21 | 0.96 |
| Persistence (trạm hôm trước) − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.17 | 0.10 | 0.07 | 0.03 | 0.12 |
| Persistence (trạm hôm trước) − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.11 | 0.00 | 0.11 | 0.06 | 0.16 |
| Nhãn hiện tại (Open-Meteo ≈ ERA5) − Khí hậu (TB theo ngày-năm) | MAE | 6.06 | 7.16 | -1.11 | -1.65 | -0.63 |
| Nhãn hiện tại (Open-Meteo ≈ ERA5) − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.25 | 0.10 | 0.15 | 0.10 | 0.20 |
| Nhãn hiện tại (Open-Meteo ≈ ERA5) − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.17 | 0.00 | 0.17 | 0.08 | 0.25 |
| ECMWF IFS trước 1 ngày − Khí hậu (TB theo ngày-năm) | MAE | 6.48 | 7.16 | -0.69 | -1.23 | -0.20 |
| ECMWF IFS trước 1 ngày − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.25 | 0.10 | 0.15 | 0.10 | 0.19 |
| ECMWF IFS trước 1 ngày − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.16 | 0.00 | 0.16 | 0.08 | 0.24 |
| ECMWF IFS trước 2 ngày − Khí hậu (TB theo ngày-năm) | MAE | 6.62 | 7.16 | -0.55 | -1.13 | -0.03 |
| ECMWF IFS trước 2 ngày − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.23 | 0.10 | 0.13 | 0.09 | 0.18 |
| ECMWF IFS trước 2 ngày − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.12 | 0.00 | 0.12 | 0.04 | 0.19 |
| ECMWF IFS trước 3 ngày − Khí hậu (TB theo ngày-năm) | MAE | 6.75 | 7.16 | -0.42 | -1.06 | 0.16 |
| ECMWF IFS trước 3 ngày − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.25 | 0.10 | 0.15 | 0.11 | 0.20 |
| ECMWF IFS trước 3 ngày − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.12 | 0.00 | 0.12 | 0.04 | 0.20 |
| ECMWF IFS trước 5 ngày − Khí hậu (TB theo ngày-năm) | MAE | 7.14 | 7.16 | -0.02 | -0.58 | 0.55 |
| ECMWF IFS trước 5 ngày − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.20 | 0.10 | 0.10 | 0.07 | 0.15 |
| ECMWF IFS trước 5 ngày − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.09 | 0.00 | 0.09 | 0.02 | 0.17 |
| GFS trước 1 ngày − Khí hậu (TB theo ngày-năm) | MAE | 6.04 | 7.16 | -1.12 | -1.67 | -0.63 |
| GFS trước 1 ngày − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.22 | 0.10 | 0.12 | 0.08 | 0.16 |
| GFS trước 1 ngày − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.16 | 0.00 | 0.16 | 0.07 | 0.23 |
| GFS trước 2 ngày − Khí hậu (TB theo ngày-năm) | MAE | 6.36 | 7.16 | -0.81 | -1.37 | -0.31 |
| GFS trước 2 ngày − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.19 | 0.10 | 0.09 | 0.04 | 0.14 |
| GFS trước 2 ngày − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.12 | 0.00 | 0.12 | 0.05 | 0.18 |
| GFS trước 3 ngày − Khí hậu (TB theo ngày-năm) | MAE | 6.63 | 7.16 | -0.54 | -1.06 | -0.08 |
| GFS trước 3 ngày − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.20 | 0.10 | 0.09 | 0.04 | 0.14 |
| GFS trước 3 ngày − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.13 | 0.00 | 0.13 | 0.07 | 0.21 |
| IMERG Final V07 − Khí hậu (TB theo ngày-năm) | MAE | 6.26 | 7.16 | -0.91 | -1.47 | -0.46 |
| IMERG Final V07 − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.25 | 0.10 | 0.15 | 0.10 | 0.19 |
| IMERG Final V07 − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.17 | 0.00 | 0.17 | 0.09 | 0.25 |
| IMERG V07 chưa hiệu chỉnh − Khí hậu (TB theo ngày-năm) | MAE | 5.96 | 7.16 | -1.20 | -1.72 | -0.75 |
| IMERG V07 chưa hiệu chỉnh − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.22 | 0.10 | 0.12 | 0.08 | 0.17 |
| IMERG V07 chưa hiệu chỉnh − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.13 | 0.00 | 0.13 | 0.05 | 0.20 |
| GSMaP v8 − Khí hậu (TB theo ngày-năm) | MAE | 6.25 | 7.16 | -0.91 | -1.62 | -0.28 |
| GSMaP v8 − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.22 | 0.10 | 0.12 | 0.07 | 0.16 |
| GSMaP v8 − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.16 | 0.00 | 0.16 | 0.08 | 0.24 |
| GSMaP v8 hiệu chỉnh trạm − Khí hậu (TB theo ngày-năm) | MAE | 4.67 | 7.16 | -2.49 | -3.08 | -1.98 |
| GSMaP v8 hiệu chỉnh trạm − Khí hậu (TB theo ngày-năm) | CSI>=16 | 0.38 | 0.10 | 0.28 | 0.23 | 0.33 |
| GSMaP v8 hiệu chỉnh trạm − Khí hậu (TB theo ngày-năm) | CSI>=50 | 0.30 | 0.00 | 0.30 | 0.20 | 0.38 |
| ECMWF IFS trước 1 ngày − Nhãn hiện tại (Open-Meteo ≈ ERA5) | MAE | 6.48 | 6.06 | 0.42 | 0.16 | 0.65 |
| ECMWF IFS trước 1 ngày − Nhãn hiện tại (Open-Meteo ≈ ERA5) | CSI>=16 | 0.25 | 0.25 | -0.00 | -0.03 | 0.02 |
| ECMWF IFS trước 1 ngày − Nhãn hiện tại (Open-Meteo ≈ ERA5) | CSI>=50 | 0.16 | 0.17 | -0.01 | -0.04 | 0.03 |
| IMERG Final V07 − Nhãn hiện tại (Open-Meteo ≈ ERA5) | MAE | 6.26 | 6.06 | 0.20 | -0.14 | 0.54 |
| IMERG Final V07 − Nhãn hiện tại (Open-Meteo ≈ ERA5) | CSI>=16 | 0.25 | 0.25 | -0.00 | -0.04 | 0.03 |
| IMERG Final V07 − Nhãn hiện tại (Open-Meteo ≈ ERA5) | CSI>=50 | 0.17 | 0.17 | 0.00 | -0.06 | 0.07 |
| IMERG V07 chưa hiệu chỉnh − Nhãn hiện tại (Open-Meteo ≈ ERA5) | MAE | 5.96 | 6.06 | -0.10 | -0.43 | 0.25 |
| IMERG V07 chưa hiệu chỉnh − Nhãn hiện tại (Open-Meteo ≈ ERA5) | CSI>=16 | 0.22 | 0.25 | -0.03 | -0.07 | 0.01 |
| IMERG V07 chưa hiệu chỉnh − Nhãn hiện tại (Open-Meteo ≈ ERA5) | CSI>=50 | 0.13 | 0.17 | -0.04 | -0.11 | 0.01 |
| GSMaP v8 − Nhãn hiện tại (Open-Meteo ≈ ERA5) | MAE | 6.25 | 6.06 | 0.20 | -0.28 | 0.70 |
| GSMaP v8 − Nhãn hiện tại (Open-Meteo ≈ ERA5) | CSI>=16 | 0.22 | 0.25 | -0.03 | -0.08 | 0.01 |
| GSMaP v8 − Nhãn hiện tại (Open-Meteo ≈ ERA5) | CSI>=50 | 0.16 | 0.17 | -0.01 | -0.07 | 0.05 |
| GSMaP v8 hiệu chỉnh trạm − Nhãn hiện tại (Open-Meteo ≈ ERA5) | MAE | 4.67 | 6.06 | -1.38 | -1.70 | -1.06 |
| GSMaP v8 hiệu chỉnh trạm − Nhãn hiện tại (Open-Meteo ≈ ERA5) | CSI>=16 | 0.38 | 0.25 | 0.13 | 0.09 | 0.17 |
| GSMaP v8 hiệu chỉnh trạm − Nhãn hiện tại (Open-Meteo ≈ ERA5) | CSI>=50 | 0.30 | 0.17 | 0.13 | 0.05 | 0.21 |

### CSI ≥50 mm theo vùng

| Nguồn | Bắc Bộ | Bắc Trung Bộ | Nam Bộ | Nam Trung Bộ | Trung Trung Bộ | Tây Nguyên |
|---|---|---|---|---|---|---|
| Khí hậu (TB theo ngày-năm) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| ECMWF IFS trước 1 ngày | 0.14 | 0.40 | 0.00 | 0.00 | 0.20 | 0.00 |
| ECMWF IFS trước 2 ngày | 0.09 | 0.27 | 0.00 | 0.00 | 0.16 | 0.00 |
| ECMWF IFS trước 3 ngày | 0.08 | 0.17 | 0.00 | 0.00 | 0.18 | 0.05 |
| ECMWF IFS trước 5 ngày | 0.00 | 0.13 | 0.00 | 0.00 | 0.15 | 0.05 |
| Nhãn hiện tại (Open-Meteo ≈ ERA5) | 0.17 | 0.33 | 0.00 | 0.00 | 0.22 | 0.00 |
| GFS trước 1 ngày | 0.09 | 0.35 | 0.00 | 0.08 | 0.21 | 0.00 |
| GFS trước 2 ngày | 0.05 | 0.29 | 0.00 | 0.06 | 0.14 | 0.05 |
| GFS trước 3 ngày | 0.10 | 0.24 | 0.00 | 0.08 | 0.17 | 0.04 |
| GSMaP v8 | 0.03 | 0.37 | 0.05 | 0.17 | 0.23 | 0.00 |
| GSMaP v8 hiệu chỉnh trạm | 0.08 | 0.59 | 0.00 | 0.25 | 0.42 | 0.04 |
| IMERG Final V07 | 0.07 | 0.34 | 0.08 | 0.22 | 0.21 | 0.00 |
| IMERG V07 chưa hiệu chỉnh | 0.05 | 0.20 | 0.07 | 0.25 | 0.17 | 0.00 |
| Persistence (trạm hôm trước) | 0.10 | 0.25 | 0.00 | 0.00 | 0.16 | 0.00 |
