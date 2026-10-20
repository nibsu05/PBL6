"""So đầu vào cũ/V1/V2 trên cùng nhãn vùng, chỉ development2021–2023."""
from pathlib import Path
import sys, json, time, argparse
import numpy as np
import pandas as pd
import lightgbm as lgb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.regional_dataset import (COMMON_MET, TIME_NAMES, RAIN_INPUTS, LABEL,
                                 legacy_predictors, supervised_windows)
from src.verification import (continuous_scores, contingency_scores,
                              paired_block_bootstrap, metric_rmse, metric_mae)
from scripts.build_regional_datasets import sha256


def clean(value):
    if isinstance(value, dict): return {k:clean(v) for k,v in value.items()}
    if isinstance(value, list): return [clean(v) for v in value]
    if isinstance(value, (float,np.floating)): return float(value) if np.isfinite(value) else None
    if isinstance(value, np.integer): return int(value)
    return value


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data',type=Path,default=ROOT/'data/processed/regional_danang')
    ap.add_argument('--report',type=Path,default=ROOT/'reports/regional_danang_v1_v2')
    ap.add_argument('--bootstrap',type=int,default=1000)
    args = ap.parse_args()
    args.report.mkdir(parents=True,exist_ok=True)
    private = ROOT/'data/operational/regional_danang_v1_v2'
    private.mkdir(parents=True,exist_ok=True)
    # Filter at the file reader. No model fitting, scoring or target diagnostics2025.
    cutoff = pd.Timestamp('2024-01-01',tz='UTC')
    v1 = pd.read_parquet(args.data/'v1_hourly.parquet',filters=[('datetime','<',cutoff)]).set_index('datetime')
    v2 = pd.read_parquet(args.data/'v2_hourly.parquet',filters=[('datetime','<',cutoff)]).set_index('datetime')
    old_path = ROOT/'data/processed/danang_full_features_2015_2026.parquet'
    legacy = pd.read_parquet(old_path,filters=[('datetime','<','2024-01-02')])
    legacy = legacy[pd.to_datetime(legacy.datetime,utc=True)<cutoff]
    old = legacy_predictors(legacy).reindex(v1.index)
    old[LABEL] = v1[LABEL]
    old['label_permanent'] = v1['label_permanent']
    catalog = pd.read_csv(args.report/'feature_catalog.csv').set_index('column').to_dict('index')
    common = [f'mean__{n}' for n in COMMON_MET] + list(TIME_NAMES)
    spatial_common = [c for c,m in catalog.items() if m['version']=='V2' and m['source'] in COMMON_MET]
    full1 = [c for c,m in catalog.items() if m['version']=='V1' and m['source'] not in RAIN_INPUTS]
    full2 = [c for c,m in catalog.items() if m['source'] not in RAIN_INPUTS]
    definitions = {'OLD_COMMON':(old,common), 'V1_COMMON':(v1,common),
                   'V2_COMMON':(v2,common+spatial_common),
                   'V1_FULL':(v1,full1),'V2_FULL':(v2,full2)}
    matrices = {k:supervised_windows(f,c) for k,(f,c) in definitions.items()}
    base = matrices['V1_COMMON']
    common_valid = np.logical_and.reduce([m['valid'] for m in matrices.values()])
    for m in matrices.values():
        if not np.array_equal(m['issue'],base['issue']) or not np.array_equal(m['y'],base['y']):
            raise ValueError('Các model không cùng issue/nhãn')
    dates = base['dates'][common_valid]
    y = base['y'][common_valid]
    x = {k:m['x'][common_valid] for k,m in matrices.items()}
    if not set(dates.year).issubset(set(range(2015,2024))):
        raise ValueError('Chặn năm ngoài development')
    # Comparison of fields is diagnostic, not verification against independent truth.
    diagnostics = []
    mask = v1.index.year<=2023
    for col in common:
        if col in TIME_NAMES: continue
        a,b = old.loc[mask,col].to_numpy(float),v1.loc[mask,col].to_numpy(float)
        valid = np.isfinite(a)&np.isfinite(b)
        a,b = a[valid],b[valid]
        diagnostics.append({'feature':col,'n':int(valid.sum()),'old_mean':a.mean(),
                            'v1_mean':b.mean(),'mean_difference_v1_minus_old':(b-a).mean(),
                            'mean_abs_difference':abs(b-a).mean(),
                            'correlation':float(np.corrcoef(a,b)[0,1]) if a.std()>0 and b.std()>0 else np.nan})
    pd.DataFrame(diagnostics).to_csv(args.report/'legacy_field_comparison.csv',index=False)
    amount_old = legacy.copy()
    amount_old.index = pd.to_datetime(amount_old.datetime,utc=True)
    amount_old = amount_old.reindex(v1.index)
    # Old precipitation is not used as a predictor or target in the pilot.
    label_diag = continuous_scores(v1[LABEL],amount_old.precipitation)
    label_diag['meaning'] = 'Different products and spatial supports; not independent truth or a quality ranking.'
    (args.report/'label_comparison.json').write_text(json.dumps(clean(label_diag),ensure_ascii=False,indent=2),encoding='utf-8')
    opts = dict(objective='tweedie',tweedie_variance_power=1.5,n_estimators=400,
                learning_rate=.04,num_leaves=15,min_child_samples=60,max_bin=63,
                n_jobs=4,random_state=20261020,verbosity=-1,deterministic=True,
                force_col_wise=True,feature_fraction=1.,bagging_fraction=1.)
    manifest = {'status':'running','years_eval':[2021,2022,2023],
                'folds':[], 'window_hours':24,'horizon_hours':[3,6],'issue_stride_hours':6,
                'target':LABEL,'target_support':'area mean over93selected full cells',
                'learner':'LightGBM Tweedie, deterministic single seed; same budget/early stopping for all',
                'model_options':opts,'temporal_features_per_column':['last','mean6','mean24','change6'],
                'views':{k:{'hourly_predictors':list(c),'tabular_features':len(matrices[k]['features'])} for k,(f,c) in definitions.items()},
                'input_files_sha256':{'legacy':sha256(old_path),
                                       'v1':sha256(args.data/'v1_hourly.parquet'),
                                       'v2':sha256(args.data/'v2_hourly.parquet')},
                'test_2025_scored':False,'new_neural_training':False,
                'rain_predictors_used':False,'legacy_ONI_used':False,'legacy_CIN_used':False,
                'caveats':['Exploratory retrospective evaluation;2021–2023 have been examined in earlier project work.',
                           'Old and new inputs differ in provider/spatial support/processing, not geography alone.',
                           'A single deterministic tree seed does not quantify architecture or training-seed uncertainty.',
                           'Persistence from delayed Gauge labels is idealized, not a real-time baseline.',
                           'Rainfall predictor fields are exported but omitted in all pilot models.',
                           'Legacy ONI may contain future months; legacy CIN missing/zero semantics are not recoverable here.']}
    scores, predictions, boots = [], [], []
    started = time.perf_counter()
    for year in [2021,2022,2023]:
        train = dates.year < year-1
        cal = dates.year == year-1
        ev = dates.year == year
        manifest['folds'].append({'eval':year,'cal':year-1,'train_start':2015,'train_end':year-2,
                                  'n_train':int(train.sum()),'n_cal':int(cal.sum()),'n_eval':int(ev.sum()),'models':[]})
        for hi,horizon in enumerate([3,6]):
            frame = pd.DataFrame({'issue':dates[ev],'obs':y[ev,hi]})
            frame['zero'] = 0.
            fitclim = pd.DataFrame({'month':dates[train].month,'hour':dates[train].hour,'y':y[train,hi]})
            clim = fitclim.groupby(['month','hour']).y.mean()
            frame['climatology'] = [clim.get((t.month,t.hour),fitclim.y.mean()) for t in dates[ev]]
            raw_target = v1[LABEL].to_numpy(float)
            issues = base['issue'][common_valid][ev]
            frame['persistence_GC_idealized'] = [raw_target[t-horizon:t].sum() for t in issues]
            for name,mat in x.items():
                model = lgb.LGBMRegressor(**opts)
                tic = time.perf_counter()
                model.fit(mat[train],y[train,hi],eval_set=[(mat[cal],y[cal,hi])],
                          eval_metric='tweedie',callbacks=[lgb.early_stopping(30,first_metric_only=True,verbose=False)])
                frame[name] = np.maximum(model.booster_.predict(mat[ev]),0.)
                model.booster_.save_model(str(private/f'{year}_{horizon}h_{name}.txt'))
                manifest['folds'][-1]['models'].append({'name':name,'horizon':horizon,'best_iteration':model.best_iteration_,
                                                       'seconds':round(time.perf_counter()-tic,3)})
                print(f'{year} {horizon}h {name}: trees={model.best_iteration_} rmse={continuous_scores(y[ev,hi],frame[name])["RMSE"]:.4f}',flush=True)
            frame['year'] = year;frame['horizon'] = horizon
            month = (pd.DatetimeIndex(frame.issue)+pd.Timedelta(hours=7)).month
            frame['season'] = np.where(np.isin(month,[11,12,1,2]),'nov_feb',np.where(np.isin(month,range(5,11)),'may_oct','mar_apr'))
            models = ['zero','climatology','persistence_GC_idealized',*x]
            for season,sub in [('all',frame),*list(frame.groupby('season'))]:
                for name in models:
                    s = continuous_scores(sub.obs,sub[name]);cs = contingency_scores(sub.obs,sub[name],10.)
                    scores.append(dict(year=year,horizon=horizon,season=season,source=name,**s,
                                       CSI10=cs['CSI'],POD10=cs['POD'],FAR10=cs['FAR'],events10=cs['n_obs_events']))
            predictions.append(frame)
        (args.report/'run.json').write_text(json.dumps(clean(manifest),ensure_ascii=False,indent=2),encoding='utf-8')
    pred = pd.concat(predictions,ignore_index=True)
    pred.to_parquet(private/'paired_predictions_2021_2023.parquet',index=False)
    pd.DataFrame(scores).to_csv(args.report/'scores.csv',index=False)
    contrasts = [('V1_COMMON','OLD_COMMON'),('V1_FULL','V1_COMMON'),
                 ('V2_COMMON','V1_COMMON'),('V2_FULL','V1_FULL')]
    for (year,horizon),f in pred.groupby(['year','horizon']):
        f = f.assign(date=pd.to_datetime(f.issue).dt.tz_localize(None))
        for a,b in contrasts:
            for metric in [metric_rmse,metric_mae]:
                row = paired_block_bootstrap(f,'obs',a,b,metric,block_days=5,n_boot=args.bootstrap,seed=20261020)
                boots.append(dict(year=int(year),horizon=int(horizon),season='all',**row))
    pd.DataFrame(boots).to_csv(args.report/'paired_bootstrap.csv',index=False)
    manifest['status']='complete';manifest['elapsed_seconds']=round(time.perf_counter()-started,1)
    manifest['bootstrap']={'block_days':5,'replicates':args.bootstrap,'seed':20261020,
                           'scope':'paired differences conditional on fixed fitted models; no multiple-comparison correction'}
    (args.report/'run.json').write_text(json.dumps(clean(manifest),ensure_ascii=False,indent=2),encoding='utf-8')
    print('Pilot complete',manifest['elapsed_seconds'],'seconds',flush=True)


if __name__=='__main__': main()
