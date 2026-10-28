# Pilot 24–72 giờ phục vụ báo cáo ngày mai

Người dùng duyệt kế hoạch ngày21/10/2026 và yêu cầu có kết quả trong khoảng3–4giờ. Đây là mốc báo cáo sơ bộ, chưa phải nghiên cứu cuối. Nhánh triển khai `research/tft-regional`; dữ liệu/checkpoint/dự báo từng dòng ngoài Git.

| Khoảng thời gian từ lúc bắt đầu | Đầu ra ưu tiên |
| --- | --- |
| 0–45 phút | Loader168h→ba tổng24h, kiểm tra chống rò rỉ/đơn vị/mask; manifest pilot |
| 45–90 phút | Khí hậu/luôn0 và LightGBM E0/E7, cùng ba fold2021–2023 |
| 90–180 phút | TFT vùng gọn E0/E7, seed42; profile và huấn luyện khi kiểm tra kỹ thuật đạt |
| 180–240 phút | Ghép cùng mẫu, CI thăm dò, hình/bảng, Word và lời trình bày |

Khóa trước kết quả: V1footprint93ô xấp xỉ, lịch sử7ngày gộp6h, issue00UTC, label ba tổng24h ngày1/2/3, không dùng ERA5 tương lai, không mở2025. E0 có11biến, E7có44; cùng mask, split và calibration. Train/cal/eval theo ba fold đã đề xuất. TFT hidden32, seed42, tối đa40epoch, patience6, chọn epoch theo calibrationBrier16. Không dùng evaluation chọn cấu hình. Runtime nếu không đủ thì công bố rõ run chưa hoàn tất, không chọn riêng năm tốt.

Ma trận rút gọn:6pipelineLightGBM (tối đa72đầu cây),6lượtTFT nếu kịp ngân sách; mỗi lượt TFT có cả ba lead. Chỉ một seed nên chưa kết luận độ ổn định theo seed. Cặp E7−E0 là thăm dò tổng hợp thêm biến, chưa quy lợi ích cho riêng A/M/C. CI95%bootstrapkhối7ngày,2.000lần chỉ phục vụ pilot, không dùng như bảng kiểm định xác nhận family9phépso của kế hoạch đầy đủ.

Báo cáo tối thiểu phải có: định nghĩa bài toán, nguồn và hạn chế vùng/nhãn, số mẫu theo fold, baseline và mô hình trên cùng mẫu, kết quả âm nếu có, hình skill theo lead, reliability, ví dụ dự báo theo quy tắc chọn trước, trạng thái TFT và danh sách việc còn lại. Không dùng điểm nhánh6h hoặc Informer cũ để xếp hạng mô hình ngày. Ngưỡng16/50/100mm là trung bình vùng/24h, không phải cảnh báo tại điểm.

Nếu thời gian hạn chế, ưu tiên dữ liệu/baseline/đánh giá đúng hơn số mô hình. Không huấn luyện final2025, không hoàn thiện app, không mở nhánh forecast thật/Informer trong mốc4giờ này. Ranh93ô được giữ cố định cho pilot; nghiên cứu cuối cần chốt giao ranh như kế hoạch đầy đủ.
