# Lời dẫn và nguồn cho bộ slide dữ liệu ngày

## Slide 1: Dự đoán mưa vùng trong ba ngày tới

Mục tiêu là nghiên cứu dự đoán trực tiếp lượng mưa trung bình vùng trong ba ngày tới. Ta kiểm tra xem thêm thông tin đối lưu, hoàn lưu hoặc nhiệt độ biển có giúp ích hay không. Đã chạy đủ LightGBM, TFT và Informer cho E0–E7. Có tín hiệu ở ngày 1; ngày 2–3 chưa xác nhận được kỹ năng hơn khí hậu tham chiếu. Các kết quả là phân tích phát triển 2021–2023, chưa mở tập 2025.

## Slide 2: Đầu ra là ba tổng mưa 24 giờ riêng

Tại một thời điểm t, mô hình xuất đồng thời ba tổng mưa: [t, t+24 giờ), [t+24, t+48 giờ) và [t+48, t+72 giờ). Ví dụ 12 / 35 / 8 mm là ba lượng riêng, không phải 12 / 47 / 55 mm tích lũy. Một mẫu đại diện một thời điểm của cả vùng. Mưa trung bình vùng không có nghĩa mọi vị trí trong vùng nhận cùng lượng mưa; thí nghiệm này không xuất bản đồ mưa từng ô.

## Slide 3: Đầu vào X và nhãn y đến từ hai nguồn

X là các đặc trưng khí tượng ERA5 trong quá khứ, còn y là lượng mưa CPC cần dự đoán. ERA5 là tái phân tích, CPC là phân tích lưới từ trạm. Thí nghiệm trước cũng dùng ERA5 làm X; GSMaP khi đó là nhãn mưa, không phải biến mưa vệ tinh trong đầu vào chính. Lần này chưa đưa mưa quá khứ CPC hoặc GSMaP vào X, và tuyệt đối không dùng khí tượng ERA5 của giờ đích.

Nguồn ERA5: https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_HOURLY

Nguồn CPC: https://ftp.cpc.ncep.noaa.gov/precip/CPC_UNI_PRCP/GAUGE_GLB/DOCU/PRCP_CU_GAUGE_V1.0GLB_0.50deg_README.txt

## Slide 4: CPC dựa trên trạm, vẫn là sản phẩm lưới

Một trạm chỉ đo tại vị trí đặt thiết bị. Để tạo nhãn cho cả vùng, CPC phân tích quan trắc của mạng trạm lên lưới 0,5 độ; nhóm tổng hợp các ô thành một lượng mưa vùng. Vì vậy có thể gọi CPC là dữ liệu dựa trên trạm, nhưng không gọi đó là phép đo trực tiếp trung bình toàn Đà Nẵng. Các chuỗi NOAA hiện đã kiểm tra chưa đủ phủ vùng và địa hình. Vrain đang xin quyền truy cập, chưa có trong huấn luyện.

Nguồn: https://ftp.cpc.ncep.noaa.gov/precip/CPC_UNI_PRCP/GAUGE_GLB/DOCU/PRCP_CU_GAUGE_V1.0GLB_0.50deg_README.txt

## Slide 5: 93 ô footprint giao với chín ô CPC

Màu xanh là 93 ô của footprint dữ liệu hiện tại, tổng diện tích toàn ô khoảng 11.074 km². Đây còn là vùng xấp xỉ Đà Nẵng mới, chưa phải ranh hành chính đã cắt chính xác. Các ô lớn là chín ô CPC giao với footprint. Trong 13 ngày probe, ba ô có báo một trạm bên trong; không suy ra có ba trạm nằm trong địa giới vì ô có thể chỉ giao một phần vùng. Ô báo gnum = 0 vẫn có thể nhận thông tin nội suy từ trạm lân cận. Hình không vẽ tọa độ trạm.

Bằng chứng: cpc_spatial_support.csv và source_audit.json của báo cáo dữ liệu ngày.

## Slide 6: Lần này thay đổi những gì?

Cả hai phiên bản vẫn dự đoán trực tiếp mưa vùng và dùng 168 giờ khí tượng quá khứ. Bản cũ chia thành 28 bước sáu giờ; bản mới thành bảy bước ngày. Nhưng đồng thời cũng đổi nguồn nhãn, mốc phát hành và cách đọc đầu ra. Vì vậy không lấy hai điểm số khác nhãn để kết luận bước ngày tốt hơn. Muốn đo riêng tác dụng của độ phân giải, cần giữ cùng CPC, mốc 12 UTC và tập mẫu, rồi mới so bước 6 giờ với 24 giờ.

## Slide 7: Từ dữ liệu giờ thành bảy bước ngày

ERA5 trước hết đã được tổng hợp không gian thành khí tượng vùng theo giờ. Mỗi khối đủ 24 giờ từ 12 UTC đến 12 UTC được lấy trung bình; với gió ta lấy trung bình thành phần u/v. Nhãn CPC vốn đã là tổng ngày nên giữ nguyên đơn vị mm/24h, không chia xuống giờ rồi dựng lại. Mọi E dùng chung mặt nạ hợp lệ E7; không điền thiếu bằng 0. Bảy ngày lịch sử là lựa chọn hiện tại, chưa được chứng minh tối ưu; trung bình ngày có thể làm mất các đỉnh khí tượng ngắn.

## Slide 8: Mô hình nhận gì và xuất ra những gì?

Với TFT và Informer, X có dạng [B, 7, F]: B là số mẫu trong batch, bảy là số ngày quá khứ, F từ 9 đến 42 tùy E. Lịch tương lai có dạng [B, 3, 2], gồm sin/cos ngày trong năm; hai biến này biết trước mà không cần khí tượng tương lai. Đầu ra có ba lượng mm và chín xác suất: ba ngày nhân ba ngưỡng 16/50/100 mm. Các xác suất là sự kiện lồng nhau, không cộng thành 100% và không phải phần trăm diện tích có mưa. Các ngưỡng là ngưỡng nghiên cứu, chưa được xác nhận là cấp cảnh báo hành chính cho mưa trung bình vùng.

## Slide 9: Vì sao dùng mốc 12 UTC, tức 19 giờ VN?

Metadata của chín ô CPC ghi giờ kết thúc ngày là 12 UTC, tức 19 giờ Việt Nam. Nhóm kiểm tra bổ sung trạm NOAA 488550-99999 trong các năm 2015, 2019, 2021, 2022 và 2023: 1.364/1.365 bản ghi mưa 24 giờ không thiếu có timestamp 12 UTC; một bản ghi trace ở 00 UTC. Có 1.151 cặp GSOD cờ G khớp cùng DATE trong sai số 0,3 mm. Đây là bằng chứng ở một trạm, chưa chứng nhận toàn mạng hoặc mọi mã chất lượng. Giả định cũ “GSOD luôn 00–00 UTC” cần được rà soát; các bảng cũ vẫn được lưu nguyên trạng.

Nguồn: station_eod_audit.json và https://www.ncei.noaa.gov/pub/data/noaa/isd-format-document.pdf

## Slide 10: Bốn nhóm thông tin: B, A, M và C

B có bảy biến khí tượng bề mặt và hai biến mã hóa mùa. A biểu diễn khả năng đối lưu, hơi nước, mây, lớp biên và ẩm đất; has_lfc sau tổng hợp là một tỷ phần theo vùng/thời gian. M có sáu biến tại 850 hPa, năm tại 500 hPa, đứt gió, ba thành phần IVT, phân kỳ dòng ẩm, hai biến bối cảnh và hai chênh áp. C hiện chỉ có SST của hộp biển đã chọn, không phải toàn bộ thông tin ENSO hoặc MJO. Danh mục 42 tên cột nằm ở phụ lục và feature_catalog_daily.csv.

## Slide 11: E0–E7: giữ nền, thêm từng tổ hợp nhóm

E0 giữ nhóm B. Ba hàng E1/E2/E3 lần lượt thử thêm riêng A/M/C; E4/E5/E6 thử các cặp; E7 thêm cả ba. Số biến lần lượt là 9, 21, 29, 10, 41, 22, 30 và 42. Mọi cấu hình dùng cùng mẫu, nhãn, thời điểm và tham chiếu để tránh việc điểm khác chỉ do tập ngày khác. Cả ba mô hình chạy đủ tám E. Thêm biến cũng làm thay đổi độ phức tạp mô hình, nên chênh lệch chưa thể quy hoàn toàn cho thông tin vật lý.

## Slide 12: Có nghiên cứu dùng đặc trưng theo ngày

Đặc trưng theo ngày có cơ sở để thử. Bài Pham 2020 dùng năm biến khí tượng ngày từ Global Weather Data for SWAT tại Hòa Bình; chia ngẫu nhiên 70/30 nên không phải mẫu kiểm chứng ngoài thời gian cho hạn 1–3 ngày. Neyestani 2025 dùng mười ngày quá khứ để dự đoán ngày kế tại năm trạm Iran. Amir 2026 thử TFT theo ngày, lịch sử 30 ngày và có hạn một/ba ngày, nhưng dùng Open-Meteo. Các bài hỗ trợ ý tưởng thiết kế; không thay thế phép kiểm chứng ở vùng nghiên cứu và không dùng điểm số của họ để xếp hạng cùng bảng với nhóm.

Pham và cs. (2020): https://doi.org/10.1016/j.atmosres.2020.104845

Neyestani và cs. (2025): https://rmets.onlinelibrary.wiley.com/doi/full/10.1002/met.70143

Amir và cs. (2026): https://juti.if.its.ac.id/index.php/juti/article/view/1518

## Slide 13: Vì sao so cả LightGBM, TFT và Informer?

LightGBM là mô hình dự đoán thông thường, được chọn làm đối chứng mạnh và tương đối gọn để kiểm tra liệu chuỗi mạng sâu có tạo thêm giá trị. Nó dùng ngày cuối, trung bình ba/bảy ngày và chênh lệch hai ngày cuối. TFT và Informer nhận chuỗi bảy ngày; TFT có cơ chế lựa chọn biến, Informer thử encoder–decoder với ProbSparse. Mục tiêu không bắt buộc TFT thắng và không chạy Informer chỉ để chứng minh nó kém. Bản dự án đã điều chỉnh đầu ra và hàm mất mát; chưa phải phép so chỉ đổi kiến trúc. Với chuỗi bảy bước, chưa kiểm tra được lợi thế chuỗi dài vốn là động lực của Informer.

TFT, Lim và cs.: https://arxiv.org/abs/1912.09363

Informer, Zhou và cs.: https://arxiv.org/abs/2012.07436

LightGBM, Ke và cs.: https://proceedings.neurips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html

## Slide 14: Chia theo thời gian, không chia ngẫu nhiên

Trong lượt chấm 2021, mô hình học 2015–2019, hiệu chỉnh bằng 2020 rồi mới chấm 2021. Hai lượt sau cuốn chiếu tương tự. Chuẩn hóa và khí hậu tham chiếu chỉ học từ train; chọn epoch, hiệu chỉnh xác suất và ngưỡng quyết định chỉ dùng cal. Nhãn ba ngày không được vượt ranh fold. Các năm chấm 2021–2023 đang được dùng để nghiên cứu và phân tích, nên không gọi là holdout độc lập. Tập 2025 vẫn giữ kín.

## Slide 15: Ba seed khác ba năm và ba ngày dự đoán

Seed là số khởi tạo bộ sinh ngẫu nhiên. Đổi seed có thể đổi trọng số ban đầu, thứ tự batch, dropout và lấy mẫu attention, khiến mạng học khác dù cùng dữ liệu. Nhóm lấy trung bình dự đoán của ba seed 42/43/44, không chọn seed đẹp nhất. Ba seed không tạo thêm ngày thời tiết. Tám E nhân ba năm nhân ba seed tạo 72 lượt TFT và 72 lượt Informer; LightGBM xác định có 24 pipeline. Tổng là 168 lượt, còn bảng chính có 72 dòng vì gộp dự đoán theo mô hình/E/ngày.

## Slide 16: Đọc đủ tám chỉ số trước khi chọn mô hình

RMSE, MAE và Bias chấm lượng mưa, đơn vị mm/24h; Bias là dự báo trừ nhãn. BS chấm xác suất so với sự kiện có/không; BSS so BS với khí hậu theo tháng học từ train. CSI, POD và FAR chấm quyết định có/không từ xác suất với ngưỡng chọn trên cal, không suy trực tiếp từ lượng mm dự đoán. H là trúng, M là bỏ sót, F là báo nhầm. FAR ở đây là tỷ lệ báo nhầm trong các lần báo có, không phải false positive rate. Không dùng riêng POD để tuyên bố mô hình tốt.

## Slide 17: BSS dương, bằng 0 và âm nghĩa là gì?

Đây là ví dụ minh họa, không phải số của các mô hình. Nếu khí hậu có BS = 0,10 và mô hình có BS = 0,08 thì BSS = 1 − 0,08/0,10 = +0,20: giảm 20% sai số Brier. BS = 0,10 cho BSS = 0; BS = 0,11 cho BSS = −0,10: tăng 10% sai số. BSS không phải tỷ lệ ngày dự đoán đúng. So BSS chỉ có ý nghĩa khi hiểu cùng nhãn, ngưỡng, hạn, mùa và tham chiếu.

## Slide 18: POD phải đọc cùng FAR và CSI

Tại E7 ngày 1 có 116 sự kiện mưa vùng đạt ít nhất 16 mm. LightGBM bắt được 61, bỏ sót 55 và báo nhầm 59. Informer bắt thêm ba sự kiện nhưng có thêm 32 báo nhầm; vì vậy phải đọc POD cạnh FAR và CSI. TFT có 59 lần trúng nhưng 147 báo nhầm. Ngưỡng quyết định được chọn trên cal, không chọn lại theo kết quả chấm. POD 0,4 tự nó không đủ để gọi tốt; muốn đối chiếu paper phải khớp ngưỡng mưa, hạn, vùng, mùa, nguồn nhãn và giao thức.

## Slide 19: Các bảng sau chấm trên cùng mẫu nào?

Mỗi hạn có 1.072 mốc chung, bằng 362 + 348 + 362 của ba năm chấm. Các ngày đích dịch đi nên số sự kiện ở ngày 1/2/3 lần lượt là 116/117/118, không bắt buộc giống nhau. Ở ngưỡng 100 mm chỉ có 13 sự kiện mỗi hạn, nên độ chắc chắn thấp hơn nhiều. Nguồn CPC có 3.287 ngày, nhưng sau tạo cửa sổ và kiểm tra hợp lệ còn 3.239 mẫu phát triển. Các bảng chính dùng toàn năm, ngưỡng 16 mm; chi tiết mùa/năm/50/100 mm nằm trong Excel 11 sheet.

## Slide 20: BSS ngày 1: đủ E0–E7 và ba mô hình

Mỗi hàng giữ cùng cấu hình, hạn, mẫu, nguồn nhãn và khí hậu tham chiếu; ba cột là ba mô hình. Số đậm là điểm tốt hơn trong hàng ở ba chữ số hiển thị, không phải dấu kiểm định; số đỏ là BSS âm. Ngày 1, LightGBM có điểm cao hơn; một số cấu hình có M tăng điểm, nhưng phải đọc thêm khoảng tin cậy của chênh lệch.

## Slide 21: BSS ngày 2: đủ E0–E7 và ba mô hình

Mỗi hàng giữ cùng cấu hình, hạn, mẫu, nguồn nhãn và khí hậu tham chiếu; ba cột là ba mô hình. Số đậm là điểm tốt hơn trong hàng ở ba chữ số hiển thị, không phải dấu kiểm định; số đỏ là BSS âm. Ngày 2, chỉ LightGBM E2 và E6 dương rất nhỏ. Điểm dương nhỏ chưa chứng minh mô hình hơn khí hậu; các khoảng tuyệt đối vẫn chứa 0.

## Slide 22: BSS ngày 3: đủ E0–E7 và ba mô hình

Mỗi hàng giữ cùng cấu hình, hạn, mẫu, nguồn nhãn và khí hậu tham chiếu; ba cột là ba mô hình. Số đậm là điểm tốt hơn trong hàng ở ba chữ số hiển thị, không phải dấu kiểm định; số đỏ là BSS âm. Ngày 3, cả 24 cặp mô hình/cấu hình đều có BSS âm. Đây là kết quả cần báo cáo đầy đủ thay vì chọn riêng những ô đẹp.

## Slide 23: E7 ngày 1: đọc đủ tám metrics

Ba mô hình cùng E7 và cùng hạn. RMSE/MAE/Bias có đơn vị mm/24h; các chỉ số xác suất và sự kiện dùng ngưỡng 16 mm. Số đậm theo chiều tốt của từng cột; Bias lấy độ gần 0, hòa ở ba chữ số cùng được đậm. BSS âm vẫn màu đỏ dù ít âm hơn. Lượng mưa và xác suất là hai đầu ra khác nhau: RMSE thấp hơn không tự bảo đảm BSS dương. Tất cả E còn lại có đủ tám chỉ số trong phụ lục.

## Slide 24: E7 ngày 2: đọc đủ tám metrics

Ba mô hình cùng E7 và cùng hạn. RMSE/MAE/Bias có đơn vị mm/24h; các chỉ số xác suất và sự kiện dùng ngưỡng 16 mm. Số đậm theo chiều tốt của từng cột; Bias lấy độ gần 0, hòa ở ba chữ số cùng được đậm. BSS âm vẫn màu đỏ dù ít âm hơn. Lượng mưa và xác suất là hai đầu ra khác nhau: RMSE thấp hơn không tự bảo đảm BSS dương. Tất cả E còn lại có đủ tám chỉ số trong phụ lục.

## Slide 25: E7 ngày 3: đọc đủ tám metrics

Ba mô hình cùng E7 và cùng hạn. RMSE/MAE/Bias có đơn vị mm/24h; các chỉ số xác suất và sự kiện dùng ngưỡng 16 mm. Số đậm theo chiều tốt của từng cột; Bias lấy độ gần 0, hòa ở ba chữ số cùng được đậm. BSS âm vẫn màu đỏ dù ít âm hơn. Lượng mưa và xác suất là hai đầu ra khác nhau: RMSE thấp hơn không tự bảo đảm BSS dương. Tất cả E còn lại có đủ tám chỉ số trong phụ lục.

## Slide 26: E7: BSS và khoảng tin cậy 95%

Mỗi ô ghi điểm BSS E7 và khoảng tin cậy 95% mô tả, dùng 20.000 lần bootstrap theo khối bảy ngày; có phân tích độ nhạy khối 14 ngày trong CSV/Excel. Ngày 1, khoảng của LightGBM và Informer nằm trên 0, TFT còn chứa 0. Các ngày sau chưa xác nhận kỹ năng dương. Đây là khoảng có điều kiện trên các mô hình đã huấn luyện, chưa bao gồm đầy đủ bất định nhãn hay toàn bộ quá trình học. Không dùng việc hai khoảng riêng giao nhau để thay phép tính khoảng của chênh lệch hai mô hình.

## Slide 27: Thêm riêng A/M/C: điểm tăng đã đủ rõ chưa?

Ở đây giữ cùng mô hình và ngày 1, rồi lấy BSS của E1/E2/E3 trừ E0. Nhóm M tăng điểm ở cả ba mô hình, nhưng khoảng tin cậy 95% của chênh lệch đều chứa 0. Vì vậy nói “có tín hiệu đáng kiểm tra” phù hợp hơn “đã chứng minh M cải thiện”. Các khoảng trên slide là 95% từng phép, chưa hiệu chỉnh cả 63 phép thử thêm nhóm; bảng đầy đủ có khoảng hiệu chỉnh. Không chọn riêng ô tăng đẹp rồi bỏ các ô khác.

## Slide 28: Tốt hơn E0 chưa chắc đã vượt khí hậu

Hai cột cuối trả lời hai câu khác nhau. Chênh lệch E6−E0 cho biết thêm M+C có tốt hơn cấu hình nền không; BSS tuyệt đối cho biết E6 có hơn khí hậu không. Với LightGBM ngày 2, chênh lệch khoảng +0,070 và khoảng hiệu chỉnh 63 phép nằm trên 0 ở cả khối 7/14 ngày. Nhưng BSS E6 chỉ khoảng +0,002; khoảng tuyệt đối 95% vẫn chứa 0. Nghĩa là đã bớt kém so với E0, chưa xác nhận dự báo hữu ích hơn khí hậu. Khoảng chênh lệch và khoảng tuyệt đối trên slide có mức hiệu chỉnh khác nhau, không gọi là cùng một loại khoảng.

## Slide 29: Có thể kết luận đến đâu từ thí nghiệm này?

Phạm vi kết luận là nhãn CPC, footprint hiện có và các pipeline đã huấn luyện. Ở E7 ngày 1, LightGBM có điểm BSS cao hơn hai mạng và khoảng chênh lệch 95% mô tả nằm trên 0. Việc thêm riêng M ngày 1 chưa rõ qua khoảng tin cậy. Ngày 2–3 chưa xác nhận kỹ năng so khí hậu. Đây là đánh giá hồi cứu với ERA5; chưa xác minh khí tượng có sẵn ngay tại mốc phát dự báo. Không kết luận kiến trúc LightGBM luôn tốt hơn TFT/Informer, dữ liệu ngày tốt hơn sáu giờ, hoặc đã dự báo chính xác mưa thực toàn địa giới.

## Slide 30: Việc tiếp theo phục vụ mục tiêu nghiên cứu

Không cần chạy thêm chỉ để lấp ma trận E vì đã đủ. Ưu tiên tiếp theo là kiểm tra dữ liệu Vrain khi được cấp: lịch sử, vị trí, chất lượng, độ phủ địa hình và giờ tích lũy. Cần chốt ranh/trọng số vùng, tránh thay đổi tập trạm từng ngày làm nhãn biến động giả. Nếu muốn so bước 6 giờ với ngày, phải giữ cùng CPC, mốc và mẫu. Sau đó khóa thiết kế trước khi mở 2025. Nếu thêm dự báo khí tượng NWP thì phải dùng phiên bản thật sự có sẵn trước mốc dự báo, không lấy ERA5 tương lai làm đầu vào.

## Slide 31: Ngày 1: bảng đầy đủ E0 / E1 / E2

Bảng tra đầy đủ có ba mô hình cạnh nhau cho mỗi E; tổng chín trang chứa 72 dòng bằng tám E nhân ba mô hình nhân ba hạn. Tám chỉ số lấy từ KET_QUA_72.csv đã kiểm chứng, toàn năm và ngưỡng 16 mm/24h. Đậm chỉ điểm tốt hơn trong cùng E/hạn, Bias gần 0; BSS âm màu đỏ. Không suy ý nghĩa thống kê chỉ từ chữ đậm. Chi tiết theo mùa, năm, ngưỡng và độ ổn định seed nằm trong Excel 11 sheet.

## Slide 32: Ngày 1: bảng đầy đủ E3 / E4 / E5

Bảng tra đầy đủ có ba mô hình cạnh nhau cho mỗi E; tổng chín trang chứa 72 dòng bằng tám E nhân ba mô hình nhân ba hạn. Tám chỉ số lấy từ KET_QUA_72.csv đã kiểm chứng, toàn năm và ngưỡng 16 mm/24h. Đậm chỉ điểm tốt hơn trong cùng E/hạn, Bias gần 0; BSS âm màu đỏ. Không suy ý nghĩa thống kê chỉ từ chữ đậm. Chi tiết theo mùa, năm, ngưỡng và độ ổn định seed nằm trong Excel 11 sheet.

## Slide 33: Ngày 1: bảng đầy đủ E6 / E7

Bảng tra đầy đủ có ba mô hình cạnh nhau cho mỗi E; tổng chín trang chứa 72 dòng bằng tám E nhân ba mô hình nhân ba hạn. Tám chỉ số lấy từ KET_QUA_72.csv đã kiểm chứng, toàn năm và ngưỡng 16 mm/24h. Đậm chỉ điểm tốt hơn trong cùng E/hạn, Bias gần 0; BSS âm màu đỏ. Không suy ý nghĩa thống kê chỉ từ chữ đậm. Chi tiết theo mùa, năm, ngưỡng và độ ổn định seed nằm trong Excel 11 sheet.

## Slide 34: Ngày 2: bảng đầy đủ E0 / E1 / E2

Bảng tra đầy đủ có ba mô hình cạnh nhau cho mỗi E; tổng chín trang chứa 72 dòng bằng tám E nhân ba mô hình nhân ba hạn. Tám chỉ số lấy từ KET_QUA_72.csv đã kiểm chứng, toàn năm và ngưỡng 16 mm/24h. Đậm chỉ điểm tốt hơn trong cùng E/hạn, Bias gần 0; BSS âm màu đỏ. Không suy ý nghĩa thống kê chỉ từ chữ đậm. Chi tiết theo mùa, năm, ngưỡng và độ ổn định seed nằm trong Excel 11 sheet.

## Slide 35: Ngày 2: bảng đầy đủ E3 / E4 / E5

Bảng tra đầy đủ có ba mô hình cạnh nhau cho mỗi E; tổng chín trang chứa 72 dòng bằng tám E nhân ba mô hình nhân ba hạn. Tám chỉ số lấy từ KET_QUA_72.csv đã kiểm chứng, toàn năm và ngưỡng 16 mm/24h. Đậm chỉ điểm tốt hơn trong cùng E/hạn, Bias gần 0; BSS âm màu đỏ. Không suy ý nghĩa thống kê chỉ từ chữ đậm. Chi tiết theo mùa, năm, ngưỡng và độ ổn định seed nằm trong Excel 11 sheet.

## Slide 36: Ngày 2: bảng đầy đủ E6 / E7

Bảng tra đầy đủ có ba mô hình cạnh nhau cho mỗi E; tổng chín trang chứa 72 dòng bằng tám E nhân ba mô hình nhân ba hạn. Tám chỉ số lấy từ KET_QUA_72.csv đã kiểm chứng, toàn năm và ngưỡng 16 mm/24h. Đậm chỉ điểm tốt hơn trong cùng E/hạn, Bias gần 0; BSS âm màu đỏ. Không suy ý nghĩa thống kê chỉ từ chữ đậm. Chi tiết theo mùa, năm, ngưỡng và độ ổn định seed nằm trong Excel 11 sheet.

## Slide 37: Ngày 3: bảng đầy đủ E0 / E1 / E2

Bảng tra đầy đủ có ba mô hình cạnh nhau cho mỗi E; tổng chín trang chứa 72 dòng bằng tám E nhân ba mô hình nhân ba hạn. Tám chỉ số lấy từ KET_QUA_72.csv đã kiểm chứng, toàn năm và ngưỡng 16 mm/24h. Đậm chỉ điểm tốt hơn trong cùng E/hạn, Bias gần 0; BSS âm màu đỏ. Không suy ý nghĩa thống kê chỉ từ chữ đậm. Chi tiết theo mùa, năm, ngưỡng và độ ổn định seed nằm trong Excel 11 sheet.

## Slide 38: Ngày 3: bảng đầy đủ E3 / E4 / E5

Bảng tra đầy đủ có ba mô hình cạnh nhau cho mỗi E; tổng chín trang chứa 72 dòng bằng tám E nhân ba mô hình nhân ba hạn. Tám chỉ số lấy từ KET_QUA_72.csv đã kiểm chứng, toàn năm và ngưỡng 16 mm/24h. Đậm chỉ điểm tốt hơn trong cùng E/hạn, Bias gần 0; BSS âm màu đỏ. Không suy ý nghĩa thống kê chỉ từ chữ đậm. Chi tiết theo mùa, năm, ngưỡng và độ ổn định seed nằm trong Excel 11 sheet.

## Slide 39: Ngày 3: bảng đầy đủ E6 / E7

Bảng tra đầy đủ có ba mô hình cạnh nhau cho mỗi E; tổng chín trang chứa 72 dòng bằng tám E nhân ba mô hình nhân ba hạn. Tám chỉ số lấy từ KET_QUA_72.csv đã kiểm chứng, toàn năm và ngưỡng 16 mm/24h. Đậm chỉ điểm tốt hơn trong cùng E/hạn, Bias gần 0; BSS âm màu đỏ. Không suy ý nghĩa thống kê chỉ từ chữ đậm. Chi tiết theo mùa, năm, ngưỡng và độ ổn định seed nằm trong Excel 11 sheet.

## Slide 40: Nguồn nhãn và bằng chứng kiểm tra dữ liệu

README CPC nêu lưới 0,5 độ, mật độ trạm thay đổi và giờ kết thúc ngày có thể khác theo quốc gia. Nhóm đối chiếu 13 ngày giữa nguồn PSL và nhị phân NOAA, đồng thời kiểm tra riêng EOD tại một trạm từ ISD gốc. Những kiểm tra này xác nhận được một phần xuất xứ và thời gian, chưa chứng nhận mưa vùng là quan trắc hoàn hảo. Nguồn và kết quả máy đọc nằm trong source_audit.json, station_eod_audit.json và tài liệu Word.

https://ftp.cpc.ncep.noaa.gov/precip/CPC_UNI_PRCP/GAUGE_GLB/DOCU/PRCP_CU_GAUGE_V1.0GLB_0.50deg_README.txt

https://www.ncei.noaa.gov/pub/data/noaa/isd-format-document.pdf

ERA5: https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_HOURLY

## Slide 41: Tài liệu mô hình và nghiên cứu theo ngày

Các bài gốc cung cấp cơ sở thuật toán và kiến trúc; code của dự án có điều chỉnh, không phải tái lập nguyên xi benchmark của paper. TFT hiện không dùng đầy đủ static context hoặc đầu ra phân vị như thiết kế gốc. Informer dùng chuỗi bảy ngày và đầu ra ngày đã sửa. Các bài mưa ngày hỗ trợ việc thử đầu vào ngày, không chứng minh sẵn hiệu quả tại Đà Nẵng.

TFT, Lim và cs.: https://arxiv.org/abs/1912.09363

Informer, Zhou và cs.: https://arxiv.org/abs/2012.07436

LightGBM, Ke và cs.: https://proceedings.neurips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html

Pham và cs. (2020): https://doi.org/10.1016/j.atmosres.2020.104845

Neyestani và cs. (2025): https://rmets.onlinelibrary.wiley.com/doi/full/10.1002/met.70143

Amir và cs. (2026): https://juti.if.its.ac.id/index.php/juti/article/view/1518

## Slide 42: Danh mục biến: B và A

Đây là tên các cột nguồn trước khi thêm tiền tố mean__. Nhóm B có bảy biến bề mặt và hai mã hóa mùa; nhóm A có 12 biến. Khí tượng vật lý được tổng hợp theo diện tích từng giờ rồi lấy trung bình 24 giờ. sin_doy và cos_doy tính từ thời gian đã biết; không phải biến khí tượng tương lai. has_lfc sau tổng hợp là tỷ phần, không còn nhất thiết là một giá trị nhị phân cho cả vùng. Danh mục gốc: feature_catalog_daily.csv.

## Slide 43: Danh mục biến: M và C

Nhóm M có 20 biến: sáu ở 850 hPa, năm ở 500 hPa, một đứt gió, ba IVT, một phân kỳ dòng ẩm, hai bối cảnh và hai chênh áp. Nhóm C hiện chỉ có sst_region_c. Không gọi C là bộ chỉ số khí hậu đầy đủ và không suy từ kết quả SST sang toàn bộ ENSO/MJO. Đây là danh mục đặc trưng hiện có; tính phù hợp cho vùng phải được đánh giá bằng thiết kế thời gian và thí nghiệm thêm/bớt biến.

## Slide 44: Kiểm chứng đã thực hiện đến mức nào?

Đã phát lại độc lập 144 checkpoint mạng, 288 đầu ra LightGBM và 336 split hiệu chỉnh/đánh giá; chuẩn hóa, hiệu chỉnh, ensemble và điểm số tái tạo đạt. Ba mẫu gồm 504 giờ predictor được kiểm tra lại từ nguồn; năm kiểm tra code mới đều đạt. Bộ slide chỉ đọc aggregate đã kiểm chứng, không huấn luyện mới và không mở giá trị nhãn 2025. Vrain chưa có. Kiểm tra code đúng không tự chứng minh nhãn đúng hay dự báo vận hành tốt. Bố cục được kiểm tra qua HTML dùng cùng scene; chưa render bằng Office gốc.
