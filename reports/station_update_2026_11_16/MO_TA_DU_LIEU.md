# Dữ liệu trạm cập nhật đến 2026 — bản 16/11/2026

**Đã cập nhật đến ngày nguồn 15/11/2026.** Có danh mục 86 vị trí trong nhóm Đà Nẵng của tài khoản Vrain. Đây là danh mục, không phải cam kết mọi trạm có đủ số đo từ năm 2021 hay phủ kín diện tích. Dữ liệu phục vụ dự báo tại từng trạm.

## 1. Nhận tệp nào để làm việc?

Gói nội bộ: `data/processed/station_update_2026_11_16/PBL6_DATA_DEN_2026.zip`. Chứa hai Parquet, mô tả, danh mục trạm và checksum; không đưa lên GitHub công khai.

| Tệp | Nội dung | Số hàng |
| --- | --- | ---: |
| PBL6_MUA_TRAM_GIO_2021_2026.parquet | Mưa giờ gốc/QC hai kênh, khoảng đo, mã nguồn và cờ xung đột | 4.427.280 |
| PBL6_GFS_VRAIN_NGAY_2021_2026.parquet | Đầu vào N0–N5, nhãn ba ngày và cờ mẫu hợp lệ theo từng kênh | 726.528 |

Tệp ngày là bản ghép cho **bài toán ngắn hạn GFS + Vrain hiện hành**. Mưa giờ là số do Vrain trả ở từng trạm, không được chia từ mưa ngày. Tệp giờ hỗ trợ kiểm tra/nhánh cực ngắn; chưa bổ sung bộ 44 biến ERA5 cũ đến 2026. Không đổi tên dữ liệu hồi cứu ERA5 thành khí tượng dự báo GFS.

## 2. Thời gian và độ phủ

- Mưa nguồn có ngày được đánh dấu từ 01/01/2021 đến 15/11/2026; mỗi ngày là cửa sổ 19h hôm trước → 19h ngày đó theo giờ Việt Nam. Tệp giờ vì vậy bắt đầu từ khoảng kết thúc 20h ngày 31/12/2020.
- Theo xác nhận của người dùng: số đo “10:00” là mưa 09:00–10:00 UTC+7. Parquet ghi cả `period_start_utc` và `period_end_utc`.
- Issue dự báo ngày: 19h mỗi ngày, từ 08/01/2021 đến **12/11/2026**. Ba nhãn là ba tổng 24h riêng tiếp theo; mẫu cuối cần quan trắc đến 19h ngày 15/11/2026.
- Các mốc thiếu giữ NaN; không thay bằng 0 và không lấp nhãn bằng ERA5/GFS/vệ tinh. Năm 2026 mới đến giữa tháng 11, chưa đủ cả năm.

| Năm | Trạm có số: cũ | Ngày–trạm đủ 24h: cũ | Trạm có số: mới | Ngày–trạm đủ 24h: mới |
| --- | ---: | ---: | ---: | ---: |
| 2021 | 57 | 20.350 | 0 | 0 |
| 2022 | 79 | 23.096 | 0 | 0 |
| 2023 | 79 | 28.309 | 0 | 0 |
| 2024 | 82 | 29.120 | 0 | 0 |
| 2025 | 82 | 29.479 | 0 | 0 |
| 2026 | 82 | 2.858 | 86 | 22.487 |


“Ngày–trạm đủ 24h” được tính riêng từng trạm/ngày sau QC nội kênh; 10 trạm đủ một ngày là 10 ngày–trạm. Bảng không chứng nhận hiệu chuẩn cảm biến. Kênh hiện hành không được tải toàn bộ 2021–2024; các probe lịch sử của nó không có số. Những ô không có số không được xem là trời khô.

**Độ phủ 2026 không đồng đều:** kênh hiện hành tháng 1 chỉ có 23 ngày–trạm đủ 24h trên 2.666 ô trạm–ngày của danh mục 86; tháng 10 có 2.652/2.666; 01–15/11 có 1.268/1.290. Số vị trí có ít nhất một số đo ở tháng 1 là 35, tháng 10 là 86. Đây là độ phủ trả về của API, chưa chứng minh ngày lắp đặt hay hoạt động thật của cảm biến. Chi tiết trong `coverage_2026_by_month.csv`.

Riêng tháng 1, **kênh cũ vẫn có 2.405 ngày–trạm đủ 24h**. Nếu nhìn hai kênh theo từng giờ và loại xung đột, có 2.422/2.666 ngày–trạm đủ số. Vì vậy kênh mới thưa đầu năm không có nghĩa toàn bộ kho đều thiếu như vậy. Hai kênh bổ sung nhau theo thời gian; đây là dấu hiệu phù hợp với việc chuyển hệ thống, chưa phải xác nhận chính thức về cảm biến hay ngày chuyển. Dữ liệu ngày vẫn loại các cửa sổ cần trộn lịch sử/nhãn giữa hai kênh.

## 3. Vì sao phải giữ hai kênh?

Kênh cũ phục vụ lịch sử; kênh hiện hành có dữ liệu mới hơn. 82 vị trí khớp tọa độ hiện tại, bốn vị trí chỉ có trong danh mục hiện hành. Đã kiểm tra alias và tọa độ hiện tại so với bản 09/11; giữ nguyên mã STxxx. Khớp metadata chưa chứng minh cảm biến/vị trí lịch sử và số đo tương đương.

Đã tải và kiểm tra **1.368 phản hồi ngày–kênh** cho 01/01/2025–15/11/2026, gồm cả 01/01/2026. Phần cũ 2021–2024 tái sử dụng từ kho đã kiểm chứng. Năm 2025 nay đã được thu thập/QC theo yêu cầu cập nhật này, nhưng **chưa dùng để fit, tuning hay tính điểm mô hình**.

Trong toàn bộ phần bổ sung có **367 cặp giờ–trạm** cùng có số ở hai kênh; **46 cặp khác nhau** quá 1e-6 mm. Đây chỉ là phần giao có số, không chứng minh các khoảng không trùng tương đương.

Trong tệp giờ, giữ `legacy_rain_raw_mm` và `modern_rain_raw_mm`, cùng giá trị sau QC. Cột tiện dụng `rain_mm` ưu tiên kênh cũ hợp lệ, dùng kênh mới khi cũ thiếu; **xung đột hai giá trị → NaN**, không lấy trung bình hay cộng hai kênh. `gauge_source_code`: 0=cũ, 1=mới, -1=thiếu, 3=xung đột. Không cắt chuỗi trực tiếp qua điểm đổi mã nguồn mà bỏ qua cờ này.

Trong tệp ngày, **một mẫu dùng lịch sử và nhãn từ cùng một kênh**. Khóa đầy đủ là `(station_id, issue_utc, gauge_namespace, horizon)`. Có thể có hai phương án nguồn cho cùng trạm–issue; `recommended_sample=True` chọn tối đa một phương án hoàn chỉnh, ưu tiên cũ khi cả hai đủ. Không coi hai phương án nguồn là hai quan trắc độc lập để nhân đôi tập train.

## 4. Đầu vào và đầu ra ngày

Một mẫu là một trạm và một issue. Ba hàng `horizon=1/2/3` là ba hạn của mẫu đó, không phải ba mẫu khí hậu độc lập. `y_mm` là mưa quan trắc tại đúng trạm trong cửa sổ 24h; ba nhãn không phải tổng tích lũy 24/48/72h.

| Nhóm | Số cột | Thông tin |
| --- | ---: | --- |
| N0 | 16 | Mưa dự báo GFS; mùa, tọa độ, ID; bảy tổng mưa ngày quá khứ và tổng 1/6/24h gần nhất |
| N1 | 21 | N0 + nhiệt độ, RH, u/v ở 850 hPa và PWAT dự báo |
| N2 | 25 | N1 + q, q×u, q×v và tốc độ gió |
| N3 | 26 | N1 + năm biến địa hình |
| N4 | 30 | N3 + bốn dẫn xuất gió–ẩm |
| N5 | 32 | N4 + hai tương tác gió/dòng ẩm với độ dốc |

GFS 00UTC, issue 12UTC=19h VN. Mưa ngày bằng các hiệu tích lũy C36−C12, C60−C36, C84−C60. Khí tượng +24/+48/+72h là trạng thái giữa cửa sổ, không phải trung bình khí tượng ngày. Nội suy bốn nút GFS 0,25° tới tọa độ trạm không tạo thêm độ phân giải thật. Địa hình Mapzen là proxy tại tọa độ hiện tại, không phải cao độ đo tại trạm.

Đơn vị: lượng mưa mm; nhiệt độ °C; RH %; u/v và tốc độ gió m/s; PWAT kg/m² (tương đương mm nước cột); q g/kg; cao độ m; độ dốc là tỷ số chênh cao/khoảng cách. q×u, q×v chỉ là dòng ẩm tại một mực850hPa, không phải IVT tích phân cả cột.

Mưa gần nhất kết thúc trước issue 1 giờ; cũng có cột trễ 3/6 giờ. Mẫu hoàn chỉnh yêu cầu đủ cả ba nhãn, mọi đặc trưng N5 và cả ba kịch bản trễ. Có `in_frozen_57_cohort` để giữ đúng phạm vi 57 trạm cũ. Số trạm có mưa không đồng nghĩa số trạm có mẫu đủ mọi điều kiện.

| Năm | Kênh | Vai trò | Mẫu trạm–issue đủ X/y |
| --- | --- | --- | ---: |
| 2021 | legacy | train | 18.539 |
| 2022 | legacy | boundary | 0 |
| 2022 | legacy | train | 19.683 |
| 2023 | legacy | boundary | 0 |
| 2023 | legacy | cal | 26.030 |
| 2024 | legacy | boundary | 0 |
| 2024 | legacy | dev | 27.773 |
| 2025 | legacy | boundary | 0 |
| 2025 | legacy | reserved2025 | 27.307 |
| 2025 | modern | boundary | 0 |
| 2025 | modern | reserved2025 | 0 |
| 2026 | legacy | external2026 | 2.437 |
| 2026 | modern | external2026 | 20.813 |


Hai issue GFS cũ bị lỗi nguồn vẫn giữ nguyên lý do loại. Phần mới có 0 issue lỗi nguồn. Tệp ngày giữ trạng thái nguồn và các mẫu không đủ, thay vì âm thầm biến chúng thành mẫu hoàn chỉnh.

## 5. Cách đọc để huấn luyện

```python
import pandas as pd

df = pd.read_parquet(
    "PBL6_GFS_VRAIN_NGAY_2021_2026.parquet",
    filters=[("recommended_sample", "=", True)],
)
# Giữ thiết kế đã chạy; không đưa mọi năm vào train.
train = df[df["split"].eq("train")]
cal = df[df["split"].eq("cal")]
dev = df[df["split"].eq("dev")]
# reserved2025 / external2026 hiện chỉ chuẩn bị dữ liệu, chưa chấm mô hình.
```

Muốn tái hiện kết quả cũ: lọc thêm `eligible_frozen_57_legacy=True` và split train/cal/dev. Đã đối chiếu toàn bộ **218.658 hàng cũ**, cùng X/y và split. Muốn lấy tensor GRU, gom ba hạn theo trạm–issue và chọn đặc trưng từ `feature_groups.json`; không đưa `y_mm`, split hay cờ tương lai vào X.

`sample_ready` xác nhận cấu trúc X/y và QC nguồn; **không chứng nhận tính liên tục giữa hai kênh**. Các mẫu modern vẫn có `continuity_with_legacy_confirmed=False`. Nên chấm riêng kênh cũ 2025 và kênh mới 2026 sau khi khóa mô hình; chưa gộp điểm hai nguồn để tuyên bố cải thiện.

## 6. Khuyến nghị nghiên cứu

Cập nhật đến 2026 là hữu ích để tăng thời gian quan trắc và kiểm tra phương pháp trên nguồn mới. Nhiều hàng hơn không tự làm mô hình tốt hơn: cần tách thiếu dữ liệu, đổi nguồn và thay đổi khí hậu theo năm. Chưa nên nối hai kênh rồi fit toàn bộ như một chuỗi đồng nhất.

Giữ kết quả 2021–2024 làm mốc. Trước khi chấm 2025/2026, khóa mục tiêu mean/median, cấu hình, cutoff và metric; năm 2026 phải báo giới hạn đổi nguồn và chưa đủ năm. Nếu chọn huấn luyện lại tới 2025, lập protocol mới với tập kiểm định sau giai đoạn đó, không gọi kết quả ấy là cùng thí nghiệm cũ.

Độ trễ GFS 8h và mưa trạm 1h vẫn là giả định; tải dữ liệu hồi cứu hôm nay chưa chứng minh nó đã có sẵn đúng giờ phát tin lịch sử. Không hứa dự báo vận hành chỉ từ kiểm tra ghép.

## 7. Đã kiểm tra những gì?

Đối chiếu 4.427.280 hàng giờ và 726.528 hàng ngày; replay 115.584 ô từ JSON gốc độc lập; kiểm tra lịch sử/nhãn/cutoff, mẫu đủ ba hạn, không trộn kênh và không nhân đôi mẫu được khuyến nghị. Tải lại độc lập 8 đoạn GRIB, đối chiếu 688 giá trị tại trạm cùng trường đã ghép. Giữ nguyên 87 tệp nghiên cứu/slide trước đó. Không train hoặc chấm mô hình trong lần cập nhật này.

Nguồn và checksum: `dataset_summary.json`, `verification.json`, `data_contract.json`, các bảng coverage và overlap cùng thư mục báo cáo. Tài liệu GFS: https://registry.opendata.aws/noaa-gfs-bdp-pds/. Raw, registry, tọa độ và Parquet chỉ chia sẻ nội bộ nhóm có quyền dữ liệu.
