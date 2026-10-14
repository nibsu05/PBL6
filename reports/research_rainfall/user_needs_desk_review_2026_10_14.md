# Khảo sát tài liệu về bài toán và nhu cầu người dùng, 14/10/2026

**Phạm vi bằng chứng:** Đây là khảo sát tài liệu công khai để xác định giả thuyết thiết kế. Nhóm **chưa phỏng vấn** người dân, cán bộ ứng phó hoặc cơ quan khí tượng; không trình bày các nhu cầu dưới đây như kết quả khảo sát người dùng trực tiếp.

## Hiện trạng địa phương

Ứng dụng Danang Smart City của thành phố đã có tiện ích theo dõi lượng mưa, mực nước và bản đồ điểm ngập theo thời gian thực, cùng chức năng phản ánh tình trạng ngập và hỗ trợ khẩn cấp. Vì thế nhóm không nên giới thiệu đồ án là “bản đồ mưa/ngập đầu tiên”. Giá trị cần thử là **thông tin mưa trong 0–6 giờ tới theo khu vực và xác suất vượt ngưỡng**, có ghi thời điểm phát hành/nguồn/độ cũ và kiểm định dự báo. Đây là **lớp thông tin dự báo**, không phải bản đồ độ sâu ngập hay cảnh báo chính thức. [Nguồn thành phố](https://tralien.danang.gov.vn/chuyen-doi-so/cac-tinh-nang-ho-tro-ung-pho-thien-tai-tren-ung-dung-danang-smart-city-324820).

Một bài trên cổng HĐND Đà Nẵng nêu nhu cầu biết khu vực có nguy cơ ngập để chọn đường đi và đề xuất bản đồ số dễ hiểu cùng các kịch bản mưa. Đây là quan điểm trong tài liệu công, không là dữ liệu phỏng vấn đại diện người dùng. [Nguồn HĐND](https://hdnd.danang.gov.vn/chi-tiet-tin/group/157/nid/23678/som-cong-khai-ban-do-ngap-lut-cua-thanh-pho-da-nang).

WMO nhấn mạnh thông tin cảnh báo cần **kịp thời, hiểu được và gắn với hành động**; dự báo theo tác động cần thêm dữ liệu phơi nhiễm/vulnerabilities ngoài bản thân lượng mưa. Vì đồ án hiện chỉ dự báo lượng mưa theo ô, nhóm **chưa thể** suy trực tiếp “đường này sẽ ngập” hoặc đưa khuyến nghị sơ tán. [Nguồn WMO](https://public.wmo.int/resources/wmo-bulletin/wmo-bulletin-vol-71-1-2022/communicating-life-saving-action-enhancing-messaging-early-warnings-systems).

## Giả thuyết người dùng để kiểm chứng sau buổi gặp

| Người dùng dự kiến | Quyết định có thể cần chuẩn bị | Thông tin đồ án có thể cung cấp | Chưa chứng minh |
| --- | --- | --- | --- |
| Người dân/đi lại trong thành phố | Có nên chuẩn bị thay đổi giờ hoặc tuyến đi khi mưa mạnh sắp đến? | Khu vực ô lưới, tổng mưa 3 giờ tới, xác suất ≥10 mm/3 giờ, giờ cập nhật | Ngưỡng 10 mm có phù hợp với quyết định đi lại của họ không; ô 0,1° không chỉ ra đoạn đường ngập |
| Cán bộ xã/phường hoặc lực lượng ứng phó | Có cần theo dõi sát một khu vực trước đợt mưa mạnh? | Bản đồ 93 ô, nơi có khả năng mưa lớn, thời gian/hạn dự báo, trạng thái nguồn | Quy trình hành động cụ thể, ngưỡng cần báo và cách tiếp nhận thông tin |
| Người quản trị ứng dụng/bộ ghi | Có thể tin dữ liệu đầu vào tại giờ phát hành không? | `first_recorded_at`, độ trễ tệp NRT, nguồn forecast, fallback khi thiếu/cũ | Năng lực vận hành liên tục qua nhiều ngày và kỹ năng T-OPS |

**Giới hạn sản phẩm:** Lưới 0,1° khoảng 11 km, không có mô hình thủy lực, cống thoát nước, triều và địa hình đường phố. App chỉ nói lượng mưa/xác suất trên một ô; việc cảnh báo ngập cấp đường cần mô hình/tổ chức khác và sự kiểm chứng riêng.

**Việc nghiên cứu người dùng tiếp theo:** hỏi một nhóm nhỏ đại diện các vai trò trên về quyết định thực tế, mốc thời gian hữu ích, cách hiểu xác suất và ngưỡng mưa; cho họ xem demo để kiểm tra cách đọc bản đồ. Ghi rõ số người/địa điểm và điều chỉnh ngưỡng/giao diện theo phản hồi, không suy từ tài liệu công rằng người dùng đã chấp nhận sản phẩm.

## Hạn dự báo: bằng chứng sản phẩm và câu hỏi khảo sát

[WMO OSCAR](https://space.oscar.wmo.int/applicationareas/view/2_3_nowcasting_very_short_range_forecasting) mô tả nowcasting là dự báo thời tiết địa phương từ hiện tại đến 6 giờ tới. [MyObservatory của Hong Kong Observatory](https://www.hko.gov.hk/en/myobservatory.htm) có dự báo mưa theo vị trí trong 1 hoặc 2 giờ. [Cơ quan Khí tượng Đài Loan (CWA, tr. 24)](https://www.cwa.gov.tw/Data/service/notice/download/Publish_20250326113535.pdf) cho biết họ phát hành lượng mưa dự báo theo **khoảng 3 giờ** cho 12 giờ tới trong đợt bão/mưa lớn. Ví dụ CWA nói về khoảng cộng dồn, **không** nói chỉ dự báo đến giờ thứ 3.

Những nguồn này cho thấy sản phẩm dự báo vài giờ và tổng mưa 3 giờ có tiền lệ chuyên môn. Chúng **không đo nhu cầu của người dùng Đà Nẵng**. Việc nhóm ưu tiên kiểm chứng 0–3 giờ là lựa chọn thử nghiệm hiện tại, phù hợp với bảng kết quả tổng mưa 3 giờ đã có; sản phẩm A vẫn dự kiến xuất hạn 1–6 giờ. [Slide khảo sát đề tài độc lập](../presentation_2026_10_14/Khao_sat_de_tai_1_slide_2026_10_14.pptx) tóm lược ranh giới này để trình bày.

Khi phỏng vấn người dùng, hỏi về một quyết định cụ thể trước mưa, rồi cho chọn mốc cần biết trước **1, 3 hoặc 6 giờ**; hỏi thêm họ cần lượng mưa, xác suất hay trạng thái nguồn, và dữ liệu cũ bao lâu thì họ không muốn dùng. Chỉ sau khi thu và ghi rõ mẫu khảo sát mới kết luận mốc nào được ưu tiên.
