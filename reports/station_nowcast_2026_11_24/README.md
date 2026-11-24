# Dự báo mưa 1–6 giờ tại trạm

Đã huấn luyện và kiểm định trên **79/86 vị trí trong danh mục Vrain**. Phạm vi bao gồm cả 57 trạm của nhánh ngày và thêm 22 trạm. Một mô hình Bi-LSTM học chung giữa các trạm, giữ sáu nhãn mưa riêng cho mỗi thời điểm phát. Gói thử nghiệm trước của nhóm dùng ba trạm và ba giờ đích. Bản này đối chiếu thêm trên đúng ba trạm đó trong các bảng `pilot3`, đồng thời kiểm định toàn bộ tập trạm đã học.

## Dữ liệu và huấn luyện

| Vai trò | Thời gian | Mẫu trạm–giờ đủ điều kiện |
| --- | --- | ---: |
| Huấn luyện | 2021–2022 | 1.032.811 |
| Chọn epoch, số cây và phương án phát lại | 2023 | 676.870 |
| Phát triển | 2024 | 680.282 |
| Kiểm định sau khóa | 2025 | 679.461 |

- Mỗi đầu vào dùng 24 giờ kết thúc tại lúc phát. Đầu ra gồm lượng mưa tại cùng trạm trong từng khoảng 1 giờ từ hạn 1 đến 6, đơn vị mm. Ví dụ, phát 19h thì giờ 1 là 19h–20h, giờ 6 là 00h–01h hôm sau theo giờ Việt Nam.
- Mẫu dự báo cần lịch sử 24 giờ hoàn chỉnh. Để chấm, cần thêm sáu quan trắc cùng nguồn Vrain ở giờ đích. Thí nghiệm dùng chung tập đủ khí tượng lịch sử để so các mô hình. Dữ liệu khí tượng ERA5 được ghép theo tọa độ từng trạm. Không điền số 0 vào mưa thiếu.
- **R (3 biến)** gồm mưa trạm, chênh mưa so giờ trước trong cửa sổ và tháng. **E0 (11 biến)** thêm nhiệt độ, tốc độ gió gần mặt đất, độ ẩm, áp suất và bốn chênh lệch tương ứng. **E2 (13 biến)** thêm đúng hai thành phần gió ở 850 hPa. Nhãn E0 và E2 ở đây bám theo thí nghiệm Bi-LSTM ba trạm. Cách chia nhóm của bộ ERA5 gốc rộng hơn.
- Bi-LSTM có một lớp hai chiều, 64 nút mỗi chiều và mã trạm học được. Hai chiều đều đọc 24 giờ đã xảy ra. Dùng MSE trên log(1 + mm), chuẩn hóa chỉ từ train và chọn epoch theo RMSE đơn vị mm năm 2023. Chạy ba seed 17, 29, 43 cho mỗi cấu hình, rồi lấy trung bình ba dự báo đã đổi về mm. Tổng thời gian trong các epoch Bi-LSTM khoảng 5,9 phút trên RTX 4060 Laptop, chưa tính bước dựng mẫu và chấm.
- Mốc **Giữ mưa** dùng lượng đo gần nhất cho cả sáu giờ. Mốc **0 mm** kiểm tra lợi ích khi số giờ khô chiếm nhiều. **LightGBM R** dùng cùng lịch sử mưa và tháng, thêm các tổng/cực đại tính từ chính 24 giờ đó. Mô hình cây dùng L2 theo mm và một bộ cây mỗi hạn dùng chung các trạm.

## Kiểm định 2025

RMSE tính theo mm trong từng khoảng một giờ, càng thấp càng tốt.

| Giờ đích | 0 mm | Giữ mưa | LightGBM R | Bi-LSTM R | Bi-LSTM E0 | Bi-LSTM E2 |
| --- | --- | --- | --- | --- | --- | --- |
| Giờ 1 | 2,738 | 2,559 | **2,151** | 2,233 | 2,320 | 2,345 |
| Giờ 2 | 2,738 | 2,955 | **2,347** | 2,418 | 2,459 | 2,483 |
| Giờ 3 | 2,737 | 3,048 | **2,411** | 2,485 | 2,509 | 2,529 |
| Giờ 4 | 2,737 | 3,160 | **2,469** | 2,525 | 2,542 | 2,562 |
| Giờ 5 | 2,735 | 3,241 | **2,504** | 2,558 | 2,564 | 2,576 |
| Giờ 6 | 2,736 | 3,282 | **2,534** | 2,580 | 2,579 | 2,590 |

CSI phát hiện mưa từ 1 mm trong giờ đích. CSI là số báo đúng chia cho tổng số báo đúng, bỏ sót và báo nhầm.

| Giờ đích | 0 mm | Giữ mưa | LightGBM R | Bi-LSTM R | Bi-LSTM E0 | Bi-LSTM E2 |
| --- | --- | --- | --- | --- | --- | --- |
| Giờ 1 | 0,000 | 0,491 | **0,495** | 0,474 | 0,440 | 0,419 |
| Giờ 2 | 0,000 | 0,388 | **0,398** | 0,374 | 0,361 | 0,352 |
| Giờ 3 | 0,000 | 0,344 | **0,359** | 0,329 | 0,331 | 0,320 |
| Giờ 4 | 0,000 | 0,313 | **0,331** | 0,302 | 0,307 | 0,295 |
| Giờ 5 | 0,000 | 0,289 | **0,311** | 0,276 | 0,288 | 0,281 |
| Giờ 6 | 0,000 | 0,271 | **0,295** | 0,257 | 0,272 | 0,264 |

**Mốc hữu ích nhất để phát lại** là LightGBM R, đã chọn bằng RMSE năm 2023. Năm 2025, LightGBM R giảm RMSE giờ 6 khoảng **22,8%** so với giữ nguyên mưa. Số trạm giảm RMSE ở các hạn 1–6 lần lượt là **79, 79, 79, 79, 79, 79** trên 79.

**Giá trị của gió 850 hPa.** Chênh CSI giờ 6 của E2 so với E0 là 0,0131 trên 2024 và **-0,0078** trên 2025. Khoảng tin cậy 95% ghép theo khối 7 ngày [-0,0386, 0,0182], khối 14 ngày [-0,0406, 0,0190]. Cả hai khoảng còn chứa 0, vì vậy chưa xác nhận lợi ích của riêng nhóm gió.

**MAE cho một cách đọc khác.** Ở giờ 6, dự báo 0 mm có MAE 0,473 mm, thấp hơn LightGBM R (0,659 mm). Các giờ khô xuất hiện thường xuyên, còn RMSE phạt mạnh lỗi lớn. Vì vậy tiêu chí chọn phương án phát lại được đặt theo RMSE từ năm 2023.

**Giờ mưa mạnh vẫn khó.** Trong 17.034 mẫu có mưa ít nhất 5 mm ở giờ 6, POD của LightGBM R là 0,086 và FAR là 0,602. Mốc giữ nguyên mưa có POD 0,274 và FAR 0,726. POD là tỷ lệ số giờ mưa thực tế được phát hiện. FAR là tỷ lệ báo nhầm trong những giờ dự báo có sự kiện. Ngưỡng 1 và 5 mm là ngưỡng thí nghiệm theo giờ.

## Phạm vi và trình diễn

- 7 vị trí chưa có cửa sổ huấn luyện đủ điều kiện trong 2021–2022. Trong tập đã học, trạm ít mẫu nhất có 3.205 mẫu. Tập kiểm định 2025 là các thời điểm mới ở những trạm đã học. Đánh giá khả năng chuyển sang trạm mới cần giữ riêng trạm trong thiết kế thí nghiệm.
- Thí nghiệm chứng minh có thể huấn luyện và chấm trên mạng trạm lớn bằng một Bi-LSTM dùng chung. Để đo riêng lợi ích của huấn luyện chung so với huấn luyện mỗi trạm một mô hình, cần thêm đối chứng cùng kiến trúc, cửa sổ và tập mẫu.
- Web cục bộ có trang **1–6 giờ** với bảy lượt phát lại từ 04 đến 10/11/2026. Mỗi lượt chọn mốc 19h để trình diễn và có 78/79 trạm có số. Màu là lượng tại trạm theo từng giờ đích. Đăng nhập để xem số đo Vrain đã ghi nhận. Năm 2026 dùng kênh Vrain khác giai đoạn huấn luyện, nên bản phát lại không xác nhận hiệu năng vận hành.
- Phương án chỉ dùng Vrain và lịch có thể chạy với 24 giờ quan trắc đạt kiểm tra. Để phát theo giờ thực tế, cần xác nhận nguồn cung cấp kịp giờ, ghi đầu vào và dự báo ngay lúc phát, rồi đối chiếu khi đủ nhãn. ERA5T có độ trễ khoảng năm ngày theo [tài liệu ECMWF](https://confluence.ecmwf.int/pages/viewpage.action?pageId=301966210).

## Kiểm chứng và tái chạy

Đã đối chiếu toàn bộ khóa trạm–giờ và sáu nhãn của 1.359.743 mẫu. Kiểm lại điểm gộp từ Parquet và nạp lại các trọng số để đối chiếu dự báo trên mẫu lấy ở mọi trạm. Bảng theo trạm, dự báo theo giờ, scaler, trọng số và bản ghi khóa nằm trong thư mục nội bộ `data/operational/station_nowcast_2026_11_24/`.

```powershell
.venv\Scripts\python.exe -X utf8 scripts/train_station_nowcast.py
.venv\Scripts\python.exe -X utf8 scripts/evaluate_station_nowcast.py
.venv\Scripts\python.exe -X utf8 scripts/prepare_station_nowcast_replay.py
.venv\Scripts\python.exe -X utf8 scripts/verify_station_nowcast.py
.venv\Scripts\python.exe -X utf8 demo/station_map.py
```

Mở trang [1–6 giờ](http://127.0.0.1:8766/cuc-ngan). Dữ liệu đầu vào lấy từ [bộ ghép Vrain–ERA5 ngày 17/11](../station_hourly_era5_2026_11_17/README.md). Giao thức, điểm gộp, độ nhạy theo seed và các khoảng tin cậy đi cùng báo cáo.
