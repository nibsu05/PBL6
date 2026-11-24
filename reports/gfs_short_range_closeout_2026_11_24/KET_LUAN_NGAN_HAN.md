# Dự báo mưa ngắn hạn tại trạm Đà Nẵng

Bản chốt ngày 24/11/2026. Đầu ra là ba tổng mưa 24 giờ tại từng trạm, bắt đầu từ 19 giờ Việt Nam và lần lượt ứng với ngày 1, 2, 3. Bộ kiểm định tập trung vào 57 trạm của nhóm Đà Nẵng. Quan trắc Vrain cung cấp đáp án. Dự báo thời tiết GFS và số đo đã có trước giờ phát cung cấp thông tin đầu vào.

## Đóng góp có thể viết vào báo cáo

**Đóng góp chính là xác định nhóm biến khí tượng GFS giúp dự báo mưa tại trạm tốt hơn ở hạn hai và ba ngày.** Nhóm giữ cùng lịch sử mưa, mẫu trạm, thời điểm và cách đánh giá. N1 bổ sung nhiệt độ, độ ẩm, hai thành phần gió ở 850 hPa và hơi nước toàn cột vào N0. Trong kiểm định 2025 sau khi khóa phương án, sai số RMSE trung bình giữa các trạm giảm **0,83 mm** ở mỗi hạn.

| Phép đối chiếu trên kiểm định 2025 | Hạn | Chỉ số (mm) | Tham chiếu → mô hình | Chênh lệch | Khoảng đồng thời 95% của chênh lệch |
| --- | --- | --- | --- | --- | --- |
| LightGBM N1 so N0 | Ngày 2 | RMSE lượng kỳ vọng | 29,99 → **29,16** | −0,83 | [−1,35, −0,19] |
| LightGBM N1 so N0 | Ngày 3 | RMSE lượng kỳ vọng | 31,45 → **30,61** | −0,83 | [−1,43, −0,02] |
| LightGBM N3 so MOS | Ngày 3 | RMSE lượng kỳ vọng | 32,35 → **30,65** | −1,70 | [−3,04, −0,62] |
| GRU N5 so MOS | Ngày 1 | MAE lượng trung vị | 9,02 → **7,97** | −1,05 | [−1,84, −0,44] |
| GRU N5 so MOS | Ngày 3 | MAE lượng trung vị | 10,03 → **9,40** | −0,63 | [−1,35, −0,14] |

Tập kiểm định có 18.723 mẫu trạm và thời điểm phát dự báo. Các số trên tính sai số ở từng trạm rồi cho các trạm trọng số bằng nhau. Đây là các phép so đạt tiêu chí đặt trước, gồm khoảng đồng thời và hiệu chỉnh Holm. Hàng GRU sử dụng đầu ra trung vị và MAE, phục vụ mục tiêu khác đầu lượng kỳ vọng mà LightGBM được chấm bằng RMSE. [Bảng đối chiếu 2025](doi_chieu_kiem_dinh_2025.csv) · [Protocol và báo cáo gốc](../gfs_station_final_2026_11_17/README.md).

**Một kết quả có ích khác là biết nhóm biến nào chưa đáng thêm.** Địa hình và các dẫn xuất gió–ẩm cùng số tham số chưa đủ tiêu chí ở phép so chính năm 2025. Thêm biến mô tả diễn biến GFS trong ngày tăng từ 26 lên 49 biến, với 0/12 phép so chính đạt tiêu chí. Thêm hai năm huấn luyện làm điểm Tweedie giảm nhẹ trong hồi cứu, nhưng các chênh lệch chưa đạt tiêu chí suy luận đã định. [Thí nghiệm diễn biến trong ngày](../gfs_temporal_2026_11_17/README.md) · [Thí nghiệm số năm và hàm mất mát](../gfs_training_window_2026_11_18/README.md).

## Phương án dùng để trình diễn

**LightGBM B** sử dụng 26 biến N3, huấn luyện 2021–2024 và hiệu chỉnh xác suất năm 2025. Đây là phương án đã chọn từ các lượt kiểm tra chỉ trong tập huấn luyện năm 2022, cùng cửa sổ dài đã định trước. Đầu vào N3 giữ địa hình theo cấu hình B đã khóa. Vòng bốn năm chưa có GRU tương đương để xếp hạng cùng B.

Mô hình đã được chạy lại trên **43.464 lượt trạm × khoảng dự báo** của 280 ngày phát, thuộc kênh Vrain hiện hành năm 2026. Loại cột nhãn và dự báo lưu sẵn trước khi suy luận. Cả 260.784 giá trị dự báo lượng, xác suất và đối chứng được đối chiếu trùng khớp với bản lưu. Bộ mô hình có 119 tệp đã kiểm mã băm. [Biên bản kiểm chứng](verification.json).

| Hạn | GFS | MOS dài | LightGBM B | Mức giảm chỉ số lỗi so GFS |
| --- | --- | --- | --- | --- |
| Ngày 1 | 20,45 | 18,93 | **15,68** | **23,3%** |
| Ngày 2 | 19,74 | 17,90 | **17,47** | **11,5%** |
| Ngày 3 | 24,95 | 22,36 | **20,27** | **18,8%** |

Đơn vị RMSE là mm cho mỗi cửa sổ 24 giờ. Ba hàng dùng cùng 14.488 mẫu trạm và lần phát dự báo mỗi hạn. Tỷ lệ phần trăm ở đây là mức giảm của RMSE.

Phân tích thăm dò bổ sung so B với GFS và MOS trên cùng mẫu, lấy lại 5.000 lượt theo khối ngày và giữ tất cả trạm trong một ngày cùng nhau. Dùng khoảng đồng thời cho sáu phép so trong mỗi độ dài khối. Cả ba độ dài 7, 14, 28 ngày đều cho thấy tín hiệu giảm RMSE của B so với GFS ở **ngày 1, 2** và so với MOS ở **ngày 1, 3**. So với GFS ở ngày 3, kết quả nhạy với độ dài khối. So với MOS ở ngày 2, khoảng chênh lệch còn chứa 0 ở cả ba độ dài khối. Đây là kết quả hồi cứu trên giai đoạn 2026 đã xem. [Bảng khoảng đồng thời và số trạm cải thiện](doi_chieu_hoi_cuu_2026.csv).

## Giới hạn và cách hiển thị

Mốc mưa lớn trong nghiên cứu là 50 mm/24 giờ tại một trạm. Ở ngày 1, B bắt 275 trong 600 trường hợp mưa lớn và có 123 lần báo nhầm trong 398 lần báo có. Ở ngày 3, 494 trong 849 lần báo có là nhầm. Đó là số đếm gộp trạm và thời điểm phát. Cần thêm nhiều đợt mưa mới trước khi đánh giá khả năng cảnh báo. Lịch theo dõi 18/11 không lưu được lần phát trước giờ dự báo. Các ví dụ bản đồ là phát lại từ kho đánh giá. [Bảng sự kiện](../gfs_training_window_2026_11_18/event_metrics.csv).

Bản đồ tô màu tại vị trí trạm theo mm/24 giờ, dùng cùng dải màu cho cả ba hạn. Trạm thiếu mẫu dùng ký hiệu riêng. Chọn trạm để xem thêm mưa dự báo, mưa thực đo đã đối chiếu và xác suất mưa từ 50 mm. Bản đồ WPC là một tham khảo về cách chọn hạn và đọc thang màu. WPC vẽ đường đồng mức từ trường mưa theo diện tích, còn đầu ra PBL6 được biểu diễn bằng điểm trạm. [Bản đồ lượng mưa WPC](https://www.wpc.ncep.noaa.gov/qpf/qpf2body.html).

[Hướng dẫn mở bản đồ trên máy](../../demo/station_map/README.md) gồm hai lần phát lịch sử, 12/11 và 07/10/2026. Lần thứ hai được chọn để minh họa vì có nhiều trạm ghi nhận mưa lớn ở ngày 1.
