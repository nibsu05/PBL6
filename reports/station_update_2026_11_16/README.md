# Dữ liệu cập nhật đến 2026

Ngày bàn giao 16/11/2026. [Mô tả dữ liệu và cách dùng](MO_TA_DU_LIEU.md) · [Word gửi nhóm](MO_TA_DU_LIEU.docx) · [Kiểm tra độc lập](verification.json).

Gói dữ liệu nội bộ: `data/processed/station_update_2026_11_16/PBL6_DATA_DEN_2026.zip`. Hai Parquet nằm cùng thư mục: mưa giờ và mẫu GFS–Vrain dự báo ngày. Raw/registry/dữ liệu từng trạm không nằm trên GitHub.

Nguồn đến 15/11/2026; issue đủ ba nhãn đến 12/11/2026. Danh mục 86 trạm, có thiếu theo từng trạm/giờ. Hai kênh nguồn giữ rõ provenance và chưa được chứng minh liên tục. Năm 2025 đã thu thập/QC theo yêu cầu cập nhật; chưa có lần fit, tuning hay chấm mô hình mới.

Tệp công khai gồm hợp đồng dữ liệu, nhóm N0–N5, số mẫu, độ phủ và cờ chất lượng tổng hợp. `dataset_summary.json` ghi checksum Parquet. Bộ này mở rộng dữ liệu GFS + Vrain hiện hành; không phải bản 44 biến ERA5 kéo dài đến 2026.
