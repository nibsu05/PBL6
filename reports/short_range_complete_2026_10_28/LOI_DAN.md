# Lời dẫn: đủ ma trận ba mô hình

## Slide 1: Đặc trưng nào giúp dự đoán mưa vùng?

Đã hoàn thành 72 TFT, 24 pipeline LightGBM và 72 Informer. Informer gồm 18 lượt E0/E7 cũ giữ nguyên và 54 lượt E1–E6 mới, cùng giao thức. Tất cả vẫn là đánh giá phát triển trên footprint xấp xỉ; chưa mở test 2025.

## Slide 2: Đầu ra: ba tổng mưa 24 giờ riêng của cả vùng

Một lần phát hành lúc 07 giờ Việt Nam tạo ba số lượng mưa trung bình vùng. Ngày 1 là khoảng 0–24 giờ, ngày 2 là 24–48 giờ, ngày 3 là 48–72 giờ. Ví dụ 12, 35, 5 mm chỉ là minh họa. Không cộng 93 giá trị mm để làm nhãn vùng; lấy trung bình theo diện tích rồi cộng 24 giờ. Dự đoán một số trung bình vùng không suy ra tất cả xã hoặc ô đều nhận lượng mưa đó.

## Slide 3: Dữ liệu: ERA5 làm đầu vào, GSMaP Gauge làm nhãn

Đầu vào gồm khí tượng quá khứ từ ERA5 và đại lượng suy ra; lịch được tính từ timestamp. Nhãn là y_region_gc_mm từ GSMaP Gauge, tổng hợp theo diện tích các ô rồi cộng 24 giờ. Mưa ERA5 không phải nhãn trong nhánh ngày. Độ đầy đủ hoặc checksum không bảo đảm biến khí tượng hay nhãn vệ tinh chính xác về vật lý. Các biến SST/bối cảnh/chênh áp có hỗ trợ không gian riêng theo mã dựng nguồn, không phải mọi trường đều là 93 phép đo độc lập.

## Slide 4: Đầu vào của ba mô hình được tạo thế nào?

Lấy 168 giờ khí tượng trước thời điểm phát hành, tính trung bình theo khối 6 giờ, thành 28 bước. Với F biến, tensor quá khứ có dạng N×28×F. Decoder chỉ nhận 12 bước lịch tương lai với 4 biến lịch; không nhận ERA5 ở giờ cần dự đoán. Đầu lượng mưa gồm 3 số, đầu sự kiện gồm 3 ngày nhân 3 ngưỡng. Mọi cấu hình dùng mask chung E7: đủ lịch sử và nhãn 72 giờ, không thay mẫu khi bớt biến.
TFT và Informer dùng chuỗi 28 bước; LightGBM dùng các thống kê của cùng cửa sổ lịch sử. Cùng nguyên liệu không đồng nghĩa cùng biểu diễn hoặc chỉ khác kiến trúc.

## Slide 5: Bốn nhóm biến: bao gồm những thông tin gì?

Đọc B là thông tin nền gần mặt đất và lịch; A bổ sung điều kiện đối lưu/mây/lớp biên/đất; M bổ sung hoàn lưu và dòng ẩm trên cao; C bổ sung nhiệt độ biển. Đây là bảng mô tả đầy đủ theo yêu cầu, còn tên 44 cột ở phụ lục. A/M cũng có các thông tin liên quan độ ẩm nên không độc lập hoàn toàn; không lặp cột không có nghĩa không tương quan. SST hiện chỉ một biến vùng biển, chưa phải cả ENSO/MJO.

## Slide 6: Đã hoàn thành E0–E7 cho cả ba mô hình

Mỗi E có ba pipeline LightGBM xác định, chín TFT và chín Informer = ba năm nhân ba seed cho mỗi mạng. Đủ 168 lượt mô hình/pipeline; không có nghĩa số ngày thời tiết tăng theo seed. Độc lập phát lại đủ 72 checkpoint Informer, giữ nguyên 96 lượt TFT/LightGBM đã kiểm chứng.

## Slide 7: 3 seed = train cùng một cấu hình 3 lần

Một mạng neural bắt đầu từ các trọng số ngẫu nhiên, thứ tự lấy mẫu và các thao tác ngẫu nhiên trong huấn luyện. Seed là số đặt trạng thái ngẫu nhiên để quản lý các lần chạy. Seed42/43/44 là ba nhãn đã chọn trước, không phải năm dữ liệu hay ba tỉnh. Mỗi lần vẫn dùng cùng dữ liệu, nhóm biến và cấu hình. Chạy ba lần giúp kiểm tra kết quả có quá phụ thuộc một khởi tạo may mắn không. Ví dụ 9,12,15mm là minh họa cách trung bình dự đoán, không phải kết quả thật.
Cả TFT và Informer đều dùng seed 42/43/44. LightGBM hiện không bagging/feature sampling nên không nhân ba lượt xác định giống nhau.

## Slide 8: 3 ngày, 3 seed và 3 lượt chia thời gian khác nhau

Ba ngày là ba đầu ra của một mô hình tại một lần dự báo. Ba seed là ba lần huấn luyện cùng cấu hình. Ba lượt chia thời gian là ba đợt đánh giá trên các năm 2021/2022/2023, với tập huấn luyện và hiệu chỉnh riêng của từng đợt. Vì thế mỗi E có 3×3=9 lượt TFT, tám E có 72 lượt. LightGBM hiện chạy xác định nên có 3 lượt mỗi E. Thêm seed không nhân ba số ngày mưa độc lập.

## Slide 9: Vì sao cùng thử LightGBM, TFT và Informer?

LightGBM là đối chứng cây mạnh, TFT học trọng số biến và chuỗi, Informer là đối chứng attention. Đây là lý do chọn thử; kết quả thực nghiệm mới cho biết mô hình nào phù hợp. Không gọi TFT thắng hoặc Informer không khả thi chỉ từ tên kiến trúc.

## Slide 10: Cùng thông tin đầu vào, khác cách biểu diễn và học

Ba mô hình cùng nguồn khí tượng quá khứ, lịch, vùng, nhãn, mẫu và chia thời gian. TFT/Informer dùng chuỗi, LightGBM tóm tắt lịch sử thành bảng. Loss và cách học không hoàn toàn giống nhau; vì vậy đây là so ba pipeline, không cô lập riêng kiến trúc.

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

## Slide 19: POD cao hơn: ba mô hình đánh đổi ra sao?

E7 ngày 1 có 114 sự kiện và 961 ngày không có sự kiện. Cả ba dùng quyết định xác suất với ngưỡng chọn riêng trên calibration. TFT bắt nhiều nhất, LightGBM báo nhầm ít nhất, Informer nằm giữa về POD/FAR và có CSI cao nhất. Không phải so ở cùng mức FAR.

## Slide 20: Nên ưu tiên metrics thế nào trong nghiên cứu hiện tại?

Giao thức hiện có gia đình kiểm định chính cho BSS16 và báo CSI. Giữ giao thức để không đổi mục tiêu theo điểm đẹp. POD/FAR là chẩn đoán bắt buộc cạnh CSI; lượng mm phải xuất hiện rõ bằng RMSE/MAE/Bias vì đó là đầu ra nghiên cứu. Nếu bài báo xác định cải thiện lượng mm là câu hỏi chính, cần chốt tiêu chí định lượng trước holdout, không dùng BSS như bằng chứng duy nhất. Nếu mục tiêu là cảnh báo ít bỏ sót, đặt yêu cầu POD và đánh đổi FAR từ nhu cầu sử dụng, chọn ngưỡng trên calibration rồi khóa. Không có một thứ tự phổ quát chỉ do dự báo là ngắn hạn.

## Slide 21: Chia theo thời gian, cùng mẫu, giữ kín năm 2025

Train học scaler, mô hình và khí hậu. Calibration chọn epoch/iteration, hiệu chỉnh xác suất và ngưỡng, nên không phải một tập đánh giá độc lập. Evaluation của ba fold là 2021–2023 và đã được xem trong development. Có 1075 mốc mỗi lead, 114 sự kiện 16, 37 sự kiện 50, 15 sự kiện 100. Ba lead có ngày mưa trùng nhau, không cộng thành số đợt độc lập. Nếu đổi ranh/nhãn, phải chạy lại phần phát triển trước khóa thiết kế. Không lấy kết quả 2026 để chọn mô hình chấm 2025.

## Slide 22: Hai ngưỡng khác nhau: lượng mưa q và xác suất τ

Ngưỡng q=16/50/100 mm xác định nhãn sự kiện từ lượng mưa vùng. Ngưỡng tau xác định báo có từ xác suất. Calibration hiện chọn tau bằng CSI; các điểm POD/FAR trong bảng là ở những ngưỡng đó, không phải tại cùng POD hoặc cùng FAR giữa hai mô hình. Khi hạ tau, có thể bắt thêm sự kiện và thêm báo nhầm; FAR không nhất thiết đơn điệu trong mẫu hữu hạn. BS/BSS không cần tau. CSI từ đầu lượng mưa>=q là amount_CSI, khác CSI chính từ xác suất>=tau. Các ngưỡng mưa là giao thức nghiên cứu, không tự là cấp cảnh báo từng xã.

## Slide 23: Ví dụ TFT: hai quy tắc báo mưa cho POD khác nhau

Cùng dự đoán E7 ngày 1 và cùng 114 sự kiện. Nếu báo có khi lượng mm dự đoán ≥16, TFT trúng 67 và báo nhầm 48, POD 0,588. Nếu dùng đầu xác suất ≥tau đã chọn trên tập hiệu chỉnh, TFT trúng 73 và báo nhầm 66, POD 0,640. Con số 0,640 đúng với quy tắc thứ hai; chưa đồng nghĩa tốt hơn chỉ vì cao hơn. Đây là chẩn đoán bổ sung trên dự đoán đã có, không chọn lại ngưỡng từ tập đánh giá và không thay chỉ số chính.
Slide này minh họa hai quy tắc của cùng TFT, không xếp hạng mô hình. Phép so mô hình đặt đủ ba ở bảng E7 tiếp theo.

## Slide 24: Ngày 1: BSS của ba mô hình trên E0–E7

Mỗi hàng đặt đủ LightGBM/TFT/Informer trong cùng E/ngày. BSS dương hơn khí hậu, âm kém khí hậu. Đậm chỉ là điểm cao nhất trong hàng, không tự là ý nghĩa thống kê. Các khoảng tin cậy mới là mô tả phát triển, chưa kiểm định cuối hoặc hiệu chỉnh nhiều phép.

## Slide 25: Ngày 2: BSS của ba mô hình trên E0–E7

Mỗi hàng đặt đủ LightGBM/TFT/Informer trong cùng E/ngày. BSS dương hơn khí hậu, âm kém khí hậu. Đậm chỉ là điểm cao nhất trong hàng, không tự là ý nghĩa thống kê. Các khoảng tin cậy mới là mô tả phát triển, chưa kiểm định cuối hoặc hiệu chỉnh nhiều phép.

## Slide 26: Ngày 3: BSS của ba mô hình trên E0–E7

Mỗi hàng đặt đủ LightGBM/TFT/Informer trong cùng E/ngày. BSS dương hơn khí hậu, âm kém khí hậu. Đậm chỉ là điểm cao nhất trong hàng, không tự là ý nghĩa thống kê. Các khoảng tin cậy mới là mô tả phát triển, chưa kiểm định cuối hoặc hiệu chỉnh nhiều phép.

## Slide 27: E7 · ngày 1: so đồng thời đủ ba mô hình

Cùng 44 biến gốc, 1075 mẫu, ba năm đánh giá và nhãn mưa vùng; sự kiện từ 16 mm/24h. TFT/Informer trung bình ba seed; LightGBM xác định. Ngưỡng xác suất chọn trên calibration. Đậm là điểm tốt nhất ở độ chính xác hiển thị, không phải kết quả kiểm định.
LightGBM tốt hơn về RMSE, MAE, BSS và FAR. Informer có CSI cao nhất; TFT có POD cao nhất.

## Slide 28: E7 · ngày 2: so đồng thời đủ ba mô hình

Cùng 44 biến gốc, 1075 mẫu, ba năm đánh giá và nhãn mưa vùng; sự kiện từ 16 mm/24h. TFT/Informer trung bình ba seed; LightGBM xác định. Ngưỡng xác suất chọn trên calibration. Đậm là điểm tốt nhất ở độ chính xác hiển thị, không phải kết quả kiểm định.
LightGBM tốt hơn ở nhiều chỉ số; TFT có POD cao nhất. Mọi BSS đều dương nhưng chỉ còn khoảng 0,025–0,043.

## Slide 29: E7 · ngày 3: so đồng thời đủ ba mô hình

Cùng 44 biến gốc, 1075 mẫu, ba năm đánh giá và nhãn mưa vùng; sự kiện từ 16 mm/24h. TFT/Informer trung bình ba seed; LightGBM xác định. Ngưỡng xác suất chọn trên calibration. Đậm là điểm tốt nhất ở độ chính xác hiển thị, không phải kết quả kiểm định.
Cả ba BSS đều âm: chưa vượt khí hậu về xác suất. Một chỉ số tốt hơn không đủ để kết luận dự báo ngày 3 đã tốt.

## Slide 30: E7: BSS và khoảng tin cậy của cả ba mô hình

Mỗi ô là điểm BSS và CI95% từ lấy mẫu lại các đợt ngày trong từng năm. Khoảng hoàn toàn trên 0 hỗ trợ kỹ năng dương trong phân tích mô tả; chứa 0 chưa phân biệt rõ với khí hậu. Không dùng việc hai CI giao nhau để thay CI chênh lệch. Các CI chênh lệch theo cặp của ba mô hình được xuất riêng; chưa hiệu chỉnh nhiều phép hoặc bao trùm bất định nhãn/huấn luyện.

## Slide 31: Thêm riêng A/M/C: đối chiếu đủ ba mô hình

Mỗi ô là BSS khi thêm riêng một nhóm trừ BSS nền E0, cùng mô hình và ngày 1. A=E1, M=E2, C=E3. Đây là CI95% điểm của phân tích phát triển đã xem trước, không hiệu chỉnh nhiều phép. Phép thử TFT chính với gia đình chín CI đồng thời vẫn giữ nguyên ở slide sau. Không đồng nhất CI95% mới với CI99,44% chính.

## Slide 32: Trong TFT: nhóm nào có bằng chứng cải thiện?

Giữ nguyên phép thử TFT chính đã đăng ký: A/M ngày 1 có CI điều chỉnh gia đình chín phép trên 0, SST chưa có. Informer giờ đã đủ E1–E6; bảng ba mô hình bổ sung dùng CI95% mô tả, không thay phép thử TFT chính hoặc biến phân tích khám phá thành holdout.

## Slide 33: Khả thi tính toán; chưa hoàn thành nghiên cứu cuối

Đã bổ sung đủ 54 lượt Informer và dùng lại 18 lượt E0/E7. Có đủ ma trận ba mô hình nhưng chưa hoàn tất giao ranh, QC nhãn hoặc kiểm tra 1h/3h/6h. Các CI mới có điều kiện trên mô hình đã fit; không bao trùm toàn bộ bất định nhãn/huấn luyện. Chưa mở test 2025.

## Slide 34: Kết luận phải đặt trong bức tranh đủ ba mô hình

Giữ kết luận trung thực trên E7: LightGBM tốt hơn theo RMSE/BSS/FAR ngày 1, Informer CSI cao nhất, TFT POD cao nhất. Cả ba E7 ngày 3 BSS âm. Đã đủ E0–E7 của cả ba; xem ma trận để biết thêm biến có lợi ở đâu, không chọn mô hình chỉ từ một điểm đẹp hoặc kết luận vượt holdout.

## Slide 35: Nhánh dev có POD/FAR; có thực sự chọn model bằng nó?

Trong script LOCAL, hàm evaluate báo POD/FAR cho tổng 6 giờ đạt 10 mm cùng CSI/RMSE/MAE. Notebook Tweedie bổ sung chỉ số 1 giờ, 3/6 giờ và max giờ. Tuy nhiên early stopping của hai tệp được rà soát so RMSE phần tử trên đầu ra giờ; tên biến val_rmse_6h không tự làm nó thành RMSE tổng 6 giờ. evaluate xác suất trong notebook ghi BS và CSI_prob ở p>=0.5, dù docstring nhắc BSS. Do đó không đồng nhất bảng báo cáo POD/FAR với việc tối ưu POD/FAR, hoặc BS với BSS. Phạm vi audit là commit này, chưa xác nhận mã riêng chưa push của thành viên.

## Slide 36: Ngày 1 · E0–E2 · ba mô hình cùng bảng

Bảng đủ LightGBM/TFT/Informer cho từng E/ngày. Đậm xét trong cùng E và độ chính xác hiển thị; Bias gần 0 tốt hơn, các metric khác theo mũi tên. Không có ô Informer thiếu. Toàn năm ở bảng này, chi tiết mùa/năm/ngưỡng trong Excel/CSV. Đậm chưa chứng minh khác biệt có ý nghĩa thống kê.

## Slide 37: Ngày 1 · E3–E5 · ba mô hình cùng bảng

Bảng đủ LightGBM/TFT/Informer cho từng E/ngày. Đậm xét trong cùng E và độ chính xác hiển thị; Bias gần 0 tốt hơn, các metric khác theo mũi tên. Không có ô Informer thiếu. Toàn năm ở bảng này, chi tiết mùa/năm/ngưỡng trong Excel/CSV. Đậm chưa chứng minh khác biệt có ý nghĩa thống kê.

## Slide 38: Ngày 1 · E6–E7 · ba mô hình cùng bảng

Bảng đủ LightGBM/TFT/Informer cho từng E/ngày. Đậm xét trong cùng E và độ chính xác hiển thị; Bias gần 0 tốt hơn, các metric khác theo mũi tên. Không có ô Informer thiếu. Toàn năm ở bảng này, chi tiết mùa/năm/ngưỡng trong Excel/CSV. Đậm chưa chứng minh khác biệt có ý nghĩa thống kê.

## Slide 39: Ngày 2 · E0–E2 · ba mô hình cùng bảng

Bảng đủ LightGBM/TFT/Informer cho từng E/ngày. Đậm xét trong cùng E và độ chính xác hiển thị; Bias gần 0 tốt hơn, các metric khác theo mũi tên. Không có ô Informer thiếu. Toàn năm ở bảng này, chi tiết mùa/năm/ngưỡng trong Excel/CSV. Đậm chưa chứng minh khác biệt có ý nghĩa thống kê.

## Slide 40: Ngày 2 · E3–E5 · ba mô hình cùng bảng

Bảng đủ LightGBM/TFT/Informer cho từng E/ngày. Đậm xét trong cùng E và độ chính xác hiển thị; Bias gần 0 tốt hơn, các metric khác theo mũi tên. Không có ô Informer thiếu. Toàn năm ở bảng này, chi tiết mùa/năm/ngưỡng trong Excel/CSV. Đậm chưa chứng minh khác biệt có ý nghĩa thống kê.

## Slide 41: Ngày 2 · E6–E7 · ba mô hình cùng bảng

Bảng đủ LightGBM/TFT/Informer cho từng E/ngày. Đậm xét trong cùng E và độ chính xác hiển thị; Bias gần 0 tốt hơn, các metric khác theo mũi tên. Không có ô Informer thiếu. Toàn năm ở bảng này, chi tiết mùa/năm/ngưỡng trong Excel/CSV. Đậm chưa chứng minh khác biệt có ý nghĩa thống kê.

## Slide 42: Ngày 3 · E0–E2 · ba mô hình cùng bảng

Bảng đủ LightGBM/TFT/Informer cho từng E/ngày. Đậm xét trong cùng E và độ chính xác hiển thị; Bias gần 0 tốt hơn, các metric khác theo mũi tên. Không có ô Informer thiếu. Toàn năm ở bảng này, chi tiết mùa/năm/ngưỡng trong Excel/CSV. Đậm chưa chứng minh khác biệt có ý nghĩa thống kê.

## Slide 43: Ngày 3 · E3–E5 · ba mô hình cùng bảng

Bảng đủ LightGBM/TFT/Informer cho từng E/ngày. Đậm xét trong cùng E và độ chính xác hiển thị; Bias gần 0 tốt hơn, các metric khác theo mũi tên. Không có ô Informer thiếu. Toàn năm ở bảng này, chi tiết mùa/năm/ngưỡng trong Excel/CSV. Đậm chưa chứng minh khác biệt có ý nghĩa thống kê.

## Slide 44: Ngày 3 · E6–E7 · ba mô hình cùng bảng

Bảng đủ LightGBM/TFT/Informer cho từng E/ngày. Đậm xét trong cùng E và độ chính xác hiển thị; Bias gần 0 tốt hơn, các metric khác theo mũi tên. Không có ô Informer thiếu. Toàn năm ở bảng này, chi tiết mùa/năm/ngưỡng trong Excel/CSV. Đậm chưa chứng minh khác biệt có ý nghĩa thống kê.

## Slide 45: Danh mục B và A: 23 biến

Tên biến giữ đúng theo feature_catalog.csv. Trường khí tượng V1 thường có tiền tố mean__; lịch không có tiền tố. Mỗi nhóm là danh mục cột, không độc lập thống kê. CIN NaNđược mã hóa 500 và has_lfc được dựng theo nguồn, cần audit vật lý; hữu hạn không tự bảo đảm đúng. Các trường context/SST/chênh áp có miền không gian riêng. Không suy ra93 quan trắc ERA5độc lập từ lưới đích0,1 độ.

## Slide 46: Danh mục M và C: 21 biến

Tên biến giữ đúng theo feature_catalog.csv. Trường khí tượng V1 thường có tiền tố mean__; lịch không có tiền tố. Mỗi nhóm là danh mục cột, không độc lập thống kê. CIN NaNđược mã hóa 500 và has_lfc được dựng theo nguồn, cần audit vật lý; hữu hạn không tự bảo đảm đúng. Các trường context/SST/chênh áp có miền không gian riêng. Không suy ra93 quan trắc ERA5độc lập từ lưới đích0,1 độ.

## Slide 47: Nguồn ứng dụng: LightGBM đã được dùng trong mưa

Ba nguồn sơ cấp được đối chiếu đến ngày 21/10/2026. R1 và R3được đọc qua phần công khai từ nhà xuất bản; không khẳng định đã audit full text phương pháp. R2 có trang bài báo và PDF chính thức. Không sao chép PDF hoặc điểm của paper vào repo. Đây là cơ sở chọn phép thử, không là bảo đảm kết quả cho Việt Nam.

## Slide 48: Nguồn thuật toán và kiểm chứng dự báo

A1 làpaper thuật toán LightGBM, A2 TFT, A3/A4 Informer. V1 làhướng dẫn kiểm chứng phân loại, V2 làkiểm chứng xác suất. Các nhận định áp dụng cho dữ liệu28 bước/vùng xấp xỉ là suy luận của dự án, không trích như kết luận bài gốc. Chi tiết lịch sử nhánh dev được đóng dấu bằng commit và SHA; không chấm lại mô hình hoặc mở 2025 trong lượt làm slide.

## Slide 49: Nguồn kiểm chứng nhận định POD khoảng 0,4

Nguồn P1 là bài gốc trên nhà xuất bản và bản lưu tại KIT. Không sao chép PDF vào Git. Nguồn P2 là ước lượng, không phải dự báo, được ghi đúng giới hạn. V3 là hướng dẫn nhóm kiểm chứng dự báo, không áp chuẩn 0,4 chung. A5 là mã attention tác giả để đối chiếu công thức queries trong subclass pilot mới.
