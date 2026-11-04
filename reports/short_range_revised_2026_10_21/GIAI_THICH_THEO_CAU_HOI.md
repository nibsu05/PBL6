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

## 6. Informer có kịp và khả thi không?

Đã hoàn thành 18 lượt, seed hoàn chỉnh [42, 43, 44], khoảng 5.30 phút tiến trình. Pilot chỉ E0/E7, không phải đủ E0–E7. So TFT trên đúng cùng seed, nhãn, mẫu, lịch sử 28 bước 6h, lịch tương lai, đầu ra 3 ngày, loss Tweedie/BCE và cách calibration. Dữ liệu vẫn chỉ 2015–2023, không mở 2025.

Bản Informer là adaptation nhỏ hidden 32/heads 4, hai encoder có distilling, một decoder; daily heads thay đầu benchmark gốc. Subclass mới sửa số query sparse theo công thức tác giả, cố định lấy mẫu keys lúc eval để replay ổn định; không sửa mã Informer cũ. Decoder prefix lấy khí tượng quá khứ, phần khí tượng tương lai bằng 0, calendar tương lai đã biết. Cùng hidden không có nghĩa cùng số tham số; không tuning riêng hoặc có kiểm định kiến trúc đầy đủ. Chạy được không tự chứng minh dự đoán tốt, điểm đẹp hơn chưa đủ khẳng định thuật toán hơn mọi cấu hình.

Nguồn số liệu trong bảng pilot: ../informer_regional_pilot_2026_10_21/scores_pooled.csv; run.json lưu protocol, epochs, thời gian, tham số, calibration và replay. Bảng slide dùng cùng tập seed với TFT để tránh so một lần Informer với ba lần TFT.

## 7. Nguồn POD và công thức Informer

- [P1] [Skill Validation of High-Impact Rainfall Forecasts over Vietnam Using the European Centre for Medium-Range Weather Forecasts (ECMWF) Integrated Forecasting System (IFS) and Dynamical Downscaling with the Weather Research and Forecasting Model](https://www.mdpi.com/2073-4433/16/2/224).
- [P2] [Can GPM IMERG Capture Extreme Precipitation in North China Plain?](https://www.mdpi.com/2072-4292/14/4/928).
- [V3] [JWGFVR Forecast Verification: Probability of Detection and False Alarm Ratio](https://jwgfvr.github.io/forecastverification/).
- [A5] [Informer official attention implementation](https://raw.githubusercontent.com/zhouhaoyi/Informer2020/main/models/attn.py).