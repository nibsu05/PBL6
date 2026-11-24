"""Bounded prospective logger. --watch records one future daily issue, then exits."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import argparse
import time
import pandas as pd
from src.gfs_window import BASE,now,write_json
from src.gfs_window_live import probe,record_issue,verify_due


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--probe',action='store_true')
    parser.add_argument('--issue-day');parser.add_argument('--watch',action='store_true');parser.add_argument('--verify-due',action='store_true')
    args=parser.parse_args()
    if args.probe:
        result=probe();print('Availability snapshot saved; no forecast/skill claim.',flush=True);return
    if args.verify_due:
        print(verify_due(),flush=True);return
    if not args.issue_day:raise ValueError('--issue-day required')
    issue=pd.Timestamp(args.issue_day,tz='UTC')+pd.Timedelta(hours=12)
    if args.watch:
        # First collection at18:40VN: last required gauge interval ended18:00VN.
        first=issue-pd.Timedelta(minutes=20)
        while pd.Timestamp.now(tz='UTC')<first:
            write_json(BASE/'live/watcher.json',dict(stage='waiting',updated_utc=now(),issue_utc=str(issue),
                first_collection_utc=str(first),bounded_to_one_issue=True))
            time.sleep(min(30,max(1,(first-pd.Timestamp.now(tz='UTC')).total_seconds())))
        while pd.Timestamp.now(tz='UTC')<issue-pd.Timedelta(minutes=2):
            try:
                result=record_issue(args.issue_day)
                print('Pre-issue forecast recorded for '+str(result['station_count'])+' stations.',flush=True)
                write_json(BASE/'live/watcher.json',dict(stage='complete',updated_utc=now(),issue_utc=str(issue)));return
            except Exception as exc:
                print('Collection attempt failed: '+type(exc).__name__,flush=True);time.sleep(30)
        write_json(BASE/'live/watcher.json',dict(stage='not_issued_deadline',updated_utc=now(),issue_utc=str(issue)))
        raise RuntimeError('No prospective issue captured before deadline')
    else:
        result=record_issue(args.issue_day);print('Recorded stations: '+str(result['station_count']),flush=True)


if __name__=='__main__':main()
