# So sánh mô hình dự báo mưa tại trạm Đà Nẵng

### Mô hình đã huấn luyện và mô hình trên bản đồ

**Phạm vi của các mô hình**

| Nhánh | Phương án đã chấm | Bản đồ hiện dùng |
| --- | --- | --- |
| 1–6 giờ | Bi-LSTM R/E0/E2, LightGBM R, GRU R và các mốc | **LightGBM R** mặc định, có Bi-LSTM R và mốc giữ mưa để đối chiếu |
| 1–3 ngày | LightGBM các nhóm N, GRU nhỏ, Bi-LSTM N3 và các mốc GFS/MOS | **LightGBM B** mặc định, có GFS và xác suất mưa lớn |

Ở nhánh giờ, Bi-LSTM là mô hình chuỗi dùng để thử giá trị của lịch sử mưa và các nhóm khí tượng. LightGBM R và Bi-LSTM R đều có thể chạy từ lịch sử mưa Vrain và lịch, nếu dữ liệu đến kịp. Bản phát lại chọn LightGBM R vì RMSE gộp sáu hạn trên năm 2023 là 2,209 mm, so với 2,243 mm của Bi-LSTM R và 2,825 mm của giữ mưa.

Ở nhánh ngày, LightGBM nhận một hàng đặc trưng cho mỗi kỳ. GRU nhỏ kiểm tra việc đọc thứ tự của bảy tổng mưa đã qua khi vẫn có cùng thông tin GFS cho các kỳ đích. LightGBM B là cấu hình dùng trên web từ giao thức có cửa sổ học 2021–2024, hiệu chỉnh xác suất 2025. Trong các bảng dưới đây, **LightGBM N3** là cấu hình so trực tiếp trên tập 2025 với cùng bộ 26 biến và giai đoạn học 2021–2022. Hai cấu hình có mốc học và vai trò kiểm định riêng.

GFS là dự báo vật lý của NOAA. MOS là hậu xử lý thống kê đơn giản từ GFS. Hai mốc này giúp đo phần cải thiện so với dự báo nguồn và bước sửa sai đơn giản. Thí nghiệm trước về nhóm biến khí tượng thô vẫn cho bằng chứng chính ở nhánh ngày, giảm RMSE khoảng 0,83 mm trên Ngày 2 và Ngày 3 so với nhóm nền LightGBM.

### Cách thực hiện phép thử hoán đổi

Đã huấn luyện thêm **GRU R cho 1–6 giờ** và **Bi-LSTM N3 cho 1–3 ngày**, mỗi cấu hình dùng ba seed 17, 29 và 43. Mỗi seed cho một lần khởi tạo và học. Điểm dưới đây tính trên dự báo đã lấy trung bình qua ba seed. Hai mạng chuỗi trong cùng phép so nhận cùng đầu vào, dùng cùng quy tắc mất mát, mốc huấn luyện và tiêu chí chọn epoch hoặc số epoch định trước.

- **Giờ.** GRU có 45.944 tham số, gần Bi-LSTM R có 45.718. Dùng 1.032.811 mẫu train 2021–2022 và 676.870 mẫu 2023 để chọn epoch theo RMSE. Đối chiếu đúng **679.461 khóa trạm–giờ** trên 79 trạm trong 2025, với sáu lượng một giờ cho mỗi khóa.
- **Ngày.** Bi-LSTM có 4.460 tham số, gần GRU N3 có 4.364. Giữ bảy tổng mưa đã qua, 18 biến bối cảnh cho mỗi kỳ, mã trạm, ba đầu dự báo và ngân sách 17 epoch. Dùng 35.116 mẫu train, 18.365 mẫu 2023 cho hiệu chỉnh và ngưỡng. Chấm đúng **18.723 khóa trạm–19h** trên 57 trạm trong 2025. Mỗi khóa có ba tổng 24 giờ.

Phép so giữa hai mạng gần nhau về số tham số và giữ cách dựng dữ liệu. Cả loại cổng và chiều đọc thay đổi khi hoán đổi nên kết quả phản ánh lựa chọn bộ mã hóa trọn vẹn. Các bảng là **phân tích bổ sung trên năm 2025 đã được xem**. Khoảng tin cậy 95% theo từng hạn dùng 4.000 lượt lấy mẫu lại các khối 14 ngày, giữ các trạm trong cùng khối. Không dùng kết quả này để đổi mặc định của bản đồ.

### Cực ngắn · LightGBM tốt hơn về sai số lượng mưa

**RMSE nhánh giờ trên cùng 679.461 mẫu, mm trong một giờ**

| Hạn | 0 mm | Giữ mưa | LightGBM R | Bi-LSTM R | GRU R |
| --- | --- | --- | --- | --- | --- |
| Giờ 1 | 2,738 | 2,559 | **2,151** | 2,233 | 2,205 |
| Giờ 2 | 2,738 | 2,955 | **2,347** | 2,418 | 2,399 |
| Giờ 3 | 2,737 | 3,048 | **2,411** | 2,485 | 2,468 |
| Giờ 4 | 2,737 | 3,160 | **2,469** | 2,525 | 2,516 |
| Giờ 5 | 2,735 | 3,241 | **2,504** | 2,558 | 2,547 |
| Giờ 6 | 2,736 | 3,282 | **2,534** | 2,580 | 2,574 |

RMSE càng thấp càng tốt và nhạy với các sai lệch lớn. GRU giảm RMSE khoảng 0,007–0,028 mm so với Bi-LSTM R. Ba khoảng theo từng hạn của giờ 1–3 nằm dưới 0, mức giảm nhỏ và cần kiểm tra trên đợt mới. Ở giờ 6, khoảng từ −0,020 đến +0,001 mm còn chứa 0. LightGBM cũng có CSI cao nhất ở ngưỡng 1 mm cho cả sáu giờ trong bảng đối chiếu này. [Chênh lệch và khoảng tin cậy từng hạn](https://github.com/nibsu05/PBL6/blob/research/tft-regional/reports/danang_system_2026_11_24/paired_rmse.csv)

**Phát hiện mưa từ 5 mm ở Giờ 6, có 17.034 giờ–trạm thực sự đạt ngưỡng**

| Phương án | POD cao hơn tốt hơn | FAR thấp hơn tốt hơn | CSI cao hơn tốt hơn |
| --- | --- | --- | --- |
| Giữ mưa | **0,274** | 0,726 | **0,158** |
| LightGBM R | 0,086 | 0,602 | 0,076 |
| Bi-LSTM R | 0,007 | 0,543 | 0,007 |
| GRU R | 0,012 | **0,282** | 0,012 |

LightGBM R phát hiện khoảng **9 trên 100** giờ mưa ≥5 mm ở hạn 6 giờ. Giữ mưa phát hiện nhiều hơn, đồng thời báo nhầm nhiều hơn. GRU R có ít báo nhầm trong nhóm đã báo, song chỉ phát hiện khoảng 1 trên 100 sự kiện. Nên đọc POD, FAR và CSI cùng nhau trước khi đánh giá khả năng cảnh báo. Kết quả RMSE của LightGBM R phù hợp với việc giữ cấu hình trình diễn lượng mưa hiện tại.

### Ngắn hạn · Bi-LSTM và GRU có điểm gần nhau ở cùng bộ N3

**RMSE đầu lượng trung bình trên 57 trạm, mm trong 24 giờ**

| Hạn | GFS | MOS | LightGBM N3 | GRU N3 | Bi-LSTM N3 |
| --- | --- | --- | --- | --- | --- |
| Ngày 1 | 26,35 | 26,13 | 26,04 | 24,67 | **24,61** |
| Ngày 2 | 27,90 | 28,68 | 29,20 | **27,18** | 27,24 |
| Ngày 3 | 33,76 | 32,35 | 30,65 | 30,62 | **30,51** |

**MAE đầu lượng trung vị trên 57 trạm, mm trong 24 giờ**

| Hạn | GFS | MOS | LightGBM N3 | GRU N3 | Bi-LSTM N3 |
| --- | --- | --- | --- | --- | --- |
| Ngày 1 | 9,77 | 9,02 | 8,14 | 7,98 | **7,96** |
| Ngày 2 | 10,38 | 9,40 | 9,25 | 8,81 | **8,78** |
| Ngày 3 | 11,74 | 10,03 | 9,50 | 9,45 | **9,44** |

Hai bảng ngày tính điểm riêng ở từng trạm rồi lấy trung bình 57 trạm. MAE cho biết sai lệch tuyệt đối trung bình, phù hợp để đọc đầu trung vị. Về RMSE, Bi-LSTM N3 so với GRU N3 chênh **−0,06 mm, +0,06 mm và −0,11 mm** qua ba ngày. Cả ba khoảng 95% còn chứa 0. Bảng in đậm điểm mẫu thấp nhất. Để đánh giá sự khác biệt ổn định cần đọc cả khoảng tin cậy.

**Cảnh báo từ 50 mm ở Ngày 3, cắt theo ngưỡng xác suất được chọn trên 2023**

| Phương án | BSS | POD | FAR | CSI |
| --- | --- | --- | --- | --- |
| MOS | 0,093 | 0,501 | 0,604 | 0,278 |
| LightGBM N3 | **0,197** | 0,493 | **0,578** | **0,289** |
| GRU N3 | 0,177 | **0,655** | 0,668 | 0,279 |
| Bi-LSTM N3 | 0,181 | 0,637 | 0,666 | 0,277 |

BSS đo chất lượng xác suất so với tần suất khí hậu tham chiếu, trước khi cắt ngưỡng để báo có hoặc không. GRU N3 báo trúng tỷ lệ cao hơn LightGBM N3 ở ngưỡng được chọn, đồng thời tỷ lệ báo nhầm cũng cao hơn. Bi-LSTM N3 cho các điểm gần GRU N3. GRU N5 dùng thêm đặc trưng và là ứng viên đã báo cáo trong thí nghiệm trước. Phép hoán đổi giữ N3 để đo tác động của việc đổi bộ đọc chuỗi.

### Quyết định cho Đà Nẵng

LightGBM, GRU và Bi-LSTM đều áp dụng được cho hai độ dài dự báo sau khi huấn luyện với đầu vào, nhãn và mục tiêu của nhánh tương ứng. Nhánh giờ đã có so sánh ba mô hình trên cùng số liệu. Nhánh ngày đã có so sánh ba mô hình ở cùng bộ N3. Dữ liệu và kiến trúc được chọn theo câu hỏi thí nghiệm và khả năng có nguồn trước giờ phát.

Giữ LightGBM R ở nhánh giờ và LightGBM B ở nhánh ngày cho bản đồ hiện tại. Giữ Bi-LSTM và GRU trong báo cáo như các phép so có kết quả, kèm giới hạn ở mưa mạnh. Ưu tiên khôi phục dữ liệu Vrain tại Đà Nẵng, ghi độ trễ và chấm các lượt phát mới. Chỉ mở thêm một mô hình khi có câu hỏi cụ thể, chẳng hạn liệu dữ liệu radar trước giờ phát có giảm bỏ sót mưa mạnh ở nhánh giờ hay liệu tín hiệu tổ hợp dự báo có cải thiện cảnh báo 1–3 ngày. Một thí nghiệm bổ sung cần giữ cùng mẫu và đối chứng để đo phần tác động này.
