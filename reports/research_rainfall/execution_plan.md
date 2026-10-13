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

## Đánh giá sau lượt thực nghiệm 13/10

Đã chạy các thí nghiệm ưu tiên, không còn ở trạng thái đề xuất: Tweedie LightGBM/NN trên RAW, bỏ riêng proxy địa hình và 63 ô chưa train. Báo cáo/CI ở `reports/followup_danang/`. RMSE 3 h LightGBM Tweedie giảm 6–14% so L1(log) trên cả ba năm; Bi-LSTM Tweedie giảm khoảng 2–11% nhưng BSS xác suất ≥1 kém hơn trong 2022. DOMAIN vẫn chưa có CI khẳng định lợi ích CSI trên từng năm hoặc 63 ô. Đủ cơ sở tiếp tục PBL và hoàn thiện demo, chưa đủ chọn AI live.

Demo archive từ checkpoint có bản đồ 93 ô và bảng 30/63 ô tách rõ; 36 HTTP parity case và 81 kiểm tra code đạt. Tab live hiện chỉ có ECMWF thô/điểm JAXA công khai. Máy chủ FTP JAXA cổng 21 tới được, FTPS không hỗ trợ; chưa có binary NRT thực chứng. Không gọi tab live là app AI vận hành.

## Từ 14 đến 20/10: nối quan trắc và đóng băng ứng viên

1. Kiểm tra JAXA login bằng `scripts/fetch_gsmap_nrt.py --check-only --allow-plain-ftp` trong terminal riêng, nhập UID/password tương tác. Sau đó tải một binary v8, ghi hash, thời điểm lấy, version, khoảng mưa, phần trăm thiếu và tốc độ trễ. FTP thường không mã hóa trên máy chủ này; script không tự hạ cấp.
2. So một hoặc nhiều tệp NRT thật với nguồn MVK/raw trong train trên cùng ô/giờ. Đo phân phối và lỗi theo mùa nếu có đủ ngày; không giả định hai thuật toán tương đương từ định dạng giống nhau. Tập đủ lịch sử quan trắc trễ và context cho cửa sổ 24 h trước khi chạy AI.
3. Chốt máy luôn bật cho logger forecast/quan trắc. Dùng timestamp phát hành và lấy dữ liệu để bảo đảm không nhìn tương lai. Nếu nguồn NRT chưa đạt contract, demo tiếp tục hiển thị archive và ECMWF thô.
4. Xem lại RAW/DOMAIN và hai đầu Tweedie theo RMSE, bias, BSS/CSI, FAR và CI. Không đổi chọn model theo một metric duy nhất; không mở test 2025 khi chưa đóng băng thiết kế.

Điều kiện hết tuần: tệp NRT thật đã xác minh hoặc ghi rõ vì sao chưa truy cập được, logger có kế hoạch máy chủ, bảng ứng viên có lý do, demo archive chạy ổn.

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