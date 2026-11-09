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

**Đã kiểm kê nguồn và thống nhất danh mục; chưa có nhãn vùng được duyệt để train.** Kho cũ có 3.653 phản hồi đã kiểm tra SHA; có bảng giờ cho 1.461 ngày 2021–2024, 2015–2020 không trả giờ. Ba station-day chênh tổng đã gắn cờ loại, số gốc được giữ. [Bàn giao hiện hành](reports/vrain_data_handoff_2026_11_09/CHOT_DU_LIEU_GUI_NHOM.md).

**Đã tải bổ sung 02/01–08/11/2026: 622/622 phản hồi, 311 ngày × hai kênh.** Không gọi đó là cả năm 2026. Kiểm kê phân biệt ngày có bảng với ngày có số thật. 2025 vẫn chưa đọc; ngày 01/01/2026 được bỏ vì chứa giờ 2025. [Thống kê đóng gói](docs/vrain_data_freeze.json).

- Yêu cầu3653ngày từ2015đến2024, tối đa1request/giây; không đọc2025.
- Raw nén theo năm ở `data/operational/vrain_2026_11_09/download/raw/`.
- Checksum/counts ở `download/manifest.sqlite`; lỗi/ngày không có giờ ghi riêng.
- Tải nền có resume, không cần GPU/trình duyệt. Giữ mạng/ổD/máy thức.
- Ước tính ban đầu60–90phút chỉ tải. Ngày yêu cầu không đồng nghĩa có quan trắc.
- Đã chốt registry chung 86: 82 cặp khớp tọa độ duy nhất, 81 tên giống và một tên khác; bốn vị trí bổ sung. Giữ nguồn số đo riêng, chưa tự nối chuỗi. Metadata kỳ đo và ranh chưa chốt.
- Chẩn đoán R93: toàn mạng cố định không có ngày đủ 100% coverage trong 2021–2023; chọn panel 45 trạm đầy đủ lại làm khoảng cách lớn nhất từ tâm ô tới trạm tăng khoảng 34→59 km. Không tự nhận nhãn vùng đã bảo đảm.

**Đã kiểm định thêm độ nhạy nhãn:** dùng 67 ngày đủ cả 82 trạm cuối 2024 làm tham chiếu nội bộ; che trạm theo lịch sử 2021–2023. Thiessen tính lại có NRMSE trung vị toàn R93 16,3–21,4%, phần vùng núi 60–71%. Đây không phải sai số thật của các năm lịch sử, không phải kết quả dự báo và không phải chứng nhận nhãn. Thiếu 100% không tự động là bất khả thi; vấn đề là sai lệch khi mạng thiếu. [Đánh giá và hướng đi](reports/vrain_data_handoff_2026_11_09/DANH_GIA_KHA_THI_VA_HUONG_DI.md).

**Khuyến nghị đang đề xuất:** nhánh ngày 1–3 ngày, vùng cố định có thể kiểm chứng, có thể nhỏ hơn địa giới mới; toàn Đà Nẵng mới là mở rộng có điều kiện. Nếu không có nhãn vùng đạt, dự phòng mô hình chung dự báo tại nhiều trạm. Chưa tự đổi phạm vi, chưa train vùng khác. Ưu tiên chốt thời gian/ranh/phương pháp nhãn trước ma trận mô hình.

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
| Kiểm kê nguồn — đã thực hiện | Registry 86, thiếu theo năm, chênh tổng, SHA và gói nguồn riêng của nhóm |
| Dữ liệu gần đây — đã thu thập phạm vi chọn | 622 phản hồi; số hợp lệ và so cặp hai kênh trong thống kê; chưa tự nối số đo |
| Xác minh/QC | Đơn vị, đầu/cuối kỳ, múi giờ, missing/trace/counter; xử lý trùng/lỗi |
| Nhãn vùng — việc cần giải quyết | Chọn phạm vi có thể kiểm chứng; polygon chung X/y; lịch sử vùng núi; estimator mạng thiếu có khai báo và kiểm định, không đổi trọng số âm thầm |
| Pilot | E0/E2/E7, thửR0/R1 trên cùng mask; baseline và kiểm tra leak |
| Ma trận | Rgiữcốđịnh, đủE0–E7 và ba mô hình ngày; split theo lịch sử thật |
| Kiểm định cuối | Khóa protocol trước mở2025 |

Nếu nguồn/độ phủ chưa đủ, báo giới hạn và chỉnh thiết kế trước train. Không chia mưa ngày thành giờ, không điền thiếu bằng0 hay thay y bằngCPC/ERA5 âm thầm.

## 7. Tài liệu gửi nhóm

[Word bàn giao hiện hành](reports/vrain_data_handoff_2026_11_09/CHOT_DU_LIEU_GUI_NHOM.docx), [nội dung](reports/vrain_data_handoff_2026_11_09/CHOT_DU_LIEU_GUI_NHOM.md). Gói riêng: `data/operational/vrain_2026_11_09/PBL6_VRAIN_SOURCE_V1.zip`.

Tài liệu `vrain_research_plan_2026_11_09/` là kế hoạch ban đầu từ 10 probe, giữ làm lịch sử; không dùng nó thay kiểm kê toàn kho mới.

## 8. Quy tắc chung

Giữ2025kín; CSI/BSSchính, POD/FAR và lỗi mm bổ sung. Cùngnhãn/mẫu/mùa/baseline/CI; chấp nhận kết quả âm. Giữ slide người dùng sửa và nguồn thí nghiệm. Raw/credential/model ngoàiGit; làm trênresearch/tft-regional, không tự merge main.
