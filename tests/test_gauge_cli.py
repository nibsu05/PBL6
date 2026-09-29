"""Kiểm tra đường đi CSV trạm -> chuẩn hóa -> chỉ số, không dùng dữ liệu giả làm kết quả."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


class GaugeCliTest(unittest.TestCase):
    def test_prepare_and_evaluate_cli(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            raw = root / "sample.csv"
            raw.write_text("datetime,precipitation_mm_h\n"
                           "2025-01-01T01:00:00+07:00,0\n"
                           "2025-01-01T02:00:00+07:00,8\n", encoding="utf-8")
            normalized = root / "normalized"
            subprocess.run([
                sys.executable, str(ROOT / "prepare_gauge_observations.py"),
                "--input", str(raw), "--station-name", "Synthetic station",
                "--lat", "16.05", "--lon", "108.20", "--source-name", "test fixture",
                "--source-timezone", "Asia/Ho_Chi_Minh", "--timestamp-means", "end",
                "--accumulation-hours", "1", "--output-dir", str(normalized),
            ], check=True, capture_output=True, text=True)
            hours = pd.date_range("2025-01-01 01:00", periods=2, freq="h",
                                  tz="Asia/Ho_Chi_Minh")
            predictions = pd.DataFrame({
                "last_input_datetime": hours - pd.Timedelta(hours=1),
                "valid_datetime": hours,
                "horizon_h": [1, 1],
                "dual_amount_mm": [0, 7],
                "dual_heavy_probability": [0.1, 0.8],
                "standard_amount_mm": [0, 6],
                "persistence_mm": [0, 0],
            })
            predictions.to_parquet(root / "predictions.parquet", index=False)
            (root / "model.json").write_text(
                json.dumps({"selected_probability_threshold": 0.4}), encoding="utf-8"
            )
            out = root / "evaluation"
            subprocess.run([
                sys.executable, str(ROOT / "evaluate_gauge_predictions.py"),
                "--observations", str(normalized / "observations.csv"),
                "--station-metadata", str(normalized / "station_metadata.json"),
                "--predictions", str(root / "predictions.parquet"),
                "--model-summary", str(root / "model.json"),
                "--output-dir", str(out),
            ], check=True, capture_output=True, text=True)
            summary = json.loads((out / "evaluation_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["matched_pairs"], 2)
            self.assertEqual(summary["status"], "evaluated")
            metrics = pd.read_csv(out / "metrics_by_horizon.csv")
            self.assertEqual(int(metrics.loc[metrics.model == "dual_head", "TP"].iloc[0]), 1)


if __name__ == "__main__":
    unittest.main()
