"""Independent source/header, normalization, replay and metric verification."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import argparse
import json
import joblib
import numpy as np
import pandas as pd
import requests
import torch
import eccodes as ec
from src.gfs_temporal import BASE,PUBLIC,OLD,CATALOG,SEEDS,RAIN_LEADS,MET_LEADS,sha,write_json,load_protocol
from src.gfs_temporal_models import arrays,make_projection,replay_gru,calibrated
from src.gfs_daily_gru import normalizers
from scripts.collect_gfs_station_pilot import range_bytes

def source_checks():
    p=load_protocol();plan=json.loads((BASE/'collection_plan.json').read_text());registry=pd.read_csv(BASE/'registry_private.csv')
    checked=0
    expected_short={'rain_cumulative':'tp','t850_k':'t','rh850':'r','u850':'u','v850':'v','pwat':'pwat'}
    for day in plan['days']:
        path=BASE/'days'/f'{day}.npz';info=json.loads(path.with_suffix('.json').read_text())
        if sha(path)!=info['sha256']:raise ValueError('Source cache checksum changed')
        if sha(ROOT/info['original_cache'])!=info['original_sha256']:raise ValueError('Original source was altered')
        if len(info['messages'])!=39:raise ValueError('Wrong message count')
        z=np.load(path)
        for m in info['messages']:
            if m['shortName']!=expected_short[m['name']] or m['dataDate']!=int(day) or m['dataTime']!=0:raise ValueError('GRIB identity mismatch')
            if m['name'].endswith('850') or m['name']=='t850_k':
                if m['index_level']!='850 mb':raise ValueError('Wrong pressure level')
            if m['name']=='rain_cumulative' and m['startStep']!=0:raise ValueError('Wrong accumulation origin')
            checked+=1
        np.testing.assert_array_equal(z['station_ids'],registry.canonical_id)
    # Dates chosen evenly from the collection schedule, never from rainfall/errors.
    selected=[plan['days'][int(i)] for i in np.linspace(0,len(plan['days'])-1,8,dtype=int)]
    independent=0
    with requests.Session() as session:
        for day in selected:
            info=json.loads((BASE/'days'/f'{day}.json').read_text());z=np.load(BASE/'days'/f'{day}.npz')
            for name,lead in [('rain_cumulative',18),('rh850',54),('pwat',78)]:
                m=next(x for x in info['messages'] if x['name']==name and x['endStep']==lead)
                data,_=range_bytes(session,m['source_url'],*m['range'])
                import hashlib
                if hashlib.sha256(data).hexdigest()!=m['message_sha256']:raise ValueError('Remote message changed')
                g=ec.codes_new_from_message(data)
                try:
                    if name=='rh850':
                        if ec.codes_get(g,'typeOfLevel')!='isobaricInhPa' or ec.codes_get(g,'level')!=850:raise ValueError('Decoded pressure level mismatch')
                    values=ec.codes_get_values(g).reshape(721,1440)
                    lat=registry.latitude.to_numpy();lon=registry.longitude.to_numpy()%360
                    south=np.floor(lat/.25)*.25;west=np.floor(lon/.25)*.25;fy=(lat-south)/.25;fx=(lon-west)/.25
                    row=np.rint((90-south)/.25).astype(int);col=np.rint(west/.25).astype(int)
                    manual=values[row,col]*(1-fy)*(1-fx)+values[row,(col+1)%1440]*(1-fy)*fx+values[row-1,col]*fy*(1-fx)+values[row-1,(col+1)%1440]*fy*fx
                    saved=z['cumulative_mm'][RAIN_LEADS.index(lead)] if name=='rain_cumulative' else z['met'][MET_LEADS.index(lead),:,0 if name=='rh850' else 4]
                    np.testing.assert_allclose(saved,manual,rtol=2e-6,atol=1e-5);independent+=len(manual)
                finally:ec.codes_release(g)
    value=dict(status='passed',days=len(plan['days']),grib_headers_checked=checked,remote_grib_messages_replayed=24,
               independent_bilinear_station_values=independent,original_caches_unchanged=True,
               protocol_sha256=sha(PUBLIC/'protocol.json'),collection_plan_sha256=sha(BASE/'collection_plan.json'))
    write_json(PUBLIC/'source_verification.json',value);print(json.dumps(value))

def protect():
    oldfinal=ROOT/'data/operational/gfs_station_final_2026_11_17'
    old=json.loads((oldfinal/'protected_before.json').read_text())
    # Snapshot current bytes; earlier manifests are also checked by frozen tools.
    paths=[ROOT/name for name in old]
    for folder in (ROOT/'reports/gfs_station_final_2026_11_17',oldfinal/'models'):
        paths.extend(p for p in folder.glob('*') if p.is_file())
    paths.extend(ROOT/name for name in ['src/gfs_final.py','src/gfs_capacity_control.py','scripts/run_gfs_capacity_controls.py'])
    saved={str(p.relative_to(ROOT)):sha(p) for p in paths if p.exists()}
    path=BASE/'protected_before.json'
    if path.exists():
        if json.loads(path.read_text())!=saved:raise ValueError('Protected artifacts changed')
    else:write_json(path,saved)
    return len(saved)

def model_checks():
    from scripts.score_gfs_temporal import assert_freeze,predict_all,MODELS
    torch.set_num_threads(4)
    assert_freeze();protected=protect();f=pd.read_parquet(BASE/'evaluation_predictions_private.parquet')
    f['_global_position']=np.arange(len(f))
    source=pd.read_parquet(BASE/'dataset_private.parquet')
    source=source[~source.split.isin(['train','cal'])].reset_index(drop=True)
    for name in ('issue_utc','station_id','horizon','gauge_namespace','target_start_utc','target_end_utc','evaluation_set'):
        np.testing.assert_array_equal(f[name],source[name])
    np.testing.assert_allclose(f[CATALOG['T3']+['y_mm']],source[CATALOG['T3']+['y_mm']],rtol=0,atol=0)
    dev=pd.read_parquet(BASE/'dataset_private.parquet',filters=[('split','in',['train','cal','dev'])])
    train=dev.split.to_numpy().reshape(-1,3)[:,0]=='train'
    for config in ('T0','T3','LINEAR23'):
        for seed in SEEDS:
            a=torch.load(BASE/'models'/f'GRU_{config}_seed{seed}.pt',map_location='cpu',weights_only=False)
            if config=='LINEAR23':
                projection=make_projection(dev,train)
                for name in projection:np.testing.assert_array_equal(a['projection'][name],projection[name])
            raw=arrays(dev,config,a['projection']);norm=normalizers(raw,train)
            for name in norm:np.testing.assert_array_equal(norm[name],a['normalizers'][name])
    keys=f[['issue_utc','station_id']].drop_duplicates().iloc[np.linspace(0,len(f)//3-1,36,dtype=int)]
    sample=f.merge(keys,on=['issue_utc','station_id'],validate='many_to_one').sort_values(['issue_utc','station_id','horizon']).reset_index(drop=True)
    replay,_=predict_all(sample);changed=sample.copy();changed['y_mm']=1234567
    perturbed,_=predict_all(changed)
    maximum=0.
    for model in MODELS:
        for head in ('mean','median','p1','p50'):
            name=model+'_'+head
            np.testing.assert_allclose(replay[name],sample[name],rtol=2e-5,atol=4e-4)
            np.testing.assert_array_equal(replay[name],perturbed[name])
            maximum=max(maximum,float(abs(replay[name]-sample[name]).max()))
    metric=pd.read_csv(PUBLIC/'point_metrics.csv');checked=0;maximum_metric_difference=0.
    for row in metric.itertuples():
        sub=f[f.evaluation_set.eq(row.evaluation_set)&f.horizon.eq(row.horizon)]
        error=sub[row.model+'_'+row.functional].to_numpy()-sub.y_mm.to_numpy();sid=sub.station_id.to_numpy()
        mae=pd.Series(abs(error)).groupby(sid).mean().mean();rmse=np.sqrt(pd.Series(error**2).groupby(sid).mean()).mean();bias=pd.Series(error).groupby(sid).mean().mean()
        for name,value in [('macro_mae',mae),('macro_rmse',rmse),('macro_bias',bias)]:
            # Frozen helper uses mae_macro/rmse_macro naming; resolve below.
            candidates=[name,name.replace('macro_','')+'_macro',name.replace('macro_','')]
            field=next((key for key in candidates if hasattr(row,key)),None)
            if field is None:raise ValueError('Unknown metric column '+name)
            tolerance=2e-6 if error.dtype==np.dtype('float32') else 1e-9
            np.testing.assert_allclose(getattr(row,field),value,rtol=tolerance,atol=tolerance)
            maximum_metric_difference=max(maximum_metric_difference,abs(float(getattr(row,field))-float(value)));checked+=1
    prob=pd.read_csv(PUBLIC/'probability_metrics.csv')
    for row in prob.itertuples():
        sub=f[f.evaluation_set.eq(row.evaluation_set)&f.horizon.eq(row.horizon)];label=sub.y_mm.ge(row.threshold_mm).to_numpy()
        error=(sub[f'{row.model}_p{row.threshold_mm}'].to_numpy()-label)**2
        station=sub.station_id.to_numpy();per=pd.Series(error).groupby(station).mean();bs=per.mean()
        np.testing.assert_allclose(row.macro_bs,bs,rtol=1e-9,atol=1e-9);checked+=1
        ref=pd.Series((sub[f'CLIM_p{row.threshold_mm}'].to_numpy()-label)**2).groupby(station).mean()
        bss=(1-per/ref.where(ref>0)).mean()
        np.testing.assert_allclose(row.macro_bss,bss,rtol=1e-9,atol=1e-9,equal_nan=True);checked+=1
    events=pd.read_csv(PUBLIC/'event_metrics.csv')
    for row in events.itertuples():
        sub=f[f.evaluation_set.eq(row.evaluation_set)&f.horizon.eq(row.horizon)]
        label=sub.y_mm.ge(row.threshold_mm).to_numpy();yes=sub[f'{row.model}_p{row.threshold_mm}'].ge(row.cutoff).to_numpy()
        table=pd.DataFrame(dict(station=sub.station_id.to_numpy(),H=(yes&label).astype(int),M=(~yes&label).astype(int),F=(yes&~label).astype(int))).groupby('station').sum()
        for name,value in [('macro_pod',(table.H/(table.H+table.M).replace(0,np.nan)).mean()),
                           ('macro_far',(table.F/(table.H+table.F).replace(0,np.nan)).mean()),
                           ('macro_csi',(table.H/(table.H+table.M+table.F).replace(0,np.nan)).mean())]:
            np.testing.assert_allclose(getattr(row,name),value,rtol=1e-9,atol=1e-9,equal_nan=True);checked+=1
        for name,column in [('hits','H'),('misses','M'),('false_alarms','F')]:
            if getattr(row,name)!=int(table[column].sum()):raise ValueError('Event contingency counts differ')
            checked+=1
    seeds=np.load(BASE/'seed_outputs_private.npz')
    for model in [m for m in MODELS if m.startswith(('LGB_','GRU_'))]:
        for head in ('mean','median','p1','p50'):
            np.testing.assert_allclose(f[model+'_'+head],np.mean([seeds[f'{model}__{j}__{head}'] for j in range(3)],0),atol=1e-12)
    cpu_values=0
    for config in ('T0','T3','LINEAR23'):
        for j,seed in enumerate(SEEDS):
            a=torch.load(BASE/'models'/f'GRU_{config}_seed{seed}.pt',map_location='cpu',weights_only=False)
            cpu=replay_gru(sample,a,'cpu');positions=sample['_global_position'].to_numpy()
            for head in ('mean','median'):
                np.testing.assert_allclose(cpu[head].ravel(),seeds[f'GRU_{config}__{j}__{head}'][positions],rtol=2e-5,atol=4e-4);cpu_values+=len(sample)
    # Independently resample dates (no count-matrix helper) for one primary CI.
    sub=f[f.evaluation_set.eq('retrospective2025_legacy')&f.horizon.eq(1)].copy()
    days=pd.date_range(sub.issue_utc.min(),sub.issue_utc.max(),freq='D');stations=sorted(sub.station_id.unique())
    matrices=[]
    for model in ('LGB_T3','LGB_T0'):
        temp=sub[['issue_utc','station_id']].copy();temp['error']=(sub[model+'_mean'].to_numpy()-sub.y_mm.to_numpy())**2
        matrices.append(temp.pivot(index='issue_utc',columns='station_id',values='error').reindex(index=days,columns=stations).to_numpy())
    rng=np.random.default_rng(1701);indices=[]
    for _ in range(5000):
        starts=rng.integers(0,len(days),size=int(np.ceil(len(days)/14)))
        indices.append(np.concatenate([(start+np.arange(14))%len(days) for start in starts])[:len(days)])
    indices=np.asarray(indices);distribution=[]
    for start in range(0,5000,100):
        a,b=[np.nanmean(np.sqrt(np.nanmean(values[indices[start:start+100]],axis=1)),axis=1) for values in matrices]
        distribution.extend(a-b)
    expected=np.quantile(distribution,[.025/12,1-.025/12])
    pair=pd.read_csv(PUBLIC/'paired_comparisons.csv')
    selected=pair[pair.evaluation_set.eq('retrospective2025_legacy')&pair.horizon.eq(1)&pair.model.eq('LGB_T3')&pair.reference.eq('LGB_T0')&pair.metric.eq('mean_rmse')].iloc[0]
    np.testing.assert_allclose([selected.simultaneous_ci_low,selected.simultaneous_ci_high],expected,rtol=1e-8,atol=1e-8)
    write_json(PUBLIC/'model_verification.json',dict(status='passed',rows=len(f),replay_rows=len(sample),
        maximum_replay_absolute_difference=maximum,future_label_perturbation_invariant=True,
        train_only_normalizers_and_projection=True,metric_values_independently_checked=checked,
        protected_artifacts_unchanged=protected,ensemble_seed_arithmetic_checked=True,
        actual_checkpoint_cpu_values_replayed=cpu_values,primary_ci_independently_replayed=True,
        all_evaluation_inputs_and_labels_match_frozen_dataset=True,
        maximum_independent_point_metric_difference=maximum_metric_difference,
        point_metric_float32_tolerance=2e-6,point_metric_float64_tolerance=1e-9))
    print('Model verification passed',len(f),checked)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sources',action='store_true');parser.add_argument('--snapshot',action='store_true');args=parser.parse_args()
    if args.snapshot:print('Protected',protect())
    elif args.sources:source_checks()
    else:model_checks()

if __name__=='__main__':main()
