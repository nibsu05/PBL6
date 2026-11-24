# Nguồn phương pháp và cách sử dụng

Các bảng số lấy từ CSV/protocol đã khóa trong evidence_inputs.json. Bản này chỉ trình bày, không huấn luyện hoặc chấm lại.

## [P1] Zhang & Ye · 2021 · JHM

[Machine Learning for Precipitation Forecasts Postprocessing: Multimodel Comparison and Experimental Investigation](https://journals.ametsoc.org/view/journals/hydr/22/11/JHM-D-21-0096.1.xml)

Bài tạp chí bình duyệt

Mục tóm tắt và các đoạn phương pháp/kết quả được lập chỉ mục trên trang nhà xuất bản; mở trực tiếp toàn văn trả HTTP403.

Cơ sở dùng LightGBM để hậu xử lý dự báo mưa; không dùng điểm số bài báo để xếp hạng dự án.

## [P2] Salehi & Salehi Neyshabouri · 2025

[A hybrid deep learning framework for improving short-term precipitation forecasts](https://doi.org/10.1016/j.envsoft.2025.106635)

Environmental Modelling & Software, bài bình duyệt

Đã kiểm tra nội dung tóm tắt/phương pháp công khai được lập chỉ mục ở ScienceDirect và kho mã của tác giả; trang toàn văn trả HTTP403.

GRU mã hóa mưa quá khứ, ghép dự báo nền CNRFC và lịch để dự báo mưa ngày; nguồn nhãn PRISM khác Vrain.

## [P3] Iwase & Takenawa · 2026 · preprint

[Improvements to the post-processing of weather forecasts using machine learning and feature selection](https://arxiv.org/html/2604.19340v1)

Bản thảo arXiv v1, chưa coi là bằng chứng bình duyệt

Đã đọc bản HTML phương pháp và tóm tắt: LightGBM, MSM/JMA, 18 vị trí, nhãn mưa3h, đầu vào lân cận và Tweedie.

Tham khảo lựa chọn biến/loss; khác kỳ đo và nguồn dự báo nên không so RMSE hoặc POD trực tiếp.

## [P4] Gneiting · 2011 · JASA

[Making and Evaluating Point Forecasts](https://arxiv.org/abs/0912.0902)

Bài phương pháp, bản thảo tác giả công khai

Đã kiểm tra tóm tắt tác giả trên arXiv; nội dung nhấn mạnh phải khớp scoring function với đại lượng cần dự báo.

Cơ sở phân biệt mean/RMSE với median/MAE; lựa chọn metric trước khi xem kết quả.

## [D1] NOAA/NCEI · GFS

[Global Forecast System (GFS)](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast)

Tài liệu cơ quan cung cấp

Đã kiểm tra trang sản phẩm chính thức: GFS cung cấp dự báo nhiều trường khí tượng và sản phẩm0,25°.

Giải thích vai trò nguồn GFS; không dùng mô tả sản phẩm để khẳng định thời điểm phát hành lịch sử từng file đã được chứng minh.

## [D2] ECMWF/Copernicus · reanalysis

[Climate reanalysis](https://climate.copernicus.eu/climate-reanalysis)

Tài liệu cơ quan cung cấp

Đã kiểm tra mô tả ERA5 tái phân tích, dữ liệu giờ trên lưới0,25° trong CDS.

Phân biệt tái phân tích với số đo trạm và bản dự báo được phát trước issue.

## [D3] NOAA/MDL · MOS

[Model Output Statistics](https://vlab.noaa.gov/web/mdl/mos)

Tài liệu cơ quan dự báo

Đã kiểm tra định nghĩa MOS là quan hệ thống kê giữa đầu ra mô hình và quan trắc.

Cơ sở đối chứng hậu xử lý đơn giản; MOS của dự án không phải tái hiện đầy đủ hệ thống MOS vận hành của NOAA.

## [P5] Lim và cộng sự · 2021 · TFT

[Temporal Fusion Transformers for interpretable multi-horizon time series forecasting](https://doi.org/10.1016/j.ijforecast.2021.03.012)

International Journal of Forecasting, bình duyệt

Đã kiểm tra tóm tắt gốc và định danh bài tạp chí; kiến trúc kết hợp đầu vào tĩnh, quá khứ và biết trước.

Giải thích TFT là ứng viên hợp lệ, chưa có đối chứng TFT trên bộ GFS–Vrain hiện tại để kết luận nó kém.

## [P6] Zhou và cộng sự · 2021 · Informer

[Informer: Beyond Efficient Transformer for Long Sequence Time-Series Forecasting](https://arxiv.org/abs/2012.07436)

AAAI2021; bản thảo tác giả công khai

Đã kiểm tra tóm tắt gốc về dự báo chuỗi dài và cơ chế ProbSparse.

Không mặc định kiến trúc chuỗi dài cần thiết cho7ngày lịch sử/3đầu ra; cũng không tuyên bố không khả thi khi chưa thử đúng dữ liệu.

## [E1] LightGBM · objective

[L2 và Tweedie với log-link; p = 1,5 là cấu hình của dự án](https://lightgbm.readthedocs.io/en/stable/Parameters.html)

Tài liệu chính thức; không chứng minh Tweedie luôn tốt hơn

Đã đối chiếu tài liệu chính thức công khai.

Chỉ hỗ trợ giải thích phương pháp; không chứng nhận kết quả dự án.

## [E2] scikit-learn · Tweedie

[Với 1 < p < 2: hỗ trợ giá trị 0 và giá trị dương liên tục](https://scikit-learn.org/stable/modules/linear_model.html#tweedie-regression)

Cơ sở thử một loss phù hợp dữ liệu không âm, lệch

Đã đối chiếu tài liệu chính thức công khai.

Chỉ hỗ trợ giải thích phương pháp; không chứng nhận kết quả dự án.

## [E3] ECMWF · Brier score

[Brier score và Brier skill score so với tham chiếu](https://confluence.ecmwf.int/pages/viewpage.action?pageId=240849421)

Dùng để giải thích ý nghĩa BSS, không đặt ngưỡng đạt cho dự án

Đã đối chiếu tài liệu chính thức công khai.

Chỉ hỗ trợ giải thích phương pháp; không chứng nhận kết quả dự án.

## [E4] ECMWF · quyết định

[Understanding how forecast users make decisions](https://www.ecmwf.int/en/newsletter/165/news/understanding-how-forecast-users-make-decisions)

Mức chấp nhận phụ thuộc mục đích và chi phí quyết định

Đã đối chiếu tài liệu chính thức công khai.

Chỉ hỗ trợ giải thích phương pháp; không chứng nhận kết quả dự án.

## [E5] PyTorch · GRU

[GRU: mạng hồi quy có cổng ghi nhớ thông tin trong chuỗi](https://docs.pytorch.org/docs/2.15/generated/torch.nn.GRU.html)

Tài liệu chính thức; cấu hình nhỏ của dự án không phải thuật ngữ kiến trúc riêng

Đã đối chiếu tài liệu chính thức công khai.

Chỉ hỗ trợ giải thích phương pháp; không chứng nhận kết quả dự án.
