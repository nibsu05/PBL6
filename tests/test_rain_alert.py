"""Kiểm tra hai đầu ra và việc chọn ngưỡng trên dữ liệu giả."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd
import torch

from run_rain_alert_experiment import select_threshold
from src.rain_alert_model import RainAlertBiLSTM, RainAlertConfig, rain_alert_loss


class RainAlertTest(unittest.TestCase):
    def test_both_heads_receive_gradient(self) -> None:
        model = RainAlertBiLSTM(input_dim=3, output_dim=2)
        amount, logit = model(torch.randn(4, 24, 3))
        target = torch.tensor([[0.0, 8.0], [0.2, 0.0], [6.0, 0.0], [0.0, 0.0]])
        loss, _ = rain_alert_loss(amount, logit, target, RainAlertConfig())
        self.assertEqual(tuple(amount.shape), (4, 2))
        self.assertTrue(bool((amount >= 0).all()))
        loss.backward()
        self.assertGreater(float(model.amount_head.weight.grad.abs().sum()), 0)
        self.assertGreater(float(model.heavy_head.weight.grad.abs().sum()), 0)

    def test_validation_threshold_uses_event_f1(self) -> None:
        hours = pd.DataFrame({"h1": pd.date_range("2025-01-01", periods=8, freq="h", tz="UTC")})
        actual = np.zeros((8, 1))
        actual[2, 0] = 9
        probabilities = np.array([[0.1], [0.2], [0.8], [0.1], [0.1], [0.1], [0.1], [0.1]])
        threshold, sweep = select_threshold(actual, probabilities, hours)
        self.assertEqual(threshold, 0.8)
        self.assertEqual(float(sweep.loc[sweep.probability_threshold == 0.8, "event_F1"].iloc[0]), 1)


if __name__ == "__main__":
    unittest.main()
