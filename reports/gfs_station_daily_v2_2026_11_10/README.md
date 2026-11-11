# Thí nghiệm GFS–Vrain hằng ngày v2

Đọc [báo cáo đầy đủ](BAO_CAO_HANG_NGAY_V2.md) hoặc [bản Word](BAO_CAO_HANG_NGAY_V2.docx). 57 trạm, ba tổng 24 giờ; LightGBM N0–N5, GRU N3/N5, ba seed; train 2021–22/cal 2023/dev 2024, chưa mở 2025.

| Tệp | Nội dung |
| --- | --- |
| point_metrics.csv | MAE/RMSE/Bias macro và micro cho mean/median, tất cả split/hạn |
| probability_metrics.csv | BS/BSS và số sự kiện; BSS tham chiếu CLIM |
| event_metrics.csv | CSI/POD/FAR tại p=0,5 và cutoff chọn từ cal; số trúng/bỏ sót/báo nhầm |
| paired_bootstrap.csv | Chênh ghép cặp và CI95%, khối 14 ngày, 1.000 lần, chưa chỉnh nhiều so sánh |
| conditional_amount_metrics.csv | Sai số theo dải mưa thực đo, micro; chỉ chẩn đoán |
| monthly_point_metrics.csv | Sai số theo tháng năm dev |
| station_improvement_summary.csv | Số/tỷ lệ trạm cải thiện so ZERO/GFS/CLIM/MOS, không công khai ID |
| reliability.csv | Tần suất thực so xác suất dự báo theo bin, hạn và ngưỡng |
| seed_metrics.csv | Điểm từng seed; không thay điểm ensemble |
| label_distribution.csv | Tỷ lệ khô, phân vị và số sự kiện theo split/hạn |
| tree_tuning_trials.csv / gru_tuning_trials.csv | Tuning theo các fold 2022 |
| tree_selection.json / gru_selection.json | Tham số chọn trước dev |
| source_latency_audit.json / source_coverage_policy.json | Bằng chứng nguồn, hai ngày loại và giới hạn độ trễ |
| dataset_audit.json / dataset_verification.json | Số mẫu, split, QC và replay timestamp |
| protocol.json / training_provenance.json / model_verification.json | Khóa thí nghiệm và kiểm chứng kết quả |
| runtime_environment.json | Phiên bản thư viện và GPU quan sát khi replay checkpoint |

Các ngày/predictor/nhãn trạm/checkpoint nằm ngoài Git; đây là tệp tổng hợp để chia sẻ. Các kết quả 2024 là phát triển, không phải test cuối.
