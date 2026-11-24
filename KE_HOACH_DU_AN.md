# Kế hoạch hiện hành — dự báo mưa tại trạm

**Cực ngắn đã kiểm định trên 79 trạm.** Mô hình chung dự báo đủ sáu lượng mưa giờ. Thực hiện R/E0/E2, ba seed, đối chứng 0 mm, giữ mưa và LightGBM R. Kiểm định 2025 cho thấy LightGBM R giảm RMSE so với giữ mưa, còn lợi ích của nhóm gió 850 hPa tại giờ 6 chưa rõ. Web có phát lại riêng theo giờ. Xem [kết quả và phạm vi](reports/station_nowcast_2026_11_24/README.md).

**Phần ngắn hạn đã chốt ngày 24/11.** Đóng góp chính là đo được lợi ích của nhóm khí tượng GFS ở ngày 2, 3 trên kiểm định 2025. Báo cáo Word hai nhánh theo mẫu Khoa CNTT nằm trong thư mục nội bộ `data/operational/pbl6_bao_cao_cuoi_ky_2026_11_24/`. Xem [kết luận](reports/gfs_short_range_closeout_2026_11_24/KET_LUAN_NGAN_HAN.md), [kiểm chứng chạy lại](reports/gfs_short_range_closeout_2026_11_24/verification.json) và [bản đồ phát lại](demo/station_map/README.md).

**Thử cải thiện tiếp.** Điều chỉnh lượng có điều kiện là ứng viên kiểm định trong các đợt mưa mới. Hồi cứu 2026 cho thấy giảm sai số ở nhóm thực đo ≥50 mm, đồng thời sai số toàn bộ có đánh đổi. Xem [kết quả ba phép thử](reports/gfs_gated_amount_2026_11_24/KET_LUAN.md).

**Chuẩn bị chạy hằng ngày.** Đã đăng ký tác vụ thử thu 18h40 và chấm lượt đến hạn lúc 20h05. Web nối vào các bản ghi dự báo thật sau khi kiểm tra tệp và thời hạn. Lần kiểm tra 24/11 cả hai đường lấy Vrain lỗi 404, nên cần khôi phục nguồn rồi theo dõi nhiều lượt, độ phủ và độ trễ. Bản Word cập nhật có bảng chi tiết xử lý, hình web và kiểm thử. Xem [web và lịch chạy](demo/station_map/README.md).

**Bản trình bày dễ hiểu:** [slide/Word giải thích từ đầu](reports/short_range_explained_v2_2026_11_18/README.md), 33 slide chính (~28 phút) và 34 phụ lục. Tách rõ LightGBM/GRU, GFS, MOS và quy tắc đối chứng. Giải thích một mẫu, train/CV, Tweedie/L2 và ý nghĩa số; tách rõ ba mốc tốt hơn đối chứng, cải thiện ổn định và đủ dùng thực tế. Hồi cứu mới cho thấy giảm điểm lỗi; chưa chứng nhận sử dụng. Không huấn luyện/chấm mới hoặc sửa nghiên cứu cũ.

**Slide tổng hợp 18/11:** [bộ báo cáo đầy đủ](reports/short_range_comprehensive_2026_11_18/README.md), 31 slide chính (~28 phút) và 31 phụ lục, Notes/Word dễ đọc. Chỉ đọc bằng chứng hiện có, không train/chấm mới hoặc đổi protocol. Paper gốc và giới hạn truy cập được ghi rõ. Giữ riêng kiểm định2025 cũ và hồi cứu2026 mới; tiến trình dự báo tương lai vẫn đang chờ, chưa có nhãn kiểm chứng.

**Đã hoàn thành phần hồi cứu 18/11:** [báo cáo và slide](reports/gfs_training_window_2026_11_18/README.md). Bốn cấu hình A–D và N0/N1/N3 chạy đủ; 52 tests/kiểm chứng 48.639 hàng/3.000 metric đạt. Thêm năm giảm điểm RMSE Tweedie nhưng chưa đủ chắc chắn; D−C ngày 3 là 1/12 phép đạt tiêu chí thăm dò, ablation 0/6. Giữ phương án B cho theo dõi tương lai theo CV và cửa sổ dài định trước, không chọn lại bằng 2026. Báo cáo Word, 28 slide, CSV và gói nội bộ một Parquet đã ghép vai trò mới hoàn tất. Đã bật tiến trình giới hạn một issue 19h ngày 18/11, chờ kiểm chứng từ 20h ngày 21/11; cần máy/mạng hoạt động. Trạng thái thật trong private live/tracker.json, không bật tiến trình trùng. Các đoạn dưới giữ thiết kế và trạng thái lịch sử.

**Đang thực hiện theo phê duyệt18/11:** [protocol mới](reports/gfs_training_window_2026_11_18/protocol.json) tách tác động số năm train2021–22/2021–24 và lossTweedie/L2 trong bốn cấu hình LightGBM, cùng57trạm/26biến/ba seed/ngân sách. Phiên bản này cho phép2025 hiệu chỉnh xác suất/cutoff; không fit trọng số2025–26. Tuning chỉ2022, loss cho ablation chọnCV,2026hồi cứu tách API. Sau bốn cấu hình, lặpN0/N1/N3 và kiểm tra mưa lớn/ngày khô. Bắt đầu ledger nguồn/dự báo trướcissue cho kiểm chứng tương lai; chưa thể có kết quảprospective ngay. Bi-LSTM tiếp tục để sau; nghiên cứu cũ giữ nguyên. Đọc progress/verification trước báo trạng thái.

**Hoàn thành vòng bổ sung 18/11:** [diễn biến GFS trong ngày](reports/gfs_temporal_2026_11_17/README.md), [kết luận](reports/gfs_temporal_2026_11_17/KET_LUAN.md). Đã lấy đủ 2.120 ngày, dựng 107.822 mẫu ba hạn, chạy LightGBM T0–T3 và GRU T0/T3/LINEAR23. Đã kiểm chứng 163.023 hàng/4.320 metric, 42 tests đạt; giữ 225 artifact cũ. Chưa có cải thiện RMSE ổn định qua 12 phép so chính, nên chưa chốt mặc định 49 biến. Một số CSI/FAR đổi theo cutoff, cần đọc cùng POD và BSS. Giữ phương án đã kiểm chứng trước làm tham chiếu. 2025/2026 ở vòng mới là hồi cứu; bước tuning hoặc mở rộng năm train tiếp theo cần protocol riêng và giai đoạn kiểm định mới. Bi-LSTM để sau theo yêu cầu.

**Hoàn thành kiểm chứng cuối 17/11/2026:** người dùng đã duyệt cả năm bước, gồm kiểm định 2025 sau khóa và đánh giá riêng 2026. [Báo cáo và bằng chứng](reports/gfs_station_final_2026_11_17/README.md). Hai đối chứng GRU, 17 phương án, cùng tập 57 trạm; test 2025 có 18.723 mẫu trạm–issue. 2026 tách legacy/modern, không chứng nhận liên tục. Đã kiểm tra 104.808 hàng kiểm định và các metric/seed/bootstrap độc lập; 26 tests đạt. Không có fit/tuning trên 2025/2026, không thay mô hình chính sau test. Các mô tả “2025 kín” bên dưới là trạng thái lịch sử trước lần phê duyệt này. Giai đoạn hiện tại là đọc và trình bày kết quả kiểm định; nghiên cứu chỉnh mô hình tiếp theo cần xác định lại vai trò dữ liệu và một tập kiểm định chưa dùng.

**Bổ sung nhánh giờ 17/11/2026:** [bộ ERA5–Vrain theo trạm](reports/station_hourly_era5_2026_11_17/README.md), một file đã ghép 44 kênh khí tượng/lịch, mưa quá khứ và sáu nhãn giờ. Khí tượng ghép tới hàng mưa kết thúc 07h ngày 11/11/2026 giờ Việt Nam, mưa tới 19h ngày 15/11; giữ thiếu ở đuôi. Danh mục có 86 vị trí, 79 có train; mask chung yêu cầu cùng API trong 24 giờ lịch sử và 6 nhãn. Loader `HourlyStationData` trong module mới giữ nguyên guard V1. Không train/chấm mới; bộ ngày GFS 16/11 và các thí nghiệm cũ không đổi. Chưa xác nhận tính liên tục hai API là giới hạn nguồn, không gọi độ phủ là độ chính xác.

**Cập nhật dữ liệu 16/11/2026:** theo yêu cầu mới, thu thập/QC 2025–2026 và dựng bản riêng [station_update_2026_11_16](reports/station_update_2026_11_16/README.md). Nguồn tới 15/11/2026; issue đủ ba nhãn tới 12/11/2026. Giữ nguyên thí nghiệm 2021–2024, chưa train/chấm mới. 2025 đã thu thập trong kho mới; mục tiêu tiếp theo là kiểm định sau khóa lựa chọn, không còn coi toàn bộ nguồn 2025 chưa được đọc. Dữ liệu2026 có đổi kênh và độ phủ không đều; chưa nối thành chuỗi đồng nhất để fit toàn bộ. Các trạng thái11/11 và trước đó phía dưới giữ bối cảnh phiên bản cũ.

**Báo cáo slide 11/11/2026:** [bản daily-v2 41 slide và ghi chú](reports/gfs_daily_slides_2026_11_11/README.md), diễn giải đầu vào/đầu ra, chia năm, tuning, N0–N5 và bảng kết quả dev 2024. Đã tách rõ 2025 là tập dành kiểm định cuối sau khóa phương án; làm slide không huấn luyện hoặc mở test.

**Hoàn thành 11/11/2026:** cả bốn đề xuất theo [protocol hằng ngày v2](reports/gfs_station_daily_v2_2026_11_10/protocol.json): issue hằng ngày/độ trễ; ZERO/MOS và mean–median; N0–N5 tách biến thô khỏi dẫn xuất; xác suất lồng nhau/tuning chỉ train. 72.886 mẫu/218.658 hàng, 57 trạm, train/cal/dev 35.116/18.365/19.405. Đã train và replay288 estimatorLightGBM/6GRU, kiểm tra2.106 metric;179tests đạt. [Báo cáo](reports/gfs_station_daily_v2_2026_11_10/BAO_CAO_HANG_NGAY_V2.md), [kết luận](reports/gfs_station_daily_v2_2026_11_10/KET_LUAN.md). Chưa mở2025, chưa chứng minh latency vận hành. Bước tiếp theo là chọn/đóng băng cấu hình cuối theo mục tiêu hoặc định nghĩa protocol bổ sung; không tự mở test. Các đoạn dưới mô tả giai đoạn trước.

**Trạng thái mới nhất:** đãmở rộng NWP lên57trạm, cùngtiêuchí train và lịch mỗi7ngày; LightGBM A0–A3/GRUba seed đã chạy. [Báo cáo57](reports/gfs_station_57_2026_11_10/BAO_CAO_MO_RONG.md), [Word](reports/gfs_station_57_2026_11_10/BAO_CAO_MO_RONG.docx). Pilot20giữ nguyên.79trạm cótrain là nhóm rộng hơn,22trạm còn lịch sử ngắn chưatrain trongbản57. Mởrộng sốtrạm không bảo đảm tăngskill; đãso trên cùng20trạm vàcùngissue, không so hai trung bình kháccohort.

**Cập nhật được duyệt 10/11/2026:** nhánh ngắn hạn triển khai NWP+Vrain, LightGBM chính và GRU nhỏ theo gatecal; TFT/Informer không còn bắt buộc. [Thiết kế mới](docs/short_range_nwp_design.md), protocol trướcfit ở `reports/gfs_station_pilot_2026_11_10/protocol.json`. Các mô tảERA5v1 bên dưới là dữ liệu đã bàn giao, không phải thí nghiệmNWP mới.

Thứ tự triển khai pilot20trạm trước đó: khóa20trạm/theo train → trích208issueGFS lịch cố định mỗi7ngày → ghép đúng khoảng và cutoffquantrắc → replayraw/kiểmtra → đốichứng/A0–A3LightGBM → GRUnhỏnếugatecalđạt → báo cáo. Nay đã mở rộng57trạm như đầu file; mở rộng hằng ngày vẫn là bước kiểmchứng tiếp theo.2025giữkín,2026khôngtuning.

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
