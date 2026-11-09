# Thiết kế nghiên cứu hiện hành — dự báo mưa tại nhiều trạm

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

Đây không phải số trạm đủ cả năm hoặc đã được chọn train. Số trạm cuối phụ thuộc lịch sử, QC và yêu cầu cửa sổ của từng nhánh. Bốn vị trí chỉ có trong danh mục mới không có lịch sử tự tạo trước khi nguồn trả số.

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

Đồng hồ nguồn20:00hômtrước→19:00ngàyđượcchọn; XLSXmẫu ghi tiêu đề19:20. Phải xác nhận timezone/đầu-cuối kỳ/đơn vị/loại tích lũy trước chuẩn hóa và ghépERA5. Giữ raw, cờQC, thời gian lấy, nguồn và các khoảng đo. Dữ liệu đã tải không tự chứng minh có sẵn tại issue vận hành.

**ERA5 phải trích theo tọa độ trạm hoặc nút lưới lân cận có quy tắc rõ.** Các trạm gần nhau có thể chia sẻ trường ERA5 vì nguồn0,25°; tọa độ, mưa quá khứ và metadata giúp mô hình phân biệt trạm. Nội suy không tạo thêm độ phân giải thật. Cao độ trạm hiện thiếu; DEM nếu bổ sung phải có nguồn, không tự nhận là cao độ đo tại trạm.

Cube theo ô ở `data/processed/dataset_v2_danang/`; phải kiểm tra trạm trong/ngoài miền và hành viNaN. Không ngoại suy âm thầm. Các cột context/SST dùng miền lớn hơn có chủ đích và provenance. Predictor44kênh trong `PBL6_VRAIN_SOURCE_V1.zip` vẫn là trung bình vùng cũ, chưa phải dataset theo trạm.

## 5. Nhóm biến và E0–E7

Giữ catalogue khí tượng dự kiến B/A/M/C, xây lại giá trị phù hợp trạm:

| Nhóm | Số kênh khí tượng/lịch giờ / ngày dự kiến | Nội dung |
| --- | ---: | --- |
| B | 11 / 9 | Nhiệt/ẩm/áp/gió gần mặt đất và lịch |
| A | 12 / 12 | Đối lưu, mây, hơi nước, lớp biên và đất |
| M | 20 / 20 | Trường850/500, shear, IVT/VIMD, context và chênháp |
| C | 1 / 1 | SSThộpbiển; chưa phảiENSO/MJO đầy đủ |
| R tùy chọn | Chưa chốt | Mưa quá khứ của chính trạm |
| Statictrạm | Chưa chốt | Tọa độ/mãtrạm; địa hình nếu bổ sung được |

E0=B; E1=BA; E2=BM; E3=BC; E4=BAM; E5=BAC; E6=BMC; E7=BAMC. Static và lựa chọnR phải nhất quán giữa cácE/model. Các con số44/42 chưa bao gồm static/R, chưa bảo đảm mọi biến đã trích tại trạm.

Chỉ dùng đầu vào đã kết thúc trước issue và lịch tương lai biết trước; không dùng khí tượng ERA5 kỳ đích. Thiếu dự báo khí tượng tương lai có thể hạn chế skill ngày2–3; chấp nhận kết quả không cải thiện.

## 6. Chia dữ liệu và đánh giá

- Chia theo thời gian chung trên mọi trạm, toàn bộ nhãn nằm trongsplit; khôngrandom các cửa sổ chồng lấn. Lịch sử Vrain thực sauQC quyết định fold, không ép từ2015.
- Fit scaler/imputer/climatology chỉtrain; earlystop/calibration/ngưỡng quyết định chỉcal. Trạm mới thiếu lịch sửtrain không được âm thầm học từ nămtest.
- Khi soE/model/R0–R1, cùng danh sách mẫu và split. Một trạm thiếu dữ liệu không làm mất mẫu của toàn mạng.
- 2025 vẫn giữ kín; không dùng2026 đểfit/tuning rồi gọi2025làtesttươnglai. Dữ liệu2026hai kênh đang giữ riêng vì chưa xác nhận tương đương.
- Báo MAE/RMSE/Bias theo trạm/mùa/horizon; CSI/POD/FAR vàBS/BSS khi có xác suất. Ngưỡng16/50/100 từ nhãn vùng cũ chưa được tự động chuyển sang nhãntrạm; chốt ngưỡng đúngkỳ/đối tượng trướctest.
- Báo macro-average giữa trạm cùngmicro khi cần, n/events rõ ràng. Bootstrap theo khối thời gian giữ cùng đợt mưa giữa các trạm; không coi nhiều trạm/ngày là nhiều mùa độc lập.
- Nếu muốn nói tổng quát sang trạm chưa thấy, cần kiểm định giữ lại trạm/khối riêng; test tương lai ở trạm đã biết chưa chứng minh điều đó.

## 7. Lộ trình

Xác minh thời gian/QC và tập trạm → tríchERA5trạm → dựngnhãn/ngàyđúnganchor → loader/split/replay → pilot nhómtrạmđạidiện → mở rộng trạm đạt → E0–E7 cùngba môhìnhngày → khóa trước2025.

Các báo cáo vùngCPC/GSMaP và kiểm định nhãn vùng được giữ để giải thích quyết định đổi mục tiêu. Chưa huấn luyện mô hình theo trạm; không đổi tên số đo/kết quả cũ.
