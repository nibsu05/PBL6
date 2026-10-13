# Bi-LSTM RAW Tweedie: retrain với quan trắc trễ 5 giờ

Câu hỏi xuất phát từ cổng NRT: 24 tệp đã tải đủ để thử nguồn trễ 5 giờ tại một issue ứng viên, nhưng checkpoint hiện tại train với trễ 4 giờ. Thí nghiệm này **train lại** cùng kiến trúc Bi-LSTM RAW Tweedie, cùng 30 ô, chính xác các index train/cal/eval cũ, 30.000 mẫu train mỗi fold, 3 seed (42–44), 15 epoch tối đa/patience 4, loss và batch size cũ. Chỉ `latency_h` của quan trắc vệ tinh đổi 4→5; normalizer fit trên cùng cột/năm/ô train nên được tái dùng. Xác suất và ngưỡng quyết định được fit lại trên năm calibration, không nhìn validation. Đối chứng lag4 tái tạo RMSE/CSI/BSS từ run gốc cả ba năm; test 2025 vẫn niêm phong.

Mùa 5–10 theo **giờ Việt Nam**, tổng mưa 0–3 giờ, 22.080 mẫu chung/năm:

| Năm | RMSE lag4 → retrain lag5 (mm/3h) | CI95% ΔRMSE lag5−lag4 | CSI xác suất ≥10 lag4 → lag5 | CI95% ΔCSI | BSS ≥1 lag4 → lag5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2021 | 3,876 → 3,929 | [+0,007; +0,105] | 0,406 → 0,385 | [−0,047; +0,004] | 0,260 → 0,248 |
| 2022 | 4,581 → 4,624 | [+0,010; +0,069] | 0,261 → 0,241 | [−0,041; +0,000] | 0,148 → 0,145 |
| 2023 | 3,540 → 3,578 | [+0,001; +0,068] | 0,414 → 0,413 | [−0,053; +0,041] | 0,217 → 0,199 |

Hiệu số và CI là bootstrap **theo cặp**, khối 5 ngày giờ Việt Nam, 1.000 lần. RMSE lag5 tăng nhỏ (khoảng 0,038–0,053 mm/3h, xấp xỉ 1%) nhưng CI dương ở cả ba fold; BSS ≥1 giảm mô tả cả ba. CSI xác suất giảm mô tả hai năm, song CI từng năm chứa 0. Đây là thí nghiệm **khám phá sau audit nguồn**, trên nhãn vệ tinh và ERA5 hồi cứu: CI không là xác nhận độc lập hay bằng chứng app sẽ kém đúng mức đó. Không đưa checkpoint lag5 vào app chỉ vì 24 tệp backfill đủ; cũng không giữ lag4 nếu nguồn thường đến muộn.

Kết quả gợi ý một đánh đổi thật cho PBL: độ trễ nguồn vận hành có thể đổi lựa chọn mô hình dù kiến trúc và dữ liệu train khác giữ nguyên. Quyết định app cần logger NRT liên tục để đo latency file mới, kiểm tra đầu vào khí tượng as-of và so cùng ECMWF trên tập đã ghép. Nếu lag4 không đủ nguồn, xét lịch phát hành khác, nguồn quan trắc khác hoặc một model dự phòng không cần mưa vệ tinh; kiểm định các nhánh ấy trước khi chọn.

Tái lập: `.venv\Scripts\python.exe scripts\train_bilstm_tweedie_lag5.py`. `run.json`, `summary.json`, bảng từng năm và CI nằm ở thư mục này; checkpoint và dự báo từng mẫu trong `data/operational/followup_danang/bilstm_tweedie_lag5/` ngoài Git. [Stress test checkpoint lag4 khi đầu vào trễ thêm](../latency_stress/README.md) là phép thử khác, không thay cho retrain.
