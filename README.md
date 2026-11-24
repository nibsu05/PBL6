# PBL6 — dự báo lượng mưa tại nhiều trạm

**Chốt phần ngắn hạn ngày 24/11/2026.** Kiểm định 2025 cho thấy nhóm biến khí tượng GFS giảm RMSE khoảng 0,83 mm ở cả ngày 2 và ngày 3. LightGBM B đã được chạy lại trên 43.464 lượt trạm và khoảng dự báo của hồi cứu 2026. Web cục bộ có bản đồ dự báo, xác suất mưa lớn, đăng nhập, theo dõi GFS/Vrain và bảng kiểm chứng. Xem [kết luận và bằng chứng](reports/gfs_short_range_closeout_2026_11_24/KET_LUAN_NGAN_HAN.md) và [cách mở web](demo/station_map/README.md).

**Bản dễ hiểu dành cho người mới:** [PowerPoint 33 slide chính (~28 phút) + 34 phụ lục](reports/short_range_explained_v2_2026_11_18/PBL6_NGAN_HAN_GIAI_THICH_DE_HIEU.pptx), [Word giải thích từ đầu](reports/short_range_explained_v2_2026_11_18/GIAI_THICH_TU_DAU.docx), [cách đọc và mốc đánh giá](reports/short_range_explained_v2_2026_11_18/README.md). Tách rõ LightGBM/GRU nhóm huấn luyện, GFS có sẵn, MOS hồi quy và quy tắc đối chứng. Có ví dụ một mẫu, cách train/CV, Tweedie và L2, tính tay MAE/RMSE/Bias, số lần bắt đúng/bỏ sót/báo nhầm. Phân biệt hơn đối chứng ở mức điểm số với cải thiện ổn định và đủ dùng thực tế. Mô hình chung và giờ19h là lựa chọn thiết kế chưa được chứng minh tối ưu. Chỉ giải thích lại bằng chứng; bản tổng hợp trước và các nghiên cứu giữ nguyên.

**Báo cáo tổng hợp cho buổi trình bày 25–30 phút:** [PowerPoint đầy đủ](reports/short_range_comprehensive_2026_11_18/PBL6_BAO_CAO_DAY_DU_DU_BAO_MUA_NGAN_HAN.pptx), [Word giải thích từng slide](reports/short_range_comprehensive_2026_11_18/THUYET_MINH_SLIDE.docx), [hướng dẫn và nguồn](reports/short_range_comprehensive_2026_11_18/README.md). Có 31 slide chính và 31 phụ lục: ý tưởng, Vrain/GFS và QC, đầu vào/đầu ra, cơ sở paper, cách train/tuning, metrics, kết quả 2025/2026, khó khăn và hướng tiếp. Tách rõ các protocol và giới hạn; không nhận kết quả hồi cứu là kiểm định tương lai. Đã kiểm tra 211 lượt trích số và bố cục bằng PowerPoint thật. PDF và gói báo cáo riêng ở private, không đưa dữ liệu hoặc thông tin đăng nhập lên Git.

**Hoàn thành vòng mở rộng năm train/loss 18/11:** [báo cáo, slide và CSV](reports/gfs_training_window_2026_11_18/README.md), [kết luận](reports/gfs_training_window_2026_11_18/KET_LUAN.md). Đã chạy A–D và N0/N1/N3, cùng 57 trạm, ngân sách và ba seed; 72 CV và 162 estimator cuối cùng. Thêm 2023–2024 giúp Tweedie giảm điểm RMSE cả ba hạn nhưng chưa đủ chắc chắn; chỉ D−C ngày 3 đạt tiêu chí thăm dò trong họ 12 phép so. L2 không thắng nhất quán. Năm 2025 chỉ hiệu chỉnh Platt/cutoff; 2026 đã xem, chỉ hồi cứu và tách API. Đã kiểm chứng 48.639 hàng/3.000 giá trị metric; 52 tests đạt, 28 slide. Tiến trình riêng chờ ghi dự báo trước 19h ngày 18/11, đối chiếu ba nhãn từ tối 21/11; chưa có kết quả kiểm chứng tương lai. Bi-LSTM tiếp tục để sau; các nghiên cứu cũ giữ nguyên.

**Hoàn thành vòng nghiên cứu bổ sung 18/11/2026:** [báo cáo và slide mới](reports/gfs_temporal_2026_11_17/README.md), [kết luận](reports/gfs_temporal_2026_11_17/KET_LUAN.md). Giữ 57 trạm, thử riêng phân bố mưa GFS 6 giờ và diễn biến khí tượng trong ngày; 107.822 mẫu đủ ba hạn, 144 estimator LightGBM, 9 GRU và các đối chứng. **Chưa có cải thiện RMSE ổn định để chốt bộ 49 biến:** cả 12 phép so chính đều chưa đạt tiêu chí đã định trước. Một số chỉ số cảnh báo thay đổi theo cutoff; đọc cả POD/FAR/CSI và BS/BSS. Đã kiểm chứng 163.023 hàng đánh giá và 4.320 giá trị metric; 42 tests đạt. 2025–2026 của vòng này là hồi cứu vì đã được xem. Giữ nguyên bằng chứng kiểm định trước đó; nhánh Bi-LSTM để sau. Gói dữ liệu riêng gửi nhóm ở `data/operational/gfs_temporal_2026_11_17/PBL6_NGAN_HAN_GFS_VRAIN_2021_2026.zip`, không đưa lên GitHub.

**Kiểm định cuối đã hoàn thành 17/11/2026:** [kết luận](reports/gfs_station_final_2026_11_17/KET_LUAN.md), [báo cáo Word](reports/gfs_station_final_2026_11_17/BAO_CAO_KIEM_DINH.docx), [toàn bộ bằng chứng](reports/gfs_station_final_2026_11_17/README.md). Đã chạy hai đối chứng dung lượng GRU, khóa mô hình trước test, chấm 17 phương án trên 2025 và tách nguồn 2026. Khí tượng thô cải thiện rõ ở ngày 2–3; địa hình và dẫn xuất N5 chưa chứng minh thêm lợi ích trong các phép so chính. LightGBM N3 vượt MOS rõ về RMSE ở ngày 3; GRU N5 vượt MOS về MAE median ở ngày 1 và 3. Năm 2025 và phần 2026 này nay đã được chấm, không còn là test chưa dùng cho các lần chỉnh mô hình tiếp theo. Kết quả cũ phía dưới giữ đúng phạm vi dev 2024.

**Bộ giờ cho Bi-LSTM, bản 17/11/2026:** [mô tả và hướng dẫn](reports/station_hourly_era5_2026_11_17/README.md). Một Parquet mới đã ghép mưa Vrain với 44 kênh ERA5/lịch theo vị trí trạm và sáu nhãn mưa giờ; đầu vào 24 × 45 khi thêm mưa quá khứ. Danh mục có 86 vị trí, 79 có train theo split hiện hành. Mưa tới 19h ngày 15/11 nhưng khí tượng mới ghép tới hàng kết thúc 07h ngày 11/11/2026 giờ Việt Nam; đuôi thiếu không dùng train. Hai đường API đều Vrain, chưa xác nhận liên tục; mẫu yêu cầu cùng nguồn suốt 24 giờ lịch sử và 6 nhãn. Gói private `data/processed/station_hourly_era5_2026_11_17/PBL6_BILSTM_GIO_2021_2026.zip`. Không có huấn luyện/chấm mới; nhánh ngày GFS và kết quả cũ giữ nguyên.

**Đã cập nhật và kiểm tra 16/11/2026:** [mô tả và hướng dẫn bộ đến 2026](reports/station_update_2026_11_16/README.md), [Word gửi nhóm](reports/station_update_2026_11_16/MO_TA_DU_LIEU.docx). Kho mưa tới 15/11/2026, GFS/nhãn ba ngày tới issue 12/11/2026; danh mục 86 trạm, có thiếu theo thời gian và hai kênh nguồn chưa được chứng minh liên tục. Có142.582mẫu đủba hạn/X/y, không phải tất cả đều là mẫu train. Gói nội bộ ~61MB ở `data/processed/station_update_2026_11_16/PBL6_DATA_DEN_2026.zip`, ngoài Git. Năm2025 đã thu thập/QC theo yêu cầu mới, chưa fit/tuning/chấm mô hình. Kết quả thí nghiệm và slide phía dưới vẫn là dev2024 của bản cũ.

**Slide mới 11/11/2026:** [PowerPoint hằng ngày v2 — 41 slide](reports/gfs_daily_slides_2026_11_11/PBL6_MUA_TRAM_HANG_NGAY_V2.pptx), [ghi chú thuyết trình](reports/gfs_daily_slides_2026_11_11/GHI_CHU_THUYET_TRINH.md), [hướng dẫn và giải thích giữ lại 2025](reports/gfs_daily_slides_2026_11_11/README.md). Bảng đủ N0–N5, đối chứng, tuning, seed, metrics và giới hạn. Kết quả là dev 2024; chưa có bảng điểm kiểm định cuối 2025.

**Đã hoàn thành 11/11/2026 — thí nghiệm lịch hằng ngày v2:** 57 trạm, 1.449 chu kỳ GFS hợp lệ trong 2021–2024; 72.886 mẫu trạm–issue. [Kết luận dễ đọc](reports/gfs_station_daily_v2_2026_11_10/KET_LUAN.md), [báo cáo đầy đủ](reports/gfs_station_daily_v2_2026_11_10/BAO_CAO_HANG_NGAY_V2.md), [Word gửi nhóm](reports/gfs_station_daily_v2_2026_11_10/BAO_CAO_HANG_NGAY_V2.docx), [bảng số và bằng chứng](reports/gfs_station_daily_v2_2026_11_10/README.md). LightGBM N0–N5 và GRU N3/N5, ba seed, đầu mean/median, xác suất nhất quán, ZERO/MOS và độ trễ 1/3/6 giờ; đã replay checkpoint và metric. Test 2025 giữ kín.

Khí tượng thô bổ sung có ích; dẫn xuất chưa giúp rõ cho LightGBM nhưng có tín hiệu ở GRU ngày1–2. GRU_N5 có MAE median 6,314/6,754/6,870 mm; RMSE mean 17,386/18,750/19,277, so MOS19,169/20,124/20,445. Đây là dev2024, không phải test cuối hay bằng chứng vượt paper khác. BSS50 dương nhưng báo nhầm mưa lớn còn nhiều. Các kết quả lịch tuần bên dưới được giữ riêng, không so trực tiếp hai tập ngày khác nhau.

**Phương án được duyệt 10/11/2026:** dự báo ba tổng24h riêng tại trạm bằng **GFS + Vrain**, LightGBM chính và GRU nhỏ. [Thiết kế hiện hành](docs/short_range_nwp_design.md), [kế hoạch](KE_HOACH_DU_AN.md), [protocol57trạm](reports/gfs_station_57_2026_11_10/protocol.json). TFT/Informer là mở rộng tùy bằng chứng.

## Bản trước đó: 57 trạm theo lịch tuần

**Nhận xét độc lập mới:** [đánh giá kết quả và đối chiếu nghiên cứu 2024–2026](reports/gfs_station_review_2026_11_10/NHAN_XET_DOC_LAP.md). Chẩn đoán bổ sung cho thấy ngày 3 các mô hình chưa vượt phương án 0 mm về MAE, dù GRU giảm RMSE rõ ở mức điểm; A2 còn yếu trên nhóm mưa lớn. Dùng tài liệu này kèm slide để tránh kết luận quá mức từ MAE giảm so GFS. Không thay dự báo, train mới hoặc mở 2025.

**Slide báo cáo chi tiết:** [PowerPoint 55 slide](reports/gfs_station_slides_2026_11_10/PBL6_DU_BAO_MUA_57_TRAM.pptx), [ghi chú thuyết trình](reports/gfs_station_slides_2026_11_10/GHI_CHU_THUYET_TRINH.md), [hướng dẫn đọc và nguồn](reports/gfs_station_slides_2026_11_10/README.md). Trình bày đầu vào/đầu ra, chia thời gian, tham số cố định và phần lựa chọn bằng cal, cùng bảng kết quả và giới hạn của thí nghiệm 57 trạm.

**Đã tăng20→57trạm**, thêm37trạm có sẵn trong nguồn; cùng tiêu chuẩn train, nguồnGFS, lịch mỗi7ngày, đặc trưng và thiết lập mô hình. Đã chạy LightGBM A0–A3 vàGRUba seed;5.032/2.582/2.782mẫu train/cal/dev. [Báo cáo mở rộng](reports/gfs_station_57_2026_11_10/BAO_CAO_MO_RONG.md), [Word](reports/gfs_station_57_2026_11_10/BAO_CAO_MO_RONG.docx), [protocol57](reports/gfs_station_57_2026_11_10/protocol.json).

Có79trạm có mẫutrain nhưng22trạm ngoài nhóm57có lịch sử ngắn; chưa gộp vào tập chính. Ba trạm chưa cótrain vàbốn vịtrí mới chưa có lịch sử cũ. Không tự nhận đủ86trạm đã sẵn sàng.

Mở rộng không bảo đảm tăngđộchínhxác: trên cùng20trạm cũ, MAE A2ngày1/2/3 đổi6,15/7,37/7,75→5,91/7,40/8,66mm; cả3CIchênh lệch chứa0. Bản57mởrộng cảtrain/cal. Không so trung bình20với57trực tiếp.53tests vàreplaynguồn/môhìnhđạt;2025giữkín. Datasetprivate ở `data/processed/gfs_station_57_2026_11_10/gfs_vrain_pilot.parquet`.

## Pilot20trạm trước khi mở rộng

20 trạm, 208 chu kỳ GFS trong2021–2024, lịch issue cố định mỗi7ngày. Đã chạy khí hậu/persistence/GFS, LightGBM A0–A3 và GRU A2 với ba seed. Có1.774/902/983mẫu trạm–issue train/cal/dev, mỗi mẫu ba nhãn. **Chưa phải thí nghiệm hằng ngày đầy đủ hoặc test cuối;2025 vẫn giữ kín.**

| Phương pháp | MAE ngày1 mm | MAE ngày2 mm | MAE ngày3 mm |
| --- | ---: | ---: | ---: |
| GFS nguyên bản | 6,40 | 8,13 | 10,27 |
| LightGBM A2 | 6,15 | 7,37 | 7,75 |
| GRU A2 | 7,81 | 8,35 | 8,46 |

Đây là macro-MAE giữa trạm trên phần phát triển2024. **CI A2−GFS cả ba ngày còn chứa0**: mức giảm ngày3khoảng24% chưa chứng minh cải thiện ổn định. GRU có MAE cao hơn nhưng RMSE ngày3 thấp hơn A2 (18,31 so20,17mm). Địa hình A3 chưa có lợi ích rõ; xác suất và lượng mưa không cải thiện đồng đều. Chưa kết luận GRU kém mọi mặt hoặc có kỹ năng mưa cực đoan ổn định.

Đọc [báo cáo đầy đủ](reports/gfs_station_pilot_2026_11_10/BAO_CAO_PILOT.md), [Word gửi nhóm](reports/gfs_station_pilot_2026_11_10/BAO_CAO_PILOT.docx), [kết quả tổng hợp](reports/gfs_station_pilot_2026_11_10/result_summary.json). Có kiểm tra nguồn và replay estimator;47tests đạt. Trễ trạm1h/GFS8h vẫn là giả định.7chu kỳ train có timestamp sửa/chép archive sau issue; đã chạy thêm độ nhạy bỏ các chu kỳ đó.

Dataset pilot private: `data/processed/gfs_station_pilot/gfs_vrain_pilot.parquet`; source/cache/model/prediction ở `data/operational/gfs_station_pilot_2026_11_10/`. Không đưa lênGitHub. BộVrain–ERA5v1 bên dưới là dữ liệu hồi cứu bàn giao09/11; khác bộNWP mới.

**Quyết định ngày 09/11/2026:** nhóm chuyển cả dự báo cực ngắn và ngắn sang **dự báo tại trạm**. [Thiết kế hiện hành gửi nhóm](project_plan_v2.md), [kế hoạch thực hiện](KE_HOACH_DU_AN.md), [metadata phạm vi](docs/station_forecast_scope.json).

## 86 trạm là ở đâu?

Đây là **86 vị trí trong nhóm dữ liệu “Đà Nẵng” mà tài khoản Vrain truy cập được**, không phải toàn Việt Nam. Số 86 là danh mục ứng viên, chưa phải số trạm đã chọn huấn luyện. Cần kiểm tra tọa độ theo phạm vi nghiên cứu khi chốt tập trạm.

Danh mục mới có 82 vị trí khớp danh mục cũ và bốn vị trí bổ sung. Trong kho lịch sử, số trạm có ít nhất một giá trị giờ sau QC: **2021: 57; 2022: 79; 2023: 79; 2024: 82**. Không đồng nghĩa đủ cả năm hoặc cả 86 có dữ liệu từ 2021.

## Hai nhánh và cách dùng mô hình

| Nhánh | Nhãn tại chính trạm | Mô hình |
| --- | --- | --- |
| Cực ngắn | Sáu lượng mưa giờ tiếp theo, 1–6h | Bi-LSTM và đối chứng |
| Ngắn | Ba tổng 24h riêng của ngày 1/2/3 | GFS + LightGBM, GRU nhỏ theo pilot |

Mỗi kiến trúc dùng **mô hình chung cho nhiều trạm**. Một mẫu là `(trạm, thời điểm)`, không bắt buộc86bộ riêng. Nhãn là mưa Vrain tại điểm đo; NWPpilot dùng GFS dự báo khởi tạo trướcissue, không dùng ERA5 kỳ đích. NhánhBi-LSTM và bộERA5v1 giữ phạm vi riêng.

## Bộ Vrain–ERA5 v1 đã bàn giao 09/11

**Đã có bộ trạm v1 ghép và kiểm tra**, gồm cả giờ/ngày trong một file: `data/processed/station_v1/PBL6_TRAM_GIO_NGAY_V1.parquet` (dữ liệu private, ngoàiGit). Gửi nhóm cùng [bản mô tả Word](reports/station_data_handoff_2026_11_09/MO_TA_DU_LIEU.docx); [hướng dẫn loader](reports/station_data_handoff_2026_11_09/HUONG_DAN_TRAIN.md), [số liệu/checksum](reports/station_data_handoff_2026_11_09/dataset_summary.json), [kiểm tra toàn file](reports/station_data_handoff_2026_11_09/verification.json).

82trạm có lịch sử;79trạm có cửa sổ train ở bộv1. Đã kiểm tra2.995.050hàng/2.480.367cửa sổ,34testsđạt ở phiên bản đó. Chưa có kết quả mô hình dùng bộERA5v1; NWPpilot phía trên là thí nghiệm khác.24trạm có dưới180mẫu ngày train. Kiểm tra cấu trúc không chứng nhận cảm biến.

Người dùng xác nhận10:00là tổng09–10hViệtNamUTC+7. Ngày là19→19h; ERA5 nội suy trực tiếp từ bốn nút gốc0,25° quanh trạm, không chép mean vùng93ô. Train2021–22/cal2023/dev2024;2025giữkín,2026chưa nhậptrain. E7+R có45kênh giờ/43kênh ngày; statictọađộ/IDriêng.

| Nguồn | Vị trí riêng |
| --- | --- |
| Vrain lịch sử 2021–2024, raw/checksum/QC | `data/operational/vrain_2026_11_09/download/`, `freeze_work/` |
| Registry 86 mã chuẩn và nguồn đóng gói | `data/operational/vrain_2026_11_09/handoff_v1/`, `PBL6_VRAIN_SOURCE_V1.zip` |
| Vrain 02/01–08/11/2026, hai kênh riêng | `data/operational/vrain_2026_11_09/recent_archive/` |
| ERA5 native, đã nội suy tại trạm trong bộ mới | `data/raw_data/gee/era5/grid/` |
| Dữ liệu đã ghép theo trạm, hai độ phân giải | `data/processed/station_v1/PBL6_TRAM_GIO_NGAY_V1.parquet` |
| Bộ trung bình vùng cũ, chỉ tham khảo | `data/processed/regional_danang/` |

**Predictor 44 kênh trong ZIP nguồn cũ vẫn là trung bình vùng, chưa phải predictor tại trạm.** Không nhân bản nó và đổi tên thành dataset trạm. Các phản hồi 2015–2020 không có hàng giờ Vrain; không gọi đó là ngày khô. Năm 2025 vẫn giữ kín; chưa dùng 2026 để fit/tuning hoặc tự nối hai kênh.

## Công việc tiếp theo

Pilot NWP đã hoàn thành. Bước tiếp theo để kiểm chứng là protocol mới cho lịch hằng ngày, độ nhạy trễ dữ liệu và thí nghiệm bỏ nhóm đặc trưng. Giữ bản pilot hiện tại làm bằng chứng, không tối ưu theo điểmdev2024 rồi gọi đó là test cuối.2025giữkín;2026khôngtuning.

Mã NWP theo thứ tự ở [thiết kế mới](docs/short_range_nwp_design.md). Tái tạo bộERA5v1: `scripts/build_station_forecast_data.py`, `scripts/validate_station_forecast_data.py`. Vrain có manifest riêng; nguồn cũ trênDrive kiểm bằng `scripts/package_data.py verify`.

## Bằng chứng và phương án cũ

- [Bàn giao nguồn 82/86](reports/vrain_data_handoff_2026_11_09/CHOT_DU_LIEU_GUI_NHOM.md), [Word](reports/vrain_data_handoff_2026_11_09/CHOT_DU_LIEU_GUI_NHOM.docx): nguồn và giới hạn, chưa phải tập train theo trạm.
- [Đánh giá nhãn vùng và lý do đổi mục tiêu](reports/vrain_data_handoff_2026_11_09/DANH_GIA_KHA_THI_VA_HUONG_DI.md), [Word](reports/vrain_data_handoff_2026_11_09/DANH_GIA_KHA_THI_VA_HUONG_DI.docx): được viết trước quyết định theo trạm, giữ làm lịch sử.
- [Kết quả CPC ngày](reports/daily_gauge_2026_11_04/README.md), [GSMaP ba mô hình](reports/short_range_complete_2026_10_28/README.md): vẫn là kết quả vùng của nguồn cũ, chưa phải Vrain tại trạm.
- [Phương án hợp nhất cũ](reports/regional_research_plan_2026_10_20/PHUONG_AN_CUOI.md), [biên bản dọn](docs/cleanup_2026_11_09.json).

GitHub công khai chỉ chứa mã, tài liệu và thống kê tổng hợp. Raw, registry/tọa độ từng trạm, credential, PDF, checkpoint và dự đoán từng mốc nằm ngoài Git. Làm trên `research/tft-regional`, không tự merge main; giữ nguyên slide người dùng sửa.
