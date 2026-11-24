"""Independently replay times, hourly sources, labels and frozen-period features."""
from pathlib import Path
import json,sqlite3,gzip,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from src.station_archive_update import BASE,OUT,PUBLIC,OLD,LAST,sha,write_json
from src.gfs_daily import FEATURES,RECENT


def main():
    summary=json.loads((PUBLIC/'dataset_summary.json').read_text(encoding='utf8'))
    for file in ('hourly','daily'):assert sha(OUT/summary[file]['file'])==summary[file]['sha256']
    preserved=json.loads((BASE/'preserved_hashes.json').read_text(encoding='utf8'))
    for p,digest in preserved.items():assert sha(ROOT/p)==digest,('Prior artifact changed',p)
    assert not (ROOT/'reports/short_range_three_models_2026_10_21/PBL6_SO_SANH_3_MO_HINH.pptx').exists()
    z=np.load(BASE/'rain_channels.npz');raw=z['raw'];valid=z['valid'];conflict=z['conflict']
    days=pd.DatetimeIndex(z['marked_day']);ids=z['station_ids'].tolist();pos={s:i for i,s in enumerate(ids)}
    assert len(ids)==86 and days[0]==pd.Timestamp('2021-01-01') and days[-1]==pd.Timestamp(LAST)
    clean=np.where(valid&~conflict[None,...],raw,np.nan)
    day_amounts=clean.sum(2);flat=clean.reshape(2,-1,len(ids))
    registry=pd.read_csv(BASE/'station_registry_private.csv',dtype={'legacy_id':str,'modern_id':str})
    aliases={c:dict(zip(registry.loc[registry[c+'_id'].notna(),c+'_id'],registry.loc[registry[c+'_id'].notna(),'canonical_id'])) for c in ('legacy','modern')}
    # Select saved source responses independently of the matrix builder.
    rng=np.random.default_rng(16112026);probes=['2025-01-01','2025-12-31','2026-01-01',LAST]
    probes+=pd.DatetimeIndex(rng.choice(pd.date_range('2025-01-01',LAST).values,size=24,replace=False)).strftime('%Y-%m-%d').tolist()
    raw_cells=0
    for channel_index,channel in enumerate(('legacy','modern')):
        for day in probes:
            payload=json.loads(gzip.decompress((BASE/'raw'/channel/day[:4]/(day+'.json.gz')).read_bytes()))
            expected=np.full((24,86),np.nan,dtype=np.float32);marked=pd.Timestamp(day)
            for row in payload['stats']:
                label=row['timePoint']
                if ':' not in label:continue
                clock,date=label.split();hour,minute=map(int,clock.split(':'));dd,month=map(int,date.split('/'))
                candidates=[]
                for year in (marked.year-1,marked.year,marked.year+1):
                    try:candidates.append(pd.Timestamp(year=year,month=month,day=dd,hour=hour,minute=minute))
                    except ValueError:pass
                end=min(candidates,key=lambda t:abs(t-marked));k=int((end-(marked-pd.Timedelta(hours=4)))/pd.Timedelta(hours=1))
                assert 0<=k<24
                for station in row['stations']:
                    value=station['depth']
                    if value=='-':continue
                    expected[k,pos[aliases[channel][str(station['id'])]]]=float(value)
            di=days.get_loc(marked);np.testing.assert_array_equal(expected,raw[channel_index,di]);raw_cells+=expected.size
    # Every hourly row is checked against retained source matrices and source code.
    hourly_rows=0;hour_path=OUT/summary['hourly']['file']
    for table in pq.ParquetFile(hour_path).iter_batches(batch_size=100_000):
        f=table.to_pandas();hourly_rows+=len(f)
        si=f.station_id.astype('string').map(pos).to_numpy(int)
        endpoints=pd.DatetimeIndex(f.period_end_utc)
        first=(pd.Timestamp('2021-01-01')-pd.Timedelta(hours=4)).tz_localize('Asia/Ho_Chi_Minh').tz_convert('UTC')
        hi=((endpoints-first)/pd.Timedelta(hours=1)).to_numpy(int);di=hi//24;hh=hi%24
        assert (f.period_end_utc-f.period_start_utc).eq(pd.Timedelta(hours=1)).all()
        np.testing.assert_array_equal(f.legacy_rain_raw_mm.to_numpy(),raw[0,di,hh,si])
        np.testing.assert_array_equal(f.modern_rain_raw_mm.to_numpy(),raw[1,di,hh,si])
        cf=conflict[di,hh,si];np.testing.assert_array_equal(f.cross_channel_conflict,cf)
        lv=valid[0,di,hh,si];mv=valid[1,di,hh,si]
        np.testing.assert_array_equal(f.legacy_sum_flag,z['bad_daily_sum'][0,di,si])
        np.testing.assert_array_equal(f.modern_sum_flag,z['bad_daily_sum'][1,di,si])
        np.testing.assert_array_equal(f.legacy_requested,z['queried'][0,di])
        np.testing.assert_array_equal(f.modern_requested,z['queried'][1,di])
        np.testing.assert_array_equal(f.source_marked_day.to_numpy(),days.values[di])
        np.testing.assert_array_equal(f.legacy_rain_qc_mm,np.where(lv,raw[0,di,hh,si],np.nan))
        np.testing.assert_array_equal(f.modern_rain_qc_mm,np.where(mv,raw[1,di,hh,si],np.nan))
        expected_code=np.full(len(f),-1,dtype=np.int8);expected_code[mv]=1;expected_code[lv]=0;expected_code[cf]=3
        np.testing.assert_array_equal(f.gauge_source_code,expected_code)
        expected=np.full(len(f),np.nan,dtype=np.float32)
        expected[expected_code==0]=raw[0,di[expected_code==0],hh[expected_code==0],si[expected_code==0]]
        expected[expected_code==1]=raw[1,di[expected_code==1],hh[expected_code==1],si[expected_code==1]]
        np.testing.assert_array_equal(f.rain_mm,expected)
    assert hourly_rows==summary['hourly']['rows']==len(days)*24*86
    f=pd.read_parquet(OUT/summary['daily']['file'])
    assert len(f)==summary['daily']['rows']
    keys=['issue_utc','station_id','gauge_namespace','horizon']
    assert not f.duplicated(keys).any()
    assert f.groupby(keys[:-1]).horizon.agg(['size','min','max']).eq([3,1,3]).all().all()
    assert f.issue_utc.dt.tz_convert('Asia/Ho_Chi_Minh').dt.hour.eq(19).all()
    assert f.target_end_utc.max()==pd.Timestamp('2026-11-15 19:00',tz='Asia/Ho_Chi_Minh')
    assert (f.target_end_utc-f.target_start_utc).eq(pd.Timedelta(hours=24)).all()
    assert f.observation_cutoff_utc.eq(f.issue_utc-pd.Timedelta(hours=1)).all()
    si=f.station_id.map(pos).to_numpy(int)
    di=days.get_indexer(f.issue_utc.dt.tz_convert('Asia/Ho_Chi_Minh').dt.tz_localize(None).dt.normalize())
    ci=f.gauge_namespace.map({'legacy':0,'modern':1}).to_numpy(int)
    expected_y=day_amounts[ci,di+f.horizon.to_numpy(int),si]
    np.testing.assert_array_equal(f.y_mm.to_numpy(),expected_y)
    # Check histories once per sample (horizon=1); no calls to gauge_history.
    one=f.loc[f.horizon.eq(1)];si=one.station_id.map(pos).to_numpy(int)
    di=days.get_indexer(one.issue_utc.dt.tz_convert('Asia/Ho_Chi_Minh').dt.tz_localize(None).dt.normalize())
    ci=one.gauge_namespace.map({'legacy':0,'modern':1}).to_numpy(int)
    for lag in range(1,8):np.testing.assert_array_equal(one[f'rain_lag_day{lag}_mm'],day_amounts[ci,di-lag,si])
    for delay in (1,3,6):
        last=di*24+23-delay
        for count in (1,6,24):
            expected=flat[ci[:,None],last[:,None]-np.arange(count)[None,:],si[:,None]].sum(1)
            # Reverse summation can cause float32 rounding differences only.
            actual=one[f'rain_recent{count}h_mm_delay{delay}'].to_numpy()
            np.testing.assert_allclose(actual,expected,rtol=1e-6,atol=1e-4,equal_nan=True)
    ready=f.loc[f.sample_ready]
    assert np.isfinite(ready[FEATURES['N5']+['y_mm']].to_numpy(float)).all()
    assert ready.gauge_history_targets_complete.all() and ready.gfs_source_status.eq('verified').all()
    assert not ready.split.eq('boundary').any()
    recommended=f.loc[f.recommended_sample]
    assert not recommended.duplicated(['station_id','issue_utc','horizon']).any()
    assert recommended.sample_ready.all()
    assert not f.loc[f.gauge_namespace.eq('modern'),'continuity_with_legacy_confirmed'].any()
    # Reproduce the old experiment exactly on its original cohort and mask.
    old=pd.read_parquet(ROOT/'data/processed/gfs_station_daily_v2_2026_11_10/dataset.parquet')
    subset=f[f.eligible_frozen_57_legacy & f.split.isin(['train','cal','dev'])]
    compare_keys=['station_id','issue_utc','horizon']
    numeric=FEATURES['N5']+['y_mm']+[f'{n}_delay{d}' for n in RECENT for d in (1,3,6)]
    old=old.sort_values(compare_keys).reset_index(drop=True);subset=subset.sort_values(compare_keys).reset_index(drop=True)
    assert len(old)==len(subset)==218658
    pd.testing.assert_frame_equal(old[compare_keys],subset[compare_keys],check_dtype=False)
    np.testing.assert_allclose(old[numeric],subset[numeric],rtol=1e-12,atol=1e-12,equal_nan=True)
    assert old.split.eq(subset.split).all()
    # Verify reused Vrain compressed bytes against the earlier capture manifests.
    db=sqlite3.connect(BASE/'manifest.sqlite');records=[json.loads(r[0]) for r in db.execute('select record from responses')];db.close()
    reused=0
    for channel in ('legacy','modern'):
        db=sqlite3.connect(OLD/'recent_archive'/channel/'manifest.sqlite')
        old_records={d:json.loads(r) for d,r in db.execute('select day,record from days')};db.close()
        for r in records:
            if r['channel']==channel and r['day'] in old_records:
                assert r['gzip_sha256']==old_records[r['day']]['gzip_sha256'];reused+=1
    # Dataset creation must not produce model artifacts or per-date model scores.
    assert not list(BASE.rglob('*.joblib')) and not list(BASE.rglob('*.pt'))
    public_names={p.suffix for p in PUBLIC.iterdir() if p.is_file()}
    assert not public_names.intersection({'.parquet','.npz','.pdf','.gz'})
    report=dict(status='passed',hourly_rows_checked=hourly_rows,daily_rows_checked=len(f),
        raw_probe_cells_checked=raw_cells,source_responses_probed=2*len(probes),
        history_samples_checked=len(one),ready_rows=len(ready),recommended_rows=len(recommended),
        original_daily_rows_reproduced=len(subset),original_features_labels_match=True,
        reused_response_checksums_verified=reused,previous_artifacts_preserved=len(preserved),
        intervals_checked=True,missing_not_zero=True,conflicting_channels_not_merged=True,
        mixed_namespace_history_targets=False,modern_continuity_confirmed=False,
        training_performed=False,model_evaluation=False,collection_2025_authorized=True,
        datasets={k:summary[k]['sha256'] for k in ('hourly','daily')})
    write_json(PUBLIC/'verification.json',report)
    summary['status']='verified_with_documented_gaps_and_source_transition'
    summary['verification_sha256']=sha(PUBLIC/'verification.json')
    write_json(PUBLIC/'dataset_summary.json',summary)
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
