# Lời trình bày 5 phút

Ngày 21/10/2026. Dùng cùng PBL6_TFT_5_PHUT.pptx. Các con số lấy từ ma trận phát triển đã kiểm chứng, không phải test 2025.

## Slide 1 · 0:00–0:55 · Mục tiêu và dữ liệu

“Phần em phụ trách là dự đoán lượng mưa trung bình vùng trong ba ngày tới. Mỗi mẫu đại diện cho một thời điểm của cả vùng, không phải một ô lưới. Nhóm tổng hợp khí tượng và nhãn từ 93 ô trước khi đưa vào mô hình. Hiện vùng này còn xấp xỉ, chưa khẳng định khớp toàn địa giới Đà Nẵng mới.

Đầu vào là bảy ngày khí tượng ERA5 quá khứ, gộp sáu giờ; nhãn là mưa GSMaP Gauge. Đầu ra gồm ba tổng 24 giờ riêng. Mô hình chỉ biết lịch tương lai, không nhận ERA5 của giờ cần dự báo.”

## Slide 2 · 0:55–1:55 · Đã chạy và kết quả tổng thể

“Nhóm đã chạy đủ tám tổ hợp đặc trưng, ba fold phát triển 2021–2023 và ba seed TFT, gồm 72 lượt TFT cùng 24 pipeline LightGBM. Mọi cấu hình được chấm trên cùng các thời điểm hợp lệ.

BSS đánh giá xác suất sự kiện mưa vùng từ 16 mm trong 24 giờ so với khí hậu tham chiếu. Ngày 1, TFT tăng từ 0,135 ở nền E0 lên 0,246 khi thêm toàn bộ biến E7. Tuy nhiên LightGBM E7 đạt 0,303 và có RMSE ngày 1 thấp hơn. Vì vậy em chưa kết luận TFT tốt hơn mô hình đối chứng.

Ngày 3, BSS đều âm ở các cấu hình đã chạy. Đây là kết quả cần ghi nhận, chưa cho phép kết luận chung rằng dự báo 72 giờ không khả thi.”

## Slide 3 · 1:55–3:00 · Đóng góp từng nhóm biến

“Mục tiêu chính là nghiên cứu đặc trưng nên nhóm tách A, M và C. A gồm khí quyển, đối lưu, mây và ẩm đất; M gồm gió, ẩm và vận chuyển ẩm; C hiện chỉ có SST vùng biển.

Khi thêm riêng vào nền E0, ngày 1 có ΔBSS khoảng +0,085 với A và +0,144 với M. Hai khoảng tin cậy sau hiệu chỉnh chín phép so vẫn trên 0, kể cả khi đổi khối bootstrap từ bảy sang mười bốn ngày. Chưa kiểm định trực tiếp M tốt hơn A.

Chưa có bằng chứng tương tự cho SST hoặc ngày 2–3. Kết luận về C chỉ áp dụng cho biến SST này, chưa phải kết luận về ENSO/MJO hay toàn bộ yếu tố khí hậu.”

## Slide 4 · 3:00–4:00 · Ý nghĩa và giới hạn

“Tín hiệu tích cực là lợi ích ngày 1 lặp lại qua ba seed và có đối chứng. Nhưng thêm hết biến không mặc nhiên tốt nhất: LightGBM E4 có điểm BSS cao hơn E7 ở ngày 1, còn chênh lệch đó chưa được kiểm định riêng.

Kết quả đang là development đã được xem trước, với nhãn vệ tinh và vùng xấp xỉ. Nhiều seed không tạo thêm ngày mưa độc lập; checksum hoặc replay đúng cũng không chứng minh nhãn đúng với mưa thật. Các yếu tố này giới hạn phạm vi kết luận.”

## Slide 5 · 4:00–5:00 · Việc tiếp theo

“Ưu tiên tiếp theo là chốt ranh và trọng số vùng, kiểm chứng nhãn ngày bằng đối chứng phù hợp. Nếu thay dữ liệu, nhóm dựng lại dữ liệu và chạy lại phần phát triển liên quan. Sau đó mới khóa thiết kế và đánh giá năm 2025 đang giữ kín.

Nếu cần cải thiện ngày 3, nhóm cân nhắc một nhánh dùng forecast thật đã được phát hành, với đối chứng cùng thông tin và thời điểm sẵn có. Chưa có phép đo Informer trong ma trận này nên em chưa kết luận nó không khả thi. Hướng chính vẫn là nghiên cứu đóng góp đặc trưng cho dự đoán vùng trực tiếp.”

## Ba câu để chốt khi thời gian ngắn

- Đã có pipeline và ma trận phát triển tái lập, với 72 TFT và 24 LightGBM.
- A/M giúp ngày 1 trong phép thử này; SST/ngày 2–3 chưa có bằng chứng tương tự.
- Còn ranh/nhãn và kiểm định độc lập; năm 2025 vẫn giữ kín.
