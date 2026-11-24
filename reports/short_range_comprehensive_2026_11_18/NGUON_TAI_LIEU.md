# Nguồn tài liệu và giới hạn đối chiếu

Ngày kiểm tra:18/11/2026. Chỉ dùng nguồn gốc hoặc tài liệu của cơ quan phát hành; không xếp hạng dự án bằng điểm ở bài toán khác.

## [P1] Zhang & Ye · 2021 · JHM

[Machine Learning for Precipitation Forecasts Postprocessing: Multimodel Comparison and Experimental Investigation](https://journals.ametsoc.org/view/journals/hydr/22/11/JHM-D-21-0096.1.xml)

**Trạng thái:** Bài tạp chí bình duyệt.

**Đã kiểm tra:** Mục tóm tắt và các đoạn phương pháp/kết quả được lập chỉ mục trên trang nhà xuất bản; mở trực tiếp toàn văn trả HTTP 403.

**Cách sử dụng:** Cơ sở dùng LightGBM để hậu xử lý dự báo mưa; không dùng điểm số bài báo để xếp hạng dự án.

## [P2] Salehi & Salehi Neyshabouri · 2025

[A hybrid deep learning framework for improving short-term precipitation forecasts](https://doi.org/10.1016/j.envsoft.2025.106635)

**Trạng thái:** Environmental Modelling & Software, bài bình duyệt.

**Đã kiểm tra:** Đã kiểm tra nội dung tóm tắt/phương pháp công khai được lập chỉ mục ở ScienceDirect và kho mã của tác giả; trang toàn văn trả HTTP 403.

**Cách sử dụng:** GRU mã hóa mưa quá khứ, ghép dự báo nền CNRFC và lịch để dự báo mưa ngày; nguồn nhãn PRISM khác Vrain.

## [P3] Iwase & Takenawa · 2026 · preprint

[Improvements to the post-processing of weather forecasts using machine learning and feature selection](https://arxiv.org/html/2604.19340 v 1)

**Trạng thái:** Bản thảo arXiv v 1, chưa coi là bằng chứng bình duyệt.

**Đã kiểm tra:** Đã đọc bản HTML phương pháp và tóm tắt: LightGBM, MSM/JMA, 18 vị trí, nhãn mưa 3 h, đầu vào lân cận và Tweedie.

**Cách sử dụng:** Tham khảo lựa chọn biến/loss; khác kỳ đo và nguồn dự báo nên không so RMSE hoặc POD trực tiếp.

## [P4] Gneiting · 2011 · JASA

[Making and Evaluating Point Forecasts](https://arxiv.org/abs/0912.0902)

**Trạng thái:** Bài phương pháp, bản thảo tác giả công khai.

**Đã kiểm tra:** Đã kiểm tra tóm tắt tác giả trên arXiv; nội dung nhấn mạnh phải khớp scoring function với đại lượng cần dự báo.

**Cách sử dụng:** Cơ sở phân biệt mean/RMSE với median/MAE; lựa chọn metric trước khi xem kết quả.

## [D1] NOAA/NCEI · GFS

[Global Forecast System (GFS)](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast)

**Trạng thái:** Tài liệu cơ quan cung cấp.

**Đã kiểm tra:** Đã kiểm tra trang sản phẩm chính thức: GFS cung cấp dự báo nhiều trường khí tượng và sản phẩm 0,25°.

**Cách sử dụng:** Giải thích vai trò nguồn GFS; không dùng mô tả sản phẩm để khẳng định thời điểm phát hành lịch sử từng file đã được chứng minh.

## [D2] ECMWF/Copernicus · reanalysis

[Climate reanalysis](https://climate.copernicus.eu/climate-reanalysis)

**Trạng thái:** Tài liệu cơ quan cung cấp.

**Đã kiểm tra:** Đã kiểm tra mô tả ERA5 tái phân tích, dữ liệu giờ trên lưới 0,25° trong CDS.

**Cách sử dụng:** Phân biệt tái phân tích với số đo trạm và bản dự báo được phát trước issue.

## [D3] NOAA/MDL · MOS

[Model Output Statistics](https://vlab.noaa.gov/web/mdl/mos)

**Trạng thái:** Tài liệu cơ quan dự báo.

**Đã kiểm tra:** Đã kiểm tra định nghĩa MOS là quan hệ thống kê giữa đầu ra mô hình và quan trắc.

**Cách sử dụng:** Cơ sở đối chứng hậu xử lý đơn giản; MOS của dự án không phải tái hiện đầy đủ hệ thống MOS vận hành của NOAA.

## [P5] Lim và cộng sự · 2021 · TFT

[Temporal Fusion Transformers for interpretable multi-horizon time series forecasting](https://doi.org/10.1016/j.ijforecast.2021.03.012)

**Trạng thái:** International Journal of Forecasting, bình duyệt.

**Đã kiểm tra:** Đã kiểm tra tóm tắt gốc và định danh bài tạp chí; kiến trúc kết hợp đầu vào tĩnh, quá khứ và biết trước.

**Cách sử dụng:** Giải thích TFT là ứng viên hợp lệ, chưa có đối chứng TFT trên bộ GFS–Vrain hiện tại để kết luận nó kém.

## [P6] Zhou và cộng sự · 2021 · Informer

[Informer: Beyond Efficient Transformer for Long Sequence Time-Series Forecasting](https://arxiv.org/abs/2012.07436)

**Trạng thái:** AAAI 2021; bản thảo tác giả công khai.

**Đã kiểm tra:** Đã kiểm tra tóm tắt gốc về dự báo chuỗi dài và cơ chế ProbSparse.

**Cách sử dụng:** Không mặc định kiến trúc chuỗi dài cần thiết cho 7 ngày lịch sử/3 đầu ra; cũng không tuyên bố không khả thi khi chưa thử đúng dữ liệu.

## Nguồn số của dự án

Các bảng lấy từ CSV đã khóa trong ba thư mục: gfs_station_final_2026_11_17, gfs_temporal_2026_11_17 và gfs_training_window_2026_11_18. evidence_inputs.json lưu checksum; numeric_bindings.json lưu bộ lọc và cột cho từng số được trích. Các hình minh họa công thức được ghi rõ, không phải dự báo thực tế.

Thí nghiệm cũ được giữ nguyên. Bản slide chỉ đọc các kết quả, không fit lại mô hình hoặc đổi vai trò các số đã công bố. Đây là báo cáo mới bao quát nhiều nghiên cứu có phạm vi khác nhau, không gộp chúng thành một bảng test chung.
