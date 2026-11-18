# Kiểm chứng cuối dự báo mưa ngắn hạn — 17/11/2026

Đã hoàn thành đối chứng GRU, khóa mô hình trước test 2025 và chấm riêng 2026 theo nguồn.
Mô hình chính/tiêu chí không đổi sau khi xem test; 17 phương án cùng mẫu, 57 trạm cố định.

Đọc [kết luận](KET_LUAN.md), [báo cáo](BAO_CAO_KIEM_DINH.md), [Word gửi nhóm](BAO_CAO_KIEM_DINH.docx).
Phương án chốt trước fit nằm ở [đây](PHUONG_AN_KIEM_DINH.md), [protocol](protocol.json), [khóa cuối](final_manifest.json).

- **Khí tượng thô N1–N0 (LightGBM):** đủ tiêu chí cải thiện trên test ở ngày 2, 3.
- **Địa hình N3–N1 (LightGBM):** chưa đủ tiêu chí xác nhận cải thiện trên test sau hiệu chỉnh nhiều so sánh.
- **Dẫn xuất N5–LINEAR6 (GRU):** chưa đủ tiêu chí xác nhận cải thiện trên test sau hiệu chỉnh nhiều so sánh.
- **LGB_N3 so MOS, RMSE mean:** đủ tiêu chí cải thiện ở ngày 3.
- **GRU_N5 so MOS, MAE median:** đủ tiêu chí cải thiện ở ngày 1, 3.

Nguồn 2026 chưa xác nhận liên tục giữa hai API; các bảng đó là kiểm tra độ bền kèm giới hạn nguồn.
Raw/checkpoint/dự báo từng thời điểm là private. [Kiểm chứng cuối](final_verification.json) và các CSV ghi rõ metric/mẫu/hạn.
