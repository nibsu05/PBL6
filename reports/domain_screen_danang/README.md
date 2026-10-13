# Phép thử hiểu biết khí tượng địa phương — Đà Nẵng

Chốt thiết kế ngày 13/10/2026 trước lượt huấn luyện đầy đủ. Smoke đã hoàn tất trên GPU và LightGBM; không dùng điểm smoke để chọn cấu hình.

## Câu hỏi và cấu hình

| Cấu hình | Đầu vào quá khứ | Phép so |
| --- | --- | --- |
| BASE | A0+A1, thời gian, 8 biến tĩnh | Nền có quan trắc trễ4h |
| RAW | BASE+TCWV,u/v/q850 | RAW−BASE đo giá trị thêm nguyên liệu |
| DOMAIN | RAW+4 chỉ báo gió–ẩm–địa hình | DOMAIN−RAW đo giá trị biểu diễn địa phương |

Bốn chỉ báo: q850 × max(−(u850+v850)/√2,0); chỉ báo đó nhân dốc nâng từ ô đông bắc; tỷ lệ giờ có thành phần gió đưa vào đất liền trong24h; cờ tầng850hPa ở trên mặt đất. q chuyển g/kg sang kg/kg; dốc là chênh cao hai tâm ô chia khoảng cách xấp xỉ theo vĩ độ. Đây là proxy, không phải IVT tích phân cột hoặc nhận diện bão/không khí lạnh.

RAW thêm4 cột zero để RAW/DOMAIN cùng kích thước và số tham số NN. Hai cấu hình cùng nguồn raw/static, mẫu, seed/khởi tạo và ngân sách. BASE ít biến và tham số hơn nên RAW−BASE chưa cô lập hoàn toàn dung lượng mạng. Tương lai chỉ gồm lịch, không dùng ERA5 giờ đích.

## Dữ liệu và ngân sách cố định

- 30 ô chọn trước theo độ cao/khoảng cách biển; cả93 ô có địa hình đủ. W24h,H6h, issue_stride6h; chung cửa sổ hợp lệ theoRAW, các nhãn không chồng nhau.
- Eval2021: train2015–2019/cal2020; eval2022: train2015–2020/cal2021; eval2023: train2015–2021/cal2022.
- Mỗi fold cố định30.000 mẫu train chung cho mọi cấu hình/learner. NN chỉ xáo trộn thứ tự, không lấy thêm mẫu qua epoch.
- Bi-LSTM hidden64,2 tầng, Adam1e−3,batch256,tối đa15epoch,patience4; seed42/43/44; Huberlog1p+BCE không trọng số lớp; ensemble trung bình3seed và ghi riêng từng seed.
- LightGBM4.5.0 flatten đúng tensor NN,6 đầu L1log1p và9 binary;100cây,15lá,min_child50,learning_rate0,05,max_bin63,4luồng; deterministic, không bagging/feature sampling nên1seed. Giữa learner còn khác loss, không coi là cô lập kiến trúc tuyệt đối.
- Chuẩn hóa trên train; chỉ báo domain fit từ cửa sổ train. Nhãn giữmm. Climatology học toàn bộ cửa sổ train hợp lệ theo ô×tháng×giờ,Beta(1,1), có nhiều mẫu hơn NN/cây; không dùng cal/eval.
- Platt và ngưỡng quyết định fit nămcal. Lưới0,01–0,95 bước0,01 tối đaCSI; đầu3h chọn tháng5–10, đầu6h chọn tháng11–2. Cal còn chọnepoch, nên điểmcal không độc lập.

## Chỉ số và tiêu chí chuyển tiếp

Chính: CSI quyết định xác suất≥10mm/3h và BSS≥1mm/3h tháng5–10. Kèm CSI lượngmưa,BSS≥10,POD/FAR,bias,RMSE; mùa11–2 chỉ chấm6h. CSI không phải tỷ lệ dự báo đúng; FAR là tỷ lệ số lần báo có nhưng không xảy ra.

DOMAIN−RAW là phép so chính, RAW−BASE là phụ. CI95% bootstrap khối5ngày, mọi ô cùng ngày đi cùng nhau,1.000lần, riêng từng năm. Phân tích phụ hướng gió6h quá khứ: NE khi u/v đều<−0,5m/s,W khi u>0,5,còn lại. Đây là proxy hướng gió, không phải chế độ bão/đối lưu đã xác minh.

Tiêu chí đặt trước: ΔCSI≥0,03 hoặc BS giảm tương đối≥5% soRAW, tín hiệu ít nhất2/3năm, xétCI và không suy giảm lớn chỉ số khác. Đây là ngưỡng kỹ thuật của đồ án, không phải mức bài báo bảo đảm. Nếu chỉ tốt1năm/CI rộng, giữ là khám phá và ưu tiên đơn giản.

2021–2023 là validation lịch sử, một số đã được khám phá; test2025 giữ kín. Khí tượng quá khứ ERA5 là hồi cứu; GSMaP lưu trữ dịch4h chưa tái hiệnNRT. Chưa suy thành thắngECMWF hoặc app.

## Đầu ra trước huấn luyện

- label_audit.json/label_station_scores.csv:1.042ngày chung GSOD2021–2023;1.092tổng ngày cube/pointGC khớp0,1mm.67,6% lượngGC mùa11–2 và20,8% mùa5–10 nằm ở giờraw≤0,01mm. Đây là phụ thuộc hiệu chỉnh, không chứng minh giờ mưa thật sai; GSOD có thể không độc lập vớiGC.
- live_contract_probe.json:snapshot96giờ.IFS9km cóCAPE/CIN/TCWV/đất,bốn trường850rỗng;IFS025 có850/TCWV,CINrỗng.q cần suy từT/RH850 và kiểm traparity.past_days chưa bảo đảm biết trước đúng giờ phát hành. [Tài liệu ECMWF API](https://open-meteo.com/en/docs/ecmwf-api).

## Tái lập

    .venv\Scripts\python.exe scripts\audit_danang_labels.py
    .venv\Scripts\python.exe scripts\probe_live_domain_contract.py
    .venv\Scripts\python.exe scripts\screen_danang_domain.py

Job bị ngắt: chạy lại nguyên tham số thêm --resume. Checkpoint/dự báo/raw snapshot ở data/operational/ ngoài Git. Báo cáo công khai chỉ gồm tổng hợp; môi trường và SHA train index ở run.json.

## Kết quả đã hoàn tất

27 lượt NN và 9 pipeline LightGBM trên 3 fold, 131.400 cửa sổ evaluation; 73 kiểm tra đạt. DOMAIN tăng CSI quyết định của Bi-LSTM so RAW 0,051 / 0,007 / 0,031, nhưng cả ba CI95% chứa 0. LightGBM chưa xác nhận lợi ích rõ. Giữ RAW/DOMAIN làm ứng viên, chưa chọn checkpoint vận hành. RAW/DOMAIN đều có 174.154 tham số NN.

Bảng đầy đủ: scores.csv; quyết định: domain_decisions.csv; manifest: run.json; tổng hợp: summary.json. Biểu đồ và diễn giải ở [brief giảng viên14/10](../research_rainfall/brief_giang_vien_2026_10_14.md); kế hoạch thực hiện ở [execution_plan.md](../research_rainfall/execution_plan.md).

CSI bootstrap đã đổi tên thành CSI_probability>=10mm/3h cho đúng ý nghĩa: phép tính dùng nhãn nhị phân của sự kiện10mm/3h rồi chấm ngưỡng1. Việc đổi nhãn không thay số liệu hay phép tính.

Suy luận CPU/checkpoint đã kiểm tra20mẫu/cấu hình ở2021 và2023; inference_parity.json lưu sai số. API health/meta/predict đã qua HTTP thật, api_smoke.json chỉ giữ tổng hợp kiểm tra. Server thử đã đóng. Checkpoint, dữ liệu và JSON dự báo chi tiết nằm ngoài Git.
