# Bản đồ dự báo mưa tại trạm

Xem hai lần phát lịch sử của **LightGBM B** ở danh mục 57 trạm Đà Nẵng. Bản đồ dùng các điểm tô màu trên nền OpenStreetMap. Có ba cửa sổ 24 giờ riêng, số mưa thực đo để đối chiếu và lớp ký hiệu thiếu mẫu. Dải màu là các khoảng lượng mưa để đọc kết quả.

Chuyển giữa LightGBM, GFS và Vrain thực đo để so cùng ngày trên cùng thang màu. Lớp **Sai lệch** tính LightGBM trừ Vrain. Xanh là dự báo thiếu, cam là dự báo thừa. Bấm một trạm để xem ba nguồn cạnh nhau trong biểu đồ ba ngày. Ngày đang chọn trên bản đồ được làm nổi trong biểu đồ.

Tại thư mục gốc dự án, tạo dữ liệu phát lại từ bản nghiên cứu đã khóa rồi mở trình xem.

```powershell
.venv\Scripts\python.exe -X utf8 scripts/close_short_range.py
.venv\Scripts\python.exe -X utf8 demo/station_map.py
```

Mở **http://127.0.0.1:8766/**. Trình xem lấy mã Leaflet và bản đồ nền qua mạng. Cửa sổ giờ Việt Nam bắt đầu vào 19 giờ ngày phát. Trạng thái `Phát lại lịch sử` áp dụng cho toàn bộ ví dụ.

## Đầu ra cho giao diện

`GET /api/short-range` trả JSON phiên bản 1 được xuất trong thư mục riêng `data/operational/gfs_short_range_closeout_2026_11_24/`. Tệp chứa danh mục tọa độ, giờ khởi tạo GFS, giờ phát, các cửa sổ dự báo và các giá trị mm/xác suất theo trạm. Giá trị thực đo được ghép sau suy luận để đối chiếu. Tệp chỉ phục vụ trên loopback và nằm ngoài Git. Điều hướng cực ngắn đang chờ đầu ra của mô hình theo giờ.

## Dự báo mỗi ngày

Quy trình đã có mã ghi một lần dự báo trước 19 giờ Việt Nam. Khoảng 18h40, lấy GFS khởi tạo lúc 07h và mưa Vrain đến 18h. Kiểm tra lịch sử mưa từng trạm, chạy LightGBM đã huấn luyện và lưu ba tổng 24 giờ của các trạm đủ đầu vào. Lần phát được lưu kèm giờ nhận nguồn. Sau khi cả ba khoảng kết thúc và số đo đầy đủ, chạy bước đối chiếu với Vrain.

Ngày 24/11/2026, đã tải và giải mã đủ 19 trường GFS tại 57 trạm lúc giữa trưa trong khoảng 10 giây. Hai đường lấy Vrain đã dùng trong dự án trả HTTP 404 khi hỏi dữ liệu 23–24/11. Lỗi vẫn xảy ra sau lần làm mới phiên đăng nhập. Do thiếu mưa đầu vào, lần thử dừng ở bước nguồn và web đang dùng bản phát lại.

Sau khi Vrain hoạt động ổn định, thử vài lần phát đúng giờ bằng [trình ghi dự báo](../../scripts/record_gfs_window.py) và đo thời gian nhận nguồn. Khi nối lên web, giữ ngày phát và giờ hiệu lực của bản đã lưu. Ngày nguồn lỗi, hiển thị bản gần nhất với ngày phát của chính nó. GFS NOAA có chu kỳ 00, 06, 12 và 18 UTC. Thiết kế này sử dụng chu kỳ 00 UTC. [Sản phẩm GFS của NOAA](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast).

[Kết quả và giới hạn của nghiên cứu](../../reports/gfs_short_range_closeout_2026_11_24/KET_LUAN_NGAN_HAN.md) · [Cách tổ chức bản đồ mưa của WPC](https://www.wpc.ncep.noaa.gov/qpf/qpf2body.html) · [Leaflet](https://leafletjs.com/examples-v1/quick-start/) · [OpenStreetMap](https://www.openstreetmap.org/copyright).
