# Kết quả mở rộng TFT vùng 24–72 giờ

Đã hoàn thành 72 lượt TFT (ba seed, E0–E7, ba fold) và 24 pipeline LightGBM; 96/96 lượt replay cả calibration/evaluation. Giữ nguyên [pilot](../short_range_pilot_2026_10_21/README.md), không mở 2025. Footprint 93 ô xấp xỉ.

- [Báo cáo Word](BAO_CAO_MO_RONG.docx), [bản Markdown](BAO_CAO_MO_RONG.md).
- [8 slide có lời dẫn](PBL6_TFT_24_72h_mo_rong_2026_10_21.pptx), [câu hỏi để chuẩn bị bảo vệ](CAU_HOI_BAO_VE.md).
- [Bảng ensemble gộp](scores_ensemble_pooled.csv), [từng seed](scores_seed_pooled.csv), [độ ổn định seed](seed_stability.csv).
- [44 đặc trưng, đơn vị và mô tả nguồn](feature_catalog.csv).
- [CI paired 20.000 lần, khối 7/14 ngày](paired_bootstrap.csv), [kiểm chứng checkpoint](checkpoint_audit.json).
- [Giao thức đã khóa trước chạy](protocol_frozen.json), [cấu hình và lịch sử](run.json).

- E7 ngày 1: BSS LightGBM 0.303; TFT ensemble 0.246.
- TFT, ΔBSS E7−E0 ngày 1 dương ở 3/3 seed; khoảng [+0.068; +0.153].
- Thêm riêng A hoặc M giúp ngày 1: 2/9 CI chính hiệu chỉnh trên 0.
- E7 ngày 3: BSS LightGBM -0.075; TFT ensemble -0.038.
- Đây là bằng chứng development; chưa chứng minh tốt trên holdout hoặc vận hành.

Dự báo từng dòng, Parquet và checkpoint nằm ngoài Git. Đây là ma trận development trên vùng xấp xỉ; còn ranh/nhãn và holdout để hoàn thiện nghiên cứu.

Tái lập trên đúng dữ liệu và mã đã khóa: chạy lần lượt `python scripts/run_short_range_matrix.py --stage all`, `python scripts/audit_short_range_matrix.py`, `python scripts/evaluate_short_range_matrix.py`, `python scripts/report_short_range_matrix.py`, `python scripts/validate_short_range_matrix.py`. Runner tiếp tục từ artifact đã có nếu checksum khớp; không tự chạy lại hoặc đổi giao thức. Dùng Python trong `.venv` của dự án.
