"""Replay saved pilot checkpoints on the original device; record CPU drift."""
from pathlib import Path
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import lightgbm as lgb
import numpy as np
import pandas as pd
import torch

from src.short_range_dataset import load_development,tabular_inputs,scale_inputs,file_hash
from src.short_range_evaluation import apply_calibration,score_predictions
from src.tft_regional import RegionalTFT


def main():
    report=ROOT/'reports/short_range_pilot_2026_10_21'
    private=ROOT/'data/operational/short_range/pilot_2026_10_21'
    run=json.loads((report/'run.json').read_text(encoding='utf-8'))
    if run['status']!='complete': raise ValueError('Pilot must complete before audit')
    for name,expected in run['worktree_code_sha256'].items():
        if file_hash(ROOT/name)!=expected: raise ValueError('Run code hash changed: '+name)
    torch.set_num_threads(4)
    predictions=pd.read_parquet(private/'predictions.parquet')
    data=load_development(); results=[]; tick=time.perf_counter()
    device=run['device']
    for entry in run['models']:
        year,experiment,learner,seed=entry['year'],entry['experiment'],entry['learner'],entry['seed']
        selected=data.select(entry['feature_names']); ev=selected.dates.year==year
        n=int(ev.sum()); amount=np.zeros((n,3)); raw=np.zeros((n,3,3))
        cross_device={}
        if learner=='lgbm':
            x,names=tabular_inputs(selected)
            if names!=entry['tabular_features']: raise ValueError('Feature order changed')
            for record in entry['output_models']:
                lead=record['lead']-1
                if record['kind']=='amount':
                    amount[:,lead]=np.maximum(lgb.Booster(model_file=str(private/record['path'])).predict(x[ev]),0.)
                else:
                    ti=[16,50,100].index(int(record['threshold']))
                    raw[:,lead,ti]=(record['constant'] if 'constant' in record else
                        lgb.Booster(model_file=str(private/record['path'])).predict(x[ev]))
        else:
            bundle=torch.load(private/entry['checkpoint'],map_location='cpu',weights_only=True)
            if bundle['features']!=entry['feature_names']: raise ValueError('Checkpoint feature order differs')
            model=RegionalTFT(**bundle['config']).to(device).eval()
            model.load_state_dict(bundle['state'])
            scaler={k:v.numpy() for k,v in bundle['scaler'].items()}
            x=scale_inputs(selected.x[ev],scaler)
            with torch.inference_mode():
                for start in range(0,n,128):
                    a,p=model(torch.as_tensor(x[start:start+128],device=device),
                              torch.as_tensor(selected.future[ev][start:start+128],device=device))
                    amount[start:start+128]=a.cpu().numpy(); raw[start:start+128]=p.sigmoid().cpu().numpy()
            if device!='cpu':
                model.cpu()
                cpu_amount=np.zeros_like(amount); cpu_raw=np.zeros_like(raw)
                with torch.inference_mode():
                    for start in range(0,n,128):
                        a,p=model(torch.from_numpy(x[start:start+128]),
                                  torch.from_numpy(selected.future[ev][start:start+128]))
                        cpu_amount[start:start+128]=a.numpy(); cpu_raw[start:start+128]=p.sigmoid().numpy()
                cross_device=dict(cpu_max_amount_drift=float(np.abs(cpu_amount-amount).max()),
                                  cpu_max_raw_probability_drift=float(np.abs(cpu_raw-raw).max()),
                                  note='Cross-device floating-point drift, not the reference replay criterion')
        probability=apply_calibration(raw,entry['calibration'])
        current=predictions[(predictions.model==learner)&(predictions.experiment==experiment)
                            &(predictions.year==year)&(predictions.seed==seed)].copy()
        max_amount=max_probability=0.
        for lead in range(3):
            rows=current[current.lead_day==lead+1].sort_values('issue')
            if not pd.DatetimeIndex(rows.issue).equals(selected.dates[ev]): raise ValueError('Issue alignment differs')
            np.testing.assert_array_equal(rows.obs.to_numpy(),selected.y[ev,lead])
            np.testing.assert_allclose(rows.amount,amount[:,lead],rtol=3e-5,atol=2e-5)
            current.loc[rows.index,'amount']=amount[:,lead]
            max_amount=max(max_amount,float(np.max(np.abs(rows.amount.to_numpy()-amount[:,lead]))))
            for ti,threshold in enumerate([16,50,100]):
                np.testing.assert_allclose(rows[f'p{threshold}'],probability[:,lead,ti],rtol=3e-5,atol=2e-6)
                current.loc[rows.index,f'p{threshold}']=probability[:,lead,ti]
                max_probability=max(max_probability,float(np.max(np.abs(rows[f'p{threshold}']-probability[:,lead,ti]))))
        reference=score_predictions(predictions[(predictions.model==learner)&(predictions.experiment==experiment)
                                               &(predictions.year==year)&(predictions.seed==seed)])
        replay=score_predictions(current)
        for column in ['RMSE','MAE','bias','BS','BSS','CSI']:
            np.testing.assert_allclose(reference[column],replay[column],rtol=3e-5,atol=2e-5,equal_nan=True)
        results.append(dict(learner=learner,year=year,experiment=experiment,seed=seed,
                            issues=n,max_amount_difference=max_amount,
                            max_probability_difference=max_probability,all_metrics_reproduced=True,
                            **cross_device))
        print('REPLAY_OK',learner,year,experiment,'issues',n,flush=True)
    output=dict(status='passed',full_runs_replayed=len(results),results=results,
                 test2025_read=False,reference_replay_device=device,new_training=False,
                 elapsed_seconds=time.perf_counter()-tick)
    (report/'checkpoint_audit.json').write_text(json.dumps(output,indent=2),encoding='utf-8',newline='\n')
    print('ALL_REPLAY_PASSED',len(results),flush=True)


if __name__=='__main__': main()
