# Đối chiếu TONG_HOP_DE_XUAT với hướng nghiên cứu hiện tại

Ngày 20/10/2026. Đã đọc toàn bộ 477 dòng tài liệu trong Downloads, đối chiếu code, báo cáo, lịch sử Git và tài liệu nhà cung cấp. Các nhãn “CHỐT” trong tài liệu là lời mô tả của tác giả, không tự thay thế yêu cầu hiện tại của người dùng. Không sửa tài liệu gốc, không đổi code huấn luyện, không chấm mô hình năm 2025.

## 1. Kết luận

Tài liệu có nhiều phần tái sử dụng được, nhưng không phù hợp để áp dụng nguyên trạng làm kế hoạch hiện tại. Có ba loại khác biệt:

1. **Phạm vi đã thay đổi:** tài liệu ưu tiên app, hai sản phẩm và hậu xử lý ECMWF; người dùng hiện ưu tiên nghiên cứu đóng góp của đặc trưng cho dự đoán mưa ở Đà Nẵng.
2. **Một lựa chọn thiết kế chưa chốt:** tài liệu dự đoán từng ô, còn V1/V2 vừa tạo dự đoán trực tiếp trung bình vùng. Dự đoán từng ô hoàn toàn phù hợp với mục tiêu phủ cả vùng; không phải nội dung sai cần loại bỏ.
3. **Một số lập luận quá chắc hoặc đã cũ:** đồng nhất Open-Meteo với ERA5, coi kiểm chứng mưa ngày đủ để chốt nhãn giờ, suy luận hiệu chỉnh mùa đông là trải đều, và trạng thái “chưa huấn luyện”.

Không coi mọi đề xuất trong tài liệu là sai; cũng không coi V1/V2 hiện tại là phương án cuối đã được xác nhận tốt hơn.

## 2. Đối chiếu phạm vi

| Nội dung trong tài liệu | Hướng hiện tại/đánh giá | Cách xử lý |
| --- | --- | --- |
| Mục 4/8/10: hai sản phẩm Bi-LSTM 0–6 giờ, TFT 1–3 ngày, app và live | Rộng hơn ưu tiên nghiên cứu đặc trưng hiện tại; hạn nghiên cứu cuối chưa chốt lại | Chọn một bài toán chính; để app, hạn thứ hai và đa vùng ở phần mở rộng |
| D8/mục 7: AI phải hậu xử lý và vượt ECMWF | Không phải điều kiện bắt buộc để nghiên cứu ERA5 hồi cứu về đặc trưng | ECMWF là đối chứng có giá trị khi có forecast phù hợp, không phải cổng chặn mọi nghiên cứu |
| D3/mục 4.2: dự đoán mỗi ô 0,1° | Khác đầu ra V1/V2, nhưng vẫn là dự đoán cho cả vùng | Cân nhắc dự đoán ô rồi tổng hợp, so với dự đoán vùng trực tiếp |
| D4: một mô hình chung cho nhiều ô, dùng địa hình | Là phương án hợp lý; không đồng nghĩa mỗi ô một mạng hoặc bắt buộc ConvLSTM/U-Net | Có thể giữ Bi-LSTM chung, mỗi mẫu là một ô và thời điểm |
| D9/mục 6.5: CSI/BSS chính, MAE/RMSE chỉ tham khảo | Phù hợp nếu trọng tâm là sự kiện/xác suất; chưa tự phù hợp với đầu ra lượng mưa hiện tại | Đăng ký bộ chỉ số theo mục tiêu: sai số lượng mưa, bias, kèm CSI/POD/FAR; BSS khi thật sự có dự báo xác suất |
| D11: ablation, cùng mẫu/kiến trúc, train-only scaling, nhiều seed và bootstrap | Phù hợp | Giữ, nhưng cần nhiều năm/đợt mưa; seed không thay thế mẫu thời tiết độc lập |

Các điểm trên là khác biệt mục tiêu, không phải bằng chứng tác giả sai về kỹ thuật. Quyết định cũ có thể đã phù hợp với mục tiêu làm app ở thời điểm đó.

## 3. Phần dự đoán từng ô đáng giữ

Tài liệu đề xuất mô hình chung học theo mẫu (ô, thời điểm). Đây là một phương án khác với việc đưa toàn bộ ảnh lưới vào ConvLSTM. Nó không bắt buộc tạo 93 mô hình.

Nếu muốn nghiên cứu tác dụng của độ cao, khoảng cách biển hoặc đặc điểm địa phương, mô hình theo ô có một lợi thế thiết kế: các đặc trưng này biến thiên giữa các mẫu không gian. Với một vùng cố định, trung bình địa hình là hằng số theo thời gian; chỉ thêm cột hằng số không cho phép đánh giá đóng góp như ở nhiều ô. V2 đã dùng phân tầng và tương tác động để tránh một phần giới hạn này, nhưng vẫn mất thông tin vị trí chi tiết.

Hai đường cần phân biệt:

- **Vùng trực tiếp:** tổng hợp đầu vào → mô hình → mưa trung bình vùng.
- **Ô rồi vùng:** mô hình chung → mưa từng ô → trung bình có trọng số diện tích.

Cả hai phải được chấm trên cùng nhãn vùng, thời điểm và điều kiện thông tin nếu muốn so hiệu quả đầu ra vùng. Chấm theo ô cần thêm bảng riêng. Chưa có thí nghiệm đối chứng thứ hai trong pilot V1/V2, nên chưa biết phương án nào tốt hơn.

Nghiên cứu Kratzert được dẫn trong tài liệu là về mô hình thủy văn trên 531 lưu vực. Nó hỗ trợ việc đặt giả thuyết về mô hình chung và đặc trưng tĩnh, không trực tiếp chứng minh dự báo mưa 93 ô Đà Nẵng sẽ cải thiện. [Bài gốc HESS](https://hess.copernicus.org/articles/23/5089/2019/).

## 4. Những kết luận khoa học cần sửa mức chắc chắn

### 4.1. Open-Meteo cũ chưa được chứng minh là ERA5 thuần

D1 và mục 3.1/3.2 gắn các số POD 8% và CSI 0,17 với ERA5. Tuy nhiên `scripts/fetch_openmeteo_baselines.py`, hàm fetch_station, gọi Archive không đặt models=era5 và lưu nguồn dưới tên era5_om. Docstring cũng nói rõ dùng mặc định best_match.

Tài liệu hiện hành của nhà cung cấp cho biết Best Match kết hợp nhiều hệ thống. Không thể từ đó suy ra chính xác nguồn của từng giờ trong cache cũ; chỉ đủ để bác bỏ việc mặc định toàn bộ cache là ERA5 thuần. [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api).

Cách viết phù hợp: “Chuỗi nhãn Open-Meteo mặc định cũ có hạn chế trong phép so đã làm; cần khóa nguồn để kiểm định riêng ERA5.” Không phải “đã chứng minh ERA5 chỉ bắt 8% mưa cực đoan ở mọi thiết kế”.

### 4.2. GSMaP là ứng viên nhãn, chưa phải chân lý mưa giờ toàn vùng

Bảng 10 trạm/ngày có ích để sàng lọc. Nó không tự xác nhận đúng phân bố từng giờ, đúng mọi ô vùng núi hoặc độc lập với trạm dùng hiệu chỉnh.

Đã tính lại trong lượt rà soát này trên các cặp ngày hiện có tại Đà Nẵng, giai đoạn 2021–2023, cùng 1.042 ngày và ngưỡng 50 mm/ngày:

| Nguồn | CSI |
| --- | --- |
| ERA5 trong cube | 0,3519 |
| GSMaP Gauge trong cube | 0,4375 |
| IMERG tại điểm | 0,2754 |

Bootstrap khối 5 ngày, 1.000 lần, seed 20261020: chênh CSI Gauge − ERA5 = +0,0856; CI 95% [−0,0542; +0,2302]. Điểm ước lượng thuận lợi cho Gauge, nhưng khoảng tin cậy còn chứa 0.

Phép tính này không thay thế hoặc bác bỏ bảng 10 trạm: khác phạm vi và nguồn đối chiếu. Nó cho thấy không nên lấy kết quả gộp nhiều trạm để khẳng định chắc ưu thế tại riêng Đà Nẵng. Bản thân cách ghép ngày trạm còn cần kiểm tra mốc tích lũy; số đo điểm cũng không xác nhận trung bình toàn vùng.

JAXA cảnh báo Gauge phụ thuộc phân tích mưa ngày CPC và có thể sai ở nơi mạng trạm thưa; Gauge NRT không dùng trực tiếp trạm hiện thời theo cùng cách. Đây là lý do phải phân biệt nhãn hồi cứu và nguồn vận hành. [JAXA release note, trang 3](https://www.eorc.jaxa.jp/GPM/doc/product/ReleaseNote/08_note_GPM-GSMaP_20231110.pdf).

### 4.3. Mưa Gauge ở giờ raw bằng 0 chưa chứng minh bị chia đều

Mục 3.4 suy từ raw bỏ sót/khác Gauge sang kết luận tổng ngày được trải đều ra giờ. Đó là một giả thuyết cần kiểm tra thuật toán và tham chiếu dưới ngày, chưa phải hệ quả tất yếu từ các thống kê đã nêu.

Raw có thể bỏ sót mưa thật; hiệu chỉnh có thể làm phân bố giờ sai; ghép thời gian cũng có thể gây khác biệt. Ví dụ vài ngày gần đều hoặc tỷ lệ lượng mưa ở giờ raw bằng 0 chưa phân biệt được các khả năng này.

Tách mùa và báo cáo độ nhạy là hợp lý. Bỏ đánh giá giờ mùa đông không chứng minh nhãn 6 giờ hoặc 24 giờ khi đó đã chính xác; cũng không cho phép tuyên bố giải quyết mưa Đà Nẵng quanh năm. Các tỷ lệ khác nhau giữa báo cáo phải so cùng vùng, năm và ngưỡng raw trước khi gọi là mâu thuẫn số liệu.

### 4.4. A4/B3 dùng ERA5 tại giờ đích là một điều kiện thông tin khác

Code FEATURE_GROUPS đúng là có ERA5 tại giờ đích cho A4/B3. Nếu mục tiêu chính là dự báo từ lịch sử có trước thời điểm t, việc thêm nhóm này đồng thời bổ sung thông tin thời tiết tương lai. Mức tăng không chỉ phản ánh “thêm đặc trưng phù hợp địa phương”.

Có thể giữ như thí nghiệm perfect-prog/oracle riêng, hoặc thay bằng forecast có thời điểm phát hành phù hợp. Không trộn với thí nghiệm chỉ dùng quá khứ rồi diễn giải ngang nhau. BASE/RAW/DOMAIN trong domain screen hiện chỉ có lịch ở x_future; không được quy lỗi A4 cho mọi mô hình đã chạy.

Không làm app giúp giảm yêu cầu vận hành, nhưng không loại bỏ yêu cầu mô tả đúng điều kiện thông tin. Ngược lại, dùng lịch sử ERA5 hồi cứu để nghiên cứu không tự bắt buộc phải có toàn bộ pipeline live.

### 4.5. BSS âm trong bảng không buộc mọi nghiên cứu phải xuất xác suất

`src/verification.py:score_table` chuyển dự báo lượng mưa thành 0/1 theo ngưỡng trước khi tính BSS. Bảng mô tả kết quả của quy tắc phân loại đó trên mẫu đã chọn. Nó không chứng minh mọi mô hình tất định đều vô ích hoặc dữ liệu ECMWF không có kỹ năng.

Nếu so xác suất AI đã hiệu chỉnh với forecast thô bị biến thành 0/1, cần nói rõ đây còn khác nhau ở cách tạo xác suất. Có thể thêm đối chứng ECMWF được hiệu chỉnh tương ứng. Với mục tiêu dự đoán lượng mưa, MAE vẫn có thể báo cáo cùng RMSE/bias và điểm mưa lớn; vấn đề là không dùng một mình MAE để tuyên bố thắng do có nhiều giờ khô.

## 5. Trạng thái và quy mô trong tài liệu đã cũ

- Tài liệu ghi cập nhật 20/10 nhưng tham chiếu commit e531982, được tạo ngày 11/10. Main hiện có commit d3f3936 cùng nhiều công việc sau mốc đó.
- Mục 9 nói chưa huấn luyện bất kỳ mô hình nào trên dữ liệu mới, chưa baseline lưới, chưa log live. Hiện đã có pilot Bi-LSTM 93 ô, domain screen 30 ô, baseline LightGBM và ghi nhận thử một số tệp NRT. Đây là bằng chứng triển khai, chưa là app AI live đã kiểm chứng.
- V1/V2 và pilot vùng cũng đã có trên main. Bộ E0–E7 mới trên dev lại đọc full_features cũ; không dùng bảng nhóm A0–A5 của tài liệu để suy rằng bộ E0–E7 đó đã chạy trên cube mới.
- Con số 105.192 là trục lịch 2015–hết 2026. Dữ liệu thực trong bản vùng mới hiện kết thúc 30/09/2026; V1/V2 xuất 102.984 giờ. Không đồng nhất kích thước cấp sẵn với số giờ có nhãn.
- “51 đặc trưng” trong cube gồm 1 nhãn, 1 cờ, 45 ứng viên khí tượng/mưa và 4 biến thời gian; không phải 51 đầu vào cho mọi cấu hình.
- Nhiều ô/triệu cửa sổ không phải từng ấy mẫu thời tiết độc lập. Các ô gần nhau và cửa sổ chồng lấn có tương quan; bootstrap phải gom các ô cùng ngày/đợt đi cùng nhau.
- Lộ trình 10 tuần, hạn nộp và số giờ GPU là giả định của tài liệu, không phải ràng buộc người dùng vừa xác nhận hoặc dự toán đã đo cho cấu hình cuối.

## 6. Phương án dung hòa phù hợp

1. Giữ trọng tâm nghiên cứu thêm/bớt nhóm đặc trưng tại Đà Nẵng, chấp nhận kết quả không cải thiện; chưa suy ra toàn Việt Nam.
2. Chốt đầu ra theo mục tiêu giảng viên: nếu cần bản đồ hoặc tác dụng địa hình giữa các nơi, mô hình chung dự đoán từng ô là hướng đáng ưu tiên; nếu chỉ cần trung bình vùng, trực tiếp vùng là một phương án hợp lệ. So hai đường trên cùng đầu ra vùng khi có điều kiện.
3. Giữ một hạn chính trước; lịch sử 24 giờ và tổng 3/6 giờ hiện là cấu hình thăm dò, không phải hạn cuối đã được người dùng xác nhận lại. Nhãn phải được đánh giá đúng thang thời gian chọn.
4. Giữ Bi-LSTM và LightGBM làm đối chứng ban đầu; cùng mẫu, nhãn, điều kiện thông tin và ngân sách phù hợp. Sửa các lỗi đơn vị/baseline và truy vết checkpoint trên dev trước khi dùng kết quả E0–E7.
5. Định nghĩa nhóm có giả thuyết rõ. Các cấu hình lưới mặc định đều có tám biến tĩnh: nếu muốn đo tác dụng địa hình, phải có cấu hình loại chúng thật sự. SST là biến khí hậu ứng viên, chưa có nghĩa đã kiểm tra ENSO/MJO.
6. Giữ test 2025 cho đánh giá cuối của thiết kế đã cố định. Dùng các năm đã xem như validation khám phá, kèm nhiều năm/mùa và khoảng tin cậy theo khối.
7. Để TFT, hạn 1–3 ngày, đa vùng, API live và app ở phần mở rộng. Nếu nghiên cứu sau này chuyển sang vận hành, khi đó đưa forecast thật, latency và T-OPS thành điều kiện chính.

## 7. Bằng chứng đã đối chiếu

- Tài liệu nguồn: TONG_HOP_DE_XUAT.md do người dùng cung cấp, 477 dòng; các mục/D được dẫn theo chính tài liệu đó.
- Git: e531982 là commit ngày 11/10; main d3f3936; dev fe27756. Không thay đổi nhánh trong lượt này.
- Code: `scripts/fetch_openmeteo_baselines.py`, `src/verification.py`, `src/dataloader_v2.py`, `scripts/build_dataset_v2.py`.
- Kết quả đã có: `reports/pilot_bilstm_v2_93cells_3seeds/`, `reports/domain_screen_danang/`, `reports/followup_danang/jaxa_live_first_detection.json`; báo cáo V1/V2 đọc từ main.
- Tính lại nhãn ngày: `data/operational/label_audit_danang/station_daily_pairs_2021_2023.parquet`, dùng `contingency_scores` và `paired_block_bootstrap` của repo. Không dùng kết quả mô hình năm 2025.
- [Rà soát E0–E7 trên dev](dev_bilstm_review_2026_10_20.md).

Bản đối chiếu được thực hiện trên dev và công bố trên main theo yêu cầu người dùng. Các đề xuất trong bản đối chiếu cần đọc cùng [phương án hợp nhất cuối](../regional_research_plan_2026_10_20/PHUONG_AN_CUOI.md), nơi ghi rõ lựa chọn và sáu tiêu chí cho từng khác biệt; bản đối chiếu không tự thay quyết định của nhóm/giảng viên.
