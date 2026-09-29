# Kế hoạch triển khai và xử lý thiếu ERA5 PL850

## Kiểm kê dữ liệu tại thời điểm triển khai

Nguồn hiện nằm trong `data/raw_data/`. Open-Meteo và ERA5 SST đều có **102.264** mốc giờ UTC từ 2015-01-01 00:00 đến 2026-08-31 23:00, không trùng giờ hoặc rỗng trong CSV đã trích xuất. ERA5 PL850 có **91.248** mốc giờ, không trùng hoặc rỗng trong CSV, nhưng thiếu **15 tháng / 11.016 giờ** so với hai nguồn trên:

| Khoảng thiếu PL850 (UTC) | Số giờ | Ảnh hưởng |
| --- | ---: | --- |
| 2024-04-01 00:00 → 2024-12-31 23:00 | 6.600 | Khoảng trống nằm giữa tập dữ liệu |
| 2026-03-01 00:00 → 2026-08-31 23:00 | 4.416 | Đuôi dữ liệu chưa tải |

Như vậy, hai đoạn PL850 liên tục dùng được là 2015-01-01 → 2024-03-31 và 2025-01-01 → 2026-02-28 theo UTC. NetCDF có 125 file tháng PL850 và 140 file tháng SST. ONI CSV hiện là bản trải theo giờ và cần gom về giá trị tháng trước khi ghép. Mã PoC cũ lấy trung bình toàn vùng ERA5; pipeline mới chọn ô lưới gần tọa độ Đà Nẵng (SST chọn ô biển hợp lệ gần nhất nếu điểm đất liền bị thiếu).

Các biến CAPE, CIN, TCWV chưa có trong dữ liệu. Theo quyết định hiện tại, baseline Bi-LSTM bỏ ba biến này; pipeline ghi cảnh báo và không tự tạo giá trị giả.

## Thứ tự thực hiện

1. **Kiểm tra nguồn theo tháng và theo giờ.** Đối chiếu thời gian, tọa độ, biến và đơn vị trong NetCDF. Lưu báo cáo khoảng trống tại `data/processed/merge_diagnostics.json`.
2. **Chạy baseline với dữ liệu sẵn có.** Ghép theo giờ Asia/Ho_Chi_Minh, chỉ nội suy tối đa 2 giờ đối với biến đầu vào khi có hai đầu quan trắc; không nội suy nhãn mưa, không lấp khoảng thiếu hàng tháng. Bỏ hàng thiếu khỏi master nhưng tái tạo trục giờ đầy đủ trước khi tính lag/rolling và lập cửa sổ, để không nối nhầm tháng 03/2024 với tháng 01/2025.
3. **Đánh giá trung thực.** Chia train/validation/test theo 70/15/15 *thời gian lịch*, fit `RobustScaler` trên train, chỉ nhận cửa sổ đủ 24 giờ đầu vào và 6 giờ nhãn liên tiếp. Báo số cửa sổ mất vì gap, metric toàn bộ 1–6 giờ và từng horizon, cùng bốn đồ thị 300 DPI.
4. **Tải bù ERA5 PL850 khi cần mở rộng phân tích đa nguồn.** Bổ sung 04–12/2024 và 03–08/2026; kiểm tra đúng 24 giờ/ngày, biến U/V/Q tầng 850 hPa, không trùng timestamp, không có ngày bị thiếu. Sau đó chạy lại toàn bộ pipeline và so sánh metric theo cùng quy trình. Việc tải ERA5 cần tài khoản/cấu hình CDS API, nên không tự suy diễn các tháng chưa có. Trong lúc chờ, nhánh Open-Meteo đầy đủ thời gian đã chạy; xem `SURFACE_BASELINE_REPORT.md`.
5. **Mở rộng sau baseline.** Nếu cần Informer 24–72 giờ, tạo bộ cửa sổ và quy trình đánh giá riêng. Cần tái kiểm tra gap cho toàn bộ 24+72 giờ và so sánh với Bi-LSTM/persistence trên cùng tập test. CAPE/CIN/TCWV chỉ thêm khi đã có dữ liệu và thí nghiệm ablation cho thấy ích lợi.

## Giới hạn của kết quả hiện tại

Đây là kiểm định hồi cứu trên Open-Meteo historical và ERA5 reanalysis. Với hệ thống phát hành dự báo thực tế, cần thay ERA5 bằng nguồn có sẵn đúng thời điểm dự báo và ghi thời điểm phát hành của từng trường. ONI theo tháng trong file hiện không có thời điểm công bố; `oni_anom` được lưu trong bảng hợp nhất nhưng mặc định **không dùng làm đầu vào mô hình** để tránh dùng chỉ số được biết muộn. Tùy chọn `--include-retrospective-oni` chỉ phục vụ thí nghiệm hồi cứu.

## Kết quả baseline đã chạy với dữ liệu hiện có

Pipeline trích xuất 265 file NetCDF tại điểm lưới (16.00°N, 108.25°E) cho U/V/Q 850 hPa. SST dùng ô biển gần nhất (16.25°N, 108.25°E). Bảng hợp nhất có 91.248 giờ, không trùng timestamp, không có NaN sau khi loại giờ thiếu nguồn. Trong lần chạy này không cần nội suy giờ nào. Sau khi tạo đặc trưng và loại cửa sổ qua gap, các tập có 68.440 / 12.574 / 10.123 cửa sổ train / validation / test, với 31 đặc trưng và 24 giờ đầu vào → 6 giờ dự báo.

Bi-LSTM chạy trên GTX 1650 qua PyTorch CUDA 12.4, dừng sớm ở epoch 8 và giữ checkpoint từ epoch 1. Test gộp sáu horizon: MAE **0,3812 mm/h**, RMSE **1,1464 mm/h**, R² **0,2480**, CC **0,5323**. Sai số tăng từ MAE 0,3378 ở t+1 lên 0,4234 mm/h ở t+6.

Mưa lớn >5 mm/h chỉ chiếm **1,05%** các cặp horizon–giờ trong test. Trên nhóm này, MAE là **6,3657 mm/h**; lượng mưa trung bình thực tế là 9,86 mm/h nhưng dự báo trung bình chỉ 3,55 mm/h. Bốn đồ thị tại `plots/` cho thấy mô hình làm trơn đỉnh mưa. Vì vậy đây là **mốc so sánh ban đầu**, chưa đủ tốt để dùng cảnh báo mưa cực đoan.

Nhánh bề mặt toàn thời gian và đối chứng persistence đã được chạy, cùng một thí nghiệm lấy mẫu cân bằng đợt mưa tỷ lệ 25%; xem `SURFACE_BASELINE_REPORT.md`. Hướng tiếp theo là đánh giá theo mùa và theo sự kiện, thử tỷ lệ lấy mẫu hoặc hàm mất mát khác dựa trên validation, rồi nghiên cứu Informer 24–72 giờ. Chỉ tải bù PL850 khi cần đánh giá đa nguồn trên các tháng còn thiếu. Mỗi thí nghiệm cần giữ nguyên split thời gian và ghi metric riêng cho mưa >5 mm/h.

## Chạy

```powershell
& 'C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install --force-reinstall 'torch==2.6.0+cu124' --index-url https://download.pytorch.org/whl/cu124
.\.venv\Scripts\python.exe run_full_pipeline.py --prepare-only
.\.venv\Scripts\python.exe run_full_pipeline.py
```

Lệnh `--prepare-only` tạo master CSV/Parquet, đặc trưng, scaler và báo cáo số cửa sổ. Lệnh cuối huấn luyện, lưu checkpoint và xuất bốn hình tại `plots/`. Môi trường `.venv` trong dự án này đã được cài xong; có thể chạy thẳng hai lệnh cuối. Khi chỉ muốn train lại trên master sẵn có, thêm `--reuse-merged` để khỏi đọc lại 265 file NetCDF.
