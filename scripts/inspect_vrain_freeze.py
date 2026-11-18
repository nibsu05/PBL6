"""Build private station matrices and count training-only panel candidates."""
from pathlib import Path
import gzip
import hashlib
import json
import re
import sys
from datetime import datetime,timedelta

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.vrain_export_audit import inventory_from_groups


def main():
    base=ROOT/'data/operational/vrain_2026_11_09'
    out=base/'freeze_work';out.mkdir(exist_ok=True)
    inv=inventory_from_groups(json.loads((base/'groups_private.json').read_text(encoding='utf8')))
    ids=[r['station_id'] for r in inv];positions={s:i for i,s in enumerate(ids)}
    days=pd.date_range('2021-01-01','2024-12-31',freq='D').as_unit('ns')
    rain=np.full((len(days),24,len(ids)),np.nan,dtype=np.float32)
    bad=np.zeros((len(days),len(ids)),bool);ends=[];source_hashes={}
    for di,day in enumerate(days):
        name=day.strftime('%Y-%m-%d');path=base/'download/raw'/name[:4]/(name+'.json.gz')
        compressed=path.read_bytes();source_hashes[name]=hashlib.sha256(compressed).hexdigest()
        data=json.loads(gzip.decompress(compressed));clock=[];total=None
        for row in data['stats']:
            match=re.fullmatch(r'(\d{2}):(\d{2}) (\d{2})/(\d{2})',row['timePoint'])
            values=np.full(len(ids),np.nan,dtype=np.float64)
            for station in row['stations']:
                value=station['depth'];index=positions[station['id']]
                if value!='-':values[index]=float(value)
            if match:
                hh,mm,dd,month=map(int,match.groups())
                candidates=[]
                for year in [day.year-1,day.year,day.year+1]:
                    try:candidates.append(datetime(year,month,dd,hh,mm))
                    except ValueError:pass
                clock.append((min(candidates,key=lambda t:abs(t-day.to_pydatetime())),values))
            else:total=values
        clock.sort(key=lambda x:x[0]);assert len(clock)==24 and total is not None
        values=np.stack([v for _,v in clock]);assert np.isfinite(values).all() or not np.isinf(values).any()
        assert np.nanmin(values)>=0
        complete=np.isfinite(values).all(0)&np.isfinite(total)
        bad[di]=complete&(np.abs(np.nansum(values,axis=0)-total)>1e-6)
        rain[di]=values;ends.extend(t for t,_ in clock)
    times=pd.DatetimeIndex(ends).as_unit('ns');assert times.is_unique and (np.diff(times.asi8)==3600_000_000_000).all()
    valid=np.isfinite(rain)&~bad[:,None,:]
    candidates=[]
    for threshold in [.90,.95,.98,.99,.995]:
        fractions=[valid[days.year==year].mean((0,1)) for year in [2021,2022]]
        selected=np.flatnonzero(np.minimum(*fractions)>=threshold)
        hours=valid[:,:,selected].all(2) if len(selected) else np.zeros(rain.shape[:2],bool)
        whole=hours.all(1)
        candidates.append({'threshold':threshold,'stations':len(selected),'hours_by_year':{str(y):int(hours[days.year==y].sum()) for y in [2021,2022,2023,2024]},'days_by_year':{str(y):int(whole[days.year==y].sum()) for y in [2021,2022,2023,2024]}})
    np.savez_compressed(out/'station_matrices.npz',rain=rain,valid=valid,bad_daily_sum=bad,clock_end_naive=times.asi8,marked_day=days.values.astype('datetime64[ns]'),station_ids=np.asarray(ids))
    stats=pd.DataFrame(inv)
    for year in [2021,2022,2023,2024]:stats[f'valid_fraction_{year}']=valid[days.year==year].mean((0,1))
    stats.to_csv(out/'station_inventory_qc.csv',index=False)
    report={'status':'station_matrix_inspected','days':len(days),'clock_rows':len(times),'stations':len(ids),'sum_flagged_station_days':int(bad.sum()),'source_time_semantics_confirmed':False,'panel_candidates':candidates,'source_gzip_sha256':source_hashes,'test2025_read':False}
    (out/'inspection.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='source_gzip_sha256'},indent=2),flush=True)


if __name__=='__main__':main()
