"""API thử nghiệm từ checkpoint thật. Chỉ validation lưu trữ, chưa forecast live.

Chạy: .venv/Scripts/python.exe demo/domain_api.py --port 8766
GET /health, /api/meta, /api/predict?year=2023&config=DOMAIN&site=...&issue=...UTC
"""
from __future__ import annotations
import argparse,json,sys
from functools import lru_cache
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import torch
from src.domain_inference import ArchivePredictor,REPORT,PRIVATE

@lru_cache(maxsize=3)
def predictor(year,config):
    return ArchivePredictor(year,config)

def metadata():
    run=json.loads((REPORT/'run.json').read_text(encoding='utf-8'))
    years=[y for y in run['args']['years'] if (PRIVATE/str(y)/'LightGBM_DOMAIN.npz').exists()]
    return dict(mode='archive_validation',operational_ready=False,years=years,
                configs=['BASE','RAW','DOMAIN'],cells=run['cells'],git_commit=run['git_commit'],
                note='Suy luận checkpoint Bi-LSTM3seed; dữ liệu hồi cứu. Không phải dự báo hôm nay.')

def forecast(query):
    year=int(query.get('year',['2023'])[0]);config=query.get('config',['DOMAIN'])[0]
    site=query['site'][0];time=pd.Timestamp(query['issue'][0])
    if time.tzinfo is not None:time=time.tz_convert('UTC').tz_localize(None)
    p=predictor(year,config)
    cell=np.flatnonzero(p.ds.cells.site.to_numpy()==site)
    if len(cell)!=1:raise ValueError('Site không hợp lệ')
    issue=p.ds.hours.get_indexer([time])[0]
    result=p.predict([[cell[0],issue]])
    return dict(site=site,issued_utc=time.isoformat(),config=config,year=year,
                **{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in result.items()})

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed=urlparse(self.path)
        try:
            if parsed.path=='/health':body=dict(ok=True,mode='archive_validation',operational_ready=False)
            elif parsed.path=='/api/meta':body=metadata()
            elif parsed.path=='/api/predict':body=forecast(parse_qs(parsed.query))
            else:self.send_error(404);return
            status=200
        except (ValueError,KeyError,StopIteration) as exc:
            body=dict(error=str(exc),mode='archive_validation');status=400
        except (FileNotFoundError,json.JSONDecodeError):
            body=dict(error='Chưa đủ artifact của fold; hãy hoàn tất training trước.',mode='archive_validation');status=503
        raw=json.dumps(body,ensure_ascii=False,allow_nan=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store')
        self.end_headers();self.wfile.write(raw)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port',type=int,default=8766)
    args=ap.parse_args()
    torch.set_num_threads(2)
    with ThreadingHTTPServer(('127.0.0.1',args.port),Handler) as server:
        print(f'Archive API http://127.0.0.1:{args.port}, không forecast live',flush=True)
        server.serve_forever()
if __name__=='__main__':main()
