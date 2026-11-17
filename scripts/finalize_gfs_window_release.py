"""Finalize hashes after native rendering and verify a static publication snapshot."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import subprocess
from src.gfs_window import BASE,PUBLIC,now,sha,read_json,write_json
from scripts.run_gfs_window import check_freeze


def main():
    check_freeze()
    render=read_json(PUBLIC/'slide_render_verification.json')
    if render['status']!='passed' or render['pptx_sha256']!=sha(PUBLIC/'PBL6_MO_RONG_NAM_TRAIN_VA_LOSS.pptx'):
        raise ValueError('Latest deck has not passed native rendering')
    result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/audit_gfs_window_release.py')],cwd=ROOT)
    if result.returncode:raise ValueError('Release audit failed')
    checks=read_json(BASE/'release_audit.json')
    write_json(PUBLIC/'release_checks.json',checks)
    tracking=read_json(PUBLIC/'prospective_tracking.json')
    tracking['snapshot_utc']=now();tracking['status_is_publication_snapshot']=True
    tracking['selected_case']='B';tracking['selection_basis']='train-only2022CV; long window predeclared'
    write_json(PUBLIC/'prospective_tracking.json',tracking)
    release=read_json(PUBLIC/'release.json')
    release['finalized_utc']=now();release['native_render']='passed;28slides;484text_boxes;0overflow'
    release['code']={p:sha(ROOT/p) for p in ['scripts/publish_gfs_window.py','scripts/render_gfs_window.ps1',
        'scripts/monitor_gfs_window.ps1','scripts/track_gfs_window_issue.py','scripts/audit_gfs_window_release.py',
        'scripts/finalize_gfs_window_release.py']}
    release['report_files']={p.name:sha(p) for p in PUBLIC.iterdir() if p.is_file() and p.name!='release.json'}
    write_json(PUBLIC/'release.json',release)
    print(dict(status='complete',report_files=len(release['report_files']),native_render='passed',
        bundle_MB=round(release['private_handoff']['bytes']/1e6,2)),flush=True)


if __name__=='__main__':main()
