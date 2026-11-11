# Slide dự báo mưa hằng ngày v2 — 11/11/2026

[PowerPoint chỉnh sửa được](PBL6_MUA_TRAM_HANG_NGAY_V2.pptx) · [Xem bằng trình duyệt](PBL6_MUA_TRAM_HANG_NGAY_V2.html) · [Ghi chú thuyết trình](GHI_CHU_THUYET_TRINH.md)

**41 slide: 32 slide chính và 9 phụ lục.** Bản này trình bày thí nghiệm lịch hằng ngày tại 57 trạm, GFS + Vrain, LightGBM N0–N5 và GRU N3/N5. Các điểm số đều thuộc **dev 2024**, không phải kiểm định cuối 2025. Không lấy số từ pilot lịch tuần hay các bộ mưa vùng trước đây.

## “Giữ kín 2025” là gì?

Để riêng năm 2025 làm phép kiểm tra sau khi chọn và khóa phương án. Năm đó đã qua về lịch, nhưng chưa được dùng để chọn mô hình, chỉnh tham số, chọn cutoff hoặc chấm điểm trong thí nghiệm hiện tại. Dataset thí nghiệm mới được dựng và kiểm chứng cho 2021–2024; **chưa có bảng điểm test 2025**, cũng chưa khẳng định đã chuẩn bị đủ bộ test này.

| Thời gian | Vai trò |
| --- | --- |
| 2021–2022 | Học mô hình; chọn tham số bằng bốn fold thời gian trong train |
| 2023 | Hiệu chỉnh xác suất và chọn ngưỡng quyết định |
| 2024 | Đánh giá để phát triển, so sánh nhóm biến và nhận diện giới hạn |
| 2025 | Dành kiểm định cuối sau khi khóa phương án |

Nếu xem điểm 2025 rồi sửa mô hình theo điểm đó, năm này trở thành dữ liệu phát triển và cần tập kiểm định khác. Khi phát lại dự báo năm 2025, vẫn được dùng mưa **quá khứ đã có trước issue** làm đầu vào; điều bị tránh là dùng nhãn tương lai hoặc điểm test để học/chọn phương án. Đây là nguyên tắc tách phát triển khỏi kiểm định trong [tài liệu cross-validation của scikit-learn](https://scikit-learn.org/stable/modules/cross_validation.html).

## Cách trình bày

- **Báo cáo ngắn khoảng 15–20 phút:** slide 1–4, 9–10, 15, 17, 21, 23–28, 32; có thể chọn bớt bảng tùy thời lượng.
- **Thảo luận kỹ:** dùng 32 slide chính; mở ghi chú của từng slide trong PowerPoint. Phần ghi chú giải thích thuật ngữ, ví dụ, nguồn và giới hạn.
- **Trả lời câu hỏi:** slide 33–39 có đầy đủ chỉ số cho năm đối chứng, sáu cấu hình LightGBM và hai GRU; slide 40 so cutoff cố định 0,5 với cutoff chọn từ 2023; slide 41 có liên kết nguồn.

| Slide | Nội dung |
| --- | --- |
| 1–4 | Mục tiêu, kết luận chính, một mẫu đầu vào và ba nhãn ngày |
| 5–8 | Nguồn, clock 19h, độ trễ và phạm vi 57 trạm |
| 9–12 | Train/cal/dev/test, giữ lại 2025, mask chung, tuning theo thời gian |
| 13–20 | Đối chứng, mean/median, N0–N5, LightGBM/GRU, tuning, seed, xác suất |
| 21–22 | Ý nghĩa RMSE/MAE/Bias/BS/BSS/CSI/POD/FAR và khoảng tin cậy |
| 23–30 | Kết quả 2024, mưa lớn, đóng góp đặc trưng và độ nhạy trễ |
| 31–32 | Kiểm chứng, giới hạn và quy trình trước khi mở test |
| 33–41 | Bảng đầy đủ và tài liệu nguồn |

**Quy ước số:** dấu phẩy là phần thập phân. Bảng lượng dùng mm/24h; RMSE chính của đầu mean, MAE chính của đầu median. Hai đầu cùng ước lượng ba nhãn lượng mưa thật, không phải hai bộ quan trắc khác nhau. In đậm trong bảng điểm là tốt nhất **trong những dòng đang hiển thị**; in đậm ở bảng chênh lệch là CI 95% nằm dưới 0. Màu đỏ chỉ BSS âm hoặc FAR/Bias cần chú ý, không phải giá trị thắng. Macro tính tại từng trạm rồi lấy trung bình; riêng bảng lượng mưa lớn slide 30 là micro trên tập con đã ghi rõ.

POD không có mức “0,4 là tốt” chung cho mọi nơi. Đọc cùng FAR, CSI, hạn dự báo, ngưỡng mưa và số sự kiện. Có nhiều trạm trong cùng một đợt mưa nên số mẫu trạm–ngày không bằng số trận mưa độc lập.

## Tệp và kiểm tra

PDF để gửi nhóm nằm ngoài Git theo quy định repo: `data/operational/gfs_daily_slides_2026_11_11/PBL6_MUA_TRAM_HANG_NGAY_V2.pdf`. Các ảnh `XEM_TRUOC_*.png` ghép từ slide do PowerPoint xuất thực tế.

Nguồn số liệu: [báo cáo và CSV daily-v2](../gfs_station_daily_v2_2026_11_10/README.md). `build_manifest.json` ghi SHA nguồn và ánh xạ từng ô metric về dòng CSV. `validation.json` ghi kiểm tra số liệu, chữ in đậm, nội dung PPTX chỉnh sửa được, ghi chú, bố cục PowerPoint/HTML và bảo toàn slide người dùng. Slide mới không huấn luyện hoặc chấm năm 2025.

Tái tạo từ thư mục gốc repo:

```powershell
.venv\Scripts\python.exe -X utf8 scripts/build_gfs_daily_slides.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/render_gfs_daily_slides.ps1
.venv\Scripts\python.exe -X utf8 scripts/validate_gfs_daily_slides.py
```

Xuất PDF/PNG cần Microsoft PowerPoint cài tại máy; kiểm tra HTML dùng Chrome. Không chạy lại builder nếu đã chỉnh trực tiếp bản PPTX này mà chưa lưu bản riêng.
