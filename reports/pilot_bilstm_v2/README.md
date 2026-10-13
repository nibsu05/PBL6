# Pilot Bi LSTM tại Đà Nẵng

Ngày 13/10/2026. S4 cải thiện dự báo xác suất có mưa so với S0/S1, nhưng chưa cải thiện chắc chắn việc phát hiện tổng mưa 3 h ≥10 mm. Chưa có cơ sở tuyên bố vượt ECMWF hoặc chọn Bi-LSTM thay TFT từ pilot này.

## Thiết kế

30 ô chọn trước khi xem nhãn, phân tầng theo độ cao và khoảng cách biển; cửa sổ quá khứ 24 h, đầu ra 6 h, bước trượt 6 h; seed 42/43. Mọi cấu hình dùng chung 306.690 cửa sổ train (2015–2021), 43.380 cửa sổ chọn epoch/hiệu chỉnh xác suất (2022), và 43.800 cửa sổ đánh giá (2023). Không chấm mô hình trên test 2025.

S0 gồm A0; S1 thêm GSMaP thô trễ 4 h; S4 gồm A0–A4. Đây là **ablation thông tin của cùng Bi-LSTM**, không phải so sánh các kiến trúc. S4 nhận ERA5 tại giờ đích theo perfect prog; số liệu này chưa chứng minh kỹ năng vận hành với ECMWF thật.

Mạng có hai đầu: Huber trên log1p lượng mưa giờ và BCE không tăng trọng số lớp dương cho các tổng 0–3/3–6/0–6 h vượt 1/10/25 mm. Chọn epoch bằng loss 2022, rồi hiệu chỉnh logits bằng logistic regression trên 2022. Baseline khí hậu fit trên train theo ô × tháng × giờ; xác suất dùng Beta(1,1).

## Kết quả chính

Tháng 5–10/2023, tổng 0–3 h, 22.080 mẫu chung. Các hàng S0/S1/S4 là trung bình **dự báo** của hai seed, không phải trung bình chỉ số.

| Nguồn | CSI ≥10 mm | BSS ≥1 mm | RMSE mm/3 h |
| --- | ---: | ---: | ---: |
| Khí hậu | 0,000 | 0,000 | 4,524 |
| ERA5 perfect prog | 0,117 | −0,720 | 4,256 |
| Persistence trễ 4 h | 0,188 | −0,560 | 6,689 |
| S0 | 0,157 | 0,186 | 3,890 |
| S1 | 0,150 | 0,195 | 3,922 |
| S4 | 0,089 | 0,239 | 3,837 |

Bootstrap theo khối 5 ngày, 1.000 lần, gộp mọi ô cùng ngày:

| Hiệu số | Điểm | Khoảng tin cậy 95% |
| --- | ---: | --- |
| CSI S0 − S1 | 0,0066 | [−0,0336; 0,0531] |
| CSI S0 − S4 | 0,0679 | [−0,0421; 0,1714] |
| CSI S1 − S4 | 0,0613 | [−0,0275; 0,1335] |
| BS S0 − S4 | 0,00691 | [0,00123; 0,01254] |
| BS S1 − S4 | 0,00577 | [0,00093; 0,01083] |

BS thấp hơn tốt hơn. S4 có lợi ích xác suất rõ trong pilot; mọi khoảng tin cậy CSI giữa các cấu hình chứa 0. S1 chưa phân biệt chắc với S0. Khoảng tin cậy là bất định theo ngày trên trung bình dự báo, chưa bao gồm đầy đủ bất định seed. Từng seed và các mùa/hạn khác nằm ở [scores.csv](scores.csv); mùa đông chỉ chấm tổng 6 h.

Hai baseline tất định được đổi thành xác suất 0/1 khi chấm BSS. Cần thêm dự báo số được hiệu chỉnh xác suất trước khi kết luận học sâu có giá trị vượt hậu xử lý đơn giản. Huber ở thang log có thể làm đầu lượng mưa thiên về giá trị thấp; đây là giả thuyết cần kiểm tra trên validation, không phải nguyên nhân đã được xác minh của CSI yếu.

## Việc tiếp theo

1. Thêm seed và baseline được hiệu chỉnh; cố định tập mẫu.
2. So Bi-LSTM và TFT ở cả hai hạn với cùng đầu vào, cùng mục tiêu/loss và cùng ngân sách chọn tham số.
3. Kiểm tra nguồn đặc trưng khi chạy app và đánh giá T-OPS; không dùng ERA5 giờ đích làm dự báo thật.

Sáu lượt mất khoảng 411 giây tổng thời gian chạy riêng, cộng chuẩn bị và chấm điểm. Máy RTX 3050 Ti 4 GB. Phiên bản code train `e0caee9`; code chấm lại `74a11d7`. Xem [run.json](run.json) và [paired_bootstrap.json](paired_bootstrap.json). Checkpoint và dự báo chứa nhãn nằm trong `data/processed/pilot_bilstm_v2/`, được Git bỏ qua.
