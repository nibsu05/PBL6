# Kết quả pilot GFS + Vrain tại trạm — 10/11/2026

**Đã chạy thí nghiệm thực tế**, gồm khí hậu tham chiếu, persistence, GFS nguyên bản và LightGBM A0–A3. GRU A2 cũng đã chạy theo gate định trước trên tập hiệu chỉnh.

**Phạm vi:** 20 trạm; lịch cố định mỗi 7 ngày trong 2021–2024, 208 issue đã trích GFS. Đây là pilot, chưa phải thí nghiệm dự báo hằng ngày hoặc kết quả cuối cho toàn bộ 79/86 trạm. Năm 2025 vẫn giữ kín.

## Bài toán và cách tránh lấy nhầm tương lai

Lúc 19:00 giờ Việt Nam, dự báo ba tổng mưa riêng: 0–24h, 24–48h và 48–72h. Nhãn là Vrain tại chính trạm. GFS khởi tạo 00UTC, sớm hơn issue 12 giờ; hiệu các tổng mưa tích lũy +12/+36/+60/+84h tạo đúng ba cửa sổ 19–19h. Các trường khí tượng ở +24/+48/+72h là dự báo từ cùng bản khởi tạo, không phải số đo tương lai hay ERA5 kỳ đích.

Giả định mưa trạm trễ 1 giờ: summary 1/6/24h kết thúc 18:00; chuỗi bảy ngày đầy đủ kết thúc hôm trước. GFS giả định sẵn sàng sau 8 giờ từ init, nhưng chưa xác minh thời điểm công bố lịch sử từng file. Đây là thiết kế hồi cứu có kiểm soát thời gian, chưa chứng nhận hệ thống vận hành.

## Mẫu, biến và mô hình

Chọn 20 trạm từ 57 ứng viên bằng dữ liệu train và địa lý/DEM, không chọn theo điểm cal/dev. Mỗi trạm pilot có 565–728 ngày train đầy đủ. Không yêu cầu toàn mạng có số đo đồng thời.

| Phần | Năm | Mẫu trạm–issue | Dòng theo ba hạn | Vai trò |
|---|---|---:|---:|---|
| train | 2021–2022 | 1,774 | 5,322 | Fit mô hình và thống kê |
| cal | 2023 | 902 | 2,706 | Earlystop, Platt, gate GRU |
| dev | 2024 | 983 | 2,949 | Đánh giá phát triển, chưa test cuối |

Hai issue bị loại vì nhãn vượt ranh split; 461 mẫu trạm–issue không đủ lịch sử/nhãn bị loại. Mọi cấu hình dùng chung phần dữ liệu còn lại. Số mẫu giữa các trạm/đợt mưa không độc lập.

| Cấu hình | Số biến | Bổ sung |
|---|---:|---|
| A0 | 6 | Mưa GFS + lịch + tọa độ/ID trạm |
| A1 | 16 | A0 + bảy ngày mưa và summary 1/6/24h tại trạm |
| A2 | 25 | A1 + T/RH/gió 850/PWAT, độ ẩm riêng dẫn xuất và proxy vận chuyển ẩm |
| A3 | 32 | A2 + DEM, gradient và tương tác gió–địa hình–ẩm |

Tất cả LightGBM dùng Tweedie p=1,5 cho lượng mưa, classifier cho ≥1/≥50mm. Mỗi cấu hình có ba seed 17/29/43, lấy trung bình dự báo; đây không phải ba năm kiểm định độc lập. Cal dùng Platt nên điểm xác suất cal không phải ngoài mẫu. Ngưỡng 50mm là phân tích thăm dò của pilot, không tự nhận tiêu chuẩn cảnh báo.

## Kết quả lượng mưa trên phần phát triển 2024

MAE dưới đây là trung bình MAE giữa các trạm, mỗi trạm có trọng số bằng nhau; nhỏ hơn tốt hơn. **In đậm là thấp nhất trong từng cột**, không tự đồng nghĩa khác biệt có ý nghĩa thống kê.

| Phương pháp | MAE ngày 1 (mm) | MAE ngày 2 (mm) | MAE ngày 3 (mm) |
|---|---:|---:|---:|
| Khí hậu | 11.90 | 11.01 | 11.13 |
| Persistence | 8.67 | 10.00 | 11.55 |
| GFS nguyên bản | 6.40 | 8.13 | 10.27 |
| LightGBM A0 | 7.09 | 7.89 | 8.83 |
| LightGBM A1 | 6.68 | 7.83 | 8.23 |
| LightGBM A2 | 6.15 | 7.37 | **7.75** |
| LightGBM A3 | **6.09** | **7.35** | 7.76 |
| GRU A2 | 7.81 | 8.35 | 8.46 |

A2 là cấu hình đặt trước cho đối chứng chuỗi, không chọn theo điểm dev. So với GFS, MAE A2 thay đổi: ngày 1: 3.8% giảm; ngày 2: 9.4% giảm; ngày 3: 24.5% giảm.

## Kiểm tra chênh lệch và tác dụng thêm biến

Chênh MAE = phương pháp thứ nhất trừ tham chiếu; số âm có lợi cho phương pháp thứ nhất. CI bootstrap 95% theo khối bốn issue liên tiếp, giữ các trạm trong cùng đợt. CI có cả 0 nghĩa là chưa đủ căn cứ cải thiện ổn định.

| So sánh | Ngày | Chênh MAE (mm) | CI 95% (mm) |
|---|---:|---:|---|
| A2 − GFS | 1 | -0.24 | [-1.32; 0.87] |
| A2 − GFS | 2 | -0.76 | [-1.55; 0.08] |
| A2 − GFS | 3 | -2.51 | [-6.94; 0.25] |
| A1 − A0 | 1 | -0.41 | [-1.64; 0.69] |
| A1 − A0 | 2 | -0.07 | [-0.51; 0.46] |
| A1 − A0 | 3 | -0.61 | [-1.66; 0.04] |
| A2 − A1 | 1 | -0.53 | [-1.15; 0.02] |
| A2 − A1 | 2 | -0.46 | [-0.95; -0.02] |
| A2 − A1 | 3 | -0.47 | [-1.08; 0.14] |
| A3 − A2 | 1 | -0.07 | [-0.15; 0.00] |
| A3 − A2 | 2 | -0.02 | [-0.14; 0.08] |
| A3 − A2 | 3 | 0.01 | [-0.10; 0.08] |
| GRU_A2 − A2 | 1 | 1.66 | [0.61; 2.99] |
| GRU_A2 − A2 | 2 | 0.97 | [0.34; 1.65] |
| GRU_A2 − A2 | 3 | 0.71 | [-0.45; 1.95] |

**Kết luận về mức chắc chắn:** CI A2−GFS ở cả ba ngày đều còn chứa 0. Mức giảm MAE ngày 3 khoảng 24% là dấu hiệu trên mẫu pilot, chưa đủ để khẳng định cải thiện ổn định. A3 chưa cho thấy lợi ích địa hình chắc chắn so A2. GRU có MAE cao hơn A2 ở cả ba hạn trong cấu hình đã thử, nhưng RMSE ngày 3 thấp hơn: GRU 18,31mm so A2 20,17mm. Có đánh đổi giữa các chỉ số; không kết luận GRU kém trên mọi mặt hoặc mọi kiến trúc GRU đều kém.

## Kiểm tra thời điểm sửa file nguồn

Đã kiểm tra Last-Modified của 3,952 thông điệp thuộc 208 chu kỳ. Có 7 chu kỳ đầu 2021 được sửa/chép trong archive sau issue; Last-Modified không chứng minh thời điểm phát hành dự báo gốc. Không có trường hợp này ở các năm cal/dev.

Đã chạy thêm A2 ba seed, bỏ các chu kỳ train có timestamp không rõ; không thay kết quả chính và không chọn theo điểm mưa.

| Ngày | MAE A2 chính (mm) | MAE A2 bỏ chu kỳ train không rõ (mm) |
|---|---:|---:|
| 1 | 6.15 | 6.09 |
| 2 | 7.37 | 7.42 |
| 3 | 7.75 | 7.88 |

## RMSE, Bias và phát hiện sự kiện

RMSE nhấn mạnh lỗi lượng mưa lớn; Bias âm là dự báo thiếu mưa. BSS >0 nghĩa là xác suất tốt hơn khí hậu tham chiếu trên cùng mẫu. POD cần đọc cùng FAR và CSI; không có mức POD tốt chung cho mọi bài toán.

### Ngày 1

| Phương pháp | RMSE mm | Bias mm | BSS ≥1 | CSI ≥1 | POD ≥1 | FAR ≥1 |
|---|---:|---:|---:|---:|---:|---:|
| Khí hậu | 21.25 | 3.42 | 0.000 | 0.322 | 0.553 | 0.560 |
| Persistence | 21.07 | 0.76 | — | 0.360 | 0.583 | 0.515 |
| GFS nguyên bản | 14.53 | 0.37 | — | 0.418 | 0.951 | 0.569 |
| LightGBM A0 | 15.54 | 1.27 | 0.312 | 0.471 | 0.634 | 0.353 |
| LightGBM A1 | 14.06 | 1.55 | 0.289 | 0.478 | 0.661 | 0.370 |
| LightGBM A2 | 13.96 | 0.95 | 0.221 | 0.451 | 0.649 | 0.407 |
| LightGBM A3 | 13.90 | 0.94 | 0.227 | 0.448 | 0.642 | 0.403 |
| GRU A2 | 15.41 | 2.87 | 0.180 | 0.381 | 0.494 | 0.378 |
### Ngày 2

| Phương pháp | RMSE mm | Bias mm | BSS ≥1 | CSI ≥1 | POD ≥1 | FAR ≥1 |
|---|---:|---:|---:|---:|---:|---:|
| Khí hậu | 19.63 | 2.92 | 0.000 | 0.428 | 0.624 | 0.414 |
| Persistence | 23.10 | -0.10 | — | 0.345 | 0.513 | 0.491 |
| GFS nguyên bản | 18.48 | -1.05 | — | 0.459 | 0.941 | 0.525 |
| LightGBM A0 | 18.17 | -1.74 | 0.135 | 0.558 | 0.805 | 0.350 |
| LightGBM A1 | 19.03 | -2.61 | 0.111 | 0.508 | 0.738 | 0.380 |
| LightGBM A2 | 18.38 | -2.56 | 0.193 | 0.571 | 0.790 | 0.330 |
| LightGBM A3 | 18.08 | -2.34 | 0.199 | 0.575 | 0.796 | 0.327 |
| GRU A2 | 18.44 | -0.13 | 0.159 | 0.504 | 0.665 | 0.316 |
### Ngày 3

| Phương pháp | RMSE mm | Bias mm | BSS ≥1 | CSI ≥1 | POD ≥1 | FAR ≥1 |
|---|---:|---:|---:|---:|---:|---:|
| Khí hậu | 20.58 | 2.49 | 0.000 | 0.496 | 0.630 | 0.298 |
| Persistence | 27.44 | -0.60 | — | 0.392 | 0.522 | 0.395 |
| GFS nguyên bản | 26.38 | 1.54 | — | 0.512 | 0.949 | 0.474 |
| LightGBM A0 | 21.52 | -0.72 | 0.113 | 0.564 | 0.738 | 0.299 |
| LightGBM A1 | 19.69 | -1.21 | 0.128 | 0.581 | 0.754 | 0.289 |
| LightGBM A2 | 20.17 | -2.77 | 0.128 | 0.554 | 0.693 | 0.264 |
| LightGBM A3 | 19.74 | -2.34 | 0.125 | 0.545 | 0.677 | 0.265 |
| GRU A2 | 18.31 | 1.28 | 0.117 | 0.504 | 0.646 | 0.303 |

Xác suất được chuyển thành báo có khi p≥0,5; GFS/persistence dùng lượng dự báo≥ngưỡng. GFS không có BSS ở đây vì là dự báo đơn trị, không phải xác suất đã hiệu chuẩn. POD/FAR không xác định được giữ NaN và báo số trạm hỗ trợ trong CSV, không tự đổi thành 0.

Xác suất không cải thiện đồng đều với lượng mưa. Ví dụ ở ngày 1, cần đối chiếu BSS A0 với A2/A3, không chọn cấu hình chỉ vì MAE thấp hơn. Ảnh reliability gộp ba hạn chỉ hỗ trợ chẩn đoán; có bin ít mẫu.

## Giới hạn và bước tiếp theo

- Pilot mới có lịch issue mỗi 7 ngày, 20 trạm và bốn năm thời tiết; cần chạy lịch hằng ngày để xác nhận. Không dùng số dòng hoặc nhiều trạm cùng trận để phóng đại cỡ mẫu độc lập.
- Mùa/năm có thể cho kết quả khác nhau. Gate GRU dựa trên cal: A2 chỉ đạt ở ngày 3 với mức cải thiện nhỏ; không dùng kết quả dev thuận lợi để sửa gate hoặc chọn trạm.
- Địa hình là proxy, không phải cao độ đo tại trạm; chưa có kiểm chứng lịch sử di chuyển/cảm biến. Một số điểm có cao độ DEM gần hoặc thấp hơn mực biển. Mean/std là chín điểm trong ô ±5km theo hai trục, không phải trung bình tất cả pixel. ID trạm đã có thể mang một phần khác biệt địa phương; chưa kiểm chứng tổng quát sang trạm chưa thấy.
- Chưa chứng minh các đặc trưng thêm đều hữu ích. Thứ tự A0→A3 còn phụ thuộc nhóm đã có; cần thử bỏ nhóm khỏi cấu hình đầy đủ, giữ cùng mẫu, trước kết luận đóng góp.
- Đánh giá ≥50mm có thể ít đợt mưa; xem số sự kiện và số issue có mưa trong CSV. Chưa có CI cho mọi chênh lệch BSS hoặc bằng chứng cải thiện cực đoan ổn định.
- Trễ mưa trạm 1 giờ và GFS 8 giờ là giả định cần kiểm chứng. GFS là sản phẩm lưới, không mô tả đầy đủ địa hình/quá trình nhỏ tại từng trạm.
- Năm 2025 chưa mở, 2026 không fit/tuning. Tập 2024 là đánh giá phát triển; kết quả này chưa là test cuối.

**Bước tiếp theo đề xuất:** hoàn thành thí nghiệm hằng ngày với protocol cố định, kiểm tra độ nhạy trễ dữ liệu, và ablation bỏ nhóm; tiếp tục đánh giá theo từng trạm/mùa/hạn. Chưa có cơ sở yêu cầu chuyển sang mô hình lớn hơn.

## Bằng chứng và tái tạo

Đã replay 10,977 dòng từ raw Vrain, kiểm tra 3,895 header GRIB; tải lại 57 thông điệp và đối chiếu 171 mẫu nội suy độc lập. Không dùng ERA5 hoặc khí tượng tương lai thực đo trong X.

Đã replay 36 estimator lượng mưa, 72 classifier và ba checkpoint GRU trên CPU; đối chiếu dự báo lưu, scaler train-only và metrics tổng hợp đạt.

[Protocol](protocol.json), [audit dữ liệu](dataset_audit.json), [verification](verification.json), [kết quả lượng mưa](point_metrics.csv), [xác suất](probability_metrics.csv), [sự kiện](event_metrics.csv), [bootstrap](paired_bootstrap.csv), [seed](seed_point_metrics.csv), [GRU](gru_summary.json), [replay mô hình](model_verification.json), [timestamp nguồn](release_timestamp_audit.json), [kiểm tra độ nhạy](release_sensitivity_metrics.csv).

Mã chạy: prepare/collect/build/validate/run_gfs_station_pilot.py và run_gfs_station_gru.py. Dữ liệu, tọa độ, checkpoint và dự đoán từng thời điểm nằm ngoài Git.

Nguồn: [NOAA GFS](https://registry.opendata.aws/noaa-gfs-bdp-pds/), [inventory GFS](https://www.nco.ncep.noaa.gov/pmb/products/gfs/), [Mapzen Terrain Tiles](https://registry.opendata.aws/terrain-tiles/), [attribution DEM](https://github.com/tilezen/joerd/blob/master/docs/attribution.md).
