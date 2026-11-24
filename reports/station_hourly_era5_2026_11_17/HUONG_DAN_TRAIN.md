# Đọc bộ giờ mới bằng loader

Từ thư mục gốc repo; dùng loader mới `src/hourly_station_update.py` và loader nền
`src/station_forecast_data.py`. Loader V1 cũ vẫn giữ chặn đọc năm2025; dùng lớp mới
để chọn rõ reserved2025/external2026 của bản cập nhật được người dùng cho phép.
Không lọc bỏ hàng thời gian trước khi đưa vào loader.

```python
from src.hourly_station_update import HourlyStationData

path = "data/processed/station_hourly_era5_2026_11_17/PBL6_TRAM_GIO_ERA5_2021_2026.parquet"
train = HourlyStationData(path, "train", "E7", use_rain=True,
                            stations=["ST001"])
sample = train[0]
print(sample["x"].shape)  # (24, 45)
print(sample["y"].shape)  # (6,)
```

`stations` là mã trong file, chọn từ lịch sử train. Bỏ tham số để lấy mọi
trạm đủ điều kiện; có thể tốn RAM vì loader đọc toàn bộ các hàng của trạm.
Đổi split sang cal/dev/reserved2025/external2026 để đọc riêng vai trò.
Không lấy các tập để dành làm train chỉ vì chúng đã có trong file.
Các E dùng cùng `sample_ready_r1`, chỉ thay danh sách đầu vào.

Muốn xem bảng: `pd.read_parquet(path, filters=[("station_id", "=", "ST001")])`.
`sample_complete` khác `sample_ready_r1`: cột sau thêm điều kiện trạm có train.
Đọc `MO_TA_DU_LIEU.docx` trước khi chia lại năm hoặc dùng số mưa hai API.
File mới chỉ chứa resolution 1h; nhánh ngày GFS dùng file riêng của gói 16/11.
