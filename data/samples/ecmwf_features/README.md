# Mẫu đặc trưng khí tượng bổ sung

## Đã tải ERA5 CIN CAPE TCWV

- Một mốc: **30/08/2024 00:00 UTC = 30/08/2024 07:00 UTC+7**.
- Vị trí yêu cầu: 16,0544°B, 108,2022°Đ (Đà Nẵng).
- Ô lưới gần nhất: **16,00°B, 108,25°Đ**, cách khoảng **7,92 km**.
- CIN = **443,8126220703125 J/kg**.
- CAPE = **1139,5 J/kg**.
- TCWV = **51,634613037109375 kg/m²**.
- Ba giá trị đều hữu hạn. TCWV chỉ gồm hơi nước, không đổi tên TCW thành TCWV.

Tệp gốc: `era5_cin_cape_tcwv_20240830_00.nc`.
Tệp một hàng ba đặc trưng: `sample_era5_one_timestamp.csv`.
Chi tiết mỗi biến: `sample_cin_cape_tcwv_era5.csv` và `.json`.
Yêu cầu API, request ID và SHA-256: `era5_request.json`.

## Đã tải SM20 S2S

Đã tải thành công biến **soil_moisture_top_20_cm** (paramId 228086),
trung tâm ECMWF, control forecast, ngày khởi tạo **29/08/2024 00 UTC**,
trung bình hạn **0–24 giờ**. Các bước điều khoản ECDS và giấy phép S2S đã được
người dùng hoàn tất; yêu cầu tải đã được xử lý thành công.

- Giá trị gốc: **502,2227478027344 kg/m³**, giữ nguyên đơn vị GRIB.
- Khoảng trung bình: 29/08/2024 00 UTC đến 30/08/2024 00 UTC
  (29/08 07:00 đến 30/08 07:00 theo UTC+7).
- Lưới **1,5° × 1,5°**. Ô gần Đà Nẵng nhất **16,5°B, 108°Đ** bị thiếu giá trị.
- Ô đất có giá trị gần nhất trong miền tải: **15°B, 108°Đ**, cách vị trí yêu cầu
  **119,23 km**. Đây là mẫu đại diện vùng từ S2S, chưa phù hợp để xem như số đo
  độ ẩm đất tại chính Đà Nẵng.
- Tệp gốc: `s2s_ecmwf_sm20_init_20240829_00_lead_0_24.grib`.
- Tệp trích xuất: `sample_sm20_s2s.csv` và `sample_sm20_s2s.json`.
- Yêu cầu API, request ID, thời điểm tải và SHA-256: `s2s_request.json`.

Để trích xuất lại từ mẫu đã lưu, chạy tại thư mục gốc dự án:

```powershell
.venv\Scripts\python.exe collect_ecmwf_feature_samples.py --kind s2s --wait
```

SM20 là độ ẩm **lớp đất 0–20 cm**, không phải riêng tại độ sâu 20 cm.
S2S cung cấp trung bình ngày trên lưới thô khoảng 1,5°; script ghi cả ô gần
nhất và ô đất có giá trị được chọn, khoảng cách, đơn vị gốc và hạn dự báo.
Không coi trung bình 0–24 giờ là giá trị tức thời ERA5 ở cuối khoảng đó.

Mẫu được lưu tách khỏi dữ liệu pipeline chính; chưa hợp nhất vào train và
chưa huấn luyện lại. Một mẫu dùng kiểm tra khả năng tải, tên biến, đơn vị và
tọa độ, không đủ để kết luận lợi ích dự báo của đặc trưng.

## Nguồn

- [SM20 S2S và định nghĩa độ sâu](https://confluence.ecmwf.int/spaces/S2S/pages/27399317/Soil%2Bmoisture%2Btop%2B20%2Bcm)
- [S2S forecasts trên ECDS](https://ecds.ecmwf.int/datasets/s2s-forecasts?tab=download)
- [Hướng dẫn chuyển S2S sang ECDS và tái sử dụng token CDS](https://confluence.ecmwf.int/plugins/viewsource/viewpagesrc.action?pageId=650253951)
- [ERA5 single levels](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=documentation)
