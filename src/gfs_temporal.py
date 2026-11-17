"""A separate, versioned temporal-GFS experiment; never changes frozen studies."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from src.gfs_daily import FEATURES, RAW_MET, HISTORY
from src.gfs_station import MET_FIELDS, accumulated_hours, rainfall_windows

ROOT = Path(__file__).resolve().parents[1]
NAME = 'gfs_temporal_2026_11_17'
BASE = ROOT / 'data/operational' / NAME
PUBLIC = ROOT / 'reports' / NAME
SOURCE = ROOT / 'data/processed/station_update_2026_11_16/PBL6_GFS_VRAIN_NGAY_2021_2026.parquet'
OLD = ROOT / 'data/operational/gfs_station_daily_v2_2026_11_10'
UPDATE = ROOT / 'data/operational/vrain_update_2026_11_16/gfs'
RAIN_LEADS = tuple(range(12, 85, 6))
MET_LEADS = (18,24,30,42,48,54,66,72,78)
NEW_RAIN = tuple(x for x in RAIN_LEADS if x not in (12,36,60,84))
NEW_MET = tuple(x for x in MET_LEADS if x not in (24,48,72))
RAIN_FEATURES = [f'gfs_rain6h_{k}_mm' for k in range(1,5)] + [
    'gfs_rain6h_max_mm','gfs_rain6h_max_fraction','gfs_rain_centroid','gfs_rain_first_half_fraction']
MET_FEATURES = [f'{c}_{s}' for c in RAW_MET for s in ('sample_mean','sample_range','late_minus_early')]
CATALOG = dict(T0=FEATURES['N3'], T1=FEATURES['N3']+RAIN_FEATURES,
               T2=FEATURES['N3']+MET_FEATURES, T3=FEATURES['N3']+RAIN_FEATURES+MET_FEATURES)
SEEDS = (17,29,43)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()

def write_json(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    tmp.replace(path)

def protocol():
    return dict(version=NAME,task='three separate next-24h station totals, issued daily at 19h Vietnam',
        user_authorization='2026-11-17: improve short range; defer Bi-LSTM',station_count=57,
        cohort='unchanged training-qualified cohort; no station selected by later performance',
        source_dataset_sha256=sha(SOURCE),cohort_sha256=sha(OLD/'cohort_private.csv'),
        input_source='same GFS 00UTC cycle as baseline, no target-period ERA5 or observations',
        rain_cumulative_leads=list(RAIN_LEADS),met_instant_leads=list(MET_LEADS),
        met_summary_note='three discrete instantaneous forecast samples, NOT the full-day atmospheric mean',
        forecast_grid_degrees=.25,station_sampling='strict bilinear, same four native nodes as old study',
        issue_offset_from_init_hours=12,gfs_release_delay_assumed_hours=8,gauge_delay_hours=1,
        actual_historical_source_latency_proven=False,
        training='2021-2022 only',calibration='2023 only, quarter cross-fit for cutoffs',
        development='2024, already explored',retrospective='2025 and observed 2026 already scored in prior study; NOT an untouched test',
        prospective='only observations after a future model freeze can provide a new untouched evaluation',
        source_policy='same API within history and three targets; legacy/modern evaluated separately; continuity unconfirmed',
        features=CATALOG,feature_counts={k:len(v) for k,v in CATALOG.items()},
        common_mask='identical complete three-horizon station/issue packs for every configuration and baseline',
        known_source_exclusions=['20210202','20221130'],
        new_source_failure_policy='retry uniformly, disclose failures, common-mask exclusion for every model; never fill from labels',
        tree_models=['T0','T1','T2','T3'],gru_models=['T0','T3','LINEAR23'],seeds=list(SEEDS),
        training_budget='reuse per-head/per-horizon hyperparameters and iteration counts selected by old train-only CV, no new search',
        gru=dict(hidden=16,head=24,epochs=17,lr=.001,batch_size=256,
                 linear_control='23 fixed random linear combinations of original T0 meteorology/terrain, scaled on train only',
                 linear_projection_seed=20261117),
        primary_comparisons=[['LGB_T1','LGB_T0'],['LGB_T2','LGB_T0'],['LGB_T3','LGB_T0'],['GRU_T3','GRU_LINEAR23']],
        primary_metric='station-macro RMSE of conditional-mean head, per horizon',
        secondary_metrics=['median-head MAE','mean Bias','BS/BSS 1mm and50mm','CSI/POD/FAR','rain-bin error','monthly error'],
        uncertainty=dict(block_days=14,draws=5000,seed=1701,family_size=12,
                         correction='Bonferroni simultaneous intervals + centered bootstrap p/Holm within each evaluation set',
                         interpretation='exploratory after earlier 2025/2026 inspection; corrections do not restore untouched-test status'),
        label_qc='no score-dependent label removal; neighbor/spike flags diagnostic only; retain all old scores',
        baselines=['ZERO','CLIM','PERSISTENCE','GFS','MOS'],
        hypothesis='intra-day forecast evolution may add information beyond a daily total and one midpoint; improvement not guaranteed')

def load_protocol():
    p=json.loads((PUBLIC/'protocol.json').read_text(encoding='utf-8'))
    lock=json.loads((BASE/'protocol_lock.json').read_text())
    if sha(PUBLIC/'protocol.json')!=lock['sha256']:raise ValueError('Temporal protocol changed')
    if sha(SOURCE)!=p['source_dataset_sha256'] or sha(OLD/'cohort_private.csv')!=p['cohort_sha256']:raise ValueError('Frozen source or cohort changed')
    return p

def select_records(records, lead):
    chosen={}
    if lead in NEW_RAIN:
        matches=[r for r in records if r.variable=='APCP' and r.level=='surface' and accumulated_hours(r.description)==(0,lead)]
        if len(matches)!=1:raise ValueError(f'Expected cumulative APCP 0--{lead}, found {len(matches)}')
        chosen['rain_cumulative']=matches[0]
    if lead in NEW_MET:
        for name,(variable,level) in MET_FIELDS.items():
            matches=[r for r in records if r.variable==variable and r.level==level and r.description==f'{lead} hour fcst']
            if len(matches)!=1:raise ValueError(f'Ambiguous/missing {name} +{lead}')
            chosen[name]=matches[0]
    if not chosen or any(r.stop is None for r in chosen.values()):raise ValueError('Unsupported or open-ended request')
    return chosen

def temporal_summaries(cumulative, quantums, met):
    """Input [13,station], [13], [9,station,5]; output [3,station,23]."""
    if cumulative.shape[0]!=13 or met.shape!=(9,cumulative.shape[1],5):raise ValueError('Temporal source shape mismatch')
    six,clipped=rainfall_windows(cumulative,quantums)
    six=six.reshape(3,4,-1).transpose(0,2,1)
    total=six.sum(-1);den=np.where(total>0,total,1)
    rain=np.concatenate([six,six.max(-1)[...,None],(six.max(-1)/den)[...,None],
        ((six*np.array([.125,.375,.625,.875])).sum(-1)/den)[...,None],
        (six[...,:2].sum(-1)/den)[...,None]],-1)
    # Original met order: RH,T,u,v,PWAT. Feature order: T,RH,u,v,PWAT.
    states=met.reshape(3,3,-1,5).transpose(0,2,1,3)[...,[1,0,2,3,4]].astype(float)
    states[...,0]-=273.15
    weather=np.stack([states.mean(2),np.ptp(states,axis=2),states[:,:,2]-states[:,:,0]],-1).reshape(3,-1,15)
    result=np.concatenate([rain,weather],-1).astype('float32')
    if not np.isfinite(result).all():raise ValueError('Nonfinite temporal features')
    return result,clipped

def eligible_source():
    load_protocol()
    f=pd.read_parquet(SOURCE)
    f=f[f.in_frozen_57_cohort & f.sample_ready & f.recommended_sample & f.split.ne('boundary')].copy()
    # No joining, averaging or deduplicating across the two API channels.
    f=f.sort_values(['issue_utc','station_id','horizon']).reset_index(drop=True)
    if f.duplicated(['issue_utc','station_id','horizon']).any():raise ValueError('Duplicate recommended sample')
    sizes=f.groupby(['issue_utc','station_id','gauge_namespace'],dropna=False).size()
    if not sizes.eq(3).all():raise ValueError('Source has incomplete/mixed-API horizon packs')
    return f
