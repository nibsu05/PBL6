# Kế hoạch dự án PBL6: Dự báo mưa cho Đà Nẵng mới

> **Dành cho các thành viên trong nhóm.** File này trả lời bốn câu hỏi: dự án làm gì, quy trình ra sao, đang ở giai đoạn nào, và mỗi người cần làm gì tiếp theo.
> Chi tiết kỹ thuật và số liệu đầy đủ nằm ở [`project_plan_v2.md`](project_plan_v2.md). Bối cảnh dành cho AI agent nằm ở [`CLAUDE.md`](CLAUDE.md).
> **Cập nhật:** 13/10/2026. Khi chuyển sang giai đoạn mới hoặc chốt một quyết định, hãy sửa mục 4, mục 6 và ngày cập nhật.

---

## 1. Đọc nhanh trong 1 phút

- **Mục tiêu:** dự báo mưa cho **Đà Nẵng mới** (Đà Nẵng cũ cộng Quảng Nam) theo hai sản phẩm. Kết quả cuối là **một app**.
  - **Sản phẩm A**, 0–6 giờ tới, dùng **Bi-LSTM**.
  - **Sản phẩm B**, 1–3 ngày tới, dùng **TFT** (Temporal Fusion Transformer).
- **Câu hỏi nghiên cứu:** nhóm thông tin nào (quan trắc vệ tinh, độ bất ổn định, dòng ẩm, dự báo số…) giúp mô hình AI **vượt dự báo số ECMWF** ở hạn nào và mùa nào?
- **Đang ở đâu:** dữ liệu, bộ đánh giá, pilot và bốn phép thử follow-up tại Đà Nẵng đã hoàn tất; demo archive từ checkpoint thật hoạt động. Chưa có dự báo AI live hay kết luận vượt ECMWF.
- **Việc cần làm ngay:** đã tải và giải mã một giờ GSMaP raw/Gauge_NRT v8; tiếp tục ghi nguồn liên tục, kiểm tra lệch giữa NRT và dữ liệu train, rồi so ECMWF trên forecast thật. Xem mục 4 và 6.

---

## 2. Dự án làm gì

### 2.1. Hai sản phẩm

| | Sản phẩm A: cực ngắn | Sản phẩm B: hạn ngắn |
| --- | --- | --- |
| Mô hình | Bi-LSTM | TFT |
| Hạn dự báo | 1–6 giờ tới, từng giờ | 1–3 ngày tới (72 giờ) |
| Phát hành | Mỗi giờ | 4 lần/ngày (00, 06, 12, 18 giờ UTC) |
| Hiển thị trên app | Tổng mưa 3 giờ tới; xác suất có mưa hoặc mưa to | Tổng mưa ngày 1, 2, 3; xác suất mưa vừa (≥16 mm), mưa to (≥50 mm), mưa rất to (≥100 mm) |
| Vai trò của AI | Kết hợp quan trắc vệ tinh gần nhất với dự báo số | Sửa sai số và đưa ra xác suất cho dự báo số ECMWF |

Về tên gọi: theo Thông tư 08/2022, hạn 1–3 ngày là **hạn ngắn**, không phải "dài hạn". Báo cáo nên dùng đúng thuật ngữ này.

### 2.2. Phạm vi không gian

- Dự báo theo **ô lưới khoảng 11 km × 11 km** (0,1°). Đà Nẵng mới gồm **93 ô đất**. Lưới cũng phủ một phần Huế (32 ô) và Quảng Ngãi (85 ô).
- **Một mô hình chung** cho mọi ô. Mô hình phân biệt các ô nhờ đặc trưng tĩnh: độ cao, khoảng cách tới biển, sườn đón gió. Nhóm **không** huấn luyện riêng cho từng tỉnh.
- App hiển thị ở hai cấp:
  - **Cấp tỉnh:** trung bình, nơi mưa nhiều nhất, % diện tích có mưa to.
  - **Cấp một điểm** (xã/phường hoặc vị trí người dùng): lấy giá trị của ô chứa điểm đó.
- Sau khi xong phần Đà Nẵng, thêm **2 vùng khí hậu khác** (Hà Nội, và TP.HCM hoặc Đắk Lắk) để kiểm tra mô hình có dùng được ở nơi khác không.

### 2.3. Điều mà kết quả phải chứng minh

Đồ án làm **hai phép so bổ sung cho nhau**: (1) Bi-LSTM/LightGBM/TFT và các nhóm đặc trưng trên cùng dữ liệu để hiểu yếu tố nào giúp; (2) cấu hình được chọn so với **dự báo ECMWF thô/hiệu chỉnh** trên cùng ô, cùng giờ, cùng nhãn để đo giá trị thêm cho app. ERA5 là tái phân tích của thời tiết đã qua, dùng trong thí nghiệm hồi cứu; ECMWF IFS Single Runs là các **bản dự báo đã phát hành trong quá khứ**, vẫn dự báo tương lai so với thời điểm phát hành đó. Thư viện [Single Runs](https://open-meteo.com/en/docs/single-runs-api) giữ từng lần chạy riêng từ 03/2024. Mốc `run` là giờ khởi tạo, chưa phải giờ bản dự báo đã sẵn có; kiểm định T-OPS phải bảo đảm `available_at ≤ issue_at` (hoặc dùng độ trễ bảo thủ và kiểm tra độ nhạy), rồi mới so cùng mẫu. Phép so này chưa hoàn tất; không diễn giải điểm validation 2021–2023 là đã thắng ECMWF. Đồ án trả lời 4 câu hỏi:
1. Nhóm thông tin nào quyết định ở hạn nào, mùa nào?
2. AI có thêm giá trị so với ECMWF không?
3. Lợi ích đó còn giữ được khi chạy với dữ liệu thật không (đánh giá T-OPS)?
4. Một mô hình có dùng được cho vùng khác không?

---

## 3. Quy trình tổng thể

```mermaid
flowchart LR
    subgraph SRC["1. Nguồn dữ liệu"]
        G["GSMaP v8 (vệ tinh)\nnhãn + quan trắc"]
        E["ERA5 (tái phân tích)\n33 biến khí quyển"]
        S["DEM + ranh giới tỉnh\nđặc trưng tĩnh"]
        T["10 trạm NOAA\nkiểm chứng độc lập"]
        N["ECMWF lưu trữ\n(đánh giá T-OPS)"]
    end
    subgraph DATA["2. Dữ liệu"]
        D["Dataset v2\n296 ô × giờ × 51 đặc trưng\n2015 → 09/2026"]
        L["Dataloader\ncửa sổ, độ trễ L, chuẩn hóa"]
    end
    subgraph MODEL["3. Mô hình"]
        A["Bi-LSTM 0–6 h"]
        B["TFT 1–3 ngày"]
        BL["Baseline: khí hậu, persistence,\nECMWF thô, LightGBM, DLinear"]
    end
    subgraph EVAL["4. Đánh giá"]
        V["Bộ chỉ số chung\nCSI, BSS, bootstrap, tách mùa"]
    end
    APP["5. App\nbản đồ tỉnh, chi tiết điểm,\nkiểm chứng live"]
    G --> D
    E --> D
    S --> D
    D --> L --> A
    L --> B
    L --> BL
    A --> V
    B --> V
    BL --> V
    T --> V
    N --> V
    V --> APP
```

| Bước | Làm gì | File chính |
| --- | --- | --- |
| 1. Tải dữ liệu | GSMaP, ERA5 và đặc trưng tĩnh từ Google Earth Engine; trạm NOAA; Open-Meteo | `scripts/extract_gee_*.py`, `scripts/fetch_*.py` |
| 2. Dựng dataset | Ghép mọi nguồn về lưới 0,1°, thống nhất quy ước giờ, kiểm tra chất lượng | `scripts/build_dataset_v2.py`, `src/dataset_v2.py` |
| 3. Dataloader | Cắt cửa sổ (24 giờ cho A, 168 giờ cho B), dịch quan trắc theo độ trễ, chuẩn hóa, chia train/val/test theo năm | `src/dataloader_v2.py` |
| 4. Huấn luyện | Bi-LSTM, TFT, các baseline. Một thí nghiệm = một cấu hình nhóm đặc trưng | *(sắp viết)* |
| 5. Đánh giá | Mọi mô hình chấm trên cùng tập mẫu, cùng chỉ số, có khoảng tin cậy | `src/verification.py`, `scripts/station_daily_benchmark.py` |
| 6. App | Chạy định kỳ, hiển thị và tự kiểm chứng | `demo/` *(sẽ nâng cấp)* |

### Cách so sánh các mô hình (thiết kế thí nghiệm)

- **Ablation theo nhóm đặc trưng:** giữ nguyên kiến trúc, chỉ thêm hoặc bớt từng nhóm đặc trưng, để đo đóng góp của từng nhóm.

  | Nhóm (sản phẩm A) | Nội dung |
  | --- | --- |
  | A0 | Biến bề mặt và thời gian |
  | A1 | Mưa vệ tinh gần nhất, có độ trễ |
  | A2 | Đối lưu: CAPE, CIN, TCWV… |
  | A3 | Gió và ẩm trên cao, dòng ẩm |
  | A4 | Dự báo số cho các giờ tới |
  | A5 | Bối cảnh vùng |

  Sản phẩm B có các nhóm tương tự B0–B5, thêm chỉ số không khí lạnh và các chỉ số khí hậu.
- **Thí nghiệm độ trễ quan trắc:** dữ liệu vệ tinh có độ trễ khi chạy thật (khoảng 4 giờ). Thí nghiệm đo kỹ năng thay đổi thế nào khi độ trễ là 0,5 / 4 / 14 giờ hoặc không có quan trắc.
- **Quy tắc bắt buộc:**
  - Mỗi cấu hình chạy 3 seed.
  - Chỉ chọn cấu hình dựa trên tập validation. Tập test (năm 2025) chỉ mở **một lần**.
  - So sánh theo cặp bằng bootstrap, kèm khoảng tin cậy 95 %.
  - Mọi bảng kết quả **tách theo mùa**.

---

## 4. Đang ở giai đoạn nào

| Giai đoạn | Trạng thái 14/10/2026 | Bằng chứng |
| --- | --- | --- |
| Dữ liệu và đánh giá | Xong | Verify 2233/2233, dataloader 0 mẫu lệch; `reports/station_benchmark/` |
| Bi-LSTM/LightGBM Đà Nẵng | Pilot và BASE/RAW/DOMAIN 3 fold xong | `reports/pilot_bilstm_v2_93cells_3seeds/`, `reports/domain_screen_danang/` |
| Follow-up có giả thuyết | Xong: Tweedie cây/NN, bỏ proxy địa hình, 63 ô; thêm stress và retrain lag5 ba fold | `reports/followup_danang/bilstm_tweedie_lag5/`: RMSE lag5 tăng nhỏ cả3 năm với CI dương; chưa là T-OPS |
| Nguồn vận hành | 4 snapshot hiện tại/93 ô không biết run; **pilot ECMWF 56/56 run, 30 ô × 14 ngày đã chấm**; 24h NRT đã kiểm; watcher 12h đang chạy, thấy file raw mới đầu tiên sau10phút, lỗi0 | `reports/research_rainfall/ecmwf_pilot_14d/`, `reports/followup_danang/jaxa_binary_audit.json`; chưa có đầu vào AI as-of hay điểm AI–ECMWF cùng mẫu |
| App Đà Nẵng | Demo archive từ checkpoint, HTTP parity 36 case đạt; watcher thấy file mới16:41 UTC. Lag4/issue17 thử: 24/24 tệp đã nhận trước mốc (lúc audit issue còn tương lai) | `demo/domain_api.py`, `reports/followup_danang/nrt_latency_sensitivity.json`; checkpoint lag4, AI live chưa bật |
| Sản phẩm B TFT, hai vùng ngoài Đà Nẵng | Chưa bắt đầu | Sau MVP và kiểm định nguồn |
| Trao đổi giảng viên 08:00 ngày 14/10 | Đã dựng 8 slide PowerPoint chỉnh sửa được (7 chính, 1 dự phòng), kiểm tra ảnh từng trang; rà soát nhu cầu từ tài liệu, chưa phỏng vấn | `reports/presentation_2026_10_14/PBL6_Da_Nang_2026_10_14.pptx`, `reports/research_rainfall/user_needs_desk_review_2026_10_14.md`; không tuyên bố AI thắng ECMWF hoặc live |

**Lựa chọn hiện tại:** Tweedie cải thiện ước lượng mm rõ trên validation; RAW và DOMAIN chưa phân định chắc ở CSI xác suất. Không chọn model chỉ vì điểm một năm hoặc tên đặc trưng. 87 kiểm tra code đạt chứng minh pipeline chạy đúng trong phạm vi được kiểm, không chứng minh kỹ năng dự báo. Test 2025 vẫn niêm phong. Bảng năm, CI và giới hạn ở `reports/followup_danang/` và brief 14/10.

## 5. Kết quả quan trọng đến nay (để hiểu vì sao làm như vậy)

1. **Nhãn mưa cũ (ERA5) sai mưa to nghiêm trọng.** Tại trạm Đà Nẵng, ERA5 chỉ bắt được 8 % số ngày mưa ≥100 mm. Ví dụ ngày 14/10/2022, trạm đo 396 mm, ERA5 chỉ có 186 mm. Vì vậy nhóm đổi nhãn.
2. **Nhãn mới được chọn bằng đối chiếu với 10 trạm** (2021–2024, 437 ngày mưa ≥50 mm):

   | Nguồn | CSI ≥50 mm (càng cao càng tốt) |
   | --- | ---: |
   | **GSMaP hiệu chỉnh trạm (nhãn được chọn)** | **0,33** |
   | IMERG | 0,22 |
   | ERA5 (nhãn cũ) | 0,17 |

3. **Mức sàn cần vượt:**
   - Dự báo ECMWF trước 1 ngày chỉ báo được khoảng một nửa số ngày mưa to.
   - Mọi dự báo dạng "có / không" đều thua việc chỉ dùng xác suất khí hậu (BSS âm).
   - Vì vậy mô hình của nhóm phải **xuất xác suất**. BSS > 0 chỉ xác nhận tốt hơn khí hậu tham chiếu; để so nguồn phải cùng mẫu, nhãn, hạn và cách xuất xác suất.
4. **Nhãn mưa giờ thay đổi chất lượng theo mùa.** Audit 93 ô Đà Nẵng 2021–2023: 67,6% tổng GC mùa11–2 nằm ở giờ raw≤0,01mm, so với20,8% mùa5–10. Đây là phụ thuộc hiệu chỉnh, chưa chứng minh mọi giờ mưa đều sai. Hệ quả:
   - Sản phẩm A được chấm theo giờ chủ yếu trên tháng 5–10.
   - Mùa đông chấm tổng 6 giờ như chỉ số phụ; 24 giờ dùng QC nhãn với trạm hoặc sản phẩm B.
   - Quan trắc vệ tinh dự kiến ít giúp vào mùa đông.
5. **Vì sao dùng TFT thay Informer:**
   - Trên bộ dữ liệu chuẩn, Informer thua cả cách đoán "lặp lại giá trị gần nhất".
   - Lần chạy cũ của nhóm chỉ đạt R² = 0,04.
   - TFT được thiết kế đúng cho loại đầu vào của bài toán: dự báo số cho tương lai và đặc trưng tĩnh.
   - Informer vẫn chạy một cấu hình để đối chiếu.

---

## 6. Lộ trình thực hiện tiếp

| Mốc | Việc đã có / cần làm | Cổng bằng chứng |
| --- | --- | --- |
| 13/10 — đã xong | BASE/RAW/DOMAIN 3 fold; Tweedie LightGBM và Bi-LSTM; NO_TERRAIN; 63 ô; demo archive | Số liệu, CI, 87 test, 36 HTTP parity; chưa mở 2025 |
| 14/10 08:00 — đã chuẩn bị | Slide nhu cầu, kết quả mô hình, giới hạn và lộ trình đã đóng số cho giảng viên | `reports/presentation_2026_10_14/PBL6_Da_Nang_2026_10_14.pptx`; khảo sát tài liệu `reports/research_rainfall/user_needs_desk_review_2026_10_14.md`; xin ý kiến về phạm vi 0–6 giờ, thước đo và trạm giờ độc lập |
| 14–20/10 | Đã tải/kiểm 24 tệp NRT liên tiếp, 93/93 ô hữu hạn; lag4/issue16 kịp 21/24, lag5/issue17 thử kịp 24/24. Đã stress và train lại Bi-LSTM Tweedie lag5 cùng30ô/3seed/3fold: RMSE tăng nhỏ cả3 năm. Watcher `scripts/watch_gsmap_nrt.py` đã chạy phiên12h từ16:31 UTC; poll2 thấy file mới12 UTC lúc16:41, lỗi0, lag4/issue thử17 có24/24 file kịp máy nhận. Để watcher tiếp tục và đo latency nhiều ngày (backfill không đo latency JAXA), kiểm tra lệch train→NRT và popup | Chỉ chọn lag/giờ phát hành khi có phân phối latency và kỹ năng T-OPS; xét model không cần vệ tinh nếu lag4 không kịp/lag5 yếu; app vẫn archive/ECMWF nguồn |
| 21–27/10 | **Pilot nguồn ECMWF 56 run/30 ô đã xong**: 1.680 cặp đủ forecast/nhãn; CI còn rộng do 4 ngày mưa mạnh. Tiếp theo kiểm tra NRT/khí tượng đầu vào AI as-of, tăng ngày/sự kiện và mở 93 ô chỉ khi parity đạt | Bảng AI–ECMWF cùng mẫu chỉ công bố sau cổng đầu vào; `available_at` lịch sử còn là giả định bảo thủ, 2025 giữ kín |
| Sau cổng vận hành | App AI live 6 h Đà Nẵng nếu đủ nguồn và kỹ năng; TFT 1–3 ngày, hai vùng khác theo sau | Mỗi dự báo lưu thời điểm phát hành, nguồn, version/hash; kiểm chứng sau khi nhãn đến |

Tweedie LightGBM giảm RMSE 3 h tháng 5–10 cả ba năm so đầu L1(log), nhưng không thay đầu xác suất. Tweedie Bi-LSTM cũng giảm RMSE cả ba năm, song BSS ≥1 năm 2022 giảm từ 0,186 xuống 0,148. DOMAIN cải thiện CSI ở hai năm nhưng CI chứa 0; kết quả bỏ proxy và 63 ô chưa train không xác nhận chắc. Vì vậy giữ nhiều ứng viên có lý do, chưa quảng cáo một cấu hình thắng mọi chỉ số.

JAXA FTP cổng 21 hoạt động nhưng trả 504 cho FTPS; đăng nhập và tải raw/Gauge_NRT v8 thành công bằng prompt terminal. Script chỉ dùng FTP thường khi có `--allow-plain-ftp`; không đưa UID/password vào lệnh, file hay Git. Một tệp lúc 10 UTC ngày 13/10 đã qua SHA-256, định dạng và 93/93 ô; raw/Gauge tương quan 0,998 nhưng popup web không khớp 3/3 ô có mưa, chưa rõ lý do. Popup chỉ để tham khảo, không dùng làm nhãn/đầu vào ML. Demo ở `http://127.0.0.1:8766/` vẫn là archive validation và ECMWF thô; AI live cần lịch sử quan trắc, T-OPS và máy ghi liên tục.

**Mốc sáng 14/10 lúc 08:00:** bộ slide `reports/presentation_2026_10_14/PBL6_Da_Nang_2026_10_14.pptx` đã hoàn thành và kiểm tra hiển thị. Khoảng 07:15 kiểm tra mở file/demo và watcher; chỉ cập nhật trạng thái nguồn có bằng chứng, không đổi số mô hình vì thêm một file NRT đêm nay. Sau buổi trao đổi, kiểm chứng giả thuyết nhu cầu với người dùng thật và ghi phản hồi vào kế hoạch.

Cuối mỗi tuần, cập nhật mục 4/6 và quyết định/trạng thái trong `CLAUDE.md`, rồi commit/push code và báo cáo; dữ liệu/checkpoint ngoài Git.

## 7. Phân công gợi ý

**Nhóm có 3 người, chưa chốt phân vai (13/10/2026).** Mỗi người vẫn nghiên cứu toàn bộ, nhưng nên có một người chịu trách nhiệm chính cho từng đầu ra:

| Thành viên (tạm gọi) | Trách nhiệm chính | Người phản biện |
| --- | --- | --- |
| 1 | Dữ liệu, baseline, chống rò rỉ, bootstrap và tổng hợp kết quả | 2 |
| 2 | Bi-LSTM trước; TFT sau; checkpoint, cấu hình và nhật ký huấn luyện | 3 |
| 3 | Ghi log live, đầu vào ECMWF/vệ tinh, pipeline suy luận và app | 1 |

Cuối mỗi tuần, cả nhóm đọc cùng bảng kết quả và chốt một việc cần giải quyết tiếp. Người phụ trách ghi bằng chứng, cập nhật mục 4/6 và `CLAUDE.md`, rồi commit/push code và báo cáo; dữ liệu và checkpoint thử nghiệm giữ ngoài Git. Đây là đề xuất, chưa gán tên người.

Mọi người dùng chung `src/dataloader_v2.py` (dữ liệu vào) và `src/verification.py` (chấm điểm), nên phần việc của từng người ghép lại được với nhau.

| Mảng | Việc | Cần từ người khác | Giao cho người khác |
| --- | --- | --- | --- |
| **Dữ liệu và đánh giá** | Baseline trên lưới, tải ECMWF lưu trữ (T-OPS), bootstrap, bảng tổng hợp | — | Bảng mức sàn; script chấm điểm chung |
| **Sản phẩm A (Bi-LSTM)** | Pilot, ablation A0–A5, thí nghiệm độ trễ | Dataloader, bảng mức sàn | Checkpoint và dự báo trên tập test |
| **Sản phẩm B (TFT)** | Cài đặt TFT, ablation B0–B5, DLinear, Informer một cấu hình | Dataloader, bảng mức sàn | Checkpoint và dự báo trên tập test |
| **App và ghi log live** | Ghi log ECMWF và vệ tinh ngay; pipeline suy luận; giao diện | Checkpoint của A và B (từ tuần 7) | Demo và số liệu kiểm chứng live |
| **Báo cáo** (cả nhóm) | Viết song song từ tuần 2: dữ liệu → phương pháp → kết quả → hạn chế | — | — |

Máy huấn luyện chính là **máy có RTX 4060**. Máy Mac 8 GB dùng để xử lý dữ liệu, viết code và chạy thử nhỏ.

---

## 8. Câu hỏi còn mở

1. Vùng kiểm tra phía nam: **TP.HCM** (mưa nhiệt đới đồng bằng) hay **Đắk Lắk** (mưa dông Tây Nguyên)? Vùng phía bắc là Hà Nội.
2. Phân vai cụ thể cho 3 thành viên (điền tên ở mục 7). Hạn nộp chưa phải ràng buộc; ưu tiên kết quả mỗi tuần.

---

## 9. Bắt đầu cho thành viên mới

**Thứ tự đọc:** file này → [`CLAUDE.md`](CLAUDE.md) (quy ước và các lỗi đã gặp) → [`project_plan_v2.md`](project_plan_v2.md) (khi cần chi tiết) → [`reports/station_benchmark/README.md`](reports/station_benchmark/README.md) (kết quả baseline).

**Cài đặt và khôi phục dữ liệu:** dữ liệu nguồn khoảng 2,9 GB, file `pbl6_data_v2_2026-10-11.tar`, nằm trên Google Drive của nhóm.

```bash
git clone https://github.com/nibsu05/PBL6.git && cd PBL6
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt          # Windows: .venv\Scripts\pip install -r requirements.txt
tar -xf pbl6_data_v2_2026-10-11.tar                 # đặt file tar ở thư mục gốc repo
.venv/bin/python scripts/package_data.py verify      # phải báo 2233/2233 file khớp
.venv/bin/python scripts/build_dataset_v2.py --years 2015 2026
.venv/bin/python -c "from src.dataloader_v2 import build_cell_major; build_cell_major()"
.venv/bin/python scripts/inspect_dataloader_v2.py    # kiểm tra: 0 mẫu lệch
```

Trên máy có GPU NVIDIA, cài PyTorch bản CUDA theo hướng dẫn tại pytorch.org. Ví dụ: `pip install torch --index-url https://download.pytorch.org/whl/cu124`.

**Windows RTX 3050 Ti, driver 546.92 (đã kiểm tra 13/10/2026):** dùng Python Windows, tránh bản MSYS2 trong PATH. Trong `.venv` cài `torch==2.5.1` từ index `cu121`, rồi cài `requirements_windows.txt`. Các phiên bản NumPy/SciPy/scikit-learn/PyArrow được giữ cố định vì DLL của một số bản mới bị Application Control trên máy này chặn.

```powershell
.venv\Scripts\python.exe -m pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu121
.venv\Scripts\python.exe -m pip install -r requirements_windows.txt
.venv\Scripts\python.exe scripts/package_data.py verify
# Chỉ lưu 93 ô Đà Nẵng, vẫn tính lân cận từ toàn bộ lưới nguồn:
.venv\Scripts\python.exe scripts/build_dataset_v2.py --years 2015 2026 --cell-major-only --provinces "Đà Nẵng" --out data/processed/dataset_v2_danang
.venv\Scripts\python.exe scripts/inspect_dataloader_v2.py --dataset-dir data/processed/dataset_v2_danang --out reports/dataloader_v2_danang
.venv\Scripts\python.exe scripts/pilot_bilstm_v2.py --dataset-dir data/processed/dataset_v2_danang
```

Pilot có 30 ô, bước trượt 6 h, seed 42/43; tối đa 15 epoch, mỗi epoch 30.000 cửa sổ, early stopping patience 4. Chọn epoch/hiệu chỉnh xác suất trên 2022, so cặp trên 2023; chỉ số chính tổng 3 h trên tháng 5–10, mùa đông chỉ tổng 6 h. ERA5 trong báo cáo pilot là tham chiếu perfect prog, chưa thay thế kiểm định với ECMWF thật. Không chấm mô hình trên test 2025 ở bước này.

## 10. Quy tắc làm việc chung

- **Không commit dữ liệu, file PDF bài báo hay token** (repo công khai). Dữ liệu đặt trên Google Drive.
- **Một cách chấm điểm duy nhất:** dùng `src/verification.py`. Không tự viết hàm chỉ số riêng.
- **Không dùng MAE làm chỉ số chính.** Ở bài toán này, "luôn dự báo 0" đã có MAE rất thấp.
- **Không nhìn tập test để chọn mô hình.** Chỉ chọn dựa trên validation.
- **Báo cáo trung thực,** kể cả khi AI không thắng ECMWF. Đó vẫn là kết quả có giá trị nếu đo đúng.
- **Khi chốt một quyết định mới,** ghi vào `CLAUDE.md`, mục "Quyết định", và cập nhật mục 4 và 6 của file này.

## 11. Thuật ngữ

| Thuật ngữ | Nghĩa |
| --- | --- |
| **Nhãn** | Lượng mưa "thật" mà mô hình học để dự báo. Ở đây là GSMaP hiệu chỉnh trạm. |
| **ERA5** | Dữ liệu tái phân tích khí quyển của ECMWF. Dùng làm đầu vào khi huấn luyện, không dùng làm nhãn. |
| **ECMWF (IFS)** | Mô hình dự báo số của châu Âu, là đối thủ chính cần vượt. |
| **Perfect prog** | Khi huấn luyện, dùng ERA5 thay cho dự báo số ở các giờ tương lai; khi chạy app thì thay bằng dự báo ECMWF thật. |
| **T-ERA5 / T-OPS** | Đánh giá với đầu vào ERA5 (giới hạn trên) và với dự báo thật đã lưu trữ (giống khi chạy app). |
| **Độ trễ L** | Số giờ từ khi mưa rơi đến khi dữ liệu vệ tinh có sẵn để dùng (GSMaP khoảng 4 giờ). |
| **Ablation / LOGO** | Thêm dần hoặc bỏ từng nhóm đặc trưng để đo đóng góp của nhóm đó. |
| **Baseline** | Cách dự báo đơn giản để so sánh: khí hậu (trung bình nhiều năm), persistence (giữ nguyên giá trị gần nhất), ECMWF thô, LightGBM. |
| **POD / FAR / CSI** | Tỷ lệ bắt được sự kiện / tỷ lệ báo sai / chỉ số tổng hợp của hai tỷ lệ này (0 đến 1, càng cao càng tốt). |
| **FBI** | Tỷ lệ số lần báo có trên số lần xảy ra thật (1 là đúng tần suất). |
| **BSS** | Kỹ năng của dự báo xác suất so với xác suất khí hậu (> 0 là có kỹ năng). |
| **Bootstrap theo cặp** | Lấy mẫu lại theo khối ngày để tính khoảng tin cậy cho chênh lệch giữa hai mô hình. |
