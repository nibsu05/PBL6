# Kiểm toán khả năng dự báo thời gian thực

Đã chạy `audit_realtime_readiness.py` trên dự báo test và dữ liệu Open-Meteo Historical hiện có. Kết quả ở `availability_audit.json` là **`unverified_missing_provenance`**: bảng dự báo không ghi `issued_at`, còn bảng đầu vào không ghi `available_at`. Vì vậy chưa thể chứng minh bất kỳ cửa sổ nào đã có đủ dữ liệu khi phát hành, dù các chuỗi thời gian không bị dùng nhãn tương lai trong bước chia train/validation/test. Đây là hai phép kiểm tra khác nhau.

## Cổng kiểm tra as-of

`audit_realtime_readiness.py` nhận bảng dự báo `.parquet` hoặc `.csv` với `last_input_datetime`, `issued_at`; nhận bảng đầu vào với `datetime`, `available_at`. Các thời điểm phải có UTC offset. `available_at` của một giờ phải là thời điểm **muộn nhất mà tất cả biến cần cho hàng input đó đã có sẵn**, gồm mưa bề mặt. Không lấy giờ quan trắc hoặc giờ tải lại archive để thay thế thời điểm này. Một cửa sổ đạt khi đủ 24 giờ liên tiếp, mọi `available_at <= issued_at` và `issued_at` sớm hơn giờ hiệu lực +1.

```powershell
.\.venv\Scripts\python.exe audit_realtime_readiness.py `
  --predictions reports/prospective/issuances/forecast_YYYYMMDDTHHMMSSZ.parquet `
  --availability data/raw_data/live_surface.csv
```

Nếu nguồn cung cấp metadata as-of trung thực, script lưu từng cửa sổ trong `window_asof_checks.csv`. Trạng thái vượt cổng chỉ kiểm tra tính nhất quán của timestamp được cung cấp; xuất xứ log và thời điểm ghi thật vẫn phải được lưu. File archive hiện tại không có các cột này và được báo chưa xác minh, không tự giả định độ trễ của nhà cung cấp.

## Sổ dự báo cho giai đoạn mới

`record_surface_forecast.py` ghi sáu dự báo vào một file theo từng thời điểm phát hành; nếu cùng thời điểm đã có file, chương trình từ chối ghi đè. File nguồn cần **ít nhất 48 giờ liên tục** kết thúc ở giờ quan trắc cuối: `datetime`, `available_at`, `temperature_2m`, `relative_humidity_2m`, `surface_pressure`, `wind_speed_10m`, `wind_direction_10m`, `precipitation`. Hai cột thời gian phải có UTC offset. 48 giờ cần thiết để tạo input 24 giờ với lag mưa 24 giờ. Các hàng thiếu, đến muộn hoặc có giờ trùng đều bị từ chối. File Open-Meteo Historical cũ không được nhận làm feed vận hành.

```powershell
.\.venv\Scripts\python.exe record_surface_forecast.py `
  --input data/raw_data/live_surface.csv `
  --source-name 'Nguồn bề mặt thực tế' `
  --issued-at '<thoi-diem-phat-hanh-ISO-co-offset>' --device cuda
```

File `.json` cùng tên lưu hash của input/checkpoint, giờ phát hành và giờ chương trình thực sự ghi dự báo. 48 hàng nguồn đã dùng được lưu trong `input_snapshots/` để kiểm toán khi file feed gốc thay đổi. Cờ `captured_before_first_target` chỉ đúng khi chương trình được chạy trước giờ hiệu lực đầu tiên. Chỉ xem một giai đoạn là kiểm định vận hành sau khi vừa qua cổng as-of, vừa có cờ này, và nguồn `available_at` là log thực tế. Hiện chưa có nguồn bề mặt trực tuyến kèm metadata đó, nên **chưa có dự báo vận hành mới được ghi**.

Ngoài thời điểm sẵn có, cần xác nhận các biến bề mặt trực tuyến dùng cùng đơn vị, vị trí và quy ước giờ mưa với dữ liệu Open-Meteo Historical đã dùng để huấn luyện. Chương trình kiểm tra kiểu, thứ tự và độ đầy đủ của đặc trưng; nó không thể tự xác nhận sự tương đương vật lý giữa hai nguồn.
