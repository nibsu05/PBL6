# Báo cáo dự báo lượng mưa tại trạm Đà Nẵng

## MỞ ĐẦU

Đề tài dự báo lượng mưa tại các trạm thuộc danh mục Vrain Đà Nẵng. Nhánh cực ngắn ước lượng sáu lượng mưa trong từng giờ tiếp theo. Nhánh ngắn hạn ước lượng ba tổng mưa 24 giờ. Hai nhánh dùng cùng loại nhãn quan trắc tại trạm. Bộ đầu vào, lịch phát và cách đánh giá được thiết kế theo thời lượng của từng nhánh.

Thí nghiệm theo giờ đã huấn luyện và kiểm định trên **79 trạm**. Thí nghiệm theo ngày có **57 trạm**, đều nằm trong nhóm 79. Bản đồ dùng mặc định 57 trạm chung và một thanh chọn gồm chín kỳ. Kết quả chủ yếu là kiểm định hồi cứu có khóa mô hình và bản phát lại để xem cách sử dụng.

## TỔNG QUAN ĐỀ TÀI

### Câu hỏi nghiên cứu

- Từ lịch sử tại trạm, một mô hình chung dự báo lượng mưa từng giờ hiệu quả đến đâu so với lấy mưa của giờ vừa đo?
- Khí tượng dự báo GFS giúp cải thiện lượng mưa theo ngày ở những hạn nào khi so cùng trạm, cùng giờ phát và cùng thiết kế học?
- Khi cả hai nhánh biểu diễn cùng lúc, phạm vi trạm, giờ hiệu lực và chênh lệch giữa các tổng được kiểm tra như thế nào?

### Phạm vi trạm và kết quả bàn giao

**Phạm vi đã kiểm định và phạm vi hiển thị**

| Phần | Số trạm | Cách đọc |
| --- | ---: | --- |
| Danh mục Vrain | 86 | Danh mục của nhóm Đà Nẵng trong kho dữ liệu |
| Mô hình giờ | 79 | Có cửa sổ huấn luyện 24 giờ và sáu nhãn giờ đạt kiểm tra |
| Mô hình ngày | 57 | Đạt tiêu chí chọn trạm từ 2021–2022, gồm từ 365 ngày đủ dữ liệu và 30 ngày có mưa từ 1 mm |
| Bản đồ mặc định | 57 | Tập trạm chung. Số trạm có dự báo được ghi riêng theo từng lượt và hạn |

Trong **22 trạm bổ sung của nhánh giờ**, dữ liệu ngày cũng có mẫu ghép đủ ba hạn ở cả 22. Mỗi trạm có **75–160 lượt** huấn luyện theo ngày trong phiên bản dữ liệu hiện có, tổng 3.106 lượt. Các trạm này có **136–191 ngày quan trắc đủ** trong kỳ chọn trạm ban đầu, thấp hơn 365 ngày theo thiết kế đã khóa. Đây là nhóm ứng viên phù hợp để thử mở rộng nhánh ngày trong một protocol mới. Bảy vị trí còn lại cần một kế hoạch huấn luyện và kiểm định dựa trên giai đoạn có đủ quan trắc.

## CƠ SỞ LÝ THUYẾT

### Giờ phát và độ dài kỳ đo

Mưa là lượng tích lũy trong một khoảng thời gian, đơn vị mm. Theo quy ước của dữ liệu Vrain tại dự án, số ghi lúc 10h là lượng rơi từ 09h đến 10h, giờ Việt Nam. Tại mốc phát 19h, **Giờ 1** là 19h–20h và **Giờ 6** là 00h–01h hôm sau. **Ngày 1** là 19h–19h hôm sau, chứa cả sáu giờ đầu. Ngày 2 và Ngày 3 là hai khoảng 24 giờ tiếp theo. Trên giao diện, cần đọc cả giờ bắt đầu, giờ kết thúc và đơn vị của kỳ đang chọn.

<!-- figure:timeline -->

### Mô hình và đối chứng

**Các phương án và mục đích sử dụng**

| Phương án | Cách dự báo | Vai trò |
| --- | --- | --- |
| Dự báo 0 mm | Luôn trả về 0 | Mốc cho tập nhiều thời điểm khô |
| Giữ mưa | Lặp lại số đo mới nhất cùng độ dài kỳ | Mốc dự báo khi trạng thái mưa còn kéo dài |
| LightGBM | Các cây học từ bảng đặc trưng của nhiều trạm | Mô hình lượng theo giờ và hậu xử lý GFS theo ngày |
| Bi-LSTM | Tóm tắt chuỗi giờ quá khứ theo hai chiều | Kiểm tra ích lợi của học chuỗi và thêm biến khí tượng |
| GFS và MOS | GFS dự báo số. MOS hiệu chỉnh thống kê bằng dữ liệu huấn luyện | Mốc vật lý và mốc hậu xử lý đơn giản cho nhánh ngày |
| GRU | Tóm tắt chuỗi mưa quá khứ rồi kết hợp đầu vào theo hạn | Đối chứng mô hình chuỗi cùng tập trạm của nhánh ngày |

Trong Bi-LSTM, cả hai chiều chỉ đọc các phần tử nằm trong cửa sổ quá khứ. Mã trạm học được giúp cùng một mô hình tạo dự báo riêng tại mỗi điểm. Trong GRU nhánh ngày, chuỗi đầu vào là bảy tổng mưa đã qua, sau đó ghép thông tin GFS và địa điểm tương ứng với từng hạn. Các mô hình theo giờ và theo ngày được chọn theo câu hỏi và nguồn dữ liệu của từng thí nghiệm.

### Chỉ số và nguyên tắc so sánh

**Ý nghĩa các chỉ số trong báo cáo**

| Chỉ số | Ý nghĩa | Chiều tốt |
| --- | --- | --- |
| RMSE | Sai số lượng mưa, phạt mạnh trường hợp sai nhiều | Nhỏ hơn |
| MAE | Trung bình độ lệch tuyệt đối, đọc trực tiếp theo mm | Nhỏ hơn |
| Bias | Trung bình dự báo trừ thực đo, cho biết xu hướng thừa hay thiếu | Gần 0 |
| POD | Tỷ lệ sự kiện thực tế được phát hiện | Lớn hơn |
| FAR | Tỷ lệ báo nhầm trong những lần đã báo có | Nhỏ hơn |
| CSI | Báo đúng chia cho tổng báo đúng, bỏ sót và báo nhầm | Lớn hơn |
| BS và BSS | Sai số của xác suất và mức cải thiện so với xác suất tham chiếu | BS nhỏ, BSS lớn |

RMSE và MAE luôn đi với thời lượng tích lũy. So sánh mô hình cùng nhánh trên cùng nhãn, mẫu và hạn. Điểm **micro** gộp các mẫu, còn điểm **macro** tính điểm theo trạm rồi lấy trung bình đều giữa các trạm. Ngưỡng 1 mm và 5 mm trong giờ dùng cho nghiên cứu nhánh giờ. Ngưỡng 50 mm trong 24 giờ dùng để chấm sự kiện ngày. Xác suất đã hiệu chỉnh và quyết định dựa trên lượng dự báo là hai cách phát hiện sự kiện khác nhau.

## THUẬT TOÁN TRIỂN KHAI

### Xử lý mưa trạm và ghép thời gian

1. Chuẩn hóa mã trạm và quy ước giờ kết thúc về một trục UTC. Giao diện hiển thị UTC+7. Giữ nguồn Vrain legacy, modern và cờ chất lượng trong bảng dữ liệu.
2. Kiểm tra giá trị mưa theo giờ, các bản ghi thiếu và tính nhất quán của nguồn. Giữ thiếu ở trạng thái thiếu. Mẫu cùng trạm và cùng kênh được chọn cho quá khứ và nhãn của thí nghiệm.
3. Với nhánh giờ, lấy đúng 24 khoảng 1 giờ kết thúc tại lúc phát để tạo đầu vào. Sáu khoảng tiếp theo cung cấp sáu nhãn. Hạn đủ nhãn được kiểm tra riêng trong bước chấm.
4. Với nhánh ngày, chỉ cộng các cửa sổ có đủ 24 giờ hợp lệ. Mỗi lần phát đóng gói ba nhãn riêng. Ghép GFS theo đúng chu kỳ và cửa sổ kiểm định, nội suy tại tọa độ trạm.
5. Chia mẫu theo thời gian trước khi huấn luyện, để toàn bộ nhãn trong kỳ tương ứng. Chuẩn hóa, số cây, số epoch và ngưỡng ra quyết định theo vai trò từng tập. Mỗi phép so dùng chung các khóa trạm, giờ phát và hạn.

### Huấn luyện nhánh cực ngắn

**Đầu vào trong ba cấu hình Bi-LSTM**

| Cấu hình | Số biến | Thành phần |
| --- | ---: | --- |
| R | 3 | Mưa Vrain, chênh mưa so với giờ liền trước trong cửa sổ, tháng |
| E0 | 11 | R cộng nhiệt độ, tốc độ gió, độ ẩm, áp suất gần mặt đất và bốn chênh lệch theo giờ |
| E2 | 13 | E0 cộng hai thành phần gió u/v ở mực 850 hPa |

ERA5 được dùng trong phép thử hồi cứu E0 và E2. R và LightGBM R có thể tính đầu vào từ mưa trạm và lịch tại giờ phát, khi quan trắc đến kịp. LightGBM R dùng 24 giá trị mưa gần nhất, tháng, mã trạm và các tổng hoặc cực đại tính từ chính cửa sổ đó. Sáu bộ cây theo hạn dùng chung cho mọi trạm.

Bi-LSTM có một lớp hai chiều, 64 nút mỗi chiều, mã trạm học được và sáu đầu ra lượng mưa không âm. Loss là MSE trên log(1 + mm). Huấn luyện tối đa 20 epoch, chọn bằng RMSE tính trên lượng đã đổi về mm năm 2023. Chạy ba seed 17, 29 và 43, rồi lấy trung bình dự báo theo mm. E0 và E2 cùng mẫu, ngân sách và kích thước mạng. Chênh khác biệt chính là hai kênh gió được đưa vào E2.

Chuẩn hóa lấy trung bình và độ lệch chuẩn từ các giờ thuộc cửa sổ huấn luyện. Cấu hình thiếu kênh theo thiết kế giữ kênh đó bằng 0 sau chuẩn hóa, để dung lượng Bi-LSTM giống nhau khi thêm biến. Với LightGBM R, huấn luyện L2 trên mm, tối đa 250 vòng tăng cường mỗi hạn. Năm 2023 quyết định vòng dừng và phương án mưa trạm dùng cho bản đồ. Seed điều khiển khởi tạo và thứ tự mẫu. Điểm của ba seed phản ánh một phần biến thiên huấn luyện của cùng tập dữ liệu.

**Phân vai thời gian**

| Giai đoạn | Thí nghiệm cực ngắn | Thiết kế kiểm định nhánh ngày |
| --- | ---: | ---: |
| 2021–2022 | Huấn luyện 1.032.811 mẫu | Huấn luyện 35.116 mẫu trạm–lượt, mỗi mẫu ba hạn |
| 2023 | Chọn epoch và số cây trên 676.870 mẫu | Hiệu chỉnh xác suất và ngưỡng trên 18.365 mẫu |
| 2024 | Phát triển trên 680.282 mẫu | Phát triển trên 19.405 mẫu |
| 2025 | Kiểm định sau khóa trên 679.461 mẫu | Kiểm định sau khóa trên 18.723 mẫu |

Số mẫu theo giờ và theo ngày có đơn vị đếm khác nhau. Một trạm có tối đa 24 mốc phát trong một ngày ở thí nghiệm giờ, trong khi thiết kế theo ngày dùng mốc 19h.

### Huấn luyện nhánh ngắn hạn

Đầu vào N0 gồm mưa GFS, lịch, vị trí và mã trạm, bảy tổng ngày quá khứ và các tổng mưa gần 1, 6 và 24 giờ. GFS khởi tạo lúc 00 UTC. Mốc phát là 12 UTC, tương đương 19h Việt Nam. Các trường nhiệt, ẩm, gió lấy theo trạng thái GFS đại diện giữa kỳ dự báo của mỗi hạn. Thiết kế lịch sử có thử trễ Vrain 1, 3 và 6 giờ.

**Các nhóm đầu vào theo ngày**

| Nhóm | Số biến | Bổ sung |
| --- | ---: | --- |
| N0 | 16 | Đầu vào nền mô tả dự báo mưa và trạm |
| N1 | 21 | N0 cộng nhiệt độ, độ ẩm, u/v ở 850 hPa và hơi nước toàn cột |
| N2 | 25 | N1 cộng độ ẩm riêng, hai thành phần dòng ẩm và tốc độ gió |
| N3 | 26 | N1 cộng năm biến địa hình |
| N4 | 30 | N3 cộng bốn dẫn xuất gió và ẩm |
| N5 | 32 | N4 cộng hai tương tác gió hoặc dòng ẩm với độ dốc |

Mô hình lượng có đầu kỳ vọng và đầu trung vị. Đầu kỳ vọng được chấm chính bằng RMSE. Đầu trung vị được chấm chính bằng MAE. Xác suất ngày từ 50 mm được tính từ xác suất có mưa từ 1 mm nhân với xác suất đạt 50 mm trong nhóm có mưa. Cách xây dựng giữ xác suất 50 mm không vượt xác suất 1 mm.

Trong thiết kế 2021–2022, nhóm chọn siêu tham số bằng bốn quý của năm 2022 theo thứ tự thời gian. Mỗi lần học dùng phần quá khứ và có khoảng cách bảy ngày trước quý chấm. LightGBM thử 7, 15 và 31 lá. Số cây cuối theo từng hạn lấy từ các lần dừng ở bốn quý. GRU chính dùng 16 nút ẩn, đầu kết hợp 24 nút và 17 epoch. Mô hình gộp ba seed 17, 29 và 43. Năm 2023 dành để hiệu chỉnh xác suất và khóa ngưỡng quyết định.

Đầu lượng kỳ vọng dùng Tweedie để xử lý lượng mưa không âm có nhiều số 0 và đuôi dương dài. Đầu trung vị học bằng pinball ở phân vị 0,5. Ví dụ giả định có 80% khả năng mưa 0 mm và 20% khả năng mưa 50 mm thì kỳ vọng là 10 mm, trung vị là 0 mm. Vì hai giá trị trả lời hai câu hỏi khác nhau, nhóm khóa đầu ra trước khi so RMSE và MAE.

Thiết kế kiểm định 2025 giữ LightGBM N3 làm phương án lượng chính và GRU N5 làm ứng viên trung vị. Đối chứng tham số của GRU kiểm tra liệu thêm dẫn xuất có lợi hơn chỉ tăng số kênh hoặc dung lượng mạng. Với bản trình diễn theo ngày **LightGBM B**, đầu vào là N3, lượng được huấn luyện trên 2021–2024 và xác suất hiệu chỉnh bằng 2025. B được đánh giá trên hồi cứu 2026, còn các phép so kiểm định 2025 ở phần dưới dùng các mô hình đã khóa của thiết kế trước.

## CHƯƠNG TRÌNH VÀ KẾT QUẢ

### Bản đồ thống nhất theo chín kỳ

Backend ghép hai sản phẩm theo **cùng thời điểm phát chính xác**. Mỗi kỳ có giờ bắt đầu, giờ kết thúc, thời lượng, trạng thái và số trạm có số riêng. Giao diện kéo từ 1h đến 6h rồi Ngày 1–3 trong một thanh. Kỳ chưa có dự báo được ghi thiếu. Việc mở bản đồ và kéo thanh chỉ đọc đầu ra đã lưu.

Các xã, phường dùng cùng bộ ranh giới tham chiếu. Màu thể hiện **lượng cao nhất tại một trạm nằm trong ranh giới**. Bảng bên cạnh có dải màu và ngưỡng lọc riêng cho 1 giờ hoặc 24 giờ. Vùng xám chưa có số. Người dùng có thể chọn trạm để xem các hạn, đổi lớp mô hình phù hợp và bật toàn bộ tập trạm theo hạn. Sau đăng nhập, có thêm Vrain thực đo, sai lệch và CSV có ghi rõ thời lượng.

Đã tạo **9 lượt phát lại có đủ hai nhánh**, gồm 05–12/11 và lượt 07/10/2026. Lượt 04/11 chỉ có nhánh giờ. Tại mốc **19h ngày 12/11**, tập chung hiển thị **57/57 trạm theo giờ** và **55/57 trạm theo ngày**. Trong chế độ toàn bộ, cực ngắn có 78/79 trạm ở lượt này. Bản đồ kiểm tra bằng Edge ở 1440×900 và 390×844, gồm đổi đơn vị qua nửa đêm, đủ chín nút, lượt thiếu, phạm vi trạm, quyền đọc quan trắc và tải CSV.

<!-- figure:map_hour -->
<!-- figure:map_day -->

### So sánh trên đúng 57 trạm và mốc 19h

Từ hai kho dự báo 2025 đã khóa, ghép khóa trạm và giờ phát 19h. Có **18.719 lượt chung từ 362 ngày phát**. Trong 18.723 lượt của nhánh ngày, bốn lượt thiếu mẫu giờ tương ứng trên cùng khóa. Tất cả phương án trong mỗi bảng dưới dùng đúng 18.719 mẫu trên từng hạn. Các bảng tính điểm micro. Đây là phân tích lại trên phần giao của hai tập kiểm định.

**RMSE dự báo lượng mưa từng giờ, đơn vị mm**

| Mô hình | Giờ 1 | Giờ 2 | Giờ 3 | Giờ 4 | Giờ 5 | Giờ 6 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 mm | 2,774 | 2,498 | 2,491 | 2,617 | 2,653 | 2,854 |
| Giữ mưa giờ vừa đo | 3,005 | 3,242 | 3,294 | 3,377 | 3,359 | 3,420 |
| Bi-LSTM R | 2,420 | 2,230 | 2,270 | 2,411 | 2,468 | 2,683 |
| Bi-LSTM E0 | 2,470 | 2,279 | 2,291 | 2,426 | 2,469 | 2,672 |
| Bi-LSTM E2 | 2,489 | 2,301 | 2,312 | 2,461 | 2,511 | 2,718 |
| LightGBM R | **2,328** | **2,188** | **2,224** | **2,344** | **2,405** | **2,613** |

Trên tập giờ đầy đủ 79 trạm, ở hạn 6 giờ LightGBM R giảm RMSE **22,8%** so với giữ mưa. Trên phần giao 57 trạm mốc 19h, kết quả cùng chiều ở cả sáu hạn. Khả năng dự báo giờ mưa mạnh còn thấp. Với ngưỡng 5 mm ở giờ 6, LightGBM R có POD **7,3%** và FAR **59,5%** trên phần giao. Phép so gió E2–E0 trên tập giờ đầy đủ có chênh CSI −0,0078 ở hạn 6 giờ, với khoảng tin cậy khối 7 ngày từ −0,0386 đến +0,0182. Thiết kế hiện tại chưa xác nhận ích lợi của riêng hai kênh gió.

**RMSE đầu lượng theo ngày, đơn vị mm trong 24 giờ**

| Mô hình | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | ---: | ---: | ---: |
| GFS | 27,362 | 28,908 | 34,682 |
| MOS | 27,219 | 29,896 | 33,427 |
| LightGBM N0 | 28,269 | 31,057 | 32,528 |
| LightGBM N1 | 27,207 | 30,215 | 31,715 |
| LightGBM N3 | 27,143 | 30,263 | 31,754 |
| GRU N3 | **25,672** | 28,250 | 31,665 |
| GRU N5 | 25,800 | **27,751** | **31,266** |

GRU N5 cũng có MAE đầu trung vị **8,047 / 8,800 / 9,477 mm** trên phần giao, so với **9,109 / 9,487 / 10,110 mm** của MOS. Trong kiểm định ngày đầy đủ đã khóa, LightGBM N1 giảm RMSE macro so với N0 **0,829 mm ở Ngày 2** và **0,833 mm ở Ngày 3**, đạt tiêu chí khoảng đồng thời và Holm. Phép so LightGBM N3 với MOS đạt tiêu chí RMSE ở Ngày 3. GRU N5 đạt tiêu chí MAE trung vị so MOS ở Ngày 1 và 3. Kết luận từ các phép so có chỉ tiêu đã định tách với thứ hạng theo điểm trong bảng.

Khoảng bất định của các phép so ngày đã định dùng 5.000 mẫu lại theo khối 14 ngày, ghép cùng lần phát và giữ mọi trạm trong cùng ngày. Quy tắc này xét việc một đợt mưa có thể ảnh hưởng nhiều trạm và nhiều ngày. Các so sánh trong một nhóm dùng khoảng đồng thời và hiệu chỉnh Holm để hạn chế chọn nhầm kết quả đẹp trong nhiều phép thử.

**BSS, POD và FAR ở ngưỡng 50 mm trong kiểm định ngày đầy đủ 2025**

| Hạn | LightGBM N3 BSS / POD / FAR | GRU N5 BSS / POD / FAR |
| --- | --- | --- |
| Ngày 1 | 0,345 / 0,680 / 0,569 | 0,349 / 0,699 / 0,559 |
| Ngày 2 | 0,248 / 0,555 / 0,493 | 0,267 / 0,535 / 0,457 |
| Ngày 3 | 0,197 / 0,493 / 0,578 | 0,186 / 0,570 / 0,577 |

Đây là điểm macro của hai đầu xác suất với cutoff đã chọn trên 2023. BSS dương cho thấy điểm xác suất tốt hơn khí hậu tham chiếu theo thiết kế, còn FAR khoảng 0,46–0,58 cho thấy vẫn có nhiều báo nhầm ở ngưỡng này.

Đối với bản trình diễn B, so trên 14.488 mẫu hồi cứu modern 2026 mỗi hạn, RMSE macro của GFS lần lượt **20,45 / 19,74 / 24,95 mm**, còn B là **15,68 / 17,47 / 20,27 mm**. Khả năng dùng trong các đợt mưa mới cần được kiểm tra qua lượt ghi đúng giờ và nhãn thu sau dự báo.

### Đối chiếu tổng sáu giờ với Ngày 1

Trên 18.719 lượt chung của 2025 và 501 lượt có đủ dự báo, nhãn trong kho phát lại 2026, tổng **thực đo** sáu giờ đầu luôn nằm trong thực đo Ngày 1, xét sai số làm tròn 0,001 mm. Đây là phép kiểm tra hướng thời gian và cách ghép nhãn.

Hai mô hình dự báo độc lập có thể cho tổng **dự báo** sáu giờ lớn hơn Ngày 1. Năm 2025 có **5.761/18.719 lượt** như vậy, trong đó **732 lượt** chênh hơn 1 mm. Bản phát lại 2026 có 12/501 lượt, trong đó 3 lượt chênh hơn 1 mm. Hai giai đoạn sử dụng cấu hình ngày và tập mưa khác nhau, nên các tỷ lệ được báo riêng.

**Hai cách hiệu chỉnh đơn giản trên phần giao 2025**

| Phương án | Lượt lệch | RMSE Giờ 6 | POD Giờ 6 ở 5 mm | RMSE Ngày 1 |
| --- | ---: | ---: | ---: | ---: |
| Dự báo gốc | 5.761 | 2,613 | 0,073 | 27,143 |
| Nâng Ngày 1 lên tổng sáu giờ khi cần | 0 | 2,613 | 0,073 | **27,027** |
| Co sáu giờ theo tỷ lệ để khớp Ngày 1 | 0 | 2,615 | 0,061 | 27,143 |

Cách nâng Ngày 1 có tín hiệu giảm nhẹ RMSE trên dữ liệu đã xem. Cách co sáu giờ làm giảm khả năng bắt mưa mạnh ở Giờ 6. Cả hai đều là phân tích thăm dò. Web giữ các giá trị đã khóa và cho xem tổng sáu giờ cùng Ngày 1 tại trạm. Một phiên bản hiệu chỉnh cần đánh giá lại trên các đợt mưa giữ riêng, cùng sai số lượng, sự kiện và tỷ lệ chênh vượt 1 mm.

### Nguồn dữ liệu và vận hành kiểm tra

Lúc **19:11 ngày 24/11/2026**, phiên Vrain được làm mới và yêu cầu danh mục trả HTTP 200, nhận diện nhóm Đà Nẵng. Hai đường tải mưa giờ đều trả HTTP 404 khi hỏi ngày hiện tại và ngày 12/11 đã có trong kho. GFS trả đủ chỉ mục của 19 trường trong lần kiểm tra. Kho Vrain cục bộ có số đo giờ hợp lệ tới **19h ngày 15/11/2026**, với 82 trạm có số tại mốc đó. Mức bao phủ thực tế của lượt mới phụ thuộc thời điểm hệ thống có thể tải quan trắc hợp lệ.

Luồng ngày đã có lịch kiểm tra nguồn trước 19h và kiểm tra nhãn đến hạn. Trang Theo dõi ghi trạng thái lỗi và kết quả từng bước. Luồng giờ đã xuất được bản phát lại từ lịch sử mưa. Cả hai loại bản ghi cần tách riêng giờ quan trắc, giờ tải được, giờ dự báo và khoảng hiệu lực khi triển khai chạy trực tiếp.

## KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

### Kết luận

Đề tài đã có quy trình dự báo theo giờ và theo ngày ở điểm trạm, các đối chứng, kiểm định sau khóa và một giao diện thống nhất. Bằng chứng chính cho nhánh giờ là giảm RMSE so với giữ mưa trên 79 trạm. Bằng chứng chính cho nhánh ngày là ích lợi của năm trường khí tượng N1 ở Ngày 2 và Ngày 3. Phép đối chiếu trên 57 trạm chung bổ sung kiểm tra cùng giờ phát, chất lượng phát hiện mưa mạnh và tính nhất quán giữa hai tổng dự báo.

### Lộ trình cải thiện

**Thứ tự thực hiện và cách xác nhận hoàn thành**

| Bước | Công việc | Bằng chứng cần có |
| --- | --- | --- |
| 1. Khôi phục tải Vrain | Xác nhận đường xuất theo giờ của nhóm Đà Nẵng, kiểm tra các ô thời gian cùng số trạm, ghi giờ nhận dữ liệu | Có mưa quan trắc mới qua kiểm tra, theo dõi độ trễ và tỷ lệ đủ trạm qua nhiều lượt |
| 2. Mở rộng nhánh ngày | Thử một mô hình chung cho 79 trạm. Giữ lại 57 trạm lõi và báo riêng 22 trạm có lịch sử ngắn. Xem xét 86 theo thời kỳ có dữ liệu phù hợp | So 57 và 79 trên cùng 57 trạm và giờ phát. Báo riêng nhóm 22 và độ bất định theo đợt mưa |
| 3. Cải thiện mưa mạnh | Nhánh giờ thử đầu xác suất sự kiện và đầu lượng riêng. Nhánh ngày thử tín hiệu GEFS sẵn có trước giờ phát và phương án hiệu chỉnh có điều kiện | So POD ở mức FAR tương đương, CSI, Brier/BSS với tham chiếu và MAE riêng ca mưa mạnh, cùng RMSE toàn tập |
| 4. Kiểm tra phù hợp 6–24 giờ | Giữ dự báo gốc làm mốc, so nâng Ngày 1 với mô hình dự báo phần mưa giờ 7–24 không âm | Giảm chênh tổng trên cùng mẫu mà giữ được kỹ năng dự báo số mm và sự kiện |
| 5. Theo dõi chạy thật | Đóng băng mô hình, ghi giờ phát và đầu vào trước nhãn. Dùng đợt mưa mới để chấm | Đếm lượt phát đúng giờ, độ phủ trạm, tỷ lệ cảnh báo, điểm theo mùa và khoảng bất định theo khối thời gian |

Các phép thử mới cần ghi rõ vai trò của năm đã xem và kỳ giữ riêng. Nên báo kết quả của mô hình đang chạy cùng các đối chứng trên cùng mẫu để nhóm có thể quyết định bằng dấu hiệu cải thiện lặp lại.

## TÀI LIỆU THAM KHẢO

- NOAA National Centers for Environmental Information, Global Forecast System. [Mô tả sản phẩm GFS](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast)
- ECMWF, ERA5 data documentation. [Nguồn và nhịp cập nhật ERA5](https://confluence.ecmwf.int/pages/viewpage.action?pageId=301966210)
- Vrain, hệ thống đo mưa chuyên dùng. [Trang hệ thống](https://www.vrain.vn/landing)
- Schuster và Paliwal, 1997. Bidirectional recurrent neural networks. [Bài báo](https://doi.org/10.1109/78.650093)
- Ke và cộng sự, 2017. LightGBM: A Highly Efficient Gradient Boosting Decision Tree. [Bài báo](https://proceedings.neurips.cc/paper_files/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html)
- Ranh giới xã, phường Đà Nẵng dùng cho bản đồ tham chiếu. [Tệp ranh giới](https://www.tinhthanhpho.com/data/wards-48.geojson) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## PHỤ LỤC

Bảng điểm mới nằm trong `so_sanh_2025_cung_tram_gio.csv`, kết quả hiệu chỉnh nằm trong `thu_rang_buoc_gio_ngay.csv`, độ phủ từng lượt nằm trong `do_phu_phat_lai.csv`. Mã băm của kho dự báo đã dùng và số khóa đối chiếu nằm trong `verification.json`.

Giao thức nhánh giờ ở `reports/station_nowcast_2026_11_24/protocol.json`. Giao thức kiểm định ngày ở `reports/gfs_station_final_2026_11_17/protocol.json`. Tài liệu bản B và thu nguồn ở `reports/gfs_short_range_closeout_2026_11_24` và `demo/station_map/README.md`.

Tạo lại bản giờ cùng các lượt ngày đã lưu bằng `scripts/prepare_station_nowcast_replay.py --align-daily`. Chạy `scripts/compare_station_forecast_branches.py` để làm lại phép đối chiếu. Bản đồ được phục vụ bởi `demo/station_map.py`.
