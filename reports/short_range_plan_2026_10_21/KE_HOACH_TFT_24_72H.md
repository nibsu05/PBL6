# Kế hoạch nghiên cứu dự đoán mưa vùng 24–72 giờ bằng TFT và LightGBM

Ngày 21/10/2026, giờ Việt Nam. **Người dùng đã duyệt kế hoạch và yêu cầu ưu tiên pilot trong 3–4 giờ; [pilot đã có kết quả](../short_range_pilot_2026_10_21/README.md).** Kế hoạch đầy đủ chưa hoàn tất. Người dùng phụ trách nhánh 24–72 giờ; thành viên khác làm Bi-LSTM 1–6 giờ. Hai nhánh cùng dự đoán vùng trực tiếp. Tài liệu bổ sung hạn ngày vào [phương án hợp nhất](../regional_research_plan_2026_10_20/PHUONG_AN_CUOI.md), không tự thay nhánh Bi-LSTM hoặc các quyết định có bằng chứng đã giữ.

**Cập nhật tiếp trong ngày:** đã hoàn thành [ma trận E0–E7 trên footprint 93 ô xấp xỉ](../short_range_ablation_2026_10_21/README.md): 72 lượt TFT, 24 pipeline LightGBM, 27 kiểm tra và 96/96 lượt replay cả calibration/evaluation. Ma trận chạy khoảng 27,9 phút. Hai trong chín CI chính đã hiệu chỉnh cho thấy thêm A hoặc M giúp TFT ngày 1; ngày 2–3/SST chưa có bằng chứng tương tự. Đây là development trên vùng đã mô tả đúng là xấp xỉ, chưa hoàn thiện giao ranh/kiểm chứng nhãn hoặc holdout 2025. Nếu thay dữ liệu phải chạy lại phần phát triển liên quan.

## 1. Phương án đề nghị duyệt

- Đầu ra: ba tổng mưa trung bình vùng, mỗi tổng tích lũy 24 giờ, kết thúc ở hạn 24/48/72 giờ; kèm xác suất vượt 16/50/100 mm trong từng khoảng.
- Vùng: cùng ranh, danh sách ô, trọng số và nguồn nhãn với nhánh Bi-LSTM. V1 hiện tại chỉ đủ gọi là footprint 93 ô xấp xỉ; cần giải quyết cách mô tả hoặc giao ranh trước thí nghiệm chính thức.
- Nghiên cứu chính: từ khí tượng ERA5 quá khứ trong V1, không nhận khí tượng ERA5 tại giờ đích. TFT vùng và LightGBM là hai họ mô hình. Khí hậu và luôn 0 là đối chứng tối thiểu.
- Ma trận: E0–E7 giữ các nhóm B/A/M/C đã thống nhất. Thử E0/E7 trước; sau kiểm tra kỹ thuật mới chạy đầy đủ ba fold và ba seed TFT.
- Informer, V2, mưa quá khứ, ECMWF forecast, phân vị và ứng dụng là các nhánh tùy chọn có điều kiện, không nằm trong ngân sách chính được đề nghị duyệt.
- Dự toán: **40–58 giờ công việc tập trung; cộng dự phòng 20% thành khoảng 48–70 giờ.** Với 5 giờ/ngày, tương đương **10–14 ngày làm việc**, thường 2–3 tuần lịch. Chạy GPU có thể xen kẽ thời gian viết/kiểm tra.
- GPU: RTX 4060 Laptop 8 GB đã được người dùng xác nhận và công cụ hệ thống kiểm chứng; CUDA khả dụng. Dự trù **8–30 giờ GPU trước pilot là ước tính lịch sử**, đã được thay bằng số đo trong bộ pilot: pipeline6TFT/6LightGBM chạy186,8giây. Thời gian nghiên cứu đầy đủ phải đọc cùng yêu cầu ranh/QC, không dùng ước tính GPU cũ như thời gian đã đo.
- Mốc kết quả đầu tiên đã đạt ngày 21/10 trong lượt triển khai hiện tại, gồm pilot và ma trận phát triển trên footprint xấp xỉ. Dự toán trước benchmark là baseline 3–4 ngày/TFT pilot 5–8 ngày không còn dùng làm dự báo thời gian của cấu hình này. Khung giờ công tổng vẫn là dự trù cho nghiên cứu gồm các cổng dữ liệu, kiểm định và bài viết, chưa phải số giờ đã làm.

## 2. Câu hỏi nghiên cứu và phạm vi kết luận

Câu hỏi chính: bổ sung nhóm nhiệt động/mây/đất, hoàn lưu/dòng ẩm và SST có cải thiện dự đoán mưa trung bình vùng ở ngày 1, ngày 2, ngày 3 hay không? Hiệu quả có lặp lại giữa các năm và các mùa không? TFT có thêm giá trị so với LightGBM khi nhận cùng nguyên liệu không?

Không đặt trước TFT phải thắng LightGBM, E7 phải thắng E0 hoặc Informer phải thất bại. Kết quả âm, nếu phép đo hợp lệ và tái lập, vẫn là kết quả nghiên cứu. Nhãn là sản phẩm GSMaP Gauge, không phải số đo mưa thật đầy đủ của cả vùng. Nghiên cứu hồi cứu từ ERA5 không chứng minh dữ liệu đến kịp để vận hành.

Hai hạn của nhóm phục vụ hai câu hỏi bổ sung. Không so RMSE mưa 6 giờ của Bi-LSTM với RMSE mưa 24 giờ của TFT để xếp hạng kiến trúc. Muốn so kiến trúc phải chạy cùng nhãn, hạn, mẫu và thông tin đầu vào.

## 3. Bằng chứng kiểm kê thực tế trước khi duyệt

Nguồn: `data/processed/regional_danang/v1_hourly.parquet`, dataset ID `regional-v1-v2-2026-10-20`, SHA-256 `92a6bc6a527b25107761e85f0d14e64713a39dfd2930560a4498927c27dfc448`. File có 102.984 dòng giờ và 53 cột: 49 predictor ứng viên, datetime và ba cột nhãn/QC. Ma trận chính chỉ dùng 44 predictor đã chọn.

Đã chạy lại `scripts/package_data.py verify` ngày 21/10: **2.233/2.233 tệp khớp, không thiếu, không sai**. Đây là kiểm tra toàn vẹn nguồn, không chứng minh độ chính xác nhãn. Máy thực tế có RTX 4060 Laptop 8 GB, RAM tổng hệ thống nhận diện khoảng 15,2 GiB, PyTorch 2.5.1+cu121, LightGBM 4.5.0; CUDA hoạt động. `pytorch-forecasting` và Lightning chưa được cài. Chưa thấy module TFT huấn luyện vùng trong repo.

Đã kiểm kê **78.888 dòng giờ của 2015–2023**, không đọc dòng 2025 để phân tích. Hash toàn file chỉ kiểm tra cơ học tính toàn vẹn. Lịch sử 168 giờ, mốc phát hành 00 UTC hằng ngày, nhãn 72 giờ đầy đủ và mask chung E7 cho **3.248 issue hợp lệ**. Các shape bên dưới là hợp đồng đề xuất; lượt kiểm kê chưa tạo loader huấn luyện.

| Fold phát triển | Train | Calibration | Evaluation | Số issue train/cal/eval hiện có |
| --- | --- | --- | --- | --- |
| F1 | 2015–2019 | 2020 | 2021 | 1.809 / 364 / 363 |
| F2 | 2015–2020 | 2021 | 2022 | 2.173 / 363 / 349 |
| F3 | 2015–2021 | 2022 | 2023 | 2.536 / 349 / 363 |

| Năm evaluation | Sự kiện ≥16 mm/ngày | ≥50 mm/ngày | ≥100 mm/ngày |
| --- | --- | --- | --- |
| 2021 | 33 | 15 | 6 |
| 2022 | 31 | 10 | 4 |
| 2023 | 50 | 12 | 5 |

Trong dữ liệu kiểm kê hiện tại, số sự kiện mỗi năm bằng nhau giữa ba lead do cùng cửa sổ ngày được dịch; không được cộng ba lead thành số sự kiện độc lập gấp ba. Năm 2022 mất 14 issue vì lịch sử có biến thiếu; nguyên nhân phải được ghi lại, không tùy tiện điền 0. Số mẫu và sự kiện phải tính lại nếu thay ranh, trọng số, mốc giờ hoặc quy tắc chất lượng. Xem [kiểm kê máy đọc được](preflight_development.json) và mã `scripts/inspect_short_range_plan.py`.

## 4. Định nghĩa dự báo và nhãn

Một issue t được đặt lúc **00:00 UTC = 07:00 giờ Việt Nam**, một lần mỗi ngày trong nghiên cứu chính. Đây là mốc giả định của nghiên cứu hồi cứu. Không có tuyên bố ERA5 hoặc Gauge đã có sẵn lúc 07:00 để vận hành.

| Đầu ra | Khoảng tích lũy | Cách tạo từ R(h) = y_region_gc_mm |
| --- | --- | --- |
| Y1, lead kết thúc 24 h | [t, t+24 h) | Tổng 24 lượng mưa giờ trong khoảng |
| Y2, lead kết thúc 48 h | [t+24 h, t+48 h) | Tổng 24 lượng mưa giờ trong khoảng |
| Y3, lead kết thúc 72 h | [t+48 h, t+72 h) | Tổng 24 lượng mưa giờ trong khoảng |

Đơn vị là mm/24 giờ, cùng hỗ trợ không gian vùng cho cả ba đầu. Ngày 2 không phải tổng 48 giờ; ngày 3 không phải tổng 72 giờ. Các khoảng tương ứng 07:00–07:00 giờ Việt Nam, không phải ngày lịch 00:00–24:00 địa phương. Không gọi đây là dự báo tại đúng một thời điểm t+24/t+48/t+72.

Lượng mưa vùng là trung bình theo diện tích, không cộng lượng mm của 93 ô. Tổng theo thời gian chỉ thực hiện sau khi đã có chuỗi mưa vùng theo giờ. Nếu chuyển từ trọng số toàn ô sang giao ranh, tạo lại đồng bộ X và y, dataset ID mới và áp dụng chung cho hai nhánh.

## 5. Đóng băng vùng và kiểm chứng nhãn

G0 phải ghi được danh sách ô, polygon/nguồn ranh nếu dùng, trọng số, diện tích phủ, ô biên và hash. Không mặc định tổng diện tích toàn ô khoảng 11.074 km² là diện tích địa giới chính xác của Đà Nẵng mới.

Có thể dựng loader và chạy thử kỹ thuật trên footprint 93 ô ngay. Trước ma trận chính, ưu tiên hoàn thiện giao ranh và kiểm tra có thiếu ô chạm biên. Nếu cần tải thêm ô, dự toán có thể tăng **2–5 ngày làm việc**, thậm chí hơn nếu nguồn truy cập khó. Nếu nhóm chấp nhận nghiên cứu trên footprint xấp xỉ, phải khóa và đặt tên đúng phạm vi đó trong báo cáo; không dùng kết quả để khẳng định đại diện toàn địa giới. Không âm thầm thay vùng giữa các E hoặc giữa hai mô hình.

Giữ quyết định dùng GSMaP Gauge permanent làm nhãn, IMERG kiểm tra độ bền và NOAA GSOD làm tham chiếu theo dữ liệu có. Tổng ngày giúp tránh phải xác nhận thời điểm mưa từng giờ mùa đông, nhưng không tự xác nhận nhãn ngày chính xác. Trạm là điểm, nhãn là vùng; không lấy RMSE trạm–trung bình vùng làm bằng chứng toàn vùng là đúng/sai.

Kiểm tra GSMaP–IMERG sau tổng hợp cùng vùng, cùng ngày, cùng khoảng giao; so tại vị trí trạm với dữ liệu trạm nếu đã xác minh giờ kết thúc tích lũy/cờ GSOD. Mốc 07:00–07:00 VN của thí nghiệm không mặc định trùng ngày GSOD. Nếu chưa xác minh EOD, ghi giới hạn và không công bố bảng kiểm chứng trạm không căn giờ. Không đổi nhãn giữa các mô hình để tìm bảng tốt hơn.

## 6. Đầu vào và xử lý thiếu

Giữ nguyên nhóm B/A/M/C từ [feature_groups.json](../regional_research_plan_2026_10_20/feature_groups.json): B=11, A=12, M=20, C=1. Tên khí tượng x ánh xạ sang mean__x; bốn biến lịch giữ tên. M là proxy hoàn lưu/dòng ẩm, C chỉ là SST vùng, không gọi là đã kiểm tra toàn bộ gió mùa, ENSO hoặc MJO.

Hợp đồng đề nghị:

- Lịch sử [t−168 h, t), chia thành 28 khối 6 giờ không chồng lấn; lấy trung bình mỗi cột trong khối. Gió đã có u/v, không trung bình góc hướng gió. Bốn cột sin/cos cũng được lấy trung bình sáu giờ theo cùng quy tắc.
- Encoder X có shape [batch, 28, F], E0 F=11 và E7 F=44. Gộp 6 giờ là lựa chọn giảm kích thước cần công bố, không phải tăng chất lượng hoặc độ phân giải dữ liệu.
- Decoder có 12 bước 6 giờ thuộc [t, t+72 h), chỉ nhận bốn biến lịch tính được từ timestamp theo đúng hàm lịch hiện có. Không đọc ERA5 thực tế tương lai. LightGBM có cùng thông tin lịch tương lai qua đặc trưng ngày/lead tương ứng.
- Nhãn Y có shape [batch, 3], mỗi phần tử là tổng 24 giờ theo mục 4. Cờ sự kiện có shape [batch, 3, 3] cho ba ngày và ba ngưỡng.
- Không đưa y_region_gc_mm, label_permanent, coverage, mưa ERA5, ONI cũ hoặc ba biến GSMaP raw vào đầu vào chính. Nhãn tương lai chỉ dùng tạo target/QC. Không đưa nhánh static hằng của một vùng vào rồi diễn giải là đóng góp địa hình.

Mask chung yêu cầu mọi biến E7 hữu hạn trong 168 giờ lịch sử và đủ 72 giờ nhãn không âm, permanent, đủ diện tích; sau đó mới lấy các tập con E0–E6. Đủ timestamp liên tục UTC, không trùng. Thiếu không được tự gán bằng 0, bfill từ tương lai hoặc đổi mẫu giữa các E. Kiểm tra rõ CIN capped/has_lfc và ý nghĩa trung bình 6 giờ của các cờ.

Scaler, chuẩn hóa loss, chọn biến và mọi thống kê học được chỉ fit trên train của fold. Cờ QC dùng để lọc mẫu, không làm predictor. Không đòi khí tượng tương lai đầy đủ để lọc mẫu của thí nghiệm chỉ dùng quá khứ.

## 7. Hai họ mô hình và loss

### 7.1. TFT vùng đề nghị

Khởi đầu hidden=32, một lớp LSTM, bốn đầu attention, dropout=0,1, batch=64, AdamW lr=0,001, weight_decay=0,0001, gradient clip=1. Tối đa 40 epoch, patience=6; seed 42/43/44. Đây là cấu hình lập kế hoạch, cần kiểm tra runtime và độ ổn định trước khi đóng băng.

TFT phải có các thành phần đối chiếu được với tài liệu gốc: GRN/gating, variable selection, encoder–decoder LSTM, attention có mask hợp lệ. Không gọi một LSTM gắn attention bất kỳ là TFT chuẩn. Nhánh static được bỏ/đặt context mặc định vì chỉ có một vùng; ghi rõ điều chỉnh.

Giữ backbone theo trục 6 giờ, lấy 12 trạng thái decoder, ghép bốn trạng thái liên tiếp cho mỗi ngày và dùng cùng một đầu đọc ngày cho ba khoảng. Đầu lượng mưa xuất ba giá trị Softplus theo mm/24h. Đầu sự kiện xuất chín logits tương ứng ba ngưỡng mỗi ngày. Không lấy tổng các phân vị mưa giờ làm phân vị ngày.

Loss chính: trung bình Tweedie deviance p=1,5 của ba tổng ngày, chuẩn hóa bằng null deviance tính từ train của từng lead, cộng BCE trung bình của chín sự kiện, hệ số BCE=1. Không tăng trọng số lớp dương trong thí nghiệm chính. Nếu train của một lead không có biến thiên/scale bằng 0 thì báo điều kiện không phù hợp, không chia cho 0.

Chọn epoch theo Brier score thô trung bình của ngưỡng 16 mm trên ba lead trong calibration, trước Platt; không chọn theo test hoặc điểm evaluation. Sau chọn epoch mới fit calibration xác suất theo mục 9. Điểm calibration không phải kết quả độc lập vì đã tham gia chọn epoch.

Triển khai đề nghị bằng PyTorch sẵn có, loader vùng riêng và đầu đọc ngày. Tham khảo cấu trúc từ [bài TFT](https://arxiv.org/abs/1912.09363) và [triển khai PyTorch Forecasting](https://pytorch-forecasting.readthedocs.io/en/stable/api/pytorch_forecasting.models.temporal_fusion_transformer.TemporalFusionTransformer.html). Không cài/đổi môi trường hiện tại trong lượt lập kế hoạch. Nếu dùng thư viện sau duyệt, khóa phiên bản tương thích và đo trên tập nhỏ. Nhận định cũ “thư viện chắc chắn không vừa RAM” không áp dụng mặc định cho một chuỗi vùng nhỏ; lựa chọn PyTorch trực tiếp ở đây nhằm khớp loader/đầu ngày và kiểm soát thay đổi, không phải kết luận thư viện bất khả thi.

### 7.2. LightGBM và đối chứng đơn giản

LightGBM nhận cùng lịch sử, các cột và mask. Đề nghị đặc trưng cho mỗi biến khí tượng: giá trị trung bình 6 giờ cuối, trung bình 24/72/168 giờ trước issue và chênh giữa hai khối 6 giờ cuối; bốn biến lịch hiện tại cộng lịch của lead đích. Không thêm nguyên liệu mà TFT không có. Tổng hợp thời gian khác nhau phải ghi rõ; phép so mô hình không cô lập hoàn toàn kiến trúc.

Mỗi pipeline E/fold có ba regressor Tweedie p=1,5 và chín classifier sự kiện. Cấu hình đầu: tối đa 400 cây, learning_rate=0,04, num_leaves=15, min_child_samples=30, không row/column sampling, deterministic, một seed. Calibration chọn iteration bằng deviance/Brier phù hợp từng đầu, early stopping=30. Không chạy ba cây deterministic giống nhau rồi coi đó là ba seed độc lập.

Đối chứng bắt buộc: lượng mưa luôn 0; lượng mưa khí hậu tháng của train; xác suất khí hậu ngưỡng theo tháng đích/lead từ train, làm trơn về tỷ lệ toàn train với 20 pseudo-observation. Các tháng thiếu train dùng tỷ lệ/giá trị toàn train. Khi một lớp không xuất hiện trong train, classifier trả xác suất hằng đã làm trơn và được đánh dấu, không để quá trình fit lỗi.

Persistence Gauge lặp tổng 24 giờ trước issue cho ba ngày có thể báo như **tham chiếu hồi cứu lý tưởng hóa**, vì nó nhận thông tin mưa mà E0–E7 chính không có. Không dùng nó để kết luận mô hình chính kém hơn trong cùng điều kiện đầu vào. Chưa triển khai mưa quá khứ làm predictor ở ma trận chính.

## 8. Ma trận thí nghiệm và giới hạn mở rộng

| ID | Nhóm | Số cột encoder |
| --- | --- | --- |
| E0 | B | 11 |
| E1 | B+A | 23 |
| E2 | B+M | 31 |
| E3 | B+C | 12 |
| E4 | B+A+M | 43 |
| E5 | B+A+C | 24 |
| E6 | B+M+C | 32 |
| E7 | B+A+M+C | 44 |

Pilot: F1, seed42, E0/E7, TFT và LightGBM. Tối đa hai lựa chọn hidden16/32 cho TFT, chỉ dùng train2015–2019/cal2020 để quyết định; không chọn từ eval2021–2023. Cấu hình và ngân sách được khóa trước ma trận chính. Nếu pilot chỉ chạy vài epoch để kiểm tra kỹ thuật, không đưa vào bảng chính; nếu chạy lại đủ protocol thì ghi run ID rõ ràng.

Ma trận phát triển: **8 E × 3 fold × 3 seed = 72 lượt TFT**; **8 E × 3 fold = 24 pipeline LightGBM**, tối đa 288 mô hình đầu ra cây. Một lượt TFT dự đoán cả ba lead, không nhân thêm ba lượt vì có ba ngày.

Kiểm tra cuối đề nghị cố định trước **E0 và E7**, giữ cả khi E7 không tốt trong development: train2015–2023/cal2024/test2025. Cần thêm 6 lượt TFT và 2 pipeline LightGBM (24 đầu cây). Tổng kế hoạch chính: **78 lượt TFT, 26 pipeline LightGBM, tối đa 312 đầu cây**, chưa tính các lượt kiểm tra/tinh chỉnh nhỏ. Không cần chọn E đẹp nhất sau khi xem 2025. Nếu muốn đưa E* khác vào holdout, đăng ký trước khi mở test và công bố quy tắc chọn từ development.

Ba phép so nhóm chính: E1−E0, E2−E0, E3−E0, theo từng lead. E4–E7 mô tả tương tác/tác dụng có điều kiện; không chỉ báo cấu hình tốt nhất. Không mặc định nhiều đặc trưng hơn luôn tốt hơn.

Informer chỉ thêm nếu giảng viên cần đối chứng kiến trúc hoặc có nguồn lực sau nhánh chính. Chạy cùng label/nguyên liệu/lead/split, ngân sách hợp lý; không dùng điểm Informer cũ để so với V1, không chạy để tạo sẵn kết luận thất bại. Dự trù riêng 4–8 giờ công và 1–4 giờ GPU cho một cấu hình × ba fold × ba seed sau khi loader chung đã ổn; đây cũng chưa phải runtime đo được.

## 9. Chia năm, hiệu chỉnh và niêm phong test

Dùng ba fold ở mục 3. Năm UTC của issue xác định split; bỏ issue có bất kỳ nhãn nào trong 72 giờ đi qua ranh năm. Lịch sử được nhìn lùi sang năm trước. Mọi mô hình dùng cùng issue hợp lệ; các lead của cùng issue giữ nguyên khi ghép/chấm.

Năm 2021–2023 đã được dự án xem nhiều lần, là development khám phá. Năm 2024 dành calibration cuối. Năm 2025 không đưa vào báo cáo phân bố/đếm sự kiện để chọn thiết kế; chỉ mở khi đã khóa ranh, target, nhóm biến, mô hình, loss, threshold, cách chấm và calibration. Năm 2026 không dùng để fit/chọn mô hình được chấm trên 2025.

Fit Platt có regularization riêng mỗi lead/ngưỡng trên calibration, không trên eval. Chỉ fit khi có ít nhất 20 sự kiện và 20 không sự kiện; nếu thiếu, dùng xác suất thô và ghi rõ không đủ dữ liệu hiệu chỉnh. Ngưỡng 50/100 hiếm không được tự hạ để làm đẹp. Sau calibration, chiếu ba xác suất về thứ tự p16≥p50≥p100 bằng quy tắc đơn điệu cố định, chỉ dựa trên dự báo và giống nhau cho mọi E/mô hình.

CSI sự kiện chính dùng quyết định xác suất với threshold chọn trên calibration, lưới cố định 0,01–0,99 bước0,01; tie chọn ngưỡng cao hơn. Chỉ chọn khi calibration có ít nhất 20 sự kiện và 20 không sự kiện; nếu thiếu, dùng 0,5 và gắn cờ. Đồng thời báo CSI từ lượng mm như chỉ số mô tả riêng. BSS/reliability luôn dùng xác suất liên tục sau xử lý, không dùng nhãn 0/1 của quyết định và không dùng lượng mm chia threshold làm xác suất.

Lưu việc calibration đã tham gia chọn epoch/iteration, Platt và threshold. Không gọi điểm calibration là kiểm định độc lập. Nếu sau khi xem test lại sửa thiết kế, 2025 phải được đánh dấu đã dùng phát triển và cần holdout tương lai khác.

## 10. Chỉ số, mùa và độ chắc chắn

Giữ tinh thần D9: **CSI/BSS chính, reliability bắt buộc; RMSE/bias và MAE phụ**, riêng từng lead. Ngưỡng chính cho nhánh ngày đề nghị 16 mm/24h; ngưỡng50/100 là mô tả mưa hiếm do số sự kiện hiện quá ít. Các ngưỡng này trên trung bình vùng, không phải cấp cảnh báo tại điểm hoặc cảnh báo chính thức. Không tự chép ngưỡng10mm/3h của nhánh Bi-LSTM sang ngày.

Bảng ngày toàn năm là đánh giá chính của nhánh này, luôn kèm tách tháng5–10,11–2,3–4. D10 hạn chế kết luận nhãn giờ mùa đông vẫn được giữ; nhánh mới dùng tổng24h không chứng minh nhãn giờ mùa đông đã đúng. Báo số mẫu, số sự kiện và giới hạn kiểm chứng nhãn cho mỗi bảng. Không gộp để che năm/mùa xấu.

Chỉ số tối thiểu: BSS16, BS16, CSI16, POD/FAR, reliability; RMSE/bias/MAE của mm/24h; các threshold50/100 mô tả riêng. Không có sự kiện/denominator0 thì ghi không xác định, không gán0. Dùng `src/verification.py`, kiểm tra hoặc bổ sung adapter cho nhãn ngày; không tự viết một hệ chỉ số khác.

Bootstrap ghép cặp theo khối issue **7 ngày**, giữ chung ba lead và cùng mẫu giữa mô hình; độ nhạy14 ngày. Gộp seed bằng trung bình xác suất/lượng mm tại mỗi issue để chấm ensemble và bootstrap, đồng thời báo từng seed và độ lệch chuẩn. Điều này tách biến động tối ưu hóa khỏi biến động thời tiết; seed không tạo thêm năm độc lập.

Family chính của TFT có ba phép so nhóm × ba lead = chín so sánh BSS16 trên các issue evaluation gộp2021–2023; bảng từng fold là mô tả, không tự coi thành27 kiểm định xác nhận khác. Báo CI95% mô tả và CI đồng thời Bonferroni99,44% cho family chính, 20.000 bootstrap cho đuôi CI; có thể dùng 2.000 lần để kiểm tra pipeline trước. Lặp index bootstrap giống nhau cho mọi cấu hình trong fold. LightGBM/CSI/RMSE/nhánh phụ là phân tích hỗ trợ, không thay metric/family chính sau khi nhìn điểm. Khi gộp development, resample khối trong từng năm, giữ số năm và không tạo khối nối qua ranh năm. Holdout E7−E0 có ba lead, family BSS16 riêng với CI đồng thời98,33%.

Khi bootstrap BSS, cả event, dự báo và xác suất khí hậu tham chiếu phải được resample theo cùng issue. Hàm bootstrap hiện có chỉ đưa hai vector obs/pred vào metric nên cần adapter nhận cả reference hoặc tính lại frame đúng index; không đóng reference gốc trong closure rồi dùng với mẫu đã resample. Kiểm tra bằng ví dụ tính tay trước bảng chính.

Với chỉ 4–6 ngày ≥100 mm/năm, CI rất rộng hoặc nhiều bootstrap không có sự kiện là điều cần công bố, không phải lỗi để bỏ mẫu. Nếu cần chứng minh kỹ năng cực đoan, cần thêm năm/vùng hoặc câu hỏi khác; không tăng số seed để thay thế số sự kiện.

## 11. Các bước, đầu ra và điều kiện hoàn thành

| Giai đoạn | Việc và đầu ra bắt buộc | Điều kiện để qua bước | Giờ công dự kiến |
| --- | --- | --- | --- |
| G0 | Khóa target, issue, nguồn/ranh/QC; kiểm kê và manifest | Vùng được mô tả trung thực; X/y cùng trọng số; split và nhãn không mâu thuẫn | 4–6 |
| G1 | Loader 168h→3 tổng ngày; mask chung, scaler train-only; test thời gian/đơn vị | Sửa dữ liệu tương lai không đổi X; tự cộng nhãn khớp; không lọt năm/ô/nhãn vào feature | 5–7 |
| G2 | Khí hậu/0, LightGBM E0/E7 F1, bộ chấm ngày | Mọi prediction ghép theo issue/lead; kiểm lại chỉ số và baseline độc lập | 4–6 |
| G3 | TFT vùng, loss ngày, event heads, checkpoint/scaler | Thành phần TFT truy vết được; forward/backward hữu hạn; save/load tái lập | 10–14 |
| G4 | Pilot TFT E0/E7 F1 seed42; đo runtime/VRAM và khóa config | Không leakage, không lỗi đơn vị/baseline; ghi thời gian epoch và dự toán mới | 3–5 |
| G5 | Ma trận development 72 TFT/24 pipeline cây, calibration | Cùng mask/budget; run hoàn tất hoặc lỗi được công bố; không tự bỏ run điểm xấu | 4–6 |
| G6 | Bảng theo lead/năm/mùa, bootstrap/reliability và QC nhãn giao dữ liệu | Chỉ kết luận theo hỗ trợ CI và nhãn; có danh sách giới hạn/số sự kiện | 6–8 |
| G7 | Khóa protocol; E0/E7 train/cal/test cuối; bản báo cáo và bàn giao | 2025 chỉ mở sau khóa; chạy lại checkpoint tái lập bảng; đầy đủ hash/config | 4–6 |

Tổng **40–58 giờ tập trung**, chưa cộng thời gian máy chạy không cần giám sát; cộng20% dự phòng thành **48–70 giờ**. G0 dự toán bao gồm chốt/QC phạm vi đang có, không bảo đảm hoàn tất tải thêm ô biên trong cùng quỹ giờ. Việc viết TFT và kiểm tra phải có thời gian riêng; không coi vài epoch chạy được là cả nghiên cứu đã xong.

| Quỹ giờ mỗi ngày | Thời gian làm việc dự kiến có dự phòng |
| --- | --- |
| 4 giờ/ngày | 12–18 ngày làm việc |
| 5 giờ/ngày, giả định lịch chính | 10–14 ngày làm việc |
| 6 giờ/ngày | 8–12 ngày làm việc |

Nếu làm5ngày/tuần, lịch chính thường2–3tuần; chưa ấn định ngày hoàn thành khi người dùng chưa xác nhận số giờ/ngày. Bản baseline đầu dự kiến sau13–19giờ công (khoảng3–4ngày). Pilot TFT đầu sau26–38giờ công (khoảng5–8ngày). Chạy nền có thể trùng với thời gian viết báo cáo; không cộng giờ GPU thẳng vào giờ công.

## 12. Ngân sách tính toán và kiểm soát thời gian

Dự toán GPU **trước pilot** là8–30giờ, mức tin cậy thấp khi chưa có TFT vùng. Pilot đã đo tổng186,8giây cho6TFT/6LightGBM; epoch khoảng1–2giây, xem số đo đầy đủ trong báo cáo. Công thức cập nhật: tổng mỗi run = số epoch thực tế × thời gian epoch đã đo (bao gồm validation) + inference/calibration/save; cộng các run, có20% dự phòng. Với cùng kiến trúc/mẫu, dự phòng khoảng1–3giờGPU cho ma trận đầy đủ hợp lý hơn ước tính ban đầu; vẫn phải tính lại nếu thay dữ liệu/cấu hình. Thời gian xử lý dữ liệu/viết nghiên cứu khác thời gian GPU.

Ở G4 đo3epoch sau warm-up trên full train F1, batch64, ghi median giây/epoch, max VRAM, RAM, thời gian data load và tốc độ suy luận. Nếu OOM, thử batch32 trước khi đổi kiến trúc; mọi thay đổi batch/budget phải khóa và áp dụng chung. Nếu epoch đo >60giây hoặc dự toán vượt30giờ, cập nhật lịch trước khi khởi chạy cả ma trận; không hứa GPU8GB làm nghiên cứu xong trong một đêm.

Không dùng2,2triệu cửa sổ ô hoặc epoch_subset300.000 của kế hoạch lưới cũ cho chuỗi vùng nhỏ. Với tensor float32 hiện đề nghị, X đầy đủ development khoảng3.248×28×44×4byte ≈15,3MiB trước overhead; đây là bộ đệm X, không phải toàn bộ RAM/VRAM huấn luyện. Đọc V1 vùng, không nhân bản cube gốc nhiều GB. Checkpoint, log và dữ liệu chạy dài lưu ổ nội bộ nếu USB D gây nghẽn, sau đó đồng bộ artifact cần giữ về nơi quản lý; không tự di chuyển/xóa dữ liệu nguồn.

## 13. Phân công, mã cần làm và tái lập

Người dùng sở hữu loader ngày/TFT/baseline/đánh giá nhánh24–72h; thành viên Bi-LSTM sở hữu nhánh1–6h. Hai bên thống nhất dataset ID, ranh/trọng số, phiên bản nhóm biến, múi giờ, ý nghĩa mm và test2025. Có thể làm độc lập sau khi hợp đồng dữ liệu thống nhất; không cần chờ một mô hình hoàn tất mới viết mô hình kia.

Các đường dẫn sau là **đề xuất sẽ triển khai sau duyệt**, hiện chưa phải code đã có:

- `src/short_range_dataset.py`: loader/cửa sổ, nhãn ngày, scaler và mask.
- `src/tft_regional.py`: TFT backbone và đầu đọc ngày; `src/short_range_losses.py`: loss/target sự kiện ngày.
- `scripts/train_short_range_lgbm.py`, `scripts/train_short_range_tft.py`, `scripts/evaluate_short_range.py`, `scripts/report_short_range.py`.
- `tests/test_short_range_dataset.py`: chống rò rỉ, cộng24h/ranh năm, missing và common mask; `tests/test_tft_regional.py`: shape/mask/loss/roundtrip; kiểm tra metric bằng ví dụ tính tay.

Tái dùng `src.verification`, `src.dataset_v2.time_features` và thành phần phù hợp của rainfall_losses. **Không chép nguyên TweedieJointLoss/aggregate_targets hiện tại**: chúng đang dùng ba khoảng0–3/3–6/0–6h và ngưỡng1/10/25mm; nhánh ngày phải dùng ba ngày/ngưỡng16/50/100. Không dùng nguyên `supervised_windows` của pilot vùng vì hàm đó khóa horizon6h. InformerDataset cũ cũng không phải loader vùng ngày.

Mỗi run lưu commit, runID, dataset/hash, weights/hash, feature list, fold, issue, seed, scaler, loss, config, history, best epoch, calibration, checkpoint và dự báo issue×lead. Có command tái tạo bảng từ checkpoint không huấn luyện lại. Run lỗi phải có trạng thái/cause, không để CSV và checkpoint thuộc hai lượt khác nhau.

Dữ liệu, checkpoint và dự báo từng dòng ở `data/operational/short_range/` hoặc kho riêng, ngoài Git. Repo công khai chỉ giữ code, plan, metadata và số liệu tổng hợp; không commit PDF/credential. Khuyến nghị nhánh triển khai riêng từ main, ví dụ `research/tft-regional`, để không xung đột notebook của thành viên trên dev; chưa tạo nhánh trong lượt lập kế hoạch.

## 14. Điều kiện tiếp tục, thu hẹp và mở rộng

G0/G1 lỗi nhãn, đơn vị, thời gian hoặc ranh chưa thống nhất thì sửa dữ liệu trước, không chạy toàn ma trận. Nếu chỉ thiếu nguồn giao ranh, pilot kỹ thuật trên93ô được gắn nhãn xấp xỉ; kết quả cuối toàn địa giới chưa được xác nhận.

Pilot không thắng baseline **không tự là lý do dừng hoặc sửa bài để thắng**. Trước tiên phân biệt bug, thiếu thông tin và biến động mẫu; giữ thiết kế, báo kết quả âm và dùng ba fold theo ngân sách đã duyệt. Nếu nhóm quyết định thu hẹp vì thời gian, lưu rõ ma trận đã chạy và giới hạn, không chọn bỏ riêng các run xấu.

Informer hoặc V2 là mở rộng sau khi có kết quả chính. Nhánh mưa quá khứ phải bổ sung nguồn/lag và đối chứng cùng thông tin; Gauge tức thời không được gọi là dữ liệu vận hành. Phân vị ngày nếu thêm thì đầu đọc trực tiếp trên tổng ngày, kiểm tra coverage/pinball, không tự cộng quantile của giờ.

ECMWF forecast là nhánh nghiên cứu khác có giá trị nếu mục tiêu là hiệu chỉnh dự báo thật. Cần lưu run/init/available_at/valid_time/lead và kiểm tra biến thực có. [Single Runs](https://open-meteo.com/en/docs/single-runs-api) nêu IFS từ03/2024; các probe hiện tại chưa bảo đảm trường850hPa. Không mặc định có forecast2015–2023 hoặc train ERA5 tương lai rồi thay bằng forecast là phép so đã hợp lệ. Dự trù ban đầu thêm1–2tuần cho thu thập/pilot nguồn nếu truy cập thuận lợi, nhưng chỉ chốt lịch sau kiểm tra độ phủ và split; không nằm trong48–70giờ chính.

## 15. Gói đầu ra cần đạt và nội dung duyệt

Gói nghiên cứu cuối gồm dataset manifest/mask; code tái lập; bảng từng lead/năm/mùa/seed; reliability và bootstrap ghép cặp; ablationE0–E7; kiểm tra nhãn giao dữ liệu và giới hạn; bảng holdoutE0/E7 năm2025; bản phương pháp/kết quả/thảo luận. Có thể kết luận “chưa có bằng chứng cải thiện” nếu CI không hỗ trợ. Không bắt buộc có app, Informer hoặc tuyên bố vượt ECMWF.

Gói đã được duyệt: **V1 vùng → ba tổng24h, lịch sử7ngày gộp6h, TFT+LightGBM, E0–E7, ba fold phát triển, test2025E0/E7, RTX4060.** Dự toán ban đầu48–70giờ công vẫn là khung nghiên cứu đầy đủ; GPU cập nhật theo pilot ở mục12. Giờ/ngày tạm giả định4–6; có thể điều chỉnh lịch mà không đổi protocol. Ưu tiên3–4giờ đã tạo được pilot E0/E7 một seed trên footprint93ô; các cổng ranh/QC/factorial/holdout còn phải hoàn tất.

Thứ tự loader/kiểm tra nhãn → baseline E0/E7 → TFT/pilot đã được áp dụng cho mốc báo cáo sơ bộ. Tiếp theo ưu tiên hoàn thiện ranh/QC và ma trận nhiều seed; không đánh dấu nghiên cứu cuối đã hoàn tất chỉ vì pilot có kết quả.

## 16. Nguồn và tài liệu liên quan

- [Phương án hợp nhất vùng trực tiếp](../regional_research_plan_2026_10_20/PHUONG_AN_CUOI.md): nguồn quyết định chung, không phải log TFT đã chạy.
- [V1/V2 và pilot LightGBM 3/6h](../regional_danang_v1_v2/README.md): bằng chứng dữ liệu và kết quả ở hạn khác, không dùng để suy ra TFT ngày đã hiệu quả.
- [Rà soát Bi-LSTM dev](../research_rainfall/dev_bilstm_review_2026_10_20.md): các lỗi thang đo/baseline/truy vết cần tránh.
- [TFT, Lim và cộng sự](https://arxiv.org/abs/1912.09363): thành phần kiến trúc và các loại đầu vào; không chứng minh ưu thế tại Đà Nẵng.
- [Tài liệu TemporalFusionTransformer](https://pytorch-forecasting.readthedocs.io/en/stable/api/pytorch_forecasting.models.temporal_fusion_transformer.TemporalFusionTransformer.html): tham khảo triển khai, API phải kiểm tra lại khi khóa dependency.
- [Single Runs API](https://open-meteo.com/en/docs/single-runs-api): giới hạn kho forecast theo run, không phải bằng chứng đã tải đủ cho nghiên cứu.

Kiểm kê hiện tại được tạo bằng `scripts/inspect_short_range_plan.py`; chưa fit mô hình và chưa chấm2025. Các ước tính giờ là dự toán kỹ thuật có điều kiện, không phải thời gian huấn luyện đã đo.
