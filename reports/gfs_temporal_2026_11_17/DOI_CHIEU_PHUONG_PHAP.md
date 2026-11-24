# Hướng nghiên cứu này đứng ở đâu so với bài báo?

Tài liệu đối chiếu phương pháp, tra cứu ngày 17/11/2026. Không dùng các điểm số khác khu vực, ngưỡng mưa hay kỳ tích lũy để tuyên bố dự án tốt hơn nghiên cứu quốc tế.

## Hai công trình đã kiểm tra được nội dung trên trang tạp chí

| Công trình | Nội dung liên quan | Điều có thể học cho dự án |
| --- | --- | --- |
| Zhang và cộng sự, HESS 2023, *Statistical post-processing of precipitation forecasts using circulation classifications and spatiotemporal deep neural networks* | Hiệu chỉnh mưa dự báo ngày của ECMWF bằng hoàn lưu và thông tin khí tượng/địa hình theo không gian, thời gian | Có cơ sở cho hướng NWP + học máy và kiểm tra thông tin thời gian; không suy ra các biến mới chắc chắn hữu ích tại Đà Nẵng |
| Fang và cộng sự, GMD 2025, *Improving the fine structure of intense rainfall forecast by a designed generative adversarial network* | Kết hợp nhiều nguồn NWP, dự báo mưa lưới 3 giờ đến 24 giờ ở Bắc Trung Quốc; chú ý phân bố mưa lệch và mưa lớn | Cần đánh giá mưa lớn và đối chứng đơn giản cùng điều kiện; kiến trúc phức tạp vẫn cần kiểm chứng đúng bài toán |

Nguồn: [Zhang et al., 2023](https://hess.copernicus.org/articles/27/1945/2023/), [Fang et al., 2025](https://gmd.copernicus.org/articles/18/9723/2025/).

## Nguồn gần bài toán nhưng chưa đọc được toàn văn trong lần này

[*Spatiotemporal Convolutional Approach for the Short-Term Forecast of Hourly Heavy Rainfall Probability Integrating Numerical Weather Predictions and Surface Observations*, WAF 2024](https://journals.ametsoc.org/view/journals/wefo/39/3/WAF-D-23-0068.1.xml): phần nội dung được lập chỉ mục trên trang tạp chí có sử dụng LightGBM cho xác suất mưa lớn. Đây là ví dụ mô hình này được dùng trong nghiên cứu mưa. Bài toán theo giờ và sự kiện của họ khác ba tổng ngày tại trạm của dự án; không chuyển nguyên ngưỡng hoặc điểm POD sang đây. Trang toàn văn trả 403 khi truy cập, nên chưa dùng bài này làm bằng chứng chi tiết về thiết kế thí nghiệm.

## Điểm có thể bảo vệ của dự án

Đóng góp phù hợp nhất hiện tại là **kiểm tra giá trị thông tin bổ sung cho hiệu chỉnh dự báo mưa tại trạm trong điều kiện Đà Nẵng**, với cách tạo nhãn và đối chứng rõ ràng. Vòng mới kiểm tra liệu phân bố mưa 6 giờ và diễn biến khí tượng bên trong ngày có hơn tổng mưa ngày + một trạng thái giữa ngày hay không.

Các yếu tố giúp kết quả đáng kiểm tra gồm: cùng trạm và mẫu giữa cấu hình; tách biến bổ sung; ngân sách huấn luyện cố định; đối chứng GRU cùng số tham số nhưng không thêm thông tin; kiểm tra mưa lớn, báo nhầm và bất định theo đợt mưa; giữ cả kết quả không cải thiện. Đây là chất lượng thiết kế nghiên cứu, **chưa phải bằng chứng đã có phát hiện mới hoặc đạt mức bài báo quốc tế**.

## Điều chưa thể khẳng định

Chưa thể nói vượt các công trình trên: họ khác nguồn NWP, số năm, nhãn điểm/lưới, kỳ tích lũy, ngưỡng sự kiện và cách chia dữ liệu. Không so trực tiếp RMSE mm hoặc POD riêng lẻ giữa các bài toán đó. Dự án dùng GFS tất định và các trạm hiện có; các cấu trúc không gian cỡ nhỏ chưa được mô tả đầy đủ bởi lưới 0,25°.

2025–2026 đã được xem trong vòng trước, nên vòng cải tiến mới chỉ cung cấp đánh giá hồi cứu. Một ứng viên có điểm tốt hơn vẫn cần khóa trước một giai đoạn tương lai chưa dùng. Chưa xác nhận đầy đủ lịch sử cảm biến, tính liên tục hai API hoặc độ trễ tại thời điểm phát dự báo. Các giới hạn này cần được trình bày cùng mọi kết quả tích cực.
