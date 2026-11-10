# Kế hoạch hiện hành — dự báo mưa tại trạm

**Cập nhật được duyệt 10/11/2026:** nhánh ngắn hạn triển khai NWP+Vrain, LightGBM chính và GRU nhỏ theo gatecal; TFT/Informer không còn bắt buộc. [Thiết kế mới](docs/short_range_nwp_design.md), protocol trướcfit ở `reports/gfs_station_pilot_2026_11_10/protocol.json`. Các mô tảERA5v1 bên dưới là dữ liệu đã bàn giao, không phải thí nghiệmNWP mới.

Thứ tự hiện tại: khóa20trạm/theo train → trích208issueGFS lịch cố định mỗi7ngày → ghép đúng khoảng và cutoffquantrắc → replayraw/kiểmtra → đốichứng/A0–A3LightGBM → GRUnhỏnếugatecalđạt → báo cáo. Saupilot mới mở rộng hằng ngày nếu có cơ sở.2025giữkín,2026khôngtuning.

**Pilot đã hoàn thành:**208issue,20trạm,1.774/902/983mẫu train/cal/dev; LightGBM A0–A3 vàGRU_A2ba seed đã chạy. [Báo cáo](reports/gfs_station_pilot_2026_11_10/BAO_CAO_PILOT.md), [Word](reports/gfs_station_pilot_2026_11_10/BAO_CAO_PILOT.docx). CI A2−GFS cả ba hạn còn chứa0, nên chưa khẳng định cải thiện ổn định.47tests vàreplaynguồn/môhìnhđạt. Bước tiếp: protocol mới để kiểmchứng bằng lịch hằng ngày, độnhạytrễ vàdrop-group; không thay pilotcũ hoặc mở2025.

Người dùng chốt ngày09/11/2026: **cả cực ngắn và ngắn đều dự báo theo trạm**. Đây là mục tiêu hiện tại; các kế hoạch mưa trung bình vùng đã chuyển thành tài liệu lịch sử.

## 1. Phạm vi và phân công

Nhóm dữ liệu Đà Nẵng trong tài khoản Vrain, không phải toàn Việt Nam. Có86 vị trí trong registry, chưa chốt dùng đủ86. Chọn trạm theo phạm vi, lịch sử và QC trước huấn luyện.

| Nhánh | Người phụ trách | Nhãn tại chính trạm |
| --- | --- | --- |
| Cực ngắn | Thành viên Bi-LSTM | Sáu lượng mưa giờ tiếp theo, 1–6h |
| Ngắn | Người dùng, GFS+LightGBM/GRU theo phương án mới | Ba tổng24hriêng của ngày1/2/3 |

Mỗi kiến trúc dự kiến dùng một mô hình chung cho nhiều trạm. Một mẫu là `(trạm, thời điểm phát dự báo)`, không cần86 mô hình riêng cho mỗi kiến trúc.

## 2. Dữ liệu đã có

- Vrain lịch sử2021–2024 theo trạm, source/QC ở `data/operational/vrain_2026_11_09/`.
- Số trạm có ít nhất một số giờ sauQC theo năm: 57/79/79/82 cho2021/22/23/24; chưa nói đủ cả năm.
- Bổ sung02/01–08/11/2026 đã tải riêng hai kênh, chưa ghép/fit;2025 giữ kín.
- Đã dựng predictor tại tọa độ82trạm từ bốn nút ERA5 gốc0,25°, không dùng trung bình vùng trong ZIPcũ. Nguồn native ở `data/raw_data/gee/era5/grid/`.

## 3. Trạng thái hiện tại

**Đã có dataset/loader theo trạm qua kiểm tra ghép.** Một file `data/processed/station_v1/PBL6_TRAM_GIO_NGAY_V1.parquet` chứa cả1h/24h. Có82trạm lịch sử,79trạm có cửa sổ train;2.995.050hàng và2.480.367cửa sổ đã kiểm tra.34testsđạt. Chưa train mô hình trạm; không coi kiểm tra cấu trúc là chứng nhận cảm biến.

Người dùng xác nhận10:00là tổng09–10hViệtNamUTC+7; nguồn hiển thị mm. Ngày giữ anchor19→19h, đủ24giờ. Chưa có căn cứ nói số đo hai kênh2026 tương đương; không tự nối.2025giữkín.24trạm có dưới180mẫungàytrain; đây là một giới hạn cho pilot.

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

Các bước dựng dữ liệu/loader đã đạt kiểm tra ghép; **bước tiếp theo là pilot mô hình**, không phải tải lại mọi nguồn. Dùng `sample_ready_r1` chung mọiE/model/R, fit scaler chỉtrain, báo từngtrạm/horizon/mùa. File Word ngắn gửi nhóm: `reports/station_data_handoff_2026_11_09/MO_TA_DU_LIEU.docx`; ví dụ loader ở `HUONG_DAN_TRAIN.md` cùng thư mục.

## 5. Đánh giá

MAE/RMSE/Bias lượng mưa; CSI/POD/FAR và BS/BSS nếu có đầu ra xác suất. Ngưỡng phải hợp trạm và kỳ đo, chưa mặc định ngưỡng vùng cũ. Báo từng trạm/mùa/chân trời và macro-average để trạm nhiều số không lấn trạm ít số. Các cửa sổ và trạm trong cùng đợt mưa phụ thuộc nhau; không coi như mẫu độc lập.

## 6. Tài liệu và quy ước

[README](README.md) là điểm vào; [thiết kế theo trạm](project_plan_v2.md) là tài liệu gửi nhóm. Metadata phạm vi ở `docs/station_forecast_scope.json`.

Làm trênresearch/tft-regional, push/PR#1, không tự merge. Raw/registry/tọa độ/credential/model ngoàiGit. Giữ nguyên slide người dùng sửa. Không đổi tên kết quả CPC/GSMaP vùng cũ thành kết quả Vrain tại trạm.
