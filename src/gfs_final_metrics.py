"""Macro verification and predeclared paired uncertainty for final study."""
import warnings
import numpy as np
import pandas as pd
from src.gfs_station_dataset import macro_metrics, event_metrics
from src.gfs_daily_evaluation import block_draw_counts


def holm(values):
    p = np.asarray(values, float)
    missing = ~np.isfinite(p)
    p = np.where(missing, 1., p)
    order = np.argsort(p)
    adjusted = np.minimum(1., np.maximum.accumulate(p[order]*(len(p)-np.arange(len(p)))))
    out = np.empty(len(p))
    out[order] = adjusted
    out[missing] = np.nan
    return out


def summary_tables(frame, models, cutoffs):
    point, probability, events, monthly, conditional, reliability, labels = [], [], [], [], [], [], []
    station_points = []
    for (scope, h), f in frame.groupby(["evaluation_set", "horizon"], sort=False):
        y = f.y_mm.to_numpy()
        labels.append(dict(evaluation_set=scope, horizon=int(h), samples=len(f),
            stations=int(f.station_id.nunique()), issue_dates=int(f.issue_utc.nunique()),
            first_issue_utc=str(f.issue_utc.min()), last_issue_utc=str(f.issue_utc.max()),
            fraction_under1=float((y < 1).mean()), mean_mm=float(y.mean()), median_mm=float(np.median(y)),
            maximum_mm=float(y.max()), events_ge50=int((y >= 50).sum()),
            issue_dates_ge50=int(f.loc[y >= 50, "issue_utc"].nunique())))
        for model in models:
            for functional in ("mean", "median"):
                col = model+"_"+functional
                score, station = macro_metrics(pd.DataFrame(dict(station_id=f.station_id, y=y, pred=f[col])))
                point.append(dict(evaluation_set=scope, horizon=int(h), model=model, functional=functional, **score))
                station_points.append(station.assign(evaluation_set=scope, horizon=h, model=model, functional=functional))
                for month, sub in f.groupby(f.target_end_utc.dt.tz_convert("Asia/Ho_Chi_Minh").dt.month):
                    s, _ = macro_metrics(pd.DataFrame(dict(station_id=sub.station_id, y=sub.y_mm, pred=sub[col])))
                    monthly.append(dict(evaluation_set=scope, horizon=int(h), month=int(month), model=model,
                                        functional=functional, **s))
                for bin_name, mask in [("under1", y < 1), ("1_to_10", (y >= 1) & (y < 10)),
                                       ("10_to_50", (y >= 10) & (y < 50)), ("ge50", y >= 50)]:
                    sub = f.loc[mask]
                    error = sub[col].to_numpy()-sub.y_mm.to_numpy()
                    conditional.append(dict(evaluation_set=scope, horizon=int(h), model=model, functional=functional,
                        observed_rain_bin=bin_name, n=len(sub), stations=int(sub.station_id.nunique()),
                        issue_dates=int(sub.issue_utc.nunique()), micro_mae=float(abs(error).mean()) if len(error) else np.nan,
                        micro_rmse=float(np.sqrt((error**2).mean())) if len(error) else np.nan,
                        micro_bias=float(error.mean()) if len(error) else np.nan))
            for threshold in (1, 50):
                col = f"{model}_p{threshold}"
                ref = f"CLIM_p{threshold}"
                per = pd.DataFrame([event_metrics(s.y_mm.ge(threshold), s[col], s[ref]) for _, s in f.groupby("station_id")])
                micro = event_metrics(y >= threshold, f[col], f[ref])
                probability.append(dict(evaluation_set=scope, horizon=int(h), model=model, threshold_mm=threshold,
                    macro_bs=float(per.bs.mean()), macro_bss=float(per.bss.mean()),
                    stations_with_bss=int(per.bss.notna().sum()), micro_bs=micro["bs"], micro_bss=micro["bss"],
                    events=micro["events"], issue_dates=int(f.loc[y >= threshold, "issue_utc"].nunique())))
                rules = [("fixed_0.5", .5)]
                if (model, h) in cutoffs:
                    rules.append(("calibration_selected", cutoffs[(model, h)]))
                for rule, tau in rules:
                    per = pd.DataFrame([event_metrics(s.y_mm.ge(threshold), s[col], s[ref], tau) for _, s in f.groupby("station_id")])
                    micro = event_metrics(y >= threshold, f[col], f[ref], tau)
                    events.append(dict(evaluation_set=scope, horizon=int(h), model=model, threshold_mm=threshold,
                        decision_rule=rule, cutoff=float(tau), macro_csi=float(per.csi.mean()), macro_pod=float(per.pod.mean()),
                        macro_far=float(per.far.mean()), stations_with_pod=int(per.pod.notna().sum()),
                        stations_with_far=int(per.far.notna().sum()), micro_csi=micro["csi"], micro_pod=micro["pod"],
                        micro_far=micro["far"], hits=micro["hits"], misses=micro["misses"],
                        false_alarms=micro["false_alarms"], events=micro["events"]))
                for number, sub in f.groupby(np.minimum((f[col]*10).astype(int), 9)):
                    reliability.append(dict(evaluation_set=scope, horizon=int(h), model=model, threshold_mm=threshold,
                        bin=int(number), n=len(sub), mean_probability=float(sub[col].mean()),
                        observed_frequency=float(sub.y_mm.ge(threshold).mean())))
    return dict(point_metrics=pd.DataFrame(point), probability_metrics=pd.DataFrame(probability),
        event_metrics=pd.DataFrame(events), monthly_point_metrics=pd.DataFrame(monthly),
        conditional_amount_metrics=pd.DataFrame(conditional), reliability=pd.DataFrame(reliability),
        label_distribution=pd.DataFrame(labels), station_points_private=pd.concat(station_points, ignore_index=True))


def bootstrap_comparisons(frame, models, p, callback=None):
    comparisons = []
    primary_feature = {tuple(pair) for pair in p["primary_feature_contrasts"]}
    primary_skill = {tuple(pair) for pair in p["primary_skill_contrasts"]}
    pairs = {(m, ref) for m in models for ref in ("ZERO", "GFS", "CLIM", "MOS") if m != ref}
    pairs.update(primary_feature)
    pairs.update(tuple(pair) for pair in p["secondary_contrasts"])
    pairs.update(("LGB_"+a, "LGB_"+b) for a, b in [("N2", "N1"), ("N4", "N3"), ("N5", "N4"), ("N5", "N3")])
    pairs.update(("GRU_"+c, "LGB_"+c) for c in ("N3", "N5"))
    pairs.update((f"LGB_N3_delay{d}", "LGB_N3") for d in (3, 6))
    pairs = sorted((a, b) for a, b in pairs if a in models and b in models)
    for (scope, h), f in frame.groupby(["evaluation_set", "horizon"], sort=False):
        dates = pd.date_range(f.issue_utc.min(), f.issue_utc.max(), freq="D")
        stations = sorted(f.station_id.unique())
        counts = block_draw_counts(len(dates), draws=p["uncertainty"]["draws"],
            block=p["uncertainty"]["block_days"], seed=p["uncertainty"]["seed"])
        def matrix(values):
            q = f[["issue_utc", "station_id"]].copy()
            q["value"] = values
            return q.pivot(index="issue_utc", columns="station_id", values="value").reindex(index=dates, columns=stations).to_numpy()
        valid = np.isfinite(matrix(np.ones(len(f)))).astype(float)
        denominator = counts @ valid
        full_support = float((denominator > 0).all(1).mean())
        def station_values(values):
            x = matrix(values)
            n = np.isfinite(x).sum(0)
            observed = np.nansum(x, axis=0)/n
            with np.errstate(divide="ignore", invalid="ignore"):
                boot = (counts @ np.nan_to_num(x))/denominator
            return observed, boot
        cache = {}
        references = {}
        for threshold in (1, 50):
            references[threshold] = station_values((f[f"CLIM_p{threshold}"].to_numpy()-f.y_mm.ge(threshold).to_numpy())**2)
        for model in models:
            err = f[model+"_mean"].to_numpy()-f.y_mm.to_numpy()
            observed, boot = station_values(err**2)
            cache[(model, "mean_rmse")] = (float(np.sqrt(observed).mean()), np.nanmean(np.sqrt(boot), axis=1))
            err = f[model+"_median"].to_numpy()-f.y_mm.to_numpy()
            observed, boot = station_values(abs(err))
            cache[(model, "median_mae")] = (float(observed.mean()), np.nanmean(boot, axis=1))
            for threshold in (1, 50):
                observed, boot = station_values((f[f"{model}_p{threshold}"].to_numpy()-f.y_mm.ge(threshold).to_numpy())**2)
                cache[(model, f"bs{threshold}")] = (float(observed.mean()), np.nanmean(boot, axis=1))
                ref, b_ref = references[threshold]
                with np.errstate(divide="ignore", invalid="ignore"):
                    ratio = 1-observed/np.where(ref > 0, ref, np.nan)
                    b_ratio = 1-boot/np.where(b_ref > 0, b_ref, np.nan)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    cache[(model, f"bss{threshold}")] = (float(np.nanmean(ratio)), np.nanmean(b_ratio, axis=1))
        for first, other in pairs:
            for metric in ("mean_rmse", "median_mae", "bs1", "bs50", "bss1", "bss50"):
                value, a = cache[(first, metric)]
                ref, b = cache[(other, metric)]
                difference = value-ref
                distribution = a-b
                distribution = distribution[np.isfinite(distribution)]
                lower_better = not metric.startswith("bss")
                family = "feature" if (first, other) in primary_feature and metric == "mean_rmse" else (
                    "skill" if (first, other, metric) in primary_skill else "exploratory")
                family_size = 9 if family == "feature" else 6 if family == "skill" else 1
                if len(distribution):
                    low, high = np.quantile(distribution, [.025, .975])
                    centered = distribution-difference
                    approximate_p = (1+np.sum(centered <= difference if lower_better else centered >= difference))/(len(distribution)+1)
                    lo_adjusted, hi_adjusted = np.quantile(distribution, [.025/family_size, 1-.025/family_size])
                else:
                    low = high = approximate_p = lo_adjusted = hi_adjusted = np.nan
                comparisons.append(dict(evaluation_set=scope, horizon=int(h), model=first, reference=other,
                    metric=metric, difference=difference, ci95_low=float(low), ci95_high=float(high),
                    family=family, family_size=family_size, simultaneous_ci_low=float(lo_adjusted),
                    simultaneous_ci_high=float(hi_adjusted), approximate_p=float(approximate_p),
                    draws=len(distribution), block_days=p["uncertainty"]["block_days"], calendar_days=len(dates),
                    full_station_support_fraction=full_support,
                    direction="negative favors model" if lower_better else "positive favors model",
                    interpretation="locked final test" if scope == "test2025_legacy" else "development exploratory" if scope.startswith("dev") else "external descriptive; API continuity unverified"))
        if callback:
            callback(scope, int(h))
    result = pd.DataFrame(comparisons)
    result["holm_p"] = np.nan
    for (scope, family), positions in result[result.family.ne("exploratory")].groupby(["evaluation_set", "family"]).groups.items():
        result.loc[positions, "holm_p"] = holm(result.loc[positions, "approximate_p"])
    result["primary_improvement_supported"] = (result.evaluation_set.eq("test2025_legacy") &
        result.family.ne("exploratory") & result.difference.lt(0) & result.simultaneous_ci_high.lt(0) & result.holm_p.lt(.05))
    return result
