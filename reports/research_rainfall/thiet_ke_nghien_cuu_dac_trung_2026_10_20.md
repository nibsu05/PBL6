# Dữ liệu và thiết kế nghiên cứu thêm/bớt đặc trưng mưa Đà Nẵng

**Cập nhật ngày 20/10/2026 theo định hướng mới của người dùng:** ưu tiên nghiên cứu đóng góp của đặc trưng dữ liệu cho dự đoán mưa trên một vùng. App, nguồn live và mục tiêu vượt ECMWF vận hành không còn là trọng tâm hiện tại. Các tài liệu cũ mô tả mục tiêu app cần được đọc như lịch sử.

> **Kết quả triển khai tiếp theo trong cùng ngày:** đã tạoV1/V2đầu vào vùng và chạy pilotLightGBM so với đầu vào full_featurescũ trên cùng nhãn. Xem [báo cáoV1/V2](../regional_danang_v1_v2/README.md). Mô tả kiểm kê ban đầu bên dưới là bối cảnh trước pilot, không phải thông báo chưa có thí nghiệm mới.

## 1. Câu hỏi nghiên cứu và phạm vi kết luận

Câu hỏi phù hợp là: “Những nhóm thông tin khí tượng, quan trắc mưa và đặc trưng địa hình nào cải thiện dự đoán mưa ngoài mẫu tại Đà Nẵng, ở hạn và mùa nào?” Thực nghiệm kiểm tra khả năng cải thiện, không đặt trước rằng đặc trưng mới bắt buộc phải thắng.

Tạm mô tả theo cấu hình đã có: lịch sử 24 giờ → dự đoán 6 giờ sau, tổng 3/6 giờ để đánh giá bổ sung. Đây chưa phải quyết định người dùng chốt lại hạn dự báo. Đổi sang ngày hoặc hạn khác sẽ cần dựng lại cửa sổ và chỉ số.

Chỉ nghiên cứu Đà Nẵng thì kết luận về Đà Nẵng. Chưa được khẳng định phù hợp toàn Việt Nam; việc thử vùng khác có thể là nghiên cứu mở rộng sau.

## 2. Kiểm kê thực tế dataset

- `data/processed/dataset_v2_danang`: 93 ô đất, lưới 0,1°; nhãn tỉnh Đà Nẵng mới theo phép ánh xạ ranh giới đang dùng trong repo.
- Cube là `[93 ô, 105192 giờ lịch, 51 cột]`. Trục lịch được cấp sẵn đến 31/12/2026; không đồng nghĩa dữ liệu có đủ đến mốc đó. Kiểm tra nhãn ô đầu tiên năm 2026 có 6.552 giờ từ 01/01 đến 30/09; quý IV là phần chưa có dữ liệu.
- Đã quét toàn bộ 93 ô, 87.672 giờ giai đoạn 2015–2024, không tính/chấm mô hình năm 2025: nhãn và các cột khác hữu hạn, trừ `kx`, `tt`, `era5_tp_mm`, mỗi cột thiếu 1.953 giá trị ô–giờ trên toàn giai đoạn. Không coi mỗi giá trị thiếu là một giờ/sự kiện độc lập.
- Nhãn trong giai đoạn quét không âm, lớn nhất khoảng 66 mm trong một giờ ở quy mô ô. Tám cột tĩnh mô hình dùng đều hữu hạn. Đây là kiểm tra cơ học, không xác nhận nhãn đúng ngoài thực tế.
- Bản vùng rộng hơn có 296 ô đất quanh Đà Nẵng, không phải dataset toàn Việt Nam. Thống kê lân cận được tính trước khi rút riêng 93 ô, nên có thông tin bối cảnh ngoài ranh Đà Nẵng.

51 cột gồm **1 nhãn + 1 cờ bản dữ liệu + 45 cột ứng viên khí tượng/mưa + 4 cột thời gian**. Tám đặc trưng tĩnh lưu riêng. Vì vậy không viết “mô hình có 51 biến đầu vào” nếu chưa nêu cấu hình chọn biến.

Nguồn dữ liệu là ERA5 qua GEE `ECMWF/ERA5/HOURLY`, GSMaP v8 và Copernicus DEM; không phải chuỗi best_match ở bảng Open-Meteo cũ. ERA5 được nội suy từ lưới 0,25° về tâm ô 0,1°. Nội suy không tự tạo thông tin khí tượng độc lập ở 93 ô.

## 3. Danh mục đầy đủ các cột đã có

| Nhóm | Tên trong dataset | Ý nghĩa |
| --- | --- | --- |
| Nhãn | `y_gsmap_gc_mm` | Mưa GSMaP v8 hiệu chỉnh trạm, giá trị trung bình ô cho khoảng một giờ; không phải mưa ERA5 hoặc số đo trạm trực tiếp |
| Metadata | `label_permanent` | Cờ bản permanent để lọc nhãn; không đưa làm predictor |
| Mưa quá khứ, 3 cột | `gsmap_mm`, `gsmap_nb5_mean_mm`, `gsmap_nb5_max_mm` | Mưa raw tại ô, trung bình và lớn nhất trong lân cận 5×5 ô |
| Khí tượng bề mặt, 12 cột | `t2m_c`, `td2m_c`, `rh2m_pct`, `sp_hpa`, `mslp_hpa`, `u10`, `v10`, `wspd10`, `tcc`, `lcc`, `mcc`, `hcc` | Nhiệt độ/điểm sương/ẩm, áp suất, gió và mây các tầng. Cấu hình A0 hiện dùng 11 cột, không dùng `wspd10` |
| Đối lưu và nhiệt động, 7 cột | `cape`, `cin_capped`, `has_lfc`, `tcwv`, `kx`, `tt`, `blh` | Bất ổn định, cản đối lưu, cờ/tỷ lệ nút có LFC, hơi nước cột, chỉ số K/Total Totals và lớp biên |
| Dòng ẩm tích phân, 4 cột | `ivt_u`, `ivt_v`, `ivt_mag`, `vimd_mmh` | Thành phần/độ lớn vận chuyển ẩm và phân kỳ thông lượng ẩm |
| Tầng 850 hPa, 6 cột | `u850`, `v850`, `q850_gkg`, `t850_c`, `w850_pas`, `rh850_pct` | Gió, độ ẩm riêng, nhiệt độ, chuyển động thẳng đứng theo áp suất và RH |
| Tầng 500 hPa và đứt gió, 6 cột | `u500`, `v500`, `q500_gkg`, `t500_c`, `w500_pas`, `shear_850_500` | Trạng thái tầng giữa và chênh gió 850–500 hPa |
| Mưa ERA5, 1 cột | `era5_tp_mm` | Mưa mô hình tái phân tích; có thể thử như predictor quá khứ hoặc baseline, không mặc định là nhãn |
| Độ ẩm đất, 1 cột | `swvl1` | Độ ẩm thể tích lớp đất trên cùng |
| Bối cảnh vùng, 2 cột | `ctx_tcwv`, `ctx_ivt_mag` | Trung bình lân cận 3×3 nút ERA5 của hơi nước cột và IVT |
| Chênh áp vùng, 2 cột | `cold_surge_dp_hpa`, `dp_tonkin_south_hpa` | Chênh áp Hà Nội–Đà Nẵng và vịnh Bắc Bộ–Nam Trung Bộ; là proxy, không phải nhãn xác nhận không khí lạnh |
| Nhiệt độ biển, 1 cột | `sst_region_c` | SST trung bình vùng biển xác định trong script, giống nhau cho mọi ô tại cùng giờ |
| Thời gian, 4 cột | `sin_hour`, `cos_hour`, `sin_doy`, `cos_doy` | Chu kỳ giờ địa phương và ngày trong năm |
| Tĩnh, 8 cột riêng | `elev_mean_m`, `elev_std_m`, `elev_max_m`, `ocean_frac`, `coast_dist_km`, `ne_upslope_m`, `lat`, `lon` | Địa hình, tỷ lệ biển, proxy khoảng cách biển, chênh cao theo hướng đông bắc và tọa độ |

`water_frac` có trong bảng ô nhưng không nằm trong tám đầu vào tĩnh mặc định. Địa hình dự án lấy Copernicus DEM, khác ASTER DEM trong paper PLOS. Không phải mọi cột đã tải đều có trong nhóm mặc định: ví dụ `swvl1` hiện lưu trong dataset nhưng chưa có nhóm chọn riêng trong `FEATURE_GROUPS`.

## 4. Một mẫu huấn luyện là gì?

Một mẫu là **một ô c và một thời điểm t**. Mô hình nhận khí tượng tại ô đó trong `[t−24h,t)`, mưa raw quá khứ theo độ trễ quy định và tám biến tĩnh; đầu ra là sáu khoảng mưa `[t,t+1h)` đến `[t+5h,t+6h)`. Lịch tương lai được biết trước nên được phép dùng.

Ví dụ t=10:00: khí tượng quá khứ từ 10:00 hôm trước đến 09:00 hôm nay; nếu L=4h thì chuỗi mưa raw kết thúc lúc 06:00; nhãn là mưa từ 10:00 đến 16:00. Chuỗi mưa được dịch cả cửa sổ, không chỉ bỏ bốn giá trị cuối.

Một mô hình chung học từ nhiều ô/năm; đưa dữ liệu của 93 ô vào lần lượt sẽ tạo 93 dự đoán cho cùng thời điểm, ghép thành bản đồ. Bi-LSTM hiện không đọc đồng thời toàn bộ trường 93 ô như một ảnh; thông tin không gian động chỉ là các thống kê lân cận đã tính, bên cạnh tọa độ/địa hình. Nó chưa mô hình hóa đầy đủ chuyển động mưa giữa mọi ô.

Nếu cần một giá trị mưa trung bình vùng, dùng trung bình có trọng số diện tích phần ô thuộc vùng. Không cộng 93 giá trị mm để gọi là “lượng mưa mm toàn tỉnh”; cộng thể tích cần diện tích và đổi đơn vị riêng. Hiện cách chọn tâm ô/ranh GAUL là xấp xỉ vùng, chưa xác minh diện tích giao ranh để tính trung bình vùng chính xác. Đánh giá bản đồ và trung bình vùng phải tách riêng vì trung bình có thể che sai lệch phân bố.

## 5. Đã huấn luyện thực tế bằng những biến nào?

| Cấu hình domain screen | Predictor chính | Vai trò |
| --- | --- | --- |
| BASE | 11 biến bề mặt + 4 thời gian + 3 mưa raw trễ + 8 tĩnh | Nền đã có mưa quá khứ và địa hình |
| RAW | BASE + `tcwv`, `u850`, `v850`, `q850_gkg` | Đo giá trị thêm của nguyên liệu khí tượng |
| DOMAIN | RAW + 4 chỉ báo dẫn xuất | Đo giá trị cách biểu diễn, không phải thêm nguồn quan trắc mới |

Bốn chỉ báo dẫn xuất là: gió ẩm chiếu theo hướng đông bắc; chỉ báo đó nhân dốc nâng; tỷ lệ giờ có thành phần gió theo hướng đã chọn; cờ 850 hPa ở trên mặt đất. Chúng là proxy do nhóm thiết kế, không phải cơ chế đã được xác nhận hoặc biến chứng minh phù hợp toàn Việt Nam. Hướng địa hình duy nhất đông bắc không đại diện mọi chế độ mưa; có thể thử hướng gió tương tác gradient địa hình như một giả thuyết bổ sung.

RAW thêm bốn cột 0 để cùng số chiều/tham số với DOMAIN. BASE cũng có padding theo wrapper nhưng ít nguyên liệu hơn nên tổng số tham số vẫn thấp hơn RAW. Bỏ riêng một proxy DOMAIN không đồng nghĩa loại mọi thông tin địa hình vì tám biến tĩnh vẫn có.

Đã lấy thử lại ba mẫu năm 2023 từ index/normalizer đã lưu: BASE có `x_past=[3,24,22]`; RAW/DOMAIN `[3,24,26]`, đều gồm padding khi áp dụng. Cả ba có `x_future=[3,6,4]` chỉ chứa lịch, static `[3,8]`, y `[3,6]`; các tensor đều hữu hạn. Đây chỉ là kiểm tra kết nối dữ liệu, không phải test kỹ năng mới.

Đợt domain screen hiện dùng **30 ô, không phải huấn luyện trên đủ 93 ô**; 30.000 mẫu train cố định mỗi fold; 3 seed NN. Có một đợt pilot khác trên 93 ô; không gộp hai đợt thành cùng cấu hình.

| Fold đã chạy | Train | Calibration/chọn epoch/ngưỡng | Evaluation khám phá |
| --- | --- | --- | --- |
| 1 | 2015–2019 | 2020 | 2021 |
| 2 | 2015–2020 | 2021 | 2022 |
| 3 | 2015–2021 | 2022 | 2023 |

Domain screen lấy thời điểm cách nhau 6 giờ. Nhãn sáu giờ không chồng trong cùng ô, nhưng các cửa sổ quá khứ và thời tiết giữa các ô vẫn tương quan. Chuẩn hóa fit trên năm/ô train; loader chặn nhãn vượt ranh năm. 2021–2023 đã được phân tích nhiều lần nên chỉ là evaluation khám phá; test mô hình 2025 tiếp tục giữ kín.

## 6. Dữ liệu có bảo đảm cho nghiên cứu không?

| Mặt cần xét | Đánh giá hiện tại |
| --- | --- |
| Có thể tạo mẫu và huấn luyện | Có: dữ liệu nhiều năm, kiểm tra hữu hạn và batch thực đạt trong phạm vi đã kiểm |
| Đủ để bắt đầu nghiên cứu thêm/bớt đặc trưng | Có điều kiện: phải cố định bài toán, mẫu, nhãn và kiểm định ngoài mẫu |
| Nhãn là mưa thực chính xác từng giờ | Chưa: thiếu mạng trạm giờ độc lập trên toàn vùng; GSMaP là ước lượng |
| Có nhiều ô nghĩa là nhiều mẫu độc lập | Không: cùng hoàn lưu và chung nút ERA5 tạo tương quan cao |
| Chắc chắn đặc trưng mới cải thiện | Không: phải chấp nhận kết quả không cải thiện hoặc chỉ tốt ở một số mùa |
| Đủ kết luận phù hợp Việt Nam | Chưa: dữ liệu chính tập trung Đà Nẵng/vùng lân cận |

Các rủi ro khoa học vẫn còn dù không làm app:

1. **Nhìn giờ đích:** nhóm A4 có ERA5 ở giờ tương lai. Không đưa vào phép so chính nếu gọi là dự báo từ quá khứ; chỉ giữ như thí nghiệm riêng về thông tin khí tượng giờ đích và ghi đúng tên. BASE/RAW/DOMAIN hiện không có lỗi này.
2. **Hỗ trợ thời gian của bản hồi cứu:** một giá trị quá khứ có thể được sản xuất bằng xử lý sau thời điểm đó. ERA5 và mưa vệ tinh lưu trữ cần mô tả là predictor hồi cứu; riêng mưa MVK cần kiểm tra thuật toán truyền xuôi/ngược trước khi tuyên bố causal. Không làm app không tự loại bỏ vấn đề thông tin tương lai.
3. **Nhãn và predictor chia sẻ nguồn:** mưa raw và Gauge có quan hệ thuật toán, nên mức tăng do thêm raw chưa tự chứng minh dự báo mưa trạm tốt hơn. Đối chiếu IMERG/trạm và một phép so không dùng mưa vệ tinh giúp kiểm tra độ phụ thuộc.
4. **Mùa và thời gian tích lũy:** kiểm tra nhãn giờ, GSOD EOD, mưa hiếm và ảnh hưởng hiệu chỉnh Gauge. Không chỉ bỏ mùa đông rồi kết luận giải quyết được đặc thù mưa Đà Nẵng.
5. **Địa hình và tầng áp suất:** kiểm tra ô cao nơi tầng 850 hPa có thể nằm dưới mặt đất, biến tĩnh là proxy, và quy tắc CIN mask có đúng ý nghĩa nguồn không; hữu hạn không đồng nghĩa có ý nghĩa vật lý.

## 7. Thiết kế ablation phù hợp mục tiêu mới

Đề xuất giữ Bi-LSTM và một baseline LightGBM trước, cùng lịch sử/hạn dự báo, nhãn, ô, mẫu, loss trong mỗi họ mô hình, seed và ngân sách. Chưa cần thay nhiều kiến trúc cùng lúc. Chọn lượng mưa làm đầu ra chính: MAE/RMSE/bias theo ô và vùng, kèm CSI/POD/FAR cho mưa lớn; xác suất là nhánh bổ sung nếu tiếp tục dùng.

Một vòng sàng lọc có thể dùng các cấu hình độc lập sau, không phải chỉ chuỗi cộng dồn:

| Mã đề xuất | Nội dung | Câu hỏi |
| --- | --- | --- |
| R0 | Khí tượng bề mặt quá khứ + thời gian/tọa độ, chưa có mưa vệ tinh hoặc địa hình chi tiết | Nền chỉ có khí tượng đơn giản đạt đến đâu? |
| R1 | R0 + nhóm ẩm/hoàn lưu quá khứ: TCWV, gió/ẩm tầng thấp, IVT khi hợp lệ | Có thêm thông tin trước sự kiện mưa không? |
| R2 | R0 + CAPE/CIN, các chỉ số bất ổn định, lớp biên | Nhiệt động giúp ở chế độ/mùa nào? |
| R3 | Nền khí tượng đã chọn + nhóm địa hình | Địa hình cải thiện phân bố giữa các ô không? |
| R4 | R3 + tương tác gió–ẩm–địa hình | Cách biểu diễn có ích hơn cùng nguyên liệu thô không? |
| R5 | Nền đã chọn + mưa vệ tinh quá khứ | Lợi ích nào do khí tượng/địa hình, lợi ích nào do mưa gần nhất? |

Khi chuyển R0/R3 phải cấu hình hoặc mask rõ các cột tĩnh; loader hiện tự đưa cả tám cột, nên chỉ đổi tên nhóm A0/A1 chưa đủ loại địa hình. R4 đối chiếu cùng nguyên liệu, cùng số tham số khi có thể. `swvl1`, SST và chênh áp vùng giữ làm ứng viên khám phá sau khi có giả thuyết theo mùa/hạn, không đưa tất cả vào một lần.

Đánh giá trên cùng tập cửa sổ hợp lệ chung của những cấu hình được so, tránh cấu hình nhiều biến bị chấm trên tập khác do NaN. Thêm persistence, khí hậu và baseline dùng mưa ERA5 quá khứ nếu phù hợp. Mưa ERA5 tại giờ đích có thể là tham chiếu tái phân tích về nhãn, không phải forecast đầu vào hay đối chứng vận hành cùng thông tin.

Tách các năm/sự kiện, có bootstrap theo khối gom mọi ô cùng ngày/đợt; số seed không thay thế số đợt mưa độc lập. Dùng vùng không gian giữ lại theo cụm thay vì chỉ ngẫu nhiên ô gần nhau nếu muốn kiểm tra khả năng chuyển địa điểm. Không chọn mùa/ngưỡng/loss bằng tập test; những năm đã khám phá không trở lại thành test độc lập.

Không cần chờ API live/ECMWF đủ nguồn để làm nghiên cứu này. Chỉ cần dùng đúng tên “nghiên cứu dự đoán hồi cứu với trạng thái khí tượng tái phân tích”, và giữ điều kiện thông tin giữa các phép so rõ ràng. Chưa có căn cứ bắt nhóm phải chuyển nguồn chính sang IFS khi mục tiêu là đo đóng góp đặc trưng trên lịch sử.

## 8. Tài liệu và nguồn kiểm tra

- Code chọn nhóm/cửa sổ: `src/dataloader_v2.py`; bảng tên/đơn vị và xử lý nguồn: `scripts/build_dataset_v2.py`.
- Cấu hình đã chạy: `scripts/screen_danang_domain.py`, [README domain screen](../domain_screen_danang/README.md), [run manifest](../domain_screen_danang/run.json).
- Kiểm tra nhãn và giới hạn trước đây: [bản phản biện ngày 20/10](phan_bien_du_lieu_2026_10_20.md). Phần khuyến nghị đường app trong bản đó không còn là ưu tiên sau đổi hướng của người dùng.
- Cơ sở vai trò gió ẩm/địa hình tại miền Trung: [nghiên cứu sự kiện mưa 1999](https://vjst.vast.vn/jmst/article/view/12989). Cơ sở vật lý hỗ trợ đặt giả thuyết, không xác nhận trước đặc trưng cụ thể của nhóm.
- Đặc điểm sai số/độ tin cậy mưa vệ tinh: [Yamaji et al., 2021](https://doi.org/10.2151/jmsj.2021-033); kiểm tra thuật toán truyền thời gian: [Ushio et al., 2009](https://doi.org/10.2151/jmsj.87A.137).

Chưa chạy thí nghiệm mới hoặc chốt bộ đặc trưng thắng. Kiểm tra mới trong lượt này là quét dữ liệu 2015–2024, kiểm tra phạm vi năm 2026 và tái tạo batch từ cấu hình đã lưu.
