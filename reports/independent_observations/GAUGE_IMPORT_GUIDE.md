# Nhập và đánh giá mưa trạm Đà Nẵng theo giờ

Hiện **chưa có file trạm Vrain** trong workspace. Bộ nhập đã sẵn sàng cho CSV hoặc Excel `.xlsx` có thời điểm đầy đủ ngày–giờ, lượng mưa mm trong đúng một giờ và thông tin trạm. Vrain cho biết có thể [xuất Excel theo giờ](https://watec.vn/products/tram-do-mua-tu-dong-vrain); [API yêu cầu API key của đối tác](https://dev.vrain.vn/). Không đặt API key trong mã nguồn, file báo cáo hoặc chat.

## Thông tin cần lấy cùng dữ liệu

- Tên/mã trạm và tọa độ đo, để biết trạm cách điểm nghiên cứu 16,0544°B, 108,2022°Đ bao xa.
- Múi giờ và quy ước timestamp: đầu hay cuối **khoảng tích lũy 60 phút**. Nếu timestamp là đầu khoảng, bộ nhập cộng một giờ và lưu tất cả dưới dạng **cuối khoảng theo UTC+7**.
- Cột lượng mưa mm/giờ, mã chất lượng nếu có, ý nghĩa số 0, mã missing và mốc trạm ngừng hoạt động. Giờ không có bản ghi không được coi là 0.
- File gồm cả giờ khô; nếu chỉ có báo cáo lúc mưa, recall và tỷ lệ cảnh báo sai sẽ bị lệch.

## Chuẩn hóa

Ví dụ khi đã xác nhận timestamp của file là **cuối giờ** (thay tên cột/tọa độ bằng metadata thật):

```powershell
.\.venv\Scripts\python.exe prepare_gauge_observations.py `
  --input data/raw_data/vrain_station.xlsx `
  --station-name 'Ten tram' --lat 16.06 --lon 108.20 `
  --source-name Vrain --source-timezone Asia/Ho_Chi_Minh `
  --timestamp-means end --accumulation-hours 1 --datetime-column 'Thoi gian' `
  --rain-column 'Luong mua'
```

Nếu timestamp là đầu khoảng, dùng `--timestamp-means start`. Với file nhiều trạm, thêm `--station-column` và `--station-value`. Nếu có mã chất lượng, thêm `--quality-column` và `--accepted-quality` với mã được chấp nhận. Giới hạn khoảng cách mặc định 30 km; chỉ nâng `--max-distance-km` khi trạm xa hơn là lựa chọn có chủ ý. Chương trình từ chối thời điểm trùng, giờ lẻ, mưa âm, giá trị chữ không hiểu được; nó **không nội suy nhãn**. Kết quả là `data/processed/independent_gauge/observations.csv` và `station_metadata.json` chứa nguồn, hash, số giờ thiếu và thống kê chất lượng.

## Đánh giá không chọn lại mô hình

```powershell
.\.venv\Scripts\python.exe evaluate_gauge_predictions.py `
  --observations data/processed/independent_gauge/observations.csv `
  --station-metadata data/processed/independent_gauge/station_metadata.json
```

Script dùng đúng ba dự báo đã lưu (Bi-LSTM hai đầu, Bi-LSTM chuẩn, persistence) và ngưỡng xác suất **0,40 đã chốt trên validation**. Nó chỉ ghép giờ hiệu lực có số đo trạm; kiểm tra anchor+horizon và lưu tỷ lệ phủ, chỉ số theo giờ và theo đợt. Khi trạm thiếu giờ, chỉ số theo đợt là chẩn đoán trên khoảng có quan trắc, không đại diện cho toàn bộ thời gian.

Để đánh giá giai đoạn **sau test cũ** (mốc cuối 2026-09-01 06:00 UTC+7), trước hết ghi các dự báo mới theo [hướng dẫn as-of](../realtime_readiness/READINESS.md), sau đó chạy:

```powershell
.\.venv\Scripts\python.exe evaluate_gauge_predictions.py `
  --observations data/processed/independent_gauge/observations.csv `
  --station-metadata data/processed/independent_gauge/station_metadata.json `
  --predictions reports/prospective/issuances `
  --start-after '2026-09-01T06:00:00+07:00'
```

Chưa có file trạm và chưa có dự báo mới, nên thư mục đánh giá trạm hiện chưa có chỉ số thật.
