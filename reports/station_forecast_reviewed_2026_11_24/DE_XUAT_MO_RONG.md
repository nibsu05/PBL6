# Đề xuất mở rộng dự báo mưa tại trạm

Đánh giá ngày 24/11/2026. Đề xuất dùng **Đà Nẵng làm địa bàn tham chiếu và Huế làm nơi thí điểm mở rộng**. Hai địa bàn có thể dùng cùng cách dựng mẫu, mô hình và giao diện. Kết quả ở Huế cần dữ liệu được cấp cho nhóm và một phép thử giữ riêng theo thời gian hoặc theo không gian.

## Phạm vi Vrain đã xác nhận

Trang Vrain công bố **2.815 trạm**, phục vụ **34 tỉnh, thành** và **266 hồ** thủy lợi, thủy điện. Đây là số liệu về mạng lưới. Phạm vi trạm được xuất, số năm lưu trữ, độ phân giải và quyền chia sẻ cần xác nhận theo địa bàn. WATEC giới thiệu tính năng xuất Excel và kết nối dữ liệu qua API. [Trang Vrain](https://www.vrain.vn/) · [Thông tin thiết bị và dịch vụ WATEC](https://watec.vn/products/tram-do-mua-tu-dong-vrain)

**VRain Open API** dành cho đối tác truy xuất số liệu từ các trạm thuộc phạm vi được cấp. API dùng khóa do Vrain cấp và tích hợp từ máy chủ. Tài liệu nêu cửa sổ tối đa **một tuần** cho mỗi truy vấn theo khoảng ngày. Cần hỏi lại về hạn mức, thời gian lưu trữ và xuất khối lượng lớn trước khi lập lịch thu. Tên địa bàn trên giao diện giúp chọn vị trí. Quyền lấy dữ liệu nghiên cứu cần được xác nhận với đơn vị quản lý. [Hỗ trợ WATEC](https://watec.vn/pages/support) · [VRain Open API](https://dev.vrain.vn/)

Tại Đà Nẵng, kho hiện có mưa giờ hợp lệ đến **19h ngày 15/11/2026**. Lần kiểm tra sau làm mới phiên lúc **19:11 ngày 24/11** đọc được danh mục nhóm, nhưng hai đường xuất mưa giờ đang dùng đều trả 404. Có thể kiểm tra đường thu được hỗ trợ bằng một tuần dữ liệu đã có trong kho, đối chiếu từng mốc giờ với bản xuất được cấp qua Open API hoặc Excel. [Báo cáo hai nhánh](../station_forecast_unified_2026_11_24/BAO_CAO_CHI_TIET.md)

## Vì sao chọn Huế

Cục Môi trường từng ghi nhận **49 trạm đo mưa tự động Vrain ở Huế** khi giới thiệu mạng quan trắc địa phương. Hướng dẫn của chính quyền địa phương cũng nêu cách chọn TP Huế để xem mưa trên ứng dụng Vrain. Số trạm, độ phủ từng năm và khả năng xuất cho dự án sẽ được xác minh theo danh mục được cấp. Tên hành chính hiện hành là **thành phố Huế** từ ngày 01/01/2025. Tên Thừa Thiên Huế có thể còn xuất hiện trong dữ liệu lịch sử. [Cục Môi trường](https://vea.mae.gov.vn/tin-tuc-su-kien/12367/tp-hue-ung-dung-cong-nghe-hien-dai-trong-du-bao-thien-tai) · [Hướng dẫn địa phương](https://phongphu.hue.gov.vn/Portals/43/Uploads/H57.104/Nam2025/Thang11/2025_Hue_To_roi_a4x8trang_1.6.pdf) · [Nghị quyết 175/2024/QH15](https://vanban.chinhphu.vn/?classid=0&docid=211916&pageid=27160)

Huế phù hợp vì có mạng quan trắc công khai được ghi nhận, gần Đà Nẵng để dùng chung thiết kế trích GFS, đồng thời có vùng núi và đồng bằng với đặc điểm mưa khác nhau. Thí điểm sẽ đo cả mức độ dùng lại của quy trình và khả năng của mô hình học gộp. Đầu mối xác nhận danh mục và quyền sử dụng là **Trạm Quản lý thông tin khí tượng thủy văn chuyên dùng** thuộc Chi cục Thủy lợi và Biến đổi Khí hậu TP Huế, cùng bộ phận hỗ trợ WATEC. [Địa chí Huế về phân bố mưa](https://hue.gov.vn/Du-dia-chi/tb/Luong-mua-thang-lon-nhat-871470) · [Cổng thông tin TP Huế](https://hue.gov.vn/Trang-chu/Tin-tuc-su-kien/tb/Thanh-lap-Tram-Quan-ly-thong-tin-khi-tuong-thuy-van-chuyen-dung-thuoc-Chi-cuc-Thuy-loi-va-Bien-doi-Khi-hau-941304)

## Dữ liệu cần xin và kiểm tra

1. **Xin phạm vi đọc cho nghiên cứu.** Nêu địa bàn, thời kỳ, nhu cầu đọc tự động và phạm vi kết quả dự định chia sẻ. Xin tệp Excel/CSV hoặc khóa Open API có phạm vi Huế. Nếu được cấp thêm địa bàn, dùng cấu hình quyền tập trung theo phạm vi để quản lý nguồn và nhật ký.
2. **Xin mẫu kèm danh mục trạm.** Cần mã trạm ổn định, tọa độ, lịch sử thay vị trí nếu có, kỳ đo và cờ chất lượng. Thời điểm đo cần đủ ngày, năm và quy ước giờ kết thúc. Ví dụ trong tài liệu API dùng giờ và ngày/tháng, do đó phải đối chiếu năm trên từng khoảng lấy, đặc biệt khi qua ngày 31/12.
3. **Đối chiếu một tuần trước khi xin nhiều năm.** Chọn cả ngày có mưa, ngày khô và ngày thiếu. So với tệp của đơn vị cung cấp. Kiểm tra 0 mm, thiếu số, trùng giờ, mưa tích lũy và độ trễ. Kiểm lại tổng 24 giờ từ 24 khoảng 1 giờ theo cùng mốc.
4. **Kiểm tra độ phủ rồi chọn tập trạm.** Thống kê trạm–ngày đủ, số đợt mưa, độ phủ mùa mưa và số cửa sổ liên tục cho từng nhánh. Ưu tiên lịch sử có nhiều mùa mưa và kỳ kiểm định sau giai đoạn học. Nếu được cấp một kỳ ngắn, có thể dùng để kiểm tra đường thu hoặc khảo sát ngoại vùng trước.

## Phần dùng lại và phần cần sửa

**Thiết kế mở rộng theo địa bàn**

| Hạng mục | Dùng lại từ Đà Nẵng | Việc cần cho Huế |
| --- | --- | --- |
| Quan trắc | QC theo giờ, quy ước mưa và cờ thiếu | Nhận dữ liệu theo quyền và xác minh quy ước |
| Khóa dữ liệu | Ghép trạm, giờ phát và hạn | Thêm mã địa bàn, ID gốc và bảng bí danh theo thời kỳ |
| Đặc trưng giờ | Lịch, mưa quá khứ, cách dùng ERA5 hồi cứu | Ghép tại trạm Huế và xác nhận thời điểm có thể dùng |
| Đặc trưng ngày | NOAA GFS và ba nhãn 24 giờ | Trích lại trường lưới theo tọa độ, tính địa hình |
| Mô hình | LightGBM, Bi-LSTM, GRU và các mốc tham chiếu | Huấn luyện, hiệu chỉnh hoặc chấm ngoại vùng tại Huế |
| Web | Bản đồ xã/phường, thanh chín kỳ, số trạm có số | Cấu hình địa bàn, ranh giới và phạm vi dữ liệu |

Mã hiện tại có cấu hình nhóm Đà Nẵng, mã trạm dạng STxxx và tệp ranh giới địa bàn. Bản mở rộng cần khóa trạm có ID nguồn ổn định và mã địa bàn theo bảng hành chính có phiên bản. Khóa dự báo giữ giờ phát và hạn. Tệp và nhật ký nên chia theo địa bàn, nguồn và thời kỳ. GFS có lưới toàn cầu. Bảng đặc trưng đã trích cho Đà Nẵng chỉ chứa các điểm cũ, vì vậy phải chạy lại bước trích theo danh mục Huế. [GFS của NOAA](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast) · [Bảng mã hành chính Việt Nam](https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/7/19ttg.signed.pdf)

## So sánh khả năng chuyển địa bàn

**Các phương án cần chấm tại Huế**

| Phương án | Cách dựng | Câu hỏi |
| --- | --- | --- |
| Mốc tại Huế | Giữ mưa cho giờ. GFS và MOS cho ngày | Mức kỹ năng tham chiếu tại địa bàn? |
| Chỉ học Huế | Học trên thời kỳ có dữ liệu Huế, chấm các đợt mưa giữ riêng | Dữ liệu tại địa bàn đủ giúp dự báo thế nào? |
| Chuyển từ Đà Nẵng | Giữ nhãn Huế của phép thử ngoài tập học | Kỹ năng ở địa bàn chưa thấy thay đổi thế nào? |
| Học gộp hoặc hiệu chỉnh | Gộp phần học hai nơi, chỉ hiệu chỉnh bằng phần được định trước | Dữ liệu bổ sung có cải thiện trên cùng mẫu Huế? |

Bi-LSTM hiện có mã trạm học được. Phép thử chuyển vùng cần một phiên bản dùng thuộc tính địa hình, tọa độ và khí tượng, hoặc cách biểu diễn trạm chưa thấy được định trước. Giữ chung khóa trạm–giờ phát và ngưỡng của mỗi phép so. Báo RMSE, MAE, Bias, POD, FAR, CSI và Brier/BSS nếu có xác suất. Báo riêng mùa mưa, ca mưa lớn và nhóm địa hình nếu đủ số đợt. Giữ các trạm cùng đợt trong một khối thời gian khi ước lượng bất định. Giữ riêng trạm hoặc vùng kiểm tra khả năng chuyển vị trí, còn giữ riêng thời gian kiểm tra khả năng dự báo các đợt mưa mới.

## Quy mô và lộ trình

Bộ giờ Đà Nẵng có **4.427.280 hàng** cho 86 trạm và khoảng **1,06 GB** Parquet. Với cùng độ dài 2.145 ngày, mật độ cột và tỷ lệ nén, kịch bản **50 trạm** có khoảng **2,57 triệu hàng** và **0,62 GB**. Kịch bản **2.815 trạm** có khoảng **145 triệu hàng** và **34,6 GB** cho một bảng giờ. Đây là ngoại suy. Trường GFS gốc, các bản sao, mẫu huấn luyện và thời gian tải có chi phí riêng. Có thể tái dùng trường GFS cùng ngày và chu kỳ để trích nhiều điểm.

**Lộ trình theo bằng chứng**

| Bước | Phạm vi | Kết quả để quyết định |
| --- | --- | --- |
| Kiểm tra đường thu | Đà Nẵng và một phần Huế được cấp | Có bản xuất hợp lệ, đúng giờ, ghi độ phủ và độ trễ |
| Thí điểm mô hình | Hai địa bàn, một giao thức | So mốc, mô hình địa phương và mô hình gộp trên phần Huế giữ riêng |
| Thí điểm sản phẩm | Một bản đồ chọn hai địa bàn | Chín kỳ, số trạm theo hạn, trạng thái thiếu và sổ giờ phát |
| Mở rộng từng nhóm | Các địa bàn được cấp dữ liệu | Biết độ trễ, tài nguyên và sai số riêng từng nơi |

Ưu tiên **Đà Nẵng và Huế** để có bằng chứng chuyển địa bàn. Bản xuất lịch sử đủ để làm thí nghiệm hồi cứu và bản phát lại. Thử nghiệm tự động theo giờ cần thêm xác nhận về thời điểm quan trắc thực sự đến máy chủ.
