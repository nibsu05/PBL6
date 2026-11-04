# Đủ E0–E7: LightGBM, TFT, Informer

- [PowerPoint 49 slide](PBL6_SO_SANH_3_MO_HINH_DAY_DU.pptx), [HTML](PBL6_SO_SANH_3_MO_HINH_DAY_DU.html), [lời dẫn](LOI_DAN.md).
- [Word giải thích](GIAI_THICH_KET_QUA_DAY_DU.docx), [Markdown](GIAI_THICH_KET_QUA_DAY_DU.md).
- [Excel chín sheet](BANG_KET_QUA_DAY_DU.xlsx), [72 dòng chính](KET_QUA_72.csv).
- [54 lượt Informer mới, 18 lượt dùng lại và kiểm chứng](../informer_regional_matrix_2026_10_28/README.md).

Đủ 72 Informer + 72 TFT + 24 pipeline LightGBM; ba mô hình cùng E/ngày/mẫu. Có 49 slide, 34 slide chính và 15 tra cứu. Các bảng E7 ở slide 27–29; BSS và CI ở 30; thêm riêng A/M/C ở 31. Đậm là điểm tốt hơn cùng E/ngày, chưa tự là ý nghĩa thống kê.

54 lượt mới giữ hàm fit cũ; E0/E7 và điểm TFT/LightGBM không đổi. CI mới là mô tả phát triển, chưa hiệu chỉnh nhiều phép; giữ riêng phép thử TFT chính. Không đọc 2025. Còn giới hạn ranh/QC nhãn, bước sáu giờ và kiểm định cuối. Tệp slide cũ do người dùng chỉnh sửa giữ nguyên; đây là phiên bản mới từ scene báo cáo đã công bố.

Tái lập báo cáo: `python scripts/build_short_range_complete.py`, `python scripts/render_short_range_complete.py`, `python scripts/validate_short_range_complete.py`, sau khi hoàn tất huấn luyện/kiểm chứng/đánh giá Informer.
