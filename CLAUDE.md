# PBL6 — bối cảnh hiện hành cho agent

Cập nhật 10/11/2026. Đọc file này trước, rồi `KE_HOACH_DU_AN.md` và `project_plan_v2.md`. Người dùng bắt đầu từ `README.md`.

## Nhận xét độc lập mới — đọc kèm slide

Người dùng yêu cầu đánh giá kết quả và đối chiếu nghiên cứu gần đây. Đã đọc nguồn gốc 2024–2026 và bổ sung **chẩn đoán hậu nghiệm trên dev**, không train hoặc mở 2025: `reports/gfs_station_review_2026_11_10/NHAN_XET_DOC_LAP.md`, `diagnostics.json`, `diagnostic_metrics.csv`; tái tạo bằng `scripts/review_gfs_station_results.py`.

Phát hiện quan trọng: **luôn dự báo 0 mm có macro MAE 5,887/6,887/7,773**, nên ngày 3 cả A2/A3/GRU chưa vượt đối chứng này về MAE ở mức điểm. Tỷ lệ mẫu <1 mm khoảng 72,0%/66,6%/63,2%. Điều này không biến 0 mm thành dự báo hữu ích: GRU ngày 3 RMSE17,62 tốt hơn ZERO22,89/khí hậu19,98/GFS26,73. Trên riêng 114 mẫu thực tế ≥50mm ngày3 (12 issue), **micro MAE GFS76,44; A2 90,00; GRU60,10mm**. Đây là chẩn đoán có điều kiện theo y, không phải cách chọn mô hình vận hành, chưa có CI. A2 giảm MAE toàn tập nhưng còn yếu mưa lớn; không chỉ dẫn mức giảm18,1% MAE so GFS để kết luận thành công.

Bộ slide đã gửi và kết quả đóng băng giữ nguyên; slide chưa có ZERO, cần dùng kèm nhận xét mới. Chưa có chứng cứ vượt nghiên cứu khác vì khác miền/nhãn/hạn/split. Dùng trạm, mô hình chung, LightGBM/GRU và thêm biến chưa tự tạo phương pháp mới; cần đối chứng cùng nguyên liệu khí tượng/địa hình để đo lợi ích của dẫn xuất vật lý, lịch hằng ngày, kiểm tra xác suất và kiểm định cuối. Không suy ra lỗi dataset hay overfitting chỉ từ các điểm mới.

## Slide báo cáo 57 trạm — yêu cầu mới nhất

Người dùng yêu cầu slide đầy đủ về đầu vào/đầu ra, chia dữ liệu, tinh chỉnh và kết quả. Bộ riêng `reports/gfs_station_slides_2026_11_10/`: `PBL6_DU_BAO_MUA_57_TRAM.pptx`/HTML, 43 slide chính + 12 phụ lục, ghi chú tiếng Việt trong PPTX và `GHI_CHU_THUYET_TRINH.md`. Hướng dẫn và lộ trình trình bày ở README cùng thư mục. PDF native PowerPoint ở private `data/operational/gfs_station_slides_2026_11_10/`, không commit PDF.

Không train mới để làm slide, không mở 2025. Đối chiếu checkpoint cho thấy LightGBM dừng sớm theo **l1/MAE cal** (metric đầu, `first_metric_only=True`), không phải Tweedie; best 62–177 cây. GRU dừng theo loss chung cal. Tham số pilot cố định; chưa GridSearch/Optuna. Script build/render/validate có tiền tố `gfs_station_slides`, ghi chú riêng `scripts/gfs_station_slide_notes.py`; không chạy builder của hai deck người dùng đã sửa.

Audit bổ sung từ dự báo đã lưu: chưa ràng buộc P(≥50)≤P(≥1). A2 vi phạm 188/8.346 dòng dev (2,25%), gap tối đa ~0,087; không có quyết định mâu thuẫn tại p≥0,5. A0/A1/A3 cũng có vi phạm; GRU không có trường hợp quan sát được nhưng mã cũng chưa ép thứ tự. `training_audit.json` trong thư mục slide có tổng hợp. Không sửa dự báo/điểm pilot; đề xuất giải quyết bằng protocol mới. Kiểm tra slide không chứng nhận kỹ năng cuối hoặc cảm biến.

## Mở rộng trạm mới nhất — đã thực hiện

Người dùng hỏi **“có thể mở rộng số lượng trạm được không”**. Đã mở rộng nhánh NWP từ20lên**57trạm**, thêm37trạm trong nguồn hiện có, giữ đúng tiêu chuẩn train>=365ngày đầy đủ và>=30ngày>=1mm.57trạm thực tế479–728ngàytrain;2trạm có<30cửa sổ tuầntrain (min18), cần báo giới hạn.

- 79trạm có cửa sổ train theo lịch tuần, nhưng22trạm ngoài57có lịch sử ngắn; chưa train79.3trạm lịch sử chưa có train và4vịtrí hiện hành chưa có lịch sử cũ. Không ép đủ86.
- Dataset57có5.032/2.582/2.782mẫu train/cal/dev, tổng31.188hàng3hạn. Lịch vẫn208issue mỗi7ngày.2025kín,2026khôngtuning. NguồnGFSđã trích82vịtrí dùng lại; chỉ tải một sốmessageđểreplay.
- ĐãtrainLightGBM A0–A3ba seed vàGRU_A2ba seed (gatecalqua ngày3), cùnghyperparameterscũ. Dataset/source/modelverificationđạt;53testsđạt (6testmới vềpathisolation vàmatchedcohort).
- Kết quả57trạm devmacroMAE: GFS5,83/7,41/10,30mm; A2 5,28/6,72/8,44; GRU_A2 6,94/7,56/8,00. Không so trực tiếp với trung bình20trạm.
- Đãso cùng20trạm/cùngissue/nhãn/32đầu vào: A2train20=6,15/7,37/7,75; A2train57=5,91/7,40/8,66mm. Ngày1tốt lên,ngày2gầnngang,ngày3điểm xấu hơn;CI cả3chứa0. Mở rộng phạm vi không bảo đảm tăngđộchínhxác. So sánh mở rộng cảtrain/cal, không chỉtrain.
- Bản20được giữ nguyên. Bản57 riêng `reports/gfs_station_57_2026_11_10/BAO_CAO_MO_RONG.md` vàWord; protocol/result_summary/cohort_scope_metrics/matched_original20_bootstrap cùngthưmục. Datasetprivate `data/processed/gfs_station_57_2026_11_10/gfs_vrain_pilot.parquet`; model/predsprivate thưmụcoperationalcùngtên.
- Scriptprepare `scripts/prepare_gfs_station_expansion.py`; các bướcbuild/validate/run/GRU/verify dùngenv `PBL6_GFS_EXPERIMENT=gfs_station_57_2026_11_10`. `src/gfs_experiment.py` tách output khỏi nguồncache20chỉđọc. Publish `scripts/publish_gfs_station_expansion.py`. Không sửa cohort/protocol đãfit; phiênbảnmớinếuđổitiêuchí.

## Hướng ngắn hạn mới được người dùng duyệt 10/11/2026

Người dùng yêu cầu đánh giá độc lập với hướng cũ, rồi nói **“ok hãy tiến hành thực hiện”** với phương án NWP + Vrain. Nhánh ngắn hạn ưu tiên **hậu xử lý GFS để dự báo ba tổng24h tại trạm**, LightGBM chính và GRU nhỏ theo điều kiện pilot. TFT/Informer không còn là bộ ba bắt buộc. Nghiên cứu giá trị đầu vào mưa trạm/khí tượng dự báo/địa hình; chưa làm app. Chi tiết: `docs/short_range_nwp_design.md`.

- GFS00UTC, issue12UTC=19hVN; hiệu tổng0–12/36/60/84h tạo ba cửa sổ19–19h. Khí tượngGFS+24/+48/+72h là ba trạng thái giữa cửa sổ, không phải trung bình ngày.
- Bản dự báo phải có trước issue theo giả định trễGFS8h và margin12h; chưa chứng minh thời điểm công bố lịch sử từng file. Trễtrạmgiảđịnh1h: summary1/6/24h kết thúc18h, bảy ngày đầy đủ kết thúc hôm trước; không dùng số đo19h ngay tại issue.
- Pilot mỗi7ngày trong2021–2024,208issue, khác thí nghiệm hằng ngày đầy đủ. Chọn20trạm từ57ứng viên chỉ theo train2021–22 và địa lý/DEM; mỗi trạm565–728ngày train hợp lệ. Không chọn ngày/trạm theo điểmdev hoặc mưa cực đoan quan sát.
- A0=mưaGFS+lịch+vịtrí/ID; A1 thêm lịch sửVrain; A2 thêm T/RH/gió850/PWAT vàproxyẩm; A3 thêmDEM/slope/tươngtácgió. MọiA cùng mẫu. Q850 tính từT/RH cùngcôngthức vì đầu2021thiếuSPFH trong sản phẩm thườngdùng.
- DEMMapzen là proxy tại tọa độ hiện có, không phải cao độ đo tại trạm; gió·gradientđịa hình/ẩm là giả thuyết, không chứng minh nhân quả.
- Protocol khóa trướcfit ở `reports/gfs_station_pilot_2026_11_10/protocol.json`; audit/verification/kết quả cùngthưmục. Private ở `data/operational/gfs_station_pilot_2026_11_10/`, `data/processed/gfs_station_pilot/`.
- Collector `scripts/collect_gfs_station_pilot.py`: HTTPbyte-range,206/Content-Range, GRIBinit/lead/interval/unit, resume/SHA; đọcprogress/PIDthật. Windows ecCodes phải giải mã tuần tự quaLock, chỉ HTTP chạy song song. Optionalenv `requirements-nwp.txt`.
- Ba seed17/29/43. GRU_A2chỉ chạy khi gatecal: A2macroMAE thấp hơn cảGFS/khíhậu và>=50%trạm cải thiện soGFS ở ít nhất một hạn. Không dùngdev để quyếtđịnhgate. Cal/earlystop2023,dev2024chưa làtestcuối;2025kín,2026khôngfit/tuning.
- BộVrain–ERA5v1 và Bi-LSTM cựcngắn giữ phạmvi riêng. “Đã ghép/train được” không chứng minh khả dụngrealtime hoặc kỹnăng1–3ngày. Không gắnNWPpilot thànhthínghiệmhằngngàyđầyđủ.

**Trạng thái sau triển khai:** NWPpilot đã hoàn thành208/208issue,20trạm,10.977hàng/3.659mẫu trạm–issue. Train/cal/dev=1.774/902/983mẫu, mỗi mẫu ba nhãn. Đãfit36estimatorlượng và72classifierLightGBM chính, GRU_A2ba seed7001tham số trênCUDA; không trainTFT/Informer. 47testsđạt; replay10.977hàng và171mẫu nội suyGRIB, replay36+72estimators vàbaGRUCPU, scalertrain-only/metricđạt.

Trên dev2024, macroMAE GFS=6,40/8,13/10,27mm; A2=6,15/7,37/7,75; GRU_A2=7,81/8,35/8,46. **CI A2−GFS cả ba hạn chứa0**, không khẳng định cải thiện ổn định dù ngày3giảmđiểmkhoảng24%. GRU có MAE cao hơn nhưng RMSEngày3 thấp hơn A2 (18,31so20,17mm); không kết luậnGRUkémmọimặt. A3chưa có lợi ích rõ; BSSkhông cải thiện đồng đều. GateGRU chỉqua ngày3cal với chênhnhỏ; không dùngdevchọngate.

AuditLast-Modified3952messages:7chu kỳ đầu2021có timestamp sửa/chéparchive sauissue, không ởcal/dev. Không suy ra phát hànhgốc muộn. Đã chạy thêmA2ba seed bỏ7chu kỳ train; devMAE6,09/7,42/7,88mm, hướng tương tự. Xemrelease_timestamp_audit.json/release_sensitivity_metrics.csv. Chưa chứng minh độtrễvậnhànhthật.

Điểmvào kếtquả: `reports/gfs_station_pilot_2026_11_10/BAO_CAO_PILOT.md`, Wordcùngtên, `result_summary.json`. Datasetprivate `data/processed/gfs_station_pilot/gfs_vrain_pilot.parquet`. Côngviệctiếpđểkiểmchứng: protocolphiênbảnmới lịch hằng ngày/lag sensitivity/drop-group; không đổi pilot cũ hoặc mở2025tùy tiện.

## Quyết định mới nhất của người dùng — đã chốt

**Chuyển cả hai nhánh sang dự báo lượng mưa tại trạm.** Người dùng nói: “nhóm tôi thực hiện dự đoán cực ngắn và ngắn theo trạm”. Quyết định này thay mục tiêu dự báo trực tiếp mưa trung bình diện tích toàn Đà Nẵng trước đây. Không tự đưa mục tiêu vùng trở lại hoặc ưu tiên app.

- Thành viên khác: Bi-LSTM, sáu lượng mưa giờ tiếp theo tại từng trạm, 1–6h.
- Người dùng: ba tổng24h riêng tại trạm; **phương án mới NWP+LightGBM/GRU ở đầu file** thay bộbaTFT/Informer bắt buộc trước đây.
- Đề xuất kỹ thuật: mỗi kiến trúc học một mô hình chung cho nhiều trạm; một mẫu là `(station_id, issue_time)`. Không cần 86 mô hình riêng cho một kiến trúc.
- Nhãn là mưa Vrain tại chính trạm. Người dùng đã xác nhận: **10:00 = tổng mưa09:00–10:00 giờ Việt Nam, UTC+7**. Đơn vị hiển thị nguồn là mm. Không còn chờ xác nhận timezone hoặc nhãn vùng.

## Phạm vi và số trạm

86 là danh mục **nhóm “Đà Nẵng” mà tài khoản được truy cập**, không phải toàn Việt Nam. Chưa chứng nhận mọi mục nằm đúng ranh hành chính cuối; lọc theo tọa độ/ranh khi chốt tập trạm nếu cần. Không gọi danh mục là phủ kín diện tích hoặc cả đảo.

- Kênh cũ có 82 vị trí, kênh hiện hành 86. 82 cặp tọa độ khớp chính xác/duy nhất, 81 tên giống và một tên khác; bốn vị trí bổ sung. Chưa biết thời điểm lắp đặt bốn trạm đó.
- Registry private 86 mã STxxx + alias hai kênh; giữ mã v1 khi thêm trạm sau này. Khớp metadata không chứng minh số đo hai kênh tương đương.
- Trong kho cũ, trạm có ít nhất một số giờ sau QC: 2021 **57**, 2022 **79**, 2023 **79**, 2024 **82**. Không đồng nghĩa đủ cả năm. Không mặc định cả 86 có lịch sử từ 2021 hoặc đã được chọn train.
- Bản dataset trạm v1 có82trạm lịch sử;79trạm có cửa sổ train hợp lệ cho cả hai nhánh, ba trạm còn lại không vào đánh giá mặc định. Đây là điều kiện cấu trúc, chưa chứng nhận cảm biến;24trạm có dưới180mẫu ngày train. Pilot một nhóm đại diện trước; thiếu tại trạm A không loại mẫu hợp lệ của B.

## Nguồn đã có và trạng thái

Private base `data/operational/vrain_2026_11_09/`:

- `download/`: 3.653 response 2015–2024, SHA gzip/raw đạt; có bảng giờ cho 1.461 ngày 2021–2024; 2015–2020 không trả giờ, không phải ngày khô. Ba station-day chênh tổng đã gắn cờ, số gốc được giữ.
- `recent_archive/`: 622 response cho 02/01–08/11/2026, 311 ngày × hai kênh. Bỏ 01/01 vì cửa sổ có giờ 2025. Có số ở 87 ngày kênh cũ, 305 ngày kênh mới; số hàng không bằng số đo hợp lệ.
- `handoff_v1/`, `PBL6_VRAIN_SOURCE_V1.zip`: nguồn/registry/QC, **không phải tập train theo trạm đã dựng**. Predictor 44 kênh trong ZIP vẫn là trung bình vùng cũ; không đổi tên hoặc nhân bản thành đầu vào theo trạm. Có 21 hàng thiếu kx/tt (42 ô), giữ NaN.
- `freeze_work/station_matrices.npz`: ma trận giờ nguồn 2021–2024, mask/QC; clock là cuối khoảng giờ Việt Nam, theo xác nhận mới. Không sửa file nguồn vì metadata cũ; áp dụng contract khi dựng dataset mới.
- Hai kênh chỉ trùng số ở một vị trí/18 ngày/367 cặp, 46 cặp có mưa đều khác số. Không tự nối nguồn 2026 hoặc fit/tuning 2026.

**Bộ trạm đã dựng và kiểm tra:** `data/processed/station_v1/PBL6_TRAM_GIO_NGAY_V1.parquet`, một file chứa1h/24h, raw/QC, X/y và chỉ số sample-ready; ngoàiGit. Tài liệu ngắn gửi nhóm: `reports/station_data_handoff_2026_11_09/MO_TA_DU_LIEU.docx`. Kỹ thuật: `HUONG_DAN_TRAIN.md`, `dataset_summary.json`, `verification.json` cùng thư mục báo cáo.

**ERA5 gốc vẫn có tại `data/raw_data/gee/era5/grid/*.parquet`.** Builder mới nội suy trực tiếp từ bốn nút0,25° quanh trạm; tất cả82trạm lịch sử có nút bao quanh. Không dùng đường vòng93ô hoặc sao chép mean vùng. Yêu cầu đủ mọi nút có trọng số dương; giữNaN nếu thiếu. Context/SST/chênháp có miền vùng có chủ đích. Không dùng các cột mưa ERA5/GSMaP làm X/y. CubeR93 và bộ vùng cũ giữ làm lịch sử.

Kiểm traERA5v1đạt2.995.050hàng/2.480.367cửa sổ,45đốichiếutrườngERA5,328sốmưagốc,72mẫuqua loader;34testsởbảnđó. ChưatrainbằngbộERA5v1; NWPpilot10/11đãtrainriêngnhưđầu file. Đây là kiểm tra cấu trúc, chưa chứng nhận cảm biến/vịtrílịchsử/độtrễ.

## Hợp đồng thời gian và nghiên cứu

- Người dùng xác nhận10:00là mưa09–10hViệtNam. Chuẩn hóa `period_start_utc=02:00`, `period_end_utc=03:00`; ERA5tức thời lấy02:00UTC. Clock20:00hômtrước→19:00ngàyđánhdấu tạo ngày19:00→19:00, không phải00–24. Không dùng tiêu đề XLSX19:20 để đổi các bin giờ đã xác nhận.
- Lưu mưa theo khoảng đo, provenance, QC; không đổi thiếu thành0, không chia mưa ngày thành giờ, không lấp y bằng ERA5/CPC/GSMaP.
- B/A/M/C đã dựng theo trạm: giờ11/12/20/1, ngày9/12/20/1. E7=44/42kênh; thêmR=45/43. Statictọađộ2kênh+IDđi riêng, cùng cách dùng giữa cácE. C chỉSST, chưa phảiENSO/MJO.
- BộERA5v1: Rlà mưa quákhứchínhtrạm, maskchungkhiablation, chỉlịchtươnglaiđãbiết. **BộNWP mới được dùng khí tượng/mưa GFS dự báo kỳ đích từ bản khởi tạo trướcissue; cấm số thực đo hoặcERA5kỳđích trongX.**
- Split theo thời gian chung cho mọi trạm, toàn bộ nhãn nằm trong split. Fit scaler/reference trên train; earlystop/calibration/tau trên cal. Không random cửa sổ lẫn trạm/ngày.
- Bảnv1: train2021–22, cal2023, dev2024 theo giờ Việt Nam;2024chưa phải testcuối. Mask `sample_ready_r1` dùng chung mọiE/model/R0–R1. Loader `src/station_forecast_data.py` giữ mọi hàng thời gian trước chọn issue; không dropNaNrồi cắtchuỗi. Chưafit bất kỳ scaler nào.
- **2025 giữ kín.** Không tuning2026 rồi gọi2025 là test tương lai. Không đổi tên kết quả vùng cũ thành kết quả trạm; NWPpilotđãtrainriêng, ERA5v1chưatrain.
- Báo metric từng trạm và macro-average, kèm micro nếu cần; bootstrap theo khối thời gian giữ đồng thời các trạm. Không coi các trạm trong cùng trận mưa là mẫu khí hậu độc lập.
- Ngưỡng mưa/POD/FAR phải chốt phù hợp trạm và kỳ giờ/ngày; không tự mang ngưỡng vùng16/50/100 sang. Không có POD0,4 tốt chung. ERA5 hồi cứu chưa chứng minh có sẵn tại issue vận hành.

## Quy ước làm việc và an toàn dữ liệu

- Tiếng Việt, đánh giá độc lập và trung thực kể cả kết quả âm.
- Workspace `D:\PBL6_v2`; Python `.venv\Scripts\python.exe -X utf8`; RTX4060Laptop8GB. Python inline qua PowerShell dùng ASCII; nguồn tiếng Việt dùng UTF-8/apply_patch.
- Git `git -c safe.directory=D:/PBL6_v2`, nhánh `research/tft-regional`; đã được phép push/cập nhật PR#1, không tự merge main.
- Repo công khai: không commit raw/PDF, registry/tọa độ từng trạm, credential/cookie, checkpoint hoặc dự đoán từng mốc. Dữ liệu nguồn cũ từ Drive `pbl6_data_v2_*.tar`, kiểm bằng `scripts/package_data.py verify`; Vrain có manifest riêng.
- Vrain login `https://www.vrain.vn/landing`; không nhắc lại mật khẩu, không lưu vào nguồn. Phiên mã hóa DPAPI ở `download/session.dpapi`. Kênh cũ `/api/vrain/private/v1/groups/29/stats/details`; mới `/api/kttv/private/v1/organizations/details`, ngữ cảnh tổ chức từ group đã xác thực, không đoán UUID.
- Tải nền dùng Start-Process `WindowStyle Hidden`, resume/checksum; đọc progress/PID thật trước nói tiến độ.

Giữ nguyên, không restore/build/stage hai slide người dùng sửa: `reports/daily_gauge_slides_2026_11_04/PBL6_DU_LIEU_NGAY_3_MO_HINH.pptx` và bản đổi tên `reports/short_range_three_models_2026_10_21/Dự đoán ngắn hạn 21_10.pptx` (bản tên gốc đã bị người dùng xóa). SnapshotSHA `data/operational/workspace_cleanup_2026_11_09/user_files.json`.

## Bằng chứng lịch sử, không phải mục tiêu hiện tại

- `reports/vrain_data_handoff_2026_11_09/DANH_GIA_KHA_THI_VA_HUONG_DI.md`: kiểm định nhãn vùng trước khi người dùng chốt theo trạm. 67 ngày tham chiếu nội bộ, NRMSE Thiessen toàn R93 16,3–21,4%, nhóm núi60–71%; không phải sai số dự báo hay chân lý diện tích.
- `reports/daily_gauge_2026_11_04/`: CPC168fits,144checkpointNN/288đầu ra cây/336split; chưa là Vrain hoặc theo trạm.
- `reports/short_range_complete_2026_10_28/`: GSMaP ba mô hình, giữ nguyên nguồn/kết quả.
- `reports/regional_research_plan_2026_10_20/PHUONG_AN_CUOI.md`: các quyết định có bằng chứng giữ đúng phạm vi cũ; không tự phủ nhận số đo cũ vì đổi mục tiêu.
- Dọn tài liệu09/11 đã được phép, có ZIPprivate/Git a05f6c0, `docs/cleanup_2026_11_09.json`. Không xóa bằng chứng thí nghiệm.
- Dataset/loaderERA5v1có34tests và kiểmtra toànfile; chưatrainv1. NWPpilotđãtrainnhưđầu file. Scriptsv1: `build_station_forecast_data.py`, `validate_station_forecast_data.py`, `publish_station_data_handoff.py`. Không đổi số đo vùng cũ thành kết quả trạm.
