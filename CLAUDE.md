# PBL6 – Dự báo mưa: bối cảnh cho agent

> **Đọc file này trước khi làm bất cứ việc gì.** Kế hoạch chi tiết, kèm số liệu bằng chứng, nằm ở
> [`project_plan_v2.md`](project_plan_v2.md); các nhận định trong kế hoạch cần đối chiếu code/dữ liệu và cập nhật phản biện. Cập nhật lần cuối: 20/10/2026.
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

## Định hướng hiện tại (người dùng xác nhận ngày 20/10/2026)

- **Ưu tiên nghiên cứu theo dạng bài báo:** đo đóng góp của việc thêm/bớt đặc trưng khí tượng, mưa và địa hình cho dự đoán mưa trên một vùng như Đà Nẵng. Không đặt trước đặc trưng mới chắc chắn cải thiện; không suy từ một vùng ra toàn Việt Nam.
- **App không còn là trọng tâm.** Thu nguồn live, hậu xử lý IFS và mục tiêu thắng ECMWF vận hành không phải cổng bắt buộc cho hướng nghiên cứu hiện tại. Giữ ERA5 làm nền nghiên cứu hồi cứu, nhưng vẫn phải tách dự báo dùng lịch sử với ước lượng dùng khí tượng giờ đích.
- Dữ liệu/cấu hình thực tế ở [thiet_ke_nghien_cuu_dac_trung_2026_10_20.md](reports/research_rainfall/thiet_ke_nghien_cuu_dac_trung_2026_10_20.md). Sau đó người dùng yêu cầu tạo2phiên bản tổng hợp vùng và so full_features cũ bằng thực nghiệm. Đã làm V1/V2 và pilot LightGBM24h→tổng3/6h; chưa chốt lại toàn bộ hạn hoặc kiến trúc nghiên cứu.
- Kiểm tra trước: đã quét93ô×87.672giờ2015–2024; ba cột kx/tt/era5_tp_mm mỗi cột thiếu1.953giátrịô–giờ; các cột khác hữu hạn. Lượt hiện tại verify nguồn2233/2233,22test đạt, kiểm tra parity V1/V2 và3mẫu tổng hợp trực tiếp nguồn. Hữu hạn không bảo đảm nhãn chính xác; test mô hình2025chưa mở.

### V1/V2 dữ liệu vùng và pilot so đầu vào (20/10/2026)

- Đã tạo `data/processed/regional_danang/v1_hourly.parquet` và `v2_hourly.parquet` ngoài Git:102.984giờ2015-01-01→2026-09-30. V1 có49predictor ứng viên, V2 có138(=V1+89không gian); các cột datetime/nhãn/QC tách riêng. Giữ nguyên file full_features và cube gốc. 2025chỉ được xuất cơ học, không fit/chấm/thống kê pilot.
- Trọng số là diện tích **toàn ô** trên cầu, footprint93ô~11.074km²; chưa có polygon giao ranh nên chưa gọi là trung bình địa giới chính xác. Tiểu vùng cố định không xem nhãn:23ô venbiển(proxy≤30km),26ô cao(≥600m,khôngvenbiển),44ô còn lại. Thiếu ô nào thì thống kê biến đóNaN, không thay vùng/điền0.
- Code: `src/regional_dataset.py`, `scripts/build_regional_datasets.py`, `pilot_regional_datasets.py`, `report_regional_datasets.py`. [Báo cáo cùng dữ liệu/CI/hình/Word](reports/regional_danang_v1_v2/README.md). Chỉ public code/thống kê; raw/Parquet/model/dự báo từng dòng ngoài Git.
- Pilot so OLD_COMMON,V1_COMMON,V2_COMMON,V1_FULL,V2_FULL trên cùng nhãn Gauge vùng và cửa sổ chung;3fold eval2021/2022/2023,calnămtrước,train2015→eval−2. Một seed LightGBM deterministic không bagging/feature sampling; không train NN mới. Không dùng cột mưa, ONI cũ hoặc CIN cũ trong đối chứng COMMON; FULL có CIN mới. Không đưa ERA5 giờ đích.
- RMSE3h toàn năm OLD_COMMON/V1_FULL/V2_FULL:2021=2,569/2,488/2,403;2022=2,632/2,584/2,648;2023=2,156/2,142/2,082mm. V2_FULL−V1_FULL:−0,085/+0,064/−0,060; CI95%chỉ2021dưới0. 6h chưa có lợi ích ổn định. V1_COMMON−OLD_COMMON CIchứa0ởcả3fold/cả2hạn; chưa khẳng định chỉ gộp lưới giúp hơn.
- Tín hiệu không gian rõ hơn ở2021, không lặp chắc2022/2023; nhiều phép so chưa hiệu chỉnh. GiữV1 làm nền,V2 nhánh ablation, không tuyên bố bộ mới thắng chung. Persistence dùng nhãnGauge hồi cứu có RMSE3h thấp hơn các model khí tượng nhưng có thông tin mưa quá khứ khác đầu vào; cần phép so bổ sung đúng nguồn, chưa là baseline vận hành. Không lấy pilot này thay kiểm chứng nhãn/thực tế/khả năng toàn Việt Nam.

### Cấu hình sản phẩm và hướng vận hành trước đây (tham khảo lịch sử)

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
10. **Nguồn JAXA và an toàn credential:** máy chủ FTP không hỗ trợ FTPS; script yêu cầu `--allow-plain-ftp`, nhập credential tại prompt terminal, không đặt vào đối số lệnh hoặc chat. Đã xác minh login và tải raw/Gauge_NRT v8 10 UTC ngày 13/10, không lưu credential. Decoder đúng định dạng tài liệu JAXA và đủ 93 ô; popup web khác cả hai binary ở 3/3 ô có mưa đã kiểm, chưa rõ nguyên nhân. Popup không là nhãn hoặc đầu vào ML. Báo cáo `reports/followup_danang/jaxa_binary_audit.json`; raw/Gauge/checkpoint ở `data/operational/` ngoài Git.

11. **Pilot đối chứng ECMWF (13/10):** đã tải 56/56 run IFS qua Open-Meteo cho 30 ô, 01–14/10/2024; 1.680 cặp issue–ô có nhãn GC permanent và forecast 6 h. Run chính khởi tạo trước issue 12 h, bảo thủ theo độ trễ công bố thường 4–6 h nhưng `available_at` lịch sử chưa chứng thực. Mưa API ghi cuối khoảng nên dịch +1 h khi so nhãn GSMaP. 0–3 h: RMSE 3,950 mm, CSI≥10 0,089; luôn dự báo 0 cùng mẫu RMSE 3,878, CI95% của chênh RMSE ECMWF−0 chứa 0. Chỉ 4/14 ngày có sự kiện mạnh; không chọn mô hình hay tuyên bố ECMWF yếu từ pilot này. Đây là forecast ECMWF qua xử lý giờ/không gian Open-Meteo, chưa là GRIB gốc, và **chưa so AI cùng mẫu**. Chi tiết `reports/research_rainfall/ecmwf_pilot_14d/README.md`.

12. **Cổng NRT as-of cho app:** `scripts/audit_jaxa_nrt_history.py` kiểm 24 khoảng giờ `[issue−28h, issue−4h)` của sản phẩm A, SHA-256/URI JAXA, 93 ô và `first_recorded_at ≤ issue`. Đã tải 24 tệp liên tiếp 12 UTC 12/10 → 11 UTC 13/10; tất cả SHA-256/shape đúng và 93/93 ô hữu hạn. Ở issue thử 16 UTC với lag4, 24/24 tệp có mặt nhưng chỉ 21/24 được máy ghi trước issue vì lượt tải hàng loạt qua mốc 16:00. Ở issue thử 17 UTC với lag5, 24/24 đã được ghi trước issue; **mốc 17 UTC lúc kiểm còn trong tương lai, chưa phát forecast**. Lần tải backlog chỉ biết giờ máy nhận, không chứng thực lúc JAXA công bố. Checkpoint hiện train lag4 nên lag5 cần retrain/đánh giá riêng; không bật AI live chỉ vì cổng nguồn lag5 đạt. Chi tiết `reports/followup_danang/nrt_latency_sensitivity.json`.

13. **Giá của quan trắc trễ thêm 1 giờ (13/10):** Sau audit24h, đã stress checkpoint Bi-LSTM RAW Tweedie lag4 với đầu vào lag5 và **train lại mô hình lag5** cùng30ô/index, 3seed, 30.000mẫu/fold, loss/budget; Platt/tau fit lại trên calibration. Validation tháng5–10 theo giờ VN, 0–3h: RMSE lag4→lag5 = 3,876→3,929 (2021), 4,581→4,624 (2022), 3,540→3,578 (2023) mm; CI95% hiệu RMSE lag5−lag4 dương ở cả3fold (xem `reports/followup_danang/bilstm_tweedie_lag5/`). CSI xác suất ≥10 giảm mô tả 2/3 năm nhưng CI từng năm chứa0; BSS≥1 giảm mô tả cả3. Đây là phép thử khám phá trên ERA5/GSMaP hồi cứu, chưa là T-OPS hay xác nhận độc lập. Không đổi app sang lag5 chỉ vì backfill24h qua cổng nguồn; cần logger live, đối chứng ECMWF và kiểm tra nguồn train→NRT.

14. **Ghi latency thật:** `scripts/watch_gsmap_nrt.py` đã chuẩn bị và test bằng FTP giả; prompt credential một lần trong terminal, poll `latest/` mỗi 10 phút, bỏ qua baseline lúc bắt đầu, chỉ tải file raw v8 mới và ghi `first_seen_at_utc`/`first_recorded_at_utc`, SHA-256 ngoài Git. `first_seen` là cận trên thời điểm JAXA phát hành với độ phân giải poll; lỗi mạng làm khoảng bất định lớn hơn. Người dùng đã chạy phiên 12 giờ lúc 16:31 UTC 13/10. Lần poll2 (16:41 UTC) thấy file raw mới `gsmap_nrt.20261013.1200.dat.gz`, không lỗi; thời điểm JAXA phát hành nằm sau baseline và trước 16:41, age sau cuối khoảng mưa bị chặn bảo thủ [3,53;3,70] h. Một tệp chưa là phân phối latency. Cổng NRT lag4/issue thử17 UTC đã có 24/24 tệp máy nhận trước issue (lúc audit issue còn trong tương lai); AI vẫn tắt vì khí tượng as-of/T-OPS chưa đạt. Snapshot tĩnh `reports/followup_danang/jaxa_live_first_detection.json`; status động watcher bị Git bỏ qua, raw ngoài Git.

15. **Báo cáo giảng viên 08:00 ngày 14/10:** Đã tạo bộ 8 slide PowerPoint chỉnh sửa được `reports/presentation_2026_10_14/PBL6_Da_Nang_2026_10_14.pptx` (7 slide chính, 1 slide đối chứng ECMWF) và rà soát nhu cầu từ tài liệu công `reports/research_rainfall/user_needs_desk_review_2026_10_14.md`. Trang người dùng là giả thuyết, **chưa có phỏng vấn**. Danang Smart City đã có theo dõi mưa/ngập; app PBL chỉ nhắm lớp dự báo mưa 0–6 giờ theo ô, chưa dự báo ngập đường hay cảnh báo chính thức. Các slide dùng validation lịch sử, nêu CI và giới hạn; AI live vẫn tắt. Nguồn đặt trong ghi chú từng slide.

16. **Slide khảo sát đề tài độc lập (14/10):** Đã tạo `reports/presentation_2026_10_14/Khao_sat_de_tai_1_slide_2026_10_14.pptx` để giải thích hạn 1–6 giờ, ưu tiên thử tổng mưa 3 giờ, sản phẩm đối chiếu và phạm vi công việc. Nguồn WMO xác nhận nowcasting 0–6 giờ; HKO MyObservatory có mưa 1–2 giờ; CWA Đài Loan có tổng mưa theo khoảng 3 giờ khi mưa lớn. Đây là tham chiếu thiết kế, **không chứng minh nhu cầu người dùng cao nhất ở 3 giờ**. Cần khảo sát quyết định thực tế và lựa chọn 1/3/6 giờ trước khi chốt giao diện. Ghi chú slide chứa URL và giới hạn diễn giải.

17. **Bộ slide giải thích đầy đủ (14/10):** Đã tạo `reports/presentation_2026_10_14/PBL6_Da_Nang_full_brief_2026_10_14.pptx` từ bộ 8 slide đã kiểm chứng, thêm bốn trang về đầu ra nghiên cứu, vai trò từng nguồn dữ liệu, phép so mô hình và luồng app. Tổng 12 slide, trong đó slide 12 ECMWF là dự phòng; ghi chú từng slide có nguồn/lời dẫn và `reports/presentation_2026_10_14/presenter_guide_full_2026_10_14.md` giúp trình bày 8–10 phút hoặc rút còn 5 phút. Không chạy thí nghiệm mới, không mở test 2025, không thay kết luận AI live/ECMWF.

## Phản biện dữ liệu ngày 20/10/2026

Theo yêu cầu đánh giá độc lập của người dùng, đã rà code, tính lại cặp nhãn Đà Nẵng 2021–2023 và probe Single Runs; không huấn luyện hoặc mở test mô hình 2025. Báo cáo [phan_bien_du_lieu_2026_10_20.md](reports/research_rainfall/phan_bien_du_lieu_2026_10_20.md) cần đọc trước khi dùng các quyết định/số liệu cũ làm lập luận:

- `fetch_openmeteo_baselines.py` không khóa `models=era5` cho Archive; `era5_om` là best_match, **không được quy bảng CSI 0,17 hoặc phát biểu 8% cho ERA5 thuần khi chưa truy lại nguồn**. Điều này không vô hiệu mọi bảng nguồn cũ, nhưng thay đổi cách diễn giải provenance.
- Cùng1.042ngày Đà Nẵng 2021–2023: CSI≥50 của cube ERA5/GSMaP GC =0,352/0,438; bootstrap khối5ngày/1.000lần seed20261020, CI95% GC−ERA5=[−0,054;+0,230]. Tháng5–10:0,467/0,487, CI=[−0,204;+0,243]. Đây là kiểm tra khám phá trên ghép ngày hiện có, chưa xác nhận nhãn giờ hoặc tính độc lập trạm. Cần kiểm chứng EOD/cờ GSOD; không tự đổi ngày từ tài liệu quốc gia cũ.
- Probe mới một tọa độ/run2024-10-01T00:00: IFS9km có mưa/bề mặt/TCWV/CAPE nhưng4trường850 toàn null; IFS025 trả400 runkhôngcó. Chưa thể tái tạo predictor850 bằng pipeline kho2024đã kiểm; không suy rằng mọi kho/ngày đều thiếu. BASE/RAW/DOMAIN chỉ dùng khí tượng quá khứ; S4 mới có ERA5 giờ đích; cả hai vẫn cần kiểm tra chuyển nguồn vận hành.
- Đề xuất thu hẹp đường app sang hậu xử lý forecast thật với bộ biến đã xác minh; ERA5 giữ cho nghiên cứu/pretrain có kiểm định; NRT/tầngcao phải chứng minh giá trị và khả năng nguồn. **Đây là đề xuất phản biện, chưa thay quyết định mô hình/phạm vi của nhóm.** Bản định hướng dữ liệu và Word được gắn cảnh báo đọc cùng phản biện.

## Còn chờ chốt (hỏi người dùng trước khi làm phần liên quan)

1. Hai vùng kiểm tra: Hà Nội, cùng TP.HCM **hoặc** Đắk Lắk.
2. Phân vai cụ thể cho 3 thành viên. Người dùng ưu tiên tiến độ hằng tuần; chưa cần chốt hạn nộp để chạy thí nghiệm Đà Nẵng.

## Trạng thái và việc tiếp theo

**Ưu tiên mới20/10:** nghiên cứu ablation đặc trưng trên dữ liệu lịch sử, theo định hướng người dùng ở đầu file. Các công việc app/logger/T-OPS bên dưới là lộ trình cũ, không tự tiếp tục như mục tiêu chính. Trước huấn luyện mới cần cố định đầu ra/hạn và giao thức so đặc trưng, kiểm chứng nhãn, giữ test2025 kín; không đưa ERA5 giờ đích vào phép so chính nếu gọi là dự báo từ quá khứ.

**Trạng thái cập nhật 14/10/2026:**
- Bộ slide mở rộng `reports/presentation_2026_10_14/PBL6_Da_Nang_full_brief_2026_10_14.pptx` gồm 11 trang chính và 1 trang ECMWF dự phòng, đã kiểm tra hiển thị. Lời dẫn tại `reports/presentation_2026_10_14/presenter_guide_full_2026_10_14.md`. Bộ 8 slide và slide khảo sát riêng vẫn giữ; nhu cầu người dùng mới là rà soát tài liệu, chưa phỏng vấn. Số mô hình không thay đổi; AI live chưa bật.
- Repo làm việc `D:\PBL6_v2`; tác giả commit mới là `nibsu05 <168987662+nibsu05@users.noreply.github.com>`. Không viết lại lịch sử đã push. Dữ liệu verify 2233/2233, dataloader lệch 0; test 2025 giữ kín.
- BASE/RAW/DOMAIN trên 30 ô/3 fold và đợt follow-up Tweedie LightGBM, Tweedie Bi-LSTM, NO_TERRAIN, 63 ô chưa train đã hoàn tất. Chi tiết cùng CI ở `reports/domain_screen_danang/` và `reports/followup_danang/`.
- Tweedie LightGBM RAW giảm RMSE 3 h mùa 5–10 từ 4,607/4,841/4,205 xuống 3,947/4,534/3,610 mm ở 2021/2022/2023. Tweedie Bi-LSTM RAW từ 4,046/4,661/3,963 xuống 3,876/4,581/3,540. Đây là validation lịch sử, chưa là hiệu năng vận hành. Đầu xác suất của Bi-LSTM Tweedie kém đi trong 2022 (BSS ≥1: 0,148 so 0,186).
- DOMAIN−RAW CSI quyết định ≥10 mm/3 h = +0,051/+0,007/+0,031 trên 30 ô; CI từng năm đều chứa 0. Bỏ proxy địa hình giảm CSI mô tả 0,025/0,009/0,051 nhưng CI chứa 0. Trên 63 ô chưa train, DOMAIN−RAW = +0,042/−0,003/+0,029, CI đều chứa 0. Chưa chốt biểu diễn domain là ưu thế đáng tin cậy.
- Retrain Bi-LSTM RAW Tweedie lag5 cùng 30 ô/index/3 seed đã hoàn tất 2021–2023; 9 checkpoint và dự báo riêng ngoài Git. RMSE3h tăng +0,053/+0,043/+0,038 mm so lag4, CI bootstrap theo cặp từng năm đều dương; CSI xác suất≥10 giảm mô tả 2/3 năm nhưng CI chứa0. `reports/followup_danang/bilstm_tweedie_lag5/` ghi đầy đủ; chưa chọn lag5 cho app.
- Demo `http://127.0.0.1:8766/` đang phục vụ checkpoint thật ở chế độ archive 2021–2023; 36 phép so HTTP với dự báo lưu đạt và 87 kiểm tra code đạt. Tab live chỉ hiển thị ECMWF nguồn/điểm JAXA công khai và cổng NRT lag4/issue thử17 UTC đạt 24/24 sau tệp mới watcher thấy 16:41 (lúc audit issue còn ở tương lai); lag4/issue16 của lần tải backlog chỉ 21/24, **không phải ML live**. Chưa so ECMWF trên cùng mẫu T-OPS. Single Runs `run` là giờ khởi tạo, không phải giờ công bố; phải chặn `available_at ≤ issue_at` (tài liệu Open-Meteo nêu trễ thường 4–6 h).
- Có **4 snapshot forecast hoàn chỉnh cho 93 ô** trong tối 13/10 (`init_time_known=false`), chỉ kiểm tra nguồn; chưa có tập ECMWF Single Runs 2024 cho 93 ô hoặc điểm AI–ECMWF cùng mẫu. Đối chứng ECMWF đã có trước đó ở `reports/station_benchmark/` là 10 trạm/ngày/hạn 1–5 ngày, không phải benchmark Bi-LSTM 0–6 giờ. Sau probe 1 điểm, pilot 56/56 run Single Runs 01–14/10/2024 trên 30 ô đã chấm đủ 1.680 cặp issue–ô. ECMWF Open-Meteo 0–3 h RMSE 3,950 mm, CSI≥10 0,089; CI chênh RMSE so luôn 0 chứa 0 và chỉ 4 ngày có sự kiện mạnh. Giờ công bố run lịch sử chưa chứng thực; chưa có bộ 2024/93 ô hoặc điểm AI–ECMWF cùng mẫu. Artifact `reports/research_rainfall/ecmwf_pilot_14d/`. Logger từng chạy giới hạn 2,1 giờ, chưa có máy luôn bật. JAXA FTP đã xác minh đăng nhập: 24 tệp gần nhất; tải raw và Gauge_NRT v8 lúc 10 UTC ngày 13/10, SHA-256 và shape 1200×3600 đúng. Ingest raw tạo 93/93 ô hữu hạn, bảo toàn thời điểm tải từ manifest. Raw/Gauge tương quan 0,998 trên 93 ô; popup web khác cả hai ở 3/3 ô có mưa. Không lưu credential trong Git; `--allow-plain-ftp` là bắt buộc vì FTPS không hỗ trợ.
- Ưu tiên tiếp theo: pilot ECMWF và retrain lag5 ba fold đã xong; kiểm tra đầu vào AI as-of (NRT lịch sử, past ERA5 thay bằng nguồn forecast có sẵn, đơn vị/lưới/giờ) trên cùng cửa sổ, sau đó mới so AI–ECMWF. Mở rộng thêm ngày/sự kiện và 93 ô khi phép ghép có chất lượng; checkpoint hiện dùng ERA5 hồi cứu + GSMaP lưu trữ nên chưa được gọi là so vận hành. Đồng thời để watcher NRT đang chạy tiếp tục ghi file mới nhiều giờ/ngày, theo dõi lỗi và phân phối latency trước chọn lag; xác định nguyên nhân popup khác binary hoặc bỏ popup khỏi phép so; kiểm tra dịch chuyển phân phối MVK/raw lưu trữ → NRT, rồi kiểm định T-OPS 2024 và ECMWF cùng mẫu trước AI live. Một tệp không đủ cửa sổ 24 giờ; test 2025 giữ kín. Brief sáng 14/10 ở `reports/research_rainfall/brief_giang_vien_2026_10_14.md`.

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
