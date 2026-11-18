# Báo cáo slide: dữ liệu, huấn luyện và kết quả trên 57 trạm

**55 slide: 43 slide chính và 12 phụ lục**, theo thí nghiệm GFS + Vrain ngày 10/11/2026. Đây là báo cáo kết quả đã chạy, không phải kết quả huấn luyện mới hoặc bản tối ưu siêu tham số.

- [PowerPoint chỉnh sửa được](PBL6_DU_BAO_MUA_57_TRAM.pptx): bảng và chữ là đối tượng PowerPoint, có ghi chú cho từng slide.
- [Bản HTML](PBL6_DU_BAO_MUA_57_TRAM.html): mở bằng trình duyệt, dùng phím trái/phải để chuyển slide.
- [Ghi chú thuyết trình](GHI_CHU_THUYET_TRINH.md): giải thích bằng lời, ví dụ và cách diễn đạt các giới hạn.
- Xem nhanh: [slide 1–20](XEM_TRUOC_01.png), [21–40](XEM_TRUOC_02.png), [41–55](XEM_TRUOC_03.png).
- [Kiểm tra số liệu và bố cục](validation.json), [kiểm tra bằng PowerPoint](native_render_audit.json), [nguồn và SHA256](build_manifest.json).

Bản PDF đã xuất bằng PowerPoint nằm ngoài Git theo quy ước repo: `data/operational/gfs_station_slides_2026_11_10/PBL6_DU_BAO_MUA_57_TRAM.pdf`.

## Nội dung và cách trình bày

| Slide | Nội dung | Câu hỏi được giải thích |
| --- | --- | --- |
| 1–6 | Mục tiêu, 57 trạm, vai trò nguồn, ví dụ một mẫu | X và y là gì? Dự báo trạm hay vùng? |
| 7–14 | Mốc giờ, cộng nhãn, mưa GFS, nội suy, A0–A3 | Thông tin nào có trước issue? Vì sao A2 có 25 biến? |
| 15–18 | Train/cal/dev, số mẫu, QC và các đối chứng | Chia dữ liệu thế nào? Có dùng tương lai không? |
| 19–22 | LightGBM, tham số, dừng sớm, Platt | Học bao nhiêu mô hình? Chọn số cây bằng gì? |
| 23–28 | Điều kiện chạy GRU, tensor, loss, epoch và seed | Mạng nhận gì? Tinh chỉnh đã làm đến đâu? |
| 29–32 | MAE/RMSE/Bias, BS/BSS, CSI/POD/FAR và CI | Đọc các chỉ số như thế nào? |
| 33–40 | Bảng kết quả, thêm biến, khoảng tin cậy, mở rộng trạm | Cải thiện ở đâu, đánh đổi gì, chắc đến đâu? |
| 41–43 | Giới hạn, kết luận và bước tiếp | Có thể khẳng định điều gì? |
| 44–55 | Tên cột, bảng đầy đủ, audit và hỏi–đáp | Chi tiết để đối chiếu và bảo vệ báo cáo |

Nếu có **20–25 phút**, có thể chọn các slide: **1, 3, 4, 6, 7, 13, 15, 16, 19, 20, 22, 24, 27, 29, 31, 33, 35, 38, 41, 42**. Các slide còn lại dùng khi cần giải thích sâu. Mỗi slide đều có ghi chú; không cần đọc nguyên văn toàn bộ chữ trên màn hình.

## Những điều phải nói đúng khi báo cáo

**Đầu ra:** ba tổng mưa Vrain 24h riêng tại từng trạm, bắt đầu từ 19h Việt Nam; kèm hai xác suất vượt 1/50 mm cho mỗi ngày. Không phải mưa trung bình vùng hoặc ba tổng cộng dồn đến 24/48/72h. Một mẫu là `(trạm, thời điểm phát dự báo)`.

**Nguồn và chia tập:** GFS dự báo làm predictor, Vrain làm mưa quá khứ/nhãn, DEM làm proxy địa hình. Train 2021–2022, cal 2023, dev 2024. Có 5.032/2.582/2.782 mẫu trạm–issue; mọi cấu hình cùng mẫu. Lịch issue **mỗi 7 ngày**, chưa phải thí nghiệm phát hằng ngày. Năm 2025 giữ kín; 2026 không fit/tuning. Đây là đánh giá thời gian tương lai tại trạm đã có trong train.

**Tinh chỉnh:** siêu tham số cố định trong pilot. Đã chọn số cây/epoch bằng cal, hiệu chỉnh xác suất Platt và dùng điều kiện cal để mở thử nghiệm GRU. **Chưa GridSearch/Optuna**, chưa tối ưu ngưỡng quyết định. Cal dùng lại cho dừng sớm và Platt nên điểm cal không phải ngoài mẫu độc lập. LightGBM dừng theo **MAE cal**, GRU dừng theo **loss chung cal**.

**Kết quả:** macro MAE dev 2024, mm cho mỗi cửa sổ 24h:

| Phương pháp | Ngày 1 | Ngày 2 | Ngày 3 |
| --- | ---: | ---: | ---: |
| GFS gốc | 5,83 | 7,41 | 10,30 |
| LightGBM A2 | **5,28** | **6,72** | 8,44 |
| GRU A2 | 6,94 | 7,56 | **8,00** |

In đậm là thấp nhất trong **ba hàng này**; bảng đầy đủ còn A0/A1/A3. **CI 95% của A2−GFS ở cả ba hạn đều chứa 0**: có tín hiệu giảm MAE, chưa chứng minh cải thiện ổn định. GRU ngày 3 giảm sai số lượng nhưng BSS mưa ≥50 mm là khoảng **−0,210**, kém tham chiếu khí hậu. Không chọn một chỉ số để nói mô hình thắng toàn diện.

**Giới hạn mới được kiểm tra khi làm slide:** chưa ép thứ tự hai xác suất. A2 có 188/8.346 dòng dev với P(≥50)>P(≥1), khoảng 2,25%. Trong mẫu hiện tại không có quyết định mâu thuẫn tại cutoff 0,5. Không sửa dự báo hoặc điểm cũ; audit ở [training_audit.json](training_audit.json), giải thích ở slide 41 và 49. Bản GRU không có vi phạm quan sát được nhưng cũng chưa được ràng buộc bằng mã.

Độ trễ GFS 8h và trạm 1h vẫn là giả định. 57 trạm không có nghĩa đã chứng nhận phủ kín ranh Đà Nẵng; hai trạm có ít cửa sổ train theo lịch tuần. QC/replay đúng không thay thế chứng nhận cảm biến hay kiểm định cuối.

## Nguồn số liệu và tái tạo

Các bảng chính đọc từ [kết quả 57 trạm](../gfs_station_57_2026_11_10/): `point_metrics.csv`, `probability_metrics.csv`, `event_metrics.csv`, `paired_bootstrap.csv`, `fit_diagnostics.csv`, `gru_summary.json`. Mã huấn luyện được đối chiếu tại `scripts/run_gfs_station_pilot.py` và `scripts/run_gfs_station_gru.py`. Không pha điểm TFT/Informer hoặc nhãn CPC/GSMaP của hướng vùng cũ vào kết quả này.

Trên môi trường Windows của dự án, có PowerPoint và Chrome:

```powershell
.venv\Scripts\python.exe -X utf8 scripts/build_gfs_station_slides.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/render_gfs_station_slides.ps1
.venv\Scripts\python.exe -X utf8 scripts/validate_gfs_station_slides.py
```

Builder cần checkpoint và dự báo riêng để đối chiếu số cây/thứ tự xác suất. Bộ slide công khai chỉ chứa tổng hợp; không chứa dữ liệu quan trắc từng mốc, tọa độ, mật khẩu hoặc checkpoint. File PDF và ảnh render từng slide ở thư mục `data/operational/` được Git bỏ qua. Hai bộ slide người dùng đã chỉnh trước đó được giữ nguyên và kiểm tra SHA256.
