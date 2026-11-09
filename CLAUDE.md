# PBL6 — bối cảnh hiện hành cho agent

Cập nhật 09/11/2026. Đọc file này trước, rồi `KE_HOACH_DU_AN.md` và `project_plan_v2.md`. Người dùng bắt đầu từ `README.md`.

## Quyết định mới nhất của người dùng — đã chốt

**Chuyển cả hai nhánh sang dự báo lượng mưa tại trạm.** Người dùng nói: “nhóm tôi thực hiện dự đoán cực ngắn và ngắn theo trạm”. Quyết định này thay mục tiêu dự báo trực tiếp mưa trung bình diện tích toàn Đà Nẵng trước đây. Không tự đưa mục tiêu vùng trở lại hoặc ưu tiên app.

- Thành viên khác: Bi-LSTM, sáu lượng mưa giờ tiếp theo tại từng trạm, 1–6h.
- Người dùng: LightGBM/TFT/Informer, ba tổng 24h riêng của ngày 1/2/3 tại từng trạm.
- Đề xuất kỹ thuật: mỗi kiến trúc học một mô hình chung cho nhiều trạm; một mẫu là `(station_id, issue_time)`. Không cần 86 mô hình riêng cho một kiến trúc.
- Nhãn là mưa Vrain tại chính trạm. Người dùng đã xác nhận: **10:00 = tổng mưa09:00–10:00 giờ Việt Nam, UTC+7**. Đơn vị hiển thị nguồn là mm. Không còn chờ xác nhận timezone hoặc nhãn vùng.

## Phạm vi và số trạm

86 là danh mục **nhóm “Đà Nẵng” mà tài khoản được truy cập**, không phải toàn Việt Nam. Chưa chứng nhận mọi mục nằm đúng ranh hành chính cuối; lọc theo tọa độ/ranh khi chốt tập trạm nếu cần. Không gọi danh mục là phủ kín diện tích hoặc cả đảo.

- Kênh cũ có 82 vị trí, kênh hiện hành 86. 82 cặp tọa độ khớp chính xác/duy nhất, 81 tên giống và một tên khác; bốn vị trí bổ sung. Chưa biết thời điểm lắp đặt bốn trạm đó.
- Registry private 86 mã STxxx + alias hai kênh; giữ mã v1 khi thêm trạm sau này. Khớp metadata không chứng minh số đo hai kênh tương đương.
- Trong kho cũ, trạm có ít nhất một số giờ sau QC: 2021 **57**, 2022 **79**, 2023 **79**, 2024 **82**. Không đồng nghĩa đủ cả năm. Không mặc định cả 86 có lịch sử từ 2021 hoặc đã được chọn train.
- Bản dataset trạm v1 có82trạm lịch sử;79trạm có cửa sổ train hợp lệ cho cả hai nhánh, ba trạm còn lại không vào đánh giá mặc định. Đây là điều kiện cấu trúc, chưa chứng nhận cảm biến;24trạm có dưới180mẫu ngày train. Pilot một nhóm đại diện trước; thiếu tại trạm A không loại mẫu hợp lệ của B.

## Nguồn đã có và trạng thái

Private base `data/operational/vrain_2026_11_09/`:

- `download/`: 3.653 response 2015–2024, SHA gzip/raw đạt; có bảng giờ cho 1.461 ngày 2021–2024; 2015–2020 không trả giờ, không phải ngày khô. Ba station-day chênh tổng đã gắn cờ, số gốc được giữ.
- `recent_archive/`: 622 response cho 02/01–08/11/2026, 311 ngày × hai kênh. Bỏ 01/01 vì cửa sổ có giờ 2025. Có số ở 87 ngày kênh cũ, 305 ngày kênh mới; số hàng không bằng số đo hợp lệ.
- `handoff_v1/`, `PBL6_VRAIN_SOURCE_V1.zip`: nguồn/registry/QC, **không phải tập train theo trạm đã dựng**. Predictor 44 kênh trong ZIP vẫn là trung bình vùng cũ; không đổi tên hoặc nhân bản thành đầu vào theo trạm. Có 21 hàng thiếu kx/tt (42 ô), giữ NaN.
- `freeze_work/station_matrices.npz`: ma trận giờ nguồn 2021–2024, mask/QC; clock là cuối khoảng giờ Việt Nam, theo xác nhận mới. Không sửa file nguồn vì metadata cũ; áp dụng contract khi dựng dataset mới.
- Hai kênh chỉ trùng số ở một vị trí/18 ngày/367 cặp, 46 cặp có mưa đều khác số. Không tự nối nguồn 2026 hoặc fit/tuning 2026.

**Bộ trạm đã dựng và kiểm tra:** `data/processed/station_v1/PBL6_TRAM_GIO_NGAY_V1.parquet`, một file chứa1h/24h, raw/QC, X/y và chỉ số sample-ready; ngoàiGit. Tài liệu ngắn gửi nhóm: `reports/station_data_handoff_2026_11_09/MO_TA_DU_LIEU.docx`. Kỹ thuật: `HUONG_DAN_TRAIN.md`, `dataset_summary.json`, `verification.json` cùng thư mục báo cáo.

**ERA5 gốc vẫn có tại `data/raw_data/gee/era5/grid/*.parquet`.** Builder mới nội suy trực tiếp từ bốn nút0,25° quanh trạm; tất cả82trạm lịch sử có nút bao quanh. Không dùng đường vòng93ô hoặc sao chép mean vùng. Yêu cầu đủ mọi nút có trọng số dương; giữNaN nếu thiếu. Context/SST/chênháp có miền vùng có chủ đích. Không dùng các cột mưa ERA5/GSMaP làm X/y. CubeR93 và bộ vùng cũ giữ làm lịch sử.

Kiểm tra đạt2.995.050hàng/2.480.367cửa sổ: nhãn Vrain gốc, tổng ngày, không vượt trạm/gap/split;45đối chiếu trườngERA5,328số mưa gốc,72mẫu qua loader. Đã có34tests (26Vrain+8mới). Chưa train mô hình trạm. Đây là kiểm tra ghép/cấu trúc, chưa chứng nhận cảm biến, vị trí lịch sử hay độ trễ vận hành.

## Hợp đồng thời gian và nghiên cứu

- Người dùng xác nhận10:00là mưa09–10hViệtNam. Chuẩn hóa `period_start_utc=02:00`, `period_end_utc=03:00`; ERA5tức thời lấy02:00UTC. Clock20:00hômtrước→19:00ngàyđánhdấu tạo ngày19:00→19:00, không phải00–24. Không dùng tiêu đề XLSX19:20 để đổi các bin giờ đã xác nhận.
- Lưu mưa theo khoảng đo, provenance, QC; không đổi thiếu thành0, không chia mưa ngày thành giờ, không lấp y bằng ERA5/CPC/GSMaP.
- B/A/M/C đã dựng theo trạm: giờ11/12/20/1, ngày9/12/20/1. E7=44/42kênh; thêmR=45/43. Statictọađộ2kênh+IDđi riêng, cùng cách dùng giữa cácE. C chỉSST, chưa phảiENSO/MJO.
- R là mưa quá khứ của chính trạm, thử R0/R1 riêng; khi ablation A/M/C phải giữ R và mask giống nhau. Chỉ lịch tương lai biết trước được dùng; không ERA5/mưa kỳ đích trong X.
- Split theo thời gian chung cho mọi trạm, toàn bộ nhãn nằm trong split. Fit scaler/reference trên train; earlystop/calibration/tau trên cal. Không random cửa sổ lẫn trạm/ngày.
- Bảnv1: train2021–22, cal2023, dev2024 theo giờ Việt Nam;2024chưa phải testcuối. Mask `sample_ready_r1` dùng chung mọiE/model/R0–R1. Loader `src/station_forecast_data.py` giữ mọi hàng thời gian trước chọn issue; không dropNaNrồi cắtchuỗi. Chưafit bất kỳ scaler nào.
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
- Có dataset/loader trạm mới,34tests và kiểm tra toàn file; chưa train mô hình. Scripts: `build_station_forecast_data.py`, `validate_station_forecast_data.py`, `publish_station_data_handoff.py`. Không đổi số đo vùng cũ thành kết quả trạm.
