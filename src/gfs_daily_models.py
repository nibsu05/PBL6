"""Train-only CV estimators and station/month references for daily-v2."""
from __future__ import annotations
import numpy as np
import pandas as pd
import lightgbm as lgb
from src.gfs_daily import VRAIN,BASE,Platt


class ConstantBinary:
    def __init__(self, labels):
        self.value=float((np.sum(labels)+.5)/(len(labels)+1));self.best_iteration_=1
    def predict_proba(self, x):
        p=np.full(len(x),self.value);return np.c_[1-p,p]


def tree_parameters(candidate, seed, trees):
    return dict(n_estimators=int(trees),learning_rate=.04,num_leaves=candidate['num_leaves'],
        max_depth=candidate['max_depth'],min_child_samples=candidate['min_child_samples'],
        reg_lambda=candidate['reg_lambda'],subsample=.9,subsample_freq=1,colsample_bytree=.9,
        random_state=int(seed),n_jobs=4,verbosity=-1,deterministic=True,force_col_wise=True,metric='None')


def fit_tree(frame, features, train, valid, head, candidate, seed=17, trees=600):
    train=np.asarray(train,bool).copy();valid=None if valid is None else np.asarray(valid,bool).copy()
    y=frame.y_mm.to_numpy()
    if head=='conditional':
        train &= y>=1
        if valid is not None:valid &= y>=1
    if head in ('wet','conditional'):
        labels=(y >= (1 if head=='wet' else 50)).astype(int)
        if len(np.unique(labels[train]))<2:return ConstantBinary(labels[train])
        estimator=lgb.LGBMClassifier(objective='binary',**tree_parameters(candidate,seed,trees));metric='binary_logloss'
    elif head=='mean':
        labels=y;metric='rmse'
        estimator=lgb.LGBMRegressor(objective='tweedie',tweedie_variance_power=1.5,**tree_parameters(candidate,seed,trees))
    elif head=='median':
        labels=y;metric='l1'
        estimator=lgb.LGBMRegressor(objective='quantile',alpha=.5,**tree_parameters(candidate,seed,trees))
    else:raise ValueError('Unknown prediction functional')
    kwargs=dict(categorical_feature=['station_code'])
    if valid is not None and valid.any():
        kwargs.update(eval_set=[(frame.loc[valid,features],labels[valid])],eval_metric=metric,
            callbacks=[lgb.early_stopping(50,first_metric_only=True,verbose=False)])
    estimator.fit(frame.loc[train,features],labels[train],**kwargs)
    return estimator


def predict_tree(model, features, frame, head):
    if head in ('wet','conditional'):return model.predict_proba(frame[features])[:,1]
    return np.maximum(model.predict(frame[features]),0.)


def best_round(model, fallback):
    return int(getattr(model,'best_iteration_',0) or fallback)


def climatology(frame):
    """All valid 2021--2022 gauge days; 20-observation monthly shrinkage."""
    z=np.load(VRAIN/'freeze_work/station_matrices.npz')
    rain=np.where(z['valid'],z['rain'],np.nan).sum(1);days=pd.DatetimeIndex(z['marked_day'])
    registry=pd.read_csv(BASE/'cohort_private.csv',dtype={'legacy_id':str});order={s:i for i,s in enumerate(z['station_ids'])}
    rows=[]
    for station in registry.itertuples():
        r=rain[:,order[station.legacy_id]];good=(days.year<=2022)&np.isfinite(r)
        rows.extend((station.canonical_id,int(days[j].month),float(r[j])) for j in np.flatnonzero(good))
    train=pd.DataFrame(rows,columns=['station_id','month','y'])
    prior={m:g.y.to_numpy() for m,g in train.groupby('month')};by={}
    for (sid,m),g in train.groupby(['station_id','month']):
        values=g.y.to_numpy();global_values=prior[m];n=len(values)
        both=np.r_[values,global_values];weights=np.r_[np.ones(n),np.full(len(global_values),20/len(global_values))]
        ordered=np.argsort(both);median=float(both[ordered][np.searchsorted(np.cumsum(weights[ordered]),weights.sum()*.5)])
        by[(sid,m)]=dict(mean=float((values.sum()+20*global_values.mean())/(n+20)),median=median,
            p1=float(((values>=1).sum()+20*(global_values>=1).mean())/(n+20)),
            p50=float(((values>=50).sum()+20*(global_values>=50).mean())/(n+20)))
    months=frame.target_end_utc.dt.tz_convert('Asia/Ho_Chi_Minh').dt.month
    records=[by[(sid,int(m))] for sid,m in zip(frame.station_id,months)]
    return pd.DataFrame(records,index=frame.index)
