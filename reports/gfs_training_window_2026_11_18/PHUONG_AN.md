# Thí nghiệm mới: thêm năm dữ liệu hay đổi hàm mất mát?

Ngày duyệt: 18/11/2026. Đây là phiên bản nghiên cứu mới, không thay checkpoint, protocol hay kết quả các phiên bản trước.

## Câu hỏi cần trả lời

Vòng trước chưa cho thấy bộ 49 biến cải thiện RMSE ổn định. Vòng này kiểm tra một khả năng khác: hai năm huấn luyện có quá ít, và hàm mất mát hiện tại có phù hợp mục tiêu dự báo lượng mưa hay không. Không mặc định thêm năm hoặc đổi loss sẽ tốt hơn.

| Cấu hình | Năm fit trọng số | Đầu lượng mưa trung bình | Đầu vào |
| --- | --- | --- | --- |
| A | 2021–2022 | Tweedie, p = 1,5 | N3: 26 biến |
| B | 2021–2024 | Tweedie, p = 1,5 | N3: 26 biến |
| C | 2021–2022 | L2, bình phương sai số | N3: 26 biến |
| D | 2021–2024 | L2, bình phương sai số | N3: 26 biến |

B−A và D−C đo tác động của thêm năm, giữ loss. C−A và D−B đo tác động của loss, giữ số năm. Đây là so sánh có kiểm soát trong bộ dữ liệu hiện có; không suy ra quan hệ nhân quả vật lý hay kết luận loss nào tốt cho mọi nơi.

## Bài toán không đổi

Một mô hình chung dự báo cho 57 trạm đủ điều kiện theo tiêu chí train cũ. Một mẫu là một trạm tại một thời điểm phát dự báo hằng ngày lúc 19h Việt Nam. Ba nhãn là tổng mưa tại chính trạm trong 0–24h, 24–48h và 48–72h sau issue. Không cộng dồn thành 24/48/72h và không lấy trung bình toàn Đà Nẵng.

Khí tượng tương lai là dự báo GFS khởi tạo 00 UTC, không phải ERA5 hoặc quan trắc tương lai. Bốn nút GFS 0,25° được nội suy song tuyến tính tại tọa độ trạm. Nội suy không tạo độ phân giải không gian thật mới. Nhãn là số đo Vrain sau QC, đủ 24 khoảng giờ của cùng một API. Không chia mưa ngày thành giờ, không điền nhãn thiếu bằng 0 hoặc bằng vệ tinh.

## Năm nào được dùng vào việc gì?

| Giai đoạn | Vai trò ở phiên bản mới |
| --- | --- |
| 2021–2022 | Fit A/C; đồng thời là phần đầu của B/D. Tuning chỉ trên các quý 2022 với dữ liệu quá khứ |
| 2023–2024 | Bổ sung vào fit B/D. Không còn là calibration/dev của phiên bản mới |
| 2025 | Hiệu chỉnh xác suất Platt và chọn ngưỡng cảnh báo; không fit cây, không early stopping |
| 2026 hiện có | Đánh giá hồi cứu, tách legacy/modern. Đã xem ở các vòng trước, không gọi là test mới |
| Sau thời điểm khóa mới | Bắt đầu lưu nguồn và dự báo trước issue; quan trắc đích chỉ lấy sau khi cửa sổ kết thúc |

Tập train ngắn có 35.116 mẫu trạm–issue, tập dài có 72.886; calibration 2025 có 18.723. Mỗi mẫu gồm ba hàng ứng với ba hạn. Giữ các cửa sổ đã đủ điều kiện theo năm ở nguồn cũ, không tự thêm cửa sổ qua ranh giới năm. Giữ nguyên 57 trạm để tránh lẫn tác động tăng số trạm với tăng số năm.

## Cách so sánh công bằng

Ba cấu hình cây × hai loss × bốn fold quý 2022 × ba hạn = 72 lần fit CV. Từng fold chỉ huấn luyện bằng quá khứ, toàn bộ 72h nhãn phải nằm trước ranh giới và có khoảng cách 7 ngày. Metric early stopping là RMSE trung bình đều giữa các trạm, sau khi chặn dự báo âm về 0.

Chọn một cấu hình cây chung bằng điểm CV trung bình qua hai loss. Mỗi hạn dùng chung số cây, lấy trung vị số vòng tốt nhất của hai loss và bốn fold. Giữ số cây, tốc độ học, cách lấy mẫu, danh sách biến và ba seed 17/29/43 giống nhau ở A–D. Vì ngân sách được giữ chung, đây không phải kết luận về khả năng tốt nhất có thể của từng loss sau tuning riêng không giới hạn.

Đầu trung vị và hai đầu phân loại giữ tham số đã chọn bằng CV train của nghiên cứu cũ. A/C dùng chung các đầu phụ; B/D dùng chung các đầu phụ. Vì thế đổi loss đầu lượng mưa không tự làm thay đổi POD/FAR hoặc BSS. Xác suất mưa lớn là `p50 = p1 × P(y≥50 | y≥1)`, bảo đảm không lớn hơn xác suất có mưa.

## Kiểm tra giá trị các nhóm biến

Sau A–D, dùng cửa sổ dài đã định trước; chọn loss chỉ theo CV 2022 để chạy N0/N1/N3, cùng ngân sách và cùng mẫu. Không chọn cấu hình nhờ điểm 2026.

| Nhóm | Số biến | Nội dung |
| --- | ---: | --- |
| N0 | 16 | Mưa GFS đúng cửa sổ đích; 2 biến lịch; tọa độ và mã trạm; 7 ngày mưa quá khứ; tổng mưa 1/6/24h kết thúc trước issue 1h |
| N1 | 21 | N0 + nhiệt độ, độ ẩm, gió u/v tại 850 hPa và hơi nước toàn cột dự báo GFS |
| N3 | 26 | N1 + cao độ DEM, trung bình/độ lệch chuẩn cao độ quanh 5km và hai thành phần độ dốc |

N1−N0 kiểm tra khí tượng thô; N3−N1 kiểm tra địa hình. N3 là bí danh của B hoặc D đã fit, không huấn luyện lại để tạo kết quả thuận lợi.

## Đánh giá và cách diễn đạt

Đầu mean ưu tiên macro RMSE; đầu median ưu tiên macro MAE. Báo Bias để thấy dự báo thiếu/thừa, BS/BSS để đánh giá xác suất, POD/FAR/CSI ở ngưỡng 1 và 50 mm/24h để đánh giá cảnh báo. Mọi BSS dùng chung khí hậu tham chiếu fit 2021–2024. Không so hai BSS dùng hai tham chiếu khác nhau.

Chia kết quả theo API, hạn, mùa, ngày khô và mưa lớn. Không bỏ những nhãn mưa cực đoan vì chúng làm RMSE xấu. Các thống kê theo mức mưa quan trắc chỉ dùng hậu kiểm sai số, không phải bộ lọc được biết trước khi dự báo.

Bootstrap ghép khối 14 ngày, 5.000 lần để giữ phụ thuộc giữa các trạm/cửa sổ trong cùng đợt mưa. Họ A–D có 12 phép so, họ ablation có 6 phép so; báo CI đồng thời Bonferroni và p bootstrap định tâm/Holm xấp xỉ. Dù có hiệu chỉnh, kết quả 2026 vẫn là thăm dò hồi cứu vì đã xem trước đó. Legacy 2026 có rất ít mưa lớn, không dùng nhóm đó một mình để kết luận ổn định POD/FAR.

## Kiểm chứng tương lai

Ghi thời điểm thực sự nhận GFS/Vrain, lưu snapshot riêng, chỉ dự báo khi đủ lịch sử cùng API và hoàn tất trước issue. Số đo giờ kết thúc sau cutoff 18h không được làm đầu vào issue 19h. Nguồn chậm hoặc thiếu thì không phát mẫu đó; không hồi phát rồi gọi là dự báo trước sự kiện.

Watcher có giới hạn một issue tương lai, không phải dịch vụ vận hành lâu dài. Máy và kết nối phải còn hoạt động. Nhãn chỉ đối chiếu sau khi ba cửa sổ khép lại cộng độ trễ; cần tích lũy nhiều đợt mưa độc lập, không công bố skill thực tế từ một ngày. Chưa có xác nhận lịch sử về độ trễ tiếp nhận, sự liên tục hai API hoặc độ chính xác từng cảm biến.
