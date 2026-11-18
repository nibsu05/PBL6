# Diễn biến GFS trong ngày — đã hoàn thành

[Báo cáo Word](BAO_CAO_CAI_TIEN_NGAN_HAN.docx) · [Markdown](BAO_CAO_CAI_TIEN_NGAN_HAN.md) · [Slide](PBL6_CAI_TIEN_DU_BAO_NGAN_HAN.pptx) · [Kết luận](KET_LUAN.md)

57 trạm; LightGBM T0–T3, GRU T0/T3/LINEAR23, ba seed và năm đối chứng. Dữ liệu2025–2026 đã xem nên vòng mới là hồi cứu; không fit/tuning bằng các năm này. [Phương án](PHUONG_AN_THUC_HIEN.md) và protocol ghi đầy đủ cách chia mẫu/đầu vào/đầu ra. Kết quả cũ được giữ nguyên.

Mọi dữ liệu trạm và checkpoint nằm ngoài Git tại `data/operational/gfs_temporal_2026_11_17/`. Gói riêng gửi nhóm là `PBL6_NGAN_HAN_GFS_VRAIN_2021_2026.zip` trong thư mục đó, gồm một Parquet đã ghép X/y và năm tệp hướng dẫn/kiểm tra. Các CSV công khai chỉ chứa thống kê tổng hợp.
