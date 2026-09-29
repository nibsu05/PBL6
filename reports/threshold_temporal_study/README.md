# Ngưỡng cảnh báo và kiểm tra theo thời gian

Đã chạy `run_threshold_temporal_study.py --device cuda` ngày 23/09/2026.
Toàn bộ lần chạy dùng seed 42. Đọc `protocol.json` để biết giao thức.

## Kết quả chính

- Ngưỡng t+1…t+6 chọn trên validation cũ: 0,55; 0,60; 0,70; 0,75; 0,75; 0,75.
- Test cũ: FP giảm 1.600 → 564; TP giảm 331 → 178; recall giảm 47,2% → 25,4%.
- Precision test 24,0% không đạt mục tiêu 30% trong calibration.
- Ba fold fit lại scaler và hai mô hình, dùng nhãn trước 01/12/2024.
- Ngưỡng riêng tắt toàn bộ horizon ở F1 và F3. F2 chỉ bật t+1 nhưng có 4 FP và 0 TP trong assessment.
- Không chọn chính sách ngưỡng riêng làm cấu hình vận hành mặc định. Các checkpoint và công cụ ghi dự báo trước đó được giữ nguyên.

`test_metrics.csv` là đánh giá thăm dò: test cũ đã được xem trong quá trình phát triển.
`temporal_metrics.csv` chứa đánh giá trên giai đoạn kế tiếp của từng fold.
Các fold hồi cứu đã có trong lịch sử dữ liệu, có train chồng lấn và chỉ một seed;
không thay thế một tập xác nhận tương lai độc lập.

## Tệp đầu ra

- `selected_thresholds.json`: ngưỡng, tiêu chí và hash checkpoint gốc.
- `validation_threshold_sweep.csv`: mọi ứng viên ngưỡng trên validation.
- `test_metrics_by_horizon.csv`: kết quả từng thời hạn dự báo.
- `fold_summary.json`: ranh giới thời gian, số mẫu, epoch và ngưỡng từng fold.
- `F1/`, `F2/`, `F3/`: checkpoint, scaler, history, calibration sweep và dự đoán assessment.
- `../professor_report/Bao_cao_tong_hop_PBL6_Da_Nang.docx`: báo cáo tổng hợp để làm slide.

F1 theo giờ và F1 theo đợt có định nghĩa khác nhau. Ghép đợt dùng giao khoảng,
nên có thể trúng một đợt dù không trúng đúng giờ vượt 5 mm/h. Số đợt gộp 6 horizon
không phải số trận mưa độc lập.
