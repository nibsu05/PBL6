# Gửi nhóm: hướng dữ liệu Vrain cho PBL6

**Ngày 09/11/2026 — đề xuất để triển khai, chưa huấn luyện Vrain.**

Mục tiêu giữ nguyên: nghiên cứu thêm/bớt đặc trưng để dự đoán trực tiếp mưa trung bình vùng Đà Nẵng mới. ERA5 tiếp tục cung cấp khí tượng; Vrain dùng để xây nhãn vùng từ trạm sau QC. Dữ liệu trạm không có nghĩa đo trực tiếp mọi điểm của tỉnh.

Đã đăng nhập/xuất được dữ liệu thật. Inventory V1 có 82 trạm và khớp mã lịch sử; V2 có 86 mục nhưng bộ mã khác, không gộp theo tên. Trong mười ngày probe, bảy ngày có 24 hàng giờ; ba ngày thử 2015/2019/2020 chỉ có hàng tổng. Ngày 15/01/2021 chỉ 50/82 trạm đủ 24 giá trị, ngày 14/10/2024 là 81/82. Chưa có kiểm kê toàn kho, chưa xác nhận đầy đủ timezone/ý nghĩa kỳ đo hoặc phủ địa hình.

**Cách tổng hợp:** chốt polygon và panel trạm lõi; chuẩn hóa khoảng đo/múi giờ; QC; dùng trọng số diện tích Thiessen cắt theo ranh để tạo một chuỗi mưa vùng. Lưu thiếu/coverage/version. Không lấy trung bình các trạm có số liệu tùy ngày, không điền thiếu bằng 0 và không coi hàng tổng 0 khi không có giờ là ngày khô. X ERA5 và y Vrain phải cùng vùng; 93 ô cũ còn là footprint xấp xỉ.

Hai nhánh dùng chung gốc: Bi-LSTM nhận lịch sử giờ, dự đoán sáu lượng mưa giờ tiếp; LightGBM/TFT/Informer nhận lịch sử ngày, dự đoán ba tổng 24h riêng. B/A/M/C giữ lại; mưa Vrain quá khứ là nhóm R mới. Thử R0/R1 cùng mẫu, sau đó giữ R cố định khi thêm/bớt A/M/C. Không so điểm Vrain mới với điểm CPC/GSMaP cũ để tuyên bố cải thiện.

**Việc trước mắt:** một người phụ trách inventory/lịch sử/QC/ranh/trọng số; một người Bi-LSTM; người phụ trách TFT chuẩn bị nhánh ngày và bảng ba mô hình. Trong 24–48h đầu cần timeline dữ liệu, coverage và số mẫu, chưa cần chạy lại toàn ma trận. Pilot E0/E2/E7 trước; chỉ chạy đủ E0–E7 sau khi dữ liệu và split đạt. Lịch sử thực quyết định fold, không mặc định train từ 2015. Giữ kín 2025.

Chi tiết nguồn, cổng bắt đầu/dừng, hợp đồng cột, cách lấy mẫu, metrics, phân công và lịch 5–10 ngày làm việc có điều kiện nằm trong tài liệu đầy đủ và workbook đi kèm. Chưa có lời hứa cải thiện tới 72h; chưa gọi đây là dự báo vận hành với đầu vào có sẵn tại mốc phát báo.
