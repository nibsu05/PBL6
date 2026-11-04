# Báo cáo đầy đủ TFT vùng: cơ sở LightGBM và vai trò POD/FAR

- [PowerPoint 34 slide chỉnh sửa được](PBL6_TFT_DAY_DU.pptx): 24 slide chính và 10 slide tra cứu; có notes.
- [Bản trình chiếu HTML độc lập](PBL6_TFT_DAY_DU.html): mở trình duyệt, dùng phím trái/phải hoặc nút; không cần Internet.
- [Lời dẫn từng slide](LOI_DAN_TRINH_BAY.md), [phân tích và nguồn](PHAN_TICH_LIGHTGBM_POD_FAR.md).
- [Ảnh xem trước toàn bộ slide](XEM_TRUOC.png).
- [Excel 18 sheet và Word giải thích đầy đủ](../short_range_explained_2026_10_21/README.md).
- [Hồ sơ paper](literature.json), [audit dev theo commit](dev_metrics_audit.json), [số đếm E7](E7_CONTINGENCY_COUNTS.csv).

In đậm theo phép so ghi dưới bảng: tốt nhất trong cột hoặc số cần đối chiếu; không tự đồng nghĩa ý nghĩa thống kê. BSS âm màu đỏ. Sáu bảng phụ lục có đủ 48 dòng E0–E7 × hai mô hình × ba ngày, với RMSE/MAE/Bias/BSS/CSI/POD/FAR. Có cả giới hạn ngày 3, vùng xấp xỉ và nhãn vệ tinh.

Kết luận: LightGBM có cơ sở ứng dụng dự đoán mưa; POD/FAR cần đi cùng CSI, BSS và sai số lượng mm. Chưa có lý do ưu tiên riêng POD hoặc FAR cho mọi mục tiêu. Giữ protocol hiện tại, chưa đổi tiêu chí sau khi xem development. Chưa mở test 2025 hoặc fit mô hình mới.

Tái lập: `python scripts/build_short_range_presentation.py`; kiểm tra bằng `python scripts/validate_short_range_presentation.py`. Cần môi trường dự án và requirements-reports. Slide đọc bảng tổng hợp đã công bố, không cần raw data/checkpoint. Hồ sơ dev là ảnh chụp commit fe27756, không đại diện mã thành viên chưa push.

Có thể dựng ảnh/kiểm tra tràn chữ bằng `python scripts/render_short_range_presentation.py` với Chrome/Edge đã cài. Đây là render bản HTML từ cùng bố cục/số liệu, chưa phải render PowerPoint bằng Office. Ảnh toàn bộ kích thước lớn và hồ sơ trình duyệt ở data/operational ngoài Git; chỉ ảnh tổng quan và biên bản kiểm tra được công bố.
