# Lời dẫn bản sửa theo phản hồi

## Slide 1: Đặc trưng nào giúp dự đoán mưa vùng?

Bản này trình bày theo cách giải thích trong cuộc trao đổi: định nghĩa trước, ví dụ cụ thể rồi mới đọc kết quả. Có bảng nhóm biến và bảng metrics đầy đủ, giải thích 3 seed, kiểm chứng nhận định POD 0,4 và pilot Informer cùng dữ liệu. Các kết quả chính vẫn là tập phát triển 2021–2023; năm 2025 chưa mở.

## Slide 2: Đầu ra: ba tổng mưa 24 giờ riêng của cả vùng

Một lần phát hành lúc 07 giờ Việt Nam tạo ba số lượng mưa trung bình vùng. Ngày 1 là khoảng 0–24 giờ, ngày 2 là 24–48 giờ, ngày 3 là 48–72 giờ. Ví dụ 12, 35, 5 mm chỉ là minh họa. Không cộng 93 giá trị mm để làm nhãn vùng; lấy trung bình theo diện tích rồi cộng 24 giờ. Dự đoán một số trung bình vùng không suy ra tất cả xã hoặc ô đều nhận lượng mưa đó.

## Slide 3: Dữ liệu: ERA5 làm đầu vào, GSMaP Gauge làm nhãn

Đầu vào gồm khí tượng quá khứ từ ERA5 và đại lượng suy ra; lịch được tính từ timestamp. Nhãn là y_region_gc_mm từ GSMaP Gauge, tổng hợp theo diện tích các ô rồi cộng 24 giờ. Mưa ERA5 không phải nhãn trong nhánh ngày. Độ đầy đủ hoặc checksum không bảo đảm biến khí tượng hay nhãn vệ tinh chính xác về vật lý. Các biến SST/bối cảnh/chênh áp có hỗ trợ không gian riêng theo mã dựng nguồn, không phải mọi trường đều là 93 phép đo độc lập.

## Slide 4: Một mẫu TFT được tạo như thế nào?

Lấy 168 giờ khí tượng trước thời điểm phát hành, tính trung bình theo khối 6 giờ, thành 28 bước. Với F biến, tensor quá khứ có dạng N×28×F. Decoder chỉ nhận 12 bước lịch tương lai với 4 biến lịch; không nhận ERA5 ở giờ cần dự đoán. Đầu lượng mưa gồm 3 số, đầu sự kiện gồm 3 ngày nhân 3 ngưỡng. Mọi cấu hình dùng mask chung E7: đủ lịch sử và nhãn 72 giờ, không thay mẫu khi bớt biến.

## Slide 5: Bốn nhóm biến: bao gồm những thông tin gì?

Đọc B là thông tin nền gần mặt đất và lịch; A bổ sung điều kiện đối lưu/mây/lớp biên/đất; M bổ sung hoàn lưu và dòng ẩm trên cao; C bổ sung nhiệt độ biển. Đây là bảng mô tả đầy đủ theo yêu cầu, còn tên 44 cột ở phụ lục. A/M cũng có các thông tin liên quan độ ẩm nên không độc lập hoàn toàn; không lặp cột không có nghĩa không tương quan. SST hiện chỉ một biến vùng biển, chưa phải cả ENSO/MJO.

## Slide 6: E0–E7: giữ mô hình, thay tổ hợp đầu vào

Ba nhóm bổ sung A/M/C tạo 2 mũ 3 bằng tám tổ hợp. Mỗi E đã chạy trên ba fold phát triển và ba seed TFT, tổng 9 lượt TFT; LightGBM xác định có 3 pipeline. E0 là bộ biến nền, không phải tên một thuật toán. Tăng số biến cũng làm tăng tham số đầu vào TFT; giữ hidden/epoch không đồng nghĩa cùng số tham số. Factorial giúp đo từng tổ hợp trong pipeline, chưa chứng minh nhân quả vật lý.

## Slide 7: 3 seed = train cùng một cấu hình 3 lần

Một mạng neural bắt đầu từ các trọng số ngẫu nhiên, thứ tự lấy mẫu và các thao tác ngẫu nhiên trong huấn luyện. Seed là số đặt trạng thái ngẫu nhiên để quản lý các lần chạy. Seed42/43/44 là ba nhãn đã chọn trước, không phải năm dữ liệu hay ba tỉnh. Mỗi lần vẫn dùng cùng dữ liệu, nhóm biến và cấu hình. Chạy ba lần giúp kiểm tra kết quả có quá phụ thuộc một khởi tạo may mắn không. Ví dụ 9,12,15mm là minh họa cách trung bình dự đoán, không phải kết quả thật.

## Slide 8: 3 ngày, 3 seed và 3 lượt chia thời gian khác nhau

Ba ngày là ba đầu ra của một mô hình tại một lần dự báo. Ba seed là ba lần huấn luyện cùng cấu hình. Ba lượt chia thời gian là ba đợt đánh giá trên các năm 2021/2022/2023, với tập huấn luyện và hiệu chỉnh riêng của từng đợt. Vì thế mỗi E có 3×3=9 lượt TFT, tám E có 72 lượt. LightGBM hiện chạy xác định nên có 3 lượt mỗi E. Thêm seed không nhân ba số ngày mưa độc lập.

## Slide 9: Vì sao thử TFT? Informer đã bị loại chưa?

TFT được thử vì có thiết kế cho nhiều nhóm biến và nhiều hạn. Informer là mô hình attention tối ưu cho chuỗi dài. Lần này đã có pilot riêng E0/E7 trên cùng dữ liệu vùng, nhãn, lịch sử, đầu ra và cách chấm. Bản này vẫn là adaptation: giữ backbone ProbSparse/encoder-distilling/decoder, thêm đầu ngày Tweedie/BCE. Chưa phải tái lập toàn bộ paper hoặc tìm cấu hình tối ưu cho Informer. Không lấy R² từ dữ liệu điểm cũ để loại nó.

## Slide 10: LightGBM đối chứng: cùng nguyên liệu, khác cách học

LightGBM là thuật toán cây boosting được huấn luyện, không phải nguồn mưa khác. TFT thấy chuỗi 28 bước; cây thấy thống kê của cùng lịch sử: khối cuối, trung bình 24/72/168 giờ và thay đổi hai khối cuối, cộng lịch. Vì thế E0 có 87 cột bảng, E7 có 252 cột. So E0/E2 trong một họ đo đóng góp M; so TFT/LightGBM tại cùng E đo hai pipeline. Còn khác biểu diễn, loss và số seed, nên chưa phải chỉ thay một kiến trúc. Với vài nghìn nhãn ngày, đối chứng cây là phép đo cần thiết; không có định lý cây luôn thắng.

## Slide 11: LightGBM có cơ sở ứng dụng trong dự đoán mưa

R1 là nghiên cứu mưa ngày kế tiếp tại Cairns, trong đó LightGBM học thành phần dư của mô hình lai. R2 dùng LightGBM cho lượng mưa tại vùng núi Nhật Bản với forecast lân cận và quan trắc. R3 nghiên cứu dự đoán mùa, nên chỉ hỗ trợ bối cảnh phương pháp. Những bài này chứng minh thuật toán đã được dùng trong nghiên cứu giáng thủy, không chứng minh cấu hình của nhóm tốt ở Đà Nẵng. Không nhập điểm giữa các bài vì khác nhãn, hạn và không gian. Phân biệt cơ sở thuật toán A1 với cơ sở ứng dụng R1/R2.

## Slide 12: Ba câu hỏi đánh giá cần ba nhóm chỉ số

Lượng mm, xác suất và quyết định là ba sản phẩm liên quan nhưng khác nhau. RMSE/MAE/Bias đo lượng. BS/BSS đánh giá xác suất với nhãn sự kiện 0/1. CSI/POD/FAR đo quyết định có/không sau khi chọn ngưỡng xác suất. BSS tốt không tự bảo đảm RMSE tốt; POD cao không bảo đảm ít báo nhầm. Tập dữ liệu ít sự kiện làm accuracy dễ bị ngày khô chi phối. Đầu lượng mưa và xác suất hiện không thuộc một phân phối duy nhất, nên không thay CSI của hai loại đầu ra cho nhau.

## Slide 13: Bảng metrics: ý nghĩa, vì sao dùng và chiều tốt

Đọc từng hàng để biết con số đang đo lượng mưa, xác suất hay quyết định. RMSE/MAE/Bias có đơn vị mm/24h. BS là sai số xác suất, BSS là cải thiện BS so khí hậu. CSI/POD/FAR lấy từ số trúng, bỏ sót và báo nhầm. Không so các con số khác đơn vị với nhau. POD cao cần xem FAR; BSS cao chưa tự suy ra lượng mm tốt. Các ví dụ tính cụ thể ở các slide ngay sau.

## Slide 14: Lượng mưa: vì sao cần cả RMSE, MAE và Bias?

Nhãn [0,10,40] mm và dự đoán [0,15,25] mm tạo lỗi [0,+5,-15] mm. MAE=(0+5+15)/3=6,67 mm. RMSE=sqrt((0+25+225)/3)=9,13 mm. Bias=(0+5-15)/3=−3,33 mm. RMSE phạt lỗi 15 mm mạnh, MAE mô tả trung bình trị tuyệt đối và Bias chỉ ra xu hướng thiếu. Bias có thể triệt tiêu khi có lỗi dương/âm, vì vậy gần 0 chưa bảo đảm tốt. Đây là tổng mưa 24 giờ trung bình vùng, không so trực tiếp với RMSE giờ hoặc tại điểm.

## Slide 15: Xác suất: BSS so với khí hậu, không phải accuracy

Với o=1 khi mưa đạt ngưỡng và o=0 khi không, Brier score là trung bình (p-o)^2. Nếu sự kiện xảy ra, dự báo 0,8 có lỗi 0,04, dự báo 0,2 có lỗi 0,64. BSS=1-BS_model/BS_ref. Ví dụ BS_model=0,06 và BS_ref=0,08 thì BSS=0,25, tương đương giảm 25% lỗi Brier so tham chiếu, không phải 25% ngày đúng. Khí hậu trong dự án học từ train theo tháng/lead. BSS có thể âm; nó không đo sai số mm và không cần ngưỡng quyết định tau. Reliability là chẩn đoán bổ sung, không thay BSS.

## Slide 16: POD, FAR, CSI: cùng xuất phát từ bảng đếm

Ví dụ 100 ngày có 10 ngày đạt ngưỡng. Báo trúng 7, bỏ sót 3, báo nhầm 5 và đúng không sự kiện 85. POD=7/(7+3)=0.700. FAR=5/(7+5)=0.417. CSI=7/(7+3+5)=0.467. FAR chia cho tổng lần báo có, khác false positive rate chia cho tổng ngày không sự kiện. Không báo lần nào thì FAR không xác định, không tự điền 0. Nếu luôn báo khô, accuracy đạt 90% nhưng không bắt được một sự kiện nào.

## Slide 17: POD = 0,4 có tự động được coi là tốt không?

POD 0,4 nghĩa là bắt 40 trong 100 sự kiện thực. Ví dụ tự tạo 300 ngày có 100 sự kiện: A và B cùng trúng 40, bỏ sót 60 nhưng A báo nhầm 10 và B báo nhầm 160. Cùng POD 0,4 nhưng FAR và CSI rất khác. Vì vậy không có kết luận tốt chỉ từ số 0,4. Trong bài toán khó, mức này có thể hữu ích nếu hơn đối chứng và đáp ứng đánh đổi báo nhầm; cần ngữ cảnh trước khi kết luận.

## Slide 18: Paper có POD khoảng 0,4: phải đọc trong ngữ cảnh

P1 nghiên cứu IFS/WRF trên Việt Nam, phần 4.3 bàn ngưỡng 25 mm/24h. Có mô tả POD 0,3–0,4 trong bản đồ, nhưng cũng có trạm vùng R6 đạt 0,5–0,7. Không có phát biểu 0,4 là chuẩn chung. P2 là đánh giá ước lượng IMERG theo giờ, nơi POD tối đa 0,4 cùng FAR tối thiểu 0,6 được tác giả nhận xét phát hiện thấp. Dùng hai nguồn để kiểm tra cách diễn giải, không xếp hạng dự án tốt hơn hai bài. Ngưỡng, không gian, nhãn và quy tắc của dự án khác.

## Slide 19: POD cao hơn có đủ để kết luận tốt hơn?

Đây là E7 ngày 1 thật, cùng 1075 mốc và 114 sự kiện. TFT bắt được 73, bỏ sót 41 và báo nhầm 66. LightGBM bắt được 60, bỏ sót 54 và báo nhầm 32. TFT bắt thêm 13 sự kiện nhưng có thêm 34 báo nhầm. Không nói mô hình nào tốt hơn chỉ từ một chỉ số. Ưu tiên bỏ sót hay báo nhầm cần mục tiêu sử dụng và chi phí rõ; chưa có yêu cầu đó để tự đặt POD tối thiểu. Các số đếm được tái tạo từ aggregate đầy đủ độ chính xác và kiểm tra khớp CSI, không dùng nhãn mới.

## Slide 20: Nên ưu tiên metrics thế nào trong nghiên cứu hiện tại?

Giao thức hiện có gia đình kiểm định chính cho BSS16 và báo CSI. Giữ giao thức để không đổi mục tiêu theo điểm đẹp. POD/FAR là chẩn đoán bắt buộc cạnh CSI; lượng mm phải xuất hiện rõ bằng RMSE/MAE/Bias vì đó là đầu ra nghiên cứu. Nếu bài báo xác định cải thiện lượng mm là câu hỏi chính, cần chốt tiêu chí định lượng trước holdout, không dùng BSS như bằng chứng duy nhất. Nếu mục tiêu là cảnh báo ít bỏ sót, đặt yêu cầu POD và đánh đổi FAR từ nhu cầu sử dụng, chọn ngưỡng trên calibration rồi khóa. Không có một thứ tự phổ quát chỉ do dự báo là ngắn hạn.

## Slide 21: Chia theo thời gian, cùng mẫu, giữ kín năm 2025

Train học scaler, mô hình và khí hậu. Calibration chọn epoch/iteration, hiệu chỉnh xác suất và ngưỡng, nên không phải một tập đánh giá độc lập. Evaluation của ba fold là 2021–2023 và đã được xem trong development. Có 1075 mốc mỗi lead, 114 sự kiện 16, 37 sự kiện 50, 15 sự kiện 100. Ba lead có ngày mưa trùng nhau, không cộng thành số đợt độc lập. Nếu đổi ranh/nhãn, phải chạy lại phần phát triển trước khóa thiết kế. Không lấy kết quả 2026 để chọn mô hình chấm 2025.

## Slide 22: Hai ngưỡng khác nhau: lượng mưa q và xác suất τ

Ngưỡng q=16/50/100 mm xác định nhãn sự kiện từ lượng mưa vùng. Ngưỡng tau xác định báo có từ xác suất. Calibration hiện chọn tau bằng CSI; các điểm POD/FAR trong bảng là ở những ngưỡng đó, không phải tại cùng POD hoặc cùng FAR giữa hai mô hình. Khi hạ tau, có thể bắt thêm sự kiện và thêm báo nhầm; FAR không nhất thiết đơn điệu trong mẫu hữu hạn. BS/BSS không cần tau. CSI từ đầu lượng mưa>=q là amount_CSI, khác CSI chính từ xác suất>=tau. Các ngưỡng mưa là giao thức nghiên cứu, không tự là cấp cảnh báo từng xã.

## Slide 23: Vì sao POD trên slide lên 0,640? Hai cách báo khác nhau

Cùng dự đoán E7 ngày 1 và cùng 114 sự kiện. Nếu báo có khi lượng mm dự đoán ≥16, TFT trúng 67 và báo nhầm 48, POD 0,588. Nếu dùng đầu xác suất ≥tau đã chọn trên tập hiệu chỉnh, TFT trúng 73 và báo nhầm 66, POD 0,640. Con số 0,640 đúng với quy tắc thứ hai; chưa đồng nghĩa tốt hơn chỉ vì cao hơn. Đây là chẩn đoán bổ sung trên dự đoán đã có, không chọn lại ngưỡng từ tập đánh giá và không thay chỉ số chính.

## Slide 24: BSS toàn ma trận: ngày 1 có ích, ngày 3 chưa vượt khí hậu

BSS=1-BS/BSref. Dương tốt hơn khí hậu, âm kém hơn; không phải accuracy. Bảng cho đủ E0–E7, ba ngày và hai mô hình, mỗi cột in đậm điểm tốt nhất ở độ chính xác hiển thị. Chữ đỏ đánh dấu BSS âm; điểm ít âm nhất vẫn kém khí hậu. TFT E2/E6 có điểm cao ngày 1, LightGBM E4 cao ngày 1; chưa có kiểm định mọi cặp để tuyên bố cấu hình thắng ngoài mẫu. Không trung bình các BSS năm để thay BSS pooled đã tính từ các dự đoán/reference ghép.

## Slide 25: Đọc đủ POD, FAR, CSI và BSS: E7 ở ba ngày

POD cho tỷ lệ bắt được, FAR cho tỷ lệ báo nhầm trong các lần báo có; CSI tóm tắt ba số đếm; BSS đánh giá xác suất so khí hậu. Ngày 3 vẫn có POD 0,412 ở TFT nhưng FAR 0,719 và BSS âm. Đây là lý do không gọi dự báo tốt từ một POD riêng. Số in đậm là điểm tốt hơn trong cặp mô hình cùng ngày, chưa là kiểm định thống kê; các ngưỡng tau được chọn riêng trên tập hiệu chỉnh.

## Slide 26: Lượng mm vẫn phải báo rõ: RMSE, MAE và Bias

RMSE phạt lỗi lớn; MAE là lỗi tuyệt đối trung bình; Bias âm là dự báo thiếu. Bảng E7 cho thấy LightGBM có RMSE/MAE ngày 1 thấp hơn, còn ngày 3 TFT RMSE thấp hơn nhưng MAE cao hơn. Chọn một chỉ số có thể dẫn đến nhận xét khác nhau; không nói thắng mọi mặt. Mỗi cột in đậm điểm tốt hơn cùng ngày, Bias theo trị tuyệt đối. BSS tốt hơn không tự suy ra RMSE tốt hơn. RMSE khoảng 20 mm là mức lỗi tổng hợp, không phải khoảng chắc chắn mọi ngày sai trong ±20 mm.

## Slide 27: Informer: đã chạy được; kết quả pilot cần đọc thế nào?

Pilot đã khóa cấu hình trước khi huấn luyện, chỉ E0/E7, ba lượt chia 2021–2023 và cùng tập seed hoàn thành với TFT. Cùng dữ liệu vùng, nhãn, mẫu, lịch sử 168h gộp 6h, đầu ra ba tổng 24h, loss Tweedie/BCE, cách hiệu chỉnh và chọn ngưỡng. Informer là bản điều chỉnh gọn: hidden 32, heads 4, hai encoder có distilling và một decoder. Chưa tuning hoặc chạy E1–E6. Bảng là điểm phát triển; chưa kiểm định khác biệt kiến trúc từ các điểm này, không lấy R² cũ để kết luận.

## Slide 28: Nhóm nào cải thiện? Đọc điểm cùng khoảng tin cậy

Hiệu số ở đây là BSS khi thêm nhóm trừ BSS nền. Khoảng tin cậy cho thấy mức dao động hiệu số khi lấy mẫu lại các đợt ngày trên chính tập phát triển. Nếu toàn khoảng trên 0 thì phép thử ủng hộ cải thiện; nếu chứa 0 thì chưa phân biệt chắc. Hai nhóm A/M ngày 1 có khoảng điều chỉnh trên 0, SST chưa có. Chưa suy ra M chắc chắn hơn A vì chưa kiểm định trực tiếp; chưa suy ra đã thắng năm 2025.

## Slide 29: Khả thi về tính toán; còn cổng dữ liệu và kiểm định

Ma trận 96 lượt hiện chạy khoảng27,9 phút trên 4060 Laptop 8 GB; đó là thời gian tiến trình, không phải mọi công việc nghiên cứu. Ưu tiên tiếp theo là ranh/trọng số vùng và kiểm chứng nhãn ngày, gồm các biến mã hóa/proxy cần xác nhận. Nếu dữ liệu thay đổi, chạy lại development liên quan rồi khóa. Ngày 3 có thể cần forecast thật hoặc cách học khác, nhưng ma trận hiện chưa cô lập nguyên nhân. Không lấy kết quả âm để kết luận toàn bộ bài toán 72 giờ không khả thi. Chưa cần thêm kiến trúc chỉ để chứng minh kiến trúc đó thua.

## Slide 30: Thông điệp có thể dùng khi báo cáo giảng viên

Có cơ sở ứng dụng LightGBM trong các bài nghiên cứu mưa, nhưng phép đo tại dự án mới quyết định giá trị. POD và FAR vẫn cần ở hạn ngày, luôn đọc cùng CSI, BSS và lượng mm; chưa có yêu cầu chi phí để ưu tiên riêng POD hoặc FAR. Đã chạy đủ E0–E7 và có tín hiệu A/M ngày 1; ngày 3 chưa vượt khí hậu. Phần tiếp theo là hoàn thiện định nghĩa vùng, nhãn, giao thức rồi holdout. Khi bị hỏi TFT sao chưa thắng LightGBM, trả lời mục tiêu nghiên cứu đặc trưng, không đặt trước thuật toán phải thắng.

## Slide 31: Nhánh dev có POD/FAR; có thực sự chọn model bằng nó?

Trong script LOCAL, hàm evaluate báo POD/FAR cho tổng 6 giờ đạt 10 mm cùng CSI/RMSE/MAE. Notebook Tweedie bổ sung chỉ số 1 giờ, 3/6 giờ và max giờ. Tuy nhiên early stopping của hai tệp được rà soát so RMSE phần tử trên đầu ra giờ; tên biến val_rmse_6h không tự làm nó thành RMSE tổng 6 giờ. evaluate xác suất trong notebook ghi BS và CSI_prob ở p>=0.5, dù docstring nhắc BSS. Do đó không đồng nhất bảng báo cáo POD/FAR với việc tối ưu POD/FAR, hoặc BS với BSS. Phạm vi audit là commit này, chưa xác nhận mã riêng chưa push của thành viên.

## Slide 32: Ngày 1 · TFT ensemble 3 seed · đủ E0–E7

Bảng chứa đúng tám cấu hình và bảy chỉ số từ aggregate gốc. Đậm là điểm tốt nhất ở độ chính xác hiển thị trong cùng cột; RMSE/MAE/FAR lấy nhỏ nhất, Bias lấy gần 0 nhất, BSS/CSI/POD lấy lớn nhất. Đỏ là BSS âm; ít âm nhất vẫn kém khí hậu. Đây không phải kiểm định mọi cặp. TFT ensemble 3 seed, không phải trung bình metric 3 seed. Cùng 1075 mốc/114 sự kiện 16 cho mọi E. Lượng mưa có đơn vị mm/24h; chỉ số sự kiện không đơn vị.

## Slide 33: Ngày 1 · LightGBM xác định · đủ E0–E7

Bảng chứa đúng tám cấu hình và bảy chỉ số từ aggregate gốc. Đậm là điểm tốt nhất ở độ chính xác hiển thị trong cùng cột; RMSE/MAE/FAR lấy nhỏ nhất, Bias lấy gần 0 nhất, BSS/CSI/POD lấy lớn nhất. Đỏ là BSS âm; ít âm nhất vẫn kém khí hậu. Đây không phải kiểm định mọi cặp. TFT ensemble 3 seed, không phải trung bình metric 3 seed. Cùng 1075 mốc/114 sự kiện 16 cho mọi E. Lượng mưa có đơn vị mm/24h; chỉ số sự kiện không đơn vị.

## Slide 34: Ngày 2 · TFT ensemble 3 seed · đủ E0–E7

Bảng chứa đúng tám cấu hình và bảy chỉ số từ aggregate gốc. Đậm là điểm tốt nhất ở độ chính xác hiển thị trong cùng cột; RMSE/MAE/FAR lấy nhỏ nhất, Bias lấy gần 0 nhất, BSS/CSI/POD lấy lớn nhất. Đỏ là BSS âm; ít âm nhất vẫn kém khí hậu. Đây không phải kiểm định mọi cặp. TFT ensemble 3 seed, không phải trung bình metric 3 seed. Cùng 1075 mốc/114 sự kiện 16 cho mọi E. Lượng mưa có đơn vị mm/24h; chỉ số sự kiện không đơn vị.

## Slide 35: Ngày 2 · LightGBM xác định · đủ E0–E7

Bảng chứa đúng tám cấu hình và bảy chỉ số từ aggregate gốc. Đậm là điểm tốt nhất ở độ chính xác hiển thị trong cùng cột; RMSE/MAE/FAR lấy nhỏ nhất, Bias lấy gần 0 nhất, BSS/CSI/POD lấy lớn nhất. Đỏ là BSS âm; ít âm nhất vẫn kém khí hậu. Đây không phải kiểm định mọi cặp. TFT ensemble 3 seed, không phải trung bình metric 3 seed. Cùng 1075 mốc/114 sự kiện 16 cho mọi E. Lượng mưa có đơn vị mm/24h; chỉ số sự kiện không đơn vị.

## Slide 36: Ngày 3 · TFT ensemble 3 seed · đủ E0–E7

Bảng chứa đúng tám cấu hình và bảy chỉ số từ aggregate gốc. Đậm là điểm tốt nhất ở độ chính xác hiển thị trong cùng cột; RMSE/MAE/FAR lấy nhỏ nhất, Bias lấy gần 0 nhất, BSS/CSI/POD lấy lớn nhất. Đỏ là BSS âm; ít âm nhất vẫn kém khí hậu. Đây không phải kiểm định mọi cặp. TFT ensemble 3 seed, không phải trung bình metric 3 seed. Cùng 1075 mốc/114 sự kiện 16 cho mọi E. Lượng mưa có đơn vị mm/24h; chỉ số sự kiện không đơn vị.

## Slide 37: Ngày 3 · LightGBM xác định · đủ E0–E7

Bảng chứa đúng tám cấu hình và bảy chỉ số từ aggregate gốc. Đậm là điểm tốt nhất ở độ chính xác hiển thị trong cùng cột; RMSE/MAE/FAR lấy nhỏ nhất, Bias lấy gần 0 nhất, BSS/CSI/POD lấy lớn nhất. Đỏ là BSS âm; ít âm nhất vẫn kém khí hậu. Đây không phải kiểm định mọi cặp. TFT ensemble 3 seed, không phải trung bình metric 3 seed. Cùng 1075 mốc/114 sự kiện 16 cho mọi E. Lượng mưa có đơn vị mm/24h; chỉ số sự kiện không đơn vị.

## Slide 38: Danh mục B và A: 23 biến

Tên biến giữ đúng theo feature_catalog.csv. Trường khí tượng V1 thường có tiền tố mean__; lịch không có tiền tố. Mỗi nhóm là danh mục cột, không độc lập thống kê. CIN NaNđược mã hóa 500 và has_lfc được dựng theo nguồn, cần audit vật lý; hữu hạn không tự bảo đảm đúng. Các trường context/SST/chênh áp có miền không gian riêng. Không suy ra93 quan trắc ERA5độc lập từ lưới đích0,1 độ.

## Slide 39: Danh mục M và C: 21 biến

Tên biến giữ đúng theo feature_catalog.csv. Trường khí tượng V1 thường có tiền tố mean__; lịch không có tiền tố. Mỗi nhóm là danh mục cột, không độc lập thống kê. CIN NaNđược mã hóa 500 và has_lfc được dựng theo nguồn, cần audit vật lý; hữu hạn không tự bảo đảm đúng. Các trường context/SST/chênh áp có miền không gian riêng. Không suy ra93 quan trắc ERA5độc lập từ lưới đích0,1 độ.

## Slide 40: Nguồn ứng dụng: LightGBM đã được dùng trong mưa

Ba nguồn sơ cấp được đối chiếu đến ngày 21/10/2026. R1 và R3được đọc qua phần công khai từ nhà xuất bản; không khẳng định đã audit full text phương pháp. R2 có trang bài báo và PDF chính thức. Không sao chép PDF hoặc điểm của paper vào repo. Đây là cơ sở chọn phép thử, không là bảo đảm kết quả cho Việt Nam.

## Slide 41: Nguồn thuật toán và kiểm chứng dự báo

A1 làpaper thuật toán LightGBM, A2 TFT, A3/A4 Informer. V1 làhướng dẫn kiểm chứng phân loại, V2 làkiểm chứng xác suất. Các nhận định áp dụng cho dữ liệu28 bước/vùng xấp xỉ là suy luận của dự án, không trích như kết luận bài gốc. Chi tiết lịch sử nhánh dev được đóng dấu bằng commit và SHA; không chấm lại mô hình hoặc mở 2025 trong lượt làm slide.

## Slide 42: Nguồn kiểm chứng nhận định POD khoảng 0,4

Nguồn P1 là bài gốc trên nhà xuất bản và bản lưu tại KIT. Không sao chép PDF vào Git. Nguồn P2 là ước lượng, không phải dự báo, được ghi đúng giới hạn. V3 là hướng dẫn nhóm kiểm chứng dự báo, không áp chuẩn 0,4 chung. A5 là mã attention tác giả để đối chiếu công thức queries trong subclass pilot mới.