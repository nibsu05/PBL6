# Web dự báo mưa tại trạm

Bản đồ dùng một thanh **1h, 2h, 3h, 4h, 5h, 6h, Ngày 1, Ngày 2, Ngày 3**. Mỗi ô giờ là lượng của một giờ riêng. Khi chọn **Mới nhất**, nhóm giờ và nhóm ngày tự chọn lượt mới nhất của từng nhóm. Hai nhánh đối chiếu tổng sáu giờ với Ngày 1 khi cùng mốc. Giờ hiệu lực, đơn vị, trạng thái và số trạm có số thay đổi theo hạn đã chọn.

Giao diện mặc định dùng **57 trạm chung** và lớp xã, phường cho cả hai nhánh. Mở **Công cụ → Phạm vi trạm** để hiện toàn bộ 79 trạm giờ hoặc 57 trạm ngày. **Nơi có mưa** mở danh sách khu vực, có tìm tên, lọc ngưỡng theo kỳ và xem số trạm. Chọn **Theo trạm** để xem dự báo từng mô hình và đối chiếu tổng sáu giờ với Ngày 1. Trên màn hình nhỏ, bảng khu vực mở từ dưới.

Dãy **Lượt đã lưu** chọn lượt mới nhất và bảy ngày trước. Bấm **Ngày gần đây** để xem lịch quanh ngày hiện tại. Khi chọn cố định một lượt chỉ có một nhánh, các kỳ còn lại hiển thị thiếu. Các lượt phát lại có ngày thật và nhãn riêng từng kỳ.

Màu khu vực dùng lượng cao nhất trong các trạm hợp lệ nằm trong ranh giới. Lọc **Có mưa** theo mức 0,1 mm trong giờ hoặc 1 mm trong 24 giờ tại ít nhất một trạm. Vùng xám chưa có số cho lớp đang xem. Lớp xác suất ngày lấy giá trị cao nhất tại trạm, lớp sai lệch lấy độ lệch tuyệt đối lớn nhất và giữ dấu.

Nhánh giờ có LightGBM R, Bi-LSTM R và giữ mưa vừa đo. Nhánh ngày có LightGBM B, GFS và xác suất đạt 50 mm trong 24 giờ. Sau đăng nhập có Vrain thực đo, sai lệch và CSV của đúng kỳ, phạm vi đang xem. Trang Theo dõi vẫn cho đối chiếu theo lượt ngày và xem trạng thái nguồn.

## Mở web

Chạy lệnh ở thư mục gốc dự án.

```powershell
.venv\Scripts\python.exe -X utf8 demo/station_map.py
```

Mở **http://127.0.0.1:8766/** và chọn **Đăng nhập**. Lần đầu, chọn tên và mật khẩu riêng cho web. Các lần sau dùng đúng tài khoản này. Nếu thiếu tệp phát lại, chạy `.venv\Scripts\python.exe -X utf8 scripts/close_short_range.py` để tạo lại từ bản nghiên cứu đã khóa. Bản đồ nền cần kết nối mạng.

Tạo lịch sử ngày bằng `.venv\Scripts\python.exe -X utf8 scripts/prepare_station_map_history.py`. Sau đó chạy `.venv\Scripts\python.exe -X utf8 scripts/prepare_station_nowcast_replay.py --align-daily` để xuất bản giờ từ trọng số đã khóa, cùng giờ phát với các lượt ngày lưu sẵn. Hai nhánh hiện có **9 lượt chung**, gồm **05–12/11/2026** và lượt minh họa mưa lớn **07/10/2026**. Tệp mưa giờ bổ sung ở `data/operational/vrain_recent_danang_2026_11_24/` có số hợp lệ đến **19h ngày 24/11/2026**.

Ứng dụng hiện nghe trên máy này qua `127.0.0.1`. Tài khoản được lưu dưới dạng băm có salt. Phiên đăng nhập hết hạn sau 8 giờ hoặc khi khởi động lại máy chủ. Hồ sơ tài khoản tại `data/operational/station_map_web/` nằm ngoài Git.

### Ranh giới tham chiếu

Lấy tệp hình học trên máy mới bằng `.venv\Scripts\python.exe -X utf8 scripts/prepare_station_map_areas.py`. Tệp `data/operational/station_map_areas/wards-48.geojson` được phục vụ qua `/api/areas` và lưu cục bộ. Khi tệp thiếu, web mở theo trạm.

Nguồn ranh giới tham chiếu là tinhthanhpho.com, bản 2026.10.8 theo đơn vị cấp xã hiện hành. Kiểm tra 94 vùng, ghép đủ 57 trạm vào 40 xã/phường theo phép chứa điểm. Trong 40 nơi có trạm, 28 nơi chỉ có một trạm. Không gán trạm sang khu vực gần nhất. Đặc khu Hoàng Sa có trong bộ ranh giới và nằm ngoài khung nhìn mặc định vì không có trạm trong bộ dự báo. [Tệp nguồn](https://www.tinhthanhpho.com/data/wards-48.geojson) · [Giấy phép CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Trang theo dõi

- **Thông báo admin** lưu các lần nguồn lỗi, trạm thiếu, lượt phát bị dừng và lượt đến hạn đối chiếu chưa có nhãn. Số chưa đọc hiện trên nút Theo dõi. Có thể đánh dấu từng mục hoặc đọc tất cả. Các lần lặp cùng loại trong cùng ngày được gộp kèm thời điểm mới nhất. Tác vụ Python lưu thông báo vào cơ sở dữ liệu cục bộ kể cả khi đóng tab web.
- **Cập nhật hằng ngày** hiển thị lịch đã đăng ký trên máy, kết quả của lần chạy gần nhất và trạng thái GFS/cả hai kênh Vrain. Nút **Kiểm tra nguồn** hỏi nguồn trong một lượt có giới hạn. GFS kiểm tra chỉ mục, Vrain kiểm tra số đo của ngày hiện tại. Trang đọc lại trạng thái lưu trên máy mỗi 30 giây khi đang mở.
- **Lần phát** hiển thị bản dự báo được ghi trước giờ phát nếu có, cùng giờ ghi nhận và tình trạng đối chiếu. Mỗi bản hiện đúng ngày đã phát. Khi thiếu lượt trực tiếp, bản đồ mở **Phát lại lịch sử**. Giờ phát theo thiết kế là 19h Việt Nam.
- **Đối chiếu** chấm LightGBM, GFS và MOS trên các trạm có đủ dự báo và thực đo cùng cửa sổ. Hiển thị MAE, RMSE, Bias và số trúng, bỏ sót, báo nhầm mưa ≥50 mm. Có thể mở đúng kỳ trên bản đồ hoặc tải CSV.
- **Nghiên cứu** trình bày RMSE hồi cứu 2026, kết quả nhóm biến trên kiểm định 2025 và MAE nhóm thực đo ≥50 mm của thử nghiệm điều chỉnh có điều kiện.

## Đầu ra cho giao diện

`GET /api/forecast` ghép theo thời điểm phát, đưa đủ chín vị trí trên thanh và giữ riêng trường thời lượng, chế độ và khoảng hiệu lực của mỗi kỳ. Khách xem dự báo. CSV ở `/api/export-forecast.csv` và thực đo cần phiên đăng nhập. Bản đồ kiểm tra cập nhật mỗi 90 giây khi mở trang. Đường dẫn cũ `/cuc-ngan` mở trực tiếp Giờ 1 ở bản đồ chung. Dashboard tiếp tục dùng đầu ra ngày tại `/api/short-range`.

Xem [báo cáo và so sánh hai nhánh trên 57 trạm](../../reports/station_forecast_unified_2026_11_24/BAO_CAO_CHI_TIET.md).

## Dự báo mỗi ngày

Tác vụ **PBL6-DailyRainfall** trong Windows Task Scheduler chạy lúc 18h40 và 20h05 giờ Việt Nam khi máy hoạt động và tài khoản Windows còn đăng nhập. Tác vụ chạy độc lập với trình duyệt. Để thiết lập trên máy dự án khác có môi trường Python và dữ liệu nội bộ, chạy `scripts/install_station_map_daily.ps1`. Kiểm tra nguồn ngay bằng `.venv\Scripts\python.exe -X utf8 scripts/run_station_map_daily.py --job probe`.

Lượt 18h40 kiểm tra GFS khởi tạo 07h và Vrain tới mốc quan trắc 18h. Nếu đủ nguồn, trình ghi tạo 26 đặc trưng tại các trạm hợp lệ, chạy mô hình đã khóa và lưu đầu vào, dự báo, mã kiểm tra tệp và giờ thực nhận. Web chỉ nhận lượt ghi trước 19h, đúng ba cửa sổ 24 giờ, kể từ thời điểm phát. Khi thiếu nguồn hoặc hết hạn thu, nhật ký ghi nguyên nhân và vẫn xem được bản trước với ngày phát của nó.

Lượt 20h05 kiểm tra các lần phát đã đủ 72 giờ cộng 1 giờ chờ số đo. Nếu chưa có đủ nhãn, có thể kiểm tra lại vào ngày sau. Các lần tải dở được lưu riêng để truy vết. Nhật ký truy vấn, lần phát và đối chiếu nằm trong `data/operational/station_map_web/daily/` và thư mục `live/` của bản nghiên cứu. Không có bước huấn luyện lại tự động.

Ngày 24/11/2026, đã tải và giải mã đủ 19 trường GFS tại 57 trạm. Đường chi tiết Vrain cũ trả 404, trong khi giao diện hiện tại dùng báo cáo phân trang trên đường mới. Tác vụ đã đọc thành công cả hai kênh mới lúc 22h41. Kênh hiện hành có số ở 84 trạm tại mốc 19h. Web có thể xem các lượt phát lại với ngày phát gốc. Kiểm tra lần phát trực tiếp cần số đo đến đúng giờ trong kỳ theo lịch. [Bằng chứng phục hồi Vrain](../../reports/danang_system_2026_11_24/THIET_KE_HE_THONG.md#khi-nguồn-thiếu-hệ-thống-xử-lý-thế-nào) · [Sản phẩm GFS của NOAA](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast).

## Thí điểm dự báo 1–6 giờ

**PBL6-HourlyRainfall** đã được đăng ký trong Windows Task Scheduler lúc 23h08 ngày 24/11/2026. Tác vụ bắt đầu ở **phút 05 mỗi giờ** và lưu lượt trước phút 15 của cùng giờ. Tác vụ dùng cùng cơ chế đăng nhập Windows của nhánh ngày. Để cài trên máy khác đã có dữ liệu và mô hình, chạy `scripts/install_station_nowcast_hourly.ps1`. Có thể thử riêng bước đọc dữ liệu và suy luận bằng `.venv\Scripts\python.exe -X utf8 scripts/run_station_nowcast_hourly.py --probe`.

Mỗi lượt lấy từ Vrain đúng 24 giờ đã chốt, ưu tiên mốc hiện tại và giữ nguyên mã trạm. LightGBM R, Bi-LSTM R và mốc giữ mưa trả sáu kỳ ở các trạm đủ lịch sử. Nhật ký ghi cả mốc dữ liệu, giờ nhận, giờ lưu và số trạm. Khi một lượt gặp lỗi, admin xem tình trạng trong thẻ **Dự báo 1–6 giờ**. Tác vụ cũng chấm các lượt đủ sáu giờ thực đo, giữ các ô thiếu riêng và báo MAE, RMSE, POD, FAR và CSI theo hạn.

Lần khởi chạy đầu tiên qua Task Scheduler đã ghi **mốc 23h ngày 24/11** lúc **23h09:34**, với **77/79 trạm** và **1.848 hàng đầu vào**. Các tệp phản hồi, đầu vào, dự báo và nhật ký thuộc `data/operational/station_map_web/hourly/`. Dự báo giờ đầu của lượt này có hiệu lực 23h–00h. Giờ thứ sáu kết thúc lúc 05h ngày 25/11.

Trong giai đoạn thí điểm, trang **Theo dõi** cho biết giờ lưu, độ phủ và trạng thái đối chiếu. Bản đồ công khai trên máy dùng các bản phát lại. Sau khi đọc nhật ký 2–3 ngày, đặt `enabled` thành `true` trong tệp `hourly/display.json` để bản đồ đọc các lượt đã ghi. Chế độ **Mới nhất** lấy riêng bản mới của nhóm giờ và nhóm ngày. Khi xem một lượt cụ thể, cả hai nhóm giữ đúng mốc của lượt đó.

## Tham khảo giao diện

- Chọn kỳ tích lũy và đọc đơn vị trên bản đồ. [Bản đồ mưa của WPC](https://www.wpc.ncep.noaa.gov/qpf/qpf2body.html).
- Đổi lớp và thời gian trong cùng bản đồ. [Bản đồ Apple Weather](https://support.apple.com/guide/iphone/view-weather-maps-iph0960651f5/ios).
- Biểu đồ dự báo theo vị trí và khung thời gian. [Biểu đồ dự báo NWS](https://www.weather.gov/wrn/hourly-weather-graph).

[Kết quả và giới hạn của nghiên cứu](../../reports/gfs_short_range_closeout_2026_11_24/KET_LUAN_NGAN_HAN.md) · [Leaflet](https://leafletjs.com/examples-v1/quick-start/) · [OpenStreetMap](https://www.openstreetmap.org/copyright).
