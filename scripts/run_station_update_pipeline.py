"""Wait for collectors, then build/verify/package without fitting models."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,time,subprocess,os
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.station_archive_update import BASE,write_json
from src.vrain_download import process_lock


def main():
    started=time.monotonic();completed=[]
    def state(status,stage,**extra):
        report=dict(state=status,stage=stage,completed=completed,pid=os.getpid(),updated_at_utc=datetime.now(timezone.utc).isoformat(),training_performed=False,model_evaluation=False,**extra)
        write_json(BASE/'pipeline_progress.json',report)
    with process_lock(BASE/'pipeline.lock'):
        while True:
            gauge=json.loads((BASE/'progress.json').read_text(encoding='utf8'))
            weather=json.loads((BASE/'gfs/progress.json').read_text(encoding='utf8'))
            if gauge['state']=='complete' and weather['state'] in ('complete','incomplete') and weather['remaining_issues']==0:break
            if gauge['state'] in ('login_required','stopped','incomplete') or time.monotonic()-started>7200:
                state('blocked','collection',gauge_state=gauge['state'],gfs_state=weather['state']);raise SystemExit(1)
            state('waiting','collectors',gauge_completed=gauge['completed_responses'],gfs_completed=weather['completed_issues'])
            time.sleep(10)
        for script,args in [('prepare_station_update',[]),('build_station_update',['--reuse-matrices']),('validate_station_update',[]),('publish_station_update',[])]:
            state('running',script)
            with (BASE/(script+'.log')).open('w',encoding='utf8') as log:
                result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts'/(script+'.py'))]+args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            if result.returncode:
                state('failed',script,exit_code=result.returncode);raise SystemExit(result.returncode)
            completed.append(script)
        state('complete','handoff')


if __name__=='__main__':main()
