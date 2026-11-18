"""Download authorized daily tables in the background, resume by verified hashes."""
from pathlib import Path
import argparse
import ctypes
import getpass
import json
import os
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.vrain_download import collect, login, save_session, planned_dates


def pid_running(pid):
    if not isinstance(pid,int) or pid<=0:return None
    if os.name=='nt':
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
        kernel.GetExitCodeProcess.restype=wintypes.BOOL
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:return None if ctypes.get_last_error()==5 else False
        try:
            code=wintypes.DWORD()
            return code.value==259 if kernel.GetExitCodeProcess(handle,ctypes.byref(code)) else None
        finally:kernel.CloseHandle(handle)
    try:os.kill(pid,0);return True
    except ProcessLookupError:return False
    except PermissionError:return None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'data/operational/vrain_2026_11_09/download')
    parser.add_argument('--start',default='2015-01-01')
    parser.add_argument('--end',default='2024-12-31')
    parser.add_argument('--group-id',type=int,default=29)
    parser.add_argument('--interval',type=float,default=1.0)
    parser.add_argument('--login',action='store_true')
    parser.add_argument('--status',action='store_true')
    parser.add_argument('--stop',action='store_true')
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args();out=args.output_dir
    if args.status:
        path=out/'progress.json'
        status=json.loads(path.read_text(encoding='utf8')) if path.exists() else {'state':'not_started'}
        status['process_alive']=pid_running(status.get('pid'))
        print(json.dumps(status,indent=2));return
    if args.stop:
        out.mkdir(parents=True,exist_ok=True);(out/'STOP').write_text('Stop requested\n',encoding='utf8')
        print('Stop requested; the current request will finish first.');return
    planned_dates(args.start,args.end)
    if args.resume and (out/'STOP').exists():
        (out/'STOP').unlink()
    if args.login:
        username=input('Vrain username: ');password=getpass.getpass('Vrain password: ')
        session=login(username,password);password=None
        out.mkdir(parents=True,exist_ok=True);save_session(session,out/'session.dpapi')
        print('Session saved with Windows DPAPI; password not stored.');return
    if os.name=='nt':
        # Keep the computer awake while allowing its display to turn off.
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        result=collect(out,args.start,args.end,args.group_id,args.interval)
        print(json.dumps(result,indent=2))
    finally:
        if os.name=='nt':ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__=='__main__':main()
