"""Vietnamese speaker notes, keyed to the frozen 57-station slide roles."""

NOTES = {
    'title': '''Báo cáo này giải thích thí nghiệm dự báo mưa tại 57 trạm bằng GFS kết hợp dữ liệu Vrain. Mục tiêu là ba tổng mưa 24 giờ riêng, không phải mưa trung bình toàn Đà Nẵng. Thí nghiệm đã chạy LightGBM và một mạng GRU nhỏ. Các bản TFT/Informer trước đây dùng bài toán hoặc nhãn khác nên không đưa điểm vào đây.

Đây là nghiên cứu hồi cứu, lấy mẫu thời điểm phát dự báo mỗi bảy ngày. Kết quả năm 2024 dùng cho phát triển; chưa phải kiểm định cuối hay chứng nhận vận hành. Các bảng lấy từ kết quả đã lưu, không huấn luyện thêm để làm slide.''',
    'map': '''Nên trình bày theo thứ tự: xác định dự báo cái gì; giải thích một mẫu gồm những gì; chia thời gian ra sao; mô hình học và dừng như thế nào; cuối cùng mới đọc bảng kết quả. Như vậy người nghe biết mỗi con số được tính trên đối tượng nào.

Phần chính có 43 slide, có thể chọn khoảng 25 slide khi chỉ có 20 phút. Phụ lục cung cấp tên biến, bảng đầy đủ, kiểm tra nguồn và câu trả lời khi bảo vệ. Không cần đọc hết thông số trên màn hình; ghi chú này dành cho người thuyết trình giải thích sâu hơn.''',
    'target': '''Tại 19 giờ ngày D, mô hình dự báo ba lượng: mưa từ 19 giờ D đến 19 giờ D+1; từ 19 giờ D+1 đến 19 giờ D+2; và từ 19 giờ D+2 đến 19 giờ D+3. Mỗi lượng có đơn vị mm trong 24 giờ. Ngày 3 không phải tổng mưa cộng dồn của cả 72 giờ.

Ngoài lượng mưa, mô hình xuất xác suất vượt 1 mm và 50 mm cho từng cửa sổ. Tổng cộng có ba lượng và sáu xác suất. Ngưỡng 50 mm hiện là ngưỡng thăm dò nghiên cứu, chưa gắn thành tiêu chuẩn cảnh báo chính thức.''',
    'stations': '''Danh mục tài khoản có 86 vị trí thuộc nhóm được đặt tên Đà Nẵng, không phải toàn Việt Nam. Trong đó 82 vị trí có alias ở kho lịch sử; bốn vị trí chỉ có ở danh mục hiện hành. Chưa biết bốn vị trí đó được lắp mới hay được bổ sung vào quyền truy cập.

Chọn 57 trạm chỉ bằng dữ liệu train 2021–2022: ít nhất 365 ngày có đủ tổng mưa và ít nhất 30 ngày mưa từ 1 mm. Thực tế có 479–728 ngày train hợp lệ. Hai trạm vẫn có dưới 30 mẫu theo lịch tuần, thấp nhất 18. Chưa chứng nhận mọi vị trí đều đã đối chiếu ranh hành chính cuối.''',
    'sources': '''Vrain cung cấp quan trắc mưa tại điểm đo: vừa làm nhãn tương lai, vừa làm lịch sử đầu vào. GFS là dự báo thời tiết số phát trước thời điểm cần dự báo; trường dự báo được lấy tại tọa độ trạm để làm predictor. DEM mô tả địa hình tĩnh và một số tương tác giả thuyết với gió.

Ba nguồn có vai trò khác nhau, không phải ba phép đo cùng loại. Bản thí nghiệm này không dùng mưa ERA5 hay mưa vệ tinh để tạo nhãn Vrain. Có dữ liệu ERA5 trong dự án không có nghĩa mọi mô hình hiện tại đều đang dùng ERA5.''',
    'sample': '''Một mẫu được xác định bởi cặp trạm và thời điểm phát dự báo. Ví dụ giả định ở đây cho một trạm: trước 19 giờ ta có lịch sử mưa, thông tin vị trí và dự báo GFS đã phát. Nhãn là ba tổng mưa trạm ở ba cửa sổ sau đó. Các số 18, 20 và 7 mm chỉ minh họa cách tổ chức, không phải dự báo hoặc số đo thật.

Mô hình học chung trên nhiều trạm; ID và tọa độ giúp phân biệt trạm. Một mẫu không phải một ô GFS, cũng không phải trung bình của 57 trạm. Trong bảng dạng dài, mẫu này được biểu diễn bằng ba dòng tương ứng ba hạn.''',
    'issue_time': '''Mọi giờ trên slide là giờ Việt Nam, UTC+7. GFS khởi tạo 00 UTC, tương ứng 07 giờ Việt Nam. Phát dự báo lúc 19 giờ, tức 12 giờ sau khởi tạo. Protocol giả định GFS có sau tám giờ, nên dành thêm bốn giờ đệm; chưa có bằng chứng phát hành gốc cho từng file lịch sử.

Quan trắc trạm được giả định trễ một giờ. Do đó lần phát 19 giờ chỉ được dùng số mưa kết thúc đến 18 giờ, không dùng ngay số đo mang mốc 19 giờ. Đây là điều kiện tránh dùng thông tin chưa có khi phát tin, cần kiểm tra độ nhạy với độ trễ thật.''',
    'labels': '''Người dùng đã xác nhận mốc 10:00 là lượng mưa 09:00–10:00 giờ Việt Nam. Vì thế, tổng ngày mục tiêu 19 giờ D đến 19 giờ D+1 được cộng từ 24 giá trị mang mốc kết thúc 20 giờ D, 21 giờ D, …, 19 giờ D+1.

Chỉ cộng khi đủ 24 giờ hợp lệ sau kiểm tra chất lượng. Thiếu một giờ không được coi là giờ khô và không được điền bằng 0. Nếu ngày mục tiêu thiếu, cửa sổ trạm–issue liên quan không đủ điều kiện. Đây là tổng từ quan trắc trạm theo giờ, không phải nội suy mưa ngày thành mưa giờ.''',
    'gfs_acc': '''GFS lưu mưa tích lũy từ đầu chu kỳ dự báo. Gọi C12, C36, C60, C84 là lượng tích lũy đến các hạn tương ứng. Lấy hiệu hai mốc liên tiếp để có ba cửa sổ 24 giờ: C36−C12, C60−C36 và C84−C60. Các khoảng này khớp ba cửa sổ 19–19 giờ sau lúc phát tin.

Ví dụ C12=10, C36=22, C60=37, C84=42 mm cho các predictor 12, 15 và 5 mm. Các số chỉ minh họa. Predictor là dự báo GFS, còn nhãn để học và chấm là tổng mưa Vrain; hai cột không được đánh đồng.''',
    'future': '''Có thể dùng thời tiết ở các hạn tương lai nếu đó là dự báo đã phát trước issue. Ví dụ trường gió GFS tại +72 giờ đã nằm trong bản chạy 00 UTC, nên có thể dùng ở lần phát 19 giờ hôm đó theo giả định khả dụng đã nêu.

Ngược lại, dùng quan trắc hoặc tái phân tích thực tế của ngày mai như một đầu vào đã biết sẽ làm bài toán hồi cứu dễ hơn điều kiện vận hành. Trong bản này, khí tượng GFS lấy ở +24, +48 và +72 giờ, tương ứng khoảng giữa ba cửa sổ mục tiêu; đây là ba trạng thái dự báo, không phải trung bình đầy đủ từng ngày.''',
    'rain_history': '''Hai nhánh lịch sử phục vụ hai mục đích. Bảy tổng ngày đầy đủ mô tả diễn biến mưa trong tuần trước. Ngày gần nhất của chuỗi kết thúc 19 giờ hôm trước, vì ngày kết thúc 19 giờ hôm nay chưa được xem là khả dụng tại issue. Các tổng 1, 6 và 24 giờ gần đây kết thúc 18 giờ hôm nay giúp bổ sung trạng thái mới hơn.

Các tổng có thể chồng thời gian; đó là biểu diễn được chọn trước, chưa chứng minh tối ưu. Cần giữ đúng lịch, không xóa ngày thiếu rồi nối những ngày không liên tiếp thành một chuỗi bảy ngày giả.''',
    'spatial': '''Vrain đo mưa tại điểm trạm, không mặc định đại diện một ô vuông xung quanh. GFS có lưới 0,25 độ; chương trình nội suy song tuyến từ bốn nút lân cận để lấy predictor tại tọa độ trạm. Hai trạm gần nhau có thể nhận dự báo rất giống nhau, nhưng vẫn có nhãn quan trắc riêng.

DEM Mapzen dùng tọa độ hiện có làm proxy địa hình, không phải cao độ khảo sát cảm biến. Trung bình và độ lệch chuẩn địa hình được lấy từ chín điểm trong ô ±5 km theo hai trục; không phải thống kê mọi pixel của một vòng tròn bán kính 5 km.''',
    'ablation': '''A0 là mưa GFS cộng mã hóa mùa và thông tin trạm, tổng sáu biến. A1 thêm bảy tổng mưa ngày quá khứ và ba tổng gần đây, thành 16 biến. A2 thêm chín biến khí tượng hoặc dẫn xuất, thành 25. A3 thêm bảy proxy địa hình và tương tác, thành 32.

Mọi cấu hình dùng cùng mẫu và cùng cách chia thời gian. Đây là thí nghiệm thêm nhóm tuần tự, không phải bảng E0–E7 đầy đủ của hướng cũ. Chênh A2−A1 là tác dụng thêm khí tượng khi đã có lịch sử; chưa tách được đóng góp độc lập hay mọi tương tác giữa các nhóm.''',
    'a2_inputs': '''LightGBM nhìn A2 như một vector 25 cột cho mỗi hạn. GRU nhận cùng thông tin nhưng tổ chức khác: bảy lượng mưa ngày thành chuỗi [7,1]; 17 biến còn lại cho từng hạn thành tensor [3,17]; ID trạm đi qua embedding riêng. Cộng 7+17+1 vẫn là 25 thông tin đầu vào theo hợp đồng A2.

17 biến ngữ cảnh không phải 17 biến thời tiết tương lai: còn có lịch, tọa độ và ba tổng mưa gần issue. Embedding có 86 vị trí mã vì dùng registry chung; chỉ 57 trạm được đưa vào lần train này. Không suy ra đã huấn luyện đủ 86 trạm.''',
    'split': '''Tất cả trạm dùng cùng ranh thời gian: train 2021–2022; cal 2023; dev 2024. Train học trọng số, scaler và khí hậu tham chiếu. Cal dùng chọn checkpoint, hiệu chỉnh xác suất và quyết định có chạy GRU theo điều kiện pilot. Dev dùng phân tích kết quả phát triển.

Không xáo trộn ngẫu nhiên các cửa sổ gần nhau sang các tập. Năm 2025 vẫn giữ kín, năm 2026 không dùng fit hoặc tuning. Vì 2024 đã được xem và phân tích, không gọi đó là test cuối độc lập. Cả 57 trạm đều có trong train/cal/dev: đây là dự báo tương lai tại trạm đã biết, chưa phải đánh giá trạm hoàn toàn mới.''',
    'counts': '''Có 5.032 mẫu trạm–issue train, 2.582 cal và 2.782 dev. Mỗi mẫu có ba hạn nên bảng dài có lần lượt 15.096, 7.746 và 8.346 dòng. Mỗi bộ LightGBM theo một hạn chỉ học 5.032 mẫu train; không được nói có 15.096 mẫu độc lập cho từng hạn.

Nguồn có 208 issue cách nhau bảy ngày từ 08/01/2021 đến 28/12/2024. Hai issue có nhãn vượt ranh tập bị loại; còn 205 issue có mẫu hợp lệ. Số dòng nhiều hơn số đợt thời tiết vì nhiều trạm cùng chịu một hệ thống mưa. Chưa chạy lịch phát hằng ngày đầy đủ.''',
    'qc': '''Một cửa sổ được dùng khi có đầy đủ lịch sử, cả ba nhãn tương lai và các predictor cần thiết. Dùng mask chung theo bộ đầy đủ để A0 không được lợi vì có thêm các hàng mà A3 phải loại. Đã loại 1.346 cửa sổ trạm–issue không đủ điều kiện.

Cả 72 giờ nhãn phải nằm trong một phần train/cal/dev; nếu đi qua ranh thì bỏ cả mẫu ba hạn. Lịch sử có thể nằm trước đầu tập vì đó là thông tin quá khứ đã biết tại issue. Trạm A thiếu không buộc loại trạm B còn đủ. QC cấu trúc chưa phải chứng nhận cảm biến không sai số.''',
    'baselines': '''Khí hậu dự báo theo tháng và trạm từ dữ liệu train; các trạm ít số được kéo về mức chung tháng bằng 20 quan trắc giả, không phải 20 trạm. Khí hậu học từ toàn bộ ngày train hợp lệ, nên dùng cùng giai đoạn nhưng nhiều ngày hơn lịch issue tuần của mô hình pilot.

Persistence lặp lại tổng 24 giờ khả dụng kết thúc 18 giờ. GFS gốc cho biết dự báo số trước hậu xử lý tốt đến đâu. LightGBM kiểm tra giá trị học từ vector đặc trưng; GRU kiểm tra thêm cách biểu diễn chuỗi. Không đặt trước mô hình nào bắt buộc thắng; các đối chứng trả lời những câu hỏi khác nhau.''',
    'lgb_io': '''Với A2, mỗi mẫu của một hạn là vector 25 biến và một lượng mưa thật. Mỗi hạn có một regressor dự báo mm và hai classifier dự báo sự kiện vượt 1 hoặc 50 mm. Mỗi estimator được học chung trên nhiều trạm, không train 57 bản riêng.

Ba hạn nhân ba loại đầu ra thành chín estimator cho một cấu hình và một seed. Bốn cấu hình, ba seed tạo 108 estimator chính: 36 lượng và 72 phân loại. station_code được khai báo là biến phân loại. Cây dùng các đại lượng theo đơn vị gốc, không fit StandardScaler như mạng GRU.''',
    'lgb_params': '''Các giá trị trên slide là bộ siêu tham số cố định cho pilot, chưa phải kết quả GridSearch hoặc Optuna. Cây bị giới hạn 15 lá, độ sâu 4, mỗi lá ít nhất 40 mẫu; L2=2 và lấy mẫu hàng/biến 0,9 giúp hạn chế độ phức tạp. Số 500 là trần số cây, không phải số cây cuối cùng.

Đầu lượng dùng hàm mất mát Tweedie với power 1,5, phù hợp biểu diễn lượng không âm có nhiều số 0 trong thiết lập này. Đầu sự kiện dùng binary logloss. Mỗi mẫu train có trọng số như nhau; chưa cân bằng trạm, tăng trọng số mưa lớn hay SMOTE.''',
    'lgb_earlystop': '''Đã đọc trực tiếp 36 checkpoint lượng để xác định tiêu chí dừng: thứ tự metric là l1 rồi Tweedie. Do first_metric_only=True, dừng sớm dựa trên MAE của cal 2023. Không được nhầm hàm loss tối ưu Tweedie với metric dùng chọn số cây.

Patience 40 nghĩa là dừng sau 40 vòng không cải thiện, rồi dự báo bằng best_iteration. Toàn bộ regressor chọn 62–177 cây; đã đánh giá 102–217 vòng nếu tính cả phần chờ. Bảng cho A2 ở ba seed. Classifier dùng binary logloss trên cal và patience 40. Không dùng MAE dev để chọn checkpoint.''',
    'calibration': '''Classifier có thể xếp hạng đúng nhưng xác suất chưa khớp tần suất thật. Phép Platt trong dự án biến đổi logit của xác suất thô bằng LogisticRegression một biến, học trên cal 2023. Tham số C=1, phạt L2, solver lbfgs, tối đa 500 vòng; xác suất được chặn trong [10⁻⁵,1−10⁻⁵] trước khi lấy logit.

Hiệu chỉnh riêng từng seed, hạn và ngưỡng, sau đó lấy trung bình ba xác suất. Báo có khi p≥0,5 là quy tắc quyết định khác, hiện cố định. Cùng cal đã dùng dừng sớm và hiệu chỉnh nên điểm xác suất cal không phải điểm ngoài mẫu độc lập. Không fit lại Platt trên dev.''',
    'gru_gate': '''Protocol chỉ cho chạy GRU khi có ít nhất một hạn mà A2 trên cal có MAE thấp hơn cả GFS lẫn khí hậu, đồng thời ít nhất 50% trạm tốt hơn GFS. Điều kiện này nhằm tránh mở rộng thử nghiệm mạng trước khi nhánh đầu vào cơ bản có tín hiệu.

Ở bản 57 trạm, chỉ ngày 3 qua đủ: A2=9,761 mm, GFS=10,048, khí hậu=13,162; 30/57 trạm tốt hơn GFS. Ngày 2 đạt chênh trung bình rất nhỏ nhưng chưa đủ tỷ lệ trạm. Đây là điều kiện pilot, không phải kiểm định thống kê. Quyết định chạy GRU không dựa vào dev 2024.''',
    'gru_shape': '''GRU đọc bảy tổng mưa ngày theo thứ tự thời gian và tạo vector 24 chiều. ID trạm tạo embedding bốn chiều. Với mỗi ngày đích, ghép vector 24 chiều, embedding bốn chiều và 17 biến ngữ cảnh thành 45 chiều; head riêng đi qua 32 nút rồi xuất ba số.

Ba số mỗi head là lượng mưa qua Softplus và hai logit sự kiện. Tổng mạng có 7.001 tham số, không phải mô hình lớn như TFT/Informer. Các trường dự báo tương lai đến từ bản GFS khởi tạo trước issue; không đọc nhãn tương lai. Mạng một chiều này cũng không phải Bi-LSTM của nhánh 1–6 giờ.''',
    'gru_train': '''Chỉ chuỗi mưa quá khứ được biến đổi log1p, sau đó chuẩn hóa. Các biến ngữ cảnh cũng chuẩn hóa bằng mean/std fit trên train. Nhãn lượng không lấy log1p: nhãn được chia cho max(mean mưa train,1), đầu ra được nhân trả scale về mm.

Loss chung gồm Tweedie power 1,5 cộng 0,5 lần binary cross-entropy cho các sự kiện. Softplus giữ dự báo lượng dương. Mạng học chung các nhiệm vụ, khác cách LightGBM fit riêng từng đầu; vì vậy khác biệt kết quả không thể quy hoàn toàn cho kiến trúc GRU. Chưa dùng trọng số mưa lớn hoặc cân bằng số mẫu giữa trạm.''',
    'gru_params': '''GRU dùng AdamW với learning rate 0,001, weight decay 0,001; batch 128, clip gradient ở 1 và dropout 0,1 trong head. Tối đa 80 epoch, patience 12, ngưỡng cải thiện nhỏ nhất 10⁻⁵. Chọn checkpoint bằng loss chung trên cal, khác MAE dùng cho LightGBM.

Ba seed chọn epoch 18, 18 và 20; vòng chạy dừng ở 30, 30 và 32 sau khi chờ patience. Đã chạy trên GPU RTX 4060 Laptop 8 GB và kiểm tra lại dự báo checkpoint trên CPU. Chưa tìm kiếm độ rộng, độ sâu mạng hoặc đổi loss weight sau khi xem dev.''',
    'tuning_status': '''Khi nói tinh chỉnh, cần nêu đúng những gì chương trình thực hiện. Đã chọn số cây và epoch bằng cal, hiệu chỉnh xác suất, và dùng điều kiện cal để mở thử nghiệm GRU. Cửa sổ, nhóm biến, learning rate, độ sâu và cấu trúc mạng vẫn cố định trong pilot.

Chưa có GridSearch, RandomSearch hoặc Optuna; chưa tuning trọng số loss, ngưỡng báo có, hay thử nhiều cửa sổ bằng các fold thời gian cuốn chiếu. Vì vậy không gọi cấu hình này là tối ưu. Giá trị của bản hiện tại là một mốc so sánh có thể kiểm tra lại để thiết kế thí nghiệm sau.''',
    'seeds': '''Seed điều khiển nguồn ngẫu nhiên: khởi tạo trọng số, thứ tự batch, dropout của mạng hoặc lấy mẫu hàng/biến của cây. Vì quá trình học khác nhau, cùng dữ liệu vẫn có thể cho dự báo hơi khác. Ba seed 17, 29 và 43 là ba lần học, không phải ba lần chia train/test.

Kết quả chính là trung bình dự báo ba seed, không chọn seed có điểm dev đẹp nhất. Xác suất từng seed được hiệu chỉnh trước khi gộp. Độ phân tán giữa seed chỉ phản ánh một phần bất ổn huấn luyện; không thay thế khoảng tin cậy theo các đợt thời tiết và không tạo ra ba năm độc lập.''',
    'amount_metrics': '''MAE là trung bình độ lệch tuyệt đối, nên đọc trực tiếp được sai số theo mm. RMSE bình phương sai số trước khi lấy trung bình rồi căn, vì vậy nhấn mạnh các lần sai lớn. Cần cả hai vì mô hình có MAE tốt chưa chắc giảm được lỗi lớn khi mưa mạnh.

Bias là dự báo trừ thực đo: âm là dự báo thiếu, dương là dự báo thừa. Bias gần 0 vẫn có thể do lỗi dương và âm bù nhau. Bản này tính từng chỉ số ở mỗi trạm rồi trung bình macro; các chỉ số không phải phần trăm độ chính xác.''',
    'prob_metrics': '''Với một ngưỡng, nhãn sự kiện là 0 hoặc 1. Brier Score, viết tắt BS, lấy trung bình (xác suất−nhãn)²; nhỏ hơn tốt hơn. BSS=1−BS mô hình/BS khí hậu tham chiếu. Ví dụ giả định BS khí hậu=0,10, mô hình=0,08 thì BSS=0,20: giảm 20% sai số Brier so với tham chiếu.

BSS âm nghĩa là xác suất dự báo kém hơn tham chiếu, không phải xác suất âm. Tính BSS riêng mỗi trạm rồi lấy macro, nên không được lấy hai cột BS macro chia nhau để suy ra BSS macro. Chỉ so khi cùng nhãn, ngưỡng, hạn và tham chiếu.''',
    'event_metrics': '''H là số báo trúng, M là số bỏ sót, F là số báo nhầm. POD=H/(H+M) cho biết bắt được bao nhiêu sự kiện thật. FAR=F/(H+F) cho biết trong các lần báo có, bao nhiêu lần nhầm; FAR khác tỷ lệ báo sai trên toàn bộ ngày không mưa. CSI=H/(H+M+F) xét đồng thời cả hai dạng lỗi.

Mô hình xác suất báo có ở p≥0,5; GFS dùng lượng dự báo vượt ngưỡng. Không có mốc POD tốt chung như 0,4 cho mọi bài toán. Nếu không lần nào báo có thì FAR không xác định, phải giữ thiếu và báo số trạm có thể tính.''',
    'macro_ci': '''Macro tính metric mỗi trạm rồi trung bình, giúp trạm nhiều số không lấn át trạm ít số khi đánh giá. Micro gộp mọi dòng nên trạm nhiều dữ liệu đóng góp nhiều hơn. Trong huấn luyện hiện chưa cân bằng trạm: mỗi mẫu vẫn có trọng số ngang nhau.

Để đánh giá chênh MAE, dùng bootstrap ghép cặp theo khối bốn issue, giữ các trạm cùng thời điểm trong cùng khối. Vì issue cách bảy ngày, một khối xấp xỉ bốn tuần. Có 1.000 lượt lấy lại mẫu. CI này có điều kiện trên mô hình đã fit, chưa bao quát toàn bộ sai số cảm biến hay bất định từ chọn thiết kế.''',
    'mae': '''Mọi hàng dùng cùng 57 trạm và 2.782 mẫu trạm–issue dev cho mỗi hạn. Số in đậm chỉ là MAE thấp nhất trong cột, chưa đồng nghĩa khác biệt có ý nghĩa thống kê. A3 tốt nhất ngày 1 ở mức điểm, A2 ngày 2, GRU ngày 3.

So với GFS, A2 có MAE thấp hơn ở cả ba hạn nhưng cần xem CI. Không lấy bảng trung bình 57 trạm so trực tiếp với bảng 20 trạm cũ để nói mở rộng tốt hơn, vì tập trạm có độ khó khác. Cũng chưa đưa TFT/Informer cũ vào bảng vì chưa chạy trên cùng bộ NWP57 và nhãn Vrain này.''',
    'tradeoff': '''Bảng giữ GFS, LightGBM A2 và GRU A2 cạnh nhau ở cả ba hạn để nhìn đánh đổi. Ngày 1–2, LightGBM A2 có MAE thấp hơn GRU. Ngày 3, GRU có MAE khoảng 8,00 và RMSE 17,62 mm, thấp hơn A2 ở mức điểm; nhưng phần xác suất cần đọc tiếp.

Bias A2 âm ở ngày 2–3 cho thấy xu hướng dự báo thiếu trung bình; GRU lại thừa mạnh hơn ngày 1. Không kết luận mô hình tốt toàn diện từ một ô in đậm. MAE, RMSE và Bias trả lời các câu hỏi khác nhau, và so sánh kiến trúc còn khác loss lẫn quy tắc dừng.''',
    'bss': '''Hai bảng dùng cùng mô hình nhưng sự kiện khác nhau: từ 1 mm và từ 50 mm trong 24 giờ. BSS lớn hơn tốt hơn; khí hậu có BSS=0 theo định nghĩa. Các ô âm đánh đỏ để thấy rõ khi mô hình thua tham chiếu.

Đáng chú ý, GRU ngày 3 có MAE tốt nhất nhưng BSS ở 50 mm khoảng −0,210, kém khí hậu. A2 ở ngưỡng này dương nhưng nhỏ trong ngày 2–3. Như vậy giảm sai số lượng chưa bảo đảm xác suất mưa lớn tốt hơn. GFS đơn trị không được gán một BSS xác suất giả trong thiết kế này.''',
    'event_wet': '''Ngưỡng ở bảng là mưa từ 1 mm trong từng cửa sổ 24 giờ. GFS có POD rất cao, khoảng 0,95–0,96, nhưng FAR cũng khoảng 0,51–0,59: bắt nhiều sự kiện đồng thời báo có quá nhiều. LightGBM A2 giảm POD nhưng thường giảm báo nhầm và tăng CSI.

Ví dụ ngày 2, A2 có CSI khoảng 0,561 so với GFS 0,456. GRU lại có FAR thấp hơn A2 ở ngày đó nhưng bỏ sót nhiều hơn. Đây là lý do không ưu tiên POD một mình. Ngưỡng p=0,5 hiện cố định; thay đổi nó sẽ đổi các chỉ số này và cần lựa chọn bằng cal.''',
    'event_heavy': '''Ngưỡng 50 mm/24 giờ chỉ là mức thăm dò. Dev có 94, 104 và 114 sự kiện trạm theo ba hạn, tập trung vào 11, 10 và 12 issue có ít nhất một trạm vượt ngưỡng. Các số này không phải số cơn mưa độc lập.

Cột N POD/FAR cho biết số trạm tính được từng chỉ số. Ví dụ A2 ngày 3 có FAR trên bảy trạm có báo có, còn POD trên 55 trạm có sự kiện thật; không được đọc FAR thấp như một thành tích toàn mạng nếu mô hình hầu như không báo. GRU ngày 3 có POD cao hơn nhưng BSS âm: kỹ năng quyết định tại một cutoff và chất lượng toàn bộ xác suất khác nhau.''',
    'ci': '''Dùng chênh MAE=A2−GFS: âm là A2 tốt hơn. Cả ba ước lượng điểm đều âm; ngày 3 giảm khoảng 1,867 mm, tương đương khoảng 18% MAE GFS ở mức điểm. Tuy nhiên, khoảng tin cậy 95% của cả ba hạn đều chứa 0.

Vì vậy câu kết luận phù hợp là có tín hiệu cải thiện trong pilot, chưa chứng minh mức cải thiện ổn định trên các đợt thời tiết. Không viết đã vượt GFS có ý nghĩa thống kê. CI chứa 0 cũng không chứng minh hai mô hình tương đương; dữ liệu có thể chưa đủ sức phân biệt.''',
    'feature_ci': '''Ba phép trừ tương ứng thêm lịch sử trạm A1−A0, thêm khí tượng A2−A1, thêm địa hình A3−A2. Chênh âm là cải thiện MAE. Đa số khoảng tin cậy chứa 0 nên chưa khẳng định nhóm đó hữu ích ổn định.

A2−A1 ngày 3 có CI âm trong kiểm tra hiện tại, nhưng đây là kết quả thăm dò qua nhiều so sánh, chưa hiệu chỉnh kiểm định nhiều lần. A3 thay đổi nhỏ và không đồng đều giữa hạn. Do thiết kế thêm tuần tự, hiệu ứng phụ thuộc nhóm đã có; cần thí nghiệm bỏ nhóm khỏi cấu hình đầy đủ và dữ liệu nhiều hơn để kết luận đóng góp riêng.''',
    'expand': '''Muốn biết thêm trạm có giúp không, phải chấm trên cùng 20 trạm và cùng issue của bản cũ. Đã kiểm tra nhãn, thời gian và 32 cột predictor khớp; ở dev có 983 mẫu mỗi hạn trong phép so ghép này.

A2 học trên 20 trạm có MAE 6,154/7,371/7,755; học trên 57 rồi chấm cùng 20 có 5,915/7,397/8,658 mm. Ngày 1 tốt hơn ở mức điểm, ngày 2 gần ngang, ngày 3 xấu hơn; CI cả ba chênh đều chứa 0. Mở rộng thay đổi cả tập train và cal nên không phải phép thử chỉ đổi train. Lợi ích chắc chắn hiện tại là mở phạm vi đánh giá, chưa bảo đảm tăng độ chính xác.''',
    'limits': '''Có bốn nhóm giới hạn cần nêu công khai: số năm và số issue còn ít; độ trễ thật của nguồn chưa được chứng minh; quan trắc/địa hình/tọa độ còn sai số; và chưa có test cuối năm 2025. Lịch tuần chưa thay thế được lịch phát dự báo hằng ngày.

Kiểm tra thêm lúc làm slide phát hiện hai xác suất học độc lập có thể vi phạm P(mưa≥50)≤P(mưa≥1). A2 có 188/8.346 dòng dev vi phạm, khoảng 2,25%; chưa có quyết định mâu thuẫn ở cutoff 0,5 trong mẫu này. Báo cáo giữ nguyên dự báo, nêu lỗi và đề xuất ràng buộc ở phiên bản mới, không sửa điểm âm thầm.''',
    'answers': '''Có thể khẳng định đã dựng dữ liệu theo hợp đồng thời gian, huấn luyện trên 57 trạm và kiểm tra lại checkpoint/metric. Không thể khẳng định thêm biến luôn tốt, GRU luôn hơn cây, hoặc đã cải thiện GFS ổn định.

Câu trả lời cân bằng là: LightGBM A2 có tín hiệu giảm MAE so với GFS; GRU đáng xem ở lượng ngày 3 nhưng còn yếu xác suất mưa lớn; địa hình chưa có lợi ích rõ. Tập 2024 vẫn là dev, chưa phải bằng chứng kiểm định cuối. Các giới hạn này là một phần kết quả nghiên cứu, không cần che bằng cách chỉ chọn ô đẹp.''',
    'next': '''Bước tiếp theo nên là một protocol mới, giữ nguyên bản pilot để đối chiếu. Trước hết xác minh độ trễ và ngữ nghĩa nguồn, bổ sung lịch issue hằng ngày và kiểm tra thiếu dữ liệu/mùa mưa. Sau đó thử độ dài lịch sử, bỏ nhóm biến, ngưỡng hoặc trọng số bằng các fold thời gian cuốn chiếu trong giai đoạn phát triển.

Cần xử lý thứ tự hai xác suất và kiểm tra lại calibration. Tách rõ mô hình tham chiếu với các cấu hình tìm kiếm, giới hạn ngân sách trước. Chỉ mở 2025 sau khi khóa lựa chọn, tiêu chí và mã đánh giá; năm 2026 không dùng để lén chọn mô hình tốt hơn.''',
    'catalog_base': '''Đây là tên cột thật trong mã dựng A0 và A1. A0 gồm một mưa GFS, hai mã hóa sin/cos ngày trong năm, hai tọa độ và một mã trạm. A1 thêm bảy lag mưa ngày và ba tổng 1/6/24 giờ gần đây. Tất cả lượng mưa có đơn vị mm trong đúng khoảng tương ứng.

Ngày lịch tương lai đã biết nên không phải rò rỉ nhãn. Danh sách feature phải được chỉ định rõ; không lấy mọi cột số của parquet làm X vì có cả nhãn, metadata hoặc cờ. Không nhầm danh sách này với full_features ERA5 của hướng vùng cũ.''',
    'catalog_physical': '''Nhiệt độ 850 hPa đổi từ Kelvin sang độ C; RH dùng phần trăm; gió dùng m/s; PWAT dùng kg/m². q850 được suy từ T/RH theo một công thức nhất quán vì đầu năm 2021 thiếu SPFH trong sản phẩm đang dùng. qflux là q nhân gió tại 850 hPa, không phải IVT tích phân toàn cột.

Năm biến DEM/gradient và hai biến tương tác bổ sung bảy cột. Mean/std địa hình là chín điểm lấy mẫu trong ô ±5 km theo hai trục. Tương tác gió với gradient là proxy có giả thuyết vật lý; bảng kết quả chưa chứng minh nó cải thiện mưa hay có quan hệ nhân quả.''',
    'all_rmse_bias': '''Phụ lục đưa đủ RMSE và Bias của tám phương pháp để người nghe không phải suy từ MAE. RMSE nhỏ hơn tốt hơn; Bias gần 0 hơn tốt hơn theo khía cạnh lệch trung bình. Số in đậm là tốt nhất trong cột ở mức điểm.

Khí hậu, persistence, GFS và các mô hình dùng cùng mẫu chấm dev. Đây là macro 57 trạm, không ghép với bảng 20 trạm hoặc mô hình vùng cũ. RMSE macro là trung bình RMSE trạm, khác căn sai số bình phương gộp mọi dòng. Bias gần 0 không bảo đảm lỗi từng ngày nhỏ.''',
    'full_prob_1': '''Hai bảng là BS và BSS cho sự kiện mưa từ 1 mm/24 giờ, đủ khí hậu và các cấu hình có đầu ra xác suất. BS nhỏ hơn tốt hơn, BSS lớn hơn tốt hơn. GFS và persistence trong bản này chỉ có đầu ra đơn trị nên không gán xác suất giả để tạo BSS.

Các kết quả đều là macro dev 2024. Tính BSS riêng từng trạm rồi trung bình; không lấy BS macro mô hình chia BS macro khí hậu để tái tạo BSS. Cấu hình tốt nhất BS và BSS có thể khác do cách tính theo trạm. Hiệu chỉnh xác suất chỉ fit trên cal, không trên dev.''',
    'full_prob_50': '''Đây là cùng cách tính nhưng sự kiện mưa từ 50 mm/24 giờ. Những BSS âm đánh đỏ cho thấy mô hình có sai số xác suất tệ hơn khí hậu tham chiếu ở ngưỡng/hạn tương ứng. BSS gần 0 là ít cải thiện so với cách dự báo tần suất theo mùa.

Do sự kiện hiếm, cần đọc kèm số trạm hỗ trợ, số issue có mưa lớn và khoảng bất định. BSS không phải POD: một mô hình có thể bắt được nhiều sự kiện tại cutoff 0,5 nhưng xác suất toàn bộ mẫu chưa tốt. Không kết luận GRU tốt toàn diện từ MAE ngày 3.''',
    'coherence': '''Về logic, sự kiện mưa từ 50 mm là tập con của mưa từ 1 mm, nên xác suất thứ nhất không được cao hơn xác suất thứ hai. Các classifier và phép Platt hiện học riêng, chưa ép thứ tự. Kiểm tra các dự báo lưu sẵn phát hiện A2 vi phạm ở 188/8.346 dòng dev, gap lớn nhất khoảng 0,087.

Không có quyết định mâu thuẫn tại p≥0,5 trong mẫu hiện tại. GRU không có vi phạm quan sát được nhưng mã cũng chưa ràng buộc, nên chưa bảo đảm tổng quát. Đây là kiểm tra bổ sung, không fit hoặc thay đổi dự báo. Việc sửa cần protocol mới và chấm lại đầy đủ.''',
    'release': '''Đã kiểm tra timestamp S3 của 3.952 message. Bảy chu kỳ đầu năm 2021 có Last-Modified sau issue; có thể do sao chép lại archive, không chứng minh dự báo gốc phát muộn. Không có trường hợp như vậy ở cal/dev.

Đã fit thêm A2 ba seed bỏ bảy chu kỳ train đó, giữ các thiết lập khác. MAE dev thay đổi từ 5,28/6,72/8,44 thành 5,37/6,76/8,34 mm, không thay thế kết quả chính. Đây là kiểm tra độ nhạy trước nguồn có timestamp không rõ. Giả định GFS khả dụng sau tám giờ vẫn cần bằng chứng vận hành gốc.''',
    'checks': '''Có 53 tests dữ liệu, thời gian và mô hình đã đạt trong lần triển khai trước. Đã kiểm tra lại 31.188 dòng dữ liệu; tải lại 57 message GRIB để đối chiếu 171 mẫu nội suy bốn nút; chạy lại dự báo từ 36 regressor, 72 classifier và ba checkpoint GRU, cùng kiểm tra scaler chỉ học train và các metric.

Các phép này chứng minh một phạm vi tái tạo và ghép dữ liệu đúng theo mã, không chứng nhận cảm biến, vị trí lịch sử hoặc độ trễ vận hành. Làm slide chỉ đọc kết quả đã có, không huấn luyện lại, tải thêm quan trắc hay mở 2025.''',
    'faq_data': '''Nếu hỏi 57 trạm hay 57 ô, trả lời là 57 điểm đo; predictor GFS có nguồn lưới rồi được nội suy tại điểm. Không có phép chia mặc định thành 57 ô đại diện diện tích. Nếu hỏi số mô hình, trả lời là học chung nhiều trạm, với các estimator hoặc head theo hạn và nhiệm vụ.

Đầu ra ngày không buộc mọi đầu vào cũng là trung bình ngày. Có thể dùng summary mưa giờ và dự báo khí tượng tại thời điểm đại diện nếu chúng khả dụng trước issue. Việc chọn biểu diễn phải được thử bằng thí nghiệm, chưa thể gọi cửa sổ hiện tại là tối ưu.''',
    'faq_models': '''Không bắt buộc TFT/Informer vì câu hỏi hiện tại là giá trị đầu vào và hậu xử lý GFS tại trạm. Chưa có kết quả của hai kiến trúc đó trên bộ NWP57; không lấy điểm cũ để kết luận chúng kém hoặc không khả thi. LightGBM là mô hình đối chiếu thực nghiệm, không có đặc quyền luôn phải thắng.

Khi hỏi đã tối ưu chưa, nói rõ mới cố định siêu tham số, chọn checkpoint và Platt bằng cal. POD 0,4 không có nghĩa tốt chung; phải xét ngưỡng, hạn và FAR/CSI. Năm 2024 đã dùng phát triển nên test cuối phải giữ độc lập sau khi khóa thiết kế.''',
    'references': '''Nguồn trực tiếp của các con số là bảng CSV, protocol, audit và checkpoint dự án. Tài liệu thuật toán giúp giải thích tham số LightGBM, cấu trúc GRU và hiện thực LogisticRegression; không thay thế bằng chứng dự báo tại khu vực nghiên cứu.

NOAA cung cấp dự báo GFS; Mapzen Terrain Tiles cung cấp proxy địa hình với thông tin ghi công nguồn. Bộ slide này không tuyên bố tái lập hoàn toàn ba bài báo trước đây, không so trực tiếp điểm giữa những bài toán khác nhãn/ngưỡng/hạn. Đường dẫn đầy đủ đặt trong ghi chú để người nghe có thể kiểm chứng.''',
    'files': '''Khi gửi nhóm, nên gửi PPTX cùng file ghi chú thuyết trình và đường dẫn các bảng tổng hợp. Người khác có thể xem protocol, tên biến, số mẫu và metric mà không phải đoán từ hình ảnh. Muốn tái tạo chính xác dự báo cần dữ liệu được cấp quyền và checkpoint riêng.

File công khai chỉ chứa cấu hình, mã và thống kê tổng hợp; không kèm mật khẩu, tọa độ trạm hay dự báo từng thời điểm. Bản PDF xuất riêng để đọc thuận tiện. Giữ nguyên bản pilot khi thiết kế thí nghiệm tiếp theo để việc so sánh giữa các phiên bản có thể kiểm tra lại.''',
}
