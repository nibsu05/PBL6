# Bản kế hoạch để duyệt: TFT mưa vùng 24–72 giờ

Ngày 21/10/2026. **Người dùng đã duyệt kế hoạch và ưu tiên pilot trong 3–4 giờ.** [Bộ pilot đã hoàn tất](../short_range_pilot_2026_10_21/README.md) có Word, slide và kết quả thật. Bản kế hoạch/Word/protocol ban đầu bên dưới được giữ như hồ sơ đề xuất; trạng thái triển khai hiện tại đọc theo README này và bộ pilot.

**Đã mở rộng tiếp:** [E0–E7, ba seed, 72 TFT + 24 LightGBM](../short_range_ablation_2026_10_21/README.md), có Word, 8 slide, FAQ, danh mục biến, 20.000 bootstrap khối 7/14 ngày và replay 96/96 lượt. Ranh/nhãn và test cuối vẫn chưa hoàn tất; năm 2025 giữ kín. Ma trận dùng footprint xấp xỉ được khóa và công bố trước chạy, không tự coi là toàn địa giới Đà Nẵng chính xác.

- [Kế hoạch đầy đủ](KE_HOACH_TFT_24_72H.md) và [bản Word](KE_HOACH_TFT_24_72H.docx): phạm vi, dữ liệu, mô hình, ma trận, kiểm chứng và thời gian.
- [Lịch theo giai đoạn](LICH_THUC_HIEN.csv): G0–G7, điều kiện hoàn thành và giờ công.
- [Protocol đề xuất](protocol_proposed.json): cấu hình máy đọc được, chưa phải log thực nghiệm.
- [Kiểm kê development](preflight_development.json): số mẫu và sự kiện từ2015–2023, không phân tích2025.
- [Checksum](build_manifest.json): kiểm tra gói tài liệu.

Phương án chính: V1 vùng, lịch sử7ngày gộp6h, dự đoán ba tổng24h ngày1/2/3, TFT+LightGBM, E0–E7, ba fold phát triển, E0/E7 holdout2025. Informer/ECMWF/V2/app chưa nằm trong phạm vi chính.

Dự toán ban đầu **48–70 giờ công có dự phòng** là khung nghiên cứu đầy đủ, chưa phải thời gian đã làm. Dự toán GPU 8–30 giờ trước benchmark đã được thay bằng số đo: pilot 186,8 giây; ma trận 96 lượt khoảng 27,9 phút. Nhiều seed/factorial đã có trên footprint xấp xỉ, còn ranh/QC nhãn và holdout cuối. Nếu đổi vùng hoặc cấu hình phải đo và chạy lại; thu thêm ô biên có thể thêm 2–5 ngày hoặc hơn tùy nguồn.

Lượt lập kế hoạch ban đầu chỉ kiểm kê read-only và verify nguồn2233/2233. Sau duyệt đã triển khai loader/TFT và chạy pilot; chưa mở2025. Hai script sau chỉ phục vụ tái tạo kiểm kê và hồ sơ kế hoạch, không huấn luyện:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/inspect_short_range_plan.py
.\.venv\Scripts\python.exe -X utf8 scripts/build_short_range_plan.py
```

Các lệnh chạy từ thư mục gốc repo; script xuất Word cần `python-docx` đang có trong môi trường. Việc kiểm kê cần tệp V1 cục bộ, giữ ngoài Git như quy ước dự án.
