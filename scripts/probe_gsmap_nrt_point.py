"""Probe điểm JAXA công khai, lưu provenance; chưa làm đầu vàoML."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import requests
import pandas as pd

def parse_point(html,stamp,lat,lon):
    time_match=re.search(r'(\d{4}/\d{2}/\d{2})\s+(\d{2}:\d{2})\s+\(UTC\)',html)
    la=re.search(r'Latitude:\s*([-+\d.]+)',html)
    lo=re.search(r'Longitude:\s*([-+\d.]+)',html)
    rain=re.search(r'<h5>\s*Rain:\s*</h5>\s*<div>\s*([-+\d.]+)\s*mm/hr',html,re.I)
    if not all([time_match,la,lo,rain]):raise ValueError('Popup thiếu schema; không đoán từ màu ảnh')
    ts=pd.Timestamp(time_match.group(1)+' '+time_match.group(2),tz='UTC')
    if ts!=pd.Timestamp(stamp) or abs(float(la.group(1))-lat)>1e-5 or abs(float(lo.group(1))-lon)>1e-5:
        raise ValueError('Timestamp/tọa độ trảvề không khớp')
    value=float(rain.group(1))
    return dict(interval_start_utc=ts.isoformat(),interval_end_utc=(ts+pd.Timedelta(hours=1)).isoformat(),
                rain_rate_mm_h=value if value>=0 else None)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--time',help='UTC HH:00; mặcđịnh lùi5h')
    ap.add_argument('--mode',choices=['NRT','NOW'],default='NRT')
    ap.add_argument('--lat',type=float,default=16.05);ap.add_argument('--lon',type=float,default=108.15)
    args=ap.parse_args()
    stamp=pd.Timestamp(args.time) if args.time else pd.Timestamp(datetime.now(timezone.utc)-timedelta(hours=5)).floor('h')
    stamp=stamp.tz_localize('UTC') if stamp.tzinfo is None else stamp.tz_convert('UTC')
    if stamp.minute or stamp.second:raise ValueError('Chỉ cửa sổ1h bắt đầuHH:00')
    retrieved=datetime.now(timezone.utc).isoformat()
    family='GSMaP_NOW' if args.mode=='NOW' else 'GSMaP'
    base='https://sharaku.eorc.jaxa.jp'
    token=stamp.strftime('%Y%m%d%H00')
    mode_url=f'{base}/{family}/map_data/mode/{stamp.year}/gsmap_mode.{stamp:%Y%m%d}.{stamp:%H}00.txt'
    mode=requests.get(mode_url,timeout=25);mode.raise_for_status()
    actual=mode.text.strip()
    if actual!=args.mode:raise ValueError(f'Nguồnđãđổi sảnphẩm:requested{args.mode},actual{actual}')
    params=dict(prod='rain',ymd=token,lat=args.lat,lon=args.lon)
    response=requests.get(f'{base}/cgi-bin/trmm/{family}/tilemap/pick.cgi',params=params,timeout=25)
    response.raise_for_status()
    request_started=retrieved
    retrieved=datetime.now(timezone.utc).isoformat()
    result=parse_point(response.text,stamp,args.lat,args.lon)
    identifier=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    private=ROOT/'data/operational/nrt_point_probe'/identifier
    private.mkdir(parents=True,exist_ok=True)
    (private/'popup.html').write_bytes(response.content);(private/'mode.txt').write_bytes(mode.content)
    result.update(source='JAXA Global Rainfall Watch public point display',product_mode=actual,
        algorithm_version='not_attested_by_point_response',latitude=args.lat,longitude=args.lon,
        retrieved_at_utc=retrieved,request_started_at_utc=request_started,ready_for_ml=False,
        latency_from_interval_end_h=(pd.Timestamp(retrieved)-stamp-pd.Timedelta(hours=1)).total_seconds()/3600,
        point_url=response.url,mode_url=mode_url,
        html_sha256=hashlib.sha256(response.content).hexdigest(),mode_sha256=hashlib.sha256(mode.content).hexdigest(),
        caveats=['Popup làm tròn, thiếu qualityflag và version; endpoint không phảiAPIổnđịnh.',
                 'TimeInformation là tuổi microwave, không phải latency côngbố.',
                 'MuốnMLcần binaryNRTv8,buffercontext và kiểmđịnh khácbiệtMVK→NRT.'])
    (private/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    latest=ROOT/'data/operational/nrt_point_probe/latest.json'
    latest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    report=ROOT/'reports/followup_danang'
    report.mkdir(parents=True,exist_ok=True)
    public={k:result[k] for k in ['source','product_mode','algorithm_version','retrieved_at_utc','ready_for_ml',
                                 'latency_from_interval_end_h','point_url','mode_url','html_sha256','mode_sha256']}
    (report/'nrt_access_status.json').write_text(json.dumps(public,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(public,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
