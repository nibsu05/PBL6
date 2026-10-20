# Giải thích đầy đủ nghiên cứu dự đoán mưa vùng 24–72 giờ

Ngày 21/10/2026. Tài liệu này giải thích từ mục tiêu đến dữ liệu, mô hình, chỉ số và kết quả, để thành viên chưa đọc mã cũng theo được. Kết quả được lấy từ ma trận đã chạy; không huấn luyện thêm hoặc mở năm 2025 trong bước tổng hợp.

**Kết luận về trạng thái:** đã chạy đủ E0–E7 cho cả TFT và LightGBM trên ba fold phát triển. TFT có ba seed, tổng 72 lượt; LightGBM có 24 pipeline. Đã tái lập 96/96 lượt từ artifact lưu. **Hoàn thành ma trận phát triển chưa có nghĩa hoàn thành nghiên cứu cuối**, vì vùng hiện còn xấp xỉ, nhãn cần kiểm chứng và test 2025 còn giữ kín.

Lộ trình đọc: 1. Đã chạy đủ chưa?; 2. Mục tiêu dự đoán chính xác là gì?; 3. Dữ liệu được biến thành mẫu học thế nào?; 4. E0–E7 thêm những gì?; 5. Vì sao chọn TFT; Informer ở đâu?; 6. So với LightGBM là so cái gì?; 7. Metrics: công thức, ví dụ, ý nghĩa; 8. Chia tập và kiểm định như thế nào?; 9. Bảng đầy đủ 48 dòng chính; 10. Khoảng tin cậy và ý nghĩa cải thiện; 11. Khả thi đến đâu và còn thiếu gì?; 12. Nội dung có thể dùng để báo cáo; 13. Tra cứu đủ 44 đặc trưng; 14. Cách dùng bảng Excel và nguồn tham khảo.

## 1. Đã chạy đủ E0–E7 hay chưa?

Đã chạy đủ. Mỗi E có 9 lượt TFT = 3 năm evaluation × 3 seed, cùng 3 pipeline LightGBM = 3 năm evaluation. Bảng sau được dựng từ run.json, kiểm tra tập hợp năm/cấu hình/seed thực tế; không chỉ đếm tên thư mục hoặc dựa vào kế hoạch.

| Cấu hình | Nhóm | Biến gốc | Cột LGBM | TFT | LGBM | Trạng thái |
| --- | --- | --- | --- | --- | --- | --- |
| E0 | B | 11 | 87 | 9 | 3 | complete |
| E1 | B+A | 23 | 147 | 9 | 3 | complete |
| E2 | B+M | 31 | 187 | 9 | 3 | complete |
| E3 | B+C | 12 | 92 | 9 | 3 | complete |
| E4 | B+A+M | 43 | 247 | 9 | 3 | complete |
| E5 | B+A+C | 24 | 152 | 9 | 3 | complete |
| E6 | B+M+C | 32 | 192 | 9 | 3 | complete |
| E7 | B+A+M+C | 44 | 252 | 9 | 3 | complete |

“Seed” là khởi tạo ngẫu nhiên cho mạng neural. Chạy ba seed giúp thấy mức nhạy với tối ưu hóa; ba seed không tạo thêm ba tập thời tiết độc lập. LightGBM hiện chạy xác định, không lấy mẫu hàng/cột ngẫu nhiên, nên không nhân ba bản giống nhau để gọi là ba thí nghiệm. Một “pipeline LightGBM” có ba đầu hồi quy và chín đầu phân loại sự kiện; con số 24 không phải chỉ có 24 cây quyết định.

Bằng chứng gồm: run.json ghi đủ 96 lượt; checkpoint_audit.json ghi replay cả calibration và evaluation; bảng scores chứa đủ tổ hợp. Các fold cùng chấm E0–E7 trên mask E7 và cùng nhãn. Tình trạng “đủ ma trận” ở đây là ba năm phát triển 2021–2023, chưa phải đã chấm năm test 2025.

## 2. Mục tiêu dự đoán chính xác là gì?

### 2.1. Đầu ra nghiệp vụ và câu hỏi nghiên cứu

Đầu ra nghiệp vụ là **lượng mưa trung bình trên một vùng trong ba khoảng 24 giờ tương lai**. Câu hỏi nghiên cứu là: thêm nhóm thông tin A/M/C có làm dự đoán tốt hơn không, ở ngày nào và mùa nào? Mô hình đồng thời xuất xác suất vượt các ngưỡng mưa để đánh giá khả năng nhận diện sự kiện.

Ví dụ minh họa, không phải dự báo thật: một lần phát hành có thể trả lượng mưa [12,35,5] mm/24 h và các xác suất vượt ngưỡng cho từng ngày. Ba số là ba khoảng riêng. Một số 35 mm là trung bình vùng cho ngày 2; từ đó không suy được mọi nơi trong vùng đều mưa 35 mm.

### 2.2. Ngày 1/2/3 nghĩa là gì?

Gọi t là giờ phát hành. Thí nghiệm phát hành một lần/ngày lúc 00 UTC, tức 07 giờ Việt Nam:

| Đầu ra | Khoảng giờ sau t | Ví dụ minh họa theo giờ Việt Nam |
| --- | --- | --- |
| Y1 | [0,24) | 07 h hôm nay đến trước 07 h ngày mai |
| Y2 | [24,48) | 07 h ngày mai đến trước 07 h ngày kế tiếp |
| Y3 | [48,72) | 07 h ngày thứ ba đến trước 07 h ngày thứ tư |

Đây là định nghĩa đã dùng trong ma trận. “Hạn 24–72 giờ” không có nghĩa đã dự đoán riêng từng giờ từ giờ 24 đến giờ 72; cũng không phải Y2/Y3 là các tổng tích lũy 48/72 giờ. Nếu muốn đầu ra từng giờ hoặc bắt đầu từ 00 h địa phương, phải xác định lại nhãn và chạy giao thức phù hợp.

Hình minh họa: dinh_nghia_han_du_bao.png.

### 2.3. “Mưa vùng trực tiếp” là gì?

Từng giờ, mưa của các ô được lấy trung bình diện tích trước mô hình: p_vùng(t)=tổng[w_i×p_i(t)], với tổng w_i=1. Nhãn ngày là tổng 24 giờ của p_vùng. Vì vậy giữ đơn vị mm trung bình vùng, không cộng mm của 93 ô với nhau. Khí tượng cũng được tổng hợp trước mô hình; một mẫu là một mốc của vùng.

Hiện sử dụng diện tích toàn 93 ô, khoảng 11.074 km². Chưa có giao ranh hành chính chính xác và kiểm tra đầy đủ phần lãnh thổ ngoài hộp nguồn. Do đó tên trung thực là **footprint 93 ô xấp xỉ khu vực Đà Nẵng mới**, chưa khẳng định trung bình đúng toàn địa giới. Đầu ra này không cung cấp bản đồ từng ô, cực đại mưa tại điểm hay cảnh báo từng xã.

## 3. Dữ liệu được biến thành mẫu học thế nào?

### 3.1. Vai trò của từng nguồn

ERA5 và các đại lượng suy ra từ nó cung cấp khí tượng quá khứ: nhiệt độ, ẩm, áp suất, gió, đối lưu, mây, đất và bối cảnh. Nhãn chính là GSMaP Gauge trung bình vùng, cột y_region_gc_mm. Lịch được tính từ timestamp. ERA5 có ích làm đầu vào không có nghĩa mọi biến đều chính xác; GSMaP Gauge cũng là sản phẩm ước lượng cần kiểm chứng với đối chứng phù hợp.

Mưa ERA5 không phải nhãn trong nhánh này. Các cột mưa vệ tinh quá khứ, mưa ERA5 và ONI cũ không được đưa vào ma trận chính hiện tại. Chưa có forecast khí tượng tương lai trong đầu vào. Vùng có một bộ đặc trưng tĩnh không đổi nên không nhân bản các cột hằng như tọa độ/tỉnh để kỳ vọng chúng tự tạo thông tin biến thiên theo thời gian.

### 3.2. Hình dạng mẫu TFT

Lấy 168 giờ trước t, chia thành 28 khối không chồng lấn, mỗi khối 6 giờ và tính trung bình khí tượng. Đầu vào quá khứ có dạng [số_mẫu,28,F], F thay đổi theo E. Ví dụ E0 có F=11, E7 có F=44.

Decoder nhận 12 bước lịch tương lai ×4 biến lịch, tính từ timestamp. Đầu lượng mưa trả [số_mẫu,3]. Đầu sự kiện trả [số_mẫu,3,3]: ba ngày × ba ngưỡng 16/50/100 mm. Dữ liệu lịch tương lai đã biết không phải khí tượng tương lai đã quan trắc; không đưa ERA5 giờ đích vào như forecast.

Một mẫu chỉ được giữ khi có đủ 168 giờ lịch sử E7 và 72 giờ nhãn hợp lệ/permanent/đủ trọng số; nhãn không vượt ranh giới năm. E0–E7 dùng chung những mẫu này để tránh cấu hình ít biến được chấm trên tập dễ hơn. Kết quả mô tả các mốc đủ dữ liệu, chưa bảo đảm hệ thống xử lý được mọi khoảng thiếu.

### 3.3. Chừng đó dữ liệu có lớn không?

Giai đoạn 2015–2023 tạo 3.248 issue ngày hợp lệ. Số mẫu train lớn nhất trong ba fold là 2.536, không phải 93×102.984 mẫu độc lập. Đây là lý do cần mô hình đối chứng đơn giản hơn và kiểm tra quá khớp. Các ô đã gộp trước học; nhiều giờ quá khứ trong một mẫu cũng không tạo thêm nhiều nhãn ngày độc lập.

## 4. E0–E7 bổ sung những đặc trưng gì?

B có 11 biến:7 trường bề mặt và 4 mã lịch. A có 12 biến khí quyển/đối lưu/mây/ẩm đất. M có 20 biến hoàn lưu/vận chuyển ẩm. C có 1 biến SST vùng. Tất cả là nhóm không chồng lấn theo danh mục hiện tại.

Chữ A là tên quy ước của nhóm bổ sung trong thí nghiệm; các biến B/M cũng mô tả khí quyển. “Không chồng lấn” nghĩa là không đưa cùng một cột vào hai nhóm, không có nghĩa các nhóm độc lập về vật lý hay thống kê. Chẳng hạn độ ẩm bề mặt, hơi nước cột và thông lượng ẩm có thể liên quan. Vì vậy thêm nhiều nhóm chưa chắc thêm nhiều thông tin mới; factorial giúp đo từng tổ hợp, chưa tự chứng minh quan hệ nhân quả hoặc mọi tương tác.

| E | Tổ hợp | Số biến | Câu hỏi được kiểm tra |
| --- | --- | --- | --- |
| E0 | B | 11 | Chỉ nền bề mặt/lịch dự đoán được đến đâu? |
| E1 | B+A | 23 | Thêm khí quyển/đối lưu/mây/đất có giúp không? |
| E2 | B+M | 31 | Thêm hoàn lưu/gió/ẩm có giúp không? |
| E3 | B+C | 12 | Thêm riêng SST vùng có giúp không? |
| E4 | B+A+M | 43 | A và M đi cùng nhau có giúp không? |
| E5 | B+A+C | 24 | SST có giúp khi đã có A không? |
| E6 | B+M+C | 32 | SST có giúp khi đã có M không? |
| E7 | B+A+M+C | 44 | Thêm toàn bộ A/M/C so với nền thì sao? |

Các tên thường gặp: t2m là nhiệt độ 2 m; td2m là điểm sương; rh là độ ẩm tương đối; u/v là các thành phần gió; q là độ ẩm riêng; tcwv là hơi nước cột; CAPE/CIN mô tả điều kiện đối lưu; IVT mô tả vận chuyển ẩm tích phân. Danh mục đủ 44 biến, đơn vị và tên cột nằm ở mục 13 và sheet DANH_MUC_BIEN.

Trong V1, trường khí tượng thường có tiền tố mean__, ví dụ mean__rh2m_pct. Các biến ctx/SST/chênh áp giữ hỗ trợ không gian riêng theo mã dựng dữ liệu: SST lấy một hộp biển, chênh áp lấy các vùng/điểm đã khai báo. Nội suy hoặc lặp lại một đại lượng bối cảnh lên 93 ô không tạo 93 quan trắc độc lập.

Tên M nên hiểu là hoàn lưu và vận chuyển ẩm, chưa là chỉ số gió mùa đã kiểm định. C hiện là SST vùng, chưa phải cả ENSO/MJO. Bổ sung nhóm cũng làm tăng số tham số đầu vào TFT (E0 khoảng 121 nghìn, E7 khoảng 361 nghìn), dù giữ hidden 32 và ngân sách epoch. Vì vậy đây là đóng góp trong pipeline hiện tại, chưa cô lập hoàn toàn ảnh hưởng thông tin khỏi năng lực mô hình.

## 5. Vì sao chọn TFT; tại sao chưa dùng Informer làm mô hình chính?

### 5.1. Lý do có cơ sở để thử TFT

Bài TFT gốc kết hợp thành phần xử lý tuần tự, attention, lựa chọn biến và gating cho dự đoán nhiều hạn với các loại covariate khác nhau. [Bài TFT](https://arxiv.org/abs/1912.09363).

Đối với nghiên cứu này, nhận định lựa chọn là: đầu ra có ba hạn và đầu vào nhiều nhóm biến, nên thử cơ chế lựa chọn biến/gating là hợp lý; các lớp tuần tự có thể xử lý biến động ở 28 bước 6 giờ, attention kết nối lịch sử. Đây là lý do thiết kế và giả thuyết để đo, chưa phải bằng chứng TFT chắc thắng. Bằng chứng giải thích hiện tại chủ yếu là ablation E0–E7; chưa có phân tích attention/VSN được kiểm chứng để suy nguyên nhân vật lý.

### 5.2. TFT đang chạy có phải nguyên bản bài báo không?

Tên đúng là bản TFT vùng điều chỉnh. Mã hiện có VSN/GRN, encoder/decoder LSTM, attention dùng chung value và gating. Bỏ static context cho vùng đơn; dùng đầu lượng mưa không âm với loss Tweedie p 1,5 cộng các đầu xác suất BCE. Bài gốc dùng đầu phân vị; bản này không xuất khoảng phân vị dự báo. Không gọi kết quả này là tái lập mọi benchmark của TFT gốc.

Hai loại đầu ra được học cùng nhau nhưng chấm riêng. Đầu xác suất có hậu xử lý để p16≥p50≥p100. Chưa có một phân phối lượng mưa thống nhất bảo đảm mọi tính chất liên hệ giữa đầu mm và đầu xác suất; không suy phân vị từ ba xác suất này.

Static covariates không được khai thác như bài toán nhiều tỉnh; future covariates hiện chỉ là lịch. Khả năng nhận forecast thật là hướng mở rộng, chưa phải ưu thế thực nghiệm đã đo của mô hình đang báo cáo.

### 5.3. Informer có không phù hợp hoặc không khả thi không?

Bài Informer tập trung giảm chi phí xử lý chuỗi dài bằng ProbSparse attention, distilling và decoder sinh nhiều bước. [Bài Informer, AAAI 2021](https://ojs.aaai.org/index.php/AAAI/article/view/17325). Trong mã của tác giả có x_mark_enc/x_mark_dec cho thông tin thời gian; vì vậy không nói Informer hoàn toàn không nhận được lịch hoặc không thể điều chỉnh covariates. [Mã chính thức](https://github.com/zhouhaoyi/Informer2020/blob/main/models/model.py).

Trong thiết kế hiện tại chỉ có 28 bước encoder, 12 bước decoder và 3 đầu lượng mưa ngày. Nhận định của mình là nút thắt chuỗi cực dài chưa rõ ở kích thước này, nên ưu tiên kiểm tra nhóm biến và chất lượng dữ liệu trước khi mở rộng số kiến trúc. Điều đó không chứng minh Informer dự đoán kém hoặc tốn tài nguyên không khả thi.

**Chưa có lần chạy Informer cùng dữ liệu/nhãn/mẫu/hạn/loss/ngân sách trong ma trận này.** Điểm R² của một mô hình cũ ở dữ liệu điểm hoặc benchmark khác không đủ để loại Informer cho bài toán vùng. Nếu giảng viên muốn so kiến trúc, phải đăng ký phép so cùng input, target, calibration, seed và ngân sách phù hợp; chấp nhận cả trường hợp Informer thắng.

### 5.4. Nên viết lý do lựa chọn thế nào?

“Chọn TFT làm kiến trúc thử nghiệm cho nghiên cứu đặc trưng đa biến và nhiều hạn. LightGBM là đối chứng cần thiết để đo giá trị của pipeline neural. Kết quả hiện chưa chứng minh TFT vượt LightGBM; Informer chưa được so cùng giao thức nên giữ là lựa chọn mở rộng.”

## 6. So sánh với LightGBM là so sánh với cái gì và vì sao?

### 6.1. LightGBM là mô hình học, không phải dữ liệu

LightGBM là triển khai gradient boosting trên cây quyết định. Trong cách hiểu đơn giản, nhiều cây được kết hợp, các cây sau góp phần sửa sai số còn lại. Thuật toán học từ tập train, không phải lấy sẵn dự báo mưa của một cơ quan. [Bài LightGBM](https://proceedings.neurips.cc/paper_files/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html).

Trong dự án, đặt hai cách học cạnh nhau: TFT học từ chuỗi khí tượng 28 bước, LightGBM học từ bảng tóm tắt cùng lịch sử. Cả hai dự đoán cùng ba nhãn lượng mưa vùng và chín xác suất sự kiện, trên cùng tập mốc đánh giá.

### 6.2. LightGBM nhận những cột nào?

Với mỗi trường khí tượng của cấu hình E, lấy giá trị trung bình khối 6 giờ cuối, trung bình 24/72/168 giờ, và thay đổi giữa hai khối 6 giờ cuối. Thêm bốn giá trị lịch của khối cuối và 48 giá trị lịch tương lai (12 khối×4). Ví dụ rh850 đưa vào thống kê độ ẩm trên các khoảng quá khứ; không đưa độ ẩm thực ở ngày cần dự báo.

Do mở rộng một biến gốc thành nhiều thống kê, E0 có 87 cột bảng và E7 có 252 cột, trong khi TFT có 11 hoặc 44 biến trên 28 bước. Cột tăng không có nghĩa lấy thêm nguồn hoặc lấy dữ liệu sau t. Đây là hai biểu diễn khác nhau của cùng nguyên liệu; LightGBM hiện không thấy nguyên vẹn toàn bộ thứ tự 28 bước như TFT.

Hồi quy dùng Tweedie; phân loại nhị phân dùng mục tiêu sự kiện cho từng ngày/ngưỡng. Mỗi pipeline có 3 đầu hồi quy và 9 đầu sự kiện. Cấu hình giữ num_leaves 15, tối đa 400 cây, learning rate 0,04, chọn iteration bằng calibration. Đây là đối chứng đã train thật, không phải một đường tham chiếu được vẽ tùy ý.

### 6.3. Vì sao đối chứng này cần thiết?

Với vài nghìn nhãn ngày, một mạng nhiều tham số có thể không hơn cách học trên bảng. Có đối chứng giúp trả lời: lợi ích đến từ nhóm biến mới có xuất hiện ở cả hai họ học không; và mức phức tạp của TFT có mang lại giá trị so với cách học khác không? Đây là nhận định lựa chọn của dự án, không phải định lý LightGBM luôn tốt với dữ liệu nhỏ. Tài liệu thuật toán cũng cảnh báo cây kiểu leafwise có thể quá khớp khi mẫu nhỏ. [LightGBM Features](https://lightgbm.readthedocs.io/en/stable/Features.html).

Hiện là so **hai pipeline dùng cùng nguyên liệu**, chưa phải kiểm định chỉ thay duy nhất kiến trúc: còn khác biểu diễn lịch sử, loss chung/riêng và số lượt seed. Nếu muốn cô lập kiến trúc hơn, có thể bổ sung cây nhận toàn bộ lag hoặc thiết kế các mô hình với cùng biểu diễn và tuning budget, trong một phép thử tiếp theo đã khóa.

### 6.4. Hai câu hỏi khác nhau phải giữ riêng

E7 TFT−E0 TFT đo thay đổi đặc trưng trong họ TFT. E7LightGBM−E0LightGBM đo thay đổi đặc trưng trong họ cây. E7 TFT so E7LightGBM đo hai pipeline cùng nguồn đầu vào. Nhóm biến hữu ích không bắt buộc mô hình neural phải thắng cây; nghiên cứu đặc trưng vẫn có kết quả nếu đối chứng đơn giản hơn tốt hơn.

Ngoài LightGBM, khí hậu theo tháng/lead học từ train và luôn 0 cũng đã được chấm. Tham chiếu khí hậu dùng để kiểm tra mô hình có hơn một xác suất theo mùa đơn giản hay không. Persistence cần nguồn mưa quá khứ; vì nhánh chính hiện không dùng mưa quá khứ, chưa thêm nó rồi gọi là cùng thông tin.

## 7. Metrics là gì, vì sao dùng và đọc thế nào?

Một con số không trả lời được mọi câu hỏi. Dự đoán lượng mm cần chỉ số lượng; xác suất mưa cần chỉ số xác suất; quyết định báo sự kiện cần chỉ số trúng/bỏ sót/báo nhầm. Tách ba loại này trước khi đọc bảng.

| Chỉ số | Đo gì | Đơn vị | Chiều tốt |
| --- | --- | --- | --- |
| RMSE | Lượng mưa | mm/24 h | Nhỏ hơn |
| MAE | Lượng mưa | mm/24 h | Nhỏ hơn |
| bias | Lượng mưa | mm/24 h | Gần 0 |
| BS | Xác suất | Không đơn vị | Nhỏ hơn |
| BSS | Xác suất | Không đơn vị | Lớn hơn |
| CSI | Quyết định sự kiện | 0 đến 1 | Lớn hơn |
| POD | Quyết định sự kiện | 0 đến 1 | Lớn hơn |
| FAR | Quyết định sự kiện | 0 đến 1 | Nhỏ hơn |
| CC | Lượng mưa | -1 đến 1 | Thường lớn hơn |
| amount_CSI | Quyết định từ mm | 0 đến 1 | Lớn hơn |
| reliability | Hiệu chỉnh xác suất | Không đơn vị | Gần đường chéo |
| CI | Bất định hiệu số | Theo metric | Tùy metric |

Các công thức dưới đây tương ứng mã verification/short_range_evaluation đang dùng. Định nghĩa chung có thể tra ở [hướng dẫn kiểm chứng khí tượng](https://www.cawcr.gov.au/projects/verification/Stanski_et_al/VerificationSWBPartI.pdf) và [hướng dẫn chỉ số hồi quy](https://scikit-learn.org/stable/modules/model_evaluation.html). Ví dụ số là minh họa tự tạo, không phải dự báo mới.

### 7.1. RMSE, MAE và Bias: lượng mưa lệch bao nhiêu mm?

Gọi y là nhãn thực dùng để chấm, f là dự đoán mm. RMSE=sqrt(mean((f−y)^2)); MAE=mean(abs(f−y)); Bias=mean(f−y). RMSE nhấn mạnh lỗi lớn, phù hợp để không bỏ qua các ngày sai nặng; MAE cho sai số tuyệt đối trung bình; Bias cho biết thiên hướng dự báo thiếu/thừa.

Ví dụ nhãn [0,10,40], dự đoán [0,15,25] thì sai số [0,+5,−15]. MAE=6,67 mm; RMSE=9,13 mm; Bias=−3,33 mm. Ba chỉ số bổ sung nhau: sai số lớn bị RMSE phạt mạnh; sai số dương và âm có thể triệt tiêu trong Bias nên Bias gần 0 chưa đủ tốt.

RMS E20,36 mm/24 h là mức lỗi bình phương trung bình đã căn trên tập mẫu; không có nghĩa từng ngày chắc chắn sai trong ±20,36 mm và chưa phải khoảng tin cậy dự báo. Chỉ so RMSE khi cùng đơn vị/nhãn/hạn; không so RMSE ngày của TFT trực tiếp với RMSE giờ của Bi-LSTM.

### 7.2. BS và BSS: xác suất có ích hơn khí hậu không?

Với sự kiện q=16 mm/24 h, đặt o=1 nếu y≥16, o=0 nếu không; p là xác suất dự báo. BS=mean((p−o)^2), nhỏ hơn tốt hơn. Ví dụ trời thực đạt ngưỡng: p=0,8 bị lỗi 0,04; p=0,2 bị lỗi 0,64. [Định nghĩa Brier score](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.brier_score_loss.html).

BSS=1−BS_mô_hình/BS_khí_hậu. BSS=0 là ngang tham chiếu, >0 tốt hơn, <0 kém hơn. Nếu BS_model=0,06 và BS_ref=0,08 thì BSS=0,25: giảm 25% lỗi Brier so tham chiếu, không phải 25% ngày được dự đoán đúng. Khí hậu hiện là xác suất theo tháng đích/lead, chỉ học train và làm trơn; reference từng fold được ghép cùng dự đoán khi chấm. [Kiểm chứng xác suất so khí hậu](https://www.cawcr.gov.au/projects/verification/Mason/IntegratedVerificationProcedures.pdf).

Trong số hiện tại, TFT ngày 1 E0 BSS=0.135, E7=0.246. ΔBSS≈+0,111 là tăng đơn vị skill score; lượng giảm BS tương đối so với E0 khoảng 12.8%. Hai cách biểu diễn này có mẫu số khác nhau; không gọi là tăng 11,1% accuracy. BSS không có đơn vị mm.

### 7.3. CSI, POD và FAR: phát hiện sự kiện và báo nhầm thế nào?

Để chuyển xác suất thành quyết định, so p≥τ, với τ chọn trên calibration. Đây là ngưỡng xác suất, khác q=16 mm của sự kiện mưa. Có thể τ=0,25 trong một fold; không mặc định mọi ngày/ngưỡng đều 0,5. Ngưỡng số cụ thể có trong bảng calibration.

H là số báo có và thực có; M là số bỏ sót; F là số báo có nhưng thực không; TN là khô báo khô. CSI=H/(H+M+F), POD=H/(H+M), FAR=F/(H+F). CSI tổng hợp trúng/bỏ sót/báo nhầm; POD chỉ tập trung bắt được sự kiện; FAR tập trung các lần báo có bị sai. Cần đọc cùng nhau.

Ví dụ 100 ngày có 10 ngày sự kiện: H=7,M=3,F=5,TN=85. CSI=7/15=0,467; POD=0,700; FAR=5/12=0,417. Mô hình luôn báo khô có accuracy 90% nhưng POD=0 và CSI=0; bởi vậy accuracy đơn thuần dễ gây hiểu nhầm khi ngày khô chiếm nhiều. FAR ở đây là false alarm ratio, không phải tỷ lệ trên tất cả ngày khô.

Trong bảng chính, CSI16/POD16/FAR16 tính từ **đầu xác suất đã hiệu chỉnh và τ calibration**. Cột amount_CSI trong Excel tính trực tiếp từ f≥q, có thể khác. Hai đầu ra mm/xác suất được học riêng nên không tự thay một CSI bằng CSI còn lại. Ô trống ở chỉ số không xác định, ví dụ FAR khi chưa có lần báo có, không có nghĩa điểm 0.

### 7.4. Reliability, CC và những chỉ số không nên lạm dụng

Reliability xem trong các mốc dự báo khoảng 30%, tần suất thực có gần 30% không. Đọc cùng số mẫu; một bin vài điểm không đủ để kết luận đã hiệu chỉnh tốt. CC là tương quan biến động lượng mưa, có thể cao dù dự báo thiếu mm có hệ thống, nên không thay RMSE/Bias.

MAPE dễ gặp phép chia cho 0 khi không mưa; accuracy dễ bị số ngày khô chi phối. R² có thể là chỉ số bổ sung trong một thiết kế nhất quán, nhưng không dùng điểm R² từ dữ liệu/hạn khác để kết luận về pipeline này. Các bảng đã chạy không có R²; không tạo lại bộ chỉ số lựa chọn sau khi nhìn điểm để làm đẹp kết quả.

### 7.5. Vì sao ưu tiên BSS/CSI mà vẫn phải báo lượng mm?

Giao thức hiện giữ BSS/CSI làm trọng tâm sự kiện theo định hướng nhóm, với RMSE/MAE/Bias bổ sung. BSS dùng toàn bộ xác suất; CSI cho khía cạnh quyết định khi sự kiện không nhiều. Đầu lượng mm vẫn là đầu ra nghiệp vụ quan trọng và phải báo đầy đủ. Một cải thiện BSS không tự chứng minh cải thiện lượng mm hay dự báo cực đoan tại điểm.

Epoch TFT hiện chọn bằng Brier calibration trung bình ba ngày; hồi quy và xác suất dùng loss chung. Nếu nhóm muốn lượng mm/RMSE trở thành tiêu chí chọn mô hình chính trong giai đoạn tiếp, cần khóa lại giao thức trước chấm test, thay vì đổi tiêu chí sau khi thấy mô hình nào đẹp điểm hơn. Loss huấn luyện, metric chọn epoch và metric báo cáo là ba việc liên quan nhưng không đồng nhất.

### 7.6. Vì sao có ngưỡng 16, 50 và 100 mm?

Đây là các ngưỡng sự kiện đã giữ trong giao thức của nhóm để so sánh nhất quán; không tìm ngưỡng đẹp nhất trên evaluation. Ngưỡng 16 mm được dùng cho phép kiểm định chính hiện tại; 50/100 mm giúp đọc các mức hiếm hơn nhưng chỉ có 37/15 sự kiện mỗi lead trong bộ gộp, nên bất định lớn. Các số này áp dụng cho **trung bình vùng trong 24 giờ**, không tự mang ý nghĩa cấp cảnh báo mưa tại trạm hoặc mọi xã. Trung bình vùng có thể dưới ngưỡng trong khi một phần vùng mưa rất lớn. Nếu mục tiêu chuyển sang mức cảnh báo địa phương, phải xác định lại đại lượng và ngưỡng theo mục tiêu đó.

## 8. Chia tập, hiệu chỉnh và kiểm định như thế nào?

| Fold | Train | Calibration | Evaluation | Số mẫu train/cal/eval |
| --- | --- | --- | --- | --- |
| F1 | 2015–2019 | 2020 | 2021 | 1809 /364 /363 |
| F2 | 2015–2020 | 2021 | 2022 | 2173 /363 /349 |
| F3 | 2015–2021 | 2022 | 2023 | 2536 /349 /363 |

Train học trọng số/scaler và khí hậu. Calibration chọn epoch/iteration, Platt và τ quyết định; không phải một tập kiểm định độc lập vì được dùng cho nhiều bước. Evaluation đo ngoài giai đoạn fit của từng fold; các năm này đã được dự án xem trước, nên gọi là development. Sau khóa thiết kế mới dùng train 2015–2023/cal 2024/test 2025 theo kế hoạch; chưa làm bước đó trong ma trận hiện tại. Không dùng 2026 để chọn mô hình chấm 2025.

TFT ensemble lấy trung bình dự đoán ba seed trên cùng issue; τ ensemble chọn trên trung bình xác suất calibration. Không lấy trung bình các τ seed và không học τ từ evaluation. Hiệu chỉnh xác suất được làm riêng từng ngày/ngưỡng; thiếu 20 sự kiện hoặc 20 đối sự kiện thì không fit Platt, giữ fallback. Xác suất được chiếu để có p16≥p50≥p100.

Pooled có 1.075 issue/lead. Mỗi lead có 114 sự kiện≥16,37 sự kiện≥50 và 15 sự kiện≥100. Các lead dịch nhãn và có ngày mưa trùng nhau; không cộng thành 342 đợt độc lập. Tháng 3–4 chỉ 4–5 sự kiện≥16/lead, nên một điểm BSS cao ở nhóm đó cần đọc thận trọng.

## 9. Bảng kết quả đầy đủ 48 dòng chính

Các bảng dưới bao phủ 8 E×2 họ×3 ngày; số được gộp trực tiếp trên dự đoán/ref từng dòng 2021–2023, toàn năm. RMSE/MAE/Bias đơn vị mm/24 h; BSS/CSI/POD/FAR cho ngưỡng 16 mm. TFT là ensemble ba seed, LGBM một pipeline xác định. Chi tiết từng seed/năm/mùa/ngưỡng 50/100 nằm trong Excel, không bị loại vì kết quả kém.

### Ngày 1

TFT: trung bình dự báo ba seed

| E | RMSE | MAE | Bias | BSS16 | CSI16 | POD16 | FAR16 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E0 | 20.720 | 7.090 | -2.484 | 0.135 | 0.357 | 0.570 | 0.511 |
| E1 | 20.531 | 6.737 | -2.819 | 0.221 | 0.395 | 0.640 | 0.493 |
| E2 | 20.341 | 6.610 | -2.807 | 0.280 | 0.403 | 0.640 | 0.479 |
| E3 | 20.737 | 7.015 | -2.802 | 0.133 | 0.344 | 0.579 | 0.542 |
| E4 | 20.438 | 6.728 | -2.516 | 0.237 | 0.426 | 0.632 | 0.433 |
| E5 | 20.578 | 6.767 | -2.944 | 0.171 | 0.364 | 0.596 | 0.518 |
| E6 | 20.269 | 6.575 | -2.879 | 0.280 | 0.423 | 0.553 | 0.357 |
| E7 | 20.361 | 6.695 | -2.710 | 0.246 | 0.406 | 0.640 | 0.475 |

LightGBM: một pipeline xác định

| E | RMSE | MAE | Bias | BSS16 | CSI16 | POD16 | FAR16 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E0 | 19.379 | 6.474 | -2.407 | 0.144 | 0.295 | 0.430 | 0.515 |
| E1 | 18.205 | 5.963 | -2.086 | 0.264 | 0.422 | 0.640 | 0.447 |
| E2 | 17.701 | 5.746 | -2.126 | 0.283 | 0.396 | 0.465 | 0.274 |
| E3 | 19.040 | 6.327 | -2.294 | 0.175 | 0.314 | 0.421 | 0.448 |
| E4 | 17.775 | 5.758 | -2.111 | 0.315 | 0.426 | 0.553 | 0.351 |
| E5 | 18.012 | 5.940 | -2.010 | 0.282 | 0.413 | 0.649 | 0.468 |
| E6 | 17.706 | 5.795 | -1.976 | 0.306 | 0.409 | 0.570 | 0.409 |
| E7 | 17.706 | 5.731 | -2.003 | 0.303 | 0.411 | 0.526 | 0.348 |

### Ngày 2

TFT: trung bình dự báo ba seed

| E | RMSE | MAE | Bias | BSS16 | CSI16 | POD16 | FAR16 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E0 | 21.149 | 7.710 | -2.054 | 0.018 | 0.252 | 0.491 | 0.659 |
| E1 | 21.087 | 7.476 | -2.349 | 0.041 | 0.243 | 0.439 | 0.648 |
| E2 | 21.044 | 7.409 | -2.351 | 0.047 | 0.254 | 0.395 | 0.583 |
| E3 | 21.151 | 7.487 | -2.445 | 0.027 | 0.242 | 0.482 | 0.673 |
| E4 | 21.125 | 7.648 | -1.980 | 0.023 | 0.257 | 0.430 | 0.611 |
| E5 | 21.089 | 7.521 | -2.400 | 0.026 | 0.247 | 0.474 | 0.660 |
| E6 | 20.958 | 7.354 | -2.455 | 0.054 | 0.246 | 0.368 | 0.576 |
| E7 | 21.018 | 7.566 | -2.105 | 0.028 | 0.257 | 0.509 | 0.659 |

LightGBM: một pipeline xác định

| E | RMSE | MAE | Bias | BSS16 | CSI16 | POD16 | FAR16 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E0 | 21.204 | 7.415 | -2.701 | -0.015 | 0.243 | 0.535 | 0.692 |
| E1 | 21.374 | 7.502 | -2.726 | -0.034 | 0.218 | 0.404 | 0.678 |
| E2 | 20.579 | 7.093 | -2.633 | 0.060 | 0.276 | 0.439 | 0.573 |
| E3 | 21.152 | 7.473 | -2.553 | -0.038 | 0.247 | 0.482 | 0.665 |
| E4 | 20.758 | 7.169 | -2.661 | 0.046 | 0.295 | 0.500 | 0.581 |
| E5 | 21.351 | 7.509 | -2.651 | -0.035 | 0.252 | 0.491 | 0.659 |
| E6 | 20.631 | 7.130 | -2.592 | 0.056 | 0.251 | 0.421 | 0.616 |
| E7 | 20.756 | 7.238 | -2.551 | 0.043 | 0.277 | 0.456 | 0.587 |

### Ngày 3

TFT: trung bình dự báo ba seed

| E | RMSE | MAE | Bias | BSS16 | CSI16 | POD16 | FAR16 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E0 | 21.292 | 8.130 | -1.612 | -0.034 | 0.197 | 0.412 | 0.725 |
| E1 | 21.287 | 7.947 | -1.935 | -0.028 | 0.231 | 0.544 | 0.713 |
| E2 | 21.344 | 7.985 | -1.797 | -0.030 | 0.206 | 0.412 | 0.708 |
| E3 | 21.270 | 7.849 | -2.124 | -0.026 | 0.206 | 0.474 | 0.733 |
| E4 | 21.383 | 8.188 | -1.459 | -0.029 | 0.221 | 0.509 | 0.718 |
| E5 | 21.246 | 7.996 | -1.838 | -0.028 | 0.196 | 0.456 | 0.744 |
| E6 | 21.237 | 7.926 | -1.886 | -0.016 | 0.227 | 0.491 | 0.704 |
| E7 | 21.321 | 8.104 | -1.565 | -0.038 | 0.201 | 0.412 | 0.719 |

LightGBM: một pipeline xác định

| E | RMSE | MAE | Bias | BSS16 | CSI16 | POD16 | FAR16 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E0 | 21.637 | 7.658 | -2.780 | -0.053 | 0.173 | 0.430 | 0.775 |
| E1 | 21.734 | 7.724 | -2.822 | -0.071 | 0.241 | 0.518 | 0.689 |
| E2 | 21.759 | 7.780 | -2.819 | -0.061 | 0.205 | 0.482 | 0.737 |
| E3 | 21.724 | 7.742 | -2.719 | -0.037 | 0.184 | 0.377 | 0.736 |
| E4 | 21.642 | 7.689 | -2.832 | -0.061 | 0.211 | 0.518 | 0.738 |
| E5 | 21.779 | 7.649 | -2.920 | -0.063 | 0.231 | 0.588 | 0.724 |
| E6 | 21.807 | 7.733 | -2.847 | -0.050 | 0.231 | 0.544 | 0.713 |
| E7 | 21.742 | 7.666 | -2.900 | -0.075 | 0.203 | 0.482 | 0.741 |


### Đối chứng tối thiểu để đọc mức điểm

| Đối chứng | Ngày | RMSE | MAE | BSS16 | CSI16 |
| --- | --- | --- | --- | --- | --- |
| climatology | 1 | 21.179 | 8.036 | 0.000 | 0.000 |
| climatology | 2 | 21.181 | 8.039 | 0.000 | 0.000 |
| climatology | 3 | 21.188 | 8.063 | 0.000 | 0.000 |
| zero | 1 | 23.664 | 7.803 | -0.284 | 0.000 |
| zero | 2 | 23.664 | 7.809 | -0.283 | 0.000 |
| zero | 3 | 23.669 | 7.818 | -0.281 | 0.000 |

CSI của khí hậu/luôn 0 dùng ngưỡngquyếtđịnh 0,5 cố định trong pipelinebaseline; mô hình học cóτ chọn calibration. Vì vậy baselinekhí hậu ở bảng này chủ yếu là tham chiếuBSS; không dùng chênhCSI ấy như một phép so quyếtđịnh đã tối ưu ngưỡng đồng đều. RMSE của khí hậu là trung bìnhmưa theo tháng/lead học train.

### Bảng gọn nhìn đủ ma trận BSS

| E | TFT ngày 1 | TFT ngày 2 | TFT ngày 3 | LGBM ngày 1 | LGBM ngày 2 | LGBM ngày 3 |
| --- | --- | --- | --- | --- | --- | --- |
| E0 | 0.135 | 0.018 | -0.034 | 0.144 | -0.015 | -0.053 |
| E1 | 0.221 | 0.041 | -0.028 | 0.264 | -0.034 | -0.071 |
| E2 | 0.280 | 0.047 | -0.030 | 0.283 | 0.060 | -0.061 |
| E3 | 0.133 | 0.027 | -0.026 | 0.175 | -0.038 | -0.037 |
| E4 | 0.237 | 0.023 | -0.029 | 0.315 | 0.046 | -0.061 |
| E5 | 0.171 | 0.026 | -0.028 | 0.282 | -0.035 | -0.063 |
| E6 | 0.280 | 0.054 | -0.016 | 0.306 | 0.056 | -0.050 |
| E7 | 0.246 | 0.028 | -0.038 | 0.303 | 0.043 | -0.075 |

## 10. Khoảng tin cậy: “cải thiện” có chắc không?

Điểm cao hơn có thể do tập ngày được đánh giá. Bootstrap paired lấy lại các khối ngày liên tiếp trong từng năm, dùng chung trọng số cho nhãn, dự báo và reference khí hậu. Khối 7 ngày là chính,14 ngày kiểm tra nhạy;20.000 lần. Đây là bất định theo thời gian điều kiện trên các mô hình đã fit, không bao phủ hết bất định đào tạo, nhãn hoặc lựa chọn vùng.

Gia đình chính đã khóa là TFT E1−E0, E2−E0, E3−E0 trên ba lead, tổng 9 phép BSS16. Dùng CI 99,44% cho mỗi phép theo Bonferroni để xấp xỉ kiểm soát việc thử nhiều phép; CI 95% khác dùng mô tả. CI không phải xác suất mô hình dự đoán đúng, cũng không là khoảng dự báo mm cho một ngày.

| Phép so TFT | Ngày | Δ BSS16 | CI 99,44% | Đọc kết quả |
| --- | --- | --- | --- | --- |
| E1-E0 | 1 | +0.085 | [+0.0022; +0.1607] | Trên 0 |
| E2-E0 | 1 | +0.144 | [+0.0681; +0.2329] | Trên 0 |
| E3-E0 | 1 | -0.003 | [-0.0426; +0.0327] | Chứa 0 |
| E1-E0 | 2 | +0.023 | [-0.0358; +0.0760] | Chứa 0 |
| E2-E0 | 2 | +0.030 | [-0.0311; +0.0959] | Chứa 0 |
| E3-E0 | 2 | +0.009 | [-0.0188; +0.0344] | Chứa 0 |
| E1-E0 | 3 | +0.006 | [-0.0352; +0.0449] | Chứa 0 |
| E2-E0 | 3 | +0.003 | [-0.0506; +0.0574] | Chứa 0 |
| E3-E0 | 3 | +0.008 | [-0.0174; +0.0337] | Chứa 0 |

Hai CI trên 0 thuộc A/M ngày 1, cùng kết luận với khối 14 ngày. M có mức tăng điểm lớn hơn A; chưa có kiểm định trực tiếp M−A. Với C hoặc ngày 2–3, CI chứa 0 nghĩa là chưa phân biệt chắc lợi ích trong phép thử này, không chứng minh tác dụng bằng 0 trong mọi thiết kế.

E7−E0 đo thêm cả A+M+C, là phép so phụ tiếp nối pilot. E4/E6 có điểm vượt E7 ở một số hàng không tự chứng minh tốt nhất ngoài mẫu; chưa có gia đình kiểm định mọi cặp để chọn cấu hình thắng. Các năm development đã xem trước nên kể cả CI điều chỉnh cũng chưa thay holdout độc lập.

## 11. Khả thi đến đâu và còn thiếu gì?

### 11.1. Khả thi về tính toán: đã đo được

Máy RTX 4060 Laptop 8 GB đã chạy 72 TFT/24 LGBM, tiến trình khoảng 27.9 phút, có artifact và replay 96/96. Mô hình vùng và chuỗi 28 bước gọn giúp khả thi. Con số này không bao gồm mọi thời gian rà soát nguồn, xây ranh, viết mã và làm nghiên cứu. Dự toán 8–30 giờ GPU ban đầu chưa benchmark không còn dùng như thời gian thực của cấu hình này.

### 11.2. Khả thi để báo cáo nghiên cứu phát triển: có

Có câu hỏi về nhóm biến, đối chứng, cùng mẫu, chia tập theo thời gian, nhiều seed, CI và kết quả âm. Tín hiệu mạnh nhất hiện là xác suất ngày 1 với A/M. Ngày 2 còn thấp; tất cả cấu hình hai họ ở ngày 3 có BSS âm. Kết quả chưa ủng hộ tuyên bố đã dự đoán tốt cả 72 giờ.

### 11.3. Chưa đủ để coi đã hoàn tất nghiên cứu hoặc vận hành

- Chốt ranh và trọng số: 93 ô nguyên ô chưa là giao ranh hành chính chính xác; có thể phải bổ sung ô biên/ngoài hộp. Nếu thay vùng, cần dựng và chạy lại phần phát triển liên quan.
- Kiểm chứng nhãn: sản phẩm vệ tinh có sai số và hiệu chỉnh; checksum/replay/hữu hạn chưa là bằng chứng lượng mưa thật chính xác. Biến mã hóa CIN/has_lfc và proxy cũng cần xác minh ý nghĩa nguồn.
- Khả dụng lúc phát hành: ERA5 hồi cứu chưa bảo đảm đầu vào đến kịp t; nếu chuyển sang forecast thật cần cả thời điểm phát hành và giờ có sẵn, chấm lại cùng thông tin.
- Hạn ngày 3: có thể cần forecast thật, thông tin bổ sung hoặc cách học khác. Ma trận chưa cô lập nguyên nhân nên không kết luận chỉ do TFT/Informer.
- Phạm vi suy rộng: một vùng, ba năm development, ít đợt mưa cực đoan và mô hình khác biểu diễn. Chưa có holdout 2025 hoặc kiểm tra vùng khác.

Đề xuất độc lập: tiếp tục TFT như một mô hình nghiên cứu, giữ LightGBM đối chứng mạnh và đọc rõ cả lượng mm lẫn xác suất. Ưu tiên ranh/nhãn và khóa thiết kế trước final. Informer chỉ cần khi câu hỏi kiến trúc hoặc yêu cầu giảng viên cần phép so ấy; chạy để đo, không chạy với mục tiêu định trước là chứng minh nó thất bại.

## 12. Nội dung có thể dùng để báo cáo và những câu nên sửa

“Nhóm đã hoàn thành ma trận phát triển E0–E7 cho dự đoán trực tiếp mưa trung bình vùng ba khoảng 24 giờ. Có 72 lượt TFT và 24 pipeline LightGBM, cùng mẫu/nhãn và ba fold thời gian. Thêm riêng A/M cải thiện xác suất ngày 1 trong phép thử này sau hiệu chỉnh nhiều phép so; SST và ngày 2–3 chưa có bằng chứng tương tự. TFT chưa thể hiện ưu thế tổng thể so LightGBM. Kết quả đang trên footprint 93 ô xấp xỉ; tiếp theo chốt ranh/nhãn và kiểm định năm giữ kín.”

| Cách nói dễ gây hiểu nhầm | Cách nói đúng với bằng chứng hiện tại |
| --- | --- |
| Đã dự báo mưa tốt 72 giờ | Đã chạy đủ ba lead; ngày 3 hiện còn kém khí hậu theo BSS |
| BSS 0,246 là accuracy 24,6% | BSS 0,246 là giảm 24,6% lỗi Brier so khí hậu tham chiếu |
| TFT được chọn vì Informer không khả thi | TFT là giả thuyết kiến trúc đã thử; Informer chưa so cùng giao thức |
| So LightGBM là so với dữ liệu khác | Cùng nguyên liệu/nhãn/mẫu, khác pipeline học và biểu diễn |
| Càng thêm biến càng tốt | Từng nhóm và tổ hợp phải được đo; E7 chưa chắc có điểm tốt nhất |
| 93 ô đúng toàn Đà Nẵng mới | Footprint 93 ô hiện còn xấp xỉ, cần chốt giao ranh |
| Chạy 3 seed có 3225 ngày đánh giá độc lập | Mỗi lead vẫn 1075 issue; 3 seed đo ổn định tối ưu hóa |
| Nhóm C không giúp nên khí hậu biển không quan trọng | Chưa có bằng chứng cho một biến SST vùng đang dùng |

## 13. Tra cứu đủ 44 đặc trưng đang dùng

Danh mục sau được lấy từ feature_catalog.csv đã công bố. Đây là mô tả theo mã dựng nguồn, chưa phải chứng nhận độc lập rằng từng trường đều chính xác. Các biến lịch biết trước; khí tượng chỉ dùng các mốc quá khứ.

### Nhóm B: Nền: bề mặt và lịch (11 biến)

| Tên biến gốc | Đơn vị | Nội dung theo mã nguồn |
| --- | --- | --- |
| t2m_c | °C | Nhiệt độ 2 m |
| td2m_c | °C | Điểm sương 2 m |
| rh2m_pct | % | Độ ẩm tương đối 2 m |
| sp_hpa | hPa | Áp suất bề mặt |
| mslp_hpa | hPa | Áp suất mực biển |
| u10 | m/s | Gió u 10 m |
| v10 | m/s | Gió v 10 m |
| sin_hour | dimensionless | sin giờ địa phương |
| cos_hour | dimensionless | cos giờ địa phương |
| sin_doy | dimensionless | sin ngày-trong-năm |
| cos_doy | dimensionless | cos ngày-trong-năm |
### Nhóm A: Khí quyển, đối lưu, mây, ẩm đất (12 biến)

| Tên biến gốc | Đơn vị | Nội dung theo mã nguồn |
| --- | --- | --- |
| cape | J/kg | CAPE |
| cin_capped | J/kg | CIN, NaN→500 (không có LFC) |
| has_lfc | 0-1 | Tỷ lệ nút có mực đối lưu tự do |
| tcwv | kg/m² | Hơi nước cột |
| kx | K | K-index |
| tt | K | Total Totals |
| blh | m | Độ cao lớp biên |
| tcc | 0-1 | Mây tổng |
| lcc | 0-1 | Mây thấp |
| mcc | 0-1 | Mây trung |
| hcc | 0-1 | Mây cao |
| swvl1 | m³/m³ | Độ ẩm đất lớp 1 |
### Nhóm M: Hoàn lưu và vận chuyển ẩm (20 biến)

| Tên biến gốc | Đơn vị | Nội dung theo mã nguồn |
| --- | --- | --- |
| u850 | m/s | Gió u 850 hPa |
| v850 | m/s | Gió v 850 hPa |
| q850_gkg | g/kg | Độ ẩm riêng 850 hPa |
| t850_c | °C | Nhiệt độ 850 hPa |
| rh850_pct | % | RH 850 hPa |
| w850_pas | Pa/s | Omega 850 hPa (âm = thăng) |
| u500 | m/s | Gió u 500 hPa |
| v500 | m/s | Gió v 500 hPa |
| q500_gkg | g/kg | Độ ẩm riêng 500 hPa |
| t500_c | °C | Nhiệt độ 500 hPa |
| w500_pas | Pa/s | Omega 500 hPa |
| shear_850_500 | m/s | Đứt gió 850–500 hPa |
| ivt_u | kg/m/s | Thông lượng ẩm tích phân, thành phần đông |
| ivt_v | kg/m/s | Thông lượng ẩm tích phân, thành phần bắc |
| ivt_mag | kg/m/s | Độ lớn IVT |
| vimd_mmh | mm/h | Phân kỳ thông lượng ẩm (âm = hội tụ) |
| ctx_tcwv | kg/m² | TCWV trung bình 3×3 nút ERA5 (~0,75°) |
| ctx_ivt_mag | kg/m/s | IVT trung bình 3×3 nút ERA5 |
| cold_surge_dp_hpa | hPa | MSLP Hà Nội − MSLP Đà Nẵng (chỉ số không khí lạnh) |
| dp_tonkin_south_hpa | hPa | MSLP vịnh Bắc Bộ − MSLP Nam Trung Bộ |
### Nhóm C: SST vùng biển (1 biến)

| Tên biến gốc | Đơn vị | Nội dung theo mã nguồn |
| --- | --- | --- |
| sst_region_c | °C | SST trung bình vùng biển 15,5–16,5°B, 108,75–109,5°Đ |

## 14. Cách dùng bảng Excel, tái lập và nguồn tham khảo

Mở BANG_KET_QUA_DAY_DU.xlsx, bắt đầu sheet HUONG_DAN. KET_QUA_48 có đủ 48 dòng chính và mọi cột đã chấm, kể cả BS/CC/amount_CSI. NGUONG_16_50_100 có 144 dòng toàn năm cho hai họ. POOLED_MUA và TUNG_NAM chứa đối chứng/các mùa; các sheet SEED, CI, RELIABILITY và NGUONG_CAL giúp kiểm tra bất định/hiệu chỉnh. Ô trống cho NaN không được tự coi là 0.

Tệp KET_QUA_CHINH_48_DONG.csv thuận tiện để sao chép vào báo cáo. TIEN_DO_E0_E7.csv ghi số biến, cột bảng và số lượt. Build manifest có SHA256 nguồn/đầu ra và mã dựng, giúp đối chiếu tệp. Các bảng là thống kê tổng hợp, không đưa nhãn/dự báo từng issue hoặc checkpoint lên Git.

Các nguồn kỹ thuật đã đối chiếu; phần nhận định áp dụng dự án được phân biệt với kết luận của bài gốc. Không sao chép bài báo/PDF vào repo công khai:

- [TFT, bài gốc](https://arxiv.org/abs/1912.09363)
- [Informer, AAAI 2021](https://ojs.aaai.org/index.php/AAAI/article/view/17325)
- [Informer, mã của tác giả](https://github.com/zhouhaoyi/Informer2020/blob/main/models/model.py)
- [LightGBM, bài gốc NeurIPS 2017](https://proceedings.neurips.cc/paper_files/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html)
- [LightGBM, mô tả thuật toán chính thức](https://lightgbm.readthedocs.io/en/stable/Features.html)
- [Brier score, scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.brier_score_loss.html)
- [Các chỉ số hồi quy, scikit-learn](https://scikit-learn.org/stable/modules/model_evaluation.html)
- [Các phương pháp kiểm chứng khí tượng, CAWCR/WMO](https://www.cawcr.gov.au/projects/verification/Stanski_et_al/VerificationSWBPartI.pdf)
- [Kiểm chứng xác suất so khí hậu, Mason](https://www.cawcr.gov.au/projects/verification/Mason/IntegratedVerificationProcedures.pdf)

Nguồn dự án để kiểm tra: reports/short_range_ablation_2026_10_21/run.json, checkpoint_audit.json, scores_ensemble_pooled.csv, scores_ensemble.csv, scores_seed*.csv, paired_bootstrap.csv; mã src/short_range_dataset.py, tft_regional.py, short_range_evaluation.py, short_range_ablation.py và các scripts tương ứng. Tài liệu này chỉ đọc kết quả đã có, không fit/chấm 2025.
