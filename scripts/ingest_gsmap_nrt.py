"""Nhập file rawNRTv8 đã tải chính thức; không lưu credential."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,sys
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import pandas as pd
from src.gsmap_nrt import decode_nrt_binary,features_for_context,interval_from_filename

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--file',type=Path,required=True)
    ap.add_argument('--source-uri',required=True,help='URL nguồn không có user/password; phải có/realtime_ver/v8/')
    args=ap.parse_args()
    uri=urlparse(args.source_uri)
    if uri.username or uri.password or uri.query:raise ValueError('SourceURI không được chứa thông tin đăng nhập/query')
    if uri.hostname not in ('hokusai.eorc.jaxa.jp','sharaku.eorc.jaxa.jp') or '/realtime_ver/v8/' not in uri.path:
        raise ValueError('Cần xác định nguồn JAXA rawNRTv8; không suy version từpopup')
    lo,hi=interval_from_filename(args.file.name)
    ingested=datetime.now(timezone.utc).isoformat()
    if pd.Timestamp(ingested)<hi:raise ValueError('Khoảngmưa chưa kếtthúc; không dùng nhưquantrắc')
    payload=args.file.read_bytes();grid=decode_nrt_binary(payload)
    context=pd.read_parquet(ROOT/'data/processed/dataset_v2/cells.parquet')
    cells=pd.read_parquet(ROOT/'data/processed/dataset_v2_danang/cells.parquet')
    frame=features_for_context(grid,context,cells.site)
    out=ROOT/'data/operational/gsmap_nrt_v8'/lo.strftime('%Y%m%dT%H00Z')
    out.mkdir(parents=True,exist_ok=True)
    frame.to_parquet(out/'features_danang.parquet',index=False)
    manifest=dict(product='GSMaP_NRT',algorithm_version=8,source_uri=args.source_uri,
        interval_start_utc=lo.isoformat(),interval_end_utc=hi.isoformat(),first_recorded_at_utc=ingested,
        acquisition_time_attested=False,sha256=hashlib.sha256(payload).hexdigest(),
        context_cells=len(context),target_cells=len(cells),
        finite_target_rows=int(frame.drop(columns='site').notna().all(axis=1).sum()),
        ready_for_ml=False,
        reason='Cần đủ lịch sử,thời điểm tải attested và kiểmđịnhMVK→NRT; nhậpfile không tựphátforecast.',
        missing_policy='Negative/nonfinite->NaN;5x5 dùng đúngcontext mask của datasetv2, không thêm pixelbiển.')
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(product=manifest['product'],target_cells=len(cells),finite_rows=manifest['finite_target_rows'],
                         interval_start_utc=lo.isoformat(),ready_for_ml=False),indent=2))
if __name__=='__main__':main()
