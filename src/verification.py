"""Bộ chỉ số kiểm chứng dùng chung cho mọi mô hình và baseline.

Mọi so sánh trong đồ án đi qua module này để cùng định nghĩa ngưỡng, cùng
tập mẫu và cùng cách tính khoảng tin cậy:

- Ngưỡng dùng ``>=`` (mưa vừa 16–50 mm/24 h nghĩa là từ 16 mm trở lên).
- ``score_table`` mặc định chỉ chấm trên các hàng mà quan trắc và *mọi* dự báo
  đều có giá trị, để không mô hình nào được chấm trên mẫu dễ hơn.
- ``paired_block_bootstrap`` lấy mẫu lại theo khối ngày liên tiếp; mọi trạm/ô
  của cùng một ngày đi cùng nhau nên giữ được tương quan không gian và thời
  gian. Khoảng tin cậy là của *hiệu số* giữa hai nguồn trên cùng mẫu.
"""

from __future__ import annotations

from typing import Callable, Iterable, Sequence

import numpy as np
import pandas as pd

VN_DAILY_THRESHOLDS: dict[float, str] = {16.0: "mưa vừa", 50.0: "mưa to", 100.0: "mưa rất to"}
VN_12H_THRESHOLDS: dict[float, str] = {8.0: "mưa vừa", 26.0: "mưa to", 51.0: "mưa rất to"}

Metric = Callable[[np.ndarray, np.ndarray], float]


def _pairs(obs: Iterable[float], fcst: Iterable[float]) -> tuple[np.ndarray, np.ndarray]:
    o = np.asarray(obs, dtype=float).ravel()
    f = np.asarray(fcst, dtype=float).ravel()
    if o.shape != f.shape:
        raise ValueError("Quan trắc và dự báo phải cùng kích thước")
    valid = np.isfinite(o) & np.isfinite(f)
    return o[valid], f[valid]


def continuous_scores(obs: Iterable[float], fcst: Iterable[float]) -> dict[str, float]:
    """MAE, RMSE, sai lệch trung bình (dự báo − quan trắc) và tương quan Pearson."""
    o, f = _pairs(obs, fcst)
    if len(o) == 0:
        raise ValueError("Không có cặp hợp lệ")
    err = f - o
    cc = float(np.corrcoef(o, f)[0, 1]) if len(o) > 1 and o.std() > 0 and f.std() > 0 else float("nan")
    return {
        "n": int(len(o)),
        "obs_mean": float(o.mean()),
        "fcst_mean": float(f.mean()),
        "MAE": float(np.abs(err).mean()),
        "RMSE": float(np.sqrt(np.square(err).mean())),
        "bias": float(err.mean()),
        "CC": cc,
    }


def contingency_scores(obs: Iterable[float], fcst: Iterable[float], threshold: float) -> dict[str, float | int]:
    """Bảng 2×2 cho sự kiện ``>= threshold``.

    FBI là tỷ lệ số lần báo có / số lần xảy ra (1 = không thiên lệch tần suất).
    ETS (Gilbert skill score) trừ đi số lần trúng do ngẫu nhiên. Chỉ số nào
    không xác định (ví dụ không có sự kiện thật) trả về NaN, không trả 0.
    """
    o, f = _pairs(obs, fcst)
    yes, fyes = o >= threshold, f >= threshold
    hits = int(np.sum(yes & fyes))
    misses = int(np.sum(yes & ~fyes))
    false_alarms = int(np.sum(~yes & fyes))
    correct_neg = int(np.sum(~yes & ~fyes))
    n = hits + misses + false_alarms + correct_neg
    nan = float("nan")
    hits_random = (hits + misses) * (hits + false_alarms) / n if n else nan
    ets_den = hits + misses + false_alarms - hits_random
    return {
        "threshold": float(threshold),
        "n_obs_events": hits + misses,
        "n_fcst_events": hits + false_alarms,
        "hits": hits, "misses": misses, "false_alarms": false_alarms, "correct_negatives": correct_neg,
        "POD": hits / (hits + misses) if hits + misses else nan,
        "FAR": false_alarms / (hits + false_alarms) if hits + false_alarms else nan,
        "CSI": hits / (hits + misses + false_alarms) if hits + misses + false_alarms else nan,
        "FBI": (hits + false_alarms) / (hits + misses) if hits + misses else nan,
        "ETS": (hits - hits_random) / ets_den if n and ets_den else nan,
    }


def brier_score(event: Iterable[float], prob: Iterable[float]) -> float:
    e, p = _pairs(event, prob)
    if len(e) == 0:
        raise ValueError("Không có cặp hợp lệ")
    if np.any((p < 0) | (p > 1)):
        raise ValueError("Xác suất phải nằm trong [0, 1]")
    return float(np.mean(np.square(p - e)))


def brier_skill_score(event: Iterable[float], prob: Iterable[float], ref_prob: Iterable[float]) -> float:
    """BSS = 1 − BS/BS_ref; chỉ dùng các hàng có đủ cả hai xác suất."""
    e = np.asarray(event, dtype=float).ravel()
    p = np.asarray(prob, dtype=float).ravel()
    r = np.asarray(ref_prob, dtype=float).ravel()
    valid = np.isfinite(e) & np.isfinite(p) & np.isfinite(r)
    bs_ref = brier_score(e[valid], r[valid])
    return float(1 - brier_score(e[valid], p[valid]) / bs_ref) if bs_ref > 0 else float("nan")


def reliability_table(event: Iterable[float], prob: Iterable[float], n_bins: int = 10) -> pd.DataFrame:
    """Tần suất quan trắc theo từng khoảng xác suất dự báo (biểu đồ reliability)."""
    e, p = _pairs(event, prob)
    bins = np.clip((p * n_bins).astype(int), 0, n_bins - 1)
    frame = pd.DataFrame({"bin": bins, "prob": p, "event": e})
    out = frame.groupby("bin").agg(n=("event", "size"), mean_prob=("prob", "mean"), obs_freq=("event", "mean"))
    out.index = [f"{b / n_bins:.1f}–{(b + 1) / n_bins:.1f}" for b in out.index]
    return out


def skill_score(score: float, reference: float, perfect: float) -> float:
    """(điểm − tham chiếu)/(hoàn hảo − tham chiếu); dùng được cho cả MAE (perfect=0) và CSI (perfect=1)."""
    return float((score - reference) / (perfect - reference)) if perfect != reference else float("nan")


# ---------------------------------------------------------------- bảng điểm --

def common_rows(frame: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    """Chỉ giữ hàng mà mọi cột trong ``columns`` đều hữu hạn."""
    mask = np.isfinite(frame[list(columns)].to_numpy(dtype=float)).all(axis=1)
    return frame.loc[mask]


def score_table(frame: pd.DataFrame, obs_col: str, forecast_cols: Sequence[str],
                thresholds: Sequence[float] = tuple(VN_DAILY_THRESHOLDS),
                *, common: bool = True,
                clim_prob_cols: dict[float, str] | None = None) -> pd.DataFrame:
    """Một hàng cho mỗi nguồn dự báo, cùng tập mẫu nếu ``common=True``.

    ``clim_prob_cols`` (ngưỡng → cột xác suất khí hậu) bật thêm BSS, coi dự báo
    tất định là xác suất 0/1 — cách này cho thấy dự báo tất định bị phạt nặng
    khi báo sai, động lực để mô hình xuất xác suất.
    """
    cols = list(forecast_cols)
    extra = list(clim_prob_cols.values()) if clim_prob_cols else []
    data = common_rows(frame, [obs_col, *cols, *extra]) if common else frame
    rows = []
    for col in cols:
        sub = data if common else common_rows(frame, [obs_col, col, *extra])
        row: dict[str, float | int | str] = {"source": col, **continuous_scores(sub[obs_col], sub[col])}
        for thr in thresholds:
            cs = contingency_scores(sub[obs_col], sub[col], thr)
            tag = f"{thr:g}"
            row[f"n_obs>={tag}"] = cs["n_obs_events"]
            for key in ("POD", "FAR", "CSI", "FBI", "ETS"):
                row[f"{key}>={tag}"] = cs[key]
            if clim_prob_cols and thr in clim_prob_cols:
                event = (sub[obs_col] >= thr).astype(float)
                row[f"BSS>={tag}"] = brier_skill_score(event, (sub[col] >= thr).astype(float),
                                                       sub[clim_prob_cols[thr]])
        rows.append(row)
    return pd.DataFrame(rows).set_index("source")


# ----------------------------------------------------------- bootstrap cặp --

def metric_mae(o: np.ndarray, f: np.ndarray) -> float:
    return float(np.abs(f - o).mean())


def metric_rmse(o: np.ndarray, f: np.ndarray) -> float:
    return float(np.sqrt(np.square(f - o).mean()))


metric_mae.__name__, metric_mae.lower_is_better = "MAE", True  # type: ignore[attr-defined]
metric_rmse.__name__, metric_rmse.lower_is_better = "RMSE", True  # type: ignore[attr-defined]


def metric_csi(threshold: float) -> Metric:
    def _csi(o: np.ndarray, f: np.ndarray) -> float:
        return float(contingency_scores(o, f, threshold)["CSI"])
    _csi.__name__ = f"CSI>={threshold:g}"
    return _csi


def metric_ets(threshold: float) -> Metric:
    def _ets(o: np.ndarray, f: np.ndarray) -> float:
        return float(contingency_scores(o, f, threshold)["ETS"])
    _ets.__name__ = f"ETS>={threshold:g}"
    return _ets


def paired_block_bootstrap(frame: pd.DataFrame, obs_col: str, col_a: str, col_b: str, metric: Metric,
                           *, date_col: str = "date", block_days: int = 5, n_boot: int = 1000,
                           seed: int = 0, ci: float = 0.95) -> dict[str, float | int | str]:
    """Khoảng tin cậy của metric(A) − metric(B) bằng moving-block bootstrap theo ngày.

    Mỗi lần lặp rút ngẫu nhiên các khối ``block_days`` ngày liên tiếp (theo
    lịch, kể cả ngày không có mẫu) đến khi đủ số ngày gốc; mọi hàng (trạm/ô)
    thuộc ngày được rút đều vào mẫu. ``frac_a_better`` là tỷ lệ lần lặp mà A
    tốt hơn B theo chiều của metric — chỉ là chỉ báo, không phải p-value hiệu
    chỉnh đa so sánh.
    """
    data = common_rows(frame, [obs_col, col_a, col_b])
    if data.empty:
        raise ValueError("Không có hàng chung để so sánh")
    days = pd.to_datetime(data[date_col]).dt.normalize()
    calendar = pd.date_range(days.min(), days.max(), freq="D")
    day_index = calendar.get_indexer(days)
    order = np.argsort(day_index, kind="stable")
    sorted_days = day_index[order]
    starts = np.searchsorted(sorted_days, np.arange(len(calendar)), side="left")
    ends = np.searchsorted(sorted_days, np.arange(len(calendar)), side="right")

    o = data[obs_col].to_numpy(float)[order]
    a = data[col_a].to_numpy(float)[order]
    b = data[col_b].to_numpy(float)[order]
    base_a, base_b = metric(o, a), metric(o, b)

    rng = np.random.default_rng(seed)
    n_days = len(calendar)
    block = max(1, min(block_days, n_days))
    n_blocks = int(np.ceil(n_days / block))
    diffs = np.full(n_boot, np.nan)
    for i in range(n_boot):
        first = rng.integers(0, n_days - block + 1, n_blocks)
        picked = (first[:, None] + np.arange(block)[None, :]).ravel()[:n_days]
        idx = np.concatenate([np.arange(starts[d], ends[d]) for d in picked])
        if idx.size:
            diffs[i] = metric(o[idx], a[idx]) - metric(o[idx], b[idx])
    diffs = diffs[np.isfinite(diffs)]
    lower_is_better = bool(getattr(metric, "lower_is_better", False))
    alpha = (1 - ci) / 2
    return {
        "metric": getattr(metric, "__name__", "metric"),
        "source_a": col_a, "source_b": col_b,
        "n_rows": int(len(data)), "n_days": int(n_days),
        "a": base_a, "b": base_b, "diff": base_a - base_b,
        "ci_low": float(np.quantile(diffs, alpha)) if diffs.size else float("nan"),
        "ci_high": float(np.quantile(diffs, 1 - alpha)) if diffs.size else float("nan"),
        "frac_a_better": float(np.mean(diffs < 0) if lower_is_better else np.mean(diffs > 0)) if diffs.size else float("nan"),
        "n_boot_valid": int(diffs.size),
    }


# ------------------------------------------------------------ chia theo năm --

def rolling_origin_folds(years: Iterable[int], first_test: int, last_test: int,
                         n_val_years: int = 1) -> list[dict[str, list[int] | int]]:
    """Kiểm định chéo cuốn chiếu: test năm k, validation n năm ngay trước, train phần còn lại trước đó."""
    all_years = sorted(set(int(y) for y in years))
    folds = []
    for test in range(first_test, last_test + 1):
        val = [y for y in all_years if test - n_val_years <= y < test]
        train = [y for y in all_years if y < test - n_val_years]
        if not train or len(val) < n_val_years or test not in all_years:
            raise ValueError(f"Không đủ năm để tạo fold test={test}")
        folds.append({"train": train, "val": val, "test": test})
    return folds
