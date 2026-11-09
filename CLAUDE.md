# PBL6 — bối cảnh hiện hành cho agent

Cập nhật 09/11/2026. Đọc trước file này, rồi `KE_HOACH_DU_AN.md` và `project_plan_v2.md`. Người dùng chỉ cần bắt đầu từ `README.md`.

## Mục tiêu và quy ước

- Trao đổi tiếng Việt, độc lập, có bằng chứng và trung thực cả kết quả âm.
- Nghiên cứu đặc trưng cho mưa trung bình vùng Đà Nẵng mới; một mẫu là một issue vùng. Không tự chuyển sang từng ô hoặc ưu tiên app.
- Thành viên khác phụ trách Bi-LSTM 1–6h; người dùng phụ trách LightGBM/TFT/Informer 1–3 ngày.
- Workspace `D:\PBL6_v2`, Python `.venv\Scripts\python.exe -X utf8`, RTX4060Laptop8GB. Python inline qua PowerShell dùng ASCII; nguồn tiếng Việt dùng UTF-8/apply_patch.
- Git: `git -c safe.directory=D:/PBL6_v2`. Làm trên `research/tft-regional`, push/PR vào main; không tự merge. Không commit raw, PDF, credential, checkpoint hoặc dự đoán từng mốc.
- Dữ liệu cũ từ Google Drive `pbl6_data_v2_*.tar`; `scripts/package_data.py verify` chỉ bao phủ nguồn cũ, không phải Vrain.

## Công việc hiện tại: tải Vrain

Đã đăng nhập/xuất mẫu thật tại `https://www.vrain.vn/landing`. Không nhắc lại hoặc lưu password vào nguồn/tài liệu; web session không đồng nghĩa có Open API key/quyền toàn quốc.

- Collector: `scripts/download_vrain_archive.py`; yêu cầu 2015-01-01→2024-12-31, 3653 ngày. Collector từ chối năm 2025.
- Trạng thái thật: `data/operational/vrain_2026_11_09/download/progress.json`; đọc file và PID, không lấy snapshot trong chat làm hiện tại.
- Raw: `download/raw/YYYY/YYYY-MM-DD.json.gz`; metadata/checksum: `download/manifest.sqlite`.
- Một request/giây, retry/backoff, khóa một worker, resume bằng checksum. Ngày không có giờ ghi `no_hourly_data`; cấu trúc lạ giữ raw và gắn cờ. Tải xong chưa phải dataset sạch.
- Cookie ở `download/session.dpapi`, mã hóa Windows. Không print cookie/header/signed URL. CLI `--login` rồi `--resume` nếu hết phiên. Không lưu mật khẩu.
- Tải nền bằng Start-Process `WindowStyle Hidden`, log private. Giữ máy thức nhưng cho màn hình tắt. Sau restart cần resume.
- Benchmark một ngày ~0,295s; request tuần/tháng chỉ trả tổng ngày nên phải tải từng ngày để giữ giờ. Dự toán ban đầu60–90phút với giới hạn1request/s, chưa tính QC/nhãn.

## Bằng chứng và giới hạn Vrain

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

Theo dõi tải → kiểm kê/QC → xác minh kỳ đo/ranh/panel/trọng số → nhãn vùng → pilotE0/E2/E7/R0/R1 → ma trận → khóa trước test2025. Cập nhật mục4/6 của kế hoạch khi đổi giai đoạn, không lặp lại lịch sử cũ.
