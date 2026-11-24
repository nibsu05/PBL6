# Vòng mới về số năm huấn luyện và hàm mất mát

- [Kết luận và bảng chính](KET_LUAN.md).
- [Báo cáo đầy đủ](BAO_CAO_MO_RONG_TRAIN.docx), [bản Markdown](BAO_CAO_MO_RONG_TRAIN.md).
- [Slide có thể chỉnh sửa](PBL6_MO_RONG_NAM_TRAIN_VA_LOSS.pptx).
- [Thiết kế trước fit](PHUONG_AN.md), [protocol](protocol.json), [kiểm chứng](verification.json).
- Các CSV báo đầy đủ hai API, ba hạn, lượng mưa/xác suất/cảnh báo/seed/CI.

Năm 2025 được hiệu chỉnh theo phê duyệt mới, không fit cây; năm 2026 đã xem, chỉ hồi cứu. Phiên bản cũ giữ nguyên. Chọn mô hình để ghi dự báo tương lai bằng CV 2022, không chọn bằng điểm 2026.

Gói nội bộ gửi nhóm: data/operational/gfs_training_window_2026_11_18/PBL6_NGAN_HAN_TRAIN_MOI.zip, chỉ một Parquet và các tệp mô tả; không đưa gói, dữ liệu hoặc checkpoint lên Git. Tiến trình theo dõi ghi một issue tương lai, cần máy và mạng còn hoạt động; kiểm chứng nhãn sau 72h cộng độ trễ, không có kết quả thực tế ngay.
