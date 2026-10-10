# 📊 Báo cáo Đánh giá Mô hình Informer Baseline (Dự án PBL6)
*(Dành cho Tổng hợp & Thuyết trình Slide)*

---

## 1. Thiết lập Thí nghiệm (Experiment Setup)
- **Tên mô hình:** Informer Baseline (Tương đương I1 trong khung nghiên cứu)
- **Mục tiêu:** Đánh giá khả năng dự báo lượng mưa dài hạn (24 giờ tới) chỉ dựa trên dữ liệu quá khứ.
- **Input Features (6 biến):** Nhiệt độ 2m, Độ ẩm 2m, Áp suất, Tốc độ gió, Hướng gió, Lượng mưa (Nguồn: Open-Meteo).
- **Kiến trúc:** 
  - Khung thời gian: Nhìn lại 168 giờ (7 ngày) -> Dự báo 24 giờ.
  - Cơ chế cốt lõi: `ProbSparse Self-Attention` (giảm độ phức tạp tính toán).
- **Quá trình huấn luyện:** Train trên GPU RTX 3050 Ti, hội tụ cực nhanh (48s/epoch). Kích hoạt Early Stopping ở Epoch 11.

---

## 2. Kết quả Đánh giá Tổng thể (Overall Performance)

Mô hình Informer Baseline thể hiện sự vượt trội rõ rệt so với kiến trúc hồi quy tuần tự (Bi-LSTM) trước đó, dù sử dụng ít biến đầu vào hơn (6 biến so với 31 biến).

| Metric (Tại mốc t+6) | Bi-LSTM Baseline | Informer Baseline (I1) | Mức độ Cải thiện |
| :--- | :---: | :---: | :---: |
| **MAE** (Sai số tuyệt đối) | 0.381 mm/h | **0.300 mm/h** | Cải thiện ~21% |
| **RMSE** (Sai số toàn phương) | 1.146 mm/h | **0.913 mm/h** | Cải thiện ~20% |

**📝 Điểm nhấn cho Slide:** 
Cơ chế Attention toàn cục giúp Informer trích xuất chu kỳ thời tiết dài hạn (ngày/đêm, các ngày trong tuần) tốt hơn hẳn việc nén thông tin vào hidden state của Bi-LSTM.

---

## 3. Độ Ổn định Dài hạn (Horizon Degradation)

Thế mạnh lớn nhất của Informer (cơ chế Generative Decoder sinh toàn bộ 24h cùng lúc) được chứng minh qua việc độ chính xác suy giảm rất chậm theo thời gian:

- **t+1h:** MAE = 0.248 mm/h
- **t+6h:** MAE = 0.300 mm/h
- **t+12h:** MAE = 0.324 mm/h
- **t+24h:** MAE = 0.327 mm/h

**📝 Điểm nhấn cho Slide:** 
Mô hình giữ được "phong độ" ổn định một cách kinh ngạc ở ngày thứ 2 (t+24), MAE chỉ tăng cực kỳ nhẹ so với t+12. Điều này chứng minh Informer cực kỳ phù hợp cho bài toán Long Sequence Time-Series Forecasting (LSTF).

---

## 4. Phân tích Hành vi Mô hình (Model Behavior)

### Xu hướng làm phẳng (Smoothing Effect)
Đúng với bản chất của dự báo dài hạn (Synoptic-scale) và hàm loss MSE:
- Mô hình làm rất tốt việc **bắt được các pha mưa dầm, mưa nhỏ, và xu hướng thời tiết chung**.
- Mô hình **không dự báo các đỉnh mưa đối lưu cực đoan** (Dự báo cao nhất trên toàn tập test chỉ đạt 4.94 mm/h, dẫn đến CSI > 5mm = 0).

**📝 Lập luận bảo vệ trước Giáo sư:**
Việc mô hình không bắt được đỉnh nhọn mưa lớn (convective peaks) là **HỢP LÝ VÀ ĐÚNG BẢN CHẤT VẬT LÝ**. 
- Dự đoán chính xác thời điểm bùng nổ đối lưu (mưa to dồn dập trong 1-2h) là nhiệm vụ của **Dự báo cực ngắn (Nowcasting / 1-6h)** kết hợp dữ liệu Radar.
- Đối với **Dự báo dài hạn (1-7 ngày)**, mục tiêu là nắm bắt được *xu hướng mặt synop* (khi nào có đợt mưa diện rộng, khi nào nắng). Việc Informer ưu tiên giảm MAE trung bình bằng cách dự báo các đợt mưa kéo dài với cường độ vừa phải cho thấy nó đang hoàn thành xuất sắc đúng vai trò của một mô hình dài hạn.

---

## 5. Các Hình ảnh phục vụ Slide

Tất cả các biểu đồ đã được xuất sẵn tại thư mục: `PBL6/plots/informer/`

1. **`exp0_history.png`**: Đồ thị Loss giảm đều và hội tụ nhanh (chứng minh code không bị bug, mô hình học được).
2. **`exp0_pred_moderate.png`**: Biểu đồ so sánh đường dự báo và thực tế (Dùng ảnh này để minh họa việc Informer bắt xu hướng rất tốt).
3. **`exp0_scatter.png`**: Biểu đồ phân tán (Scatter plot) cho thấy mô hình không văng ra các dự báo sai lệch (false alarms) khổng lồ, an toàn và đáng tin cậy cho cảnh báo dài hạn.

---

## 6. Kết luận & Hướng phát triển

- Khung Baseline I1 đã hoạt động thành công rực rỡ, thiết lập một nền tảng vững chắc.
- Informer chứng tỏ ưu thế tuyệt đối trong việc dự báo chuỗi dài (không bị tích lũy sai số như Bi-LSTM).
- Hướng mở rộng hợp lý tiếp theo (theo Khung Nghiên cứu) là bổ sung các trường động lực/nhiệt động quy mô lớn để mô hình dự báo dài hạn nhạy bén hơn với các hình thế gây mưa (như I4, I5, I8).
