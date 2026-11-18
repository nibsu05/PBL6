# Thêm năm huấn luyện và đổi hàm mất mát: kết quả nghiên cứu mới

Ngày hoàn thành: 18/11/2026. Phiên bản: gfs_training_window_2026_11_18.

## Kết luận đọc trước

Trong 12 phép so A–D trên modern 2026, 1 phép đạt tiêu chí cải thiện thăm dò đã định; ablation có 0/6. Đây không phải xác nhận trên test chưa dùng.

Tweedie train dài (B) so với train ngắn (A) đổi RMSE ngày 1/2/3 lần lượt -0,025/-0,560/-0,407 mm/24 h. Cả ba điểm giảm, nhưng chưa phép nào đạt đồng thời hai tiêu chí suy luận đã định. Phép đạt tiêu chí thăm dò: D−C, ngày 3: -0,949 mm/24 h. Đổi sang L2 không cho lợi ích nhất quán qua các hạn, nên chưa có cơ sở thay mặc định Tweedie bằng L2. Khí tượng thô có điểm cải thiện ở cả ba hạn so với N0, nhưng chưa đạt tiêu chí suy luận ở vòng 2026 này; địa hình chỉ thay đổi rất nhỏ. Đây là tín hiệu để theo dõi tiếp, không phải chứng minh đã cải thiện chắc chắn trên một tập kiểm định mới.

Phương án đưa vào ghi dự báo tương lai là B: cửa sổ train dài đã định trước, loss tweedie được chọn chỉ từ CV 2022. Không chọn lại mô hình bằng kết quả 2026. Mô hình có điểm tốt nhất trên bảng hồi cứu có thể khác lựa chọn này; cần báo trung thực cả hai.

Mục tiêu là mưa tại từng trạm trong ba ngày tới, không phải mưa trung bình toàn Đà Nẵng. Một mô hình chung phục vụ 57 trạm; mỗi trạm–issue có ba nhãn 24 h riêng. Khí tượng là dự báo GFS, nhãn là số đo Vrain sau QC.

## Bốn cấu hình và dữ liệu

| Mã | Năm fit | Hàm mất mát mean | Số biến |
| --- | --- | --- | --- |
| A | 2021–2022 | Tweedie p=1,5 | 26 |
| B | 2021–2024 | Tweedie p=1,5 | 26 |
| C | 2021–2022 | L2 bình phương sai số | 26 |
| D | 2021–2024 | L2 bình phương sai số | 26 |

Train ngắn: 35.116 mẫu trạm–issue; train dài: 72.886; calibration 2025: 18.723. Mỗi mẫu có ba hạn, không coi ba hàng là ba trạm độc lập. Chỉ B/D thêm 2023–2024 vào fit; 2025 chỉ hiệu chỉnh xác suất/cutoff. Mọi trọng số cây và tham số khí hậu/MOS đều dừng ở 2024. Các phiên bản cũ giữ nguyên split và kết quả cũ.

| Tập 2026 | Mẫu D1 | Trạm | Issue | Sự kiện ≥50 D1 |
| --- | --- | --- | --- | --- |
| legacy | 1725 | 56 | 62 | 2 |
| modern | 14488 | 57 | 280 | 600 |

2026 chưa đủ năm và đã được xem ở vòng trước, vì vậy toàn bộ điểm mới là hồi cứu. Hai API không được nối thành chuỗi đồng nhất. Legacy có rất ít mưa lớn; không kết luận chất lượng cảnh báo từ nhóm này một mình. Các bảng chính dưới đây dùng modern 2026; CSV báo cả hai nhóm, từng hạn.

## Đầu vào và thời gian

| Cấu hình | Số biến | Nội dung |
| --- | --- | --- |
| N0 | 16 | Mưa GFS + lịch/vị trí/ID + 7 ngày mưa và tổng 1/6/24 h |
| N1 | 21 | N0 + T/RH/u/v tại 850 hPa và hơi nước toàn cột |
| N3 | 26 | N1 + 5 biến địa hình DEM; không thêm dẫn xuất gió–ẩm |

GFS được nội suy song tuyến tính từ bốn nút lưới 0,25° bao quanh tọa độ trạm, không phải ô đo mưa quanh cảm biến. Nhiều trạm gần nhau có thể chia sẻ trường khí tượng quy mô lớn. Mưa quá khứ lấy tại chính trạm; metadata/địa hình mô tả vị trí. DEM không phải cao độ cảm biến đã khảo sát. Xem feature_catalog.csv để biết tên và đơn vị từng biến.

Issue 19 h Việt Nam dùng GFS khởi tạo 00 UTC cùng ngày và mưa gần nhất kết thúc trước 18 h. GFS mưa đích là thông tin dự báo đã có trước issue, không phải quan trắc tương lai. Khí tượng T/RH/u/v/PWAT là trạng thái dự báo giữa mỗi cửa sổ, không gọi là trung bình ngày. Ba nhãn: 19 h hôm nay→19 h mai; 19 h mai→19 h ngày kế; tiếp tục một ngày nữa. Mỗi nhãn cần đủ 24 giờ cùng API, không điền thiếu bằng 0/vệ tinh.

## Tuning và ba seed

Đã chạy 72 fit CV: ba ứng viên × hai loss × bốn quý 2022 × ba hạn. Fold chỉ dùng quá khứ, purge toàn bộ 72 h nhãn và gap 7 ngày. Metric early stopping là RMSE trung bình đều giữa các trạm. Candidate chung được chọn: small, số lá 7; số cây ngày 1/2/3: 171/109/76. Ngân sách này áp dụng chung cho A–D và ablation, không tìm lại trên 2025/2026.

Điểm CV chuẩn hóa trung bình của hai loss tại candidate chung: Tweedie 0,91080, L2 0,92881. Điểm nhỏ hơn tốt hơn; đây là trung bình tỷ lệ RMSE so với GFS theo fold/hạn, không phải số mm.

Seed 17/29/43 là ba lần chạy với khởi tạo nguồn số ngẫu nhiên khác nhau cho việc lấy mẫu hàng/biến trong LightGBM. Cùng dữ liệu và cấu hình vẫn có thể cho cây khác nhau. Dự báo chính là trung bình ba lần; bảng sau là khoảng RMSE của từng lần, không phải khoảng tin cậy và không phải ba lần chia lại dữ liệu.

| Mô hình | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | --- | --- | --- |
| A · 2 năm/Tweedie | 15,667–15,792 | 17,999–18,057 | 20,599–20,727 |
| B · 4 năm/Tweedie | 15,629–15,821 | 17,464–17,500 | 20,227–20,329 |
| C · 2 năm/L2 | 15,596–15,703 | 17,553–17,869 | 21,233–21,443 |
| D · 4 năm/L2 | 15,932–16,423 | 16,740–16,836 | 20,285–20,501 |

Đã fit 162 estimator LightGBM cuối cùng: 54 đầu mean và 108 đầu phụ. Không có GRU/TFT/Informer mới ở vòng này. A/C dùng chung median/xác suất, B/D dùng chung median/xác suất; vì vậy đổi loss mean không tự tạo ra khác biệt cảnh báo. Ngoài ra có hai bộ khí hậu và các đối chứng MOS fit riêng theo cửa sổ.

A là mốc của protocol mới, không phải tái sử dụng nguyên checkpoint N3 cũ: ngân sách cây đã được chọn chung lại qua cả hai loss. Xác suất cũng được hiệu chỉnh bằng năm 2025 thay cho 2023. Vì vậy để tách tác động số năm/loss, dùng các phép so trong bảng A–D; không ghép điểm cũ với điểm mới rồi quy toàn bộ chênh lệch cho một thay đổi.

## Các metric và mục tiêu đầu ra

| Chỉ số | Ý nghĩa | Vai trò | Chiều tốt |
| --- | --- | --- | --- |
| RMSE | Phạt mạnh những lần sai lượng mưa lớn; mm/24 h | Chính cho đầu mean | Nhỏ hơn |
| MAE | Trung bình sai lệch tuyệt đối; mm/24 h | Chính cho đầu median | Nhỏ hơn |
| Bias | Dự báo trừ quan trắc; âm: dự báo thiếu | Theo dõi thiếu/thừa | Gần 0 |
| BS | Sai số bình phương xác suất so với có/không | Chấm xác suất trước khi chọn cutoff | Nhỏ hơn |
| BSS | 1 − BS/BS khí hậu cùng mẫu | Âm: kém khí hậu tham chiếu | Lớn hơn |
| CSI | H/(H+M+F) | Cân bằng trúng, bỏ sót, báo nhầm | Lớn hơn |
| POD | H/(H+M) | Bắt được bao nhiêu sự kiện thực | Lớn hơn |
| FAR | F/(H+F) | Bao nhiêu lần báo có là báo nhầm | Nhỏ hơn |

H là báo trúng; M là bỏ sót; F là báo nhầm. Không có mốc POD 0,4 hay 0,6 tốt chung cho mọi bài toán. POD tăng có thể đi cùng FAR tăng khi hạ cutoff. BSS âm nghĩa là xác suất kém khí hậu tham chiếu trên cùng mẫu; không nói trực tiếp lượng mưa sai bao nhiêu mm. Ở vòng này mọi BSS dùng cùng khí hậu fit 2021–2024 để so sánh công bằng.

Đầu mean nhằm dự báo mức mưa kỳ vọng, phù hợp RMSE; đầu median nhằm giá trị trung vị, phù hợp MAE và có thể gần 0 trong ngày ít khả năng mưa. Không dùng MAE của median để khẳng định đầu mean tốt hơn, hoặc ngược lại. Điểm macro cho mỗi trạm trọng số như nhau; micro gộp mọi mẫu và được báo riêng trong CSV.

Vì sao thử L2? L2 phạt bình phương sai số lượng mưa, gần trực tiếp với mục tiêu RMSE đang ưu tiên. Tweedie p=1,5 là lựa chọn hiện có cho lượng mưa không âm, có nhiều số 0 và giá trị dương lệch mạnh. Cả hai đầu đều nhằm dự báo mean; không phải một bên dự báo mean còn bên kia dự báo median. Với dữ liệu hữu hạn và cây giới hạn, hai loss tạo cách cập nhật khác nhau. L2 có thể tập trung hơn vào sai số lớn nhưng cũng nhạy với các đợt mưa cực đoan; cần đo thực tế, không mặc định phù hợp tên metric là sẽ tốt hơn.

## Kết quả lượng mưa — modern 2026

RMSE đầu mean, đơn vị mm/24 h; in đậm giá trị nhỏ nhất trong mỗi cột của bảng này, không hàm ý có ý nghĩa thống kê.

| Mô hình | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | --- | --- | --- |
| A · 2 năm/Tweedie | 15,708 | 18,029 | 20,677 |
| B · 4 năm/Tweedie | 15,683 | 17,469 | **20,270** |
| C · 2 năm/L2 | **15,627** | 17,736 | 21,356 |
| D · 4 năm/L2 | 16,135 | **16,776** | 20,406 |
| GFS nguyên bản | 20,445 | 19,738 | 24,953 |
| MOS · 4 năm | 18,933 | 17,899 | 22,361 |

GFS là dự báo khí tượng nguyên bản. MOS là hậu xử lý đơn giản từ mưa GFS và lịch mùa (Ridge cho mean, hồi quy phân vị cho median, logistic cho xác suất), giúp kiểm tra liệu LightGBM có hơn hiệu chỉnh đơn giản cùng nguồn hay không. ZERO và khí hậu/ngày trước là những mốc tối thiểu; xem bảng CSV đầy đủ để tránh chỉ so với đối chứng yếu.

Chênh lệch RMSE: âm có lợi cho cấu hình đứng trước, dương là xấu hơn.

| Phép so | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | --- | --- | --- |
| B − A | -0,025 | -0,560 | -0,407 |
| D − C | 0,508 | -0,960 | -0,949 |
| C − A | -0,081 | -0,293 | 0,678 |
| D − B | 0,452 | -0,693 | 0,136 |

B−A/D−C: tác động thêm năm với loss giữ nguyên. C−A/D−B: tác động đổi loss với số năm giữ nguyên. Không diễn giải một chênh lệch nhỏ ở riêng một hạn thành tiến bộ chắc chắn.

## Giá trị đặc trưng với cửa sổ dài

Loss tweedie được chọn từ CV 2022, dùng chung candidate/số cây/ba seed và cùng mẫu.

| Mô hình | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | --- | --- | --- |
| N0 · 16 biến | 16,055 | 17,888 | 20,833 |
| N1 · 21 biến | 15,710 | **17,450** | 20,288 |
| N3 · 26 biến | **15,683** | 17,469 | **20,270** |
| GFS nguyên bản | 20,445 | 19,738 | 24,953 |
| MOS · 4 năm | 18,933 | 17,899 | 22,361 |

N1−N0 kiểm tra khí tượng thô, N3−N1 kiểm tra địa hình. N3 là bí danh của B, không fit thêm. Kết quả phản ánh thiết kế và ngân sách này, không chứng minh một nhóm biến vô ích ở mọi mô hình.

## Trung vị và xác suất

MAE đầu median, mm/24 h. A đại diện A/C; B đại diện B/D vì chung đầu phụ.

| Mô hình | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | --- | --- | --- |
| A · 2 năm/Tweedie | **5,901** | 6,575 | 7,158 |
| B · 4 năm/Tweedie | 5,946 | 6,540 | **6,832** |
| N0 · 16 biến | 6,205 | 6,699 | 7,105 |
| N1 · 21 biến | 5,959 | **6,523** | 6,840 |
| GFS nguyên bản | 7,590 | 7,718 | 8,832 |
| MOS · 4 năm | 6,407 | 6,838 | 7,440 |

BSS cho mưa ≥50 mm/24 h; lớn hơn tốt hơn, 0 ngang khí hậu, âm kém khí hậu. Khí hậu tham chiếu chung fit 2021–2024.

| Mô hình | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | --- | --- | --- |
| A · 2 năm/Tweedie | 0,329 | 0,254 | 0,124 |
| B · 4 năm/Tweedie | 0,363 | 0,291 | 0,186 |
| N0 · 16 biến | 0,338 | 0,299 | 0,180 |
| N1 · 21 biến | 0,364 | 0,293 | 0,186 |
| GFS nguyên bản | 0,120 | 0,049 | -0,236 |
| MOS · 4 năm | 0,297 | 0,256 | 0,104 |

Hiệu chỉnh dùng Platt trên năm 2025 theo từng seed. Cutoff chọn bằng cách giữ riêng từng quý, có khoảng cách 7 ngày, sau đó fit calibrator trên toàn năm 2025. Xác suất p50=p1 ×P(y≥50|y≥1), nên không có mưa lớn với xác suất cao hơn mưa ≥1. Hai ngưỡng 1/50 dùng chung cutoff mỗi cấu hình/hạn để quyết định cảnh báo lồng nhau. Đây là ngưỡng nghiên cứu cho tổng 24 h tại trạm, không tự nhận là quy chuẩn vận hành.


### Cảnh báo ≥50 mm/24 h — ngày 1

| Mô hình | Cutoff | POD | FAR | CSI |
| --- | --- | --- | --- | --- |
| A · 2 năm/Tweedie | 0,35 | 0,439 | 0,287 | 0,371 |
| B · 4 năm/Tweedie | 0,35 | 0,465 | 0,308 | 0,382 |
| N0 · 16 biến | 0,35 | 0,503 | 0,361 | 0,386 |
| N1 · 21 biến | 0,35 | 0,469 | 0,297 | 0,388 |
| GFS nguyên bản | 0,50 | 0,304 | 0,207 | 0,277 |
| MOS · 4 năm | 0,35 | 0,326 | 0,164 | 0,303 |

GFS dùng quyết định xác định từ lượng mưa, thể hiện bằng xác suất 0/1; các mô hình khác dùng cutoff chọn bằng 2025. CSV cũng báo cutoff 0,5 để kiểm tra độ nhạy.

### Cảnh báo ≥50 mm/24 h — ngày 2

| Mô hình | Cutoff | POD | FAR | CSI |
| --- | --- | --- | --- | --- |
| A · 2 năm/Tweedie | 0,30 | 0,509 | 0,491 | 0,335 |
| B · 4 năm/Tweedie | 0,35 | 0,487 | 0,456 | 0,342 |
| N0 · 16 biến | 0,30 | 0,480 | 0,404 | 0,362 |
| N1 · 21 biến | 0,35 | 0,491 | 0,447 | 0,345 |
| GFS nguyên bản | 0,50 | 0,335 | 0,307 | 0,286 |
| MOS · 4 năm | 0,30 | 0,358 | 0,301 | 0,307 |

GFS dùng quyết định xác định từ lượng mưa, thể hiện bằng xác suất 0/1; các mô hình khác dùng cutoff chọn bằng 2025. CSV cũng báo cutoff 0,5 để kiểm tra độ nhạy.

### Cảnh báo ≥50 mm/24 h — ngày 3

| Mô hình | Cutoff | POD | FAR | CSI |
| --- | --- | --- | --- | --- |
| A · 2 năm/Tweedie | 0,20 | 0,527 | 0,614 | 0,285 |
| B · 4 năm/Tweedie | 0,20 | 0,591 | 0,588 | 0,319 |
| N0 · 16 biến | 0,15 | 0,614 | 0,627 | 0,303 |
| N1 · 21 biến | 0,20 | 0,593 | 0,581 | 0,323 |
| GFS nguyên bản | 0,50 | 0,156 | 0,612 | 0,130 |
| MOS · 4 năm | 0,10 | 0,654 | 0,721 | 0,245 |

GFS dùng quyết định xác định từ lượng mưa, thể hiện bằng xác suất 0/1; các mô hình khác dùng cutoff chọn bằng 2025. CSV cũng báo cutoff 0,5 để kiểm tra độ nhạy.

## Ngày khô, mưa lớn và độ chắc chắn

Ngày 1 modern 2026; Bias theo nhóm quan trắc và phần trăm tổng sai số bình phương thuộc nhóm ≥50. Các nhóm này chỉ dùng hậu kiểm, không được biết trước khi dự báo.

| Cấu hình | Bias ngày khô | Bias mưa ≥50 | % sai số bình phương từ ≥50 |
| --- | --- | --- | --- |
| A | 1,762 | -49,669 | 76,9% |
| B | 1,884 | -46,407 | 73,4% |
| C | 2,656 | -44,548 | 72,2% |
| D | 2,629 | -34,433 | 61,7% |

Ví dụ đổi từ B sang D (cùng train bốn năm, chỉ đổi loss đầu mean) ở ngày 1: L2 dự báo bớt thiếu trong nhóm mưa ≥50 nhưng báo thừa nhiều hơn trong ngày khô; RMSE chung của D vẫn cao hơn B. Vì thế không chọn loss chỉ theo một nhóm mưa hoặc một chỉ số thuận lợi. Các xác suất của B/D là giống nhau, nên phần đánh đổi này là của lượng mưa mean, không phải thay đổi cảnh báo xác suất.

Không có nhãn nào bị bỏ vì mưa quá lớn hoặc vì mô hình dự báo sai. Kiểm tra nguồn/QC không chứng nhận tuyệt đối cảm biến. Mưa lớn hiếm, các trạm và các cửa sổ trong cùng đợt mưa phụ thuộc nhau.

Bootstrap ghép khối 14 ngày, 5.000 lần; khoảng 95% đồng thời Bonferroni theo họ 12 phép A–D và họ 6 phép ablation; p bootstrap định tâm/Holm là xấp xỉ. “Đạt tiêu chí” đòi hỏi cả CI đồng thời nằm dưới 0 và Holm p<0,05. Trong 12 phép so A–D trên modern 2026, 1 phép đạt tiêu chí cải thiện thăm dò đã định; ablation có 0/6. Đây không phải xác nhận trên test chưa dùng. Xem paired_comparisons.csv cho từng hiệu ứng, CI và số ngày có dữ liệu. Hiệu chỉnh nhiều so sánh không xóa được việc đã xem năm 2026 trước khi thiết kế nghiên cứu mới.

## Ghi dự báo tương lai

Đã lấy snapshot nguồn trực tiếp, chưa coi đó là kiểm chứng dự báo. Tệp live_availability_snapshot.json ghi thời điểm và độ phủ thực tế, không dùng Last-Modified lịch sử để giả định nguồn đã có sẵn. Phiên đăng nhập hết hạn đã được làm mới riêng; không đưa thông tin đăng nhập vào báo cáo/Git.

Tiến trình theo dõi giới hạn một issue tương lai lúc 19 h Việt Nam, thử lấy dữ liệu trước issue. Chỉ ghi dự báo nếu có đủ lịch sử cùng API và hoàn tất trước issue; không dùng giờ đo sau cutoff 18 h. Máy và mạng cần còn hoạt động; nếu nguồn chậm/thiếu thì đánh dấu không phát. Tất cả A–D được ghi để kiểm tra, lựa chọn B được định trước bằng CV.

Nhận nhãn sau 72 h cộng độ trễ, lưu riêng với hash của dự báo đã phát. Một issue không đủ kết luận kỹ năng dự báo; cần theo dõi nhiều đợt mưa và cả ngày khô. Các lần hồi phát, nguồn lấy sau issue hoặc mô hình chọn bằng nhãn tương lai không được gọi là kiểm chứng dự báo trước sự kiện.

## Kiểm chứng và giới hạn

52 bài kiểm tra đạt. Đã đối chiếu độc lập 48,639 hàng đánh giá, 3,000 giá trị metric và 2,880 giá trị dự báo từ checkpoint. Thay nhãn tương lai không làm đổi dự báo. Đã kiểm tra trực tiếp bootstrap theo ngày, ngân sách 54 đầu mean và xác suất lồng nhau. Có 367 mục checksum đã khớp, tương ứng 336 tệp riêng biệt được giữ nguyên, gồm mô hình/báo cáo cũ và slide người dùng.

Không có tập kiểm định mới chưa xem cho vòng này. Năm 2026 chưa đủ năm, có thay API và chưa xác nhận tính liên tục; lịch sử trạm và độ trễ chưa được xác nhận đầy đủ. Điểm khác nhau giữa hai API có thể do mùa, độ phủ hoặc nguồn, không quy hết cho mô hình. Các phép so giữ cùng 57 trạm trong train và đánh giá, nên chưa chứng minh khả năng dự báo tại trạm chưa gặp hoặc khu vực mới. Muốn kết luận khả năng mở rộng cần kiểm định giữ riêng trạm/khu vực.

Không tuyên bố vượt nghiên cứu khác khi khác dữ liệu, kỳ mưa, ngưỡng hoặc thời hạn. Không ép dùng mô hình sâu nếu chưa có bằng chứng cần thiết; Bi-LSTM tiếp tục để sau.

## Cách dùng lại dữ liệu

Gói nội bộ mới giữ một Parquet đã ghép X/y, có cột role, fit_short, fit_long, calibration_2025 và retrospective_2026. Các cờ không phải đặc trưng mô hình. Chỉ chọn X theo danh sách N0/N1/N3 ở feature_sets.json, không đưa y_mm, role hoặc số đo tương lai vào X. Giữ station_id/issue/horizon/gauge_namespace để ghép đúng và chấm cùng mẫu. Gói không chứa checkpoint, dữ liệu nguồn thô hoặc thông tin đăng nhập.

Nguồn, quyết định và số liệu đầy đủ: protocol.json, selection.json, train_only_cv.csv, cutoffs.csv, point_metrics.csv, probability_metrics.csv, event_metrics.csv, seed_metrics.csv, paired_comparisons.csv, verification.json. PHUONG_AN.md giải thích thiết kế trước fit.
