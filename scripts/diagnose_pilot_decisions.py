"""Chẩn đoán khám phá trên 30 ô/3 seed: chọn ngưỡng ở mùa hè–thu 2022, chấm 2023.
Không train mới hoặc mở test 2025. CSI từ đầu xác suất không thay thế CSI lượng mưa gốc.
Chạy ở repo: python scripts/diagnose_pilot_decisions.py
"""
import sys,json
from pathlib import Path
import numpy as np,pandas as pd,torch
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from src.bilstm_v2 import BiLSTMV2
from src.dataloader_v2 import DatasetV2,WindowConfig,Normalizer,WindowSampler
from src.verification import contingency_scores,paired_block_bootstrap
from scripts.pilot_bilstm_v2 import predict,labels
private=root/'data/processed/pilot_bilstm_v2_3seeds'
r=json.loads((root/'reports/pilot_bilstm_v2_3seeds/run.json').read_text(encoding='utf-8'))
assert not r['test_2025_scored']
ds=DatasetV2(root/'data/processed/dataset_v2_danang')
cal=np.load(private/'index_calibration_2022.npy');ev=np.load(private/'index_evaluation_2023.npy')
assert set(ds.hours[cal[:,1]].year)=={2022} and set(ds.hours[ev[:,1]].year)=={2023}
mc=(ds.hours[cal[:,1]]+pd.Timedelta(hours=7)).month.to_numpy();me=(ds.hours[ev[:,1]]+pd.Timedelta(hours=7)).month.to_numpy()
cm=(mc>=5)&(mc<=10);em=(me>=5)&(me<=10)
yc=labels(ds,cal)[:,:3].sum(1);ye=labels(ds,ev)[:,:3].sum(1)
device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');torch.set_num_threads(4);torch.backends.cudnn.benchmark=False
results=[];decisions={}
for name in ['S1','S4']:
    cp=[];ep=[];amount=[]
    for seed in [42,43,44]:
        ck=torch.load(private/f'{name}_seed{seed}.pt',map_location=device,weights_only=True)
        cfg=WindowConfig(**ck['config']);norm=Normalizer.load(private/f'normalizer_{name}.json');sampler=WindowSampler(ds,cfg,norm)
        model=BiLSTMV2(len(sampler.x_past_names),len(sampler.future_names)).to(device);model.load_state_dict(ck['model'])
        _,logits=predict(model,sampler,cal,256,device)
        params=next(h['calibration'] for h in r['history'] if h['run']==f'{name}_seed{seed}')
        pp=np.empty_like(logits)
        for j,p in enumerate(params):
            if 'constant' in p:pp[:,j]=p['constant']
            else:pp[:,j]=1/(1+np.exp(-np.clip(p['coef']*logits[:,j]+p['intercept'],-30,30)))
        cp.append(np.minimum.accumulate(pp.reshape(-1,3,3),axis=2)[:,0,1])
        with np.load(private/f'{name}_seed{seed}.npz') as saved:
            ep.append(saved['probability'][:,0,1]);amount.append(saved['amount'][:,:3].sum(1))
        del model;torch.cuda.empty_cache()
    cprob=np.mean(cp,axis=0);eprob=np.mean(ep,axis=0)
    grid=np.arange(.01,.96,.01)
    def csi_flags(o,f):return float(contingency_scores(o>=10,f,.5)['CSI'])
    tau=max(grid,key=lambda t:csi_flags(yc[cm],(cprob[cm]>=t).astype(float)))
    flags=(eprob[em]>=tau).astype(float);decisions[name]=flags
    result={'config':name,'threshold_selected_on_summer_2022':float(tau),'n_2023':int(em.sum()),'n_events_2023':int((ye[em]>=10).sum()),'CSI_from_amount':float(contingency_scores(ye[em],np.mean(amount,axis=0)[em],10)['CSI']),'CSI_from_probability':csi_flags(ye[em],flags)}
    results.append(result);print(json.dumps(result),flush=True)
frame=pd.DataFrame({'date':ds.hours[ev[em,1]],'obs':ye[em],**decisions})
csi_flags.__name__='CSI_event_head>=10mm/3h'
boot=paired_block_bootstrap(frame,'obs','S1','S4',csi_flags,n_boot=1000)
report={'scope':'Exploratory validation diagnostic; original amount CSI unchanged; no test 2025','results':results,'paired_bootstrap':boot}
p=root/'reports/research_rainfall/decision_head_diagnostic.json';p.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(boot),flush=True)
# Ghi POD/FAR để không diễn giải CSI như phần trăm dự báo đúng.
for result in report['results']:
    score=contingency_scores(ye[em]>=10,decisions[result['config']],.5)
    result['classification_counts']={k:score[k] for k in ['hits','misses','false_alarms','POD','FAR','FBI']}
amounts=[]
for seed in [42,43,44]:
    with np.load(private/f'S1_seed{seed}.npz') as saved:
        amounts.append(saved['amount'][:,:3].sum(1))
af=(np.mean(amounts,axis=0)[em]>=10).astype(float)
f=pd.DataFrame({'date':ds.hours[ev[em,1]],'obs':ye[em],'probability_rule':decisions['S1'],'amount_rule':af})
def decision_metric(o,v):return float(contingency_scores(o>=10,v,.5)['CSI'])
decision_metric.__name__='CSI>=10mm/3h decision rule'
report['S1_probability_vs_amount_bootstrap']=paired_block_bootstrap(f,'obs','probability_rule','amount_rule',decision_metric,n_boot=1000)
p.write_text(json.dumps(report,indent=2),encoding='utf-8')
