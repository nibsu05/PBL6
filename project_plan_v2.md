# Thiết kế nghiên cứu — dự báo mưa tại nhiều trạm

**Bản mở rộng hiện hành:**57trạm, giữtiêuchítraincủapilot, lịch7ngày và thiết lập môhình. [Báo cáo/phạmvi57](reports/gfs_station_57_2026_11_10/BAO_CAO_MO_RONG.md).20trạm là pilottrướcđó; chưatrain79hoặc86trạm. So sánh kết quả mởrộng trên đúngcohort/timecũ để tránh nhầm thay đổi độkhótậptrạm thànhskill.

**Phương án ngắn hạn hiện hành được duyệt10/11/2026: [GFS + Vrain, LightGBM/GRU](docs/short_range_nwp_design.md).** Protocol khóa trướcfit: `reports/gfs_station_pilot_2026_11_10/protocol.json`. Câu hỏi nghiên cứu là giá trị lịch sửmưa/khítượngdựbáo/địaphương cho ba tổng24h tại trạm; không bắt buộc TFT/Informer.

Phần dưới ghi thiết kế và giới hạn **bộVrain–ERA5v1 đã bàn giao09/11**. Giữ để diễn giải nguồn và hỗ trợ nhánh cực ngắn; không coi là thiết kếNWPmới hay bằng chứng khả dụng realtime.

Người dùng đã chốt09/11/2026: cả hai nhánh dự báo theo trạm. Tài liệu này thay thiết kế dự báo trực tiếp mưa trung bình vùng trước đó. Đây là thiết kế để triển khai; chưa có kết quả train Vrain theo trạm.

## 1. Phạm vi: 86 là danh mục ứng viên ở nhóm Đà Nẵng

API trả một nhóm tên “Đà Nẵng” với86 vị trí hiện hành; không phải toàn quốc. Chưa khẳng định mọi mục đã được đối chiếu với ranh hành chính cuối. Khi cần chọn trạm thuộc đúng khu vực, kiểm tra tọa độ/ranh trước chốt tập.

Registry86 gồm82 vị trí có alias kênh cũ và bốn vị trí bổ sung. Chưa biết bốn vị trí được lắp mới hay bổ sung vào danh mục. Mã chuẩn STxxx giữ cố định, alias kênh lưu riêng. Chỉ khớp tọa độ hiện tại, chưa chứng minh số đo hai kênh liên tục/tương đương.

| Kho lịch sử đã tải | Trạm có ít nhất một số đo giờ sauQC |
| --- | ---: |
| 2021 | 57 |
| 2022 | 79 |
| 2023 | 79 |
| 2024 | 82 |

Đây không phải số trạm đủ cả năm. **Datasettrạmv1đãdựng:82trạm lịch sử,79trạm có cửa sổ train cho cả hai nhánh.** Ba trạm chưa có train bị loại khỏi đánh giá mặc định; bốn vị trí chỉ có trong danh mục mới không có lịch sử tự tạo.79là đủ điều kiện cấu trúc, chưa chứng nhận cảm biến;24trạm có dưới180mẫu ngày train.

## 2. Một mô hình chung cho nhiều trạm

Mỗi mẫu là `(station_id, issue_time)`; trạmA tại thờit là một mẫu, trạmB tại cùngt là mẫu khác. Nhãn luôn là mưa đo ở chính trạm đó. Mỗi kiến trúc dự kiến dùng một mô hình chung; dự đoán nhiều trạm bằng mộtbatch, không bắt buộc86 mô hình riêng.

Đầu vào gồm khí tượng phù hợp vị trí trạm, lịch sử mưa chính trạm nếu dùngR, và metadata tĩnh như tọa độ/mãtrạm. Không cộng/gộp nhãn của các trạm thành một nhãn vùng. TrạmA thiếu một khoảng chỉ loại mẫuA không hợp lệ; không yêu cầu tất cả trạm đủ đồng thời.

## 3. Hai nhánh dự báo

| Nhánh | Lịch sử ban đầu | Đầu ra | Mô hình |
| --- | --- | --- | --- |
| Cực ngắn | 24giờ tại trạm | Sáu lượng mưa giờ tiếp theo | Bi-LSTM; persistence/LightGBM làm đối chiếu phù hợp |
| Ngắn | Bảyngày tại trạm | Ba tổng24hriêng ngày1/2/3 | LightGBM, TFT, Informer cùng mẫu |

Độ dài lịch sử là cấu hình ban đầu, chưa tối ưu. Tensor chuỗi vẫn có dạng `[batch, thời gian, đặc trưng]`, nhưng mỗi phần tử batch thuộc một trạm và một issue. Statictrạm có thể đi nhánh riêng tùy kiến trúc; chưa chốt số kênh cuối.

## 4. Nguồn và những phần phải dựng lại

Vrain là số đo tại điểm, không có ô vuông mặc định quanh mỗi trạm. Nhãn lấy từ mưa trạm sauQC; nhãn ngày là tổng những giờ thuộc đúng cùng cửa sổ, đủ số lượng và chất lượng. Không chia mưa ngày thành giờ, không điền thiếu thành0, không lấp y bằngERA5/CPC/GSMaP.

**Người dùng xác nhận10:00là tổng09:00–10:00 giờ Việt NamUTC+7**, đơn vị nguồn hiển thịmm. Ghép trạng tháiERA5lúc09:00VN(02:00UTC) với khoảng09–10; issue là cuối khoảng. Clock20:00hômtrước→19:00ngàyđượcchọn tạo ngày19:00→19:00; nhãn ngày yêu cầu đủ24giờ. Tiêu đềXLSX19:20không dùng để thay bin giờ. Giữraw/QC/provenance; dữ liệu hồi cứu không tự chứng minh có sẵn tại issue vận hành.

**ERA5 phải trích theo tọa độ trạm hoặc nút lưới lân cận có quy tắc rõ.** Các trạm gần nhau có thể chia sẻ trường ERA5 vì nguồn0,25°; tọa độ, mưa quá khứ và metadata giúp mô hình phân biệt trạm. Nội suy không tạo thêm độ phân giải thật. Cao độ trạm hiện thiếu; DEM nếu bổ sung phải có nguồn, không tự nhận là cao độ đo tại trạm.

**Đã nội suy trực tiếp từ nativeERA5** ở `data/raw_data/gee/era5/grid/*.parquet`; mọi trạm lịch sử đều có bốn nút bao quanh. Yêu cầu mọi nút có trọng số dương hợp lệ; thiếu thìNaN, không tái chuẩn hóa bỏ nút. Không dùng đường vòngcube93ô. Các cột context/SST dùng miền lớn hơn có chủ đích và provenance. Predictor44kênh trong `PBL6_VRAIN_SOURCE_V1.zip` vẫn là trung bình vùng cũ, khác với bộ trạm mới.

## 5. Nhóm biến và E0–E7

Đã xây catalogue B/A/M/C theo trạm trong bảnv1:

| Nhóm | Số kênh khí tượng/lịch giờ / ngày dự kiến | Nội dung |
| --- | ---: | --- |
| B | 11 / 9 | Nhiệt/ẩm/áp/gió gần mặt đất và lịch |
| A | 12 / 12 | Đối lưu, mây, hơi nước, lớp biên và đất |
| M | 20 / 20 | Trường850/500, shear, IVT/VIMD, context và chênháp |
| C | 1 / 1 | SSThộpbiển; chưa phảiENSO/MJO đầy đủ |
| R tùy chọn | 1/1 | Mưa quá khứ của chính trạm |
| Statictrạm | 2tọađộ vàID riêng | Chưa có cao độ/lịch sử di chuyển trạm |

E0=B; E1=BA; E2=BM; E3=BC; E4=BAM; E5=BAC; E6=BMC; E7=BAMC. Static và lựa chọnR phải nhất quán giữa cácE/model. E7đãdựng44/42kênh; thêmRthành45/43, staticđiriêng. Dùng `sample_ready_r1` chung mọiE/model/R0–R1.

Chỉ dùng đầu vào đã kết thúc trước issue và lịch tương lai biết trước; không dùng khí tượng ERA5 kỳ đích. Thiếu dự báo khí tượng tương lai có thể hạn chế skill ngày2–3; chấp nhận kết quả không cải thiện.

## 6. Chia dữ liệu và đánh giá

- Chia theo thời gian chung trên mọi trạm, toàn bộ nhãn nằm trongsplit; khôngrandom các cửa sổ chồng lấn. Lịch sử Vrain thực sauQC quyết định fold, không ép từ2015.
- Bảnv1dùng train2021–22/cal2023/dev2024 theo giờ Việt Nam.2024là đánh giá phát triển, chưa phải testcuối. Cửa sổ nhãn băng ranh bị loại; lịch sử được lấy quá khứ trước đầu split.
- Fit scaler/imputer/climatology chỉtrain; earlystop/calibration/ngưỡng quyết định chỉcal. Trạm mới thiếu lịch sửtrain không được âm thầm học từ nămtest.
- Khi soE/model/R0–R1, cùng danh sách mẫu và split. Một trạm thiếu dữ liệu không làm mất mẫu của toàn mạng.
- 2025 vẫn giữ kín; không dùng2026 đểfit/tuning rồi gọi2025làtesttươnglai. Dữ liệu2026hai kênh đang giữ riêng vì chưa xác nhận tương đương.
- Báo MAE/RMSE/Bias theo trạm/mùa/horizon; CSI/POD/FAR vàBS/BSS khi có xác suất. Ngưỡng16/50/100 từ nhãn vùng cũ chưa được tự động chuyển sang nhãntrạm; chốt ngưỡng đúngkỳ/đối tượng trướctest.
- Báo macro-average giữa trạm cùngmicro khi cần, n/events rõ ràng. Bootstrap theo khối thời gian giữ cùng đợt mưa giữa các trạm; không coi nhiều trạm/ngày là nhiều mùa độc lập.
- Nếu muốn nói tổng quát sang trạm chưa thấy, cần kiểm định giữ lại trạm/khối riêng; test tương lai ở trạm đã biết chưa chứng minh điều đó.

## 7. Lộ trình

Đã dựng dữ liệu/nhãn/loader/split và kiểm tra toàn file. Bước tiếp: pilot nhómtrạmđạidiện → mở rộng trạm đạt → E0–E7 cùngba môhìnhngày → khóa trước2025. Chưa có kết quả train mô hình trạm.

**Bàn giao:** `data/processed/station_v1/PBL6_TRAM_GIO_NGAY_V1.parquet` (ngoàiGit), `reports/station_data_handoff_2026_11_09/MO_TA_DU_LIEU.docx`. Có2.995.050hàng/2.480.367cửa sổ qua kiểm tra không thiếuX/y, đúngtrạm/giờ/tổngngày/split;34testsđạt. Loader/ví dụ/giới hạn ở `HUONG_DAN_TRAIN.md`, số liệu vàchecksum ở `dataset_summary.json`, bằng chứng ở `verification.json`. Đây là kiểm tra ghép/cấu trúc, chưa chứng nhận cảm biến hoặc dự báo vận hành.

Các báo cáo vùngCPC/GSMaP và kiểm định nhãn vùng được giữ để giải thích quyết định đổi mục tiêu. Chưa huấn luyện mô hình theo trạm; không đổi tên số đo/kết quả cũ.
