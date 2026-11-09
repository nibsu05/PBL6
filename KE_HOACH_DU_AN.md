# Kế hoạch hiện hành — dự báo mưa tại trạm

Người dùng chốt ngày09/11/2026: **cả cực ngắn và ngắn đều dự báo theo trạm**. Đây là mục tiêu hiện tại; các kế hoạch mưa trung bình vùng đã chuyển thành tài liệu lịch sử.

## 1. Phạm vi và phân công

Nhóm dữ liệu Đà Nẵng trong tài khoản Vrain, không phải toàn Việt Nam. Có86 vị trí trong registry, chưa chốt dùng đủ86. Chọn trạm theo phạm vi, lịch sử và QC trước huấn luyện.

| Nhánh | Người phụ trách | Nhãn tại chính trạm |
| --- | --- | --- |
| Cực ngắn | Thành viên Bi-LSTM | Sáu lượng mưa giờ tiếp theo, 1–6h |
| Ngắn | Người dùng, LightGBM/TFT/Informer | Ba tổng24hriêng của ngày1/2/3 |

Mỗi kiến trúc dự kiến dùng một mô hình chung cho nhiều trạm. Một mẫu là `(trạm, thời điểm phát dự báo)`, không cần86 mô hình riêng cho mỗi kiến trúc.

## 2. Dữ liệu đã có

- Vrain lịch sử2021–2024 theo trạm, source/QC ở `data/operational/vrain_2026_11_09/`.
- Số trạm có ít nhất một số giờ sauQC theo năm: 57/79/79/82 cho2021/22/23/24; chưa nói đủ cả năm.
- Bổ sung02/01–08/11/2026 đã tải riêng hai kênh, chưa ghép/fit;2025 giữ kín.
- ERA5 theo ô đã có; **chưa dựng predictor theo tọa độ trạm**. Predictor trung bình vùng trong ZIP cũ không phải đầu vào trạm.

## 3. Trạng thái hiện tại

Đã đổi mục tiêu trong tài liệu và xác minh phạm vi danh mục. Đã có nguồn trạm, chưa có dataset/loader/train theo trạm đã nghiệm thu. Không còn phải đợi giải quyết trung bình diện tích vùng để làm nhãn chính.

Vẫn cần xác nhận đơn vị, timezone, đầu/cuối kỳ và QC. Chưa có căn cứ nói số đo hai kênh2026 tương đương; không tự nối.

## 4. Thứ tự thực hiện

| Bước | Bàn giao cụ thể |
| --- | --- |
| Chốt phạm vi trạm | Registry chung; danh sách đủ điều kiện theo từng nhánh; lý do loại, không ép đủ86 |
| Xác minh thời gian/QC | Interval giờ, cờ thiếu/lỗi, tổng ngày đúnganchor, nguồn và ngày lấy |
| Predictor trạm | ERA5 tại/gần tọa độ trạm, trường context/SST có chủ đích; kiểm tra trạm ngoài miềncube |
| Dataset và loader | Hai độ phân giải; một mẫu/trạm/issue; nhãn của chính trạm; mask chung khi so model/E |
| Pilot nhóm đại diện | Một nhóm trạm có lịch sử đủ, gồm điều kiện địa lý khác nhau; baseline, kiểm tra leak và replay vài mẫu |
| Mở rộng | Thêm trạm đạtQC, dùng mô hình chung; giữ cách đánh giá từng trạm và tổng hợp |
| E0–E7 | Cùng mẫu/split; Rgiữcốđịnh; đủ ba mô hình nhánh ngày nếu pilot đủ dữ liệu |
| Kiểm định cuối | Khóa protocol trước mở2025; không tuning2026 để chọn mô hình |

## 5. Đánh giá

MAE/RMSE/Bias lượng mưa; CSI/POD/FAR và BS/BSS nếu có đầu ra xác suất. Ngưỡng phải hợp trạm và kỳ đo, chưa mặc định ngưỡng vùng cũ. Báo từng trạm/mùa/chân trời và macro-average để trạm nhiều số không lấn trạm ít số. Các cửa sổ và trạm trong cùng đợt mưa phụ thuộc nhau; không coi như mẫu độc lập.

## 6. Tài liệu và quy ước

[README](README.md) là điểm vào; [thiết kế theo trạm](project_plan_v2.md) là tài liệu gửi nhóm. Metadata phạm vi ở `docs/station_forecast_scope.json`.

Làm trênresearch/tft-regional, push/PR#1, không tự merge. Raw/registry/tọa độ/credential/model ngoàiGit. Giữ nguyên slide người dùng sửa. Không đổi tên kết quả CPC/GSMaP vùng cũ thành kết quả Vrain tại trạm.
