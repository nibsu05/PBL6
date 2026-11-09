# PBL6 — bắt đầu từ đây

Nghiên cứu thêm/bớt đặc trưng để **dự đoán trực tiếp mưa trung bình vùng Đà Nẵng mới**. Bi-LSTM phụ trách 1–6 giờ; LightGBM/TFT/Informer phụ trách ba tổng mưa 24h riêng của ngày 1–3. ERA5 cung cấp khí tượng; Vrain đã tải xong phản hồi nguồn, cần QC để xây nhãn vùng. Chưa có bộ huấn luyện Vrain hoàn chỉnh.

## 1. Dữ liệu và tiến độ tải

**Hoàn tất lúc 17:57 ngày 09/11/2026:** đã lưu đủ 3.653/3.653 phản hồi ngày và kiểm tra SHA256 của cả bản nén/lẫn dữ liệu giải nén. Bảng giờ có ở toàn bộ 1.461 ngày từ 01/01/2021–31/12/2024; 2.192 ngày yêu cầu thuộc 2015–2020 không trả hàng giờ. Đây không phải bảo đảm mọi trạm/giờ đều đủ: có thiếu tại trạm và ba ngày cần rà soát tổng giờ so với hàng tổng. [Thống kê sau tải](docs/vrain_archive_summary.json).

**Vrain có dữ liệu mới hơn 2024.** Phạm vi trên là đợt tải đã chọn, không phải giới hạn hệ thống. Kiểm tra thêm xác nhận dữ liệu2026 và kênh hiện hành86trạm (`kttv`, cần ngữ cảnh tổ chức của tài khoản) có bảng10phút tới18:50ngày09/11 và xuất được giờ. Kênh nhóm cũ82ID không trả một số ngày gần đây dù kênh mới có. [Bằng chứng kiểm tra mới](docs/vrain_recent_check.json). Chưa tải toàn bộ2026;2025vẫn giữ kín. Không tự trộn hai bộ mã trạm.

Đợt này yêu cầu từng ngày **01/01/2015–31/12/2024**, tổng 3.653 ngày, không đọc 2025. Khoảng yêu cầu không có nghĩa nguồn có đủ từ 2015; ngày không có hàng giờ được ghi riêng.

- [Trạng thái sống: progress.json](data/operational/vrain_2026_11_09/download/progress.json).
- [Raw chia theo năm, mỗi ngày một JSON nén](data/operational/vrain_2026_11_09/download/raw).
- [Manifest/checksum/counts](data/operational/vrain_2026_11_09/download/manifest.sqlite).
- [Log lỗi](data/operational/vrain_2026_11_09/download/stderr.log).

Xem tiến độ trong PowerShell:

```powershell
.venv\Scripts\python.exe -X utf8 scripts/download_vrain_archive.py --status
```

Dừng và tiếp tục:

```powershell
.venv\Scripts\python.exe -X utf8 scripts/download_vrain_archive.py --stop
.venv\Scripts\python.exe -X utf8 scripts/download_vrain_archive.py --resume
```

Tiếp tục sẽ kiểm tra checksum và bỏ qua ngày đã tải đúng. Nếu trạng thái là `login_required`, chạy cùng script với `--login` để nhập lại trong terminal, rồi `--resume`. Không ghi mật khẩu vào câu lệnh hoặc tệp. Phiên lưu bằng Windows DPAPI.

**Giữ mạng, cắm ổ D: và tránh Sleep/Hibernate; có thể tắt màn hình.** Không cần GPU hoặc mở Vrain trên trình duyệt. Chương trình giữ máy thức khi tải; sau khởi động lại cần chạy tiếp tục. Dự toán ban đầu 60–90 phút ở tối đa một request/giây, chưa tính QC/tạo nhãn.

## 2. Chỉ đọc các tài liệu hiện hành này

- [Word đầy đủ gửi nhóm](reports/vrain_research_plan_2026_11_09/PHUONG_AN_VRAIN_GUI_NHOM.docx), [Word ngắn](reports/vrain_research_plan_2026_11_09/TOM_TAT_GUI_NHOM.docx).
- [Excel đặc trưng, hợp đồng cột và phân công](reports/vrain_research_plan_2026_11_09/DU_LIEU_VRAIN_VA_PHAN_CONG.xlsx).
- [Kế hoạch công việc](KE_HOACH_DU_AN.md), [thiết kế kỹ thuật](project_plan_v2.md).

## 3. Phân biệt các bộ dữ liệu

| Bộ | Vị trí | Ý nghĩa |
| --- | --- | --- |
| Vrain đã tải | `data/operational/vrain_2026_11_09/download/` | Đủ phản hồi yêu cầu; nguồn còn cần QC, chưa phải nhãn vùng |
| Inventory và mẫu ban đầu | `data/operational/vrain_2026_11_09/` | 82 ID V1 khớp lịch sử; không trộn với 86 mục V2 |
| ERA5/bộ vùng cũ | `data/processed/regional_danang/` | 2015–09/2026, nhãn cũ và footprint xấp xỉ |
| Nhãn Vrain trung bình vùng | Chưa xuất | Cần kỳ đo, polygon, panel và trọng số |

Không đổi thiếu thành 0. Hàng tổng 0 khi không có hàng giờ chưa chứng minh ngày khô. Tải xong không đồng nghĩa đủ điều kiện huấn luyện.

## 4. Kết quả cũ giữ để tham khảo

- [Ma trận CPC ngày](reports/daily_gauge_2026_11_04/README.md) và [slide mới nhất, giữ bản người dùng sửa](reports/daily_gauge_slides_2026_11_04/README.md).
- [Ma trận GSMaP đủ ba mô hình](reports/short_range_complete_2026_10_28/README.md).
- [Phương án vùng và sáu tiêu chí](reports/regional_research_plan_2026_10_20/PHUONG_AN_CUOI.md), [bằng chứng V1/V2](reports/regional_danang_v1_v2/README.md).

Ngày 09/11 đã xóa ba kế hoạch gốc lỗi thời và ba bộ trình bày bị thay thế, sau khi sao lưu. [Biên bản dọn](docs/cleanup_2026_11_09.json). Các bản gốc còn trong Git ở commit `a05f6c0`; công cụ báo cáo lịch sử cần checkout phiên bản đó để tái lập.

Repo công khai chỉ chứa mã/cấu hình/thống kê; raw, inventory từng trạm, thông tin truy cập và mô hình nằm ngoài Git.
