# Kết quả pilot24–72 giờ để báo cáo ngày mai

Số liệu21/10/2026, chuẩn bị cho ngày 22/10. **Pilot một seed, chưa mở 2025.**

- [Báo cáo đầy đủ](BAO_CAO_PILOT.md) / [Word](BAO_CAO_PILOT.docx).
- [PowerPoint7slide chỉnh sửa được](PBL6_TFT_24_72h_pilot_2026_10_21.pptx):6slide chính,1reliability dự phòng; có ghi chú trình bày.
- [Khung4giờ](PILOT_TRONG_4_GIO.md), [bảng theo năm](scores.csv), [bảng gộp](scores_pooled.csv), [CI](paired_bootstrap.csv).
- [Kiểm tra checkpoint](checkpoint_audit.json), [log/cấu hình](run.json).

- Ngày 1, E7: BSS LightGBM=0.303; TFT=0.220.
- Ngày 1: RMSE LightGBM=17.71; TFT=20.39mm/24 h.
- Ngày 3, E7: BSS LightGBM=-0.075; TFT=-0.047.
- Mới là pilot một seed; chưa chứng minh TFT tốt hơn đối chứng.

Đã hoàn tất6 lượtTFT và6 pipelineLightGBM,23 kiểm tra code đạt,12/12 lượt tái lập. Dữ liệu V1 hiện là footprint93 ô xấp xỉ; chưa là kết quả toàn địa giới hoặc vận hành. Dự báo từng dòng/checkpoint nằm ngoàiGit. Không dùng pilot để bác bỏInformer hoặc khẳng định TFT chắc chắn tốt hơn.

Chạy lại theo thứ tự: scripts/pilot_short_range.py → scripts/audit_short_range_pilot.py → scripts/evaluate_short_range_pilot.py → scripts/report_short_range_pilot.py, dùng Python trong .venv. XuấtWord/slide cầnpython-docx/python-pptx. Không chạy pilot lại chỉ để đọc báo cáo đã có.
