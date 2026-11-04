# Phân tích cơ sở LightGBM và cách ưu tiên POD/FAR cho dự đoán mưa vùng

Ngày 21/10/2026. Đây là rà soát và trình bày lại bằng chứng phát triển đã có; không đổi mô hình, dữ liệu hoặc tiêu chí, không chấm năm 2025.

## 1. Có paper ứng dụng LightGBM trong dự đoán mưa không?

Có. Cần phân biệt paper thuật toán (A1) với paper ứng dụng mưa, và phân biệt dự đoán tương lai với ước lượng mưa đồng thời. Ba nguồn sơ cấp đã đối chiếu:

| Nguồn | Nội dung liên quan | Giới hạn khi dùng làm cơ sở |
| --- | --- | --- |
| R1, He và cs., 2022 | Mưa ngày kế tiếp ở Cairns; LightGBM học thành phần dư trong mô hình lai STL-ML. | Có mưa quá khứ; không phải LightGBM đơn lẻ hoặc vùng 93 ô. |
| R2, Iwase & Takenawa, 2024 | LightGBM dự đoán lượng mưa vùng núi Nhật Bản từ forecast lân cận và quan trắc. | Dự đoán tại điểm; có forecast đầu vào. |
| R3, Qian & Jia, 2023 | LightGBM/XGBoost dự đoán giáng thủy mùa đông ở Trung Quốc. | Hạn mùa, không chứng minh hiệu quả 24–72 giờ. |

R1/R3 được đối chiếu bằng phần công khai của nhà xuất bản; không gọi là đã audit toàn bộ phương pháp. R2 có bài/PDF chính thức. Tài liệu literature.json lưu DOI, đường dẫn và phạm vi. Không sao chép PDF hoặc điểm của paper vào bảng dự án. Một mô hình được dùng trong paper là cơ sở hợp lý để thử, chưa bảo đảm phù hợp dữ liệu/nhãn/vùng/lead của nhóm.

Trong dự án, LightGBM học từ cùng nguyên liệu khí tượng quá khứ và lịch với TFT, qua thống kê lịch sử. Hai bên chấm cùng nhãn/mốc/lead. Đây là đối chứng thật; còn khác biểu diễn chuỗi/bảng, loss và số seed, nên không gọi là kiểm định chỉ thay duy nhất kiến trúc. Câu hỏi chính về đóng góp biến vẫn có giá trị nếu cây tốt hơn mạng neural.

## 2. Dev trước đó có ưu tiên POD/FAR không?

Đã đọc trực tiếp blob tại origin/dev commit `fe27756ff57e90b09553f4e5c62d17aa74efee89`, không checkout hoặc chạy notebook. Hai tệp triển khai được rà soát là LOCAL.py và Tweedie COLAB.ipynb; có đối chiếu notebook LOCAL và bảng summary. Hồ sơ SHA ở dev_metrics_audit.json.

- LOCAL.py báo POD/FAR cho tổng 6 giờ ≥10 mm, cùng CSI và RMSE/MAE.
- Notebook Tweedie bổ sung nhiều cột 1h, tổng 3/6h và max giờ; không lấy nhóm max giờ thay tổng 24h vùng.
- Các POD/FAR lượng mưa được tính bằng quy tắc lượng dự đoán ≥ngưỡng mưa. Bảng chính TFT hiện dùng xác suất ≥ngưỡng τ chọn trên calibration.
- Việc bảng có POD/FAR nổi bật không đồng nghĩa early stopping tối ưu POD/FAR. Mã hai tệp chọn bằng RMSE phần tử trên đầu ra giờ; biến tên val_rmse_6h nhưng chưa cộng tổng 6h tại phép tính đó.
- Trong evaluate xác suất của notebook Tweedie, thấy BS và CSI_prob với p≥0,5; chưa thấy BSS được tính trong hàm ấy, dù docstring nhắc BSS. Không đồng nhất BS và BSS hoặc coi tên cột là bằng chứng tính đúng.

Đây là audit có phạm vi, không khẳng định mọi mã của dev hoặc bản thành viên chưa push đều giống vậy. Nhãn cũ precipitation/full_features tại điểm khác nhãn vùng GSMaP hiện tại; ngưỡng 10mm/6h không tương đương 16mm/24h vùng. Không so trực tiếp POD/FAR hai nhánh để nói mô hình nào tốt hơn.

## 3. POD/FAR có cần ở hạn 24–72 giờ không?

Có. Chúng áp dụng cho sự kiện được định nghĩa rõ ở mọi hạn, không riêng nowcasting. Với y là tổng mưa trung bình vùng trong một khoảng 24 giờ và q là ngưỡng mưa, đặt o=1 nếu y≥q. Sau đó đặt quyết định d=1 nếu xác suất p≥τ. Từ d/o đếm:

- H: báo có và thực có; M: báo không nhưng thực có.
- F: báo có nhưng thực không; TN: báo không và thực không.
- POD=H/(H+M): tỷ lệ bắt được sự kiện thực, lớn hơn tốt hơn.
- FAR=F/(H+F): tỷ lệ báo nhầm trong những lần báo có, nhỏ hơn tốt hơn.
- CSI=H/(H+M+F): gộp trúng, bỏ sót, báo nhầm, lớn hơn tốt hơn.

FAR ở đây là false alarm ratio, không phải false positive rate F/(F+TN). Nếu không báo có lần nào, FAR không xác định; không tự điền 0. POD/FAR phụ thuộc ngưỡng và tần suất sự kiện; cần báo n/events, lead, mùa và quy tắc chọn τ. Khi ngưỡng làm bắt thêm sự kiện, thường có đánh đổi báo nhầm; FAR không nhất thiết đơn điệu trên một tập hữu hạn. CSI liên hệ toán học với POD/FAR, không phải một nguồn bằng chứng độc lập thứ ba.

## 4. Vì sao không tối ưu riêng POD hoặc FAR?

Ví dụ tự tạo 100 ngày có 10 sự kiện: luôn báo có đạt POD=1 nhưng FAR=0,90, CSI=0,10. Luôn báo không có POD=0, CSI=0 và FAR không xác định. Vì thế một con số đơn lẻ có thể thưởng cho hành vi không hữu ích.

Ví dụ thực E7 ngày 1, cùng 1.075 mốc/114 sự kiện:

| Mô hình | Trúng | Bỏ sót | Báo nhầm | POD | FAR | CSI | BSS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TFT | **73** | 41 | 66 | **0.640** | 0.475 | 0.406 | 0.246 |
| LightGBM | 60 | 54 | **32** | 0.526 | **0.348** | 0.411 | 0.303 |

TFT bắt thêm 13 sự kiện nhưng thêm 34 báo nhầm. POD cao hơn chưa đủ để gọi là mô hình tốt hơn. Cả hai đang ở τ chọn CSI trên calibration riêng; chưa phải so tại cùng POD, cùng FAR hoặc cùng chi phí. Các số đếm được tái tạo từ n/events/POD/FAR full precision trong aggregate, kiểm tra khớp CSI; không đọc nhãn hoặc dự đoán từng mốc.

## 5. Đề nghị vai trò từng nhóm metric

| Câu hỏi | Nhóm metric | Vai trò trong báo cáo hiện tại |
| --- | --- | --- |
| Lượng mưa vùng dự đoán lệch bao nhiêu? | RMSE, MAE, Bias | Hiển thị rõ và đọc cùng; không bỏ vì BSS tăng. |
| Xác suất sự kiện tốt hơn tham chiếu không? | BS/BSS, reliability | BSS16 là phép kiểm định chính đã khóa; reference chỉ học train. |
| Quyết định báo có bỏ sót/báo nhầm thế nào? | CSI + POD + FAR | Luôn báo cả ba cùng n/events và quy tắc τ. |
| Cải thiện có chắc trong tập ngày hiện tại? | Paired block CI | Kiểm định hiệu số đúng phép so, không suy từ in đậm. |

Giữ protocol đang khóa, chưa tự nâng POD hoặc FAR lên thành tiêu chí duy nhất sau khi thấy điểm. POD/FAR là chẩn đoán thiết yếu cạnh CSI. Ngay cả CSI cũng không thay thế được mục tiêu sử dụng và đánh giá xác suất/lượng mưa.

Nếu mục tiêu chính bài báo được chốt là cải thiện lượng mm, nên đăng ký RMSE cùng MAE/Bias cho câu hỏi đó trước holdout, và xử lý đa so sánh nếu thêm phép kiểm định chính. Hiện epoch TFT được chọn bằng Brier calibration, nên kết quả lượng mm thuộc pipeline được chọn theo tiêu chí xác suất; không mô tả như đã tối ưu RMSE riêng.

Nếu mục tiêu là cảnh báo hạn chế bỏ sót, trước hết cần yêu cầu về POD tối thiểu và mức báo nhầm chấp nhận từ người dùng/nghiệp vụ; sau đó chọn τ trên calibration theo ràng buộc rồi khóa. Chưa có yêu cầu chi phí để tự đặt một mức như POD≥70% làm tiêu chuẩn thật. Thời hạn 24–72h tự nó không quyết định POD quan trọng hơn FAR.

## 6. BSS và sai số lượng mm cần được đọc ra sao?

BS=mean((p-o)^2); BSS=1-BS/BS_reference. BSS>0 tốt hơn khí hậu tham chiếu, BSS<0 kém hơn. BSS 0,246 không phải accuracy 24,6%. Khí hậu hiện theo tháng đích/lead học từ train. Reliability đọc xác suất so tần suất thực, kèm số mẫu trong bin.

RMSE=sqrt(mean((f-y)^2)), MAE=mean(abs(f-y)), Bias=mean(f-y). RMSE/MAE nhỏ hơn tốt hơn, Bias gần 0; Bias âm là dự báo thiếu. BSS/POD tốt không tự chứng minh lượng mm tốt. Không dùng MAPE với nhiều ngày mưa 0 hoặc accuracy bị ngày khô chi phối làm bằng chứng chính. Đầu mm và xác suất hiện chưa chung một phân phối thống nhất; CSI của f≥q khác CSI chính của p≥τ.

## 7. Tín hiệu hiện có và phạm vi kết luận

Đã chạy 72 TFT/24 LightGBM; 96/96 replay. Ngày 1, thêm riêng A/M vào TFT tăng BSS lần lượt +0.0853/+0.1443; CI 99,44% điều chỉnh [+0.0022;+0.1607] và [+0.0681;+0.2329]. C chưa rõ. Đây là 9 phép chính, khối 7 ngày/20.000 bootstrap; khối 14 ngày cùng phân loại. Chưa kiểm định M−A. Ngày 2 chưa có CI chính tương tự trên 0; ngày 3 mọi E/họ có BSS âm.

Giới hạn: footprint 93 ô xấp xỉ, nhãn vệ tinh chưa kiểm chứng đầy đủ, ít sự kiện 50/100, development đã xem trước, không chắc đầu vào ERA5 có sẵn lúc phát hành thật. Chỉ nhìn POD ngày 3 vẫn có thể che BSS âm. Bootstrap điều kiện mô hình đã fit, không bao phủ mọi bất định nhãn/vùng/huấn luyện.

## 8. Quy tắc in đậm trong slide

- Bảng so hai mô hình cùng ngày: đậm điểm tốt hơn trong cặp theo chiều đã ghi.
- Bảng tám E trong cùng mô hình/ngày: đậm điểm tốt nhất theo số hiển thị; bằng nhau cùng đậm. Bias chọn trị tuyệt đối nhỏ nhất.
- BSS âm màu đỏ; ít âm nhất vẫn kém khí hậu. In đậm không có nghĩa kết quả đã có ý nghĩa thống kê.
- Bảng số đếm nêu các số cần đối chiếu; chú thích rõ. Phép kiểm định A/M có CI riêng, không suy CI từ tô màu.
- Sáu bảng phụ lục có đủ 48 dòng và 7 metrics; Excel có chi tiết ngưỡng/năm/mùa/seed, không giấu điểm kém.

## 9. Nguồn tham khảo

- [R1] He, Zhang & Chew (2022). [Modeling and predicting rainfall time series using seasonal-trend decomposition and machine learning](https://www.sciencedirect.com/science/article/pii/S095070512200555X).
- [R2] Iwase & Takenawa (2024). [Interpolation of Mountain Weather Forecasts by Machine Learning](https://www.jstage.jst.go.jp/article/ipsjjip/32/0/32_873/_article/-char/en).
- [R3] Qian & Jia (2023). [Seasonal forecast of winter precipitation over China using machine learning models](https://www.sciencedirect.com/science/article/abs/pii/S0169809523003587).
- [A1] Ke et al. (2017). [LightGBM: A Highly Efficient Gradient Boosting Decision Tree](https://proceedings.neurips.cc/paper_files/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html).
- [A2] Lim et al. (2021). [Temporal Fusion Transformers for Interpretable Multi-horizon Time Series Forecasting](https://arxiv.org/abs/1912.09363).
- [A3] Zhou et al. (2021). [Informer: Beyond Efficient Transformer for Long Sequence Time-Series Forecasting](https://ojs.aaai.org/index.php/AAAI/article/view/17325).
- [A4] Tác giả Informer (2021). [Mã mô hình Informer chính thức](https://github.com/zhouhaoyi/Informer2020/blob/main/models/model.py).
- [V1] Pertti Nurmi (2007). [Verification of Categorical Forecasts](https://www.ecmwf.int/sites/default/files/elibrary/2007/15490-verification-categorical-forecasts.pdf).
- [V2] ECMWF (2026). [Forecast User Guide, Section 12.B: Statistical Concepts — Probabilistic Data](https://confluence.ecmwf.int/spaces/FUG/pages/673551875/Section%2B12.B%2BStatistical%2BConcepts%2B-%2BProbabilistic%2BData).