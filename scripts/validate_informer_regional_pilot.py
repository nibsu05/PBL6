"""Independently replay every pilot checkpoint on calibration and development.

Only 2015–2023 source windows are loaded. Private forecasts stay outside Git.
"""
from pathlib import Path
import json,sys,time,itertools
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import torch
from src.informer_regional_pilot import RegionalInformer
from src.short_range_dataset import load_development,feature_groups,train_scaler,scale_inputs,file_hash
from src.short_range_evaluation import apply_calibration,score_predictions
from scripts.pilot_short_range import network_predict,dump


def main():
    start=time.perf_counter();report=ROOT/'reports/informer_regional_pilot_2026_10_21'
    private=ROOT/'data/operational/short_range/informer_pilot_2026_10_21'
    run=json.loads((report/'run.json').read_text(encoding='utf8'))
    assert run['status']=='complete' and len(run['models'])==18 and run['completed_seeds']==[42,43,44]
    assert {(m['seed'],m['year'],m['experiment']) for m in run['models']}==set(itertools.product([42,43,44],[2021,2022,2023],['E0','E7']))
    provenance_path=report/'code_provenance.json'
    provenance=json.loads(provenance_path.read_text(encoding='utf8')) if provenance_path.exists() else None
    for p,digest in run['protocol']['code_sha256'].items():
        if file_hash(ROOT/p)!=digest:
            import hashlib
            assert provenance is not None,p
            canonical=hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            assert canonical==provenance['files'][p]['normalized_lf_sha256'],p
    old=json.loads((ROOT/'reports/short_range_ablation_2026_10_21/run.json').read_text(encoding='utf8'))
    for p,digest in old['code_hashes'].items():assert file_hash(ROOT/p)==digest,p
    torch.set_num_threads(4);device='cuda' if torch.cuda.is_available() else 'cpu'
    data=load_development();groups=feature_groups();details=[]
    for meta in run['models']:
        path=private/meta['checkpoint'];assert file_hash(path)==meta['checkpoint_sha256']
        ck=torch.load(path,map_location='cpu',weights_only=True)
        samples=data.select(groups[meta['experiment']]);train=data.dates.year<meta['year']-1
        scaler={k:v.numpy() for k,v in ck['scaler'].items()}
        expected=train_scaler(samples.x[train])
        for k in scaler:np.testing.assert_array_equal(scaler[k],expected[k])
        x=scale_inputs(samples.x,scaler)
        model=RegionalInformer(**ck['config']).to(device);model.load_state_dict(ck['state'])
        for split,year,key in [('cal',meta['year']-1,'cal_predictions'),('eval',meta['year'],'eval_predictions')]:
            mask=data.dates.year==year;a,p=network_predict(model,x[mask],samples.future[mask],device)
            p=apply_calibration(p,meta['calibration']);saved=pd.read_parquet(private/meta[key])
            for day in [1,2,3]:
                part=saved[saved.lead_day==day]
                assert part.issue.tolist()==data.dates[mask].tolist()
                np.testing.assert_array_equal(part.obs,samples.y[mask,day-1])
                np.testing.assert_allclose(part.amount,a[:,day-1],rtol=2e-5,atol=1e-5)
                for i,q in enumerate([16,50,100]):np.testing.assert_allclose(part[f'p{q}'],p[:,day-1,i],rtol=2e-5,atol=1e-6)
        details.append(dict(year=meta['year'],experiment=meta['experiment'],seed=meta['seed'],full_cal_eval_replayed=True))
        del model
    frame=pd.read_parquet(private/'predictions_matched.parquet');assert set(frame.year)=={2021,2022,2023}
    frame['year']='pooled2021-2023'
    expected=score_predictions(frame);saved=pd.read_csv(report/'scores_pooled.csv')
    pd.testing.assert_frame_equal(expected,saved,check_dtype=False,rtol=1e-12,atol=1e-12)
    original=pd.read_csv(ROOT/'reports/short_range_ablation_2026_10_21/scores_ensemble_pooled.csv')
    a=saved[saved.model=='tft'].reset_index(drop=True)
    b=original[(original.model=='tft')&original.experiment.isin(['E0','E7'])].reset_index(drop=True)
    pd.testing.assert_frame_equal(a,b,check_dtype=False,rtol=1e-12,atol=1e-12)
    result=dict(status='passed',independent_full_replayed_runs=18,calibration_and_eval_splits_replayed=36,
                train_scalers_reproduced=18,same_completed_seeds_with_tft=True,tft_scores_match_original=True,
                scores_reproduced=True,test2025_read=False,seconds=time.perf_counter()-start,results=details)
    dump(report/'validation.json',result)
    compact=saved[(saved.season=='all')&(saved.threshold_mm==16)]
    lines=['| Mô hình | E | Ngày | RMSE | BSS | CSI | POD | FAR |','| --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in compact.itertuples():lines.append(f'| {r.model} | {r.experiment} | {r.lead_day} | {r.RMSE:.3f} | {r.BSS:.3f} | {r.CSI:.3f} | {r.POD:.3f} | {r.FAR:.3f} |')
    (report/'README.md').write_text('''# Pilot Informer vùng, E0/E7, 21/10/2026

Đã chạy 18 lượt = hai cấu hình × ba fold 2021–2023 × ba seed. Cùng seed hoàn chỉnh với TFT, cùng dữ liệu/nhãn/mẫu/lịch sử/đầu ra/loss/calibration. Không mở 2025 hoặc sửa nguồn huấn luyện TFT. Đây là bản Informer điều chỉnh, chưa tuning, chưa chạy E1–E6, không phải tái lập mọi benchmark bài gốc.

Informer E7 ngày 1 có BSS/CSI tốt hơn TFT theo điểm, RMSE hơi cao hơn. Ngày 3 cả hai vẫn BSS âm. Chưa có kiểm định chênh lệch kiến trúc hoặc lý do tuyên bố thắng tổng thể. Khả thi về tính toán đã được xác nhận, không phải bằng chứng vận hành.

'''+f'Thời gian tiến trình {run["elapsed_seconds"]/60:.2f} phút. Đã replay độc lập đủ 18 checkpoint trên cả calibration/evaluation; các điểm TFT tái tính khớp bảng cũ.\n\n'+'\n'.join(lines)+'''

- [Protocol khóa trước fit](protocol_frozen.json), [nhật ký](run.json), [kiểm tra độc lập](validation.json).
- [Điểm gộp đầy đủ](scores_pooled.csv), [điểm từng năm/mùa/ngưỡng](scores_by_year.csv).
- [Slide giải thích và kết quả](../short_range_revised_2026_10_21/README.md).

Checkpoint, scaler và dự đoán từng mốc ở data/operational ngoài Git. Chạy scripts/pilot_informer_regional.py theo protocol để tái lập; source SHA và tham số lưu trong protocol. Subclass mới sửa số query sparse theo mã tác giả, cố định lấy mẫu keys lúc eval cho replay; mã cũ giữ nguyên. Cùng hidden không đồng nghĩa cùng số tham số.
''',encoding='utf8',newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k!='results'},indent=2))


if __name__=='__main__':main()
