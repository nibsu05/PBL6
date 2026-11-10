"""Audit source object timestamps and rerun A2 without ambiguous train cycles.

S3 Last-Modified may reflect archive copies, not original dissemination. This
sensitivity is driven only by metadata, never by observed rainfall or scores.
"""
from pathlib import Path
from email.utils import parsedate_to_datetime
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd

from src.gfs_station_dataset import FEATURES,macro_metrics

BASE=ROOT/'data/operational/gfs_station_pilot_2026_11_10'
PUBLIC=ROOT/'reports/gfs_station_pilot_2026_11_10'


def main():
    late=set();records=[];delays=[]
    for path in sorted((BASE/'days').glob('*.json')):
        d=json.loads(path.read_text());init=pd.Timestamp(d['init_utc']);issue=pd.Timestamp(d['issue_utc'])
        after=0
        for m in d['messages']:
            timestamp=pd.Timestamp(parsedate_to_datetime(m['source_last_modified']))
            delays.append(float((timestamp-init)/pd.Timedelta(hours=1)))
            after+=timestamp>issue
        if after:late.add(d['day'])
        records.append(dict(day=d['day'],year=init.year,late_messages=int(after)))
    audit=dict(status='audited',cycles=len(records),messages=len(delays),
        cycles_with_object_modification_after_issue=len(late),
        modified_after_issue_by_cycle_year={str(year):sum(r['late_messages']>0 for r in records if r['year']==year) for year in [2021,2022,2023,2024]},
        last_modified_minus_init_hours_quantiles=np.quantile(delays,[0,.5,.95,1]).tolist(),
        interpretation='Last-Modified can reflect archive recopy; does not prove late original dissemination or reforecast identity',
        actual_original_release_times_proven=False)
    (PUBLIC/'release_timestamp_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    pd.DataFrame(records).to_csv(BASE/'release_dates_private.csv',index=False)
    f=pd.read_parquet(BASE/'predictions_private.parquet')
    ambiguous=f.issue_utc.dt.strftime('%Y%m%d').isin(late)
    if (ambiguous & f.split.ne('train')).any():
        raise ValueError('Ambiguous release timestamps include evaluation; requires explicit protocol review')
    rows=[]
    for h in [1,2,3]:
        s=f[f.horizon.eq(h)];bad=s.issue_utc.dt.strftime('%Y%m%d').isin(late)
        tr=s.split.eq('train')&~bad;cal=s.split.eq('cal')
        names=FEATURES['A2'];predictions=[]
        for seed in [17,29,43]:
            original=joblib.load(BASE/'models'/f'A2_d{h}_seed{seed}.joblib')
            estimator=lgb.LGBMRegressor(**original['amount'].get_params())
            estimator.fit(s.loc[tr,names],s.loc[tr,'y_mm'],categorical_feature=['station_code'],
                eval_set=[(s.loc[cal,names],s.loc[cal,'y_mm'])],eval_metric='l1',
                callbacks=[lgb.early_stopping(40,first_metric_only=True,verbose=False)])
            predictions.append(np.maximum(estimator.predict(s[names]),0))
            joblib.dump(dict(amount=estimator,features=names,excluded_source_dates=sorted(late)),
                BASE/'models'/f'release_sensitivity_A2_d{h}_seed{seed}.joblib',compress=3)
        prediction=np.mean(predictions,axis=0)
        for fold in ['cal','dev']:
            part=s[s.split.eq(fold)];positions=s.split.eq(fold).to_numpy()
            for model,values in [('A2_primary',part.A2.to_numpy()),('A2_omit_ambiguous_train_cycles',prediction[positions]),('GFS',part.GFS.to_numpy())]:
                metric,_=macro_metrics(pd.DataFrame(dict(station_id=part.station_id,y=part.y_mm,pred=values)))
                rows.append(dict(fold=fold,horizon=h,model=model,train_rows_after_omission=int(tr.sum()),**metric))
    pd.DataFrame(rows).to_csv(PUBLIC/'release_sensitivity_metrics.csv',index=False)
    print(json.dumps(audit,indent=2));print(pd.DataFrame(rows).query("fold=='dev'")[['horizon','model','macro_mae']].to_string(index=False))


if __name__=='__main__':main()
