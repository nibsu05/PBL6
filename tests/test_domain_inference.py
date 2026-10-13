import unittest
import numpy as np
from src.domain_inference import calibrated_probability, ArchivePredictor
class InferenceCalibrationTest(unittest.TestCase):
    def test_platt_and_monotonic_thresholds(self):
        logits=np.zeros((1,9),dtype=np.float32)
        params=[dict(coef=2.,intercept=0.),dict(constant=.8),dict(constant=.1)]*3
        actual=calibrated_probability(logits,params)
        np.testing.assert_allclose(actual[0],[[.5,.5,.1]]*3)
    def test_test_year_cannot_be_served_by_archive_api(self):
        with self.assertRaisesRegex(ValueError,'test2025'):ArchivePredictor(2025,'DOMAIN')
    def test_constant_fallback_not_logit_sigmoid(self):
        actual=calibrated_probability(np.full((1,9),1000.),[dict(constant=.2)]*9)
        np.testing.assert_allclose(actual,.2)
if __name__=='__main__':unittest.main()