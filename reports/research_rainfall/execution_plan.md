# Kế hoạch thực hiện để chọn mô hình và triển khai app

Cập nhật 13/10/2026. Tập trung Đà Nẵng trước; ưu tiên một đầu ra kiểm chứng được mỗi tuần. Ba người cùng hiểu toàn bộ dự án, nhưng có người chịu trách nhiệm chính cho từng đầu ra; chưa gán tên.

## Mục tiêu cụ thể

Một app dự báo 6 giờ cho các ô 0,1° thuộc Đà Nẵng: mưa giờ, tổng 3 giờ và xác suất vượt ngưỡng, thời điểm cập nhật, trạng thái nguồn và so với forecast thô. Chọn cấu hình bằng đánh giá cùng mẫu và đầu vào thực sự có lúc phát hành. Một mô hình chung có đặc trưng địa hình; chưa tuyên bố đặc biệt phù hợp mọi tỉnh Việt Nam.

## Hai phép so trong kế hoạch

Giữ phép so mô hình/nhóm đặc trưng trên **cùng đầu vào, cửa sổ, nhãn và năm** để trả lời câu hỏi nghiên cứu. Thêm ECMWF IFS như đối chứng vận hành: lấy bản dự báo có `run` được khởi tạo trong quá khứ nhưng **đã sẵn có trước giờ app phát hành**, chấm trên đúng ô/giờ/hạn/nhãn với AI. [Open-Meteo Single Runs](https://open-meteo.com/en/docs/single-runs-api) giữ từng run ECMWF từ 03/2024 và nêu rõ giờ `run` chưa phải giờ công bố (thường trễ 4–6 h). T-OPS 2024 sẽ ghi `run_init`, `available_at` ước lượng bảo thủ/đã đo và `issue_at`, kiểm tra `available_at ≤ issue_at`, thử độ nhạy với độ trễ, rồi mới so ECMWF thô, ECMWF hiệu chỉnh, LightGBM và Bi-LSTM. ERA5 dùng trong hồi cứu không được thay cho dự báo đã phát hành. Chưa có kết quả cùng mẫu nên chưa kết luận AI vượt ECMWF. Hiện có 4 snapshot hiện tại/93 ô (không biết run), baseline trạm/ngày từ Previous Runs và **pilot 56/56 run, 30 ô × 14 ngày 2024** với 1.680 cặp forecast/nhãn. Pilot ECMWF qua Open-Meteo 0–3 h RMSE 3,950 mm, CSI≥10 0,089; chỉ 4 ngày có sự kiện mạnh, CI chênh RMSE với luôn 0 chứa 0. **Chưa có dataset run 2024 cho 93 ô hoặc phép so AI–ECMWF cùng mẫu.** Checkpoint hiện dùng ERA5 hồi cứu và GSMaP raw lưu trữ; phải kiểm tra/thay nguồn as-of trước khi gắn nhãn so vận hành.

## Đầu ra đợt này

| Đầu ra | Bằng chứng | Trạng thái |
| --- | --- | --- |
| So BASE/RAW/DOMAIN trên 3 fold năm, NN/cây | reports/domain_screen_danang/ | Đã xong:27NN+9LightGBM; summary.json xác nhận |
| Kiểm tra nguồn nhãn theo mùa và trạm | label_audit.json, label_station_scores.csv | Đã chạy trên 2021–2023 |
| Hợp đồng nguồn forecast và dữ liệu 93 ô | live_contract_probe.json, live_collection_status.json | 4 snapshot hoàn chỉnh 93/93 ô; chưa biết run, chưa dùng chấm AI |
| Pilot ECMWF lịch sử | ecmwf_pilot_14d/ | 56 run, 30 ô, 1.680 cặp 6 h đủ; số liệu và CI trong README/summary.json; chưa có AI cùng mẫu |
| Suy luận checkpoint và API | src/domain_inference.py, demo/domain_api.py | Đã chạy CPU/HTTP thật; archive validation |
| Báo cáo có kết quả, CI và đề xuất | brief_giang_vien_2026_10_14.md | Sinh từ số liệu, không thay việc huấn luyện |

## Đánh giá sau lượt thực nghiệm 13/10

Đã chạy các thí nghiệm ưu tiên, không còn ở trạng thái đề xuất: Tweedie LightGBM/NN trên RAW, bỏ riêng proxy địa hình, 63 ô chưa train và stress/retrain quan trắc lag5 ba fold. Báo cáo/CI ở `reports/followup_danang/`. RMSE 3 h LightGBM Tweedie giảm 6–14% so L1(log) trên cả ba năm; Bi-LSTM Tweedie giảm khoảng 2–11% nhưng BSS xác suất ≥1 kém hơn trong 2022. DOMAIN vẫn chưa có CI khẳng định lợi ích CSI trên từng năm hoặc 63 ô. Đủ cơ sở tiếp tục PBL và hoàn thiện demo, chưa đủ chọn AI live.

Demo archive từ checkpoint có bản đồ 93 ô và bảng 30/63 ô tách rõ; 36 HTTP parity case và 87 kiểm tra code đạt. JAXA FTP đã xác minh và tải raw/Gauge_NRT v8 cùng giờ; raw 93/93 ô hữu hạn, SHA-256 đúng. Popup web khác hai binary ở 3/3 ô có mưa, nguyên nhân chưa rõ. Tab live chỉ có ECMWF nguồn/điểm web tham khảo và cổng NRT lag4/issue16 21/24 tệp kịp; lag5/issue17 thử trong tương lai 24/24; chưa là app AI vận hành.

**Kết quả độ trễ nguồn:** Tải24h raw NRT cho thấy lag4/issue16 có21/24 file đến kịp máy; lag5/issue17 thử có24/24, nhưng giờ phát hành JAXA chưa được đo liên tục. Train lại Bi-LSTM RAW Tweedie lag5 cùng index/3seed/đầu loss làm RMSE 3h tăng +0,053/+0,043/+0,038 mm ở 2021/2022/2023 (CI95% hiệu số dương cả3), CSI xác suất ≥10 giảm mô tả 2/3 năm nhưng CI chứa0. [Bảng/CI](../followup_danang/bilstm_tweedie_lag5/README.md). Tín hiệu này là validation khám phá, chưa chọn lag4 hay lag5 cho app.

## Từ 14 đến 20/10: nối quan trắc và đóng băng ứng viên

1. Đã tải/kiểm 24 tệp raw NRT liên tiếp: SHA-256 đúng, 93/93 ô hữu hạn. `scripts/audit_jaxa_nrt_history.py` cho lag4/issue16 có 21/24 tệp kịp máy nhận; lag5/issue17 (lúc kiểm còn tương lai) có 24/24. **Đây là tải backlog**, không chứng thực latency phát hành JAXA. Đã stress và train lại lag5 trên validation. Watcher `scripts/watch_gsmap_nrt.py` đã test; người dùng chạy terminal với `--hours 12 --interval-s 600 --allow-plain-ftp`, nhập credential tại prompt và để máy không ngủ. Watcher bỏ qua baseline, chỉ ghi file **mới** và giờ thấy/tải; lần poll 10 phút cho cận trên latency, lỗi mạng làm bất định lớn hơn. Thu nhiều ngày rồi so hai cấu hình bằng NRT/khí tượng as-of trước khi đổi app. FTP thường không mã hóa trên máy chủ này; script không tự hạ cấp. Chỉ nhập credential ở prompt terminal.
2. Làm rõ sai khác popup web với binary bằng nguồn JAXA độc lập/phiên bản hiển thị; không dùng popup làm chuẩn. So lịch sử NRT thật với MVK/raw trong train trên cùng ô/giờ và đo lệch theo mùa khi đủ ngày. Không giả định hai thuật toán tương đương từ định dạng giống nhau; cần cửa sổ 24 h kết thúc trước giờ phát hành 4 h, tức ít nhất 28 h lịch sử khi bắt đầu ghi.
3. Chốt máy luôn bật cho logger forecast/quan trắc. Dùng timestamp phát hành và lấy dữ liệu để bảo đảm không nhìn tương lai. Nếu nguồn NRT chưa đạt contract, demo tiếp tục hiển thị archive và ECMWF thô.
4. Xem lại RAW/DOMAIN và hai đầu Tweedie theo RMSE, bias, BSS/CSI, FAR và CI. Nếu lag4 thường không kịp và lag5 giảm kỹ năng, train thêm đối chứng không cần vệ tinh trên cùng mẫu và giữ ECMWF nguồn làm dự phòng. Không đổi chọn model theo một metric duy nhất; không mở test 2025 khi chưa đóng băng thiết kế.

Điều kiện hết tuần: lịch sử NRT ≥28 giờ có timestamp/hash, kiểm tra lệch train→NRT và bất nhất popup được ghi rõ, logger có máy chạy, bảng ứng viên có lý do, demo archive chạy ổn.

## Từ 21 đến 27/10: kiểm định nguồn forecast thật và app 6 giờ

1. **Đã xong thí điểm nguồn ECMWF 01–14/10/2024 trên 30 ô**: 56/56 run, 1.680 cặp đủ forecast/nhãn và căn giờ +1 h được kiểm tra. Chỉ 4/14 ngày có sự kiện ≥10 mm/3 h, nên cần thêm ngày mưa trước kết luận kỹ năng. Chỉ mở rộng 93 ô/mùa khi đầu vào AI as-of/parity đạt. Dùng ECMWF IFS Single Runs 2024 giữ nguyên từng `run`. Giờ khởi tạo run không phải giờ công bố: Open-Meteo nêu global model thường trễ 4–6 h. Ghi hoặc chặn bằng `available_at` bảo thủ, kiểm tra `available_at ≤ issue_at` cho mọi tensor và làm phân tích độ nhạy; quan trắc cũng phải có `first_recorded_at ≤ issue_at`. Chuỗi Historical Forecast/past_days đã ghép không đủ để chứng minh as-of parity.
2. Trước so AI–ECMWF, thay/kiểm tra các trường ERA5 quá khứ bằng forecast có sẵn tại issue, nối raw NRT đủ lịch sử và tính `first_recorded_at`; chấm độ lệch phân phối/đơn vị/ô/giờ. Sau đó so cùng mẫu: ECMWF qua Open-Meteo, hiệu chỉnh xác suất đơn giản, persistence đúng độ trễ, LightGBM và ứng viên Bi-LSTM. Hiệu chỉnh/ngưỡng chỉ chọn trên tập cho phép; giữ 2025 kín tới khi đóng băng thiết kế.
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