from pathlib import Path
import unittest
from unittest.mock import patch
import pandas as pd

from src.gfs_experiment import SOURCE_NAME,experiment_paths
from src.gfs_cohort_comparison import match_original_examples
from src.gfs_station_dataset import FEATURES


def example():
    f=pd.DataFrame(dict(station_id=['S1','S2'],issue_utc=pd.to_datetime(['2024-01-01','2024-01-01'],utc=True),
                        horizon=[1,1],split=['dev','dev'],y_mm=[1.,2.],A2=[1.,3.]))
    for name in FEATURES['A3']:f[name]=1.
    return f


class ExpansionTests(unittest.TestCase):
    def test_experiment_paths_preserve_source_and_separate_outputs(self):
        root=Path('workspace')
        old=experiment_paths(root,SOURCE_NAME);new=experiment_paths(root,'gfs_station_57_2026_11_10')
        self.assertEqual(old.source,new.source)
        self.assertNotEqual(old.base,new.base)
        self.assertNotEqual(old.dataset,new.dataset)
        self.assertEqual(old.data,root/'data/processed/gfs_station_pilot')
        with patch.dict('os.environ',{'PBL6_GFS_EXPERIMENT':'gfs_station_57_2026_11_10'}):
            self.assertEqual(experiment_paths(root),new)

    def test_path_traversal_and_absolute_paths_rejected(self):
        for name in ['../gfs_station_x','gfs_station_../../x','D:/gfs_station_x','gfs_station_x/y']:
            with self.assertRaises(ValueError):experiment_paths(Path('.'),name)

    def test_changed_predictions_are_allowed_on_same_examples(self):
        old=example();new=example();new['A2']=[.5,2.5]
        paired=match_original_examples(old,new,['S1','S2'])
        self.assertEqual(len(paired),2)
        self.assertNotEqual(paired.A2_20.iloc[0],paired.A2_expanded.iloc[0])

    def test_missing_original_example_rejected(self):
        with self.assertRaises(ValueError):match_original_examples(example(),example().iloc[:1],['S1','S2'])

    def test_label_or_forecast_input_change_rejected(self):
        for column in ['y_mm','gfs_rain_mm','rain_recent24h_mm']:
            new=example();new.loc[0,column]+=1
            with self.assertRaises(ValueError):match_original_examples(example(),new,['S1','S2'])

    def test_duplicates_and_changed_split_rejected(self):
        with self.assertRaises(ValueError):match_original_examples(example(),pd.concat([example(),example()]),['S1','S2'])
        new=example();new.loc[0,'split']='cal'
        with self.assertRaises(ValueError):match_original_examples(example(),new,['S1','S2'])


if __name__=='__main__':unittest.main()
