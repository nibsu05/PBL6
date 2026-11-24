# Kết quả hoàn chỉnh LightGBM, TFT và Informer — 28/10/2026

Đã chạy thêm **54 lượt Informer E1–E6**, cùng hàm fit và protocol pilot. Dùng lại **18 lượt E0/E7**; tổng **72 Informer**, cùng 72 TFT và 24 pipeline LightGBM đã có. Đủ **168 lượt mô hình/pipeline** và **72 dòng chính** = tám E × ba mô hình × ba ngày. Không mở test 2025, không tuning hoặc thay bước gộp sáu giờ.

Độc lập phát lại đủ 72 checkpoint Informer trên 144 split calibration/evaluation; tái tạo scaler train và calibration. E0/E7 Informer và toàn bộ điểm TFT/LightGBM giữ nguyên. Có cùng 1.075 mốc/hạn, nhãn, tham chiếu Brier và quy trình chọn ngưỡng trên calibration.

## Kết quả E7: cùng 44 biến, đủ ba mô hình

### Ngày 1

| Mô hình | RMSE ↓ | MAE ↓ | Bias ≈0 | BS ↓ | BSS ↑ | CSI ↑ | POD ↑ | FAR ↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LightGBM | 17.706 | 5.731 | -2.003 | 0.058 | 0.303 | 0.411 | 0.526 | 0.348 |
| TFT | 20.361 | 6.695 | -2.710 | 0.062 | 0.246 | 0.406 | 0.640 | 0.475 |
| Informer | 20.486 | 6.810 | -2.659 | 0.060 | 0.278 | 0.440 | 0.614 | 0.391 |

### Ngày 2

| Mô hình | RMSE ↓ | MAE ↓ | Bias ≈0 | BS ↓ | BSS ↑ | CSI ↑ | POD ↑ | FAR ↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LightGBM | 20.756 | 7.238 | -2.551 | 0.079 | 0.043 | 0.277 | 0.456 | 0.587 |
| TFT | 21.018 | 7.566 | -2.105 | 0.080 | 0.028 | 0.257 | 0.509 | 0.659 |
| Informer | 21.190 | 7.717 | -2.069 | 0.081 | 0.025 | 0.239 | 0.447 | 0.660 |

### Ngày 3

| Mô hình | RMSE ↓ | MAE ↓ | Bias ≈0 | BS ↓ | BSS ↑ | CSI ↑ | POD ↑ | FAR ↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LightGBM | 21.742 | 7.666 | -2.900 | 0.089 | -0.075 | 0.203 | 0.482 | 0.741 |
| TFT | 21.321 | 8.104 | -1.565 | 0.086 | -0.038 | 0.201 | 0.412 | 0.719 |
| Informer | 21.347 | 8.051 | -1.797 | 0.084 | -0.019 | 0.216 | 0.456 | 0.709 |

LightGBM E7 ngày 1–2 có nhiều điểm tốt hơn; Informer CSI cao nhất ngày 1, TFT POD cao nhất ngày 1 nhưng báo nhầm nhiều hơn. Cả ba E7 ngày 3 BSS âm. Riêng Informer E6 ngày 3 có BSS khoảng +0,004, tương ứng giảm khoảng 0,4% sai số Brier; điểm dương nhỏ này chưa đủ để khẳng định kỹ năng chắc chắn. Các mô hình có thể có lợi ở E khác nhau; không chọn kiến trúc hoặc nhóm biến chỉ từ một điểm đẹp.

## Đọc bảng nhóm biến và độ bất định

E0=B; E1=B+A; E2=B+M; E3=B+C; E4=B+A+M; E5=B+A+C; E6=B+M+C; E7=B+A+M+C. Số biến lần lượt 11/23/31/12/43/24/32/44. Nhóm C chỉ là SST hộp biển, không phải đã kiểm tra ENSO/MJO đầy đủ.

CI mới dùng 20.000 bootstrap khối bảy ngày và độ nhạy 14 ngày, giữ chung mẫu giữa mô hình, ngưỡng và các ngày; lấy mẫu trong từng năm. Đây là **CI95% mô tả**, chưa hiệu chỉnh nhiều phép và có điều kiện trên mô hình đã fit. Chúng không bao trùm toàn bộ bất định huấn luyện hoặc nhãn. Thêm biến cũng có thể làm đổi số tham số mạng, cần công bố khi diễn giải hiệu ứng nhóm. Phép thử TFT chính với CI điều chỉnh gia đình chín phép vẫn giữ riêng; không đổi phân tích mới thành kiểm định xác nhận. Kiểm định cuối 2025 chưa mở.

## Lịch, chín xác suất và bước sáu giờ

Bốn biến lịch là sin_hour/cos_hour/sin_doy/cos_doy, biểu diễn hai chu kỳ giờ trong ngày và ngày trong năm theo giờ Việt Nam. Decoder chỉ biết lịch tương lai, không biết ERA5 tương lai. 72 giờ tương lai tạo 12 khối sáu giờ × bốn biến lịch.

Đầu ra có ba lượng mm/24h và chín xác suất: ba ngày × ba sự kiện đạt 16/50/100 mm. Các sự kiện lồng nhau, không cộng ba xác suất thành 100%; xác suất nói về tổng mưa trung bình vùng, không phải phần trăm diện tích có mưa. Ngưỡng nghiên cứu này không tự là cấp cảnh báo hành chính.

Gộp sáu giờ là lấy trung bình đặc trưng khí tượng để giảm 168 giờ lịch sử còn 28 bước. Nhãn vẫn cộng 24 giờ để tạo tổng ngày. Chưa có đối chứng cùng điều kiện 1h/3h/6h để chứng minh sáu giờ tối ưu hoặc không mất đỉnh CAPE/gió/ẩm. Các kết quả mới vẫn có điều kiện trên lựa chọn sáu giờ đã khóa.

## Seed, LightGBM và BSS

TFT/Informer có ba seed 42/43/44: cùng dữ liệu/cấu hình nhưng khác khởi tạo và thao tác ngẫu nhiên khi học. Báo cáo dùng trung bình dự đoán ba seed rồi tính metric, không chọn seed đẹp nhất; ba seed không tạo thêm ngày thời tiết. LightGBM hiện chạy xác định nên mỗi E/năm có một pipeline.

LightGBM là mô hình tham chiếu để so sánh, không phải mô hình buộc TFT phải thắng. Trọng tâm là đóng góp đặc trưng và đánh giá các pipeline cùng điều kiện. Cây dùng thống kê lịch sử, mạng dùng chuỗi; chưa cô lập riêng ảnh hưởng kiến trúc.

BSS = 1 − BS_mô_hình/BS_khí_hậu. BSS=0,03 là giảm 3% sai số Brier; BSS=−0,038 là tăng 3,8% sai số Brier, không phải tỷ lệ ngày dự đoán sai. BSS âm chỉ kết luận cho xác suất ở ngưỡng, hạn và tập đang xét. POD cao không tự bảo đảm BSS dương.

## Giới hạn và bước tiếp

Footprint 93 toàn ô, diện tích khoảng 11.074 km², còn xấp xỉ địa giới Đà Nẵng mới. Nhãn GSMaP Gauge và provenance khí tượng cần tiếp tục QC. Đủ ma trận không có nghĩa đã xong kiểm chứng ranh/nhãn hoặc chứng minh vận hành. Khóa thiết kế trước holdout; không sửa ngưỡng hay chọn cấu hình theo test 2025.
