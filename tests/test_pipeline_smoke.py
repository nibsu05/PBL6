"""Kiểm tra các ranh giới dễ gây sai lệch thời gian trong pipeline."""

from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from src.dataset_prep import prepare_datasets
from src.event_sampling import build_event_sampled_loader
from src.feature_engineering import engineer_features
from src.train_bilstm import TrainingConfig, predict, train_bilstm, weighted_mse_loss
from src.visualize_and_evaluate import evaluate_and_visualize
from run_surface_baseline import _select_variant, _write_json


class PipelineSmokeTest(unittest.TestCase):
    def test_surface_selection_uses_validation_only_and_json_is_strict(self) -> None:
        results = {
            "standard": {
                "validation": {"metrics": {"RMSE": 1.0, "MAE": 0.4},
                               "detection": {"F1": 0.3}, "heavy_count": 10,
                               "heavy_mae": 4.0},
                "metrics": {"RMSE": 99.0},
            },
            "event_balanced": {
                "validation": {"metrics": {"RMSE": 1.05, "MAE": 0.42},
                               "detection": {"F1": 0.1}, "heavy_count": 10,
                               "heavy_mae": 5.0},
                "metrics": {"RMSE": 0.1},
            },
        }
        self.assertEqual(_select_variant(results)[0], "standard")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "metric.json"
            _write_json(path, {"undefined_cc": float("nan"), "valid": np.float32(1.5)})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")),
                             {"undefined_cc": None, "valid": 1.5})
            self.assertNotIn("NaN", path.read_text(encoding="utf-8"))

    def test_weighted_mse_penalizes_heavy_rain(self) -> None:
        prediction = torch.tensor([[0.0, 0.0]])
        actual = torch.tensor([[1.0, 6.0]])
        self.assertAlmostEqual(weighted_mse_loss(prediction, actual).item(), 72.5)

    def test_gap_split_and_outputs(self) -> None:
        hours = pd.date_range("2020-01-01", periods=360, freq="h", tz="Asia/Ho_Chi_Minh")
        t = np.arange(len(hours))
        frame = pd.DataFrame({
            "datetime": hours,
            "temperature_2m": 27 + 2 * np.sin(t / 24),
            "relative_humidity_2m": 75 + 5 * np.cos(t / 24),
            "surface_pressure": 1010 + np.cos(t / 24),
            "wind_speed_10m": 4 + 0.5 * np.sin(t / 6),
            "wind_direction_10m": np.full(len(t), 90.0),
            "precipitation": np.where(t % 47 == 0, 8.0, np.where(t % 11 == 0, 0.5, 0.0)),
            "sea_surface_temperature": np.full(len(t), 28.0),
            "u_850": np.full(len(t), 3.0),
            "v_850": np.full(len(t), 4.0),
            "specific_humidity_850": np.full(len(t), 0.012),
            "oni_anom": np.full(len(t), 0.7),
        })
        frame = frame.drop(index=[150, 151, 152]).reset_index(drop=True)
        engineered = engineer_features(frame)
        self.assertEqual(int(engineered["temperature_2m"].isna().sum()), 3)
        self.assertEqual(engineered.loc[150, "precip_lag_1h"], 0.0)
        self.assertTrue(np.isnan(engineered.loc[151, "precip_lag_1h"]))

        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            prepared = prepare_datasets(
                engineered, batch_size=32, scaler_path=temp / "scaler.pkl",
            )
            self.assertNotIn("oni", prepared.feature_cols)
            self.assertGreater(prepared.diagnostics["windows_with_missing_value"], 0)
            self.assertTrue((temp / "scaler.pkl").exists())
            for dataset in (prepared.train_dataset, prepared.val_dataset, prepared.test_dataset):
                self.assertGreater(len(dataset), 0)
                for start in dataset.starts:
                    segment = dataset.timestamps[start:start + 30]
                    self.assertTrue((np.diff(segment.as_unit("ns").asi8) == 3_600_000_000_000).all())
            self.assertTrue(
                (prepared.test_dataset.target_datetimes.iloc[:, 0]
                 >= prepared.split_boundaries["val_end"]).all()
            )
            sampled_loader, sampling_info = build_event_sampled_loader(
                prepared.train_dataset, batch_size=32, target_draw_fraction=0.25,
            )
            self.assertGreater(sampling_info.heavy_events, 0)
            self.assertEqual(len(list(iter(sampled_loader.sampler))), len(prepared.train_dataset))

            training = train_bilstm(
                prepared.train_loader, prepared.val_loader, None,
                feature_cols=prepared.feature_cols,
                checkpoint_path=temp / "best.pth",
                config=TrainingConfig(max_epochs=2, patience=2, device="cpu"),
            )
            self.assertIsNone(training.y_true)
            self.assertIsNone(training.y_pred)
            y_true, y_pred = predict(training.model, prepared.test_loader, training.device)
            self.assertEqual(y_true.shape, y_pred.shape)
            self.assertEqual(y_true.shape[1], 6)
            self.assertTrue((temp / "best.pth").exists())
            metrics = evaluate_and_visualize(
                engineered, training.history, y_true, y_pred,
                prepared.test_dataset.target_datetimes, output_dir=temp / "plots",
            )
            self.assertIn("CC", metrics)
            for number in range(1, 5):
                self.assertEqual(len(list((temp / "plots").glob(f"plot{number}_*.png"))), 1)


if __name__ == "__main__":
    unittest.main()
