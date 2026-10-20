# Rà soát Bi-LSTM trên nhánh dev

Ngày 20/10/2026. Phạm vi: commit `fe27756` (BI-LSTM), đối chiếu với main `d3f3936`. Đây là rà soát code, dữ liệu và checkpoint đã lưu; không huấn luyện lại, không chấm mô hình trên năm 2025. Không sửa code huấn luyện của thành viên.

## 1. Trạng thái Git

- Đã commit và push 26 tệp code, tài liệu, báo cáo tổng hợp lên main: `d3f39360b8ab28e88be4b56310fbae10db8b9db7`.
- Đã kiểm tra 22 kiểm thử liên quan trước khi push. Không đưa dữ liệu vùng, checkpoint hoặc tệp khóa Office vào commit.
- Đã chuyển workspace sang nhánh dev, theo dõi origin/dev, HEAD `fe27756`.
- Hai nhánh đã tách: main có 3 commit riêng, dev có 1 commit riêng. Chưa merge hoặc sửa lịch sử nhánh nào.

## 2. E0–E7 trên dev đang dùng gì?

**Đúng: bộ thí nghiệm E0–E7 được thêm trong commit này dùng chuỗi full_features cũ, không dùng nhãn hoặc đầu vào trung bình 93 ô.** Nói toàn bộ các biến đều là quan trắc tại một điểm thì chưa chính xác: một số biến cũ là trung bình các hộp vùng. Tuy nhiên dữ liệu không có chiều không gian 93 ô.

Các bản LOCAL, COLAB và Tweedie đều đọc `data/danang_full_features_2015_2026.parquet`. SHA-256 của file này và bản `data/processed/danang_full_features_2015_2026.parquet` trên máy trùng nhau:

`a3f9e665734be45fff2517dde0469e2fed1fd5dbec7620610d4938fd148ddfd1`

File có 102.264 hàng và 16 cột, kể cả datetime. Nhãn là cột `precipitation` cũ từ Open-Meteo, không phải `y_gsmap_gc_mm` hoặc `y_region_gc_mm`. Cấu hình nguồn cũ dùng tọa độ 16,0544°B, 108,2022°Đ; một số biến ERA5 bổ sung lấy từ hộp vùng. Không mặc định chuỗi Open-Meteo này là ERA5 thuần.

| Nội dung | E0–E7 mới trên dev | V1/V2 trên main |
| --- | --- | --- |
| Đơn vị mẫu | Một chuỗi thời gian cũ | Một chuỗi tổng hợp từ tập 93 ô |
| Nhãn | Mưa Open-Meteo cũ | Mưa GSMaP Gauge trung bình vùng |
| Phân bố không gian | Không giữ riêng các ô | V1 giữ trung bình; V2 thêm phân bố/tiểu vùng |
| Thử nghiệm vừa có | Bi-LSTM, các nhóm E0–E7 | Pilot LightGBM so đầu vào cũ/mới; chưa chạy E0–E7 trên V1/V2 |

Repo vẫn có pipeline Bi-LSTM lưới từ trước ở `scripts/pilot_bilstm_v2.py` và `src/bilstm_v2.py`. Pipeline đó đọc DatasetV2/WindowSampler, có chiều ô. Không nên đồng nhất nó với các notebook E0–E7 mới.

## 3. Cách thiết kế mô hình và nhóm đặc trưng

- Lịch sử 24 giờ, dự đoán 6 lượng mưa giờ tiếp theo; tổng 3/6 giờ dùng để chấm.
- Bi-LSTM hai lớp, hidden 64, ghép hidden cuối hai chiều; đầu lượng mưa có Softplus.
- Huấn luyện 2015–2021, validation 2022, đánh giá 2023, chia theo năm giờ Việt Nam. Năm 2023 đã được dự án xem nhiều lần, nên là đánh giá khám phá chứ chưa là kiểm định độc lập mới.
- Ba seed 42/43/44; LOCAL tối đa 15 epoch, batch 128; COLAB tối đa 20 epoch, batch 256; patience 4.
- Min-max fit trên train; delta dùng hiệu lùi; tạo cửa sổ chung dựa trên các biến của E7 rồi chọn tập con cho từng E. Đây là các điểm thiết kế hợp lý.

| Nhóm | Đặc trưng trong notebook |
| --- | --- |
| B | Nhiệt độ, mưa quá khứ, tốc độ gió, RH, áp suất; delta của 5 biến đó; tháng |
| A | CAPE, CIN, TCWV, q850, độ ẩm đất |
| M | u850, v850 |
| C | SST; ONI đã bị bỏ |

Bốn biến lịch sin/cos giờ và ngày trong năm được thêm chung. Vì vậy số đầu vào thực tế của E0/E1/E2/E7 lần lượt là 15/20/17/23.

Tên nhóm cần diễn giải vừa mức: M hiện chỉ là gió tầng thấp, chưa phải chỉ số hoàn lưu gió mùa quy mô lớn; C chỉ có SST, chưa kiểm tra ENSO/MJO. Giữ Bi-LSTM là khả thi, nhưng đổi nhãn/phạm vi mẫu là đổi bài toán và phải chạy lại phép so trên cùng dữ liệu.

## 4. Các lỗi ảnh hưởng kết luận

### 4.1. Bản MSE chấm trên thang căn bậc hai nhưng ghi mm

Trong `bilstm_factorial_e0_e7_LOCAL.py`, dòng 354–357 tạo nhãn sqrt(y) cho train/validation. Dòng 485–486 cũng chuyển nhãn test sang sqrt(y). Tuy nhiên `predict_amount`, từ dòng 325, trả thẳng nhãn và đầu ra mô hình mà không bình phương lại. Các hàm tổng và đánh giá sau đó cộng các căn bậc hai thay vì cộng lượng mưa mm. Bản COLAB và hai notebook MSE có cùng lỗi.

Hệ quả: RMSE/MAE và ngưỡng CSI ghi là mm trong đường code này không có cách diễn giải vật lý đang ghi trên bảng. Không dùng chúng để so với mưa thật hoặc kết quả vùng V1/V2.

Ví dụ trực tiếp: chấm lại checkpoint E0 seed42 trên 8.731 cửa sổ năm 2023, đường code cũ cho RMSE tổng 6 giờ = 1,469 trên tổng căn bậc hai; bình phương đầu ra từng giờ rồi cộng theo mm cho RMSE = 3,462 mm. Đây là hai đại lượng khác nhau, không phải mô hình đột nhiên kém đi.

Ngoài ra, `val_rmse_6h` ở dòng 378 tính trung bình sai số trên từng phần tử giờ, không tính tổng 6 giờ như tên biến/nhật ký. Đổi ngược khi suy luận chưa sửa được tiêu chí chọn epoch trước đó; muốn kết quả theo tiêu chí mới phải huấn luyện/chọn epoch lại.

### 4.2. Persistence của bản MSE không khớp cửa sổ

`PERS_TEST` được tạo cho mọi dòng dữ liệu test, còn nhãn đã qua lọc cửa sổ. Năm 2023 có 8.760 dòng nhưng chỉ 8.731 cửa sổ hợp lệ. Phép trừ ở dòng 526 của bản LOCAL dùng hai kích thước khác nhau và gây lỗi broadcast. Cần ghép baseline theo issue timestamp thực tế của từng cửa sổ, không theo vị trí raw.

### 4.3. Persistence trong notebook Tweedie sao chép nhãn cần dự đoán

Cell tổng hợp, bắt đầu quanh dòng JSON 1004 của `bilstm_factorial_tweedie_COLAB.ipynb`, lấy `y_test[3:N]` rồi chèn 3 số 0 lên đầu; tương tự với 6 giờ. Với hàng i >= 3, baseline 3 giờ trở thành đúng tổng nhãn của chính hàng i; với i >= 6, baseline 6 giờ cũng vậy.

Đây là sử dụng nhãn cần dự đoán trong đối chứng, không phải persistence từ mưa quá khứ. Đã kiểm tra phép chỉ số bằng ví dụ mảng nhỏ: phần sau padding bằng đúng nhãn. Lỗi này nằm ở baseline, không phải bằng chứng rằng đầu vào mô hình Tweedie cũng lấy tương lai. Notebook Tweedie dùng nhãn mm trực tiếp nên không có lỗi sqrt của bản MSE, nhưng baseline này vẫn làm phép so không hợp lệ.

### 4.4. Checkpoint và CSV chưa truy vết được cùng lượt chạy

Commit lưu CSV của 8 cấu hình × 3 seed, nhưng chỉ có 9 checkpoint E0/E1/E2. Ba notebook không lưu execution_count hoặc output đã chạy. Chưa thấy checkpoint/nhật ký khớp của notebook Tweedie E0–E7 trong commit này; `_out.txt` là traceback lỗi Unicode khi chạy một script phân tích không có trong commit, không chứng minh đã chạy 93 ô.

Đã nạp 9 checkpoint bằng `torch.load(weights_only=True)`, dựng đúng lớp mô hình và chạy lại suy luận CPU với scaler trong từng checkpoint:

- 8/9 checkpoint có best_epoch khác dòng CSV tương ứng.
- 0/9 tái lập được các chỉ số CSV tương ứng trong ngưỡng sai khác 0,00002 theo đường code hiện tại.

Điều này cho thấy chưa ghép được code, checkpoint, bảng kết quả thành cùng một lượt chạy; chưa xác định nguyên nhân là checkpoint từ lượt khác hay code chạy thực tế khác bản đã commit. Không coi bảng CSV đã được xác thực.

## 5. Những gì vẫn có thể dùng lại

Chấm lại theo mm thật các checkpoint đang có, lấy trung bình điểm qua ba seed:

| Checkpoint | RMSE tổng 3 giờ (mm) | RMSE tổng 6 giờ (mm) |
| --- | --- | --- |
| E0 | 1,9515 | 3,4607 |
| E1 | 1,8846 | 3,2557 |
| E2 | 1,9331 | 3,4063 |

Đây chỉ là chẩn đoán của các checkpoint đã lưu trên nhãn cũ, chưa phải bảng CSV được đính chính, chưa có khoảng tin cậy theo khối và chưa sửa việc chọn epoch. Có dấu hiệu E1 tốt hơn E0 trong phép chẩn đoán này, nhưng không suy ra mưa vùng hoặc so trực tiếp với RMSE của V1/V2 vì khác nhãn, phạm vi, mẫu và mô hình.

Kiến trúc Bi-LSTM, bộ nhóm E0–E7, chuẩn hóa train-only và cách dùng chung cửa sổ có thể giữ lại. Cần thay hợp đồng dữ liệu và sửa đánh giá trước khi chạy dài.

## 6. Hướng thống nhất hai nhánh

1. Chốt đầu ra: mưa trung bình vùng hay mưa từng ô; xác định ranh vùng và nhãn tham chiếu. V1/V2 hiện vẫn có giới hạn về ranh và kiểm chứng nhãn, chưa mặc định là bộ cuối hoàn hảo.
2. Nếu chọn trung bình vùng, đưa V1/V2 vào cùng loader cho Bi-LSTM. Giữ bộ cũ làm một đối chứng riêng, không dùng điểm của nhãn cũ làm kết quả dự báo toàn Đà Nẵng.
3. Sửa thang đo, tiêu chí chọn epoch, persistence theo issue timestamp và loại việc sao chép nhãn đích; dùng bộ chỉ số chung của repo.
4. Lưu run ID, commit, checksum dữ liệu, feature list, scaler, split, history và checkpoint đi cùng nhau. Báo cáo nhiều năm/mùa và bootstrap theo khối; tiếp tục giữ kín năm 2025 để chọn mô hình.
5. Sau đó chạy E0–E7 cùng kiến trúc, ngân sách và mẫu. Không cần bỏ Bi-LSTM hoặc giả định thêm đặc trưng phải cải thiện.

Lưu ý quản lý repo: commit dev đã track `data/danang_full_features_2015_2026.parquet` và một tài liệu trong data, khác quy ước dữ liệu ngoài Git. Lượt này không đưa các tệp đó vào main, không tự xóa hay viết lại lịch sử dev.

Chẩn đoán và script suy luận đọc lại checkpoint lưu riêng tại `data/operational/dev_bilstm_review_2026_10_20/`, ngoài Git. Báo cáo rà soát commit dev `fe27756` được công bố trên main theo yêu cầu người dùng; không merge dữ liệu/checkpoint hoặc sửa lịch sử dev.
