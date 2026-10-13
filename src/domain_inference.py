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

def validation_index(ds,year,scope):
    if year not in (2021,2022,2023):raise ValueError('Chỉ validation2021–2023; không dùng test2025')
    if scope not in ('trained','unseen'):raise ValueError('Scope phải trained hoặc unseen')
    path=PRIVATE/str(year)/'index_eval.npy' if scope=='trained' else ROOT/'data/operational/followup_danang/spatial'/str(year)/'index_eval.npy'
    index=np.load(path)
    meta=json.loads((REPORT/'run.json').read_text(encoding='utf-8'))
    trained=set(r['site'] for r in meta['cells'])
    sites=set(ds.cells.iloc[np.unique(index[:,0])].site)
    if (scope=='trained' and not sites<=trained) or (scope=='unseen' and sites&trained):
        raise ValueError('Index không khớp scope nguồn')
    if not (ds.hours[index[:,1]].year==year).all() or not (ds.hours[index[:,1]+5].year==year).all():
        raise ValueError('Index vượt năm validation')
    return index

class ArchivePredictor:
    def __init__(self,year,config,device='cpu',scope='trained'):
        if year not in (2021,2022,2023):raise ValueError('Chỉ validation2021–2023; không dùng test2025')
        if config not in ('BASE','RAW','DOMAIN','RAW_TWEEDIE'):raise ValueError('Cấu hình không hợp lệ')
        if scope=='unseen' and config not in ('RAW','DOMAIN'):
            raise ValueError('Cấu hình này chưa đánh giá trên ô chưa train')
        self.year,self.config,self.scope,self.device=year,config,scope,torch.device(device)
        self.ds=DatasetV2(ROOT/'data/processed/dataset_v2_danang')
        source=json.loads((REPORT/'run.json').read_text(encoding='utf-8'))
        self.models,self.calibration=[],[]
        folder=PRIVATE/str(year)
        self.index=validation_index(self.ds,year,scope)
        base_config='RAW' if config=='RAW_TWEEDIE' else config
        norm=Normalizer.load(folder/f'{base_config}_normalizer.json')
        derived=DerivedNormalizer(**json.loads((folder/'derived_normalizer.json').read_text(encoding='utf-8'))) if config=='DOMAIN' else None
        extra=ROOT/'data/operational/followup_danang/bilstm_tweedie'/str(year)
        meta=json.loads((ROOT/'reports/followup_danang/bilstm_tweedie/run.json').read_text(encoding='utf-8')) if config=='RAW_TWEEDIE' else source
        self.amount_mode='mean' if config=='RAW_TWEEDIE' else 'log'
        for seed in source['args']['seeds']:
            name=f'BiLSTM_{base_config}_seed{seed}'
            original=torch.load(folder/f'{name}.pt',map_location=self.device,weights_only=True)
            saved=torch.load(extra/f'seed{seed}.pt',map_location=self.device,weights_only=True) if config=='RAW_TWEEDIE' else original
            cfg=WindowConfig(**original['config'])
            sampler=DomainSampler(WindowSampler(self.ds,cfg,norm),'domain' if config=='DOMAIN' else 'padding',derived)
            model=BiLSTMV2(len(sampler.x_past_names),len(sampler.future_names)).to(self.device)
            model.load_state_dict(saved['model']);model.eval()
            calibration=next(h['calibration'] for h in meta['history'] if h['year']==year and
                (h.get('seed')==seed if config=='RAW_TWEEDIE' else h.get('run')==name))
            self.models.append(model);self.calibration.append(calibration)
        self.sampler=sampler
        self._valid=set(map(tuple,self.index.tolist()))
    @torch.no_grad()
    def predict(self,index):
        index=np.asarray(index,np.int32).reshape(-1,2)
        if not all(tuple(row) in self._valid for row in index):raise ValueError('Ngoài cửa sổ validation hợp lệ')
        b=self.sampler.batch(index)
        xp,xf,st=[torch.from_numpy(b[k]).to(self.device) for k in ('x_past','x_future','static')]
        amounts,probs=[],[]
        for model,params in zip(self.models,self.calibration):
            a,l=model(xp,xf,st)
            amounts.append((a if self.amount_mode=='mean' else torch.expm1(a)).cpu().numpy())
            probs.append(calibrated_probability(l.cpu().numpy(),params))
        return dict(amount_mm=np.mean(amounts,axis=0),probability=np.mean(probs,axis=0),
                    windows=['0-3h','3-6h','0-6h'],thresholds_mm=[1,10,25],
                    mode='archive_validation',scope=self.scope,operational_ready=False)

class TreeArchivePredictor:
    def __init__(self,year,config):
        import lightgbm as lgb
        if year not in (2021,2022,2023):raise ValueError('Chỉ validation2021–2023; không dùng test2025')
        if config not in ('TREE_L1','TREE_TWEEDIE'):raise ValueError('Cấu hình cây không hợp lệ')
        self.year,self.config,self.scope=year,config,'trained'
        self.ds=DatasetV2(ROOT/'data/processed/dataset_v2_danang')
        self.index=validation_index(self.ds,year,'trained')
        source=json.loads((REPORT/'run.json').read_text(encoding='utf-8'))
        original=torch.load(PRIVATE/str(year)/'BiLSTM_RAW_seed42.pt',map_location='cpu',weights_only=True)
        cfg=WindowConfig(**original['config'])
        self.sampler=DomainSampler(WindowSampler(self.ds,cfg,Normalizer.load(PRIVATE/str(year)/'RAW_normalizer.json')))
        self.calibration=next(h['calibration'] for h in source['history'] if h['year']==year and h['run']=='LightGBM_RAW')
        self.amount_models=[]
        for h in range(6):
            path=ROOT/'data/operational/followup_danang/amount'/str(year)/f'amount{h}.txt' if config=='TREE_TWEEDIE' else PRIVATE/str(year)/f'LightGBM_RAW_amount{h}.txt'
            self.amount_models.append(lgb.Booster(model_file=str(path)))
        self.event_models=[]
        for j in range(9):
            path=PRIVATE/str(year)/f'LightGBM_RAW_event{j}.txt'
            self.event_models.append(lgb.Booster(model_file=str(path)) if path.exists() else None)
        self._valid=set(map(tuple,self.index.tolist()))
    def predict(self,index):
        index=np.asarray(index,np.int32).reshape(-1,2)
        if not all(tuple(row) in self._valid for row in index):raise ValueError('Ngoài cửa sổ validation cây')
        data=self.sampler.batch(index)
        x=np.concatenate([data['x_past'].reshape(len(index),-1),data['x_future'].reshape(len(index),-1),data['static']],axis=1)
        pred=np.stack([m.predict(x,num_threads=2) for m in self.amount_models],axis=1)
        amount=pred if self.config=='TREE_TWEEDIE' else np.expm1(np.maximum(pred,0))
        logits=np.empty((len(index),9))
        for j,m in enumerate(self.event_models):
            if m is not None:logits[:,j]=m.predict(x,raw_score=True,num_threads=2)
            elif 'constant' in self.calibration[j]:logits[:,j]=0.
            else:raise ValueError('Thiếu event model; không tự điền')
        return dict(amount_mm=amount,probability=calibrated_probability(logits,self.calibration),
                    windows=['0-3h','3-6h','0-6h'],thresholds_mm=[1,10,25],
                    mode='archive_validation',scope='trained',operational_ready=False)

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
