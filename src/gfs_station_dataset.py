"""Causal gauge history, forecast covariates and feature sets for NWP pilot."""
from __future__ import annotations
import numpy as np
import pandas as pd

HISTORY = [f"rain_lag_day{k}_mm" for k in range(1, 8)]
RECENT = [f"rain_recent{k}h_mm" for k in (1, 6, 24)]
A0 = ["gfs_rain_mm", "sin_doy", "cos_doy", "latitude", "longitude", "station_code"]
A1 = A0 + HISTORY + RECENT
A2 = A1 + ["gfs_t850_c", "gfs_rh850_pct", "gfs_u850", "gfs_v850", "gfs_pwat",
           "gfs_q850_gkg", "gfs_qflux_e", "gfs_qflux_n", "gfs_wspd850"]
A3 = A2 + ["dem_elev_m", "dem_mean_5km_m", "dem_std_5km_m", "dem_slope_east",
           "dem_slope_north", "wind_upslope", "moist_upslope"]
FEATURES = {"A0": A0, "A1": A1, "A2": A2, "A3": A3}


def gauge_history(hourly, daily, day_index, station_index, delay_hours=1):
    """Seven completed 19--19 days plus 1/6/24h rain ending before cutoff."""
    if day_index < 7 or delay_hours != 1:
        raise ValueError("Protocol uses seven prior days and one-hour gauge delay")
    end = 24*day_index+23  # source hourly row ending at current 19:00 local
    last = end-delay_hours
    past = daily[day_index-7:day_index, station_index][::-1]
    result = dict(zip(HISTORY, past))
    for k, name in zip((1, 6, 24), RECENT):
        result[name] = hourly[last-k+1:last+1, station_index].sum()
    return result


def forecast_met(names, values):
    d = dict(zip(names, values))
    t = float(d["t850_k"])-273.15
    rh = float(d["rh850"])
    # Same Magnus approximation for every GFS version, not a mix of q products.
    e = (rh/100)*6.112*np.exp(17.67*t/(t+243.5))
    q = .622*e/(850-.378*e)*1000
    u, v = float(d["u850"]), float(d["v850"])
    if not (-100 < t < 70 and 0 <= rh <= 150 and 0 <= q < 60):
        raise ValueError("GFS thermodynamic range/unit check failed")
    return dict(gfs_t850_c=t, gfs_rh850_pct=rh, gfs_u850=u, gfs_v850=v,
                gfs_pwat=float(d["pwat"]), gfs_q850_gkg=q,
                gfs_qflux_e=u*q, gfs_qflux_n=v*q, gfs_wspd850=float(np.hypot(u, v)))


def add_calendar(target_end):
    local = target_end.tz_convert("Asia/Ho_Chi_Minh")
    return dict(sin_doy=float(np.sin(2*np.pi*local.dayofyear/365.25)),
                cos_doy=float(np.cos(2*np.pi*local.dayofyear/365.25)))


def macro_metrics(frame):
    """Point metrics: equal weight to each station, with micro separately."""
    error = frame.pred.to_numpy()-frame.y.to_numpy()
    rows = []
    for sid, f in frame.groupby("station_id"):
        e = f.pred.to_numpy()-f.y.to_numpy()
        rows.append(dict(station_id=sid, n=len(f), mae=np.abs(e).mean(), rmse=np.sqrt((e*e).mean()), bias=e.mean()))
    per_station = pd.DataFrame(rows)
    return dict(n=len(frame), stations=len(rows), macro_mae=float(per_station.mae.mean()),
                macro_rmse=float(per_station.rmse.mean()), macro_bias=float(per_station.bias.mean()),
                micro_mae=float(np.abs(error).mean()), micro_rmse=float(np.sqrt((error*error).mean())),
                micro_bias=float(error.mean())), per_station


def event_metrics(y, probability, reference, cutoff=.5):
    y = np.asarray(y, bool); probability = np.asarray(probability, float)
    predicted = probability >= cutoff
    h = int((predicted & y).sum()); m = int((~predicted & y).sum()); f = int((predicted & ~y).sum())
    bs = float(np.mean((probability-y)**2)); ref = float(np.mean((np.asarray(reference)-y)**2))
    return dict(bs=bs, bss=1-bs/ref if ref > 0 else np.nan,
        csi=h/(h+m+f) if h+m+f else np.nan, pod=h/(h+m) if h+m else np.nan,
        far=f/(h+f) if h+f else np.nan, hits=h, misses=m, false_alarms=f, events=int(y.sum()),
        forecast_yes=int(predicted.sum()), observed_frequency=float(y.mean()), mean_probability=float(probability.mean()))
