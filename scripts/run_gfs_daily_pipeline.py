"""Run the daily-v2 build, replay, training and evaluation with durable logs."""
from pathlib import Path
from datetime import datetime,timezone
import json
import os
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.gfs_daily import BASE,write_json
from src.vrain_download import process_lock


def main():
    stages=['build_gfs_daily','validate_gfs_daily','run_gfs_daily_trees','run_gfs_daily_gru','evaluate_gfs_daily']
    with process_lock(BASE/'pipeline.lock'):
        completed=[]
        for stage in stages:
            write_json(BASE/'pipeline_progress.json',dict(state='running',stage=stage,completed=completed,
                pid=os.getpid(),updated_utc=datetime.now(timezone.utc).isoformat()))
            with (BASE/(stage+'.log')).open('a',encoding='utf8') as log:
                result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts'/(stage+'.py'))],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            if result.returncode:
                write_json(BASE/'pipeline_progress.json',dict(state='failed',stage=stage,completed=completed,
                    exit_code=result.returncode,updated_utc=datetime.now(timezone.utc).isoformat()))
                raise SystemExit(result.returncode)
            completed.append(stage)
        write_json(BASE/'pipeline_progress.json',dict(state='evaluated_pending_model_verification',completed=completed,
            updated_utc=datetime.now(timezone.utc).isoformat()))


if __name__=='__main__':main()
