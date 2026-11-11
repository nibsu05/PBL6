# Đánh giá khả thi nhãn mưa vùng và hướng nghiên cứu đề xuất

Ngày 09/11/2026. Đánh giá từ dữ liệu Vrain 2021–2024 và tài liệu nghiên cứu sơ cấp. Chưa mở 2025, chưa dùng số đo 2026 để lựa chọn phương pháp, chưa huấn luyện mô hình dự báo Vrain.

## 1. Quyết định đề xuất

**Chưa chốt chuỗi thuần Vrain cho toàn Đà Nẵng mới làm nhãn chính của thí nghiệm.** Có thể tính một chuỗi bằng nội suy hoặc trọng số, nhưng bằng chứng hiện tại chưa đủ để gọi nó là lượng mưa thực tế đại diện đáng tin cậy cho toàn địa giới.

**Hướng phù hợp nhất với mục tiêu và nguồn lực của nhóm:** giữ nghiên cứu thêm/bớt đặc trưng và dự báo vùng trực tiếp, ưu tiên nhánh ngày 1–3 ngày; chọn một vùng cố định nhỏ hơn có thể kiểm chứng được nhãn. Phần ven biển/nội địa là ứng viên để kiểm tra tiếp, không phải ranh hành chính đã được chốt. Toàn Đà Nẵng mới là bước mở rộng khi bổ sung được lịch sử và kiểm chứng phần vùng núi.

Nếu không xác nhận được thời gian đo hoặc không tìm được vùng có nhãn ổn định, chuyển sang **dự báo tại nhiều trạm bằng một mô hình chung**, dùng mưa đo tại trạm làm nhãn. Khi đó phải đổi tên bài toán và cách đánh giá cho đúng; không lấy trung bình dự báo ở trạm rồi tự gọi là mưa trung bình toàn diện tích thành phố.

Đây là khuyến nghị lựa chọn phạm vi, chưa phải thay đổi âm thầm ranh dữ liệu hay kết quả đang có. Chưa tạo bộ train của vùng khác hoặc chạy lại toàn ma trận.

## 2. Điều cần sửa trong cách đánh giá trước

**Thiếu một phần trạm không tự động làm bài toán mưa vùng bất khả thi.** Điều kiện 100% trọng số của toàn danh mục hiện tại chỉ là một quy tắc lọc nghiêm ngặt. Chỉ số coverage 70%/83,5% trước đây phụ thuộc mạng và phân chia Thiessen đã chọn; nó không có nghĩa đã đo trực tiếp đúng 70%/83,5% diện tích thật.

Có thể ước lượng khi mạng thiếu bằng cách phân chia lại vùng đại diện hoặc nội suy. Cần lưu rõ mạng đang dùng, phương pháp, khoảng thiếu, mức hỗ trợ không gian và bất định. Quy tắc không được đổi trọng số âm thầm vẫn đúng; việc thử một estimator thay đổi theo mạng có khai báo không bị cấm về phương pháp.

Vấn đề phải đo là: **bỏ những trạm thực tế bị thiếu làm ước lượng vùng thay đổi bao nhiêu, ở đâu, trong loại mưa nào?** Các phép thử dưới đây trả lời một phần câu hỏi này.

## 3. Đã thực hiện phép kiểm tra nào?

### 3.1. Bộ tham chiếu nội bộ

Chọn các ngày có đủ 24 giá trị hợp lệ tại cả 82 trạm trong dữ liệu 2021–2024, sau khi loại bằng cờ ba station-day chênh tổng giờ–ngày. Có **67 ngày**, từ **21/08 đến 31/12/2024**: tháng 8/9/10/11/12 lần lượt có 4/8/20/24/11 ngày.

Dùng Thiessen trên footprint R93 để tính một ước lượng từ mạng đầy đủ làm tham chiếu nội bộ. Trong 67 ngày có 24 ngày mưa vùng ≥16, 10 ngày ≥50 và chỉ một ngày ≥100 theo đơn vị mm quy ước của nguồn. Múi giờ/đầu-cuối kỳ vẫn cần xác nhận trước khi ghép dự báo; phép kiểm tra này chỉ so cùng ngày được chọn trên nguồn.

**Tham chiếu này không phải chân lý độc lập.** Nó vẫn có thể sai do cảm biến, vị trí trạm và vùng không được lấy mẫu. 67 ngày cũng không đại diện đủ mùa khô, mọi loại bão hoặc biến động nhiều năm. Con số 69 ngày trong kiểm kê trước chỉ yêu cầu các trạm có trọng số diện tích dương đủ số; phép thử hiện tại yêu cầu đủ cả 82 để so được cả IDW và các mạng con trên cùng mẫu.

### 3.2. Che trạm theo lịch sử thiếu thực tế

Giữ nguyên số đo của 67 ngày trên. Lần lượt che các trạm theo từng mẫu có/thiếu trạm thực tế trong năm 2021, 2022 và 2023. Như vậy có thể so ước lượng từ mạng bị che với ước lượng từ cùng ngày và mạng đầy đủ.

Thử ba cách: chuẩn hóa lại trọng số toàn mạng theo trạm còn số; tính lại Thiessen theo trạm còn số; và IDW nghịch đảo bình phương khoảng cách, tối đa tám trạm gần nhất, tích phân trên vùng. IDW dùng điểm tích phân trong ô, không tạo thêm quan trắc. Không tối ưu tham số để ép kết quả đẹp.

Các phân vị 10/50/90 trong tệp kết quả được tính theo tần suất xuất hiện của từng mẫu thiếu lịch sử. **Chúng không phải khoảng tin cậy thống kê.** Cùng 67 ngày được dùng nhiều lần, không được đếm thành hàng chục nghìn ngày độc lập.

### 3.3. Giấu trạm và giấu cụm không gian

Ở dữ liệu ngày 2021–2024, dùng trạm khác trong cùng ngày để ước lượng giá trị tại trạm được giấu. Thử giấu từng trạm và toàn cụm theo các khối tọa độ cố định 25 km. Trạm bị giấu không được dùng để dự đoán chính nó. So trạm gần nhất với IDW2 tối đa tám trạm.

Đây là **kiểm tra khôi phục dữ liệu không gian**, không phải dự báo ngày tương lai. Sai số tại điểm cũng không trực tiếp bằng sai số trung bình vùng.

## 4. Kết quả quan trọng

NRMSE dưới đây = RMSE chia cho lượng mưa trung bình của bộ tham chiếu. Đây là sai khác tương đối giữa hai ước lượng, không phải tỷ lệ dự báo đúng/sai. Các giá trị làm tròn từ CSV trong cùng thư mục.

### 4.1. Trung bình toàn vùng có vẻ tương đối ổn, nhưng chưa đủ để phê duyệt

| Mẫu thiếu lấy từ | Thiessen tính lại theo mạng còn số: NRMSE trung vị | Chênh tổng lượng mưa trung vị |
| --- | ---: | ---: |
| 2021 | **21,4%** | +9,2% |
| 2022 | **19,8%** | +7,7% |
| 2023 | **16,3%** | +6,2% |

Đây là kết quả giả lập trên 67 ngày cuối 2024, **không phải sai số thật đã đo được của năm 2021/2022/2023**. Cách chuẩn hóa lại trọng số đơn giản cho NRMSE trung vị khoảng 21,9–25,6%, kém hơn Thiessen tính lại trong phép thử này. IDW2 có kết quả tốt hơn tại các điểm giấu nhưng không tự động tốt hơn cho trung bình vùng; không chọn phương pháp chỉ bằng một bảng điểm.

Ngay khi dùng toàn mạng, hai cách tích phân IDW2 và Thiessen cũng khác nhau: NRMSE khoảng 8,3%, chênh tổng khoảng +1,1% trên 67 ngày. Phương pháp gộp là một nguồn bất định cần công bố.

### 4.2. Trung bình toàn vùng che khuất vấn đề ở vùng núi

| Phần của footprint R93 | Mẫu thiếu 2021 | Mẫu thiếu 2022 | Mẫu thiếu 2023 |
| --- | ---: | ---: | ---: |
| Ven biển | 10,0% | 7,1% | 1,6% |
| Nội địa | 8,4% | 8,4% | 6,5% |
| **Vùng núi** | **71,0%** | **69,3%** | **60,0%** |

Các số là NRMSE trung vị của Thiessen tính lại so với mạng đầy đủ cho từng phần. Với mẫu thiếu 2023, phần vùng núi có RMSE khoảng 9,37 và MAE khoảng 5,08 đơn vị mm/ngày, chênh tổng khoảng +23,4%. Không thể kết luận sai lệch luôn là dự báo thiếu mưa; trong phép thử này chênh tổng chủ yếu dương.

Các nhóm ven biển/nội địa/vùng núi đã có trong metadata 93 ô; **không phải Đà Nẵng cũ, không phải địa giới hành chính và chưa phải các vùng đã được chứng nhận chất lượng**. Tín hiệu tốt hơn tại vùng thấp chỉ là cơ sở chọn ứng viên để kiểm định tiếp. Không cắt ranh tùy ý để làm đẹp điểm rồi gọi kết quả là toàn thành phố.

### 4.3. Chọn 45 trạm đầy đủ không giải quyết được vấn đề

Panel 45 trạm được chọn bằng độ đầy đủ ≥98% riêng từng năm 2021 và 2022, không bằng điểm mô hình. Trên cùng 67 ngày, Thiessen từ panel này khác toàn mạng khoảng **23,1% NRMSE**. Kiểm kê hình học trước cho khoảng cách tâm ô xa nhất đến trạm tăng khoảng 34→59 km.

Không nên chọn panel chỉ vì nó tạo ra nhiều hàng đầy đủ hơn. Những trạm bị bỏ có thể mang thông tin không gian quan trọng dù lịch sử đo của chúng ngắn.

### 4.4. Dữ liệu trạm cũng cần QC, kể cả khi đủ số

Trong năm 2024, IDW2 giấu từng trạm có RMSE khoảng 8,76 đơn vị mm/ngày; giấu cả khối 25 km thì khoảng 10,62. Với quan trắc tại trạm ≥50/ngày, RMSE giấu khối khoảng 38,89. Đây không phải sai số TFT hoặc LightGBM. Các chênh lệch có thể gồm biến thiên mưa thật và lỗi số đo, cần điều tra thay vì tự xóa các cực trị.

Nhánh giờ phải kiểm tra riêng. Cùng panel trạm và cùng các ngày, sai khác theo giờ có thể lớn hơn đáng kể theo thước đo tương đối. Không dùng kết luận nhãn ngày để tự duyệt nhãn Bi-LSTM 1–6 giờ; số đối chiếu giờ/ngày nằm trong JSON audit.

## 5. Làm thế nào để chứng minh “đủ tin cậy cho nghiên cứu”?

Không thể chỉ đưa một hệ số tương quan cao hoặc một ngưỡng POD để chứng minh nhãn đúng. Cần hồ sơ bằng chứng cho các phần sau:

| Phần cần đạt | Bằng chứng phải có | Hiện tại |
| --- | --- | --- |
| Định nghĩa vùng | Polygon có nguồn/thời điểm, phạm vi đất liền/đảo rõ; X và y thống nhất vùng | R93 mới xấp xỉ |
| Định nghĩa thời gian | Xác nhận đơn vị, timezone, đầu/cuối kỳ, tổng ngày; không dùng giờ tương lai trong X | Chưa xác nhận đủ |
| Chất lượng trạm | Thiếu, tổng giờ–ngày, lặp, zero kéo dài, vị trí/thiết bị và chênh hai kênh được rà soát | Mới kiểm tra cấu trúc và một phần QC |
| Kiểm định không gian | Giấu trạm/khối, xem riêng địa hình, mùa, mưa lớn; so nhiều phương pháp hợp lý | Đã có probe ban đầu; vùng núi yếu |
| Độ bền trung bình vùng | Che trạm theo lịch sử và giấu nhóm vùng núi; lặp trên nhiều mùa/năm, có tham chiếu độc lập nếu có | Mới 67 ngày cuối 2024 |
| Kết luận mô hình bền với nhãn | Cùng mẫu/split; so thêm ít nhất một nhãn vùng hợp lý; kiểm tra chênh E0–E7 và thứ hạng mô hình có giữ được không | Chưa train Vrain |
| Đánh giá cuối | Khóa estimator, mask, feature và protocol trước mở 2025 | 2025 vẫn giữ kín |

Ngưỡng chấp nhận phải được đăng ký trước đợt xác nhận mới, theo mục đích sử dụng. Không lấy mốc 20% từ một lưu vực nước ngoài làm tiêu chuẩn chung cho Đà Nẵng, cũng không chọn ngưỡng sau khi nhìn kết quả để tuyên bố đạt.

Nếu thay nhãn hợp lý làm kết luận “thêm nhóm M giúp cải thiện” đổi dấu hoặc mất ổn định, chỉ được báo kết quả có điều kiện, chưa khẳng định cải thiện vững. Ngược lại, nhãn có bất định không tự động phủ nhận mọi cải thiện nhỏ; cần so sánh theo cặp và kiểm tra độ bền trực tiếp.

## 6. Hướng triển khai phù hợp nhất

### Phương án chính đề xuất: vùng cố định có thể kiểm chứng, độ phân giải ngày

Giữ mục tiêu dự báo trực tiếp một chuỗi mưa trung bình vùng, ba tổng 24h riêng của ngày 1/2/3. Chọn phạm vi bằng địa lý và điều kiện quan trắc, công bố rõ phạm vi và lý do; kiểm định trên dữ liệu chưa dùng chọn phương pháp. Có thể xét một tiểu vùng đất liền của Đà Nẵng hoặc Đà Nẵng cũ, nhưng Đà Nẵng cũ cũng có vùng núi và phải được kiểm tra, không tự mặc định đủ tốt.

Trước chạy mô hình, chốt hợp đồng thời gian, nguồn polygon, estimator nhãn và số mùa/sự kiện còn lại. Nếu một vùng chỉ còn quá ít mùa hoặc sự kiện mưa lớn, không gọi đó là bộ đủ cho kết luận về cực đoan hoặc về ưu thế mô hình sâu.

ERA5 quá khứ tiếp tục làm X, Vrain sau QC làm y. Giữ B/A/M/C, E0–E7; mưa quá khứ R là thử riêng. Dùng LightGBM làm mô hình đầu tiên cùng khí hậu/persistence, sau đó TFT và Informer nhận cùng mẫu và nhãn. Không tăng kích thước mô hình để bù lịch sử quan trắc ngắn. Đầu vào tương lai chỉ là lịch biết trước; ERA5 tương lai không được dùng để biến ước lượng cùng thời điểm thành dự báo.

Nhánh 1–3 ngày là trọng tâm nên ưu tiên vì khả năng kiểm chứng nhãn tốt hơn nhánh giờ. Bi-LSTM của thành viên khác có thể tiếp tục phần kiến trúc/loader, nhưng phải có kiểm định nhãn giờ riêng trước tuyên bố dự báo mưa toàn vùng 1–6h.

### Toàn Đà Nẵng mới: phương án mở rộng có điều kiện

Cần lịch sử hoặc quan trắc độc lập hỗ trợ vùng núi, metadata thời gian/vị trí và thử phương pháp có địa hình nếu cần. Nội suy phức tạp có thể cải thiện, nhưng chưa được thử ở đây và không tạo ra thông tin quan trắc chưa tồn tại. Tự xây sản phẩm mưa lưới có QC/bất định cho cả vùng núi có thể thành một đề tài lớn riêng, vượt phần nghiên cứu đặc trưng ban đầu.

Nếu vẫn chọn toàn vùng trước khi có đủ bằng chứng, tên nhãn phải là **ước lượng mưa vùng từ mạng Vrain với bất định đã công bố**; kết quả mô hình chỉ có giá trị với nhãn ước lượng này. Chưa được gọi là dự đoán đúng lượng mưa thực đo trên toàn thành phố.

### Phương án dự phòng: dự báo tại nhiều trạm

Nếu nhãn vùng không đạt, dùng mưa từng trạm làm nhãn của một mô hình chung, có thông tin vị trí/trạm và khí tượng phù hợp. Chia theo thời gian, kiểm tra thêm trạm bị giữ lại nếu muốn nói khả năng mở rộng không gian. Mẫu ở nhiều trạm trong cùng đợt mưa phụ thuộc nhau, không xem chúng như những mùa khí hậu độc lập. Cách này giảm phụ thuộc vào nhãn diện tích tự tạo nhưng thay đổi mục tiêu gốc, cần trình bày đúng.

## 7. Nghiên cứu liên quan hỗ trợ quyết định nào?

- **Vo và Gourbesville (2014), Vu Gia–Thu Bồn:** so sánh phân bố mưa bằng nhiều phương pháp với 15 trạm trên lưu vực khoảng 10.350 km². Đây là tiền lệ địa phương cho việc ước lượng mưa vùng và xem xét bất định, không phải bằng chứng rằng danh mục 86 trạm hiện tại tự bảo đảm chất lượng. [IAHR, nguồn công bố](https://www.iahr.org/library/infor?pid=10692).
- **O và Foelsche (2019):** dùng mạng dày để đo bất định khi giảm số trạm; vị trí phân bố và thời gian tích lũy ảnh hưởng sai số. Không chuyển các mật độ/ngưỡng từ khu vực nghiên cứu ở Áo sang Đà Nẵng thành tiêu chuẩn bắt buộc. [HESS](https://hess.copernicus.org/articles/23/2863/2019/).
- **Ośródka và cộng sự (2022):** RainGaugeQC cho thấy số đo trạm cần nhiều phép QC và thông tin chất lượng; đủ số không đồng nghĩa đúng số. [AMT](https://amt.copernicus.org/articles/15/5581/2022/).
- **Nguyen và cộng sự (2026), nghiên cứu tại Australia:** nội suy có địa hình và xử lý zero sai có thể cải thiện sản phẩm mưa giờ. Đây là hướng kỹ thuật có thể thử nếu tiếp tục xây nhãn, không chứng minh hiện đã có nhãn Vrain tốt ở Việt Nam. [HESS](https://hess.copernicus.org/articles/30/45/2026/).

## 8. Tệp bằng chứng và tái lập

- `label_feasibility_audit.json`: phạm vi, hash đầu vào, định nghĩa metric và giới hạn.
- `network_thinning_daily.csv`: che trạm theo lịch sử, ba phương pháp và hai loại tham chiếu.
- `zone_thinning_daily.csv`: độ nhạy theo ba nhóm ô R93.
- `spatial_holdout_daily.csv`: giấu trạm/khối, theo năm, nhóm địa hình xấp xỉ và loại mưa.
- `DO_NHAY_NHAN_VUNG.png`: biểu đồ thống kê tổng hợp; không chứa số đo từng trạm/ngày.
- Tái lập phân tích: `scripts/assess_vrain_label_feasibility.py`; kiểm thử: `tests.test_vrain_label_feasibility`.

Nguồn private và gói bàn giao trước giữ nguyên. Tệp công khai chỉ chứa mã và thống kê tổng hợp. Các phép thử ở đây không phê duyệt nhãn cuối, không phải kết quả dự báo, không mở 2025 hoặc dùng số đo 2026 để lựa chọn mô hình.
