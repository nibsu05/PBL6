# PBL6 – Dự báo mưa: bối cảnh cho agent

> **Đọc file này trước khi làm bất cứ việc gì.** Kế hoạch chi tiết, kèm số liệu bằng chứng, nằm ở
> [`project_plan_v2.md`](project_plan_v2.md); đó là nguồn sự thật. Cập nhật lần cuối: 13/10/2026.
> **Kế hoạch dành cho nhóm** (quy trình, giai đoạn hiện tại, lộ trình, phân công) nằm ở [`KE_HOACH_DU_AN.md`](KE_HOACH_DU_AN.md). Mỗi khi xong một giai đoạn hoặc chốt một quyết định, cập nhật các mục 4 và 6 của file đó.
> `project_master_plan.md`, `SURFACE_BASELINE_REPORT.md`, `DATA_GAP_PLAN.md` và `reports/informer_baseline_report.md`
> là tài liệu cũ, do agent khác viết. Chỉ dùng chúng để tham khảo lịch sử. Một số nhận định trong đó đã bị bác bỏ (xem mục "Quyết định").

## Người dùng và cách làm việc

- Nhóm sinh viên Đại học Bách khoa Đà Nẵng làm đồ án PBL6. **Trao đổi bằng tiếng Việt.**
- Người dùng muốn **đánh giá độc lập, có bằng chứng, trung thực**, kể cả khi kết quả âm. Không chiều theo tài liệu cũ một cách mù quáng.
- Không phóng đại kết quả. Mọi so sánh phải trên cùng tập mẫu, kèm baseline và khoảng tin cậy.
- Máy:
  - MacBook M2 8 GB RAM: lưu dữ liệu, viết code, chạy pilot.
  - Máy nhóm có RTX 4060 8 GB: chạy huấn luyện dài.
  - Máy Windows đang thiết lập ngày 13/10/2026: RTX 3050 Ti Laptop 4 GB, driver 546.92; ổ C ít dung lượng. Python Windows ở `.venv\Scripts\python.exe` (không dùng Python MSYS2 có sẵn).
  - Repo làm việc chuyển sang USB **`D:\PBL6_v2`** theo xác nhận của người dùng. `D:\PBL6` cũ giữ nguyên; bản trên C là bản nguồn/backup của lần chuyển này.
- Repo `nibsu05/PBL6` là **repo công khai**. Không commit dữ liệu, file PDF bài báo hay thông tin đăng nhập.

## Bài toán (đã chốt)

- **Sản phẩm A:**
  - Mô hình: Bi-LSTM.
  - Hạn: t+1…t+6 h.
  - Phát hành mỗi giờ.
  - Hiển thị: tổng mưa 3 h và xác suất.
- **Sản phẩm B:**
  - Hạn: 1–3 ngày, có thể mở rộng đến 7 ngày.
  - Phát hành lúc 00/06/12/18 UTC.
  - Hiển thị: tổng mưa ngày và xác suất vượt 16/50/100 mm.
  - Mô hình: **TFT** (Temporal Fusion Transformer), chốt ngày 11/10/2026 vì giảng viên không bắt buộc Informer. Chi tiết ở plan mục 4.4.
- **Thuật ngữ** (Thông tư 08/2022): cực ngắn ≤12 h; ngắn 12–72 h; vừa 3–10 ngày. **Không gọi 24–72 h là "dài hạn".**
- **Đơn vị không gian:** ô 0,1° (lưới GSMaP).
  - Một tỉnh là tập các ô nằm trong ranh giới 34 tỉnh mới (Nghị quyết 202/2025). Đà Nẵng mới gồm Đà Nẵng cũ và Quảng Nam.
  - Dùng **một mô hình chung** cho mọi ô, kèm đặc trưng tĩnh. Không huấn luyện riêng từng tỉnh.
  - Vùng trọng tâm là Đà Nẵng mới. Thêm 2 vùng khí hậu khác để kiểm tra tổng quát hóa.
- **Nhãn:** GSMaP v8 hiệu chỉnh trạm (`hourlyPrecipRateGC`), chốt ở Cổng 1 ngày 11/10/2026.
  - IMERG Final là nhãn kiểm tra độ bền.
  - GSMaP thô là đầu vào quan trắc (nhóm A1), dịch trễ L giờ.
- **Vai trò của AI:** hậu xử lý cộng nowcasting. Đối thủ chính là **dự báo ECMWF thô**, không phải các mô hình AI khác.
- **Nguyên tắc perfect prog:** khi train, giá trị tại giờ đích lấy từ ERA5; khi chạy thật, thay bằng ECMWF. Khoảng cách giữa hai chế độ đo bằng T-OPS.

## Quyết định và bằng chứng then chốt

Số liệu đầy đủ ở plan v2, các mục 1, 4.1, 4.1b, 0b và 1.7.

1. **ERA5 không dùng làm nhãn.**
   - Tại trạm Đà Nẵng, ERA5 chỉ bắt được 8 % số ngày ≥100 mm.
   - Cùng bộ đặc trưng ERA5 cho R² 0,70 khi dự đoán mưa ERA5 nhưng chỉ 0,42 khi dự đoán mưa trạm, nghĩa là ablation dùng nhãn ERA5 sẽ thổi phồng giá trị đặc trưng.
2. **Thí nghiệm 0 (10 trạm GSOD, 2021–2024):** CSI ≥50 mm của GSMaP hiệu chỉnh là 0,33; IMERG 0,22; ERA5 0,17.
   - Lưu ý: GSMaP được hiệu chỉnh theo dữ liệu trạm NOAA CPC, có thể gồm chính các trạm kiểm chứng, nên điểm tại trạm cao hơn thực tế.
3. **Mức sàn:** ECMWF dự báo trước 1 ngày ngang ERA5. Mọi dự báo tất định có BSS < 0 và FBI ≥50 mm khoảng 0,47.
   - Vì vậy mô hình phải xuất xác suất đã hiệu chỉnh.
   - MAE **không phải** chỉ số chính.
4. **Chất lượng nhãn mưa giờ phụ thuộc mùa ở Đà Nẵng/Trung Bộ.**
   - Audit 93 ô Đà Nẵng 2021–2023: 67,6% tổng GC mùa 11–2 nằm ở giờ raw ≤0,01 mm; mùa 5–10 là 20,8%. Chỉ báo cho thấy phụ thuộc hiệu chỉnh mạnh, không chứng minh mọi giờ mưa mùa đông đều sai hoặc được trải đều.
   - Sản phẩm A chấm giờ/3 h chính trên tháng 5–10; mùa đông chỉ chấm 6 h như chỉ số phụ vẫn có bất định nhãn. Tổng 24 h dùng QC nhãn với trạm hoặc sản phẩm B, không biến mô hình 6 h thành dự báo 24 h. Tách mọi bảng theo mùa.
5. **Chọn TFT thay Informer cho sản phẩm B** (chốt 11/10/2026). Informer là lựa chọn yếu vì:
   - Trên bộ chuẩn Weather, Informer kém cả phương án lặp lại giá trị gần nhất (Zeng 2023).
   - Lần chạy cũ của đồ án chỉ đạt R² = 0,04.
   - Informer không có cơ chế riêng cho đầu vào tương lai và đặc trưng tĩnh.
   - TFT có sẵn cơ chế cho đặc trưng tĩnh, dự báo số tương lai và chuỗi quá khứ, xuất được phân vị và trọng số chọn biến.
   - Đối chứng bắt buộc: ECMWF thô, ECMWF + quantile mapping, LightGBM, DLinear, Bi-LSTM (bảng 2×2). Informer chỉ chạy một cấu hình.
   - TFT được **tự cài đặt** bằng PyTorch, đọc từ `WindowSampler`; không dùng `pytorch-forecasting` vì không vừa 8 GB RAM.
6. **Không có dữ liệu Vrain** (người dùng xác nhận không xin được). Kiểm chứng độc lập chỉ dựa vào NOAA GSOD tại 10 trạm, đến 24/08/2025.
7. **Những nhận định cũ đã bị bác bỏ:**
   - "Informer vượt Bi-LSTM 21 %": hai mô hình được chấm trên tập test khác nhau.
   - "IMERG trễ 29 h nên không dùng được làm đầu vào": IMERG Early lấy trực tiếp từ NASA chỉ trễ khoảng 4 h.
   - "Previous Runs có CAPE": thực tế các trường này rỗng.
8. **Phạm vi và cách làm việc chốt ngày 13/10/2026:** tập trung nghiên cứu và thử nghiệm Đà Nẵng trước; chưa chọn vùng phía nam. Nhóm 3 người, chưa phân vai; ưu tiên đầu ra kiểm chứng được hằng tuần, không dùng hạn nộp giả định làm ràng buộc. Phân vai ở kế hoạch mục 7 chỉ là đề xuất.

9. **Kết quả sau thay hàm mất mát (13/10):** cải thiện lớn nhất hiện thấy ở đầu lượng mưa Tweedie, không phải thêm nhiều tên mô hình. Giữ riêng điểm lượng mm và xác suất; chỉ chọn cấu hình app sau khi kiểm định T-OPS cùng ECMWF, bởi Tweedie Bi-LSTM làm BSS năm 2022 xấu hơn. Kết quả NO_TERRAIN/63 ô chưa đủ quy lợi ích chắc chắn cho địa hình.
10. **Nguồn JAXA và an toàn credential:** máy chủ FTP không hỗ trợ FTPS trong probe; không tự hạ cấp rồi gửi mật khẩu. Script yêu cầu `--allow-plain-ftp`, nhập credential tại prompt terminal, không đặt vào đối số lệnh hoặc chat, chỉ lưu dữ liệu trong `data/operational/`.

## Còn chờ chốt (hỏi người dùng trước khi làm phần liên quan)

1. Hai vùng kiểm tra: Hà Nội, cùng TP.HCM **hoặc** Đắk Lắk.
2. Phân vai cụ thể cho 3 thành viên. Người dùng ưu tiên tiến độ hằng tuần; chưa cần chốt hạn nộp để chạy thí nghiệm Đà Nẵng.

## Trạng thái và việc tiếp theo

**Trạng thái chốt sau lượt tiếp tục 13/10/2026:**
- Repo làm việc `D:\PBL6_v2`; tác giả commit mới là `nibsu05 <168987662+nibsu05@users.noreply.github.com>`. Không viết lại lịch sử đã push. Dữ liệu verify 2233/2233, dataloader lệch 0; test 2025 giữ kín.
- BASE/RAW/DOMAIN trên 30 ô/3 fold và đợt follow-up Tweedie LightGBM, Tweedie Bi-LSTM, NO_TERRAIN, 63 ô chưa train đã hoàn tất. Chi tiết cùng CI ở `reports/domain_screen_danang/` và `reports/followup_danang/`.
- Tweedie LightGBM RAW giảm RMSE 3 h mùa 5–10 từ 4,607/4,841/4,205 xuống 3,947/4,534/3,610 mm ở 2021/2022/2023. Tweedie Bi-LSTM RAW từ 4,046/4,661/3,963 xuống 3,876/4,581/3,540. Đây là validation lịch sử, chưa là hiệu năng vận hành. Đầu xác suất của Bi-LSTM Tweedie kém đi trong 2022 (BSS ≥1: 0,148 so 0,186).
- DOMAIN−RAW CSI quyết định ≥10 mm/3 h = +0,051/+0,007/+0,031 trên 30 ô; CI từng năm đều chứa 0. Bỏ proxy địa hình giảm CSI mô tả 0,025/0,009/0,051 nhưng CI chứa 0. Trên 63 ô chưa train, DOMAIN−RAW = +0,042/−0,003/+0,029, CI đều chứa 0. Chưa chốt biểu diễn domain là ưu thế đáng tin cậy.
- Demo `http://127.0.0.1:8766/` đang phục vụ checkpoint thật ở chế độ archive 2021–2023; 36 phép so HTTP với dự báo lưu đạt và 81 kiểm tra code đạt. Tab live chỉ hiển thị ECMWF thô/điểm JAXA công khai, **không phải ML live**. Chưa so ECMWF trên cùng mẫu T-OPS.
- Forecast 93/93 ô đã đạt hợp đồng nguồn trong snapshot; logger từng chạy giới hạn 2,1 giờ, chưa có máy luôn bật. Điểm GSMaP NRT công khai đã probe nhưng không đạt điều kiện đầu vào ML. Máy chủ FTP JAXA cổng 21 trả 220, FTPS `AUTH TLS` trả 504; chưa xác minh đăng nhập/tải binary vì công cụ terminal không truyền được mật khẩu qua stdin an toàn. `scripts/fetch_gsmap_nrt.py` bắt buộc chọn rõ `--allow-plain-ftp` nếu dùng FTP thường, hỗ trợ `--check-only`; không có credential trong Git.
- Ưu tiên tiếp theo: người dùng chạy kiểm tra đăng nhập JAXA trong terminal riêng; tải một tệp NRT v8, kiểm tra schema/latency và parity với dữ liệu train; sau đó ghi quan trắc liên tục, kiểm định T-OPS 2024 và ECMWF cùng mẫu trước khi bật AI live. Brief sáng 14/10 ở `reports/research_rainfall/brief_giang_vien_2026_10_14.md`; lộ trình ở `execution_plan.md`.

**Đã xong (11/10/2026):**
- Bộ đánh giá dùng chung.
- Dữ liệu 10 trạm và bảng baseline (`reports/station_benchmark/README.md`).
- Thí nghiệm 0.
- Dataset v2: 296 ô đất, trong đó 214 ô thuộc Việt Nam (93 Đà Nẵng, 85 Quảng Ngãi, 32 Huế, 4 ô giáp ranh); giai đoạn 2015 → 09/2026; 51 đặc trưng.
- Dataloader.

**Thiết lập máy Windows và pilot (13/10/2026):**
- Đã khôi phục dữ liệu và xác minh **2233/2233 file khớp, thiếu 0, sai 0**; xóa bản tar sau verify theo đồng ý của người dùng để thu hồi dung lượng. Nguồn vẫn trên Drive.
- GitHub đã đăng nhập bằng `gh auth login --web`, thông tin đăng nhập lưu trong keyring.
- Python Windows 3.12.15; PyTorch 2.5.1+cu121; CUDA nhận RTX 3050 Ti và phép nhân ma trận GPU hữu hạn. `requirements_windows.txt` giữ các phiên bản tương thích.
- Dataset riêng `data/processed/dataset_v2_danang/`: 93 ô, khoảng 2 GB; số giờ và tổng mưa từng năm khớp manifest gốc. Inspect bốn cấu hình: **0 mẫu lệch, batch hữu hạn**.
- Sửa dataloader loại cửa sổ có nhãn vượt ranh giới năm train/validation; đổi phiên bản cache để không tái dùng chỉ số cũ.
- Pilot dùng chung cửa sổ của S4 cho S0/S1/S4, 30 ô chọn theo địa hình/khoảng cách biển, 2 seed. Train 2015–2021; chọn epoch và hiệu chỉnh xác suất ở 2022; so cặp ở 2023. **Không chấm mô hình trên test 2025 trong pilot.**
- Pilot 2 seed đã xong: BSS mùa hè–thu tổng 0–3 h S0/S1/S4 = 0,186/0,195/0,239; CSI ≥10 mm = 0,157/0,150/0,089. S4 giảm BS chắc hơn theo bootstrap, nhưng chưa phân biệt chắc CSI. Không tuyên bố thắng ECMWF hoặc TFT. Xem `reports/pilot_bilstm_v2/README.md`.
- Thiết kế so kiến trúc và app được rà soát ở `reports/research_rainfall/README.md`: bảng 2×2 cùng dữ liệu/hạn; ablation thông tin tách riêng; ECMWF là đối chứng giá trị vận hành. TFT và T-OPS chưa triển khai trong lượt này.
<!-- OFFLINE_BATCH_STATUS --> Batch 3 seed trên 93 ô đã hoàn tất; bảng số liệu ở `reports/pilot_bilstm_v2_93cells_3seeds/`. Đã diễn giải: S1 tăng CSI so S0; S4 tốt hơn về BS; chưa so kiến trúc hoặc kiểm định vận hành. Không chấm test 2025.

- Rà soát bài báo và chẩn đoán bổ sung ở `reports/research_rainfall/literature_domain_review.md`: ưu tiên kiểm tra nhãn, quy tắc quyết định mưa hiếm và giả thuyết gió–ẩm–địa hình trước khi nhân số kiến trúc. Chẩn đoán 30 ô/3 seed: CSI đầu xác suất S1 = 0,383 (ngưỡng chọn 2022, chấm 2023), FAR = 0,485; đây là khám phá validation, không thay CSI lượng mưa gốc hoặc chứng minh triển khai. Chưa train E0–E5/TFT.

**Tiếp theo, theo thứ tự:**
0. *(Ưu tiên)* Bộ ghi khí tượng93 ô đã có và chạy giới hạn2,1 giờ; cần chốt máy luôn bật và nguồn NRT để ghi lâu dài: dự báo ECMWF cho các ô Đà Nẵng và quan trắc GSMaP NRT/IMERG. Mùa mưa đang diễn ra, nên mỗi tuần chậm là mất một tuần dữ liệu để kiểm định thật.
1. Đã xong pilot 3 seed trên 30 và 93 ô: S1 tăng CSI so S0 có khoảng tin cậy không chứa 0; S4 giảm BS so S0/S1. Chưa có cấu hình thắng mọi chỉ số. Đợt tiếp theo được đề xuất ở `reports/research_rainfall/next_experiment.md`: kiểm tra nguồn live, giữ Bi-LSTM để so riêng TCWV, CAPE/CIN, gió–ẩm 850 và độ ẩm đất trên nền A0+A1; thêm baseline cùng mẫu, sau đó kiểm tra kiến trúc và vận hành. Đã xong đợtBASE/RAW/DOMAIN 3 fold; xem reports/domain_screen_danang/ và reports/research_rainfall/execution_plan.md. Test 2025 giữ kín.
2. Baseline khí hậu/LightGBM cùng3 fold đã có; bổ sung persistence đúng nguồn live và ECMWF thô/hiệu chỉnh khi T-OPS.
3. Ablation A0–A5 và thí nghiệm độ trễ L ∈ {0,5; 2; 4; 8; 14; ∞} trên máy RTX 4060.
4. Sản phẩm B: **TFT** (tự cài đặt; quantile loss cộng xác suất vượt ngưỡng ngày), ablation B0–B5 và LOGO; DLinear; Informer một cấu hình; bảng 2×2 Bi-LSTM với TFT.
5. T-OPS:
   - Single Runs ECMWF IFS 9 km: có mưa, CAPE, TCWV từ 03/2024; biến 850 hPa trả rỗng.
   - Historical Forecast: có từ 2017.
6. Tải thêm 2 vùng (cùng script, đổi `--bbox`) và chạy thí nghiệm "bỏ một vùng".
7. App: một mô hình cho mọi ô; hiển thị cấp tỉnh và cấp xã; ghi log để kiểm định live.

## Bản đồ code mới (pipeline v2)

| File | Vai trò |
| --- | --- |
| `src/verification.py` | Chỉ số dùng chung (ngưỡng `>=`), bootstrap khối theo cặp, chia fold cuốn chiếu theo năm |
| `src/baselines.py` | Baseline khí hậu theo ngày trong năm, persistence |
| `src/station_registry.py`, `src/admin_regions.py` | 12 trạm synop; ánh xạ 63 tỉnh cũ (GAUL) sang 34 tỉnh mới |
| `src/dataset_v2.py` | Phép biến đổi thuần: nội suy ERA5 → ô, mã hóa CIN, thống kê lân cận 5×5, đặc trưng thời gian |
| `src/domain_features.py`, `src/domain_inference.py`, `src/live_domain_inputs.py` | Biểu diễn vật lý, suy luận checkpoint và hợp đồng nguồn khí tượng |
| `scripts/screen_danang_domain.py`, `collect_domain_live.py`, `predict_domain_archive.py` | Thí nghiệm3 fold, thu forecast và kiểm tra suy luận |
| `demo/domain_api.py` | API archive từ checkpoint thật; chưa dự báo live |
| `src/dataloader_v2.py` | `WindowConfig`, `product_a/b`, `FEATURE_GROUPS` A0–A5 / B0–B5, `sample_index`, `Normalizer`, `WindowSampler`, `epoch_subset`, `torch_dataset` |
| `scripts/fetch_gsod_stations.py`, `fetch_openmeteo_baselines.py`, `station_daily_benchmark.py` | Dữ liệu trạm và bảng baseline / Thí nghiệm 0 |
| `scripts/extract_gee_precip.py`, `extract_gee_era5.py`, `extract_gee_static.py` | Tải từ Earth Engine (cần `--project`) |
| `scripts/build_dataset_v2.py`, `inspect_dataloader_v2.py` | Dựng dataset v2; kiểm tra dataloader |
| `scripts/package_data.py`, `download_progress.py` | Đóng gói / kiểm tra dữ liệu khi chuyển máy; theo dõi tiến độ tải |

Code cũ (`src/train_bilstm.py`, `src/informer/`, `src/rain_alert_model.py`, …) vẫn dùng lại được phần mô hình, nhưng **đầu vào và nhãn cũ thì không**.

## Quy ước và các lỗi đã gặp (đọc trước khi sửa code dữ liệu)

- **Thời gian:** hàng `t` = khoảng `[t, t+1h)` UTC.
  - Open-Meteo và ERA5 ghi mưa ở *cuối* khoảng, nên phải dịch lùi 1 h.
  - GSMaP và IMERG ghi mưa ở *đầu* khoảng.
  - Ngày của GSOD tính theo UTC, tức 07h–07h giờ Việt Nam.
- **CIN bị mask** nghĩa là không có mực đối lưu tự do: mã hóa thành `cin_capped = 500` và `has_lfc = 0`. Giờ thiếu hẳn ERA5 thì để NaN. **Không bao giờ điền 0.**
- **ERA5 trên Earth Engine:** `getRegion` phải dùng `crsTransform=[0.25,0,-180.125,0,-0.25,90.125]`. Dùng `scale` sẽ lấy mẫu lệch nửa ô. Chỉ có tầng 850 và 500 hPa.
- **pandas 3:** `date_range` dùng đơn vị micro giây, nên khi lưu mốc giờ phải ép kiểu `datetime64[ns]` tường minh.
- **GSOD:** chỉ giữ cờ D/F/G (đủ 24 h) và I (ngày khô). Nội Bài và Cần Thơ báo toàn 0 nên bị loại tự động.
- **Open-Meteo Previous Runs:**
  - GFS `previous_day5` thấp khoảng 50 % ở mọi quý (lỗi nguồn), nên đã loại.
  - Previous Runs không có CAPE/TCWV, còn Single Runs (`ecmwf_ifs`) thì có.
- **IMERG V07 bản permanent** trên Earth Engine chỉ có đến 30/09/2025.
- **Python Homebrew** chặn `pip install` toàn hệ thống, nên luôn dùng `.venv`. Test cũ cần `matplotlib` và `torch`.

## Môi trường, dữ liệu, lệnh

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # có torch, earthengine-api
# Dữ liệu nguồn (khoảng 2,9 GB) nằm trên Google Drive của nhóm: pbl6_data_v2_2026-10-11.tar
tar -xf pbl6_data_v2_2026-10-11.tar                   # chạy ở thư mục gốc repo
.venv/bin/python scripts/package_data.py verify        # so với data/DATA_MANIFEST_v2.json
.venv/bin/python scripts/build_dataset_v2.py --years 2015 2026                                    # khoảng 1,5 phút
.venv/bin/python -c "from src.dataloader_v2 import build_cell_major; build_cell_major()"          # khoảng 1,5 phút
.venv/bin/python scripts/inspect_dataloader_v2.py      # kiểm tra: 0 mẫu lệch, batch hữu hạn
.venv/bin/python scripts/station_daily_benchmark.py    # tạo lại bảng baseline và Thí nghiệm 0
for t in tests/test_*.py; do PYTHONPATH=.:scripts .venv/bin/python -m unittest $t; done
```

Nếu muốn tải lại từ Earth Engine: chạy `earthengine authenticate` rồi dùng `--project <ID project của nhóm>` (hỏi người dùng ID). Mất khoảng 1–2 h.
