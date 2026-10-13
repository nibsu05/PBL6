"""Suy luận checkpoint domain đã train; chỉ chế độ lưu trữ validation2021–2023."""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import torch
from src.bilstm_v2 import BiLSTMV2
from src.dataloader_v2 import DatasetV2,Normalizer,WindowConfig,WindowSampler
from src.domain_features import DomainSampler,DerivedNormalizer

ROOT=Path(__file__).resolve().parent.parent
PRIVATE=ROOT/'data/operational/domain_screen_danang'
REPORT=ROOT/'reports/domain_screen_danang'

def calibrated_probability(logits,params):
    x=np.empty_like(logits)
    for j,p in enumerate(params):
        if 'constant' in p:x[:,j]=p['constant']
        else:
            z=np.clip(p['coef']*logits[:,j]+p['intercept'],-60,60)
            x[:,j]=1/(1+np.exp(-z))
    return np.minimum.accumulate(x.reshape(-1,3,3),axis=2)

class ArchivePredictor:
    def __init__(self,year,config,device='cpu'):
        if year not in (2021,2022,2023):raise ValueError('Chỉ validation2021–2023; không dùng test2025')
        if config not in ('BASE','RAW','DOMAIN'):raise ValueError('Cấu hình không hợp lệ')
        self.year,self.config,self.device=year,config,torch.device(device)
        self.ds=DatasetV2(ROOT/'data/processed/dataset_v2_danang')
        meta=json.loads((REPORT/'run.json').read_text(encoding='utf-8'))
        self.models,self.calibration=[],[]
        fold=PRIVATE/str(year)
        self.index=np.load(fold/'index_eval.npy')
        norm=Normalizer.load(fold/f'{config}_normalizer.json')
        derived=DerivedNormalizer(**json.loads((fold/'derived_normalizer.json').read_text(encoding='utf-8'))) if config=='DOMAIN' else None
        for seed in meta['args']['seeds']:
            name=f'BiLSTM_{config}_seed{seed}'
            saved=torch.load(fold/f'{name}.pt',map_location=self.device,weights_only=True)
            cfg=WindowConfig(**saved['config'])
            sampler=DomainSampler(WindowSampler(self.ds,cfg,norm),'domain' if config=='DOMAIN' else 'padding',derived)
            model=BiLSTMV2(len(sampler.x_past_names),len(sampler.future_names)).to(self.device)
            model.load_state_dict(saved['model']);model.eval()
            calibration=next(h['calibration'] for h in meta['history'] if h['year']==year and h['run']==name)
            self.models.append(model);self.calibration.append(calibration)
        self.sampler=sampler
        self._valid=set(map(tuple,self.index.tolist()))
    @torch.no_grad()
    def predict(self,index):
        index=np.asarray(index,np.int32).reshape(-1,2)
        if not all(tuple(row) in self._valid for row in index):raise ValueError('Ngoài cửa sổ validation hợp lệ củafold')
        b=self.sampler.batch(index)
        xp,xf,st=[torch.from_numpy(b[k]).to(self.device) for k in ('x_past','x_future','static')]
        amounts,probs=[],[]
        for model,params in zip(self.models,self.calibration):
            a,l=model(xp,xf,st)
            amounts.append(torch.expm1(a).cpu().numpy())
            probs.append(calibrated_probability(l.cpu().numpy(),params))
        return dict(amount_mm=np.mean(amounts,axis=0),probability=np.mean(probs,axis=0),
                    windows=['0-3h','3-6h','0-6h'],thresholds_mm=[1,10,25],
                    mode='archive_validation',operational_ready=False)

def parity_check(year=2021,n=20):
    torch.set_num_threads(4)
    meta=json.loads((REPORT/'run.json').read_text(encoding='utf-8'))
    rows=[]
    for config in ('BASE','RAW','DOMAIN'):
        predictor=ArchivePredictor(year,config)
        positions=np.random.default_rng(2026).choice(len(predictor.index),n,replace=False)
        actual=predictor.predict(predictor.index[positions])
        amounts,probs=[],[]
        for seed in meta['args']['seeds']:
            with np.load(PRIVATE/str(year)/f'BiLSTM_{config}_seed{seed}.npz') as old:
                amounts.append(old['amount_eval'][positions]);probs.append(old['prob_eval'][positions])
        amount_error=float(abs(actual['amount_mm']-np.mean(amounts,axis=0)).max())
        prob_error=float(abs(actual['probability']-np.mean(probs,axis=0)).max())
        # CPU vs CUDA phép tích số học có sai khác nhỏ; ngưỡng đặt trước khi đối chiếu.
        np.testing.assert_allclose(actual['amount_mm'],np.mean(amounts,axis=0),rtol=1e-4,atol=1e-4)
        np.testing.assert_allclose(actual['probability'],np.mean(probs,axis=0),rtol=1e-4,atol=1e-5)
        rows.append(dict(year=year,config=config,n=n,max_abs_amount_mm=amount_error,max_abs_probability=prob_error))
    return dict(passed=True,device='cpu',rows=rows,source='Reload trained checkpoints, normalization and stored Platt parameters; compare saved CUDA ensemble.')
