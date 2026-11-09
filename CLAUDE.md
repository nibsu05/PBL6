# PBL6 — bối cảnh hiện hành cho agent

Cập nhật 09/11/2026. Đọc file này trước, rồi `KE_HOACH_DU_AN.md` và `project_plan_v2.md`. Người dùng bắt đầu từ `README.md`.

## Quyết định mới nhất của người dùng — đã chốt

**Chuyển cả hai nhánh sang dự báo lượng mưa tại trạm.** Người dùng nói: “nhóm tôi thực hiện dự đoán cực ngắn và ngắn theo trạm”. Quyết định này thay mục tiêu dự báo trực tiếp mưa trung bình diện tích toàn Đà Nẵng trước đây. Không tự đưa mục tiêu vùng trở lại hoặc ưu tiên app.

- Thành viên khác: Bi-LSTM, sáu lượng mưa giờ tiếp theo tại từng trạm, 1–6h.
- Người dùng: LightGBM/TFT/Informer, ba tổng 24h riêng của ngày 1/2/3 tại từng trạm.
- Đề xuất kỹ thuật: mỗi kiến trúc học một mô hình chung cho nhiều trạm; một mẫu là `(station_id, issue_time)`. Không cần 86 mô hình riêng cho một kiến trúc.
- Nhãn là mưa Vrain tại chính trạm. Không còn chờ phê duyệt nhãn mưa diện tích vùng; vẫn phải xác nhận thời gian, đơn vị và QC trạm trước train.

## Phạm vi và số trạm

86 là danh mục **nhóm “Đà Nẵng” mà tài khoản được truy cập**, không phải toàn Việt Nam. Chưa chứng nhận mọi mục nằm đúng ranh hành chính cuối; lọc theo tọa độ/ranh khi chốt tập trạm nếu cần. Không gọi danh mục là phủ kín diện tích hoặc cả đảo.

- Kênh cũ có 82 vị trí, kênh hiện hành 86. 82 cặp tọa độ khớp chính xác/duy nhất, 81 tên giống và một tên khác; bốn vị trí bổ sung. Chưa biết thời điểm lắp đặt bốn trạm đó.
- Registry private 86 mã STxxx + alias hai kênh; giữ mã v1 khi thêm trạm sau này. Khớp metadata không chứng minh số đo hai kênh tương đương.
- Trong kho cũ, trạm có ít nhất một số giờ sau QC: 2021 **57**, 2022 **79**, 2023 **79**, 2024 **82**. Không đồng nghĩa đủ cả năm. Không mặc định cả 86 có lịch sử từ 2021 hoặc đã được chọn train.
- Số trạm train cuối chưa chốt; pilot một nhóm đại diện trước, rồi mở rộng trạm đủ điều kiện. Thiếu tại trạm A không loại mẫu hợp lệ của trạm B.

## Nguồn đã có và trạng thái

Private base `data/operational/vrain_2026_11_09/`:

- `download/`: 3.653 response 2015–2024, SHA gzip/raw đạt; có bảng giờ cho 1.461 ngày 2021–2024; 2015–2020 không trả giờ, không phải ngày khô. Ba station-day chênh tổng đã gắn cờ, số gốc được giữ.
- `recent_archive/`: 622 response cho 02/01–08/11/2026, 311 ngày × hai kênh. Bỏ 01/01 vì cửa sổ có giờ 2025. Có số ở 87 ngày kênh cũ, 305 ngày kênh mới; số hàng không bằng số đo hợp lệ.
- `handoff_v1/`, `PBL6_VRAIN_SOURCE_V1.zip`: nguồn/registry/QC, **không phải tập train theo trạm đã dựng**. Predictor 44 kênh trong ZIP vẫn là trung bình vùng cũ; không đổi tên hoặc nhân bản thành đầu vào theo trạm. Có 21 hàng thiếu kx/tt (42 ô), giữ NaN.
- `freeze_work/station_matrices.npz`: ma trận giờ nguồn 2021–2024, mask/QC; chưa khẳng định timezone/đầu-cuối khoảng.
- Hai kênh chỉ trùng số ở một vị trí/18 ngày/367 cặp, 46 cặp có mưa đều khác số. Không tự nối nguồn 2026 hoặc fit/tuning 2026.

ERA5 theo ô đã có ở `data/processed/dataset_v2_danang/cube_cell_major.npy`, `hours_all.npy`, `cells.parquet`, `manifest.json`. Bộ vùng cũ ở `data/processed/regional_danang/` có nhãn GSMaP cũ và 102.984 giờ 2015–09/2026. Phải trích khí tượng tại/gần tọa độ trạm, kiểm tra miền phủ và nội suy/NaN; một số trạm có thể ngoài footprint 93 ô. Nguồn ERA5 0,25° biểu diễn 0,1° không tăng độ phân giải vật lý.

## Hợp đồng thời gian và nghiên cứu

- Nguồn hiển thị clock 20:00 hôm trước→19:00 ngày được chọn; XLSX mẫu ghi tiêu đề 19:20. Chưa xác nhận đủ đơn vị, timezone, đầu/cuối kỳ và loại tích lũy. Không tự gắn 00–24 UTC hoặc anchor CPC.
- Lưu mưa theo khoảng đo, provenance, QC; không đổi thiếu thành0, không chia mưa ngày thành giờ, không lấp y bằng ERA5/CPC/GSMaP.
- B/A/M/C giữ làm catalogue dự kiến: giờ11/12/20/1, ngày9/12/20/1. Giá trị phải xây lại theo trạm; C chỉ SST, chưa phải ENSO/MJO đầy đủ. Metadata vị trí/ID là static dùng nhất quán mọiE, chưa chốt số kênh cuối.
- R là mưa quá khứ của chính trạm, thử R0/R1 riêng; khi ablation A/M/C phải giữ R và mask giống nhau. Chỉ lịch tương lai biết trước được dùng; không ERA5/mưa kỳ đích trong X.
- Split theo thời gian chung cho mọi trạm, toàn bộ nhãn nằm trong split. Fit scaler/reference trên train; earlystop/calibration/tau trên cal. Không random cửa sổ lẫn trạm/ngày.
- **2025 giữ kín.** Không tuning2026 rồi gọi2025 là test tương lai. Chưa train theo trạm hoặc đổi tên kết quả vùng cũ thành kết quả trạm.
- Báo metric từng trạm và macro-average, kèm micro nếu cần; bootstrap theo khối thời gian giữ đồng thời các trạm. Không coi các trạm trong cùng trận mưa là mẫu khí hậu độc lập.
- Ngưỡng mưa/POD/FAR phải chốt phù hợp trạm và kỳ giờ/ngày; không tự mang ngưỡng vùng16/50/100 sang. Không có POD0,4 tốt chung. ERA5 hồi cứu chưa chứng minh có sẵn tại issue vận hành.

## Quy ước làm việc và an toàn dữ liệu

- Tiếng Việt, đánh giá độc lập và trung thực kể cả kết quả âm.
- Workspace `D:\PBL6_v2`; Python `.venv\Scripts\python.exe -X utf8`; RTX4060Laptop8GB. Python inline qua PowerShell dùng ASCII; nguồn tiếng Việt dùng UTF-8/apply_patch.
- Git `git -c safe.directory=D:/PBL6_v2`, nhánh `research/tft-regional`; đã được phép push/cập nhật PR#1, không tự merge main.
- Repo công khai: không commit raw/PDF, registry/tọa độ từng trạm, credential/cookie, checkpoint hoặc dự đoán từng mốc. Dữ liệu nguồn cũ từ Drive `pbl6_data_v2_*.tar`, kiểm bằng `scripts/package_data.py verify`; Vrain có manifest riêng.
- Vrain login `https://www.vrain.vn/landing`; không nhắc lại mật khẩu, không lưu vào nguồn. Phiên mã hóa DPAPI ở `download/session.dpapi`. Kênh cũ `/api/vrain/private/v1/groups/29/stats/details`; mới `/api/kttv/private/v1/organizations/details`, ngữ cảnh tổ chức từ group đã xác thực, không đoán UUID.
- Tải nền dùng Start-Process `WindowStyle Hidden`, resume/checksum; đọc progress/PID thật trước nói tiến độ.

Giữ nguyên, không restore/build/stage hai slide người dùng sửa: `reports/daily_gauge_slides_2026_11_04/PBL6_DU_LIEU_NGAY_3_MO_HINH.pptx` và bản đổi tên `reports/short_range_three_models_2026_10_21/Dự đoán ngắn hạn 21_10.pptx` (bản tên gốc đã bị người dùng xóa). SnapshotSHA `data/operational/workspace_cleanup_2026_11_09/user_files.json`.

## Bằng chứng lịch sử, không phải mục tiêu hiện tại

- `reports/vrain_data_handoff_2026_11_09/DANH_GIA_KHA_THI_VA_HUONG_DI.md`: kiểm định nhãn vùng trước khi người dùng chốt theo trạm. 67 ngày tham chiếu nội bộ, NRMSE Thiessen toàn R93 16,3–21,4%, nhóm núi60–71%; không phải sai số dự báo hay chân lý diện tích.
- `reports/daily_gauge_2026_11_04/`: CPC168fits,144checkpointNN/288đầu ra cây/336split; chưa là Vrain hoặc theo trạm.
- `reports/short_range_complete_2026_10_28/`: GSMaP ba mô hình, giữ nguyên nguồn/kết quả.
- `reports/regional_research_plan_2026_10_20/PHUONG_AN_CUOI.md`: các quyết định có bằng chứng giữ đúng phạm vi cũ; không tự phủ nhận số đo cũ vì đổi mục tiêu.
- Dọn tài liệu09/11 đã được phép, có ZIPprivate/Git a05f6c0, `docs/cleanup_2026_11_09.json`. Không xóa bằng chứng thí nghiệm.
- 26 tests Vrain đạt trước chuyển mục tiêu. Chưa có loader/train theo trạm mới; không nói đã chạy mô hình.
