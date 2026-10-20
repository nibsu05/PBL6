# Dữ liệu cho bài toán dự báo mưa Đà Nẵng: cơ sở lựa chọn và hướng thực hiện

**Tài liệu trao đổi nội bộ nhóm PBL6 — ngày 20/10/2026.**

> **Cập nhật sau phản biện:** Đọc [bản phản biện độc lập ngày 20/10](phan_bien_du_lieu_2026_10_20.md) trước khi chốt hướng triển khai. Bảng nguồn Open-Meteo cũ chưa xác nhận ERA5 thuần; tính lại tại Đà Nẵng chưa khẳng định chắc ưu thế CSI mưa ngày ≥50 mm của GSMaP; probe forecast còn thiếu tầng 850 hPa. Các lựa chọn dưới đây mô tả kế hoạch hiện có, chưa phải bằng chứng hướng này đã khả thi khi vận hành.

Mục đích: thống nhất vì sao dùng ERA5 cùng các nguồn khác, học gì từ ba paper đã đọc và cần làm gì tiếp theo. Đây là tài liệu giải thích và đề xuất thực hiện trong phạm vi kế hoạch hiện có, không phải quyết định mở rộng dữ liệu. Trạng thái thực nghiệm dưới đây dựa trên báo cáo dự án cập nhật đến 14/10/2026; chưa xác minh lại tiến trình logger hoặc chạy thí nghiệm mới ngày 20/10.

## 1. Kết luận để cả nhóm thống nhất

ERA5 tiếp tục là nguồn khí tượng lịch sử quan trọng. Tuy nhiên, cần phân biệt dữ liệu đầu vào, nhãn để học và nguồn kiểm chứng. Dùng ERA5 làm đầu vào không bắt buộc phải dùng lượng mưa ERA5 làm nhãn.

Hướng hiện tại là: **ERA5 cho nghiên cứu hồi cứu; GSMaP hiệu chỉnh trạm làm nhãn mưa trên lưới; mưa vệ tinh raw có độ trễ là đầu vào cần kiểm nghiệm; dữ liệu trạm và IMERG dùng để đối chiếu; dự báo ECMWF IFS cùng GSMaP NRT phục vụ kiểm định khả năng chạy thực tế.** Địa hình là đặc trưng tĩnh có giả thuyết vật lý, chưa được coi là chắc chắn cải thiện mô hình.

Không mặc định càng nhiều nguồn càng tốt. Chỉ giữ nguồn đầu vào khi có lợi ích trên cùng tập mẫu, chi phí phù hợp và có thể lấy kịp lúc phát hành dự báo. Chưa có kết luận AI của nhóm vượt ECMWF khi vận hành.

## 2. Ba khái niệm dễ nhầm

| Khái niệm | Ý nghĩa | Ví dụ trong dự án |
| --- | --- | --- |
| Đầu vào X | Thông tin mô hình được phép sử dụng để tạo dự báo | Gió, độ ẩm, nhiệt độ, mưa vệ tinh quá khứ, địa hình |
| Nhãn y | Lượng mưa hoặc sự kiện mưa mà mô hình học để dự đoán | Mưa GSMaP hiệu chỉnh trạm ở giờ đích |
| Nguồn kiểm chứng | Tham chiếu để xem kết quả có đáng tin không | Mưa trạm theo ngày; IMERG để kiểm tra độ bền |

Ví dụ: đưa độ ẩm ERA5 vào X, dùng mưa GSMaP ở tương lai làm y là một thiết kế bình thường. Khi thêm mưa quá khứ vào X, chỉ được lấy những giờ đã có trước lúc phát hành. Mưa ở tương lai chỉ xuất hiện trong y khi huấn luyện/chấm điểm.

ECMWF là tổ chức vận hành nhiều hệ thống dữ liệu. ERA5 là tái phân tích; IFS là hệ thống dự báo số; S2S là dự báo dưới mùa. Ba tên này không chỉ cùng một bộ dữ liệu. ERA-Interim và CFSR cũng là các bộ tái phân tích khác ERA5.

## 3. Ba paper thực sự dùng dữ liệu như thế nào?

### 3.1. Enhancing rainfall estimation accuracy with machine learning, cloud masking, and multi-source data (2026)

Đây là bài ước lượng mưa từ thông tin vệ tinh và khí tượng tại thời điểm đang xét; không được đồng nhất với dự báo trước 1–6 giờ.

- Đầu vào: ảnh hồng ngoại Himawari-8, ERA5 và địa hình ASTER DEM, giai đoạn 2019–2023.
- Nhãn và tham chiếu đánh giá: mưa từ 175 trạm tự động.
- Sản phẩm đối chiếu: IMERG, GSMaP và PERSIANN-CCS; radar được dùng trong đánh giá một số sự kiện.
- ERA5 cung cấp các biến môi trường khí tượng. Bộ đặc trưng chung có TCW, độ dốc địa hình dưới lưới SLOR, độ ẩm R850 và hai thành phần gió ở 850 hPa.

Lý do tác giả nêu: độ ẩm và gió tầng thấp mô tả luồng không khí mang ẩm từ biển vào đất liền; nước trong cột khí quyển cung cấp thông tin về tiềm năng tạo mưa; địa hình liên quan đến mưa ở sườn đón gió. Ảnh mây, khí tượng và địa hình bổ sung cho nhau. Bài này là một ví dụ dùng đa nguồn, không phải chỉ ERA5.

Vị trí kiểm tra: mục Datasets, trang 5 PDF; giải thích chọn đặc trưng ở trang 12–13. Việc chuyển từ tái phân tích sang dữ liệu gần thời gian thực được nêu như hướng phát triển, không phải bằng chứng đã vận hành tương đương.

Nguồn: https://doi.org/10.1371/journal.pone.0342825

### 3.2. Development of advanced artificial intelligence models for daily rainfall prediction (2020)

- Nguồn thời tiết: Global Weather Data for SWAT. Nguồn này tương ứng CFSR, không phải ERA5; nhận diện dựa trên trang cung cấp và các tài liệu CFSR mà bài trích dẫn.
- Đầu vào: nhiệt độ cao nhất/thấp nhất, tốc độ gió, độ ẩm tương đối và bức xạ mặt trời.
- Theo mô tả của tác giả, mưa được lấy từ trạm khí tượng tại Cao Phong, Hòa Bình và làm đầu ra.
- Dữ liệu: 3.653 mẫu ngày, 2004–2013; so sánh ANN, SVM và PSOANFIS.

Bài không đưa ra phép so chọn CFSR thay ERA5. Việc nguồn này cung cấp sẵn các biến cần thiết là giải thích thực dụng có thể suy luận, không phải kết quả so sánh được tác giả chứng minh. Mục dữ liệu cũng chưa mô tả rõ độ trễ X→y để có thể diễn giải ngay là dự báo trước một số ngày cụ thể.

Vị trí kiểm tra: mục 2.2 Data used, trang 13–14 trong bản PDF Journal Pre-proof do nhóm cung cấp. Giữ nguyên mức chắc chắn của mô tả nguồn; chưa kiểm toán dữ liệu gốc của tác giả.

Nguồn: https://doi.org/10.1016/j.atmosres.2020.104845 ; trang nguồn dữ liệu: https://globalweather.tamu.edu/

### 3.3. Advancing Subseasonal Extreme Rainfall Forecasting in Vietnam Using Machine Learning (2025)

- Đầu vào chính: dự báo ECMWF S2S về độ ẩm đất, gió 850 hPa để tính chỉ số gió mùa và các chỉ số MJO.
- Nhãn: sự kiện mưa cực đoan theo tuần, xác định từ số liệu ngày của 186 trạm tại Việt Nam, 2001–2023.
- Mô hình: RF và XGBoost để hậu xử lý dự báo; huấn luyện 2001–2014, đánh giá 2015–2023; hạn tuần 1–6.
- Tái phân tích ERA được dùng tính chỉ số gió mùa tham chiếu để đánh giá S2S. Trích dẫn Dee et al. (2011) là về ERA-Interim; không có căn cứ gọi nguồn này là ERA5.

Lý do sử dụng S2S: ở hạn nhiều tuần, dự báo mưa cực đoan địa phương khó nhưng các tín hiệu quy mô lớn như MJO và gió mùa còn có khả năng dự báo. ML học mối liên hệ giữa các tín hiệu đó với sự kiện mưa tại từng vùng.

Vị trí kiểm tra: mục 2.1, trang 275 của tạp chí, tức trang 3 PDF; tài liệu tham khảo Dee et al. ở trang 281.

Nguồn: https://doi.org/10.2151/sola.2025-034

### Điều rút ra cho nhóm

Chỉ bài thứ nhất nêu rõ dùng ERA5. Cả ba mô tả sử dụng mưa trạm làm mục tiêu học. Lựa chọn dữ liệu phụ thuộc câu hỏi, hạn dự báo và khả năng tiếp cận quan trắc; tên một nguồn phổ biến không thay cho thiết kế thí nghiệm. Điểm số ba paper không được so trực tiếp với đồ án vì khác nhãn, thời gian, không gian và hạn dự báo.

## 4. Vì sao dự án không lấy luôn mưa ERA5 làm nhãn?

ERA5 kết hợp mô hình và quan trắc để tái dựng thời tiết đã qua. Chuỗi biến đồng bộ, bao phủ rộng và kéo dài nhiều năm rất hữu ích cho huấn luyện. Tuy nhiên, mưa ERA5 là ước lượng của hệ thống mô hình, có sai số và có thể bỏ sót mưa lớn tại địa phương.

Nếu một trận mưa thực tế là 100 mm nhưng nhãn chỉ ghi 40 mm, mô hình dự đoán 40 mm sẽ được chấm tốt theo nhãn đó. Học đúng nhãn chưa đủ để khẳng định dự báo đúng mưa thực tế. Ví dụ này chỉ minh họa nguyên lý, không phải số liệu một sự kiện của dự án.

Bằng chứng nội bộ: đối chiếu cùng 13.836 trạm–ngày tại 10 trạm trong 2021–2024, gồm 437 trạm–ngày mưa ≥50 mm:

| Nguồn mưa | CSI ≥50 mm/ngày |
| --- | ---: |
| Nhãn cũ Open-Meteo Archive ≈ ERA5 | 0,17 |
| IMERG Final V07 | 0,22 |
| GSMaP v8 hiệu chỉnh trạm | 0,33 |

CSI xét số lần phát hiện đúng, bỏ sót và báo sai sự kiện; cao hơn là tốt hơn, không phải tỷ lệ chính xác chung. Hàng nhãn cũ là nguồn qua Open-Meteo, không nên gọi đó là kiểm định trực tiếp mọi sản phẩm ERA5 gốc.

Bảng này hỗ trợ lựa chọn GSMaP hiệu chỉnh làm nhãn hiện tại, nhưng không chứng minh nó luôn tốt nhất. GSMaP hiệu chỉnh dựa vào phân tích mưa trạm CPC, có thể trùng trạm kiểm chứng. Quan trắc điểm khác trung bình ô lưới. Kết quả ngày chưa chứng minh đúng phân bố mưa từng giờ. Đối chiếu trạm là bằng chứng bổ sung có giới hạn về tính độc lập.

Nguồn nội bộ: [báo cáo đối chiếu trạm](../station_benchmark/README.md).

## 5. Vai trò và mức ưu tiên của từng nguồn trong dự án

| Nguồn | Dùng làm gì? | Hướng xử lý |
| --- | --- | --- |
| ERA5 | Khí tượng lịch sử; nền thí nghiệm hồi cứu | Giữ; không coi dữ liệu hồi cứu là sẵn có tại giờ phát hành |
| GSMaP v8 hiệu chỉnh trạm | Nhãn mưa theo ô | Giữ làm nhãn chính; kiểm tra theo mùa, sự kiện và tổng thời gian |
| GSMaP raw lưu trữ | Mưa quá khứ cho thí nghiệm đầu vào | Giữ như một ứng viên; dịch trễ; không mặc định tương đương NRT |
| GSMaP NRT | Đầu vào mưa khi chạy thật | Ưu tiên ghi liên tục, đo độ trễ và so khác biệt với raw lưu trữ |
| ECMWF IFS theo từng run | Đầu vào forecast vận hành và đối chứng | Ưu tiên kiểm tra thời điểm sẵn có, biến, đơn vị, giờ và ô |
| NOAA GSOD | Kiểm tra tổng mưa ngày | Dùng sau QC; không suy ra kiểm chứng mưa từng giờ |
| IMERG Final | Nhãn đối chiếu độ bền kết luận | Không mặc định là đầu vào live; không cần thêm vào mọi cấu hình |
| Địa hình/đặc trưng tĩnh | Phân biệt các ô, kiểm tra giả thuyết địa phương | Giữ đối chứng có/bỏ địa hình; lợi ích còn cần xác nhận |

Hiện nhóm không có Vrain và chưa có mạng trạm giờ tương tự hai paper có 175/186 trạm. Vì thế GSMaP là nhãn thay thế có giới hạn; kết quả so GSMaP cần được mô tả là so với một ước lượng mưa.

Chưa ưu tiên bổ sung Himawari-8, radar, CFSR hay nhiều sản phẩm mưa mới chỉ vì paper có sử dụng. Các nguồn đó chỉ nên mở thành hạng mục khi có câu hỏi cụ thể mà bộ hiện tại chưa trả lời được và có khả năng lấy dữ liệu phù hợp.

## 6. Hai luồng dữ liệu phải phân biệt

### Luồng nghiên cứu hồi cứu

ERA5 + mưa raw quá khứ có độ trễ + địa hình → mô hình → mưa giờ/tổng 3 giờ/xác suất → chấm với GSMaP hiệu chỉnh; đối chiếu tổng ngày với trạm và kiểm tra độ bền bằng IMERG.

Luồng này trả lời nhóm thông tin nào có ích trong điều kiện dữ liệu lịch sử. Nó chưa chứng minh app chạy được ở thời điểm thực.

Trong các cấu hình perfect prog, biến khí tượng ở giờ đích được lấy từ ERA5 khi train. Điều này phải ghi rõ là thiết kế hồi cứu có thông tin khí tượng giờ đích; khi chạy thật phải thay bằng dự báo có sẵn. Không được mô tả điểm đó như dự báo vận hành chỉ dùng dữ liệu quá khứ.

### Luồng kiểm định vận hành

ECMWF IFS đã sẵn có trước giờ phát hành + GSMaP NRT đã nhận trước giờ phát hành + địa hình → mô hình phù hợp nguồn → lưu dự báo → chấm sau khi nhãn đến.

ERA5 không cung cấp trạng thái vừa xảy ra theo thời gian thực: bản sơ bộ ERA5T thường trễ khoảng 5 ngày. Vì vậy phải kiểm tra cả các biến ERA5 quá khứ lẫn giờ đích khi chuyển sang vận hành. Đổi tên cột ERA5 thành ECMWF không bảo đảm hai nguồn có phân bố hoặc kỹ năng tương đương; có thể cần huấn luyện lại hoặc hiệu chỉnh.

Ví dụ minh họa tại 10:00: chỉ được dùng run forecast và tệp NRT đã thực sự sẵn có/được nhận trước 10:00. Tệp có giờ quan trắc 06:00 nhưng đến máy lúc 10:20 không được tính là đầu vào của lần phát hành 10:00. Giờ khởi tạo run cũng không đồng nghĩa giờ bản dự báo đã được công bố.

Nguồn về ERA5: https://www.ecmwf.int/en/forecasts/dataset/ecmwf-reanalysis-v5 ; độ trễ ERA5T: https://www.ecmwf.int/en/about/media-centre/news/2026/era5t-reanalysis-data
