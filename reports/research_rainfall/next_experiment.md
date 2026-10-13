# Thí nghiệm đặc trưng trước khi triển khai app

Đề xuất ngày 13/10/2026. Mục tiêu trước mắt là đo giá trị bổ sung của các nhóm dữ liệu trên Đà Nẵng, rồi chọn cấu hình có nguồn đầu vào vận hành. Chưa khởi chạy các thí nghiệm này.

## Phạm vi đợt đầu

Đà Nẵng, dự báo 6 giờ; hiển thị lượng mưa giờ, tổng 3 giờ và xác suất. Giữ sản phẩm 1–3 ngày ở giai đoạn tiếp theo. Giữ Bi-LSTM để cô lập đóng góp dữ liệu; kiểm tra kết luận bằng một mô hình tabular sau sàng lọc, rồi so TFT trên cùng đầu vào và cùng hạn.

## Điều kiện trước khi huấn luyện

Lập hợp đồng cho từng biến: trường ERA5, trường nguồn live, đơn vị, độ sâu/tầng áp suất, thời điểm phát hành, độ trễ và biến đổi. Gọi thử dữ liệu tại Đà Nẵng; kiểm tra hữu hạn và đối chiếu thời gian, không chỉ dựa vào danh sách biến trên trang API.

Open-Meteo ghi nhận IFS HRES 9 km không cung cấp trường tầng áp suất; các trường này lấy từ mô hình open-data 0,25 độ. Nguồn tầng áp suất và nguồn bề mặt có thể khác độ phân giải/cadence; cần kiểm tra cả kho dự báo lịch sử. [Tài liệu ECMWF API](https://open-meteo.com/en/docs/ecmwf-api).

Biến chưa có nguồn live tương đương được giữ trong nhóm nghiên cứu, chưa đưa vào danh sách ứng viên triển khai. Lưu snapshot dự báo live sớm để có dữ liệu kiểm chứng sau này.

## Ma trận đặc trưng

Nền = A0 + A1: bề mặt, thời gian, địa hình và GSMaP thô trễ 4 giờ. Mọi hàng chỉ dùng khí tượng quá khứ; tương lai chỉ có đặc trưng thời gian đã biết. Chưa đưa ERA5 tại giờ đích vào đợt này.

| Cấu hình | Phần thêm so với nền | Biến chính |
| --- | --- | --- |
| E0 | Không thêm | A0 + A1 |
| E1 | Hơi ẩm cột | tcwv |
| E2 | Đối lưu | cape, cin_capped, has_lfc |
| E3 | Gió và ẩm tầng thấp | u850, v850, q850_gkg |
| E4 | Trạng thái đất | swvl1 |
| E5 | Tổ hợp | Các nhóm E1–E4 |

Dataset đã có swvl1 nhưng FEATURE_GROUPS chưa chọn biến này. Cần bổ sung cấu hình đọc đúng biến trước khi chạy. CIN giữ mã hóa hiện có; giờ thực sự thiếu khí tượng vẫn là NaN.

## Kiểm soát và chỉ số

Giữ cùng cửa sổ hợp lệ của E5 cho mọi cấu hình, kiến trúc, loss, optimizer, ngân sách epoch và seed 42/43/44. Fit chuẩn hóa chỉ trên train. Bắt đầu 30 ô đã chọn; chỉ các ứng viên sau sàng lọc mới chạy toàn bộ 93 ô. Ghi số tham số và thời gian.

Train 2015–2021; 2022 chọn epoch và hiệu chỉnh; 2023 so cặp. Test 2025 giữ kín. Do 2023 đã dùng nhiều lần để khám phá, mọi kết luận ở đây là kết luận validation; không gọi là xác nhận trên test độc lập.

CSI tổng 3 h ≥10 mm và BSS ≥1 mm là hai chỉ số chính; kèm RMSE, bias, reliability và số sự kiện. Tháng 5–10 chấm 3 h; mùa đông chỉ chấm tổng 6 h trong đợt này. Tách nhóm độ cao/khoảng cách biển bằng quy tắc đặt trước khi xem kết quả. Bootstrap khối ngày và báo biến thiên giữa seed; xét nhiều phép so làm tăng nguy cơ tìm được cải thiện ngẫu nhiên.

Baseline dùng chung mẫu: khí hậu ô/tháng/giờ, persistence đúng trễ, và mô hình tabular với cùng dữ liệu. Dự báo số thô/hiệu chỉnh là đối chứng ở giai đoạn đầu vào dự báo thật. Không coi BSS của dự báo tất định đổi thành 0/1 là đủ để kết luận học sâu thắng hậu xử lý xác suất đơn giản.

## Cách chọn ứng viên

Giữ các cấu hình có lợi ích CSI hoặc BSS rõ và không suy giảm nghiêm trọng chỉ số còn lại. Khi hai chỉ số trái chiều, giữ cả hai ứng viên để kiểm tra tiếp thay vì gọi một mô hình thắng chung. Khi chênh lệch chưa phân biệt chắc, ưu tiên cấu hình đơn giản và nguồn dữ liệu ổn định. Ngưỡng quyết định và hiệu chỉnh lượng mưa/xác suất chỉ chọn trên validation.

Với tổ hợp tốt, bỏ từng nhóm ra để kiểm tra thông tin trùng lặp; điểm quan trọng biến không thay thế phép so có kiểm soát và không chứng minh nhân quả.

## Cổng triển khai

1. Chốt ứng viên bằng validation và kiểm tra độ bền bằng mô hình đối chứng.
2. Thay nguồn ERA5 hồi cứu bằng dự báo/quan trắc thực sự có sẵn lúc phát hành; dựng tensor đúng đơn vị, giờ và độ trễ. Dữ liệu forecast 2024 chọn biến thể vận hành; test 2025 chỉ mở sau đóng băng thiết kế.
3. Chạy cùng đầu vào qua pipeline train và app để kiểm tra parity; kiểm tra nguồn lỗi/cũ, độ trễ và cấu hình dự phòng.
4. Chấm trên dự báo thật; chỉ tích hợp checkpoint đạt điều kiện vào app. Một mô hình chung cho các ô, không nhân bản một mô hình cho từng tỉnh.

App có thể làm giao diện và ghi log song song: bản đồ 93 ô, chọn điểm, lượng mưa và xác suất, thời điểm cập nhật và trạng thái dữ liệu. Việc chọn checkpoint cuối phải dựa trên kiểm định vận hành, không chỉ bảng điểm ERA5.
