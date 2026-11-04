# Báo cáo nhanh: dự đoán mưa vùng 24–72 giờ

Ngày 21/10/2026 · Dùng để báo cáo tiến độ nghiên cứu · Test 2025 giữ kín

TFT ngày 1 có BSS từ 0.135 ở E0 lên 0.246 ở E7. Thêm riêng nhóm A hoặc M có bằng chứng cải thiện ngày 1 sau hiệu chỉnh chín phép so. Chưa có bằng chứng tương tự cho SST hoặc ngày 2–3. Đây là kết quả phát triển hồi cứu, chưa phải kiểm định cuối.

## 1. Bài toán và cách làm

Mỗi ngày lúc 07 giờ Việt Nam, dùng 168 giờ khí tượng quá khứ gộp thành 28 bước 6 giờ để dự đoán trực tiếp ba tổng mưa trung bình vùng: [t,t+24), [t+24,t+48), [t+48,t+72). Đơn vị mm/24h; ngày 2/3 là hai tổng riêng. Nhãn GSMaP Gauge; đầu vào khí tượng ERA5. Decoder chỉ biết lịch.

Vùng hiện là 93 ô xấp xỉ, chưa phải giao ranh hành chính chính xác. E0 có 11 biến nền; E7 có 44 biến. Thí nghiệm đủ E0–E7 trên ba fold evaluation 2021–2023, ba seed TFT: 72 lượt TFT và 24 pipeline LightGBM. Mỗi lead có 1.075 mốc đánh giá, 114 sự kiện ≥16 mm; thêm seed không tạo thêm ngày thời tiết độc lập.

## 2. Kết quả cần nhớ

| Ngày | TFT E0 | TFT E7 | LGBM E0 | LGBM E7 |
| --- | --- | --- | --- | --- |
| 1 | 0.135 | 0.246 | 0.144 | 0.303 |
| 2 | 0.018 | 0.028 | -0.015 | 0.043 |
| 3 | -0.034 | -0.038 | -0.053 | -0.075 |

Bảng là BSS cho xác suất mưa vùng ≥16 mm/24h, so với xác suất khí hậu học từ train: dương có lợi, âm kém hơn tham chiếu. TFT là trung bình dự báo ba seed; LightGBM là một pipeline xác định.

RMSE ngày 1 E7: TFT 20.36, LightGBM 17.71 mm/24h. TFT chưa thể hiện ưu thế tổng thể; phép so này còn khác biểu diễn lịch sử và loss.

Ngày 1 có tín hiệu lặp lại: E7−E0 dương ở cả ba seed TFT, ΔBSS từ +0,068 đến +0,153. Ngày 3, BSS âm ở tất cả cấu hình hiện đã chạy của cả hai họ mô hình. Đây là điểm yếu cần báo cáo.

## 3. Nhóm đặc trưng nào có tín hiệu?

| Nhóm thêm riêng vào E0 | ΔBSS ngày 1 | CI99,44% đã hiệu chỉnh |
| --- | --- | --- |
| A: khí quyển/đối lưu/mây/đất | +0.085 | [+0.002; +0.161] |
| M: hoàn lưu và vận chuyển ẩm | +0.144 | [+0.068; +0.233] |
| C: SST vùng biển | -0.003 | [-0.043; +0.033] |

Bootstrap paired 20.000 lần, khối 7 ngày; gia đình chín phép so gồm ba nhóm × ba lead. Hai CI trên 0 thuộc A/M ngày 1; kiểm tra khối 14 ngày cho cùng kết luận. Các CI điều kiện trên mô hình đã fit, chưa bao gồm mọi bất định của nhãn và huấn luyện. Những năm development đã được xem trước.

M có mức tăng lớn hơn khi thêm riêng vào nền; chưa kiểm định trực tiếp M−A. SST hiện chỉ là một biến vùng biển, chưa đại diện đầy đủ ENSO/MJO. Không suy ra yếu tố khí hậu biển không quan trọng từ phép thử này.

## 4. Nhận xét độc lập và bước tiếp theo

- Thêm hết biến chưa chắc tốt nhất: LightGBM ngày 1 có BSS E4=0,315, E7=0,303. Đây là chênh lệch điểm mô tả, chưa kiểm định E4−E7.
- Ngày 2 có kỹ năng xác suất thấp, ngày 3 chưa vượt khí hậu. Chưa thể kết luận nguyên nhân duy nhất là kiến trúc hoặc thiếu forecast.
- Cần chốt ranh/trọng số 93 ô và kiểm chứng nhãn ngày. Nếu thay dữ liệu, chạy lại phần phát triển liên quan; sau khóa thiết kế mới đánh giá năm 2025.
- ERA5 hồi cứu chưa bảo đảm sẵn có lúc phát hành. Chưa có kết luận vận hành, mưa cực đoan tại điểm hay giá trị trên toàn địa giới Đà Nẵng mới.

Kiểm chứng kỹ thuật: 27 kiểm tra đạt; 96/96 lượt tái lập cả calibration/evaluation. Những kiểm tra này xác nhận pipeline, chưa xác nhận nhãn vệ tinh đúng với mưa thực. Informer chưa được chạy trong phép so, nên chưa có kết luận về tính khả thi của Informer.

Nguồn số liệu: scores_ensemble_pooled.csv, paired_bootstrap.csv, checkpoint_audit.json trong thư mục báo cáo mở rộng. Báo cáo đầy đủ, 8 slide và danh mục biến vẫn được giữ nguyên.
