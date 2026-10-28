# PBL6 – Dự báo mưa: bối cảnh cho agent

> **Đọc file này trước khi làm bất cứ việc gì.** Kế hoạch chi tiết, kèm số liệu bằng chứng, nằm ở
> [`project_plan_v2.md`](project_plan_v2.md); đọc cùng phương án hiện tại và đối chiếu bằng chứng. Cập nhật lần cuối: 28/10/2026.
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
  - **Máy hiện tại xác nhận21/10/2026:** RTX4060Laptop8GB, driver617.14; CUDA khả dụng với torch2.5.1+cu121, RAM hệ thống nhận diện~15,2GiB. Người dùng xác nhận dùng GPU này cho TFT. Mốc3050Ti ở trên là lịch sử, không dùng để dự toán công việc mới.
  - Repo làm việc chuyển sang USB **`D:\PBL6_v2`** theo xác nhận của người dùng. `D:\PBL6` cũ giữ nguyên; bản trên C là bản nguồn/backup của lần chuyển này.
- Repo `nibsu05/PBL6` là **repo công khai**. Không commit dữ liệu, file PDF bài báo hay thông tin đăng nhập.

## Quyết định hiện tại: nghiên cứu và dự đoán vùng trực tiếp (20/10/2026)

- Người dùng xác nhận **nghiên cứu đặc trưng là trọng tâm, đầu ra chính là dự đoán vùng trực tiếp**. Tổng hợp khí tượng/nhãn từ các ô trước khi học; một mẫu là một thời điểm của cả vùng. Không tự đổi sang dự đoán từng ô rồi mới gộp hoặc quay lại ưu tiên app.
- Đã hợp nhất tài liệu nhóm TONG_HOP_DE_XUAT với phương án nghiên cứu: [phương án cuối](reports/regional_research_plan_2026_10_20/PHUONG_AN_CUOI.md), kèm Word, 18 quyết định, mỗi quyết định giải thích đủ sáu tiêu chí mục 13.
- **Giữ D1/D2/D9/D10/D14/D15 có nhãn bằng chứng theo yêu cầu người dùng**; chưa có phép đo tốt hơn cùng giao thức để thay. Gauge chính/IMERG kiểm tra độ bền; CSI/BSS chính, RMSE/bias và MAE phụ; tách mùa, không gọi điểm giờ mùa đông là kết quả chính. Ghi rõ provenance Best Match và giới hạn nhãn giờ, không dùng phép tính khác mẫu để tự thay bảng của nhóm.
- Phương án triển khai chọn lịch sử 24 giờ → 6 giờ, Bi-LSTM vùng và LightGBM, factorial E0–E7 trên V1; V2/S0/S7 và raw lag4/Q0/Q7 là nhánh phụ. Danh mục 11/12/20/1 cột B/A/M/C không chồng lấn lưu trong feature_groups.json. Không đưa ERA5 giờ đích vào nghiên cứu chính; không gọi SST là đã kiểm tra ENSO/MJO.
- Ba fold phát triển eval 2021–2023; sau khóa thiết kế, train 2015–2023/cal 2024/test 2025. Không dùng 2026 để chọn mô hình chấm năm 2025. Giữ kín test 2025.
- V1/V2 đã tạo ở main d3f3936, nhưng loader/huấn luyện Bi-LSTM vùng theo phương án cuối **chưa triển khai trong lượt viết tài liệu**. Cần sửa các lỗi trên dev theo [bản rà soát](reports/research_rainfall/dev_bilstm_review_2026_10_20.md), chốt giao ranh/ô biên và kiểm chứng nhãn trước chạy đầy đủ. 93 ô hiện là vùng xấp xỉ, không mặc định đúng toàn địa giới.
- App, TFT 1–3 ngày, T-OPS và đa vùng là mở rộng; giữ code/kết quả đã có để tái dùng. Người dùng yêu cầu đưa toàn bộ thay đổi mới lên main; bộ tài liệu hợp nhất và rà soát được công bố trên main, không merge dữ liệu/checkpoint của dev.
- Kiểm tra trước: đã quét93ô×87.672giờ2015–2024; ba cột kx/tt/era5_tp_mm mỗi cột thiếu1.953giátrịô–giờ; các cột khác hữu hạn. Lượt hiện tại verify nguồn2233/2233,22test đạt, kiểm tra parity V1/V2 và3mẫu tổng hợp trực tiếp nguồn. Hữu hạn không bảo đảm nhãn chính xác; test mô hình2025chưa mở.

### V1/V2 dữ liệu vùng và pilot so đầu vào (20/10/2026)

- Đã tạo `data/processed/regional_danang/v1_hourly.parquet` và `v2_hourly.parquet` ngoài Git:102.984giờ2015-01-01→2026-09-30. V1 có49predictor ứng viên, V2 có138(=V1+89không gian); các cột datetime/nhãn/QC tách riêng. Giữ nguyên file full_features và cube gốc. 2025chỉ được xuất cơ học, không fit/chấm/thống kê pilot.
- Trọng số là diện tích **toàn ô** trên cầu, footprint93ô~11.074km²; chưa có polygon giao ranh nên chưa gọi là trung bình địa giới chính xác. Tiểu vùng cố định không xem nhãn:23ô venbiển(proxy≤30km),26ô cao(≥600m,khôngvenbiển),44ô còn lại. Thiếu ô nào thì thống kê biến đóNaN, không thay vùng/điền0.
- Code: `src/regional_dataset.py`, `scripts/build_regional_datasets.py`, `pilot_regional_datasets.py`, `report_regional_datasets.py`. [Báo cáo cùng dữ liệu/CI/hình/Word](reports/regional_danang_v1_v2/README.md). Chỉ public code/thống kê; raw/Parquet/model/dự báo từng dòng ngoài Git.
- Pilot so OLD_COMMON,V1_COMMON,V2_COMMON,V1_FULL,V2_FULL trên cùng nhãn Gauge vùng và cửa sổ chung;3fold eval2021/2022/2023,calnămtrước,train2015→eval−2. Một seed LightGBM deterministic không bagging/feature sampling; không train NN mới. Không dùng cột mưa, ONI cũ hoặc CIN cũ trong đối chứng COMMON; FULL có CIN mới. Không đưa ERA5 giờ đích.
- RMSE3h toàn năm OLD_COMMON/V1_FULL/V2_FULL:2021=2,569/2,488/2,403;2022=2,632/2,584/2,648;2023=2,156/2,142/2,082mm. V2_FULL−V1_FULL:−0,085/+0,064/−0,060; CI95%chỉ2021dưới0. 6h chưa có lợi ích ổn định. V1_COMMON−OLD_COMMON CIchứa0ởcả3fold/cả2hạn; chưa khẳng định chỉ gộp lưới giúp hơn.
- Tín hiệu không gian rõ hơn ở2021, không lặp chắc2022/2023; nhiều phép so chưa hiệu chỉnh. GiữV1 làm nền,V2 nhánh ablation, không tuyên bố bộ mới thắng chung. Persistence dùng nhãnGauge hồi cứu có RMSE3h thấp hơn các model khí tượng nhưng có thông tin mưa quá khứ khác đầu vào; cần phép so bổ sung đúng nguồn, chưa là baseline vận hành. Không lấy pilot này thay kiểm chứng nhãn/thực tế/khả năng toàn Việt Nam.

## Nhánh 24–72 giờ được duyệt ngày 21/10/2026 — pilot và ma trận phát triển

- **Cập nhật ưu tiên 28/10/2026 — người dùng yêu cầu chạy nốt Informer:** đã chạy đủ 54 lượt E1–E6, dùng nguyên hàm fit pilot và dữ liệu/tham số/loss/calibration. Dùng lại 18 lượt E0/E7; tổng 72 Informer, cùng 72 TFT và 24 pipeline LightGBM = 168 lượt. [Hồ sơ đầy đủ](reports/informer_regional_matrix_2026_10_28/README.md), [49 slide/Word/Excel chín sheet](reports/short_range_complete_2026_10_28/README.md). Phần fit/save/replay mới khoảng 22,4 phút, tiến trình khoảng 22,8 phút; không gọi đây là thời gian hoàn tất nghiên cứu.
- Kiểm chứng độc lập 72 checkpoint × calibration/evaluation = 144 split, tái tạo scaler train, calibration, ensemble và điểm số. Điểm Informer E0/E7 và TFT/LightGBM giữ nguyên; nguồn 2233/2233 file khớp; hai unittest Informer đạt. Không tuning hoặc mở test 2025. Code huấn luyện và báo cáo cũ giữ nguyên; mô hình/dữ liệu/dự đoán từng mốc nằm ngoài Git.
- Cả ba mô hình có tín hiệu cải thiện BSS ngày 1 khi thêm M. Informer E6 ngày 1/2/3 có BSS 0,284/0,062/0,004; điểm dương ngày 3 rất nhỏ, chưa tự khẳng định kỹ năng chắc chắn. Cả ba E7 ngày 3 vẫn BSS âm. CI mới: 20.000 bootstrap paired, khối 7/14 ngày, CI95% mô tả, chưa hiệu chỉnh nhiều phép, có điều kiện trên mô hình đã fit; giữ riêng phép thử TFT chính có CI điều chỉnh. Không đổi phân tích mới thành holdout hoặc coi chọn E đẹp nhất trên development là kết luận cuối.
- LightGBM là mô hình tham chiếu để so sánh, không bắt buộc TFT phải thắng; trọng tâm là đo đóng góp đặc trưng. Gộp sáu giờ vẫn là lựa chọn thiết kế chưa có đối chứng 1h/3h/6h. Footprint 93 toàn ô còn xấp xỉ, cần giao ranh và QC nhãn trước khóa/holdout.
- Người dùng đã đổi tên và chỉnh sửa slide 21/10 ở working tree; không phục hồi/ghi đè/commit hộ tệp này. Bản mới xuất riêng vào thư mục 28/10. Chỉ stage mã/tài liệu/kết quả tổng hợp thuộc công việc mới.

- **Quy ước trình bày (bản lịch sử 21/10):** mọi bảng xếp hạng mô hình phải đặt đủ LightGBM, TFT, Informer cạnh nhau cùng E/ngày/mẫu/nhãn/mùa/ngưỡng. [Bản 47 slide và Word](reports/short_range_three_models_2026_10_21/README.md) còn thiếu Informer E1–E6 ở thời điểm đó; bản 28/10 bên trên đã hoàn tất. Ví dụ công thức/hai quy tắc trong cùng mô hình và ablation trong TFT phải ghi rõ mục đích, không dùng chúng làm xếp hạng kiến trúc.

- **Quy trình Git đã được người dùng đồng ý:** phát triển trên `research/tft-regional`, commit/push mã và báo cáo lên nhánh đó, tạo PR vào `main`. `main` là bản tích hợp chung cho các nhánh nghiên cứu sau review. Dữ liệu/checkpoint ngoài Git; nhánh Bi-LSTM do thành viên khác phụ trách.
- Đã push commit đầu tiên `ad78de3`, mở [PR #1](https://github.com/nibsu05/PBL6/pull/1), chưa merge. Sau khi người dùng hỏi kết quả và cần báo cáo trong 30 phút, bổ sung [bản ngắn Word, 5 slide và lời trình bày 5 phút](reports/short_range_brief_2026_10_21/README.md) từ kết quả đã kiểm chứng. Không fit/chấm mô hình mới, không đổi dữ liệu hoặc mở 2025 trong bước tổng hợp này.
- Người dùng duyệt [kế hoạch đầy đủ/Word/protocol](reports/short_range_plan_2026_10_21/README.md) và yêu cầu ưu tiên kết quả trong 3–4 giờ để báo cáo ngày mai. Đã tạo nhánh `research/tft-regional`, triển khai loader/TFT vùng/baseline/đánh giá và hoàn thành [bộ pilot có Word, 7 slide, hình, CI](reports/short_range_pilot_2026_10_21/README.md). Không tự thay ma trận nhánh6h.
- Đề nghị V1 vùng, lịch sử168h gộp6h, ba tổng24h kết thúc tại24/48/72h; TFT+LightGBM E0–E7. Decoder chính chỉ biết lịch; không đưa ERA5 giờ đích. Informer/forecast thật/V2/app là tùy chọn ngoài ngân sách chính.
- Kiểm kê read-only2015–2023 được3.248issue ngày hợp lệ trên maskE7; F1/F2/F3 có train1.809/2.173/2.536issue. Không phân tích2025; verify nguồn2233/2233 lại đạt ngày21/10. Hai scriptinspect_short_range_plan/build_short_range_plan chỉ kiểm kê/xuất tài liệu, không phải pipeline huấn luyện.
- Pilot: E0/E7, 3 fold eval2021–2023, seed42; 6 lượt TFT và6pipeline LightGBM. 23 kiểm tra đạt (12 mới,11 verification),12/12 lượt checkpoint tái lập toàn bộ evaluation trên thiết bị gốc; CPU có trôi số học nhỏ được ghi riêng. Bootstrap paired7/14ngày,2.000lần là CI thăm dò, chưa hiệu chỉnh đa so sánh hoặc bất định seed. Không mở2025.
- BSS16 gộp E7 ngày1: LightGBM0,303/TFT0,220; ngày3:−0,075/−0,047. RMSE ngày1 E7:17,706/20,391mm/24h. ΔBSS E7−E0 ngày1: LightGBM+0,160 CI95%[+0,101;+0,223], TFT+0,088[+0,023;+0,156], khối7ngày. Không kết luận TFT thắng hoặc quy lợi ích riêng từng nhóm. Nhiều điểm chỉ là phát triển khám phá.
- **Mở rộng sau pilot:** người dùng hỏi còn thời gian làm gì tiếp; đã hoàn thành [E0–E7, ba seed, Word/8 slide/FAQ/danh mục 44 biến](reports/short_range_ablation_2026_10_21/README.md): 72 lượt TFT và 24 pipeline LightGBM trên footprint 93 ô xấp xỉ đã khóa. 27 kiểm tra đạt; 96/96 lượt tái lập cả calibration/evaluation; 12/12 seed 42 E0/E7 khớp pilot. Dữ liệu/checkpoint/dự báo từng dòng ngoài Git; giữ nguyên pilot và bốn module nguồn đã băm. Không phân tích hoặc chấm năm 2025.
- TFT ensemble ba seed: BSS E0 ngày 1/2/3 = 0,135/0,018/−0,034; E7 = 0,246/0,028/−0,038. Ngày 1, E1−E0 (thêm A) ΔBSS +0,085, CI99,44% [+0,002;+0,161]; E2−E0 (thêm M) +0,144 [+0,068;+0,233]. Đây là hai CI trên 0 trong gia đình 9 phép so đã khóa; cùng kết luận với khối 14 ngày. 20.000 bootstrap paired, reference lấy mẫu lại cùng nhãn/dự báo. Chưa có CI chính điều chỉnh trên 0 cho SST hoặc ngày 2–3; các năm development đã được xem trước, chưa là holdout độc lập.
- LightGBM ngày 1 BSS E4=0,315, E7=0,303: thêm hết biến chưa chắc có điểm tốt nhất. Không quy mọi chênh lệch TFT/LightGBM cho kiến trúc; còn khác biểu diễn/loss và số tham số tăng theo số biến. Nhóm C chỉ có SST vùng, không diễn giải thành ENSO/MJO đã được kiểm tra đầy đủ.
- **Yêu cầu giải thích đầy đủ tiếp theo ngày 21/10:** đã tạo [Word/Markdown và Excel 18 sheet](reports/short_range_explained_2026_10_21/README.md), có 48 dòng chính = 8 E × 2 họ × 3 ngày, bảng đủ 44 biến, chi tiết năm/mùa/seed/ngưỡng và ví dụ metrics. Đầu ra là ba tổng 24 giờ riêng [0,24), [24,48), [48,72), không phải từng giờ hoặc tổng tích lũy 48/72 giờ; một mẫu là cả vùng. Chỉ đọc aggregate đã kiểm chứng, không fit thêm hoặc mở 2025. Người dùng cần giải thích có chiều sâu, không chỉ gửi nhận xét ngắn hoặc link.
- **Sửa lý do chọn mô hình:** chọn TFT là giả thuyết thiết kế cho nhiều nhóm biến/nhiều hạn, chưa có bằng chứng thắng Informer cùng giao thức. Informer có time marks trong mã chính thức; R² cũ và benchmark khác không loại được nó cho mưa vùng. Bản TFT hiện là adaptation không có static context/phân vị, chỉ lịch tương lai. LightGBM là đối chứng học từ cùng nguyên liệu tóm tắt, không phải nguồn dữ liệu khác; phép so hiện chưa cô lập riêng kiến trúc. Tài liệu mới dẫn bài gốc và phân biệt nhận định áp dụng của dự án.
- **Bổ sung slide và phản biện POD/FAR theo yêu cầu 21/10:** [34 slide, HTML, lời dẫn/phân tích và nguồn](reports/short_range_presentation_2026_10_21/README.md): 24 slide chính + 10 phụ lục, đủ 48 dòng/7 metrics, số cần đọc được in đậm có chú thích, BSS âm màu đỏ. Cơ sở ứng dụng LightGBM: He et al. 2022 (mô hình lai, mưa ngày), Iwase/Takenawa 2024 (dự đoán tại điểm có forecast), Qian/Jia 2023 (hạn mùa, không bằng chứng 24–72h). Không trộn điểm paper vào dự án.
- **Sửa slide theo phản hồi tiếp theo:** [42 slide dễ hiểu hơn, Word và lời dẫn](reports/short_range_revised_2026_10_21/README.md), bảng đủ 8 metrics, bốn nhóm biến đầy đủ, giải thích ba seed so với ba ngày/ba năm, ví dụ POD 0,4 và hai cách ra quyết định. Không có căn cứ coi POD 0,4 là chuẩn tốt chung; phải xét ngưỡng mưa, hạn, vùng, FAR/CSI và baseline. E7 TFT ngày 1: quyết định xác suất cho POD 0,640 và FAR 0,475; quyết định lượng mm cho POD 0,588 và FAR 0,417. Đây là mô tả dự đoán đã khóa, không chọn lại ngưỡng trên tập đánh giá.
- **Informer được người dùng đề nghị thử trong 30 phút:** [pilot vùng 18 lượt và hồ sơ kiểm chứng](reports/informer_regional_pilot_2026_10_21/README.md), adaptation dùng cùng đầu vào, nhãn, mốc thời gian, loss/calibration và ba seed với TFT. Không sửa code Informer cũ hoặc kết quả cũ. Mã mới sửa số query ProbSparse theo mã chính thức và cố định lấy mẫu attention lúc eval; công khai khác biệt với bài gốc. Độc lập phát lại đủ 18 mô hình × calibration/evaluation và khớp bảng TFT gốc. Chỉ E0/E7, không tune, không mở test 2025; chưa kết luận thay TFT.
- Audit read-only dev `fe27756`: LOCAL/Tweedie notebook có POD/FAR nhưng early stopping dùng RMSE phần tử đầu ra giờ, chưa cộng tổng dù tên biến có 6h; nhóm xác suất evaluate notebook có BS/CSI_prob, chưa BSS trong hàm đó. Không nói toàn bộ dev/mã chưa push đều giống hai tệp này. Giữ protocol BSS16/CSI; POD/FAR cần báo cạnh CSI, cùng RMSE/MAE/Bias, chưa tự nâng một chỉ số lên duy nhất. E7 ngày1: TFT H/M/F=73/41/66, LightGBM=60/54/32; không chọn TFT chỉ vì POD cao. Đổi mục tiêu hoặc chọn ràng buộc POD/FAR phải khóa trước holdout, không đổi theo điểm đẹp.
- Dự toán 48–70 giờ công ban đầu là khung nghiên cứu đầy đủ, chưa phải thời gian đã làm. **Số đo ma trận 96 lượt:** fitting/save/calibration khoảng 27,7 phút, tiến trình khoảng 27,9 phút; thay dự trù GPU 8–30 giờ ban đầu bằng số đo thực. Nhiều seed/factorial đã có trên footprint xấp xỉ; bước tiếp là chốt ranh và kiểm chứng nhãn, chạy lại nếu dữ liệu đổi, sau khóa mới holdout. Chưa coi nghiên cứu đầy đủ đã hoàn tất. Người dùng chưa xác nhận giờ/ngày.

## Cấu hình sản phẩm trước đây (lịch sử, không thay định hướng trên)

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
5. **TFT là kiến trúc thử nghiệm chính nhánh ngày**, rà soát lại lý do 21/10/2026:
   - Đã đủ Informer E0–E7 × ba năm × ba seed (72 lượt), độc lập phát lại đủ checkpoint. Bổ sung 54 lượt ngày 28/10, giữ nguyên pilot E0/E7. Có CI chênh lệch mô tả với TFT/LightGBM, chưa tuning hoặc kiểm định cuối. Benchmark khác và R² cũ 0,04 không loại được Informer; không kết luận chọn kiến trúc từ điểm đơn lẻ.
   - Informer có time marks; không nói hoàn toàn không nhận thông tin tương lai đã biết. Ưu thế tính toán chuỗi dài của nó chưa phải nút thắt rõ ở encoder 28 bước hiện tại.
   - TFT gốc có lựa chọn biến/gating và thiết kế nhiều hạn, là lý do để thử; chưa bảo đảm dự đoán tốt hơn. Bản vùng tự cài PyTorch giữ VSN/GRN/LSTM/attention, bỏ static context, dùng Tweedie/BCE, chưa xuất phân vị và chưa dùng forecast thật.
   - Đối chứng đang có: LightGBM, khí hậu, luôn 0 và Informer vùng đủ E0–E7. Bảng xếp hạng phải có đủ LightGBM/TFT/Informer. Cùng nguyên liệu nhưng cây và mạng khác biểu diễn, chưa là phép so chỉ đổi kiến trúc. ECMWF/DLinear trên giao thức vùng này chưa được chấm, không gọi là đã chạy.
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
