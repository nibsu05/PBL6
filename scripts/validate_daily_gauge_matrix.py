"""Independently replay all daily checkpoints, calibration and ensemble scores."""
from pathlib import Path
import argparse
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import lightgbm as lgb
import numpy as np
import pandas as pd
import torch
from src.daily_gauge_dataset import load_development, feature_groups, tabular_inputs, PRIVATE, TIME
from src.daily_gauge_models import DailyTFT,DailyInformer
from src.short_range_dataset import train_scaler,scale_inputs,fit_climatology,predict_climatology
from src.short_range_evaluation import fit_calibration,apply_calibration,prediction_frame
from src.short_range_ablation import seed_mean,ensemble_thresholds
from scripts.pilot_short_range import network_predict,dump
from scripts.run_daily_gauge_matrix import sha,score,REPORT,MODELS,YEARS,SEEDS


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--partial',action='store_true');args=parser.parse_args()
    tick=time.perf_counter();torch.set_num_threads(4)
    protocol=json.loads((REPORT/'protocol_frozen.json').read_text(encoding='utf8'))
    manifest=json.loads((REPORT/'run.json').read_text(encoding='utf8'))
    assert manifest['protocol_sha256']==sha(REPORT/'protocol_frozen.json')
    assert not protocol['test2025_read'] and protocol['expected_models']==168
    for name,digest in protocol['code_hashes'].items():assert sha(ROOT/name)==digest,name
    assert sha(PRIVATE/'cpc_daily_region.parquet')==protocol['labels_sha256']
    inherited=json.loads((ROOT/'reports/informer_regional_matrix_2026_10_28/code_provenance.json').read_text(encoding='utf8'))
    for name,meta in inherited['files'].items():assert sha(ROOT/name)==meta['normalized_lf_sha256'],name
    data,daily=load_development()
    cached=pd.read_parquet(PRIVATE/'daily_predictors_and_labels.parquet')
    pd.testing.assert_frame_equal(cached,daily,check_freq=False)
    assert data.x.shape[1:]==(7,42) and data.future.shape[1:]==(3,2)
    assert (data.dates.year==(data.dates+pd.Timedelta(days=3)).year).all()
    assert data.dates.max().year<=2023 and len(data.dates)==manifest['total_samples']
    assert [len(v) for v in feature_groups().values()]==[9,21,29,10,41,22,30,42]
    # Raw-hour reconstruction checks: no 23-hour averages or future timestamps.
    import pyarrow.parquet as pq
    from src.daily_gauge_dataset import SOURCE
    selected=[0,len(data.dates)//2,len(data.dates)-1];hour_checks=0
    physical=[name for name in data.features if name not in TIME]
    for i in selected:
        issue=data.dates[i]
        h=pq.read_table(SOURCE,columns=['datetime',*physical],filters=[
            ('datetime','>=',issue-pd.Timedelta(days=7)),('datetime','<',issue)]).to_pandas()
        assert len(h)==168
        expected=h[physical].to_numpy().reshape(7,24,len(physical)).mean(1)
        indices=[data.features.index(n) for n in physical]
        np.testing.assert_allclose(data.x[i][:,indices],expected,rtol=2e-6,atol=2e-5)
        hour_checks+=168
    models=manifest['models']
    if not args.partial:assert manifest['status']=='complete' and len(models)==168
    cal_frames={};ev_frames={};replayed=0;trees=0
    for meta in models:
        year,exp,kind,seed=[meta[k] for k in ['year','experiment','model','seed']]
        sample=data.select(feature_groups()[exp]);assert sample.features==meta['features']
        train=data.dates.year<=year-2;cal=data.dates.year==year-1;ev=data.dates.year==year
        assert [int(m.sum()) for m in [train,cal,ev]]==[meta[k] for k in ['n_train','n_cal','n_eval']]
        if kind=='lgbm':
            x,names=tabular_inputs(sample);assert names==meta['tabular_names']
            ac=np.zeros((cal.sum(),3));ae=np.zeros((ev.sum(),3));pc=np.zeros((cal.sum(),3,3));pe=np.zeros((ev.sum(),3,3))
            for item in meta['output_models']:
                lead=item['lead']-1
                if 'constant' in item:
                    ti=[16,50,100].index(int(item['threshold']));pc[:,lead,ti]=pe[:,lead,ti]=item['constant'];continue
                path=PRIVATE/'models'/item['path'];assert sha(path)==item['sha256']
                booster=lgb.Booster(model_file=str(path));a=booster.predict(x[cal]);b=booster.predict(x[ev]);trees+=1
                if item['kind']=='amount':ac[:,lead]=np.maximum(a,0);ae[:,lead]=np.maximum(b,0)
                else:
                    ti=[16,50,100].index(int(item['threshold']));pc[:,lead,ti]=a;pe[:,lead,ti]=b
        else:
            path=PRIVATE/'models'/meta['checkpoint'];assert sha(path)==meta['checkpoint_sha256']
            saved=torch.load(path,map_location='cpu',weights_only=True)
            assert saved['features']==sample.features and saved['seed']==seed
            scaler=train_scaler(sample.x[train])
            for key,value in scaler.items():np.testing.assert_array_equal(value,saved['scaler'][key].numpy())
            best=min(meta['history'],key=lambda x:x['cal_BS16'])
            assert best['epoch']==saved['best_epoch']==meta['best_epoch']
            assert best['cal_BS16']==meta['best_cal_BS16']
            device=manifest['device'];model=(DailyTFT if kind=='tft' else DailyInformer)(**saved['config']).to(device)
            model.load_state_dict(saved['state']);x=scale_inputs(sample.x,scaler)
            ac,pc=network_predict(model,x[cal],sample.future[cal],device)
            ae,pe=network_predict(model,x[ev],sample.future[ev],device)
            del model
            replayed+=1
        params=fit_calibration(sample.y[cal],pc)
        for actual,expected in zip(params,meta['calibration']):
            assert actual.keys()==expected.keys()
            for key,value in actual.items():
                if isinstance(value,float):assert abs(value-expected[key])<2e-6,(kind,exp,year,seed,key)
                else:assert value==expected[key]
        fitted=fit_climatology(data.dates[train],data.y[train])
        for split,mask,a,p in [('cal',cal,ac,pc),('eval',ev,ae,pe)]:
            _,ref=predict_climatology(data.dates[mask],fitted)
            expected=prediction_frame(data.dates[mask],sample.y[mask],a,apply_calibration(p,params),ref,params,kind,exp,year,seed)
            path=PRIVATE/meta[split+'_predictions'];assert sha(path)==meta[split+'_predictions_sha256']
            actual=pd.read_parquet(path)
            pd.testing.assert_frame_equal(actual,expected,rtol=2e-5,atol=2e-5)
            (cal_frames if split=='cal' else ev_frames)[(year,exp,kind,seed)]=actual
    if not args.partial:
        ensemble=[]
        for year,exp,kind in __import__('itertools').product(YEARS,feature_groups(),MODELS):
            seeds=[42] if kind=='lgbm' else SEEDS
            c=[cal_frames[(year,exp,kind,s)] for s in seeds];e=[ev_frames[(year,exp,kind,s)] for s in seeds]
            if kind=='lgbm':p=e[0]
            else:p,_=ensemble_thresholds(seed_mean(c,tuple(seeds)),seed_mean(e,tuple(seeds)))
            ensemble.append(p)
        expected=pd.concat(ensemble,ignore_index=True)
        pd.testing.assert_frame_equal(expected,pd.read_parquet(PRIVATE/'predictions_ensemble.parquet'),rtol=1e-12,atol=1e-12)
        expected.year='pooled2021-2023'
        pd.testing.assert_frame_equal(score(expected),pd.read_csv(REPORT/'scores_pooled.csv'),check_dtype=False,rtol=1e-11,atol=1e-11)
        old=ROOT/'reports/informer_regional_matrix_2026_10_28'
        frozen=json.loads((old/'publication_manifest.json').read_text(encoding='utf8'))
        for name,info in frozen['files'].items():assert sha(old/name)==info['sha256']
    result=dict(status='partial_passed' if args.partial else 'passed',models_replayed=len(models),
        neural_checkpoints_replayed=replayed,lightgbm_heads_replayed=trees,
        calibration_and_evaluation_splits=2*len(models),raw_predictor_hours_reconstructed=hour_checks,
        train_scalers_reproduced=True,calibration_reproduced=True,
        source_rows_match=True,old_results_preserved=True,test2025_read=False,
        seconds=time.perf_counter()-tick,validator_sha256=sha(__file__))
    dump(REPORT/('validation_partial.json' if args.partial else 'validation.json'),result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
