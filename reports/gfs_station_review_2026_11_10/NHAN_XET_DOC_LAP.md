# Nhận xét độc lập kết quả 57 trạm và đối chiếu nghiên cứu 2024–2026

Ngày rà soát: 10/11/2026. Đọc kết quả và mã đã có, kiểm tra thêm dự báo lưu sẵn; không train, không thay dự báo và không mở năm 2025. Các chẩn đoán mới bên dưới là phân tích hậu nghiệm trên dev 2024, không phải chỉ tiêu xác nhận đã đặt trước protocol.

**Đánh giá hiện tại:** hướng GFS + quan trắc trạm có cơ sở nghiên cứu. Kết quả pilot có tín hiệu hữu ích, đặc biệt LightGBM ở ngày 1–2 và GRU ở RMSE ngày 3. Nhưng dự báo lượng ngày 3 và mưa lớn còn yếu; chưa đủ bằng chứng vượt GFS ổn định hay vượt các công trình khác. Có một đối chứng mới quan trọng mà bộ slide trước chưa bao gồm: luôn dự báo 0 mm.

## 1. MAE tốt hơn GFS chưa đủ để gọi kết quả tốt

Macro MAE trên cùng 57 trạm và 2.782 mẫu trạm–issue mỗi hạn ở dev 2024, đơn vị mm trong một cửa sổ 24h:

| Phương pháp | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | ---: | ---: | ---: |
| Luôn dự báo 0 mm — chẩn đoán mới | 5,89 | 6,89 | **7,77** |
| GFS gốc | 5,83 | 7,41 | 10,30 |
| LightGBM A2 | 5,28 | **6,72** | 8,44 |
| LightGBM A3 | **5,24** | 6,75 | 8,34 |
| GRU A2 | 6,94 | 7,56 | 8,00 |

In đậm là nhỏ nhất trong cột ở các hàng trên, không khẳng định ý nghĩa thống kê. Phương án 0 mm không được fit hoặc chọn từ năm test.

Tỷ lệ mẫu có mưa dưới 1 mm là khoảng 72,0% / 66,6% / 63,2%. Vì vậy dự báo rất ít mưa có thể đạt MAE khá thấp. Ngày 3, cả A2/A3/GRU đều chưa vượt phương án 0 mm về MAE. Không nên chỉ nhìn mức giảm khoảng 18,1% MAE của A2 so GFS rồi gọi dự báo ngày 3 đã tốt.

Điều này không biến phương án 0 mm thành giải pháp dự báo: nó bỏ sót mọi sự kiện mưa và dự báo thiếu toàn bộ lượng. GRU ngày 3 vẫn có RMSE **17,62 mm**, thấp hơn 0 mm **22,89**, khí hậu **19,98**, GFS **26,73** và A2 **23,77** ở mức điểm. Mô hình có học được thông tin thời tiết; thành tích phụ thuộc loại lỗi muốn giảm.

MAE và bình phương sai số nhắm đến những đại lượng khác nhau của phân phối: median và mean. Cần xác định mục tiêu đầu lượng trước khi tuning, thay vì đổi chỉ số hậu nghiệm để chọn mô hình thắng. [Gneiting, Making and Evaluating Point Forecasts, 2011](https://arxiv.org/abs/0912.0902).

## 2. Mưa lớn là điểm yếu đáng ưu tiên

Chẩn đoán riêng những mẫu thực tế ≥50 mm/24h ở ngày 3:

| Phương pháp | MAE trên nhóm mưa lớn, mm | Bias trên nhóm mưa lớn, mm |
| --- | ---: | ---: |
| GFS gốc | 76,44 | −54,79 |
| LightGBM A2 | 90,00 | −74,90 |
| GRU A2 | 60,10 | −55,82 |

Đây là **micro trên nhóm mẫu mưa lớn**, khác cách macro của bảng toàn tập; chỉ so các hàng trong cùng bảng. Có 114 sự kiện-trạm nhưng chỉ 12 issue có ít nhất một sự kiện, chưa phải 114 đợt mưa độc lập. Chưa có CI cho các chẩn đoán điều kiện này.

A2 giảm MAE toàn tập nhưng có sai số lượng lớn hơn GFS trên nhóm này; GRU tốt hơn ở mức điểm song vẫn thiếu mưa mạnh. Ở cutoff xác suất 0,5, POD ≥50 mm ngày 3 của A2 khoảng 0,020; GRU khoảng 0,694 nhưng FAR khoảng 0,509 và BSS khoảng −0,210. BSS âm nghĩa là chất lượng xác suất kém khí hậu tham chiếu. Đây chưa phải bằng chứng cho hệ thống cảnh báo mưa lớn đáng tin cậy.

Không dùng mưa thật tương lai để quyết định chuyển mô hình trong vận hành. Chẩn đoán theo nhóm chỉ giúp hiểu lỗi, không tạo ra một mô hình hỗn hợp đã triển khai.

## 3. Tín hiệu cải thiện có thật ở mức nào?

- A2 giảm MAE so GFS khoảng **9,5% / 9,2% / 18,1%** trên dev. Nhưng CI 95% của A2−GFS cả ba hạn đều chứa 0. Đây là tín hiệu, chưa phải kết quả cải thiện ổn định đã được xác nhận.
- A2 có MAE thấp hơn GFS ở 43/57, 45/57 và 47/57 trạm trên dev. Nhiều trạm cùng tốt hơn vẫn không tạo thêm các năm thời tiết độc lập.
- Ở cal 2023, A2 ngày 1 còn kém GFS khoảng 3,0%; ngày 2 gần ngang; ngày 3 chỉ giảm khoảng 2,9%. Mức lợi ích thay đổi giữa hai năm.
- Khi so cùng 20 trạm cũ, mô hình mở rộng 57 trạm không tốt hơn đồng đều: ngày 3 có MAE cao hơn ở mức điểm; CI cả ba chênh chứa 0. Thêm trạm giúp mở phạm vi, chưa bảo đảm tăng độ chính xác.
- A2 thêm khí tượng có tín hiệu ngày 3 so A1; A3 thêm địa hình chưa cải thiện rõ. Chưa tách tác dụng của biến khí tượng thô khỏi dẫn xuất vận chuyển ẩm, hay DEM thô khỏi tương tác gió–địa hình.

Không đủ bằng chứng gọi đây là overfitting chỉ từ vài bảng điểm. Cần learning curve, độ bền theo năm/mùa/trạm và kiểm định mới để phân biệt thiếu mẫu, lệch phân phối, loss chưa phù hợp hay mô hình quá phức tạp.

## 4. Đối chiếu công trình gần đây

Không tìm thấy benchmark công khai được các công trình dưới đây cùng sử dụng với đúng Vrain57, issue 19h, nhãn 19–19h và split của dự án. Vì vậy đây là đối chiếu về thiết kế và bằng chứng, chưa phải bảng xếp hạng mô hình.

| Nghiên cứu gốc | Điểm liên quan đã kiểm tra | Bài học cho dự án |
| --- | --- | --- |
| [PostRainBench, phiên bản 2024](https://arxiv.org/html/2310.02676v3) — bản workshop/preprint | Hậu xử lý NWP; nhiều mạng thông dụng thua NWP ở mưa lớn trên các bộ kiểm tra. Dùng lưới, nhãn giờ/3h và ngưỡng khác dự án. | Cần vượt NWP trên cùng dữ liệu; thêm mạng phức tạp chưa bảo đảm thắng. Không lấy CSI của hai bài toán để so trực tiếp. |
| [Esquivel-González và cộng sự, Ecological Informatics 2025](https://www.sciencedirect.com/science/article/pii/S157495412500264X) | UNet hậu xử lý 25 thành viên WRF, mưa giờ tại 130 trạm Canary; so EMOS/CSGD, Analog Ensemble và mạng đơn giản, kiểm tra trạm giữ lại. | Cần đối chứng hậu xử lý đơn giản và kiểm tra tổng quát hóa. Lưới 1 km, ensemble, kỳ đo và chia theo ngày khác dự án. |
| [Trotta & Abellan, 2026](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2026JH001327) | Hậu xử lý tổng ngày, mạng ban đầu 755 trạm AWS và khoảng một triệu mẫu train; loại một số trạm theo land–sea mask. Lân cận không gian giúp HRES, nhưng không cải thiện rõ AIFS. | Predictor quanh trạm có thể đáng thử; lợi ích phải kiểm chứng theo nguồn NWP, không suy ra mọi mô hình đều cần CNN. |
| [Dantanarayana & Kanae, SOLA 2026](https://link.springer.com/article/10.1007/s44393-026-00025-z) | XGBoost với lựa chọn biến theo nguồn ẩm cho mưa trung bình Kyushu. Mức cải thiện NSE ở hạn 4–6 ngày báo cáo 15,1%, giảm còn 5,6% khi tính điều kiện vận hành. | Dẫn xuất có ý nghĩa vật lý là hướng nghiên cứu hợp lý; cần đối chứng cùng nguyên liệu và tính khả dụng thật. Không so % NSE này với % giảm MAE của dự án. |

[Main và cộng sự, Meteorological Applications 2024](https://rmets.onlinelibrary.wiley.com/doi/full/10.1002/met.2222) đánh giá dự báo ECMWF tại Việt Nam và thấy skill giảm khi dùng VnGP thay ERA5 làm tham chiếu mưa. Điều này hỗ trợ việc kiểm chứng bằng dữ liệu gần quan trắc trạm hơn, nhưng không chứng nhận số đo Vrain không sai số hay chứng minh dự án tốt hơn bài báo.

Bài [PLOS One 2026 về bốn tỉnh ven biển Trung Bộ](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0342825) dùng Himawari, ERA5, địa hình và trạm để **ước lượng mưa cùng giờ**. Bài toán khác dự báo trước ba ngày; không so trực tiếp MAE mm/h, CSI hoặc POD của bài đó với nhãn mm/24h của dự án, cũng không chia/nhân 24 để tạo so sánh tương đương.

Các bài báo có thiết kế khác nhau; không mặc định split của chúng chứng minh cùng dạng tổng quát hóa theo thời gian mà dự án hướng tới.

## 5. Điểm có giá trị và đóng góp chưa được chứng minh

Điểm có giá trị là bộ dữ liệu mưa tại điểm, hợp đồng thời gian rõ, đối chứng GFS, mô hình dùng chung nhiều trạm và đánh giá nhiều khía cạnh. Đây là nền để thực hiện nghiên cứu địa phương có thể kiểm tra lại.

Tuy nhiên, dùng LightGBM/GRU, thêm nhiều biến hay train 57 trạm chưa tự tạo đóng góp phương pháp mới. Đóng góp tiềm năng là chứng minh **một biểu diễn gió–ẩm–địa hình phù hợp khu vực** làm tốt hơn đối chứng cùng nguồn dữ liệu, lặp được qua năm/mùa và không suy giảm nghiêm trọng mưa lớn. Hiện chưa có bằng chứng đó.

## 6. Thứ tự kiểm chứng tiếp theo

1. Tạo protocol phiên bản mới với lịch issue hằng ngày và kiểm tra độ trễ nguồn; giữ nguyên pilot cũ. Nhiều ngày hơn tăng mẫu nhưng không tạo thêm mùa cực đoan độc lập.
2. Bổ sung đối chứng 0 mm và hậu xử lý GFS đơn giản; định nghĩa rõ đầu lượng nhắm mean hay median. Giữ MAE/RMSE/Bias, chất lượng xác suất và mưa lớn cùng lúc. Không đổi metric chính chỉ vì bảng mới có kết quả khó đẹp.
3. Tách thí nghiệm nguyên liệu thô và biểu diễn: đối chứng chứa T/RH/u/v/PWAT và địa hình thô tương ứng; cấu hình thử mới thêm qflux/upslope hoặc đặc trưng hoàn lưu. Cùng mẫu, loss và ngân sách.
4. Xử lý thứ tự P(≥50)≤P(≥1), kiểm tra calibration và cách chọn cutoff trên cal. Không nâng POD bằng mọi giá nếu FAR tăng hoặc BSS xấu đi.
5. Tuning có giới hạn trong các fold thời gian phát triển; sau khi khóa thiết kế mới mở test 2025. Chưa nên tăng số kiến trúc chỉ để có thêm bảng so sánh.

Đối với báo cáo đồ án, có thể trình bày đây là **pilot nghiên cứu đã có kết quả và đã phát hiện các giới hạn quan trọng**. Đối với tuyên bố cải thiện khoa học hoặc vận hành cảnh báo, bằng chứng hiện tại còn thiếu. Cần tập trung sửa cách đánh giá và kiểm chứng giả thuyết trước khi mở rộng mô hình.

## 7. Nguồn nội bộ và tái tạo

- [Kết quả pilot57](../gfs_station_57_2026_11_10/BAO_CAO_MO_RONG.md), các CSV `point_metrics`, `probability_metrics`, `event_metrics`, `paired_bootstrap` cùng thư mục.
- [Chẩn đoán mới](diagnostics.json), [bảng tổng hợp](diagnostic_metrics.csv). Không có dòng dự báo, tọa độ hoặc số liệu từng trạm trong các file công khai này.
- Chạy `.venv\Scripts\python.exe -X utf8 scripts/review_gfs_station_results.py`; cần dự báo private đã được cấp quyền. Script chỉ đọc nguồn cũ, đối chiếu lại metric, không fit hoặc sửa kết quả đã đóng băng.

Bộ slide đã gửi được giữ nguyên. Khi sử dụng để báo cáo, cần nói bổ sung phát hiện đối chứng 0 mm và lỗi theo nhóm mưa lớn trong tài liệu này; không chỉ trình bày phần giảm MAE so GFS.
