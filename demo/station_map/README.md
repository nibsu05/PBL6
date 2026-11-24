# Bản đồ dự báo mưa tại trạm

Xem hai lần phát lịch sử của **LightGBM B** ở danh mục 57 trạm Đà Nẵng. Bản đồ dùng các điểm tô màu trên nền OpenStreetMap. Có ba cửa sổ 24 giờ riêng, số mưa thực đo để đối chiếu và lớp ký hiệu thiếu mẫu. Dải màu là các khoảng lượng mưa để đọc kết quả.

Tại thư mục gốc dự án, tạo dữ liệu phát lại từ bản nghiên cứu đã khóa rồi mở trình xem.

```powershell
.venv\Scripts\python.exe -X utf8 scripts/close_short_range.py
.venv\Scripts\python.exe -X utf8 demo/station_map.py
```

Mở **http://127.0.0.1:8766/**. Trình xem lấy mã Leaflet và bản đồ nền qua mạng. Cửa sổ giờ Việt Nam bắt đầu vào 19 giờ ngày phát. Trạng thái `Phát lại lịch sử` áp dụng cho toàn bộ ví dụ.

## Đầu ra cho giao diện

`GET /api/short-range` trả JSON phiên bản 1 được xuất trong thư mục riêng `data/operational/gfs_short_range_closeout_2026_11_24/`. Tệp chứa danh mục tọa độ, giờ khởi tạo GFS, giờ phát, các cửa sổ dự báo và các giá trị mm/xác suất theo trạm. Giá trị thực đo được ghép sau suy luận để đối chiếu. Tệp chỉ phục vụ trên loopback và nằm ngoài Git. Điều hướng cực ngắn đang chờ đầu ra của mô hình theo giờ.

[Kết quả và giới hạn của nghiên cứu](../../reports/gfs_short_range_closeout_2026_11_24/KET_LUAN_NGAN_HAN.md) · [Cách tổ chức bản đồ mưa của WPC](https://www.wpc.ncep.noaa.gov/qpf/qpf2body.html) · [Leaflet](https://leafletjs.com/examples-v1/quick-start/) · [OpenStreetMap](https://www.openstreetmap.org/copyright).
