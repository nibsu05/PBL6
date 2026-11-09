# Kế hoạch công việc hiện tại — 09/11/2026

Điểm vào duy nhất là [README](README.md). Đây là công việc đang làm; kết quả nguồn cũ dùng làm bằng chứng tham khảo.

## 1. Mục tiêu

Nghiên cứu thêm/bớt đặc trưng để dự đoán trực tiếp mưa trung bình vùng Đà Nẵng mới. Một mẫu là một issue của vùng; app hoặc bản đồ dự báo từng ô chưa là trọng tâm.

Bi-LSTM: sáu lượng giờ tiếp theo. LightGBM/TFT/Informer: ba tổng mưa24hriêng ngày1/2/3.

## 2. Dữ liệu

ERA5 quá khứ làmX. Vrain từng trạm cần QC/ranh/trọng số để thành y vùng. Mưa Vrain quá khứ là nhómR đề xuất thử riêng. Các bộ Parquet/CPC/GSMaP cũ không tự trở thành dữ liệuVrain.

## 3. Quy trình

Tải nguồn → kiểm kê/QC → chốt vùng và mạng trạm → tổng hợp nhãn giờ/ngày → ghépERA5 → kiểm tra loader/split → pilot → E0–E7 → khóa thiết kế → kiểm định cuối.

## 4. Đang ở giai đoạn nào

**Đã tải xong và kiểm tra checksum đủ 3.653 phản hồi; chưa có bộ huấn luyện Vrain.** Hoàn tất17:57VN09/11/2026. Có bảng giờ cho1.461ngày2021–2024; các ngày2015–2020không trả giờ. Trạm vẫn thiếu theo thời gian và có ba ngày cần kiểm tra tổng. [Thống kê sau tải](docs/vrain_archive_summary.json), [trạng thái](data/operational/vrain_2026_11_09/download/progress.json).

- Yêu cầu3653ngày từ2015đến2024, tối đa1request/giây; không đọc2025.
- Raw nén theo năm ở `data/operational/vrain_2026_11_09/download/raw/`.
- Checksum/counts ở `download/manifest.sqlite`; lỗi/ngày không có giờ ghi riêng.
- Tải nền có resume, không cần GPU/trình duyệt. Giữ mạng/ổD/máy thức.
- Ước tính ban đầu60–90phút chỉ tải. Ngày yêu cầu không đồng nghĩa có quan trắc.
- V1có82IDkhớp lịch sử; V2có86mục khác namespace. Metadata kỳ đo, ranh và độ phủ chưa chốt.

## 5. Phân công đề xuất

| Người | Bàn giao |
| --- | --- |
| Phụ trách dữ liệu | Inventory/lịch sử/QC, polygon/panel/trọng số, nhãn giờ/ngày và manifest |
| Phụ tráchBi-LSTM | Loader vùng, sáu nhãn giờ, persistence/LightGBM và pilotR0/R1 |
| Người dùng phụ tráchTFT | Ba mô hình nhánhngày cùngmẫu, E0–E7, metrics/CI/báo cáo |

Cả nhóm thống nhất region/timezone/anchor/panel/mask/version. Không mỗi người gộp theo một cách.

## 6. Công việc tiếp theo và điều kiện chuyển bước

| Bước | Bằng chứng cần có |
| --- | --- |
| Tải nguồn — đã hoàn tất | Đủ3.653phản hồi, checksumgzip/raw đạt; không lỗi tải |
| Kiểm kê — bước tiếp theo | Độ đầy đủ từng trạm/mùa, panel ổn định và ba ngày chênh tổng |
| Xác minh/QC | Đơn vị, đầu/cuối kỳ, múi giờ, missing/trace/counter; xử lý trùng/lỗi |
| Nhãn vùng | Polygon chungX/y, panel ổn định, trọng số cố định, coverage và độ bền nhãn |
| Pilot | E0/E2/E7, thửR0/R1 trên cùng mask; baseline và kiểm tra leak |
| Ma trận | Rgiữcốđịnh, đủE0–E7 và ba mô hình ngày; split theo lịch sử thật |
| Kiểm định cuối | Khóa protocol trước mở2025 |

Nếu nguồn/độ phủ chưa đủ, báo giới hạn và chỉnh thiết kế trước train. Không chia mưa ngày thành giờ, không điền thiếu bằng0 hay thay y bằngCPC/ERA5 âm thầm.

## 7. Tài liệu gửi nhóm

[Word đầy đủ](reports/vrain_research_plan_2026_11_09/PHUONG_AN_VRAIN_GUI_NHOM.docx), [Word ngắn](reports/vrain_research_plan_2026_11_09/TOM_TAT_GUI_NHOM.docx), [Excel dữ liệu/phân công](reports/vrain_research_plan_2026_11_09/DU_LIEU_VRAIN_VA_PHAN_CONG.xlsx).

Các tài liệu này ghi10probe ban đầu; tiến độ tải lớn nằm trong progress/manifest. Không viết lại báo cáo probe thành audit toàn kho.

## 8. Quy tắc chung

Giữ2025kín; CSI/BSSchính, POD/FAR và lỗi mm bổ sung. Cùngnhãn/mẫu/mùa/baseline/CI; chấp nhận kết quả âm. Giữ slide người dùng sửa và nguồn thí nghiệm. Raw/credential/model ngoàiGit; làm trênresearch/tft-regional, không tự merge main.
