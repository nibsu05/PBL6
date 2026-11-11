# Câu hỏi có thể gặp khi báo cáo nhánh 24–72 giờ

Tài liệu đi cùng BAO_CAO_MO_RONG.md. Các kết quả là phát triển hồi cứu trên footprint 93 ô xấp xỉ; năm 2025 còn giữ kín.

## 1. Vì sao tổng hợp 93 ô trước mô hình, không dự báo từng ô?

Vì đầu ra nghiên cứu đã chọn là **lượng mưa trung bình vùng**. Tổng hợp khí tượng và nhãn theo diện tích trước mô hình tạo một chuỗi phù hợp với đầu ra đó; mô hình học trực tiếp ba tổng mưa ngày của vùng. Dự báo từng ô là một bài toán khác, cần đánh giá khả năng phân bố mưa và sai số không gian.

Cách tổng hợp làm mất một phần thông tin không gian. Mưa rất lớn ở một nơi có thể bị làm nhỏ khi lấy trung bình vùng. Vì vậy kết quả này không cung cấp bản đồ, cực đại mưa cục bộ hay cảnh báo cho từng xã. Nếu sau này câu hỏi nghiên cứu đòi hỏi những đầu ra đó, cần mở rộng biểu diễn hoặc đổi bài toán; không thể suy chúng từ một giá trị vùng.

## 2. Có phải 93 ô là 93 quan trắc ERA5 độc lập?

Không. 93 ô là đơn vị của lưới dữ liệu đã ghép, không chứng minh có 93 quan trắc khí tượng độc lập. Các nguồn có lưới và cách xử lý riêng; nội suy hoặc đưa về cùng lưới không tạo thêm thông tin gốc. Khi tổng hợp thành một vùng, một mẫu huấn luyện là **một mốc thời gian**, không phải 93 mẫu.

Hiện dùng diện tích toàn ô. Chưa có trọng số giao giữa ô và ranh hành chính chính xác, nên phải nói “vùng xấp xỉ gồm 93 ô”, chưa khẳng định là trung bình đúng toàn địa giới Đà Nẵng mới.

## 3. Vậy có khác full_features cũ không, nếu cuối cùng vẫn là một chuỗi?

Có. “Một chuỗi” chỉ mô tả hình dạng bảng. Chuỗi cũ trộn biến tại tọa độ với biến trung bình các hộp khác nhau, nhãn là mưa Open-Meteo tại tọa độ. V1 tổng hợp trên tập ô và trọng số được khai báo, nhãn là GSMaP Gauge vùng. Nguyên liệu, đơn vị, hỗ trợ không gian và định nghĩa nhãn khác nhau.

Các biến bối cảnh như SST vùng biển và chênh áp giữa vùng vẫn giữ ý nghĩa hỗ trợ không gian riêng của nguồn. Đưa chúng vào bảng vùng không biến chúng thành 93 quan trắc độc lập hoặc thành SST đo trên 93 ô đất.

Do đó không so trực tiếp hai cột mưa rồi kết luận dữ liệu mới tốt hơn. Muốn so đầu vào phải đưa về cùng nhãn, thời điểm, mẫu và quy trình chấm. Pilot OLD/V1/V2 trước đây là một thí nghiệm riêng; ma trận hiện tại chỉ tách nhóm đặc trưng trên V1.

## 4. Vì sao không dùng ERA5 cho cả đặc trưng và nhãn?

ERA5 giúp cung cấp trường khí tượng nhất quán để nghiên cứu: nhiệt độ, độ ẩm, áp suất, gió, đối lưu và vận chuyển ẩm. Nhãn GSMaP Gauge cho phép mô hình học một sản phẩm ước lượng mưa khác với mưa của tái phân tích, thay vì chỉ học lại mưa ERA5.

Điều đó **không chứng minh** nhãn GSMaP chính xác tuyệt đối hoặc các biến ERA5 còn lại đều đúng. ECMWF cũng nêu những nguồn bất định của ERA5 chưa được biểu diễn đầy đủ, gồm sai số hệ thống của mô hình. [Tài liệu bất định ERA5 của ECMWF](https://confluence.ecmwf.int/pages/viewpage.action?pageId=111158485).

Theo mô tả v8 của JAXA, GSMaP Gauge được điều chỉnh bằng phân tích mưa ngày từ trạm NOAA CPC. Vì vậy không tự coi nó hoàn toàn độc lập với mọi trạm kiểm chứng; cần kiểm tra trạm đối chứng có tham gia sản phẩm hiệu chỉnh hay không. Đây là giới hạn cần kiểm tra, **chưa khẳng định trạm cụ thể của nhóm đã bị dùng trùng**. [Mô tả sản phẩm GSMaP v8, mục 4.1](https://sharaku.eorc.jaxa.jp/GSMaP/document/new/DataFormatDescription_MVK_RNL_v8.0000.pdf).

Kiểm tra checksum hoặc không có NaN chỉ xác nhận tính toàn vẹn, không xác nhận mưa thật.

## 5. Đầu vào và đầu ra cụ thể là gì?

- Mỗi ngày phát hành lúc 00 UTC, tức 07 giờ Việt Nam.
- Lấy **168 giờ quá khứ**, chia thành **28 bước, mỗi bước 6 giờ**. TFT nhận `[số mẫu, 28, số biến]`.
- Decoder có 12 bước lịch tương lai; không nhận thời tiết ERA5 của tương lai hoặc nhãn mưa.
- Đầu ra là ba tổng mưa **24 giờ riêng**: `[t,t+24)`, `[t+24,t+48)`, `[t+48,t+72)`, đơn vị mm/24h trung bình vùng, cùng các xác suất vượt ngưỡng.

Ngày 2 và ngày 3 không phải tổng tích lũy 48 hoặc 72 giờ. Các khoảng cũng không bắt đầu lúc 00 giờ địa phương; bắt đầu theo issue 07 giờ địa phương đã khai báo.

## 6. Vì sao cần ba seed và bootstrap, có đủ tin cậy chưa?

Ba seed giúp phát hiện kết quả phụ thuộc khởi tạo và quá trình tối ưu hóa. Bootstrap khối giúp xem mức nhạy với các cụm ngày thời tiết được lấy mẫu lại. Hai cách trả lời hai nguồn bất định khác nhau; thêm seed không tăng số ngày mưa độc lập.

Phép so chính có chín thành phần nên báo CI đã hiệu chỉnh, thay vì chọn một CI95% đẹp trong nhiều phép thử. Tuy nhiên các năm phát triển đã được dự án xem trước, bootstrap đang điều kiện trên mô hình đã fit, và nhãn/vùng còn hạn chế. Vì vậy đây là bằng chứng phát triển, chưa phải xác nhận cuối trên holdout hoặc ngoài thực tế.

## 7. TFT không thắng LightGBM thì nghiên cứu có thất bại không?

Không cần đặt điều kiện TFT phải thắng. Câu hỏi chính là nhóm đặc trưng nào giúp dự đoán vùng, ở hạn và mùa nào, với mức bất định ra sao. Một kết quả cho thấy mô hình đơn giản đủ tốt, hoặc nhóm biến không giúp ở ngày 3, vẫn trả lời được câu hỏi nếu phép so được kiểm soát và báo cáo đầy đủ.

TFT và LightGBM hiện khác cách biểu diễn lịch sử và đầu ra/loss. Bảng điểm so hai pipeline dùng cùng nguyên liệu; chưa quy mọi chênh lệch cho riêng kiến trúc. Không so RMSE mm/24h này trực tiếp với RMSE giờ của Bi-LSTM.

## 8. Có cần Informer để chứng minh nó không khả thi?

Chưa có phép đo Informer trong ma trận này nên không có cơ sở kết luận nó không khả thi. Nếu mục tiêu là so kiến trúc, phải chạy cùng dữ liệu, nhãn, đầu vào, hạn dự báo và ngân sách phù hợp. Với mục tiêu nghiên cứu đặc trưng hiện tại, ưu tiên ma trận nhóm biến, độ ổn định và chất lượng dữ liệu; Informer là phần mở rộng khi có câu hỏi và nguồn lực rõ.

## 9. Hạn 72 giờ yếu thì cần làm gì?

Trước hết báo đúng điểm và CI, không chỉnh thiết kế theo kết quả năm giữ kín. Thí nghiệm hiện chỉ dùng khí tượng quá khứ; muốn kiểm tra giá trị của dự báo số tương lai cần một nhánh có **bản forecast thật đã phát hành**, kèm thời điểm dữ liệu sẵn có và đối chứng cùng mẫu. Không lấy ERA5 giờ đích rồi gọi đó là forecast.

## 10. Việc gì còn thiếu trước khi gọi là kết quả nghiên cứu cuối?

Chốt phạm vi vùng/trọng số; kiểm chứng nhãn ngày bằng đối chứng phù hợp; xử lý lại và chạy lại development nếu thay dữ liệu; khóa thiết kế; sau đó mới đánh giá năm giữ kín theo giao thức. Ma trận đầy đủ chạy nhanh không có nghĩa các bước dữ liệu và kiểm định đã hoàn thành.
