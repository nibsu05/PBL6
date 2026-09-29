# Kiểm tra nhãn mưa độc lập tại Đà Nẵng

## Nguồn và độ phủ

Đã tải dữ liệu [NOAA GHCNh](https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly) năm 2025 của trạm **VMW00041003 – DA NANG** tại 16,05°B, 108,20°Đ. File có 17.189 bản ghi, nhưng cột mưa **1 giờ không có giá trị nào**. Có 216 bản ghi mưa tích lũy 6 giờ, 271 bản ghi 12 giờ và 358 bản ghi 24 giờ. Trong 216 bản ghi 6 giờ đạt mã chất lượng 1, có 163 kỳ mưa dương và 53 kỳ đánh dấu mưa rất nhỏ (trace, lưu thành 0 mm). Không suy các giờ vắng bản ghi thành 0 mm.

Đã đối chiếu thêm file [NOAA ISD và quy cách mã AA](https://www.ncei.noaa.gov/pub/data/noaa/isd-format-document.pdf) năm 2025 của sân bay Đà Nẵng (488550-99999): 13.012 bản tin; có các kỳ tích lũy 6, 12, 18, 24 giờ và kỳ không xác định, nhưng không có kỳ 1 giờ. Vì vậy hai nguồn NOAA này **chưa đủ để kiểm định nhãn mưa từng giờ hoặc recall/FAR trên tất cả giờ**.

## Kiểm tra phụ ở độ phân giải 6 giờ

Ghép 216 kỳ GHCNh 6 giờ với tổng 6 dự báo Bi-LSTM và tổng 6 giờ Open-Meteo trên phần test. Giả định thời điểm `DATE` của NOAA là **cuối kỳ tích lũy**; Open-Meteo định nghĩa mưa tại một giờ là [tổng của giờ trước đó](https://open-meteo.com/en/docs/historical-weather-api). Cần xác nhận quy ước timestamp NOAA với đơn vị cung cấp trước khi coi đây là đối chiếu chính thức.

| Chuỗi so với trạm NOAA | MAE (mm/6h) | RMSE (mm/6h) | Tương quan CC | Sai lệch trung bình (mm/6h) |
| --- | ---: | ---: | ---: | ---: |
| Open-Meteo | 5,95 | 12,73 | 0,797 | -1,99 |
| Bi-LSTM chuẩn | 7,49 | 18,49 | 0,392 | -1,63 |
| Persistence | 8,07 | 20,60 | 0,296 | -1,97 |

Các kỳ 6 giờ được báo **không đều và thiên về lúc có mưa**: trong mẫu này mưa trạm trung bình 7,97 mm/6h, cực đại 232 mm/6h. Bảng trên chỉ mô tả **216 kỳ được báo**, không phải hiệu năng trên cả năm; không dùng để chọn mô hình hoặc ngưỡng. Nó cũng cho thấy sai số của nhãn Open-Meteo so với quan trắc trạm, nên các chỉ số test dùng Open-Meteo cần được đọc là đánh giá theo nhãn đại diện này.

## Dữ liệu cần bổ sung cho xác nhận chính

Cần chuỗi mưa trạm tự ghi hoặc radar đã hiệu chỉnh với độ phân giải **1 giờ**, tọa độ và múi giờ được ghi rõ, quy ước thời điểm là đầu hay cuối kỳ tích lũy, mã chất lượng và mốc bị thiếu. Cần phủ cả giờ khô để tính recall và tỷ lệ cảnh báo sai. Có thể dùng giao diện `evaluate_surface_baseline.py --observations-csv ... --observations-source ...` khi có dữ liệu đã xác minh; đầu vào yêu cầu `datetime` có UTC offset và `precipitation_mm_h`.

Hướng thu thập ưu tiên là xuất dữ liệu trạm tự động của [hệ thống Vrain Đà Nẵng](https://dwrm.mae.gov.vn/SMPT_Publishing_UC/KhaiThac/TinTuc/pInTinTuc.aspx?ItemID=15506&UrlList=). Nguồn chính quyền nêu hệ thống có 82 trạm và quyền xem qua tài khoản. [WATEC mô tả chức năng xuất Excel theo giờ](https://watec.vn/products/tram-do-mua-tu-dong-vrain); [Open API của Vrain yêu cầu API key cho đối tác](https://dev.vrain.vn/). Vì vậy cần xin quyền xuất lịch sử, metadata trạm và định nghĩa kỳ tích lũy từ đơn vị quản lý. Chưa đưa số liệu Vrain vào thí nghiệm hiện tại.

Chi tiết có trong [noaa_audit_2025.json](noaa_audit_2025.json), các cặp quan trắc trong `matched_noaa_6h_2025.csv`. Tái lập bằng `audit_noaa_observations.py`.

Khi có file mưa trạm 1 giờ, dùng [hướng dẫn nhập và đánh giá](GAUGE_IMPORT_GUIDE.md); không dùng tổng mưa NOAA 6 giờ làm nhãn mưa 1 giờ.
