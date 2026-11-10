"""Freeze the 57-station expansion using the original train-only criteria.

Keeps the 20-station experiment and every source cache byte intact. Availability
for the wider 79-station candidate cohort is descriptive, not a score filter.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
import numpy as np

from src.gfs_experiment import SOURCE_NAME,experiment_paths
from src.gfs_station_dataset import gauge_history
from src.station_forecast_data import target_splits

NAME='gfs_station_57_2026_11_10'


def availability_inventory(source):
    inventory=pd.read_csv(source.base/'station_terrain_private.csv',dtype={'legacy_id':str})
    z=np.load(ROOT/'data/operational/vrain_2026_11_09/freeze_work/station_matrices.npz')
    hourly=np.where(z['valid'],z['rain'],np.nan).reshape(-1,82)
    daily=hourly.reshape(-1,24,82).sum(1);days=pd.DatetimeIndex(z['marked_day'])
    order={sid:i for i,sid in enumerate(z['station_ids'])}
    counts={sid:{fold:0 for fold in ['train','cal','dev']} for sid in inventory.canonical_id}
    for date in pd.date_range('2021-01-08','2024-12-28',freq='7D'):
        fold=target_splits(pd.DatetimeIndex([date.tz_localize('UTC')+pd.Timedelta(hours=12)]),72)[0]
        if fold=='unused':continue
        j=days.get_loc(date)
        for row in inventory.itertuples():
            si=order[row.legacy_id]
            if np.isfinite(list(gauge_history(hourly,daily,j,si).values())+daily[j+1:j+4,si].tolist()).all():
                counts[row.canonical_id][fold]+=1
    calculated=inventory.merge(pd.DataFrame.from_dict(counts,orient='index').rename_axis('canonical_id').reset_index(),on='canonical_id')
    cache=source.base/'station_expansion_eligibility_private.csv'
    if cache.exists():
        previous=pd.read_csv(cache,dtype={'legacy_id':str})
        old=previous.set_index('canonical_id');new=calculated.set_index('canonical_id')
        if not old[['train','cal','dev']].equals(new[['train','cal','dev']]):
            raise ValueError('Availability cache no longer matches the frozen source')
        return previous
    calculated.to_csv(cache,index=False)
    return pd.read_csv(cache,dtype={'legacy_id':str})


def main():
    paths=experiment_paths(ROOT,NAME)
    source=experiment_paths(ROOT,SOURCE_NAME)
    inventory=availability_inventory(source)
    # Identical train-quality criteria to the pilot, now include every eligible
    # station instead of choosing a geographic subset of twenty.
    core=inventory[(inventory.complete_train_days>=365)&(inventory.wet_train_days_ge1>=30)].sort_values('canonical_id')
    old=pd.read_csv(source.base/'pilot_stations_private.csv').canonical_id
    if len(core)!=57 or not set(old)<=set(core.canonical_id):
        raise ValueError('Expected stable train-only 57-station superset')
    if not core.train.gt(0).all():raise ValueError('Expanded cohort has unseen train station')
    paths.base.mkdir(parents=True,exist_ok=True);paths.public.mkdir(parents=True,exist_ok=True)
    cohort=paths.base/'pilot_stations_private.csv'
    # Match the original input schema; keep per-fold availability in a separate
    # private audit so it cannot become an accidental station feature.
    columns=pd.read_csv(source.base/'pilot_stations_private.csv',nrows=0).columns
    core=core[columns]
    content=core.to_csv(index=False).encode()
    if any((paths.base/'models').glob('*.joblib')) and (not cohort.exists() or cohort.read_bytes()!=content):
        raise ValueError('Expanded cohort already fitted: use a new experiment version')
    cohort.write_bytes(content)
    protocol=json.loads((source.public/'protocol.json').read_text())
    protocol.update(version='gfs_station_57_v1',parent_experiment=SOURCE_NAME,
        expansion_authorized_date='2026-11-10',selected_stations=57,
        station_selection='all stations meeting original train2021--2022 >=365 complete days and >=30 days >=1mm; no cal/dev score filtering',
        station_manifest_sha256=hashlib.sha256(content).hexdigest(),
        source_cache_shared_from=SOURCE_NAME,extra_GFS_download_required=False,
        purpose='expand station coverage while holding date cadence, features, folds and model settings fixed',
        comparative_design='report all57, original20 matched station/issue rows, and additional37 separately',
        dataset_cadence_changed=False,all_79_stations_trained=False,
        min_selected_complete_train_days=int(core.complete_train_days.min()),
        max_selected_complete_train_days=int(core.complete_train_days.max()))
    path=paths.public/'protocol.json'
    if any((paths.base/'models').glob('*.joblib')) and path.exists() and json.loads(path.read_text())!=protocol:
        raise ValueError('Expanded protocol is frozen')
    path.write_text(json.dumps(protocol,indent=2)+'\n')
    known=inventory.train.gt(0)
    report=dict(status='cohort_frozen',source_stations=82,train_quality_eligible=57,
        initial_pilot=20,added_stations=37,broader_stations_with_train_windows=int(known.sum()),
        broader_short_history_stations=int(known.sum()-len(core)),no_train_history_stations=int((~known).sum()),
        modern_only_without_legacy_history=4,
        selected_train_day_range=[int(core.complete_train_days.min()),int(core.complete_train_days.max())],
        min_train_weekly_windows=int(inventory.loc[inventory.canonical_id.isin(core.canonical_id),'train'].min()),
        stations_below_30_train_weekly_windows=int((inventory.loc[inventory.canonical_id.isin(core.canonical_id),'train']<30).sum()),
        selected_elevation_proxy_range_m=[float(core.dem_elev_m.min()),float(core.dem_elev_m.max())],
        complete_station_issue_counts_57={fold:int(inventory.loc[inventory.canonical_id.isin(core.canonical_id),fold].sum()) for fold in ['train','cal','dev']},
        complete_station_issue_counts_79={fold:int(inventory.loc[known,fold].sum()) for fold in ['train','cal','dev']},
        selection_used_only_train_and_static_metadata=True,models_unchanged=True,cadence_days=7,
        original_pilot_preserved=True,test2025_read=False)
    (paths.public/'cohort_expansion_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
