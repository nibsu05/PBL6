# Phản biện độc lập hướng dữ liệu dự báo mưa PBL6

**Ngày 20/10/2026 — đọc cùng tài liệu định hướng dữ liệu.**

Đánh giá này kiểm tra code, tính lại một số thống kê trên dữ liệu 2021–2023, gọi thử API forecast và đối chiếu tài liệu gốc. Không huấn luyện mô hình, không mở test mô hình 2025, không coi mô tả trong kế hoạch là bằng chứng mặc định.

## 1. Kết luận đánh giá

**Hướng nghiên cứu có cơ sở, nhưng kế hoạch dữ liệu hiện tại chưa chứng minh được một app AI dự báo mưa 1–6 giờ đáng tin cậy.** Nghiên cứu hồi cứu trên lưới là khả thi; chuyển thành vận hành cần giảm phụ thuộc biến, kiểm chứng lại nhãn và thử bằng forecast thật. Không có đủ cơ sở nói phải bỏ ERA5, GSMaP chắc chắn tốt hơn tại Đà Nẵng, hoặc thêm nhiều nguồn sẽ cải thiện kết quả.

Tài liệu định hướng trước đó của mình còn dựa quá nhiều vào lựa chọn đã ghi trong dự án. Cần sửa mức chắc chắn ở ba điểm: nhận diện nguồn nhãn cũ, bằng chứng ưu thế GSMaP theo giờ, và khả năng thay đầu vào ERA5 bằng forecast tương ứng.

## 2. Phát hiện quan trọng nhất: bảng nhãn cũ chưa phải kiểm định ERA5 thuần

Trong `scripts/fetch_openmeteo_baselines.py`, hàm `fetch_station` gọi Historical Weather API nhưng không đặt tham số `models=era5`. Docstring nói rõ dùng mặc định best_match; sau đó code đặt tên nguồn là `era5_om`.

Tài liệu Open-Meteo cho biết Historical Weather kết hợp nhiều nguồn và có IFS 9 km từ 2017; muốn chuỗi nhất quán phải chọn nguồn ERA5/ERA5-Land tường minh. Cache kiểm tra tại Đà Nẵng năm 2022 không chứa định danh model đủ để chứng minh nguồn ERA5 thuần. [Tài liệu nhà cung cấp](https://open-meteo.com/en/docs/historical-weather-api).

**Hệ quả:** số liệu “ERA5 CSI 0,17” trong bảng đối chiếu 10 trạm không được diễn giải như điểm của ERA5 gốc. Bảng có thể vẫn hữu ích để đánh giá nhãn Open-Meteo cũ. Chưa chứng minh được đó là model nào trong mọi giờ lịch sử; không suy ngược từ tài liệu hiện nay để khẳng định toàn bộ cache là IFS.

**Cần sửa cách viết:** “Nhãn Open-Meteo mặc định cũ có hạn chế; kiểm định riêng ERA5 cần khóa nguồn và ghép đúng giờ.” Câu “ERA5 chỉ bắt 8% mưa ≥100 mm” cũng phải truy lại nguồn, thời kỳ và định nghĩa trước khi dùng làm lý do loại bỏ ERA5.

## 3. Tính lại tại Đà Nẵng: lợi thế nhãn chưa chắc như cách trình bày trước

Đọc các cặp ngày đã có trong `data/operational/label_audit_danang/station_daily_pairs_2021_2023.parquet`, giới hạn 2021–2023, dùng cùng 1.042 ngày đủ quan trắc và ba nguồn. `cube_era5` là trường ERA5 trong dataset, tách biệt với `era5_om` ở bảng cũ.

| Nguồn | Trúng ≥50 mm | Bỏ sót | Báo sai | CSI ≥50 mm/ngày |
| --- | ---: | ---: | ---: | ---: |
| ERA5 trong cube | 19 | 26 | 9 | 0,352 |
| GSMaP hiệu chỉnh | 28 | 17 | 19 | 0,438 |
| IMERG | 19 | 26 | 24 | 0,275 |

GSMaP phát hiện thêm mưa lớn, đồng thời báo sai nhiều hơn ERA5. Bootstrap theo khối 5 ngày, 1.000 lần, seed 20261020, cho chênh CSI GSMaP−ERA5 = **+0,086, CI95% [−0,054; +0,230]**.

Riêng tháng 5–10, cùng 521 ngày và 27 sự kiện: GSMaP CSI **0,487**, ERA5 **0,467**; chênh **+0,021, CI95% [−0,204; +0,243]**. Đây là kiểm tra khám phá trên một trạm, dùng cách ghép ngày hiện có và bootstrap có điều kiện; không giải quyết bất định giờ tích lũy hoặc tính độc lập của trạm.

**Đánh giá:** điểm ước lượng hỗ trợ tiếp tục xem xét GSMaP; chưa đủ kết luận nó chắc chắn vượt ERA5 cho mưa lớn Đà Nẵng. Không thay bảng toàn quốc bằng bảng một trạm rồi coi đó là kết luận toàn vùng. Số lượng sự kiện độc lập quan trọng hơn số ô×giờ lớn.

Tái lập: lọc ngày 2021-01-01 đến trước 2024-01-01, bỏ NaN ở station/cube_era5/cube_gc/point_imerg; dùng `contingency_scores` và `paired_block_bootstrap(..., metric_csi(50), block_days=5, n_boot=1000, seed=20261020)` trong `src/verification.py`. Bảng nguồn: `reports/domain_screen_danang/label_station_scores.csv`.

## 4. Nhãn giờ là điểm yếu lớn hơn việc chọn kiến trúc

Mưa ngày đúng có thể vẫn bị phân bổ sai giữa các giờ. Vì vậy benchmark ngày không đủ xác nhận nhãn 1 giờ/3 giờ. JAXA cảnh báo GSMaP Gauge phụ thuộc phân tích mưa ngày CPC và có sai số ở vùng ít trạm; Gauge NRT không sử dụng trực tiếp quan trắc trạm hiện tại theo cùng cách. [Release note JAXA, trang 3](https://www.eorc.jaxa.jp/GPM/doc/product/ReleaseNote/08_note_GPM-GSMaP_20231110.pdf).

Audit nội bộ có 67,6% lượng Gauge mùa 11–2 nằm tại giờ raw ≤0,01 mm. Đây là dấu hiệu cần kiểm tra mạnh, không xác định bên nào đúng. Có ít nhất ba khả năng: raw bỏ sót mưa, hiệu chỉnh tạo phân bố giờ không phù hợp, hoặc khác biệt ghép/thuật toán cần rà lại. Không được mặc định tất cả là lỗi Gauge.

Không có trạm giờ/radar tham chiếu phù hợp, kết luận hợp lệ trước mắt là “dự đoán sản phẩm mưa GSMaP trên lưới”. Dự án vẫn có giá trị nghiên cứu, nhưng chưa đủ xác nhận lượng mưa thực ở từng giờ hoặc cảnh báo tại xã/phường. Tổng 3/6 giờ có thể giảm một phần sai lệch thời điểm; phải đo, không mặc định gộp giờ giải quyết được nhãn.

**Vấn đề trạm cần kiểm tra riêng:** code lấy ngày GSOD làm 00–24 UTC, gộp cờ D/F/G thành đủ ngày và coi I là khô. Cờ G chỉ mô tả một báo cáo tích lũy 24 giờ, không tự chứng minh mốc kết thúc. Nghiên cứu EOD đã chỉ ra cần xác định cửa sổ tích lũy theo nguồn; bảng lịch sử có Việt Nam GSOD G ở EOD 12. Điều này chưa chứng minh cửa sổ Đà Nẵng 2021–2023 sai, nhưng đủ để yêu cầu kiểm chứng bằng metadata/SYNOP trước khi dùng bảng làm chuẩn. Không tự đổi sang EOD 12. [Yatagai et al., 2020, bảng A1](https://doi.org/10.3390/atmos11080772).

Trong dữ liệu Đà Nẵng 2021–2023, đếm lại có 860 hàng cờ G và 186 hàng cờ I; không phải 1.046 số đo mưa 24 giờ xác nhận độc lập. Cần báo cáo độ nhạy khi bỏ các ngày khô suy định. Việc NOAA có thể nằm trong mạng CPC cũng làm phép so Gauge với trạm chưa được bảo đảm độc lập; chưa xác nhận trạm nào trùng.

## 5. ERA5 train → ECMWF live là một thí nghiệm chuyển nguồn

Khác nguồn có thể khác sai số, độ phân giải, cách tính biến và lead time. Perfect prog là một cách xây dựng mô hình hợp lệ, nhưng cần kiểm tra bằng predictor forecast thật. Không thể gọi đây là hậu xử lý IFS đã được xác nhận nếu chưa train/hiệu chỉnh/đánh giá trên forecast IFS.

Phân biệt đúng cấu hình: pilot S4 có ERA5 giờ đích; BASE/RAW/DOMAIN trong `scripts/screen_danang_domain.py` dùng khí tượng quá khứ, không có biến khí tượng giờ đích. Tuy nhiên, cả khí tượng quá khứ gần hiện tại từ ERA5 cũng không sẵn có khi phát forecast thật. Không đánh đồng tất cả điểm số với “nhìn tương lai”, và cũng không mặc định quá khứ ERA5 là đầu vào vận hành hợp lệ.

**Gọi thử mới ngày 20/10:** Single Runs, một tọa độ 16,05°N–108,15°E, run 2024-10-01T00:00, yêu cầu 24 giờ:

| Model yêu cầu | Kết quả kiểm tra |
| --- | --- |
| ecmwf_ifs | HTTP 200; mưa hữu hạn 23/24, biến bề mặt/TCWV/CAPE 24/24; bốn trường T/RH/tốc độ/hướng gió 850 hPa đều 0/24 hữu hạn |
| ecmwf_ifs025 | HTTP 400: run được yêu cầu không có trong kho |

Tài liệu hiện hành cũng nêu IFS HRES 9 km trên Open-Meteo không có trường tầng áp suất; các trường đó nằm ở model open-data 0,25°. [ECMWF API, Native model variables](https://open-meteo.com/en/docs/ecmwf-api). Kho Single Runs nêu IFS từ 03/2024, các model khác chủ yếu từ 04/2026. [Single Runs](https://open-meteo.com/en/docs/single-runs-api).

**Hệ quả:** pipeline đã kiểm không đủ tái hiện u/v/q850 cho thí nghiệm vận hành năm 2024. Đây là kết quả một run, không chứng minh mọi ngày hoặc mọi kho đều thiếu. Có thể tìm GRIB/kho chính thức khác, nhưng phải chứng minh quyền truy cập, độ phủ và chi phí; không ghi sẵn là đã giải quyết.

Hướng ít phụ thuộc hơn là thử mô hình dùng mưa forecast và những biến bề mặt/TCWV/CAPE đã xác minh có; kiểm tra theo mùa trước khi mở rộng. Không điền 0 cho 850 hPa để dùng checkpoint cũ.

## 6. Quan trắc trễ 4 giờ chưa chắc giúp mục tiêu 1–3 giờ

Theo JAXA, NRT có độ trễ danh nghĩa khoảng 4 giờ; archive NRT v8 cũng được liệt kê cho các giai đoạn lịch sử, nên không được mặc định chỉ có dữ liệu sau khi nhóm bắt đầu logger. Phải kiểm tra đúng bản, khả năng truy cập và việc xử lý lại. [JAXA FAQ](https://sharaku.eorc.jaxa.jp/GSMaP/faq/GSMaP_faq06.html).

Nếu phát forecast lúc 10:00, mưa mới nhất kết thúc khoảng 06:00, thì dự đoán 10:00–13:00 thực chất cách quan trắc mới nhất 4–7 giờ. Sự hữu ích của mưa cũ phụ thuộc chế độ mưa; với đối lưu phát triển nhanh có thể hạn chế. Đây là suy luận vật lý cần kiểm nghiệm, không phải chứng minh vệ tinh vô ích.

Do đó phải có đối chứng không dùng vệ tinh, persistence đúng độ trễ, và mô hình có vệ tinh NRT thật. Không dùng bản MVK lưu trữ rồi dịch 4 giờ để kết luận kỹ năng NRT. Không cần đợi logger nhiều tháng mới bắt đầu nghiên cứu: trước hết kiểm tra archive NRT có thể dùng, giả định latency lịch sử được công bố và phân tích độ nhạy; logger đo riêng độ trễ/độ tin cậy hiện tại.

## 7. Ba paper không bảo đảm hướng hiện tại sẽ thành công

| Paper | Điều có thể học | Điều chưa thể suy ra |
| --- | --- | --- |
| Enhancing rainfall estimation… | Kết hợp ảnh mây, khí tượng, địa hình và trạm để ước lượng mưa | Không chứng minh dự báo trước 1–6 giờ với vệ tinh trễ. Test lấy một số giờ cố định trong cùng giai đoạn 2019–2023; chưa là giữ riêng năm tương lai hoặc trạm mới |
| Development of advanced AI… | So mô hình với bộ biến khí tượng đơn giản | Mục phương pháp chia ngẫu nhiên 70/30; chưa xác định rõ lead time. Không chứng minh kỹ năng dự báo tương lai với dữ liệu có sẵn tại issue |
| Advancing Subseasonal… | Dùng predictor forecast thật và mưa trạm để hậu xử lý | Mục tiêu sự kiện theo vùng/tuần, 186 trạm và hạn 1–6 tuần; không bảo đảm áp dụng cho từng ô/giờ |

Đây là khác biệt về thiết kế đánh giá, không phải kết luận các paper sai. Đặc biệt, bài 2020 nói mưa trạm nhưng dữ liệu đầu vào lấy SWAT/CFSR: nhóm chưa kiểm toán được dữ liệu gốc để khẳng định provenance từng cột.

Nguồn: [PLOS 2026](https://doi.org/10.1371/journal.pone.0342825), mục Training and evaluation, trang 9–10 PDF; [Atmospheric Research 2020](https://doi.org/10.1016/j.atmosres.2020.104845), mục 2.2 và bước 1 mục 3, trang 13–14/18 PDF; [SOLA 2025](https://doi.org/10.2151/sola.2025-034), mục 2.1.

## 8. Hướng khả thi hơn để nhóm lựa chọn

Đây là đề xuất sau phản biện, chưa tự thay quyết định mô hình/phạm vi của nhóm.

| Phương án | Khả thi hiện tại | Điều kiện để kết luận |
| --- | --- | --- |
| Nghiên cứu hồi cứu dự đoán mưa GSMaP 3/6 giờ từ ERA5 | Cao về triển khai kỹ thuật | Giữ đúng phạm vi sản phẩm nhãn; benchmark đơn giản, chia năm/sự kiện, kiểm tra độ bền nguồn |
| Hậu xử lý forecast ECMWF bằng bộ biến tối thiểu, hướng tới app | Có triển vọng và cần pilot xác nhận | Có archive cùng nguồn/live; hiệu chỉnh từ forecast thật; đủ sự kiện ngoài mẫu và đầu vào đến kịp |
| Nowcasting mưa cục bộ từng giờ với NRT trễ 4 giờ + nhiều biến tầng cao | Chưa đủ bằng chứng; phụ thuộc dữ liệu lớn | Phải giải quyết nhãn giờ, nguồn 850 hPa và giá trị thêm của NRT |
| Đồng thời hai sản phẩm, TFT, nhiều vùng, cảnh báo chi tiết | Chưa hợp lý để mở rộng ngay | Chỉ tiếp tục sau khi phép so tối thiểu có kết quả và nguồn ổn định |

Nếu mục tiêu ưu tiên là app thật, đề xuất lấy **hậu xử lý ECMWF với predictor forecast thật** làm đường triển khai chính. Bắt đầu mô hình hiệu chỉnh đơn giản/LightGBM và Bi-LSTM cùng bộ dữ liệu; giữ ERA5 cho nghiên cứu hoặc pretrain có kiểm định. Tạm chưa bắt buộc vệ tinh NRT và đặc trưng tầng cao. Cấu hình 3 giờ/6 giờ phải so với khả năng nguồn và nhãn, chưa tự đổi hạn đã chốt.

Nếu nhóm không lấy được dữ liệu vận hành phù hợp hoặc không có cách kiểm chứng nhãn giờ, nên công bố phạm vi nghiên cứu hồi cứu rõ ràng; có thể xem xét bài toán ngày nếu đáp ứng được dữ liệu/trạm và mục tiêu giảng viên. Đổi sang ngày không tự giải quyết mọi sai số hoặc bảo đảm tốt hơn.

### Pilot nhỏ để quyết định trước khi đầu tư tiếp

1. Chọn một cửa sổ lịch sử cho phép, có cả mưa/khô và nhiều sự kiện, không mở test 2025. Kiểm tra một số run trước; dừng mở rộng số biến nếu thiếu ngay ở nguồn. Chốt trước cách chia train/calibration/evaluation theo các đợt hoặc thời gian liên tục.
2. Rà nhãn trên một số sự kiện; kiểm tra giờ tích lũy trạm, tách Gauge/raw/IMERG. Nếu không có tham chiếu dưới ngày, ghi rõ giới hạn trước huấn luyện.
3. Tạo dataset forecast thật tối thiểu: mưa ECMWF, biến đã xác minh có, thời gian và địa hình nếu cần. Mỗi hàng lưu issue/run/valid time và giả định giờ sẵn có; giữ phiên bản xử lý nguồn.
4. So ECMWF thô, hiệu chỉnh đơn giản và một mô hình nhỏ trên đúng hàng chung. Khi đủ dữ liệu, thêm NRT thật để đo đóng góp riêng. Không lấy điểm mô hình cũ từ ERA5 so trực tiếp với điểm forecast mới.
5. Quyết định bằng kỹ năng trên nhiều sự kiện, sai số/xác suất, FAR, CI và độ phủ nguồn. Pilot ít sự kiện chỉ xác nhận pipeline; không thể xác nhận ưu thế mô hình. Nếu không có tín hiệu, thu hẹp phạm vi thay vì nhân thêm kiến trúc.

Kho forecast gần đây ngắn hơn chuỗi ERA5, nhất là khi vẫn giữ kín 2025. Nhiều ô không bù được thiếu năm và đợt mưa độc lập; pretrain/transfer có thể thử nhưng không phải giải pháp bảo đảm. Chưa có căn cứ hứa mức tăng kỹ năng hoặc thời gian hoàn thành huấn luyện đầy đủ.

## 9. Những điều cần sửa ngay trong cách diễn giải

- Thay “ERA5 không được dùng làm nhãn” bằng lựa chọn có điều kiện: ERA5 dùng được cho benchmark tái phân tích; nhãn quan trắc/ước lượng độc lập phù hợp hơn nếu mục tiêu là mưa thực, nhưng phải kiểm chứng tại vùng và thang thời gian cần dùng.
- Thay “GSMaP đã tốt nhất” bằng “ứng viên nhãn chính hiện tại, có lợi thế điểm ước lượng ở một số phép so; chưa xác nhận ưu thế giờ/3 giờ tại Đà Nẵng”.
- Thay “train ERA5 rồi thay ECMWF” bằng “thí nghiệm chuyển nguồn, cần dữ liệu forecast thực và có thể huấn luyện lại”.
- Đối chứng ECMWF xác suất cần được hiệu chỉnh hợp lý; không diễn giải việc chấm forecast tất định như xác suất 0/1 rồi được BSS âm là bằng chứng ECMWF không có giá trị.
- Không xem số test code đạt, bootstrap sau nhiều lần chọn mô hình hoặc số ô×giờ lớn là chứng minh kỹ năng ngoài mẫu. Các năm 2021–2023 đã được khám phá nhiều lần cần được gọi là validation khám phá.

**Đánh giá cuối:** không cần bỏ dự án, nhưng cần đổi thứ tự ưu tiên sang chứng minh nguồn và mục tiêu đánh giá trước. Điểm khó nhất hiện tại là biết đang học lượng mưa nào và có tái tạo đúng đầu vào lúc phát hành hay không; chưa phải chọn thêm mô hình mạnh hơn.
