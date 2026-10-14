# Lời dẫn ngắn cho bộ 12 slide, 14/10/2026

**Thời lượng gợi ý:** 8–10 phút cho slide 1–11. Slide 12 chỉ mở khi được hỏi về ECMWF. Đây là kết quả giữa kỳ; các số mô hình là validation lịch sử, chưa phải chất lượng dự báo AI live. Nguồn chi tiết có trong ghi chú từng slide của PowerPoint.

1. **Mở đầu.** “Nhóm làm dự báo mưa vài giờ tới cho Đà Nẵng, đồng thời kiểm tra liệu nguồn dữ liệu và mô hình có đủ tin cậy để đưa lên app.”
2. **Nhu cầu.** Thành phố đã có ứng dụng theo dõi mưa và ngập đang xảy ra. Nhóm thử bổ sung lớp **dự báo lượng mưa** vài giờ tới. Đây là giả thuyết rút từ tài liệu, chưa phỏng vấn người dùng.
3. **Bài toán.** Phát hành mỗi giờ cho 93 ô lưới; hiển thị tổng mưa 3 giờ và xác suất mưa mạnh trong hạn 1–6 giờ. Lưới khoảng 10–11 km nên không dự báo đoạn đường nào sẽ ngập.
4. **Nguồn dữ liệu.** GSMaP GC là mưa lịch sử để học; GSMaP NRT là quan trắc gần hiện tại. ERA5 là khí tượng hồi cứu; ECMWF là dự báo có thể dùng khi chạy thật và là đối chứng. Cần kiểm tra mọi đầu vào đã có trước giờ phát hành.
5. **Chọn nhãn.** ERA5 bỏ sót nhiều ngày mưa lớn trong audit trạm. GSMaP GC có CSI ngày ≥50 mm cao hơn IMERG và ERA5 tại 10 trạm, nhưng sản phẩm này đã được hiệu chỉnh bằng trạm nên cần kiểm chứng độc lập hơn.
6. **So mô hình.** Nhóm cố định 30 ô và cùng thời điểm để so LightGBM, Bi-LSTM, thêm đặc trưng địa phương và đổi hàm học. Chấm ba năm 2021–2023, ba seed; giữ test 2025 chưa mở. RMSE là sai số lượng mưa, CSI là bắt mưa vượt ngưỡng, BSS là chất lượng xác suất so khí hậu tham chiếu.
7. **Kết quả mạnh nhất.** Đổi đầu học lượng mưa sang Tweedie làm RMSE giảm ở cả ba năm cho LightGBM và Bi-LSTM. Tuy vậy xác suất Bi-LSTM năm 2022 kém đi theo BSS, nên chưa có một cấu hình thắng mọi chỉ số.
8. **Hiểu địa phương.** Gió Đông Bắc đi cùng nhiều sự kiện mưa mạnh trong dữ liệu; biểu diễn gió, ẩm, địa hình làm CSI Bi-LSTM tăng mô tả. Khoảng tin cậy của lợi ích vẫn chứa 0: chưa được nói “đặc trưng địa phương chắc chắn giúp”.
9. **Nguồn vận hành.** Đã giải mã 24 tệp NRT/93 ô, nhưng mới có một file mới được watcher ghi trực tiếp. Train lại với quan trắc trễ thêm 1 giờ làm RMSE tăng nhỏ; cần đo nhiều ngày và kiểm tra toàn bộ đầu vào trước khi chọn lag.
10. **App.** Demo đã chạy checkpoint thật trên dữ liệu quá khứ, 36 phép đối chiếu API khớp. Luồng live phải kiểm tra đủ dữ liệu/giờ nguồn, suy luận, rồi hiển thị bản đồ, xác suất và thời điểm cập nhật. AI live hiện chưa bật.
11. **Việc tiếp theo.** Ghi độ trễ nguồn nhiều ngày, tái tạo đúng thông tin có trước giờ phát hành, so AI và ECMWF trên cùng ô/giờ/nhãn, rồi mới chốt model và app. Xin ý kiến giảng viên về ưu tiên RMSE hay bắt mưa mạnh, phạm vi 0–6 giờ, và khả năng bổ sung trạm giờ độc lập.
12. **Dự phòng ECMWF.** ECMWF IFS là dự báo đã phát hành, khác nhãn ERA5 hồi cứu. Pilot 14 ngày có 1.680 cặp nhưng chỉ bốn ngày mưa mạnh và chưa so AI cùng mẫu vận hành; không tuyên bố AI thắng ECMWF.

Nếu thời gian chỉ còn 5 phút, trình bày slide **2, 3, 4, 5, 7, 10, 11**; chỉ nhắc một câu về slide 8–9. Không biến demo hồi cứu thành tuyên bố AI dự báo trực tiếp.
