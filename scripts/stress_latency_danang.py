"""Stress test checkpoint Bi-LSTM RAW Tweedie đã train lag4 với quan trắc lag5.

Không retrain, không đổi norm/Platt/tau; so trên cùng index validation2021–23.
Đây là thử độ nhạy nguồn, chưa là cấu hình lag5 được phép triển khai.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.domain_inference import ArchivePredictor
from src.verification import continuous_scores

PUBLIC = ROOT / 'reports/followup_danang/latency_stress'
PRIVATE = ROOT / 'data/operational/followup_danang/latency_stress'
SEASON = (5, 6, 7, 8, 9, 10)


def csi(obs, probability, tau, threshold=10):
    event = np.asarray(obs) >= threshold
    predicted = np.asarray(probability) >= tau
    hit = int(np.sum(event & predicted))
    miss = int(np.sum(event & ~predicted))
    false = int(np.sum(~event & predicted))
    return hit / (hit + miss + false) if hit + miss + false else float('nan')


def summary(obs, amount, p1, p10, tau):
    score = continuous_scores(obs, amount)
    score['BS_1'] = float(np.mean(np.square(p1 - (obs >= 1))))
    score['BS_10'] = float(np.mean(np.square(p10 - (obs >= 10))))
    score['CSI_prob_10'] = float(csi(obs, p10, tau))
    score['CSI_amount_10'] = float(csi(obs, amount, 10))
    event = obs >= 10
    predicted = p10 >= tau
    score['n_obs_events_10'] = int(event.sum())
    score['hits_prob_10'] = int((event & predicted).sum())
    score['false_alarms_prob_10'] = int((~event & predicted).sum())
    return score


def paired_ci(obs, a4, a5, p4, p5, days, tau, draws=1000, block_days=5, seed=42):
    unique = pd.DatetimeIndex(days.unique()).sort_values()
    groups = [np.flatnonzero(days == d) for d in unique]
    rng = np.random.default_rng(seed)
    rmse, csi_d = [], []
    for _ in range(draws):
        positions = []
        while len(positions) < len(unique):
            first = int(rng.integers(0, max(1, len(unique) - block_days + 1)))
            positions.extend(range(first, min(first + block_days, len(unique))))
        rows = np.concatenate([groups[j] for j in positions[:len(unique)]])
        y = obs[rows]
        rmse.append(float(np.sqrt(np.mean((a5[rows] - y)**2)) - np.sqrt(np.mean((a4[rows] - y)**2))))
        old, new = csi(y, p4[rows], tau), csi(y, p5[rows], tau)
        if np.isfinite(old) and np.isfinite(new):
            csi_d.append(new - old)
    quantiles = lambda x: [float(v) for v in np.quantile(x, [.025, .975])] if x else [None, None]
    return dict(rmse_lag5_minus_lag4_ci95=quantiles(rmse),
                csi_prob10_lag5_minus_lag4_ci95=quantiles(csi_d),
                bootstrap_valid_csi=len(csi_d))


def predict_batched(predictor, index, batch_size):
    amounts, probs = [], []
    for lo in range(0, len(index), batch_size):
        pred = predictor.predict(index[lo:lo + batch_size])
        amounts.append(pred['amount_mm'])
        probs.append(pred['probability'])
    return np.concatenate(amounts), np.concatenate(probs)


def run_year(year, batch_size=512):
    predictor = ArchivePredictor(year, 'RAW_TWEEDIE', device='cuda' if torch.cuda.is_available() else 'cpu')
    ds = predictor.ds
    local_issue = ds.hours[predictor.index[:, 1]] + pd.Timedelta(hours=7)
    index = predictor.index[np.isin(local_issue.month, SEASON)]
    if not len(index):
        raise ValueError('Không có mẫu mùa 5–10')
    year_index = ds.hours[index[:, 1]]
    if not (year_index.year == year).all() or not (ds.hours[index[:, 1] + 5].year == year).all():
        raise ValueError('Vượt fold validation')
    current = predictor.sampler.cfg.latency_h
    if current != 4:
        raise ValueError('Checkpoint nguồn không phải lag4')
    a4, p4 = predict_batched(predictor, index, batch_size)
    predictor.sampler.cfg.latency_h = 5
    try:
        a5, p5 = predict_batched(predictor, index, batch_size)
    finally:
        predictor.sampler.cfg.latency_h = current
    label = ds.feature_index['y_gsmap_gc_mm']
    y = np.empty((len(index), 6), dtype=np.float32)
    for cell in np.unique(index[:, 0]):
        where = np.flatnonzero(index[:, 0] == cell)
        t = index[where, 1]
        y[where] = ds.cube[cell, t[:, None] + np.arange(6), label]
    valid = np.isfinite(y).all(1) & np.isfinite(a4).all(1) & np.isfinite(a5).all(1) & np.isfinite(p4).all((1,2)) & np.isfinite(p5).all((1,2))
    if not valid.all():
        raise ValueError(f'Lag5 làm mất {int((~valid).sum())} mẫu; cần thiết kế common-index mới')
    obs = y[:, :3].sum(1)
    amount4, amount5 = a4[:, :3].sum(1), a5[:, :3].sum(1)
    prob1_4, prob1_5 = p4[:, 0, 0], p5[:, 0, 0]
    prob10_4, prob10_5 = p4[:, 0, 1], p5[:, 0, 1]
    table = pd.read_csv(ROOT / 'reports/followup_danang/bilstm_tweedie/scores.csv')
    selected = table[(table.year == year) & (table.source == 'BiLSTM_RAW_TWEEDIE') &
                     (table.season == 'may_oct') & (table.window == '0-3h')]
    if len(selected) != 1:
        raise ValueError('Không tìm thấy tau từ calibration đã lưu')
    tau = float(selected.iloc[0].tau_10)
    old = summary(obs, amount4, prob1_4, prob10_4, tau)
    new = summary(obs, amount5, prob1_5, prob10_5, tau)
    if not np.isclose(old['RMSE'], float(selected.iloc[0].RMSE), atol=1e-4) or not np.isclose(old['CSI_prob_10'], float(selected.iloc[0].CSI_prob_10), atol=1e-4):
        raise ValueError(f"Lag4 không khớp: n={len(index)}, RMSE={old['RMSE']:.6f} vs {float(selected.iloc[0].RMSE):.6f}, CSI={old['CSI_prob_10']:.6f} vs {float(selected.iloc[0].CSI_prob_10):.6f}")
    days = pd.DatetimeIndex(ds.hours[index[:, 1]] + pd.Timedelta(hours=7)).normalize()
    ci = paired_ci(obs, amount4, amount5, prob10_4, prob10_5, days, tau)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(PRIVATE / f'{year}.npz', index=index, obs3=obs, amount_lag4=amount4,
                        amount_lag5=amount5, prob10_lag4=prob10_4, prob10_lag5=prob10_5)
    return dict(year=year, n=len(index), days=int(days.nunique()), tau_10=tau,
                checkpoint_trained_latency_h=4, stressed_input_latency_h=5,
                frozen_checkpoint_norm_calibration=True, lag4=old, lag5=new, paired_ci=ci,
                test_2025_scored=False)


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', type=int, choices=(2021, 2022, 2023), action='append',
                        help='mặc định cả ba fold validation')
    parser.add_argument('--batch-size', type=int, default=512)
    args = parser.parse_args()
    if args.batch_size < 1 or args.batch_size > 1024:
        parser.error('batch-size phải 1–1024')
    torch.set_num_threads(4)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    outputs = []
    for year in args.year or [2021, 2022, 2023]:
        result = run_year(year, args.batch_size)
        outputs.append(result)
        (PUBLIC / f'{year}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('YEAR ' + str(year) + ' ' + json.dumps(dict(n=result['n'],
              rmse4=result['lag4']['RMSE'], rmse5=result['lag5']['RMSE'],
              csi4=result['lag4']['CSI_prob_10'], csi5=result['lag5']['CSI_prob_10'],
              ci=result['paired_ci'])), flush=True)
    summary_file = PUBLIC / 'summary.json'
    summary_file.write_text(json.dumps(dict(results=outputs, model='BiLSTM_RAW_TWEEDIE',
             interpretation='Frozen lag4 checkpoint stressed with lag5 observation; not a retrained lag5 model or T-OPS.',
             test_2025_scored=False), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
