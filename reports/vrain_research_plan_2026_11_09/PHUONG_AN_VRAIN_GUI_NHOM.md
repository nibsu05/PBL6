# Phương án dữ liệu và nghiên cứu khi có quyền truy cập Vrain

**PBL6 — cập nhật 09/11/2026. Dành cho cả nhóm.** Mục tiêu vẫn là nghiên cứu thêm/bớt đặc trưng để dự đoán trực tiếp lượng mưa trung bình vùng Đà Nẵng mới. Tài liệu này là phương án triển khai có điều kiện trên dữ liệu thực tế; chưa phải kết quả huấn luyện Vrain.

## 1. Đề xuất chính và điều kiện để bắt đầu

**Giữ ERA5 làm nguồn khí tượng; dùng mạng trạm Vrain để xây nhãn mưa vùng mới sau kiểm kê/QC.** Hai nhánh dùng chung dữ liệu gốc, vùng và quy ước thời gian: Bi-LSTM dự đoán sáu lượng mưa giờ tiếp theo; LightGBM/TFT/Informer dự đoán ba tổng mưa 24 giờ riêng. Tổng hợp không gian trước khi học; mỗi mẫu vẫn là một thời điểm của cả vùng.

Có tài khoản đã giải quyết một phần nút thắt truy cập. Chưa giải quyết tự động lịch sử, độ phủ địa hình, dữ liệu thiếu, ranh giới và ý nghĩa timestamp. Không hứa thay CPC bằng Vrain sẽ làm BSS tăng hoặc dự đoán tốt đến ngày 3. Giá trị đầu tiên là có cơ hội xây mục tiêu nghiên cứu sát quan trắc hơn và đo bất định nhãn rõ hơn.

**Chưa chạy lại toàn bộ mô hình ngay.** Thứ tự: kiểm kê đầy đủ → xác minh thời gian/định danh → chốt vùng và mạng lõi → tạo nhãn và kiểm chứng → pilot cùng mẫu → khóa protocol → chạy ma trận. Không thay đổi các báo cáo GSMaP/CPC đã công bố; các điểm cũ thuộc nhãn và giao thức cũ.

## 2. Đã kiểm tra được gì từ tài khoản?

Đã đăng nhập tại [Vrain](https://www.vrain.vn/landing), đọc dữ liệu được tài khoản cho phép và tải thành công một tệp XLSX lịch sử ngày 14/10/2023. Workbook mở được, có một sheet và 24 tiêu đề giờ. Đây là kiểm tra đọc/xuất thực tế, không chỉ đọc hướng dẫn website. Thông tin đăng nhập, cookie và đường dẫn tải có chữ ký không nằm trong tài liệu hoặc Git.

| Bằng chứng trực tiếp | Kết luận được phép đưa ra |
| --- | --- |
| Summary API V1 có 82 mục trạm; V2 có 86 mục | Hai danh mục khác namespace; không cộng thành 168 trạm, không mặc định chỉ có bốn trạm mới |
| Mã và UUID của 82 trạm trong bảng lịch sử khớp inventory V1 82/82 | Có thể nối lịch sử với metadata V1 theo mã; chưa xác nhận tọa độ không đổi trong quá khứ |
| Mã lịch sử không khớp trực tiếp inventory V2 | Không ép nối bằng tên hoặc tự bỏ hậu tố mã; muốn dùng V2 cần crosswalk được xác nhận |
| 10 ngày probe, bảy ngày có 24 hàng giờ và một hàng tổng | Có dữ liệu lịch sử theo hàng giờ ở các ngày này; chưa phải kiểm kê toàn kho |
| Ngày thử 2015, 2019, 2020 chỉ có hàng tổng | Chưa có bằng chứng số liệu giờ ở các ngày đó; không coi hàng tổng 0 là ngày không mưa |
| Dấu `-` xuất hiện ở ô số liệu | Là ô thiếu trong audit; không chuyển thành 0 |
| 490 cặp trạm/ngày đủ 24 số có tổng giờ khớp hàng tổng, sai số ≤ 1e-6 | Bảng có nhất quán số học trên các cặp này; chưa chứng nhận cảm biến, đơn vị hoặc ý nghĩa khoảng đo |
| Độ cao trạm đều thiếu trong hai inventory | Cần metadata bổ sung hoặc DEM có ghi nguồn; DEM không tự trở thành độ cao đo tại trạm |

Các hàng giờ quan sát được chạy từ `20:00 ngày trước` đến `19:00 ngày được chọn`. Đây là bằng chứng về nhãn hiển thị; cần xác nhận múi giờ và một hàng là lượng tăng trong khoảng nào trước khi chuẩn hóa sang UTC. Không áp mốc CPC 12 UTC chỉ vì nhìn giống 19 giờ Việt Nam.

Tệp XLSX mẫu còn ghi thời điểm kết thúc ở phần tiêu đề là 19:20, trong khi nhãn cột cuối là 19:00. Cần làm rõ đây là cách ghi thời điểm báo cáo, chốt khoảng hay quy ước khác; không tự diễn giải thành 24 khoảng đủ một giờ chỉ từ tiêu đề cột.

### Bảng probe để thấy vấn đề dữ liệu thiếu

| Ngày được chọn | Hàng giờ | Trạm đủ 24 giá trị | Thiếu một phần | Không có giá trị giờ |
| --- | --- | --- | --- | --- |
| 14/10/2015 | 0 | 0 | 0 | 82 |
| 14/10/2019 | 0 | 0 | 0 | 82 |
| 14/10/2020 | 0 | 0 | 0 | 82 |
| 15/01/2021 | 24 | 50 | 7 | 25 |
| 14/10/2021 | 24 | 57 | 0 | 25 |
| 14/10/2022 | 24 | 69 | 9 | 4 |
| 15/01/2023 | 24 | 78 | 1 | 3 |
| 14/10/2023 | 24 | 79 | 0 | 3 |
| 15/01/2024 | 24 | 76 | 1 | 5 |
| 14/10/2024 | 24 | 81 | 1 | 0 |

“Đủ 24 giá trị” ở đây chỉ có nghĩa đủ số không âm, hữu hạn trong bảng, chưa qua toàn bộ QC khí tượng. Không suy từ mười probe rằng kho bắt đầu năm 2021, rằng các năm trước hoàn toàn không có dữ liệu, hoặc rằng cả năm 2024 có 81 trạm đầy đủ. Chưa tính diện tích được đại diện; số trạm không phải tỷ lệ diện tích.

Chi tiết máy đọc và SHA256 nguồn: [audit ngoại tuyến](access_audit.json), [bảng probe CSV](history_probe_summary.csv), [kiểm tra truy cập và XLSX](web_access_check.json). Trường `authentication_attempted=false` trong audit ngoại tuyến mô tả chính script đọc tệp; việc đăng nhập/xuất thật được ghi riêng ở kiểm tra truy cập.

**Quyền web khác Open API.** Đã dùng phiên đăng nhập của website. Open API đối tác yêu cầu API key riêng; chưa có bằng chứng tài khoản này có key hoặc quyền toàn quốc. Nếu sử dụng kênh API đó phải tuân theo giới hạn của kênh đó, không suy từ quyền xem web. [Tài liệu Vrain Open API](https://dev.vrain.vn/).

## 3. Vai trò từng nguồn và điều gì thay đổi so với trước

| Thành phần | Nguồn/cách làm đề xuất | Điều cần hiểu đúng |
| --- | --- | --- |
| X khí tượng | ERA5 quá khứ: nhiệt độ, ẩm, áp suất, gió, đối lưu, mây, đất, dòng ẩm, SST | Vrain chưa cung cấp các trường này trong những bảng đã đọc; có mưa trạm không thay thế được khí quyển ba chiều |
| y mưa chính | Ước lượng mưa diện tích từ Vrain sau QC và trọng số cố định | Là phép tổng hợp quan trắc điểm, không phải đo trực tiếp mọi vị trí trong tỉnh |
| R mưa quá khứ | Một kênh mưa vùng Vrain trong quá khứ, nếu dữ liệu/độ trễ cho phép | Là đầu vào bổ sung cần thí nghiệm riêng; khác với y tương lai |
| CPC/GSMaP | Đối chiếu nhãn hoặc thí nghiệm chuyển miền có kiểm soát | Không dùng để lấp nhãn Vrain thiếu rồi gọi đó là nhãn thuần trạm |
| Ranh/DEM | Polygon nghiên cứu có phiên bản; DEM giúp kiểm tra phủ địa hình | Không biến độ cao trung bình cố định của một vùng thành đặc trưng thay đổi theo thời gian |

Trong thí nghiệm cũ, X chính đã là ERA5, còn GSMaP/CPC là nhãn. Vì vậy thay nhãn không đồng nghĩa “bỏ đầu vào vệ tinh” nếu trước đó đầu vào vốn không có mưa vệ tinh. Vrain chủ yếu giúp thay và kiểm tra mục tiêu mưa; ERA5 vẫn có sai số ở các biến khác, không có biến nào được bảo đảm hoàn toàn chỉ do thuộc ERA5.

## 4. Chốt vùng trước khi tổng hợp

Mục tiêu người dùng là Đà Nẵng mới, không phải một trạm Đà Nẵng cũ. Tuy vậy, tên nhóm “Đà Nẵng” trong website không chứng minh mạng đã phủ đúng mọi phần địa giới.

**Bản nghiên cứu cuối phải có polygon có nguồn và hash.** Xác định rõ phần đất liền, đảo gần bờ và phần xa không có trạm. Khuyến nghị đánh giá chính trên phạm vi đất liền được mạng đại diện, nhưng đây là đề xuất về phạm vi cần nhóm chốt; không âm thầm đổi yêu cầu “toàn vùng”. Nếu chưa có nguồn cho phần đảo/ngoài mạng, phải nêu giới hạn hoặc bổ sung nguồn, không kéo ô Thiessen đất liền ra đó và gọi là mưa thực toàn địa giới.

93 ô hiện tại là footprint xấp xỉ, khoảng 11.074 km² theo toàn ô, chưa phải polygon giao ranh chuẩn. Có thể dùng footprint này để kiểm tra kỹ thuật tạm thời, tên phiên bản phải ghi `R93`. Kết quả chính với ranh chuẩn dùng phiên bản khác, ví dụ `R_admin_v1`. Không so riêng hai tổng diện tích để kết luận tỷ lệ phủ đúng ranh.

**X và y phải cùng vùng.** Nếu chuyển từ footprint 93 ô sang polygon chuẩn, phải tính lại cả trọng số ERA5 và trọng số trạm. Nếu ranh chuẩn vượt phần cube đã thu thập, cần tải bổ sung khí tượng hoặc nêu phần thiếu, không tự ngoại suy/điền 0. Trạm gần ngoài ranh có thể giúp ước lượng vùng biên nếu được phép truy cập; không ép trọng số của chúng bằng 0 chỉ vì tọa độ nằm ngoài tỉnh.

## 5. Cần thu thập và lưu những gì?

Tách bốn lớp, không chỉ gửi nhau một CSV đã lấy trung bình:

- **Nguồn nguyên gốc:** JSON/XLSX tải từ quyền được cấp, khoảng thời gian yêu cầu, thời điểm tải, SHA256 và trạng thái request. Không lưu password/cookie/signed URL vào manifest chia sẻ.
- **Danh mục trạm:** namespace V1/V2, ID, UUID, tọa độ, thời gian hoạt động, di chuyển/thay cảm biến, đơn vị, múi giờ và chu kỳ đo. Không lấy tên trạm làm khóa duy nhất. ID hiện tại khớp không tự chứng minh tọa độ lịch sử.
- **Quan trắc chuẩn hóa:** các khoảng thời gian thật, lượng mưa, cờ QC, thiếu/trace, liên kết nguồn và thời điểm có thể sử dụng.
- **Dữ liệu vùng và mẫu học:** trọng số, nhãn giờ/ngày, khí tượng, mặt nạ hợp lệ chung, split và protocol.

Ưu tiên tải danh mục/lịch sử và metadata của phần trước 2025. Kiểm kê theo ngày/tháng để biết lúc nào từng trạm thực sự có số, số ngày đầy đủ, độ phủ mùa và số cửa sổ hợp lệ. Một response HTTP 200 hoặc một hàng tổng không xác nhận có số liệu. Không tự tải toàn quốc hay tải ngoài phạm vi tài khoản.

Không giả định kho có từ 2015. Những ngày probe trước 2021 chưa cho thấy số liệu giờ; thời điểm bắt đầu thực phải do kiểm kê đầy đủ quyết định. Trước tải lớn, đo một lô nhỏ để ước lượng dung lượng, giới hạn request và thời gian; tải tiếp được sau gián đoạn, không gửi hàng loạt thiếu kiểm soát.

## 6. Chuẩn hóa thời gian và QC

Trước hết xác nhận năm điểm: đơn vị; timestamp đầu/cuối; múi giờ; lượng tăng/cường độ/bộ đếm/tổng trượt; mã thiếu/trace/reset. Nếu `20:00` được xác nhận là cuối một khoảng giờ địa phương, mới đổi thành khoảng `[19:00,20:00)` tương ứng. Đây hiện là ví dụ quy ước, chưa phải metadata đã được nhà cung cấp xác nhận.

Lưu `period_start_utc`, `period_end_utc`, `rain_mm`, `source_timezone`, `retrieved_at_utc`; lưu thêm `available_at_utc` chỉ khi biết thật thời điểm dữ liệu được cung cấp. Thời điểm tải hồi cứu hôm nay không chứng minh dữ liệu đã có ở giờ dự báo trong quá khứ.

Các kiểm tra bắt buộc gồm trùng/xung đột ID–giờ, thiếu khoảng, số âm, NaN/Inf, mã thiếu, reset, đổi thiết bị/vị trí, đơn vị và cộng chồng tổng trượt. Hàng tổng là hàng kiểm tra, tuyệt đối không cộng thêm vào 24 hàng giờ. Giữ giá trị gốc và lý do gắn cờ. Trường hợp cấu trúc bất hợp lệ dừng lô, không tự sửa âm thầm.

Với mưa cực đoan hoặc lệch hàng xóm, gắn cờ và kiểm tra cảm biến/nguồn trước khi loại. Không xóa chỉ vì ERA5 thấp hơn, trạm lân cận khô hơn hoặc vì làm RMSE xấu. Thuật toán RainGaugeQC cũng yêu cầu cân nhắc khí hậu địa phương; không bê ngưỡng của quốc gia khác sang Đà Nẵng. [RainGaugeQC, AMT 2022](https://amt.copernicus.org/articles/15/5581/2022/).

Nguồn đã thấy có hàng giờ. Nếu sau này có số liệu khoảng nhỏ hơn thì gộp thành giờ từ khoảng thật và yêu cầu độ đầy đủ phù hợp; nếu chỉ được tổng ngày thì chỉ dùng nhánh ngày. Không chia mưa ngày xuống giờ. Audit cấu trúc hiện có chỉ nhận hàng giờ có đồng hồ rõ; chưa phải parser mọi định dạng Vrain.

## 7. Từ trạm thành một nhãn vùng

Chọn một mạng trạm lõi có lịch sử và vị trí đủ ổn định trong giai đoạn nghiên cứu. Chọn bằng metadata/development đã đăng ký, không bằng điểm test. Có nhiều trạm tập trung đồng bằng chưa chắc đại diện tốt phần núi. Báo cáo bản đồ trạm/địa hình, khoảng cách tới trạm gần nhất, trọng số lớn nhất và số ngày/mùa thật sự dùng được.

Phương án dễ giải thích để bắt đầu là **Thiessen/Voronoi cắt theo ranh**. Mỗi phần vùng được gán cho trạm gần nhất; trọng số bằng tỷ lệ diện tích phần đó. Đây là phương pháp mưa diện tích được dùng trong HEC-HMS, chưa mô hình hóa đầy đủ địa hình. [USACE: Gage Weights](https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/meteorology/precipitation/gage-weights).

`w_i = area(Voronoi_i ∩ R) / area(R)`

`y_region(t) = Σ_i w_i × rain_i(t)`

Tạo hình và tính diện tích trong CRS phẳng phù hợp, chẳng hạn phép chiếu LAEA đặt tâm tại vùng, lưu WKT và kiểm tra biến dạng. Không tính `.area` trực tiếp trên kinh/vĩ độ. [GeoPandas: area](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoSeries.area.html).

Ví dụ minh họa: ba phần có trọng số 0,5 / 0,3 / 0,2 và mưa 10 / 20 / 0 mm thì mưa vùng là 11 mm. Đây là ví dụ tính toán, không phải quan trắc Vrain. Mưa mm là độ sâu; không cộng 10+20+0 rồi gọi là mưa trung bình vùng.

### Khi một trạm thiếu

Lưu `coverage(t) = Σ_i w_i × valid_i(t)`. Với bản nhãn nghiêm ngặt, chỉ tính khi panel lõi có đầy đủ giá trị cần thiết. Thiếu không phải 0. Không tự chuẩn hóa lại trọng số theo số trạm còn lại rồi coi đó là cùng một quan trắc vùng: phần không gian được đại diện đã thay đổi, đặc biệt nguy hiểm nếu trạm mất truyền khi bão.

Nếu điều kiện đủ mọi trạm làm mất quá nhiều mẫu, cần đo và chọn lại panel lõi theo tiêu chí đã đăng ký, hoặc tạo **phiên bản ước lượng mạng khuyết riêng**, có coverage/cờ và kiểm tra độ nhạy. Không chọn panel riêng cho mỗi giờ và không dùng CPC/ERA5 để lấp y chính. Các probe 50–81 trạm đủ/ngày cho thấy lấy toàn bộ 82 trạm từ đầu rất có thể quá nghiêm ngặt; chưa đủ để xác định panel tối ưu.

Kiểm chứng nhãn bằng rút trạm/leave-one-station-out trên development, độ nhạy panel và phương pháp tổng hợp, cộng giờ–ngày, kiểm tra đợt mưa lớn và tỷ lệ mẫu bị loại theo mùa. Bỏ trạm giúp kiểm tra nội suy tại vị trí trạm, không chứng nhận mọi vùng núi không trạm. Muốn so CPC/GSMaP với Vrain phải cùng vị trí hoặc cùng vùng và cùng khoảng thời gian; chưa biết trạm có tham gia sản phẩm đối chiếu thì không gọi kiểm chứng độc lập hoàn toàn.

## 8. ERA5 được tổng hợp như thế nào?

Giữ các biến khí tượng đã có và cách tính vật lý đã kiểm tra. Trọng số vùng là diện tích giao ô với cùng R của nhãn. Các biến bối cảnh gió/dòng ẩm và SST vẫn giữ miền bối cảnh/hộp biển có chủ đích; không ép toàn bộ biến về polygon đất liền. Lưu riêng trọng số và miền của từng phép tổng hợp.

ERA5 hiện được biểu diễn từ lưới nguồn 0,25° sang lưới 0,1°. 93 ô nhỏ không phải 93 phép đo ERA5 độc lập và nội suy không tạo thêm độ phân giải khí tượng thật. Có thể tái dùng biểu diễn để giữ công việc trước; khi đổi sang ranh chuẩn phải kiểm tra giao ô và dữ liệu nguồn đủ. Audit mới cần kiểm tra cả các nút nguồn ERA5, vì code nội suy cũ có thể bỏ nút NaN rồi chuẩn hóa lại trọng số.

Nhánh giờ giữ chuỗi quá khứ theo giờ. Nhánh ngày trước mắt lấy trung bình đủ 24 giờ cho các đặc trưng vật lý như thiết kế CPC hiện có; gió giữ u/v. Cộng mưa nhưng không cộng nhiệt độ hoặc độ ẩm. Mean ngày có thể làm mất đỉnh CAPE/gió; bổ sung max/min hay chia bước sáu giờ là thí nghiệm sau, không lén thêm khi đang đo tác dụng A/M/C.

Các trung bình tỉnh, phân tán giữa các ô hoặc thống kê theo tiểu vùng đều có thể làm X mà mô hình vẫn xuất trực tiếp một y vùng. Nếu thử thêm biểu diễn không gian, coi đó là nhánh riêng và giữ cùng nhãn/mẫu. Một hằng số độ cao trung bình của duy nhất một vùng không tự mang thông tin thay đổi thời tiết.

## 9. Các nhóm biến và cách thêm mưa quá khứ

| Nhóm | Giờ / ngày | Nội dung |
| --- | --- | --- |
| B — Nền | 11 / 9 | Bảy biến bề mặt; sin/cos giờ và ngày trong năm ở nhánh giờ, bỏ hai mã hóa giờ hằng ở nhánh ngày |
| A — Đối lưu, mây, đất | 12 / 12 | CAPE, CIN, has_lfc, TCWV, K-index, Total Totals, lớp biên, bốn trường mây và ẩm đất |
| M — Hoàn lưu và vận chuyển ẩm | 20 / 20 | Các trường 850/500 hPa, đứt gió, IVT/phân kỳ dòng ẩm, bối cảnh và chênh áp |
| C — Biển | 1 / 1 | SST hộp biển; không gọi là đã kiểm tra đầy đủ ENSO/MJO |
| R — Mưa quan trắc quá khứ, đề xuất mới | 1 / 1 | Một kênh mưa vùng tại mỗi bước quá khứ; theo giờ hoặc tổng 24h đúng khoảng |

Giữ B/A/M/C để đo thông tin khí tượng. **R0** là không có mưa quá khứ; **R1** thêm kênh R. So R0/R1 trên cùng mẫu và cùng độ trễ được định nghĩa. Sau đó nếu chọn R1 làm nền chính, phải giữ R ở mọi E/mô hình. Không lén thêm R riêng cho Bi-LSTM, riêng E7 hay riêng mô hình tốt nhất rồi gán lợi ích cho A/M.

| E | Tổ hợp thêm trên B | Số biến ngày R0 | Số biến ngày R1 |
| --- | --- | --- | --- |
| E0 | Không thêm A/M/C | 9 | 10 |
| E1 | A | 21 | 22 |
| E2 | M | 29 | 30 |
| E3 | C | 10 | 11 |
| E4 | A+M | 41 | 42 |
| E5 | A+C | 22 | 23 |
| E6 | M+C | 30 | 31 |
| E7 | A+M+C | 42 | 43 |

Với nhánh giờ, mỗi con số trên tăng thêm hai mã hóa giờ. Đây là số kênh theo bước, không phải số cột LightGBM sau các phép tóm tắt. R1 là đề xuất một kênh cụ thể; thêm tổng lũy kế, dry spell hay độ phân tán mưa sẽ tạo danh mục khác và phải phiên bản hóa. Dataset giữ cờ QC/coverage để kiểm tra nhưng không tự cho mô hình đọc cờ chất lượng của nhãn tương lai.

Mưa quá khứ đáng thử nhất với 1–6 giờ; vẫn có thể giúp ngày 1 nhưng không bảo đảm ngày 3. Chốt độ trễ quan trắc theo nguồn đã xác minh hoặc ghi rõ kịch bản hồi cứu; biết rằng mưa xảy ra trước t chưa chứng minh dữ liệu đã truyền tới hệ thống trước t.

## 10. Một mẫu huấn luyện sẽ có dạng gì?

| Thành phần | Cực ngắn | Hạn ngắn |
| --- | --- | --- |
| Một mẫu | Một thời điểm t của vùng | Một thời điểm t của vùng |
| X khởi đầu để tái sử dụng | 24 giờ quá khứ × F | Bảy khối ngày quá khứ × F |
| y lượng mưa | Sáu lượng mưa vùng của sáu giờ tiếp theo | Ba tổng vùng [t,t+24h), [t+24h,t+48h), [t+48h,t+72h) |
| Mô hình đối chiếu | Bi-LSTM và LightGBM cùng nhãn | LightGBM, TFT, Informer cùng nhãn |
| Lịch tương lai | Chỉ thông tin lịch biết trước | Ba ngày × sin/cos ngày trong năm |

24 giờ và bảy ngày là lựa chọn ban đầu để tái sử dụng, chưa là độ dài tối ưu đã chứng minh. Nếu cần độ trễ, ghi rõ khoảng quá khứ nào thực sự có thể dùng. Nhãn ba ngày là ba lượng riêng, không phải ba tổng tích lũy 24/48/72h.

Tổng hợp trạm thành y vùng trước; không tạo 82 mẫu lặp từ cùng một t, cũng không coi 93 ô thành 93 quan trắc độc lập. Nhánh ngày chỉ có xấp xỉ một issue/ngày: 4 năm đủ sẽ cho cỡ 1.460 issue trước cửa sổ/QC, không phải 35.040 mẫu ngày. Đó là phép tính minh họa, chưa phải số mẫu Vrain đã có. Dữ liệu giờ nhiều không tự bù được thiếu số mùa để học TFT ngày.

## 11. Chia thời gian và bảo vệ kiểm định cuối

Không mặc định giữ train 2015–2019/cal 2020/eval 2021 khi các ngày probe 2015–2020 chưa có số liệu giờ. Chọn khoảng giao thật của panel và khí tượng, rồi mới xây split. Không chia ngẫu nhiên các cửa sổ chồng lấn.

Nếu kiểm kê xác nhận có giai đoạn đủ trước 2025, có thể thiết kế phát triển cuốn chiếu trong 2021–2024 tùy lịch sử thực có. Đây là đề xuất để khóa sau kiểm kê, chưa là fold được duyệt hoặc đã chạy. Chỉ fit scaler/khí hậu trên train, chọn epoch/hiệu chỉnh xác suất/ngưỡng trên cal; toàn bộ sáu giờ hoặc ba ngày y phải nằm trong split. Các model/E dùng chung mask hoàn chỉnh, kể cả R0/R1 khi so chúng.

Ví dụ có điều kiện nếu panel dùng được từ 2021 đến hết 2024: lượt phát triển thứ nhất train 2021/cal 2022/eval 2023; lượt thứ hai train 2021–2022/cal 2023/eval 2024. Sau khóa thiết kế, có thể train 2021–2023/cal 2024/test 2025. Lượt chỉ có một năm train cần báo hạn chế số mùa, đặc biệt với mạng sâu. Không cố tạo ba fold như CPC khi thiếu lịch sử; nếu panel bắt đầu muộn hơn phải giảm kết luận hoặc đăng ký lại giao thức. Đây chưa phải xác nhận dữ liệu đủ cho các năm ví dụ.

**2025 tiếp tục giữ kín**: lượt này không đọc/tải nhãn năm đó và không chấm mô hình. Không dùng kết quả 2026 để tuning rồi gọi đánh giá 2025 là kiểm định tương lai độc lập. Nếu Vrain không đủ lịch sử để giữ thiết kế đó, phải trình bày lại kế hoạch holdout với nhóm trước khi chạy; không tự mở hoặc thay năm test.

Không nối CPC trước năm có trạm với Vrain sau đó thành một y đồng nhất. Nếu cần pretrain CPC/GSMaP rồi fine-tune Vrain, đó là thí nghiệm chuyển miền riêng, chấm cuối cùng trên cùng Vrain và cùng các split, không gọi là có thêm lịch sử trạm.

## 12. Thí nghiệm và chỉ số để trả lời đúng câu hỏi

**Pilot gọn trước:** E0/E2/E7, R0/R1 trên nhãn Vrain và mask chung; LightGBM chạy trước để kiểm tra dữ liệu, sau đó chạy các mạng phù hợp từng nhánh. Báo đúng những ô đã chạy. Pilot chưa có đủ E0–E7 thì không vẽ như đã hoàn tất ma trận.

**Ma trận chính sau pilot:** giữ lựa chọn R cố định, chạy E0–E7; nhánh ngày có đủ LightGBM/TFT/Informer cạnh nhau, nhánh giờ có Bi-LSTM/LightGBM. Nếu mục tiêu đo toàn bộ tương tác với R thì mở rộng cả hai mức R0/R1 thành thí nghiệm riêng; không mặc định nhân đôi ngân sách ngay.

TFT vẫn đáng thử vì thiết kế nhiều hạn và lựa chọn biến; Informer là đối chứng kiến trúc đã chạy được, không thử chỉ để chứng minh không khả thi. Chuỗi bảy ngày chưa kiểm tra lợi thế chuỗi dài của Informer. LightGBM là mô hình tham chiếu mạnh, không có yêu cầu mạng phải thắng. Các bản hiện có đã điều chỉnh loss/đầu ra, nên phép so còn khác biểu diễn, không chỉ đổi kiến trúc. [TFT gốc](https://arxiv.org/abs/1912.09363), [Informer gốc](https://arxiv.org/abs/2012.07436).

Thêm khí hậu theo mùa và persistence đúng nhãn/cửa sổ làm baseline. Persistence lượng mưa không tự tạo xác suất hợp lệ; muốn chấm BS/BSS phải định nghĩa đầu xác suất hoặc đối chứng xác suất riêng. Không gọi ECMWF là baseline đã chạy trên Vrain nếu chưa ghép forecast đúng nguồn/mốc/mẫu.

| Chỉ số | Giải thích dễ hiểu | Chiều tốt |
| --- | --- | --- |
| RMSE | Sai số lượng mưa, phạt mạnh lỗi lớn | Thấp |
| MAE | Trung bình lệch tuyệt đối bao nhiêu mm | Thấp |
| Bias | Dự báo thừa/thiếu trung bình; dự báo trừ quan trắc | Gần 0 |
| BS | Sai số của xác suất sự kiện | Thấp |
| BSS | BS tốt hơn khí hậu tham chiếu bao nhiêu | Cao; dương mới có điểm tốt hơn tham chiếu |
| CSI | Trúng/(trúng+bỏ sót+báo nhầm) | Cao |
| POD | Trúng/(trúng+bỏ sót) | Cao, nhưng đọc cạnh FAR |
| FAR | Báo nhầm/(trúng+báo nhầm) | Thấp |

Giữ CSI/BSS là chỉ số chính theo phương án nghiên cứu; RMSE/MAE/Bias bổ sung cho lượng mm, POD/FAR giải thích quyết định và đánh đổi. POD 0,4 hay 0,6 không có chuẩn tốt chung. Với BSS âm, mô hình có BS kém hơn khí hậu ở cùng phép chấm, dù có thể hơn E0.

Ngưỡng ngày 16/50/100 mm có thể giữ để liên tục với nghiên cứu trước, nhưng là ngưỡng mưa trung bình vùng, chưa tự thành cấp cảnh báo hành chính. Ngưỡng giờ phải định nghĩa theo kỳ 1/3/6h, không dùng nguyên 50 mm/ngày cho 1h. Chỉ chọn ngưỡng quyết định xác suất trên cal. Báo số sự kiện, số mẫu, mùa/năm; lớp quá hiếm không đủ căn cứ kết luận.

Dùng so sánh paired trên cùng issue, bootstrap khối theo thời gian và kiểm tra độ nhạy độ dài khối. Các CI trước đây 7/14 ngày là thiết kế tham khảo, không phải chân lý cho mọi mùa/độ dài chuỗi Vrain. Khóa trước nhóm phép so chính, hiệu chỉnh đa so sánh phù hợp; không dùng chữ đậm thay cho CI. Ba seed của mạng nhằm kiểm tra ngẫu nhiên huấn luyện, không tăng số ngày thời tiết.

## 13. Các cổng bắt đầu/dừng thực tế

| Cổng | Bằng chứng cần có trước bước tiếp | Hiện trạng |
| --- | --- | --- |
| G0 — Truy cập | Đọc inventory, lịch sử thật, xuất mẫu | Đã đạt bước đọc/xuất thử; chưa tải toàn kho |
| G1 — Ngữ nghĩa | Đơn vị, timezone, đầu/cuối kỳ, thiếu, increment/counter rõ | Chưa xác nhận đầy đủ; chưa ghép thành nhãn UTC chính |
| G2 — Trạm và vùng | Panel, tọa độ theo thời kỳ, polygon, bản đồ địa hình/trọng số | V1 ID khớp; ranh và tính đại diện chưa chốt |
| G3 — Lịch sử/QC | Số mẫu theo mùa, chuỗi giao nhau, tỷ lệ thiếu và mẫu bị loại | Mới có mười probe |
| G4 — Độ bền nhãn | Tổng thời gian, rút trạm/panel, đợt mưa lớn, bất định không gian | Chưa thực hiện toàn mạng |
| G5 — Pilot | Loader đúng, baseline, mask/split chung, kiểm tra leak | Chưa huấn luyện Vrain |
| G6 — Ma trận/holdout | Protocol khóa, số sự kiện đủ để diễn giải, review trước mở test | Chưa bắt đầu |

Không có căn cứ gọi “ít nhất 10 trạm”, “90% diện tích” hoặc “5 năm” là chuẩn quốc tế bảo đảm dự báo tốt. Nhóm cần đo coverage, trọng số chi phối, mùa/sự kiện và độ nhạy rồi đăng ký tiêu chí. Với núi không trạm, một số coverage đẹp theo Thiessen vẫn chưa chứng minh chất lượng tốt.

Nếu Vrain đủ giờ nhưng lịch sử ngày quá ngắn, ưu tiên pilot kỹ thuật nhánh 1–6h và pilot ngày có giới hạn; không ép đủ ba mạng sâu. Nhánh giờ cũng phải có đủ mùa và sự kiện độc lập; nhiều hàng giờ không bảo đảm đủ bằng chứng thống kê. Nếu chỉ có dữ liệu ngày, không tạo nhãn giờ giả. Nếu độ phủ toàn vùng chưa đạt, có thể giữ CPC làm nghiên cứu phụ và dùng Vrain kiểm tra đúng phần phủ; không đổi tên kết quả đó thành nhãn trạm toàn tỉnh.

## 14. Bàn giao data cho nhóm theo hợp đồng chung

Các tệp dưới đây là **thiết kế bàn giao**, chưa phải dataset đã dựng. Tên nhãn đề xuất `vrain_areal_estimate_mm`, kèm `valid`, `coverage_weight`, `region_version`, `network_version`, `weights_version`, `source_version`.

| Tệp/lớp | Nội dung tối thiểu |
| --- | --- |
| station_inventory | Namespace/ID/UUID, lon/lat/CRS, valid_from/to, metadata cảm biến/thời gian, cờ chưa xác nhận |
| source_manifest | Hash tệp gốc, chức năng/endpoint dạng mẫu không secret, khoảng yêu cầu, retrieved_at, schema và phạm vi quyền |
| station_intervals | Khoảng bắt đầu/kết thúc UTC, lượng mưa, QC, thiếu/trace, provenance |
| station_hourly | Tổng giờ thật, số khoảng kỳ vọng/nhận được, valid; không lấp bằng 0 |
| station_daily | Tổng 24h đúng anchor đã xác nhận, số giờ đủ, valid |
| region_definition / station_weights | Polygon/hash/CRS/phạm vi đảo, panel và trọng số cố định |
| region_hourly / region_daily | Ước lượng vùng, coverage và toàn bộ version liên quan |
| predictors_hourly / daily | ERA5 B/A/M/C trên cùng vùng, miền bối cảnh được ghi riêng, cờ đầy đủ nguồn |
| sample_index / split / protocol | Issue, history, từng khoảng đích, all-E mask, vai trò split và điều kiện as-of |

Workbook đi kèm có hợp đồng cột, danh mục 44 biến giờ/42 biến ngày, ma trận R0/R1, probe và checklist/phân công. Raw, inventory từng trạm, tọa độ, quan trắc từng giờ, mô hình và dự đoán từng mốc giữ ở thư mục private/Drive theo quyền chia sẻ. Git công khai chỉ nhận mã, cấu hình và thống kê tổng hợp; không đưa tài khoản vào notebook/chat nhóm/tài liệu công khai.

Manifest cũ của `package_data.py verify` không bao phủ bộ Vrain này. Tạo manifest/checksum Vrain riêng, giữ manifest nguồn cũ. Người nhận phải kiểm tra hash, version, khoảng thời gian và schema trước chạy; “tệp có cùng tên” chưa đủ xác nhận cùng data.

## 15. Phân công và thời gian khả thi

| Người phụ trách đề xuất | Bàn giao | Điều kiện bắt đầu |
| --- | --- | --- |
| Thành viên dữ liệu | Quyền xuất, metadata, lịch sử, parser/QC, polygon/panel/trọng số, manifest và báo cáo thiếu | Có quyền truy cập; xác minh G1 với nhà cung cấp khi cần |
| Thành viên Bi-LSTM | Loader vùng, sáu nhãn giờ, persistence/LightGBM, pilot R0/R1 rồi E0–E7 | Bộ giờ đã vượt G1–G4 |
| Người dùng phụ trách TFT | Bộ ngày từ cùng gốc, pilot LightGBM/TFT/Informer, E0–E7, metrics/CI và báo cáo | Bộ ngày/split đã khóa |

Trước khi giao việc, cả ba thống nhất region/timezone/anchor/panel/mask/version. Không để mỗi người tự lấy trung bình trạm và chọn giờ ngày khác nhau rồi so mô hình.

Ước lượng theo công việc, giả định ba người phối hợp, một máy RTX 4060 8 GB, quyền tải được lịch sử và metadata được trả lời sớm: 0,5–1 ngày kiểm kê/xác minh nguồn; 1–2 ngày tải/QC; 1–2 ngày ranh/trọng số/nhãn; 0,5–1 ngày pilot; 2–4 ngày ma trận và báo cáo. Một số phần có thể song song. **Dự kiến 5–10 ngày làm việc để có bộ phát triển có thể báo cáo**, không phải cam kết hoàn tất khoa học trong vài giờ; thời gian chờ nhà cung cấp nằm ngoài ước lượng.

Trong 24–48 giờ đầu, đầu ra ưu tiên là inventory, timeline dữ liệu, bản đồ phủ, tỷ lệ thiếu/mẫu và quyết định có đủ lịch sử cho nhánh ngày hay không. Không lấy việc GPU chạy nhanh làm bằng chứng dữ liệu đã sẵn sàng. Sau pilot mới đo thời gian fit trên số mẫu Vrain thực và chốt ngân sách; số 168 lượt thuộc giao thức CPC ba fold/ba seed trước, không tự áp lên lịch sử Vrain ngắn hơn.

## 16. Vì sao chọn hướng này theo sáu tiêu chí của nhóm?

| Tiêu chí | Lập luận và giới hạn |
| --- | --- |
| C1 — Nhãn được kiểm chứng bằng số đo | Vrain cung cấp cơ hội dùng quan trắc thật ở trạm; nhãn vùng vẫn cần QC, trọng số và độ bền không gian |
| C2 — Đầu vào/độ trễ tại mốc dự báo | Chỉ dùng quá khứ; ERA5 vẫn là hồi cứu, thời gian truyền Vrain còn cần xác minh; chưa tuyên bố vận hành |
| C3 — Cùng mẫu/baseline/CI | Mỗi phép so dùng cùng Vrain, vùng, split và mask; không so điểm khác nguồn nhãn như bằng chứng cải thiện |
| C4 — Mưa hiếm | Giữ CSI/BSS cùng POD/FAR, số sự kiện và lỗi mm; không ưu tiên riêng POD hoặc ngưỡng làm điểm đẹp |
| C5 — Khả thi | Kiểm tra dữ liệu và LightGBM trước, pilot hẹp, chỉ mở ma trận sau cổng; không ép mạng sâu khi số ngày ít |
| C6 — Tái sử dụng | Giữ ERA5, B/A/M/C, kiến trúc và đánh giá; thêm adapter nhãn/version mới, không sửa đè pipeline đóng băng |

Các quyết định D1/D2/D9/D10/D14/D15 có bằng chứng trong phương án hợp nhất vẫn giữ đúng phạm vi lịch sử. Điều kiện “chưa có Vrain” nay đã thay đổi bằng truy cập thực; điều đó chưa tự bác bỏ các phép đo cũ hoặc chứng minh nhãn mới tốt hơn. Khi có phép kiểm chứng cùng cách, cập nhật quyết định mới có dẫn bằng chứng, không viết lại kết quả đã công bố.

ERA5 là tái phân tích, có thể kết hợp quan trắc và thông tin mô hình để mô tả khí quyển đã qua. Dùng nó trong nghiên cứu hồi cứu là hợp lý, nhưng chưa thể gọi điểm số đó là dự báo vận hành tại thời điểm t. Nếu mục tiêu sau này là dự báo thật ngày 2–3, cân nhắc dự báo NWP đã phát hành và được chứng minh có sẵn trước t như một nhánh bổ sung, không lấy ERA5 của ngày đích. Đây là vấn đề thông tin tương lai/độ trễ, không cần quay lại làm app mới phải xử lý. [Copernicus/ECMWF: ERA5](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview).

## 17. Những câu không nên ghi trong báo cáo

- “Đã có 86 trạm đầy đủ từ 2015.” Mới có inventory và mười ngày probe; lịch sử thực có thể ngắn và mạng thay đổi.
- “Có hàng tổng 0 nên năm 2020 không mưa.” Không có hàng giờ thì chưa xác minh được quan trắc.
- “Vrain là mưa thực đo chính xác toàn Đà Nẵng.” Trạm đo tại điểm; mưa vùng là ước lượng theo mạng và phương pháp.
- “Nội suy ERA5 xuống 93 ô làm độ phân giải thật tăng lên.” Lưới biểu diễn không tạo thông tin đo mới.
- “Vrain thay CPC nên điểm sẽ cao hơn.” Đổi nhãn làm thay bài toán chấm; cần cùng nhãn khi so hiệu quả mô hình/đặc trưng.
- “Thêm hết đặc trưng hoặc thêm TFT thì chắc cải thiện đến 72h.” Kết quả CPC trước không hỗ trợ lời hứa này; vẫn phải đo trên Vrain.
- “Ba seed hoặc 82 trạm làm số ngày độc lập tăng tương ứng.” Một mẫu vẫn là một issue vùng.

## 18. Nguồn và trạng thái tài liệu

Nguồn truy cập và kiểm kê: phiên tài khoản được người dùng cấp ngày 09/11/2026; mười response lịch sử và hai inventory, bản XLSX mẫu lưu ngoài Git. Audit chỉ công bố thống kê/count/hash, không công bố số đo từng trạm. Đã có mã kiểm tra cấu trúc; chưa có collector toàn kho, nhãn vùng Vrain, trọng số Thiessen hoặc lần huấn luyện Vrain nào.

Các tài liệu sơ cấp dùng cho lập luận: [Vrain Open API](https://dev.vrain.vn/), [USACE Gage Weights](https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/meteorology/precipitation/gage-weights), [GeoPandas diện tích](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoSeries.area.html), [RainGaugeQC](https://amt.copernicus.org/articles/15/5581/2022/), [Copernicus/ECMWF ERA5](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview), [TFT](https://arxiv.org/abs/1912.09363), [Informer](https://arxiv.org/abs/2012.07436). Các lựa chọn panel, thiếu, pilot và lộ trình là đề xuất của nhóm/dự án, không được trình bày như ngưỡng tiêu chuẩn của các nguồn đó.

Đọc cùng [phương án vùng hợp nhất](../regional_research_plan_2026_10_20/PHUONG_AN_CUOI.md), [thí nghiệm CPC đã hoàn thành](../daily_gauge_2026_11_04/README.md) và [bộ slide ngày](../daily_gauge_slides_2026_11_04/README.md). Các báo cáo này là lịch sử khác nhãn. Bản slide người dùng đã chỉnh sửa được giữ nguyên.
