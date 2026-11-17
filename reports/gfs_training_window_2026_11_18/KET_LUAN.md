# Kết quả vòng mới

Trong 12 phép so A–D trên modern 2026, 1 phép đạt tiêu chí cải thiện thăm dò đã định; ablation có 0/6. Đây không phải xác nhận trên test chưa dùng.

Tweedie train dài (B) so với train ngắn (A) đổi RMSE ngày 1/2/3 lần lượt -0,025/-0,560/-0,407 mm/24h. Cả ba điểm giảm, nhưng chưa phép nào đạt đồng thời hai tiêu chí suy luận đã định. Phép đạt tiêu chí thăm dò: D−C, ngày 3: -0,949 mm/24h. Đổi sang L2 không cho lợi ích nhất quán qua các hạn, nên chưa có cơ sở thay mặc định Tweedie bằng L2. Khí tượng thô có điểm cải thiện ở cả ba hạn so với N0, nhưng chưa đạt tiêu chí suy luận ở vòng 2026 này; địa hình chỉ thay đổi rất nhỏ. Đây là tín hiệu để theo dõi tiếp, không phải chứng minh đã cải thiện chắc chắn trên một tập kiểm định mới.

| Mô hình | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | --- | --- | --- |
| A · 2 năm/Tweedie | 15,708 | 18,029 | 20,677 |
| B · 4 năm/Tweedie | 15,683 | 17,469 | **20,270** |
| C · 2 năm/L2 | **15,627** | 17,736 | 21,356 |
| D · 4 năm/L2 | 16,135 | **16,776** | 20,406 |
| GFS nguyên bản | 20,445 | 19,738 | 24,953 |
| MOS · 4 năm | 18,933 | 17,899 | 22,361 |

A/C: train 2021–22; B/D: train 2021–24. A/B Tweedie; C/D L2. Cùng 26 biến, 57 trạm, ngân sách và ba seed.

Lựa chọn để ghi dự báo tương lai: B, theo CV 2022 và cửa sổ dài định trước. Năm 2025 chỉ hiệu chỉnh xác suất/cutoff, không fit cây. Năm 2026 là hồi cứu đã xem, không phải test mới.

Đọc báo cáo Word/Markdown, slide và CSV đầy đủ. Không loại nhãn theo sai số. Kiểm chứng tương lai cần máy còn hoạt động và chờ nhãn sau 72h. Bi-LSTM tiếp tục để sau.
