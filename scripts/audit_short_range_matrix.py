"""Replay all saved factorial checkpoints and calibration/evaluation predictions."""
from pathlib import Path
import argparse
import json
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import lightgbm as lgb
import numpy as np
import pandas as pd
import torch
from pilot_short_range import network_predict
from src.short_range_dataset import load_development,tabular_inputs,scale_inputs,file_hash,SOURCE
from src.short_range_evaluation import apply_calibration,score_predictions
from src.tft_regional import RegionalTFT

REPORT=ROOT/'reports/short_range_ablation_2026_10_21'
PRIVATE=ROOT/'data/operational/short_range/ablation_2026_10_21'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--partial',action='store_true',help='Audit a completed-run snapshot while fitting continues')
    args=parser.parse_args()
    tick=time.perf_counter();torch.set_num_threads(4)
    run=json.loads((REPORT/'run.json').read_text(encoding='utf-8'))
    if not args.partial and (run['status']!='complete' or len(run['models'])!=96):raise ValueError('Matrix incomplete')
    if file_hash(SOURCE)!=run['source_hash']:raise ValueError('Source checksum differs')
    for name,expected in run['code_hashes'].items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Run code checksum differs: '+name)
    data=load_development();device=run['device'];results=[]
    old_path=ROOT/'data/operational/short_range/pilot_2026_10_21/predictions.parquet'
    old=pd.read_parquet(old_path) if old_path.exists() else None
    for entry in run['models']:
        for name,expected in entry['artifact_hashes'].items():
            if file_hash(PRIVATE/name)!=expected:raise ValueError('Artifact checksum differs: '+name)
        selected=data.select(entry['feature_names'])
        cal,ev=selected.dates.year==entry['year']-1,selected.dates.year==entry['year']
        outputs={};model=None
        if entry['learner']=='tft':
            checkpoint=torch.load(PRIVATE/entry['checkpoint'],map_location='cpu',weights_only=True)
            if checkpoint['features']!=entry['feature_names']:raise ValueError('Checkpoint feature order differs')
            model=RegionalTFT(**checkpoint['config']).to(device).eval();model.load_state_dict(checkpoint['state'])
            scaler={k:v.numpy() for k,v in checkpoint['scaler'].items()}
            x=scale_inputs(selected.x,scaler)
            for name,mask in [('cal',cal),('eval',ev)]:
                a,p=network_predict(model,x[mask],selected.future[mask],device)
                outputs[name]=(a,apply_calibration(p,entry['calibration']))
        else:
            x,names=tabular_inputs(selected)
            if names!=entry['tabular_features']:raise ValueError('Tabular feature order differs')
            for name,mask in [('cal',cal),('eval',ev)]:
                a=np.zeros((mask.sum(),3));p=np.zeros((mask.sum(),3,3))
                for head in entry['output_models']:
                    li=head['lead']-1
                    values=(np.full(mask.sum(),head['constant']) if 'constant' in head else
                        lgb.Booster(model_file=str(PRIVATE/head['path'])).predict(x[mask],num_threads=4))
                    if head['kind']=='amount':a[:,li]=np.maximum(values,0.)
                    else:p[:,li,[16,50,100].index(int(head['threshold']))]=values
                outputs[name]=(a,apply_calibration(p,entry['calibration']))
        worst_a=worst_p=0.
        for split,mask in [('cal',cal),('eval',ev)]:
            saved=pd.read_parquet(PRIVATE/entry['cal_predictions' if split=='cal' else 'eval_predictions'])
            replay=saved.copy();a,p=outputs[split]
            for lead in range(3):
                rows=saved[saved.lead_day==lead+1].sort_values('issue')
                if not pd.DatetimeIndex(rows.issue).equals(selected.dates[mask]):raise ValueError('Issue alignment differs')
                np.testing.assert_array_equal(rows.obs.to_numpy(),selected.y[mask,lead])
                np.testing.assert_allclose(rows.amount,a[:,lead],rtol=3e-5,atol=2e-5)
                replay.loc[rows.index,'amount']=a[:,lead]
                worst_a=max(worst_a,float(np.max(np.abs(rows.amount.to_numpy()-a[:,lead]))))
                for ti,threshold in enumerate([16,50,100]):
                    np.testing.assert_allclose(rows[f'p{threshold}'],p[:,lead,ti],rtol=3e-5,atol=2e-6)
                    replay.loc[rows.index,f'p{threshold}']=p[:,lead,ti]
                    worst_p=max(worst_p,float(np.max(np.abs(rows[f'p{threshold}'].to_numpy()-p[:,lead,ti]))))
            before,after=score_predictions(saved),score_predictions(replay)
            for column in ['RMSE','MAE','bias','BS','BSS','CSI']:
                np.testing.assert_allclose(before[column],after[column],rtol=3e-5,atol=2e-5,equal_nan=True)
        pilot_match=None
        if old is not None and entry['seed']==42 and entry['experiment'] in ['E0','E7']:
            prior=old[(old.model==entry['learner'])&(old.year==entry['year'])&(old.experiment==entry['experiment'])]
            current=pd.read_parquet(PRIVATE/entry['eval_predictions'])
            prior=prior.sort_values(['issue','lead_day']);current=current.sort_values(['issue','lead_day'])
            for col in ['amount','p16','p50','p100']:
                np.testing.assert_allclose(prior[col],current[col],rtol=3e-5,atol=2e-5)
            pilot_match=True
        results.append(dict(learner=entry['learner'],year=entry['year'],experiment=entry['experiment'],
            seed=entry['seed'],calibration_and_evaluation_replayed=True,all_metrics_reproduced=True,
            max_amount_difference=worst_a,max_probability_difference=worst_p,pilot_seed42_reproduced=pilot_match))
        del model
        print('REPLAY_OK',entry['learner'],entry['year'],entry['experiment'],entry['seed'],flush=True)
    output=dict(status='passed',partial_snapshot=args.partial,full_runs_replayed=len(results),splits_per_run=2,reference_device=device,
        seed42_pilot_matches=sum(r['pilot_seed42_reproduced'] is True for r in results),
        pilot_comparison_available=old is not None,results=results,
        seconds=time.perf_counter()-tick,test2025_read=False,new_training=False,
        audit_code_sha256=file_hash(Path(__file__)))
    (REPORT/('checkpoint_audit_partial.json' if args.partial else 'checkpoint_audit.json')).write_text(json.dumps(output,indent=2),encoding='utf-8',newline='\n')
    print('ALL_REPLAY_PASSED',len(results),'seconds',round(output['seconds'],2),flush=True)


if __name__=='__main__':main()
