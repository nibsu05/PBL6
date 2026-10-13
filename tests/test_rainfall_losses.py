import unittest
import torch
from src.rainfall_losses import tweedie_deviance,TweedieJointLoss
class RainfallLossTest(unittest.TestCase):
    def test_deviance_zero_at_target_and_finite_at_dry(self):
        y=torch.tensor([0.,.5,20.])
        self.assertTrue(torch.isfinite(tweedie_deviance(y,y)))
        self.assertLess(float(tweedie_deviance(y[1:],y[1:])),1e-5)
    def test_constant_optimum_is_mean_not_median(self):
        mu=torch.tensor(1.,requires_grad=True)
        y=torch.tensor([0.,0.,0.,4.])
        loss=tweedie_deviance(mu.expand_as(y),y);loss.backward()
        self.assertAlmostEqual(float(mu.grad),0.,places=5)
        self.assertLess(float(loss),float(tweedie_deviance(torch.full_like(y,.1),y)))
    def test_joint_loss_has_finite_gradients_for_extreme_sample(self):
        mu=torch.full((2,6),.2,requires_grad=True);logits=torch.zeros((2,9),requires_grad=True)
        y=torch.zeros((2,6));y[1,0]=100.
        loss=TweedieJointLoss(3.)(mu,logits,y);loss.backward()
        self.assertTrue(torch.isfinite(loss))
        self.assertTrue(torch.isfinite(mu.grad).all() and torch.isfinite(logits.grad).all())
if __name__=='__main__':unittest.main()
