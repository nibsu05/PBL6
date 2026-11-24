# Dữ liệu ngày: LightGBM, TFT và Informer

Đủ **168 lượt: 24 LightGBM + 72 TFT + 72 Informer**, E0–E7. Đầu vào ERA5 ngày, bảy ngày quá khứ; ba nhãn CPC 24 giờ riêng, mốc 12 UTC. Nhãn là phân tích lưới từ trạm, chưa là quan trắc trực tiếp toàn Đà Nẵng mới. Có 1072 mốc chung/hạn; số sự kiện ≥16 mm ngày 1/2/3: 116 / 117 / 118; test 2025 giữ kín.

- [Phương án, kết quả và giải thích Word](PHUONG_AN_VA_KET_QUA.docx), [Markdown](PHUONG_AN_VA_KET_QUA.md).
- [Excel 11 sheet](BANG_KET_QUA_NGAY.xlsx), [72 dòng chính, ba mô hình cạnh nhau mỗi E/ngày](KET_QUA_72.csv), [hình BSS cả ba mô hình](BSS_BA_MO_HINH.png).
- [Audit nguồn/trạm/EOD](source_audit.json), [truy vết các nguồn kiểm tra](source_probe_manifest.json), [protocol khóa](protocol_frozen.json).
- [Kiểm tra EOD bằng NOAA gốc và GSOD cờ G](station_eod_audit.json): hỗ trợ mốc 12 UTC tại trạm, không tự xác nhận chất lượng nhãn toàn vùng.
- [Kiểm chứng độc lập](validation.json), [CI và phạm vi phân tích](evaluation.json), [nhật ký 168 lượt](run.json).

Đậm trong báo cáo chỉ là điểm tốt nhất cùng E/ngày. Không so trực tiếp với điểm GSMaP cũ để nói dữ liệu ngày tốt hơn. Footprint 93 ô còn xấp xỉ; EOD theo metadata nguồn chưa xác nhận độc lập; đang chờ Vrain. Chỉ public mã và aggregate; nguồn thô, PDF, mô hình và dự đoán từng mốc nằm ngoài Git.
