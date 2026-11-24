# PBL6 — bối cảnh hiện hành cho agent

Cập nhật 24/11/2026. Đọc file này trước, rồi `KE_HOACH_DU_AN.md` và `project_plan_v2.md`. Người dùng bắt đầu từ `README.md`.

## Hoàn thiện tại Đà Nẵng và so sánh kiến trúc

Người dùng ưu tiên Đà Nẵng. [Báo cáo bổ sung](reports/danang_system_2026_11_24/SO_SANH_MO_HINH.md) huấn luyện GRU R cho 1–6 giờ và Bi-LSTM N3 cho 1–3 ngày với ba seed. Chấm hồi cứu trên đúng 679.461 mẫu giờ/79 trạm và 18.723 mẫu ngày/57 trạm của 2025. LightGBM R giữ RMSE thấp nhất cả sáu giờ. GRU R giảm RMSE 0,007–0,028 mm so với Bi-LSTM R. Bi-LSTM N3 và GRU N3 chênh 0,06–0,11 mm RMSE, cả ba khoảng 95% còn chứa 0. Mô hình mặc định của app vẫn là LightGBM R/B. [Sáu sơ đồ và kiểm tra nguồn](reports/danang_system_2026_11_24/THIET_KE_HE_THONG.md). Bản Word mới là `data/operational/pbl6_bao_cao_cuoi_ky_2026_11_24/PBL6_BAO_CAO_CUOI_KY_DA_NANG.docx`.

Hai lần kiểm tra 20h20 và 22h20 ngày 24/11 ghi Vrain danh mục 200 và cả hai đường mưa 404. Kết quả tương tự khi hỏi ngày 12/11 đã có dữ liệu. Kiểm trực tiếp Parquet cho thấy mốc mưa hợp lệ cuối 19h 15/11 với 82 trạm. GFS có 19 chỉ mục ở lần kiểm tra. Ưu tiên kiểm tra đường thu được cấp cho Đà Nẵng và ghi thời gian thực nhận trước khi đánh giá lượt phát trực tiếp.

## Bản đồ chung và báo cáo chi tiết hai nhánh

Bản đồ tại `/` có một thanh 1–6 giờ và Ngày 1–3, cùng lớp xã/phường và mặc định 57 trạm chung. Phạm vi toàn bộ theo hạn là 79 trạm cho giờ và 57 cho ngày. Mốc 19h 12/11 có 57/57 trạm giờ và 55/57 trạm ngày trên tập chung. API `/api/forecast` ghép theo giờ phát chính xác, ghi chế độ và kỳ hiệu lực riêng rồi ẩn thực đo với khách. `/cuc-ngan` dẫn về thanh chung ở Giờ 1. Thêm bản giờ phát lại cùng các mốc ngày trong tệp private, tổng 9 lượt đủ hai nhánh. Kiểm Edge 1440×900, 390×844 và 320×780, gồm CSV sau đăng nhập, thiếu ra màu xám và chuyển đơn vị.

[Đối chiếu và báo cáo](reports/station_forecast_unified_2026_11_24/BAO_CAO_CHI_TIET.md) dùng 18.719 khóa trạm–19h chung năm 2025. Dữ liệu ngày có cửa sổ cấu trúc ở cả 22 trạm bổ sung, 75–160 lượt/trạm nhưng dưới tiêu chí 365 ngày quan trắc đủ dùng. Hai thử nghiệm hiệu chỉnh 6–24 giờ là phân tích lại trên dự báo đã khóa. Có 732/18.719 lượt dự báo sáu giờ cao hơn tổng ngày 1 hơn 1 mm. Nâng tổng ngày giảm nhẹ RMSE trên phần giao, co giờ làm giảm POD mưa ≥5 mm ở giờ 6. Web giữ giá trị gốc và có mục đối chiếu tại trạm. Báo cáo Word chi tiết theo mẫu Khoa nằm trong `data/operational/pbl6_bao_cao_cuoi_ky_2026_11_24/`.

Vrain kiểm lại lúc 19h11 24/11 sau làm mới phiên. Danh mục 200, có nhóm Đà Nẵng, cả hai đường mưa giờ 404 cho 24/11 và ngày đã có dữ liệu 12/11. Kho hiện có đến 19h 15/11 và app đọc bản phát lại. GFS đủ 19 chỉ mục. Theo dõi trạng thái mới từ nhật ký, chưa suy nguyên nhân lỗi phía dịch vụ.

Bản Word rà soát là `PBL6_BAO_CAO_CUOI_KY_RA_SOAT.docx` trong thư mục trên. Bản này ghép lại phần thí nghiệm chi tiết, chín kỳ trên một giao diện và lộ trình mở rộng. [Đề xuất thí điểm tại Huế](reports/station_forecast_reviewed_2026_11_24/DE_XUAT_MO_RONG.md) dựa trên nguồn công khai. Cần được cấp phạm vi dữ liệu Huế và xác minh độ phủ trước khi so sánh mô hình. Open API do Vrain cấp cho đối tác là một đường thu cần kiểm tra cho cả Đà Nẵng.

## Kết quả dự báo cực ngắn trên 79 trạm

[Giao thức, kết quả và lệnh tái chạy](reports/station_nowcast_2026_11_24/README.md). Bản này thay giai đoạn thử Bi-LSTM ba trạm khi cần kết luận về toàn bộ tập trạm đã học. Giữ 79/86 vị trí đủ cửa sổ train, gồm 57 trạm nhánh ngày và 22 trạm bổ sung. Một mẫu dùng 24 giờ tại trạm, nhãn là sáu lượng mưa 1 giờ riêng biệt. Đã huấn luyện 1.032.811 mẫu 2021–2022, chọn mô hình/epoch trên 676.870 mẫu 2023, chấm 680.282 mẫu 2024 và 679.461 mẫu 2025 sau khóa.

Bi-LSTM chung cho mạng, chạy R/E0/E2 với ba seed. E2 chỉ thêm hai thành phần gió 850 hPa vào E0. Sửa bộ lọc để dùng lịch sử 24 giờ và chấm trên cùng sáu nhãn. Phép so chính CSI mưa ≥1 mm ở giờ 6 cho E2−E0 là +0,0131 ở 2024 và −0,0078 ở 2025. Khoảng tin cậy khối 7/14 ngày của 2025 đều chứa 0. LightGBM R giảm RMSE so với giữ mưa ở cả 79 trạm và sáu hạn trong kiểm định 2025. Ở ngưỡng ≥5 mm, giờ 6 vẫn bỏ sót phần lớn sự kiện.

Trang [1–6 giờ](http://127.0.0.1:8766/cuc-ngan) dùng phát lại 04–10/11/2026, mỗi lượt 78/79 trạm có số. LightGBM R được chọn theo RMSE trên 2023. Trình xem có Bi-LSTM R và mốc giữ mưa để đối chiếu, quan trắc chỉ hiện sau đăng nhập. Chạy thực cần xác nhận độ trễ nguồn Vrain. Kết quả nghiên cứu, bản phát lại và trạng thái vận hành có phạm vi khác nhau. Các tệp mô hình, dự báo, tọa độ, Word và PDF nằm trong `data/operational/`; trạng thái nguồn và mô hình nhánh ngày được mô tả trong các mục dưới.

## Lịch sử bảy ngày và thông báo admin

Thanh trượt ngang chọn ba hạn, ghi ngày kết thúc và khoảng hiệu lực. Dãy lượt lưu có **05–12/11/2026**, trích thêm 7 lượt từ Parquet B đã khóa bằng `scripts/prepare_station_map_history.py`. Nút Ngày gần đây hiện ngày thiếu bản hoặc chờ 19h. Trình đọc không gán hồi cứu thành lượt phát mới. Đã kiểm tra giao diện và quyền truy cập bằng Edge.

Thông báo admin lưu cục bộ trong `data/operational/station_map_web/admin_alerts.sqlite`. Tác vụ dự báo và bước kiểm tra nguồn ghi lỗi GFS/Vrain, số trạm thiếu hoặc tình trạng dự báo và đối chiếu bị dừng. Gộp lỗi cùng loại theo ngày, giữ thời điểm và trạng thái đã đọc. Phiên admin đọc từ Theo dõi. Kiểm tra 17h19 ngày 24/11 thấy GFS 19/19 chỉ mục. Phiên Vrain trước đó bị từ chối ở danh mục. Sau gia hạn, danh mục HTTP 200 xác nhận có nhóm Đà Nẵng, song hai đường lấy mưa theo giờ vẫn HTTP 404. Có thông báo thật trong tài khoản admin. Kho mưa giờ có số hợp lệ tới 19h 15/11 (82 trạm ở giờ đó), chưa có lượt phát trực tiếp. Bước chạy 18h40 dựa trên lịch Windows và trạng thái máy. Xem [web và cách đọc](demo/station_map/README.md).

## Bản đồ theo xã/phường và bảng nơi có mưa

Web mở mặc định lớp khu vực và bảng dự kiến mưa cho từng kỳ 24 giờ. Ranh giới tham chiếu tinhthanhpho.com bản 2026.10.8, CC BY 4.0, có 94 vùng. Tệp hình học lưu riêng theo `scripts/prepare_station_map_areas.py`. Ghép đủ 57 trạm vào 40 xã/phường theo phép chứa điểm, 28 vùng có một trạm. Màu lượng mưa là giá trị cao nhất của các trạm trong ranh giới, vùng xám chưa có số, bảng lọc mưa từ 1 mm và ngưỡng 10 mm. Có bộ lọc theo tên, trạm hợp lệ/tổng trạm và chi tiết khi chọn vùng. Lớp Trạm và liên kết đối chiếu theo trạm vẫn dùng được. Kiểm tra bằng Edge desktop/mobile, kể cả khi tệp ranh giới thiếu. Xem [cách đọc và nguồn ranh giới](demo/station_map/README.md).

## Bản đồ toàn màn hình, lịch cập nhật và Word chi tiết

Web cục bộ `http://127.0.0.1:8766/` mở bản đồ toàn cửa sổ. Có bảng công cụ trái trên máy tính, bảng trượt dưới trên điện thoại, thanh ba ngày và bảng chi tiết khi chọn trạm. Trang Theo dõi có lịch 18h40/19h/20h05, trạng thái riêng từng kênh Vrain, trạm sai khác nhiều và MAE mưa lớn của thí nghiệm bổ sung. Đã kiểm thử bằng Edge ở 1440×900 và 390×844, tài khoản kiểm thử lưu riêng. API phát lượt ghi trước 19h sau khi kiểm tra thời gian hiệu lực, mô hình khóa và hàm kiểm tệp. Khi thiếu lượt trực tiếp, map dùng các bản phát lại có ngày thật. Khách không nhận thực đo hoặc MOS.

Windows Task Scheduler đã đăng ký `PBL6-DailyRainfall` ở 18h40 và 20h05 giờ Việt Nam cho tài khoản đang đăng nhập. Đã chạy thử tác vụ và ghi trạng thái chưa có lượt đến hạn đối chiếu. Đọc lịch thật bằng `Get-ScheduledTaskInfo` và nhật ký trong `data/operational/station_map_web/daily/`. Lần kiểm tra 16h06 ngày 24/11 có đủ 19 chỉ mục GFS, nhưng hai kênh Vrain trả HTTP 404. Lượt kiểm tra các ngày 23/11 và 15/11 cũng 404. Chưa có dự báo trực tiếp đủ nguồn để xác nhận toàn bộ vận hành. Xem [luồng chạy](demo/station_map/README.md).

Đã bổ sung chẩn đoán trên hồi cứu 2026. Trong 248 lượt bỏ sót mưa ≥50 mm ở ngày 3, 158 lượt GFS dưới 10 mm và 65 lượt cả GFS lẫn B dưới 10 mm. Dùng để xác định nhóm cần thử tín hiệu từ tổ hợp GEFS. Các phép thử trước và chỉ số năm 2025 giữ vai trò đã nêu. Xem [bảng số và cách tái hiện](reports/gfs_gated_amount_2026_11_24/KET_LUAN.md). Word về phần ngắn hạn phiên bản chi tiết hơn nằm trong `data/operational/pbl6_bao_cao_cuoi_ky_2026_11_24/PBL6_BAO_CAO_CUOI_KY_NGAN_HAN_CAP_NHAT.docx`.

## Bản thảo cuối kỳ và thử cải thiện ngày 24/11

Bản thảo Word ngắn hạn theo mẫu Khoa CNTT nằm trong `data/operational/pbl6_bao_cao_cuoi_ky_2026_11_24/PBL6_BAO_CAO_CUOI_KY_PHAN_NGAN_HAN.docx`. Bìa chừa tên, chương 3 và 4 chừa phương pháp và kết quả cực ngắn. Nội dung dùng dữ liệu trạm Vrain, các đặc trưng dự báo GFS, kiểm định 2025, hồi cứu 2026 và mô tả web cục bộ.

Đã chạy ba thử nghiệm trên cùng tập dữ liệu của B. Bối cảnh GFS lân cận 25/50 km chưa cải thiện RMSE nhất quán. Tăng trọng số cho mẫu mưa lớn toàn bộ làm bias ngày khô vượt giới hạn CV 2022. Điều chỉnh lượng với ngưỡng kích hoạt 5 mm chọn trong CV giảm MAE nhóm thực đo ≥50 mm khoảng 3,91–6,47 mm trong hồi cứu 2026. RMSE toàn bộ có đánh đổi. Xác suất giữ nguyên. B tiếp tục là mặc định của web. Chi tiết, giao thức và bảng số trong [kết luận thí nghiệm bổ sung](reports/gfs_gated_amount_2026_11_24/KET_LUAN.md).

## Chốt phần dự báo ngắn hạn ngày 24/11

Người dùng yêu cầu hoàn thành phần ngắn hạn, chỉ ra đóng góp cụ thể, xem cách làm bản đồ màu và chuẩn bị báo cáo cuối kỳ trong ngày. Người dùng sẽ gửi template. Thành viên khác chuẩn bị đầu ra cực ngắn để tích hợp sau.

[Kết luận chốt](reports/gfs_short_range_closeout_2026_11_24/KET_LUAN_NGAN_HAN.md) dùng kiểm định 2025 đã khóa làm bằng chứng chính. LightGBM N1 so N0 giảm RMSE ngày 2/3 lần lượt 0,829/0,833 mm, đạt tiêu chí đồng thời và Holm. N3 vượt MOS về RMSE ngày 3. GRU N5 vượt MOS về MAE trung vị ngày 1/3. Phép so địa hình, dẫn xuất và mở rộng đặc trưng còn giới hạn như nghiên cứu gốc. B là phương án trình diễn theo lựa chọn từ tập học, giữ 26 biến, train 2021–2024 và hiệu chỉnh xác suất 2025.

`scripts/close_short_range.py` kiểm nguồn, 119 artifact đã khóa và chạy lại 43.464 lượt, đối chiếu 260.784 giá trị với chênh lệch lớn nhất bằng 0. Phân tích hồi cứu 2026 bổ sung dùng khoảng đồng thời cho 6 phép B–GFS/MOS theo khối 7/14/28 ngày, 5.000 lượt mỗi khối. Cả ba độ dài cho tín hiệu B giảm RMSE so GFS ngày 1, 2 và MOS ngày 1, 3. Đây là phân tích thăm dò trên giai đoạn đã xem. Lần theo dõi 18/11 dừng ở giai đoạn chờ, không tạo bản ghi lần phát. Tập huấn luyện, trọng số và kết quả đã khóa ở các phiên bản cũ giữ vai trò lịch sử.

[Trình xem bản đồ cục bộ](demo/station_map/README.md) đọc tệp `station_map_private.json` trong vùng riêng của bản chốt. Chế độ phát lại cho lần 12/11 và một lần có nhiều trạm ghi nhận mưa lớn. Hiển thị tọa độ trạm qua loopback, màu theo mm/24 giờ, ba khoảng ngày và số liệu đối chiếu. Đầu ra theo giờ sẽ được tích hợp khi thành viên cung cấp. Viết báo cáo cuối kỳ theo template người dùng gửi, dựa trên kiểm định 2025 và hồi cứu 2026 có nhãn rõ.

Bản đồ ban đầu có bốn lớp LightGBM, GFS, Vrain, sai lệch LightGBM−Vrain và biểu đồ ba ngày tại trạm. Ba lớp lượng mưa dùng chung thang màu. Edge đã kiểm tra cô lập ngày/lớp, dấu sai lệch, trạm thiếu và màn hình nhỏ. Trong lần thử nguồn trước khi đăng ký lịch ngày 24/11, GFS 00 UTC đã tải và giải mã đủ 19 trường ở 57 trạm, nhưng hai đường lấy Vrain trả 404 cho 23–24/11, kể cả sau khi làm mới phiên. Báo cáo thử nguồn trong `data/operational/gfs_short_range_closeout_2026_11_24/daily_rehearsals/`.

Web cục bộ đã bổ sung tài khoản riêng và trang Theo dõi. Khách xem dự báo LightGBM/GFS và xác suất ≥50 mm. Sau đăng nhập có Vrain thực đo, sai lệch, CSV, bảng 55 trạm và so sánh RMSE/MAE/Bias theo lượt, biểu đồ hồi cứu 2026, kết quả nhóm biến 2025. Tài khoản tạo lần đầu trên web và lưu băm ở `data/operational/station_map_web/`. Theo dõi đọc trạng thái lưu mỗi 30 giây khi mở trang. Nút kiểm tra nguồn có giới hạn một lượt mỗi 5 phút, ghi dấu thời gian và tình trạng nguồn. Kiểm tra bằng giao diện ngày 24/11 nhận đủ 19 chỉ mục GFS và HTTP 404 từ Vrain. Báo trạng thái ngày phát theo ledger, không suy từ lần kiểm tra nguồn. Xem [cách mở web](demo/station_map/README.md).

## Bản giải thích từ đầu — người dùng cần hiểu train và mốc kết quả

Theo phản hồi slide khó hiểu, đã tạo bản riêng `reports/short_range_explained_v2_2026_11_18/`, không ghi đè bản comprehensive. Có 33 slide chính (~28 phút) và 34 phụ lục, Word/Markdown giải thích từng slide. Tách LightGBM/GRU do nhóm fit, GFS là mô hình vật lý NOAA có sẵn, MOS là hậu xử lý hồi quy nhóm fit bằng mưa GFS + sin/cos ngày trong năm, quy tắc 0 mm không fit. GRU là Gated Recurrent Unit đọc chuỗi; “nhỏ” chỉ cấu hình 4.364 tham số N3, không phải họ mô hình khác. Thêm ví dụ giả định có nhãn rõ, cách học/CV, loss Tweedie/L2, mean–median, tính tay MAE/RMSE/Bias và bảng ba mốc đủ tốt. Hồi cứu 2026 modern B ngày 1 RMSE 20,45(GFS)→15,68 mm, giảm 23,3% chỉ số lỗi; không gọi accuracy 76,7%. Đếm sự kiện chính là micro: ngày 1 H275/M325/F123, POD45,8%/FAR30,9%; ngày 3 F494/849=58,2%. Macro giữ riêng trong phụ lục. Chưa có suy luận riêng B−GFS/MOS trong protocol mới để gọi ổn định; các phép A–D không thay cho điều đó. Chưa đặt ngưỡng sử dụng; POD 0,4 không tự gọi đạt.

Giải thích Tweedie p1,5 hỗ trợ0+dương lệch là giả thuyết hợp lý để thử, không chứng minh luôn tốt; L2 là squared-error objective, không phải regularizationL2. Chỉ thay lossmean, xác suất chungA/C vàB/D. ChọnTweedie bằngtrain-onlyCV2022, không bằng2026. Globalmodel và19h đều là thiết kế chưa có đối chứng riêng/khảo sát tối ưu. ChưatrainGRU bốn năm, không so2025GRU với2026B để xếp hạng. Builder/validator/finalizer/renderer tênshort_range_explained_v2; không sửa code/mô hình nghiên cứu cũ. PDF/ZIP ởprivate cùngNAME. Xem content_verification/native_render/release để biết kiểm tra thực, không tự suy ra hoàn thành từ tênfile. Không thay tiến trìnhruntime hoặc nguồn; nếu báotracker phải kiểm traPID/heartbeat thật.

## Báo cáo slide tổng hợp 18/11 — luồng chính 25–30 phút

Người dùng yêu cầu slide đầy đủ, dễ hiểu từ ý tưởng/nhãn Vrain, đầu vào/đầu ra, mô hình và paper gốc, cách train, kết quả, độ đảm bảo, khó khăn và hướng tiếp. Đã xác nhận25–30phút. Bản riêng `reports/short_range_comprehensive_2026_11_18/`: `PBL6_BAO_CAO_DAY_DU_DU_BAO_MUA_NGAN_HAN.pptx` có31slide chính (~28,3phút) +31phụlục. Từng slide có Notes, Word `THUYET_MINH_SLIDE.docx`, Markdown vàHTML offline tự chứa hình. Tách đúng2025protocolcũ/2026hồicứu, khôngtrộn điểm. Trích211lượt số từCSV,31bảng/641ô, inđậm28ô; nativePowerPoint62slide/1.211hộpchữ,0overflow. Bản này chỉ đọc, khôngtrain/chấmlạimôhình;109filebáocáocũ/slideuser giữ nguyên.

Nguồn gồm paper gốc LightGBM(Zhang&Ye2021), GRU+dựbáonền(Salehi2025), preprint2026chọnbiến/loss(ghi rõ chưa bìnhduyệt), Gneitingmean/median, TFT/Informer vàNOAA/ECMWF. `NGUON_TAI_LIEU.md` ghi rõ phạm vi đọc: một số trang publisher403, chỉ kiểm tra nội dung tóm tắt/phương pháp công khai được lập chỉ mục, không nhận đã đọc hết toàn văn. Không xếp hạng dự án bằng metric khác nguồn/nhãn. Predictor GFS tại trạm, GRUhistory7×1/context3×18(N3), không mô tả sai7×26. Chưa có TFT/Informer cùng bộtrạm để tuyên bố kém.

PDF62trang private `data/operational/short_range_comprehensive_2026_11_18/native_render/report.pdf`; gói báo cáo7file ~1,2MB `PBL6_BAO_CAO_NGAN_HAN_DAY_DU.zip` cùng BASE. Gói này là báo cáo, không phải ZIPdữliệu train. Public cóevidence_inputs/numeric_bindings/content_verification/release vànguồn. Builder/renderer/validator/finalizer mới cótiềntốshort_range_overview; khôngchạybuildercũhoặc ghiđèdeckngườidùng.

Lúc bắt đầu rà soát, haiPIDtrackerphiêntrướckhôngcònchạy/heartbeatđứngtừđê m; đãkiểmtrakhôngcótiếntrìnhtrùngvàkhởilạimộtissue18/11đãđượcduyệt. Launcher11208, PIDthật32436tại thời điểm khởi lại; phảiđọc`gfs_training_window_2026_11_18/live/tracker.json`/PIDhiệntạitrước báo. Chưa phát dự báo, vẫn chờ18:35gia hạnphiên/18:40thu/19hissue; nhãnđủtừ21/11tối. Snapshottrongslidekhôngthaythếtrạngtháiruntime. Không khởi chạy trùng hoặc gọi prospective đã kiểm chứng.

## Hoàn thành hồi cứu 18/11 — số năm train/loss; đang chờ theo dõi tương lai

Đã hoàn thành72CV và162estimatorLightGBM cuối cùng (54mean/108headphụ), MOS hai cửa sổ và hai bộ khí hậu;119artifact/cutoff khóa trước chấm. CV chọn small7lá,171/109/76cây, Tweedie cho ablation/candidate tương laiB. 2026modern RMSEmean D1/2/3: A15,708/18,029/20,677; B15,683/17,469/20,270; C15,627/17,736/21,356; D16,135/16,776/20,406; GFS20,445/19,738/24,953; MOSlong18,933/17,899/22,361. Thêm năm choTweedie giảm cả3điểm nhưng chưa đủ tiêu chí; D−Cngày3 là1/12phépA–D đạt tiêu chí thăm dò. N0/N1/N3:0/6; địa hình đổi rất nhỏ. L2 bớt thiếu mưa lớn nhưng báo thừa ngày khô, không thắng mọi hạn. Không chọn lại theo2026.

Đã đối chiếu48.639hàng/3.000giátrịmetric,48hàngreplay/2.880giátrị,8quantilebootstrapbằngresample trực tiếp ngày,54budgetmean;52testsđạt.367mụcSHA tương ứng336file riêng biệt giữ nguyên (khácslash trongmanifestcũ); ghi rõ trongverification_notes. ArchiveDrive2233/2233khớp. Báo cáoWord/Markdown,28slide/14bảngWord vàCSV ởPUBLIC; nativePowerPoint khôngtrànchữ. Gói riêng `BASE/PBL6_NGAN_HAN_TRAIN_MOI.zip` ~12,34MB/7file, mộtParquet323.466hàng với26biến/cờrole rõ; khôngGit. Source83cột cũ vẫn giữ nguyên.

Đã bật tiến trình giới hạn `scripts/track_gfs_window_issue.py --issue-day 2026-11-18`, chờ thu trước18:40VN/phát trước19h18/11; cả ba nhãn kết thúc19h21/11, kiểm tra từ20h21/11 và retry tối đa6h. Cần máy/mạng còn hoạt động. Đọc `BASE/live/tracker.json`, PIDthật/heartbeat vàstderr trước báo đangchạy; không spawn trùng khiturnmới. Tracker gia hạn session bằng tài khoản usercho phép trong DPAPIprivate, không plaintext/Git; metadata/registry cũ không đổi. Khi bàn giao mới ởwaiting_for_preissue_collection, **chưa phát dự báo/chưa có xác minh nhãn tươnglai**. Probe hiện đại thấy84vị trí cógiờ tại lúc đo, không đồng nghĩa đãtrain84. SnapshotPUBLIC chỉ trạng thái lúc xuất bản; trạng thái thật ởprivate. Không cần giữ turn chờ72h hoặc tự tạo goal.

Người dùng đã duyệt “ok hãy thực hiện” sau đề xuất bốn cấu hình LightGBM: A=train2021–22/Tweedie, B=train2021–24/Tweedie, C=train2021–22/L2, D=train2021–24/L2; giữ57trạm/N3=26biến. Phiên bản riêng `gfs_training_window_2026_11_18`, public/private theo quy ước. **Phê duyệt mới cho phép đưa2023–24 vào train và dùng2025 hiệu chỉnh xác suất/cutoff trong phiên bản này**; không thay vai trò dữ liệu, checkpoint hay kết quả các nghiên cứu cũ. Không fit cây/mô hình dự báo chính hoặc early stopping trên2025/26; tham số Platt và cutoff được phép fit2025. 2026 đã xem nên chỉ đánh giá hồi cứu, tách API; không gọi lại test chưa dùng.

Ba ứng viên × hai loss × bốn quý2022 × ba hạn =72CVfit, tối ưu macroRMSE sau clip0. Chọn chung candidate và số cây mỗi hạn (median qua hai loss/bốn quý), dùng giống nhau ở cảA–D/ba seed17/29/43. Loss dùng cho ablation N0/N1/N3 và dự báo tương lai chọn chỉ từCV2022; dùng cửa sổ train dài đã định trước, không chọn theo2026. Median và xác suất dùng chung A/C và B/D, tham số phụ chọn từtrain-onlyCVcũ. Nhãn không loại theo residual. Chưa triển khai Bi-LSTM.

Đọc `reports/gfs_training_window_2026_11_18/protocol.json`, `progress.json` private và verification thực trước báo hoàn thành. `scripts/run_gfs_window.py` prepare/train/score; `scripts/verify_gfs_window.py` kiểm tra. Khóa mã trướcfit và artifact trước chấm2026; không sửa mã toán học sau lock, lỗi cần phiên bản mới. AtomicIO mới có retryWinError5; tránh dùngGet-Content đểpoll file đangghi.

`scripts/record_gfs_window.py --probe` lưu snapshot nguồn hiện tại; `--issue-day YYYY-MM-DD --watch` là watcher có giới hạn một issue tương lai19hVN, ghi dự báo trướcissue, failclosed khi thiếu/nguồn chậm. `--verify-due` chỉ lấy nhãn sau72h+1h. Không nhận hồi phát là prospective, không khẳng định skill từ một issue. Dữ liệu/ledger/tọa độ/dự báo chi tiết ở private, khôngGit. Làm trênresearch/tft-regional, push/PR#1 được phép, không merge main; giữ nguyên ba thay đổi slide của người dùng.

## Hoàn thành 18/11 — thí nghiệm diễn biến GFS trong ngày

Theo phê duyệt “ok hãy thực hiện, nhánh BI-LSTM thì bạn cứ để sau, hãy hoàn thiện tốt nhất có thể dự đoán ngắn hạn”. Phiên bản `gfs_temporal_2026_11_17`: public trong `reports/`, dữ liệu/checkpoint/nguồn trong `data/operational/` cùng tên. Không sửa nghiên cứu final/daily-v2 hoặc nhánh Bi-LSTM. Giữ 57 trạm, train2021–22/cal2023/dev2024. Không fit/tuning bằng2025–26; hai năm đã xem nên vòng mới là đánh giá hồi cứu, không gọi test chưa dùng.

Đã lấy đủ2.120ngày×39messageGFSbổsung, kiểm tra82.680header và tải lại24message/1.368giá trị nội suy độc lập. Dataset323.466hàng=107.822pack ba hạn, không mất mẫu; tái hiện đúng218.658hàng và toàn bộ dự báo T0 của bản cũ (chênh tối đa0). Số pack train/cal/dev2024/2025/2026legacy/2026modern:35.116/18.365/19.405/18.723/1.725/14.488. 2026 vẫn tách API và chưa đủ năm, nguồn nhãn tới15/11, issue tới12/11.

T0=N3cũ26biến; T1 thêm8biến phân bố mưa6h; T2 thêm15biến diễn biến T/RH/u/v850/PWAT; T3 có49biến. GFS cùngcycle00UTC, issue19hVN; ba trạng thái khí tượng +6/+12/+18h từng cửa sổ, không gọi trung bình ngày. Đã chạy144estimator LightGBM và9GRU cuối cùng trênCUDA. GRU T0=4.364tham số; T3/LINEAR23=6.020, cùng17epoch/3seed. LINEAR23 chỉ thêm tổ hợp tuyến tính T0, không thêm thông tin. Không tìm lại siêu tham số; giữ ngân sách train-only CV cũ.

Kết quả2025 RMSEmean D1/2/3: LGB T0=26,035/29,203/30,645; T3=25,869/29,163/30,683. GRU T0=24,667/27,184/30,620; T3=24,675/28,154/30,761; LINEAR23=24,916/26,874/30,089. **0/12 phép so chính** đạt cả CI đồng thời và Holm. Chưa có cơ sở chốt49biến làm đầu vào chính ở thiết kế/ngân sách này. Một sốCSI/FAR thay đổi theo cutoff, POD/BSS không tăng đồng đều; không gọi toàn bộ đặc trưng vô ích hoặc tuyên bố cải thiện chỉ theo CSI. Giữ phương án đã kiểm chứng trước làm tham chiếu. GRU N5 cũ được khớp lại đúng các hàng mới để tham khảo, không fit lại/chọn lại mô hình chính.

Đã kiểm chứng163.023hàng đánh giá,4.320giá trịmetric,108hàng replay,1.944giá trịCPU, CI chính bằng lấy mẫu trực tiếp ngày. Perturb nhãn tương lai không đổi dự báo, scaler/projection chỉtrain;225artifactcũ và slide người dùng giữ nguyên.42tests đạt; archiveDrive2233/2233SHAkhớp. Nhãn cực đoan:136ngày–trạm≥200năm2025 đều có trạm trong30km≥50;128/136cóGSMaPraw≥50. Không sửa/loại nhãn, chưa chứng nhận cảm biến/API liên tục. GSOD ngàyUTC khác19–19VN nên không so thẳng.

Mã và môi trường khóa trướcfit trong `training_lock.json`;67artifact/cutoff khóa trước chấm trong `model_freeze.json`. Không sửa các mã train/inference/metric trong lock hoặc các checkpoint. Lỗi có ảnh hưởng toán học cần phiên bản mới. Một lần va chạm đọc log trênWindows làm ngắt fit; đã resume đúng checkpoint/seed/ngân sách, không đổi mã toán học. Dùng `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/monitor_gfs_temporal.ps1` để đọc tiến độ với FileShare.Delete, tránh Get-Content giữ khóa làm os.replace lỗiWinError5.

Pipeline `scripts/run_gfs_temporal_pipeline.py` có `--resume-verified` và `--publish-only`; đọc release/progress/PID thật trước báo trạng thái. Kết quả chính ở `BAO_CAO_CAI_TIEN_NGAN_HAN.docx`/`.md`, slide và CSV cùng thư mục. ZIP riêng gửi nhóm `PBL6_NGAN_HAN_GFS_VRAIN_2021_2026.zip` trong private BASE,6file gồm một Parquet đã ghép X/y (tên thân thiện), Word, catalogue49biến, protocol, hướng dẫn vàSHA. File canonical là `BASE/dataset_private.parquet`, SHA3497f0832313df953640a8d83229117bc2da51d2adae434a405edf66cdcda8a2. Không đưa ZIP/dataset/registry/checkpoint/dự báo theo mốc lên Git.

## Kiểm chứng cuối — đã hoàn thành theo phê duyệt 17/11

Người dùng đã duyệt toàn bộ kế hoạch năm bước bằng “ok, hãy thực hiện”: chốt protocol, đối chứng dung lượng GRU trên2021–2024, khóa mô hình/cutoff/mã chấm rồi kiểm định2025 và đánh giá riêng2026, sau đó báo cáo. Đây là **phê duyệt chấm2025/2026 sau khóa**, thay giới hạn chưa cho mở test ở các mục lịch sử bên dưới. Không yêu cầu hỏi lại sau mỗi bước. Không dùng2025/2026 để fit/tuning/chọn mô hình.

Phiên bản `gfs_station_final_2026_11_17`, public ở `reports/` và private ở `data/operational/` cùng tên. Giữ57trạm cũ; LightGBM N3 là phương án lượng mưa chính, GRU N5 là ứng viên trung vị đã định trước. Đối chứng GRU N3_LINEAR6 thêm sáu tổ hợp tuyến tính dữ liệu thô, đúng4.796tham số nhưN5; N3_WIDE giữ đầu vàoN3, head27 có4.751tham số (gầnN5, lệch45). Giữ17epoch/3seed/chuẩn hóa train/hiệu chỉnh2023, không tìm siêu tham số mới.

Protocol đã khóa trước fit trong `protocol.json`; `control_training_lock.json` khóa mã và dữ liệu. **Không sửa** `src/gfs_final.py`, `src/gfs_capacity_control.py`, `scripts/run_gfs_capacity_controls.py` sau khi đã bắt đầu fit. Nếu lỗi có ảnh hưởng toán học cần phiên bản mới. Script verify kiểm tra replayCPU, chuẩn hóa/projection train-only, thay nhãn tương lai không đổi đầu ra, và tái hiện toàn bộ dự báo cũ. `gfs_final_gate.py` chỉ cho đọc hàng kiểm định sau `control_verification` và tests passed, khóa111artifactcũ+12artifactmới và mã suy luận/chấm vào `final_manifest.json`; ghi `holdout_opened.json` trước lần đọc hàng test. Sau gate không sửa mô hình/cutoff/mã suy luận hoặc chấm.

Chín đối chiếu đặc trưng chính: N1–N0/N3–N1 LightGBM và N5–LINEAR6 GRU ở3hạn theoRMSEmean. Sáu đối chiếu kỹ năng: LGBN3vsMOS(RMSEmean), GRUN5vsMOS(MAEmedian) ở3hạn. Bootstrap ghép khối14ngày,5.000lần, CIđồngthờiBonferroni từnghọ +pbootstrapđịnhtâm/Holm xấp xỉ; các so sánh khác thăm dò. 2026 táchlegacy/modern, chưa xác nhậnliêntục vàchưađủnăm. Không tuyên bố cơ chế vật lý nhân quả hoặc vận hànhrealtime.

Đã hoàn thành cả năm bước:6fit đối chứng trênCUDA; khóa123artifact mô hình/hiệu chỉnh và mã trước mở test; chấm17phương án; kiểm chứng độc lập; xuất báo cáo Word/Markdown, ba hình và CSV. Test2025 có18.723mẫu trạm–issue/57trạm;2026legacy có1.725/56trạm (issue01/01–03/03), modern14.488/57trạm (06/02–12/11). Tổng104.808hàng kiểm định, 9.936đối chiếu metric,1.296seed,360bootstrap;181artifactcũ được bảo toàn,26tests đạt. `final_verification.json` passed, `release.json` complete. Cả2025 vàphần2026 này nay **đã chấm mô hình**; không gọi làtest chưa dùng cho các lần tuning tiếp theo.

Kết luận test sau tiêu chí đã khóa: khí tượng thô LGBN1–N0 đủ tiêu chí cải thiện RMSE ngày2/3; địa hình N3–N1 và GRUN5–LINEAR6 chưa đủ cả3hạn. LGBN3vsMOS chỉ đủ RMSE ngày3; GRUN5vsMOS đủ MAEmedian ngày1/3. Không đổi mô hình chính theo test. RMSEmean test D1/2/3: GFS26,345/27,899/33,765; MOS26,131/28,683/32,346; LGBN3 26,035/29,203/30,645; GRUN5 24,812/26,711/30,233. MAEmedian GRUN5 7,969/8,724/9,399. BSS50 LGBN3=0,345/0,248/0,197; GRUN5=0,349/0,267/0,186; FAR vẫn khoảng0,46–0,58.

Nguồn2025 có nhãn lớn nhất772,6mm/24h so dev2024 là366mm; đã hậu kiểm36nhãn lớn nhất từ JSON gốc, đủ24giờ/tổng nguồn khớp, chưa xác nhận cảm biến. Không bỏ nhãn/sửa điểm. Legacy2026 chỉ có2sự kiện trạm–ngày≥50 tại1issue mỗi hạn, không đánh giá ổn định cảnh báo mưa lớn từ nhóm này. Đọc báo cáo `BAO_CAO_KIEM_DINH.docx`/`.md`, `KET_LUAN.md` và CSV cùng thư mục. Mọi checkpoint/dự báo/registry nằm ngoàiGit; dữ liệu/báo cáo cũ và slide người dùng giữ nguyên.

## Bộ giờ ERA5 theo trạm — cập nhật 17/11/2026

Người dùng yêu cầu bổ sung đầy đủ đặc trưng giờ đến2026 và cung cấp Cloud Project ID để tải. Bản mới `station_hourly_era5_2026_11_17`; không sửa bộV1 hay checkpoint/protocol cũ. ERA5 gốc đã có tới09/2026; tải thêm11khối tới23UTC10/11 (nguồn mới nhất tại lúc lấy). Toàn bộ86tọa độ được nội suy song tuyến trực tiếp bốn nút0,25°, giữ NaN khi thiếu góc cần thiết. Nguồn khí tượng là hồi cứu, không chứng minh sẵn tại issue realtime; GEE chưa cho biết expver final/ERA5T trong bản này.

- Private nguồn/cache/log/snapshot ở `data/operational/era5_station_hourly_2026_11_17/`. Private dữ liệu/ZIP ở `data/processed/station_hourly_era5_2026_11_17/`. Public aggregate/mô tả Word/Markdown ở `reports/station_hourly_era5_2026_11_17/`.
- File chính `PBL6_TRAM_GIO_ERA5_2021_2026.parquet`:4.427.280hàng,44kênh khí tượng/lịch, mưa quá khứ, nhãn1–6h, raw/QC haiAPI vàcờ mẫu. Chỉresolution1h; fileGFSngày16/11khácphạmvi. Mưa tới19h15/11; khí tượng đầu khoảng tới06h11/11VN, nên hàng mưa06–07h11/11 là hàng khí tượng cuối.9.288hàngđuôi thiếuERA5 giữNaN/khôngready.
- 86vị trí,79cótrain2021–22. `sample_complete` đủkỹthuật kểcảvịtríchưacótrain; `sample_ready_r1`/`recommended_sample` thêmđiềukiệntrạmcótrain. R0cốýcùngmaskR1bảothủ. Cả24giờlịchsử+6nhãnphảicùngmãAPI0hoặc1; khôngtựnối legacy/modern. Đây làhaiđườngAPIcủaVrain, khôngphảihaitầngchấtlượnghayxácnhậnhai cảm biến; nguyênnhân khácđộphủ vàtínhliêntục chưacóxácnhậnchínhthức.
- Loader mới `src.hourly_station_update.HourlyStationData(path, split, experiment, ...)` hỗtrợtrain/cal/dev/reserved2025/external2026. LoaderV1giữnguyênchặn2025; khôngsửaguardcũ. Giữtoànbộtrụcthờigiantrướckhicắtchuỗi; khônglọc hàngreadytrước.
- Train/cal/dev/reserved2025/external2026 có1.032.811/676.870/680.282/679.461/575.655mẫuready. Phần2024cóthêm394cửasổđuôivìnguồnV1kếtthúc19h31/12, naycóthêmnhãn trước ranh nửađêm; khôngthayđiểmcũ. Khôngfit/tuning/chấmmôhìnhtronglầncậpnhật.
- Scripts `collect_hourly_era5_update.py`, `build_hourly_station_update.py`, `verify_hourly_station_update.py`, `publish_hourly_station_update.py`; kiểmtra trạngthái thật trong log/verification/release trước báohoànthành. Snapshotcũ76artifact và1128khốiERA5 khôngđượcghiđè. ZIPgửi nhóm chỉ5file:Parquet,Word,hướngdẫntrain,featuregroups,SHA256.
- Mô tả16/11phíadướilàgóimưagiờthuần+GFSngày. Bộgiờ17/11 bổsungphầnERA5màgói16/11chưacó. Vai trò năm2025/2026khôngtựđổithànhtrain chỉvì đãchuẩnbịdữliệu.

## Dữ liệu cập nhật đến 2026 — hoàn thành 16/11/2026

Người dùng đã yêu cầu thực hiện một bản dữ liệu đầy đủ tới 2026. Yêu cầu này cho phép thu thập/QC và dựng dữ liệu năm 2025–2026 trong **phiên bản mới**, thay giới hạn không đọc 2025 ở cấp kho nguồn trước đây. Chưa yêu cầu fit/tuning/chấm mô hình mới. Thí nghiệm và slide daily-v2 cũ vẫn phản ánh bộ 2021–2024; không đổi protocol đã khóa hay gắn dữ liệu mới vào checkpoint cũ.

- Bản mới `station_update_2026_11_16`, hợp đồng `reports/station_update_2026_11_16/data_contract.json`; private raw/session/progress ở `data/operational/vrain_update_2026_11_16/`; dữ liệu bàn giao ở `data/processed/station_update_2026_11_16/` (ngoài Git).
- Đã hoàn thành build/validate/publish và ZIP nội bộ ~61MB `PBL6_DATA_DEN_2026.zip`: mưa giờ 4.427.280 hàng; GFS–Vrain ngày 726.528 hàng, 427.746 hàng đủ X/y =142.582 mẫu trạm–issue đủ ba hạn. Các mẫu đủ theo vai trò: train38.222/cal26.030/dev27.773/reserved2025 27.307/external2026 23.250 (gồm2.437 legacy và20.813 modern); đây là toàn danh mục, không phải chỉ57. Tái hiện đúng218.658 hàng của cohort57 cũ. Verification toàn bộgiờ/ngày,115.584ôJSON độc lập,8rangeGRIB/688giá trị đạt. Mô tả Markdown/Word và JSON/CSV tổng hợp ở thư mục report cùng tên. Chưa fit/chấm mới.
- Đã lấy đủ 1.368 phản hồi ngày–kênh cho 01/01/2025–15/11/2026, gồm 01/01/2026; hai namespace riêng, tái dùng nguồn 2026 đã kiểm SHA. GFS bổ sung 684/684 cycle 29/12/2024–12/11/2026, 19 trường/cycle, 86 vị trí; chưa có lỗi nguồn mới. Tái dùng GFS cũ 2021–2024, giữ hai ngày nguồn lỗi đã chốt.
- Giữ mã STxxx, so alias/tọa độ current không đổi so registry 09/11: 82 legacy, 86 modern, bốn modern-only. Kênh cũ có số trong 365 ngày 2025; modern không có số 2025, bắt đầu có số 08/01/2026. Phần giao 2026 chỉ 367 cặp tại một vị trí/18 ngày, 46 cặp mưa khác nhau; chưa chứng minh tương đương hay liên tục. Tháng 1/2026 modern chỉ 23 ngày–trạm đủ24h, tháng10 2.652/2.666, 01–15/11 1.268/1.290.
- Một Parquet mưa giờ giữ raw/QC hai kênh, `rain_mm` có mã nguồn; xung đột thành NaN, không cộng/trung bình hai nguồn. Một Parquet GFS–Vrain ngày có N0–N5, ba nhãn, từng namespace, mask đủ ba hạn và delay1/3/6. `recommended_sample` chọn tối đa một namespace hoàn chỉnh/trạm/issue; cả lịch sử và nhãn của mẫu dùng cùng namespace. Modern vẫn `continuity_with_legacy_confirmed=False`; đủ X/y chưa phải chứng nhận tính liên tục hoặc cảm biến.
- Nguồn tới 15/11/2026; issue cuối đủ ba nhãn là 12/11/2026 lúc19h. Năm2026 chưa đủ năm. Bộ mới là GFS+Vrain, **chưa kéo dài 44 biến ERA5**. Mưa giờ là số nguồn, không chia mưa ngày.
- Lệnh lần lượt: `prepare_station_update.py`, `update_station_archive.py`/`collect_gfs_station_update.py`, `build_station_update.py`, `validate_station_update.py`, `publish_station_update.py`; runner `run_station_update_pipeline.py` đợi hai collector. Xem `pipeline_progress.json` và log thật trước báo hoàn thành. Publish tái tải8rangeGRIB/688giá trị để kiểm chứng độc lập rồi đóng gói ZIP private. Bảo toàn87artifact cũ/slide;37tests nguồn/thời gian/nhãn đạt.
- 2025 nay đã được thu thập/QC theo yêu cầu cập nhật; gọi là **chưa chấm mô hình**, không còn nói toàn kho chưa đọc năm2025. Vai trò mặc định vẫn train2021–22/cal2023/dev2024/reserved2025/external2026; muốn đổi tập train cần protocol mới. Mô tả “2025 kín” phía dưới là trạng thái của các bản đã đóng băng trước16/11.

## Thí nghiệm hằng ngày v2 — đã hoàn thành và kiểm chứng

**Slide daily-v2 mới 11/11:** `reports/gfs_daily_slides_2026_11_11/PBL6_MUA_TRAM_HANG_NGAY_V2.pptx`/HTML, 32 slide chính + 9 phụ lục, ghi chú tiếng Việt; README giải thích “giữ kín 2025” và lộ trình trình bày. Builder/render/validator `scripts/*gfs_daily_slides*`; chỉ đọc aggregate của daily-v2, không train hay mở 2025. PDF private ở `data/operational/gfs_daily_slides_2026_11_11/`. Không chạy lại builder các deck cũ. Năm 2025 dành kiểm định sau khóa phương án; hiện dataset thí nghiệm mới dựng/kiểm chứng 2021–2024, chưa có bảng điểm 2025. Các phần “slide/nhận xét” phía dưới thuộc pilot lịch tuần, không thay kết quả mới này.

Người dùng đã duyệt thực hiện cả bốn đề xuất sau nhận xét độc lập: lịch issue hằng ngày/độ trễ; ZERO/MOS và mục tiêu mean–median; tách biến thô khỏi dẫn xuất; xác suất nhất quán/tuning có kiểm soát. Thí nghiệm riêng `gfs_station_daily_v2_2026_11_10` (tên theo ngày duyệt, chạy tiếp 11/11). Không đổi các pilot cũ, slide đã bàn giao hoặc mở 2025.

- Protocol đã khóa trước fit trong `reports/gfs_station_daily_v2_2026_11_10/protocol.json`; mã/data/source policy khóa tiếp bằng `src/gfs_daily_lock.py`. Không sửa protocol/huấn luyện sau khóa rồi dùng lại checkpoint.
- Lịch 1.451 ngày 08/01/2021–28/12/2024; 1.449 chu kỳ GFS hợp lệ. Hai ngày 02/02/2021 (404 chỉ mục cả hai layout) và 30/11/2022 (chỉ mục không khớp byte GRIB, xác nhận tải lại) loại toàn issue chung mọi mô hình trước fit; bằng chứng `source_coverage_policy.json`. Không chọn theo mưa/điểm.
- Dataset đã dựng: 57 trạm, 72.886 mẫu/218.658 hàng; train/cal/dev 35.116/18.365/19.405 mẫu, 717/362/363 ngày issue. Mask chung cả 3 hạn, N0–N5 và độ trễ trạm1/3/6h. File private `data/processed/gfs_station_daily_v2_2026_11_10/dataset.parquet`.
- N0=16 biến nền gồm mưa GFS/lịch/vị trí/lịch sử Vrain; N1 thêm 5 khí tượng thô; N2 thêm 4 dẫn xuất ẩm/gió; N3=N1+5 địa hình; N4=N3+4 dẫn xuất; N5=N4+2 tương tác theo dốc. Tách mean/median và hai xác suất lồng nhau `p50=p1*q50givenwet`.
- Tuning 3 ứng viên × 4 fold quý2022 (gap7 ngày), chỉ train2021–22; N3 là anchor; final fixed số cây/epoch theo CV. Cal2023 chỉ Platt/cutoff cross-fit theo quý; dev2024 đánh giá, chưa test. LightGBM N0–N5 + N3delay3/6; GRU N3/N5; ba seed17/29/43. Không tuyên bố GRU đủ sáu cấu hình.
- Nguồn GFS hiện tại có Last-Modified~3,65–4,04h sau init; 48 chu kỳ lịch sử đầu2021 có timestamp sửa kho sauissue. Không chứng minh giờ phát hành gốc. API Vrain hiện hành có hàng giờ nhưng chưa chứng minh latency tiếp nhận. 8hGFS/1htrạm vẫn là giả định; có sensitivity3/6h, GFS16h không đủ cùngcycle. Không fit2026.
- Pipeline `scripts/run_gfs_daily_pipeline.py`: build → validate → trees → GRU → evaluate; sau đó `verify_gfs_daily_models.py` → `publish_gfs_daily.py`. Đã hoàn tất; 179 tests đạt, replay218.658 hàng/81 mẫu nội suy độc lập, 288 estimator LightGBM/6GRU/186 calibrator/2.106 phép đối chiếu metric đạt; 56 artifact cũ/slide người dùng giữ nguyên. Kết quả mới nằm riêng, không thay các phần lịch sử bên dưới.
- Báo cáo đầy đủ: `reports/gfs_station_daily_v2_2026_11_10/BAO_CAO_HANG_NGAY_V2.md` và `.docx`; `KET_LUAN.md` đọc nhanh, CSV đầy đủ/CI/seed/độ trễ cùng thư mục. LightGBM chọn mean/wet/conditional cấu hình small, median medium; GRU small hidden16/head24, 17epoch final, tuning chỉ train.
- Dev2024 RMSE mean D1/2/3: GFS19,271/20,228/22,139; MOS19,169/20,124/20,445; LGB_N3 17,527/18,550/19,150; GRU_N5 17,386/18,750/19,277. MAE median GRU_N5 6,314/6,754/6,870, thấp nhất trong các model chính đã chạy. Hai model N3LGB/N5GRU đều vượt MOS về RMSEmean/MAEmedian với CI95% chênh dưới0, nhưng đây là dev/CI thăm dò chưa chỉnh nhiều so sánh.
- N1−N0 thêm khí tượng thô giảmRMSE cả3hạn, CI dưới0. Dẫn xuất N5−N3: LGB chưa rõ cả3hạn; GRU giảmRMSE/MAEmedian ngày1–2 vớiCI dưới0, ngày3chưa rõ. GRU_N5 so LGB_N5 giảmMAEmedian nhưngCI chênhRMSE chứa0. Không gọi GRU thắng mọi mặt hoặc dẫn xuất luônvôích. Tăngkênh cũngtăng tham sốGRU, chưa tách hoàn toàn dung lượng.
- BSS50 LGB_N3=0,280/0,227/0,164; GRU_N5=0,287/0,228/0,158. FAR cảnh báo50mm còn~0,5–0,7; PODcao chưađủ. Không quy chênh với pilot tuần cho riêng lịch hằng ngày; chưa chứng minh vận hành realtime/nguồn đúng giờ. 2025 vẫn kín; cần quyết định đóng băng cuối trước khi mở.

## Nhận xét độc lập mới — đọc kèm slide

Người dùng yêu cầu đánh giá kết quả và đối chiếu nghiên cứu gần đây. Đã đọc nguồn gốc 2024–2026 và bổ sung **chẩn đoán hậu nghiệm trên dev**, không train hoặc mở 2025: `reports/gfs_station_review_2026_11_10/NHAN_XET_DOC_LAP.md`, `diagnostics.json`, `diagnostic_metrics.csv`; tái tạo bằng `scripts/review_gfs_station_results.py`.

Phát hiện quan trọng: **luôn dự báo 0 mm có macro MAE 5,887/6,887/7,773**, nên ngày 3 cả A2/A3/GRU chưa vượt đối chứng này về MAE ở mức điểm. Tỷ lệ mẫu <1 mm khoảng 72,0%/66,6%/63,2%. Điều này không biến 0 mm thành dự báo hữu ích: GRU ngày 3 RMSE17,62 tốt hơn ZERO22,89/khí hậu19,98/GFS26,73. Trên riêng 114 mẫu thực tế ≥50mm ngày3 (12 issue), **micro MAE GFS76,44; A2 90,00; GRU60,10mm**. Đây là chẩn đoán có điều kiện theo y, không phải cách chọn mô hình vận hành, chưa có CI. A2 giảm MAE toàn tập nhưng còn yếu mưa lớn; không chỉ dẫn mức giảm18,1% MAE so GFS để kết luận thành công.

Bộ slide đã gửi và kết quả đóng băng giữ nguyên; slide chưa có ZERO, cần dùng kèm nhận xét mới. Chưa có chứng cứ vượt nghiên cứu khác vì khác miền/nhãn/hạn/split. Dùng trạm, mô hình chung, LightGBM/GRU và thêm biến chưa tự tạo phương pháp mới; cần đối chứng cùng nguyên liệu khí tượng/địa hình để đo lợi ích của dẫn xuất vật lý, lịch hằng ngày, kiểm tra xác suất và kiểm định cuối. Không suy ra lỗi dataset hay overfitting chỉ từ các điểm mới.

## Slide báo cáo 57 trạm — yêu cầu mới nhất

Người dùng yêu cầu slide đầy đủ về đầu vào/đầu ra, chia dữ liệu, tinh chỉnh và kết quả. Bộ riêng `reports/gfs_station_slides_2026_11_10/`: `PBL6_DU_BAO_MUA_57_TRAM.pptx`/HTML, 43 slide chính + 12 phụ lục, ghi chú tiếng Việt trong PPTX và `GHI_CHU_THUYET_TRINH.md`. Hướng dẫn và lộ trình trình bày ở README cùng thư mục. PDF native PowerPoint ở private `data/operational/gfs_station_slides_2026_11_10/`, không commit PDF.

Không train mới để làm slide, không mở 2025. Đối chiếu checkpoint cho thấy LightGBM dừng sớm theo **l1/MAE cal** (metric đầu, `first_metric_only=True`), không phải Tweedie; best 62–177 cây. GRU dừng theo loss chung cal. Tham số pilot cố định; chưa GridSearch/Optuna. Script build/render/validate có tiền tố `gfs_station_slides`, ghi chú riêng `scripts/gfs_station_slide_notes.py`; không chạy builder của hai deck người dùng đã sửa.

Audit bổ sung từ dự báo đã lưu: chưa ràng buộc P(≥50)≤P(≥1). A2 vi phạm 188/8.346 dòng dev (2,25%), gap tối đa ~0,087; không có quyết định mâu thuẫn tại p≥0,5. A0/A1/A3 cũng có vi phạm; GRU không có trường hợp quan sát được nhưng mã cũng chưa ép thứ tự. `training_audit.json` trong thư mục slide có tổng hợp. Không sửa dự báo/điểm pilot; đề xuất giải quyết bằng protocol mới. Kiểm tra slide không chứng nhận kỹ năng cuối hoặc cảm biến.

## Mở rộng trạm mới nhất — đã thực hiện

Người dùng hỏi **“có thể mở rộng số lượng trạm được không”**. Đã mở rộng nhánh NWP từ20lên**57trạm**, thêm37trạm trong nguồn hiện có, giữ đúng tiêu chuẩn train>=365ngày đầy đủ và>=30ngày>=1mm.57trạm thực tế479–728ngàytrain;2trạm có<30cửa sổ tuầntrain (min18), cần báo giới hạn.

- 79trạm có cửa sổ train theo lịch tuần, nhưng22trạm ngoài57có lịch sử ngắn; chưa train79.3trạm lịch sử chưa có train và4vịtrí hiện hành chưa có lịch sử cũ. Không ép đủ86.
- Dataset57có5.032/2.582/2.782mẫu train/cal/dev, tổng31.188hàng3hạn. Lịch vẫn208issue mỗi7ngày.2025kín,2026khôngtuning. NguồnGFSđã trích82vịtrí dùng lại; chỉ tải một sốmessageđểreplay.
- ĐãtrainLightGBM A0–A3ba seed vàGRU_A2ba seed (gatecalqua ngày3), cùnghyperparameterscũ. Dataset/source/modelverificationđạt;53testsđạt (6testmới vềpathisolation vàmatchedcohort).
- Kết quả57trạm devmacroMAE: GFS5,83/7,41/10,30mm; A2 5,28/6,72/8,44; GRU_A2 6,94/7,56/8,00. Không so trực tiếp với trung bình20trạm.
- Đãso cùng20trạm/cùngissue/nhãn/32đầu vào: A2train20=6,15/7,37/7,75; A2train57=5,91/7,40/8,66mm. Ngày1tốt lên,ngày2gầnngang,ngày3điểm xấu hơn;CI cả3chứa0. Mở rộng phạm vi không bảo đảm tăngđộchínhxác. So sánh mở rộng cảtrain/cal, không chỉtrain.
- Bản20được giữ nguyên. Bản57 riêng `reports/gfs_station_57_2026_11_10/BAO_CAO_MO_RONG.md` vàWord; protocol/result_summary/cohort_scope_metrics/matched_original20_bootstrap cùngthưmục. Datasetprivate `data/processed/gfs_station_57_2026_11_10/gfs_vrain_pilot.parquet`; model/predsprivate thưmụcoperationalcùngtên.
- Scriptprepare `scripts/prepare_gfs_station_expansion.py`; các bướcbuild/validate/run/GRU/verify dùngenv `PBL6_GFS_EXPERIMENT=gfs_station_57_2026_11_10`. `src/gfs_experiment.py` tách output khỏi nguồncache20chỉđọc. Publish `scripts/publish_gfs_station_expansion.py`. Không sửa cohort/protocol đãfit; phiênbảnmớinếuđổitiêuchí.

## Hướng ngắn hạn mới được người dùng duyệt 10/11/2026

Người dùng yêu cầu đánh giá độc lập với hướng cũ, rồi nói **“ok hãy tiến hành thực hiện”** với phương án NWP + Vrain. Nhánh ngắn hạn ưu tiên **hậu xử lý GFS để dự báo ba tổng24h tại trạm**, LightGBM chính và GRU nhỏ theo điều kiện pilot. TFT/Informer không còn là bộ ba bắt buộc. Nghiên cứu giá trị đầu vào mưa trạm/khí tượng dự báo/địa hình; chưa làm app. Chi tiết: `docs/short_range_nwp_design.md`.

- GFS00UTC, issue12UTC=19hVN; hiệu tổng0–12/36/60/84h tạo ba cửa sổ19–19h. Khí tượngGFS+24/+48/+72h là ba trạng thái giữa cửa sổ, không phải trung bình ngày.
- Bản dự báo phải có trước issue theo giả định trễGFS8h và margin12h; chưa chứng minh thời điểm công bố lịch sử từng file. Trễtrạmgiảđịnh1h: summary1/6/24h kết thúc18h, bảy ngày đầy đủ kết thúc hôm trước; không dùng số đo19h ngay tại issue.
- Pilot mỗi7ngày trong2021–2024,208issue, khác thí nghiệm hằng ngày đầy đủ. Chọn20trạm từ57ứng viên chỉ theo train2021–22 và địa lý/DEM; mỗi trạm565–728ngày train hợp lệ. Không chọn ngày/trạm theo điểmdev hoặc mưa cực đoan quan sát.
- A0=mưaGFS+lịch+vịtrí/ID; A1 thêm lịch sửVrain; A2 thêm T/RH/gió850/PWAT vàproxyẩm; A3 thêmDEM/slope/tươngtácgió. MọiA cùng mẫu. Q850 tính từT/RH cùngcôngthức vì đầu2021thiếuSPFH trong sản phẩm thườngdùng.
- DEMMapzen là proxy tại tọa độ hiện có, không phải cao độ đo tại trạm; gió·gradientđịa hình/ẩm là giả thuyết, không chứng minh nhân quả.
- Protocol khóa trướcfit ở `reports/gfs_station_pilot_2026_11_10/protocol.json`; audit/verification/kết quả cùngthưmục. Private ở `data/operational/gfs_station_pilot_2026_11_10/`, `data/processed/gfs_station_pilot/`.
- Collector `scripts/collect_gfs_station_pilot.py`: HTTPbyte-range,206/Content-Range, GRIBinit/lead/interval/unit, resume/SHA; đọcprogress/PIDthật. Windows ecCodes phải giải mã tuần tự quaLock, chỉ HTTP chạy song song. Optionalenv `requirements-nwp.txt`.
- Ba seed17/29/43. GRU_A2chỉ chạy khi gatecal: A2macroMAE thấp hơn cảGFS/khíhậu và>=50%trạm cải thiện soGFS ở ít nhất một hạn. Không dùngdev để quyếtđịnhgate. Cal/earlystop2023,dev2024chưa làtestcuối;2025kín,2026khôngfit/tuning.
- BộVrain–ERA5v1 và Bi-LSTM cựcngắn giữ phạmvi riêng. “Đã ghép/train được” không chứng minh khả dụngrealtime hoặc kỹnăng1–3ngày. Không gắnNWPpilot thànhthínghiệmhằngngàyđầyđủ.

**Trạng thái sau triển khai:** NWPpilot đã hoàn thành208/208issue,20trạm,10.977hàng/3.659mẫu trạm–issue. Train/cal/dev=1.774/902/983mẫu, mỗi mẫu ba nhãn. Đãfit36estimatorlượng và72classifierLightGBM chính, GRU_A2ba seed7001tham số trênCUDA; không trainTFT/Informer. 47testsđạt; replay10.977hàng và171mẫu nội suyGRIB, replay36+72estimators vàbaGRUCPU, scalertrain-only/metricđạt.

Trên dev2024, macroMAE GFS=6,40/8,13/10,27mm; A2=6,15/7,37/7,75; GRU_A2=7,81/8,35/8,46. **CI A2−GFS cả ba hạn chứa0**, không khẳng định cải thiện ổn định dù ngày3giảmđiểmkhoảng24%. GRU có MAE cao hơn nhưng RMSEngày3 thấp hơn A2 (18,31so20,17mm); không kết luậnGRUkémmọimặt. A3chưa có lợi ích rõ; BSSkhông cải thiện đồng đều. GateGRU chỉqua ngày3cal với chênhnhỏ; không dùngdevchọngate.

AuditLast-Modified3952messages:7chu kỳ đầu2021có timestamp sửa/chéparchive sauissue, không ởcal/dev. Không suy ra phát hànhgốc muộn. Đã chạy thêmA2ba seed bỏ7chu kỳ train; devMAE6,09/7,42/7,88mm, hướng tương tự. Xemrelease_timestamp_audit.json/release_sensitivity_metrics.csv. Chưa chứng minh độtrễvậnhànhthật.

Điểmvào kếtquả: `reports/gfs_station_pilot_2026_11_10/BAO_CAO_PILOT.md`, Wordcùngtên, `result_summary.json`. Datasetprivate `data/processed/gfs_station_pilot/gfs_vrain_pilot.parquet`. Côngviệctiếpđểkiểmchứng: protocolphiênbảnmới lịch hằng ngày/lag sensitivity/drop-group; không đổi pilot cũ hoặc mở2025tùy tiện.

## Quyết định mới nhất của người dùng — đã chốt

**Chuyển cả hai nhánh sang dự báo lượng mưa tại trạm.** Người dùng nói: “nhóm tôi thực hiện dự đoán cực ngắn và ngắn theo trạm”. Quyết định này thay mục tiêu dự báo trực tiếp mưa trung bình diện tích toàn Đà Nẵng trước đây. Không tự đưa mục tiêu vùng trở lại hoặc ưu tiên app.

- Thành viên khác: Bi-LSTM, sáu lượng mưa giờ tiếp theo tại từng trạm, 1–6h.
- Người dùng: ba tổng24h riêng tại trạm; **phương án mới NWP+LightGBM/GRU ở đầu file** thay bộbaTFT/Informer bắt buộc trước đây.
- Đề xuất kỹ thuật: mỗi kiến trúc học một mô hình chung cho nhiều trạm; một mẫu là `(station_id, issue_time)`. Không cần 86 mô hình riêng cho một kiến trúc.
- Nhãn là mưa Vrain tại chính trạm. Người dùng đã xác nhận: **10:00 = tổng mưa09:00–10:00 giờ Việt Nam, UTC+7**. Đơn vị hiển thị nguồn là mm. Không còn chờ xác nhận timezone hoặc nhãn vùng.

## Phạm vi và số trạm

86 là danh mục **nhóm “Đà Nẵng” mà tài khoản được truy cập**, không phải toàn Việt Nam. Chưa chứng nhận mọi mục nằm đúng ranh hành chính cuối; lọc theo tọa độ/ranh khi chốt tập trạm nếu cần. Không gọi danh mục là phủ kín diện tích hoặc cả đảo.

- Kênh cũ có 82 vị trí, kênh hiện hành 86. 82 cặp tọa độ khớp chính xác/duy nhất, 81 tên giống và một tên khác; bốn vị trí bổ sung. Chưa biết thời điểm lắp đặt bốn trạm đó.
- Registry private 86 mã STxxx + alias hai kênh; giữ mã v1 khi thêm trạm sau này. Khớp metadata không chứng minh số đo hai kênh tương đương.
- Trong kho cũ, trạm có ít nhất một số giờ sau QC: 2021 **57**, 2022 **79**, 2023 **79**, 2024 **82**. Không đồng nghĩa đủ cả năm. Không mặc định cả 86 có lịch sử từ 2021 hoặc đã được chọn train.
- Bản dataset trạm v1 có82trạm lịch sử;79trạm có cửa sổ train hợp lệ cho cả hai nhánh, ba trạm còn lại không vào đánh giá mặc định. Đây là điều kiện cấu trúc, chưa chứng nhận cảm biến;24trạm có dưới180mẫu ngày train. Pilot một nhóm đại diện trước; thiếu tại trạm A không loại mẫu hợp lệ của B.

## Nguồn đã có và trạng thái

Private base `data/operational/vrain_2026_11_09/`:

- `download/`: 3.653 response 2015–2024, SHA gzip/raw đạt; có bảng giờ cho 1.461 ngày 2021–2024; 2015–2020 không trả giờ, không phải ngày khô. Ba station-day chênh tổng đã gắn cờ, số gốc được giữ.
- `recent_archive/`: 622 response cho 02/01–08/11/2026, 311 ngày × hai kênh. Bỏ 01/01 vì cửa sổ có giờ 2025. Có số ở 87 ngày kênh cũ, 305 ngày kênh mới; số hàng không bằng số đo hợp lệ.
- `handoff_v1/`, `PBL6_VRAIN_SOURCE_V1.zip`: nguồn/registry/QC, **không phải tập train theo trạm đã dựng**. Predictor 44 kênh trong ZIP vẫn là trung bình vùng cũ; không đổi tên hoặc nhân bản thành đầu vào theo trạm. Có 21 hàng thiếu kx/tt (42 ô), giữ NaN.
- `freeze_work/station_matrices.npz`: ma trận giờ nguồn 2021–2024, mask/QC; clock là cuối khoảng giờ Việt Nam, theo xác nhận mới. Không sửa file nguồn vì metadata cũ; áp dụng contract khi dựng dataset mới.
- Hai kênh chỉ trùng số ở một vị trí/18 ngày/367 cặp, 46 cặp có mưa đều khác số. Không tự nối nguồn 2026 hoặc fit/tuning 2026.

**Bộ trạm đã dựng và kiểm tra:** `data/processed/station_v1/PBL6_TRAM_GIO_NGAY_V1.parquet`, một file chứa1h/24h, raw/QC, X/y và chỉ số sample-ready; ngoàiGit. Tài liệu ngắn gửi nhóm: `reports/station_data_handoff_2026_11_09/MO_TA_DU_LIEU.docx`. Kỹ thuật: `HUONG_DAN_TRAIN.md`, `dataset_summary.json`, `verification.json` cùng thư mục báo cáo.

**ERA5 gốc vẫn có tại `data/raw_data/gee/era5/grid/*.parquet`.** Builder mới nội suy trực tiếp từ bốn nút0,25° quanh trạm; tất cả82trạm lịch sử có nút bao quanh. Không dùng đường vòng93ô hoặc sao chép mean vùng. Yêu cầu đủ mọi nút có trọng số dương; giữNaN nếu thiếu. Context/SST/chênháp có miền vùng có chủ đích. Không dùng các cột mưa ERA5/GSMaP làm X/y. CubeR93 và bộ vùng cũ giữ làm lịch sử.

Kiểm traERA5v1đạt2.995.050hàng/2.480.367cửa sổ,45đốichiếutrườngERA5,328sốmưagốc,72mẫuqua loader;34testsởbảnđó. ChưatrainbằngbộERA5v1; NWPpilot10/11đãtrainriêngnhưđầu file. Đây là kiểm tra cấu trúc, chưa chứng nhận cảm biến/vịtrílịchsử/độtrễ.

## Hợp đồng thời gian và nghiên cứu

- Người dùng xác nhận10:00là mưa09–10hViệtNam. Chuẩn hóa `period_start_utc=02:00`, `period_end_utc=03:00`; ERA5tức thời lấy02:00UTC. Clock20:00hômtrước→19:00ngàyđánhdấu tạo ngày19:00→19:00, không phải00–24. Không dùng tiêu đề XLSX19:20 để đổi các bin giờ đã xác nhận.
- Lưu mưa theo khoảng đo, provenance, QC; không đổi thiếu thành0, không chia mưa ngày thành giờ, không lấp y bằng ERA5/CPC/GSMaP.
- B/A/M/C đã dựng theo trạm: giờ11/12/20/1, ngày9/12/20/1. E7=44/42kênh; thêmR=45/43. Statictọađộ2kênh+IDđi riêng, cùng cách dùng giữa cácE. C chỉSST, chưa phảiENSO/MJO.
- BộERA5v1: Rlà mưa quákhứchínhtrạm, maskchungkhiablation, chỉlịchtươnglaiđãbiết. **BộNWP mới được dùng khí tượng/mưa GFS dự báo kỳ đích từ bản khởi tạo trướcissue; cấm số thực đo hoặcERA5kỳđích trongX.**
- Split theo thời gian chung cho mọi trạm, toàn bộ nhãn nằm trong split. Fit scaler/reference trên train; earlystop/calibration/tau trên cal. Không random cửa sổ lẫn trạm/ngày.
- Bảnv1: train2021–22, cal2023, dev2024 theo giờ Việt Nam;2024chưa phải testcuối. Mask `sample_ready_r1` dùng chung mọiE/model/R0–R1. Loader `src/station_forecast_data.py` giữ mọi hàng thời gian trước chọn issue; không dropNaNrồi cắtchuỗi. Chưafit bất kỳ scaler nào.
- **2025 giữ kín.** Không tuning2026 rồi gọi2025 là test tương lai. Không đổi tên kết quả vùng cũ thành kết quả trạm; NWPpilotđãtrainriêng, ERA5v1chưatrain.
- Báo metric từng trạm và macro-average, kèm micro nếu cần; bootstrap theo khối thời gian giữ đồng thời các trạm. Không coi các trạm trong cùng trận mưa là mẫu khí hậu độc lập.
- Ngưỡng mưa/POD/FAR phải chốt phù hợp trạm và kỳ giờ/ngày; không tự mang ngưỡng vùng16/50/100 sang. Không có POD0,4 tốt chung. ERA5 hồi cứu chưa chứng minh có sẵn tại issue vận hành.

## Quy ước làm việc và an toàn dữ liệu

- Tiếng Việt, đánh giá độc lập và trung thực kể cả kết quả âm.
- Workspace `D:\PBL6_v2`; Python `.venv\Scripts\python.exe -X utf8`; RTX4060Laptop8GB. Python inline qua PowerShell dùng ASCII; nguồn tiếng Việt dùng UTF-8/apply_patch.
- Git `git -c safe.directory=D:/PBL6_v2`, nhánh `research/tft-regional`; đã được phép push/cập nhật PR#1, không tự merge main.
- Repo công khai: không commit raw/PDF, registry/tọa độ từng trạm, credential/cookie, checkpoint hoặc dự đoán từng mốc. Dữ liệu nguồn cũ từ Drive `pbl6_data_v2_*.tar`, kiểm bằng `scripts/package_data.py verify`; Vrain có manifest riêng.
- Vrain login `https://www.vrain.vn/landing`; không nhắc lại mật khẩu, không lưu vào nguồn. Phiên mã hóa DPAPI ở `download/session.dpapi`. Kênh cũ `/api/vrain/private/v1/groups/29/stats/details`; mới `/api/kttv/private/v1/organizations/details`, ngữ cảnh tổ chức từ group đã xác thực, không đoán UUID.
- Tải nền dùng Start-Process `WindowStyle Hidden`, resume/checksum; đọc progress/PID thật trước nói tiến độ.

Giữ nguyên, không restore/build/stage hai slide người dùng sửa: `reports/daily_gauge_slides_2026_11_04/PBL6_DU_LIEU_NGAY_3_MO_HINH.pptx` và bản đổi tên `reports/short_range_three_models_2026_10_21/Dự đoán ngắn hạn 21_10.pptx` (bản tên gốc đã bị người dùng xóa). SnapshotSHA `data/operational/workspace_cleanup_2026_11_09/user_files.json`.

## Bằng chứng lịch sử, không phải mục tiêu hiện tại

- `reports/vrain_data_handoff_2026_11_09/DANH_GIA_KHA_THI_VA_HUONG_DI.md`: kiểm định nhãn vùng trước khi người dùng chốt theo trạm. 67 ngày tham chiếu nội bộ, NRMSE Thiessen toàn R93 16,3–21,4%, nhóm núi60–71%; không phải sai số dự báo hay chân lý diện tích.
- `reports/daily_gauge_2026_11_04/`: CPC168fits,144checkpointNN/288đầu ra cây/336split; chưa là Vrain hoặc theo trạm.
- `reports/short_range_complete_2026_10_28/`: GSMaP ba mô hình, giữ nguyên nguồn/kết quả.
- `reports/regional_research_plan_2026_10_20/PHUONG_AN_CUOI.md`: các quyết định có bằng chứng giữ đúng phạm vi cũ; không tự phủ nhận số đo cũ vì đổi mục tiêu.
- Dọn tài liệu09/11 đã được phép, có ZIPprivate/Git a05f6c0, `docs/cleanup_2026_11_09.json`. Không xóa bằng chứng thí nghiệm.
- Dataset/loaderERA5v1có34tests và kiểmtra toànfile; chưatrainv1. NWPpilotđãtrainnhưđầu file. Scriptsv1: `build_station_forecast_data.py`, `validate_station_forecast_data.py`, `publish_station_data_handoff.py`. Không đổi số đo vùng cũ thành kết quả trạm.
