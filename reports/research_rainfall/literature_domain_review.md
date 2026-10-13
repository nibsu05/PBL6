# Đánh giá đóng góp của hiểu biết khí tượng địa phương

Rà soát ngày 13/10/2026. Hướng nghiên cứu có cơ sở, nhưng chưa có bằng chứng rằng đổi kiến trúc hoặc thêm mọi biến ERA5 sẽ tạo cải thiện lớn. Cơ hội đáng ưu tiên là biểu diễn vận chuyển ẩm tương tác với địa hình, phân biệt chế độ mưa, đánh giá nhãn và sử dụng đầu xác suất đúng với sự kiện hiếm. Ma trận E0–E5 hiện tại là vòng sàng lọc, chưa đủ làm toàn bộ phần hiểu biết địa phương.

## Bằng chứng và giới hạn chuyển giao

| Bài gốc | Bằng chứng liên quan | Giới hạn với PBL6 |
| --- | --- | --- |
| [PLOS One 2026](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0342825) | Bốn tỉnh Trung Bộ; cùng LGBM và 13 biến, bộ chọn theo khí tượng/địa hình CSI 0,55, RF importance 0,53 (Table 14). Bộ cố định có TCW, dốc, R/u/v850. | Ước lượng cùng giờ, dùng Himawari và trạm; evaluation 5 giờ/ngày trong cùng giai đoạn 2019–2023. Không phải holdout năm tương lai hay dự báo trước 6 h. |
| [Advances in Meteorology 2023](https://onlinelibrary.wiley.com/doi/full/10.1155/2023/7256634) | Hai chế độ chính: mưa tháng 10–11 gắn không khí lạnh và nhiễu động nhiệt đới; chế độ đầu thu phía bắc gắn gió mùa phía tây. Địa hình làm tác động hoàn lưu khác nhau. | Phân tích cơ chế/biến động mưa, không đo lợi ích thêm biến vào Bi-LSTM. Không đồng nhất mọi mưa Trung Bộ với một cơ chế. |
| [Climatic Change 2021](https://link.springer.com/article/10.1007/s10584-021-03261-3) | Các đợt tháng 10/2020 có gió đông mang ẩm, nâng địa hình Trường Sơn và tác động phối hợp xoáy nhiệt đới/không khí lạnh. | Nghiên cứu quy kết một chuỗi cực đoan; hỗ trợ giả thuyết vật lý, không cung cấp mức tăng CSI cho mô hình của nhóm. |
| [SOLA 2026](https://link.springer.com/article/10.1007/s44393-026-00025-z) | XGBoost chọn đầu vào theo nguồn ẩm cho Kyushu; bài báo mô tả cải thiện NSE 15,1% ở hạn 4–6 ngày, giảm còn 5,6% trong điều kiện vận hành. | Một vùng/mùa, mô hình FLEXPART và hạn ngày; không chuyển phần trăm này sang CSI 3 h Đà Nẵng. Phải phân biệt phân tích khí quyển và forecast khi xác định nguồn ẩm. |
| [JMSJ 2019](https://www.jstage.jst.go.jp/article/jmsj/97/3/97_2019-040/_article/-char/en) | Các kênh Himawari giúp ước lượng mưa mạnh từ mây ấm trong trường hợp GSMaP NRT bỏ sót khi thiếu vi sóng. | Ước lượng vệ tinh, chưa là dự báo trước. Cho thấy loại mây và nguồn quan trắc có thể giới hạn kỹ năng. |
| [npj Climate and Atmospheric Science 2021](https://www.nature.com/articles/s41612-021-00190-x) | CAPE mô tả tiềm năng đối lưu, nhưng cần khởi phát; ERA5 và quan trắc có bất đồng, nhất là môi trường nhiệt đới. | Không coi CAPE/CIN là số đo hoàn hảo hoặc bảo đảm cải thiện mọi chế độ mưa. |
| [JAMES 2023](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2023MS003719) | Phản hồi đất–mưa phụ thuộc cả bề mặt và hoàn lưu; trong mô phỏng lý tưởng có thể có phản hồi âm. | Chưa có bằng chứng định lượng cho swvl1 ở Đà Nẵng 0–6 h; ưu tiên thấp hơn nhóm gió–ẩm–địa hình. |
| [Weather and Forecasting 2022](https://repository.library.noaa.gov/view/noaa/45331) | Ước lượng mưa ở địa hình phức tạp có bất định; dùng nhiều nguồn nhãn giúp đánh giá dự báo có xét độ tin cậy của quan trắc. | Miền Bắc California; không cung cấp điểm cho Đà Nẵng. Đúng thuật toán vẫn có thể bị chấm sai nếu nhãn sai. |
| [GMD 2024](https://gmd.copernicus.org/articles/17/4579/2024/) | Sai lệch nhỏ về vị trí/thời điểm có thể tạo cả báo sai và bỏ sót trong điểm nhị phân; nên đánh giá nhiều khía cạnh. | Không đổi chỉ số hậu nghiệm để làm điểm tăng; giữ chỉ số chính và đặt trước cách chấm bổ sung theo vùng/sự kiện. |

Đã kiểm tra JATS gốc của PLOS. Table 15 ghi RMSE 5,68/5,79, không khớp 5,48 trong đoạn thuyết minh về bảng. Dùng bảng cho so sánh đó; không lấy abstract làm mức cải thiện kỳ vọng.

## Kiểm tra dữ liệu công khai của tác giả

[Figshare 30782003](https://doi.org/10.6084/m9.figshare.30782003) cung cấp bộ tối thiểu 41.003.890 byte, CC BY 4.0; checksum khớp metadata. Ba file data_matching đã đọc là tháng 3/2019, 6/2020, 9/2019, lần lượt 3.272/3.094/3.113 hàng và 65/80/68 ID. Có utc_time, ID, value, x_id/y_id; chưa có lat/lon tường minh trong ba file này. Đây không phải toàn bộ 175 trạm liên tục 2019–2023. Chưa bổ sung vào dataset v2; cần kiểm tra bản đồ tọa độ, ý nghĩa nhãn và độ phủ trước khi dùng kiểm chứng. Dữ liệu chỉ cache ngoài Git.

## Chẩn đoán pilot có sẵn

Không train thêm. Dùng 30 ô, 3 seed; chọn ngưỡng theo CSI trên tháng 5–10/2022 rồi chấm tháng 5–10/2023, 22.080 cửa sổ, 721 sự kiện ≥10 mm/3 h. Không mở test 2025. Đầu xác suất đã hiệu chỉnh bằng 2022; ngưỡng thử là 0,01–0,95 bước 0,01.

| Cấu hình | CSI từ lượng mưa | CSI từ quyết định xác suất | Ngưỡng xác suất chọn ở 2022 | POD | FAR |
| --- | ---: | ---: | ---: | ---: | ---: |
| S1 | 0,180 | 0,383 | 0,21 | 0,599 | 0,485 |
| S4 | 0,091 | 0,271 | 0,38 | 0,298 | 0,253 |

Trong S1, hiệu số CSI giữa hai quy tắc là 0,203, CI bootstrap 95% [0,086; 0,268]. Hiệu số CSI đầu xác suất S1–S4 là 0,112, CI [−0,028; 0,219]: chưa khẳng định S1 thắng S4.

Đây là thay đổi quy tắc ra quyết định cho sự kiện, không cải thiện lượng mưa mm của cùng checkpoint. FAR 0,485 là 48,5% số lần báo có bị báo sai; không phải 48,5% toàn bộ mẫu. Cũng không coi CSI là tỷ lệ dự báo đúng. Dữ liệu 2023 đã được khám phá nhiều lần, CI còn điều kiện theo mô hình/ngưỡng; chưa là xác nhận độc lập. S4 dùng ERA5 giờ đích; chuỗi GSMaP lưu trữ dịch 4 h chưa chứng minh tái hiện nguồn NRT. Chưa có kết luận vận hành.

Số liệu: [decision_head_diagnostic.json](decision_head_diagnostic.json). Tái lập: `python scripts/diagnose_pilot_decisions.py`; cần dataset/checkpoint ngoài Git đã có.

## Giả thuyết địa phương nên ưu tiên

Các mục sau là đề xuất của dự án, chưa được các bài báo hoặc pilot xác minh trực tiếp:

1. Cùng độ ẩm, gió đưa không khí từ biển vào sườn đón gió có giá trị khác với gió đi từ nội địa ra biển. Thử tương tác gió–ẩm–địa hình, không chỉ từng cột u/v.
2. Độ bền của gió ẩm/hoàn lưu trong 6–24 h và xu thế ẩm/áp suất có thể giúp nhận diện mưa kéo dài. Chỉ tính từ quá khứ, giữ nguồn raw tương đương ở đối chứng.
3. Tách chế độ gió đông/đông bắc, gió tây/tây nam và đối lưu, bằng quy tắc từ đầu vào đặt trước khi xem kết quả; không dùng mưa tương lai để gán chế độ.
4. Kiểm tra tác động theo độ cao/khoảng cách biển và loại mây; kiểm tra tầng 850 có đại diện hợp lý ở ô địa hình cao.
5. Độ ẩm đất giữ ở vòng khám phá nhỏ; không đặt nó làm đóng góp chính khi chưa có tín hiệu.

## Thiết kế giảm rủi ro chạy nhiều mà ít kết quả

Trước hết rà nhãn theo sự kiện/mùa và kiểm tra quy tắc đầu lượng mưa/đầu xác suất. Giữ bảng CSI lượng mưa gốc, bổ sung CSI quyết định đã chọn ngưỡng ở validation; không trộn hai định nghĩa để công bố mức tăng.

So ba cấu hình: nền bề mặt + quan trắc; nền + nguyên liệu khí tượng thô cần thiết; cấu hình raw đó + biểu diễn có giả thuyết địa phương. Đối chứng raw phải chứa cùng nguồn dữ liệu thành phần để không quy lợi ích thêm nguồn cho biểu diễn vật lý. E0–E5 có thể dùng sàng lọc nguyên liệu, nhưng chưa cần nhân lên nhiều kiến trúc.

Giữ cùng mẫu, cùng loss/seed/ngân sách; thử trước trên Bi-LSTM và một baseline tabular. Với ứng viên, kiểm tra 3 fold: train 2015–2019/val 2020/eval 2021; train 2015–2020/val 2021/eval 2022; train 2015–2021/val 2022/eval 2023. Đây là kiểm tra độ bền trên lịch sử đã biết, chưa thay test độc lập 2025.

Đặt tiêu chí thực dụng trước khi chạy: ví dụ ΔCSI ≥0,03 hoặc BS giảm tương đối ≥5% so với nền mạnh, không suy giảm lớn chỉ số còn lại và có tín hiệu lặp ở ít nhất 2/3 năm. Các con số là ngưỡng kỹ thuật đề xuất, không phải mức bài báo bảo đảm. Phải xét bất định, số sự kiện, nhiều phép so và nguồn live.

Nếu không có tín hiệu: kiểm tra chất lượng nhãn, độ trễ/nguồn, đầu ra và baseline; thu hẹp phạm vi hoặc dùng mô hình đơn giản. Chỉ mở rộng TFT/ablation khi có câu hỏi riêng mà phép so đó giải quyết. App chọn cấu hình bằng kiểm định dự báo thật và độ tin cậy nguồn, không bằng mức tăng hồi cứu đẹp nhất.
