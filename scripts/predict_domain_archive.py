"""Chạy suy luận thật checkpoint trong archive; không phát forecast live."""
from pathlib import Path
import argparse,json,sys
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from src.domain_inference import ArchivePredictor,parity_check

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--year',type=int,default=2021)
    ap.add_argument('--config',choices=['BASE','RAW','DOMAIN'],default='DOMAIN')
    ap.add_argument('--site')
    ap.add_argument('--issue',help='Giờ bắt đầu dự báo,UTC,VD2021-10-10T06:00')
    ap.add_argument('--parity',action='store_true')
    args=ap.parse_args()
    if args.parity:
        out=parity_check(args.year)
        path=ROOT/'reports/domain_screen_danang/inference_parity.json'
        if path.exists():
            previous=json.loads(path.read_text(encoding='utf-8'))
            out['rows']=[r for r in previous['rows'] if r['year']!=args.year]+out['rows']
        path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    else:
        predictor=ArchivePredictor(args.year,args.config)
        if not args.site or not args.issue:ap.error('Cần --site và --issue')
        cell=np.flatnonzero(predictor.ds.cells.site.to_numpy()==args.site)
        if len(cell)!=1:raise ValueError('Site không hợp lệ')
        issue=pd.Timestamp(args.issue)
        if issue.tzinfo is not None:issue=issue.tz_convert('UTC').tz_localize(None)
        t=predictor.ds.hours.get_indexer([issue])[0]
        out=predictor.predict([[cell[0],t]])
        out=dict(site=args.site,issue_utc=issue.isoformat(),config=args.config,
                 **{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in out.items()})
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
