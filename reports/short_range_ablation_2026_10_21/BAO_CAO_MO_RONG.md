# Mở rộng nghiên cứu dự đoán mưa vùng 24–72 giờ

Ngày 21/10/2026. **Hoàn thành ma trận phát triển E0–E7 trên vùng xấp xỉ đã khóa; chưa phải nghiên cứu cuối hoặc kết quả test 2025.** Bộ này bổ sung [pilot một seed](../short_range_pilot_2026_10_21/README.md), giữ nguyên pilot để truy vết.

## 1. Kết quả mới để báo cáo

- E7 ngày 1: BSS LightGBM 0.303; TFT ensemble 0.246.
- TFT, ΔBSS E7−E0 ngày 1 dương ở 3/3 seed; khoảng [+0.068; +0.153].
- Thêm riêng A hoặc M giúp ngày 1: 2/9 CI chính hiệu chỉnh trên 0.
- E7 ngày 3: BSS LightGBM -0.075; TFT ensemble -0.038.
- Đây là bằng chứng development; chưa chứng minh tốt trên holdout hoặc vận hành.

Đã chạy **72 lượt TFT** (8 cấu hình × 3 fold × 3 seed 42/43/44) và **24 pipeline LightGBM xác định** (8 cấu hình × 3 fold, không nhân seed giả). Đã nạp lại **96/96 lượt**, kiểm tra cả calibration và evaluation, tái lập dự báo/chỉ số từ artifact lưu. 12/12 pipeline seed 42 E0/E7 tái lập kết quả pilot cũ. Tổng cộng 27 kiểm tra đã đạt, gồm các kiểm tra mới chống tăng giả số mẫu, lệch nhãn/reference và chọn ngưỡng trên evaluation.

## 2. Phần nào giống pilot, phần nào mở rộng

Không đổi nguồn V1, 93 ô, trọng số toàn ô, nhãn GSMaP Gauge, mốc issue 00 UTC, lịch sử 168 giờ gộp 6 giờ, ba tổng mưa 24 giờ riêng. E0–E7 dùng cùng mask E7, cùng nhãn và mẫu. Scaler/khí hậu học từ train; chọn epoch và Platt trên calibration. Decoder chỉ biết lịch; không có ERA5 giờ đích, mưa quá khứ hoặc nhãn trong predictors. Cấu hình hidden 32, batch 64, tối đa 40 epoch, patience 6 được giữ nguyên. Thêm seed và tách A/M/C, không dò siêu tham số dựa trên điểm evaluation.

Vùng hiện tại là **93 ô đầy đủ, khoảng 11.074 km²**, chưa là giao ranh hành chính Đà Nẵng mới chính xác. Trước chạy ma trận đã khóa lựa chọn dùng footprint xấp xỉ và gọi đúng tên trong protocol_frozen.json. Đây là nghiên cứu phát triển có giới hạn phạm vi địa lý; phải giải quyết ranh và kiểm chứng nhãn trước tuyên bố nghiên cứu cuối. Nếu đổi ranh/nhãn phải dựng và chạy lại phần phát triển liên quan.

| Cấu hình | Nhóm | Số biến | Số tham số TFT |
| --- | --- | --- | --- |
| E0 | B | 11 | 121008 |
| E1 | B+A | 23 | 199848 |
| E2 | B+M | 31 | 257848 |
| E3 | B+C | 12 | 127204 |
| E4 | B+A+M | 43 | 353008 |
| E5 | B+A+C | 24 | 206860 |
| E6 | B+M+C | 32 | 265404 |
| E7 | B+A+M+C | 44 | 361380 |

B: bề mặt và lịch; A: khí quyển/đối lưu/mây/ẩm đất; M: gió, ẩm và proxy hoàn lưu/vận chuyển ẩm; C: SST vùng. Các trường khí tượng/đại lượng dẫn xuất là ERA5; nhãn mưa là GSMaP Gauge. C không đại diện đầy đủ ENSO/MJO; M chưa phải chỉ số gió mùa đã kiểm định. Danh mục từng cột trong feature_groups.json của phương án hợp nhất. Cùng kiến trúc/hidden/budget nhưng thêm biến làm tăng số tham số đầu vào; không gọi đây là thí nghiệm giữ tuyệt đối số tham số.

[Danh mục 44 đặc trưng, đơn vị và mô tả lấy từ mã dựng dữ liệu](feature_catalog.csv). Các biến bối cảnh giữ hỗ trợ không gian của nguồn: SST là trung bình một hộp biển; ctx là lân cận nút ERA5; các chênh áp lấy các địa điểm/vùng đã khai báo. Không diễn giải chúng như 93 quan trắc mới tại địa phương. Biến mã hóa như CIN/has_lfc và các proxy cũng cần kiểm tra ý nghĩa vật lý; hữu hạn không đồng nghĩa đã được xác nhận đúng.

F1 train 2015–2019/cal 2020/eval 2021: 1.809/364/363 issue; F2 train 2015–2020/cal 2021/eval 2022: 2.173/363/349; F3 train 2015–2021/cal 2022/eval 2023: 2.536/349/363. Mỗi lead gộp có **1.075 issue, 114 sự kiện ≥16 mm/24 h**. Ba seed không tạo 3.225 mẫu thời tiết độc lập. Các lead cũng có ngày nhãn chồng nhau, không cộng thành 342 sự kiện độc lập. Chỉ đọc dữ liệu trước 2024; 2025 tiếp tục giữ kín.

## 3. Kết quả toàn bộ E0–E7

BSS16 so với khí hậu theo tháng đích/lead học từ train từng fold; BSS dương có lợi. RMSE mm/24 h thấp hơn có lợi. TFT trong bảng là **trung bình dự báo ba seed trên từng issue**, LightGBM là một pipeline xác định. CSI16 dùng xác suất và ngưỡng chọn từ calibration. Đây là hai pipeline dùng cùng nguyên liệu nhưng khác biểu diễn lịch sử/loss, chưa cô lập tuyệt đối ảnh hưởng kiến trúc. Các giá trị pooled tính trực tiếp trên lỗi và reference từng dòng, không trung bình cơ học BSS của năm hoặc seed.

### Ngày 1

| Cấu hình | BSS LGBM | BSS TFT | RMSE LGBM | RMSE TFT | CSI TFT |
| --- | --- | --- | --- | --- | --- |
| E0 B | 0.144 | 0.135 | 19.379 | 20.720 | 0.357 |
| E1 B+A | 0.264 | 0.221 | 18.205 | 20.531 | 0.395 |
| E2 B+M | 0.283 | 0.280 | 17.701 | 20.341 | 0.403 |
| E3 B+C | 0.175 | 0.133 | 19.040 | 20.737 | 0.344 |
| E4 B+A+M | 0.315 | 0.237 | 17.775 | 20.438 | 0.426 |
| E5 B+A+C | 0.282 | 0.171 | 18.012 | 20.578 | 0.364 |
| E6 B+M+C | 0.306 | 0.280 | 17.706 | 20.269 | 0.423 |
| E7 B+A+M+C | 0.303 | 0.246 | 17.706 | 20.361 | 0.406 |
### Ngày 2

| Cấu hình | BSS LGBM | BSS TFT | RMSE LGBM | RMSE TFT | CSI TFT |
| --- | --- | --- | --- | --- | --- |
| E0 B | -0.015 | 0.018 | 21.204 | 21.149 | 0.252 |
| E1 B+A | -0.034 | 0.041 | 21.374 | 21.087 | 0.243 |
| E2 B+M | 0.060 | 0.047 | 20.579 | 21.044 | 0.254 |
| E3 B+C | -0.038 | 0.027 | 21.152 | 21.151 | 0.242 |
| E4 B+A+M | 0.046 | 0.023 | 20.758 | 21.125 | 0.257 |
| E5 B+A+C | -0.035 | 0.026 | 21.351 | 21.089 | 0.247 |
| E6 B+M+C | 0.056 | 0.054 | 20.631 | 20.958 | 0.246 |
| E7 B+A+M+C | 0.043 | 0.028 | 20.756 | 21.018 | 0.257 |
### Ngày 3

| Cấu hình | BSS LGBM | BSS TFT | RMSE LGBM | RMSE TFT | CSI TFT |
| --- | --- | --- | --- | --- | --- |
| E0 B | -0.053 | -0.034 | 21.637 | 21.292 | 0.197 |
| E1 B+A | -0.071 | -0.028 | 21.734 | 21.287 | 0.231 |
| E2 B+M | -0.061 | -0.030 | 21.759 | 21.344 | 0.206 |
| E3 B+C | -0.037 | -0.026 | 21.724 | 21.270 | 0.206 |
| E4 B+A+M | -0.061 | -0.029 | 21.642 | 21.383 | 0.221 |
| E5 B+A+C | -0.063 | -0.028 | 21.779 | 21.246 | 0.196 |
| E6 B+M+C | -0.050 | -0.016 | 21.807 | 21.237 | 0.227 |
| E7 B+A+M+C | -0.075 | -0.038 | 21.742 | 21.321 | 0.201 |

Toàn bộ MAE, bias, CSI lượng mm, POD/FAR và ngưỡng 50/100 nằm trong scores_ensemble*.csv. Số lượng sự kiện cực đoan ít, nhất là ≥100 mm; không dùng bảng ít sự kiện để khẳng định dự báo cực đoan tốt.

Thêm toàn bộ biến không bảo đảm cho điểm cao nhất: LightGBM ngày 1 có BSS E4=0.315, E7=0.303. Đây là so điểm mô tả trên development; chưa có kiểm định E4−E7 riêng để tuyên bố ưu thế chắc chắn hoặc chọn lại cấu hình holdout.

## 4. Độ ổn định qua seed và cách gộp

| Ngày | Seed | ΔBSS E7−E0 | ΔRMSE E7−E0 |
| --- | --- | --- | --- |
| 1 | 42 | +0.088 | -0.202 |
| 1 | 43 | +0.068 | -0.378 |
| 1 | 44 | +0.153 | -0.461 |
| 2 | 42 | -0.012 | +0.037 |
| 2 | 43 | -0.000 | -0.137 |
| 2 | 44 | +0.036 | -0.265 |
| 3 | 42 | -0.018 | +0.107 |
| 3 | 43 | -0.026 | +0.154 |
| 3 | 44 | +0.025 | -0.140 |

Sau hiệu chỉnh xác suất riêng từng seed, lấy trung bình xác suất và lượng mm trên cùng issue. Ngưỡng CSI ensemble được chọn lại trên **trung bình dự báo calibration**, không lấy trung bình các ngưỡng seed và không dùng nhãn evaluation. Nếu calibration không đủ 20 sự kiện/counter-event thì giữ ngưỡng 0,5. Không fit một Platt mới trên evaluation. Báo cả chỉ số từng seed, mean/std/min/max trong seed_stability.csv; ensemble không thay bảng seed.

## 5. Nhóm A/M/C có bằng chứng cải thiện không?

Gia đình chính đã khóa trước chạy ma trận: TFT ensemble, E1−E0 / E2−E0 / E3−E0 × ba lead, BSS16 gộp development. Bootstrap paired theo khối lịch 7 ngày, resample trong từng năm, 20.000 lần; nhãn, dự báo và khí hậu reference cùng trọng số. Dùng CI99,44% cho mỗi phép so theo Bonferroni 9 phép; CI95% chỉ mô tả. Không đổi gia đình sau khi nhìn điểm.

| So sánh | Ngày | ΔBSS16 | CI99,44% cho 9 phép | Diễn giải |
| --- | --- | --- | --- | --- |
| E1-E0 | 1 | +0.085 | [+0.002; +0.161] | Trên 0 |
| E2-E0 | 1 | +0.144 | [+0.068; +0.233] | Trên 0 |
| E3-E0 | 1 | -0.003 | [-0.043; +0.033] | Chứa 0 |
| E1-E0 | 2 | +0.023 | [-0.036; +0.076] | Chứa 0 |
| E2-E0 | 2 | +0.030 | [-0.031; +0.096] | Chứa 0 |
| E3-E0 | 2 | +0.009 | [-0.019; +0.034] | Chứa 0 |
| E1-E0 | 3 | +0.006 | [-0.035; +0.045] | Chứa 0 |
| E2-E0 | 3 | +0.003 | [-0.051; +0.057] | Chứa 0 |
| E3-E0 | 3 | +0.008 | [-0.017; +0.034] | Chứa 0 |

Trong ma trận này, A và M khi thêm riêng vào nền B có bằng chứng cải thiện ở ngày 1; M có mức tăng BSS lớn hơn. Chưa có CI chính điều chỉnh nằm trên 0 ở ngày 2–3 hoặc với nhóm C. Việc thêm A/M có lợi riêng không bảo đảm tổ hợp đầy đủ E7 tốt nhất: tương tác, dư thừa thông tin và tối ưu hóa mô hình đều có thể ảnh hưởng; chưa tách được nguyên nhân từ ma trận này. Không suy rằng khí hậu biển không quan trọng chỉ từ một biến SST vùng.

Có 2/9 CI điều chỉnh nằm trên 0 ở khối 7 ngày. Các phép còn trên 0 khi dùng khối 14 ngày: **E1-E0, ngày 1; E2-E0, ngày 1**. CI này điều kiện trên các mô hình đã fit, không bao trùm mọi bất định huấn luyện, nguồn nhãn hoặc cách chọn vùng. Những năm development đã được dự án xem trước; điều chỉnh đa so sánh không biến chúng thành holdout độc lập. Khoảng bootstrap percentile hữu hạn cũng không phải bảo đảm tuyệt đối mức sai lầm thống kê.

Đóng góp trung bình của một nhóm qua bốn cặp factorial (điểm ước lượng mô tả, chưa có CI/hiệu chỉnh riêng):

| Pipeline | Nhóm | ΔBSS ngày 1 | ΔBSS ngày 2 | ΔBSS ngày 3 |
| --- | --- | --- | --- | --- |
| lgbm | A | +0.064 | -0.011 | -0.017 |
| lgbm | M | +0.085 | +0.082 | -0.006 |
| lgbm | C | +0.015 | -0.008 | +0.005 |
| tft | A | +0.012 | -0.007 | -0.004 |
| tft | M | +0.096 | +0.010 | +0.000 |
| tft | C | -0.011 | +0.002 | +0.003 |

Ví dụ nhóm A lấy trung bình E1−E0, E4−E2, E5−E3, E7−E6. Đây là đóng góp trong pipeline và biểu diễn hiện tại; không chứng minh nhân quả khí tượng. Vị trí xếp hạng cấu hình trên development cũng không phải bằng chứng đã chọn được cấu hình tốt nhất ngoài mẫu độc lập.

## 6. E7−E0: phép so phụ tiếp nối pilot

| Pipeline | Ngày | Chỉ số | ΔE7−E0 | CI95% mô tả |
| --- | --- | --- | --- | --- |
| lgbm | 1 | RMSE | -1.672 | [-2.291; -1.062] |
| lgbm | 1 | BSS16 | +0.160 | [+0.101; +0.224] |
| lgbm | 2 | RMSE | -0.448 | [-0.725; -0.179] |
| lgbm | 2 | BSS16 | +0.058 | [+0.004; +0.114] |
| lgbm | 3 | RMSE | +0.105 | [-0.067; +0.269] |
| lgbm | 3 | BSS16 | -0.022 | [-0.069; +0.026] |
| tft | 1 | RMSE | -0.359 | [-0.661; -0.106] |
| tft | 1 | BSS16 | +0.111 | [+0.054; +0.171] |
| tft | 2 | RMSE | -0.131 | [-0.355; +0.062] |
| tft | 2 | BSS16 | +0.011 | [-0.036; +0.057] |
| tft | 3 | RMSE | +0.028 | [-0.243; +0.300] |
| tft | 3 | BSS16 | -0.004 | [-0.044; +0.033] |

Phép so này mô tả cả A+M+C; không dùng nó thay kiểm định riêng từng nhóm. Xem paired_bootstrap.csv để có CSI16 và độ nhạy khối 14 ngày. Độ ổn định seed và CI thời gian trả lời hai câu hỏi khác nhau; không xem ba seed như ba đợt mưa độc lập.

## 7. Mùa, xác suất và diễn giải báo cáo

Đọc thêm từng năm để không che khuất khác biệt bằng số gộp. Bảng dưới giữ E0/E7 đã định trước; toàn bộ tổ hợp có trong scores_ensemble.csv.

| Năm | Ngày | BSS LGBM E0 | BSS LGBM E7 | BSS TFT E0 | BSS TFT E7 |
| --- | --- | --- | --- | --- | --- |
| 2021 | 1 | 0.195 | 0.312 | 0.175 | 0.231 |
| 2021 | 2 | -0.027 | -0.005 | 0.016 | -0.047 |
| 2021 | 3 | -0.132 | -0.119 | -0.056 | -0.114 |
| 2022 | 1 | 0.108 | 0.403 | 0.105 | 0.287 |
| 2022 | 2 | 0.050 | 0.128 | 0.046 | 0.088 |
| 2022 | 3 | 0.021 | 0.012 | -0.004 | 0.012 |
| 2023 | 1 | 0.134 | 0.227 | 0.130 | 0.228 |
| 2023 | 2 | -0.053 | 0.016 | -0.002 | 0.038 |
| 2023 | 3 | -0.051 | -0.107 | -0.040 | -0.022 |

Đã chấm riêng tháng 5–10, tháng 11–2 và tháng 3–4 theo tháng issue ở giờ Việt Nam; xem seasonal_bss.png và bảng scores_ensemble.csv. Các nhóm mùa là phân tầng giao thức, chưa khẳng định tối ưu theo cơ chế khí hậu Đà Nẵng. Reliability16.csv có số mẫu và tần suất từng bin; không kết luận hiệu chỉnh tốt chỉ từ vài bin ít mẫu.

Tháng 3–4 chỉ có 4/5/5 sự kiện ≥16 mm tương ứng ngày 1/2/3 trên ba năm evaluation; không diễn giải một BSS cao ở nhóm ít sự kiện này như bằng chứng mạnh về dự báo mưa lớn.

Có thể trình bày: “Nhóm đã hoàn thành ma trận phát triển nhánh dự đoán vùng 24–72 giờ, với ba seed TFT và đối chứng LightGBM. Nghiên cứu so đủ các tổ hợp đặc trưng, báo cả kết quả không cải thiện, kèm bootstrap theo thời gian và hiệu chỉnh đa so sánh. Đây là bằng chứng hồi cứu trên footprint xấp xỉ; còn phải chốt ranh/kiểm chứng nhãn và kiểm định trên năm giữ kín.”

Không dùng kết quả này để nói TFT luôn tốt hơn LightGBM, Informer không khả thi, đã dự báo chính xác toàn Đà Nẵng mới, hoặc đã có hệ thống vận hành. Chưa chạy Informer trong phép so. Ngày 3 yếu là kết quả cần báo; muốn kiểm tra dự báo số tương lai phải có nhánh dùng forecast thật đã phát hành và đối chứng cùng thông tin.

## 8. Tái lập, thời gian và giới hạn

Tổng fitting/save/calibration của 96 lượt khoảng 27.7 phút; thời gian tiến trình ma trận 27.9 phút. Epoch TFT median 1.31 giây, khoảng [0.69; 2.14] giây; peak allocated PyTorch cao nhất 177 MiB. GPU NVIDIA GeForce RTX 4060 Laptop GPU. Đánh giá ensemble/bootstrap khoảng 21.2 giây; replay kiểm chứng 46.5 giây. Đây là số đo thực trên mô hình nhỏ/dữ liệu vùng; không đồng nhất với tổng thời gian nghiên cứu.

Artifact/checkpoint/dự báo từng dòng lưu ngoài Git trong data/operational/short_range/ablation_2026_10_21. Run.json có code/source SHA256, artifact SHA256, thứ tự biến, best epoch, lịch sử train và hiệu chỉnh; environment.json ghi phiên bản phần mềm/CUDA. Checkpoint_audit.json ghi replay cả calibration/evaluation; source verify 2.233/2.233 từ lần kiểm tra cùng ngày không thay kiểm chứng nhãn mưa độc lập.

Giới hạn còn lại: vùng xấp xỉ; nhãn vệ tinh; số đợt mưa độc lập ít; ERA5 hồi cứu chưa bảo đảm có sẵn tại issue; calibration vừa chọn epoch vừa fit xác suất; development đã xem trước; số tham số tăng theo số biến; LightGBM nhận thống kê còn TFT nhận chuỗi; bootstrap không gồm mọi nguồn bất định. Không so RMSE mm/24 h nhánh này trực tiếp với RMSE giờ của Bi-LSTM; hai nhánh còn khác lịch sử 168/24 giờ.

## 9. Công việc tiếp theo

1. Khóa ranh và trọng số phù hợp đúng câu hỏi “mưa vùng Đà Nẵng”, kiểm chứng nhãn ngày độc lập.
2. Nếu thay vùng/nhãn, dựng lại dữ liệu và chạy lại ma trận development liên quan; giữ báo cáo hiện tại như thí nghiệm footprint xấp xỉ.
3. Khóa thiết kế cuối, sau đó mới train 2015–2023/cal 2024/test 2025 E0/E7 theo kế hoạch; chưa làm trong đợt này.
4. Với ngày 3, cân nhắc nhánh forecast thật khi có dữ liệu lịch sử phát hành phù hợp, không đưa ERA5 giờ đích vào như forecast.
5. Hoàn thiện bài viết và phần phương pháp. Informer/V2/app không cần thêm chỉ để báo cáo ngày mai.

Tài liệu phương pháp: [bài TFT gốc](https://arxiv.org/abs/1912.09363). Mô hình này là bản điều chỉnh vùng, giữ VSN/GRN/LSTM/attention/gating, bỏ static context và dùng đầu Tweedie/BCE thay đầu phân vị; chưa phải tái lập toàn bộ benchmark bài gốc.
