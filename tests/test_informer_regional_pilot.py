import numpy as np
import torch
import unittest
from src.informer_regional_pilot import RegionalInformer,RegionalProbAttention


def test_shapes_gradients_and_deterministic_replay():
    torch.set_num_threads(2);torch.manual_seed(42)
    model=RegionalInformer(11,[7,8,9,10]);x=torch.randn(4,28,11);c=torch.randn(4,12,4)
    model.set_scaler({'center':np.zeros(11,dtype='float32'),'scale':np.ones(11,dtype='float32')})
    amount,logits=model(x,c)
    assert amount.shape==(4,3) and logits.shape==(4,3,3) and (amount>0).all()
    (amount.mean()+logits.square().mean()).backward()
    assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
    model.eval();a,b=model(x,c);aa,bb=model(x,c)
    torch.testing.assert_close(a,aa,rtol=0,atol=0);torch.testing.assert_close(b,bb,rtol=0,atol=0)
    copy=RegionalInformer(**model.config);copy.load_state_dict(model.state_dict());copy.eval()
    ca,cb=copy(x,c);torch.testing.assert_close(a,ca);torch.testing.assert_close(b,cb)


def test_sparse_query_count_does_not_select_all_28():
    attention=RegionalProbAttention(False,factor=3);q=torch.randn(2,28,4,8)
    seen=[];original=attention._prob_QK
    def capture(Q,K,sample_k,n_top):seen.append(n_top);return original(Q,K,sample_k,n_top)
    attention._prob_QK=capture
    attention(q,q,q)
    assert seen==[12]


class InformerPilotTests(unittest.TestCase):
    def test_shapes_gradients_replay(self):
        test_shapes_gradients_and_deterministic_replay()

    def test_sparse_queries(self):
        test_sparse_query_count_does_not_select_all_28()


if __name__=='__main__':unittest.main()
