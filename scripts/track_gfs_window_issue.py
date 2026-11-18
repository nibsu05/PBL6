"""One bounded prospective cycle: pre-issue forecast, then delayed truth verification."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import argparse
from datetime import datetime,timedelta,timezone
import json
import os
import subprocess
import time
from src.gfs_window import BASE,VRAIN,now,write_json


def state(stage,**details):
    write_json(BASE/'live/tracker.json',dict(stage=stage,pid=os.getpid(),updated_utc=now(),**details))


def wait_until(target,stage,issue):
    while datetime.now(timezone.utc)<target:
        state(stage,issue_utc=issue.isoformat(),next_action_utc=target.isoformat(),bounded_to_one_issue=True)
        time.sleep(min(30,max(1,(target-datetime.now(timezone.utc)).total_seconds())))


def refresh_authorized_session():
    """Read user-authorized account only from machine-bound encrypted private storage."""
    from src.vrain_download import _dpapi,login,save_session
    path=BASE/'live/authorized_account.dpapi'
    if not path.exists():return
    account=json.loads(_dpapi(path.read_bytes(),decrypt=True))
    session=login(account['username'],account['password'])
    save_session(session,VRAIN/'session.dpapi')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--issue-day',required=True);args=parser.parse_args()
    issue=datetime.fromisoformat(args.issue_day).replace(hour=12,tzinfo=timezone.utc)
    if datetime.now(timezone.utc)>=issue:raise ValueError('Cannot schedule a past issue')
    wait_until(issue-timedelta(minutes=25),'waiting_for_preissue_collection',issue)
    try:refresh_authorized_session()
    except Exception as exc:state('session_refresh_failed',error_type=type(exc).__name__)
    command=[sys.executable,'-X','utf8',str(ROOT/'scripts/record_gfs_window.py'),'--issue-day',args.issue_day,'--watch']
    result=subprocess.run(command,cwd=ROOT)
    if result.returncode:
        state('forecast_not_issued',returncode=result.returncode,issue_utc=issue.isoformat());return
    due=issue+timedelta(hours=73);deadline=due+timedelta(hours=6)
    wait_until(due,'forecast_recorded_waiting_for_truth',issue)
    while datetime.now(timezone.utc)<deadline:
        try:
            refresh_authorized_session()
            # Preserve interrupted truth downloads as separate attempts before retry.
            root=(BASE/'live').resolve();verification=root/'verification'
            for folder in verification.glob('*'):
                if folder.is_dir() and not (folder/'verification.json').exists():
                    destination=root/'incomplete_verification'/f'{folder.name}_{datetime.now(timezone.utc):%Y%m%dT%H%M%S}'
                    if not folder.resolve().is_relative_to(root) or not destination.resolve().is_relative_to(root):
                        raise ValueError('Refuse move outside this private live workspace')
                    destination.parent.mkdir(exist_ok=True);folder.rename(destination)
            from src.gfs_window_live import verify_due
            report=verify_due()
            state('truth_verification_complete',issue_utc=issue.isoformat(),**report);return
        except Exception as exc:
            state('truth_retry_pending',error_type=type(exc).__name__,issue_utc=issue.isoformat(),deadline_utc=deadline.isoformat())
            time.sleep(30)
    state('truth_unavailable_at_deadline',issue_utc=issue.isoformat(),deadline_utc=deadline.isoformat())


if __name__=='__main__':main()
