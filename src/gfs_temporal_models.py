"""Fixed-budget temporal ablations and a same-parameter redundant-input control."""
import copy
import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import TensorDataset,DataLoader
from src.gfs_temporal import CATALOG,SEEDS
from src.gfs_daily import HISTORY,RAW_MET,TERRAIN,nested_probabilities
from src.gfs_daily_gru import DailyGRU,normalizers,tensors,predict,loss_function

def arrays(frame,config,projection=None):
    n=len(frame)//3
    if len(frame)%3 or not np.array_equal(frame.horizon.to_numpy().reshape(n,3),np.tile([1,2,3],(n,1))):raise ValueError('Complete sorted horizon packs required')
    for key in ('station_id','station_code','issue_utc','gauge_namespace'):
        if key in frame:
            values=frame[key].to_numpy().reshape(n,3)
            if not (values==values[:,0,None]).all():raise ValueError('Mixed station/time/source within horizon packs')
    names=[c for c in CATALOG['T0' if config=='LINEAR23' else config] if c not in HISTORY+['station_code']]
    context=frame[names].to_numpy('float32').reshape(n,3,-1)
    if config=='LINEAR23':
        if projection is None:raise ValueError('Frozen train-only linear projection required')
        indices=[names.index(c) for c in RAW_MET+TERRAIN]
        extra=((context[:,:,indices]-projection['mean'])/projection['std'])@projection['matrix']
        context=np.concatenate([context,extra],-1).astype('float32')
        names=names+[f'linear_redundant_{k}' for k in range(23)]
    y=frame.y_mm.to_numpy('float32').reshape(n,3)
    return dict(context=context,names=names,y=y,events=np.stack([y>=1,y>=50],-1).astype('float32'),
        history=np.log1p(frame[HISTORY].to_numpy('float32').reshape(n,3,7)[:,0,::-1,None].copy()),
        station=frame.station_code.to_numpy('int64').reshape(n,3)[:,0])

def make_projection(frame,train):
    x=frame[RAW_MET+TERRAIN].to_numpy('float32').reshape(-1,3,10)[train]
    matrix=np.random.default_rng(20261117).normal(size=(10,23))
    matrix/=np.maximum(np.linalg.norm(matrix,axis=0),1e-9)
    return dict(mean=x.mean((0,1)),std=np.maximum(x.std((0,1)),1e-5),matrix=matrix.astype('float32'),seed=20261117)

def train_gru(frame,config,seed,callback=None):
    train=frame.split.to_numpy().reshape(-1,3)[:,0]=='train'
    projection=make_projection(frame,train) if config=='LINEAR23' else None
    raw=arrays(frame,config,projection);norm=normalizers(raw,train);inputs=tensors(raw,norm)
    torch.set_num_threads(4);torch.manual_seed(seed);np.random.seed(seed)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    if device.type=='cuda':torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.use_deterministic_algorithms(True,warn_only=True)
    model=DailyGRU(len(raw['names']),16,24).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.001)
    loader=DataLoader(TensorDataset(*[t[train] for t in inputs]),batch_size=256,shuffle=True,
        generator=torch.Generator().manual_seed(seed),num_workers=0)
    curves=[]
    for epoch in range(1,18):
        model.train();total=0;seen=0
        for batch in loader:
            h,c,s,target,event=[t.to(device) for t in batch]
            optimizer.zero_grad(set_to_none=True);point,logits=model(h,c,s)
            loss=loss_function(point,logits,target,event)
            if not torch.isfinite(loss):raise ValueError('Nonfinite training loss')
            loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step()
            total+=float(loss.detach().cpu())*len(h);seen+=len(h)
        row=dict(epoch=epoch,train_loss=total/seen);curves.append(row)
        if callback:callback(row)
    artifact=dict(state={k:v.detach().cpu() for k,v in model.state_dict().items()},normalizers=norm,
        projection=projection,config=config,seed=seed,features=raw['names'],hidden=16,head=24,epochs=17,
        parameter_count=sum(p.numel() for p in model.parameters()),device=str(device),curves=curves)
    out=predict(model,inputs,norm['target_scale'],device)
    del model
    if device.type=='cuda':torch.cuda.empty_cache()
    return artifact,out

def replay_gru(frame,artifact,device_name=None):
    raw=arrays(frame,artifact['config'],artifact['projection'])
    if raw['names']!=artifact['features']:raise ValueError('Neural feature contract mismatch')
    inputs=tensors(raw,artifact['normalizers']);device=torch.device(device_name or ('cuda' if torch.cuda.is_available() else 'cpu'))
    model=DailyGRU(len(raw['names']),artifact['hidden'],artifact['head']).to(device);model.load_state_dict(artifact['state'])
    result=predict(model,inputs,artifact['normalizers']['target_scale'],device)
    del model
    if device.type=='cuda':torch.cuda.empty_cache()
    return result

def calibrated(wet,conditional,pair):
    return nested_probabilities(pair[0].predict(wet),pair[1].predict(conditional))
