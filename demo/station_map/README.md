# Web dự báo mưa tại trạm

Xem hai lần phát lại của **LightGBM B** trong danh mục 57 trạm Đà Nẵng. Bản đồ có ba cửa sổ 24 giờ, lớp lượng mưa LightGBM/GFS, lớp xác suất mưa ≥50 mm và ký hiệu trạm thiếu mẫu. Bấm vào điểm để xem biểu đồ qua ba ngày.

Sau đăng nhập, có thêm Vrain thực đo, lớp sai lệch, tải CSV và trang theo dõi. Ba lớp lượng mưa dùng chung thang màu. Lớp **Sai lệch** tính LightGBM trừ Vrain. Xanh là dự báo thiếu, cam là dự báo thừa.

## Mở web

Chạy lệnh ở thư mục gốc dự án.

```powershell
.venv\Scripts\python.exe -X utf8 demo/station_map.py
```

Mở **http://127.0.0.1:8766/** và chọn **Đăng nhập**. Lần đầu, chọn tên và mật khẩu riêng cho web. Các lần sau dùng đúng tài khoản này. Nếu thiếu tệp phát lại, chạy `.venv\Scripts\python.exe -X utf8 scripts/close_short_range.py` để tạo lại từ bản nghiên cứu đã khóa. Bản đồ nền cần kết nối mạng.

Ứng dụng hiện nghe trên máy này qua `127.0.0.1`. Tài khoản được lưu dưới dạng băm có salt. Phiên đăng nhập hết hạn sau 8 giờ hoặc khi khởi động lại máy chủ. Hồ sơ tài khoản tại `data/operational/station_map_web/` nằm ngoài Git.

## Trang theo dõi

- **Nguồn dữ liệu** hiển thị lúc kiểm tra GFS/Vrain, chu kỳ, số trường và thời điểm có số đo gần nhất. Nút **Kiểm tra nguồn** hỏi nguồn trong một lượt có giới hạn. GFS kiểm tra các chỉ mục, Vrain kiểm tra số đo của ngày hiện tại. Trang đọc lại trạng thái lưu trên máy mỗi 30 giây khi đang mở. Lượt kiểm tra này dùng phiên Vrain đã có trên máy chủ.
- **Lần phát** hiển thị bản dự báo được ghi trước giờ phát nếu có, cùng giờ ghi nhận và tình trạng đối chiếu. Trạng thái hiện tại là **Phát lại lịch sử**. Giờ phát theo thiết kế là 19h Việt Nam.
- **Đối chiếu** chấm LightGBM, GFS và MOS trên các trạm có đủ dự báo và thực đo cùng cửa sổ. Hiển thị MAE, RMSE, Bias và số trúng, bỏ sót, báo nhầm mưa ≥50 mm. Có thể mở đúng kỳ trên bản đồ hoặc tải CSV.
- **Nghiên cứu** trình bày kết quả hồi cứu 2026 theo ba hạn và phép thử nhóm biến trên kiểm định 2025 theo từng kỳ.

## Đầu ra cho giao diện

`GET /api/short-range` đọc JSON phiên bản 1 từ thư mục riêng `data/operational/gfs_short_range_closeout_2026_11_24/`. API khách chỉ trả đầu ra dự báo cho bản đồ, còn Vrain thực đo và MOS cần phiên đăng nhập. Trạng thái nguồn, bảng kiểm chứng và CSV cũng cần đăng nhập. Tệp gốc nằm ngoài Git. Nhánh cực ngắn đang chờ đầu ra của mô hình theo giờ.

## Dự báo mỗi ngày

Quy trình đã có mã ghi một lần dự báo trước 19 giờ Việt Nam. Khoảng 18h40, lấy GFS khởi tạo lúc 07h và mưa Vrain đến 18h. Kiểm tra lịch sử mưa từng trạm, chạy LightGBM đã huấn luyện và lưu ba tổng 24 giờ của các trạm đủ đầu vào. Lần phát được lưu kèm giờ nhận nguồn. Sau khi cả ba khoảng kết thúc và số đo đầy đủ, chạy bước đối chiếu với Vrain.

Ngày 24/11/2026, đã tải và giải mã đủ 19 trường GFS tại 57 trạm lúc giữa trưa trong khoảng 10 giây. Hai đường lấy Vrain đã dùng trong dự án trả HTTP 404 khi hỏi dữ liệu 23–24/11. Lỗi vẫn xảy ra sau lần làm mới phiên đăng nhập. Do thiếu mưa đầu vào, lần thử dừng ở bước nguồn và web đang dùng bản phát lại.

Sau khi Vrain hoạt động ổn định, thử vài lần phát đúng giờ bằng [trình ghi dự báo](../../scripts/record_gfs_window.py) và đo thời gian nhận nguồn. Khi nối lên web, giữ ngày phát và giờ hiệu lực của bản đã lưu. Ngày nguồn lỗi, hiển thị bản gần nhất với ngày phát của chính nó. GFS NOAA có chu kỳ 00, 06, 12 và 18 UTC. Thiết kế này sử dụng chu kỳ 00 UTC. [Sản phẩm GFS của NOAA](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast).

## Tham khảo giao diện

- Chọn kỳ tích lũy và đọc đơn vị trên bản đồ. [Bản đồ mưa của WPC](https://www.wpc.ncep.noaa.gov/qpf/qpf2body.html).
- Đổi lớp và thời gian trong cùng bản đồ. [Bản đồ Apple Weather](https://support.apple.com/guide/iphone/view-weather-maps-iph0960651f5/ios).
- Biểu đồ dự báo theo vị trí và khung thời gian. [Biểu đồ dự báo NWS](https://www.weather.gov/wrn/hourly-weather-graph).

[Kết quả và giới hạn của nghiên cứu](../../reports/gfs_short_range_closeout_2026_11_24/KET_LUAN_NGAN_HAN.md) · [Leaflet](https://leafletjs.com/examples-v1/quick-start/) · [OpenStreetMap](https://www.openstreetmap.org/copyright).
