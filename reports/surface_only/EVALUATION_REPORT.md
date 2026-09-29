# Đánh giá chi tiết Bi-LSTM bề mặt trên tập test

## Thiết lập

Chạy `evaluate_surface_baseline.py` từ checkpoint đã chọn `models/surface_only/best_surface_model.pth`; **không huấn luyện hoặc chọn lại mô hình**. Tập test có 15.335 cửa sổ 24→6 giờ, tương ứng 92.010 cặp horizon–giờ. Theo từng horizon có 15.335 giờ hiệu lực, 117 giờ mưa >5 mm/h và **44 đợt theo định nghĩa bên dưới**. Khoảng test: 2024-12-01 03:00 đến 2026-09-01 06:00, giờ Đà Nẵng.

Đối chứng `persistence` giữ nguyên lượng mưa ở giờ quan sát cuối của từng cửa sổ; `zero` luôn dự báo 0. Các đối chứng dùng đúng cùng giờ và nhãn với Bi-LSTM.

## Kết quả theo giờ dự báo

| Horizon | RMSE Bi-LSTM | RMSE persistence | Recall giờ mưa >5 Bi-LSTM | Recall giờ mưa >5 persistence | Đợt mưa Bi-LSTM phát hiện |
| ---: | ---: | ---: | ---: | ---: | ---: |
| +1 giờ | 0,904 | **0,858** | 46,2% | 45,3% | 13/44 (29,5%) |
| +2 giờ | **0,965** | 1,109 | 26,5% | 33,3% | 11/44 (25,0%) |
| +3 giờ | **1,016** | 1,223 | 20,5% | 23,9% | 9/44 (20,5%) |
| +4 giờ | **1,019** | 1,268 | 10,3% | 19,7% | 7/44 (15,9%) |
| +5 giờ | **1,038** | 1,296 | 12,8% | 17,1% | 5/44 (11,4%) |
| +6 giờ | **1,044** | 1,323 | 6,8% | 17,9% | 2/44 (4,5%) |

Đơn vị RMSE là mm/h. Các chỉ số khác gồm MAE, R², CC, precision, F1, FAR và CSI nằm trong `metrics_by_horizon.csv`. **Ở +1 giờ, persistence có RMSE tốt hơn Bi-LSTM**; từ +2 đến +6 giờ Bi-LSTM giảm RMSE nhưng tỷ lệ phát hiện mưa lớn rất thấp ở các horizon xa. Đỉnh thật trung bình của 44 đợt là 10,65 mm/h; dự báo đỉnh trong cùng khoảng đợt chỉ đạt trung bình 3,45 mm/h ở +1 giờ và 1,74 mm/h ở +6 giờ.

## Định nghĩa đợt mưa và độ độc lập

Một đợt gồm các giờ mưa **>5 mm/h** cách nhau không quá 6 giờ, miễn là không thiếu giờ quan trắc ở giữa. Khoảng đợt đi từ giờ vượt ngưỡng đầu tới giờ vượt ngưỡng cuối. Một đợt dự báo được ghép với tối đa **một** đợt thật nếu hai khoảng này chồng nhau; phép đo này cho phép lệch thời điểm trong nội bộ cùng đợt, nhưng không có dung sai ngoài khoảng đợt. Ghép cực đại theo số đợt trúng để một cảnh báo dài không được tính trúng nhiều đợt thật.

**Mỗi horizon chỉ lấy một dự báo cho mỗi giờ hiệu lực**. Vì vậy 44 đợt ở +1 giờ không bị nhân sáu do sáu horizon cùng dự báo một thời điểm. Các chỉ số gộp horizon hoặc theo tháng/mùa vẫn là chỉ số trên *cặp horizon–giờ*, không phải trên số giờ độc lập.

## Biến thiên theo tháng và mùa

`metrics_by_month.csv` và `metrics_by_season.csv` dùng giờ địa phương, với DJF/MAM/JJA/SON là các quý khí tượng. Trong tập test, SON có 318/702 cặp mưa lớn >5 mm/h, JJA có 306, MAM có 72 và DJF có 6. Riêng tháng 10 có 210/702 cặp, RMSE Bi-LSTM 2,286 mm/h và recall giờ mưa lớn 9,5%. Test chỉ chứa **một tháng 10**, nên các con số này mô tả đúng tập test hiện tại, không suy ra quy luật khí hậu dài hạn. Số cặp giữa các quý cũng không bằng nhau.

Tháng không có mưa thật >5 mm/h được để trống recall/F1/CSI thay vì ghi 0 vì các chỉ số phát hiện mưa khi đó không xác định.

## Quan trắc độc lập

Sau báo cáo baseline, đã tải và kiểm tra NOAA GHCNh/ISD của Đà Nẵng. GHCNh năm 2025 có 216 kỳ mưa trạm tích lũy 6 giờ, nhưng **không có giá trị mưa 1 giờ**; ISD cũng không có kỳ tích lũy 1 giờ. Đã đối chiếu phụ các kỳ 6 giờ trong [báo cáo NOAA](../independent_observations/NOAA_AUDIT.md). Vì thiếu các giờ khô và quy ước timestamp trạm còn cần xác nhận, đối chiếu đó không thay cho phép đánh giá theo giờ. Target Open-Meteo được tải từ Historical Weather API, tức dữ liệu mô hình/tái phân tích. `observation_audit.json` phản ánh thời điểm chạy đánh giá baseline trước khi tải dữ liệu NOAA.

Khi có file quan trắc, chạy:

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
.\.venv\Scripts\python.exe evaluate_surface_baseline.py --device auto `
  --observations-csv 'C:\duong-dan\tram-mua.csv' `
  --observations-source 'Tên trạm và đơn vị cung cấp'
```

CSV phải có `datetime` với UTC offset (ví dụ `2025-10-01T07:00:00+07:00`) và `precipitation_mm_h` không âm. Giờ trong file cần biểu thị **cùng khoảng tích lũy một giờ** với giờ hiệu lực của Open-Meteo; chương trình không tự dịch giờ hay nội suy. Báo cáo độc lập chỉ dùng phần thời gian giao nhau và lưu riêng dưới tên `independent_*`. Cần xác minh tọa độ, quy ước giờ và chất lượng số đo trước khi diễn giải.

## Tệp đầu ra

- `test_predictions.parquet`: giờ cuối của input, giờ hiệu lực, nhãn và ba dự báo cho từng horizon. Giờ cuối input chưa phải thời điểm dữ liệu archive thực sự có sẵn để phát hành dự báo.
- `metrics_by_horizon.csv`, `metrics_by_month.csv`, `metrics_by_season.csv`: chỉ số theo giờ dự báo và lịch.
- `event_metrics_by_horizon.csv`, `observed_events_t_plus_1.csv`: chỉ số theo đợt và chi tiết 44 đợt ở +1 giờ.
- `plot_horizon_and_event_skill.png`: hình 300 DPI cho báo cáo.
- `evaluation_manifest.json`: checkpoint, hash, định nghĩa ngưỡng/đợt và độ phủ.

Kết quả test này dùng để chẩn đoán. Khi thử mô hình hay ngưỡng mới, chọn cấu hình bằng validation; nên dành dữ liệu tương lai mới cho lần xác nhận cuối nếu có thể.
