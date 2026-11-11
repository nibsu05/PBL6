"""Freeze daily-v2 before downloading/training; copy immutable pilot cache."""
from pathlib import Path
import json
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.gfs_daily import BASE,PUBLIC,DATA,PARENT,OLD_CACHE,protocol_definition,sha,write_json


def main():
    for folder in [BASE,PUBLIC,DATA,BASE/'days',BASE/'models']:
        folder.mkdir(parents=True,exist_ok=True)
    source=PARENT/'pilot_stations_private.csv';cohort=BASE/'cohort_private.csv'
    content=source.read_bytes()
    if cohort.exists() and cohort.read_bytes()!=content:
        raise ValueError('Cohort changed')
    cohort.write_bytes(content)
    definition=protocol_definition(sha(cohort));path=PUBLIC/'protocol.json'
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8'))!=definition:
            raise ValueError('Protocol is already frozen')
    else:write_json(path,definition)
    lock=BASE/'protocol_lock.json'
    if lock.exists() and json.loads(lock.read_text())['protocol_sha256']!=sha(path):
        raise ValueError('Protocol lock mismatch')
    write_json(lock,dict(protocol_sha256=sha(path)))
    preserved={}
    for directory in ['reports/gfs_station_pilot_2026_11_10','reports/gfs_station_57_2026_11_10','reports/gfs_station_slides_2026_11_10']:
        for p in (ROOT/directory).iterdir():
            if p.is_file():preserved[p.relative_to(ROOT).as_posix()]=sha(p)
    snapshot=BASE/'preserved_hashes.json'
    if snapshot.exists():
        if json.loads(snapshot.read_text())!=preserved:raise ValueError('Frozen earlier results changed')
    else:write_json(snapshot,preserved)
    copied=0
    for source in (OLD_CACHE/'days').glob('*'):
        if source.suffix not in ('.json','.npz'):continue
        destination=BASE/'days'/source.name
        if not destination.exists():shutil.copy2(source,destination);copied+=1
        elif sha(source)!=sha(destination):raise ValueError('Copied cache changed')
    write_json(PUBLIC/'preparation.json',dict(status='protocol_frozen',protocol_sha256=sha(path),station_count=57,
        source_cache_days_reused=len(list((OLD_CACHE/'days').glob('*.npz'))),copied_files=copied,
        earlier_public_files_preserved=len(preserved),test2025_read=False))
    print(json.dumps(dict(status='protocol_frozen',copied=copied,protocol_sha256=sha(path))),flush=True)


if __name__=='__main__':main()
