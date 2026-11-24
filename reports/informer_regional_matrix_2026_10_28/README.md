# Informer đủ E0–E7 — 28/10/2026

**Đã chạy bổ sung 54 lượt E1–E6** theo đúng hàm fit pilot và dùng lại **18 lượt E0/E7**. Tổng 72 Informer = tám E × ba năm đánh giá 2021–2023 × ba seed 42/43/44. Cùng 72 TFT và 24 pipeline LightGBM đã có, đủ 168 lượt mô hình/pipeline. Không tuning, không thay dữ liệu hoặc bước sáu giờ, không mở test 2025.

Thời gian fit/save/replay của 54 lượt mới: **22.35 phút**; tiến trình gồm tập hợp điểm khoảng 22.82 phút. Không tính đây là thời gian hoàn thành toàn nghiên cứu.

**Kiểm chứng độc lập:** phát lại đủ 72 checkpoint trên 144 split calibration/evaluation; tái tạo scaler train, calibration và ensemble. Toàn bộ điểm TFT/LightGBM và điểm Informer E0/E7 giữ nguyên. Mỗi hạn có 1.075 mốc đánh giá, 114 sự kiện vùng từ 16 mm/24h; ba seed không nhân số ngày thời tiết.

## BSS theo ngày, đủ ba mô hình

### Ngày 1

| E | LightGBM | TFT | Informer |
| --- | ---: | ---: | ---: |
| E0 | 0.144 | 0.135 | 0.135 |
| E1 | 0.264 | 0.221 | 0.202 |
| E2 | 0.283 | 0.280 | 0.279 |
| E3 | 0.175 | 0.133 | 0.156 |
| E4 | 0.315 | 0.237 | 0.228 |
| E5 | 0.282 | 0.171 | 0.199 |
| E6 | 0.306 | 0.280 | 0.284 |
| E7 | 0.303 | 0.246 | 0.278 |

### Ngày 2

| E | LightGBM | TFT | Informer |
| --- | ---: | ---: | ---: |
| E0 | -0.015 | 0.018 | 0.020 |
| E1 | -0.034 | 0.041 | 0.013 |
| E2 | 0.060 | 0.047 | 0.038 |
| E3 | -0.038 | 0.027 | 0.031 |
| E4 | 0.046 | 0.023 | 0.014 |
| E5 | -0.035 | 0.026 | 0.012 |
| E6 | 0.056 | 0.054 | 0.062 |
| E7 | 0.043 | 0.028 | 0.025 |

### Ngày 3

| E | LightGBM | TFT | Informer |
| --- | ---: | ---: | ---: |
| E0 | -0.053 | -0.034 | -0.020 |
| E1 | -0.071 | -0.028 | -0.022 |
| E2 | -0.061 | -0.030 | -0.006 |
| E3 | -0.037 | -0.026 | -0.003 |
| E4 | -0.061 | -0.029 | -0.017 |
| E5 | -0.063 | -0.028 | -0.022 |
| E6 | -0.050 | -0.016 | 0.004 |
| E7 | -0.075 | -0.038 | -0.019 |

## E7: đọc cả lượng mm và xác suất

| Ngày | Mô hình | RMSE | BSS | CSI | POD | FAR |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | LightGBM | 17.706 | 0.303 | 0.411 | 0.526 | 0.348 |
| 1 | TFT | 20.361 | 0.246 | 0.406 | 0.640 | 0.475 |
| 1 | Informer | 20.486 | 0.278 | 0.440 | 0.614 | 0.391 |
| 2 | LightGBM | 20.756 | 0.043 | 0.277 | 0.456 | 0.587 |
| 2 | TFT | 21.018 | 0.028 | 0.257 | 0.509 | 0.659 |
| 2 | Informer | 21.190 | 0.025 | 0.239 | 0.447 | 0.660 |
| 3 | LightGBM | 21.742 | -0.075 | 0.203 | 0.482 | 0.741 |
| 3 | TFT | 21.321 | -0.038 | 0.201 | 0.412 | 0.719 |
| 3 | Informer | 21.347 | -0.019 | 0.216 | 0.456 | 0.709 |

Ở E7 ngày 1, LightGBM tốt hơn theo RMSE/BSS/FAR; Informer có CSI cao nhất; TFT có POD cao nhất. Cả ba E7 ngày 3 BSS âm. Riêng Informer E6 ngày 3 có BSS khoảng +0,004, chỉ giảm khoảng 0,4% sai số Brier; không đủ để tự khẳng định kỹ năng chắc chắn. Điểm tốt hơn chưa tự là ý nghĩa thống kê hoặc lý do chọn một kiến trúc duy nhất. Các E khác cần đọc đầy đủ theo bảng trên.

## Khoảng tin cậy và giới hạn

Có 20.000 bootstrap paired theo khối bảy ngày và độ nhạy 14 ngày, giữ chung mốc/ngày đích/nhãn/tham chiếu. CI95% mới là **mô tả**, chưa hiệu chỉnh nhiều phép và có điều kiện trên các ensemble đã fit; không bao trùm toàn bộ bất định nhãn/huấn luyện. Năm phát triển và E0/E7 đã được xem trước. Không thay phép thử TFT chính và không gọi phân tích này là holdout độc lập.

Thêm biến cũng có thể làm thay đổi số tham số mạng. Cây dùng thống kê lịch sử, mạng dùng chuỗi nên chưa cô lập riêng kiến trúc. Footprint 93 toàn ô vẫn xấp xỉ; nhãn và ranh cần QC. Độ phân giải sáu giờ chưa được đối chứng 1h/3h/6h. Không suy ra đã dự báo vận hành tốt đến 72 giờ chỉ vì đủ ma trận.

## Tệp kết quả và tái lập

- [Báo cáo, slide, Word và Excel đủ ba mô hình](../short_range_complete_2026_10_28/README.md).
- [Protocol khóa trước 54 lượt mới](protocol_frozen.json), [nhật ký 72 lượt](run.json), [kiểm chứng độc lập](validation.json).
- [Điểm gộp đủ mùa/ngưỡng](scores_ensemble_pooled.csv), [từng năm](scores_ensemble.csv), [ba seed Informer](scores_seed_pooled.csv), [độ ổn định seed](seed_stability.csv).
- [CI chênh lệch mô tả](paired_bootstrap_exploratory.csv), [CI điểm E7](absolute_skill_ci.csv), [reliability](reliability16.csv), [ngưỡng chọn trên calibration của cả ba mô hình](calibration_thresholds_all_models.csv).

Chạy `python scripts/run_informer_regional_matrix.py`, `python scripts/validate_informer_regional_matrix.py`, `python scripts/evaluate_informer_regional_matrix.py`, rồi `python scripts/publish_informer_regional_matrix.py`. Cần V1, artifact pilot E0/E7 và artifact TFT/LightGBM gốc ngoài Git. Hàm fit cũ giữ nguyên; runner chỉ chuyển thư mục lưu. Runner có thể tiếp tục các job chưa xong. Raw data/checkpoint/scaler/dự đoán từng mốc ở `data/operational/short_range/`, không công bố vào repo.
