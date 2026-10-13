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
