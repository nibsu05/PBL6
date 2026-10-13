"""Đầu mean mm/h với Tweedie p1.5; BCE đầu sự kiện giữ không trọng số lớp."""
import torch
from torch.nn import functional as F
from src.bilstm_v2 import aggregate_targets

def tweedie_deviance(mu,y):
    # D1.5=4*(y/sqrt(mu)+sqrt(mu)-2sqrt(y)); tối ưu mean có điều kiện.
    safe_mu=mu.clamp_min(1e-3)
    dev=4*(y/safe_mu.sqrt()+safe_mu.sqrt()-2*y.clamp_min(0).sqrt())
    return dev.clamp_min(0).mean()

class TweedieJointLoss:
    def __init__(self,train_null_deviance):
        if train_null_deviance<=0:raise ValueError('Scale phải dương từ train')
        self.scale=float(train_null_deviance)
    def __call__(self,amount_mean,logits,y):
        return tweedie_deviance(amount_mean,y)/self.scale+F.binary_cross_entropy_with_logits(logits,aggregate_targets(y))
