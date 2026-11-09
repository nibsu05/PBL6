# Thiết kế kỹ thuật hiện hành — ERA5 và Vrain

Cập nhật09/11/2026. [README](README.md) chỉ vị trí dữ liệu/tiến độ; [kế hoạch công việc](KE_HOACH_DU_AN.md) chỉ giai đoạn. Lịch sử trước khi rút gọn còn trongGit a05f6c0.

## 1. Bài toán

Dự đoán trực tiếp mưa trung bình theo diện tích của Đà Nẵng mới. Một issue vùng là một mẫu. Polygon cuối và phần không được mạng trạm đại diện cần xác nhận; footprint93ô chưa phải ranh chính xác.

- Giờ: X24giờ×F → sáu lượng mưa giờ tiếp theo.
- Ngày: Xbảyngày×F → ba tổng24hriêng, không tích lũy24/48/72h.
- Các độ dài lịch sử trên là lựa chọn ban đầu, chưa chứng minh tối ưu.

## 2. Thu thập và dữ liệu đã có

Đợt tải hoàn tất17:57VN09/11/2026. Đã kiểm tra SHA256 của3.653tệp nén và dữ liệu giải nén. Có bảng24h cho toàn bộ ngày2021–2024, nhưng vẫn thiếu tại trạm;2015–2020không trả hàng giờ trong toàn bộ các ngày đã yêu cầu. Ba ngày có chênh tổng cầnQC. [Thống kê kiểm kê sau tải](docs/vrain_archive_summary.json). Tải đủresponse không đồng nghĩa nhãn vùng đã sẵn sàng.

Phạm vi tới2024là quyết định thu thập, không phải giới hạnVrain. Đã kiểm tra kênh hiện hành`kttv`86trạm có dữ liệu10phút ngày09/11/2026 và giờ ngày15/10,08/11/2026. Truy cập cần ngữ cảnh tổ chức như giao diện; nhómV1cũ82IDrỗng không đủ kết luận không có dữ liệu gần đây. Ngược lại, bảng mới2024-10-14có24hnhưng toàn thiếu, không đếm hàng thay số liệu hợp lệ; giai đoạn2024có số ởkênhcũ. [Bằng chứng](docs/vrain_recent_check.json). Chưa tải toàn2026, chưa đọc2025, chưa xác nhận crosswalk hai namespace hoặc độ trễ truyền được bảo đảm.

Collector yêu cầu3653ngày2015–2024, từ chối2025. Mỗi ngày một response giữ giờ; request nhiều ngày đã kiểm tra chỉ trả tổng ngày. Tối đa1request/s, retry/backoff, khóa mộtworker và resumechecksum.

Trong `data/operational/vrain_2026_11_09/download/`: raw/YYYY/*.json.gz giữ nguồn, manifest.sqlite giữ SHA/counts/provenance, progress.json giữ trạng thái sống, session.dpapi giữ phiên mã hóa ngoàiGit. Không lưu mật khẩu. Khi tải xong vẫn phải QC và tạo nhãn.

InventoryV1có82ID/UUIDkhớphistory. V2có86mục khác namespace, không ép nối theo tên. Metadata vị trí trong quá khứ cần xác minh. Mười probe ban đầu không chứng minh lịch sử liên tục hoặc phủ toàn vùng.

ERA5/bộvùngV1/V2 ở `data/processed/regional_danang/`,102984giờ2015–09/2026UTC,49/138predictorứngviên, nhãnGSMaPcũ. Nguồn0,25°được biểu diễn0,1° không tăng thông tin vật lý; nội suy cũ có thể bỏ nútNaN. Không nhầm dữ liệu này với nhãnVrain.

## 3. Chuẩn hóa và nhãn

Xác nhận đơn vị, timezone, timestamp đầu/cuối kỳ, increment/counter/rate/tổngtrượt và mã thiếu/trace/reset trước ghépUTC. XLSX có tiêu đề19:20 nhưng cột cuối19:00; không tự áp mốcCPC12UTC.

Lưu period_start/endUTC, mưa, QC, provenance/retrieved_at. available_at chỉ ghi khi biết thật. Tải hồi cứu hôm nay không chứng minh nguồn đã có tại giờforecast.

Không cộng hàng tổng vào24h, không đổi dấu thiếu thành0. Cực trị/khácERA5 hoặc hàngxóm là cờ rà soát, không tự xóa. Raw cấu trúc lạ giữ và đánh dấu, không sửa âm thầm.

Chốt polygonR và panel lõi, trọng số Thiessen cắt ranh trong CRSphẳngphùhợp:

`w_i = area(Voronoi_i intersect R) / area(R)`

`y_region(t) = sum_i w_i * rain_i(t)`

`coverage(t) = sum_i w_i * valid_i(t)`

Không chuẩn hóa lại theo trạm còn lại trong nhãn chính. Nếu thiếu quá nhiều, chọn panel bằngmetadata/development hoặc thử estimator mạngkhuyết riêng. Không lấp bằngCPC/GSMaP/ERA5 rồi gọi thuầnVrain.

Kiểm chứng rúttrạm/LOSO, nhạy panel/phương pháp, tổng giờ–ngày, cực trị và mẫu bị loại theo mùa. Sốtrạm/coverageThiessen chưa chứng nhận vùngnúi/đảo. XERA5 vày cùngpolygon; tải bổ sung khí tượng nếu ranh vượt cube.

## 4. Đặc trưng và thí nghiệm

| Nhóm | Số biến ngày/giờ | Nội dung |
| --- | --- | --- |
| B | 9/11 | Bảy biến bề mặt và lịch; giờ thêm sin/cosgiờ |
| A | 12/12 | Đối lưu, hơi nước, mây, lớp biên và đất |
| M | 20/20 | Trường850/500, shear, IVT/VIMD, context và chênháp |
| C | 1/1 | SSThộpbiển, chưa đầyđủENSO/MJO |
| Rđềxuất | 1/1 | Một kênh mưa vùng quákhứ, thử riêngR0/R1 |

E0B/E1BA/E2BM/E3BC/E4BAM/E5BAC/E6BMC/E7BAMC.
NgàyR0:9/21/29/10/41/22/30/42; R1mỗiEtăng1. Giờ thêm2mãhóa giờ. Đây là sốkênh, không phải sốcột cây sau tóm tắt.

Pilot E0/E2/E7 cùngVrain/mask, thửR0/R1 riêng. Saupilot chọnR cốđịnh cho mọiE/model rồi chạy đủE0–E7. Nhánhngày so đồngthờiLightGBM/TFT/Informer, nhánhgiờBi-LSTM/LightGBM. Không ép mạng thắng hoặc chạyInformer chỉ để bác nó.

Chỉ lịch tươnglai biết trước được dùng; khôngERA5/mưa giờđích trongX. Không nốiCPC trước năm cótrạm vàVrain sau đó thành nhãn đồng nhất; pretrain/fine-tune là thí nghiệm riêng. Nhiều hàng giờ không tạo thêm nhiều mùa độc lập.

## 5. Split và đánh giá

- Chia theo lịch sử Vrain thực sauQC; không ép train từ2015.
- Ví dụ cóđiềukiện nếu2021–2024đủ: train2021/cal2022/eval2023; train2021–2022/cal2023/eval2024. Chưa chốt khi chưa kiểm kê.
- Scaler/climatefittrain; earlystop/Platt/tau chỉcal. Toàn bộ y trongsplit, mask chungmọiE/model vàR0/R1 khi so.
- 2025giữkín; không tuning2026 rồi gọi2025làtesttươnglai. Thiếu lịch sử thì đăng ký lại kế hoạch trước mởtest.
- CSI/BSSchính; POD/FAR, RMSE/MAE/Bias/BS bổ sung; báo n/events/mùa/năm. Không có chuẩnPOD0,4tốtchung.
- Ngưỡngngày16/50/100 là ngưỡngnghiêncứumưavùng; giờ cần ngưỡng đúngkỳ. Ngưỡng quyết định xác suất chọncal.
- Bootstrap pairedkhối, kiểm tra độnhạy; khóa nhóm phépso/hiệuchỉnh. Chữđậm không thayCI; development chưaholdout.
- ERA5 làhồi cứu; chưa chứng minh cósẵntạiissue. Nếu thêmNWP phải dùngrunđãphát trướcissue, khôngERA5tươnglai.

## 6. Bằng chứng và công cụ

- [Phương án Vrain đầy đủ](reports/vrain_research_plan_2026_11_09/PHUONG_AN_VRAIN_GUI_NHOM.md): nguồn sơ cấp, cổngG0–G6, sáutiêuchí.
- [CPCngày](reports/daily_gauge_2026_11_04/README.md):168fits, E7BSSngày1LG/TFT/IF0,190/0,026/0,078; ngày2–3âm. Không gọiVrain.
- [GSMaPđủ ba mô hình](reports/short_range_complete_2026_10_28/README.md).
- [Phương án hợp nhất](reports/regional_research_plan_2026_10_20/PHUONG_AN_CUOI.md):giữD1/D2/D9/D10/D14/D15đúngphạmvi. CóVrain mới chưa tự bác phépđo cũ.
- [Danh mục biến](reports/daily_gauge_2026_11_04/feature_catalog_daily.csv); miềnSST/contextngoàiđấtliền cóchủđích.

Kiểm thử mới: `python -m unittest tests.test_vrain_download tests.test_vrain_export_audit`.
Nguồn cũ kiểm bằng `scripts/package_data.py verify`; Vrain cómanifest riêng.

Không commitraw/PDF/credential/checkpoint/dựđoántừngmốc. Không thay/stageslide người dùng sửa. Các báo cáo trình bày/kế hoạch cũ bị xóa09/11cóZIPprivate vàGit a05f6c0; checkoutbảnđó khi tái lập công cụ lịch sử.
