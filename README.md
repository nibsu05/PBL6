# PBL6 — dự báo lượng mưa tại nhiều trạm

**Quyết định ngày 09/11/2026:** nhóm chuyển cả dự báo cực ngắn và ngắn sang **dự báo tại trạm**. [Thiết kế hiện hành gửi nhóm](project_plan_v2.md), [kế hoạch thực hiện](KE_HOACH_DU_AN.md), [metadata phạm vi](docs/station_forecast_scope.json).

## 86 trạm là ở đâu?

Đây là **86 vị trí trong nhóm dữ liệu “Đà Nẵng” mà tài khoản Vrain truy cập được**, không phải toàn Việt Nam. Số 86 là danh mục ứng viên, chưa phải số trạm đã chọn huấn luyện. Cần kiểm tra tọa độ theo phạm vi nghiên cứu khi chốt tập trạm.

Danh mục mới có 82 vị trí khớp danh mục cũ và bốn vị trí bổ sung. Trong kho lịch sử, số trạm có ít nhất một giá trị giờ sau QC: **2021: 57; 2022: 79; 2023: 79; 2024: 82**. Không đồng nghĩa đủ cả năm hoặc cả 86 có dữ liệu từ 2021.

## Hai nhánh và cách dùng mô hình

| Nhánh | Nhãn tại chính trạm | Mô hình |
| --- | --- | --- |
| Cực ngắn | Sáu lượng mưa giờ tiếp theo, 1–6h | Bi-LSTM và đối chứng |
| Ngắn | Ba tổng 24h riêng của ngày 1/2/3 | LightGBM, TFT, Informer |

Mỗi kiến trúc dự kiến dùng **một mô hình chung cho nhiều trạm**. Một mẫu là `(trạm, thời điểm)`, không bắt buộc 86 mô hình riêng. Mưa Vrain làm nhãn; ERA5 phải trích phù hợp tọa độ trạm. Mục tiêu chính đã chuyển từ mưa trung bình diện tích sang mưa tại điểm đo.

## Nguồn nằm ở đâu, đã sẵn sàng train chưa?

**Đã có nguồn, chưa có tập huấn luyện theo trạm hoàn thiện.** Vẫn phải xác nhận đơn vị, múi giờ, đầu/cuối kỳ đo; kiểm tra chất lượng, chọn trạm đủ lịch sử và trích ERA5 tại trạm.

| Nguồn | Vị trí riêng |
| --- | --- |
| Vrain lịch sử 2021–2024, raw/checksum/QC | `data/operational/vrain_2026_11_09/download/`, `freeze_work/` |
| Registry 86 mã chuẩn và nguồn đóng gói | `data/operational/vrain_2026_11_09/handoff_v1/`, `PBL6_VRAIN_SOURCE_V1.zip` |
| Vrain 02/01–08/11/2026, hai kênh riêng | `data/operational/vrain_2026_11_09/recent_archive/` |
| ERA5 theo ô đã có, cần trích theo trạm | `data/processed/dataset_v2_danang/` |
| Bộ trung bình vùng cũ, chỉ tham khảo | `data/processed/regional_danang/` |

**Predictor 44 kênh trong ZIP nguồn cũ vẫn là trung bình vùng, chưa phải predictor tại trạm.** Không nhân bản nó và đổi tên thành dataset trạm. Các phản hồi 2015–2020 không có hàng giờ Vrain; không gọi đó là ngày khô. Năm 2025 vẫn giữ kín; chưa dùng 2026 để fit/tuning hoặc tự nối hai kênh.

## Công việc tiếp theo

Chốt thời gian/QC/tập trạm → trích ERA5 tại trạm → dựng hai loader và split → pilot → mở rộng trạm đạt → E0–E7 và ba mô hình ngày. Thiếu tại một trạm không buộc loại mẫu hợp lệ ở trạm khác. Báo điểm từng trạm và trung bình giữa trạm, kèm thống kê gộp khi cần.

Mã kiểm kê/collector hiện có: `scripts/download_vrain_archive.py`, `scripts/download_vrain_recent.py`. Vrain có manifest riêng; nguồn cũ trên Drive kiểm bằng `scripts/package_data.py verify`. Có 26 tests Vrain đã đạt; chưa có kết quả train theo trạm.

## Bằng chứng và phương án cũ

- [Bàn giao nguồn 82/86](reports/vrain_data_handoff_2026_11_09/CHOT_DU_LIEU_GUI_NHOM.md), [Word](reports/vrain_data_handoff_2026_11_09/CHOT_DU_LIEU_GUI_NHOM.docx): nguồn và giới hạn, chưa phải tập train theo trạm.
- [Đánh giá nhãn vùng và lý do đổi mục tiêu](reports/vrain_data_handoff_2026_11_09/DANH_GIA_KHA_THI_VA_HUONG_DI.md), [Word](reports/vrain_data_handoff_2026_11_09/DANH_GIA_KHA_THI_VA_HUONG_DI.docx): được viết trước quyết định theo trạm, giữ làm lịch sử.
- [Kết quả CPC ngày](reports/daily_gauge_2026_11_04/README.md), [GSMaP ba mô hình](reports/short_range_complete_2026_10_28/README.md): vẫn là kết quả vùng của nguồn cũ, chưa phải Vrain tại trạm.
- [Phương án hợp nhất cũ](reports/regional_research_plan_2026_10_20/PHUONG_AN_CUOI.md), [biên bản dọn](docs/cleanup_2026_11_09.json).

GitHub công khai chỉ chứa mã, tài liệu và thống kê tổng hợp. Raw, registry/tọa độ từng trạm, credential, PDF, checkpoint và dự đoán từng mốc nằm ngoài Git. Làm trên `research/tft-regional`, không tự merge main; giữ nguyên slide người dùng sửa.
