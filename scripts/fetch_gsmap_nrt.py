"""Kiểm tra và tải tệp GSMaP NRT v8 từ JAXA; chỉ nhận credential qua stdin."""
import argparse
import ftplib
import getpass
import hashlib
import json
import re
import ssl
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.gsmap_nrt import decode_nrt_binary

HOST = 'hokusai.eorc.jaxa.jp'
DIRECTORY = '/realtime_ver/v8/latest/'
FILE_PATTERN = re.compile(r'gsmap_(?:nrt|gauge)\.\d{8}\.\d{2}00\.dat\.gz')


def credentials():
    if sys.stdin.isatty():
        uid = input('JAXA UID: ').strip()
        pw = getpass.getpass('JAXA password (hidden): ')
    else:
        uid = sys.stdin.readline().strip()
        pw = sys.stdin.readline().rstrip('\r\n')
    if not uid or not pw:
        raise RuntimeError('Credential stdin unavailable; run in an interactive terminal')
    return uid, pw


def connect(allow_plain_ftp, announce=True):
    client = ftplib.FTP_TLS(context=ssl.create_default_context())
    client.connect(HOST, 21, timeout=25)
    try:
        client.auth()
        return client, 'FTPS'
    except ftplib.error_perm as exc:
        client.close()
        if str(exc)[:3] not in ('500', '502', '504'):
            raise
        if not allow_plain_ftp:
            raise RuntimeError('JAXA does not offer FTPS; rerun with --allow-plain-ftp')
        if announce:
            print('TRANSPORT FTP_PLAINTEXT (JAXA server does not support FTPS)', flush=True)
        plain = ftplib.FTP()
        plain.connect(HOST, 21, timeout=25)
        return plain, 'FTP_PLAINTEXT'


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--hours', type=int, default=1, help='số giờ/tệp mới nhất, 1–48')
    ap.add_argument('--check-only', action='store_true', help='xác minh đăng nhập và liệt kê, không tải/ghi tệp')
    ap.add_argument('--product', choices=('raw', 'gauge'), default='raw', help='raw NRT làm đầu vào hoặc Gauge NRT để đối chiếu')
    ap.add_argument('--at', help='chọn đúng giờ UTC YYYYMMDDHH thay vì tệp mới nhất')
    ap.add_argument('--allow-plain-ftp', action='store_true', help='cho phép FTP không mã hóa nếu JAXA không hỗ trợ FTPS')
    args = ap.parse_args()
    if not 1 <= args.hours <= 48:
        ap.error('--hours must be 1–48')
    if args.at and not re.fullmatch(r'\d{10}', args.at):
        ap.error('--at must be YYYYMMDDHH (UTC)')
    prefix = 'gsmap_nrt' if args.product == 'raw' else 'gsmap_gauge'
    product = 'GSMaP_NRT' if args.product == 'raw' else 'GSMaP_Gauge_NRT'
    try:
        uid, pw = credentials()
        client, transport = connect(args.allow_plain_ftp)
        try:
            client.login(uid, pw)
            pw = None
            if transport == 'FTPS':
                client.prot_p()
            client.cwd(DIRECTORY)
            files = sorted({Path(x).name for x in client.nlst()
                            if FILE_PATTERN.fullmatch(Path(x).name) and Path(x).name.startswith(prefix + '.')})
            if not files:
                raise RuntimeError('No matching NRT gz files in JAXA directory')
            selected = [prefix + '.' + args.at[:8] + '.' + args.at[8:] + '00.dat.gz'] if args.at else files[-args.hours:]
            if any(name not in files for name in selected):
                raise RuntimeError('Requested UTC hour is not in latest/; use archive or another hour')
            public = dict(authenticated=True, host=HOST, transport=transport,
                          directory=DIRECTORY, algorithm_version=8,
                          product=product, available_files=len(files),
                          last_file=files[-1], credential_persisted=False)
            if args.check_only:
                print('JAXA_OK ' + json.dumps(public), flush=True)
                return
            out = ROOT / 'data/operational/jaxa_downloads' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + args.product)
            out.mkdir(parents=True, exist_ok=True)
            rows = []
            for name in selected:
                path = out / name
                with path.open('wb') as f:
                    client.retrbinary('RETR ' + name, f.write)
                body = path.read_bytes()
                grid = decode_nrt_binary(body)
                rows.append(dict(file=name, bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                                 first_recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                                 decoded_shape=list(grid.shape),
                                 source_uri='ftp://' + HOST + DIRECTORY + name))
                print('DOWNLOADED ' + name + ' bytes=' + str(len(body)) + ' shape=' + str(grid.shape), flush=True)
            result = dict(public, files=rows)
            (out / 'manifest.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            report = ROOT / 'reports/followup_danang'
            report.mkdir(parents=True, exist_ok=True)
            public['downloaded_files'] = len(rows)
            status_name = 'jaxa_ftp_status.json' if args.product == 'raw' else 'jaxa_gauge_ftp_status.json'
            (report / status_name).write_text(json.dumps(public, indent=2), encoding='utf-8')
            print('JAXA_OK ' + json.dumps(public), flush=True)
        finally:
            try:
                client.quit()
            except Exception:
                client.close()
    except Exception as exc:
        code = ' code=' + str(exc)[:3] if isinstance(exc, ftplib.Error) else ''
        reason = ' reason=' + str(exc) if isinstance(exc, RuntimeError) else ''
        print('JAXA_FAILED type=' + type(exc).__name__ + code + reason, flush=True)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
