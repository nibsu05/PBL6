"""Compare network expansions on exactly the original station/time examples."""
import numpy as np

from src.gfs_station_dataset import FEATURES

KEYS=['station_id','issue_utc','horizon']


def match_original_examples(previous,current,original_ids):
    old=previous[previous.station_id.isin(original_ids)].copy()
    new=current[current.station_id.isin(original_ids)].copy()
    if old.duplicated(KEYS).any() or new.duplicated(KEYS).any():
        raise ValueError('Duplicate station/issue/horizon in comparison')
    if set(map(tuple,old[KEYS].to_numpy()))!=set(map(tuple,new[KEYS].to_numpy())):
        raise ValueError('Original cohort/time coverage changed; direct comparison is invalid')
    paired=old.merge(new,on=KEYS,suffixes=('_20','_expanded'),validate='one_to_one')
    for name in ['y_mm']+FEATURES['A3']:
        if not np.allclose(paired[name+'_20'],paired[name+'_expanded'],rtol=1e-10,atol=1e-10,equal_nan=False):
            raise ValueError(f'Matched labels/input changed: {name}')
    if not paired.split_20.equals(paired.split_expanded):
        raise ValueError('Chronological folds differ')
    return paired
