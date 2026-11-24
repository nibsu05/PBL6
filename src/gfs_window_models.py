"""Fixed-budget factorial estimators, independent of retrospective labels."""
from __future__ import annotations

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge, QuantileRegressor, LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.gfs_window import (BASE, PUBLIC, OLD, VRAIN, SEEDS, FEATURES, FOLDS, TREE_CANDIDATES,
    atomic, save_csv, read_json, write_json, fit_mask, cv_masks, macro_rmse, progress)
from src.gfs_daily_models import tree_parameters, fit_tree, predict_tree, ConstantBinary


def save_model(path, value):
    atomic(path,lambda p:joblib.dump(value,p,compress=3))


def fit_mean(frame, features, train, valid, objective, candidate, seed, trees):
    if objective not in ('l2','tweedie'):
        raise ValueError('Unknown mean objective')
    params = tree_parameters(candidate,seed,trees)
    params['objective'] = 'regression' if objective=='l2' else 'tweedie'
    if objective=='tweedie':
        params['tweedie_variance_power']=1.5
    estimator = lgb.LGBMRegressor(**params)
    kwargs = dict(categorical_feature=['station_code'])
    if valid is not None:
        stations = frame.loc[valid,'station_id'].to_numpy()
        def metric(y,p):
            return 'macro_rmse_nonnegative', macro_rmse(y,np.maximum(p,0.),stations), False
        kwargs.update(eval_set=[(frame.loc[valid,features],frame.loc[valid,'y_mm'])],
            eval_metric=metric,callbacks=[lgb.early_stopping(50,first_metric_only=True,verbose=False)])
    estimator.fit(frame.loc[train,features],frame.loc[train,'y_mm'],**kwargs)
    return estimator


def select_shared(frame):
    rows=[]
    folder=BASE/'cv';folder.mkdir(exist_ok=True)
    for candidate in TREE_CANDIDATES:
        for objective in ('tweedie','l2'):
            for h in (1,2,3):
                f=frame[frame.horizon.eq(h)].reset_index(drop=True)
                for fold_index,fold in enumerate(FOLDS):
                    path=folder/f"{candidate['name']}_{objective}_d{h}_q{fold_index+1}.json"
                    progress('train_only_cv',candidate=candidate['name'],objective=objective,horizon=h,fold=fold_index+1)
                    if path.exists():
                        rows.append(read_json(path));continue
                    train,valid=cv_masks(f,fold)
                    model=fit_mean(f,FEATURES['N3'],train,valid,objective,candidate,17,600)
                    score=macro_rmse(f.loc[valid,'y_mm'],np.maximum(model.predict(f.loc[valid,FEATURES['N3']]),0.),f.loc[valid,'station_id'])
                    ref=macro_rmse(f.loc[valid,'y_mm'],f.loc[valid,'gfs_rain_mm'],f.loc[valid,'station_id'])
                    row=dict(candidate=candidate['name'],objective=objective,horizon=h,fold=fold_index+1,
                        train_rows=int(train.sum()),valid_rows=int(valid.sum()),best_iteration=int(model.best_iteration_ or 600),
                        macro_rmse=score,gfs_macro_rmse=ref,normalized_rmse=score/ref,
                        fit_last_target_utc=str((f.loc[train,'issue_utc']+pd.Timedelta(hours=72)).max()),
                        validation_first_issue_utc=str(f.loc[valid,'issue_utc'].min()))
                    write_json(path,row);rows.append(row)
    table=pd.DataFrame(rows);save_csv(table,PUBLIC/'train_only_cv.csv')
    ranking=table.groupby('candidate').normalized_rmse.mean().sort_values()
    candidate=next(c for c in TREE_CANDIDATES if c['name']==ranking.index[0])
    chosen=table[table.candidate.eq(candidate['name'])]
    loss_scores=chosen.groupby('objective').normalized_rmse.mean().sort_values()
    value=dict(status='selected_train2021_2022_only',candidate=candidate,
        candidate_scores={str(k):float(v) for k,v in ranking.items()},
        objective_scores={str(k):float(v) for k,v in loss_scores.items()},
        selected_loss=str(loss_scores.index[0]), selected_window='long',
        trees={str(h):max(1,int(np.median(chosen.loc[chosen.horizon.eq(h),'best_iteration']))) for h in (1,2,3)},
        cv_estimators=len(table), same_candidate_and_rounds_all_four_cases=True)
    write_json(PUBLIC/'selection.json',value)
    return value


def fit_auxiliary(f,features,window,h,config):
    folder=BASE/'models';folder.mkdir(exist_ok=True)
    selection=read_json(PUBLIC.parent/'gfs_station_daily_v2_2026_11_10/tree_selection.json')['selected']
    result=[]
    for seed in SEEDS:
        path=folder/f'AUX_{window}_{config}_d{h}_s{seed}.joblib'
        if path.exists():
            a=joblib.load(path)
            if a['features']!=features or a['window']!=window:
                raise ValueError('Auxiliary checkpoint mismatch')
        else:
            progress('auxiliary',window=window,config=config,horizon=h,seed=seed)
            a=dict(window=window,features=features,seed=seed,heads={})
            train=fit_mask(f,window)
            for head in ('median','wet','conditional'):
                selected=selection[head]
                a['heads'][head]=fit_tree(f,features,train,None,head,selected['candidate'],seed,selected['trees'][str(h)])
            save_model(path,a)
        result.append(a)
    return result


def predict_auxiliary(artifacts,f):
    median=np.mean([predict_tree(a['heads']['median'],a['features'],f,'median') for a in artifacts],axis=0)
    raw=[(predict_tree(a['heads']['wet'],a['features'],f,'wet'),
          predict_tree(a['heads']['conditional'],a['features'],f,'conditional')) for a in artifacts]
    return median,raw


def fit_case(f,window,objective,config,h,selection):
    folder=BASE/'models';folder.mkdir(exist_ok=True)
    features=FEATURES[config];result=[]
    for seed in SEEDS:
        path=folder/f'MEAN_{window}_{objective}_{config}_d{h}_s{seed}.joblib'
        if path.exists():
            a=joblib.load(path)
            if a['features']!=features or a['window']!=window or a['objective']!=objective:
                raise ValueError('Mean checkpoint mismatch')
        else:
            progress('mean_fit',window=window,objective=objective,config=config,horizon=h,seed=seed)
            model=fit_mean(f,features,fit_mask(f,window),None,objective,selection['candidate'],seed,selection['trees'][str(h)])
            a=dict(model=model,window=window,objective=objective,features=features,seed=seed,
                   tree_budget=selection['trees'][str(h)],training_rows=int(fit_mask(f,window).sum()))
            save_model(path,a)
        result.append(a)
    return result


def predict_means(artifacts,f):
    seeds=np.array([np.maximum(a['model'].predict(f[a['features']]),0.) for a in artifacts])
    return seeds.mean(0),seeds


def fit_climatology(frame,last_year):
    """Gauge-only valid daily totals, never restrict climatology to NWP-ready rows."""
    z=np.load(VRAIN/'rain_channels.npz')
    days=pd.DatetimeIndex(z['marked_day'])
    clean=np.where(z['valid'][0] & ~z['conflict'],z['raw'][0],np.nan)
    totals=clean.sum(1)
    ids=z['station_ids'].tolist();pos={s:i for i,s in enumerate(ids)}
    rows=[]
    use=(days.year>=2021)&(days.year<=last_year)
    for sid in sorted(frame.station_id.unique()):
        r=totals[:,pos[sid]]
        for j in np.flatnonzero(use & np.isfinite(r)):
            rows.append((sid,int(days[j].month),float(r[j])))
    train=pd.DataFrame(rows,columns=['station_id','month','y'])
    priors={m:s.y.to_numpy() for m,s in train.groupby('month')};by={}
    for (sid,m),s in train.groupby(['station_id','month']):
        values=s.y.to_numpy();prior=priors[m];n=len(values)
        both=np.r_[values,prior];weight=np.r_[np.ones(n),np.full(len(prior),20/len(prior))]
        order=np.argsort(both)
        median=float(both[order][np.searchsorted(np.cumsum(weight[order]),weight.sum()*.5)])
        by[(sid,int(m))]=dict(mean=float((values.sum()+20*prior.mean())/(n+20)),median=median,
            p1=float(((values>=1).sum()+20*(prior>=1).mean())/(n+20)),
            p50=float(((values>=50).sum()+20*(prior>=50).mean())/(n+20)))
    return dict(by=by,first_year=2021,last_year=last_year,valid_gauge_days=len(train))


def predict_climatology(artifact,frame):
    month=frame.target_end_utc.dt.tz_convert('Asia/Ho_Chi_Minh').dt.month
    return pd.DataFrame([artifact['by'][(s,int(m))] for s,m in zip(frame.station_id,month)],index=frame.index)


def mos_x(f):
    return np.c_[f.gfs_rain_mm.to_numpy(),f.sin_doy.to_numpy(),f.cos_doy.to_numpy()]


def fit_mos(f,window):
    mask=fit_mask(f,window);x=mos_x(f)[mask];y=f.loc[mask,'y_mm'].to_numpy()
    median=make_pipeline(StandardScaler(),QuantileRegressor(quantile=.5,alpha=.01,solver='highs')).fit(x,y)
    mean=make_pipeline(StandardScaler(),Ridge(alpha=10.)).fit(x,y)
    def binary(mask,labels):
        if len(np.unique(labels))<2:
            return ConstantBinary(labels)
        return make_pipeline(StandardScaler(),LogisticRegression(C=1.,max_iter=1000)).fit(x[mask],labels)
    wet=binary(np.ones(len(y),bool),(y>=1).astype(int))
    conditional=binary(y>=1,(y[y>=1]>=50).astype(int))
    return dict(mean=mean,median=median,wet=wet,conditional=conditional,window=window,training_rows=len(y))


def predict_mos(a,f):
    x=mos_x(f)
    return {k:np.maximum(a[k].predict(x),0.) for k in ('mean','median')} | {
        'wet':a['wet'].predict_proba(x)[:,1],'conditional':a['conditional'].predict_proba(x)[:,1]}
