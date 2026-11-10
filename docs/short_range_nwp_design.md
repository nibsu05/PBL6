# Phương án được duyệt — dự báo mưa ngày 1–3 tại trạm

Người dùng duyệt triển khai ngày **10/11/2026**, sau khi yêu cầu đánh giá độc lập với hướng cũ. Câu hỏi: **mưa quan trắc gần đây, khí tượng dự báo và thông tin địa phương có cải thiện dự báo tại trạm so với GFS nguyên bản không?**

## Mục tiêu và thời gian

Mỗi mẫu là `(station_id, issue_time)`, nhãn đo tại chính trạm thuộc nhóm Đà Nẵng của tài khoản. Một kiến trúc học chung nhiều trạm; không cần bộ mô hình riêng cho từng trạm.

Issue19h Việt Nam: dự báo ba lượng mưa riêng trong các cửa sổ19hD→19hD+1;19hD+1→19hD+2;19hD+2→19hD+3. Không phải ba tổng tích lũy chồng nhau. Nhãn ngày đòi hỏi đủ24giờ Vrain quaQC; không lấp bằngERA5/CPC/GSMaP.

ERA5v1 đã đúng cấu trúc nhưng là tái phân tích trễ khoảng5ngày, chưa chứng minh khả dụng lúc phát tin. Hướng mới dùng **bản GFS khởi tạo trước issue** để cung cấp khí tượng tương lai. Đây là dự báo đã biết tại issue, khác việc dùng số thực đo/ERA5 kỳ đích làmX. [ERA5](https://confluence.ecmwf.int/pages/viewpage.action?pageId=384141176), [hướng hậu xử lý mưa](https://arxiv.org/abs/2310.02676).

GFS00UTC cùng ngày; issue12UTC=19hVN. Lấy hiệu APCP tích lũy0–12/36/60/84h để tạo ba tổng24h. Không nhầm trường6h với tổng từinit. Kiểm tra GRIBinit/validtime/step/unit, SHA và HTTPRange. Âm nhỏ do lượng tử hóa được gắn cờ theo bước đóng gói; âm lớn làm lỗi, không tựclip.

GFS giả định công bố sau8h, margin init→issue12h; **chưa xác minh thời điểm công bố lịch sử từng file**. MetadataS3 có thể là lúc chép archive. Trạm giả định trễ1h: issue19h dùng tổng1/6/24h kết thúc18h và bảy ngày19–19h đầy đủ kết thúc hôm trước, không dùng số đo19h ngay lập tức.

## Dữ liệu và cohort

Sản phẩm [GFS NOAA](https://registry.opendata.aws/noaa-gfs-bdp-pds/) 0,25° nội suy tại trạm; không phải khí tượng đo tại trạm. T850/RH850/U850/V850/PWAT ở+24/+48/+72h là ba trạng thái giữa cửa sổ, chưa phải trung bình ngày. Q850/proxyẩm tính nhất quán từT/RH vì sản phẩm đầu2021thiếuSPFH. [Inventory GFS](https://www.nco.ncep.noaa.gov/pmb/products/gfs/).

DEM từ [Mapzen Terrain Tiles](https://registry.opendata.aws/terrain-tiles/): cao độ, lân cận±5km, gradient địa hình. Đây là proxy tại tọa độ hiện có, chưa phải cao độ khảo sát hoặc lịch sử vị trí trạm. Gió·gradient và proxyẩm là giả thuyết; thêmbiến không chứng minh nhân quả.

Pilot chọn20trạm từ57ứng viên có≥365ngày train đầy đủ và≥30ngày≥1mm trong2021–2022. Thuật toánfarthest-first trênlat/lon/logDEM cố định, không dùngcal/dev. Trạm được chọn có565–728ngày train hợp lệ. Danh mục86vịtrí/82lịch sử không đồng nghĩa đủ86train.

**Cadence7ngày** cố định từ08/01/2021 đến28/12/2024:208issue, không chọn ngày theo mưa. Đây là pilot quy trình/kỹ năng sơ bộ, chưa phải thí nghiệm hằng ngày. Thiếu tại một trạm chỉ loại mẫu trạm đó; nhiều trạm cùng đợt không là nhiều mẫu thời tiết độc lập.

## Thí nghiệm

| Cấu hình | Đầu vào |
| --- | --- |
| A0 | MưaGFS, lịch tương lai, tọa độ vàIDtrạm |
| A1 | A0 + bảyngày mưa trạm và summary1/6/24h khả dụng |
| A2 | A1 + T/RH/gió850/PWAT dự báo, Q850dẫn xuất và proxyẩm |
| A3 | A2 + DEM, gradient và tươngtácgió–độdốc–ẩm |

MọiA cùng mẫu/horizon/split. Saupilot cần kiểm tra bỏ nhóm khỏi cấu hình đầy đủ, vì tác dụng thêmnhóm phụ thuộc thứ tự. Không tiếp tục E0–E7 cũ một cách mặc định.

Đối chứng: khí hậu tháng/trạm cóshrinkage fittrain; persistence với mưa khả dụng; GFSnguyênbản. LightGBM chính: amountTweediep=1,5 và classifier≥1/≥50mm.50mm là ngưỡng thăm dò pilot, không tự nhận chuẩn cảnh báo. Ba seed17/29/43, lấy trung bình dự báo; seed không phải mùa/năm độc lập.

GRU_A2 nhỏ chỉ chạy nếu **cal** A2macroMAE thấp hơn cảGFS/khíhậu và≥50%trạm tốt hơnGFS ở ít nhất một hạn. Cấu hìnhGRU cố định trướcdev, cùng đầu vàoA2. TFT/Informer là mở rộng tùy bằng chứng, không bắt buộc.

## Kiểm chứng

Train2021–2022;cal2023choearlystop/calibration;dev2024chưa testcuối. Toàn bộ72hnhãn phải ở cùngfold. Scaler/statistics/reference fittrain. Cal dùngPlatt nên điểm xác suấtcal không phải ngoài mẫu. Không dùngdev cho gateGRU.

MAE/RMSE/Bias từng trạm/hạn vàmacro đồng trọng số, kèm micro. BS/BSS so khíhậu cùng mẫu, reliabilitybins. CSI/POD/FAR: cutoffxácsuất0,5 với mô hình xác suất, ngưỡnglượng vớiGFS/persistence; ghi rõ quy tắc. Chỉ số không xác định giữNaN, báo số trạm hỗ trợ. Không tối ưuPOD đơn lẻ.

Bootstrap ghép cặp theo khối4issue liên tiếp, giữ mọi trạm/hạn đồng thời. CI chênhMAE gồm0 thì chưa đủ căn cứ cải thiện ổn định. Ngưỡng50mm có thể ítđợt; không gộp nhiều trạm thành nhiều đợt độc lập.

**2025 giữ kín,2026 khôngfit/tuning.** Chỉ sau khóa protocol và kiểm tra nguồn mới mở2025 nếu đủQC. Không đổi tên kết quảCPC/GSMaP/vùng cũ thànhVraintrạm.

## Chạy và bàn giao

`prepare_gfs_station_pilot.py` → `collect_gfs_station_pilot.py` → `build_gfs_station_pilot.py` → `validate_gfs_station_pilot.py` → `run_gfs_station_pilot.py` → `run_gfs_station_gru.py` nếugateđạt. Cài thêm `requirements-nwp.txt` trongvenv. HTTP chạy song song, giải mãecCodesWindows dùngLock.

Protocol trướcfit, audit, verification, metrics và báo cáo tổng hợp: `reports/gfs_station_pilot_2026_11_10/`. Private ở `data/operational/gfs_station_pilot_2026_11_10/` và `data/processed/gfs_station_pilot/`. Mở rộng hằng ngày saupilot và kiểm tra độ phủ/độtrễ. BộERA5v1 đã gửi trước giữ phạmvi riêng; không sửađổi âmthầm. GitHub chỉ chứa mã/tài liệu/aggregates, không raw/tọađộ/credential/model/per-timepredictions.
