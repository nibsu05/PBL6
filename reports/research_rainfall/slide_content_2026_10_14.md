# Nội dung 6 slide để trao đổi với giảng viên lúc 08:00, 14/10/2026

> **Bản dàn ý chốt khoảng 00:00 ngày 14/10.** Sau đó đã dựng [bộ PowerPoint 8 slide](../presentation_2026_10_14/PBL6_Da_Nang_2026_10_14.pptx), bổ sung slide nhu cầu từ [rà soát tài liệu](user_needs_desk_review_2026_10_14.md). Bản này giữ lời dẫn và số liệu gốc để nhóm tập nói 6–7 phút. Watcher NRT chỉ thêm nhật ký nguồn, không tự biến thành kết quả chất lượng mô hình.

## Thông điệp mở đầu (20 giây)

“Nhóm tập trung dự báo xác suất mưa 0–6 giờ cho Đà Nẵng. Phần khác biệt là hiểu nguồn dữ liệu và khí tượng địa phương, so mô hình trên cùng mẫu, rồi kiểm tra đầu vào có thật sự đến kịp khi app phát hành hay không. Đã có kết quả thực nghiệm và demo hồi cứu; AI live đang chờ kiểm định vận hành.”

## Slide 1 — Câu hỏi và sản phẩm

**Đặt lên slide**
- Đà Nẵng mới: 93 ô lưới 0,1°. Sản phẩm đang làm sâu: dự báo mưa 0–6 giờ, hiển thị tổng 3 giờ và xác suất mưa mạnh theo ô.
- Câu hỏi: nhóm dữ liệu/biểu diễn khí tượng địa phương nào có ích, và cấu hình nào đủ tin cậy để đưa vào app?
- Sản phẩm 1–3 ngày (TFT) là giai đoạn sau; sáng mai tập trung 0–6 giờ.

**Nói:** “Mục tiêu không phải có nhiều tên mô hình. Nhóm muốn biết thay đổi nào thực sự giúp dự báo mưa Đà Nẵng và có chạy được với dữ liệu đến đúng giờ.”

**Hình:** bản đồ 93 ô từ demo `http://127.0.0.1:8766/` hoặc sơ đồ nguồn → mô hình → bản đồ/xác suất. Ghi rõ ảnh demo là **kiểm chứng lịch sử**, chưa là AI live.

## Slide 2 — Chọn nhãn và thiết kế phép so

**Đặt lên slide**
- Không dùng mưa ERA5 làm nhãn: tại trạm Đà Nẵng, nó bắt được 8% số ngày ≥100 mm trong phép audit cũ.
- Chọn GSMaP v8 hiệu chỉnh trạm làm nhãn. Ở 10 trạm GSOD, CSI ngày ≥50 mm: GSMaP GC **0,33**, IMERG **0,22**, ERA5 **0,17**. GSMaP GC có thể chịu ảnh hưởng từ trạm tham gia hiệu chỉnh, nên chưa coi đây là kiểm chứng hoàn toàn độc lập.
- Thử mô hình trên **cùng 30 ô** được chọn trước theo địa hình/khoảng cách biển, 3 fold năm 2021–2023, 3 seed, cùng cửa sổ; ngưỡng/hiệu chỉnh chọn ở năm calibration. Năm test 2025 giữ kín.

**Nói:** “Nếu nhãn bỏ sót mưa to, mô hình có thể đạt điểm đẹp nhưng học sai. Nhóm sửa nhãn và khóa cách chia dữ liệu trước khi so mô hình.”

**Hình:** một timeline train → calibration → validation; không cần đưa toàn bộ 51 đặc trưng lên slide. Nguồn: [benchmark trạm](../station_benchmark/README.md), [thiết kế domain](../domain_screen_danang/README.md).

## Slide 3 — Kết quả mạnh nhất: đổi cách học lượng mưa

**Đặt lên slide** (RMSE tổng mưa 0–3 giờ, tháng 5–10; nhỏ hơn là tốt hơn)

| Năm validation | LightGBM RAW: L1(log) → Tweedie | Bi-LSTM RAW: log-Huber → Tweedie |
| --- | ---: | ---: |
| 2021 | 4,607 → **3,947** mm | 4,046 → **3,876** mm |
| 2022 | 4,841 → **4,534** mm | 4,661 → **4,581** mm |
| 2023 | 4,205 → **3,610** mm | 3,963 → **3,540** mm |

- Với LightGBM, CI95% của mức giảm RMSE không chứa 0 cả ba năm. Với Bi-LSTM, CI chứa 0 ở 2022; đầu xác suất BSS ≥1 cũng giảm 0,186→0,148 năm đó.

**Nói:** “Lợi ích rõ nhất hiện nay là sửa đầu học lượng mưa đang dự báo quá thấp, chứ chưa phải thêm kiến trúc phức tạp. Nhưng lượng mm tốt hơn không đồng nghĩa xác suất tốt hơn ở mọi năm.”

**Hình:** 3 cặp cột RMSE trước/sau, ưu tiên LightGBM; Bi-LSTM là kiểm tra bổ sung. Nguồn: [LightGBM Tweedie](../followup_danang/amount/paired_bootstrap.json), [Bi-LSTM Tweedie](../followup_danang/bilstm_tweedie/paired_bootstrap.json).

## Slide 4 — Hiểu Đà Nẵng: giả thuyết vật lý có tín hiệu, chưa chứng minh thắng

**Đặt lên slide**
- Nhóm gió Đông Bắc trong audit chỉ chiếm khoảng **12–18% mẫu** nhưng chứa **46–65% sự kiện mưa ≥10 mm/3 giờ**; đây là mô tả để chọn giả thuyết, không chứng minh nguyên nhân.
- Thêm biểu diễn gió–ẩm–địa hình vào Bi-LSTM RAW làm CSI xác suất mưa ≥10 mm/3 giờ tăng **+0,051 / +0,007 / +0,031** ở 2021/2022/2023. **CI95% từng năm đều chứa 0**; LightGBM chưa xác nhận lợi ích lặp.
- Kết luận hiện tại: hiểu domain giúp đặt thí nghiệm đúng và phát hiện giới hạn nhãn theo mùa; chưa tuyên bố “đặc trưng địa hình chắc chắn làm mô hình tốt hơn”.

**Nói:** “Đây là chỗ nhóm muốn xin góp ý: tín hiệu khí tượng địa phương có thật trong dữ liệu, nhưng còn phải tách tác động từng biến và kiểm tra qua thời gian/nguồn thật.”

**Hình:** [gió và tần suất sự kiện](../domain_screen_danang/regime_event_rates.png) **hoặc** [hiệu số CSI kèm CI](../domain_screen_danang/domain_effect_ci.png); không cần cả hai nếu slide chật.

## Slide 5 — Từ nghiên cứu đến app: dữ liệu phải đến kịp

**Đặt lên slide**
- Demo đã hiển thị kết quả từ checkpoint thật trên **93 ô**, ở chế độ lịch sử 2021–2023; đã kiểm tra 36 trường hợp suy luận HTTP khớp dự báo lưu. **AI live chưa phát hành.**
- Đã tải và giải mã 24 giờ GSMaP NRT v8, 93/93 ô hữu hạn. Một tệp mới được watcher thấy trong khoảng 10 phút theo dõi đầu tiên; cửa sổ nguồn lag4 ở **giờ phát hành thử 17 UTC** có 24/24 tệp máy đã nhận trước mốc đó. Một lần quan sát chưa đủ kết luận độ trễ điển hình của JAXA.
- Train lại Bi-LSTM với vệ tinh trễ **5 giờ thay vì 4 giờ** trên cùng 30 ô/3 seed làm RMSE 3 giờ tăng khoảng **0,038–0,053 mm** (xấp xỉ 1%) ở cả ba fold, CI hiệu số dương. Đủ dữ liệu và chất lượng mô hình là hai điều kiện riêng.

**Nói:** “App có cổng nguồn: thiếu hoặc đến muộn thì không tự tạo dự báo AI. Nhóm đang đo giờ tệp mới thật sự xuất hiện, rồi mới chọn lag 4, lag 5 hoặc phương án dự phòng.”

**Hình:** ảnh demo archive + một ô trạng thái “nguồn đủ/chưa đủ”; không dùng ảnh tab live để nói là mô hình đang dự báo hôm nay. Nguồn: [audit NRT](../followup_danang/jaxa_live_first_detection.json), [retrain lag5](../followup_danang/bilstm_tweedie_lag5/README.md).

## Slide 6 — Việc tiếp theo và ý kiến cần xin

**Đặt lên slide**
1. Ghi NRT **liên tục nhiều ngày** trên máy luôn bật để đo độ trễ thật; kiểm tra khác biệt giữa dữ liệu train hồi cứu và NRT.
2. Tái tạo đầu vào AI chỉ từ thông tin có trước giờ phát hành; sau đó mới so AI với dự báo ECMWF trên **cùng ô, giờ, hạn, nhãn**. Nếu nguồn không đạt, app dùng forecast nguồn và báo trạng thái rõ.
3. Khi sản phẩm 0–6 giờ có kiểm chứng, mới mở rộng TFT 1–3 ngày và vùng khí hậu khác.

**Xin ý kiến giảng viên:** ưu tiên nghiên cứu sâu một vùng/hạn 6 giờ trước có phù hợp không; nên đặt trọng số vào RMSE lượng mưa hay khả năng bắt mưa mạnh/xác suất; có thể bổ sung nhãn trạm theo giờ độc lập không?

**Nói:** “Nhóm có kết quả thí nghiệm và demo hôm nay, đồng thời biết chính xác cổng còn thiếu trước khi phát hành AI live. Mỗi tuần sẽ chốt một bảng kết quả và một quyết định.”

## Slide dự phòng nếu hỏi “vì sao phải so ECMWF?”

ECMWF không phải ERA5 nhãn cũ. ERA5 là tái phân tích thời tiết đã qua; ECMWF IFS là dự báo đã phát hành trước giờ đích. Nhóm vẫn so Bi-LSTM/LightGBM/đặc trưng trên **cùng dữ liệu** để trả lời câu hỏi nghiên cứu; ECMWF là mức đối chứng thêm để biết AI có giá trị cho app hay không. Pilot đã tải **56 run**, 30 ô × 14 ngày tháng 10/2024, 1.680 cặp forecast/nhãn; ECMWF qua Open-Meteo RMSE 3 giờ **3,950 mm**, CSI ≥10 **0,089**. Chỉ 4/14 ngày có mưa mạnh, CI hiệu RMSE so cách luôn 0 chứa 0. **Chưa chấm AI cạnh ECMWF trên cùng đầu vào vận hành** và chưa tuyên bố AI thắng. Nguồn: [pilot ECMWF](ecmwf_pilot_14d/README.md).

## Ba câu không nên nói

- “AI đã vượt ECMWF.” Chưa có phép so cùng mẫu/đầu vào vận hành.
- “Địa hình chắc chắn giúp.” CI lợi ích DOMAIN hiện chứa 0.
- “App đang dự báo AI live.” Demo hiện là archive và hiển thị nguồn; cổng vận hành chưa đạt.

## Kế hoạch để kịp 08:00

- **Đêm 13→14/10:** chỉ dựng 6 slide từ bảng/hình trên và chụp một ảnh demo archive. Không thêm thí nghiệm mới vào slide. Watcher cứ chạy; không cần thức canh.
- **Khoảng 07:15 ngày 14/10:** kiểm tra máy/demo mở được và watcher có lỗi không. Chỉ cập nhật một dòng tiến độ nguồn nếu có bằng chứng mới; giữ nguyên các bảng điểm mô hình đã chốt.
- **Trước 08:00:** tập nói 6–7 phút theo các câu “Nói” ở trên. Nếu thiếu thời gian thiết kế, ưu tiên slide 1, 2, 3, 5 và 6; slide 4 có thể nói miệng trong 30 giây.
