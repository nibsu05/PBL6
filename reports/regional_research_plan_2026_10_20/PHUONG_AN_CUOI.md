# Phương án nghiên cứu cuối: dự đoán mưa vùng trực tiếp tại Đà Nẵng

**Bản bàn giao cho nhóm — 20/10/2026.** Hợp nhất TONG_HOP_DE_XUAT.md với định hướng người dùng đã xác nhận: ưu tiên nghiên cứu đặc trưng và dự đoán vùng trực tiếp. Đây là phương án thực hiện đã chọn; các kết quả thí nghiệm mới chưa được tạo chỉ bằng việc viết tài liệu này.

## 1. Đọc nhanh để thống nhất lại bối cảnh

**Mục tiêu:** đo đóng góp của các nhóm đặc trưng khí tượng và cách biểu diễn không gian đối với dự đoán lượng mưa trung bình vùng Đà Nẵng mới. Chấp nhận kết quả không cải thiện hoặc chỉ cải thiện ở một số mùa; không đặt trước rằng E7, V2 hay Bi-LSTM phải thắng.

**Luồng chính:** dữ liệu khí tượng của các ô → tổng hợp thành chuỗi vùng V1/V2 → mô hình dự đoán vùng trực tiếp → lượng mưa trung bình vùng trong 6 giờ tiếp theo, đánh giá tổng 3/6 giờ và xác suất vượt ngưỡng.

93 ô là nguyên liệu để tạo nhãn và đầu vào vùng. Một mẫu học là **một thời điểm của cả vùng**, không phải một ô. Mô hình chính không dự đoán 93 lượng mưa rồi mới lấy trung bình. Dự đoán từng ô có thể làm đối chứng mở rộng, không phải điều kiện để hoàn thành hướng đã chọn.

Giữ Bi-LSTM làm mô hình chính, LightGBM làm đối chứng; khung chính E0–E7. V1 là biểu diễn nền; V2 là nhánh kiểm tra thông tin phân bố không gian, chưa mặc định tốt hơn. Nhãn chính vẫn là GSMaP Gauge, IMERG là kiểm tra độ bền trong phạm vi có dữ liệu; ERA5 cung cấp phần lớn đầu vào khí tượng.

**App, TFT 1–3 ngày, nhiều vùng và kiểm định live chuyển sang phần mở rộng.** Dữ liệu được nghiên cứu ở chế độ hồi cứu; chưa gọi kết quả là AI vận hành hoặc cảnh báo ngập. Các quyết định có nhãn [CHỐT · BẰNG CHỨNG] của tài liệu nhóm được giữ theo mục 3; không dùng kết quả khác giao thức để tự thay chúng.

## 2. Bài toán, vùng và đầu ra

### 2.1. Định nghĩa đầu ra

Vùng mục tiêu R là Đà Nẵng mới, gồm Đà Nẵng cũ và Quảng Nam cũ. Trước khi đóng băng dữ liệu, phải lưu phiên bản ranh, hệ tọa độ, mặt nạ đất/biển, các phần lãnh thổ được bao phủ và danh sách ô. Tập 93 ô hiện có là bản xấp xỉ ban đầu, chưa tự chứng minh bao phủ đúng toàn bộ R.

Gọi a_i là diện tích phần ô i giao với R, sau khi áp dụng mặt nạ nghiên cứu đã công bố; w_i = a_i / tổng(a_i). Mưa vùng mỗi giờ là p_R(t) = tổng[w_i × p_i(t)]. Nhãn tổng H giờ là Y_H(t) = tổng p_R(t+h), với h từ 0 đến H−1. Đơn vị là mm trung bình trên vùng, không phải tổng mm cộng từ các ô; thể tích nước là một đại lượng khác.

**Cổng bắt buộc:** kiểm tra cả những ô biên hoặc phần lãnh thổ nằm ngoài hộp nguồn hiện tại. Nếu thiếu ô giao ranh, phải bổ sung hoặc công bố lại phạm vi nghiên cứu; chỉ sửa trọng số trên 93 ô chưa đủ để gọi là toàn Đà Nẵng chính xác. Không tự đổi phạm vi thành “Đà Nẵng cũ”.

### 2.2. Một mẫu và hạn nghiên cứu

Phương án triển khai đầu tiên chọn lịch sử 24 giờ → 6 khoảng mưa giờ kế tiếp, kế thừa cấu hình A của nhóm. Tại thời điểm t, đầu vào khí tượng là [t−24 giờ, t); nhãn là [t, t+6 giờ). Tổng 3 giờ đầu và tổng 6 giờ được tính từ cùng sáu đầu ra.

Ví dụ: phát hành hồi cứu lúc 10:00 UTC, dùng khí tượng đến hàng 09:00, dự đoán các khoảng 10:00–11:00 tới 15:00–16:00. Không đưa ERA5 tại các giờ 10:00–16:00 vào phép thử chính. Lịch tương lai được biết trước nhưng phải dùng giống nhau giữa các cấu hình.

Lịch sử tái phân tích được mô tả là đầu vào hồi cứu, không cam kết có sẵn ở thời điểm vận hành thực. Dùng thuật ngữ **cực ngắn** cho hạn này, giữ D15; không gọi 1–3 ngày là dài hạn.

### 2.3. Vì sao chọn vùng trực tiếp?

Đây là lựa chọn đầu ra theo mục tiêu nghiên cứu, không phải kết luận dữ liệu lưới kém hoặc tổng hợp luôn chính xác hơn. Nó giúp tập trung phép so vào một nhãn vùng và đánh giá trực tiếp giá trị các nhóm thông tin đối với mục tiêu đó. Tổng hợp trước có thể làm mất cực đại cục bộ và vị trí mưa; V2 chỉ giữ thêm thống kê và tiểu vùng, không khôi phục bản đồ mưa.

Không diễn giải xác suất “mưa vùng vượt 10 mm” thành xác suất một điểm/xã bất kỳ vượt 10 mm. Không dùng kết quả vùng để tuyên bố cảnh báo ngập hoặc kỹ năng mưa cục bộ.

## 3. Các mục có bằng chứng được giữ

Nguyên tắc người dùng yêu cầu: chỉ thay mục [CHỐT · BẰNG CHỨNG] khi có phép đo tốt hơn **cùng giao thức**. Lượt tính lại 1.042 ngày ở một trạm, pilot LightGBM vùng và chẩn đoán checkpoint cũ khác phạm vi bảng 10 trạm; không đủ điều kiện thay D1/D2/D9/D10. Không có mục được bảo vệ nào bị thay bằng một điểm số khác giao thức trong phương án này.

| Mục gốc | Quyết định được giữ | Cách áp dụng cho bài toán vùng |
| --- | --- | --- |
| D1 | Không dùng mưa ERA5/Open-Meteo cũ làm nhãn chính | GSMaP Gauge là nhãn chính; mưa ERA5 chỉ là tham chiếu hồi cứu hoặc ứng viên đầu vào phụ |
| D2 | GSMaP v8 Gauge chính; IMERG Final kiểm tra độ bền | Tổng hợp cùng ranh/trọng số/thời gian; không tuyên bố nhãn giờ đã được kiểm chứng độc lập toàn vùng |
| D9 và mục 6.5 | CSI/BSS là chỉ số chính; reliability bắt buộc; không lấy MAE làm chỉ số chính | CSI tổng 3 giờ ≥10 mm và BSS ≥1 mm trong tháng 5–10; RMSE/bias và MAE phụ phải được báo cáo để đánh giá lượng mm |
| D10 và mục 3.4 | Tách mùa; không lấy điểm giờ mùa đông làm kết quả chính | Tháng 5–10 chấm 3 giờ chính; tháng 11–2 chấm 6 giờ phụ, kiểm chứng nhãn tổng ngày. Không có forecast 24 giờ từ mô hình chỉ dự đoán 6 giờ |
| D14 | Không có Vrain; nguồn kiểm chứng hiện có là NOAA GSOD | Giữ phạm vi/cờ chất lượng và mốc dữ liệu đã có; mưa ngày một số trạm không đại diện đầy đủ mưa giờ trung bình tỉnh |
| D15 | Thuật ngữ hạn dự báo theo Thông tư 08/2022 | Cực ngắn đến 12 giờ; ngắn trên 12 đến 72 giờ; vừa trên 3 đến 10 ngày |
| Mục 3.1/3.2/7 | Giữ các bảng bằng chứng gốc trong đúng phạm vi đã đo | Gắn rõ nguồn, thời kỳ, đơn vị điểm/ngày và cách tạo xác suất 0/1; không đổi thành kết luận phổ quát cho vùng/3 giờ |

Hai chú thích không thay quyết định: (1) code nguồn cũ dùng Open-Meteo Best Match, chưa xác nhận ERA5 thuần; (2) Gauge có mưa lúc raw bằng 0 là dấu hiệu cần kiểm tra, chưa tự xác nhận mọi giờ đều do chia đều tổng ngày. Giữ chính sách chọn nhãn và tách mùa, đồng thời lưu giới hạn bằng chứng. “Không dùng MAE” được áp dụng theo chính mục 6.5 của tài liệu nhóm: MAE chỉ là phụ, không phải bỏ mọi báo cáo MAE.

## 4. Dữ liệu nào dùng và cần hoàn thiện gì?

| Thành phần | Nguồn và vai trò | Trạng thái |
| --- | --- | --- |
| Khí tượng | ERA5 qua GEE, biến bề mặt, nhiệt động, hoàn lưu và ẩm | Đã có cube; nội suy 0,25° về tâm lưới chung không tạo độ phân giải thật mới |
| Nhãn | GSMaP Gauge v8 permanent | Đã có; cần trọng số vùng cuối và kiểm chứng theo thang thời gian |
| Mưa quá khứ phụ | GSMaP raw và thống kê lân cận | Đã có trong file, chưa dùng trong khung chính; thử riêng với dịch trễ |
| Địa hình | Copernicus DEM và ranh vùng | Đã có biến tĩnh; cần ranh/giao ô chính xác cho mục tiêu cuối |
| Kiểm tra độ bền | IMERG Final, NOAA GSOD | Chỉ dùng khoảng giao dữ liệu; không mặc định có tham chiếu độc lập cho toàn năm 2025 hoặc mọi giờ |
| ECMWF forecast | Đối chứng mở rộng nếu có dữ liệu phù hợp | Chưa là điều kiện chặn nghiên cứu hồi cứu; không dùng ERA5 giờ đích thay forecast có sẵn tại issue |

Hiện V1 có 102.984 hàng giờ, 49 đầu vào ứng viên; V2 cùng số hàng, 138 đầu vào ứng viên, từ 01/2015 đến 30/09/2026. Cờ chất lượng và nhãn tách riêng. Đây là số cột trong file, không phải số cột mọi mô hình sẽ sử dụng. Dữ liệu năm 2026 không được đưa vào huấn luyện/chọn mô hình cho bài kiểm tra năm 2025.

V1 hiện dùng diện tích toàn ô, khoảng 11.074 km² cho 93 ô. Cần tạo phiên bản trọng số theo giao ranh, rồi tạo lại cả X và y và đổi dataset ID. Không ghép nhãn theo trọng số mới với đầu vào theo trọng số cũ mà không công bố.

Thiếu bất kỳ phần ô bắt buộc nào thì thống kê biến đó thiếu; không tự đổi diện tích mẫu giữa các giờ hoặc điền mưa thiếu bằng 0. Cửa sổ train/cal/eval phải hợp lệ trên tập biến chung của các cấu hình đang so. Kiểm tra nhãn không âm, UTC, đầu/cuối khoảng, đơn vị gió/ẩm, nguồn thiếu CIN và tầng áp suất nằm dưới mặt đất. Quy tắc mã hóa CIN là lựa chọn xử lý phải lưu nguồn, không phải chứng minh mọi missing có cùng nguyên nhân.

Tệp nguồn đã được verify 2.233/2.233 và 22 kiểm thử liên quan đã đạt ở lượt tạo V1/V2. Các kiểm tra đó chứng minh tính toàn vẹn/xử lý trong phạm vi đã kiểm; không chứng minh lượng mưa thật chính xác.

## 5. Hai biểu diễn vùng và khung E0–E7

### 5.1. V1 và V2

V1 lấy trung bình theo diện tích cho từng biến, giữ các biến bối cảnh vùng có nguồn riêng. V2 giữ nguyên V1, thêm độ lệch chuẩn, phân vị 90%, cực đại, trung bình tiểu vùng, chênh lệch ven biển–miền núi và một số tương tác gió–ẩm–địa hình.

Các ngưỡng tiểu vùng được đặt từ địa hình trước khi xem nhãn; phải tính lại số ô nếu mặt nạ vùng thay đổi. Với một vùng cố định, độ cao trung bình là hằng số theo thời gian: không thêm tám cột tĩnh hằng rồi diễn giải đó là thí nghiệm đóng góp địa hình. Dùng phân tầng hoặc tương tác động, ghi rõ đây là thêm cách biểu diễn và thông tin địa hình, không phải nâng độ phân giải ERA5.

### 5.2. Nhóm đặc trưng không chồng lấn

Danh mục máy đọc được nằm trong feature_groups.json. Tên x ứng với cột mean__x trong V1; bốn cột lịch giữ tên. Không lấy toàn bộ 49/138 cột đưa vào mọi thí nghiệm.

| Nhóm | Biến nguồn | Số cột V1 |
| --- | --- | --- |
| B — nền | t2m, td2m, RH2m, áp suất bề mặt/MSLP, u10/v10; sin/cos giờ và ngày trong năm | 11 |
| A — nhiệt động, mây và đất | CAPE, CIN capped, has_lfc, TCWV, K-index, Total Totals, BLH, mây tổng/thấp/trung/cao, swvl1 | 12 |
| M — hoàn lưu và dòng ẩm | u/v/q/T/RH/omega 850; u/v/q/T/omega 500, shear; IVT u/v/độ lớn, VIMD; TCWV/IVT bối cảnh; hai chênh áp vùng | 20 |
| C — SST vùng | sst_region_c | 1 |

M là các proxy hoàn lưu/dòng ẩm, chưa phải chỉ số gió mùa đã xác nhận. C hiện chỉ có SST; không gọi kết quả đó là đã kiểm tra toàn bộ ENSO/MJO. ONI cũ không dùng; chỉ bổ sung chỉ số khí hậu sau khi xác minh thời điểm công bố và thiết kế riêng.

Mưa Gauge tương lai, cờ chất lượng, mưa ERA5 và ba cột raw không có trong đầu vào chính. wspd10 không thêm cùng u/v chỉ để tăng số cột; nó là ứng viên khác nếu sau này đăng ký phép so riêng.

| ID | Cấu hình | Số cột V1, gồm lịch |
| --- | --- | --- |
| E0 | B | 11 |
| E1 | B + A | 23 |
| E2 | B + M | 31 |
| E3 | B + C | 12 |
| E4 | B + A + M | 43 |
| E5 | B + A + C | 24 |
| E6 | B + M + C | 32 |
| E7 | B + A + M + C | 44 |

Ba phép so chính đăng ký trước là E1−E0, E2−E0, E3−E0. E4–E7 kiểm tra sự phối hợp và tác dụng có điều kiện; không chỉ chọn cặp đẹp nhất sau khi nhìn kết quả. Một nhóm chỉ tốt khi có nhóm khác là kết quả hợp lệ, không phải bằng chứng nhóm đó luôn có ích.

### 5.3. Nhánh phụ cố định trước

- S0: E0 cộng đặc trưng V2 có nguồn thuộc B; S7: E7 cộng các đặc trưng V2 không chứa mưa, chỉ từ nguyên liệu được phép. Ba proxy gió–ẩm–địa hình chỉ vào S7 khi đủ biến nguồn. Không để S0 nhận u850/CAPE qua cột không gian rồi vẫn gọi là B.
- Q0/Q7: E0/E7 cộng ba biến raw dịch trễ 4 giờ. Đây là độ nhạy hồi cứu; chưa tương đương GSMaP NRT thật và chưa chứng minh có sẵn lúc issue. Phân tích latency thêm chỉ là mở rộng sau khi nhánh này có ý nghĩa.
- Kiểm tra IMERG trên khoảng giao và mask/trọng số tương ứng. Nếu đổi nhãn để huấn luyện lại, phải so các cấu hình trên cùng tập thời gian giao; không so thẳng điểm của hai tập khác nhau.

Không chạy tích chéo tất cả V1/V2 × mọi latency × mọi nhãn × mọi kiến trúc ngay từ đầu. Chốt danh sách nhánh phụ trước khi huấn luyện, báo cáo mọi nhánh đã chạy kể cả kết quả âm.

## 6. Mô hình, loss và ngân sách

Bi-LSTM vùng: đầu vào [batch, 24 giờ, F], hai lớp hidden 64, dropout 0,1; đầu lượng mưa 6 giá trị không âm; đầu sự kiện 9 logits cho các khoảng 0–3, 3–6 và 0–6 giờ tại ngưỡng 1/10/25 mm. Không có chiều ô ở batch mẫu và không có nhánh tám static hằng. Có thể tái dùng khối Bi-LSTM, loss và đánh giá của repo, nhưng phải thay hợp đồng dữ liệu.

Giữ nhãn mm, dùng Tweedie p=1,5 cho lượng mưa, chuẩn hóa loss bằng null deviance từ train; BCE sự kiện không tăng trọng số lớp. Đây là cấu hình triển khai ban đầu, không phải kết luận Tweedie chắc chắn tối ưu cho mọi nhóm. Nếu thử loss khác, so cùng nhãn, thời gian, feature và ngân sách, tách khỏi kết luận về đặc trưng.

Chọn epoch theo RMSE của **tổng 3 giờ trên calibration tháng 5–10**, tính bằng mm thật; tiêu chí này cố định cho mọi E, không gọi sai số từng giờ là RMSE tổng 6 giờ. CSI/BSS vẫn là các chỉ số đánh giá chính được giữ từ D9. Platt và ngưỡng quyết định fit trên calibration; việc calibration còn chọn epoch phải ghi rõ, không coi điểm calibration là kiểm định độc lập.

LightGBM nhận cùng cửa sổ, biểu diễn bằng giá trị cuối/trung bình/thay đổi theo quá khứ và bốn biến lịch; có các đầu lượng mưa và sự kiện tương ứng. Cùng nguyên liệu nhưng khác biểu diễn/loss: đây là đối chứng mô hình, không khẳng định cô lập tuyệt đối kiến trúc.

Ngân sách đầu: batch 128 trên GPU 4 GB, tối đa 15 epoch, patience 4, Adam 0,001, seed 42/43/44. Máy 8 GB có thể tăng batch sau thử nhỏ nhưng phải cố định giữa các E. Dùng toàn bộ cửa sổ vùng train hợp lệ của mỗi fold, không sao chép ngân sách 30.000 mẫu ô từ thử nghiệm lưới vào bộ vùng nhỏ hơn. LightGBM deterministic dùng một seed nếu không sampling; không chạy ba bản cây giống nhau để tạo bất định giả.

Khung chính có 8 E × 3 fold × 3 seed = 72 lượt Bi-LSTM và 24 pipeline LightGBM. Bốn cấu hình phụ S0/S7/Q0/Q7 thêm 36 lượt NN và 12 pipeline cây nếu chạy đủ ba fold. Đo thời gian/RAM bằng một lượt thử trước khi lên lịch; không cam kết số giờ GPU chưa đo. Đọc Parquet vùng và tạo cửa sổ theo batch, không nạp cube nhiều GB thành nhiều bản RAM.

## 7. Chia dữ liệu và chống rò rỉ

| Lượt phát triển | Train | Calibration | Evaluation khám phá |
| --- | --- | --- | --- |
| 1 | 2015–2019 | 2020 | 2021 |
| 2 | 2015–2020 | 2021 | 2022 |
| 3 | 2015–2021 | 2022 | 2023 |
| Kiểm tra cuối sau khóa thiết kế | 2015–2023 | 2024 | 2025 |

Chia theo năm UTC của giờ đích đầu, bỏ cửa sổ có nhãn đi qua ranh năm; lịch sử có thể nhìn lùi sang phần trước. Mùa tính theo giờ Việt Nam của issue. Bước issue 6 giờ ở thí nghiệm chính, nên nhãn 6 giờ không chồng; khi thử phát hành mỗi giờ phải tách là cấu hình khác và giữ bootstrap theo khối.

Chuẩn hóa, cắt ngưỡng ngoại lai, chọn biến và ngưỡng phân vị chỉ fit trên train. Tập cửa sổ chung được xác định từ yêu cầu chất lượng, không từ giá trị điểm đánh giá. So cả E0–E7 trên cùng hàng train/cal/eval. Các năm 2021–2023 đã được xem nhiều lần nên chỉ là phát triển khám phá; dữ liệu 2026 không được dùng để lựa chọn cho bài test 2025.

Năm 2025 chỉ mở sau khi khóa ranh, nhóm biến, mô hình, loss, ngưỡng và protocol. Nếu sau đó sửa theo kết quả 2025, phải coi 2025 là đã dùng phát triển và cần kiểm tra tương lai khác. Không đồng thời dùng rolling tới 2025 để chọn cấu hình rồi lại gọi 2025 là holdout mới.

## 8. Baseline và đánh giá giữ theo mục tiêu

Baseline tối thiểu: luôn 0, khí hậu tháng×giờ học từ train, LightGBM cùng nguyên liệu và persistence có nguồn/mốc thời gian rõ ràng. Persistence raw lag4 được chấm cùng mẫu của nhánh Q; nếu đặt cạnh mô hình không có mưa quá khứ thì ghi rõ khác điều kiện thông tin. Persistence dùng Gauge quá khứ chỉ là tham chiếu hồi cứu lý tưởng hóa, không gọi là vận hành.

ECMWF không là cổng bắt buộc của nghiên cứu hiện tại. Giữ nguyên bảng mức sàn của nhóm trong đúng giao thức trạm/ngày. Chỉ tạo đối chứng ECMWF vùng khi có cùng issue, lead, valid interval, ranh, nhãn và mẫu; để tuyên bố vận hành còn phải chứng minh đầu vào AI có sẵn tại issue. Không so RMSE điểm của dev với RMSE vùng V1/V2 để chọn người thắng.

| Mùa/phạm vi | Điểm chính/phụ |
| --- | --- |
| Tháng 5–10, tổng 3 giờ | Chính: CSI ≥10 mm và BSS ≥1 mm, kèm reliability bắt buộc theo D9. Phụ: RMSE, bias, POD/FAR, MAE và số sự kiện |
| Tháng 11–2 | Chỉ số 6 giờ phụ; không dùng điểm 1/3 giờ để xác nhận kỹ năng chính. Kiểm chứng nhãn tổng ngày khi có trạm phù hợp |
| Tháng 3–4 và toàn năm | Bảng mô tả riêng, không gộp để che kết quả mùa bất lợi; RMSE/bias theo 3/6 giờ và số sự kiện |
| Nhãn tổng 24 giờ | QC theo ngày; mô hình 6 giờ không được báo điểm forecast 24 giờ. Hạn 24 giờ nếu làm sau phải có thiết kế riêng |

Ngưỡng 10 mm ở đây là **trung bình vùng**, không đồng nghĩa cấp mưa tại điểm; giữ ngưỡng từ D9 nhưng phải báo tần suất và không suy thành cảnh báo chính thức. Nếu một fold không có sự kiện, ghi chỉ số không xác định, không gán 0 để làm đẹp. BSS dùng cùng xác suất khí hậu học từ train; không dùng min(1, lượng mưa/ngưỡng) như xác suất đã hiệu chỉnh.

Bootstrap theo cặp, khối 5 ngày, ít nhất 1.000 lần, cùng thời điểm cho mọi cấu hình. Ba phép so chính × hai chỉ số được công bố đủ; nếu đưa ra tuyên bố ý nghĩa thống kê gộp, hiệu chỉnh nhiều phép so (ví dụ Holm) và mô tả cách gộp/năm. Bảng từng năm vẫn kèm effect size/CI; số seed không thay số đợt mưa độc lập. Phân tích độ nhạy khối dài hơn nếu đợt mưa kéo dài; không đổi khối để lấy CI mong muốn.

Chỉ nói “cải thiện lượng mưa” khi RMSE/bias hỗ trợ; CSI/BSS tăng riêng thì nói đúng là cải thiện sự kiện/xác suất. Báo cáo trade-off khi hai đầu đi khác chiều. Không có mục tiêu bắt buộc AI thắng ECMWF hoặc V2 thắng V1.

## 9. Kiểm chứng nhãn và giới hạn kết luận

Giữ NOAA GSOD là nguồn kiểm chứng hiện có, không có Vrain. Cần kiểm tra mốc tích lũy và cờ chất lượng; không mặc định ngày mang tên giống nhau luôn có cửa sổ tích lũy giống nhau. Trạm đo điểm và nhãn trung bình vùng khác hỗ trợ không gian; vài trạm không tự tạo chuẩn mưa diện tích đầy đủ.

GSMaP Gauge phụ thuộc CPC; chưa xác nhận từng trạm NOAA có/không tham gia hiệu chỉnh. IMERG là đối chiếu sản phẩm khác, không tự thành quan trắc độc lập hoàn hảo. Không có bằng chứng dưới ngày phù hợp thì phạm vi kết luận là dự đoán **sản phẩm mưa GSMaP trung bình vùng**. Khả năng dự đoán lượng mưa thực toàn Đà Nẵng phải có bằng chứng bổ sung.

Không dùng mưa ngày tốt để suy ra nhãn giờ tốt, không mặc định gộp 93 ô làm nhãn chính xác hơn. Giữ quyết định D10 và kiểm tra độ nhạy theo mùa; kết quả chính tháng 5–10 không đại diện quanh năm.

## 10. Những gì có thể dùng lại và những gì cần sửa

| Thành phần | Cách dùng |
| --- | --- |
| Cube mới, V1/V2, manifest và bộ chỉ số | Tái sử dụng; đóng phiên bản trọng số/ranh cuối trước thí nghiệm chính |
| Lớp Bi-LSTM, Tweedie/BCE, Platt | Tái sử dụng khối phù hợp; viết loader vùng và kiểm tra đầu ra mm |
| Khung E0–E7 của bạn thành viên | Giữ ý tưởng factorial; thay nguồn, nhãn và danh mục biến theo phương án này |
| full_features cũ | Giữ đối chứng lịch sử. Khi so đầu vào cũ/mới, mọi mô hình dùng cùng nhãn vùng và cùng mẫu; không giữ nhãn điểm khác nhau |
| Checkpoint và CSV E0–E7 trên dev | Chưa dùng làm kết quả xác nhận vì lỗi đơn vị, baseline và truy vết lượt chạy |
| Pipeline Bi-LSTM theo ô trước đây | Tài nguyên tham khảo, không phải loader của bài toán vùng chính |
| Demo/app, logger và pilot ECMWF | Lưu làm lịch sử/mở rộng; không chi phối công việc chính hiện tại |

Các lỗi đã có bằng chứng code phải sửa trước khi chạy: MSE sqrt thiếu bình phương ngược; chọn epoch nhầm sai số từng giờ thành tổng 6 giờ; persistence lệch dòng/cửa sổ; notebook Tweedie sao chép nhãn đích vào baseline; checkpoint và CSV không cùng truy vết. Kiểm tra các lỗi này không có nghĩa bác bỏ các bảng [CHỐT · BẰNG CHỨNG] của thí nghiệm trạm/ngày khác.

Mỗi run lưu commit, dataset ID/checksum, ranh/trọng số, feature list, split, seed, loss, siêu tham số, history, scaler, checkpoint và dự báo từng issue. Dữ liệu/checkpoint/dự báo từng dòng giữ ngoài Git; repo công khai giữ code, tài liệu và số liệu tổng hợp. Không commit tài liệu tham khảo PDF hoặc credential.

## 11. Trạng thái thực nghiệm để tránh hiểu nhầm

Pilot vùng LightGBM đã có, nhưng chưa phải E0–E7 Bi-LSTM vùng. V2 so V1 ở RMSE 3 giờ giảm khoảng 3,4% năm 2021, tăng khoảng 2,5% năm 2022, giảm khoảng 2,8% năm 2023; chỉ CI năm 2021 hoàn toàn phía cải thiện. Đây là bằng chứng thử tiếp, không là xác nhận bộ mới luôn thắng.

Đã có các pilot Bi-LSTM lưới 30/93 ô và một số ghi log nguồn; tài liệu nguồn ở commit e531982 ngày 11/10 chưa phản ánh các công việc này. Các điểm trên lưới, điểm cũ và điểm vùng có nhãn/không gian khác; không gộp thành một bảng thắng-thua.

Việc tạo tài liệu này không tạo loader huấn luyện vùng mới, không sửa xong mọi lỗi dev, không bổ sung ranh và không tạo kết quả mô hình mới. Chúng là các đầu việc cụ thể ở mục 12.

## 12. Lộ trình bàn giao theo đầu ra

| Giai đoạn | Công việc | Điều kiện hoàn thành |
| --- | --- | --- |
| G0 — dữ liệu vùng | Chốt ranh/mask/ô biên, trọng số; dựng lại V1/V2, nhãn Gauge/IMERG giao thời gian và QC | Manifest truy vết; X/y cùng vùng; báo cáo độ phủ và giới hạn nhãn |
| G1 — chạy tối thiểu đúng | Loader vùng; sửa loss/đơn vị/baseline; một E0/E7 nhỏ và kiểm tra suy luận | Nhãn tương lai không vào X; baseline cùng issue; checkpoint tái lập; không mở 2025 |
| G2 — ablation chính | E0–E7, Bi-LSTM ba seed, LightGBM, ba fold; freeze protocol | Bảng đầy đủ theo mùa/năm, số sự kiện, effect size và CI, cả kết quả âm |
| G3 — nhánh phụ | S0/S7, Q0/Q7, độ bền nhãn theo danh sách đã đăng ký | Tách lợi ích nguyên liệu, biểu diễn và mưa quá khứ; không đổi danh sách sau khi xem điểm |
| G4 — kết quả cuối | Khóa thiết kế; train/cal theo mục 7; chấm 2025 một lần | Bảng holdout, hạn chế kiểm chứng, báo cáo tái lập và bản viết nghiên cứu |

Phân công theo vai trò thay vì gán tên: một người phụ trách dữ liệu/nhãn vùng; một người phụ trách mô hình/loader; một người phụ trách đánh giá/tái lập. Mỗi đầu ra có người khác rà soát. Không tự đặt hạn nộp cuối tháng 12 hoặc cam kết 4–5 đêm GPU khi nhóm chưa xác nhận/đo.

Để đánh giá đúng C5 của mục 13 nguồn, dùng thêm **kịch bản giả định 10 tuần, RAM 8 GB và một GPU 8 GB**: tuần 1–2 dành G0/G1; tuần 3–5 G2; tuần 6–7 G3; tuần 8–10 G4 và viết báo cáo. Đây là phân bổ có điều kiện sau lượt đo thời gian đầu tiên, không phải xác nhận hạn nộp hoặc cam kết hoàn thành khi thiếu nhãn/ranh. Máy GPU 4 GB vẫn dùng batch nhỏ cho thử nghiệm; máy 8 GB ưu tiên huấn luyện chính. G0 có thể hoàn thành với giới hạn nhãn được công bố rõ, không yêu cầu xin được một mạng trạm giờ chưa có mới cho phép bắt đầu nghiên cứu hồi cứu.

Thứ tự cắt giảm nếu thiếu nguồn lực: app, TFT/hạn thứ hai, đa vùng, nhiều latency, thêm chỉ số khí hậu, rồi các nhánh phụ. Không cắt phép so cùng mẫu, chuẩn hóa train-only, kiểm tra nhãn và việc giữ kín holdout để đổi lấy nhiều mô hình.

## 13. Cách hòa giải từng khác biệt theo sáu tiêu chí

C1: nhãn có kiểm chứng với số đo thật? C2: đầu vào có sẵn tại thời điểm dự báo với đúng độ trễ? C3: cùng mẫu, baseline và khoảng tin cậy? C4: chỉ số phù hợp mưa hiếm? C5: khả thi với RAM/GPU và thời gian? C6: tái sử dụng được phần đã làm?

Giữ đủ sáu tiêu chí của mục 13 tài liệu nhóm. Riêng C2 được ghi rõ trạng thái “hồi cứu” thay vì giả vờ đã đạt vận hành; khi chuyển sang app thì vẫn phải qua kiểm tra as-of. Sáu tiêu chí là lập luận định tính có bằng chứng, không phải bảng điểm số tùy ý để ép một bên thắng.

Mỗi quyết định trong phụ lục A ghi phương án nhóm, phương án nghiên cứu, lựa chọn cuối và giải thích riêng C1–C6. Các mục bảo vệ được giữ ngay cả khi một phương án khác rẻ hơn; mong muốn vùng trực tiếp là chỉ dẫn hiện tại thay D3 [CHỐT · NHÓM], không phải kết quả đo chứng minh nó tốt hơn lưới.

## 14. Nguồn và phiên bản cần đọc

- TONG_HOP_DE_XUAT.md người dùng cung cấp, 477 dòng, tham chiếu e531982 ngày 11/10; các số liệu gốc giữ trong phạm vi tài liệu đó.
- Main d3f3936: [báo cáo V1/V2](https://github.com/nibsu05/PBL6/blob/d3f39360b8ab28e88be4b56310fbae10db8b9db7/reports/regional_danang_v1_v2/README.md), cùng catalog/manifest/run và CI. Dev fe27756: notebook E0–E7 và checkpoint đã rà soát.
- [Đối chiếu tài liệu nhóm](../research_rainfall/doi_chieu_TONG_HOP_DE_XUAT_2026_10_20.md); [rà soát Bi-LSTM dev](../research_rainfall/dev_bilstm_review_2026_10_20.md).
- [Open-Meteo Historical Weather](https://open-meteo.com/en/docs/historical-weather-api): xác minh cách chọn nguồn; không suy ngược thành định danh chắc chắn từng giờ cache cũ.
- [JAXA release note v8, trang 3](https://www.eorc.jaxa.jp/GPM/doc/product/ReleaseNote/08_note_GPM-GSMaP_20231110.pdf): giới hạn Gauge/CPC và khác biệt Gauge NRT.
- [Thông tư 08/2022, bản từ Cổng Chính phủ](https://datafiles.chinhphu.vn/cpp/files/vbpq/2022/07/08-btnmt.pdf), Điều 4–5: thuật ngữ hạn dự báo. Các ngưỡng mm của nghiên cứu phải nêu khoảng tích lũy và hỗ trợ không gian riêng.

## Phụ lục A. Quyết định từng điểm khác nhau

<!-- DECISIONS_START -->

### K01. Mục tiêu nghiên cứu hay sản phẩm app

**Phương án nhóm:** Hai sản phẩm và app, ưu tiên nguồn live/T-OPS (mục 4, 8, 10).

**Phương án nghiên cứu đã trao đổi:** Nghiên cứu đóng góp đặc trưng cho dự đoán vùng trực tiếp.

**Lựa chọn cuối:** Chọn định hướng người dùng hiện tại; app là mở rộng.

| Tiêu chí | Vì sao chọn |
| --- | --- |
| C1 — Kiểm chứng nhãn với số đo thật | Nguồn lực tập trung vào nhãn vùng và giới hạn kiểm chứng, thay vì mặc định dữ liệu live giải quyết được độ đúng của nhãn. |
| C2 — Đầu vào và độ trễ tại thời điểm dự báo | Chấp nhận phạm vi hồi cứu và ghi rõ chưa đạt as-of; không đổi nó thành tuyên bố có đầu vào vận hành. |
| C3 — Cùng mẫu, baseline và khoảng tin cậy | Ưu tiên các phép so cố định cùng dữ liệu, không lấy số điểm app/forecast khác mẫu ghép vào. |
| C4 — Chỉ số phù hợp sự kiện mưa hiếm | Giữ CSI/BSS và tách mùa của nhóm, dù không làm giao diện cảnh báo. |
| C5 — Khả thi với RAM, GPU và thời gian | Giảm công việc API, hosting, TFT và nhiều vùng; phù hợp nguồn lực đã có hơn. |
| C6 — Tái sử dụng công việc đã làm | Dùng lại dữ liệu, Bi-LSTM, LightGBM, loss và bộ chấm; demo/logger được lưu để dùng sau. |

### K02. Đầu ra vùng trực tiếp hay 93 ô rồi tổng hợp

**Phương án nhóm:** D3/D4: một mô hình chung dự đoán từng ô, tổng hợp để hiển thị tỉnh.

**Phương án nghiên cứu đã trao đổi:** Một mô hình nhận chuỗi đặc trưng vùng và xuất trực tiếp mưa vùng.

**Lựa chọn cuối:** Chọn người dùng: dự đoán vùng trực tiếp; D3 [CHỐT · NHÓM] được thay theo yêu cầu mới.

| Tiêu chí | Vì sao chọn |
| --- | --- |
| C1 — Kiểm chứng nhãn với số đo thật | Nhãn cũng phải là trung bình diện tích vùng. Trạm điểm chưa đủ xác nhận nhãn diện tích; cần công bố giới hạn này. |
| C2 — Đầu vào và độ trễ tại thời điểm dự báo | Tổng hợp không làm ERA5 có sẵn sớm hơn; giữ cùng điều kiện hồi cứu của nguồn. |
| C3 — Cùng mẫu, baseline và khoảng tin cậy | Mọi E dự đoán cùng một y vùng; không dùng điểm từng ô hoặc nhãn điểm cũ làm đối chứng ngang hàng. |
| C4 — Chỉ số phù hợp sự kiện mưa hiếm | Giữ ngưỡng D9 trên mưa trung bình vùng, ghi rõ khác ý nghĩa mưa tại điểm và báo số sự kiện. |
| C5 — Khả thi với RAM, GPU và thời gian | Một chuỗi vùng nhỏ hơn số cửa sổ ô; có thể dùng loader đơn giản và hai biểu diễn V1/V2. |
| C6 — Tái sử dụng công việc đã làm | Tái dùng cube và hai bản tổng hợp. Đây là lựa chọn đầu ra, chưa là bằng chứng vùng trực tiếp tốt hơn lưới. |

### K03. Giữ lựa chọn nhãn có bằng chứng

**Phương án nhóm:** D1/D2 [CHỐT · BẰNG CHỨNG]: Gauge chính, IMERG kiểm tra độ bền, không dùng mưa ERA5 cũ làm nhãn chính.

**Phương án nghiên cứu đã trao đổi:** Đã phản biện mức chắc chắn của nhãn giờ và tính độc lập, chưa có phép đo cùng giao thức tốt hơn.

**Lựa chọn cuối:** Giữ phía nhóm theo yêu cầu bảo vệ bằng chứng; thêm giới hạn phạm vi, không đổi nhãn chính.

| Tiêu chí | Vì sao chọn |
| --- | --- |
| C1 — Kiểm chứng nhãn với số đo thật | Giữ benchmark trạm/ngày làm bằng chứng sàng lọc; chưa suy ra nhãn giờ toàn vùng đúng hoặc độc lập CPC. |
| C2 — Đầu vào và độ trễ tại thời điểm dự báo | Gauge hồi cứu là y dùng để chấm sau sự kiện, không cần có sẵn lúc issue; không đưa Gauge giờ đích vào X. |
| C3 — Cùng mẫu, baseline và khoảng tin cậy | Kiểm tra IMERG trên khoảng giao cùng mask/mẫu; phép tính một trạm khác thời kỳ không thay bảng 10 trạm. |
| C4 — Chỉ số phù hợp sự kiện mưa hiếm | Duy trì kiểm tra mưa lớn theo ngưỡng, POD/FAR/bias và phân mùa, không chỉ tương quan trung bình. |
| C5 — Khả thi với RAM, GPU và thời gian | Đã có dữ liệu Gauge; chỉ bổ sung kiểm chứng/ranh còn thiếu thay vì đổi toàn bộ nguồn khi chưa có bằng chứng đủ. |
| C6 — Tái sử dụng công việc đã làm | Dùng lại permanent flag, cube, dữ liệu trạm và các script đánh giá của nhóm. |

### K04. Chỉ số lượng mưa và CSI/BSS

**Phương án nhóm:** D9 và mục 6.5 [CHỐT · BẰNG CHỨNG]: CSI/BSS chính, MAE không làm chính.

**Phương án nghiên cứu đã trao đổi:** Pilot trước báo RMSE/MAE và đề xuất đo trực tiếp lượng mưa.

**Lựa chọn cuối:** Giữ phía nhóm về CSI/BSS chính; bổ sung bắt buộc RMSE/bias và MAE phụ đúng mục 6.5.

| Tiêu chí | Vì sao chọn |
| --- | --- |
| C1 — Kiểm chứng nhãn với số đo thật | Điểm tốt chỉ mô tả kỹ năng với nhãn Gauge đã chọn; chưa thay kiểm chứng mưa thực. |
| C2 — Đầu vào và độ trễ tại thời điểm dự báo | Xác suất khí hậu, Platt và ngưỡng phải học từ train/cal, không từ evaluation tương lai. |
| C3 — Cùng mẫu, baseline và khoảng tin cậy | Tính mọi chỉ số trên cùng hàng; baseline xác suất so cùng reference; không chỉ dùng RMSE pilot để chọn thắng. |
| C4 — Chỉ số phù hợp sự kiện mưa hiếm | CSI/BSS phản ánh mưa hiếm; RMSE/bias ngăn diễn giải tăng phát hiện thành tăng độ đúng lượng mm khi thực tế có trade-off. |
| C5 — Khả thi với RAM, GPU và thời gian | Đầu sự kiện chín logits và công cụ Brier/reliability đã có, chi phí tăng nhỏ so với thêm một họ mô hình. |
| C6 — Tái sử dụng công việc đã làm | Tái dùng aggregate_targets, calibration và verification; bảng RMSE cũ vẫn là bằng chứng thăm dò phụ. |

### K05. Đánh giá mùa đông và phạm vi quanh năm

**Phương án nhóm:** D10 [CHỐT · BẰNG CHỨNG]: tháng 5–10 chấm giờ; mùa đông chỉ tổng 6/24 giờ; tách mùa.

**Phương án nghiên cứu đã trao đổi:** Phản biện việc suy raw bằng 0 thành Gauge chia đều, và mong muốn dự đoán cả vùng.

**Lựa chọn cuối:** Giữ D10; không bỏ mùa trong dữ liệu, không báo điểm 1/3 giờ mùa đông là kết quả chính.

| Tiêu chí | Vì sao chọn |
| --- | --- |
| C1 — Kiểm chứng nhãn với số đo thật | Kiểm chứng nhãn tổng ngày khi có GSOD phù hợp; điều đó chưa xác nhận mưa 6 giờ. Nhận định chia đều phải ghi là giới hạn cần kiểm tra. |
| C2 — Đầu vào và độ trễ tại thời điểm dự báo | Dùng cùng quy tắc nguồn hồi cứu giữa các mùa; không tự coi NRT và Gauge là một sản phẩm. |
| C3 — Cùng mẫu, baseline và khoảng tin cậy | Báo riêng 5–10, 11–2, 3–4 và cả năm; không chọn mùa thuận lợi sau khi nhìn kết quả. |
| C4 — Chỉ số phù hợp sự kiện mưa hiếm | Giữ ngưỡng và báo số sự kiện từng mùa; mẫu không có sự kiện được ghi không xác định. |
| C5 — Khả thi với RAM, GPU và thời gian | Mô hình hiện dự đoán 6 giờ: 24 giờ dùng QC nhãn, không tự phát sinh một mô hình ngày chỉ để đủ bảng. |
| C6 — Tái sử dụng công việc đã làm | Dùng lại season masks và điểm 6 giờ; số liệu mùa cũ giữ trong đúng phạm vi được đo. |

### K06. Một hạn chính hay đồng thời 0–6 giờ và 1–3 ngày

**Phương án nhóm:** D6 giữ Bi-LSTM; D7 chọn TFT cho hạn 1–3 ngày; hai sản phẩm chạy song song.

**Phương án nghiên cứu đã trao đổi:** Tập trung một câu hỏi đặc trưng cho đầu ra vùng.

**Lựa chọn cuối:** Chọn 24 giờ lịch sử → 6 giờ tương lai làm cấu hình chính; giữ lựa chọn TFT cho mở rộng 1–3 ngày.

| Tiêu chí | Vì sao chọn |
| --- | --- |
| C1 — Kiểm chứng nhãn với số đo thật | Một hạn giúp kiểm tra nhất quán nhãn theo thang thời gian cần dùng; không dùng độ đúng ngày để thay độ đúng 3 giờ. |
| C2 — Đầu vào và độ trễ tại thời điểm dự báo | Không cần lấy biến forecast nhiều ngày cho nghiên cứu hồi cứu đầu tiên; nguồn tương lai vẫn không được lẫn vào phép so chính. |
| C3 — Cùng mẫu, baseline và khoảng tin cậy | Cùng horizon, window, y và hàng đánh giá cho các nhóm, thay vì so kiến trúc ở hai nhiệm vụ khác nhau. |
| C4 — Chỉ số phù hợp sự kiện mưa hiếm | Giữ CSI/BSS cho 3 giờ và 6 giờ phụ; các ngưỡng mưa ngày của sản phẩm B được lưu cho nhánh ngày. |
| C5 — Khả thi với RAM, GPU và thời gian | Giảm một kiến trúc và nhiều thí nghiệm; không tự hứa cả hai họ mô hình hoàn thành trong số giờ GPU ước tính cũ. |
| C6 — Tái sử dụng công việc đã làm | Tái dùng các khối Bi-LSTM/6 đầu giờ và loss; ý tưởng TFT/Informer chưa bị xóa, chỉ không nằm trong phạm vi chính. |

### K07. full_features cũ hay bộ dữ liệu vùng mới

**Phương án nhóm:** Tài liệu nhóm đã đề xuất cube mới; thí nghiệm E0–E7 mới trên dev thực tế vẫn đọc full_features cũ.

**Phương án nghiên cứu đã trao đổi:** V1/V2 tổng hợp vùng có cùng y Gauge; giữ full_features như đối chứng riêng.

**Lựa chọn cuối:** Chọn bộ vùng mới cho mô hình chính, giữ chuỗi cũ làm đối chứng đầu vào trên cùng y vùng.

| Tiêu chí | Vì sao chọn |
| --- | --- |
| C1 — Kiểm chứng nhãn với số đo thật | Thay nhãn điểm bằng nhãn diện tích đúng mục tiêu; vẫn phải hoàn thiện ranh và xác minh nhãn, không coi dữ liệu mới mặc nhiên đúng hơn. |
| C2 — Đầu vào và độ trễ tại thời điểm dự báo | Cả hai bản là hồi cứu; đổi file không giải quyết việc nguồn có sẵn lúc vận hành. |
| C3 — Cùng mẫu, baseline và khoảng tin cậy | So đầu vào cũ/mới phải chuẩn hóa đơn vị/UTC và cùng y/hàng. Nếu muốn tách ảnh hưởng nguồn với cách lấy điểm, cần đối chứng điểm từ cùng cube. |
| C4 — Chỉ số phù hợp sự kiện mưa hiếm | Mưa cực đoan tại điểm và trung bình vùng có tần suất khác; không so trực tiếp CSI/RMSE của hai nhãn. |
| C5 — Khả thi với RAM, GPU và thời gian | Parquet vùng nhỏ hơn cube và đã có, phù hợp máy ít RAM; chưa cần dựng lại toàn bộ dataset quốc gia. |
| C6 — Tái sử dụng công việc đã làm | Giữ nguyên cube và file cũ; dùng builder, catalog, manifest và báo cáo pilot đã có trên main. |

### K08. Khung cộng dồn A0–A5 hay factorial E0–E7

**Phương án nhóm:** Mục 6.1/6.2: các nhóm A/B theo sản phẩm, cộng dồn và LOGO.

**Phương án nghiên cứu đã trao đổi:** B, A, M, C và đủ tám tổ hợp để đo thêm/bớt đặc trưng.

**Lựa chọn cuối:** Chọn E0–E7 theo mục tiêu nghiên cứu; định nghĩa lại nhóm từ các cột thực có, không chồng lấn.

| Tiêu chí | Vì sao chọn |
| --- | --- |
| C1 — Kiểm chứng nhãn với số đo thật | Giữ y Gauge và ranh cố định, không thay nhãn khi thêm nhóm; lợi ích chỉ được phát biểu trong phạm vi nhãn đó. |
| C2 — Đầu vào và độ trễ tại thời điểm dự báo | B/A/M/C của phép so chính chỉ dùng giờ quá khứ; SST không đồng nghĩa đã có ENSO/MJO kịp công bố. |
| C3 — Cùng mẫu, baseline và khoảng tin cậy | Tám E dùng chung mask hợp lệ, fold, seed và ngân sách; đăng ký E1/E2/E3 so E0 trước, các tương tác là phụ. |
| C4 — Chỉ số phù hợp sự kiện mưa hiếm | Đánh giá đủ CSI/BSS cùng RMSE/bias theo mùa; không chỉ giữ tổ hợp có một điểm CSI đẹp. |
| C5 — Khả thi với RAM, GPU và thời gian | Tám cấu hình và ba fold là hữu hạn; V2/latency/nhãn khác không được tích chéo toàn bộ ngay từ đầu. |
| C6 — Tái sử dụng công việc đã làm | Giữ ý tưởng E0–E7 từ dev, lấy nguyên liệu từ cube và catalog mới; không bê nguyên những cột cũ chưa có trong nguồn mới. |

### K09. ERA5 tại giờ đích trong A4/B3

**Phương án nhóm:** Thêm ERA5 future khi train rồi thay ECMWF lúc vận hành, đánh giá T-ERA5/T-OPS.

**Phương án nghiên cứu đã trao đổi:** Phép so chính dự đoán từ lịch sử, không có khí tượng tại giờ đích.

**Lựa chọn cuối:** Chọn quá khứ cho nghiên cứu chính; A4/B3 future là thí nghiệm riêng hoặc mở rộng forecast thật.

| Tiêu chí | Vì sao chọn |
| --- | --- |
| C1 — Kiểm chứng nhãn với số đo thật | Khí tượng giờ đích giúp khớp nhãn nhưng không làm nhãn đáng tin hơn; không dùng nó để chứng minh đặc trưng quá khứ dự báo tốt. |
| C2 — Đầu vào và độ trễ tại thời điểm dự báo | ERA5 giờ đích chưa tồn tại tại issue. Forecast tương lai chỉ hợp lệ khi đã được phát hành trước issue, với nguồn/mốc rõ ràng. |
| C3 — Cùng mẫu, baseline và khoảng tin cậy | Tách chế độ thông tin, không coi mức tăng do thấy trạng thái khí tượng tương lai là hiệu quả thêm biến quá khứ. |
| C4 — Chỉ số phù hợp sự kiện mưa hiếm | Giữ ngưỡng và y khi có thí nghiệm riêng; không ghép CSI/BSS của oracle với bảng causal/hồi cứu từ lịch sử. |
| C5 — Khả thi với RAM, GPU và thời gian | Chưa cần giải quyết toàn bộ kho 850 hPa forecast để làm được nghiên cứu vùng chính. |
| C6 — Tái sử dụng công việc đã làm | Dùng lại code past-only và future calendar; loader forecast/oracle cũ được lưu để mở rộng có nhãn chế độ rõ ràng. |

### K10. Mưa vệ tinh và thí nghiệm độ trễ

**Phương án nhóm:** D13: raw dịch L giờ, nhiều mức latency là đóng góp chính của sản phẩm A.

**Phương án nghiên cứu đã trao đổi:** Tách lợi ích khí tượng và không gian khỏi lợi ích mưa quá khứ; chưa ưu tiên app.

**Lựa chọn cuối:** Kết hợp: không dùng mưa trong E0–E7 chính; Q0/Q7 thêm raw lag4 như nhánh hồi cứu riêng.

| Tiêu chí | Vì sao chọn |
| --- | --- |
| C1 — Kiểm chứng nhãn với số đo thật | Raw và Gauge cùng họ thuật toán; tăng điểm với Gauge chưa tự chứng minh tăng độ đúng trạm, nên cần nhánh không raw. |
| C2 — Đầu vào và độ trễ tại thời điểm dự báo | Dịch 4 giờ trong archive chưa chứng minh tương đương NRT; giữ chú thích này và kiểm tra nguồn trước mọi tuyên bố vận hành. |
| C3 — Cùng mẫu, baseline và khoảng tin cậy | Q0/Q7 và persistence raw có cùng issue/lag/mẫu; đối chứng Gauge tức thời được gắn lý tưởng hóa. |
| C4 — Chỉ số phù hợp sự kiện mưa hiếm | Đo riêng CSI/BSS và bias theo mùa; không đặt trước raw gần nhất luôn giúp ở hạn 1–3 giờ. |
| C5 — Khả thi với RAM, GPU và thời gian | Hai cấu hình phụ trước thay vì lưới nhiều latency nhân mọi E; mở rộng khi câu hỏi latency thực sự là trọng tâm. |
| C6 — Tái sử dụng công việc đã làm | Tái dùng ba cột raw/lân cận, phép dịch cửa sổ và nghiên cứu latency đã có; logger không bị bỏ mất. |

### K11. Địa hình tĩnh và biểu diễn V2

**Phương án nhóm:** Mỗi mẫu ô có tám biến tĩnh; mô hình phân biệt các vị trí.

**Phương án nghiên cứu đã trao đổi:** Mẫu là cả vùng nên trung bình địa hình cố định không biến thiên theo thời gian.

**Lựa chọn cuối:** Chọn biểu diễn vùng: dùng tiểu vùng và tương tác động trong S0/S7, không lặp tám cột hằng rồi gọi là thêm địa hình.

| Tiêu chí | Vì sao chọn |
| --- | --- |
| C1 — Kiểm chứng nhãn với số đo thật | Đổi biểu diễn không tạo chuẩn nhãn mới; kiểm chứng cùng nhãn và ranh giữa V1/V2. |
| C2 — Đầu vào và độ trễ tại thời điểm dự báo | Địa hình có trước issue; proxy động chỉ được tính từ khí tượng quá khứ, không từ mưa tương lai. |
| C3 — Cùng mẫu, baseline và khoảng tin cậy | S0 chỉ lấy nguồn thuộc B; S7 theo nguồn E7. Nêu rõ khi thêm kiến thức phân vùng/địa hình, không gọi là cùng lượng thông tin tuyệt đối. |
| C4 — Chỉ số phù hợp sự kiện mưa hiếm | Trung bình vùng có thể che cực đại cục bộ; điểm vùng không chứng minh dự đoán tốt mưa to tại một xã. |
| C5 — Khả thi với RAM, GPU và thời gian | Dùng thống kê/zone có sẵn thay vì một mô hình ảnh lưới mới; chỉ hai nhánh phụ để kiểm tra. |
| C6 — Tái sử dụng công việc đã làm | Tái dùng V2, DEM, zone masks và proxy. Nếu ranh đổi phải dựng lại thống kê và ghi số ô/diện tích mới. |

### K12. Loss và bộ mô hình ban đầu

**Phương án nhóm:** Bi-LSTM log1p/Huber+BCE, TFT, nhiều baseline và bảng so kiến trúc 2×2.

**Phương án nghiên cứu đã trao đổi:** Bi-LSTM vùng đầu mm với Tweedie+BCE và LightGBM trước; sửa bản MSE sqrt trên dev.

**Lựa chọn cuối:** Kết hợp kiến trúc nhóm và thực nghiệm đã có: Bi-LSTM Tweedie+BCE ban đầu, LightGBM đối chứng; chưa làm bảng 2×2.

| Tiêu chí | Vì sao chọn |
| --- | --- |
| C1 — Kiểm chứng nhãn với số đo thật | Loss tối ưu với nhãn Gauge, không tự xác nhận nhãn thật; thang mm phải đúng khi chấm. |
| C2 — Đầu vào và độ trễ tại thời điểm dự báo | Loss và mạng không thay quy tắc đầu vào; không đưa label vào feature hay persistence. |
| C3 — Cùng mẫu, baseline và khoảng tin cậy | Giữ loss/hyperparameter/budget trong mỗi họ giữa các E; nếu so loss thì làm phép so riêng cùng mẫu. |
| C4 — Chỉ số phù hợp sự kiện mưa hiếm | Tweedie cho lượng mưa, BCE cho xác suất; báo cả hai vì cải thiện lượng mm có thể làm xác suất xấu đi. |
| C5 — Khả thi với RAM, GPU và thời gian | Hai họ mô hình, hidden64/batch128 và thử ngắn trước; không coi Tweedie chắc chắn tốt nhất cho vùng khi chưa chạy. |
| C6 — Tái sử dụng công việc đã làm | Tái dùng lớp LSTM, TweedieJointLoss, Platt và verification; thay loader vùng và sửa lỗi đơn vị/baseline đã thấy. |

### K13. ECMWF là cổng bắt buộc hay đối chứng mở rộng

**Phương án nhóm:** D8/D12 và mục 7: phải so ECMWF thô, T-OPS và khoảng cách vận hành.

**Phương án nghiên cứu đã trao đổi:** Nghiên cứu hồi cứu tập trung giá trị đặc trưng; kho forecast tương ứng chưa đủ cho mọi biến.

**Lựa chọn cuối:** Chọn ưu tiên nghiên cứu; giữ bảng bằng chứng mục 7, đưa đối chứng ECMWF vùng vào khi dữ liệu so sánh phù hợp.

| Tiêu chí | Vì sao chọn |
| --- | --- |
| C1 — Kiểm chứng nhãn với số đo thật | Cùng nhãn Gauge vùng và kiểm chứng đúng phạm vi; bảng trạm/ngày trước đây không phải chuẩn 3 giờ toàn tỉnh. |
| C2 — Đầu vào và độ trễ tại thời điểm dự báo | Muốn nói vận hành phải chứng minh cả forecast và đầu vào AI có sẵn tại issue; past ERA5 hồi cứu chưa đạt điều kiện đó. |
| C3 — Cùng mẫu, baseline và khoảng tin cậy | ECMWF mới phải cùng issue/lead/valid time/ranh/mẫu; BSS của forecast 0/1 không ngang với xác suất AI đã hiệu chỉnh nếu không nêu rõ. |
| C4 — Chỉ số phù hợp sự kiện mưa hiếm | Giữ các điểm BSS/CSI gốc đúng giao thức; không suy BSS âm trong bảng thành mọi forecast tất định vô ích. |
| C5 — Khả thi với RAM, GPU và thời gian | Không chặn toàn bộ nghiên cứu bởi kho forecast/850 hPa còn thiếu; không hứa AI đã thắng vận hành. |
| C6 — Tái sử dụng công việc đã làm | Tái dùng baseline và pilot forecast hiện có cho bước mở rộng, không vứt kết quả trước. |

### K14. Chia năm, test và độ chắc chắn

**Phương án nhóm:** Train 2015–2021, val 2022–2023, 2024 val-ops, 2025 test; rolling tới 2025.

**Phương án nghiên cứu đã trao đổi:** Ba fold 2021–2023 đã khám phá, chốt thiết kế trước khi mở 2025; 2024 dùng calibration cuối.

**Lựa chọn cuối:** Kết hợp: giữ chia thời gian/seed/bootstrap; chọn ba fold phát triển và final train2015–2023/cal2024/test2025.

| Tiêu chí | Vì sao chọn |
| --- | --- |
| C1 — Kiểm chứng nhãn với số đo thật | Mỗi fold giữ nhãn/ranh cố định; thiếu kiểm chứng độc lập cuối 2025 vẫn phải ghi rõ. |
| C2 — Đầu vào và độ trễ tại thời điểm dự báo | Mọi fit scaler/threshold từ train/cal quá khứ; không đưa 2026 vào thiết kế mô hình được chấm trên 2025. |
| C3 — Cùng mẫu, baseline và khoảng tin cậy | Cùng cửa sổ chung cho mọi E, không vượt năm ở nhãn, bootstrap theo cặp. Năm đã xem là phát triển, không gọi lại là test mới. |
| C4 — Chỉ số phù hợp sự kiện mưa hiếm | Báo số sự kiện/CI từng mùa và hiệu chỉnh nhiều phép so cho các kết luận chính; seed không thay số đợt mưa. |
| C5 — Khả thi với RAM, GPU và thời gian | Ba fold là mức phát triển chính; không nhân rolling test trên mọi năm/nhãn/latency và rồi chọn theo holdout. |
| C6 — Tái sử dụng công việc đã làm | Tái dùng logic rolling-origin, common mask và bootstrap; cột năm UTC/season VN được ghi rõ để tránh nhầm với notebook cũ. |

### K15. Nguồn kiểm chứng và diễn giải phạm vi

**Phương án nhóm:** D14: NOAA GSOD, không Vrain, chỉ mưa ngày và phạm vi thời gian đã có.

**Phương án nghiên cứu đã trao đổi:** Không muốn mặc định nhãn giờ hay trung bình vùng được bảo đảm từ vài trạm.

**Lựa chọn cuối:** Giữ ràng buộc D14, bổ sung giới hạn hỗ trợ không gian/thời gian; không bịa thêm trạm giờ.

| Tiêu chí | Vì sao chọn |
| --- | --- |
| C1 — Kiểm chứng nhãn với số đo thật | Kiểm tra cờ và giờ kết thúc tích lũy; GSOD điểm/ngày chưa là chuẩn diện tích/giờ, Gauge có thể phụ thuộc CPC. |
| C2 — Đầu vào và độ trễ tại thời điểm dự báo | Dữ liệu kiểm chứng được phép đến sau forecast vì dùng chấm; đầu vào mưa trạm chưa được giả định có lúc issue. |
| C3 — Cùng mẫu, baseline và khoảng tin cậy | Chỉ so nguồn trên ngày/trạm giao nhau; khi đổi sang y vùng phải ghi đây là bài toán khác bảng trạm. |
| C4 — Chỉ số phù hợp sự kiện mưa hiếm | Phân tích các đợt mạnh và sai số bỏ sót/báo sai; không chỉ dùng tương quan để xác nhận nhãn. |
| C5 — Khả thi với RAM, GPU và thời gian | Tận dụng nguồn đã có; không hứa đánh giá mưa thực từng xã hay toàn năm cuối 2025 khi thiếu tham chiếu. |
| C6 — Tái sử dụng công việc đã làm | Giữ registry, bộ lọc chất lượng và bảng cặp ngày; IMERG dùng như kiểm tra độ bền sản phẩm chứ không phong làm chân lý. |

### K16. Phạm vi vùng, lịch trình và phần mở rộng

**Phương án nhóm:** Thêm Hà Nội/miền nam, nhiều kiến trúc, app và 10 tuần tới hạn nộp giả định.

**Phương án nghiên cứu đã trao đổi:** Một vùng, một hạn, đầu ra nghiên cứu theo cổng bằng chứng; hạn nộp chưa được xác nhận.

**Lựa chọn cuối:** Chọn người dùng: Đà Nẵng trước, lộ trình G0–G4; các mở rộng có điều kiện.

| Tiêu chí | Vì sao chọn |
| --- | --- |
| C1 — Kiểm chứng nhãn với số đo thật | Tập trung ranh và nhãn vùng chính trước khi khái quát Việt Nam; không lấy thêm vùng để che điểm yếu kiểm chứng. |
| C2 — Đầu vào và độ trễ tại thời điểm dự báo | Chỉ khi chuyển sang vận hành mới đưa logger/as-of thành cổng chính; nguồn hiện tại vẫn được ghi đúng hồi cứu. |
| C3 — Cùng mẫu, baseline và khoảng tin cậy | Giữ protocol và holdout dù cắt số mô hình; đối chứng dữ liệu thống nhất quan trọng hơn nhiều tên mạng. |
| C4 — Chỉ số phù hợp sự kiện mưa hiếm | Không cắt việc tách mùa, số sự kiện và CI để kịp giao diện; vẫn báo kết quả âm. |
| C5 — Khả thi với RAM, GPU và thời gian | Đo RAM/thời gian trên một run trước; bỏ app/TFT/đa vùng trước khi giảm độ chặt phương pháp. |
| C6 — Tái sử dụng công việc đã làm | Tái dùng gói dữ liệu/manifest và code hiện có; lưu kế hoạch nhiều vùng để nối tiếp sau kết quả vùng đầu tiên. |

### K17. Trạng thái đã làm và bảng kết quả dev

**Phương án nhóm:** Mục 9 nói chưa huấn luyện dữ liệu mới; commit dev có CSV E0–E7 được đặt tên lượng mm.

**Phương án nghiên cứu đã trao đổi:** Main đã có pilot lưới/vùng; rà soát dev phát hiện lỗi thang đo, baseline và checkpoint lệch CSV.

**Lựa chọn cuối:** Chọn trạng thái đã đối chiếu code/artifact; sửa lỗi và truy vết trước khi tái sử dụng số điểm dev.

| Tiêu chí | Vì sao chọn |
| --- | --- |
| C1 — Kiểm chứng nhãn với số đo thật | Các kiểm thử và nạp checkpoint không xác nhận nhãn thực; chúng chỉ kiểm tra đúng đường dữ liệu/chấm. |
| C2 — Đầu vào và độ trễ tại thời điểm dự báo | Baseline không được lấy chính y_test cần dự đoán; sửa persistence theo issue và nguồn quá khứ. |
| C3 — Cùng mẫu, baseline và khoảng tin cậy | Lưu run ID, checksum, commit, feature list, scaler và prediction; không ghép checkpoint từ run khác với CSV cũ. |
| C4 — Chỉ số phù hợp sự kiện mưa hiếm | Sqrt chưa đổi ngược làm sai đơn vị ngưỡng CSI; không dùng bảng đó làm bằng chứng mưa to hoặc thắng V1/V2. |
| C5 — Khả thi với RAM, GPU và thời gian | Kiểm tra suy luận nhỏ trước huấn luyện dài; không chạy lại cả lưới thí nghiệm khi lỗi cơ bản chưa sửa. |
| C6 — Tái sử dụng công việc đã làm | Tái dùng kiến trúc và ý tưởng thí nghiệm; giữ artifact cũ làm lịch sử, không ghi đè rồi mất khả năng truy vết. |

### K18. Tên nguồn và mức chắc chắn của bằng chứng

**Phương án nhóm:** Nhãn cũ được gọi ERA5; bảng ngày và raw/Gauge được dùng làm căn cứ cho quyết định.

**Phương án nghiên cứu đã trao đổi:** Code Best Match chưa khóa ERA5; kiểm chứng ngày chưa đủ xác nhận giờ; chưa đo cùng giao thức để thay quyết định.

**Lựa chọn cuối:** Giữ các quyết định bảo vệ và số liệu đúng phạm vi; bổ sung provenance/giới hạn, không đổi bằng điểm khác cách đo.

| Tiêu chí | Vì sao chọn |
| --- | --- |
| C1 — Kiểm chứng nhãn với số đo thật | Chưa gắn định danh nguồn không được biến thành kết luận ERA5 thuần; kết quả ngày không xác nhận mọi giờ/vùng. |
| C2 — Đầu vào và độ trễ tại thời điểm dự báo | Giữ khác biệt archive/NRT và forecast/reanalysis; không coi tên nguồn giống nhau là cùng độ trễ/cách xử lý. |
| C3 — Cùng mẫu, baseline và khoảng tin cậy | Mọi đề nghị thay D1/D2/D9/D10 phải đo lại cùng mẫu/thời kỳ/ngưỡng/protocol; audit khác thiết kế chỉ thêm giới hạn. |
| C4 — Chỉ số phù hợp sự kiện mưa hiếm | Giữ các bảng CSI/BSS mưa lớn của nhóm nhưng ghi đúng đại lượng và hỗ trợ không gian; không cấm MAE phụ ngoài ý mục 6.5. |
| C5 — Khả thi với RAM, GPU và thời gian | Làm rõ provenance bằng code/metadata ít tốn hơn đổi toàn bộ dữ liệu do một kết luận bị diễn giải quá rộng. |
| C6 — Tái sử dụng công việc đã làm | Giữ kết quả gốc và liên kết script, đồng thời dùng các báo cáo phản biện để tránh lặp nhận định chưa được xác nhận. |

<!-- DECISIONS_END -->

## Phụ lục B. Sổ bằng chứng gốc được giữ

Các số dưới đây được giữ theo tài liệu nhóm và chỉ là kết quả trong giao thức gốc, không phải số đo mới của mô hình vùng. Ghi nguồn như tài liệu mô tả, đồng thời chú thích định danh Open-Meteo/ERA5 chưa được khóa trong code cũ. Không dùng phép tính khác mẫu để thay những con số này.

| Căn cứ | Số liệu tài liệu nhóm ghi | Phạm vi phải giữ |
| --- | --- | --- |
| D1/mục 3.1 | 3.453 ngày chung; trạm có 51 ngày ≥100 mm, nhãn cũ có 11 và trùng 4; POD khoảng 0,08, CSI khoảng 0,07 | Trạm Đà Nẵng, 2015–2024, mưa ngày, nhãn Open-Meteo cũ; không tự quy thành toàn bộ ERA5 thuần hoặc nhãn vùng |
| D2/mục 3.2 | 13.836 trạm-ngày, 437 sự kiện ≥50 mm; CSI ≥50: Gauge 0,33, IMERG 0,22, nhãn cũ 0,17 | 10 trạm, 2021–2024, cùng tập trạm/ngày và giao thức nguồn |
| D2/CI | Gauge − nhãn cũ: ΔCSI ≥50 = +0,16; CI 95% [0,11; 0,21] | Bootstrap theo cặp, khối 5 ngày, 1.000 lần theo giao thức gốc; không thay bằng CI một trạm/giai đoạn khác |
| D9/mục 3.1 | Bi-LSTM cũ MAE 0,326 so với luôn 0 là 0,265; Informer 0,309 so với luôn 0 là 0,230 | Các tập thử cũ tương ứng; lý do không dùng riêng MAE để đánh giá mưa hiếm, không phải so hai mô hình khác tập |
| D10/mục 3.4 | Audit gốc ghi khoảng 56% mưa nhãn mùa đông ở giờ raw bằng 0; mùa 5–10 khoảng 25% | Giữ phạm vi/ngưỡng raw/mùa của audit gốc khi tái lập; khác với audit 93 ô raw ≤0,01 mm. Không dùng tỷ lệ này như chứng minh độc lập về cơ chế chia đều |
| Mục 7 | ECMWF trước 1 ngày CSI ≥50 = 0,16; nguồn được gọi ERA5 trong bảng = 0,17; CI chênh [−0,04; 0,03] | 5.313 trạm-ngày, 02/2024–08/2025; không phải điểm forecast vùng 3 giờ |
| Mục 7/BSS | Các nguồn tất định trong bảng có BSS âm khi chuyển sang dự báo sự kiện 0/1 | Giữ đúng cách tính so reference khí hậu; không kết luận mọi forecast tất định hoặc mọi phương pháp hiệu chỉnh xác suất đều thua |

Các hạn chế vốn đã nêu trong tài liệu nhóm vẫn giữ: Gauge có thể phụ thuộc trạm CPC; sai số mưa núi/mùa đông; nguồn kiểm chứng ngày hạn chế. Muốn thay quyết định được bảo vệ phải có báo cáo tái lập cùng cách đo và chỉ rõ thay điều gì; không chỉ đưa một điểm tốt hơn từ mô hình/nhãn khác.
