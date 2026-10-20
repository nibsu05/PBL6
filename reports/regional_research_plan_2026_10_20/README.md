# Bàn giao phương án nghiên cứu mưa vùng trực tiếp

Ngày 20/10/2026. Có thể gửi PHUONG_AN_CUOI.docx cho thành viên; bản Markdown chứa cùng nội dung và dễ dùng để cập nhật bối cảnh cho công cụ hỗ trợ code.

- **PHUONG_AN_CUOI.docx / .md:** tài liệu tự đứng được, gồm mục tiêu vùng trực tiếp, các quyết định có bằng chứng giữ lại, nhãn/trọng số, V1/V2, E0–E7, mô hình, đánh giá, sửa code và lộ trình.
- **Phụ lục A:** 18 điểm khác nhau; mỗi điểm ghi rõ chọn bên nào và giải thích C1–C6, đủ 108 nhận định theo tiêu chí.
- **Phụ lục B:** các số liệu bằng chứng gốc được giữ trong đúng giao thức, không tráo bằng số tốt hơn từ mẫu khác.
- **QUYET_DINH_6_TIEU_CHI.csv / decisions.json:** cùng ma trận quyết định, thuận tiện lọc/đối chiếu.
- **feature_groups.json:** danh sách chính xác các cột B/A/M/C và tổ hợp E0–E7. Đây là protocol dự kiến thực hiện, chưa phải log đã huấn luyện.
- **feature_catalog_reference.csv / build_manifest.json:** danh mục nguồn/cột và checksum tài liệu.

Khi đọc context cũ của dev, ưu tiên hai xác nhận mới: nghiên cứu đặc trưng là trọng tâm; dự đoán vùng trực tiếp là đầu ra chính. 93 ô được tổng hợp thành X/y vùng trước khi học. Không quay lại mặc định phải làm app, TFT hay dự đoán riêng từng ô. Giữ các mục [CHỐT · BẰNG CHỨNG] theo quy tắc trong tài liệu; phần thay đổi đầu ra không phải tuyên bố vùng trực tiếp đã thắng mô hình lưới.

Việc tiếp theo: hoàn thiện ranh/trọng số, sửa loader/phép chấm và truy vết checkpoint, chạy tối thiểu trước ma trận chính. Không dùng các chỉ số E0–E7 cũ trên dev như kết quả Bi-LSTM vùng đã được xác nhận; giữ kín 2025.

Toàn bộ tài liệu và mã xuất được đưa lên main theo yêu cầu người dùng. Gói [ZIP bàn giao](PBL6_phuong_an_vung_truc_tiep_2026_10_20.zip) chứa tài liệu, metadata, mã xuất và bản đề xuất Markdown gốc để đối chiếu. Không có huấn luyện mới hoặc chấm test 2025 trong lần bàn giao này.

Tạo lại Word, CSV và checksum từ thư mục gốc repo (cần cài `python-docx` trong môi trường Python):

```powershell
.\.venv\Scripts\python.exe -m pip install python-docx
.\.venv\Scripts\python.exe -X utf8 scripts/build_final_regional_plan.py --source "C:\Users\Vie\Downloads\TONG_HOP_DE_XUAT.md"
```

`--source` chỉ dùng ghi checksum tài liệu gốc khi tệp tồn tại; nội dung phương án và ma trận quyết định đã nằm trong thư mục này. Các tệp văn bản dùng LF để checksum nhất quán khi tải từ GitHub.
