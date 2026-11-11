# Hướng Vrain cho nghiên cứu dự đoán mưa vùng — 09/11/2026

- [Tài liệu đầy đủ gửi nhóm (Word)](PHUONG_AN_VRAIN_GUI_NHOM.docx), [bản Markdown](PHUONG_AN_VRAIN_GUI_NHOM.md).
- [Bản ngắn gửi nhóm (Word)](TOM_TAT_GUI_NHOM.docx), [nội dung có thể sao chép](TOM_TAT_GUI_NHOM.md).
- [Excel dữ liệu, probe, hợp đồng cột, đặc trưng và phân công](DU_LIEU_VRAIN_VA_PHAN_CONG.xlsx).
- [Audit cấu trúc](access_audit.json), [CSV probe](history_probe_summary.csv), [kiểm tra truy cập/xuất XLSX](web_access_check.json).
- [Hợp đồng dữ liệu đề xuất](dataset_contract.json), [từ điển cột CSV](DATA_DICTIONARY.csv).

Đã đăng nhập và xuất mẫu thật: inventory V1 82 trạm khớp history, V2 86 mục khác namespace. Mới kiểm tra mười ngày, chưa kiểm kê toàn kho; đủ 24 số không đồng nghĩa qua mọi QC. Chưa xác nhận đầy đủ thời gian/đơn vị, vị trí lịch sử, polygon và độ phủ. Chưa tạo nhãn vùng hoặc huấn luyện Vrain, chưa mở 2025. Giữ nguyên slide người dùng sửa và các báo cáo trước.

Tái lập kiểm kê với nguồn private: `scripts/audit_vrain_exports.py`. Kiểm thử parser: `python -m unittest tests.test_vrain_export_audit`. Xuất lại tài liệu từ aggregate công khai: `scripts/publish_vrain_research_plan.py`; kiểm tra bằng `scripts/validate_vrain_research_plan.py`. Các script này không đăng nhập, tải thêm hoặc học mô hình. Raw/XLSX gốc/inventory và phiên đăng nhập không nằm trong Git; cần quyền nguồn để nhận dữ liệu.
