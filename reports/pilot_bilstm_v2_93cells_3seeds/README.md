# Batch Bi LSTM ba seed tại Đà Nẵng

93 ô; S0/S1/S4; seed 42/43/44. Đây là ablation thông tin, chưa là so Bi-LSTM với TFT.
Không chấm test 2025. Mùa hè–thu, tổng 0–3 h; các hàng là trung bình dự báo của 3 seed.

| Cấu hình | CSI ≥10 mm | BSS ≥1 mm |
| --- | ---: | ---: |
| S0 | 0.1258 | 0.1875 |
| S1 | 0.2228 | 0.1968 |
| S4 | 0.1360 | 0.2488 |

Chi tiết và khoảng tin cậy: `scores.csv`, `paired_bootstrap.json`, `run.json`.
Báo cáo tự sinh; chưa có diễn giải mới của agent. Checkpoint/dự báo nằm ngoài Git.

## Diễn giải sau kiểm tra

Ngày 13/10/2026. Trên 68.448 cửa sổ mùa hè–thu 2023, tổng 0–3 h:

- S1 so với S0: CSI tăng 0,0970; khoảng tin cậy bootstrap 95% [0,0193; 0,1407]. Tín hiệu cải thiện có cả trong batch 30 ô. Chênh lệch BS giữa hai cấu hình chưa chắc chắn.
- S4 so với S0: BS giảm 0,00805; khoảng tin cậy [0,00227; 0,01387]. So với S1, BS giảm 0,00683; khoảng tin cậy [0,00171; 0,01222]. S4 có lợi ích xác suất.
- CSI S1 cao hơn S4 ở ước lượng điểm, nhưng khoảng tin cậy chênh lệch chứa 0; chưa kết luận S1 thắng S4 về CSI.

Các điểm là của trung bình dự báo 3 seed. Bootstrap theo khối ngày giữ các ô cùng ngày đi cùng nhau; chưa mô tả đầy đủ bất định giữa seed. Nhãn là GSMaP hiệu chỉnh, đầu vào tương lai S4 là ERA5 perfect prog; chưa là kiểm định vận hành hay kiểm chứng mưa tại điểm.

Bước ưu tiên là baseline hiệu chỉnh xác suất và tabular cùng mẫu, kiểm tra đầu ra lượng mưa/hiệu chỉnh trên 2022, rồi bảng 2×2 Bi-LSTM/TFT ở 6/72 h. Không chọn mô hình bằng test 2025. Trước app cần hợp đồng dữ liệu live và T-OPS.

