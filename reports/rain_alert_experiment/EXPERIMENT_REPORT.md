# Thí nghiệm Bi-LSTM hai đầu ra cho mưa lớn 1–6 giờ

## Thiết kế

Dùng đúng 24 giờ đầu vào, 22 đặc trưng bề mặt và các split thời gian của baseline (71.531/15.335/15.335 cửa sổ train/validation/test). Hai đầu ra chung Bi-LSTM hai tầng: lượng mưa không âm và xác suất lượng mưa **>5 mm/h** ở từng horizon. Loss gồm Huber có trọng số 4 cho giờ mưa lớn và BCE có `pos_weight=12` (hệ số BCE 0,5). Adam 0,001; patience 7. Huấn luyện bằng CUDA trên GTX 1650; checkpoint theo validation loss tốt nhất ở **epoch 2**, dừng ở epoch 9.

Ngưỡng xác suất được quét 0,05–0,95, chọn **0,40 bằng event F1 gộp trên validation** trước khi suy luận test. Với một horizon, các giờ mưa >5 mm/h cách nhau tối đa 6 giờ tạo một đợt. Ghép dự báo và đợt thật một đối một theo phần thời gian giao nhau. Chỉ số gộp event là tổng đợt qua sáu horizon, tức cùng một hiện tượng vật lý có thể xuất hiện trong sáu phép đánh giá; các horizon cần được đọc riêng.

## Kết quả cùng tập test

| Phương pháp | RMSE mm/h ↓ | MAE mm/h ↓ | Recall giờ mưa lớn ↑ | Precision giờ mưa lớn ↑ | Event F1 ↑ | Đợt phát hiện / tổng đợt |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Bi-LSTM hai đầu, ngưỡng 0,40 | **0,996** | **0,255** | **47,2%** | 17,1% | 0,258 | 71/264 |
| Bi-LSTM chuẩn, dự báo >5 mm/h | 0,999 | 0,326 | 20,5% | **27,7%** | 0,240 | 47/264 |
| Persistence | 1,190 | 0,285 | 26,2% | 26,2% | **0,280** | **74/264** |

Có 702 cặp horizon–giờ mưa lớn trên 92.010 cặp test (0,763%). Hai đầu ra làm recall giờ mưa lớn tăng từ 144/702 lên 331/702 và phát hiện thêm 24 lượt đợt theo horizon so với Bi-LSTM chuẩn; đổi lại cảnh báo sai theo giờ tăng từ 375 lên **1.600**. RMSE chỉ giảm 0,003 mm/h; event F1 vẫn kém persistence. Xác suất mưa lớn có average precision 0,161; Brier score 0,0137. Brier score nên đọc cùng tỷ lệ sự kiện hiếm và chưa chứng minh xác suất đã hiệu chỉnh tốt.

| Horizon | Hai đầu: đợt phát hiện/44 | Bi-LSTM chuẩn | Persistence |
| ---: | ---: | ---: | ---: |
| +1 giờ | 13 | 13 | 19 |
| +2 giờ | 12 | 11 | 15 |
| +3 giờ | 11 | 9 | 11 |
| +4 giờ | 12 | 7 | 11 |
| +5 giờ | 12 | 5 | 9 |
| +6 giờ | 11 | 2 | 9 |

Ở +4 đến +6 giờ, đầu phân loại giữ được recall đợt cao hơn Bi-LSTM chuẩn, nhưng số cảnh báo cũng nhiều hơn. Ở +1 giờ, persistence vẫn mạnh nhất về phát hiện đợt. Chưa nên thay mô hình vận hành hay gọi đây là cải thiện chắc chắn về cảnh báo; cần xác nhận trên nhãn quan trắc độc lập theo giờ và một giai đoạn tương lai mới. Chỉ số test hiện tại dùng nhãn Open-Meteo historical, không phải kiểm chứng dự báo phát hành thời gian thực. [Kiểm toán NOAA](../independent_observations/NOAA_AUDIT.md) có 216 kỳ mưa trạm 6 giờ để đối chiếu phụ, nhưng không có chuỗi 1 giờ đủ phủ.

## Tái lập và tệp đầu ra

Chạy từ thư mục gốc dự án (lệnh sẽ huấn luyện lại checkpoint hai đầu):

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
.\.venv\Scripts\python.exe run_rain_alert_experiment.py --device cuda
```

Checkpoint `models/surface_only/rain_alert_dual_head.pth`; tập dự báo có timestamp `test_predictions.parquet`; quá trình học `training_history.csv`; kiểm tra ngưỡng `validation_threshold_sweep.csv`; chỉ số `validation_summary.json`, `test_summary.json`; đồ thị 300 DPI `plot_rain_alert_skill.png`. Checkpoint Bi-LSTM chuẩn được giữ nguyên. Không điều chỉnh tiếp cấu hình theo kết quả test này; nếu thử phương án khác, cần chọn trên validation và xác nhận trên dữ liệu mới.
