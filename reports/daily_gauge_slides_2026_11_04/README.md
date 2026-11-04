# Slide mới: ERA5 ngày → mưa CPC vùng 1–3 ngày

- [PowerPoint chỉnh sửa được, 44 slide](PBL6_DU_LIEU_NGAY_3_MO_HINH.pptx).
- [HTML xem bằng trình duyệt](PBL6_DU_LIEU_NGAY_3_MO_HINH.html), [lời dẫn từng slide](LOI_DAN.md).
- [Word và Excel 11 sheet của thí nghiệm](../daily_gauge_2026_11_04/README.md).

30 slide chính và 14 phụ lục. Bốn nhóm biến ở slide 10, E0–E7 ở 11, tám metrics ở 16; ba bảng BSS ở 20–22; E7 đủ metrics ở 23–25; khoảng tin cậy ở 26–28. Phụ lục 31–39 tra đủ 72 dòng E0–E7, luôn đủ ba mô hình cạnh nhau.

Gợi ý trình bày 12–15 phút: 1–3, 6–8, 10–11, 14–16, 20–22, 26–30. Các trang còn lại dùng giải thích khi cần. Đậm chỉ là điểm tốt hơn cùng E/ngày; đỏ là BSS âm. CPC là phân tích lưới từ trạm, footprint còn xấp xỉ, Vrain chưa có. Không dùng điểm khác nhãn so với bộ GSMaP trước để kết luận bước ngày tốt hơn.

Chỉ dựng báo cáo từ aggregate đã kiểm chứng; không train thêm hoặc mở 2025. Giữ nguyên các báo cáo đã công bố và slide người dùng chỉnh sửa. Tái lập: build_daily_gauge_slides.py → render_daily_gauge_slides.py → validate_daily_gauge_slides.py.
