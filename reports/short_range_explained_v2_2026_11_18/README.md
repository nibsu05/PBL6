# Báo cáo ngắn hạn — bản giải thích từ đầu

Mở **[PBL6_NGAN_HAN_GIAI_THICH_DE_HIEU.pptx](PBL6_NGAN_HAN_GIAI_THICH_DE_HIEU.pptx)** để trình bày. Có **33 slide chính (~28 phút)** và **34 phụ lục**. Mỗi slide có Notes; [Word](GIAI_THICH_TU_DAU.docx) và [bản đọc](GIAI_THICH_TU_DAU.md) diễn giải bằng lời.

Bản này làm rõ một mẫu dữ liệu, cách LightGBM/GRU học, chia năm, chọn tham số, Tweedie/L2, rồi mới đọc từng kết quả. Ví dụ giả định luôn được đánh dấu. Đếm mưa lớn ở luồng chính là **micro**, các bảng chi tiết có **macro**; hai cách không trộn.

## Mốc đánh giá đủ tốt

- **Hơn đối chứng:** B giảm điểm RMSE so GFS và MOS dài trên ba hạn của hồi cứu2026 modern. Ngày1 giảm khoảng23,3% so GFS; không phải độ chính xác76,7%.
- **Cải thiện ổn định:** chưa đủ bằng chứng trong protocol mới để khẳng định B hơn đối chứng ổn định qua các thời kỳ; các phép suy luận A–D không thay cho B–GFS/MOS.
- **Đủ dùng thực tế:** chưa chứng minh. Còn bỏ sót và báo nhầm mưa lớn; cần yêu cầu sử dụng, nguồn đúng hạn và kiểm định tương lai đủ dài. Không có mốc POD0,4 hoặc RMSE cố định để tự gọi đạt.

Mô hình chung và giờ phát19h là lựa chọn thiết kế chưa được so với mô hình riêng hoặc giờ khác. Tweedie/L2 là loss đầu mean; thay loss không thay các đầu xác suất dùng chung theo cửa sổ.

Giữ riêng kiểm định2025 protocol cũ và hồi cứu2026 protocol mới; không xếp hạng bằng hai năm khác nhau. Bản cũ tại ../short_range_comprehensive_2026_11_18/ giữ nguyên. Không có huấn luyện hoặc chấm mô hình mới.

## Gửi thành viên

Gửi PPTX và Word; gói nội bộ gồm PDF có tại `data/operational/short_range_explained_v2_2026_11_18/PBL6_BAO_CAO_DE_HIEU.zip`. Gói báo cáo này không chứa dữ liệu train. Nguồn và giới hạn truy cập: [NGUON_TAI_LIEU.md](NGUON_TAI_LIEU.md). Bằng chứng số và kiểm tra nằm trong JSON cùng thư mục.
