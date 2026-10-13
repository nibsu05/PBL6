# Kế hoạch thực hiện để chọn mô hình và triển khai app

Cập nhật 13/10/2026. Tập trung Đà Nẵng trước; ưu tiên một đầu ra kiểm chứng được mỗi tuần. Ba người cùng hiểu toàn bộ dự án, nhưng có người chịu trách nhiệm chính cho từng đầu ra; chưa gán tên.

## Mục tiêu cụ thể

Một app dự báo 6 giờ cho các ô 0,1° thuộc Đà Nẵng: mưa giờ, tổng 3 giờ và xác suất vượt ngưỡng, thời điểm cập nhật, trạng thái nguồn và so với forecast thô. Chọn cấu hình bằng đánh giá cùng mẫu và đầu vào thực sự có lúc phát hành. Một mô hình chung có đặc trưng địa hình; chưa tuyên bố đặc biệt phù hợp mọi tỉnh Việt Nam.

## Đầu ra đợt này

| Đầu ra | Bằng chứng | Trạng thái |
| --- | --- | --- |
| So BASE/RAW/DOMAIN trên 3 fold năm, NN/cây | reports/domain_screen_danang/ | Đã xong:27NN+9LightGBM; summary.json xác nhận |
| Kiểm tra nguồn nhãn theo mùa và trạm | label_audit.json, label_station_scores.csv | Đã chạy trên 2021–2023 |
| Hợp đồng nguồn forecast và dữ liệu 93 ô | live_contract_probe.json, live_collection_status.json | 93/93 ô đạt contract; snapshot ngoài Git |
| Suy luận checkpoint và API | src/domain_inference.py, demo/domain_api.py | Đã chạy CPU/HTTP thật; archive validation |
| Báo cáo có kết quả, CI và đề xuất | brief_giang_vien_2026_10_14.md | Sinh từ số liệu, không thay việc huấn luyện |

## Từ 14 đến 20/10: chốt ứng viên và nối dữ liệu

1. Xem cả ba năm, biến thiên seed và CI. Nếu DOMAIN không lặp lợi ích, không đưa vào app chỉ vì tên gọi vật lý. Giữ RAW và BASE để kiểm tra nguồn; giảm số cấu hình khi lợi ích chưa rõ.
2. Với DOMAIN, bỏ từng proxy để biết thành phần nào giúp; xem gradient địa hình hai chiều như giả thuyết tiếp theo, cung cấp cùng gradient cho RAW. Tách đóng góp nguyên liệu còn thiếu bằng phép bỏ TCWV/bỏ gió–ẩm850 trên cùng cửa sổ RAW. CAPE/CIN là nhánh tiếp theo có giả thuyết về mưa đối lưu; đất là nhánh khám phá thấp hơn. Mỗi đợt chỉ trả lời một câu hỏi, không đồng thời đổi kiến trúc/loss/split.
3. Đánh giá đầu lượng mưa riêng: L1/Huber trên log có thể co mưa to về nhỏ. Thử một đầu Tweedie hoặc hai phần có/không mưa và cường độ, giữ nguyên dữ liệu/đầu xác suất. Báo bias/RMSE/CSI cùng mẫu; không chọn đầu mm bằng MAE đơn độc.
4. Duy trì ghi forecast mỗi giờ trên máy luôn bật. scripts/collect_domain_live.py đã có vòng lặp; hiện chạy giới hạn 2,1 giờ để không tạo dịch vụ vĩnh viễn ngầm. Thiết lập tác vụ Windows lâu dài khi chốt máy chạy.
5. Hoàn tất nguồn quan trắc NRT: kiểm tra truy cập GSMaP NRT hoặc IMERG Early, timestamp khoảng mưa, latency đo từ file thật, checksum và sơ đồ chuyển về ô. Thông tin đăng nhập qua công cụ/hệ thống máy, không vào chat/repo. Không lấy bản GC đã hiệu chỉnh trạm làm đầu vào live.
6. Làm giao diện archive từ API hiện có để xem bản đồ ô, các trận mưa và dự báo cùng quan trắc. Giao diện live dùng ECMWF thô trong lúc ML chưa đủ nguồn; ghi nguồn rõ. Đây là một đầu ra app cụ thể cho tuần đầu.

Điều kiện hoàn tất tuần: bảng chọn ứng viên có lý do; hợp đồng đơn vị/tầng/giờ cho mọi biến; quan trắc NRT mẫu đã kiểm tra hoặc ghi rõ điều kiện truy cập còn thiếu; demo archive dùng checkpoint thật. Không đổi kết luận để che thiếu nguồn.

## Từ 21 đến 27/10: kiểm định nguồn forecast thật và app 6 giờ

1. Dùng forecast lưu trữ có run/issued time kiểm tra biến thể vận hành trên năm 2024. Chứng minh từng tensor chỉ dùng bản forecast/quan trắc đã đến trước giờ phát hành. Historical Forecast/past_days ghép chuỗi chưa đủ bằng chứng cho run-time parity.
2. So cùng mẫu: forecast thô, hiệu chỉnh xác suất đơn giản, persistence đúng độ trễ, LightGBM và ứng viên Bi-LSTM. Hiệu chỉnh/ngưỡng chỉ chọn trên tập cho phép; giữ 2025 kín tới khi đóng băng thiết kế.
3. Cùng đầu vào qua pipeline train và app; kiểm tra thời gian, cloud%, m/s, q850, dữ liệu thiếu/cũ. Kiểm tra suy luận CPU hiện có là bước đầu; chưa thay parity nguồn vận hành.
4. App chỉ dùng ML khi đủ contract và được đánh giá. Nếu quan trắc thiếu/cũ, hiển thị nguồn dự phòng ECMWF thô hoặc cấu hình không quan trắc đã kiểm định; không điền 0 để tạo dự báo AI.
5. Mỗi dự báo lưu retrieved_at/issued_at/valid_at, version và hash đầu vào, độ trễ nguồn, dự báo và xác suất. Kiểm chứng sau khi nhãn đến; tách nhãn vệ tinh và trạm.

Điều kiện ra MVP: API/giao diện chạy định kỳ cho Đà Nẵng; lượng mưa/xác suất có điểm và giới hạn rõ; xử lý nguồn lỗi; forecast được lưu trước quan trắc đích. Nếu AI chưa thắng, app vẫn có forecast thô và bảng kiểm định; không quảng cáo lợi ích chưa đo.

## Sau MVP

TFT 1–3 ngày là câu hỏi riêng. So kiến trúc trên cùng đầu vào/hạn, có LightGBM/DLinear và dự báo số thô/hiệu chỉnh. Không cần thêm kiến trúc chỉ để có nhiều tên trong báo cáo. Mở rộng ô chưa thấy và hai vùng khí hậu sau; kết quả Đà Nẵng chưa chứng minh tổng quát hóa toàn quốc.

## Phân vai đề xuất cho 3 người

| Người phụ trách tạm | Đầu ra chính | Người kiểm tra chéo |
| --- | --- | --- |
| Thành viên 1 | Nhãn, thời gian, split, baseline, CI và bảng lựa chọn | 2 |
| Thành viên 2 | Huấn luyện, ablation có giả thuyết, checkpoint/normalizer, suy luận | 3 |
| Thành viên 3 | Ghi nguồn live, parity vận hành, API/giao diện, kiểm chứng | 1 |

Cuối mỗi tuần: cả nhóm xem cùng bảng, chốt một quyết định và một câu hỏi tiếp theo; cập nhật KE_HOACH_DU_AN.md mục4/6 và CLAUDE.md rồi commit/push. Dữ liệu, checkpoint và thông tin đăng nhập ngoài Git.

## Các lệnh đang dùng

    .venv\Scripts\python.exe scripts\screen_danang_domain.py --resume
    .venv\Scripts\python.exe scripts\predict_domain_archive.py --parity --year 2021
    .venv\Scripts\python.exe demo\domain_api.py --port 8766
    .venv\Scripts\python.exe scripts\collect_domain_live.py --hours 8 --interval 3600

API chỉ phục vụ archive validation 2021–2023. Ví dụ GET /api/meta liệt kê các ô/fold; /api/predict cần year, config, site, issue UTC. Test 2025 bị từ chối bằng kiểm tra mã. Bộ ghi hiện chỉ có khí tượng forecast, chưa có stream quan trắc NRT. Bản demo cũ demo/app.py hiển thị ECMWF thô, chưa chạy model mới.