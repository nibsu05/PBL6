"""Prepare -> freeze code -> train-only CV -> fit -> calibrate2025 -> freeze -> score2026."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import argparse
import os
from importlib.metadata import version
import joblib
import numpy as np
import pandas as pd

from src.gfs_window import (BASE,PUBLIC,SOURCE,SOURCE_SHA,OLD,VRAIN,CODE,CASES,SEEDS,FEATURES,
    now,sha,protocol,write_json,read_json,save_csv,save_parquet,progress,load_frame,fit_mask,
    calibrate,apply_calibration,assert_dependencies)
from src.gfs_window_models import (select_shared,fit_case,fit_auxiliary,predict_auxiliary,
    predict_means,fit_climatology,predict_climatology,fit_mos,predict_mos,save_model)
from src.gfs_window_evaluation import bootstrap_table,dry_heavy_table
from src.gfs_final_metrics import summary_tables


def prepare():
    BASE.mkdir(parents=True,exist_ok=True);PUBLIC.mkdir(parents=True,exist_ok=True)
    path=PUBLIC/'protocol.json';p=protocol()
    if path.exists() and read_json(path)!=p:
        raise ValueError('Protocol already exists and differs; create a new version')
    if not path.exists():write_json(path,p)
    if sha(SOURCE)!=SOURCE_SHA:raise ValueError('Source SHA mismatch')
    for rel in ['source_verification.json','dataset_verification.json','model_verification.json']:
        original=ROOT/'reports/gfs_temporal_2026_11_17'/rel
        if read_json(original)['status']!='passed':raise ValueError('Parent not verified: '+rel)
    # Protect all published parent models/data/code and the three user-edited slides.
    protected={}
    for rel in ['data/operational/gfs_temporal_2026_11_17/protected_before.json']:
        value=read_json(ROOT/rel)
        if isinstance(value,dict):
            for k,v in value.items():
                if isinstance(v,str) and len(v)==64:protected[k]=v
    for directory in ['reports/gfs_temporal_2026_11_17','reports/gfs_station_final_2026_11_17',
                      'data/operational/gfs_temporal_2026_11_17/models']:
        for file in (ROOT/directory).rglob('*'):
            if file.is_file():protected[str(file.relative_to(ROOT)).replace('\\','/')]=sha(file)
    for rel in ['src/gfs_daily.py','src/gfs_daily_models.py','src/gfs_temporal.py',
                'src/gfs_temporal_models.py','src/gfs_temporal_evaluation.py',
                'reports/daily_gauge_slides_2026_11_04/PBL6_DU_LIEU_NGAY_3_MO_HINH.pptx',
                'reports/short_range_three_models_2026_10_21/Dự đoán ngắn hạn 21_10.pptx']:
        if (ROOT/rel).exists():protected[rel]=sha(ROOT/rel)
    if not (BASE/'protected_before.json').exists():write_json(BASE/'protected_before.json',protected)
    f=load_frame(training_only=True)
    if not np.isfinite(f[FEATURES['N3']+['y_mm']].to_numpy(dtype=float)).all():raise ValueError('Missing training/calibration inputs')
    if f.station_id.nunique()!=57 or not f.sample_ready.all() or not f.recommended_sample.all():raise ValueError('Cohort/mask changed')
    if f.duplicated(['station_id','issue_utc','horizon']).any():raise ValueError('Duplicate issue/station/horizon')
    for role,years in [('fit2021_22',(2021,2022)),('fit2023',(2023,2023)),('fit2024',(2024,2024)),('calibration2025',(2025,2025))]:
        g=f[f.role.eq(role)]
        for col in ('target_start_utc','target_end_utc'):
            if not g[col].dt.tz_convert('Asia/Ho_Chi_Minh').dt.year.between(*years).all():raise ValueError('Target crosses role/year boundary')
    counts=f[f.horizon.eq(1)].groupby('role').agg(packs=('station_id','size'),stations=('station_id','nunique'),issue_dates=('issue_utc','nunique')).reset_index()
    save_csv(counts,PUBLIC/'role_counts.csv')
    verification=dict(status='passed',source_sha256=SOURCE_SHA,station_count=57,
        short_training_packs=int((fit_mask(f,'short') & f.horizon.eq(1)).sum()),
        long_training_packs=int((fit_mask(f,'long') & f.horizon.eq(1)).sum()),
        calibration_packs=int((f.role.eq('calibration2025') & f.horizon.eq(1)).sum()),
        fitting_max_year=2024,calibration_year=2025,retrospective_labels_read=False,
        common_rows_and_features_finite=True,original_source_read_only=True)
    write_json(PUBLIC/'dataset_verification.json',verification)


def lock_training():
    tests=read_json(PUBLIC/'tests_verification.json')
    if tests['status']!='passed':raise ValueError('Tests must pass before fitting')
    lock=dict(protocol_sha256=sha(PUBLIC/'protocol.json'),dataset_sha256=SOURCE_SHA,
        code={rel:sha(ROOT/rel) for rel in CODE},
        auxiliary_selection_sha256=sha(ROOT/'reports/gfs_station_daily_v2_2026_11_10/tree_selection.json'),
        gauge_days_sha256=sha(VRAIN/'rain_channels.npz'),
        environment={p:version(p) for p in ['numpy','pandas','pyarrow','scikit-learn','lightgbm','joblib']})
    path=BASE/'training_lock.json'
    if path.exists():
        if read_json(path)!=lock:raise ValueError('Training dependencies changed')
    else:write_json(path,lock)
    assert_dependencies(lock)
    return lock


def train():
    lock=lock_training()
    if (BASE/'model_freeze.json').exists():raise ValueError('Models already frozen; use score/verify')
    f=load_frame(training_only=True)
    selection=select_shared(f)
    models=BASE/'models';models.mkdir(exist_ok=True)
    objective=selection['selected_loss'];cutoffs=[];registry=[]
    for h in (1,2,3):
        sub=f[f.horizon.eq(h)].reset_index(drop=True)
        cal=sub[sub.role.eq('calibration2025')].reset_index(drop=True)
        for window in ('short','long'):
            aux=fit_auxiliary(sub,FEATURES['N3'],window,h,'N3')
            _,raw=predict_auxiliary(aux,cal)
            a,_,_=calibrate(cal,[r[0] for r in raw],[r[1] for r in raw])
            save_model(models/f'CAL_{window}_N3_d{h}.joblib',a)
            for case,(w,loss) in CASES.items():
                if w!=window:continue
                fit_case(sub,window,loss,'N3',h,selection)
                cutoffs.append(dict(model=case,horizon=h,cutoff=a['cutoff'],source='cross_fitted2025',shared_auxiliary=window+'_N3'))
                registry.append(dict(model=case,window=window,loss=loss,config='N3',horizon=h))
        for config in ('N0','N1'):
            fit_case(sub,'long',objective,config,h,selection)
            aux=fit_auxiliary(sub,FEATURES[config],'long',h,config)
            _,raw=predict_auxiliary(aux,cal)
            a,_,_=calibrate(cal,[r[0] for r in raw],[r[1] for r in raw])
            save_model(models/f'CAL_long_{config}_d{h}.joblib',a)
            cutoffs.append(dict(model=config,horizon=h,cutoff=a['cutoff'],source='cross_fitted2025',shared_auxiliary='long_'+config))
            registry.append(dict(model=config,window='long',loss=objective,config=config,horizon=h))
        selected='B' if objective=='tweedie' else 'D'
        registry.append(dict(model='N3',window='long',loss=objective,config='N3',horizon=h,alias=selected))
        selected_cutoff=next(r['cutoff'] for r in cutoffs if r['model']==selected and r['horizon']==h)
        cutoffs.append(dict(model='N3',horizon=h,cutoff=selected_cutoff,source='alias_train_CV_selected_'+selected))
        for window in ('short','long'):
            path=models/f'MOS_{window}_d{h}.joblib'
            progress('mos_fit',window=window,horizon=h)
            if path.exists():a=joblib.load(path)
            else:a=fit_mos(sub,window);save_model(path,a)
            raw=predict_mos(a,cal)
            c,_,_=calibrate(cal,[raw['wet']],[raw['conditional']])
            save_model(models/f'CAL_MOS_{window}_d{h}.joblib',c)
            cutoffs.append(dict(model='MOS_'+window.upper(),horizon=h,cutoff=c['cutoff'],source='cross_fitted2025'))
    for window,end in [('short',2022),('long',2024)]:
        save_model(models/f'CLIM_{window}.joblib',fit_climatology(f,end))
    write_json(PUBLIC/'model_catalog.json',dict(cases=registry,selected_prospective_case='B' if objective=='tweedie' else 'D',
        objective_selection='train-only2022CV',new_mean_estimators=54,new_auxiliary_estimators=108,
        factorial_cases=4,ablations=['N0','N1','N3 alias'],seeds=list(SEEDS)))
    save_csv(pd.DataFrame(cutoffs),PUBLIC/'cutoffs.csv')
    assert_dependencies(lock)
    artifacts={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in models.glob('*.joblib')}
    for rel in ['selection.json','cutoffs.csv','model_catalog.json']:
        artifacts[str((PUBLIC/rel).relative_to(ROOT)).replace('\\','/')]=sha(PUBLIC/rel)
    freeze=dict(frozen_utc=now(),training_lock_sha256=sha(BASE/'training_lock.json'),
        artifacts=artifacts,selection=selection,retrospective2026_labels_read_by_this_pipeline=False,
        prior2026_seen_in_earlier_studies=True)
    write_json(BASE/'model_freeze.json',freeze)
    write_json(PUBLIC/'model_freeze_summary.json',dict(frozen_utc=freeze['frozen_utc'],artifact_count=len(artifacts),
        mean_estimators=54,auxiliary_estimators=108,total_lightgbm_estimators=162,cv_mean_estimators=72,
        model_freeze_sha256=sha(BASE/'model_freeze.json'),training_lock_sha256=sha(BASE/'training_lock.json'),
        objective=objective,calibration_year=2025,retrospective_is_not_untouched_test=True))
    progress('models_frozen',artifacts=len(artifacts))


def check_freeze():
    freeze=read_json(BASE/'model_freeze.json');lock=read_json(BASE/'training_lock.json')
    assert_dependencies(lock)
    if sha(BASE/'training_lock.json')!=freeze['training_lock_sha256']:raise ValueError('Training lock changed')
    for rel,digest in freeze['artifacts'].items():
        if sha(ROOT/rel)!=digest:raise ValueError('Frozen artifact changed: '+rel)
    return freeze


def predict_frame(frame, keep_seed=False):
    """Uses only feature columns. This same routine is used for live input and replay."""
    f=frame.copy();selection=read_json(PUBLIC/'selection.json');seed_rows=[]
    folder=BASE/'models'
    for h in sorted(f.horizon.unique()):
        mask=f.horizon.eq(h);sub=f.loc[mask].reset_index(drop=True)
        aux_cache={}
        for window,config in [('short','N3'),('long','N3'),('long','N0'),('long','N1')]:
            artifacts=[joblib.load(folder/f'AUX_{window}_{config}_d{h}_s{s}.joblib') for s in SEEDS]
            median,raw=predict_auxiliary(artifacts,sub)
            calibration=joblib.load(folder/f'CAL_{window}_{config}_d{h}.joblib')
            aux_cache[(window,config)]=(median,apply_calibration(calibration,raw))
        specs=[(case,w,o,'N3') for case,(w,o) in CASES.items()]
        specs += [(c,'long',selection['selected_loss'],c) for c in ('N0','N1')]
        for label,window,objective,config in specs:
            artifacts=[joblib.load(folder/f'MEAN_{window}_{objective}_{config}_d{h}_s{s}.joblib') for s in SEEDS]
            mean,seeds=predict_means(artifacts,sub);median,prob=aux_cache[(window,config)]
            for head,value in [('mean',mean),('median',median),('p1',prob[:,0]),('p50',prob[:,1])]:
                f.loc[mask,label+'_'+head]=value
            if keep_seed:
                for j,seed in enumerate(SEEDS):
                    seed_rows.append(sub[['station_id','gauge_namespace','issue_utc','horizon','y_mm']].assign(model=label,seed=seed,prediction=seeds[j]))
        selected='B' if selection['selected_loss']=='tweedie' else 'D'
        for head in ('mean','median','p1','p50'):f.loc[mask,'N3_'+head]=f.loc[mask,selected+'_'+head]
        for window in ('short','long'):
            a=joblib.load(folder/f'MOS_{window}_d{h}.joblib');out=predict_mos(a,sub)
            c=joblib.load(folder/f'CAL_MOS_{window}_d{h}.joblib')
            prob=apply_calibration(c,[(out['wet'],out['conditional'])]);label='MOS_'+window.upper()
            for head,value in [('mean',out['mean']),('median',out['median']),('p1',prob[:,0]),('p50',prob[:,1])]:f.loc[mask,label+'_'+head]=value
    for window in ('short','long'):
        clim=predict_climatology(joblib.load(folder/f'CLIM_{window}.joblib'),f)
        for head in ('mean','median','p1','p50'):f['CLIM_'+window.upper()+'_'+head]=clim[head].to_numpy()
    for head in ('mean','median','p1','p50'):f['CLIM_'+head]=f['CLIM_LONG_'+head]
    for label,values in [('ZERO',np.zeros(len(f))),('GFS',f.gfs_rain_mm.to_numpy()),('PERSIST',f.rain_lag_day1_mm.to_numpy())]:
        f[label+'_mean']=values;f[label+'_median']=values
        for threshold in (1,50):f[label+'_p'+str(threshold)]=(values>=threshold).astype(float)
    return f,(pd.concat(seed_rows,ignore_index=True) if seed_rows else None)


def score():
    check_freeze();progress('retrospective2026_scoring')
    if not (BASE/'retrospective_opened.json').exists():write_json(BASE/'retrospective_opened.json',dict(opened_utc=now(),model_freeze_sha256=sha(BASE/'model_freeze.json'),prior_seen=True))
    f=load_frame()
    f=f[f.role.eq('retrospective2026')].reset_index(drop=True)
    f['evaluation_set']='retrospective2026_'+f.gauge_namespace
    if not np.isfinite(f[FEATURES['N3']+['y_mm']].to_numpy(dtype=float)).all():raise ValueError('Evaluation missing values')
    out,seeds=predict_frame(f,keep_seed=True)
    save_parquet(out,BASE/'predictions_private.parquet');save_parquet(seeds,BASE/'seed_predictions_private.parquet')
    models=list(CASES)+['N0','N1','N3','ZERO','GFS','PERSIST','CLIM_SHORT','CLIM_LONG','MOS_SHORT','MOS_LONG']
    c=pd.read_csv(PUBLIC/'cutoffs.csv');cutoffs={(r.model,int(r.horizon)):float(r.cutoff) for r in c.itertuples()}
    tables=summary_tables(out,models,cutoffs)
    for label,table in tables.items():save_csv(table,(BASE if label.endswith('_private') else PUBLIC)/(label+'.csv'))
    save_csv(dry_heavy_table(out,models),PUBLIC/'dry_heavy_metrics.csv')
    progress('paired_bootstrap',draws=5000)
    save_csv(bootstrap_table(out),PUBLIC/'paired_comparisons.csv')
    seed_scores=[]
    from src.gfs_window import macro_rmse
    for (label,h,seed,namespace),s in seeds.groupby(['model','horizon','seed','gauge_namespace']):
        seed_scores.append(dict(evaluation_set='retrospective2026_'+namespace,model=label,horizon=int(h),seed=int(seed),
            macro_rmse=macro_rmse(s.y_mm,s.prediction,s.station_id)))
    save_csv(pd.DataFrame(seed_scores),PUBLIC/'seed_metrics.csv')
    write_json(BASE/'scoring_complete.json',dict(completed_utc=now(),rows=len(out),model_count=len(models),
        predictions_sha256=sha(BASE/'predictions_private.parquet'),labels='2026 retrospective; not used to select loss/hyperparameters'))
    progress('scoring_complete',rows=len(out),models=len(models))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','train','score','all'])
    args=parser.parse_args()
    if args.stage in ('prepare','all'):prepare()
    if args.stage in ('train','all'):train()
    if args.stage in ('score','all'):score()


if __name__=='__main__':main()
