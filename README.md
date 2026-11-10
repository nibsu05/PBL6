# PBL6 — dự báo lượng mưa tại nhiều trạm

**Phương án được duyệt 10/11/2026:** dự báo ba tổng24h riêng tại trạm bằng **GFS + Vrain**, LightGBM chính và GRU nhỏ. [Thiết kế hiện hành](docs/short_range_nwp_design.md), [kế hoạch](KE_HOACH_DU_AN.md), [protocol57trạm](reports/gfs_station_57_2026_11_10/protocol.json). TFT/Informer là mở rộng tùy bằng chứng.

## Bản mở rộng hiện tại:57trạm

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
