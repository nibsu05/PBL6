"""Run frozen LightGBM ablations, references and paired verification.

All checkpoints and time/station predictions are private. Public reports expose
aggregate metrics only. Calibration/early stopping uses 2023; development 2024
is not a final test. No ERA5, Vrain2025, 2026 or score-based station selection.
"""
from pathlib import Path
import json
import sys
import warnings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from src.gfs_station_dataset import FEATURES, macro_metrics, event_metrics

BASE = ROOT / "data/operational/gfs_station_pilot_2026_11_10"
PUBLIC = ROOT / "reports/gfs_station_pilot_2026_11_10"
DATA = ROOT / "data/processed/gfs_station_pilot/gfs_vrain_pilot.parquet"
VRAIN = ROOT / "data/operational/vrain_2026_11_09"


def climatology(frame):
    """Station/month shrinkage reference fit exclusively on train gauge days."""
    z = np.load(VRAIN / "freeze_work/station_matrices.npz")
    rain = np.where(z["valid"], z["rain"], np.nan).sum(1)
    days = pd.DatetimeIndex(z["marked_day"])
    registry = pd.read_csv(BASE / "pilot_stations_private.csv", dtype={"legacy_id": str})
    order = {s:i for i,s in enumerate(z["station_ids"])}
    source = []
    for station in registry.itertuples():
        r = rain[:,order[station.legacy_id]]
        ok = (days.year <= 2022) & np.isfinite(r)
        source.extend(dict(station_id=station.canonical_id, month=int(days[j].month), y=float(r[j]))
                      for j in np.flatnonzero(ok))
    train = pd.DataFrame(source)
    prior = train.groupby("month").agg(mean=("y","mean"))
    for threshold in (1.,50.):
        train[f"p{threshold:g}"] = train.y.ge(threshold).astype(float)
        prior[f"p{threshold:g}"] = train.groupby("month")[f"p{threshold:g}"].mean()
    by = {}
    for key, group in train.groupby(["station_id","month"]):
        month = key[1]; weight = len(group)
        by[key] = dict(mean=(group.y.sum()+20*prior.loc[month,"mean"])/(weight+20),
            **{f"p{t:g}":(group[f"p{t:g}"].sum()+20*prior.loc[month,f"p{t:g}"])/(weight+20) for t in (1.,50.)})
    months = pd.DatetimeIndex(frame.target_end_utc).tz_convert("Asia/Ho_Chi_Minh").month
    result = []
    for sid, month in zip(frame.station_id, months):
        result.append(by.get((sid,int(month)),prior.loc[int(month)].to_dict()))
    return pd.DataFrame(result,index=frame.index)


def calibrate(raw_cal, y_cal, raw_all):
    if len(np.unique(y_cal)) < 2:
        return raw_all, None
    def logits(p):
        p=np.clip(p,1e-5,1-1e-5)
        return np.log(p/(1-p)).reshape(-1,1)
    estimator=LogisticRegression(C=1.,solver="lbfgs",max_iter=500)
    estimator.fit(logits(raw_cal),y_cal)
    return estimator.predict_proba(logits(raw_all))[:,1],estimator


def block_difference(frame, a, b, draws=1000):
    delta = np.abs(frame[a]-frame.y_mm)-np.abs(frame[b]-frame.y_mm)
    f=frame[["issue_utc","station_id"]].copy();f["difference"]=delta
    x=f.pivot(index="issue_utc",columns="station_id",values="difference").to_numpy()
    rng=np.random.default_rng(1701); result=[];n=len(x)
    for _ in range(draws):
        starts=rng.integers(0,n,size=int(np.ceil(n/4)))
        positions=((starts[:,None]+np.arange(4)[None,:])%n).ravel()[:n]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore",RuntimeWarning)
            result.append(float(np.nanmean(np.nanmean(x[positions],axis=0))))
    lo,hi=np.quantile(result,[.025,.975])
    return dict(mae_difference=float(np.nanmean(np.nanmean(x,axis=0))),ci95_low=float(lo),ci95_high=float(hi),
                sign="negative favors first model",issue_dates=n,bootstrap_draws=draws,block_issues=4)


def report_predictions(frame, models):
    point_rows=[];prob_rows=[];event_rows=[];private=[];ci=[]
    for fold in ("cal","dev"):
        for horizon in (1,2,3):
            f=frame[frame.split.eq(fold)&frame.horizon.eq(horizon)]
            for model in models:
                score,station=macro_metrics(pd.DataFrame(dict(station_id=f.station_id,y=f.y_mm,pred=f[model])))
                point_rows.append(dict(fold=fold,horizon=horizon,model=model,**score))
                station["fold"]=fold;station["horizon"]=horizon;station["model"]=model;private.append(station)
                for threshold in (1.,50.):
                    pcol=f"{model}_p{threshold:g}"
                    decision=f[pcol].to_numpy() if pcol in f else f[model].ge(threshold).to_numpy(float)
                    station_events=[]
                    for sid,s in f.groupby("station_id"):
                        p=s[pcol] if pcol in s else s[model].ge(threshold).to_numpy(float)
                        station_events.append(event_metrics(s.y_mm.ge(threshold),p,s[f"CLIM_p{threshold:g}"]))
                    ev=pd.DataFrame(station_events)
                    micro_event=event_metrics(f.y_mm.ge(threshold),decision,f[f"CLIM_p{threshold:g}"])
                    event_rows.append(dict(fold=fold,horizon=horizon,model=model,threshold_mm=threshold,
                        decision_rule="probability>=0.5" if pcol in f else "amount>=rain_threshold",
                        macro_csi=float(ev.csi.mean()),macro_pod=float(ev.pod.mean()),macro_far=float(ev.far.mean()),
                        stations_with_pod=int(ev.pod.notna().sum()),stations_with_far=int(ev.far.notna().sum()),
                        micro_csi=micro_event["csi"],micro_pod=micro_event["pod"],micro_far=micro_event["far"],
                        events=micro_event["events"],hits=micro_event["hits"],misses=micro_event["misses"],
                        false_alarms=micro_event["false_alarms"]))
                    if pcol not in f:
                        continue
                    rows=[]
                    for _,s in f.groupby("station_id"):
                        rows.append(event_metrics(s.y_mm.ge(threshold),s[pcol],s[f"CLIM_p{threshold:g}"]))
                    micro=event_metrics(f.y_mm.ge(threshold),f[pcol],f[f"CLIM_p{threshold:g}"])
                    average=pd.DataFrame(rows).mean(numeric_only=True)
                    bs_ref=float(np.mean((f[f"CLIM_p{threshold:g}"]-f.y_mm.ge(threshold))**2))
                    prob_rows.append(dict(fold=fold,horizon=horizon,model=model,threshold_mm=threshold,
                        macro_bs=float(average.bs),macro_bss=float(average.bss),macro_csi=float(average.csi),
                        macro_pod=float(average.pod),macro_far=float(average.far),reference_micro_bs=bs_ref,
                        stations_with_bss=int(pd.DataFrame(rows).bss.notna().sum()),
                        wet_issue_dates=int(f.loc[f.y_mm.ge(threshold),"issue_utc"].nunique()),
                        **{"micro_"+k:v for k,v in micro.items()}))
            for model in [m for m in models if m.startswith(("A","GRU"))]:
                previous={"A1":"A0","A2":"A1","A3":"A2","GRU_A2":"A2"}.get(model)
                references=["GFS","CLIM"]+([previous] if previous else [])
                for reference in references:
                    ci.append(dict(fold=fold,horizon=horizon,model=model,reference=reference,
                                   **block_difference(f,model,reference)))
    pd.DataFrame(point_rows).to_csv(PUBLIC / "point_metrics.csv",index=False)
    pd.DataFrame(prob_rows).to_csv(PUBLIC / "probability_metrics.csv",index=False)
    pd.DataFrame(event_rows).to_csv(PUBLIC / "event_metrics.csv",index=False)
    pd.DataFrame(ci).to_csv(PUBLIC / "paired_bootstrap.csv",index=False)
    pd.concat(private,ignore_index=True).to_csv(BASE / "metrics_by_station_private.csv",index=False)
    # Reliability bins are descriptive in dev; cal was used for Platt fitting.
    rel=[]
    for model in models:
        for threshold in (1.,50.):
            col=f"{model}_p{threshold:g}"
            if col not in frame:
                continue
            f=frame[frame.split.eq("dev")].copy()
            f["bin"]=np.minimum((f[col]*10).astype(int),9)
            for bin_number,g in f.groupby("bin"):
                rel.append(dict(model=model,threshold_mm=threshold,bin=int(bin_number),n=len(g),
                    mean_probability=float(g[col].mean()),observed_frequency=float(g.y_mm.ge(threshold).mean())))
    pd.DataFrame(rel).to_csv(PUBLIC / "reliability.csv",index=False)
    return pd.DataFrame(point_rows)


def main():
    protocol=json.loads((PUBLIC / "protocol.json").read_text())
    frame=pd.read_parquet(DATA).reset_index(drop=True)
    if set(frame.split)!={"train","cal","dev"}:
        raise ValueError("Missing chronological fold")
    reference=climatology(frame)
    frame["CLIM"]=reference["mean"];frame["PERSISTENCE"]=frame.rain_recent24h_mm;frame["GFS"]=frame.gfs_rain_mm
    for t in (1.,50.):frame[f"CLIM_p{t:g}"]=reference[f"p{t:g}"]
    checkpoints=BASE / "models";checkpoints.mkdir(exist_ok=True)
    seeds=[];diagnostics=[]
    for config,names in FEATURES.items():
        for h in (1,2,3):
            positions=frame.index[frame.horizon.eq(h)];f=frame.loc[positions]
            tr=f.split.eq("train");cal=f.split.eq("cal")
            if not np.isfinite(f[names].to_numpy()).all():raise ValueError("Missing predictor")
            predictions=[];probabilities={t:[] for t in (1.,50.)}
            for seed in protocol["model_seeds"]:
                common=dict(n_estimators=500,learning_rate=.04,num_leaves=15,max_depth=4,min_child_samples=40,
                    reg_lambda=2.,subsample=.9,subsample_freq=1,colsample_bytree=.9,random_state=seed,
                    n_jobs=4,verbosity=-1,deterministic=True,force_col_wise=True)
                model=lgb.LGBMRegressor(objective="tweedie",tweedie_variance_power=1.5,**common)
                model.fit(f.loc[tr,names],f.loc[tr,"y_mm"],categorical_feature=["station_code"],
                    eval_set=[(f.loc[cal,names],f.loc[cal,"y_mm"])],eval_metric="l1",
                    callbacks=[lgb.early_stopping(40,first_metric_only=True,verbose=False)])
                amount=np.maximum(model.predict(f[names]),0);predictions.append(amount)
                artifact=dict(amount=model,features=names,probability={})
                for t in probabilities:
                    y=f.y_mm.ge(t).astype(int)
                    if y[tr].nunique()<2:
                        p=np.full(len(f),(y[tr].sum()+.5)/(tr.sum()+1));classifier=None;platt=None
                    else:
                        classifier=lgb.LGBMClassifier(objective="binary",**common)
                        classifier.fit(f.loc[tr,names],y[tr],categorical_feature=["station_code"],
                            eval_set=[(f.loc[cal,names],y[cal])],eval_metric="binary_logloss",
                            callbacks=[lgb.early_stopping(40,verbose=False)])
                        raw=classifier.predict_proba(f[names])[:,1]
                        p,platt=calibrate(raw[cal.to_numpy()],y[cal].to_numpy(),raw)
                    probabilities[t].append(p)
                    artifact["probability"][t]=dict(classifier=classifier,platt=platt)
                for fold in ("cal","dev"):
                    ok=f.split.eq(fold)
                    metric,_=macro_metrics(pd.DataFrame(dict(station_id=f.loc[ok,"station_id"],y=f.loc[ok,"y_mm"],pred=amount[ok.to_numpy()])))
                    seeds.append(dict(config=config,horizon=h,seed=seed,fold=fold,**metric))
                joblib.dump(artifact,checkpoints / f"{config}_d{h}_seed{seed}.joblib",compress=3)
                diagnostics.append(dict(config=config,horizon=h,seed=seed,best_iteration=int(model.best_iteration_),
                    train_rows=int(tr.sum()),cal_rows=int(cal.sum())))
            frame.loc[positions,config]=np.mean(predictions,axis=0)
            for t,p in probabilities.items():frame.loc[positions,f"{config}_p{t:g}"]=np.mean(p,axis=0)
            print(f"Fitted {config} day{h}: train={tr.sum()} cal={cal.sum()} seeds={len(predictions)}",flush=True)
    models=["CLIM","PERSISTENCE","GFS"]+list(FEATURES)
    point=report_predictions(frame,models)
    frame.to_parquet(BASE / "predictions_private.parquet",index=False)
    pd.DataFrame(seeds).to_csv(PUBLIC / "seed_point_metrics.csv",index=False)
    pd.DataFrame(diagnostics).to_csv(PUBLIC / "fit_diagnostics.csv",index=False)
    gate=[]
    for h in (1,2,3):
        m=point[point.fold.eq("cal")&point.horizon.eq(h)].set_index("model")
        f=frame[frame.split.eq("cal")&frame.horizon.eq(h)]
        per=f.assign(a=np.abs(f.A2-f.y_mm),b=np.abs(f.GFS-f.y_mm)).groupby("station_id")[["a","b"]].mean()
        fraction=float((per.a<per.b).mean())
        passed=bool(m.loc["A2","macro_mae"] < min(m.loc["GFS","macro_mae"],m.loc["CLIM","macro_mae"]) and fraction>=.5)
        gate.append(dict(horizon=h,passed=passed,station_fraction_better_raw_gfs=fraction,
                         cal_mae_A2=float(m.loc["A2","macro_mae"]),cal_mae_GFS=float(m.loc["GFS","macro_mae"]),cal_mae_CLIM=float(m.loc["CLIM","macro_mae"])))
    summary=dict(status="lightgbm_pilot_complete",configurations=list(FEATURES),seeds=protocol["model_seeds"],
        models=models,stations=int(frame.station_id.nunique()),fits_amount=36,fits_binary_max=72,
        probability_calibration="Platt on cal2023, after tree early stopping; cal probabilities not out-of-sample",
        ensemble="arithmetic mean of three seeds",daily_experiment_complete=False,
        pilot_cadence_days=protocol["pilot_cadence_days"],small_gru_gate_based_only_on_cal=gate,
        test2025_read=False,station_model_training_performed=True)
    (PUBLIC / "run_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2),flush=True)


if __name__=="__main__":main()
