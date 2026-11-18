# Mở rộng dự báo ngắn hạn từ 20 lên 57 trạm

**Đã mở rộng tập huấn luyện chính lên 57 trạm**, bổ sung 37 trạm đã có trong nguồn. Không phải lắp thêm trạm hay lấy dữ liệu toàn Việt Nam. Tất cả thuộc danh mục Vrain nhóm Đà Nẵng đang dùng.

## Vì sao 57, chưa phải 86?

| Nhóm | Số trạm | Trạng thái |
|---|---:|---|
| Giữ tiêu chuẩn train của pilot | 57 | ≥365 ngày đầy đủ và ≥30 ngày ≥1 mm trong 2021–2022; đưa vào bản mở rộng |
| Có mẫu train nhưng lịch sử ngắn hơn | 22 | Có thể làm phân tích mở rộng riêng; chưa gộp vào nhóm chính |
| Có lịch sử nhưng chưa có cửa sổ train hợp lệ | 3 | Chưa đưa vào đánh giá các trạm đã biết |
| Chỉ có trong danh mục hiện hành | 4 | Chưa có lịch sử từ nguồn2021–2024 đang dùng |

Nhóm57 có 479–728 ngày train đầy đủ. Tuy nhiên, 2 trạm có dưới 30 cửa sổ train theo lịch7 ngày (ít nhất18). Đủ tổng số ngày không đồng nghĩa chuỗi liên tục hoặc chất lượng cảm biến đã được chứng nhận.

## Đã thực hiện

- Dùng lại GFS đã trích cho82vịtrí; không tải lại toàn bộ dữ liệu GFS. Có tải kiểm tra một số thông điệp để replay độc lập.
- Giữ lịch208issue mỗi7 ngày, cùng đặc trưng A0–A3, hyperparameter, seed17/29/43 và split; không mở2025.
- Huấn luyện LightGBM A0–A3 trên57 trạm; chạy GRU theo gatecal đã định trước. Khí hậu, persistence và GFS là các đối chứng.
- Giữ nguyên pilot20 trạm. Mở rộng là phiên bản riêng, có protocol, dataset, model, kết quả và checksum riêng.

| Phần | Mẫu trạm–issue | Dòng ba hạn |
|---|---:|---:|
| train | 5,032 | 15,096 |
| cal | 2,582 | 7,746 |
| dev | 2,782 | 8,346 |

Mỗi mẫu dự báo ba lượng24hriêng tại cùng trạm; cutoffmưa18 h choissue19 h. GFS00UTC cung cấp ba cửa sổ19–19 h. MọiA dùng cùng mẫu. Dữ liệu trạm thiếu chỉ loại mẫu của chính trạm đó.

## Kết quả trên toàn57 trạm, phần phát triển2024

Macro-MAE đồng trọng số giữa trạm, nhỏ hơn tốt hơn. In đậm là thấp nhất trong cột; không tự khẳng định khác biệt có ý nghĩa thống kê.

| Phương pháp | Ngày1 mm | Ngày2 mm | Ngày3 mm |
|---|---:|---:|---:|
| Khí hậu | 10.75 | 10.26 | 10.93 |
| Persistence | 7.83 | 9.43 | 11.19 |
| GFS nguyên bản | 5.83 | 7.41 | 10.30 |
| LightGBM A0 | 6.57 | 7.07 | 10.42 |
| LightGBM A1 | 5.50 | 6.92 | 9.86 |
| LightGBM A2 | 5.28 | **6.72** | 8.44 |
| LightGBM A3 | **5.24** | 6.75 | 8.34 |
| GRU A2 | 6.94 | 7.56 | **8.00** |

**Không so trực tiếp bảng57 trạm với điểm trung bình20 trạm cũ để kết luận mô hình tốt lên hoặc kém đi.** Các trạm mới có độ khó và lịch sử khác nhau. Phải giữ cùng đối tượng đánh giá.

## So sánh công bằng trên đúng 20 trạm ban đầu

Đã xác minh nhãn, toàn bộ32 đầu vào A3, split và khóa(trạm,issue,hạn) giống nhau. So sánh dưới đây mở rộng cả dữ liệu train và cal, giữ thiết lập mô hình; không phải chỉ tăng dữ liệu train đơn độc.

| Mô hình A2 | Ngày1 mm | Ngày2 mm | Ngày3 mm |
|---|---:|---:|---:|
| Train/cal20 trạm; đánh giá cùng 20 trạm | 6.15 | 7.37 | 7.75 |
| Train/cal57 trạm; đánh giá cùng 20 trạm | 5.91 | 7.40 | 8.66 |

| Ngày | MAE57−MAE20 mm | CI95% mm |
|---|---:|---|
| 1 | -0.239 | [-0.757; 0.128] |
| 2 | 0.026 | [-0.185; 0.248] |
| 3 | 0.903 | [-0.116; 2.564] |

Số âm có lợi cho bản mở rộng. CI bao gồm0 thì chưa đủ bằng chứng cải thiện ổn định. Bootstrap theo khối4issue liên tiếp, giữ các trạm trong cùng đợt. Không dùng20 và 57như hai mẫu độc lập.

**Diễn giải kết quả:** trên cùng 20 trạm, điểm MAE A2 ngày 1 giảm, ngày 2 gần như ngang và ngày 3 tăng ở bản train/cal 57 trạm. Các CI chênh lệch vẫn chứa0. Vì vậy, mở rộng phạm vi thành công chưa đồng nghĩa tăng độ chính xác ổn định; cũng chưa đủ để kết luận mô hình mở rộng chắc chắn kém hơn.

## Đọc giới hạn đúng phạm vi

- Tăng số trạm giúp mở rộng phạm vi, chưa bảo đảm mọi trạm hoặc mọi chỉ số tốt hơn. Đọc cảRMSE/Bias/BS/BSS/CSI/POD/FAR trong CSV.
- Lịch vẫn mỗi7 ngày, chưa phải dự báo hằng ngày đầy đủ. Số năm và các đợt thời tiết không tăng; nhiều trạm cùng trận mưa không là nhiều mùa độc lập.
- 79 trạm có cửa sổtrain là giới hạn rộng hơn của nguồn hiện có, nhưng22 trạm bổ sung có lịch sử ngắn. Có thể thử mô hình chung ở nhóm này với protocol riêng, không tự gọi tất cả86 trạm đã sẵn sàng.
- Chưa đánh giá tổng quát sang trạm chưa thấy. Các37 trạm bổ sung đã có dữ liệu train trong bản 57; đây là kiểm định tương lai ở trạm đã biết.
- Trễtrạm 1 h/GFS8 h vẫn là giả định. Có7chu kỳ đầu2021 có timestamp sửa/chép archive sauissue; không suy ra đó là thờiđiểmpháthànhgốc.
- Dữ liệu qua kiểm tra ghép/cấu trúc, chưa chứng nhận cảm biến, vị trí lịch sử hoặc độtrễ vận hành. DEM là proxy, không phải cao độ khảo sát.
- 2024 là phần đánh giá phát triển;2025vẫn giữ kín,2026khôngfit/tuning.

## File và tái tạo

Dataset private: `data/processed/gfs_station_57_2026_11_10/gfs_vrain_pilot.parquet`. Mô hình và per-timepredictions ở `data/operational/gfs_station_57_2026_11_10/`.

Chạy `scripts/prepare_gfs_station_expansion.py`; đặt `PBL6_GFS_EXPERIMENT=gfs_station_57_2026_11_10` trước các script build/validate/run/GRU/verify. Nguồn GFS dùng chung chỉ đọc. Publisher của bản mở rộng là `scripts/publish_gfs_station_expansion.py`.

[Protocol](protocol.json), [QC/cohort](cohort_expansion_audit.json), [ghép mẫu](dataset_audit.json), [kiểm tra nguồn](verification.json), [replay mô hình](model_verification.json), [toàn bộ nhóm đánh giá](cohort_scope_metrics.csv), [so sánh ghép cặp20 trạm](matched_original20_bootstrap.csv), [lượng mưa](point_metrics.csv), [xác suất](probability_metrics.csv), [sự kiện](event_metrics.csv).
