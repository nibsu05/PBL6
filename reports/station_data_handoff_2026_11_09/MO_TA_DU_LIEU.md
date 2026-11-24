# Dữ liệu dùng chung — dự báo mưa tại trạm

Ngày bàn giao: 09/11/2026. Gửi cùng file **PBL6_TRAM_GIO_NGAY_V1.parquet** (432.9 MB).

## 1. Dữ liệu này là gì?

Một file đã ghép mưa Vrain tại trạm với khí tượng ERA5 theo tọa độ trạm; có hai độ phân giải `1h` và `24h`. Mục tiêu là dự báo tại từng trạm, không phải mưa trung bình toàn Đà Nẵng. Mỗi kiến trúc học một mô hình chung cho nhiều trạm.

Danh mục tài khoản nhóm Đà Nẵng có **86 vị trí**; file có **82 trạm với lịch sử**. Trong đó **79 trạm có cửa sổ train hợp lệ**; ba trạm chưa có cửa sổ train bị loại khỏi đánh giá mặc định. Bốn vị trí chỉ có ở danh mục mới chưa có lịch sử trong nguồn này.

Nguồn có ngày đánh dấu 01/01/2021–31/12/2024. Khoảng đo thực: **19:00 ngày 31/12/2020 đến19:00 ngày 31/12/2024, giờ Việt Nam**; không có nghĩa mọi trạm đủ suốt giai đoạn. **10:00 = tổng mưa09:00–10:00 (UTC+7)**. Nhãn ngày cộng đủ 24 giờ từ 19:00 hôm trước đến19:00 ngày được đánh dấu.

## 2. Hai nhánh dùng cùng file

| Nhánh | Chọn resolution | Đầu vào E7 + mưa quá khứ | Nhãn tương lai tại cùng trạm |
| --- | --- | --- | --- |
| Bi-LSTM, cực ngắn | `1h` | 24 giờ ×45 kênh | `y_h1_mm`…`y_h6_mm`: sáu lượng mưa giờ riêng |
| LightGBM/TFT/Informer, ngắn | `24h` | 7 ngày ×43 kênh | `y_d1_mm`…`y_d3_mm`: ba tổng24h riêng |

45/43 kênh đã gồm một kênh mưa quá khứ; tọa độ/mã trạm đi nhánh tĩnh riêng. Không lấy các cột nhãn hoặc QC làm đầu vào. Cột `rain_mm` là mưa đã quan trắc trong khoảng của hàng hiện tại; nhãn tương lai nằm ở các cột `y_*`.

## 3. Đặc trưng và nguồn

| Nhóm | Kênh giờ/ngày | Bao gồm |
| --- | --- | --- |
| B — nền | 11/9 | Nhiệt độ, điểm sương, độ ẩm2m; áp suất mặt đất/mực biển; gió u/v10m; lịch sin/cos giờ và ngày-trong-năm, bỏ hai kênh giờ ở bản ngày |
| A — đối lưu/mây/đất | 12/12 | CAPE, CIN, has_lfc, TCWV, K-index, Total Totals, độ cao lớp biên, bốn loại độ phủ mây, ẩm đất lớp1 |
| M — hoàn lưu/dòng ẩm | 20/20 | Gió/nhiệt/ẩm/chuyển động đứng850/500hPa; shear; IVT/VIMD; context TCWV/IVT; hai chênh áp |
| C — biển | 1/1 | SST trung bình hộp biển; chưa phải ENSO/MJO |
| R — tùy chọn | 1/1 | Mưa quá khứ của chính trạm, không dùng mưa tương lai |

Khí tượng: ERA5 gốc0,25° nội suy từ bốn nút quanh tọa độ trạm; không chép trung bình vùng 93ô. Đây vẫn là trường khí tượng lưới, không phải khí tượng đo tại trạm. Giờ dùng ERA5 lúc đầu khoảng mưa; ngày lấy trung bình đủ 24trạng thái giờ. Context/SST/chênháp có miền vùng có chủ đích. Không dùng mưa ERA5, GSMaP hoặc CPC làm nhãn hay lấp mưa thiếu.

## 4. Chia dữ liệu và dùng đúng

| Phần | Vai trò | Mẫu giờ | Mẫu ngày |
| --- | --- | ---: | ---: |
| train —2021–2022 | Học mô hình/scaler | 1.032.811 | 37.872 |
| cal —2023 | Chọn cấu hình, earlystop/calibration | 676.870 | 26.200 |
| dev —2024 | Đánh giá phát triển, chưa là test cuối | 679.888 | 26.726 |

Toàn bộ nhãn phải nằm trong phần chia theo giờ Việt Nam. Mọi E/model dùng cùng `sample_ready_r1`; khi so R0/R1 cũng giữ mask này. **Không lọc bỏ các hàng thời gian thiếu rồi mới cắt chuỗi** vì sẽ nối sai lịch sử. Dùng loader trong repo `src/station_forecast_data.py`; chỉ cần file Parquet này, không phải ghép lại nguồn.

E0=B; E1=BA; E2=BM; E3=BC; E4=BAM; E5=BAC; E6=BMC; E7=BAMC. R và metadata tĩnh giữ giống nhau khi so E. LightGBM làm phẳng cùng lịch sử; TFT/Informer nhận chuỗi tương ứng. Chỉ lịch tương lai biết trước được dùng ở decoder; không khí tượng kỳ đích.

## 5. Đã kiểm tra và giới hạn

Đã kiểm tra **2.995.050 dòng**, **2.480.367 cửa sổ**: đúng trạm/giờ/nhãn; tổng ngày đủ 24 giờ; không thiếu X/y trong cửa sổ đã đánh dấu; không vượt ranh nhãn giữa các phần chia. Ba station-day lệch tổng bị loại khỏi nhãn. NaN vẫn được giữ ở các hàng không dùng được; không điền thiếu thành0. CIN có mã500 kèm has_lfc theo quy ước nguồn, không phải phép điền mưa.

Đạt kiểm tra ghép/cấu trúc, **chưa phải chứng nhận độ chính xác cảm biến hoặc kỹ năng dự báo**. 24 trạm có dưới180 mẫu ngày train; dùng mô hình chung và báo điểm riêng từng trạm. Tọa độ là metadata hiện có, chưa có lịch sử di chuyển/cao độ trạm. ERA5 là dữ liệu hồi cứu, chưa chứng minh khả dụng ngay tại lúc phát dự báo.

**2025 giữ kín. 2026 đã tải riêng nhưng chưa nhập bản train**, vì hai kênh chưa chứng minh tương đương và khí tượng chưa phủ hết giai đoạn mới. Bộ này dùng cho bước huấn luyện tiếp theo; chưa có kết quả mô hình trạm. Chỉ chia sẻ nội bộ nhóm có quyền dữ liệu, không đẩy Parquet lên GitHub công khai.

Hướng dẫn chạy loader: [HUONG_DAN_TRAIN.md](HUONG_DAN_TRAIN.md). SHA256 dữ liệu: `04e16e230111d71ec16367d287412beb156fcf3570049e5a5f0f4b846f03ad74`.
