# Dùng bộ trạm v1 để huấn luyện

Hai file gửi nhóm: `PBL6_TRAM_GIO_NGAY_V1.parquet` và `MO_TA_DU_LIEU.docx`. Parquet nằm riêng tại `data/processed/station_v1/`, ngoài Git. Tài liệu và mã đọc ở repo này. Dùng pandas, NumPy và PyArrow theo môi trường dự án; không cần đăng nhập Vrain để đọc file đã ghép.

## Bắt đầu

Chạy từ thư mục gốc repo. Loader chỉ chọn các cột đầu vào được cho phép; không đưa nhãn tương lai hoặc thông tin QC vào X.

```python
from src.station_forecast_data import StationForecastData

path = "data/processed/station_v1/PBL6_TRAM_GIO_NGAY_V1.parquet"
train = StationForecastData(path, "24h", "train", "E7", use_rain=True)
cal = StationForecastData(path, "24h", "cal", "E7", use_rain=True)
dev = StationForecastData(path, "24h", "dev", "E7", use_rain=True)
sample = train[0]
print(sample["x"].shape, sample["y"].shape)  # (7, 43), (3,)
```

Bi-LSTM đổi `"24h"` thành `"1h"`: đầu vào `(24,45)`, nhãn `(6,)` với E7+R. Khi pilot, dùng tham số `stations=[...]` với các mã trong file để giảm RAM/thời gian; chọn dựa trên lịch sử train, không dựa trên điểm dev. Mỗi kiến trúc dùng một mô hình chung; nhiều trạm là nhiều mẫu trong batch.

Kết quả loader:

| Khóa | Ý nghĩa |
| --- | --- |
| `x` | Lịch sử đúng một trạm, đơn vị vật lý, chưa chuẩn hóa |
| `y` | Sáu lượng mưa giờ riêng hoặc ba tổng24hriêng tương lai, mm |
| `static` | Hai tọa độ latitude/longitude, không phải cao độ |
| `station_code` | Số nguyên0–85 theo mã registry ổn định; embedding86phần tử nếu dùng |
| `station_id` | Mã chuẩn STxxx để phân tích từng trạm |
| `issue_time_utc_ns` | Cuối khoảng quan trắc cuối của lịch sử, nanosecond UTC |
| `future_calendar` | Lịch biết trước: sáu bước×4kênh giờ, hoặc ba bước×2kênh ngày |

Với TFT/Informer, decoder chỉ nhận lịch tương lai và static đã biết; không lấy ERA5 hoặc mưa của kỳ đích. LightGBM làm phẳng chính `x` này và thêm static nếu dùng; cả ba mô hình phải dùng cùng các mẫu và chân trời. Bi-LSTM hai chiều chỉ chạy trong cửa sổ quá khứ, không phải đọc chuỗi mục tiêu tương lai.

## Mask, R và so sánh E0–E7

`feature_names` của loader trả đúng danh sách biến cho thí nghiệm. E0=B; E1=BA; E2=BM; E3=BC; E4=BAM; E5=BAC; E6=BMC; E7=BAMC. E7 có44kênh giờ hoặc42kênh ngày; `use_rain=True` thêm một cột mưa quá khứ.

Mặc định mọi E và cả `use_rain=False/True` dùng chung `sample_ready_r1`, giúp so sánh trên cùng các mẫu. `paired_r=False, use_rain=False` là phân tích phụ với tập weather-only rộng hơn, không đưa vào bảng R0/R1 chính. Static/ID cũng phải giữ cùng cách dùng giữa các E và mô hình.

**Không dùng `df.select_dtypes(...)` để lấy toàn bộ cột số làm X.** File chứa cả y tương lai, QC và tọa độ. Không lấy `rain_raw_mm` thay `rain_mm` vì số gốc có thể đã bị QC loại. Không xóa các hàng NaN/không ready trước khi cắt chuỗi: làm vậy có thể nối ngày khác nhau thành lịch sử liên tục. Loader giữ toàn bộ trục thời gian rồi chọn chỉ số issue hợp lệ.

Hai độ phân giải dùng chung schema: hàng `1h` để trống các cột `y_d*`; hàng `24h` để trống `y_h*` và sin/cos giờ. Đây là cột không áp dụng, không phải lỗi ghép. Không gọi `df.dropna()` trên toàn bộ cột; tính đầy đủ theo đúng danh sách X/y của từng nhánh như loader.

## Thời gian và chia dữ liệu

Mưa Vrain ghi10:00 là tổng09:00–10:00 giờ Việt Nam. Trong hàng giờ, `period_start_utc=02:00`, `period_end_utc=03:00`; trạng thái ERA5 lấy02:00UTC. `period_end_vn` hiển thị10:00+07. Các cột khí tượng không chứa ERA5 kỳ đích. Không khẳng định ERA5 có sẵn theo thời gian thực tại issue.

Ngày là19:00 hôm trước→19:00 hôm sau, không phải00–24. Mưa ngày yêu cầu đủ24giờ hợp lệ; khí tượng là trung bình24trạng thái đầu giờ, bất kỳ nút/giờ cần thiết thiếu thì giữ NaN. Ba nhãn ngày là ba tổng24h riêng, không phải tổng tích lũy0–72h. Lịch dùng mốc cuối khoảng theo giờ Việt Nam; sin/cos ngày có mẫu số365,25, hai kênh giờ có mẫu số24.

Theo giờ Việt Nam: train2021–2022, cal2023, dev2024. Toàn bộ khoảng nhãn phải nằm trong split; những issue có nhãn băng ranh bị loại. Lịch sử có thể lấy quá khứ trước đầu split, như dự báo cuốn chiếu thực tế. Không random trộn các cửa sổ của cùng trận mưa. Tập2024 là đánh giá phát triển; nếu tiếp tục dùng để quyết định, phải ghi rõ vai trò đó.

Fit scaler, mã hóa thống kê, reference/climatology chỉ trên train; các thời điểm lịch sử lặp lại trong nhiều cửa sổ nên cân nhắc fit trên các hàng train duy nhất, hoặc công bố rõ cách tính. Chọn cấu hình/earlystop/tau/calibration trên cal. Giữ2025 kín cho kiểm định cuối sau khi khóa protocol; không dùng2026 để tuning rồi gọi2025 là test tương lai.

## QC và mức tin cậy

`rain_qc_code`:0=số không âm qua kiểm tra hiện có;1=thiếu giờ hoặc ngày không đủ;2=station-day lệch tổng. Mưa gốc giữ ở `rain_raw_mm`; mưa dùng train đã mask ở `rain_mm`. Nguồn dấu `-` vẫn là NaN, số0 giữ đúng0. Không lấp nhãn bằng ERA5/CPC/GSMaP. CIN không có LFC được mã500và has_lfc theo phép biến đổi nguồn; các NaN khí tượng khác không được tự động điền.

ERA5 nội suy trực tiếp tại trạm từ bốn nút0,25°; yêu cầu mọi góc có trọng số dương hợp lệ, không tái chuẩn hóa bỏ nút thiếu. Một số biến context/SST/chênháp là thông tin vùng có chủ đích. Đây không phải độ phân giải thật ở mức từng trạm và không chứng minh địa hình nhỏ đã được mô tả đầy đủ. Tọa độ dùng metadata hiện có, chưa xác nhận mọi trạm không di chuyển trong lịch sử.

Các số mẫu/số trạm và SHA256 ở `dataset_summary.json`; bằng chứng kiểm tra ở `verification.json`. Bản này có79trạm có train, nhưng24trạm có dưới180mẫu ngày train; nên pilot trên nhóm có lịch sử tốt và công bố phạm vi rõ. Đánh giá theo từng trạm, horizon, mùa; báo macro giữa trạm kèm micro, bootstrap theo khối thời gian giữ cùng đợt mưa. Số cửa sổ lớn không đồng nghĩa có nhiều mùa mưa độc lập.

## Tái tạo và kiểm tra

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/build_station_forecast_data.py
.\.venv\Scripts\python.exe -X utf8 scripts/validate_station_forecast_data.py
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_station_forecast_data.py -v
```

Builder đọc dữ liệu private có sẵn trong workspace, không mở Vrain2025, không gọi mạng và không huấn luyện mô hình. `--reuse-weather` chỉ tái dùng cache nếu chữ ký đầu vào và checksum khớp. Không commit Parquet, registry/tọa độ từng trạm, source hoặc credential lên GitHub công khai.
