"""Resume the whole new study after collection; no need for repeated approval."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from datetime import datetime,timezone
import json
import os
import subprocess
import time
import re
import argparse
from src.gfs_temporal import BASE,PUBLIC,write_json,sha

def progress(stage,**details):
    write_json(BASE/'pipeline_progress.json',dict(stage=stage,pid=os.getpid(),updated_utc=datetime.now(timezone.utc).isoformat(),**details))

def run(script,*args):
    progress(script)
    subprocess.run([sys.executable,'-X','utf8',f'scripts/{script}.py',*args],cwd=ROOT,check=True)

def tests():
    path=PUBLIC/'tests_verification.json'
    if path.exists():return
    names=['tests.test_gfs_temporal','tests.test_gfs_temporal_models','tests.test_gfs_temporal_evaluation','tests.test_gfs_temporal_integration',
           'tests.test_gfs_daily_v2','tests.test_gfs_capacity_control','tests.test_gfs_final_evaluation']
    progress('tests')
    result=subprocess.run([sys.executable,'-X','utf8','-m','unittest',*names,'-v'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    output=result.stdout+result.stderr
    (BASE/'tests_private.log').write_text(output,encoding='utf-8')
    match=re.search(r'Ran (\d+) tests',output)
    write_json(path,dict(status='passed' if result.returncode==0 else 'failed',tests=int(match[1]) if match else 0,
        suites=names,code_sha256={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'tests').glob('test_gfs_temporal*.py')}))
    if result.returncode:raise RuntimeError('Tests failed; inspect tests_private.log')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resume-verified',action='store_true');parser.add_argument('--publish-only',action='store_true');args=parser.parse_args()
    try:
        run('verify_gfs_temporal','--snapshot')
        if args.publish_only:
            run('publish_gfs_temporal');progress('complete',resumed_publication_only=True);return
        while True:
            p=json.loads((BASE/'collection_progress.json').read_text())
            if p['state']=='complete':break
            if p['state']=='incomplete':raise RuntimeError('Source collection incomplete; inspect failures before training')
            progress('waiting_for_collection',completed=p['completed'],planned=p['planned']);time.sleep(20)
        if args.resume_verified:
            for name in ('dataset_verification','source_verification','tests_verification'):
                if json.loads((PUBLIC/(name+'.json')).read_text())['status']!='passed':raise ValueError('Cannot resume unverified inputs')
            if sha(BASE/'dataset_private.parquet')!=json.loads((PUBLIC/'dataset_verification.json').read_text())['dataset_sha256']:raise ValueError('Verified dataset changed')
            if sha(PUBLIC/'protocol.json')!=json.loads((PUBLIC/'source_verification.json').read_text())['protocol_sha256']:raise ValueError('Verified protocol changed')
        else:
            run('build_gfs_temporal');run('verify_gfs_temporal','--sources');tests()
        if not (BASE/'model_freeze.json').exists():run('train_gfs_temporal')
        run('score_gfs_temporal');run('verify_gfs_temporal');run('publish_gfs_temporal')
        progress('complete')
    except Exception as exc:
        progress('failed',error=f'{type(exc).__name__}: {exc}');raise

if __name__=='__main__':main()
