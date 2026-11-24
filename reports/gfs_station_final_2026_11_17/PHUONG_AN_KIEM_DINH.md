# Phương án kiểm chứng cuối — dự báo mưa tại trạm

Ngày chốt: 17/11/2026, trước khi huấn luyện đối chứng mới và tính điểm mô hình trên 2025–2026. Đây là phiên bản nghiên cứu riêng; kết quả daily-v2 cũ được giữ nguyên. Người dùng đã duyệt kế hoạch gồm đối chứng, khóa phương án rồi kiểm định 2025 và đánh giá riêng 2026.

## 1. Câu hỏi nghiên cứu và phạm vi

Mỗi ngày lúc 19h Việt Nam, dự báo ba tổng mưa 24 giờ riêng tại từng trạm: 0–24h, 24–48h và 48–72h. Nhãn là mưa Vrain sau kiểm tra chất lượng; đầu vào gồm lịch sử mưa tại chính trạm, dự báo GFS đã khởi tạo trước thời điểm phát tin, lịch/vị trí và đặc trưng địa hình. Các trạng thái khí tượng GFS là giữa cửa sổ dự báo, không phải trung bình khí tượng cả ngày.

Giữ **57 trạm được chọn chỉ bằng lịch sử train** của daily-v2 làm tập nghiên cứu chính. Có 86 vị trí trong danh mục không đồng nghĩa phải dùng cả 86 cho cùng thí nghiệm. Mở rộng tập trạm là câu hỏi khác, không gộp vào phép kiểm định này.

Câu hỏi chính: khí tượng dự báo, địa hình và cách biểu diễn gió–ẩm–địa hình có cải thiện kết quả so với dữ liệu nền hay không? Kết quả không cải thiện cũng phải được công bố.

## 2. Hai đối chứng GRU mới

| Cấu hình | Đầu vào bổ sung | Tham số học được | Vai trò |
| --- | --- | ---: | --- |
| GRU N3 gốc | Khí tượng thô và địa hình | 4.364 | Mốc trước bổ sung dẫn xuất |
| GRU N5 gốc | N3 + sáu dẫn xuất gió–ẩm–địa hình | 4.796 | Cấu hình đang cần kiểm chứng |
| GRU N3_LINEAR6 | N3 + sáu tổ hợp tuyến tính cố định của khí tượng thô và địa hình | 4.796 | Cùng số kênh và tham số với N5; không thêm thông tin quan trắc |
| GRU N3_WIDE | Giữ đầu vào N3, tăng chiều rộng head từ 24 lên 27 | 4.751 | Gần bằng số tham số N5, sai khác 45 tham số, khoảng 0,94% |

Các tổ hợp tuyến tính dùng ma trận ngẫu nhiên với seed đã khóa, không chọn dựa trên điểm số hay nhãn. Trung bình/độ lệch chuẩn để tạo chúng chỉ tính trên train. Đây là đối chứng cho ảnh hưởng của việc thêm kênh và thay đổi cách tham số hóa. Dẫn xuất N5 là các phép biến đổi phi tuyến từ cùng nguyên liệu khí tượng/địa hình.

Cùng ba seed 17/29/43, encoder GRU hidden16, learning rate 0,001, batch256, 17 epoch cố định, loss và weight decay như mô hình cũ. Không tìm thêm siêu tham số hoặc early stopping trên 2023/2024. Cấu hình dùng lại lựa chọn CV theo thời gian chỉ trong 2021–2022 của daily-v2.

Giữ cùng số tham số chưa làm hai mô hình hoàn toàn giống về khả năng biểu diễn hay cách tối ưu. Kết quả chỉ hỗ trợ giá trị của cách biểu diễn trong thiết lập đã thử, không chứng minh cơ chế vật lý nhân quả.

## 3. Chia thời gian và khóa phương án

| Giai đoạn | Vai trò |
| --- | --- |
| 2021–2022 | Fit mạng và mọi phép chuẩn hóa; dùng nguyên tập train cũ |
| 2023 | Hiệu chỉnh xác suất và chọn cutoff bằng cross-fit theo quý; không early stopping |
| 2024 | Phân tích phát triển; đã được xem trước nên không phải kiểm định cuối |
| 2025, API legacy | Kiểm định theo thời gian trên cùng 57 trạm sau khóa checkpoint/cutoff/mã chấm |
| 2026 | Đánh giá độ bền riêng theo API legacy/modern, kèm giới hạn nguồn và chưa đủ năm |

Danh sách mô hình, checkpoint, chuẩn hóa, calibrator, cutoff và mã suy luận/chấm phải được ghi SHA trước lần suy luận mô hình đầu tiên trên các hàng kiểm định. Việc 2025 đã được thu thập/QC không có nghĩa đã dùng nó để chọn mô hình. Sau khi xem kết quả 2025 không chỉnh mô hình rồi tiếp tục gọi năm đó là kiểm định chưa từng được dùng.

Không huấn luyện lại trên 2025 hoặc 2026. Mô hình lượng mưa chính được định trước là LightGBM N3, ứng viên đầu trung vị là GRU N5; các phép so sánh đặc trưng cũng được định trước. Không chọn mô hình thắng hoặc thay đầu mean/median sau khi nhìn test.

## 4. Tiêu chí đánh giá

- **RMSE đầu mean**: tiêu chí chính của dự báo lượng mưa trung bình, nhấn mạnh các lỗi lớn.
- **MAE đầu median**: tiêu chí riêng của dự báo trung vị; không đổi sang đầu khác để chọn điểm đẹp hơn.
- **Bias**: xu hướng dự báo thừa/thiếu mưa.
- **BS/BSS** ở ngưỡng 1 và 50mm/24h: sai số xác suất và cải thiện so với khí hậu tham chiếu chỉ fit bằng train.
- **CSI/POD/FAR**: báo trúng, bỏ sót và báo nhầm; báo cùng nhau. Ngưỡng50 là ngưỡng nghiên cứu thăm dò, chưa được nhận là chuẩn cảnh báo chính thức.

Báo macro giữa các trạm và micro riêng, số mẫu và số ngày có sự kiện. Có phân tích từng mùa/tháng, trạm và các khoảng lượng mưa quan trắc; các khoảng theo nhãn chỉ dùng chẩn đoán, không làm quy tắc chọn mô hình vận hành.

Ba đối chiếu đặc trưng chính là LightGBM N1–N0, LightGBM N3–N1 và GRU N5–N3_LINEAR6, theo RMSE mean ở cả ba hạn: tổng cộng một họ chín so sánh. Hai đối chiếu kỹ năng chính là LightGBM N3 với MOS về RMSE mean và GRU N5 với MOS về MAE median: một họ sáu so sánh. Các đối chiếu còn lại báo thăm dò.

Dùng bootstrap ghép cặp theo khối 14 ngày, 5.000 lần, giữ các trạm/hạn cùng đợt thời gian. Báo CI95% và khoảng đồng thời Bonferroni cho từng họ so sánh chính; kèm p xấp xỉ từ bootstrap đã định tâm và hiệu chỉnh Holm. Không diễn giải các phép so sánh chính như thể chỉ thử một giả thuyết. Khoảng này điều kiện theo ensemble đã fit, chưa bao gồm sai số cảm biến hoặc bất định do các lần huấn luyện khác nhau; báo thêm dao động giữa ba seed.

## 5. Giới hạn phải giữ khi đọc kết quả

Hai namespace legacy/modern đều từ Vrain, là nhãn dự án đặt cho hai đường API. Chưa xác nhận chính thức nguyên nhân khác độ phủ và tính liên tục số đo. Mỗi mẫu giữ lịch sử/nhãn cùng namespace; kết quả2026 báo riêng hai API và độ phủ. Không gộp điểm các năm khác độ phủ để quy thay đổi cho riêng mô hình hay API.

Độ trễ GFS8h và mưa trạm1h vẫn là giả định; phân tích nhạy trễ3/6h hiện có được giữ trong bảng. Chưa chứng minh các bản dự báo/quan trắc lịch sử đều đã có sẵn đúng thời điểm phát tin. Chưa được tuyên bố vận hành realtime hay vượt paper khác khi chưa có đối chiếu cùng miền, nhãn, hạn và cách chia dữ liệu.

Đầu ra cuối gồm bảng kết quả đồng thời các mô hình, các đối chiếu đặc trưng có bất định, chẩn đoán mưa lớn, biểu đồ minh họa, báo cáo Word và manifest tái lập. Raw, checkpoint và dự báo từng thời điểm nằm ngoài GitHub công khai.
