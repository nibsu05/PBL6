# Các phép thử tiếp theo tại Đà Nẵng

Đóng băng ngày13/10/2026 trước chạy. Chỉ validation2021–2023; test2025 giữ kín. Tái dùng source domain_screen_danang,30ô train, index30000mẫu và normalizer/Platt đã lưu. Các kết quả mới vẫn là khám phá lịch sử.

## Amount

RAW LightGBM Tweedie p=1,5 trên mm,6 đầu giờ;100cây,15lá,max_bin63,min_child50,learning_rate0,05,seed42,4luồng deterministic. Mọi tham số cây/cửa sổ đúng baselineL1log; chỉ thay objective và thangtarget. Đầu sự kiện/xác suất giữ nguyên baselineLightGBM_RAW.

Chính: RMSE3h tháng5–10 và bias; phụ CSI lượngmưa≥10, sai số trên những cửa sổ nhãn≥10/25. Đối chứngL1log vàNN_RAW đều có sẵn, không chỉnh mô hình sau xem năm eval. Mốc thực dụng đề xuất: RMSE giảm≥5% ít nhất2/3năm soL1log, xétCI và bias/sự kiện lớn. GiảmRMSE chưa đảm bảo lượngmưa hay xácsuất tốt mọi khía cạnh.

## Terrain

NO_TERRAIN = DOMAIN chuẩn hóa gốc, cột ne_terrain_index trở thành0 sau chuẩn hóa. Còn ba proxy và toàn bộ raw/static giữ nguyên; nên raw ne_upslope vẫn có. NN174.154tham số, khởi tạo/seed42/43/44, optimizer/loss/batch256/15epoch/patience4, thứ tựtrain vàcal_subset đúng run gốc. Không fit lại normalizer.

FULL−NO_TERRAIN đo giá trị việc trình bày tương tác gió–ẩm×địa hình, không đo việc thêm DEM vào dữ liệu. CSI quyết định≥10/3h vàBSS≥1, CI5ngày1000lần. Chưa gán mọi lợi ích của FULL cho địa hình nếu không có tín hiệu bỏ thành phần lặp theo năm.

## Spatial

63ô bổ sung không có trong30ô train/calidation của domain run. Chỉ suy luận RAW/DOMAIN seed42/43/44; không học lại,không đổi chuẩn hóa/Platt/ngưỡng. Cửa sổ hợp lệ chung theoRAW; tau lấy từcal30ô. Climatologytham chiếu dùng nhãn quá khứ tại63ô, được ghi rõ là một baseline có thông tin tại địa phương; không truyền nhãn đó vàoNN/hiệu chỉnh.

Đây là kiểm tra nội suy sang ô chưa fit của chính checkpoint; chưa là test độc lập giữa các tỉnh hoặc thí nghiệm không gian có vùng đệm. Các ô/đợt mưa tương quan và lịch sử đã dùng trong các khảo sát trước. Phụ:coast≤20km vs>20km, đặt trước. Bootstrap theo ngày gom mọi ô.

## Tái lập

    .venv\Scripts\python.exe scripts\followup_danang.py --task amount
    .venv\Scripts\python.exe scripts\followup_danang.py --task terrain
    .venv\Scripts\python.exe scripts\followup_danang.py --task spatial

Model/pred/index ởdata/operational/followup_danang ngoàiGit. Số liệu theo task ởreports/followup_danang. run.json có sourcecommit/sourcehash/history/completed; chỉ gọi xong khi completed=true. Không sửa output/checkpoint run gốc.
## Mở rộng có điều kiện sau kết quả amount

Tweedie LightGBM đã giảm RMSE trên cả3năm soL1log, nên thử Bi-LSTM RAW giữ nguyên174.154tham số/seed/ngân sách. Softplus được diễn giải là meanmm/h thay vìlog1p; hồi quy bằng devianceTweedie p1,5, chia cho deviance của forecast meanhằng tính trên chính30.000mẫu train. BCE không trọng số lớp giữ hệ số1. Encoder học chung nên đầu xácsuất có thể đổi và phải hiệu chỉnh lại trên nămcal cũ.

Đây là mở rộng khám phá sau nhìn kết quảLightGBM, không là xác nhận độc lập. Script train_bilstm_tweedie.py; các artifact gốc giữ nguyên. Chính:RMSE3h/bias/sự kiệnmưa; kiểm traBSS/CSIprob để không đánh đổi đầu xácsuất vô thức. Không chọn giá trịp/scale bằng năm evaluation.

## Độ trễ quan trắc và mô hình lag5

Sau 24 file NRT và hai audit as-of, đã stress checkpoint lag4 và train lại Bi-LSTM RAW Tweedie lag5 với cùng30ô/index/3seed/3fold. RMSE lượng mưa3h của bản retrain lag5 tăng nhỏ nhưng CI hiệu số dương cả3 năm; BSS≥1 giảm mô tả cả3, CSI xác suất≥10 chưa phân biệt chắc. Bảng đầy đủ và giới hạn ở [`bilstm_tweedie_lag5/README.md`](bilstm_tweedie_lag5/README.md). Không dùng dữ liệu backfill để suy latency JAXA hay phát AI live. `scripts/watch_gsmap_nrt.py` đã test bằng FTP giả; khi người dùng chạy trong terminal, script chỉ đo file raw mới sau baseline, poll10phút và ghi manifest riêng tư không có credential. Chưa có số đo file mới từ watcher thật.

## Kết quả và quyết định tạm thời 13/10/2026

| Năm | RMSE LightGBM RAW L1(log) → Tweedie | RMSE Bi-LSTM RAW log-Huber → Tweedie | CSI lượng mưa ≥10 Bi-LSTM cũ → Tweedie |
| --- | ---: | ---: | ---: |
| 2021 | 4,607 → 3,947 | 4,046 → 3,876 | 0,191 → 0,289 |
| 2022 | 4,841 → 4,534 | 4,661 → 4,581 | 0,164 → 0,272 |
| 2023 | 4,205 → 3,610 | 3,963 → 3,540 | 0,092 → 0,391 |

Đơn vị RMSE là mm/3 h; tất cả là mùa 5–10, cùng 30 ô và mẫu theo năm. CI bootstrap RMSE LightGBM Tweedie−L1(log) dưới 0 cả ba năm; Bi-LSTM Tweedie−cũ dưới 0 năm 2021 và 2023, chứa 0 năm 2022. Đầu xác suất Bi-LSTM Tweedie kém ở 2022: BSS ≥1 là 0,148 so 0,186. Không tuyên bố một cấu hình thắng mọi chỉ số.

Bỏ `ne_terrain_index` làm CSI xác suất của DOMAIN giảm mô tả 0,025/0,009/0,051 theo năm, nhưng CI của từng hiệu số chứa 0. Trên 63 ô chưa train, DOMAIN−RAW là +0,042/−0,003/+0,029, CI đều chứa 0. 63 ô vẫn ở cùng Đà Nẵng và có tương quan thời tiết; chưa là kiểm tra tỉnh khác. Điểm ngoại suy tỉnh hoặc ưu thế domain chưa được chứng minh.

Demo archive dùng checkpoint thật trên 93 ô; 36 phép so dự báo HTTP và 83 kiểm tra code đạt. JAXA FTP đã xác minh login và tải raw/Gauge_NRT v8 10 UTC ngày 13/10. SHA-256 và shape 1200×3600 khớp; raw có 93/93 ô hữu hạn, Gauge cũng vậy. Hai binary tương quan 0,998 trên 93 ô, nhưng popup web lệch cả hai ở 3/3 ô có mưa; nguyên nhân chưa rõ. Chi tiết tổng hợp ở `jaxa_binary_audit.json`, tệp/giá trị từng ô ở `data/operational/` ngoài Git. `scripts/fetch_gsmap_nrt.py` chỉ dùng FTP thường khi có `--allow-plain-ftp`; credential nhập ở terminal và không lưu. `scripts/ingest_gsmap_nrt.py --fetch-manifest` kiểm hash/URI/giờ tải, vẫn đánh dấu `ready_for_ml=false`. Đã tải 24 giờ NRT raw liên tục và kiểm 93/93 ô hữu hạn; lag4/issue16 có 21/24 tệp kịp máy nhận, lag5/issue17 thử có 24/24 (xem `nrt_latency_sensitivity.json`). Tải backlog không chứng thực giờ JAXA công bố; model lag5 chưa train/đánh giá. Cần logger liên tục để đo latency nhiều ngày, kiểm tra nguồn train→live và ECMWF T-OPS cùng mẫu trước AI live; test 2025 giữ kín.
