# So sánh LightGBM, TFT và Informer trên cùng điều kiện

Informer hiện **chưa chạy E1–E6**. TFT đã có 72 lượt E0–E7; LightGBM 24 pipeline E0–E7; Informer 18 lượt E0/E7. Còn 54 lượt Informer để đủ toàn ma trận. Lượt cập nhật này chỉ tổng hợp aggregate đã kiểm chứng, không huấn luyện mới hoặc mở test 2025.

So mô hình cần đặt đủ ba trong cùng E, cùng ngày, cùng mẫu, nhãn, mùa, ngưỡng mưa và quy trình chọn ngưỡng xác suất trên calibration. Không cần huấn luyện cùng lúc hoặc chạy lại LightGBM/TFT. TFT và Informer là trung bình dự đoán ba seed; LightGBM hiện chạy xác định. Cùng nguyên liệu nhưng LightGBM dùng thống kê lịch sử, mạng dùng chuỗi, nên đây là so pipeline chứ chưa cô lập riêng kiến trúc.

Mỗi hạn có 1.075 mốc đánh giá gộp 2021–2023; 114 sự kiện vùng từ 16 mm/24 giờ. Các bảng dưới gộp toàn năm. Tách mùa vẫn có ở báo cáo nguồn; không đổi phạm vi thành chỉ mùa mưa.

## E7, ngày 1

| Mô hình | RMSE ↓ | MAE ↓ | Bias ≈0 | BS ↓ | BSS ↑ | CSI ↑ | POD ↑ | FAR ↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LightGBM | 17.706 | 5.731 | -2.003 | 0.058 | 0.303 | 0.411 | 0.526 | 0.348 |
| TFT | 20.361 | 6.695 | -2.710 | 0.062 | 0.246 | 0.406 | 0.640 | 0.475 |
| Informer | 20.486 | 6.810 | -2.659 | 0.060 | 0.278 | 0.440 | 0.614 | 0.391 |

LightGBM tốt hơn về RMSE, MAE, BSS và FAR.
Informer có CSI cao nhất; TFT có POD cao nhất.

## E7, ngày 2

| Mô hình | RMSE ↓ | MAE ↓ | Bias ≈0 | BS ↓ | BSS ↑ | CSI ↑ | POD ↑ | FAR ↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LightGBM | 20.756 | 7.238 | -2.551 | 0.079 | 0.043 | 0.277 | 0.456 | 0.587 |
| TFT | 21.018 | 7.566 | -2.105 | 0.080 | 0.028 | 0.257 | 0.509 | 0.659 |
| Informer | 21.190 | 7.717 | -2.069 | 0.081 | 0.025 | 0.239 | 0.447 | 0.660 |

LightGBM tốt hơn ở nhiều chỉ số; TFT có POD cao nhất.
Mọi BSS đều dương nhưng chỉ còn khoảng 0,025–0,043.

## E7, ngày 3

| Mô hình | RMSE ↓ | MAE ↓ | Bias ≈0 | BS ↓ | BSS ↑ | CSI ↑ | POD ↑ | FAR ↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LightGBM | 21.742 | 7.666 | -2.900 | 0.089 | -0.075 | 0.203 | 0.482 | 0.741 |
| TFT | 21.321 | 8.104 | -1.565 | 0.086 | -0.038 | 0.201 | 0.412 | 0.719 |
| Informer | 21.347 | 8.051 | -1.797 | 0.084 | -0.019 | 0.216 | 0.456 | 0.709 |

Cả ba BSS đều âm: chưa vượt khí hậu về xác suất.
Một chỉ số tốt hơn không đủ để kết luận dự báo ngày 3 đã tốt.

## Kết luận và phần còn thiếu

LightGBM E7 ngày 1–2 có nhiều điểm tốt hơn TFT/Informer; không được bỏ đối chứng này khỏi kết luận. Informer ngày 1 có CSI cao nhất, TFT có POD cao nhất; ưu thế POD phải đọc cùng FAR. Ngày 3 cả ba BSS âm, chưa vượt khí hậu tham chiếu. Chữ đậm chỉ là điểm tốt nhất trong phép so đủ ba, chưa chứng minh chênh lệch có ý nghĩa thống kê.

Chưa có kết quả riêng nhóm A/M/C của Informer vì thiếu E1–E6; không lấy kết quả TFT để khẳng định các nhóm có ích với mọi kiến trúc. Chưa tuning hoặc kiểm định chênh lệch ba pipeline, chưa chốt ranh/QC nhãn và chưa mở holdout 2025. Ma trận CSV có 72 vị trí dự kiến, 54 có kết quả và 18 vị trí Informer chưa chạy; số vị trí bảng không phải số lượt huấn luyện.

## Giải thích dữ liệu, nhóm biến, seed và metrics

Phần dưới giữ giải thích đầy đủ từ báo cáo trước. Các bảng so sánh ba mô hình ở đầu tài liệu này và slide mới là bản cập nhật; các ví dụ một mô hình minh họa công thức không phải xếp hạng mô hình.

# Giải thích lại theo các câu hỏi của nhóm

## 1. Bốn nhóm biến gồm những gì?

| Nhóm | Số biến | Thông tin |
| --- | --- | --- |
| B — Nền | 11 | Nhiệt độ, điểm sương, độ ẩm gần mặt đất; áp suất bề mặt và mực biển; hai thành phần gió 10 m; bốn biến mã hóa giờ và ngày trong năm |
| A — Đối lưu, mây, lớp biên, đất | 12 | CAPE, CIN, has_lfc, hơi nước cột TCWV, K-index, Total Totals, độ cao lớp biên, bốn loại độ che phủ mây và độ ẩm đất lớp 1 |
| M — Hoàn lưu và vận chuyển ẩm | 20 | Gió, độ ẩm, nhiệt độ, chuyển động thẳng đứng ở 850/500 hPa; đứt gió; dòng vận chuyển ẩm IVT; phân kỳ dòng ẩm; bối cảnh hơi nước/dòng ẩm; hai biến chênh áp |
| C — Nhiệt độ biển | 1 | SST trung bình tại hộp biển đã chọn |

E0 chỉ B; E1 B+A; E2 B+M; E3 B+C; E4 B+A+M; E5 B+A+C; E6 B+M+C; E7 B+A+M+C. E0–E7 là tám bộ đầu vào, không phải tám mô hình. TFT/LightGBM là các cách học từ từng bộ đầu vào. Nhóm C hiện chỉ một biến SST, chưa đại diện đầy đủ ENSO/MJO.

## 2. Bảng metrics đầy đủ

| Chỉ số | Ý nghĩa dễ hiểu | Vì sao dùng? | Chiều tốt |
| --- | --- | --- | --- |
| RMSE | Sai số lượng mưa, phạt mạnh lỗi lớn | Không để những ngày dự đoán sai nặng bị che khuất | Nhỏ hơn |
| MAE | Trung bình sai lệch tuyệt đối bao nhiêu mm | Dễ đọc mức sai số lượng mưa | Nhỏ hơn |
| Bias | Trung bình dự báo thừa hay thiếu | Phát hiện xu hướng dự báo thiếu hoặc thừa mưa | Gần 0 |
| BS | Sai số của xác suất dự báo | Chấm toàn bộ xác suất, chưa cần chọn ngưỡng báo có/không | Nhỏ hơn |
| BSS | BS cải thiện bao nhiêu so với khí hậu tham chiếu | Kiểm tra có hơn cách dự báo theo mùa đơn giản không | Lớn hơn |
| CSI | H / (H + M + F) | Cân nhắc đồng thời báo trúng, bỏ sót và báo nhầm | Lớn hơn |
| POD | H / (H + M) | Bắt được bao nhiêu sự kiện thực tế | Lớn hơn |
| FAR | F / (H + F) | Trong các lần báo có, bao nhiêu lần bị nhầm | Nhỏ hơn |

H là số báo trúng; M bỏ sót; F báo nhầm. Sai số lượng mm, sai số xác suất và chất lượng quyết định là ba câu hỏi khác nhau. Giữ BSS/CSI theo protocol hiện tại, đồng thời phải đọc đủ POD/FAR và RMSE/MAE/Bias. Nếu muốn chọn mô hình chính theo lượng mm, cần khóa mục tiêu trước holdout, không đổi chỉ vì một bảng đang đẹp hơn.

## 3. 3 seed là gì?

Seed 42/43/44 là ba trạng thái ngẫu nhiên cho ba lần train cùng dữ liệu, nhãn, nhóm biến, cấu hình. Chúng thay đổi khởi tạo, thứ tự đưa mẫu và thao tác ngẫu nhiên. Mục đích là thấy kết quả có phụ thuộc mạnh vào một lần khởi tạo không; chúng không tạo thêm ngày thời tiết.

Ví dụ minh họa: cùng ngày, ba model trả 9, 12, 15 mm; dự đoán trung bình là 12 mm. Kết quả TFT đang báo dùng trung bình lượng mm và xác suất đã hiệu chỉnh của ba seed, sau đó tính metric; không lấy trung bình ba giá trị BSS/CSI để thay metric của dự đoán trung bình. Ngưỡng quyết định cho dự đoán trung bình chọn trên calibration.

Ba ngày là ba đầu ra; ba seed là ba lần train cùng cấu hình; ba lượt chia thời gian đánh giá lần lượt 2021/2022/2023. Một E có 3×3=9 lượt TFT, tám E có 72 lượt; số mốc chấm mỗi lead vẫn 1075. LightGBM cấu hình hiện tại chạy xác định nên không nhân ba bản giống nhau.

## 4. POD 0,4 có phải là tốt?

POD 0,4 nghĩa là bắt40/100 sự kiện. Không tìm thấy một chuẩn chung 0,4 trong hướng dẫn/nguồn đã đối chiếu. POD bỏ qua báo nhầm nên phải đọc cùng FAR/CSI, số sự kiện và baseline. Ví dụ 300 ngày/100 sự kiện: cùng H40/M60, F10 cho FAR 0,2/CSI 0,364; F160 cho FAR 0,8/CSI 0,154. Cùng POD 0,4 nhưng hiệu quả rất khác.

Nguồn P1 tại Việt Nam có POD 0,3–0,4 trong bản đồ ngưỡng 25 mm/24h và có trạm 0,5–0,7; không phát biểu 0,4 là chuẩn. Nguồn P2 đánh giá ước lượng IMERG theo giờ, POD tối đa0,4 đi với FAR tối thiểu0,6 lại được nhận xét phát hiện thấp. Hai ngữ cảnh không tương đương nhau hoặc tương đương dự án; chúng bác bỏ việc diễn giải chỉ từ một mốc số.

POD 0,640trong TFT E7 ngày 1 là 73/114 sự kiện vùng ≥16 mm/24h, theo đầu xác suất với τ calibration. Nó không phải độ chính xác chung 64%. Không suy ra đã hơn paper dùng trạm, ngưỡng25/50/100, forecast số, nhãn trạm hoặc quy tắc trực tiếp từ lượng mm.

## 5. Cùng mô hình, khác quy tắc thì POD thay đổi ra sao?

| Quy tắc | Trúng | Bỏ sót | Báo nhầm | POD | FAR | CSI |
| --- | --- | --- | --- | --- | --- | --- |
| amount | 67 | 47 | 48 | 0.588 | 0.417 | 0.414 |
| probability | 73 | 41 | 66 | 0.640 | 0.475 | 0.406 |

amount là lượng dự đoán ≥16 mm; probability là xác suất ≥τ đã chọn trên calibration. Đây là chẩn đoán bổ sung từ dự đoán đã có, không fit/chọn lại ngưỡng evaluation hoặc thay chỉ số chính. Bảng có đủ ba ngày/hai mô hình ở DECISION_RULES_E7.csv.
