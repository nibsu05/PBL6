"""Versioned Vrain update helpers; preserve channels and explicit time intervals.

The 2026-11-16 user request authorizes collecting 2025--2026. Earlier collector
guards and frozen training datasets remain unchanged. This module fits no model.
"""
from datetime import datetime,timedelta
from pathlib import Path
import hashlib
import json
import math
import re
import numpy as np
import pandas as pd

NAME='station_update_2026_11_16'
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/operational/vrain_update_2026_11_16'
OUT=ROOT/'data/processed'/NAME
PUBLIC=ROOT/'reports'/NAME
OLD=ROOT/'data/operational/vrain_2026_11_09'
CLOCK=re.compile(r'^(\d{2}):(\d{2}) (\d{2})/(\d{2})$')
FIRST='2021-01-01'
LAST='2026-11-15'  # last complete local source day before authorized update date


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.part')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
    tmp.replace(path)


def parse_day(payload,day,aliases,station_ids):
    """Return 24 source hour bins, raw values and QC, without filling missing rain.

    Unknown IDs, shifted clocks, duplicate entries and invalid values fail closed.
    Sum disagreement flags an entire station-day, retaining original values.
    """
    marked=pd.Timestamp(day)
    if not pd.Timestamp(FIRST)<=marked<=pd.Timestamp(LAST):raise ValueError('Day outside authorized release')
    if not isinstance(payload,dict) or not isinstance(payload.get('stats'),list):raise ValueError('Invalid daily schema')
    ids=list(station_ids);pos={s:i for i,s in enumerate(ids)}
    times=pd.date_range(marked-pd.Timedelta(hours=4),periods=24,freq='h')
    values=np.full((24,len(ids)),np.nan,dtype=np.float64);total=np.full(len(ids),np.nan,dtype=np.float64)
    clock_rows=set();summary_count=0;membership=None
    for row in payload['stats']:
        if not isinstance(row,dict) or not isinstance(row.get('stations'),list):raise ValueError('Invalid row')
        match=CLOCK.fullmatch(row.get('timePoint','').strip())
        index=None
        if match:
            hh,mm,dd,month=map(int,match.groups())
            if hh>23 or mm!=0:raise ValueError('Invalid hourly clock')
            possible=[]
            for year in (marked.year-1,marked.year,marked.year+1):
                try:possible.append(pd.Timestamp(datetime(year,month,dd,hh,mm)))
                except ValueError:pass
            if not possible:raise ValueError('Invalid date')
            time=min(possible,key=lambda t:abs(t-marked))
            if time not in times or time in clock_rows:raise ValueError('Duplicate or shifted clock')
            clock_rows.add(time);index=times.get_loc(time)
        else:
            if not row.get('timePoint') or re.match(r'^\d{2}:',row['timePoint']):raise ValueError('Malformed clock')
            summary_count+=1
        seen=set()
        for item in row['stations']:
            sid=str(item.get('id'))
            if sid not in aliases or aliases[sid] not in pos:raise ValueError('Unknown station alias')
            canonical=aliases[sid]
            if canonical in seen:raise ValueError('Duplicate station')
            seen.add(canonical)
            value=item.get('depth')
            if isinstance(value,str) and value.strip()=='-':continue
            if value is None or isinstance(value,bool):raise ValueError('Invalid rain value')
            value=float(value)
            if not math.isfinite(value) or value<0:raise ValueError('Invalid rain range')
            j=pos[canonical]
            if index is None:total[j]=value
            else:values[index,j]=value
        if membership is None:membership=seen
        elif membership!=seen:raise ValueError('Inconsistent daily station membership')
    if summary_count!=1 or len(clock_rows) not in (0,24):raise ValueError('Need one summary and zero or 24 hours')
    complete=np.isfinite(values).all(0)
    # Calculate the check in source precision, before the float32 storage cast.
    bad=complete & np.isfinite(total) & (np.abs(values.sum(0)-total)>1e-6)
    valid=np.isfinite(values)&~bad[None,:]
    metadata=dict(hourly_rows=len(clock_rows),station_count=len(membership or []),
                  numeric_cells=int(np.isfinite(values).sum()),wet_cells=int((values>0).sum()),
                  complete_station_days=int(complete.sum()),sum_mismatch_station_days=int(bad.sum()),
                  complete_qc_station_days=int(valid.all(0).sum()))
    return dict(raw=values.astype(np.float32),valid=valid,bad_daily_sum=bad,total=total,times=times,metadata=metadata)


def issue_contract(day):
    init=pd.Timestamp(day,tz='UTC')
    if init.hour or not pd.Timestamp('2024-12-29',tz='UTC')<=init<=pd.Timestamp('2026-11-12',tz='UTC'):
        raise ValueError('Cycle outside extended collection contract')
    return init,init+pd.Timedelta(hours=12)


def same_source_window(channel_codes,start,stop):
    """Prevent a history/target sample from silently spanning source namespaces."""
    window=np.asarray(channel_codes)[start:stop]
    return bool(len(window)==stop-start and len(window)>0 and np.isin(window,(0,1)).all() and (window==window[0]).all())


def combine_hourly(legacy,modern,legacy_valid,modern_valid):
    """One traceable convenience view; conflicting numbers remain missing."""
    legacy=np.asarray(legacy);modern=np.asarray(modern)
    lv=np.asarray(legacy_valid,bool);mv=np.asarray(modern_valid,bool)
    conflict=lv&mv&(np.abs(legacy-modern)>1e-6)
    code=np.where(conflict,3,np.where(lv,0,np.where(mv,1,-1))).astype('int8')
    rain=np.where(code==0,legacy,np.where(code==1,modern,np.nan)).astype('float32')
    return rain,code,conflict
