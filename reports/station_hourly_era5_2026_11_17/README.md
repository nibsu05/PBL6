# Dữ liệu giờ ERA5 + Vrain đến 2026

Bản 17/11/2026 đã ghép và kiểm chứng. File chính private: `data/processed/station_hourly_era5_2026_11_17/PBL6_TRAM_GIO_ERA5_2021_2026.parquet`.
Gửi nhóm ZIP `PBL6_BILSTM_GIO_2021_2026.zip` trong cùng thư mục dữ liệu; chỉ có năm file.

Đọc [mô tả](MO_TA_DU_LIEU.md), [Word](MO_TA_DU_LIEU.docx), [cách đọc để train](HUONG_DAN_TRAIN.md).
Mưa tới 19h15/11, khí tượng ghép tới hàng kết thúc07h11/11/2026 giờ Việt Nam. Giữ thiếu ở đuôi.
86 vị trí; 79 có train theo split cố định. 44 khí tượng/lịch + mưa quá khứ; X24×45, y6.
Hai API đều Vrain, chưa xác nhận liên tục; mẫu yêu cầu cùng nguồn cả lịch sử/nhãn.
Đây là dữ liệu hồi cứu, không phải bằng chứng khả dụng realtime hay kết quả train mới.
Mô tả và số liệu kiểm chứng là aggregate; raw/registry/Parquet không nằm trên GitHub.
