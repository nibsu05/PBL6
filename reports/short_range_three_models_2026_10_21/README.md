# Báo cáo so sánh đồng thời ba mô hình

- [PowerPoint 47 slide](PBL6_SO_SANH_3_MO_HINH.pptx), [HTML trình chiếu](PBL6_SO_SANH_3_MO_HINH.html).
- [Giải thích Word](GIAI_THICH_SO_SANH_3_MO_HINH.docx), [Markdown](GIAI_THICH_SO_SANH_3_MO_HINH.md), [lời dẫn](LOI_DAN.md).
- [Bảng 72 vị trí E × mô hình × ngày](KET_QUA_3_MO_HINH.csv): 54 đã có kết quả, 18 vị trí Informer chưa chạy; không điền 0.
- [Số đếm E7 ngày 1](SO_DEM_E7_NGAY1.csv); [ma trận TFT/LightGBM và bảng mùa](../short_range_ablation_2026_10_21/README.md), [pilot Informer và bảng mùa](../informer_regional_pilot_2026_10_21/README.md).
- [Giải thích nguồn POD và hai quy tắc báo mưa](../short_range_revised_2026_10_21/README.md).

Có 32 slide chính, 15 slide tra cứu. Bảng trạng thái ở slide 6; ba bảng E7 đầy đủ tám metrics ở slide 27–29. Mỗi bảng xếp hạng mô hình đặt đủ LightGBM, TFT, Informer trong cùng E/ngày; khi thiếu Informer thì không đánh dấu mô hình thắng. Ví dụ công thức hoặc ablation trong một mô hình được ghi rõ mục đích.

Informer mới chạy E0/E7, chưa E1–E6; đây là bản cập nhật trình bày, không huấn luyện mới. Đậm theo số hiển thị chỉ là điểm tốt hơn, chưa có kiểm định chênh lệch ba pipeline. Cùng dữ liệu/nhãn/mẫu nhưng khác biểu diễn giữa cây và mạng. Vùng 93 ô còn xấp xỉ, nhãn cần QC; không đọc test 2025.

Tái lập: `python scripts/build_short_range_three_models.py`, rồi `python scripts/render_short_range_three_models.py` và `python scripts/validate_short_range_three_models.py`. Các báo cáo cũ giữ nguyên.
