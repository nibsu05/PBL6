# Ghi chú thuyết trình — Dự báo mưa hằng ngày v2

Các bảng kết quả là dev 2024. Năm 2025 chưa được chấm trong thí nghiệm này.

## 01. Dự báo mưa 1–3 ngày tại 57 trạm

Mở đầu bằng mục tiêu nghiên cứu: dùng khí tượng dự báo và lịch sử mưa tại trạm để dự báo ba lượng mưa 24 giờ. Nhóm đánh giá giá trị bổ sung đặc trưng và so với các đối chứng đơn giản. Đây là bản hằng ngày mới, có kiểm soát tuning và xác suất; không phải bộ kết quả cũ dùng 208 issue cách nhau một tuần.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · protocol.json

## 02. Ba điều cần nhớ trước khi xem các bảng

Tránh mở đầu bằng một loạt con số chưa có bối cảnh. Thông điệp thứ nhất là khí tượng thô dự báo có giá trị. Thứ hai, giá trị dẫn xuất không giống nhau ở LightGBM và GRU. Thứ ba, điểm trung bình cải thiện không đồng nghĩa cảnh báo mưa lớn đã đủ tin cậy. Các kết luận thống kê đều nằm trong phạm vi dev 2024 và khoảng tin cậy thăm dò.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · KET_LUAN.md

## 03. Dự báo điều gì tại mỗi trạm?

Ngày dự báo là cửa sổ 19 giờ đến 19 giờ hôm sau, không phải ngày lịch 0–24 giờ. Mỗi nhãn là tổng 24 giờ tại đúng trạm. Ba nhãn không chồng nhau. Không dùng tổng các trạm hay mưa trung bình diện tích. Một mô hình chung học nhiều trạm, còn giá trị đầu ra vẫn riêng cho từng trạm.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · protocol.json

## 04. Một mẫu = một trạm + một thời điểm phát tin

Ví dụ trên slide chỉ minh họa, không phải số đo một trạm thật. Trong lúc train, nhãn tương lai dùng để tính lỗi và cập nhật mô hình. Khi phát dự báo, chỉ đưa X vào mô hình. Cùng một issue có thể có nhiều mẫu tương ứng nhiều trạm; trạm thiếu dữ liệu chỉ làm mất mẫu của trạm đó, không làm mất toàn mạng.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · protocol.json

## 05. Ba nguồn dữ liệu có ba vai trò

Vrain cung cấp nhãn thực đo sau QC và lịch sử mưa. GFS là dự báo khí tượng số, lấy bốn nút lưới 0,25 độ nội suy về vị trí trạm; nội suy không tạo thêm độ phân giải thật. DEM từ Mapzen chỉ là proxy địa hình tại tọa độ hiện có, không phải cao độ đo bằng khảo sát tại cảm biến. Mean/std địa hình lấy chín điểm trong ô ±5 km.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · protocol.json

## 06. 07h → 18h → 19h: đầu vào phải có trước issue

Issue nghĩa là thời điểm phát hành dự báo. Chu kỳ GFS 00UTC tương ứng 07 giờ Việt Nam; khoảng cách đến issue là 12 giờ. Với giả định trễ trạm một giờ, chỉ dùng số đo kết thúc 18 giờ, không dùng số đo kết thúc 19 giờ ngay lúc phát tin. Bảy tổng ngày đầy đủ gần nhất kết thúc ở 19 giờ hôm trước. Giả định độ trễ khác với việc đã xác minh khoảng đo giờ.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · protocol.json

## 07. Đã kiểm tra nguồn, nhưng chưa chứng minh realtime

GFS Last-Modified chỉ là giờ sửa đối tượng trên kho, không phải lịch sử thời điểm người dùng nhận được bản tin. Có 48 chu kỳ đầu 2021 mang timestamp sửa archive sau issue, có thể do chép lại kho; không suy diễn chắc chắn là phát hành gốc muộn hoặc sớm. API Vrain hiện tại trả hàng giờ nhưng chưa chứng minh độ trễ tiếp nhận từng số đo lịch sử. Không đưa dữ liệu 2026 của lần kiểm tra API vào train.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · source_latency_audit.json

## 08. 57 trạm và 1.449 chu kỳ dùng được

Có 86 vị trí trong danh mục nhóm Đà Nẵng của tài khoản, không phải toàn quốc hay chứng nhận phủ kín diện tích. Cohort 57 giữ điều kiện chọn chỉ bằng train: ít nhất 365 ngày đủ và 30 ngày mưa ≥1 mm. Lịch mới là mỗi ngày, không phải mỗi tuần. Hai ngày nguồn lỗi bị loại trước fit, đồng đều cho mọi mô hình, dựa trên 404 và đối chiếu byte GRIB, không dựa trên lượng mưa.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · dataset_audit.json / source_coverage_policy.json

## 09. Mỗi giai đoạn có một nhiệm vụ khác nhau

Train 2021–2022 dùng học trọng số, scaler và tham chiếu khí hậu; tuning cũng chỉ diễn ra bên trong giai đoạn này. Cal 2023 dùng hiệu chỉnh xác suất và chọn cutoff, không chọn checkpoint như pilot cũ. Dev 2024 dùng đọc kết quả và định hướng phát triển, nên chưa phải test cuối. Mẫu trạm–issue có ba nhãn; dữ liệu dạng bảng dài có ba hàng cho một mẫu.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · dataset_audit.json / protocol.json

## 10. “Giữ kín 2025” có nghĩa là gì?

Giữ kín là giữ lại một năm để kiểm định cuối, không phải giấu một bảng kết quả đã có. Năm 2025 đã qua về lịch, nhưng chưa tham gia chọn đặc trưng, tham số, cutoff hoặc chấm điểm trong pipeline hiện tại. Nếu liên tục xem điểm 2025 rồi sửa mô hình cho đẹp, năm đó trở thành dữ liệu phát triển. Hiện dataset thí nghiệm mới chỉ được dựng và kiểm chứng cho 2021–2024; không khẳng định đã có sẵn bộ test 2025 hoàn chỉnh.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · protocol.json · scikit-learn: cross-validation

## 11. So sánh công bằng và tránh nhầm tương lai

Dùng cùng mẫu có đủ nhãn cả ba hạn và đủ đặc trưng cho mọi cấu hình, kể cả ba kịch bản trễ trạm. Không điền nhãn thiếu thành 0. Toàn bộ 72 giờ nhãn phải thuộc cùng split, còn lịch sử được phép lấy từ quá khứ trước ranh. Scaler chỉ fit train. Số mẫu còn lại có thể không đại diện các đợt cảm biến bị lỗi, nhất là nếu thiếu số liên quan mưa lớn.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · dataset_verification.json

## 12. Tuning: bốn lần học quá khứ → kiểm tra quý kế

Đây là rolling validation bên trong train 2021–2022, không dùng năm 2024 để early stop. Ở mỗi fold, nhãn train phải kết thúc ít nhất bảy ngày trước đầu quý validation; ba nhãn validation nằm trong quý. Bốn quý gồm các điều kiện mùa khác nhau. Sau khi chọn cấu hình, fit lại toàn train với số cây hoặc epoch cố định lấy trung vị từ CV.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · protocol.json / tree_tuning_trials.csv

## 13. Vì sao cần cả 0 mm, GFS thô và MOS?

ZERO kiểm tra trường hợp nhiều ngày khô khiến MAE trông dễ đạt; nó không phải cảnh báo hữu ích. Khí hậu là thông tin tháng–trạm từ train. Persistence lặp tổng 24 giờ đã có. GFS là dự báo trước học máy. MOS chỉ dùng lượng mưa GFS và sin/cos mùa, với mô hình tuyến tính/phân vị/logistic; nếu mô hình phức tạp không hơn nó thì chưa chứng minh cần sự phức tạp. LightGBM cũng là mô hình dự báo thật, không phải đối chứng được cố tình làm yếu.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · protocol.json

## 14. Vì sao có hai cách trả lời “mưa bao nhiêu mm”?

Mean là kỳ vọng, median là trung vị của lượng mưa có điều kiện theo đầu vào. Ví dụ hoàn toàn giả định: xác suất 80% không mưa và 20% mưa 50 mm; kỳ vọng là 10 mm nhưng trung vị là 0. MAE và sai số bình phương khuyến khích các đại lượng khác nhau. Vì thế hai đầu được định nghĩa trước khi chấm dev; không chọn đầu đẹp theo từng metric rồi gọi là một dự báo duy nhất. Cơ sở: Gneiting, Making and Evaluating Point Forecasts.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · protocol.json · Gneiting (2011)

## 15. N0–N5: thêm thông tin gì vào mô hình?

Các cấu hình này thuộc thí nghiệm trạm hằng ngày v2, không phải E0–E7 của bộ vùng trước đây. N0 có 16 đặc trưng gồm mưa GFS, mùa, tọa độ, ID và 10 biến mưa lịch sử. N1 thêm khí tượng thô. N2 và N4 thêm biến được tính từ cùng T, RH, u, v, không phải nguồn quan trắc mới. N3 thêm năm biến địa hình. N5 thêm tương tác giữa gió/ẩm và độ dốc. q là độ ẩm riêng suy ra từ nhiệt độ, độ ẩm tương đối ở 850 hPa; q*u và q*v là dòng ẩm một mực, không phải tích phân vận chuyển ẩm IVT.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · protocol.json · tree_summary.json

## 16. Mỗi phép so sánh trả lời một câu hỏi

Không chỉ so N0 với N5 rồi quy hết cải thiện cho các dẫn xuất. N1 so N0 tách phần thông tin khí tượng mới. N3 so N1 tách địa hình. N2 so N1 và N4 so N3 tách cách biểu diễn gió ẩm. N5 so N4 tách tương tác địa hình; N5 so N3 là hiệu quả toàn bộ gói dẫn xuất. LightGBM chạy đủ N0–N5. GRU chỉ chạy N3 và N5 để kiểm tra xem gói dẫn xuất có tác dụng trong một họ mô hình khác. Cấu hình, mẫu, seed và tiêu chí đánh giá được giữ chung trong từng họ.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · protocol.json · paired_bootstrap.csv

## 17. Hai cách học trên cùng bài toán trạm

LightGBM là mô hình dự báo đầy đủ, mạnh với dữ liệu bảng và là đối chứng cần thiết. Nó học riêng từng hạn và từng đầu ra. GRU là mạng tuần tự nhỏ đọc chuỗi bảy tổng mưa ngày, ghép với ngữ cảnh dự báo khí tượng từng hạn và embedding trạm. Cả hai học chung nhiều trạm; không huấn luyện 57 mô hình độc lập. Ngữ cảnh GRU N3 có 18 số liên tục, N5 có 24; lịch sử và embedding được xử lý riêng nên không thể so số chiều này trực tiếp với 26/32 cột LightGBM. TFT/Informer cũ dùng bài toán, nhãn và protocol khác; bộ kết quả đó không thể đưa vào bảng so sánh hiện tại. Đây không phải bằng chứng TFT hay Informer không khả thi.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · gru_summary.json · tree_summary.json

## 18. LightGBM: chỉnh trên train, khóa trước calibration

Mỗi đầu ra có ba ứng viên nhỏ/pilot/vừa, thử trên bốn fold thời gian trong train, với N3 làm cấu hình neo. Chọn ứng viên theo điểm CV rồi dùng trung vị số cây tối ưu giữa các fold cho fit cuối. Mỗi cấu hình N0–N5 dùng chung lựa chọn này, tránh tăng cơ hội tuning riêng cho nhóm nhiều biến. Learning rate 0,04; subsample và colsample 0,9; L2 bằng 5. Tối đa 600 cây, patience 50 chỉ trong CV train. Đầu mean dùng Tweedie power 1,5; median dùng quantile 0,5; hai đầu xác suất dùng binary loss. Tổng 144 fit CV và 288 bộ ước lượng cuối bao gồm các thí nghiệm độ trễ. Không early stopping bằng 2023 hay 2024.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · tree_selection.json · tree_tuning_trials.csv

## 19. GRU và “ba seed”: chạy lặp để giảm may rủi

Seed điều khiển khởi tạo trọng số, trộn mẫu và các thành phần ngẫu nhiên. Ba seed không phải ba năm hay ba lần chia test. Bảng minh họa GRU N5 ngày 1; ensemble là trung bình dự báo trước khi tính metric, không phải trung bình ba metric. GRU chọn hidden 16, head 24, learning rate 0,001, fit cuối 17 epoch qua CV train; dropout 0,1, batch 256, AdamW weight decay 0,001, gradient clip 1. Loss gộp Tweedie đã chuẩn hóa, pinball và 0,5 lần hai BCE. N3 có 4.364 tham số và N5 có 4.796: gói dẫn xuất tăng 432 tham số, nên chưa tách hoàn toàn tác động biểu diễn khỏi dung lượng mạng.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · gru_selection.json · seed_metrics.csv

## 20. Xác suất phải hợp lý trước khi dùng cảnh báo

Hai sự kiện lồng nhau: mọi ngày mưa ít nhất 50 mm cũng phải là ngày mưa ít nhất 1 mm. Mô hình học P1 và xác suất có điều kiện Q50 trên các mẫu wet. Sau hiệu chỉnh Platt trên 2023, tính P50=P1×Q50. Cách làm giữ P50 không vượt P1 ở từng seed và cả ensemble. Ngưỡng quyết định tau được chọn bằng quarter cross-fitting trên 2023, cách ly ±7 ngày; cùng tau cho hai sự kiện tại mỗi mô hình/hạn. Quarter cross-fit chỉ là công cụ calibration lịch sử, không phải giả lập dự báo thời gian thực năm 2023. Chấm 2024 bằng calibrator fit trên toàn bộ 2023 và tau đã chọn. Mốc 50 mm ở đây là ngưỡng nghiên cứu thăm dò, không tự động là chuẩn cảnh báo hành chính.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · probability_coherence.csv · decision_cutoffs.json

## 21. Đọc các chỉ số như thế nào?

RMSE phạt mạnh sai số lớn và là tiêu chí chính của đầu mean; MAE dễ diễn đạt theo mm và là tiêu chí chính của đầu median. Bias là dự báo trừ quan trắc: âm nghĩa dự báo thiếu trung bình. BS là sai số bình phương giữa xác suất và nhãn 0/1. BSS=1−BS/BS khí hậu, với cùng tập mẫu và tham chiếu khí hậu học từ train; âm nghĩa kém hơn tham chiếu đó theo BS. H là báo trúng, M là bỏ sót, F là báo nhầm. POD=H/(H+M), FAR=F/(H+F), CSI=H/(H+M+F). FAR ở đây là false alarm ratio, không phải false positive rate. Không có quy tắc POD 0,4 luôn tốt; cần cùng ngưỡng mưa, hạn dự báo, mẫu và FAR/CSI để so sánh. Các bảng lượng ghi rõ đầu dự báo, các bảng sự kiện ghi rõ ngưỡng và tau.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · MET Appendix C · protocol.json

## 22. Một con số chung và khoảng tin cậy nói gì?

Macro: tính metric tại từng trạm rồi lấy trung bình 57 trạm; mỗi trạm có trọng số bằng nhau. Macro RMSE không phải căn của MSE gộp toàn mạng. Macro BSS là trung bình skill từng trạm, không tính lại bằng tỷ số hai macro BS. So sánh cặp dùng cùng ngày và trạm, lấy mẫu lại 1.000 lần theo khối tròn 14 ngày để giữ một phần phụ thuộc thời gian và đồng biến các trạm. Chênh lệch A−B âm tốt hơn cho sai số. CI chứa 0 nghĩa chưa có bằng chứng rõ theo phép thử này, không chứng minh hai mô hình bằng nhau. Đây là CI thăm dò chưa điều chỉnh nhiều phép so sánh, điều kiện trên các mô hình đã fit; không bao quát độ bất định cảm biến hay thay đổi khi train lại.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · paired_bootstrap.csv · protocol.json

## 23. Sai số lượng mưa: RMSE của đầu mean ↓

Các giá trị có đơn vị mm/24h, macro theo trạm. In đậm giá trị thấp nhất trong những dòng đang hiển thị; bảng toàn bộ cấu hình ở phụ lục. Mô hình có điểm thấp nhất từng ngày không nhất thiết thắng có ý nghĩa thống kê. ZERO thấp ở MAE nhưng RMSE cao cho thấy tác hại của bỏ qua mưa. So với MOS, các mô hình nhiều biến có tín hiệu cải thiện trên dev.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · point_metrics.csv

## 24. Sai số điển hình: MAE của đầu median ↓

Đầu median được huấn luyện để tối ưu trung vị, nên được so theo MAE chính. Không lấy MAE từ median rồi dùng như cùng một dự báo mean trong bảng RMSE. GRU N5 có MAE median thấp nhất trong các cấu hình chính, nhưng đó vẫn là kết quả dev. Phụ lục có toàn bộ N0–N5.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · point_metrics.csv

## 25. Xác suất mưa ≥50 mm: BSS so với khí hậu ↑

BSS dương nghĩa tốt hơn khí hậu tham chiếu theo BS; âm nghĩa kém hơn. GFS thô ở đây bị chuyển thành xác suất 0 hoặc 1 từ một lượng dự báo tất định; đó không phải hệ dự báo tổ hợp GFS và không nên diễn giải là năng lực xác suất của một ensemble. MOS và CLIM là đối chứng xác suất phù hợp hơn. BSS là macro của skill từng trạm. In đậm là cao nhất trong các dòng hiển thị, không phải mọi cấu hình trong phụ lục.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · probability_metrics.csv

## 26. Bắt được mưa lớn nhiều hơn, nhưng báo nhầm còn cao

Bảng là sự kiện ≥50 mm/24h, với tau chọn trên calibration 2023 và đóng băng khi chấm 2024. Mỗi dòng hiển thị ngày dự báo, mô hình, cutoff, POD, FAR, CSI. Không thể so POD riêng rồi kết luận: hạ tau thường bắt được nhiều mưa hơn nhưng cũng tăng báo nhầm. Ngày 1 có 890 station-day mưa lớn trên 96 issue; ngày 2 là 886/95; ngày 3 là 884/94. Đây không phải hàng trăm trận mưa độc lập vì nhiều trạm có thể gặp cùng hệ thời tiết. Bảng dùng macro; không diễn giải phép nhân POD với tổng số sự kiện như thể đó là micro.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · event_metrics.csv

## 27. Khí tượng thô bổ sung: tín hiệu cải thiện rõ hơn

So LightGBM N1 với N0 giữ cùng mô hình và quy trình, chỉ thêm T/RH/u/v 850 hPa và PWAT dự báo. Các khoảng RMSE dưới 0 ở cả ba ngày cho thấy ích lợi của thông tin khí tượng dự báo ngoài lượng mưa GFS và lịch sử mưa. Bảng cũng cho chênh MAE median để người đọc không nhầm chức năng đầu ra. Đây là bằng chứng trên cùng dev 2024 và bootstrap thăm dò, không phải bằng chứng nhân quả hay đánh bại một paper khác có dữ liệu khác.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · paired_bootstrap.csv

## 28. N5 − N3: dẫn xuất giúp ích khác nhau giữa mô hình

N5 so N3 giữ cùng nguồn khí tượng thô và địa hình, bổ sung sáu dẫn xuất gió–ẩm–địa hình. LightGBM chưa có chênh lệch RMSE hoặc MAE rõ ở cả ba ngày theo CI này. GRU có CI âm ở ngày 1–2, còn ngày 3 chứa 0. Không gọi mọi con số giảm nhỏ là cải thiện được chứng minh. GRU N5 đồng thời tăng 432 tham số nên cần thí nghiệm khớp dung lượng nếu muốn quy kết riêng cho cách biểu diễn. Các cấu hình được khảo sát trên dev 2024; cần kiểm định 2025 sau khi khóa lựa chọn.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · paired_bootstrap.csv

## 29. Nếu mưa trạm đến chậm hơn thì sao?

LightGBM N3 được fit và chấm lại với lịch sử mưa trạm bị cắt sớm 1, 3 hoặc 6 giờ trước issue 19h; dùng chung mẫu hoàn chỉnh giữa ba trường hợp. Tổng mưa 1/6/24h gần nhất thay theo cutoff, chuỗi bảy ngày hoàn chỉnh vẫn là thông tin trước issue. Kết quả không suy giảm lớn trong kiểm tra này; không suy ra API thực tế luôn sẵn sàng hoặc chậm luôn có lợi. Trễ GFS 8h được giả định; nếu thực tế trễ 16h thì cycle 00UTC không kịp issue 19h, protocol này chưa có fallback cycle cũ. Cần kiểm chứng receipt-time thực tế khi vận hành.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · point_metrics.csv · source_latency_audit.json

## 30. Mưa lớn vẫn là phần khó của bài toán

Bảng lọc theo lượng quan trắc ≥50 mm ở ngày 3 để chẩn đoán: 884 station-day trên 94 issue. Các sai số là micro trên tập con này, không trộn với macro của bảng toàn bộ. Bias âm cho thấy trên những ngày thực sự mưa lớn, lượng kỳ vọng thường thấp hơn quan trắc. Vì đang điều kiện trên Y lớn, ngay một dự báo kỳ vọng đúng cũng có thể có bias âm ở tập con; riêng bảng này không chứng minh xác suất đã sai calibration. Không được dùng ngưỡng quan trắc tương lai để chọn mô hình khi phát tin. Cần xem đồng thời reliability, BS/BSS và sai số theo mức mưa.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · conditional_amount_metrics.csv

## 31. Đã kiểm tra gì, còn điều gì chưa biết?

Kết quả công bố của daily-v2 đã qua 179 unit tests, đối chiếu lại 218.658 dòng station-issue-horizon, replay checkpoint 288 mô hình cây và sáu GRU, 186 calibrator và 2.106 giá trị metric; 27 đoạn GRIB được lấy mới để kiểm tra độc lập 81 phép nội suy bốn nút. Kiểm tra này hỗ trợ tính đúng của pipeline, không phải chứng nhận chất lượng cảm biến. Năm 2025 chưa nằm trong tập kết quả thí nghiệm này. Dữ liệu chỉ có hai năm train, một năm calibration, một năm dev; complete-case có thể thiên lệch khi mất số liệu trong mưa lớn. Địa hình dùng DEM và tọa độ hiện tại, không có lịch sử di dời trạm đầy đủ. Khi áp dụng nơi khác phải kiểm tra nguồn và train/validation lại.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · release_validation.json · model_verification.json

## 32. Chốt hiện tại và cách mở kiểm định 2025

Kết luận hợp lý hiện tại: thông tin khí tượng thô có ích; dẫn xuất có tín hiệu ở GRU ngày 1–2 nhưng không đồng đều giữa họ mô hình; vẫn phải cải thiện dự báo mưa lớn và báo nhầm. Không kết luận hơn các paper khác nếu chưa có cùng bài toán và protocol. Trước khi đánh giá 2025 cần đóng băng cấu hình được chọn, baseline, đầu lượng, ngưỡng sự kiện, cutoff, quy tắc QC và cách tính metric; chuẩn bị dữ liệu 2025 theo đúng quy tắc, kiểm tra độ phủ và availability không dựa trên điểm mô hình; sau đó chấm và báo cáo cả kết quả không đẹp. Nếu xem điểm 2025 rồi tiếp tục tuning theo nó, 2025 trở thành dev và phải có tập kiểm định mới. Khi replay 2025 vẫn được dùng mưa quá khứ đã có trước từng issue làm đầu vào, nhưng không được fit bằng nhãn tương lai. Bản slide này chỉ đọc các tổng hợp 2021–2024, không mở hoặc chấm test 2025.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · protocol.json

## 33. Toàn bộ cấu hình: RMSE đầu mean (mm) ↓

Bảng đủ năm đối chứng và sáu cấu hình LightGBM, hai GRU. Cùng tập mẫu dev 2024, macro theo trạm. In đậm giá trị tốt nhất trong bảng; Bias chọn giá trị gần 0 nhất. Không suy ra thắng thống kê chỉ từ in đậm. Đối chứng tất định được chuyển sang xác suất 0/1 để chấm BS, nên MOS và khí hậu là tham chiếu xác suất quan trọng hơn. Các thí nghiệm độ trễ được trình bày riêng, không lẫn vào phép so đặc trưng.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · point_metrics.csv

## 34. Toàn bộ cấu hình: MAE đầu median (mm) ↓

Bảng đủ năm đối chứng và sáu cấu hình LightGBM, hai GRU. Cùng tập mẫu dev 2024, macro theo trạm. In đậm giá trị tốt nhất trong bảng; Bias chọn giá trị gần 0 nhất. Không suy ra thắng thống kê chỉ từ in đậm. Đối chứng tất định được chuyển sang xác suất 0/1 để chấm BS, nên MOS và khí hậu là tham chiếu xác suất quan trọng hơn. Các thí nghiệm độ trễ được trình bày riêng, không lẫn vào phép so đặc trưng.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · point_metrics.csv

## 35. Toàn bộ cấu hình: Bias đầu mean (mm) → 0

Bảng đủ năm đối chứng và sáu cấu hình LightGBM, hai GRU. Cùng tập mẫu dev 2024, macro theo trạm. In đậm giá trị tốt nhất trong bảng; Bias chọn giá trị gần 0 nhất. Không suy ra thắng thống kê chỉ từ in đậm. Đối chứng tất định được chuyển sang xác suất 0/1 để chấm BS, nên MOS và khí hậu là tham chiếu xác suất quan trọng hơn. Các thí nghiệm độ trễ được trình bày riêng, không lẫn vào phép so đặc trưng.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · point_metrics.csv

## 36. Toàn bộ cấu hình: BS cho mưa ≥1 mm ↓

Bảng đủ năm đối chứng và sáu cấu hình LightGBM, hai GRU. Cùng tập mẫu dev 2024, macro theo trạm. In đậm giá trị tốt nhất trong bảng; Bias chọn giá trị gần 0 nhất. Không suy ra thắng thống kê chỉ từ in đậm. Đối chứng tất định được chuyển sang xác suất 0/1 để chấm BS, nên MOS và khí hậu là tham chiếu xác suất quan trọng hơn. Các thí nghiệm độ trễ được trình bày riêng, không lẫn vào phép so đặc trưng.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · probability_metrics.csv

## 37. Toàn bộ cấu hình: BSS cho mưa ≥1 mm ↑

Bảng đủ năm đối chứng và sáu cấu hình LightGBM, hai GRU. Cùng tập mẫu dev 2024, macro theo trạm. In đậm giá trị tốt nhất trong bảng; Bias chọn giá trị gần 0 nhất. Không suy ra thắng thống kê chỉ từ in đậm. Đối chứng tất định được chuyển sang xác suất 0/1 để chấm BS, nên MOS và khí hậu là tham chiếu xác suất quan trọng hơn. Các thí nghiệm độ trễ được trình bày riêng, không lẫn vào phép so đặc trưng.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · probability_metrics.csv

## 38. Toàn bộ cấu hình: BS cho mưa ≥50 mm ↓

Bảng đủ năm đối chứng và sáu cấu hình LightGBM, hai GRU. Cùng tập mẫu dev 2024, macro theo trạm. In đậm giá trị tốt nhất trong bảng; Bias chọn giá trị gần 0 nhất. Không suy ra thắng thống kê chỉ từ in đậm. Đối chứng tất định được chuyển sang xác suất 0/1 để chấm BS, nên MOS và khí hậu là tham chiếu xác suất quan trọng hơn. Các thí nghiệm độ trễ được trình bày riêng, không lẫn vào phép so đặc trưng.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · probability_metrics.csv

## 39. Toàn bộ cấu hình: BSS cho mưa ≥50 mm ↑

Bảng đủ năm đối chứng và sáu cấu hình LightGBM, hai GRU. Cùng tập mẫu dev 2024, macro theo trạm. In đậm giá trị tốt nhất trong bảng; Bias chọn giá trị gần 0 nhất. Không suy ra thắng thống kê chỉ từ in đậm. Đối chứng tất định được chuyển sang xác suất 0/1 để chấm BS, nên MOS và khí hậu là tham chiếu xác suất quan trọng hơn. Các thí nghiệm độ trễ được trình bày riêng, không lẫn vào phép so đặc trưng.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · probability_metrics.csv

## 40. Cùng mô hình: đổi tau làm POD / FAR thay đổi

Chỉ sự kiện ≥50 mm/24h. Tau 0,5 được đặt cố định; tau chọn bằng 2023 được áp dụng nguyên trạng lên 2024. Cả hai phải báo cáo để cho thấy POD cao có thể do chính sách quyết định chứ không chỉ do xác suất tốt hơn. CSI cũng chưa mô tả hết chi phí thực tế của bỏ sót và báo nhầm; protocol hiện chưa tối ưu hàm chi phí vận hành. So ngưỡng cần cùng sự kiện và hạn dự báo.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · event_metrics.csv

## 41. Nguồn để kiểm tra lại phương pháp và con số

Số liệu trong slide lấy từ các CSV/JSON daily-v2 được lưu cùng báo cáo; build_manifest ghi SHA-256 và ánh xạ từng ô số về dòng nguồn. Cross-validation trong tài liệu scikit-learn giải thích vì sao test phải độc lập khỏi tuning. Gneiting giải thích ghép đại lượng dự báo với hàm mất mát. MET Appendix C định nghĩa các metric kiểm định. LightGBM 4.5.0 là tài liệu tham số phù hợp môi trường đã chạy. Tài liệu phương pháp không phải bằng chứng rằng dữ liệu dự án đã đạt độ tin cậy vận hành.

Bối cảnh: thí nghiệm hằng ngày tại 57 trạm; kết quả đang trình bày là phát triển trên 2024. Chưa có điểm kiểm định cuối 2025. Không dùng số liệu pilot lịch tuần để thay số liệu ở đây.

Nguồn: 57 trạm · Lịch hằng ngày · Dev 2024 · Chưa chấm 2025 · Tài liệu gốc · bản ghi kết quả dự án
