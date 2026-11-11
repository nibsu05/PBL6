"""Metadata-only source audit and authenticated current Vrain snapshot.

No 2025 requests, no observations for fitting, no credentials in reports.
Current timestamps support a feasibility check, not historical latency proof.
"""
from pathlib import Path
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import re
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import requests
from src.gfs_daily import BASE,PUBLIC,VRAIN,write_json,load_protocol
from src.vrain_download import load_session,ORIGIN
from src.gfs_station import choose_records,parse_index
from scripts.collect_gfs_station_pilot import range_bytes


def current_metadata():
    now=datetime.now(timezone.utc);day=now.strftime('%Y%m%d')
    records=[]
    with requests.Session() as session:
        for lead in (12,24,36,48,60,72,84):
            url=f'https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{day}/00/atmos/gfs.t00z.pgrb2.0p25.f{lead:03d}'
            try:
                response=session.head(url,timeout=(10,30));item=dict(lead=lead,status=response.status_code)
                if response.ok and response.headers.get('Last-Modified'):
                    modified=pd.Timestamp(parsedate_to_datetime(response.headers['Last-Modified']))
                    item.update(last_modified_utc=modified.isoformat(),modified_minus_init_hours=float((modified-pd.Timestamp(day,tz='UTC'))/pd.Timedelta(hours=1)))
            except requests.RequestException as error:item=dict(lead=lead,error_type=type(error).__name__)
            records.append(item)
    return dict(captured_utc=now.isoformat(),cycle_day=day,method='HEAD only, no forecast values',records=records,
                interpretation='object modification time is not a delivery SLA or proof for historical cycles')


def vrain_snapshot():
    now=datetime.now(timezone.utc);local=pd.Timestamp(now).tz_convert('Asia/Ho_Chi_Minh');day=local.strftime('%Y-%m-%d')
    if local.year!=2026:raise ValueError('Latency audit may only query current 2026 data')
    folder=BASE/'latency_private';folder.mkdir(exist_ok=True)
    try:
        session=load_session(VRAIN/'download/session.dpapi')
        response=session.get(ORIGIN+'/api/vrain/private/v2/stats/summary',timeout=(10,45))
        if response.status_code in (401,403):return dict(status='login_required',historical_latency_proven=False)
        response.raise_for_status();groups=response.json()
        chosen=[g for g in groups if any(int(s.get('groupId',-1))==29 for s in g.get('stats',[]))]
        if len(chosen)!=1 or not chosen[0].get('groupOrgUuid'):return dict(status='organization_context_unavailable',historical_latency_proven=False)
        organization=chosen[0]['groupOrgUuid'];captures=[]
        for namespace in ('legacy','modern'):
            url=ORIGIN+('/api/vrain/private/v1/groups/29/stats/details' if namespace=='legacy' else '/api/kttv/private/v1/organizations/details')
            kwargs=dict(params={'from':day,'to':day},timeout=(10,60))
            if namespace=='modern':kwargs['params']['i']='_1h';kwargs['headers']={'x-org-uuid':organization}
            retrieved=datetime.now(timezone.utc);r=session.get(url,**kwargs)
            record=dict(namespace=namespace,http_status=r.status_code,retrieved_utc=retrieved.isoformat())
            if r.ok and 'json' in r.headers.get('Content-Type',''):
                payload=r.json();token=retrieved.strftime('%Y%m%dT%H%M%SZ')
                private=folder/f'{namespace}_{token}.json';private.write_bytes(r.content)
                record['response_sha256']=hashlib.sha256(r.content).hexdigest()
                record['top_level_fields']=list(payload) if isinstance(payload,dict) else ['list']
                record['hourly_rows']=sum(bool(re.fullmatch(r'\d{2}:\d{2} \d{2}/\d{2}',str(row.get('timePoint','')))) for row in payload.get('stats',[])) if isinstance(payload,dict) else 0
                rows=payload.get('stats',[]) if isinstance(payload,dict) else []
                record['row_fields']=sorted({k for row in rows if isinstance(row,dict) for k in row})
                record['rainfall_ingestion_timestamp_available']='not established from response schema'
                record['interpretation']='hour-bin labels alone do not establish ingestion time; current channel also cannot prove 2021-2024 delivery delay'
            captures.append(record)
        return dict(status='captured',query_day=day,captures=captures,used_for_model_fit=False,historical_latency_proven=False)
    except Exception as error:
        return dict(status='capture_unavailable',error_type=type(error).__name__,historical_latency_proven=False)


def historical_metadata():
    records=[];delays=[]
    for path in sorted((BASE/'days').glob('*.json')):
        metadata=json.loads(path.read_text());init=pd.Timestamp(metadata['init_utc']);issue=pd.Timestamp(metadata['issue_utc'])
        late=0
        for message in metadata['messages']:
            if not message.get('source_last_modified'):continue
            stamp=pd.Timestamp(parsedate_to_datetime(message['source_last_modified']))
            delays.append(float((stamp-init)/pd.Timedelta(hours=1)));late+=int(stamp>issue)
        records.append(dict(day=metadata['day'],year=init.year,late_messages=late))
    late_dates=[r['day'] for r in records if r['late_messages']]
    write_json(BASE/'latency_private/historical_late_dates.json',late_dates)
    result=dict(cycles_checked=len(records),messages_with_timestamp=len(delays),
        cycles_modified_after_issue=len(late_dates),late_by_year={str(y):sum(r['year']==y and r['late_messages']>0 for r in records) for y in range(2021,2025)},
        modified_minus_init_hours_quantiles=np.quantile(delays,[0,.5,.95,1]).tolist() if delays else [],
        historical_original_release_proven=False,
        interpretation='late archive modifications may reflect recopy; neither early nor late Last-Modified proves delivery to the user')
    return result


def confirm_missing_cycles():
    manifest=BASE/'collection_manifest.json'
    if not manifest.exists():return dict(status='collection_running')
    collection=json.loads(manifest.read_text());confirmed=[];unresolved=[]
    for day,error in collection['errors'].items():
        statuses=[]
        with requests.Session() as session:
            for lead in (12,24,36,48,60,72,84):
                found=False;checks=[]
                for layout in ('atmos/',''):
                    url=f'https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{day}/00/{layout}gfs.t00z.pgrb2.0p25.f{lead:03d}.idx'
                    try:
                        r=session.get(url,timeout=(10,30));checks.append(r.status_code)
                        if r.ok:found=True;break
                    except requests.RequestException:checks.append('network_error')
                statuses.append(dict(lead=lead,available=found,http_status=checks))
        inaccessible=[s for s in statuses if not s['available']]
        verified=bool(inaccessible) and all(all(code==404 for code in s['http_status']) for s in inaccessible)
        framing=[]
        if not inaccessible and 'GRIB framing' in error:
            # Independently re-fetch the official index and bad range twice.
            # A matching HTTP byte count is insufficient: the GRIB boundaries
            # must agree with that index. Never repair bytes or guess a field.
            with requests.Session() as session:
                for lead in (12,24,36,48,60,72,84):
                    url=f'https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{day}/00/atmos/gfs.t00z.pgrb2.0p25.f{lead:03d}'
                    r=session.get(url+'.idx',params={'audit':time.time_ns()},timeout=(10,40));r.raise_for_status()
                    for name,record in choose_records(parse_index(r.text),lead).items():
                        data,_=range_bytes(session,url,record.start,record.stop)
                        if data[:4]==b'GRIB' and data[-4:]==b'7777':continue
                        fresh,_=range_bytes(session,url+'?audit='+str(time.time_ns()),record.start,record.stop)
                        repeat_bad=fresh[:4]!=b'GRIB' or fresh[-4:]!=b'7777'
                        framing.append(dict(lead=lead,field=name,index_sha256=hashlib.sha256(r.content).hexdigest(),
                            range=[record.start,record.stop],first_sha256=hashlib.sha256(data).hexdigest(),
                            repeat_sha256=hashlib.sha256(fresh).hexdigest(),repeat_invalid=repeat_bad))
            verified=bool(framing) and all(r['repeat_invalid'] for r in framing)
        reason='official index and object bytes disagree on GRIB framing, confirmed by repeated range retrieval' if framing else 'required index missing in both official historical layouts'
        record=dict(day=day,checks=statuses,framing_checks=framing,reason=reason,observations_used=False)
        (confirmed if verified else unresolved).append(record)
    policy=dict(status='confirmed' if not unresolved else 'unresolved',planned_cycles=len(collection['planned_dates']),
        available_cycles=len(collection['completed_dates']),confirmed_source_missing=confirmed,unresolved=unresolved,
        policy='exclude only confirmed source-unavailable or structurally corrupt entire issue, identically for all models; do not replace source or choose days by rainfall',
        protocol_common_complete_mask=True,locked_before_fit=not (BASE/'training_lock.json').exists())
    if (BASE/'training_lock.json').exists():
        old=json.loads((PUBLIC/'source_coverage_policy.json').read_text())
        if [r['day'] for r in old['confirmed_source_missing']]!=[r['day'] for r in confirmed]:raise ValueError('Source exclusions changed after fitting lock')
        return old
    write_json(PUBLIC/'source_coverage_policy.json',policy)
    return policy


def main():
    p=load_protocol()
    result=dict(captured_utc=datetime.now(timezone.utc).isoformat(),current_gfs=current_metadata(),vrain=vrain_snapshot(),
        historical_gfs=historical_metadata(),source_coverage=confirm_missing_cycles(),
        gfs_delay_scenarios=[dict(delay_hours=d,same_cycle_eligible=bool(d<=12)) for d in p['gfs_delay_scenarios_hours']],
        gauge_delays=[1,3,6],test2025_read=False,recent_observations_used_for_fit=False,
        production_schedule_reference='https://www.nco.ncep.noaa.gov/pmb/nwprod/prodstat/production_status.html')
    write_json(PUBLIC/'source_latency_audit.json',result)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
