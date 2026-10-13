# Stress test quan trắc trễ 5 giờ trên checkpoint đã train trễ 4 giờ

Động cơ: 24 file GSMaP NRT tải ngày 13/10/2026 có đủ cửa sổ thử lag5/issue17 UTC, còn lag4/issue16 chỉ 21/24 file được máy nhận trước mốc. Đây là **backfill**, không đo latency công bố JAXA. Trước khi cân nhắc cấu hình app, kiểm tra độ nhạy của checkpoint Bi-LSTM RAW Tweedie đã train với lag4.

Giữ nguyên ba seed/checkpoint, normalizer, hiệu chỉnh Platt, ngưỡng xác suất từ năm calibration và index validation. Chỉ dịch ba cột mưa vệ tinh/5×5 sang sớm hơn một giờ (`latency_h=5`). Cùng 22.080 mẫu mùa 5–10 **theo giờ Việt Nam** mỗi năm, 30 ô, tổng mưa 0–3 giờ. Suy luận lag4 tái tạo RMSE và CSI gốc với sai số số học; 2025 chưa chấm. Đây là **stress test sau khi thấy nguồn NRT**, không là mô hình lag5 được train lại hay xác nhận vận hành.

| Năm | RMSE lag4 → lag5 (mm/3h) | CI95% ΔRMSE lag5−lag4 | CSI xác suất ≥10 lag4 → lag5 | CI95% ΔCSI |
| --- | ---: | ---: | ---: | ---: |
| 2021 | 3,876 → 3,921 | [+0,002; +0,087] | 0,406 → 0,408 | [−0,022; +0,018] |
| 2022 | 4,581 → 4,582 | [−0,012; +0,010] | 0,261 → 0,256 | [−0,013; +0,004] |
| 2023 | 3,540 → 3,546 | [−0,031; +0,043] | 0,414 → 0,402 | [−0,029; +0,014] |

CI lấy mẫu bootstrap theo cặp, khối 5 ngày giờ Việt Nam, 1.000 lần; mọi ô cùng ngày đi cùng nhau. Đầu xác suất ≥1 mm (BS) xấu nhẹ cả ba năm; CSI từ **lượng mm** năm 2021 giảm 0,289→0,250. Không diễn giải CSI xác suất gần giữ nguyên là mô hình lag5 đã đủ tốt: lượng mưa 2021 có tín hiệu giảm chất lượng và dữ liệu đầu vào vận hành còn khác tập train.

Code: `.venv\Scripts\python.exe scripts\stress_latency_danang.py --batch-size 256`. Bảng chi tiết/CI từng năm trong `2021.json`–`2023.json` và `summary.json`; dự báo từng mẫu ở `data/operational/followup_danang/latency_stress/` ngoài Git. Bước tiếp theo là **train và hiệu chỉnh lại ứng viên lag5** trên cùng thiết kế/seed/ngân sách, kiểm định nhiều năm và nguồn NRT as-of trước khi thay checkpoint app. Đồng thời ghi liên tục để biết JAXA thực sự phát hành file sau bao lâu, thay vì suy từ một lần tải lại.
