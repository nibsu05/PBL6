"""Demo Đà Nẵng từ checkpoint thật; archive và forecast nguồn tách chế độ."""
from __future__ import annotations
import argparse,json,sys
from functools import lru_cache
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import torch
from src.domain_inference import ArchivePredictor,TreeArchivePredictor,REPORT,PRIVATE
from src.dataloader_v2 import DatasetV2

@lru_cache(maxsize=1)
def dataset():return DatasetV2(ROOT/'data/processed/dataset_v2_danang')
@lru_cache(maxsize=6)
def predictor(year,config,scope='trained'):
    return TreeArchivePredictor(year,config) if config.startswith('TREE_') else ArchivePredictor(year,config,scope=scope)

def metadata():
    run=json.loads((REPORT/'run.json').read_text(encoding='utf-8'))
    ds=dataset();trained={r['site'] for r in run['cells']}
    cells=ds.cells[['site','lat','lon','elev_mean_m','coast_dist_km']].to_dict('records')
    for cell in cells:cell['trained']=cell['site'] in trained
    configs=[dict(id='RAW',label='Bi-LSTM · biến thô',unseen=True),
             dict(id='DOMAIN',label='Bi-LSTM · gió–ẩm–địa hình',unseen=True),
             dict(id='TREE_L1',label='LightGBM · đầu lượng mưa cũ',unseen=False),
             dict(id='TREE_TWEEDIE',label='LightGBM · lượng mưa Tweedie',unseen=False)]
    path=ROOT/'reports/followup_danang/bilstm_tweedie/run.json'
    if path.exists() and json.loads(path.read_text(encoding='utf-8')).get('completed'):
        configs.append(dict(id='RAW_TWEEDIE',label='Bi-LSTM · lượng mưa Tweedie',unseen=False))
    return dict(mode='archive_validation',operational_ready=False,years=[2021,2022,2023],
                configs=configs,cells=cells,git_commit=run['git_commit'],
                note='Checkpoint thật; nhãn GSMaP GC; dữ liệu hồi cứu, chưa là dự báo AI hôm nay.')

def inputs(query):
    year=int(query.get('year',['2023'])[0])
    if year not in (2021,2022,2023):raise ValueError('Chỉ các năm validation2021–2023; test2025 giữ kín')
    config=query.get('config',['DOMAIN'])[0]
    if config not in ('RAW','DOMAIN','TREE_L1','TREE_TWEEDIE','RAW_TWEEDIE'):raise ValueError('Cấu hình không hợp lệ')
    stamp=pd.Timestamp(query['issue'][0])
    stamp=stamp.tz_convert('UTC').tz_localize(None) if stamp.tzinfo is not None else stamp
    if stamp.year!=year:raise ValueError('Ngày không khớp năm')
    return year,config,stamp

def forecast(query):
    year,config,stamp=inputs(query);site=query['site'][0]
    ds=dataset();cells=np.flatnonzero(ds.cells.site.to_numpy()==site)
    if len(cells)!=1:raise ValueError('Ô không có trong vùng nghiên cứu')
    trained={c['site'] for c in metadata()['cells'] if c['trained']}
    scope='trained' if site in trained else 'unseen'
    if scope=='unseen' and config not in ('RAW','DOMAIN'):raise ValueError('Cấu hình này đang kiểm chứng ở30ô; chọn ô đã train')
    p=predictor(year,config,scope)
    issue=ds.hours.get_indexer([stamp])[0]
    result=p.predict([[cells[0],issue]])
    obs=ds.cube[cells[0],issue:issue+6,ds.feature_index['y_gsmap_gc_mm']]
    return dict(site=site,issued_utc=stamp.isoformat()+'Z',config=config,year=year,
                observed_label_mm=np.asarray(obs,float).tolist(),
                **{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in result.items()})

def map_forecast(query):
    year,config,stamp=inputs(query);ds=dataset()
    issued=ds.hours.get_indexer([stamp])[0]
    meta=metadata();out=[]
    winter=(stamp+pd.Timedelta(hours=7)).month in (11,12,1,2)
    window=2 if winter else 0
    for scope in ['trained','unseen']:
        if scope=='unseen' and config not in ('RAW','DOMAIN'):continue
        p=predictor(year,config,scope)
        index=p.index[p.index[:,1]==issued]
        if len(index)==0:continue
        result=p.predict(index)
        for n,c in enumerate(index[:,0]):
            out.append(dict(site=ds.cells.iloc[c].site,scope=scope,
                            total_mm=float(result['amount_mm'][n,:6 if winter else 3].sum()),
                            probability_ge10=float(result['probability'][n,window,1])))
    if not out:raise ValueError('Không có cửa sổ hợp lệ tại giờ này')
    return dict(issued_utc=stamp.isoformat()+'Z',config=config,cells=out,window='6 giờ' if winter else '3 giờ',operational_ready=False)

def scores():
    rows=[]
    paths=[REPORT/'scores.csv',
           ROOT/'reports/followup_danang/amount/scores.csv',
           ROOT/'reports/followup_danang/bilstm_tweedie/scores.csv',
           ROOT/'reports/followup_danang/spatial/scores.csv']
    wanted=['BiLSTM_RAW','BiLSTM_DOMAIN','LightGBM_RAW','LightGBM_RAW_TWEEDIE','BiLSTM_RAW_TWEEDIE',
            'BiLSTM_RAW_unseen63','BiLSTM_DOMAIN_unseen63']
    for path in paths:
        if not path.exists():continue
        f=pd.read_csv(path)
        f=f[(f.season=='may_oct')&(f.window=='0-3h')&(f.source.isin(wanted))]
        rows+=f[['year','source','CSI_prob_10','CSI_amount_10','BSS_1','RMSE','bias','FAR_prob_10']].to_dict('records')
    unique={(r['year'],r['source']):r for r in rows}
    return dict(rows=list(unique.values()),note='Tháng5–10; validation lịch sử. CSI xác suất vàCSI lượngmưa khác nhau.')

def live_data(query):
    site=query.get('site',['c16.05_108.15'])[0]
    if site not in set(dataset().cells.site):raise ValueError('Ô không hợp lệ')
    folder=ROOT/'data/operational/domain_live_snapshots'
    directories=sorted([p for p in folder.iterdir() if p.is_dir() and (p/'manifest.json').exists()]) if folder.exists() else []
    result=dict(operational_ready=False,ai_forecast=None)
    if directories:
        latest=directories[-1];manifest=json.loads((latest/'manifest.json').read_text(encoding='utf-8'))
        entry=next(r for r in manifest['entries'] if r['site']==site and r['model']=='ecmwf_ifs')
        group=json.loads((latest/entry['file']).read_text(encoding='utf-8'))
        entries=[r for r in manifest['entries'] if r['file']==entry['file'] and r['model']=='ecmwf_ifs']
        position=[r['site'] for r in entries].index(site)
        payload=group[position] if isinstance(group,list) else group
        times=pd.to_datetime(payload['hourly']['time'],utc=True)
        start=pd.Timestamp(datetime.now(timezone.utc)).ceil('h')
        # precipitation ghi cuối khoảng: hour_end=start+1h -> [start,start+1h).
        selected=np.flatnonzero((times>start)&(times<=start+pd.Timedelta(hours=6)))
        result['ecmwf']=dict(site=site,source='ECMWF IFS9km quaOpen-Meteo',
            retrieved_at_utc=entry['retrieved_at_utc'],init_time_known=False,
            interval_end_utc=[times[i].isoformat() for i in selected],
            amount_mm=[payload['hourly']['precipitation'][i] for i in selected])
    point=ROOT/'data/operational/nrt_point_probe/latest.json'
    if point.exists():result['satellite_point']=json.loads(point.read_text(encoding='utf-8'))
    history=ROOT/'reports/followup_danang/nrt_history_readiness.json'
    if history.exists():result['nrt_history']=json.loads(history.read_text(encoding='utf-8'))
    return result

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed=urlparse(self.path)
        if parsed.path=='/':
            raw=(ROOT/'demo/research.html').read_bytes()
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
        try:
            q=parse_qs(parsed.query)
            if parsed.path=='/health':body=dict(ok=True,mode='archive_validation',operational_ready=False)
            elif parsed.path=='/api/meta':body=metadata()
            elif parsed.path=='/api/predict':body=forecast(q)
            elif parsed.path=='/api/map':body=map_forecast(q)
            elif parsed.path=='/api/scores':body=scores()
            elif parsed.path=='/api/live':body=live_data(q)
            else:self.send_error(404);return
            status=200
        except (ValueError,KeyError,StopIteration) as exc:
            body=dict(error=str(exc),mode='archive_validation');status=400
        except (FileNotFoundError,json.JSONDecodeError):
            body=dict(error='Chưa đủ dữ liệu/checkpoint của cấu hình.',mode='archive_validation');status=503
        raw=json.dumps(body,ensure_ascii=False,allow_nan=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store')
        self.end_headers();self.wfile.write(raw)

def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--port',type=int,default=8766)
    args=ap.parse_args();torch.set_num_threads(2)
    with ThreadingHTTPServer(('127.0.0.1',args.port),Handler) as server:
        print(f'Demo http://127.0.0.1:{args.port}, checkpoint archive + forecast nguồn',flush=True)
        server.serve_forever()
if __name__=='__main__':main()
