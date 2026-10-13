# Thiết kế so sánh mô hình và app dự báo mưa Đà Nẵng

Ngày 13/10/2026. Đề tài cần hai loại bằng chứng: mô hình nào tốt hơn khi nhận cùng thông tin, và mô hình được chọn có dùng được trong một app phát hành dự báo thật hay không. Trọng tâm hiện tại là đóng góp nhóm thông tin và biểu diễn theo khí tượng địa phương; so kiến trúc là đối chứng, dự báo ECMWF kiểm tra giá trị sử dụng của app.

## Ba phép so sánh cần tách biệt

| Phép so | Giữ cố định | Thay đổi | Câu hỏi trả lời |
| --- | --- | --- | --- |
| Kiến trúc | Ô, giờ phát hành, nhãn, đặc trưng, hạn, split, chỉ số và ngân sách tuning | Bi-LSTM, TFT, baseline tabular/tuyến tính | Cách học nào phù hợp hơn với cùng dữ liệu? |
| Nhóm thông tin | Kiến trúc, seed, mục tiêu và quy trình huấn luyện | A0–A5/B0–B5, độ trễ quan trắc | Thông tin nào giúp ở hạn và mùa nào? |
| Vận hành | Giờ phát hành/giờ đích, ô, nhãn và chỉ số | AI, ECMWF thô, ECMWF được hiệu chỉnh | App có cải thiện so với nguồn dự báo sẵn có? |

Không lấy Bi-LSTM dự báo 6 h và TFT dự báo 72 h để tính một tỷ lệ thắng/thua kiến trúc. Bảng 2×2 cần cả hai mô hình ở cả hai hạn. Khi thêm A4, đầu vào đã thay đổi: kết quả ablation không tự chứng minh kiến trúc tốt hơn.

ECMWF là một hệ thống dự báo số khí quyển; nó không được huấn luyện lại bằng dataset của nhóm trong phép đối chứng. Để so giá trị vận hành, hai bên vẫn phải dự báo cùng nơi, cùng thời điểm, cùng hạn và được chấm bằng cùng nhãn. Nếu đề tài chỉ khảo sát thuật toán, phép so kiến trúc đã trả lời câu hỏi đó; sản phẩm app cần thêm kiểm định với nguồn dự báo thật.

## Cơ sở chọn mô hình

TFT có cơ chế riêng cho lịch sử, đặc trưng tĩnh và đầu vào tương lai đã biết, nên phù hợp cấu trúc dataloader. Bài gốc không chứng minh TFT luôn thắng Bi-LSTM trên mưa Đà Nẵng; đó là giả thuyết của thí nghiệm. [Lim và cộng sự](https://arxiv.org/abs/1912.09363).

Kết quả DLinear cho thấy mô hình tuyến tính đơn giản có thể thắng các Transformer trên benchmark chuỗi thời gian. Kết quả ấy không trực tiếp áp dụng cho CSI mưa to hoặc TFT có đầu vào NWP; nó là lý do cần đối chứng đơn giản, không phải lý do kết luận trước về kiến trúc. [Zeng và cộng sự](https://arxiv.org/abs/2205.13504).

MetNet-2 và NowcastNet khai thác thông tin không gian và dữ liệu radar; không chuyển các điểm số đó sang bài toán chuỗi ô 0,1° với vệ tinh trễ 4 h. Chúng hỗ trợ việc xem độ trễ và bối cảnh không gian là các yếu tố nghiên cứu. [MetNet-2](https://www.nature.com/articles/s41467-022-32483-x), [NowcastNet](https://www.nature.com/articles/s41586-023-06184-4).

Global MetNet là một hướng mới dùng vệ tinh, NWP và CORRA cho nơi ít radar. Bản preprint 2025 đưa ra kết quả triển khai toàn cầu; không phải cấu hình có thể tái tạo ngay với dữ liệu và GPU hiện có của nhóm. Cần giữ đúng khác biệt nguồn nhãn và đầu vào khi tham khảo. [Agrawal và cộng sự](https://arxiv.org/abs/2510.13050).

## Nhãn và đầu vào khi chạy thật

GSMaP Gauge phụ thuộc phân tích mưa ngày CPC. GSMaP Gauge NRT dùng tham số sai số đã suy ra từ Gauge, không sử dụng trực tiếp các trạm hiện tại theo cùng cách. Vì vậy chỉ dịch trễ chuỗi bản standard không tạo ra bản NRT tương đương; đây là một khoảng cách dữ liệu cần đo. [JAXA release note](https://www.eorc.jaxa.jp/GPM/doc/product/ReleaseNote/08_note_GPM-GSMaP_20231110.pdf).

JAXA liệt kê NRT trễ khoảng 4 h, NOW có độ trễ khác và phạm vi/phiên bản riêng. App phải lưu thời điểm thực sự nhận dữ liệu, không chỉ giả định mọi mẫu đều trễ đúng 4 h. [JAXA FAQ](https://sharaku.eorc.jaxa.jp/GSMaP/faq/GSMaP_faq06.html).

Nghiên cứu ở Việt Nam cho thấy chu kỳ mưa trong ngày và sai số GSMaP thay đổi theo mùa và địa hình. Kết quả trên v6/v7 không thay cho kiểm chứng v8 của nhóm, nhưng hỗ trợ tách mùa và kiểm tra nhãn ở miền Trung. [Pham-Thi và cộng sự](https://vjs.ac.vn/jse/article/view/16594).

Trong T-ERA5, mô hình có thể nhận ERA5 ở giờ đích theo perfect prog. Đây là phép thử thông tin/hậu xử lý, chưa phải dự báo vận hành. T-OPS thay các giá trị ấy bằng dự báo đã phát hành trước giờ đích. Kho dự báo lịch sử giúp thu hẹp khác biệt nguồn; phải kiểm tra mô hình, biến, đơn vị, thời gian và chu kỳ trước khi ghép tensor. [Open-Meteo Historical Forecast](https://open-meteo.com/en/docs/historical-forecast-api).

## Thiết kế thực nghiệm đề xuất

1. Đóng băng protocol: train 2015–2021; validation 2022–2023; test 2025 giữ kín. Trong pilot hiện tại, 2022 chọn epoch/hiệu chỉnh, 2023 so cặp.
2. Chạy bảng 2×2 Bi-LSTM/TFT × 6/72 h trên 30 ô, 3 seed. Cùng feature contract trong từng hạn, cùng tập cửa sổ hợp lệ; ghi số tham số và thời gian. Nếu dùng loss khác nhau, chỉ gọi là so hệ thống; thêm một lượt cùng loss để tách ảnh hưởng kiến trúc.
3. Baseline: khí hậu theo ô/tháng/giờ, persistence đúng trễ, dự báo số thô và được hiệu chỉnh xác suất, tabular, DLinear ở hạn ngày. Tham số và ngưỡng quyết định chỉ fit/chọn trên train/validation.
4. Chỉ số chính: CSI tổng 3 h ≥10 mm và BSS ≥1 mm cho A; CSI tổng ngày ≥50 mm và BSS ≥16 mm cho B. Kèm reliability, bias, RMSE, số sự kiện và bootstrap khối ngày. Mùa đông của A chỉ chấm tổng 6/24 h theo giới hạn nhãn.
5. Chỉ mở test sau khi đóng băng mô hình, quy trình dữ liệu và hiệu chỉnh. Sau đó báo T-ERA5/T-OPS và kiểm tra nhãn IMERG/trạm ở giai đoạn có dữ liệu phù hợp.

Pilot đã có tín hiệu S4 tốt hơn về xác suất nhưng CSI mưa to yếu; cần kiểm tra thêm seed và baseline hiệu chỉnh trước khi mở rộng. [Báo cáo pilot](../pilot_bilstm_v2/README.md).

## Đường đi tới một app

App Đà Nẵng gồm bản đồ 93 ô; chọn điểm; dự báo 6 h và ngày 1–3; lượng mưa kèm xác suất; thời điểm cập nhật và trạng thái dữ liệu. Mỗi giá trị là trung bình ô khoảng 11 km, không phải số đo tại một điểm.

Pipeline gồm thu nhận ECMWF/vệ tinh → dựng đặc trưng dùng chung với train → kiểm tra hữu hạn/độ trễ → suy luận → lưu snapshot/version/hash → API → giao diện. Mô hình phụ thuộc biến chưa có nguồn live được giữ ở chế độ nghiên cứu; không điền các biến ấy bằng 0 để chạy demo.

Trước khi tích hợp checkpoint, cần bảng hợp đồng từng biến và parity test: cùng một đầu vào lưu trữ phải cho cùng tensor ở train và app. Nếu vệ tinh không có hoặc quá trễ, dùng cấu hình đã kiểm định không có quan trắc. Nếu bản tin cũ, giao diện hiện tuổi dữ liệu. Forecast ECMWF có thể là lớp hiển thị dự phòng trong lúc AI chưa đủ bằng chứng.

Đầu ra gần nhất là protocol 2×2, một bảng so trên validation và hợp đồng dữ liệu live. TFT hoàn chỉnh, kiểm định T-OPS và app hai sản phẩm vẫn là các giai đoạn phải triển khai và kiểm tra, chưa được pilot hiện tại hoàn tất.

Rà soát chuyên sâu và điều chỉnh ưu tiên: [literature_domain_review.md](literature_domain_review.md).
