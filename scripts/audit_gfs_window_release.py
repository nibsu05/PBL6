"""Additional release checks: actual budgets, CV selection, handoff and public payload."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import argparse
import hashlib
import subprocess
import zipfile
import joblib
import numpy as np
import pandas as pd
from src.gfs_window import BASE,PUBLIC,now,sha,read_json,write_json,FEATURES


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--index',action='store_true');args=parser.parse_args()
    selection=read_json(PUBLIC/'selection.json');cv=pd.read_csv(PUBLIC/'train_only_cv.csv')
    if len(cv)!=72 or cv.duplicated(['candidate','objective','horizon','fold']).any():raise ValueError('Wrong CV budget')
    ratios=cv.groupby('candidate').normalized_rmse.mean().sort_values()
    if ratios.index[0]!=selection['candidate']['name']:raise ValueError('Shared candidate not chosen by declared score')
    chosen=cv[cv.candidate.eq(ratios.index[0])]
    loss=chosen.groupby('objective').normalized_rmse.mean().sort_values()
    if loss.index[0]!=selection['selected_loss']:raise ValueError('Loss not chosen from training-only CV')
    for h in (1,2,3):
        if selection['trees'][str(h)]!=int(np.median(chosen.loc[chosen.horizon.eq(h),'best_iteration'])):raise ValueError('Wrong shared tree budget')
    mean_count=0;aux_count=0
    for path in (BASE/'models').glob('MEAN_*.joblib'):
        a=joblib.load(path);m=a['model'];h=int(path.name.split('_d')[1].split('_')[0]);params=m.get_params()
        if params['n_estimators']!=selection['trees'][str(h)]:raise ValueError('Actual estimator budget mismatch')
        if params['num_leaves']!=selection['candidate']['num_leaves']:raise ValueError('Actual leaves mismatch')
        objective='regression' if a['objective']=='l2' else 'tweedie'
        if params['objective']!=objective:raise ValueError('Actual estimator objective mismatch')
        if a['features']!=FEATURES['N0' if '_N0_' in path.name else 'N1' if '_N1_' in path.name else 'N3']:
            raise ValueError('Actual feature list mismatch')
        mean_count+=1
    for path in (BASE/'models').glob('AUX_*.joblib'):aux_count+=len(joblib.load(path)['heads'])
    if (mean_count,aux_count)!=(54,108):raise ValueError('Incomplete final estimator set')
    release=read_json(PUBLIC/'release.json');bundle=ROOT/release['private_handoff']['path']
    if sha(bundle)!=release['private_handoff']['sha256']:raise ValueError('Bundle digest mismatch')
    with zipfile.ZipFile(bundle) as archive:
        if archive.testzip() is not None:raise ValueError('Archive CRC mismatch')
        entry='PBL6_NGAN_HAN_57_TRAM_2021_2026.parquet'
        digest=hashlib.sha256(archive.read(entry)).hexdigest()
        if digest!=release['private_handoff']['dataset_sha256']:raise ValueError('Archived dataset differs')
        if len(archive.namelist())!=7:raise ValueError('Unexpected extra handoff files')
    data=pd.read_parquet(BASE/entry)
    if data.fit_long.sum()!=72886*3 or data.fit_short.sum()!=35116*3 or data.calibration_2025.sum()!=18723*3:
        raise ValueError('Handoff role counts changed')
    for col in ('fit_long','fit_short','calibration_2025','retrospective_2026'):
        allowed={'fit_long':[2021,2022,2023,2024],'fit_short':[2021,2022],'calibration_2025':[2025],'retrospective_2026':[2026]}[col]
        years=data.loc[data[col],'target_end_utc'].dt.tz_convert('Asia/Ho_Chi_Minh').dt.year
        if not years.isin(allowed).all():raise ValueError('Handoff role leakage')
    public_files=list(PUBLIC.iterdir())
    for path in public_files:
        if path.suffix.lower() in ('.parquet','.npz','.joblib','.pt','.zip','.pdf','.dpapi'):raise ValueError('Private artifact in public report')
        if path.suffix=='.csv':
            columns=pd.read_csv(path,nrows=0).columns
            if any(c in columns for c in ['station_id','latitude','longitude','legacy_id','modern_id','password']):
                raise ValueError('Private fields published in '+path.name)
    # Feature catalogue mentions latitude as a feature NAME, never coordinate VALUES.
    if args.index:
        for name,digest in release['report_files'].items():
            rel=str((PUBLIC/name).relative_to(ROOT)).replace('\\','/')
            raw=subprocess.run(['git','-c','safe.directory=D:/PBL6_v2','show',':'+rel],cwd=ROOT,capture_output=True,check=True).stdout
            if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Index byte mismatch: '+name)
        lock=read_json(BASE/'training_lock.json')
        for rel,digest in lock['code'].items():
            raw=subprocess.run(['git','-c','safe.directory=D:/PBL6_v2','show',':'+rel],cwd=ROOT,capture_output=True,check=True).stdout
            if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Locked code index mismatch: '+rel)
    report=dict(status='passed',completed_utc=now(),cv_estimators_checked=len(cv),mean_estimators_checked=mean_count,
        auxiliary_estimators_checked=aux_count,shared_candidate_rounds_and_actual_objectives=True,
        prospective_selection_train_CV_only=True,handoff_rows=len(data),handoff_files=7,public_payload_private_fields_absent=True,
        git_index_bytes_checked=args.index)
    write_json(BASE/('index_verification.json' if args.index else 'release_audit.json'),report)
    print(report,flush=True)


if __name__=='__main__':main()
