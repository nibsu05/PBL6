"""Hợp đồng mô hình v2: ngưỡng >=, tensor ba nhánh, backward và độ trễ quan trắc."""
import unittest
import torch
from src.bilstm_v2 import BiLSTMV2, aggregate_targets, pilot_loss


class BiLSTMV2Test(unittest.TestCase):
    def test_aggregate_event_includes_exact_threshold(self):
        y = torch.tensor([[1., 0., 0., 10., 0., 0.]])
        expected = torch.tensor([[1., 0., 0., 1., 1., 0., 1., 1., 0.]])
        torch.testing.assert_close(aggregate_targets(y), expected)

    def test_three_inputs_contribute_to_finite_backward(self):
        torch.manual_seed(1)
        model = BiLSTMV2(15, 10, hidden_dim=8)
        past = torch.randn(4, 24, 15, requires_grad=True)
        future = torch.randn(4, 6, 10, requires_grad=True)
        static = torch.randn(4, 8, requires_grad=True)
        amount, logits = model(past, future, static)
        self.assertEqual(amount.shape, (4, 6))
        self.assertEqual(logits.shape, (4, 9))
        self.assertTrue((amount >= 0).all())
        loss = pilot_loss(amount, logits, torch.rand(4, 6) * 5)
        loss.backward()
        for tensor in (past, future, static):
            self.assertTrue(torch.isfinite(tensor.grad).all())
            self.assertGreater(tensor.grad.abs().sum().item(), 0)


if __name__ == "__main__":
    unittest.main()
