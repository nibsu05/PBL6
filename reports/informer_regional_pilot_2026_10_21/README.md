# Pilot Informer vùng, E0/E7, 21/10/2026

Đã chạy 18 lượt = hai cấu hình × ba fold 2021–2023 × ba seed. Cùng seed hoàn chỉnh với TFT, cùng dữ liệu/nhãn/mẫu/lịch sử/đầu ra/loss/calibration. Không mở 2025 hoặc sửa nguồn huấn luyện TFT. Đây là bản Informer điều chỉnh, chưa tuning, chưa chạy E1–E6, không phải tái lập mọi benchmark bài gốc.

Informer E7 ngày 1 có BSS/CSI tốt hơn TFT theo điểm, RMSE hơi cao hơn. Ngày 3 cả hai vẫn BSS âm. Chưa có kiểm định chênh lệch kiến trúc hoặc lý do tuyên bố thắng tổng thể. Khả thi về tính toán đã được xác nhận, không phải bằng chứng vận hành.

Thời gian tiến trình 5.30 phút. Đã replay độc lập đủ 18 checkpoint trên cả calibration/evaluation; các điểm TFT tái tính khớp bảng cũ.

| Mô hình | E | Ngày | RMSE | BSS | CSI | POD | FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| informer | E0 | 1 | 20.970 | 0.135 | 0.381 | 0.588 | 0.481 |
| informer | E0 | 2 | 21.294 | 0.020 | 0.264 | 0.526 | 0.653 |
| informer | E0 | 3 | 21.343 | -0.020 | 0.260 | 0.588 | 0.682 |
| informer | E7 | 1 | 20.486 | 0.278 | 0.440 | 0.614 | 0.391 |
| informer | E7 | 2 | 21.190 | 0.025 | 0.239 | 0.447 | 0.660 |
| informer | E7 | 3 | 21.347 | -0.019 | 0.216 | 0.456 | 0.709 |
| tft | E0 | 1 | 20.720 | 0.135 | 0.357 | 0.570 | 0.511 |
| tft | E0 | 2 | 21.149 | 0.018 | 0.252 | 0.491 | 0.659 |
| tft | E0 | 3 | 21.292 | -0.034 | 0.197 | 0.412 | 0.725 |
| tft | E7 | 1 | 20.361 | 0.246 | 0.406 | 0.640 | 0.475 |
| tft | E7 | 2 | 21.018 | 0.028 | 0.257 | 0.509 | 0.659 |
| tft | E7 | 3 | 21.321 | -0.038 | 0.201 | 0.412 | 0.719 |

- [Protocol khóa trước fit](protocol_frozen.json), [nhật ký](run.json), [kiểm tra độc lập](validation.json).
- [Điểm gộp đầy đủ](scores_pooled.csv), [điểm từng năm/mùa/ngưỡng](scores_by_year.csv).
- [Slide giải thích và kết quả](../short_range_revised_2026_10_21/README.md).

Checkpoint, scaler và dự đoán từng mốc ở data/operational ngoài Git. Chạy scripts/pilot_informer_regional.py theo protocol để tái lập; source SHA và tham số lưu trong protocol. Subclass mới sửa số query sparse theo mã tác giả, cố định lấy mẫu keys lúc eval cho replay; mã cũ giữ nguyên. Cùng hidden không đồng nghĩa cùng số tham số.
