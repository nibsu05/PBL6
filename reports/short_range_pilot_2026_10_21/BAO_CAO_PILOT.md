# Báo cáo pilot dự đoán mưa vùng 24–72 giờ

Ngày 21/10/2026, chuẩn bị cho báo cáo ngày 22/10. **Kết quả sơ bộ, chưa phải nghiên cứu cuối hoặc kiểm định trên2025.**

## 1. Điều đã thực hiện

Đã triển khai loader vùng168 h→ba tổng24 h, TFT vùng điều chỉnh và LightGBM. Đã chạy E0/E7 trên ba fold evaluation 2021/2022/2023, seed 42, cùng mask và nhãn; hoàn tất6 lượtTFT và6 pipelineLightGBM.23 kiểm tra code đạt (12 mới,11 bộ chỉ số chung). Nạp lại toàn bộ12 lượt từ artifact đã lưu tái lập chỉ số evaluation trên thiết bị gốc; không tái huấn luyện trong audit.

- Ngày 1, E7: BSS LightGBM=0.303; TFT=0.220.
- Ngày 1: RMSE LightGBM=17.71; TFT=20.39mm/24 h.
- Ngày 3, E7: BSS LightGBM=-0.075; TFT=-0.047.
- Mới là pilot một seed; chưa chứng minh TFT tốt hơn đối chứng.

Đây là kết quả của các mô hình đã chạy, không phải bảng dự toán. Không có mô hình Informer trong phép so này, nên không thể kết luận Informer không khả thi.

## 2. Dữ liệu và giao thức

V1: nhãn GSMaP Gauge trung bình diện tích toàn93 ô, footprint xấp xỉ khoảng11.074km²; chưa là giao ranh chính xác toàn địa giới Đà Nẵng mới. Nghiên cứu dự đoán vùng trực tiếp, không dự đoán93 ô rồi gộp sau mô hình. Khí tượng ERA5 quá khứ; không dùng ERA5 giờ đích, mưa quá khứ hoặc nhãn làm predictor. E0=11 cột nền, E7=44 cột B/A/M/C, SST chỉ là một biến vùng, chưa là ENSO/MJO đầy đủ.

Issue00UTC=07 giờVN, mỗi ngày; encoder28bước6 h của7 ngày trước issue; decoder chỉ biết lịch. Y1/Y2/Y3 là các tổng24 h riêng [t,t+24),[t+24,t+48),[t+48,t+72). Không phải tổng tích lũy48/72 h. Đơn vị mm/24 h, trung bình vùng, không phải mức mưa tại điểm hoặc cảnh báo chính thức.

F1train 2015–2019/cal 2020/eval 2021:1809/364/363issue. F2train 2015–2020/cal 2021/eval 2022:2173/363/349. F3train 2015–2021/cal 2022/eval 2023:2536/349/363. Mask chung E7, đủ168 h lịch sử và72 h nhãn permanent; bỏ cửa sổ nhãn qua ranh năm. Scaler và khí hậu chỉ học train; epoch/iteration, Platt và ngưỡng quyết định dùng calibration. Ngưỡng50/100 quá ít sự kiện nên thường không fit Platt; fallback được lưu trong metadata. Calibration không phải tập kiểm định độc lập.

Pooled mỗi lead có1075issue và114sự kiện≥16mm. Các lead là các ngày được dịch, không được cộng thành342sự kiện độc lập. Năm2025 không được đọc để phân tích/fit/chấm;2026 không dùng lựa chọn.

## 3. Kết quả gộp evaluation 2021–2023

| Ngày | Cấu hình | RMSE mm/24 h | BSS16 | CSI16 |
| --- | --- | --- | --- | --- |
| 1 | Khí hậu | 21.179 | 0.000 | 0.000 |
| 1 | LightGBM E0 | 19.379 | 0.144 | 0.295 |
| 1 | LightGBM E7 | 17.706 | 0.303 | 0.411 |
| 1 | TFT E0 | 20.593 | 0.133 | 0.361 |
| 1 | TFT E7 | 20.391 | 0.220 | 0.414 |
| 2 | Khí hậu | 21.181 | 0.000 | 0.000 |
| 2 | LightGBM E0 | 21.204 | -0.015 | 0.243 |
| 2 | LightGBM E7 | 20.756 | 0.043 | 0.277 |
| 2 | TFT E0 | 21.016 | 0.022 | 0.265 |
| 2 | TFT E7 | 21.053 | 0.010 | 0.238 |
| 3 | Khí hậu | 21.188 | 0.000 | 0.000 |
| 3 | LightGBM E0 | 21.637 | -0.053 | 0.173 |
| 3 | LightGBM E7 | 21.742 | -0.075 | 0.203 |
| 3 | TFT E0 | 21.216 | -0.029 | 0.205 |
| 3 | TFT E7 | 21.323 | -0.047 | 0.206 |

BSS so với xác suất khí hậu theo tháng đích/lead học từ train, làm trơn20 pseudo-observation. BSS>0 có kỹ năng so với reference; <0 kém hơn reference trong phép đo này. CSI16 dùng threshold xác suất chọn trên calibration; không phải CSI từ lượng mm. CSI từ lượng mm, POD/FAR, MAE/bias và các ngưỡng50/100 có trong scores.csv. PooledBSS tính trên toàn bộ lỗi ghép và reference từng fold, không trung bình cơ học ba BSS năm.

## 4. Tác dụng thêm toàn bộ đặc trưng E7 so E0

| Họ | Ngày | Chỉ số ΔE7−E0 | Ước lượng | CI95% |
| --- | --- | --- | --- | --- |
| lgbm | 1 | RMSE | -1.672 | [-2.282; -1.042] |
| lgbm | 1 | BSS16 | 0.160 | [0.101; 0.223] |
| lgbm | 2 | RMSE | -0.448 | [-0.728; -0.174] |
| lgbm | 2 | BSS16 | 0.058 | [0.003; 0.112] |
| lgbm | 3 | RMSE | 0.105 | [-0.072; 0.273] |
| lgbm | 3 | BSS16 | -0.022 | [-0.066; 0.024] |
| tft | 1 | RMSE | -0.202 | [-0.456; -0.007] |
| tft | 1 | BSS16 | 0.088 | [0.023; 0.156] |
| tft | 2 | RMSE | 0.037 | [-0.156; 0.209] |
| tft | 2 | BSS16 | -0.012 | [-0.063; 0.035] |
| tft | 3 | RMSE | 0.107 | [-0.160; 0.352] |
| tft | 3 | BSS16 | -0.018 | [-0.062; 0.025] |

- LightGBM, ngày 1: ΔBSS16=+0.160, CI95%[+0.101;+0.223], CI nằm trên0; thăm dò, chưa hiệu chỉnh đa so sánh.
- LightGBM, ngày 2: ΔBSS16=+0.058, CI95%[+0.003;+0.112], CI nằm trên0; thăm dò, chưa hiệu chỉnh đa so sánh.
- LightGBM, ngày 3: ΔBSS16=-0.022, CI95%[-0.066;+0.024], CI chứa0; thăm dò, chưa hiệu chỉnh đa so sánh.
- TFT, ngày 1: ΔBSS16=+0.088, CI95%[+0.023;+0.156], CI nằm trên0; thăm dò, chưa hiệu chỉnh đa so sánh.
- TFT, ngày 2: ΔBSS16=-0.012, CI95%[-0.063;+0.035], CI chứa0; thăm dò, chưa hiệu chỉnh đa so sánh.
- TFT, ngày 3: ΔBSS16=-0.018, CI95%[-0.062;+0.025], CI chứa0; thăm dò, chưa hiệu chỉnh đa so sánh.

ΔRMSE âm có lợi; ΔBSS dương có lợi. Các CI là pairedbootstrapkhối 7 ngày,2000 lần, gộp theo năm nhưng resample trong từng năm, một seed cố định; có độ nhạy14 ngày trong paired_bootstrap.csv. Reference khí hậu được resample cùng obs/pred. Chưa có hiệu chỉnh đa so sánh hoặc bất định do seed, không dùng bảng này như kiểm định xác nhận của ma trận E0–E7 đầy đủ.

Ngày 1 có tín hiệu giá trị từ lịch sử/đặc trưng thêm; ở ngày 3 cả hai E7 có BSS âm. TFT chưa tốt hơn LightGBM về cả lượng mm và xác suất. Không suy nguyên nhân duy nhất là kiến trúc hay thiếu forecast; cần thêm phép so có kiểm soát. E0/E7 chỉ đo tổng thể thêm A+M+C, chưa phân biệt nhóm nào tạo lợi ích.

## 5. Hình để trình bày

- rmse_by_year.png: tất cả ba năm và ba lead, có khí hậu/luôn0.
- bss_by_year.png: kỹ năng xác suất riêng theo năm, không chỉ đọc số gộp.
- feature_effect_ci.png: hiệu số E7−E0 và CI.
- reliability16.png, reliability16.csv: độ hiệu chỉnh và số mẫu từng bin.
- fixed_example_2023.png: ví dụ ngày 1 cố định issue tháng10–11/2023, không chọn đoạn theo lỗi nhỏ.

## 6. Kiểm tra kỹ thuật và thời gian đo

Tổng chạy pipeline mô hình khoảng186.8giây; tổng thời gian6 lượtTFT gồm calibration/save khoảng148.1giây. EpochTFT median1.40giây, khoảng[1.06;2.16]giây; peak memory allocated PyTorch cao nhất177MiB, không phải tổngVRAM của hệ thống. GPU làNVIDIA GeForce RTX 4060 Laptop GPU.

Dự toán8–30giờGPU trước pilot là dự phòng khi chưa có benchmark. Số đo hiện tại cho thấy chuỗi vùng nhỏ chạy nhanh hơn nhiều; ma trận đầy đủ cần cập nhật bằng số run/epoch thực tế, không tiếp tục coi8–30giờ là số đã đo. Thời gian viết code, kiểm tra dữ liệu, ranh, kiểm chứng nhãn và viết nghiên cứu không nằm trong thời gian huấn luyện vài phút này.

Checkpointaudit:12/12 lượt tái lập trên thiết bị gốc. CPU/GPU có sai khác số học nhỏ, max lượng mưa0.003456mm/24 h, ghi riêng trong audit; không trộn làm kết quả huấn luyện khác. Cấu hình, codeSHA256, sourceSHA256, calibration và bestepoch được lưu. Nguồn2.233/2.233 đãverify trong lượt lập kế hoạch ngày 21/10; không phải kiểm chứng độc lập nhãn mưa.

## 7. Những điều chưa được chứng minh

- Ranh93 ô xấp xỉ chưa bảo đảm trung bình toàn địa giới; nhãn vệ tinh chưa có kiểm chứng vùng độc lập đầy đủ. Không đồng nhất “pipeline chạy đúng” với “mưa thật chính xác”.
- Một seed 42; chưa có ma trận E0–E7, chưa đánh giá độ ổn định tối ưu hóa, chưa mở test 2025.2021–2023 là development đã được dự án xem nhiều lần.
- Chỉ có4–6ngày≥100mm mỗi năm evaluation; không khẳng định dự báo cực đoan tốt từ bảng nhỏ.
- ERA5 hồi cứu không có bảo đảm sẵn tại issue; không phải kết quả vận hành/live, không có forecast ECMWF thật trong đầu vào.
- Biến chọn/attention chỉ giúp diễn giải mô hình, không chứng minh quan hệ nhân quả khí tượng.
- Bi-LSTM nhánh6 h dùng lịch sử24 h, nhánh ngày này dùng lịch sử168 h. Không quy khác biệt giữa hai nhánh chỉ cho hạn hoặc kiến trúc khi cửa sổ đầu vào chưa giống nhau.
- TFT nhận chuỗi còn LightGBM nhận thống kê lịch sử từ cùng nguyên liệu; loss/đầu ra là joint so với các đầu riêng. So sánh là giữa hai pipeline, chưa cô lập tuyệt đối tác dụng kiến trúc.

## 8. Nội dung có thể nói trong báo cáo ngày mai

“Nhóm đã thống nhất dự đoán vùng trực tiếp và triển khai pilot nhánh24–72 giờ. Từ7 ngày khí tượng quá khứ, mô hình dự đoán ba tổng mưa24giờ và xác suất sự kiện. Trên ba năm phát triển, ngày 1 có tín hiệu kỹ năng so khí hậu; ngày 3 còn yếu. TFT chưa thể hiện ưu thế rõ so với LightGBM. Kết quả hiện là pilot một seed trên footprint93 ô; bước tiếp theo là chốt ranh/kiểm chứng nhãn, chạy nhiều seed và tách đóng góp từng nhóm đặc trưng, giữ kín2025.”

## 9. Việc tiếp theo

Ưu tiên ranh/QC nhãn, xác nhận protocol đã duyệt, chạy ba seed và factorialE0–E7. Không điều chỉnh thiết kế để làm đẹp điểm2025. Chỉ sau khóa mới train 2015–2023/cal 2024/test 2025E0/E7. Forecastthật, Informer và V2 là nhánh riêng, không bắt buộc thêm để có báo cáo pilot.

Artifact: scores.csv, scores_pooled.csv, paired_bootstrap.csv, reliability16.csv, checkpoint_audit.json, run.json; checkpoint/dự báo từng dòng giữ ngoàiGit tại data/operational/short_range/pilot_2026_10_21. Code: short_range_dataset, tft_regional, short_range_evaluation và các scriptpilot/audit/evaluate/report. Kiến trúc tham khảo bàiTFT https://arxiv.org/abs/1912.09363; bản này điều chỉnh bỏ static context, giữVSN/GRN/LSTM/attention dùng chung value/gating, thay đầu phân vị bằngđầu ngày Tweedie/BCE. Chưa phải tái lập mọi benchmark của bài gốc.
