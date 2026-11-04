# Báo cáo sửa theo phản hồi: dễ hiểu, đủ bảng và pilot Informer

- [PowerPoint 42 slide](PBL6_BAO_CAO_DE_HIEU.pptx), [HTML trình chiếu](PBL6_BAO_CAO_DE_HIEU.html).
- [Giải thích Word](GIAI_THICH_THEO_CAU_HOI.docx), [Markdown](GIAI_THICH_THEO_CAU_HOI.md), [lời dẫn](LOI_DAN.md).
- [Kết quả pilot Informer và protocol](../informer_regional_pilot_2026_10_21/run.json), [bảng cùng seed TFT/Informer](../informer_regional_pilot_2026_10_21/scores_pooled.csv).
- [Bảng đối chiếu quy tắc báo mưa](DECISION_RULES_E7.csv), [nguồn kiểm chứng POD](POD_SOURCES.json).
- [Excel đầy đủ E0–E7 và Word trước](../short_range_explained_2026_10_21/README.md).

Có 30 slide chính và 12 slide tra cứu. Bảng nhóm biến ở slide 5; seed ở 7–8; bảng metrics đầy đủ ở 13; POD0,4 ở 17–18; hai quy tắc POD ở 23; Informer ở 27. Không phải đọc mã mới hiểu phần chính. Chữ đậm có chú thích theo phép so; không tự là ý nghĩa thống kê.

Đây là phát triển trên vùng 93 ô xấp xỉ. Informer chỉ thử E0/E7 với cùng seed hoàn chỉnh và các điều kiện đã đăng ký, chưa tuning hoặc chạy đủ E0–E7. Giữ nguyên kết quả cũ; không chấm 2025. Raw data/checkpoint/dự đoán từng mốc ở data/operational ngoài Git.

Tái lập slide: `python scripts/build_short_range_revised.py`; cần kết quả pilot đã hoàn thành và bảng quy tắc tổng hợp. Bộ slide 34 trang trước giữ nguyên để đối chiếu.
