# Pilot ECMWF Single Runs, Đà Nẵng, 01–14/10/2024

Đây là **đối chứng nguồn dự báo**, chưa là phép so AI–ECMWF. Kho [Single Runs của Open-Meteo](https://open-meteo.com/en/docs/single-runs-api) trả từng run IFS đã khởi tạo; bộ hiện tại gồm 56/56 run, 30 ô đã chọn trước trong `reports/domain_screen_danang/run.json`, 4 giờ phát hành/ngày và 14 ngày liên tiếp. Cả 1.680 cặp ô–giờ phát hành có nhãn GSMaP GC permanent và đủ 6 giờ forecast. Không dùng năm test 2025.

## Quy ước và khả năng tái lập

- Mỗi giờ phát hành `issue` dùng run khởi tạo trước 12 giờ. Theo tài liệu, `run` là giờ khởi tạo chứ **không** phải giờ đã phân phối; dữ liệu lịch sử không chứng thực `available_at`. 12 giờ là giả định bảo thủ cho pilot, không là bằng chứng as-of hoàn chỉnh. Run trước 6 giờ chỉ chấm độ nhạy và có thể chưa sẵn có đúng `issue`.
- Open-Meteo ghi `precipitation` là tổng **giờ trước** ([tài liệu ECMWF API](https://open-meteo.com/en/docs/ecmwf-api)); forecast tại timestamp `t+1` so với nhãn GSMaP khoảng `[t,t+1)`. Bốn mẫu đầu/giữa/cuối đã được đối chiếu lại với JSON và cube; test tự động chặn lệch giờ, đơn vị hoặc tọa độ.
- Open-Meteo cung cấp chuỗi giờ và ánh xạ không gian đã xử lý, **không phải GRIB ECMWF gốc**. 30 ô mục tiêu nhận 29 tọa độ forecast khác nhau ở run kiểm tra. Không suy rằng 1.680 mẫu là 1.680 đợt mưa độc lập.
- Phản hồi, URL, SHA-256, thời điểm tải và dự báo từng ô ở `data/operational/ecmwf_pilot_20241001_14/` ngoài Git. `collection_status.json` và `summary.json` là thống kê công khai. Lệnh tái lập: `.venv\Scripts\python.exe scripts\pilot_ecmwf_single_runs.py` (cache/resume). Ban đầu bị HTTP 429 sau 22 run; ấn định nghỉ 8 giây giữa request mới theo [giới hạn API miễn phí](https://open-meteo.com/en/pricing), rồi tải đủ 56/56. Không dùng API key hoặc gói trả phí.

## Kết quả mô tả, 30 ô × 56 giờ phát hành

| Tổng mưa | RMSE ECMWF (mm) | RMSE luôn 0, cùng mẫu | CSI ECMWF | Sự kiện thật | Ngày có sự kiện |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0–3 giờ | 3,950 | 3,878 | 0,089 ở ≥10 mm | 62 | 4/14 |
| 3–6 giờ | 4,047 | 3,521 | 0,061 ở ≥10 mm | 52 | 4/14 |
| 0–6 giờ | 7,078 | 7,222 | 0,024 ở ≥25 mm | 29 | 4/14 |

Ở 0–3 giờ, ECMWF trúng 8/62 sự kiện ≥10 mm, báo sai 28 lần; FAR 0,778 và POD 0,129. Bootstrap khối 5 ngày/1.000 lần cho RMSE 0–3 giờ CI95% [3,320; 5,232] mm; CSI [0; 0,119]. Chênh RMSE ECMWF−luôn 0 có CI95% [−0,873; +1,235] mm, **chưa phân biệt chắc**. Run trễ 6 giờ có RMSE 3,972 so 3,978 của run trễ 12 giờ trên 1.650 cặp chung; CI hiệu số vẫn chứa 0 và trạng thái sẵn có của run 6 giờ chưa chứng thực.

Pilot xác nhận có thể thu/chấm dữ liệu forecast lịch sử cùng nhãn tại Đà Nẵng. Khoảng thời gian 14 ngày chỉ có bốn ngày xảy ra mưa ≥10 mm/3 giờ, nên các điểm kỹ năng còn bất định và không đại diện cả mùa. Checkpoint Bi-LSTM/LightGBM hiện dùng ERA5 hồi cứu và GSMaP raw lưu trữ; **chưa được chấm cạnh ECMWF như mô hình vận hành**. Bước tiếp là nối đầu vào AI as-of (NRT và khí tượng có trước giờ phát hành), tăng số ngày mưa/mùa theo thiết kế cố định, rồi so trên các hàng chung. Giữ test 2025 niêm phong.
