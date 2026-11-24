"""Write the verified full-matrix summary and public artifact provenance."""
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd

REPORT=ROOT/'reports/informer_regional_matrix_2026_10_28'
BASE=ROOT/'reports/informer_regional_pilot_2026_10_21'
LABELS={'lgbm':'LightGBM','tft':'TFT','informer':'Informer'}


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    run=json.loads((REPORT/'run.json').read_text(encoding='utf8'))
    validation=json.loads((REPORT/'validation.json').read_text(encoding='utf8'))
    evaluation=json.loads((REPORT/'evaluation.json').read_text(encoding='utf8'))
    assert run['status']=='complete' and len(run['models'])==72 and validation['status']=='passed' and evaluation['status']=='complete'
    assert validation['informer_checkpoints_replayed']==72 and run['new_runs']==54 and run['reused_runs']==18
    scores=pd.read_csv(REPORT/'scores_ensemble_pooled.csv')
    s=scores[(scores.season=='all')&(scores.threshold_mm==16)]
    matrix=s.pivot(index=['experiment','lead_day'],columns='model',values='BSS').reset_index()
    matrix.to_csv(REPORT/'bss_three_models.csv',index=False,lineterminator='\n')
    threshold_parts=[pd.read_csv(REPORT/'ensemble_calibration_thresholds.csv'),
                     pd.read_csv(ROOT/'reports/short_range_ablation_2026_10_21/ensemble_calibration_thresholds.csv')]
    original=json.loads((ROOT/'reports/short_range_ablation_2026_10_21/run.json').read_text(encoding='utf8'))
    lgbm=[]
    for meta in original['models']:
        if meta['learner']!='lgbm':continue
        for p in meta['calibration']:
            lgbm.append(dict(model='lgbm',year=meta['year'],experiment=meta['experiment'],
                lead_day=p['lead_index']+1,threshold_mm=int(p['threshold_mm']),positive=p['positive'],
                negative=p['negative'],decision_threshold=p['decision_threshold'],fallback=min(p['positive'],p['negative'])<20))
    threshold_parts.append(pd.DataFrame(lgbm))
    thresholds=pd.concat(threshold_parts,ignore_index=True)
    assert len(thresholds)==648 and set(thresholds.model)=={'lgbm','tft','informer'}
    assert not thresholds.duplicated(['model','year','experiment','lead_day','threshold_mm']).any()
    thresholds.to_csv(REPORT/'calibration_thresholds_all_models.csv',index=False,lineterminator='\n')
    lines=['# Informer đủ E0–E7 — 28/10/2026','',
        '**Đã chạy bổ sung 54 lượt E1–E6** theo đúng hàm fit pilot và dùng lại **18 lượt E0/E7**. Tổng 72 Informer = tám E × ba năm đánh giá 2021–2023 × ba seed 42/43/44. Cùng 72 TFT và 24 pipeline LightGBM đã có, đủ 168 lượt mô hình/pipeline. Không tuning, không thay dữ liệu hoặc bước sáu giờ, không mở test 2025.','',
        f'Thời gian fit/save/replay của 54 lượt mới: **{run["new_fits_seconds"]/60:.2f} phút**; tiến trình gồm tập hợp điểm khoảng {run["invocation_seconds"]/60:.2f} phút. Không tính đây là thời gian hoàn thành toàn nghiên cứu.','',
        '**Kiểm chứng độc lập:** phát lại đủ 72 checkpoint trên 144 split calibration/evaluation; tái tạo scaler train, calibration và ensemble. Toàn bộ điểm TFT/LightGBM và điểm Informer E0/E7 giữ nguyên. Mỗi hạn có 1.075 mốc đánh giá, 114 sự kiện vùng từ 16 mm/24h; ba seed không nhân số ngày thời tiết.','',
        '## BSS theo ngày, đủ ba mô hình','']
    for day in [1,2,3]:
        lines += [f'### Ngày {day}','','| E | LightGBM | TFT | Informer |','| --- | ---: | ---: | ---: |']
        for i in range(8):
            e=f'E{i}';r=matrix[(matrix.experiment==e)&(matrix.lead_day==day)].iloc[0]
            lines.append(f'| {e} | {r.lgbm:.3f} | {r.tft:.3f} | {r.informer:.3f} |')
        lines.append('')
    lines += ['## E7: đọc cả lượng mm và xác suất','','| Ngày | Mô hình | RMSE | BSS | CSI | POD | FAR |','| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for day in [1,2,3]:
        for model in ['lgbm','tft','informer']:
            r=s[(s.model==model)&(s.experiment=='E7')&(s.lead_day==day)].iloc[0]
            lines.append(f'| {day} | {LABELS[model]} | {r.RMSE:.3f} | {r.BSS:.3f} | {r.CSI:.3f} | {r.POD:.3f} | {r.FAR:.3f} |')
    lines += ['',
        'Ở E7 ngày 1, LightGBM tốt hơn theo RMSE/BSS/FAR; Informer có CSI cao nhất; TFT có POD cao nhất. Cả ba E7 ngày 3 BSS âm. Riêng Informer E6 ngày 3 có BSS khoảng +0,004, chỉ giảm khoảng 0,4% sai số Brier; không đủ để tự khẳng định kỹ năng chắc chắn. Điểm tốt hơn chưa tự là ý nghĩa thống kê hoặc lý do chọn một kiến trúc duy nhất. Các E khác cần đọc đầy đủ theo bảng trên.','',
        '## Khoảng tin cậy và giới hạn','',
        'Có 20.000 bootstrap paired theo khối bảy ngày và độ nhạy 14 ngày, giữ chung mốc/ngày đích/nhãn/tham chiếu. CI95% mới là **mô tả**, chưa hiệu chỉnh nhiều phép và có điều kiện trên các ensemble đã fit; không bao trùm toàn bộ bất định nhãn/huấn luyện. Năm phát triển và E0/E7 đã được xem trước. Không thay phép thử TFT chính và không gọi phân tích này là holdout độc lập.','',
        'Thêm biến cũng có thể làm thay đổi số tham số mạng. Cây dùng thống kê lịch sử, mạng dùng chuỗi nên chưa cô lập riêng kiến trúc. Footprint 93 toàn ô vẫn xấp xỉ; nhãn và ranh cần QC. Độ phân giải sáu giờ chưa được đối chứng 1h/3h/6h. Không suy ra đã dự báo vận hành tốt đến 72 giờ chỉ vì đủ ma trận.','',
        '## Tệp kết quả và tái lập','',
        '- [Báo cáo, slide, Word và Excel đủ ba mô hình](../short_range_complete_2026_10_28/README.md).',
        '- [Protocol khóa trước 54 lượt mới](protocol_frozen.json), [nhật ký 72 lượt](run.json), [kiểm chứng độc lập](validation.json).',
        '- [Điểm gộp đủ mùa/ngưỡng](scores_ensemble_pooled.csv), [từng năm](scores_ensemble.csv), [ba seed Informer](scores_seed_pooled.csv), [độ ổn định seed](seed_stability.csv).',
        '- [CI chênh lệch mô tả](paired_bootstrap_exploratory.csv), [CI điểm E7](absolute_skill_ci.csv), [reliability](reliability16.csv), [ngưỡng chọn trên calibration của cả ba mô hình](calibration_thresholds_all_models.csv).','',
        'Chạy `python scripts/run_informer_regional_matrix.py`, `python scripts/validate_informer_regional_matrix.py`, `python scripts/evaluate_informer_regional_matrix.py`, rồi `python scripts/publish_informer_regional_matrix.py`. Cần V1, artifact pilot E0/E7 và artifact TFT/LightGBM gốc ngoài Git. Hàm fit cũ giữ nguyên; runner chỉ chuyển thư mục lưu. Runner có thể tiếp tục các job chưa xong. Raw data/checkpoint/scaler/dự đoán từng mốc ở `data/operational/short_range/`, không công bố vào repo.','']
    (REPORT/'README.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf8',newline='\n')
    source_paths=list(run['protocol']['base_protocol']['code_sha256'])+[
        'src/short_range_ablation.py','src/verification.py','src/dataset_v2.py',
        'scripts/run_informer_regional_matrix.py','scripts/validate_informer_regional_matrix.py',
        'scripts/evaluate_informer_regional_matrix.py','scripts/publish_informer_regional_matrix.py']
    provenance={name:dict(workspace_sha256=sha(ROOT/name),normalized_lf_sha256=hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()) for name in source_paths}
    (REPORT/'code_provenance.json').write_text(json.dumps(dict(note='Inherited pilot fit unchanged; canonical LF hashes support equivalent Git checkouts.',files=provenance),indent=2)+'\n',encoding='utf8',newline='\n')
    files={p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in REPORT.iterdir() if p.is_file() and p.name!='publication_manifest.json'}
    manifest=dict(status='complete',new_informer_runs=54,reused_informer_runs=18,total_informer_runs=72,
                  test2025_read=False,files=files,source_pilot_protocol_sha256=sha(BASE/'protocol_frozen.json'))
    (REPORT/'publication_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8',newline='\n')
    print('Published verified Informer matrix summary:',len(files),'artifacts')


if __name__=='__main__':main()
