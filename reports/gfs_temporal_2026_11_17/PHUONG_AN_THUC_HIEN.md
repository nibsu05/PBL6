# Cải tiến dự báo mưa ngắn hạn tại trạm

Ngày lập: 17/11/2026. Đây là thí nghiệm mới, độc lập với bản kiểm chứng đã đóng băng. Nhánh Bi-LSTM để sau theo yêu cầu người dùng.

## 1. Mục tiêu cụ thể

Mỗi ngày lúc **19:00 giờ Việt Nam**, dùng thông tin được giả định có trước thời điểm này để dự báo **ba tổng lượng mưa 24 giờ riêng biệt tại chính trạm**:

| Đầu ra | Khoảng thời gian tính từ lúc phát dự báo | Ví dụ phát lúc 19h thứ Hai |
| --- | --- | --- |
| Ngày 1 | 0–24 giờ tiếp theo | 19h thứ Hai → 19h thứ Ba |
| Ngày 2 | 24–48 giờ tiếp theo | 19h thứ Ba → 19h thứ Tư |
| Ngày 3 | 48–72 giờ tiếp theo | 19h thứ Tư → 19h thứ Năm |

Nhãn là tổng 24 số đo mưa giờ Vrain, cùng trạm và cùng API trong cả lịch sử lẫn ba nhãn. Không chia mưa ngày thành giờ; không thay nhãn bằng GFS, ERA5 hay vệ tinh. Giữ 57 trạm đạt điều kiện từ tập huấn luyện trước đây để so sánh được với nghiên cứu cũ. Một mô hình dùng chung cho nhiều trạm.

## 2. Vì sao thử hướng này?

Đầu vào cũ đã có tổng mưa GFS của từng ngày, nhưng khí tượng của một ngày chỉ được đại diện bởi **một trạng thái dự báo ở giữa ngày đó**. Hai ngày cùng tổng 80 mm có thể khác nhau: một ngày mưa tập trung vào vài giờ, ngày kia trải đều. Một trạng thái giữa ngày cũng có thể bỏ qua quá trình ẩm tăng hoặc gió đổi hướng.

Đề xuất mới giữ nguyên bản GFS khởi tạo 00 UTC, bổ sung diễn biến bên trong mỗi cửa sổ ngày. Đây là giả thuyết cần kiểm tra; thêm biến không bảo đảm giảm sai số.

## 3. Bốn cấu hình LightGBM

26 biến nền T0 gồm: một tổng mưa GFS, hai biến lịch sin/cos ngày trong năm, ba biến vị trí/ID, mười biến mưa quá khứ, năm trường khí tượng giữa ngày và năm biến DEM. Vị trí/ID chỉ giúp phân biệt trạm trong mô hình; không biến lượng mưa tại điểm thành mưa trung bình một vùng.

| Cấu hình | Số đặc trưng | Thông tin |
| --- | ---: | --- |
| T0 | 26 | Đúng N3 cũ: mưa GFS ngày; lịch, vị trí/ID; bảy ngày mưa quá khứ và tổng gần nhất 1/6/24 giờ; T/RH/gió 850 hPa/PWAT ở giữa ngày; năm đặc trưng DEM |
| T1 | 34 | T0 + bốn lượng mưa GFS 6 giờ, lượng lớn nhất 6 giờ, tỷ trọng lớn nhất, vị trí trọng tâm mưa theo thời gian và tỷ trọng mưa nửa đầu ngày |
| T2 | 41 | T0 + trung bình của ba mẫu, biên độ và chênh lệch cuối–đầu của từng trường T/RH/u/v/PWAT: 5 × 3 = 15 biến |
| T3 | 49 | T0 + cả phân bố mưa 6 giờ lẫn diễn biến khí tượng |

Các trạng thái khí tượng mới nằm ở **+6, +12, +18 giờ trong từng cửa sổ 24 giờ đích**. Trung bình ba mẫu tức thời không được gọi là trung bình khí tượng toàn ngày. Bốn lượng mưa 6 giờ là dự báo GFS lấy bằng hiệu tích lũy, không phải số đo mưa Vrain được nội suy.

Mưa bằng 0 có các tỷ trọng/trọng tâm quy ước bằng 0. Chỉ sửa chênh lệch âm rất nhỏ trong dung sai đóng gói GRIB và ghi cờ; chênh lệch âm lớn bị từ chối. Tổng mưa ngày cũ được giữ nguyên để đối chiếu.

Ví dụ giả định, chỉ xét thông tin mưa dự báo: hai chuỗi 6 giờ `[0, 0, 80, 0]` và `[20, 20, 20, 20]` đều có tổng 80 mm/ngày. Dữ liệu mới phân biệt được mưa dồn hay mưa rải đều. Chọn bốn khoảng 6 giờ để mô tả diễn biến với ít biến và khối lượng trích xuất phù hợp; đây là lựa chọn thiết kế, chưa chứng minh tối ưu hơn khoảng 3 giờ hoặc 1 giờ. Không dùng lựa chọn này để biện minh việc nội suy nhãn mưa trạm.

## 4. Mô hình và so sánh công bằng

LightGBM chạy đủ T0–T3. GRU nhỏ chạy T0, T3 và **LINEAR23**: thêm 23 tổ hợp tuyến tính cố định của dữ liệu T0, không thêm nguồn thông tin mới. LINEAR23 có cùng số kênh và số tham số với GRU T3. Đối chứng này giúp xem lợi ích có vượt việc tăng dung lượng đầu vào hay không; cùng số tham số chưa đồng nghĩa cùng khả năng tối ưu.

Giữ ba seed 17/29/43, ngân sách cây theo từng đầu/hạn đã chọn bằng cross-validation chỉ trên 2021–2022. GRU giữ 17 epoch, hidden 16, head 24, learning rate 0,001. Không tìm thêm nhiều kiến trúc để chọn theo kết quả 2025. Các đối chứng gồm 0 mm, khí hậu, mưa 24h gần nhất, GFS thô và MOS hiệu chỉnh đơn giản.

Seed là mã khởi tạo ngẫu nhiên. Ba mã 17/29/43 tạo ba lần huấn luyện trên cùng dữ liệu và cách chia năm; kết quả có thể khác vì trọng số ban đầu, xáo trộn batch hoặc cách lấy mẫu. Lấy trung bình ba dự báo và báo điểm từng seed để thấy độ ổn định. Ba seed không tạo ra ba bộ số đo độc lập. LightGBM học từ bảng đặc trưng; GRU dùng thêm bộ mã hóa chuỗi mưa bảy ngày, giúp kiểm tra hành vi với một cách biểu diễn khác.

Mọi cấu hình được chấm **trên đúng cùng các mẫu trạm–ngày**, đủ cả ba nhãn và toàn bộ đầu vào T3. Báo riêng việc mất mẫu nếu trường mới bị thiếu. T0 được huấn luyện lại cùng quy trình và đối chiếu dự báo cũ; không lấy điểm hai tập mẫu khác nhau để kết luận tăng chất lượng.

Với T3, LightGBM nhận bảng `[số mẫu ở một hạn, 49 biến]` và học riêng từng hạn. GRU nhận lịch sử mưa `[số mẫu, 7 ngày, 1]`, context dự báo `[số mẫu, 3 ngày đích, 41]` và ID trạm. Con số 41 bằng 49 trừ bảy biến lịch sử đã đưa qua nhánh chuỗi và một mã trạm đã đưa qua embedding. Cả hai cùng dùng thông tin được phép tại issue; chỉ khác cách biểu diễn.

Mỗi mẫu trả ba lượng mean, ba lượng median, ba xác suất mưa từ 1 mm và ba xác suất mưa từ 50 mm. Mean và median là hai cách ước lượng lượng mưa cho hai mục tiêu đánh giá, không phải hai nhãn đo khác nhau.

## 5. Chia dữ liệu và giới hạn kết luận

| Giai đoạn | Vai trò trong thí nghiệm mới |
| --- | --- |
| 2021–2022 | Fit mô hình và mọi phép chuẩn hóa |
| 2023 | Hiệu chỉnh xác suất và chọn ngưỡng qua cross-fit theo quý |
| 2024 | Phát triển, đã được phân tích trước đây |
| 2025 | Đánh giá hồi cứu; đã chấm ở vòng cũ, không còn là test chưa dùng |
| 2026 hiện có | Đánh giá hồi cứu, tách hai API; chưa đủ năm và chưa xác nhận tính liên tục |
| Dữ liệu sau thời điểm khóa mô hình tương lai | Có thể tạo kiểm định mới thực sự chưa sử dụng |

Lần này vẫn không fit/tuning bằng nhãn 2025–2026. Tuy nhiên, việc đã xem kết quả những năm đó ảnh hưởng lựa chọn hướng nghiên cứu; không thể khôi phục tính độc lập bằng cách chỉ đổi tên tập hoặc khóa lại checkpoint. Giữ nguyên toàn bộ kết quả kiểm chứng cũ.

## 6. Chấm điều gì?

Mô hình có hai đầu lượng: **mean** phục vụ RMSE và **median** phục vụ MAE. Không chọn mỗi mô hình một đầu tốt nhất sau khi thấy kết quả. Đầu xác suất gồm P(mưa ≥ 1 mm) và P(mưa ≥ 50 mm), luôn bảo đảm xác suất ngưỡng lớn không vượt ngưỡng nhỏ. 50 mm/24h là ngưỡng phân tích nghiên cứu ở đây, không tự nhận là chuẩn cảnh báo vận hành.

| Chỉ số | Diễn giải | Chiều tốt |
| --- | --- | --- |
| RMSE của đầu mean | Phạt mạnh các lần sai lượng mưa lớn | Nhỏ hơn |
| MAE của đầu median | Sai số tuyệt đối điển hình theo mm | Nhỏ hơn |
| Bias | Trung bình dự báo thừa hay thiếu | Gần 0 |
| BS | Sai số xác suất sự kiện mưa | Nhỏ hơn |
| BSS | BS tốt hơn khí hậu tham chiếu bao nhiêu; âm là kém tham chiếu | Lớn hơn |
| POD | Trong sự kiện mưa thực tế, bắt đúng bao nhiêu | Lớn hơn, phải đọc cùng FAR |
| FAR | Trong các lần báo mưa, tỷ lệ báo nhầm | Nhỏ hơn |
| CSI | Cân nhắc báo đúng, bỏ sót và báo nhầm | Lớn hơn |

Chấm từng trạm rồi lấy trung bình giữa trạm; kèm phân tích theo tháng, mức mưa và từng seed. Bootstrap ghép khối 14 ngày, giữ các trạm cùng đợt mưa trong cùng lần lấy mẫu. Bốn so sánh chính × ba hạn = 12, hiệu chỉnh nhiều so sánh. Kết quả hiệu chỉnh ở các năm đã xem vẫn là bằng chứng thăm dò.

## 7. Kiểm tra nhãn và nguồn

Kiểm tra độc lập tổng 24 giờ, độ đầy đủ, xung đột API, mưa ở trạm lân cận và GSMaP chưa hiệu chỉnh trạm. Vệ tinh là đối chiếu bối cảnh, không phải chân lý để sửa trạm. Trạm gần nhau cũng có thể cùng chịu lỗi hệ thống; mưa cục bộ có thể khác xa lân cận. Không loại mưa lớn chỉ vì mô hình dự báo sai.

Hai đường API đều thuộc Vrain. Tọa độ hiện tại khớp không chứng minh lịch sử cảm biến hoặc tính liên tục số đo. Chưa có xác nhận chính thức nguyên nhân đổi độ phủ hai API. Độ trễ GFS 8 giờ và trạm 1 giờ vẫn là giả định cần đo khi vận hành, không phải điều đã được chứng minh từ archive.

GSOD không được ghép trực tiếp để kiểm chứng cùng ngày: ngày UTC của GSOD khác cửa sổ 19h–19h Việt Nam của nhãn hiện tại. Cần tái tổng hợp từ số giờ đúng khoảng trước khi dùng đối chiếu lượng.

## 8. Điều kiện bàn giao

Chỉ báo hoàn thành khi đã tải và kiểm tra các chu kỳ nguồn, dựng tập chung, huấn luyện đủ cấu hình/seed, khóa artifact trước chấm hồi cứu, kiểm tra replay/không rò rỉ, xuất bảng kết quả và báo cáo kết luận kể cả khi không cải thiện. Không coi trạng thái đang tải là đã huấn luyện xong.

Dữ liệu, registry, checkpoint và dự báo từng thời điểm nằm riêng trong `data/operational/gfs_temporal_2026_11_17/`, không đưa lên GitHub công khai. Báo cáo tổng hợp nằm cùng thư mục với tài liệu này.

Nguồn kỹ thuật: [sản phẩm GFS của NOAA](https://www.nco.ncep.noaa.gov/pmb/products/gfs/), [thời gian bin GSMaP](https://sharaku.eorc.jaxa.jp/GSMaP/faq/GSMaP_faq03.html), [định dạng và kênh hiệu chỉnh trạm GSMaP](https://www.eorc.jaxa.jp/GPM/doc/product/format/en/07.GPM_GSMaP_Product_Format_E.pdf), [mô tả GSOD của NOAA](https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc%3AC00516).
