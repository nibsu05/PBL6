# Web dự báo mưa tại trạm

Bản đồ **LightGBM B** mở mặc định theo xã, phường, với bảng **Nơi dự kiến có mưa** ở bên phải. Trên điện thoại, bấm **Nơi có mưa** để mở bảng trượt từ dưới. Dùng thanh ngày để chọn một trong ba khoảng 24 giờ. Có thể tìm theo tên, lọc nơi từ 10 mm hoặc xem các khu vực chưa có số. Bấm tên để xem khu vực và các trạm bên trong. Mở **Công cụ → Theo trạm** để xem mọi điểm và biểu đồ ba ngày.

Màu khu vực dùng lượng cao nhất trong các trạm hợp lệ nằm trong ranh giới. Bảng xếp theo lượng LightGBM cao nhất và lọc **Có mưa** khi có ít nhất một trạm đạt 1 mm/24 giờ. Cột Trạm cho biết số có dự báo trên tổng số trạm thuộc khu vực. Vùng xám chưa có số cho lớp đang xem. Lớp xác suất lấy giá trị cao nhất tại trạm, còn lớp sai lệch lấy giá trị tại trạm có độ lệch tuyệt đối lớn nhất, giữ dấu. Các đại lượng này tóm tắt kết quả tại các điểm trạm trong ranh giới.

Sau đăng nhập, có thêm Vrain thực đo, lớp sai lệch, tải CSV và trang theo dõi. Ba lớp lượng mưa dùng chung thang màu. Lớp **Sai lệch** tính LightGBM trừ Vrain. Xanh là dự báo thiếu, cam là dự báo thừa. Từ danh sách trạm có sai lệch lớn nhất có thể mở đúng lượt, ngày và trạm trên bản đồ.

## Mở web

Chạy lệnh ở thư mục gốc dự án.

```powershell
.venv\Scripts\python.exe -X utf8 demo/station_map.py
```

Mở **http://127.0.0.1:8766/** và chọn **Đăng nhập**. Lần đầu, chọn tên và mật khẩu riêng cho web. Các lần sau dùng đúng tài khoản này. Nếu thiếu tệp phát lại, chạy `.venv\Scripts\python.exe -X utf8 scripts/close_short_range.py` để tạo lại từ bản nghiên cứu đã khóa. Bản đồ nền cần kết nối mạng.

Ứng dụng hiện nghe trên máy này qua `127.0.0.1`. Tài khoản được lưu dưới dạng băm có salt. Phiên đăng nhập hết hạn sau 8 giờ hoặc khi khởi động lại máy chủ. Hồ sơ tài khoản tại `data/operational/station_map_web/` nằm ngoài Git.

### Ranh giới tham chiếu

Lấy tệp hình học trên máy mới bằng `.venv\Scripts\python.exe -X utf8 scripts/prepare_station_map_areas.py`. Tệp `data/operational/station_map_areas/wards-48.geojson` được phục vụ qua `/api/areas` và lưu cục bộ. Khi tệp thiếu, web mở theo trạm.

Nguồn ranh giới tham chiếu là tinhthanhpho.com, bản 2026.10.8 theo đơn vị cấp xã hiện hành. Kiểm tra 94 vùng, ghép đủ 57 trạm vào 40 xã/phường theo phép chứa điểm. Trong 40 nơi có trạm, 28 nơi chỉ có một trạm. Không gán trạm sang khu vực gần nhất. Đặc khu Hoàng Sa có trong bộ ranh giới và nằm ngoài khung nhìn mặc định vì không có trạm trong bộ dự báo. [Tệp nguồn](https://www.tinhthanhpho.com/data/wards-48.geojson) · [Giấy phép CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Trang theo dõi

- **Cập nhật hằng ngày** hiển thị lịch đã đăng ký trên máy, kết quả của lần chạy gần nhất và trạng thái GFS/cả hai kênh Vrain. Nút **Kiểm tra nguồn** hỏi nguồn trong một lượt có giới hạn. GFS kiểm tra chỉ mục, Vrain kiểm tra số đo của ngày hiện tại. Trang đọc lại trạng thái lưu trên máy mỗi 30 giây khi đang mở.
- **Lần phát** hiển thị bản dự báo được ghi trước giờ phát nếu có, cùng giờ ghi nhận và tình trạng đối chiếu. Mỗi bản hiện đúng ngày đã phát. Khi thiếu lượt trực tiếp, bản đồ mở **Phát lại lịch sử**. Giờ phát theo thiết kế là 19h Việt Nam.
- **Đối chiếu** chấm LightGBM, GFS và MOS trên các trạm có đủ dự báo và thực đo cùng cửa sổ. Hiển thị MAE, RMSE, Bias và số trúng, bỏ sót, báo nhầm mưa ≥50 mm. Có thể mở đúng kỳ trên bản đồ hoặc tải CSV.
- **Nghiên cứu** trình bày RMSE hồi cứu 2026, kết quả nhóm biến trên kiểm định 2025 và MAE nhóm thực đo ≥50 mm của thử nghiệm điều chỉnh có điều kiện.

## Đầu ra cho giao diện

`GET /api/short-range` ghép các lượt dự báo trực tiếp đã qua kiểm tra với hai bản phát lại lưu nội bộ. Bản đồ và bảng đối chiếu kiểm tra đầu ra mới mỗi 90 giây khi đang mở. Nếu đã chọn một lượt thì vẫn giữ đúng lượt đó. API khách chỉ trả đầu ra dự báo cho bản đồ. Vrain thực đo, MOS, trạng thái nguồn, bảng kiểm chứng và CSV cần phiên đăng nhập. Tệp dữ liệu và kết quả từng trạm nằm ngoài Git. Nhánh cực ngắn đang chờ đầu ra của mô hình theo giờ.

## Dự báo mỗi ngày

Tác vụ **PBL6-DailyRainfall** trong Windows Task Scheduler chạy lúc 18h40 và 20h05 giờ Việt Nam khi máy hoạt động và tài khoản Windows còn đăng nhập. Tác vụ chạy độc lập với trình duyệt. Để thiết lập trên máy dự án khác có môi trường Python và dữ liệu nội bộ, chạy `scripts/install_station_map_daily.ps1`. Kiểm tra nguồn ngay bằng `.venv\Scripts\python.exe -X utf8 scripts/run_station_map_daily.py --job probe`.

Lượt 18h40 kiểm tra GFS khởi tạo 07h và Vrain tới mốc quan trắc 18h. Nếu đủ nguồn, trình ghi tạo 26 đặc trưng tại các trạm hợp lệ, chạy mô hình đã khóa và lưu đầu vào, dự báo, mã kiểm tra tệp và giờ thực nhận. Web chỉ nhận lượt ghi trước 19h, đúng ba cửa sổ 24 giờ, kể từ thời điểm phát. Khi thiếu nguồn hoặc hết hạn thu, nhật ký ghi nguyên nhân và vẫn xem được bản trước với ngày phát của nó.

Lượt 20h05 kiểm tra các lần phát đã đủ 72 giờ cộng 1 giờ chờ số đo. Nếu chưa có đủ nhãn, có thể kiểm tra lại vào ngày sau. Các lần tải dở được lưu riêng để truy vết. Nhật ký truy vấn, lần phát và đối chiếu nằm trong `data/operational/station_map_web/daily/` và thư mục `live/` của bản nghiên cứu. Không có bước huấn luyện lại tự động.

Ngày 24/11/2026, đã tải và giải mã đủ 19 trường GFS tại 57 trạm. Lần kiểm tra lại khoảng 16h06 thấy đủ chỉ mục, nhưng cả hai kênh Vrain trả HTTP 404. Lần chạy thử tác vụ nhận diện đúng tình trạng chưa có lượt đến hạn đối chiếu. Chưa có dự báo trực tiếp đủ nguồn để đánh giá vận hành đầu cuối. Web hiển thị các lượt phát lại có ghi ngày phát. [Sản phẩm GFS của NOAA](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast).

## Tham khảo giao diện

- Chọn kỳ tích lũy và đọc đơn vị trên bản đồ. [Bản đồ mưa của WPC](https://www.wpc.ncep.noaa.gov/qpf/qpf2body.html).
- Đổi lớp và thời gian trong cùng bản đồ. [Bản đồ Apple Weather](https://support.apple.com/guide/iphone/view-weather-maps-iph0960651f5/ios).
- Biểu đồ dự báo theo vị trí và khung thời gian. [Biểu đồ dự báo NWS](https://www.weather.gov/wrn/hourly-weather-graph).

[Kết quả và giới hạn của nghiên cứu](../../reports/gfs_short_range_closeout_2026_11_24/KET_LUAN_NGAN_HAN.md) · [Leaflet](https://leafletjs.com/examples-v1/quick-start/) · [OpenStreetMap](https://www.openstreetmap.org/copyright).
