# PBL6 — bắt đầu từ đây

Nghiên cứu thêm/bớt đặc trưng để **dự đoán trực tiếp mưa trung bình vùng Đà Nẵng mới**. Bi-LSTM phụ trách 1–6 giờ; LightGBM/TFT/Informer phụ trách ba tổng 24h riêng của ngày 1–3. ERA5 cung cấp khí tượng; Vrain cung cấp mưa tại trạm để nghiên cứu xây nhãn vùng.

## Tài liệu hiện hành gửi nhóm

**[Đánh giá khả thi và hướng đi sau kiểm định — Word](reports/vrain_data_handoff_2026_11_09/DANH_GIA_KHA_THI_VA_HUONG_DI.docx)**, [bản đọc](reports/vrain_data_handoff_2026_11_09/DANH_GIA_KHA_THI_VA_HUONG_DI.md), [biểu đồ độ nhạy nhãn](reports/vrain_data_handoff_2026_11_09/DO_NHAY_NHAN_VUNG.png). Đã thử che trạm theo lịch sử và giấu trạm/khối không gian; khuyến nghị chưa chốt toàn Đà Nẵng mới làm nhãn chính, ưu tiên kiểm chứng một vùng cố định nhỏ hơn cho nhánh ngày. Đây là đề xuất phạm vi, chưa tự thay đổi vùng hoặc train mô hình mới.

**[Bàn giao dữ liệu và giải thích 82/86 trạm — Word](reports/vrain_data_handoff_2026_11_09/CHOT_DU_LIEU_GUI_NHOM.docx)**, [bản đọc trên GitHub](reports/vrain_data_handoff_2026_11_09/CHOT_DU_LIEU_GUI_NHOM.md), [thống kê kiểm kê](docs/vrain_data_freeze.json).

**Đã chốt danh mục chung 86 vị trí:** 82 vị trí khớp tọa độ duy nhất giữa hai kênh, trong đó 81 tên giữ nguyên và một tên khác; bốn vị trí chỉ có ở danh mục mới. Không cộng thành 168 trạm. Danh mục 86 không có nghĩa cả 86 trạm đều có dữ liệu từ 2021.

**Đã đóng gói nguồn; chưa chốt nhãn vùng để train chính thức.** Kiểm kê phát hiện thiếu số đo tại các vị trí đại diện diện tích lớn trong những năm đầu. Chỉ giữ trạm rất đầy đủ lại làm vùng núi ít được đại diện. Còn phải xác nhận ngữ nghĩa đồng hồ và ranh vùng. Chi tiết đo được nằm trong tài liệu bàn giao; không gọi bộ nguồn là bộ huấn luyện đã bảo đảm.

## Dữ liệu nằm ở đâu?

| Thành phần | Thời gian / nội dung | Vị trí riêng trên máy |
| --- | --- | --- |
| Gói gửi thành viên | Nguồn, registry chung, QC, predictor và checksum; không có phiên đăng nhập | `data/operational/vrain_2026_11_09/PBL6_VRAIN_SOURCE_V1.zip` |
| Bản giải nén | Một thư mục bàn giao chung cho nhóm | `data/operational/vrain_2026_11_09/handoff_v1/` |
| Vrain lịch sử | 1.461 bảng ngày có giờ, 2021–2024; 2015–2020 chỉ có phản hồi không có giờ | `data/operational/vrain_2026_11_09/download/` |
| Vrain bổ sung 2026 | 02/01–08/11/2026, 311 ngày × hai kênh, kiểm tra SHA và số đo hợp lệ riêng | `data/operational/vrain_2026_11_09/recent_archive/` |
| ERA5 trong gói | 44 kênh giờ trước 2025, bỏ nhãn GSMaP cũ; 42 kênh ngày mới là cấu hình dự kiến | `handoff_v1/era5_predictors_hourly_44.parquet` |
| Nhãn mưa trung bình vùng Vrain | **Chưa đóng phiên bản** | Chờ hợp đồng thời gian và kiểm chứng estimator không gian |

2025 vẫn giữ kín; không lấy dữ liệu 2026 để tuning rồi gọi 2025 là kiểm định tương lai. Phạm vi tải 2026 bắt đầu 02/01 để tránh cửa sổ ngày 01/01 chứa giờ thuộc 2025. Bảng đồng hồ nguồn chưa tự được xem là 00–24h UTC.

Không đổi thiếu thành 0, không tự tạo lịch sử cho bốn trạm bổ sung, không nối hai kênh chỉ theo tên và không âm thầm đổi trọng số vùng theo giờ. Footprint 93 ô khác mạng 86 trạm; R93 vẫn là xấp xỉ ranh Đà Nẵng mới.

## Công cụ và công việc tiếp theo

- [Kế hoạch công việc](KE_HOACH_DU_AN.md), [thiết kế kỹ thuật](project_plan_v2.md).
- Tải bổ sung 2026 có resume: `.venv\Scripts\python.exe -X utf8 scripts/download_vrain_recent.py`.
- Đóng gói sau khi tải đủ: `.venv\Scripts\python.exe -X utf8 scripts/finalize_vrain_handoff.py`.
- QC không gian cần thêm `requirements-vrain-qc.txt`. Bộ kiểm thử Vrain: `python -m unittest tests.test_vrain_download tests.test_vrain_export_audit tests.test_vrain_station_identity tests.test_vrain_spatial_panel`.
- Manifest của nguồn cũ trên Drive kiểm bằng `scripts/package_data.py verify`; gói Vrain có manifest riêng.

Việc tiếp theo là xác nhận thời gian/ranh và kiểm chứng nhãn vùng, sau đó pilot cùng nhãn/mask/split trước khi chạy lại toàn bộ E0–E7. Chưa có kết quả mô hình Vrain.

Tái lập kiểm định nhãn: `scripts/assess_vrain_label_feasibility.py`; xuất tài liệu/biểu đồ từ aggregate: `scripts/publish_vrain_feasibility.py`. JSON/CSV trong thư mục bàn giao ghi rõ 67 ngày tham chiếu cuối 2024 không phải chân lý độc lập, và các phân vị qua mẫu thiếu không phải CI. Bộ kiểm thử thêm `tests.test_vrain_label_feasibility` (tổng 26 tests Vrain).

## Bằng chứng lịch sử

- [Kế hoạch Vrain ban đầu, mới kiểm tra 10 ngày](reports/vrain_research_plan_2026_11_09/README.md); đã có kiểm kê toàn kho và bàn giao mới ở trên.
- [Ma trận CPC ngày](reports/daily_gauge_2026_11_04/README.md), [slide giữ bản người dùng sửa](reports/daily_gauge_slides_2026_11_04/README.md).
- [Ma trận GSMaP đủ ba mô hình](reports/short_range_complete_2026_10_28/README.md).
- [Phương án vùng và sáu tiêu chí](reports/regional_research_plan_2026_10_20/PHUONG_AN_CUOI.md), [bằng chứng V1/V2 cũ](reports/regional_danang_v1_v2/README.md).

GitHub chỉ chứa mã, tài liệu và thống kê tổng hợp. Raw, registry từng trạm, thông tin truy cập và mô hình nằm ngoài Git. Các tài liệu bị thay thế đã dọn có biên bản tại `docs/cleanup_2026_11_09.json`; giữ nguyên các slide người dùng đang sửa.
