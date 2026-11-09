# PBL6 — bối cảnh hiện hành cho agent

Cập nhật 09/11/2026. Đọc trước file này, rồi `KE_HOACH_DU_AN.md` và `project_plan_v2.md`. Người dùng chỉ cần bắt đầu từ `README.md`.

## Mục tiêu và quy ước

- Trao đổi tiếng Việt, độc lập, có bằng chứng và trung thực cả kết quả âm.
- Nghiên cứu đặc trưng cho mưa trung bình vùng Đà Nẵng mới; một mẫu là một issue vùng. Không tự chuyển sang từng ô hoặc ưu tiên app.
- Thành viên khác phụ trách Bi-LSTM 1–6h; người dùng phụ trách LightGBM/TFT/Informer 1–3 ngày.
- Workspace `D:\PBL6_v2`, Python `.venv\Scripts\python.exe -X utf8`, RTX4060Laptop8GB. Python inline qua PowerShell dùng ASCII; nguồn tiếng Việt dùng UTF-8/apply_patch.
- Git: `git -c safe.directory=D:/PBL6_v2`. Làm trên `research/tft-regional`, push/PR vào main; không tự merge. Không commit raw, PDF, credential, checkpoint hoặc dự đoán từng mốc.
- Dữ liệu cũ từ Google Drive `pbl6_data_v2_*.tar`; `scripts/package_data.py verify` chỉ bao phủ nguồn cũ, không phải Vrain.

## Trạng thái: đã kiểm kê/đóng gói nguồn, nhãn vùng chưa chốt

Kho cũ đủ 3.653 response 2015–2024, SHA gzip/raw đạt. Có 1.461 bảng 24h cho ngày 2021–2024; 2015–2020 không có hàng giờ. Ba station-day chênh tổng đã gắn cờ, giữ số gốc. Đã tải thêm 622 response cho 02/01–08/11/2026 (311 ngày × hai kênh), không bao gồm ngày 01/01 vì cửa sổ chứa 2025. Giữ kín 2025, không train/tuning 2026.

**Bàn giao hiện hành:** `reports/vrain_data_handoff_2026_11_09/CHOT_DU_LIEU_GUI_NHOM.md`/docx, aggregate `docs/vrain_data_freeze.json`. Private `data/operational/vrain_2026_11_09/handoff_v1/`, ZIP `PBL6_VRAIN_SOURCE_V1.zip`. Gói là SOURCE, **không phải nhãn vùng đã duyệt**. ERA5 44 kênh giờ trước 2025 đã tách bỏ nhãn GSMaP; ngày 42 kênh chưa materialize khi chưa chốt anchor.

**Đã đồng bộ metadata 82↔86:** 82 vị trí cũ khớp chính xác/duy nhất 82 mục mới, 81 tên giống và một tên khác; bốn vị trí bổ sung. Dùng registry 86 mã chuẩn + alias, không cộng hai mạng; chưa xác nhận lịch sử thiết bị/vị trí hoặc tự nối số đo. Giữ ID registry v1 khi bổ sung trạm sau này, không đánh số lại.

2026 có số ở 87 ngày kênh cũ, 305 ngày kênh mới trong 311 ngày yêu cầu; có bảng không đồng nghĩa có số. Phần trùng hai kênh chỉ một vị trí/18 ngày/367 cặp, 46 cặp có mưa đều khác số; không suy tương đương toàn mạng. ERA5 bàn giao có 21 hàng thiếu kx/tt (42 ô), giữ NaN. 22 tests Vrain đạt; ZIP có 4.275 raw responses, không phiên đăng nhập.

**Phát hiện cản trở nhãn:** toàn mạng cố định 82 trên R93 không có ngày đủ 100% coverage năm 2021–2023; coverage giờ tối đa khoảng 70,0%/83,5%/83,5%. Panel 45 trạm đầy đủ ≥98% từng năm 2021/22 làm khoảng cách tâm ô xa nhất tới trạm tăng 34→59 km, trung bình vùng núi 13→30 km. Chưa chọn panel/estimator nhãn chính. Không gọi dữ liệu đã bảo đảm chỉ vì đã tải đủ. Cần xác nhận kỳ đo và giải quyết tính đại diện không gian trước train.

**Đánh giá độc lập mới:** `DANH_GIA_KHA_THI_VA_HUONG_DI.md`/docx trong thư mục bàn giao. Đã spatial CV và che trạm theo lịch sử trên 67 ngày đủ cả 82 cuối 2024 (khác69ngàyđủtrạmtrọngsốdương). Thiessen toàn R93 NRMSE trung vị 2021/22/23 masks =21,4/19,8/16,3%; vùng núi71/69,3/60%. Tham chiếu nội bộ không phải chân lý; percentiles theo mask không phải CI; chưa train dự báo. Điều kiện100% là quy tắc lọc cũ, thiếu không tự động bất khả thi; có thể thử estimator mạng thiếu được khai báo/kiểm chứng.

Khuyến nghị mới để người dùng chọn phạm vi: ưu tiên dự báo vùng trực tiếp theo ngày trên vùng cố định kiểm chứng được, có thể nhỏ hơn Đà Nẵng mới; toàn vùng mới là mở rộng có điều kiện. Dự phòng mô hình chung dự báo tại nhiều trạm nếu nhãn vùng không đạt. Chưa tự thay ranh/mục tiêu hiện có. Không chốt tên một vùng hành chính từ các zone R93; chúng chỉ là nhóm ô chẩn đoán. 26 tests Vrain đạt. Tái lập `scripts/assess_vrain_label_feasibility.py`, xuất `scripts/publish_vrain_feasibility.py`.

Đã đăng nhập/xuất mẫu thật tại `https://www.vrain.vn/landing`. Không nhắc lại hoặc lưu password vào nguồn/tài liệu; web session không đồng nghĩa có Open API key/quyền toàn quốc.

- Collector: `scripts/download_vrain_archive.py`; yêu cầu 2015-01-01→2024-12-31, 3653 ngày. Collector từ chối năm 2025.
- Trạng thái thật: `data/operational/vrain_2026_11_09/download/progress.json`; đọc file và PID, không lấy snapshot trong chat làm hiện tại.
- Raw: `download/raw/YYYY/YYYY-MM-DD.json.gz`; metadata/checksum: `download/manifest.sqlite`.
- Một request/giây, retry/backoff, khóa một worker, resume bằng checksum. Ngày không có giờ ghi `no_hourly_data`; cấu trúc lạ giữ raw và gắn cờ. Tải xong chưa phải dataset sạch.
- Cookie ở `download/session.dpapi`, mã hóa Windows. Không print cookie/header/signed URL. CLI `--login` rồi `--resume` nếu hết phiên. Không lưu mật khẩu.
- Tải nền bằng Start-Process `WindowStyle Hidden`, log private. Giữ máy thức nhưng cho màn hình tắt. Sau restart cần resume.
- Benchmark một ngày ~0,295s; request tuần/tháng chỉ trả tổng ngày nên phải tải từng ngày để giữ giờ. Dự toán ban đầu60–90phút với giới hạn1request/s, chưa tính QC/nhãn.

## Bằng chứng và giới hạn Vrain

- Kênh cũ `/api/vrain/private/v1/groups/29/stats/details`; kênh hiện hành `/api/kttv/private/v1/organizations/details`, `x-org-uuid` từ groupOrgUuid đã xác thực, `i=_1h`/`_10m`. Không đoán UUID hoặc mở phạm vi tài khoản. Bảng có 24 clock có thể toàn dấu thiếu: đếm `valid_numeric_cells`, không chỉ đếm hàng. Kênh cũ rỗng không có nghĩa toàn mạng không đo. Probe 09/11/2026 có 143 mốc 10 phút tới 18:50; không suy SLA/độ trễ được bảo đảm.

- Inventory API V1 có82ID/UUID khớp history82/82; V2 có86mục khác namespace. Không cộng/ép nối theo tên. Không nhầm với V1/V2 bộ vùng cũ.
- Mười probe ban đầu:7có24h;3ngày thử2015/2019/2020không có giờ. Trạm đủ24số50–81tùyprobe;490cặp tổng khớp1e-6 đơn vị nguồn. Không suy kho bắt đầu2021 hoặc mạng đầy đủ cả năm.
- Clock20:00ngàytrước→19:00ngàyđượcchọn, XLSX tiêu đề kết thúc19:20. Chưa xác nhận đủ timezone/đầu-cuối kỳ/đơn vị/loại tích lũy; không áp12UTC củaCPC.
- Cao độ metadata thiếu; chưa xác minh vị trí lịch sử, polygon hoặc phủ địa hình. Chưa tạo nhãn vùng/huấn luyệnVrain.
- Báo cáo mười probe đã công bố: `reports/vrain_research_plan_2026_11_09/`. Không sửa nó để gọi thành kiểm kê toàn kho; archive mới có manifest riêng.

## Chính sách nghiên cứu

- ERA5 quá khứ làmX; Vrain sauQC/panel/trọng số cố định làm y. Mưa quá khứ là nhómR riêng; giữ R giống nhau khi ablationA/M/C.
- B/A/M/C ngày9/12/20/1=42, giờ11/12/20/1=44. C chỉ SST, chưa đầy đủENSO/MJO.
- Nhãn ngày là ba tổng24hriêng; nhãn giờ là sáu lượng giờ tiếp. Chỉ lịch tương lai biết trước được dùng; không ERA5/mưa giờđích trongX.
- Footprint93toànô~11.074km² còn xấp xỉ. Đổi ranh phải tính lại cảX/y; trạm không phải ô lưới, không mặc định phủ toàn vùng/đảo.
- ERA5 nguồn0,25°→biểu diễn0,1° không tăng độ phân giải thật. Nội suy cũ có thể bỏ nútNaN: audit nguồn khi dựng lại.
- Không biến thiếu thành0 hoặc đổi denominator âm thầm; không lấy CPC/GSMaP lấp y rồi gọi thuầnVrain.
- Split theo lịch sử thực; scaler/reference chỉtrain, earlystop/calibration/tau chỉcal; toàn bộ y trongsplit. Không ép train từ2015.
- Giữ kín2025; không tuning2026 rồi gọi2025làtesttươnglai. Không so điểm khácnhãn như tác dụng một thay đổi.
- CSI/BSS chính; POD/FAR, RMSE/MAE/Bias/BS bổ sung, cùngmẫu/mùa/ngưỡng/baseline/CI. POD0,4không có chuẩn tốt chung.
- ERA5 là hồi cứu, chưa chứng minh có sẵn tạiissue. Không bắt TFT thắng cây/Informer hoặc chạyInformer để chứng minh kém.

## Nguồn cũ cần giữ

- `reports/regional_research_plan_2026_10_20/PHUONG_AN_CUOI.md`: D1/D2/D9/D10/D14/D15 và sáu tiêu chí đúng phạm vi cũ. Có quyềnVrain mới không tự bác số đo cũ.
- `reports/daily_gauge_2026_11_04/`: CPC2015–2023,168fits=24LGBM+72TFT+72Informer, tái lập144NN/288đầura cây/336split. E7BSSngày1=.190/.026/.078, ngày2–3âm. CI development, chưa holdout, không gọi làVrain.
- `reports/short_range_complete_2026_10_28/`: GSMaP đủ ba mô hình, nguồn khácnhãn.
- ParquetV1/V2 trong `data/processed/regional_danang/`:102984giờ2015–09/2026;49/138predictorứngviên, nhãnGSMapcũ. Không nhầm thành nhãnVrain.
- GSODDATE chưa chứng minh00–00UTC. Audit04/11trạm488550 có1364/1365bản24hở12UTC, chưa toànmạng.

## Dọn dẹp đã được người dùng cho phép

Ngày09/11xóa ba kế hoạch gốc lỗi thời và ba bộ trình bày bị thay thế. CóZIPprivate vàGit a05f6c0; không xóa nguồn thí nghiệm/metadata dùng tái lập. Tài liệu gốc đã rút gọn thay vì nối lịch sử dài.

Không restore/build lại/stage hộ hai bản người dùng sửa:
- `reports/daily_gauge_slides_2026_11_04/PBL6_DU_LIEU_NGAY_3_MO_HINH.pptx`.
- Bản đổi tên `reports/short_range_three_models_2026_10_21/Dự đoán ngắn hạn 21_10.pptx`; bản tên gốc bị người dùng xóa.

SnapshotSHA: `data/operational/workspace_cleanup_2026_11_09/user_files.json`.

## Tiếp theo

Nguồn đã bàn giao → xác nhận kỳ đo/ranh/lịch sử vùng núi → kiểm chứng estimator và chốt nhãn vùng → loader/split → pilot E0/E2/E7/R0/R1 → ma trận → khóa trước test 2025. Không train toàn ma trận trước khi giải quyết cổng nhãn. Kiểm thử: tests.test_vrain_download, tests.test_vrain_export_audit, tests.test_vrain_station_identity, tests.test_vrain_spatial_panel.
