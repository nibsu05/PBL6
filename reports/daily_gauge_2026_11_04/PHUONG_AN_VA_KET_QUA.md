# Thí nghiệm dữ liệu ngày: dự đoán mưa vùng Đà Nẵng mới 1–3 ngày

Cập nhật 04/11/2026. Đã hoàn tất 24 pipeline LightGBM, 72 TFT và 72 Informer: **168 lượt**, đủ E0–E7. Năm đánh giá phát triển 2021–2023; test 2025 giữ kín. Đây là thí nghiệm dùng nhãn CPC theo ngày, chưa phải mô hình được xác nhận đúng lượng mưa thực toàn địa giới.

## 1. Điều đã thay đổi và điều cần hiểu đúng

Đầu vào chính trước đây là khí tượng ERA5 quá khứ, không có mưa vệ tinh. GSMaP là nhãn trong thí nghiệm trước. Lần này dùng ERA5 tổng hợp theo ngày và thay nhãn bằng phân tích mưa ngày CPC xây dựng từ trạm. ERA5 vẫn là tái phân tích; đổi bước thời gian không biến nó thành số đo trạm. Dữ liệu Vrain đang được nhóm xin quyền truy cập, chưa có trong lần huấn luyện này.

Nhãn CPC là sản phẩm lưới 0,5° nội suy/phân tích từ trạm, không phải toàn bộ số đo trạm riêng lẻ hay phép đo trực tiếp trung bình vùng. Tổng hợp theo diện tích của footprint 93 ô đã có giúp giữ mục tiêu vùng trực tiếp; footprint vẫn xấp xỉ Đà Nẵng mới và chưa cắt theo polygon địa giới chính xác.

| Thành phần | Thí nghiệm trước | Thí nghiệm ngày mới |
| --- | --- | --- |
| Nguồn khí tượng X | ERA5 Hourly, gộp sáu giờ | Cùng ERA5 Hourly, gộp 24 giờ |
| Lịch sử đầu vào | 168 giờ, 28 bước | 168 giờ, bảy bước ngày |
| Nguồn nhãn y | GSMaP Gauge, cộng 24 giờ | CPC đã có tổng ngày từ phân tích trạm |
| Đầu ra cần dự đoán | Ba tổng 24 giờ riêng | Vẫn ba tổng 24 giờ riêng |
| Mốc dự báo | 00 UTC | 12 UTC theo EOD nguồn CPC |
| Số biến E7 | 44 | 42, bỏ hai mã hóa giờ hằng |
| Mưa vệ tinh trong X chính | Không có | Không có |

Như vậy, lần này không phải chuyển từ dự đoán từng giờ sang dự đoán ngày: đầu ra cũ đã là tổng ngày. Thay đổi là nguồn nhãn và cách biểu diễn khí tượng quá khứ, cùng mốc tích lũy được kiểm tra lại.

## 2. Độ phủ trạm: kết quả kiểm tra thực tế

Bộ GSOD của dự án có một trạm Đà Nẵng 488550 trong vùng. Kiểm tra thêm danh mục GHCN-Daily của NOAA: trạm DANANG INTL có khoảng năm PRCP 1973–2025 trong danh mục; các trạm khác gần vùng như Chu Lai, Kỳ Hà, An Hòa và Marble Mtn chủ yếu có mưa từ thập niên 1960–1970. Khoảng năm trong danh mục không bảo đảm từng ngày đầy đủ. Chưa tìm được mạng trạm quan trắc phủ vùng cho giai đoạn phát triển.

Footprint 93 ô giao chín ô CPC. Trong 13 ngày kiểm tra định trước (đầu bốn quý ở 2015/2019/2023 và 14/10/2022), ba ô có gnum=1, sáu ô gnum=0. Đây là số trạm trong toàn ô CPC; không suy thành ba trạm nằm trong địa giới hoặc kết luận các ô không có trạm là không có thông tin. Kiểm tra 13 ngày chưa đại diện toàn bộ mạng trạm của chín năm. Các ô không có trạm trực tiếp vẫn nhận phân tích từ lân cận.

Đã tải 3.287 ngày CPC 2015–2023, đủ chín ô cần dùng, không thiếu tổng vùng. Đã đối chiếu các giá trị PSL với file nhị phân gốc NOAA ở đủ 13 ngày và khớp sau chuyển đơn vị 0,1 mm sang mm. Có thể tái lập từ source_audit.json và source_probe_manifest.json; raw ngoài Git.

## 3. Một mẫu huấn luyện là gì?

Mốc dự báo t = 12 UTC, tức 19 giờ Việt Nam. Dùng dữ liệu EOD do NOAA cung cấp: chín ô đều ghi tổng mưa kết thúc tại 12 UTC của ngày mang nhãn. NOAA cảnh báo metadata EOD chưa được kiểm chứng hoàn toàn; đây là giả định danh định theo nguồn, cần xác nhận lại với trạm/Vrain.

Kiểm tra bổ sung dữ liệu ISD gốc của trạm 488550-99999 trong 2015/2019/2021/2022/2023: 1.364/1.365 bản ghi có trường tích lũy 24 giờ và độ sâu không thiếu mang timestamp 12 UTC; một bản ghi mưa vết năm 2023 ở 00 UTC. Có 1.151 cặp khớp với GSOD cờ G cùng ngày ghi nhãn, tất cả lệch không quá 0,3 mm do độ phân giải/làm tròn. Các mã condition/quality được lưu, không xem mọi bản ghi là số đo đã được chứng nhận đúng. Bằng chứng này hỗ trợ mốc 12 UTC tại trạm đó; chưa xác minh mọi trạm dùng trong CPC hoặc mọi năm. Chi tiết trong station_eod_audit.json. Không mặc định mưa GSOD là tổng 00–00 UTC chỉ vì DATE thuộc một ngày UTC.

- Đầu vào: khí tượng của bảy ngày đã hoàn tất, từ t−168 giờ đến t. Mỗi biến vật lý được lấy trung bình đúng 24 giờ, tạo bảy bước ngày; không lấy trung bình từ ngày thiếu giờ.
- Nhãn ngày 1: tổng mưa CPC trong [t,t+24 giờ); ngày 2: [t+24,t+48); ngày 3: [t+48,t+72). CPC đã là tổng ngày, không chia xuống giờ và không cộng lặp lại 24 lần.
- TFT/Informer nhận [số mẫu, 7 ngày, số đặc trưng] và lịch tương lai [số mẫu, 3 ngày, 2 biến]. Hai biến lịch là sin_doy/cos_doy. Hai biến giờ bị bỏ vì cố định tại mỗi bước ngày.
- LightGBM nhận cùng nguyên liệu quá khứ dưới dạng: ngày cuối, trung bình ba/bảy ngày, chênh lệch hai ngày cuối; cùng lịch tương lai. Khác cách biểu diễn nên chưa cô lập riêng ảnh hưởng kiến trúc.
- Có ba đầu ra lượng mm/24h và chín xác suất: ba ngày × ba ngưỡng 16/50/100 mm. Mưa vùng đạt ngưỡng không có nghĩa mọi điểm trong vùng đều đạt ngưỡng.

Chọn bảy ngày để giữ cùng độ dài lịch sử 168 giờ của thí nghiệm cũ, không phải đã chứng minh bảy ngày tối ưu. Lấy trung bình ngày có thể làm mất đỉnh CAPE, gió hoặc độ ẩm trong ngày; không mặc định dữ liệu ngày luôn tốt hơn dữ liệu giờ. Không đưa mưa quá khứ CPC hoặc khí tượng giờ đích vào X trong lần này.

## 4. Các nhóm biến và E0–E7

| Nhóm | Số biến | Nội dung |
| --- | --- | --- |
| B — Nền | 9 | Bảy biến: nhiệt độ, điểm sương, độ ẩm, áp suất bề mặt, áp suất mực biển, u/v gió 10 m; hai biến sin/cos ngày trong năm. |
| A — Đối lưu, mây, lớp biên, đất | 12 | CAPE, CIN, has_lfc, TCWV, K-index, Total Totals, độ cao lớp biên, bốn loại độ che phủ mây, ẩm đất lớp 1. |
| M — Hoàn lưu và vận chuyển ẩm | 20 | Gió/ẩm/nhiệt/chuyển động thẳng đứng 850/500 hPa, đứt gió, IVT, phân kỳ dòng ẩm, bối cảnh hơi nước/dòng ẩm và hai biến chênh áp. |
| C — Nhiệt độ biển | 1 | SST trung bình hộp biển đã chọn; chưa đại diện đầy đủ ENSO/MJO. |

Các biến vật lý đã có trung bình diện tích theo giờ, sau đó mới lấy trung bình thời gian 24 giờ. has_lfc trở thành tỷ phần theo không gian/thời gian; u/v lấy trung bình thành phần, không lấy trung bình góc gió. Danh mục 42 cột nằm trong feature_catalog_daily.csv.

| Cấu hình | Nhóm biến | Số biến |
| --- | --- | --- |
| E0 | B | 9 |
| E1 | B+A | 21 |
| E2 | B+M | 29 |
| E3 | B+C | 10 |
| E4 | B+A+M | 41 |
| E5 | B+A+C | 22 |
| E6 | B+M+C | 30 |
| E7 | B+A+M+C | 42 |

## 5. Chia thời gian, ba seed và cách so công bằng

| Năm chấm | Train | Calibration | Số train | Số cal | Số eval |
| --- | --- | --- | --- | --- | --- |
| 2021 | 2015–2019 | 2020 | 1804 | 363 | 362 |
| 2022 | 2015–2020 | 2021 | 2167 | 362 | 348 |
| 2023 | 2015–2021 | 2022 | 2529 | 348 | 362 |

Tổng 3,239 mẫu phát triển hợp lệ; 1,072 mốc đánh giá chung cho mỗi hạn. Số sự kiện từ 16 mm/24h của ngày 1/2/3 lần lượt là 116 / 117 / 118. Tất cả E dùng mask hợp lệ của E7 để tránh mô hình ít biến được chấm trên ngày dễ hơn. Cả ba mô hình dùng cùng issue/nhãn/tham chiếu trong mỗi E/ngày. Nhãn ba ngày không vượt ranh năm fold.

TFT/Informer có seed 42/43/44; lấy trung bình dự đoán ba seed rồi tính metrics, không chọn seed đẹp nhất. LightGBM chạy xác định nên không nhân ba bản giống nhau. Scaler và khí hậu tham chiếu chỉ fit trên train. Chọn epoch, Platt calibration và ngưỡng quyết định CSI chỉ dùng calibration. Cấu hình tối đa 40 epoch, patience 6, hidden 32 được khóa trước fit, không tuning theo kết quả đánh giá.

TFT và Informer là các bản điều chỉnh cho bài toán này, không phải tái lập nguyên vẹn benchmark bài gốc. Readout đổi từ bốn bước sáu giờ/ngày thành một bước/ngày. Informer dùng prefix ba ngày và hai dấu thời gian mùa; encoder chỉ có bảy bước nên chưa kiểm tra được lợi thế tính toán chuỗi dài của ProbSparse. TFT không có static context hay đầu ra phân vị. Không đồng nhất mọi chênh lệch điểm với ưu thế thuần của kiến trúc.

Các job được chạy bằng hai tiến trình độc lập, giữ nguyên hàm fit, dữ liệu và seed đã khóa; chỉ tiến trình cha ghi nhật ký tổng. Thời gian từng job có thể chồng lấp và chịu chia sẻ GPU, không dùng nhật ký này làm benchmark tốc độ riêng của kiến trúc.

## 6. Bảng BSS đầy đủ ba mô hình

Tất cả bảng chính là toàn năm, ngưỡng 16 mm/24h. BSS = 1−BS mô hình/BS khí hậu tháng học từ train. BSS=+0,10 là giảm 10% sai số Brier so khí hậu; BSS=−0,10 là tăng 10%. BSS không phải tỷ lệ ngày đoán đúng. **Đậm là điểm cao nhất trong cùng E/ngày**, chưa tự là khác biệt có ý nghĩa thống kê.

### Ngày 1

| Cấu hình | LightGBM | TFT | Informer |
| --- | --- | --- | --- |
| E0 | **0.136** | 0.044 | 0.054 |
| E1 | **0.128** | 0.040 | 0.063 |
| E2 | **0.193** | 0.053 | 0.078 |
| E3 | **0.123** | 0.016 | 0.060 |
| E4 | **0.198** | 0.019 | 0.072 |
| E5 | **0.141** | 0.036 | 0.050 |
| E6 | **0.206** | 0.048 | 0.083 |
| E7 | **0.190** | 0.026 | 0.078 |
### Ngày 2

| Cấu hình | LightGBM | TFT | Informer |
| --- | --- | --- | --- |
| E0 | -0.068 | **-0.008** | -0.013 |
| E1 | -0.022 | -0.012 | **-0.005** |
| E2 | **0.006** | -0.020 | -0.015 |
| E3 | -0.036 | -0.018 | **-0.007** |
| E4 | **-0.004** | -0.035 | -0.013 |
| E5 | -0.037 | **-0.003** | -0.022 |
| E6 | **0.002** | -0.010 | -0.015 |
| E7 | **-0.004** | -0.013 | -0.027 |
### Ngày 3

| Cấu hình | LightGBM | TFT | Informer |
| --- | --- | --- | --- |
| E0 | -0.046 | -0.030 | **-0.012** |
| E1 | -0.073 | -0.030 | **-0.010** |
| E2 | -0.060 | -0.042 | **-0.018** |
| E3 | -0.061 | -0.033 | **-0.013** |
| E4 | -0.064 | -0.056 | **-0.023** |
| E5 | -0.068 | **-0.015** | -0.038 |
| E6 | -0.076 | -0.029 | **-0.022** |
| E7 | -0.074 | -0.031 | **-0.025** |

## 7. E7: đọc đồng thời lượng mm và khả năng bắt sự kiện

RMSE và MAE đo sai số lượng mm/24h; RMSE phạt mạnh lỗi lớn. Bias gần 0 giúp phát hiện dự báo thừa/thiếu. BS/BSS chấm xác suất. CSI cân đối báo trúng, bỏ sót và báo nhầm. POD là phần sự kiện thật được bắt; FAR là phần cảnh báo bị nhầm. POD phải đọc cùng FAR/CSI, không có chuẩn POD=0,4 tốt cho mọi ngưỡng, vùng và hạn.

### Ngày 1, cùng E7

| Mô hình | RMSE ↓ | MAE ↓ | Bias ≈0 | BS ↓ | BSS ↑ | CSI ↑ | POD ↑ | FAR ↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LightGBM | **17.560** | **6.328** | **-2.056** | **0.068** | **0.190** | **0.349** | 0.526 | **0.492** |
| TFT | 20.028 | 7.560 | -2.618 | 0.082 | 0.026 | 0.224 | 0.509 | 0.714 |
| Informer | 19.829 | 7.405 | -2.524 | 0.077 | 0.078 | 0.309 | **0.552** | 0.587 |
### Ngày 2, cùng E7

| Mô hình | RMSE ↓ | MAE ↓ | Bias ≈0 | BS ↓ | BSS ↑ | CSI ↑ | POD ↑ | FAR ↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LightGBM | **20.117** | **7.661** | -2.601 | **0.085** | **-0.004** | **0.248** | **0.496** | **0.669** |
| TFT | 20.182 | 7.834 | -2.526 | 0.086 | -0.013 | 0.214 | 0.427 | 0.701 |
| Informer | 20.212 | 7.919 | **-2.450** | 0.087 | -0.027 | 0.219 | **0.496** | 0.718 |
### Ngày 3, cùng E7

| Mô hình | RMSE ↓ | MAE ↓ | Bias ≈0 | BS ↓ | BSS ↑ | CSI ↑ | POD ↑ | FAR ↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LightGBM | 20.423 | **7.858** | -2.706 | 0.092 | -0.074 | **0.240** | **0.576** | **0.708** |
| TFT | **20.229** | 7.976 | -2.407 | **0.088** | -0.031 | 0.219 | **0.576** | 0.739 |
| Informer | 20.236 | 8.114 | **-2.177** | **0.088** | **-0.025** | 0.205 | 0.568 | 0.757 |

## 8. Nhận xét từ kết quả mới và khoảng tin cậy

- LightGBM E7: BSS ngày 1/2/3 = +0.190 / -0.004 / -0.074.
- TFT E7: BSS ngày 1/2/3 = +0.026 / -0.013 / -0.031.
- Informer E7: BSS ngày 1/2/3 = +0.078 / -0.027 / -0.025.

| Mô hình | Ngày 1: BSS [CI95%] | Ngày 2: BSS [CI95%] | Ngày 3: BSS [CI95%] |
| --- | --- | --- | --- |
| LightGBM | +0.190 [+0.102; +0.268] | -0.004 [-0.064; +0.052] | -0.074 [-0.134; -0.025] |
| TFT | +0.026 [-0.010; +0.067] | -0.013 [-0.051; +0.025] | -0.031 [-0.071; +0.004] |
| Informer | +0.078 [+0.028; +0.130] | -0.027 [-0.067; +0.017] | -0.025 [-0.067; +0.016] |

Khoảng hoàn toàn trên 0 hỗ trợ kỹ năng dương trong phân tích mô tả; khoảng chứa 0 chưa phân biệt rõ với khí hậu tham chiếu. Không dùng việc hai CI giao nhau để thay CI của chênh lệch mô hình. CI chênh lệch kiến trúc có trong Excel.

Ở E7 ngày 1, CI95% BSS tuyệt đối của LightGBM và Informer nằm trên 0, còn TFT chứa 0. LightGBM có điểm BSS ngày 1 cao hơn hai mạng trong cùng E7; CI chênh lệch 95% mô tả cũng trên 0. Đây là bằng chứng trong điều kiện pipeline hiện tại, chưa là kết luận kiến trúc luôn tốt hơn trên nhãn khác, cấu hình khác hoặc holdout.

Ngày 3, cả 24 cặp mô hình/cấu hình đều có điểm BSS âm. Ngày 2 chỉ LightGBM E2/E6 có điểm dương rất nhỏ, khoảng 0,006/0,002; CI tuyệt đối đều chứa 0. Vì vậy thí nghiệm này chưa xác nhận kỹ năng dự báo xác suất hữu ích tới 72 giờ chỉ bằng cách chuyển sang dữ liệu ngày.

Đóng góp khi thêm riêng A/M/C so với E0 ở ngày 1, đặt đủ ba mô hình cho mỗi nhóm:

| Nhóm thêm | Mô hình | ΔBSS ngày 1 | CI95% điểm | CI điều chỉnh 63 phép |
| --- | --- | --- | --- | --- |
| A | LightGBM | -0.008 | [-0.065; +0.046] | [-0.105; +0.084] |
| A | TFT | -0.004 | [-0.045; +0.034] | [-0.079; +0.060] |
| A | Informer | +0.009 | [-0.018; +0.032] | [-0.036; +0.052] |
| M | LightGBM | +0.057 | [-0.002; +0.119] | [-0.049; +0.170] |
| M | TFT | +0.008 | [-0.028; +0.045] | [-0.058; +0.069] |
| M | Informer | +0.024 | [-0.010; +0.060] | [-0.034; +0.086] |
| C | LightGBM | -0.013 | [-0.044; +0.019] | [-0.069; +0.043] |
| C | TFT | -0.028 | [-0.059; +0.000] | [-0.082; +0.022] |
| C | Informer | +0.005 | [-0.010; +0.022] | [-0.021; +0.033] |

ΔBSS dương nghĩa là điểm tăng khi thêm nhóm, cùng mô hình và cùng nhãn; CI điều chỉnh chứa 0 nghĩa là chưa có bằng chứng tương ứng sau cân nhắc nhiều phép so. Thêm toàn bộ biến chưa chắc đạt điểm cao nhất.

Thêm riêng M ở ngày 1 làm điểm tăng khoảng 0,057/0,008/0,024 cho LightGBM/TFT/Informer, nhưng cả ba CI95% vẫn chứa 0. Chưa nên viết rằng đã chứng minh chắc chắn M cải thiện ngày 1 trên nhãn CPC này.

Đây là điểm phát triển của nhãn CPC. Không lấy chênh lệch với các con số GSMaP cũ làm bằng chứng cải thiện: lần này đổi cả nguồn nhãn, mốc giờ, bước đầu vào và readout mạng. Để đo riêng lợi ích ngày so với sáu giờ cần một thí nghiệm cùng nhãn CPC, cùng khoảng đích và cùng mẫu; chưa thực hiện phép đó.

Khoảng tin cậy dùng 20.000 bootstrap theo cặp, khối bảy ngày và kiểm tra độ nhạy 14 ngày, giữ chung dự báo/nhãn/tham chiếu giữa các mô hình. Có CI95% điểm cho các chênh lệch và BSS tuyệt đối. Riêng chênh lệch BSS đặc trưng có thêm CI Bonferroni cho toàn bộ 63 phép (7 Ei−E0 × 3 ngày × 3 mô hình). Đây vẫn là phân tích phát triển khám phá, không phải holdout xác nhận và không bao trùm bất định do huấn luyện hoặc chất lượng nhãn. Thêm biến làm đổi số tham số mạng, cần thận trọng khi quy tác động thuần cho thông tin vật lý.

Các phép có CI điều chỉnh 63 phép hoàn toàn trên 0 ở khối bảy ngày:

- LightGBM E2 ngày 2: ΔBSS +0.073, CI điều chỉnh [+0.003; +0.159]
- LightGBM E6 ngày 2: ΔBSS +0.070, CI điều chỉnh [+0.001; +0.153]

Xem cả khối 14 ngày và từng năm/mùa trước kết luận. Không chọn một E chỉ vì điểm cao nhất trong nhiều phép thử. Có cả baseline khí hậu và luôn dự báo 0 trong Excel; LightGBM là mô hình tham chiếu cần so công bằng, không bắt buộc TFT hoặc Informer phải thắng.

Ví dụ cần phân biệt: LightGBM E6 ngày 2 cải thiện BSS so E0 ở cả khối 7/14 ngày sau điều chỉnh 63 phép, nhưng BSS tuyệt đối chỉ +0,002 và CI95% khối 7 ngày khoảng [−0,055; +0,055]. Kết luận đúng là giúp pipeline bớt sai so với E0, chưa chứng minh hơn khí hậu. LightGBM E2 ngày 2 có CI điều chỉnh trên 0 ở khối 7 nhưng chưa lặp lại ở 14 ngày.

## 9. Có nghiên cứu dùng đặc trưng theo ngày không?

- Pham và cộng sự (2020), Development of advanced artificial intelligence models for daily rainfall prediction, dùng năm biến khí tượng ngày và 3.653 mẫu ở Hòa Bình. PDF người dùng cung cấp, mục 2.2, mô tả dữ liệu thời tiết từ Global Weather Data for SWAT; không phải bằng chứng bài này dùng ERA5. Mục 3 chia ngẫu nhiên 70/30, chưa đủ làm mẫu cho phép dự báo ngoài thời gian 1–3 ngày của dự án. [Bài gốc](https://doi.org/10.1016/j.atmosres.2020.104845).
- Neyestani và cộng sự (2025), Application of Machine and Deep Learning Models to Forecast Daily Precipitation Over the Western Part of Iran: năm trạm, dữ liệu ngày, chuỗi mười ngày quá khứ để dự báo ngày kế tiếp. Đây là cơ sở cho khả năng dùng predictor ngày, không chứng minh kỹ năng ba ngày ở Việt Nam. [Bài gốc, mục 2](https://rmets.onlinelibrary.wiley.com/doi/full/10.1002/met.70143).
- Amir và cộng sự (2026), Comparative analysis of deep learning models for multi-horizon rainfall forecasting in flood-prone tropical highlands: thử TFT và các mạng khác với đầu vào 30 bước ngày, nhiều hạn gồm một và ba ngày; dữ liệu khí tượng Open-Meteo. Đây là ví dụ thiết kế mạng dùng bước ngày, không thay kiểm chứng nguồn/trạm hoặc chứng minh TFT thắng trên bộ mới của nhóm. [Bài gốc](https://juti.if.its.ac.id/index.php/juti/article/view/1518).

## 10. Giới hạn và hướng tiếp theo

Lần chạy này phù hợp để nghiên cứu dự đoán trực tiếp sản phẩm mưa ngày CPC trung bình footprint vùng, với đầu vào ERA5 ngày. Nó chưa giải quyết việc thiếu mạng trạm đo trung bình toàn Đà Nẵng mới, độ đúng của địa giới hoặc khả năng dự báo vận hành. ERA5 quá khứ hồi cứu chưa được chứng minh có sẵn đúng lúc phát hành; dùng dữ liệu ngày không tự giải quyết độ trễ nguồn.

Khi có Vrain, cần kiểm kê tọa độ, lịch sử, độ phủ theo địa hình, chất lượng và thời điểm tích lũy để xây nhãn vùng cố định. Không coi số trạm nhiều là tự động phủ đủ hoặc thay tập trạm theo từng ngày rồi tạo thay đổi mưa giả. Trạm có thể trùng nguồn CPC; chưa xác định thì không gọi phép kiểm chứng là độc lập hoàn toàn.

Giữ các báo cáo GSMaP trước đây để đối chiếu lịch sử. Khóa thiết kế và nhãn trước holdout 2025; không dùng kết quả 2025 để chọn lại nhóm biến, mốc ngày hoặc ngưỡng. Chưa truy cập Vrain, chưa đưa dữ liệu/checkpoint/dự đoán từng mốc lên Git.

Các phép đối chiếu nguồn với GSOD trước đây dùng giả định00–00UTC cần được rà soát lại theo giờ tích lũy, cờ chất lượng và từng trạm. Audit mới chưa tính lại các bảng lịch sử đó và không tự phủ định tính tái lập các thí nghiệm học nhãn GSMaP.

## Nguồn dữ liệu và tái lập

- [NOAA/CPC README: độ phân giải, số trạm và EOD](https://ftp.cpc.ncep.noaa.gov/precip/CPC_UNI_PRCP/GAUGE_GLB/DOCU/PRCP_CU_GAUGE_V1.0GLB_0.50deg_README.txt).
- [PSL CPC daily archive](https://psl.noaa.gov/thredds/catalog/Datasets/cpc_global_precip/catalog.html).
- [NOAA GHCN-Daily station metadata](https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt), [inventory](https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-inventory.txt).
- [Tài liệu định dạng NOAA ISD, trường AA1–AA4 và timestampUTC](https://www.ncei.noaa.gov/pub/data/noaa/isd-format-document.pdf); mã audit_daily_gauge_eod.py lưu truy vết năm nguồn gốc theo trạm.
- Mã: fetch_cpc_daily_region.py → run_daily_gauge_matrix.py (hoặc scheduler hai worker) → validate_daily_gauge_matrix.py → evaluate_daily_gauge_matrix.py → publish_daily_gauge_matrix.py. Năm test 2025 không được tải hoặc đọc giá trị cho thí nghiệm này.
