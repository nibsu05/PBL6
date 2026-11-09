"""Diagnostics for gauge interpolation; not a rainfall label approval system."""
import numpy as np


def neighbor_weights(distance_km, allowed, k=8, power=2):
    """Nonnegative IDW weights; forbidden and unavailable gauges get zero mass.

    Rows with no allowed source stay zero. Exact coincident sources share mass.
    ``allowed`` is explicit so spatial holdouts cannot accidentally use themselves.
    """
    d = np.asarray(distance_km, float)
    ok = np.broadcast_to(np.asarray(allowed, bool), d.shape) & np.isfinite(d)
    if d.ndim != 2 or k < 1 or power <= 0 or np.any(d < 0):
        raise ValueError('Invalid distance/IDW configuration')
    ranks = np.argsort(np.where(ok, d, np.inf), axis=1)[:, :min(k, d.shape[1])]
    selected = np.zeros_like(ok)
    np.put_along_axis(selected, ranks, True, axis=1)
    selected &= ok
    exact = selected & (d <= 1e-9)
    with np.errstate(divide='ignore', invalid='ignore'):
        raw = np.where(selected, np.maximum(d, 1e-9) ** (-power), 0.)
    raw = np.where(exact.any(axis=1, keepdims=True), exact.astype(float), raw)
    total = raw.sum(axis=1, keepdims=True)
    return np.divide(raw, total, out=np.zeros_like(raw), where=total > 0)


def error_metrics(observed, estimated):
    """Daily depth metrics; NRMSE denominator is mean observed depth."""
    a, b = np.broadcast_arrays(np.asarray(observed, float), np.asarray(estimated, float))
    valid = np.isfinite(a) & np.isfinite(b)
    a, b = a[valid], b[valid]
    if not len(a):
        return dict(n=0)
    e = b-a
    mean = float(a.mean())
    rmse = float(np.sqrt(np.mean(e*e)))
    return dict(n=int(len(a)), mean_observed=mean, mae=float(np.abs(e).mean()),
                rmse=rmse, bias=float(e.mean()), nrmse=rmse/mean if mean > 0 else None,
                volume_bias=float(b.sum()/a.sum()-1) if a.sum() > 0 else None)


def weighted_quantiles(values, counts, quantiles=(.1, .5, .9)):
    """Quantiles over observed mask frequencies, not confidence intervals."""
    values, counts = np.asarray(values, float), np.asarray(counts, int)
    if (counts < 0).any() or len(values) != len(counts) or counts.sum() == 0:
        raise ValueError('Invalid frequency weights')
    return np.quantile(np.repeat(values, counts), quantiles).tolist()
