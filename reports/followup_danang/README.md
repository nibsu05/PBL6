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
