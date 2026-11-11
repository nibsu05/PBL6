# Bàn giao dữ liệu Vrain và ERA5 — 09/11/2026

**Mục tiêu vẫn là dự đoán trực tiếp lượng mưa trung bình vùng Đà Nẵng mới.** Không đổi sang dự đoán một trạm hoặc từng ô. Tuy nhiên, cần phân biệt ba việc: đã tải nguồn, đã thống nhất mã trạm và đã có nhãn vùng đủ tin cậy. Hai việc đầu có thể hoàn thành trước khi việc thứ ba được kiểm chứng.

## 1. Vì sao có cả 82 và 86? Đã thống nhất được chưa?

Đây là hai danh mục mà hai kênh Vrain trả về, không phải hai mạng độc lập để cộng thành 168 trạm:

| Đối chiếu trực tiếp metadata | Kết quả |
| --- | ---: |
| Danh mục kênh cũ | 82 mục |
| Danh mục kênh hiện hành | 86 mục |
| Trạm cũ có tọa độ khớp chính xác, duy nhất với một mục mới | **82/82** |
| Trong các cặp khớp: tên giữ nguyên | 81 |
| Trong các cặp khớp: tên khác | 1 |
| Vị trí trong danh mục mới chưa có mục tương ứng ở danh mục cũ | **4** |

**Chốt cách quản lý: một danh mục chuẩn gồm 86 mã `ST001`–`ST086`.** Mỗi trạm có mã nguồn cũ/mới tương ứng; không dùng tên làm khóa nối. Tọa độ giống nhau là bằng chứng đối chiếu metadata hiện tại. Nó chưa chứng minh thiết bị, vị trí lịch sử hoặc phép đo đã liên tục không thay đổi.

Mọi thành viên dùng đúng registry đã đóng phiên bản. Nếu sau này có thêm trạm, giữ mã cũ và cấp mã tiếp theo; không tự chạy lại cách sắp xếp rồi đánh số lại toàn mạng.

Ví dụ minh họa: mã `OLD_A` và `NEW_B` cùng khớp duy nhất một vị trí sẽ được quản lý dưới mã chuẩn `STxxx`; đây vẫn là một vị trí trạm. Một mục chỉ có ở kênh mới sẽ có trường mã cũ để trống. Lịch sử thiếu không được tự tạo ra khi đổi mã.

**Số trạm trong danh mục khác số trạm có số đo tại một thời điểm.** Đổi 82 mã cũ sang danh mục 86 không làm 4 cột thiếu xuất hiện số liệu. Khi hai kênh cùng có số, phải so sánh và lưu nguồn; không cộng hai giá trị của cùng một trạm, không tự lấy trung bình hai kênh.

Bảng ánh xạ chứa tọa độ và mã nguồn nằm trong gói riêng của nhóm, không đưa lên GitHub công khai. Mã tạo ánh xạ: `src/vrain_station_identity.py`; từ chối ghép khi tọa độ trùng nhiều trạm hoặc không khớp.

## 2. Chốt được những phần nào?

| Thành phần | Quyết định hiện tại |
| --- | --- |
| Nguồn mưa | Vrain tại trạm; giữ số gốc và cờ QC |
| Nguồn khí tượng đầu vào | ERA5 quá khứ; không lấy mưa tương lai vào đầu vào |
| Danh mục chung | 86 vị trí theo metadata hiện tại, có 82 ánh xạ cũ–mới |
| Kho lịch sử đã kiểm kê | Bảng giờ cho 1.461 ngày được chọn từ **01/01/2021 đến 31/12/2024**; 35.064 hàng giờ, vẫn có thiếu theo trạm |
| Yêu cầu 2015–2020 | Đã lưu phản hồi nhưng không có hàng giờ; không được gọi là các ngày không mưa |
| Bổ sung gần đây | Thu thập riêng hai kênh cho **02/01/2026–08/11/2026**; kết quả thực tế trong `docs/vrain_data_freeze.json` sau khi hoàn tất kiểm tra |
| Năm 2025 | Chưa đọc, giữ kín cho thiết kế đánh giá cuối |
| Nhãn mưa trung bình toàn vùng | **Chưa chốt để huấn luyện chính thức**, vì còn vấn đề thời gian và đại diện không gian bên dưới |
| Chạy lại ba mô hình trên Vrain | Chưa thực hiện; không đổi tên kết quả CPC/GSMaP cũ thành kết quả Vrain |

Khoảng thời gian ở bảng là **ngày được chọn trên nguồn**. Bảng của một ngày có các cột 20:00 hôm trước đến 19:00 ngày đó. Đó chưa phải khẳng định khoảng 00:00–24:00 UTC. Không lấy nhãn ngày của CPC áp sang Vrain.

Không tải ngày được chọn 01/01/2026 vì cửa sổ của nó chứa giờ 31/12/2025. Các khoảng thiếu năm 2025 trong gói hiện tại là chủ đích giữ kín, không phải kết luận Vrain không có dữ liệu năm đó.

## 3. Vì sao chưa thể nói “dữ liệu đã bảo đảm”?

### Thời gian

Nguồn có hàng theo giờ thật ở định dạng bảng; không phải mưa ngày được chia thành 24 phần bằng nhau. Tuy nhiên, vẫn cần xác nhận chính thức múi giờ, timestamp là đầu hay cuối khoảng đo, đơn vị và loại tích lũy. Có mẫu XLSX ghi tiêu đề kết thúc 19:20 trong khi cột cuối là 19:00. Gói nguồn giữ nhãn đồng hồ nguyên trạng; chưa gắn UTC tùy ý.

Một mẫu huấn luyện chỉ hợp lệ khi biết chính xác các giờ đầu vào đã kết thúc trước giờ phát dự báo và các giờ nhãn thực sự nằm sau đó. Tự giả định rồi gọi đó là thông tin đã xác nhận có thể gây lệch nhãn hoặc rò rỉ dữ liệu.

### Không gian — phát hiện quan trọng từ kiểm kê toàn kho

Đã thử trọng số Thiessen cố định trên footprint cũ R93, với **toàn bộ 82 vị trí lịch sử**. Mỗi vị trí đại diện một phần diện tích; coverage là tổng trọng số của các trạm có số đo hợp lệ trong giờ đó. Đây là coverage theo mô hình Thiessen, không phải chứng nhận diện tích đã được quan trắc trực tiếp.

| Kiểm tra trên R93 và metadata hiện tại | 2021 | 2022 | 2023 | 2024 |
| --- | ---: | ---: | ---: | ---: |
| Coverage lớn nhất trong một giờ, toàn mạng cố định | **70,0%** | **83,5%** | **83,5%** | 100% |
| Số ngày đủ 24 giờ, mỗi giờ đủ 100% trọng số toàn mạng | **0** | **0** | **0** | 69 |

Như vậy, tải đủ 1.461 bảng ngày không đồng nghĩa có đủ nhãn vùng theo quy tắc nghiêm ngặt. Một số vị trí đại diện diện tích lớn chưa có số trong những năm đầu.

Nếu chỉ chọn trạm rất đầy đủ trong **2021 và 2022** — không dựa vào điểm mô hình hay số đo năm 2025 — có thể giữ 45 trạm với độ đầy đủ mỗi năm ít nhất 98%. Nhưng trên R93, khoảng cách lớn nhất từ tâm một ô đến trạm gần nhất tăng từ khoảng **34 km lên 59 km**; khoảng cách trung bình tại các tâm ô vùng núi tăng từ khoảng **13 km lên 30 km**. Đây là đổi độ phủ không gian lấy độ đầy đủ thời gian, chưa phải một cải thiện đã được chứng minh.

Vì vậy, **không chốt tùy tiện panel 45 trạm rồi gọi nhãn của nó là lượng mưa thực đo đáng tin cậy toàn Đà Nẵng**. Cũng không âm thầm đổi trọng số mỗi giờ theo trạm còn số. Một estimator cho mạng thiếu có thể nghiên cứu, nhưng phải ghi công thức, coverage, bất định và kiểm chứng trước khi dùng làm nhãn chính.

93 ô là cách biểu diễn vùng của bộ ERA5 cũ; 86 là danh mục trạm Vrain. Hai số đếm hai loại đối tượng khác nhau. Trọng số Thiessen phân chia vùng theo vị trí trạm; nó không tạo thêm quan trắc ở nơi không có trạm.

### Ranh vùng

R93 là hợp của 93 ô đầy đủ 0,1°, diện tích khoảng 11.074 km²; hiện vẫn là footprint xấp xỉ Đà Nẵng mới, chưa phải polygon hành chính chính xác. Nó dùng được để chẩn đoán vì nhất quán với bộ đầu vào cũ, nhưng chưa đủ để khẳng định nhãn đại diện chính xác toàn địa giới hoặc các phần đảo. Nếu đổi ranh, phải tính lại cả X lẫn y.

## 4. Đặc trưng đầu vào gồm những gì?

**Vrain hiện cung cấp mưa tại trạm. Các biến khí tượng dưới đây lấy từ ERA5**, không phải tự có đầy đủ trong Vrain.

| Nhóm | Số kênh giờ / ngày | Thông tin |
| --- | ---: | --- |
| B — nền | 11 / 9 | Nhiệt độ 2 m, điểm sương, độ ẩm tương đối, áp suất bề mặt và mực biển, gió u/v 10 m; sin/cos ngày trong năm; nhánh giờ thêm sin/cos giờ |
| A — đối lưu, mây, lớp biên, đất | 12 / 12 | CAPE, CIN đã giới hạn, has_lfc, TCWV, K-index, Total Totals, độ cao lớp biên, bốn mức che phủ mây, ẩm đất lớp 1 |
| M — hoàn lưu và vận chuyển ẩm | 20 / 20 | u/v/q/T/omega ở 850 và 500 hPa, thêm RH850; đứt gió 850–500; IVT u/v/độ lớn; VIMD; bối cảnh TCWV/IVT; hai chênh áp |
| C — nhiệt độ biển | 1 / 1 | SST của hộp biển đã chọn; chưa phải một bộ đầy đủ ENSO/MJO |
| R — tùy chọn, tách khỏi E0–E7 | Chưa chốt | Mưa Vrain vùng trong quá khứ, chỉ có sau khi chốt estimator và xử lý thiếu |

| Cấu hình | Nhóm biến | Số kênh giờ | Số kênh ngày |
| --- | --- | ---: | ---: |
| E0 | B | 11 | 9 |
| E1 | B + A | 23 | 21 |
| E2 | B + M | 31 | 29 |
| E3 | B + C | 12 | 10 |
| E4 | B + A + M | 43 | 41 |
| E5 | B + A + C | 24 | 22 |
| E6 | B + M + C | 32 | 30 |
| E7 | B + A + M + C | **44** | **42** |

Đây là số kênh đầu vào, không phải số mẫu hoặc số trạm. Gói bàn giao chứa 44 kênh ERA5 theo giờ trước năm 2025 và danh sách nhóm. **Chưa xuất đầu vào ngày** khi chưa chốt cửa sổ 24h để ghép đúng với nhãn Vrain. Các cột mưa GSMaP và nhãn cũ không được đưa vào tệp predictor này.

Kiểm tra tệp predictor bàn giao có **35.808 hàng**, từ 01/12/2020 đến hết 2024 để giữ lịch sử đầu vào trước nhãn 2021. Có **21 hàng thiếu K-index và Total Totals**, tổng 42 ô thiếu; giữ nguyên NaN, không tự điền 0. Khi tạo tập train phải dùng mask chung cho mọi E/model hoặc quy tắc bù thiếu chỉ fit trên train và công bố rõ.

## 5. Nhóm làm gì tiếp theo?

1. **Dùng chung danh mục 86 và bảng alias đã tạo.** Không mỗi thành viên tự ghép tên hoặc tự đổi mã. Giữ nguyên nguồn của từng số đo.
2. **Xác nhận hợp đồng thời gian với Vrain**: đơn vị, timezone, đầu/cuối kỳ và cửa sổ ngày; lưu bằng chứng. Khi đó mới chuẩn hóa UTC và gộp ngày.
3. **Giải quyết nhãn vùng trước khi train lại toàn ma trận**: xác minh ranh, lịch sử vị trí/trạm và khả năng bổ sung lịch sử ở vùng núi. Nếu phải dùng estimator mạng thiếu, đánh giá độ nhạy, rút trạm theo khối thời gian và sai lệch theo địa hình; nêu giới hạn với mưa trung bình vùng.
4. Sau khi nhãn đạt yêu cầu, pilot E0/E2/E7 và R0/R1, kiểm tra số mẫu thực còn lại. Chia theo lịch sử, toàn bộ nhãn phải nằm trong split; scaler chỉ fit train. Đăng ký thiết kế đánh giá trước khi mở 2025.
5. Nhánh giờ dự kiến X 24 giờ → sáu lượng giờ tiếp. Nhánh ngày dự kiến X bảy ngày → ba tổng 24h riêng. LightGBM/TFT/Informer phải cùng mẫu, cùng nhãn và E0–E7; CSI/BSS kèm POD/FAR và lỗi lượng mưa. Đây là thiết kế dự kiến, **chưa phải kết quả chạy Vrain**.

**Kết luận bàn giao:** đã có cơ sở thống nhất danh mục và nguồn; chưa có bằng chứng để đóng dấu “bộ nhãn vùng đã bảo đảm”. Đếm 82 hay 86 không phải trở ngại chính sau khi có bảng ánh xạ. Trở ngại chính là lịch sử đo không đầy đủ đều trên không gian và hợp đồng thời gian chưa được xác nhận.

## 6. Vị trí tệp

- Thống kê công khai, không chứa từng trạm: [`docs/vrain_data_freeze.json`](../../docs/vrain_data_freeze.json).
- Gói riêng gửi thành viên: `data/operational/vrain_2026_11_09/PBL6_VRAIN_SOURCE_V1.zip`.
- Bản giải nén: `data/operational/vrain_2026_11_09/handoff_v1/`.
- `station_registry_private.csv`: 86 mã chuẩn, alias hai kênh và trạng thái xác minh.
- `station_source_values_2021_2024.parquet`: 35.064 hàng đồng hồ nguồn × 86 cột trạm; bốn vị trí chỉ có trong danh mục mới để thiếu; ba station-day chênh tổng được loại bằng cờ QC. Ma trận gốc vẫn được giữ riêng để hoàn tác.
- `era5_predictors_hourly_44.parquet`: khí tượng quá khứ 44 kênh, không có nhãn GSMaP cũ.
- `manifest.json` cùng raw manifests: checksum và nguồn để kiểm tra; không có mật khẩu/cookie.

Gói ZIP là **bản nguồn đã kiểm kê**, không phải gói huấn luyện có nhãn vùng đã duyệt. Dữ liệu từng trạm chỉ chia sẻ trong nhóm theo phạm vi được phép; GitHub chỉ chứa mã, tài liệu và thống kê tổng hợp.
<!-- GENERATED_RECENT_AUDIT -->

## 7. Kiểm kê bổ sung 2026 sau khi tải xong

| Kênh | Phản hồi đã kiểm tra SHA | Ngày có hàng giờ | Ngày có ít nhất một số đo |
| --- | ---: | ---: | ---: | ---: |
| Cũ | 311 | 87 | 87 |
| Hiện hành | 311 | 311 | 305 |

Đối chiếu hai kênh tại cùng ngày, nhãn đồng hồ và mã chuẩn: **367** cặp có số ở cả hai phía; **46** cặp có mưa ở ít nhất một phía; **46** cặp khác nhau quá 1e-6 đơn vị nguồn. Phần trùng chỉ thuộc **1 vị trí** trên **18 ngày**; **27** cặp có mưa ở kênh cũ nhưng bằng 0 ở kênh mới. Đây chưa phải kiểm chứng tương đương số đo cho cả 82 cặp vị trí. Phép so này chỉ bao phủ các cặp cùng có số, không xác nhận các khoảng không trùng, lịch sử vị trí hoặc ngữ nghĩa thời gian. Gói này vẫn giữ hai nguồn riêng, chưa tự nối thành chuỗi huấn luyện.
