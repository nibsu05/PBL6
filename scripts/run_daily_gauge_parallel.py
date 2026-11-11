"""Complete the frozen daily fit jobs in two independent worker processes.

Training functions, seed lists, hyperparameters, data and calibration are inherited
unchanged. Only the parent writes run.json; workers own distinct job files.
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import itertools
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import torch
from scripts import run_daily_gauge_matrix as runner

DATA=None


def initialize():
    global DATA
    torch.set_num_threads(4)
    DATA,_=runner.load_development()


def job(spec):
    year,exp,kind,seed=spec;data=DATA
    train=data.dates.year<=year-2;cal=data.dates.year==year-1;ev=data.dates.year==year
    sample=data.select(runner.feature_groups()[exp])
    clim=runner.fit_climatology(data.dates[train],data.y[train])
    _,ref=runner.predict_climatology(data.dates[ev],clim)
    _,cref=runner.predict_climatology(data.dates[cal],clim)
    tag=f'{kind}_{exp}_{year}_s{seed}';tick=time.perf_counter()
    if kind=='lgbm':
        x,names=runner.tabular_inputs(sample)
        ac,ae,pc,pe,meta=runner.fit_lgbm(x,sample.y,train,cal,ev,runner.PRIVATE/'models',tag)
        meta['tabular_names']=names
        for item in meta['output_models']:
            if 'path' in item:item['sha256']=runner.sha(runner.PRIVATE/'models'/item['path'])
    else:ac,ae,pc,pe,meta=runner.fit_network(kind,sample,train,cal,ev,tag,'cuda')
    params=runner.fit_calibration(sample.y[cal],pc)
    c=runner.prediction_frame(data.dates[cal],sample.y[cal],ac,runner.apply_calibration(pc,params),cref,params,kind,exp,year,seed)
    e=runner.prediction_frame(data.dates[ev],sample.y[ev],ae,runner.apply_calibration(pe,params),ref,params,kind,exp,year,seed)
    cp=f'{tag}_cal.parquet';ep=f'{tag}_eval.parquet'
    c.to_parquet(runner.PRIVATE/cp,index=False);e.to_parquet(runner.PRIVATE/ep,index=False)
    meta.update(year=year,experiment=exp,model=kind,seed=seed,features=sample.features,
        n_train=int(train.sum()),n_cal=int(cal.sum()),n_eval=int(ev.sum()),calibration=params,
        cal_predictions=cp,eval_predictions=ep,cal_predictions_sha256=runner.sha(runner.PRIVATE/cp),
        eval_predictions_sha256=runner.sha(runner.PRIVATE/ep),total_seconds=time.perf_counter()-tick)
    runner.dump(runner.PRIVATE/f'{tag}_completed.json',meta)
    return meta


def main():
    assert torch.cuda.is_available()
    path=runner.REPORT/'run.json';manifest=json.loads(path.read_text(encoding='utf8'))
    protocol=json.loads((runner.REPORT/'protocol_frozen.json').read_text(encoding='utf8'))
    for name,digest in protocol['code_hashes'].items():assert runner.sha(ROOT/name)==digest
    def key(m):return (m['year'],m['experiment'],m['model'],m['seed'])
    completed={key(m):m for m in manifest['models']}
    # Crash recovery is per completed job, not a second writer to the main manifest.
    for p in runner.PRIVATE.glob('*_completed.json'):
        m=json.loads(p.read_text(encoding='utf8'));completed.setdefault(key(m),m)
    tasks=[]
    for year,exp,kind in itertools.product(runner.YEARS,runner.feature_groups(),runner.MODELS):
        for seed in ([42] if kind=='lgbm' else runner.SEEDS):
            spec=(year,exp,kind,seed)
            if spec not in completed:tasks.append(spec)
    start=time.perf_counter()
    execution=dict(worker_processes=2,training_functions='Unchanged frozen run_daily_gauge_matrix.fit_network / pilot_short_range.fit_lgbm',
        completed_before_parallel=len(completed),pending=len(tasks),code_sha256=runner.sha(__file__),
        test2025_read=False)
    runner.dump(runner.REPORT/'parallel_execution.json',execution)
    with ProcessPoolExecutor(max_workers=2,initializer=initialize) as pool:
        futures=[pool.submit(job,spec) for spec in tasks]
        for future in as_completed(futures):
            m=future.result();completed[key(m)]=m
            manifest['models']=list(completed.values());runner.dump(path,manifest)
            print(f'{len(completed)}/168 {m["model"]}_{m["experiment"]}_{m["year"]}_s{m["seed"]}: {m["total_seconds"]:.1f}s',flush=True)
    assert len(completed)==168
    manifest['models']=sorted(completed.values(),key=lambda m:(m['year'],m['experiment'],runner.MODELS.index(m['model']),m['seed']))
    runner.collect(manifest);data,_=runner.load_development();runner.baselines(data)
    manifest.update(status='complete',parallel_wall_seconds=time.perf_counter()-start)
    runner.dump(path,manifest)
    print('Complete frozen daily matrix: 168 jobs',flush=True)


if __name__=='__main__':main()
