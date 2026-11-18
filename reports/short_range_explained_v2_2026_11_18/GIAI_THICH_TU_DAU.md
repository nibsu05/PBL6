# Dự báo mưa ngắn hạn — giải thích từ đầu

Đọc các slide chính theo thứ tự. Con số màu đậm là điểm cần giải thích, không phải chứng nhận đạt. Ví dụ giả định được ghi riêng; các kết quả thật giữ đúng năm, nguồn và protocol.

## 01. Dự báo mưa tại trạm: mô hình học gì, kết quả tốt đến đâu?

Bản này dành cho người chưa biết dự án. Đi từ một mẫu dữ liệu đến cách mô hình học, rồi mới đọc kết quả. Mỗi kết quả được gắn với câu hỏi cụ thể và một đối chứng. Luồng chính dài khoảng 28 phút; phụ lục giữ các bảng chi tiết, paper và cấu hình để trả lời giảng viên. Không có lần huấn luyện mới trong bản trình bày này. Mục tiêu là giải thích đúng bằng chứng đã có, không làm điểm số đẹp hơn.

**Ý cần nhớ:** Đọc theo ba câu hỏi: dự báo gì → học như thế nào → có hơn cách đơn giản không?

## 02. Đầu ra: lượng mưa ngày 1, ngày 2 và ngày 3

Giả sử phát dự báo lúc 19 giờ ngày 18/11. Ngày 1 là lượng mưa từ 19 giờ hôm đó đến 19 giờ hôm sau. Ngày 2 là cửa sổ 24 giờ kế tiếp, và ngày 3 cũng vậy. Có ba con số riêng cho từng trạm, không phải một tổng tích lũy 72 giờ. Lịch trên hình là ví dụ giải thích cửa sổ thời gian, không phải một bản dự báo đã được phát. Đơn vị của mỗi đầu ra là mm trong 24 giờ tại điểm đặt trạm.

**Ý cần nhớ:** Một trạm nhận ba số mm; dự án hiện không dự báo mưa trung bình toàn Đà Nẵng.

## 03. Một mẫu học là một trạm tại một lần phát dự báo

Ví dụ trên slide chỉ minh họa, không phải số đo hoặc dự báo thật. Ở thời điểm phát, ta đã có mưa quá khứ tại trạm và một bản GFS dự báo 12 mm cho ngày mai. Sau khi ngày mai kết thúc, Vrain ghi nhận 20 mm. Khi huấn luyện từ các ngày lịch sử, 20 mm là đáp án để tính lỗi. Khi dự báo một ngày chưa xảy ra, đáp án này chưa có và tuyệt đối không được đưa vào đầu vào. Mẫu của trạm khác giữ lịch sử và đáp án riêng.

**Ý cần nhớ:** MINH HỌA: đầu vào đã biết trước giờ phát; đáp án là số đo xuất hiện sau đó.

## 04. Nguồn nào làm đầu vào, nguồn nào làm đáp án?

| Nguồn | Thông tin gì? | Vai trò ở nhánh ngắn hạn |
| --- | --- | --- |
| Vrain | Mưa đo tại từng trạm | Lịch sử và nhãn mưa tương lai |
| GFS | Mưa, nhiệt, ẩm, gió dự báo | Đầu vào cho ba ngày sắp tới |
| DEM | Địa hình quanh tọa độ | Đặc trưng vị trí, không phải nhãn |
| ERA5 | Khí tượng tái phân tích | Bộ giờ riêng; không lấy tương lai |

Vrain cung cấp mưa đo tại trạm, dùng cho lịch sử và nhãn cần dự đoán. GFS cung cấp bản dự báo khí tượng đã khởi tạo trước thời điểm phát, giúp mô hình có thông tin về thời tiết sắp tới. ERA5 là tái phân tích và vẫn có vai trò ở bộ dữ liệu giờ riêng, nhưng không được dùng trường ERA5 của ngày tương lai làm đầu vào cho thí nghiệm dự báo GFS–Vrain này. GFS được nội suy từ bốn nút lưới 0,25 độ về tọa độ trạm; nội suy không biến nó thành số đo tại điểm.

**Ý cần nhớ:** Nhãn là mưa Vrain; GFS là thông tin dự báo đầu vào, không thay thế số đo.

Nguồn: [NOAA/NCEI · GFS](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast); [ECMWF/Copernicus · reanalysis](https://climate.copernicus.eu/climate-reanalysis)

## 05. Mô hình chung vẫn dự báo riêng cho từng trạm

Chung có nghĩa là dùng chung bộ quy tắc hoặc trọng số đã học. Mỗi mẫu vẫn mang mã trạm, tọa độ, địa hình, lịch sử mưa và GFS tại vị trí của chính trạm đó, nên đầu ra có thể khác nhau giữa các trạm. Cách này có thể chia sẻ kinh nghiệm giữa trạm nhiều và ít lịch sử. Tuy nhiên, dự án chưa so công bằng với 57 mô hình riêng nên không khẳng định mô hình chung tốt hơn. Dữ liệu các trạm trong cùng đợt mưa cũng có tương quan, không tạo ra 57 năm lịch sử độc lập.

**Ý cần nhớ:** Đây là lựa chọn thiết kế; chưa có thí nghiệm chứng minh hơn 57 mô hình riêng.

## 06. Vì sao chọn phát lúc 19 giờ?

| Mốc | Ý nghĩa |
| --- | --- |
| 07h Việt Nam | GFS khởi tạo 00 UTC được sử dụng |
| 18h | Kết thúc dữ liệu mưa gần nhất được phép dùng |
| 19h | Giờ phát cố định; bắt đầu cửa sổ nhãn |
| Chưa chứng minh | Độ trễ nguồn thực tế và ưu thế so với giờ khác |

19 giờ là mốc cố định của thí nghiệm để thống nhất cửa sổ mưa 19–19 và phép so các mô hình. Nó không phải giờ tối ưu đã được khảo sát người dùng hoặc chứng minh bằng paper cho dự án. GFS 00 UTC tương ứng 07 giờ Việt Nam, cách giờ phát 12 tiếng. Thí nghiệm giả định nguồn GFS trễ 8 tiếng và trạm trễ 1 tiếng, nên chỉ dùng tổng gần nhất kết thúc lúc 18 giờ. Khả dụng thực tế từng ngày vẫn cần ghi nhận trước giờ phát. Có thể đổi giờ hoặc cycle, nhưng phải định nghĩa và kiểm tra lại protocol.

**Ý cần nhớ:** 19 giờ là quy ước nghiên cứu hiện tại; chưa có bằng chứng đây là giờ tốt nhất.

Nguồn: [NOAA/NCEI · GFS](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast)

## 07. Dữ liệu dùng được không có nghĩa là mọi trạm đều đủ

Danh mục có 86 vị trí nhưng chỉ 57 trạm vào thí nghiệm cố định theo điều kiện lịch sử huấn luyện. Một trạm thiếu giờ không làm mất mẫu hợp lệ của trạm khác. Nhãn ngày chỉ được tính khi đủ 24 số giờ sau kiểm tra; không điền thiếu thành 0 và không lấy mưa vệ tinh để lấp đáp án. Nguồn mưa đã thu tới ngày 15/11/2026 và issue đủ ba nhãn tới 12/11. Hai kênh Vrain được báo riêng vì chưa chứng minh liên tục. Kiểm tra cấu trúc và ghép dữ liệu không chứng nhận độ chính xác vật lý của cảm biến.

**Ý cần nhớ:** Đã kiểm tra cách ghép và tính nhãn; chất lượng cảm biến và nguồn vẫn có giới hạn.

## 08. Đâu là mô hình nhóm học, đâu là mốc để so sánh?

| Tên | Bản chất | Tự huấn luyện? | Mục đích |
| --- | --- | --- | --- |
| LightGBM | Học từ bảng đặc trưng | Có | Mô hình chính để thử biến |
| GRU | Mạng đọc chuỗi quá khứ | Có | Mô hình học chuỗi để so |
| GFS | Vật lý khí tượng (NOAA) | Không | Dự báo nền trước hậu xử lý |
| MOS | Hồi quy hiệu chỉnh GFS | Có | Mốc hậu xử lý đơn giản |
| Luôn 0 mm | Quy tắc cố định | Không | Kiểm tra việc chỉ đoán khô |

LightGBM và GRU là hai họ mô hình học máy nhóm đã huấn luyện. GFS cũng là mô hình, nhưng là hệ thống dự báo khí tượng bằng mô phỏng vật lý của NOAA; nhóm lấy bản dự báo đã có, không huấn luyện lại GFS. MOS là hậu xử lý thống kê, ở dự án được fit bằng hồi quy đơn giản từ mưa GFS và mùa trong năm để dự đoán mưa trạm. Quy tắc luôn 0 mm không cần học. Cả năm cách có thể cho lượng mưa để chấm trên cùng ngày và trạm. Mốc đơn giản là vai trò trong thí nghiệm, không phải tên một mô hình. Nếu mô hình phức tạp chưa hơn cách đơn giản, chưa có lý do nói độ phức tạp tạo thêm giá trị.

**Ý cần nhớ:** Đều có thể tạo dự báo để chấm; khác nhau ở cách tạo và mức độ học của nhóm.

Nguồn: [NOAA/NCEI · GFS](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast); [NOAA/MDL · MOS](https://vlab.noaa.gov/web/mdl/mos); [PyTorch · GRU](https://docs.pytorch.org/docs/2.15/generated/torch.nn.GRU.html)

## 09. “Huấn luyện” là sửa cách dự đoán từ các ngày đã biết

Huấn luyện không phải chỉ nạp file rồi tạo ra một con số chính xác. Với nhiều ngày lịch sử, mô hình dùng đầu vào được phép biết trước giờ phát để dự đoán lượng mưa. Ta so dự đoán với mưa trạm đã xảy ra, tính lỗi theo quy tắc đã chọn, rồi cập nhật mô hình. Quy trình lặp nhiều lần trên tập học. Các ví dụ đánh giá phải ở thời gian riêng để kiểm tra khả năng dùng quy tắc đã học cho dữ liệu khác. Dữ liệu tương lai không được tham gia cập nhật trọng số.

**Ý cần nhớ:** Mô hình học quan hệ từ đầu vào đến số đo trạm, không học bằng năm đánh giá.

## 10. LightGBM học từ bảng đặc trưng như thế nào?

Với mỗi hạn dự báo, LightGBM nhận một bảng: mỗi hàng là một trạm tại một thời điểm, các cột là đặc trưng. Mưa của bảy ngày trước cũng là bảy cột trong bảng, nên LightGBM có lịch sử mưa chứ không phải chỉ GRU mới có. Các cây được thêm dần để giảm hàm mất mát trên tập học. Đầu lượng mưa là dự đoán trực tiếp mưa trạm, trong đó GFS là một cột đầu vào. Vì vậy, gọi đây là hậu xử lý GFS về mặt bài toán là đúng, nhưng không nên nói thuật toán luôn bắt đầu từ GFS rồi cộng một residual đã định trước. Dự án có mô hình riêng theo hạn và loại đầu ra, cùng chia sẻ dữ liệu nhiều trạm.

**Ý cần nhớ:** GFS là một đầu vào; mô hình học lượng mưa tại trạm từ toàn bộ bảng.

Nguồn: [Zhang & Ye · 2021 · JHM](https://journals.ametsoc.org/view/journals/hydr/22/11/JHM-D-21-0096.1.xml)

## 11. GRU là mạng học diễn biến của chuỗi mưa

GRU viết tắt của Gated Recurrent Unit, một dạng mạng nơ-ron đọc dữ liệu theo thứ tự và học giữ hoặc bỏ thông tin quá khứ. Có thể hình dung đọc bảy ngày mưa từ cũ đến mới thay vì chỉ nhìn một dòng rời rạc. Ở dự án, mỗi ngày có một lượng mưa trạm; phần ghi nhớ sau đó được ghép với GFS ba hạn và thông tin trạm. Nhỏ chỉ cấu hình ít tham số để hạn chế chi phí và nguy cơ học thuộc, không phải tên mô hình khác. N3 có 4.364 tham số, hidden 16; 17 epoch là 17 lượt học, không phải 17 ngày. GRU mới chạy protocol cũ; chưa chạy cửa sổ bốn năm A–D. Thắng điểm số chưa tự chứng minh cơ chế ghi nhớ là nguyên nhân duy nhất.

**Ý cần nhớ:** GRU đọc chuỗi theo thứ tự; “nhỏ” chỉ kích thước cấu hình, không phải một mô hình thứ ba.

Nguồn: [Salehi & Salehi Neyshabouri · 2025](https://doi.org/10.1016/j.envsoft.2025.106635); [PyTorch · GRU](https://docs.pytorch.org/docs/2.15/generated/torch.nn.GRU.html)

## 12. Mỗi nhóm năm làm một việc khác nhau

| Giai đoạn | Vai trò trong vòng A–D mới |
| --- | --- |
| 2021–2022 / 2021–2024 | Học trọng số: cửa sổ ngắn / dài |
| Các quý 2022 | Chọn cấu hình chỉ bằng quá khứ của tập học |
| 2025 | Hiệu chỉnh xác suất và ngưỡng cảnh báo |
| 2026 đã xem | Đánh giá hồi cứu; không chọn lại mô hình theo điểm |

Bảng này nói về protocol mới A–D. Hai cửa sổ học là 2021–2022 và 2021–2024 để kiểm tra tác động số năm. Các quý năm 2022 dùng kiểm tra có thứ tự thời gian bên trong phần học, giúp chọn tham số. Năm 2025 được phép hiệu chỉnh xác suất và ngưỡng cảnh báo, không fit cây dự báo lượng mưa. Năm 2026 được đánh giá hồi cứu và đã được xem, nên không gọi là test kín cho các chỉnh sửa tiếp theo. Nghiên cứu cũ có cách chia năm riêng và giữ nguyên kết quả.

**Ý cần nhớ:** Không trộn vai trò các năm giữa protocol cũ và mới; 2026 hiện là hồi cứu.

## 13. Chọn tham số bằng cách giả lập dự báo trong quá khứ

Thay vì xáo trộn các ngày, mỗi lượt kiểm tra giữ lại một quý năm 2022 và chỉ học từ thời gian sớm hơn quý đó. Có khoảng cách bảy ngày và loại các nhãn 72 giờ băng ranh để giảm chồng lấn. Ba cấu hình cây, hai loss, bốn quý và ba hạn tạo thành 72 lượt CV. Điểm dùng để lựa chọn là RMSE trung bình theo trạm, sau chặn dự đoán âm về 0. Số cây và cấu hình cuối được dùng chung giữa bốn phương án để so sánh không bị lệch ngân sách.

**Ý cần nhớ:** CV là kiểm tra trong tập học, không phải xem năm 2026 để tìm cấu hình đẹp.

## 14. Ba con số về huấn luyện nên hiểu thế nào?

Cấu hình được chọn có tối đa bảy lá mỗi cây, tức mỗi cây chỉ tạo ra một số ít vùng điều kiện. Ngày 1 dùng 171 cây, ngày 2 dùng 109 và ngày 3 dùng 76. Đây là số cây cộng dần, không phải số tầng mạng hoặc số ngày đầu vào. Ba seed 17, 29, 43 thay đổi một số bước lấy mẫu ngẫu nhiên; các dự đoán cuối được tổng hợp theo protocol. Dao động giữa seed giúp thấy nhạy với lần chạy nhưng không phải khoảng tin cậy thống kê theo thời tiết.

**Ý cần nhớ:** 7 lá = độ phức tạp mỗi cây; 171 cây = số bước thêm cây; 3 seed = ba lần chạy.

## 15. L2: sai càng nhiều, điểm phạt càng tăng nhanh

| Thực tế (minh họa) | Dự đoán | Sai số | Điểm phạt L2 |
| --- | --- | --- | --- |
| 50 mm | 40 mm | −10 mm | **100** |
| 50 mm | 20 mm | −30 mm | **900** |
| 0 mm | 30 mm | +30 mm | **900** |

L2 ở đây là hàm mất mát bình phương sai số dự đoán, không phải thuật ngữ regularization L2 dù tên giống nhau. Lấy dự đoán trừ lượng mưa thực tế rồi bình phương. Trong ví dụ giả định, thực tế 50 mm: dự đoán 40 mm sai 10 mm và nhận phạt 100; dự đoán 20 mm sai 30 mm và nhận phạt 900. Vì vậy lỗi lớn ảnh hưởng mạnh đến việc học. L2 gắn với mục tiêu dự báo trung bình và giảm RMSE, nhưng chỉ tối ưu trên tập học không bảo đảm tốt nhất trên năm khác hoặc ở từng trạm.

**Ý cần nhớ:** L2 là cách chấm lỗi để học; phạt mạnh dự đoán lệch nhiều, không chỉ ngày mưa lớn.

Nguồn: [LightGBM · objective](https://lightgbm.readthedocs.io/en/stable/Parameters.html); [Gneiting · 2011 · JASA](https://arxiv.org/abs/0912.0902)

## 16. Tweedie: một cách học phù hợp để thử với mưa

Tweedie là một họ phân phối dùng để xây dựng hàm mất mát. Với tham số p bằng 1,5 đang dùng, họ này có thể mô tả giá trị bằng 0 cùng với các giá trị dương liên tục và lệch phải. Điều đó phù hợp về mặt giả thuyết với mưa: nhiều ngày khô, nhiều ngày mưa ít, ít ngày rất lớn. LightGBM dùng log-link cho dự báo trung bình dương; không có nghĩa nhóm đổi nhãn thành log1p hay chia lại lượng mưa. p không phải xác suất mưa và 1,5 không phải ngưỡng mm. Chưa có kiểm định phân phối khẳng định dữ liệu Vrain đúng Tweedie; vẫn phải kiểm tra bằng kết quả ngoài tập học.

**Ý cần nhớ:** Có lý do để thử Tweedie; tên loss không chứng minh mô hình dự báo tốt hơn.

Nguồn: [LightGBM · objective](https://lightgbm.readthedocs.io/en/stable/Parameters.html); [scikit-learn · Tweedie](https://scikit-learn.org/stable/modules/linear_model.html#tweedie-regression)

## 17. Vì sao báo cáo cả Tweedie lẫn L2?

Bốn phương án tách hai câu hỏi: thêm hai năm dữ liệu có ích không, và đổi cách tính lỗi có ích không. A và B cùng Tweedie, khác cửa sổ học; C và D cùng L2, cũng khác cửa sổ. So A với C hoặc B với D giữ số năm để xét loss. Cả bốn giữ 57 trạm, 26 biến, số cây và seed. Chỉ thay loss đầu dự báo trung bình; đầu median và xác suất được dùng chung theo cửa sổ. Do đó không dùng B so D để khẳng định thay đổi POD hay FAR. Tweedie được chọn cho bước tiếp từ CV trong phần học, không chọn bằng điểm 2026.

**Ý cần nhớ:** Đổi loss chỉ là một thay đổi trong cách học; không phải bốn kiến trúc khác nhau.

Nguồn: [LightGBM · objective](https://lightgbm.readthedocs.io/en/stable/Parameters.html)

## 18. Một số mm và một xác suất trả lời hai câu hỏi

Đầu lượng mưa trả lời dự báo bao nhiêu mm trong từng ngày. Đầu xác suất trả lời khả năng lượng mưa vượt một ngưỡng định trước, ví dụ 50 mm trong 24 giờ tại trạm. Dự báo 30% không có nghĩa sẽ mưa 30 mm và cũng không phải độ chính xác của mô hình. Đầu median tối ưu cho sai lệch tuyệt đối; đầu mean tối ưu cho bình phương sai số. Minh họa năm kết quả có thể xảy ra 0, 0, 0, 0, 50 mm cho trung bình 10 mm nhưng trung vị 0 mm. Hai số khác nhau vì trả lời hai đại lượng khác nhau.

**Ý cần nhớ:** Không dùng % xác suất thay mm; không lấy MAE median để gọi đó là RMSE mean.

Nguồn: [Gneiting · 2011 · JASA](https://arxiv.org/abs/0912.0902)

## 19. Hiệu chỉnh xác suất không phải sửa số đo mưa

Mô hình có thể nói xác suất 70% nhưng tần suất quan sát ở những trường hợp tương tự không gần 70%. Hiệu chỉnh dùng tập riêng năm 2025 để điều chỉnh đầu ra xác suất. Sau đó chọn ngưỡng báo có theo CSI bằng xác suất dự đoán ngoài fold thời gian, rồi khóa trước đánh giá. Ở ngày 1, cutoff đã chọn là 0,35: xác suất từ 35% trở lên được chuyển thành một lần báo có mưa từ 50 mm. Đây là hai ngưỡng khác nhau, một ngưỡng xác suất và một ngưỡng lượng mưa. Quy trình không chỉnh các nhãn Vrain.

**Ý cần nhớ:** 50 mm xác định sự kiện; 35% là ngưỡng quyết định báo có ở ngày 1.

## 20. Minh họa: sai số được tính từ đâu?

| Ví dụ giả định | Thực tế | Dự đoán | Dự đoán − thực tế |
| --- | --- | --- | --- |
| Ngày A | 0 mm | 2 mm | +2 mm |
| Ngày B | 10 mm | 7 mm | −3 mm |
| Ngày C | 30 mm | 20 mm | −10 mm |

Đây là ba ví dụ giả định để tính tay, không phải ba ngày trong bộ dữ liệu thật. Lấy dự đoán trừ thực tế được +2, −3, −10 mm. MAE là trung bình độ lớn các sai số: 15 chia 3 bằng 5 mm. RMSE là căn của trung bình bình phương: căn của 113 chia 3, bằng khoảng 6,14 mm. Bias là trung bình sai số có dấu, bằng −3,67 mm, nghĩa là có xu hướng dự báo thiếu. RMSE lớn hơn MAE vì lần sai 10 mm được nhấn mạnh hơn. Chưa thể đánh giá tốt hay xấu nếu chưa biết đối chứng trên cùng các ngày này.

**Ý cần nhớ:** MINH HỌA: MAE = 5 mm; RMSE ≈ 6,14 mm; Bias ≈ −3,67 mm.

## 21. Kết quả thật: “RMSE 15,68 mm” nghĩa là gì?

Hồi cứu 2026 modern • 57 trạm • 14.488 mẫu trạm–issue • chưa đủ cả năm

Ba số trên slide đều thuộc cùng đầu mean của B và ngày 1 trong hồi cứu 2026 modern. RMSE 15,68 mm là chỉ số nhấn mạnh sai lệch lớn, không phải dự báo rằng ngày mai mưa 15,68 mm, cũng không phải sai lệch tuyệt đối trung bình. Nếu muốn diễn đạt trung bình lệch bao nhiêu mm, xem MAE 6,15 mm. Bias -0,98 mm cho thấy xu hướng dự báo thiếu trên toàn bộ tập, nhưng mức thiếu ở riêng ngày mưa lớn có thể nặng hơn. Các chỉ số này tính từng trạm rồi trung bình đều 57 trạm, gọi là macro; không phải tính lỗi của lượng mưa trung bình toàn vùng.

**Ý cần nhớ:** RMSE là chỉ số lỗi; MAE dễ đọc hơn về số mm lệch trung bình. Cần xem cả hai.

## 22. “Tốt” trước hết phải tốt hơn cách dự báo nào?

| Đối chứng | Câu hỏi kiểm tra |
| --- | --- |
| 0 mm mọi ngày | Mô hình có chỉ học đoán khô để giảm lỗi? |
| Khí hậu theo mùa | Có hơn quy luật mưa thường gặp? |
| GFS nguyên bản | Học máy tạo thêm giá trị gì so dự báo nền? |
| MOS: hồi quy từ GFS | Có hơn một cách hậu xử lý ít phức tạp? |

Dữ liệu mưa thường có nhiều ngày khô nên luôn nói 0 mm có thể đạt MAE nhỏ mà bỏ sót toàn bộ mưa lớn. Vì thế cần ZERO. Khí hậu theo mùa dùng thống kê mưa các năm học. GFS là mô hình dự báo vật lý có sẵn của NOAA: trước hết kiểm tra học máy có hơn dùng trực tiếp bản đó không. MOS viết tắt Model Output Statistics, nghĩa là hậu xử lý thống kê đầu ra mô hình. MOS đơn giản của dự án chỉ nhận ba biến mưa GFS, sin và cos ngày trong năm; đầu mean dùng hồi quy Ridge, các đầu median và xác suất có mô hình riêng. Đây là mô hình nhóm có fit, không phải sản phẩm MOS chính thức của NOAA. MOS kiểm tra mức cải thiện có cần đến LightGBM hoặc GRU không. Mọi cách đều chấm cùng trạm, ngày, nhãn và metric.

**Ý cần nhớ:** Đối chứng là mốc so thực nghiệm; không có ngưỡng RMSE chung áp dụng mọi nơi.

Nguồn: [NOAA/NCEI · GFS](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast); [NOAA/MDL · MOS](https://vlab.noaa.gov/web/mdl/mos)

## 23. Cùng ngày và trạm: B giảm lỗi so với GFS

Hồi cứu 2026 modern • 57 trạm • 14.488 mẫu trạm–issue • chưa đủ cả năm • RMSE mm, thấp hơn tốt hơn

| Hạn | GFS | MOS dài | LightGBM B | Giảm so GFS |
| --- | --- | --- | --- | --- |
| Ngày 1 | 20,45 | 18,93 | **15,68** | **23,3%** |
| Ngày 2 | 19,74 | 17,90 | **17,47** | **11,5%** |
| Ngày 3 | 24,95 | 22,36 | **20,27** | **18,8%** |

Bảng dùng đầu mean và cùng mẫu trong hồi cứu 2026 modern. Ngày 1 RMSE GFS khoảng 20,45 mm, MOS dài 18,93 mm và B 15,68 mm. Tỷ lệ giảm là lấy chênh lệch RMSE chia RMSE GFS, khoảng 23,3%. Đây là mức giảm một chỉ số lỗi, không phải độ chính xác 76,7% hoặc 23,3% số ngày đúng thêm. Cả ba hạn có điểm B thấp hơn GFS và MOS dài. Tuy nhiên, phép so B với các đối chứng ở protocol mới chưa có suy luận khoảng tin cậy được xác nhận riêng; bảng hiện là so sánh điểm trên giai đoạn đã xem.

**Ý cần nhớ:** Đã có giá trị ở mức điểm số; chưa đủ để chứng nhận cải thiện ổn định hoặc vận hành.

## 24. Thêm hai năm học: điểm tốt hơn đã đủ chắc chưa?

Hồi cứu 2026 modern • 57 trạm • 14.488 mẫu trạm–issue • chưa đủ cả năm

A và B cùng Tweedie và đầu vào N3, chỉ khác cửa sổ học. Ngày 2, A học 2021–2022 đạt RMSE 18,03 mm, B học 2021–2024 đạt 17,47 mm. Mức giảm 0,56 mm, khoảng 3,1%. Cả ba hạn B đều giảm điểm so A nhưng chưa đạt đủ tiêu chí suy luận đã định trước. Điều đó không chứng minh thêm dữ liệu vô ích; nó nói rằng thí nghiệm chưa có bằng chứng đủ mạnh để tách mức cải thiện khỏi biến động của thời tiết và mẫu. Không chọn lại mô hình theo năm 2026 sau khi thấy các điểm này.

**Ý cần nhớ:** Điểm tốt hơn là tín hiệu; muốn khẳng định cải thiện phải kiểm tra độ chắc chắn.

## 25. Mưa ≥50 mm: ngày 1 bắt đúng và bỏ sót bao nhiêu?

Hồi cứu 2026 modern • 57 trạm • 14.488 mẫu trạm–issue • chưa đủ cả năm • B • ngày 1 • cutoff 35%

Từ bảng đếm thật, có 600 trường hợp ngày–trạm mưa ít nhất 50 mm trong 24 giờ. Mô hình báo đúng 275 và bỏ sót 325, nên POD gộp là 45,8%. Trong 398 trường hợp đã phát báo có, 123 là báo nhầm, nên FAR gộp là 30,9%. Một đợt mưa có thể xuất hiện ở nhiều trạm và nhiều cửa sổ; không gọi đây là 600 cơn bão độc lập. Các tỷ lệ này tính từ tổng đếm, gọi là micro; có thể khác bảng macro tính tỷ lệ từng trạm rồi trung bình. Chưa có ngưỡng POD 0,4 chung để nói đạt.

**Ý cần nhớ:** POD gộp = 45,8%; FAR gộp = 30,9%. Có tín hiệu nhưng vẫn bỏ sót nhiều.

## 26. BSS dương: xác suất có hơn khí hậu tham chiếu không?

Hồi cứu 2026 modern • 57 trạm • 14.488 mẫu trạm–issue • chưa đủ cả năm

Brier score chấm khoảng cách giữa xác suất dự báo và sự kiện thực tế 0 hoặc 1. BSS so lỗi xác suất đó với khí hậu tham chiếu: BSS bằng 0 nghĩa là ngang tham chiếu, âm là kém hơn, 1 là hoàn hảo. Với một phép tính BSS, 0,36 tương ứng giảm khoảng 36% lỗi Brier so tham chiếu, không phải 36% dự báo đúng. Điểm thực trên slide là trung bình BSS từng trạm so CLIM_LONG được fit 2021–2024, nên không được lấy tỷ số của hai macro BS để tính ngược. BSS dương chưa bảo đảm ngưỡng báo có đang đáp ứng nhu cầu sử dụng.

**Ý cần nhớ:** BSS > 0 là hơn khí hậu theo lỗi xác suất; không phải chứng nhận cảnh báo đủ tốt.

Nguồn: [ECMWF · Brier score](https://confluence.ecmwf.int/pages/viewpage.action?pageId=240849421)

## 27. Ngày 3: hơn nửa số lần báo có là báo nhầm

Hồi cứu 2026 modern • 57 trạm • 14.488 mẫu trạm–issue • chưa đủ cả năm • B • ngày 3 • cutoff 20%

Ở ngày 3, B có 355 lần bắt đúng, 248 lần bỏ sót và 494 lần báo nhầm mưa từ 50 mm. Có 849 lần báo có, trong đó 494 sai, tức FAR gộp 58,2%. Cutoff ngày 3 là 20%, khác ngày 1 là 35%, nên thay đổi POD và FAR không chỉ do hạn dự báo mà còn do ngưỡng quyết định. Nếu hạ ngưỡng, thường bắt thêm sự kiện nhưng có thể tăng báo nhầm. Không được chỉ chọn POD cao để nói mô hình tốt. Chấp nhận tỷ lệ báo nhầm này hay không cần xét mục đích và chi phí hành động.

**Ý cần nhớ:** FAR gộp ngày 3 = 58,2%; chưa đủ cơ sở gọi mô hình sẵn sàng cảnh báo.

## 28. Có ba mốc để kết luận “đủ tốt”, không chỉ một số

| Mốc so sánh | Hiện có bằng chứng gì? | Đánh giá hiện tại |
| --- | --- | --- |
| 1. Hơn đối chứng | RMSE B < GFS/MOS dài; BSS50 > 0 | **Đạt ở mức điểm số** |
| 2. Cải thiện ổn định | Cần kiểm tra nhiều giai đoạn và độ chắc chắn | **Chưa đủ** |
| 3. Đủ dùng thực tế | Cần yêu cầu bỏ sót/báo nhầm và độ trễ thật | **Chưa chứng minh** |

Mức thứ nhất là có hơn các đối chứng hợp lý trên cùng mẫu hay không. Hiện B tốt hơn GFS và MOS dài về điểm RMSE ở ba hạn trong giai đoạn đã xem; BSS 50 cũng dương. Mức thứ hai là cải thiện có ổn định qua năm, mùa, trạm và mưa lớn hay không, với khoảng tin cậy phù hợp các đợt thời tiết phụ thuộc. Phần này chưa được hoàn tất cho B so các đối chứng ở protocol mới. Mức thứ ba là đủ cho một quyết định thực tế: cần biết chấp nhận bỏ sót, báo nhầm và độ trễ thế nào. Chưa có ngưỡng người sử dụng và kiểm chứng tương lai đủ dài nên chưa được tuyên bố đạt mức ba.

**Ý cần nhớ:** Hiện có kết quả nghiên cứu đáng theo dõi; chưa có bằng chứng để chứng nhận vận hành.

Nguồn: [ECMWF · quyết định](https://www.ecmwf.int/en/newsletter/165/news/understanding-how-forecast-users-make-decisions)

## 29. Đổi sang L2: bớt thiếu mưa lớn nhưng thừa ngày khô

Hồi cứu 2026 modern • 57 trạm • 14.488 mẫu trạm–issue • chưa đủ cả năm

Hình là số liệu thật của đầu mean ngày 1 trong hồi cứu modern, so B và D cùng cửa sổ bốn năm. Bias ở các trường hợp thực tế từ 50 mm trở lên chuyển từ khoảng −46,41 lên −34,43 mm: vẫn thiếu nhưng bớt thiếu. Ở các trường hợp thực tế dưới 1 mm, bias tăng từ khoảng +1,88 lên +2,63 mm: báo thừa nhiều hơn. RMSE chung ngày 1 của D cũng cao hơn B. Đây là phân tích có điều kiện theo nhãn quan sát sau sự kiện, không phải quy tắc chọn mô hình trước khi biết trời mưa. Không có khoảng tin cậy cho từng bias có điều kiện trong hình.

**Ý cần nhớ:** Không có loss tốt nhất mọi mặt; cần giữ mục tiêu chính và kiểm tra đánh đổi.

## 30. GRU có hữu ích không? Chỉ so khi cùng protocol

Kiểm định 2025 legacy • protocol cũ • 57 trạm • thấp hơn tốt hơn

| Mô hình | RMSE ngày 1 (mm) |
| --- | --- |
| GFS | 26,35 |
| LightGBM N3 | 26,04 |
| GRU N3 | 24,67 |

Ba số trong bảng đều thuộc kiểm định 2025 của protocol cũ, cùng trạm, mẫu, đầu mean và hạn ngày 1. GRU N3 có RMSE thấp hơn LightGBM N3 và GFS về điểm số, cho thấy đây là một ứng viên đáng kiểm tra. Tuy nhiên, không lấy 24,67 mm của GRU năm 2025 so 15,68 mm của B năm 2026 để kết luận B hơn GRU: thời tiết, nguồn và cách chia năm đã khác. Bảng cũng không tự chứng minh chênh lệch có ý nghĩa thống kê. Nếu cần xếp hạng theo protocol mới, phải huấn luyện GRU với cùng cửa sổ và ngân sách rồi kiểm tra cùng mẫu.

**Ý cần nhớ:** Chưa có so sánh GRU bốn năm với LightGBM B. Không xếp hạng bằng hai năm khác nhau.

## 31. Bổ sung đặc trưng: đã có cải thiện nào đáng tin?

2025 · protocol cũ · bootstrap ghép khối và hiệu chỉnh nhiều so sánh

| Phép so RMSE đã định trước | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | --- | --- | --- |
| Khí tượng thô: N1−N0 | Chưa đủ | **Đạt tiêu chí** | **Đạt tiêu chí** |
| Địa hình: N3−N1 | Chưa đủ | Chưa đủ | Chưa đủ |
| Dẫn xuất: N5−LINEAR6 | Chưa đủ | Chưa đủ | Chưa đủ |

Các phép so về nhóm biến được đặt trước và có hiệu chỉnh nhiều so sánh. Khí tượng thô N1−N0 đạt tiêu chí ở ngày 2–3 trên 2025. Địa hình N3−N1 chưa đủ cả ba hạn. Với dẫn xuất GRU, phải so N5 với đối chứng LINEAR6 có cùng số tham số và nguyên liệu; sau kiểm soát này chưa đủ bằng chứng cả ba hạn. Đây là kết luận trong thiết kế/ngân sách đã chạy, không phủ nhận vai trò vật lý của địa hình hoặc độ ẩm.

**Ý cần nhớ:** Bằng chứng rõ nhất hiện có là khí tượng thô; đặc trưng bổ sung chưa tự động tốt hơn.

## 32. Cần làm gì để tiến từ kết quả nghiên cứu đến tin cậy?

Giữ mô hình đã chọn bằng phần học, không tiếp tục lựa chọn bằng năm 2026 đã xem rồi gọi lại là test kín. Thu và lưu đầu vào, dự báo trước giờ phát để kiểm tra có thực sự dùng được GFS và mưa trạm đúng hạn. Tích lũy nhiều đợt mưa chưa xảy ra rồi đánh giá cả lượng và xác suất, theo mùa và từng trạm. Nếu muốn nói mô hình chung tốt hơn mô hình riêng hoặc giờ 19 tốt hơn giờ khác, cần thí nghiệm riêng có kiểm soát. Nếu muốn dùng cảnh báo, phải thống nhất chi phí bỏ sót và báo nhầm với người dùng trước khi chọn điểm vận hành.

**Ý cần nhớ:** Bước quan trọng kế tiếp là kiểm chứng đúng điều kiện sử dụng, không thêm mô hình cho đủ tên.

## 33. Có thể báo cáo điều gì một cách trung thực?

Nhóm đã chuyển sang nhãn mưa đo tại trạm, ghép bản dự báo khí tượng trước kỳ đích, xây dựng kiểm tra dữ liệu và thí nghiệm có đối chứng. Học máy tạo thêm giá trị ở mức điểm RMSE trên giai đoạn hồi cứu mới, và một số lợi ích của khí tượng thô có bằng chứng trong kiểm định cũ. Những phần chưa chắc cũng là kết quả nghiên cứu: thêm biến không tự động tốt hơn, thêm năm chưa đủ bằng chứng, đổi loss tạo đánh đổi. Vẫn phải cải thiện bỏ sót mưa lớn, báo nhầm, kiểm chứng nguồn và kiểm định tương lai. Không tuyên bố vượt các paper khác chỉ từ RMSE hay POD khác điều kiện.

**Ý cần nhớ:** Có đóng góp nghiên cứu và tín hiệu cải thiện; chưa phải hệ thống cảnh báo đã được chứng nhận.

## 34. Phụ lục: cách dùng trong phần phản biện

Phụ lục giữ các bảng và mô tả kỹ thuật từ bản tổng hợp trước. Chỉ mở khi người nghe cần kiểm tra một biến, một cấu hình hoặc một số cụ thể. Các bảng luôn giữ nhãn thời kỳ và protocol riêng; không dùng để so trực tiếp các năm khác nhau. Các slide cuối bổ sung bảng A–D, bảng metric và nguồn chính thức cho loss, BSS và tiêu chí sử dụng.

**Ý cần nhớ:** Phụ lục là tài liệu đầy đủ để tra cứu; không phải phần phải trình bày liên tục.

## 35. Các thuật ngữ cần hiểu trước khi đọc báo cáo

| Từ trong báo cáo | Nghĩa dùng ở dự án |
| --- | --- |
| Issue | Thời điểm phát dự báo: 19h Việt Nam |
| Init | GFS khởi tạo 00 UTC = 07h Việt Nam |
| Horizon 1/2/3 | Ba cửa sổ 24h liên tiếp sau issue |
| Loss | Hàm phạt dùng khi cập nhật mô hình |
| Calibration / cutoff | Hiệu chỉnh xác suất / ngưỡng xác suất báo có |
| Ablation | So thêm/bớt nhóm biến, giữ các điều kiện khác |

Issue là thời điểm phát, init là thời điểm khởi tạo GFS. Horizon 1/2/3 trong file là ba cửa sổ ngày, còn lead phải nói rõ tính từ init hay issue. Loss điều khiển việc học; calibration điều chỉnh xác suất/ngưỡng trên phần riêng. Ablation giữ các điều kiện khác để kiểm tra nhóm thông tin.

**Ý cần nhớ:** Không dùng lẫn lead tính từ init và lead tính từ issue.

## 36. GFS được đổi về đúng cửa sổ nhãn như thế nào?

| Nhãn | Mưa: lead sau init | Khí tượng: lead sau init | Sau issue |
| --- | --- | --- | --- |
| Ngày 1 | P36 − P12 | Trạng thái +24h | 0–24h |
| Ngày 2 | P60 − P36 | Trạng thái +48h | 24–48h |
| Ngày 3 | P84 − P60 | Trạng thái +72h | 48–72h |

Issue 12 UTCnằm sau init 00 UTC 12 giờ. Các mốc mưa tích lũy 12/36/60/84 hđược lấy hiệu thành ba tổng 24 hđúng nhãn. Các mốc khí tượng 24/48/72 hsau init nằm giữa ba cửa sổ đó. Có kiểm tra GRIB về init, thời gian hiệu lực, đơn vị và kỳ tích lũy; sai lệch âm do mã hóa chỉ được chặn trong dung sai đã định.

**Ý cần nhớ:** Các mốc +24/+48/+72h khí tượng là tính từ init, không tính từ issue.

Nguồn: [NOAA/NCEI · GFS](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast)

## 37. N0: 16 biến nền, không phải “chỉ ERA5”

| Nhóm tên biến | Số biến | Nội dung / đơn vị |
| --- | --- | --- |
| gfs_rain_mm | 1 | Mưa GFS đúng cửa sổ đích, mm/24h |
| sin_doy, cos_doy | 2 | Mã hóa chu kỳ ngày trong năm |
| latitude, longitude, station_code | 3 | Tọa độ hiện có và ID phân loại |
| rain_lag_day1_mm … day7_mm | 7 | Bảy tổng ngày Vrain quá khứ, mm/24h |
| rain_recent1h/6h/24h_mm | 3 | Tổng gần nhất kết thúc trước cutoff |

16 biến N0 gồm 1 mưa GFS,2 lịch,3 vị trí/ID,7 ngày mưa và 3 tổng mưa gần nhất. Mưa quá khứ lấy ở chính trạm, không phải mưa vùng. Các tổng gần nhất kết thúc trước issue 1 giờ; các ngày lag đã hoàn tất trước ngày issue. Station_code là biến phân loại, không phải trường khí tượng.

**Ý cần nhớ:** Tên và đơn vị chính xác của từng cột nằm trong feature_catalog.csv.

## 38. N1: thêm 5 biến khí tượng dự báo thô

| Tên cột | Đơn vị | Ý nghĩa |
| --- | --- | --- |
| gfs_t850_c | °C | Nhiệt độ dự báo ở 850 hPa |
| gfs_rh850_pct | % | Độ ẩm tương đối dự báo ở 850 hPa |
| gfs_u850 | m/s | Gió thành phần hướng Đông |
| gfs_v850 | m/s | Gió thành phần hướng Bắc |
| gfs_pwat | kg/m² | Hơi nước toàn cột dự báo |

Năm biến khí tượng của N1 đều là dự báo GFS đã khởi tạo trước issue. T/RH/u/v 850 hPamô tả quy mô khí quyển, PWAT là hơi nước cột. Các trạm gần nhau có thể chia sẻ trường vì lưới thô. Nội suy tại tọa độ không biến chúng thành số đo chính xác của từng cảm biến.

**Ý cần nhớ:** N1−N0 là phép kiểm tra thông tin khí tượng ngoài mưa GFS và mưa trạm quá khứ.

## 39. N3: thêm 5 biến địa hình DEM

| Tên cột | Đơn vị | Ý nghĩa |
| --- | --- | --- |
| dem_elev_m | m | Cao độ DEM tại tọa độ |
| dem_mean_5km_m | m | Trung bình cao độ vùng lân cận 5km |
| dem_std_5km_m | m | Mức biến thiên cao độ vùng 5km |
| dem_slope_east | m/m | Độ dốc theo hướng Đông |
| dem_slope_north | m/m | Độ dốc theo hướng Bắc |

Các biến DEM là proxy địa hình quanh tọa độ hiện hành. Không có ý nghĩa đã đo cao độ cảm biến ngoài thực địa. Chưa thấy cải thiện rõ của N3 không phủ nhận địa hình ảnh hưởng mưa; ID/vị trí đã chứa thông tin địa phương, dữ liệu và ngân sách cũng có giới hạn.

**Ý cần nhớ:** Có cơ sở địa lý để thử, nhưng giá trị dự báo phải được đo bằng N3−N1.

## 40. N0–N5 và các biến dẫn xuất khác nhau thế nào?

| Cấu hình | Số biến | Công thức nhóm |
| --- | --- | --- |
| N0 | 16 | Nền GFS + lịch/vị trí + mưa Vrain |
| N1 | 21 | N0 + 5 khí tượng thô |
| N2 | 25 | N1 + 4 dẫn xuất ẩm/gió |
| N3 | 26 | N1 + 5 địa hình |
| N4 | 30 | N3 + 4 dẫn xuất ẩm/gió |
| N5 | 32 | N4 + 2 tương tác gió–sườn |

N2/N4 thêm bốn dẫn xuất ẩm–gió, N5 thêm hai tương tác với sườn. Q nhân gió tại 850 hPakhông phải IVT tích phân cả cột. Các dẫn xuất dùng cùng nguyên liệu nên cần đối chứng biểu diễn và dung lượng. Các nhóm N không được đồng nhất với E 0–E 7 của hướng nhãn vùng/ERA5 trước đây.

**Ý cần nhớ:** Các nhóm N thuộc nghiên cứu GFS–Vrain; không đồng nhất với E0–E7 của hướng dữ liệu cũ.

## 41. Kiến trúc GRU thực tế trong thí nghiệm đã chạy

Encoder GRU nhận 7 ngày mưa sau log1p và chuẩn hóa train. Hidden 16, embedding ID 4 kênh, MLP head 24, dropout 0,1. N3 có 4.364 tham số; N5 có 4.796. AdamW lr 0,001, weight decay 0,001, batch 256, clip gradient 1; số epoch cuối 17 được chọn bằng CV train. Không fit scaler hoặc chọn epoch bằng 2025/2026.

**Ý cần nhớ:** GRU học chuỗi mưa; context khí tượng tương lai được ghép theo từng hạn, không đưa nhãn tương lai vào encoder.

## 42. Số cây: phân biệt phiên bản cũ và vòng A–D

| Đầu dự báo · bản cũ | Số lá | Cây D1 | Cây D2 | Cây D3 |
| --- | --- | --- | --- | --- |
| Mean · Tweedie | 7 | 109 | 109 | 93 |
| Median · quantile 0,5 | 31 | 68 | 40 | 72 |
| P(y≥1) | 7 | 150 | 169 | 147 |
| P(y≥50 | y≥1) | 7 | 162 | 106 | 85 |

Bảng số cây cũ giải thích các đầu phụ đang tái dùng. Mean A–D mới có ngân sách chung 171/109/76 cây,7 lá; không gọi A là checkpoint N3 cũ nguyên vẹn. Median/wet/conditional giữ cấu hình chọn từ CV cũ; năm 2025 chỉ fit Platt/cutoff trong protocol mới. Không dừng sớm bằng 2026.

**Ý cần nhớ:** Đầu mean A–D mới: 7 lá, 171 / 109 / 76 cây. Các đầu phụ giữ cấu hình chọn từ CV cũ.

## 43. Hiệu chỉnh xác suất và chọn cutoff diễn ra ở đâu?

Giữ riêng từng quý calibration để tạo xác suất OOF và chọn cutoff, có gap 7 ngày. Sau đó fit Platt trên toàn năm calibration để áp dụng vào phần đánh giá. Một cutoff chung cho hai ngưỡng mưa giữ quyết định lồng nhau. OOF calibration không phải dự báo đã thực phát trước mỗi quý. Protocol cũ dùng 2023, A–D dùng 2025.

**Ý cần nhớ:** Hiệu chỉnh và chọn ngưỡng là những bước học từ dữ liệu; phải được tách khỏi tập đánh giá.

## 44. Macro và micro: vì sao phải báo cả hai?

| Minh họa, không phải dữ liệu thật | Số mẫu | RMSE |
| --- | --- | --- |
| Trạm A | 100 | 1 mm |
| Trạm B | 10 | 9 mm |
| Macro: mỗi trạm như nhau | — | **5,000 mm** |
| Micro: gộp mọi mẫu | 110 | **2,876 mm** |

Ví dụ chỉ minh họa cách chấm. Macro RMSE tính RMSE từng trạm rồi lấy trung bình, nên A/Bcó trọng số ngang nhau. Micro gộp 110 mẫu, trạm 100 mẫu có ảnh hưởng lớn hơn. Với POD/FAR, một số tỷ lệ có thể không xác định ở trạm không có sự kiện hoặc không báo có; báo thêm số trạm chấm được.

**Ý cần nhớ:** Dự án ưu tiên macro để trạm có nhiều giờ hợp lệ không lấn át phần còn lại.

## 45. 2025: bảng đầy đủ RMSE đầu mean

2025 legacy · protocol cũ · mm/24h · cùng mẫu

| Mô hình | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | --- | --- | --- |
| GFS | 26,345 | 27,899 | 33,765 |
| MOS | 26,131 | 28,683 | 32,346 |
| LGB N0 | 27,142 | 29,985 | 31,447 |
| LGB N1 | 26,092 | 29,157 | 30,614 |
| LGB N2 | 26,098 | 29,078 | 30,473 |
| LGB N3 | 26,035 | 29,203 | 30,645 |
| LGB N4 | 26,155 | 29,094 | 30,436 |
| LGB N5 | 26,079 | 29,130 | 30,475 |
| GRU N3 | **24,667** | 27,184 | 30,620 |
| GRU N5 | 24,812 | **26,711** | **30,233** |

Bảng đầy đủ RMSE mean của 2025 giữ cùng cohort, mẫu và split cũ. In đậm là nhỏ nhất trong bảng chứ không chứng minh ý nghĩa thống kê. N5/N3 khác thông tin đầu vào; so kiến trúc thuần cần kiểm soát nhóm biến. Các mốc ZERO/CLIM/PERSIST và đối chứng dung lượng có trong CSV nguồn.

**Ý cần nhớ:** Không so MAE median của một mô hình với RMSE mean của mô hình khác để chọn bên thắng.

## 46. 2025: bảng đầy đủ MAE đầu median

2025 legacy · protocol cũ · mm/24h · cùng mẫu

| Mô hình | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | --- | --- | --- |
| GFS | 9,768 | 10,383 | 11,743 |
| MOS | 9,019 | 9,404 | 10,026 |
| LGB N0 | 8,328 | 9,442 | 9,695 |
| LGB N1 | 8,148 | 9,254 | 9,549 |
| LGB N2 | 8,074 | 9,173 | 9,532 |
| LGB N3 | 8,142 | 9,246 | 9,501 |
| LGB N4 | 8,091 | 9,173 | 9,482 |
| LGB N5 | 8,117 | 9,195 | 9,540 |
| GRU N3 | 7,975 | 8,808 | 9,454 |
| GRU N5 | **7,969** | **8,724** | **9,399** |

Bảng MAE dùng đầu median đã học bằng quantile 0,5. So các hàng cùng tập 2025; không so MAE median ở đây với RMSE mean để chọn mô hình thắng. Mưa nhiều ngày khô làm median có thể rất thấp, nên vẫn phải đọc mưa lớn và cảnh báo.

**Ý cần nhớ:** Không so MAE median của một mô hình với RMSE mean của mô hình khác để chọn bên thắng.

## 47. 2025: xác suất mưa lớn so với khí hậu

2025 legacy · BSS50 · tham chiếu fit 2021–22

| Mô hình | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | --- | --- | --- |
| GFS gốc | 0,086 | 0,040 | -0,166 |
| MOS đơn giản | 0,275 | 0,235 | 0,092 |
| LightGBM · N3 | 0,345 | 0,248 | 0,197 |
| GRU · N3 | 0,346 | 0,257 | 0,177 |
| GRU · N5 | 0,349 | 0,267 | 0,186 |

BSS 50 cũ dùng khí hậu fit 2021–2022 và hiệu chỉnh 2023. Giá trị dương nói hơn khí hậu trên cùng mẫu. Tham chiếu khác vòng mới 2021–2024, vì vậy không so hai BSS như chỉ thay mô hình. Chất lượng xác suất và quyết định cảnh báo là hai mặt cần báo song song.

**Ý cần nhớ:** Đọc BSS cùng reliability, POD/FAR/CSI và số sự kiện, không chỉ xem dấu dương.

## 48. 2026 legacy: báo riêng vì ít mưa lớn

2026 legacy · 1.725 mẫu/trạm–issue · 56 trạm · chỉ 2 sự kiện ≥50/hạn

| Cấu hình · đầu mean | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | --- | --- | --- |
| A · 2 năm/Tweedie | 4,101 | 4,462 | 4,659 |
| B · 4 năm/Tweedie | **3,888** | **4,290** | **4,520** |
| C · 2 năm/L2 | 4,135 | 4,497 | 4,755 |
| D · 4 năm/L2 | 4,058 | 4,529 | 4,639 |
| GFS gốc | 4,319 | 4,743 | 4,533 |
| MOS · 4 năm | 5,819 | 6,178 | 6,416 |

Legacy 2026 có 1.725 mẫu,56 trạm,62 issue; mỗi hạn chỉ 2 sự kiện trạm–ngày từ 50 mm. RMSE nhỏ không chứng minh API tốt hơn modern, vì thời kỳ/mùa/độ phủ khác. Không dựa vào nhóm này một mình để kết luận cảnh báo mưa lớn ổn định.

**Ý cần nhớ:** Không dùng nhóm có hai sự kiện để kết luận ổn định chất lượng cảnh báo mưa lớn.

## 49. 2026 modern: lặp kiểm tra N0/N1/N3

2026 modern · RMSE mean · train 2021–24 · cùng mẫu

| Mô hình | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | --- | --- | --- |
| N0 · 16 biến | 16,055 | 17,888 | 20,833 |
| N1 · 21 biến | 15,710 | **17,450** | 20,288 |
| N3 · 26 biến | **15,683** | 17,469 | **20,270** |
| GFS | 20,445 | 19,738 | 24,953 |
| MOS · 4 năm | 18,933 | 17,899 | 22,361 |

Ablation mới dùng train dài và Tweedie chọn bằng CV 2022. N3 là bí danh củaB, không fit lại để tạo thêm kết quả. Điểm khí tượng thô cải thiện nhưng chưa đủ tiêu chí ở 2026; địa hình đổi rất ít. Kết luận này không xóa bằng chứng 2025 của protocol cũ vì đây là năm và cách học khác.

**Ý cần nhớ:** Nhiều năm hơn làm thay đổi bối cảnh học; không giả định hiệu quả biến giữ nguyên qua mọi năm.

## 50. 2026 modern: MAE median của các đầu phụ

2026 modern · MAE median · mm/24h

| Cấu hình | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | --- | --- | --- |
| A/C · 2 năm | **5,901** | 6,575 | 7,158 |
| B/D · 4 năm | 5,946 | 6,540 | **6,832** |
| N0 · 4 năm | 6,205 | 6,699 | 7,105 |
| N1 · 4 năm | 5,959 | **6,523** | 6,840 |
| GFS | 7,590 | 7,718 | 8,832 |
| MOS · 4 năm | 6,407 | 6,838 | 7,440 |

A/Cchung median, B/Dchung median; không phải thiếu chạyC/D. Việc đổi loss chỉ áp dụng cho mean trong phép so có kiểm soát. N0/N1 là ablation cửa sổ dài trên cùng mẫu. Đơn vị ở bảng là mm/24 hvà nhỏ hơn tốt hơn.

**Ý cần nhớ:** Giá trị nhỏ hơn tốt hơn cho median; không thay cho RMSE của đầu mean.

## 51. 2026 modern: BSS 50 và tham chiếu thống nhất

2026 modern · BSS50 · chung khí hậu fit 2021–24

| Cấu hình | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | --- | --- | --- |
| A/C · 2 năm | 0,329 | 0,254 | 0,124 |
| B/D · 4 năm | 0,363 | 0,291 | 0,186 |
| N0 · 4 năm | 0,338 | 0,299 | 0,180 |
| N1 · 4 năm | 0,364 | 0,293 | 0,186 |
| GFS | 0,120 | 0,049 | -0,236 |
| MOS · 4 năm | 0,297 | 0,256 | 0,104 |

BSS vòng mới dùng chung CLIM_LONG, fit 2021–2024. Platt dùng 2025. BSS âm là xác suất kém khí hậu, không phải lượng mưa âm. Hạ cutoff để tăng POD không làm BSS tự tốt lên vì BSS được tính trước cutoff.

**Ý cần nhớ:** BSS dùng xác suất trước cutoff; tăng POD bằng hạ cutoff không tự làm BSS tốt lên.

## 52. Độ chắc chắn của 12 phép so A–D

Bootstrap ghép khối 14 ngày giữ sự phụ thuộc giữa trạm trong cùng đợt mưa;5.000 lần. Tiêu chí đòi cả CI đồng thời âm và Holm p nhỏ. D−Cngày 2 có p nhỏ nhưng CI đồng thời chứa 0 nên chưa đạt. Các kết quả vẫn là hồi cứu thăm dò vì năm 2026 đã được xem.

**Ý cần nhớ:** CI cắt 0: chưa đủ phân biệt cải thiện với dao động theo các đợt thời tiết.

## 53. Ba seed: khoảng điểm từng lần chạy

| Cấu hình | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | --- | --- | --- |
| A | 15,667 – 15,792 | 17,999 – 18,057 | 20,599 – 20,727 |
| B | 15,629 – 15,821 | 17,464 – 17,500 | 20,227 – 20,329 |
| C | 15,596 – 15,703 | 17,553 – 17,869 | 21,233 – 21,443 |
| D | 15,932 – 16,423 | 16,740 – 16,836 | 20,285 – 20,501 |

Đây là min–max của ba mô hình đơn, không phải CI. Ensemble lấy trung bình dự báo rồi mới tính RMSE, không lấy trung bình ba RMSE. Seed đo nhạy của lần học; bootstrap thời gian đo dao động theo các giai đoạn thời tiết. Hai loại kiểm tra không thay thế nhau.

**Ý cần nhớ:** Cùng seed giữa các cấu hình giúp đối chiếu; bootstrap theo thời gian trả lời câu hỏi khác.

## 54. Các nhóm diễn biến GFS trong ngày đã thử

| Cấu hình | Số biến | Thông tin thêm so với T0 |
| --- | --- | --- |
| T0 | 26 | N3 của nghiên cứu cũ |
| T1 | 34 | 8 biến phân bố mưa trong ngày |
| T2 | 41 | 15 biến diễn biến khí tượng trong ngày |
| T3 | 49 | Cả phân bố mưa và diễn biến khí tượng |

T1 thêm 8 biến phân bố mưa 6 h; T2 thêm 15 thống kê của 5 trường khí tượng; T3 kết hợp thành 49. Các thống kê khí tượng dùng ba mẫu dự báo bên trong ngày, không phải đủ 24 mẫu giờ. Toàn bộ là thông tin từ cùng bản GFS có trước issue, không thêm quan trắc tương lai.

**Ý cần nhớ:** T0–T3 là nghiên cứu riêng, không gọi lại thành E0–E7 hoặc A–D.

## 55. 49 biến: kết quả và đối chứng cùng số tham số

2025 legacy · RMSE mean · cùng mẫu trong nghiên cứu temporal

| Mô hình | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | --- | --- | --- |
| LGB T0 · 26 | 26,035 | 29,203 | 30,645 |
| LGB T3 · 49 | 25,869 | 29,163 | 30,683 |
| GRU T0 · 26 | **24,667** | 27,184 | 30,620 |
| GRU T3 · 49 | 24,675 | 28,154 | 30,761 |
| GRU LINEAR23 | 24,916 | **26,874** | **30,089** |

GRU T3 vàLINEAR 23 cùng 6.020 tham số; LINEAR23 chỉ thêm tổ hợp tuyến tính nguyên liệu cũ. Nhờ đó kiểm tra phần thông tin mới bên cạnh phần tăng dung lượng.0/12 phép RMSE chính đạt nên chưa chốt 49 biến. Không suy rộng kết quả này thành vô ích cho mọi ngân sách hoặc kiến trúc.

**Ý cần nhớ:** Không chọn mô hình theo riêng một con số tốt, hoặc nhầm tăng tham số thành thêm thông tin.

## 56. Vì sao không buộc phải dùng TFT hoặc Informer?

TFT có cơ chế xử lý biến tĩnh/quá khứ/biết trước; Informer chú trọng chuỗi dài. Cả hai là ứng viên hợp lệ, nhưng chưa có phép so đúng GFS–Vrain tại trạm này. Ưu tiên mô hình nhỏ để kiểm tra dữ liệu và giả thuyết không đồng nghĩa chứng minh Transformer kém. Kết quả nhãn vùng cũ không thay cho phép so hiện tại.

**Ý cần nhớ:** Chỉ thêm kiến trúc khi có giả thuyết, cùng dữ liệu/ngân sách và một kế hoạch kiểm định mới.

Nguồn: [Lim và cộng sự · 2021 · TFT](https://doi.org/10.1016/j.ijforecast.2021.03.012); [Zhou và cộng sự · 2021 · Informer](https://arxiv.org/abs/2012.07436)

## 57. Paper về LightGBM và GRU: giống ở ý tưởng nào?

Điểm tham khảo là có nghiên cứu dùng LightGBM cho hậu xử lý mưa và GRU kết hợp chuỗi quá khứ với dự báo nền. Nguồn PRISM/CNRFC của P2 khác Vrain/GFS, nên chỉ liên hệ phương pháp. Không sử dụng mức cải thiện của paper như một mốc phải đạt ở Đà Nẵng.

**Ý cần nhớ:** Dùng paper để xây dựng giả thuyết và đối chứng, không sao chép mức cải thiện khác dữ liệu.

Nguồn: [Zhang & Ye · 2021 · JHM](https://journals.ametsoc.org/view/journals/hydr/22/11/JHM-D-21-0096.1.xml); [Salehi & Salehi Neyshabouri · 2025](https://doi.org/10.1016/j.envsoft.2025.106635)

## 58. Tài liệu 2026 về chọn biến: tham khảo có điều kiện

P3 là preprint 2026 về LightGBM, dữ liệu MSM/JMA và lựa chọn biến/loss. Nhãn mưa 3 hkhác 24 hở dự án. Đây là bối cảnh tham khảo, không coi là bằng chứng bình duyệt hoặc phép so mô hình chung với dữ liệu Việt Nam.

**Ý cần nhớ:** Tình trạng xuất bản và tính tương đồng của bài toán đều phải được ghi rõ.

Nguồn: [Iwase & Takenawa · 2026 · preprint](https://arxiv.org/html/2604.19340v1)

## 59. Gói dữ liệu nào để gửi thành viên?

| Thành phần | Cách dùng |
| --- | --- |
| Một Parquet X/y | Một trạm × issue × horizon; y_mm là nhãn 24h |
| feature_sets.json / catalogue | Chọn đúng N0/N1/N3; không lấy mọi cột làm X |
| fit_short / fit_long | Train 2021–22 / 2021–24 |
| calibration_2025 | Chỉ Platt và cutoff; không fit cây |
| retrospective_2026 | Đã xem; dùng đánh giá hồi cứu, không gọi test mới |

Gói ngắn hạn mới có một Parquet 323.466 hàng,44 cột tổng cộng;26 cột là XcủaN 3. Dùng feature_sets.json để chọn X, không lấy mọi cột. Cờ fit_short/fit_long/calibration_2025/retrospective_2026 giải thích vai trò mới; split cũ giữ để truy vết. Không trộn toàn bộ file để train hoặc đưa nhãn/cờ chia tập vào X.

**Ý cần nhớ:** Cờ chia dữ liệu, nhãn và số đo tương lai không được đưa vào X.

## 60. Những câu hỏi dễ gặp khi bảo vệ

| Giảng viên hỏi | Trả lời ngắn gọn |
| --- | --- |
| Vì sao chưa dự báo trung bình vùng? | Nhãn trạm là điểm đo; chưa chứng minh được trung bình diện tích tin cậy. |
| Vì sao không chỉ dùng ERA5? | Cần nhãn trạm và khí tượng dự báo có trước issue, không ERA5 kỳ đích. |
| Vì sao chỉ 57 trong 86? | Giữ tiêu chí lịch sử train và cohort chung để so công bằng. |
| Có vượt paper khác chưa? | Chưa có benchmark cùng nguồn, kỳ đo, split và ngưỡng. |

Câu hỏi về mục tiêu vùng cần trả lời rõ nhóm đã chốt dự báo theo trạm. Vrain là điểm đo, chưa chứng minh được trung bình diện tích toàn vùng. ERA5 vẫn hữu ích nghiên cứu lịch sử, nhưng nhánh ngắn hạn cần nhãn trạm và dự báo có trước issue. Chỉ 57 trạm nhằm giữ lịch sử đủ và phép so chung; chưa có benchmark cùng điều kiện để nói vượt paper.

**Ý cần nhớ:** Trả lời đúng phạm vi bằng chứng, không phòng thủ bằng các con số khác bài toán.

## 61. Những câu hỏi về mô hình và kết quả

| Giảng viên hỏi | Trả lời ngắn gọn |
| --- | --- |
| POD 0,4 có tốt chưa? | Không có chuẩn chung; cần FAR/CSI, ngưỡng, kỳ đo và đối chứng. |
| L2 sao không thắng dù chấm RMSE? | Mẫu hữu hạn, cây hữu hạn; đổi cách học có đánh đổi ngày khô/mưa lớn. |
| RMSE 2026 thấp hơn 2025 là tiến bộ? | Không suy ra vậy: khác tập, mùa, mức mưa và API. |
| Đã dùng thực tế được chưa? | Mới có hồi cứu và tiến trình chờ; cần dự báo trước sự kiện và nhãn đến sau. |

Không có mốc POD tốt chung. L2 có thể đánh đổi nhóm mưa vì mẫu và cây hữu hạn. Điểm 2026 nhỏ hơn 2025 không chứng minh tiến bộ vì khác phân phối và API. Hiện có hồi cứu và tiến trình chờ; phải ghi dự báo trước sự kiện rồi mới nhận nhãn để tiến tới kết luận vận hành.

**Ý cần nhớ:** Những kết quả chưa tốt là đầu vào để thiết kế phép kiểm chứng tiếp theo.

## 62. Tài liệu gốc về hậu xử lý mưa

Liên kết dẫn tới trang nhà xuất bản hoặc bản thảo tác giả. P1/P2 là bài tạp chí; P3 là preprint. Tài liệu nguồn ghi rõ phần đã đọc và trường hợp trang toàn văn chặn truy cập. Không lấy các bài khác nguồn/nhãn làm bảng xếp hạng chung.

**Ý cần nhớ:** Ưu tiên nguồn gốc; phân biệt tạp chí bình duyệt, preprint và tài liệu kỹ thuật.

Nguồn: [Zhang & Ye · 2021 · JHM](https://journals.ametsoc.org/view/journals/hydr/22/11/JHM-D-21-0096.1.xml); [Salehi & Salehi Neyshabouri · 2025](https://doi.org/10.1016/j.envsoft.2025.106635); [Iwase & Takenawa · 2026 · preprint](https://arxiv.org/html/2604.19340v1)

## 63. Tài liệu về mục tiêu dự báo và kiến trúc

P4 hỗ trợ việc khớp đại lượng cần dự báo với metric. P5/P6 là các nguồn kiến trúc TFT/Informer, không phải bằng chứng hai mô hình đã được chạy trong bộ thí nghiệm trạm hiện tại. Phân biệt cơ sở lý thuyết với kết quả thực nghiệm của nhóm.

**Ý cần nhớ:** Ưu tiên nguồn gốc; phân biệt tạp chí bình duyệt, preprint và tài liệu kỹ thuật.

Nguồn: [Gneiting · 2011 · JASA](https://arxiv.org/abs/0912.0902); [Lim và cộng sự · 2021 · TFT](https://doi.org/10.1016/j.ijforecast.2021.03.012); [Zhou và cộng sự · 2021 · Informer](https://arxiv.org/abs/2012.07436)

## 64. Tài liệu chính thức về nguồn và đối chứng

Đây là các nguồn chính thức về GFS, tái phân tích và MOS. Mô tả sản phẩm không chứng minh mọi file lịch sử đã có sẵn trước issue. MOS đơn giản của nhóm cũng không phải tái hiện đầy đủ hệ thống vận hành NOAA. Dùng chúng để làm rõ khái niệm và nguồn dữ liệu.

**Ý cần nhớ:** Ưu tiên nguồn gốc; phân biệt tạp chí bình duyệt, preprint và tài liệu kỹ thuật.

Nguồn: [NOAA/NCEI · GFS](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast); [ECMWF/Copernicus · reanalysis](https://climate.copernicus.eu/climate-reanalysis); [NOAA/MDL · MOS](https://vlab.noaa.gov/web/mdl/mos)

## 65. Hồi cứu 2026: điểm số của bốn cấu hình

2026 · modern · 14.488 mẫu/trạm–issue · cùng 57 trạm · đã xem

| Cấu hình · đầu mean | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | --- | --- | --- |
| A · 2 năm/Tweedie | 15,708 | 18,029 | 20,677 |
| B · 4 năm/Tweedie | 15,683 | 17,469 | **20,270** |
| C · 2 năm/L2 | **15,627** | 17,736 | 21,356 |
| D · 4 năm/L2 | 16,135 | **16,776** | 20,406 |
| GFS gốc | 20,445 | 19,738 | 24,953 |
| MOS · 4 năm | 18,933 | 17,899 | 22,361 |

Đây là modern 2026, cùng 14.488 mẫu trạm–issue thuộc 57 trạm, chưa đủ năm. Năm 2026 đã xem ở các vòng trước nên gọi là hồi cứu. B có điểm thấp hơn A ở cả ba hạn; C/Dkhông thắng Tweedie nhất quán. So với GFS/MOS cùng mẫu có tín hiệu giá trị học máy, nhưng không lấy điểm nhỏ hơn của 2026 so với 2025 để gọi là tiến bộ, vì phân phối mưa và nguồn API khác nhau.

**Ý cần nhớ:** RMSE, mm/24h; nhỏ hơn tốt hơn. Kết quả có tính hồi cứu, chưa phải test tương lai mới.

## 66. Bảng tra tám chỉ số và mốc đọc kết quả

| Chỉ số | Câu hỏi dễ hiểu | Chiều tốt / mốc đọc |
| --- | --- | --- |
| RMSE | Có nhiều lần sai rất xa không? | Thấp hơn đối chứng |
| MAE | Trung bình lệch tuyệt đối bao nhiêu mm? | Thấp hơn đối chứng |
| Bias | Thường dự báo thừa hay thiếu? | Gần 0; xem riêng mưa lớn |
| BS | Xác suất lệch so sự kiện 0/1 ra sao? | Nhỏ hơn |
| BSS | Có hơn xác suất khí hậu tham chiếu? | >0 là hơn tham chiếu |
| POD | Bắt được bao nhiêu sự kiện thật? | Cao hơn; đọc cùng FAR |
| FAR | Trong lần báo có, bao nhiêu là nhầm? | Thấp hơn; đọc cùng POD |
| CSI | Cân bằng trúng, bỏ sót và báo nhầm? | Cao hơn; cùng ngưỡng |

Các chỉ số lượng mưa đánh giá bằng mm; các chỉ số sự kiện phụ thuộc ngưỡng mm, kỳ tích lũy, cutoff và tỷ lệ xuất hiện. FAR ở dự án là false alarm ratio F chia H cộng F, không phải false alarm rate F chia F cộng TN. BSS so với tham chiếu xác định rõ, không phải phần trăm dự đoán đúng. Khi so kết quả giữa paper, phải khớp đối tượng, kỳ đo, ngưỡng và cách tổng hợp; nếu không thì chỉ so phương pháp và giới hạn, không xếp hạng.

**Ý cần nhớ:** Không có ngưỡng POD 0,4 hoặc RMSE cố định để tự chứng nhận đạt.

Nguồn: [ECMWF · Brier score](https://confluence.ecmwf.int/pages/viewpage.action?pageId=240849421); [ECMWF · quyết định](https://www.ecmwf.int/en/newsletter/165/news/understanding-how-forecast-users-make-decisions)

## 67. Nguồn bổ sung cho mô hình, loss và mốc đánh giá

| Nguồn | Dùng để giải thích |
| --- | --- |
| LightGBM · objective | L2 và Tweedie với log-link; p = 1,5 là cấu hình của dự án |
| scikit-learn · Tweedie | Với 1 < p < 2: hỗ trợ giá trị 0 và giá trị dương liên tục |
| ECMWF · Brier score | Brier score và Brier skill score so với tham chiếu |
| ECMWF · quyết định | Understanding how forecast users make decisions |
| PyTorch · GRU | GRU: mạng hồi quy có cổng ghi nhớ thông tin trong chuỗi |

Đã đối chiếu tài liệu chính thức LightGBM về objective L2, Tweedie log-link và tweedie_variance_power. Tài liệu scikit-learn giải thích miền của Tweedie với 1 nhỏ hơn p nhỏ hơn 2. Tài liệu ECMWF giải thích Brier score và skill score, cùng vai trò chi phí và lợi ích trong quyết định dùng dự báo. Các nguồn này hỗ trợ cách diễn giải, không thay cho thí nghiệm tại Đà Nẵng và không đặt một ngưỡng đủ tốt chung cho dự án.

**Ý cần nhớ:** Đường dẫn đầy đủ có trong Notes và NGUON_TAI_LIEU.md.

Nguồn: [LightGBM · objective](https://lightgbm.readthedocs.io/en/stable/Parameters.html); [scikit-learn · Tweedie](https://scikit-learn.org/stable/modules/linear_model.html#tweedie-regression); [ECMWF · Brier score](https://confluence.ecmwf.int/pages/viewpage.action?pageId=240849421); [ECMWF · quyết định](https://www.ecmwf.int/en/newsletter/165/news/understanding-how-forecast-users-make-decisions); [PyTorch · GRU](https://docs.pytorch.org/docs/2.15/generated/torch.nn.GRU.html)
