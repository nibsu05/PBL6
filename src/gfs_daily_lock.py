"""Freeze the exact protocol, source policy, data and training implementation."""
from datetime import datetime,timezone
import json
from src.gfs_daily import ROOT,BASE,PUBLIC,DATA,sha,write_json,load_protocol


def training_lock():
    load_protocol()
    paths=['src/gfs_daily.py','src/gfs_daily_models.py','src/gfs_daily_gru.py',
        'src/gfs_daily_lock.py','scripts/run_gfs_daily_trees.py','scripts/run_gfs_daily_gru.py',
        'scripts/build_gfs_daily.py','reports/'+PUBLIC.name+'/protocol.json',
        'reports/'+PUBLIC.name+'/source_coverage_policy.json']
    hashes={name:sha(ROOT/name) for name in paths}
    current=dict(code_and_protocol_sha256=hashes,dataset_sha256=sha(DATA/'dataset.parquet'))
    path=BASE/'training_lock.json'
    if path.exists():
        old=json.loads(path.read_text())
        for key in current:
            if old[key]!=current[key]:raise ValueError('Locked training inputs/code changed: '+key)
        return old
    if any((BASE/'models').iterdir()) or any((BASE/'tuning_models').glob('*')):
        raise ValueError('Cannot backdate a training lock after fitting')
    audit=json.loads((PUBLIC/'dataset_verification.json').read_text())
    if audit['status']!='passed' or audit['dataset_sha256']!=current['dataset_sha256']:raise ValueError('Validate dataset before fitting')
    current.update(locked_utc=datetime.now(timezone.utc).isoformat(),test2025_read=False)
    write_json(path,current);write_json(PUBLIC/'training_provenance.json',current)
    return current
