# Thử cải thiện dự báo ngắn hạn ngày 24/11/2026

Trên các ca Vrain đo được từ 50 mm/24 giờ trong hồi cứu 2026, điều chỉnh lượng mưa có điều kiện giảm MAE ở cả ba hạn. Mức giảm nằm trong khoảng 3,91–6,47 mm. RMSE tính trên toàn bộ mẫu chưa giảm nhất quán. Dự báo xác suất giữ nguyên. Web dùng LightGBM B làm mặc định.

## Ba phép thử

| Phép thử | Thay đổi | Quyết định |
| --- | --- | --- |
| Bổ sung bối cảnh GFS lân cận | Thêm trung bình và cực đại mưa GFS trong bán kính 25 và 50 km, tính từ các dự báo GFS sẵn có tại 57 vị trí, gồm vị trí đang dự báo. | Ngày 2 giảm RMSE 0,10 mm. Khoảng đồng thời 95% từ −0,36 đến +0,14 mm. BS cho ngưỡng 50 mm tăng nhẹ ở cả ba hạn. |
| Tăng trọng số mẫu mưa lớn | Trong đầu dự báo lượng, dùng trọng số `1 + α × min(y/50, 1)` với `α ∈ {0, 0.5, 1}`. Giữ nguyên biến và ngân sách cây của B. | Hai mức tăng trọng số đều vượt giới hạn tăng dự báo thừa 0,50 mm trên ngày khô trong CV 2022. CV chọn `α = 0`. |
| Điều chỉnh lượng có điều kiện | Huấn luyện đầu lượng có trọng số `α = 1` bằng dữ liệu 2021–2024. Mức tăng từ đầu lượng này được nhân với `clip((B − θ)/20, 0, 1)`. Thử `θ` bằng 5, 10 và 20 mm trên CV 2022. | CV chọn `θ = 5 mm` trong các cấu hình thỏa hai giới hạn. Bên dưới 5 mm và tại 5 mm, lượng dự báo giữ nguyên. Từ 25 mm trở lên, dự báo lấy giá trị lớn hơn giữa B và đầu lượng có trọng số. |

CV theo quý 2022 dùng tập huấn luyện đứng trước tập đánh giá và có khoảng đệm 7 ngày. Hai giới hạn là RMSE macro được tăng tối đa 0,25 mm và bias ngày khô được tăng tối đa 0,50 mm. Trong tập phương án đạt giới hạn, cấu hình có MAE thấp nhất ở ca thực đo từ 50 mm được ưu tiên, sau đó xét RMSE macro. Phép thử lân cận hiệu chỉnh xác suất trên 2025 giống vai trò dữ liệu của B. Phép thử điều chỉnh lượng giữ nguyên các đầu xác suất của B.

## Kết quả điều chỉnh lượng

Chấm cùng 43.464 lượt trạm và khoảng dự báo, gồm 14.488 lượt ở mỗi hạn. Đơn vị lượng mưa là mm/24 giờ. RMSE macro là trung bình RMSE của các trạm.

| Hạn | Lượt thực đo ≥50 mm | MAE ca ≥50 mm của B | MAE ca ≥50 mm sau điều chỉnh | Chênh MAE và khoảng đồng thời 95% | Chênh RMSE macro toàn bộ |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ngày 1 | 600 | 52,61 | **48,70** | **−3,91** [−5,84 đến −1,47] | −0,07 |
| Ngày 2 | 604 | 57,65 | **52,09** | **−5,56** [−7,14 đến −2,34] | +0,20 |
| Ngày 3 | 603 | 72,14 | **65,67** | **−6,47** [−8,37 đến −2,96] | −0,25 |

Khoảng đồng thời trên nhóm thực đo ≥50 mm là phân tích thăm dò bổ sung. Dùng 5.000 lượt bootstrap ghép cặp theo khối 14 ngày, có hiệu chỉnh Bonferroni cho ba hạn. Khoảng đồng thời của chênh RMSE macro toàn bộ chứa 0 ở cả ba hạn. MAE gộp toàn bộ lượt tăng ở ba hạn. Bias ngày khô tăng lần lượt 0,12, 0,18 và 0,23 mm.

Cấu hình điều chỉnh phù hợp để tiếp tục kiểm chứng khi ưu tiên sai số lượng ở ca mưa lớn. Nó chỉ tăng lượng khi B đã dự báo mưa vượt 5 mm, nên ít tác động tới các ca B bỏ sót sâu. Trong lượt phát 12/11, hai ca ngày 1 thực đo 50,6 và 52,4 mm chỉ tăng lần lượt khoảng 0,11 và 0,23 mm. Hồi cứu 2026 đã được xem ở vòng trước. Cần phát dự báo cả hai cấu hình và ghi thời gian trước khi nhãn xuất hiện để kiểm định trên các đợt mưa mới. Bằng chứng chính trong báo cáo cuối kỳ vẫn là chênh lệch giữa nhóm biến N1 và N0 trên [kiểm định 2025 đã khóa](../gfs_short_range_closeout_2026_11_24/KET_LUAN_NGAN_HAN.md).

## Chẩn đoán mưa lớn bị bỏ sót

Dùng cùng hồi cứu 2026 và ngưỡng xác suất đã khóa của B. Trong 325, 311 và 248 lượt bỏ sót mưa ≥50 mm ở ngày 1, 2 và 3, lần lượt có 45, 41 và 65 lượt cả GFS và B đều dự báo dưới 10 mm. Riêng ngày 3, GFS dự báo dưới 10 mm ở 158 trong 248 lượt bỏ sót. Đây là phép đếm theo ngưỡng đọc dữ liệu, không phải tham số mới của mô hình. Nhóm này phù hợp để thử thêm tín hiệu độc lập, chẳng hạn độ phân tán và tỷ lệ thành viên GEFS báo mưa, rồi so với B trên các kỳ đủ dữ liệu cùng giờ phát. [Bảng số](missed_signal.csv), [mã tính](../../scripts/diagnose_gfs_heavy_misses.py).

Thử nguồn GEFS đã đọc được 24 chỉ mục mưa chọn ở bốn ngày mẫu thuộc các năm 2021, 2024, 2025 và 2026. Đã giải mã đủ 12 bản tin của ba thành viên trong lượt 12/11/2026, cộng bốn khoảng sáu giờ để lấy đúng cửa sổ ngày 1. Tại hai trạm thực đo ≥50 mm bị bỏ sót, có thành viên dự báo nhiều mưa hơn B và các thành viên đã thử đều dưới 50 mm. Đây là kiểm tra truy cập và cách cộng mưa theo kỳ. Độ phủ toàn giai đoạn và lợi ích mô hình cần kiểm tra trên tập đủ thành viên và nhiều ngày. [Nguồn GEFS của NOAA](https://www.ncei.noaa.gov/products/weather-climate-models/global-ensemble-forecast).

## Dấu vết thí nghiệm

- GFS lân cận có [thiết kế](../gfs_neighborhood_2026_11_24/protocol.json), [RMSE và BS theo hạn](../gfs_neighborhood_2026_11_24/paired_comparisons.csv) và [kiểm chứng](../gfs_neighborhood_2026_11_24/verification.json).
- Trọng số toàn bộ có [thiết kế](../gfs_weighted_amount_2026_11_24/protocol.json), [bảng chọn bằng CV](../gfs_weighted_amount_2026_11_24/train_only_selection.csv) và [kiểm chứng](../gfs_weighted_amount_2026_11_24/verification.json).
- Điều chỉnh lượng có điều kiện có [thiết kế](protocol.json), [bảng chọn bằng CV](train_only_selection.csv), [sai số theo nhóm mưa](amount_metrics.csv), [RMSE toàn bộ](paired_comparisons.csv), [MAE nhóm ≥50 mm](tail_mae_paired.csv) và [kiểm tra độc lập](independent_verification.json).
- Mã chạy lần lượt là [lân cận](../../scripts/run_gfs_neighborhood.py), [trọng số](../../scripts/run_gfs_weighted_amount.py) và [điều chỉnh lượng](../../scripts/run_gfs_gated_amount.py). Các phép chạy cần dữ liệu và mô hình đã khóa trong vùng nội bộ. Các bảng công khai chứa số tổng hợp.
- Khi có các dự báo nội bộ đã lưu, chạy `python scripts/verify_gfs_rain_improvements.py` để tính lại bảng RMSE, BS và khoảng bất định của MAE nhóm mưa lớn.
