# Kết quả Bi-LSTM chỉ dùng dữ liệu bề mặt

## Mục đích và dữ liệu

Khi ERA5 PL850 còn thiếu 15 tháng, nhánh này dùng toàn bộ Open-Meteo đã có để tạo một baseline 1–6 giờ độc lập với việc tải bù. Không dùng CAPE, CIN, TCWV, ERA5 hoặc ONI làm đầu vào. Dữ liệu bề mặt gồm 102.264 giờ liên tục (2015-01-01 00:00 đến 2026-08-31 23:00 UTC). Mỗi cửa sổ có 24 giờ đầu vào, 6 giờ nhãn và 22 đặc trưng. `RobustScaler` chỉ fit trên train; các biến thể dùng chung các split theo thời gian và không có cửa sổ nào băng qua split.

| Tập | Số cửa sổ |
| --- | ---: |
| Train | 71.531 |
| Validation | 15.335 |
| Test | 15.335 |

Ranh giới train là 2023-03-02 23:00 và ranh giới validation là 2024-12-01 03:00 theo giờ Đà Nẵng (UTC+7). Test có 92.010 cặp dự báo horizon–giờ. Trong đó 702 cặp (0,763%) thực tế mưa >5 mm/h. Các cửa sổ có 24 giờ đầu thiếu lag bị loại.

## Thí nghiệm trên GPU

Đã huấn luyện trên NVIDIA GTX 1650 với cùng Bi-LSTM hai tầng và weighted MSE (trọng số 4 cho nhãn >5 mm/h):

- **Standard:** lấy mẫu train theo phân bố tự nhiên; checkpoint tốt nhất ở epoch 2.
- **Event balanced:** 1.212/71.531 cửa sổ train có ít nhất một nhãn >5 mm/h, được nhóm thành 135 đợt mưa với khoảng cách tối đa 6 giờ. Sampler tăng tỷ lệ rút các cửa sổ đó từ 1,69% lên 25%, chia đều khối lượng xác suất giữa các đợt; checkpoint tốt nhất ở epoch 11. Validation và test không được lấy mẫu lại.

Quy tắc chọn biến thể chỉ đọc validation; dự báo test được tính sau khi chọn. Standard có F1 mưa lớn validation 0,274 so với 0,094 của event balanced, và RMSE 0,939 so với 0,970 mm/h. Vì thế checkpoint được chọn là **standard**.

| Phương pháp, cùng tập test | MAE ↓ | RMSE ↓ | R² ↑ | CC ↑ | MAE mưa >5 ↓ | F1 mưa >5 ↑ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Luôn dự báo 0 | **0,265** | 1,157 | −0,055 | không xác định | 9,661 | 0,000 |
| Giữ nguyên lượng mưa giờ cuối | 0,285 | 1,190 | −0,116 | 0,442 | 7,132 | **0,262** |
| Bi-LSTM standard, được chọn | 0,326 | **0,999** | **0,214** | **0,501** | **6,733** | 0,236 |
| Bi-LSTM event balanced | 0,295 | 1,048 | 0,135 | 0,389 | 7,798 | 0,106 |

Các chỉ số hồi quy gộp sáu horizon. F1 dùng điều kiện dự báo **>5 mm/h** trên từng cặp horizon–giờ; không phải F1 trên các đợt mưa độc lập. MAE thấp của dự báo 0 phản ánh lớp giờ không mưa áp đảo, vì thế cần xem đồng thời RMSE, sai số mưa lớn và F1. Bi-LSTM standard giảm RMSE so với cả hai đối chứng, nhưng MAE toàn tập kém hơn và F1 thấp hơn persistence. Trong 702 cặp mưa lớn, standard chỉ phát hiện đúng 144 cặp (recall 20,5%); mưa thực tế trung bình 9,66 mm/h, dự báo trung bình 3,03 mm/h. Đây là **baseline nghiên cứu, chưa dùng để cảnh báo mưa lớn**.

Sampler 25% làm kết quả mưa lớn và F1 xấu đi. Đây là kết quả âm của cấu hình đã thử, chưa đủ để kết luận mọi cách lấy mẫu sự kiện đều không hiệu quả. Nếu thử tỷ lệ hoặc hàm mất mát khác, cần chọn bằng validation, giữ test này cho báo cáo cuối.

## Quan hệ với kết quả đa nguồn

Trong thí nghiệm trước đó **trên cùng các giờ có ERA5 PL850**, Bi-LSTM chỉ dùng bề mặt đạt RMSE 1,183 mm/h, còn đa nguồn đạt 1,146 mm/h (cải thiện khoảng 3,1%); các file là `models/ablation_surface_only_results.json` và `models/training_summary.json`. Kết quả 0,999 mm/h của nhánh đầy đủ ở bảng trên có **khoảng test khác** nên không được so trực tiếp với 1,146 mm/h để suy ra giá trị của ERA5. Nhánh hiện tại cho phép tiếp tục nghiên cứu khi chưa tải bù 15 tháng PL850.

Đây là đánh giá hồi cứu trên dữ liệu Open-Meteo historical. Để tuyên bố hiệu năng dự báo thời gian thực, cần kiểm tra nguồn bề mặt thực sự có sẵn tại thời điểm phát hành từng dự báo và đánh giá trên luồng dữ liệu vận hành.

Đã bổ sung [cổng kiểm toán thời điểm có sẵn](reports/realtime_readiness/READINESS.md), bộ ghi dự báo mới theo từng lần phát hành và [hướng dẫn nhập/đánh giá mưa trạm](reports/independent_observations/GAUGE_IMPORT_GUIDE.md). File hiện tại thiếu `issued_at` và `available_at`, nên cổng báo **chưa xác minh thời gian thực**; chưa có dữ liệu Vrain theo giờ để chạy đánh giá độc lập chính.

Đánh giá chi tiết theo từng horizon, tháng và đợt mưa có trong `reports/surface_only/EVALUATION_REPORT.md`. Ở +1 giờ persistence có RMSE 0,858 mm/h, tốt hơn Bi-LSTM 0,904; ở +6 giờ Bi-LSTM chỉ phát hiện 2/44 đợt mưa >5 mm/h. Đã kiểm tra trạm NOAA trong [báo cáo quan trắc độc lập](reports/independent_observations/NOAA_AUDIT.md): có tổng mưa 6 giờ, chưa có chuỗi 1 giờ đủ để đánh giá chính. [Thí nghiệm Bi-LSTM hai đầu](reports/rain_alert_experiment/EXPERIMENT_REPORT.md) cải thiện recall mưa lớn so với baseline này, nhưng event F1 test vẫn thấp hơn persistence.

## File và cách chạy

- Runner: `run_surface_baseline.py` (mặc định chạy cả hai biến thể; `--prepare-only` chỉ tạo dữ liệu và đối chứng).
- Scaler và checkpoint: `models/surface_only/scaler.pkl`, `models/surface_only/best_surface_model.pth`.
- Chẩn đoán và so sánh: `data/processed/surface_only/window_diagnostics.json`, `models/surface_only/comparison.json`.
- Bốn hình 300 DPI của model được chọn: `plots/surface_only/standard/plot1_feature_correlation.png` đến `plot4_residuals_scatter.png`.

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
.\.venv\Scripts\python.exe run_surface_baseline.py --prepare-only
.\.venv\Scripts\python.exe run_surface_baseline.py --device cuda
```

Hai biến môi trường giới hạn BLAS threads để tránh lỗi bộ nhớ phân trang trên máy Windows này. Lệnh cuối **huấn luyện lại** và ghi đè các checkpoint/hình trong `models/surface_only` và `plots/surface_only`; kết quả hiện tại đã có sẵn.
