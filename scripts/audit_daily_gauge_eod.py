"""Audit raw ISD 24-hour timestamps and GSOD G-date correspondence, <=2023."""
from collections import Counter
from pathlib import Path
import gzip
import hashlib
import json
import re
import urllib.request
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'data/operational/daily_gauge_2026_11_04/source_probe'
REPORT=ROOT/'reports/daily_gauge_2026_11_04'


def main():
    results=[]
    for year in [2015,2019,2021,2022,2023]:
        url=f'https://www.ncei.noaa.gov/pub/data/noaa/{year}/488550-99999-{year}.gz'
        path=PRIVATE/f'noaa_isd_488550_{year}.gz'
        if not path.exists():
            with urllib.request.urlopen(url,timeout=40) as r:path.write_bytes(r.read())
        lines=gzip.decompress(path.read_bytes()).decode().splitlines();rows=[]
        for line in lines:
            additional=line[105:].split('REM',1)[0]
            for group,duration,value,condition,quality in re.findall(r'AA([1-4])(\d{2})(\d{4})([0-9A-Z])([0-9])',additional):
                if duration=='24' and value!='9999':
                    rows.append(dict(end=pd.to_datetime(line[15:27],format='%Y%m%d%H%M',utc=True),
                        mm=int(value)/10.,condition=condition,quality=quality))
        frame=pd.DataFrame(rows)
        matched=frame[frame.end.dt.hour==12].copy()
        matched['date']=matched.end.dt.tz_localize(None).dt.normalize()
        # Distinct reports with conflicting depths are excluded from this date check.
        disagreement=matched.groupby('date').mm.nunique()
        matched=matched[matched.date.isin(disagreement[disagreement==1].index)].drop_duplicates('date')
        gsod=pd.read_csv(ROOT/f'data/raw_data/gsod/48855099999_{year}.csv',dtype={'PRCP_ATTRIBUTES':str})
        gsod['date']=pd.to_datetime(gsod.DATE)
        gsod=gsod[(gsod.PRCP_ATTRIBUTES.str.strip()=='G')&(gsod.PRCP<99)]
        pair=matched.merge(gsod[['date','PRCP']],on='date',validate='one_to_one')
        error=(pair.mm-pair.PRCP*25.4).abs()
        result=dict(year=year,source=url,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            raw_rows=len(lines),nonmissing_depth_24h_records=len(frame),
            end_hours_utc={str(k):int(v) for k,v in frame.end.dt.hour.value_counts().items()},
            condition_codes=dict(Counter(frame.condition)),quality_codes=dict(Counter(frame.quality)),
            gsod_G_matches_at_same_marked_date=len(pair),
            fraction_G_matches_within_03mm=float((error<=.3).mean()),
            median_absolute_rounding_difference_mm=float(error.median()))
        results.append(result)
    total=sum(r['nonmissing_depth_24h_records'] for r in results)
    at12=sum(r['end_hours_utc'].get('12',0) for r in results)
    out=dict(status='audited',station_id='488550-99999',years=results,records_24h=total,records_at_12UTC=at12,
        interpretation='Raw 24-hour accumulation timestamps predominantly end12UTC; GSOD G-date is not proof of a midnight-to-midnight rain interval',
        limits='One station ID and five development years only; condition/quality codes retained, not a certification of every rain depth or of the entire CPC region',
        format_document='https://www.ncei.noaa.gov/pub/data/noaa/isd-format-document.pdf',
        test2025_read=False)
    (REPORT/'station_eod_audit.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(out,indent=2))


if __name__=='__main__':main()
