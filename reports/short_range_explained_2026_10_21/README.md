# Giải thích đầy đủ và bảng kết quả TFT vùng 24–72 giờ

Đã xác nhận đủ E0–E7: 72 TFT, 24 pipeline LightGBM, 96/96 lượt replay. Đây là development trên footprint 93 ô xấp xỉ; năm 2025 giữ kín.

- [Tài liệu Word đầy đủ](GIAI_THICH_DAY_DU.docx), [bản Markdown](GIAI_THICH_DAY_DU.md): mục tiêu, ví dụ, dữ liệu, từng cấu hình, TFT/Informer/LightGBM, công thức và cách đọc metrics, bảng 48 dòng, CI, giới hạn và đủ 44 biến.
- [Excel kết quả đầy đủ](BANG_KET_QUA_DAY_DU.xlsx): bắt đầu sheet HUONG_DAN, có 18 sheet về kết quả/ngưỡng/năm/mùa/seed/CI/calibration và nguồn.
- [Bảng chính 48 dòng CSV](KET_QUA_CHINH_48_DONG.csv), [tiến độ 8 cấu hình](TIEN_DO_E0_E7.csv).
- [Bộ 5 slide và lời dẫn ngắn](../short_range_brief_2026_10_21/README.md), [kết quả gốc](../short_range_ablation_2026_10_21/README.md).

Bản này giải thích kết quả đã có, không thêm lượt huấn luyện hoặc thay dữ liệu. Chạy `python scripts/build_short_range_explainer.py` để dựng lại từ các bảng tổng hợp đã commit; cần requirements-reports và openpyxl trong môi trường dự án.
Chạy `python scripts/validate_short_range_explainer.py` để đối chiếu nguồn, hash, số liệu Excel/Markdown và cấu trúc Word; không đọc dữ liệu hoặc chấm lại mô hình.
