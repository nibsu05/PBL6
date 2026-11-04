# Lời dẫn báo cáo TFT vùng

24 slide chính (~25 phút) và 10 slide tra cứu. Có thể bỏ qua phụ lục khi trình bày, mở khi được hỏi.

## Slide 1: Đặc trưng nào giúp dự đoán mưa vùng?

Phần này nghiên cứu dữ liệu cho dự đoán trực tiếp lượng mưa trung bình vùng trong ba khoảng 24 giờ. Ba điều cần giữ: đã có đủ E0–E7; POD và FAR phải đọc cùng nhau; kết quả tích cực tập trung ở ngày 1, chưa chứng minh dự đoán tốt toàn bộ 72 giờ. Các slide phụ lục chứa đủ 48 dòng chính để kiểm tra. Đây là development, không phải kết quả test 2025.

## Slide 2: Đầu ra: ba tổng mưa 24 giờ riêng của cả vùng

Một lần phát hành lúc 07 giờ Việt Nam tạo ba số lượng mưa trung bình vùng. Ngày 1 là khoảng 0–24 giờ, ngày 2 là 24–48 giờ, ngày 3 là 48–72 giờ. Ví dụ 12, 35, 5 mm chỉ là minh họa. Không cộng 93 giá trị mm để làm nhãn vùng; lấy trung bình theo diện tích rồi cộng 24 giờ. Dự đoán một số trung bình vùng không suy ra tất cả xã hoặc ô đều nhận lượng mưa đó.

## Slide 3: Dữ liệu: ERA5 làm đầu vào, GSMaP Gauge làm nhãn

Đầu vào gồm khí tượng quá khứ từ ERA5 và đại lượng suy ra; lịch được tính từ timestamp. Nhãn là y_region_gc_mm từ GSMaP Gauge, tổng hợp theo diện tích các ô rồi cộng 24 giờ. Mưa ERA5 không phải nhãn trong nhánh ngày. Độ đầy đủ hoặc checksum không bảo đảm biến khí tượng hay nhãn vệ tinh chính xác về vật lý. Các biến SST/bối cảnh/chênh áp có hỗ trợ không gian riêng theo mã dựng nguồn, không phải mọi trường đều là 93 phép đo độc lập.

## Slide 4: Một mẫu TFT được tạo như thế nào?

Lấy 168 giờ khí tượng trước thời điểm phát hành, tính trung bình theo khối 6 giờ, thành 28 bước. Với F biến, tensor quá khứ có dạng N×28×F. Decoder chỉ nhận 12 bước lịch tương lai với 4 biến lịch; không nhận ERA5 ở giờ cần dự đoán. Đầu lượng mưa gồm 3 số, đầu sự kiện gồm 3 ngày nhân 3 ngưỡng. Mọi cấu hình dùng mask chung E7: đủ lịch sử và nhãn 72 giờ, không thay mẫu khi bớt biến.

## Slide 5: Bốn nhóm đặc trưng: cùng cột nguồn, khác vai trò

B gồm 7 trường bề mặt và 4 mã lịch. A gồm đối lưu, mây, lớp biên và ẩm đất. M gồm khí tượng trên cao và dòng ẩm. C chỉ có một biến nhiệt độ biển tại hộp biển. Các nhóm không lặp cột nhưng có thể tương quan vật lý và thống kê. A là tên quy ước: B/M cũng mô tả khí quyển. M chưa là một chỉ số gió mùa đã được kiểm định; C chưa là cả ENSO/MJO. Danh mục 44 biến ở phụ lục.

## Slide 6: E0–E7: giữ mô hình, thay tổ hợp đầu vào

Ba nhóm bổ sung A/M/C tạo 2 mũ 3 bằng tám tổ hợp. Mỗi E đã chạy trên ba fold phát triển và ba seed TFT, tổng 9 lượt TFT; LightGBM xác định có 3 pipeline. E0 là bộ biến nền, không phải tên một thuật toán. Tăng số biến cũng làm tăng tham số đầu vào TFT; giữ hidden/epoch không đồng nghĩa cùng số tham số. Factorial giúp đo từng tổ hợp trong pipeline, chưa chứng minh nhân quả vật lý.

## Slide 7: Vì sao thử TFT? Informer đã bị loại chưa?

TFT được chọn như một giả thuyết kiến trúc có lựa chọn biến/gating và dự đoán nhiều hạn. Bản vùng điều chỉnh dùng LSTM/attention và đầu Tweedie/BCE, chưa có static context hoặc phân vị. Informer thiết kế cho chuỗi dài; mã tác giả có time marks. Với encoder 28 bước, hiệu quả chuỗi cực dài chưa phải nút thắt rõ. Chưa có phép so cùng giao thức, vì vậy R² cũ hay benchmark khác không đủ kết luận Informer kém hoặc không khả thi. Nếu so kiến trúc, cần cùng input/target/ngân sách và chấp nhận mọi kết quả.

## Slide 8: LightGBM đối chứng: cùng nguyên liệu, khác cách học

LightGBM là thuật toán cây boosting được huấn luyện, không phải nguồn mưa khác. TFT thấy chuỗi 28 bước; cây thấy thống kê của cùng lịch sử: khối cuối, trung bình 24/72/168 giờ và thay đổi hai khối cuối, cộng lịch. Vì thế E0 có 87 cột bảng, E7 có 252 cột. So E0/E2 trong một họ đo đóng góp M; so TFT/LightGBM tại cùng E đo hai pipeline. Còn khác biểu diễn, loss và số seed, nên chưa phải chỉ thay một kiến trúc. Với vài nghìn nhãn ngày, đối chứng cây là phép đo cần thiết; không có định lý cây luôn thắng.

## Slide 9: LightGBM có cơ sở ứng dụng trong dự đoán mưa

R1 là nghiên cứu mưa ngày kế tiếp tại Cairns, trong đó LightGBM học thành phần dư của mô hình lai. R2 dùng LightGBM cho lượng mưa tại vùng núi Nhật Bản với forecast lân cận và quan trắc. R3 nghiên cứu dự đoán mùa, nên chỉ hỗ trợ bối cảnh phương pháp. Những bài này chứng minh thuật toán đã được dùng trong nghiên cứu giáng thủy, không chứng minh cấu hình của nhóm tốt ở Đà Nẵng. Không nhập điểm giữa các bài vì khác nhãn, hạn và không gian. Phân biệt cơ sở thuật toán A1 với cơ sở ứng dụng R1/R2.

## Slide 10: Nhánh dev có POD/FAR; có thực sự chọn model bằng nó?

Trong script LOCAL, hàm evaluate báo POD/FAR cho tổng 6 giờ đạt 10 mm cùng CSI/RMSE/MAE. Notebook Tweedie bổ sung chỉ số 1 giờ, 3/6 giờ và max giờ. Tuy nhiên early stopping của hai tệp được rà soát so RMSE phần tử trên đầu ra giờ; tên biến val_rmse_6h không tự làm nó thành RMSE tổng 6 giờ. evaluate xác suất trong notebook ghi BS và CSI_prob ở p>=0.5, dù docstring nhắc BSS. Do đó không đồng nhất bảng báo cáo POD/FAR với việc tối ưu POD/FAR, hoặc BS với BSS. Phạm vi audit là commit này, chưa xác nhận mã riêng chưa push của thành viên.

## Slide 11: Ba câu hỏi đánh giá cần ba nhóm chỉ số

Lượng mm, xác suất và quyết định là ba sản phẩm liên quan nhưng khác nhau. RMSE/MAE/Bias đo lượng. BS/BSS đánh giá xác suất với nhãn sự kiện 0/1. CSI/POD/FAR đo quyết định có/không sau khi chọn ngưỡng xác suất. BSS tốt không tự bảo đảm RMSE tốt; POD cao không bảo đảm ít báo nhầm. Tập dữ liệu ít sự kiện làm accuracy dễ bị ngày khô chi phối. Đầu lượng mưa và xác suất hiện không thuộc một phân phối duy nhất, nên không thay CSI của hai loại đầu ra cho nhau.

## Slide 12: Lượng mưa: vì sao cần cả RMSE, MAE và Bias?

Nhãn [0,10,40] mm và dự đoán [0,15,25] mm tạo lỗi [0,+5,-15] mm. MAE=(0+5+15)/3=6,67 mm. RMSE=sqrt((0+25+225)/3)=9,13 mm. Bias=(0+5-15)/3=−3,33 mm. RMSE phạt lỗi 15 mm mạnh, MAE mô tả trung bình trị tuyệt đối và Bias chỉ ra xu hướng thiếu. Bias có thể triệt tiêu khi có lỗi dương/âm, vì vậy gần 0 chưa bảo đảm tốt. Đây là tổng mưa 24 giờ trung bình vùng, không so trực tiếp với RMSE giờ hoặc tại điểm.

## Slide 13: Xác suất: BSS so với khí hậu, không phải accuracy

Với o=1 khi mưa đạt ngưỡng và o=0 khi không, Brier score là trung bình (p-o)^2. Nếu sự kiện xảy ra, dự báo 0,8 có lỗi 0,04, dự báo 0,2 có lỗi 0,64. BSS=1-BS_model/BS_ref. Ví dụ BS_model=0,06 và BS_ref=0,08 thì BSS=0,25, tương đương giảm 25% lỗi Brier so tham chiếu, không phải 25% ngày đúng. Khí hậu trong dự án học từ train theo tháng/lead. BSS có thể âm; nó không đo sai số mm và không cần ngưỡng quyết định tau. Reliability là chẩn đoán bổ sung, không thay BSS.

## Slide 14: POD, FAR, CSI: cùng xuất phát từ bảng đếm

Ví dụ 100 ngày có 10 ngày đạt ngưỡng. Báo trúng 7, bỏ sót 3, báo nhầm 5 và đúng không sự kiện 85. POD=7/(7+3)=0.700. FAR=5/(7+5)=0.417. CSI=7/(7+3+5)=0.467. FAR chia cho tổng lần báo có, khác false positive rate chia cho tổng ngày không sự kiện. Không báo lần nào thì FAR không xác định, không tự điền 0. Nếu luôn báo khô, accuracy đạt 90% nhưng không bắt được một sự kiện nào.

## Slide 15: POD cao hơn có đủ để kết luận tốt hơn?

Đây là E7 ngày 1 thật, cùng 1075 mốc và 114 sự kiện. TFT bắt được 73, bỏ sót 41 và báo nhầm 66. LightGBM bắt được 60, bỏ sót 54 và báo nhầm 32. TFT bắt thêm 13 sự kiện nhưng có thêm 34 báo nhầm. Không nói mô hình nào tốt hơn chỉ từ một chỉ số. Ưu tiên bỏ sót hay báo nhầm cần mục tiêu sử dụng và chi phí rõ; chưa có yêu cầu đó để tự đặt POD tối thiểu. Các số đếm được tái tạo từ aggregate đầy đủ độ chính xác và kiểm tra khớp CSI, không dùng nhãn mới.

## Slide 16: Nên ưu tiên metrics thế nào trong nghiên cứu hiện tại?

Giao thức hiện có gia đình kiểm định chính cho BSS16 và báo CSI. Giữ giao thức để không đổi mục tiêu theo điểm đẹp. POD/FAR là chẩn đoán bắt buộc cạnh CSI; lượng mm phải xuất hiện rõ bằng RMSE/MAE/Bias vì đó là đầu ra nghiên cứu. Nếu bài báo xác định cải thiện lượng mm là câu hỏi chính, cần chốt tiêu chí định lượng trước holdout, không dùng BSS như bằng chứng duy nhất. Nếu mục tiêu là cảnh báo ít bỏ sót, đặt yêu cầu POD và đánh đổi FAR từ nhu cầu sử dụng, chọn ngưỡng trên calibration rồi khóa. Không có một thứ tự phổ quát chỉ do dự báo là ngắn hạn.

## Slide 17: Chia theo thời gian, cùng mẫu, giữ kín năm 2025

Train học scaler, mô hình và khí hậu. Calibration chọn epoch/iteration, hiệu chỉnh xác suất và ngưỡng, nên không phải một tập đánh giá độc lập. Evaluation của ba fold là 2021–2023 và đã được xem trong development. Có 1075 mốc mỗi lead, 114 sự kiện 16, 37 sự kiện 50, 15 sự kiện 100. Ba lead có ngày mưa trùng nhau, không cộng thành số đợt độc lập. Nếu đổi ranh/nhãn, phải chạy lại phần phát triển trước khóa thiết kế. Không lấy kết quả 2026 để chọn mô hình chấm 2025.

## Slide 18: Hai ngưỡng khác nhau: lượng mưa q và xác suất τ

Ngưỡng q=16/50/100 mm xác định nhãn sự kiện từ lượng mưa vùng. Ngưỡng tau xác định báo có từ xác suất. Calibration hiện chọn tau bằng CSI; các điểm POD/FAR trong bảng là ở những ngưỡng đó, không phải tại cùng POD hoặc cùng FAR giữa hai mô hình. Khi hạ tau, có thể bắt thêm sự kiện và thêm báo nhầm; FAR không nhất thiết đơn điệu trong mẫu hữu hạn. BS/BSS không cần tau. CSI từ đầu lượng mưa>=q là amount_CSI, khác CSI chính từ xác suất>=tau. Các ngưỡng mưa là giao thức nghiên cứu, không tự là cấp cảnh báo từng xã.

## Slide 19: BSS toàn ma trận: ngày 1 có ích, ngày 3 chưa vượt khí hậu

BSS=1-BS/BSref. Dương tốt hơn khí hậu, âm kém hơn; không phải accuracy. Bảng cho đủ E0–E7, ba ngày và hai mô hình, mỗi cột in đậm điểm tốt nhất ở độ chính xác hiển thị. Chữ đỏ đánh dấu BSS âm; điểm ít âm nhất vẫn kém khí hậu. TFT E2/E6 có điểm cao ngày 1, LightGBM E4 cao ngày 1; chưa có kiểm định mọi cặp để tuyên bố cấu hình thắng ngoài mẫu. Không trung bình các BSS năm để thay BSS pooled đã tính từ các dự đoán/reference ghép.

## Slide 20: E7: đọc POD, FAR, CSI và BSS cùng nhau

Mỗi hàng dùng cùng ngưỡng mưa 16, nhưng tau quyết định được chọn riêng trên calibration của từng fold/mô hình. Bảng in đậm điểm tốt hơn giữa TFT và LightGBM cùng ngày ở độ chính xác hiển thị; chưa là kiểm định khác biệt giữa hai mô hình. Biểu đồ dùng success ratio=1-FAR trên trục ngang, POD trên trục dọc và đường CSI. Đây là performance diagram, không phải ROC vì trục ngang không phải FPR. Điểm gộp đại diện các fold có tau riêng, không phải một ngưỡng xác suất toàn cục. Ngày 3 BSS âm dù POD vẫn khoảng 0,4–0,5, nên chỉ nhìn POD sẽ che lỗi xác suất.

## Slide 21: Lượng mm vẫn phải báo rõ: RMSE, MAE và Bias

RMSE phạt lỗi lớn; MAE là lỗi tuyệt đối trung bình; Bias âm là dự báo thiếu. Bảng E7 cho thấy LightGBM có RMSE/MAE ngày 1 thấp hơn, còn ngày 3 TFT RMSE thấp hơn nhưng MAE cao hơn. Chọn một chỉ số có thể dẫn đến nhận xét khác nhau; không nói thắng mọi mặt. Mỗi cột in đậm điểm tốt hơn cùng ngày, Bias theo trị tuyệt đối. BSS tốt hơn không tự suy ra RMSE tốt hơn. RMSE khoảng 20 mm là mức lỗi tổng hợp, không phải khoảng chắc chắn mọi ngày sai trong ±20 mm.

## Slide 22: Thêm A/M có tín hiệu xác suất ngày 1; SST chưa rõ

Gia đình chính gồm E1-E0, E2-E0, E3-E0 trên ba ngày, tổng 9 phép. CI 99,44% điều chỉnh theo Bonferroni cho từng phép. A ngày 1 delta khoảng 0.0853, CI [0.0022,0.1607]; M khoảng 0.1443, CI [0.0681,0.2329]; C chứa 0. Khối 14 ngày cho cùng phân loại. Bootstrap lấy chung trọng số cho nhãn, dự đoán và reference, điều kiện trên mô hình đã fit; không bao phủ mọi bất định nhãn, khởi tạo, ranh và lựa chọn mô hình. Chưa kiểm định trực tiếp M-A. Các năm development đã xem trước nên không thay holdout độc lập.

## Slide 23: Khả thi về tính toán; còn cổng dữ liệu và kiểm định

Ma trận 96 lượt hiện chạy khoảng27,9 phút trên 4060 Laptop 8 GB; đó là thời gian tiến trình, không phải mọi công việc nghiên cứu. Ưu tiên tiếp theo là ranh/trọng số vùng và kiểm chứng nhãn ngày, gồm các biến mã hóa/proxy cần xác nhận. Nếu dữ liệu thay đổi, chạy lại development liên quan rồi khóa. Ngày 3 có thể cần forecast thật hoặc cách học khác, nhưng ma trận hiện chưa cô lập nguyên nhân. Không lấy kết quả âm để kết luận toàn bộ bài toán 72 giờ không khả thi. Chưa cần thêm kiến trúc chỉ để chứng minh kiến trúc đó thua.

## Slide 24: Thông điệp có thể dùng khi báo cáo giảng viên

Có cơ sở ứng dụng LightGBM trong các bài nghiên cứu mưa, nhưng phép đo tại dự án mới quyết định giá trị. POD và FAR vẫn cần ở hạn ngày, luôn đọc cùng CSI, BSS và lượng mm; chưa có yêu cầu chi phí để ưu tiên riêng POD hoặc FAR. Đã chạy đủ E0–E7 và có tín hiệu A/M ngày 1; ngày 3 chưa vượt khí hậu. Phần tiếp theo là hoàn thiện định nghĩa vùng, nhãn, giao thức rồi holdout. Khi bị hỏi TFT sao chưa thắng LightGBM, trả lời mục tiêu nghiên cứu đặc trưng, không đặt trước thuật toán phải thắng.

## Slide 25: Ngày 1 · TFT ensemble 3 seed · đủ E0–E7

Bảng chứa đúng tám cấu hình và bảy chỉ số từ aggregate gốc. Đậm là điểm tốt nhất ở độ chính xác hiển thị trong cùng cột; RMSE/MAE/FAR lấy nhỏ nhất, Bias lấy gần 0 nhất, BSS/CSI/POD lấy lớn nhất. Đỏ là BSS âm; ít âm nhất vẫn kém khí hậu. Đây không phải kiểm định mọi cặp. TFT ensemble 3 seed, không phải trung bình metric 3 seed. Cùng 1075 mốc/114 sự kiện 16 cho mọi E. Lượng mưa có đơn vị mm/24h; chỉ số sự kiện không đơn vị.

## Slide 26: Ngày 1 · LightGBM xác định · đủ E0–E7

Bảng chứa đúng tám cấu hình và bảy chỉ số từ aggregate gốc. Đậm là điểm tốt nhất ở độ chính xác hiển thị trong cùng cột; RMSE/MAE/FAR lấy nhỏ nhất, Bias lấy gần 0 nhất, BSS/CSI/POD lấy lớn nhất. Đỏ là BSS âm; ít âm nhất vẫn kém khí hậu. Đây không phải kiểm định mọi cặp. TFT ensemble 3 seed, không phải trung bình metric 3 seed. Cùng 1075 mốc/114 sự kiện 16 cho mọi E. Lượng mưa có đơn vị mm/24h; chỉ số sự kiện không đơn vị.

## Slide 27: Ngày 2 · TFT ensemble 3 seed · đủ E0–E7

Bảng chứa đúng tám cấu hình và bảy chỉ số từ aggregate gốc. Đậm là điểm tốt nhất ở độ chính xác hiển thị trong cùng cột; RMSE/MAE/FAR lấy nhỏ nhất, Bias lấy gần 0 nhất, BSS/CSI/POD lấy lớn nhất. Đỏ là BSS âm; ít âm nhất vẫn kém khí hậu. Đây không phải kiểm định mọi cặp. TFT ensemble 3 seed, không phải trung bình metric 3 seed. Cùng 1075 mốc/114 sự kiện 16 cho mọi E. Lượng mưa có đơn vị mm/24h; chỉ số sự kiện không đơn vị.

## Slide 28: Ngày 2 · LightGBM xác định · đủ E0–E7

Bảng chứa đúng tám cấu hình và bảy chỉ số từ aggregate gốc. Đậm là điểm tốt nhất ở độ chính xác hiển thị trong cùng cột; RMSE/MAE/FAR lấy nhỏ nhất, Bias lấy gần 0 nhất, BSS/CSI/POD lấy lớn nhất. Đỏ là BSS âm; ít âm nhất vẫn kém khí hậu. Đây không phải kiểm định mọi cặp. TFT ensemble 3 seed, không phải trung bình metric 3 seed. Cùng 1075 mốc/114 sự kiện 16 cho mọi E. Lượng mưa có đơn vị mm/24h; chỉ số sự kiện không đơn vị.

## Slide 29: Ngày 3 · TFT ensemble 3 seed · đủ E0–E7

Bảng chứa đúng tám cấu hình và bảy chỉ số từ aggregate gốc. Đậm là điểm tốt nhất ở độ chính xác hiển thị trong cùng cột; RMSE/MAE/FAR lấy nhỏ nhất, Bias lấy gần 0 nhất, BSS/CSI/POD lấy lớn nhất. Đỏ là BSS âm; ít âm nhất vẫn kém khí hậu. Đây không phải kiểm định mọi cặp. TFT ensemble 3 seed, không phải trung bình metric 3 seed. Cùng 1075 mốc/114 sự kiện 16 cho mọi E. Lượng mưa có đơn vị mm/24h; chỉ số sự kiện không đơn vị.

## Slide 30: Ngày 3 · LightGBM xác định · đủ E0–E7

Bảng chứa đúng tám cấu hình và bảy chỉ số từ aggregate gốc. Đậm là điểm tốt nhất ở độ chính xác hiển thị trong cùng cột; RMSE/MAE/FAR lấy nhỏ nhất, Bias lấy gần 0 nhất, BSS/CSI/POD lấy lớn nhất. Đỏ là BSS âm; ít âm nhất vẫn kém khí hậu. Đây không phải kiểm định mọi cặp. TFT ensemble 3 seed, không phải trung bình metric 3 seed. Cùng 1075 mốc/114 sự kiện 16 cho mọi E. Lượng mưa có đơn vị mm/24h; chỉ số sự kiện không đơn vị.

## Slide 31: Danh mục B và A: 23 biến

Tên biến giữ đúng theo feature_catalog.csv. Trường khí tượng V1 thường có tiền tố mean__; lịch không có tiền tố. Mỗi nhóm là danh mục cột, không độc lập thống kê. CIN NaNđược mã hóa 500 và has_lfc được dựng theo nguồn, cần audit vật lý; hữu hạn không tự bảo đảm đúng. Các trường context/SST/chênh áp có miền không gian riêng. Không suy ra93 quan trắc ERA5độc lập từ lưới đích0,1 độ.

## Slide 32: Danh mục M và C: 21 biến

Tên biến giữ đúng theo feature_catalog.csv. Trường khí tượng V1 thường có tiền tố mean__; lịch không có tiền tố. Mỗi nhóm là danh mục cột, không độc lập thống kê. CIN NaNđược mã hóa 500 và has_lfc được dựng theo nguồn, cần audit vật lý; hữu hạn không tự bảo đảm đúng. Các trường context/SST/chênh áp có miền không gian riêng. Không suy ra93 quan trắc ERA5độc lập từ lưới đích0,1 độ.

## Slide 33: Nguồn ứng dụng: LightGBM đã được dùng trong mưa

Ba nguồn sơ cấp được đối chiếu đến ngày 21/10/2026. R1 và R3được đọc qua phần công khai từ nhà xuất bản; không khẳng định đã audit full text phương pháp. R2 có trang bài báo và PDF chính thức. Không sao chép PDF hoặc điểm của paper vào repo. Đây là cơ sở chọn phép thử, không là bảo đảm kết quả cho Việt Nam.

## Slide 34: Nguồn thuật toán và kiểm chứng dự báo

A1 làpaper thuật toán LightGBM, A2 TFT, A3/A4 Informer. V1 làhướng dẫn kiểm chứng phân loại, V2 làkiểm chứng xác suất. Các nhận định áp dụng cho dữ liệu28 bước/vùng xấp xỉ là suy luận của dự án, không trích như kết luận bài gốc. Chi tiết lịch sử nhánh dev được đóng dấu bằng commit và SHA; không chấm lại mô hình hoặc mở 2025 trong lượt làm slide.