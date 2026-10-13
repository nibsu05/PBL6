"""Train lại Bi-LSTM RAW Tweedie với quan trắc lag5, so cặp lag4 cùng mẫu.

Giữ 30 ô/index train-cal-eval, 3 seed, kiến trúc/ngân sách/loss của run lag4.
Tau và Platt fit lại ở cal trước khi chấm validation2021–23; không mở 2025.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.dataloader_v2 import DatasetV2, sample_index
from src.rainfall_losses import tweedie_deviance, TweedieJointLoss
from src.verification import paired_block_bootstrap, metric_rmse, metric_csi
from scripts.followup_danang import metadata, write_run, load_sampler, cfg_for, taus_for, PRIVATE, REPORT, SOURCE
from scripts.screen_danang_domain import pack, nn_train, predict_pack, score
from scripts.pilot_bilstm_v2 import calibrate, climatology, totals

LOG = logging.getLogger('tweedie_lag5')


def json_safe(value):
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def run_year(ds, source, meta, args, year, device):
    folder = SOURCE / str(year)
    report = REPORT / 'bilstm_tweedie_lag5'
    target = PRIVATE / 'bilstm_tweedie_lag5' / str(year)
    target.mkdir(parents=True, exist_ok=True)
    train, cal, ev = [np.load(folder / f'index_{part}.npy') for part in ('train', 'cal', 'eval')]
    sampler = load_sampler(ds, source, year, 'RAW')
    if sampler.cfg.latency_h != 4:
        raise ValueError('Nguồn không phải lag4')
    sampler.cfg.latency_h = 5
    tr, ca, ee = [pack(sampler, index) for index in (train, cal, ev)]
    if not np.array_equal(ee['y'], np.stack([ds.cube[c, t:t+6, ds.feature_index['y_gsmap_gc_mm']]
                                             for c, t in ev])):
        raise ValueError('Nhãn lag5 thay đổi so source index')
    yt = torch.from_numpy(tr['y'])
    null_scale = float(tweedie_deviance(torch.full_like(yt, yt.mean()), yt))
    loss_fn = TweedieJointLoss(max(null_scale, 1e-6))
    ensemble = []
    for seed in (42, 43, 44):
        started = time.perf_counter()
        LOG.info('year=%s seed=%s train=%s cal=%s eval=%s', year, seed, len(train), len(cal), len(ev))
        model, state, history = nn_train(tr, ca, seed, args, device, loss_fn=loss_fn)
        amount_cal, logits_cal = predict_pack(model, ca, args.batch_size, device, amount_mode='mean')
        amount_eval, logits_eval = predict_pack(model, ee, args.batch_size, device, amount_mode='mean')
        prob_cal, params = calibrate(logits_cal, ca['y'], logits_cal)
        prob_eval, _ = calibrate(logits_cal, ca['y'], logits_eval)
        torch.save(dict(model=state,amount_mode='mean',seed=seed,year=year,latency_h=5), target / f'seed{seed}.pt')
        np.savez_compressed(target / f'seed{seed}.npz', amount_cal=amount_cal, amount_eval=amount_eval,
                            prob_cal=prob_cal, prob_eval=prob_eval)
        ensemble.append(dict(amount_cal=amount_cal, amount_eval=amount_eval,
                             prob_cal=prob_cal, prob_eval=prob_eval))
        meta['history'].append(dict(year=year,seed=seed,epochs=history,calibration=params,
                                    null_deviance_train=null_scale,latency_h=5,
                                    seconds=time.perf_counter()-started))
        write_run(report, meta)
        del model
        if device.type=='cuda':
            torch.cuda.empty_cache()
    new = {key: np.mean([run[key] for run in ensemble], axis=0) for key in ensemble[0]}
    np.savez_compressed(target / 'ensemble.npz', **new)
    with np.load(PRIVATE / 'bilstm_tweedie' / str(year) / 'ensemble.npz') as saved:
        old = {key: saved[key].copy() for key in saved.files}
    old_tau = taus_for(ds,cal,ca['y'],old['prob_cal'])
    new_tau = taus_for(ds,cal,ca['y'],new['prob_cal'])
    reference = climatology(ds,sample_index(ds,cfg_for(ds,source),range(2015,year-1)),ev)[1]
    rows = []
    for name, result, tau in [('BiLSTM_RAW_TWEEDIE_LAG4',old,old_tau),
                              ('BiLSTM_RAW_TWEEDIE_LAG5',new,new_tau)]:
        score_rows,_ = score(ds,ev,ee['y'],result['amount_eval'],result['prob_eval'],reference,tau,name,year)
        rows.extend(score_rows)
    saved_scores = pd.read_csv(REPORT / 'bilstm_tweedie' / 'scores.csv')
    baseline = saved_scores[(saved_scores.year==year) & (saved_scores.source=='BiLSTM_RAW_TWEEDIE') &
                            (saved_scores.season=='may_oct') & (saved_scores.window=='0-3h')]
    original = next(row for row in rows if row['source']=='BiLSTM_RAW_TWEEDIE_LAG4' and
                    row['season']=='may_oct' and row['window']=='0-3h')
    if len(baseline)!=1 or any(not np.isclose(original[key],float(baseline.iloc[0][key]),atol=1e-4)
                               for key in ('RMSE','CSI_prob_10','BSS_1')):
        raise ValueError('Đối chứng lag4 không tái tạo bảng điểm gốc')
    warm = np.isin((ds.hours[ev[:,1]] + pd.Timedelta(hours=7)).month,range(5,11))
    obs = totals(ee['y'])[warm,0]
    amounts = pd.DataFrame(dict(date=ds.hours[ev[warm,1]] + pd.Timedelta(hours=7),
                                obs=obs,
                                lag4=totals(old['amount_eval'])[warm,0],
                                lag5=totals(new['amount_eval'])[warm,0]))
    ci_rmse = paired_block_bootstrap(amounts,'obs','lag5','lag4',metric_rmse,n_boot=args.bootstrap,seed=year)
    decisions = pd.DataFrame(dict(date=amounts.date,event=(obs>=10).astype(float),
                                  lag4=(old['prob_eval'][warm,0,1]>=old_tau[0,1]).astype(float),
                                  lag5=(new['prob_eval'][warm,0,1]>=new_tau[0,1]).astype(float)))
    ci_csi = paired_block_bootstrap(decisions,'event','lag5','lag4',metric_csi(1),n_boot=args.bootstrap,seed=year)
    (report / f'{year}_scores.json').write_text(json.dumps(json_safe(rows),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    result=dict(year=year,train_rows=len(train),cal_rows=len(cal),eval_rows=len(ev),
                train_index_same_as_lag4=True,checkpoint_new_latency_h=5,
                lag4_tau10=float(old_tau[0,1]),lag5_tau10=float(new_tau[0,1]),
                rmse_paired_ci=ci_rmse,csi_prob10_paired_ci=ci_csi,
                warm_scores=[row for row in rows if row['season']=='may_oct' and row['window']=='0-3h'],
                test_2025_scored=False)
    (report / f'{year}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    LOG.info('year=%s rmse4=%.4f rmse5=%.4f csi4=%.4f csi5=%.4f',year,
             result['warm_scores'][0]['RMSE'],result['warm_scores'][1]['RMSE'],
             result['warm_scores'][0]['CSI_prob_10'],result['warm_scores'][1]['CSI_prob_10'])
    return result


def main():
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--years',nargs='+',type=int,default=[2021,2022,2023])
    parser.add_argument('--epochs',type=int,default=15)
    parser.add_argument('--patience',type=int,default=4)
    parser.add_argument('--batch-size',type=int,default=256)
    parser.add_argument('--bootstrap',type=int,default=1000)
    args=parser.parse_args()
    if any(year not in (2021,2022,2023) for year in args.years) or len(set(args.years))!=len(args.years):
        parser.error('Chỉ ba năm validation2021–2023, không trùng')
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark=False
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    ds=DatasetV2(ROOT / 'data/processed/dataset_v2_danang')
    source,meta=metadata('bilstm_tweedie_lag5',args)
    meta['design']='Same 30 cells/index/3 seeds/architecture/Tweedie loss as lag4; only observation latency 5h, refit model and calibration on allowed years.'
    out=[]
    for year in args.years:
        out.append(run_year(ds,source,meta,args,year,device))
    report=REPORT/'bilstm_tweedie_lag5'
    meta['completed']=True
    write_run(report,meta)
    (report/'summary.json').write_text(json.dumps(dict(results=out,completed=True,
        exploratory_after_nrt_audit=True,test_2025_scored=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('COMPLETE years=' + ','.join(map(str,args.years)),flush=True)


if __name__=='__main__':
    main()
