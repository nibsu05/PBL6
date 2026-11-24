"""Audit saved exports only; never log in, download data, or read 2025 probes."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.vrain_export_audit import inventory_from_groups, audit_history


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, default=ROOT/'data/operational/vrain_2026_11_09')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'reports/vrain_research_plan_2026_11_09')
    parser.add_argument('--sum-tolerance-source-units', type=float, default=1e-6)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sources = []
    def load(path):
        raw = path.read_bytes()
        value = json.loads(raw.decode('utf8'))
        sources.append(dict(path=str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name,
                            sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                            schema={'groups_v2_private.json':'current_groups_v2',
                                    'groups_private.json':'legacy_endpoint_groups_v1'}.get(path.name,'history_stats_table')))
        return value
    inventory = inventory_from_groups(load(args.input_dir/'groups_v2_private.json'))
    legacy_path = args.input_dir/'groups_private.json'
    legacy = inventory_from_groups(load(legacy_path)) if legacy_path.exists() else None
    private_csv = args.input_dir/'inventory_stations_private.csv'
    with private_csv.open('w', encoding='utf8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(inventory[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(inventory)
    if legacy:
        with (args.input_dir/'inventory_v1_stations_private.csv').open('w', encoding='utf8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(legacy[0]), lineterminator='\n')
            writer.writeheader(); writer.writerows(legacy)
    probes, skipped = [], []
    for path in sorted(args.input_dir.glob('history_*.json')):
        match = re.fullmatch(r'history_(\d{4}-\d{2}-\d{2})\.json', path.name)
        if not match:
            raise ValueError('Unexpected history filename; refusing ambiguous date')
        date = match.group(1)
        if date.startswith('2025-'):
            skipped.append(path.name)
            continue
        audit = audit_history(load(path), date, inventory, args.sum_tolerance_source_units, legacy)
        probes.append(audit)
    if not probes:
        raise ValueError('No non-2025 probes found')
    report = dict(status='structural_audit_complete', declared_audit_date='2026-11-09',
                  scope='Saved current inventory and selected daily history probes only; not a full archive audit',
                  authentication_attempted=False, new_downloads=False, training_performed=False,
                  test2025_read=False, skipped_2025_files=skipped,
                  current_inventory=dict(stations=len(inventory), groups=len({r['group_name'] for r in inventory}),
                      latitude_min=min(r['latitude'] for r in inventory), latitude_max=max(r['latitude'] for r in inventory),
                      longitude_min=min(r['longitude'] for r in inventory), longitude_max=max(r['longitude'] for r in inventory),
                      altitude_missing=sum(r['altitude'] is None for r in inventory)),
                  v1_endpoint_inventory=dict(stations=len(legacy),
                      latitude_min=min(r['latitude'] for r in legacy), latitude_max=max(r['latitude'] for r in legacy),
                      longitude_min=min(r['longitude'] for r in legacy), longitude_max=max(r['longitude'] for r in legacy),
                      altitude_missing=sum(r['altitude'] is None for r in legacy)) if legacy else None,
                  probe_count=len(probes), probes_with_24_hourly_rows=sum(r['hourly_rows']==24 for r in probes),
                  probes_without_hourly_rows=sum(r['hourly_rows']==0 for r in probes),
                  timestamps_are_unresolved_clock_labels=True, historical_to_v2_crosswalk_confirmed=False,
                  historical_ids_match_v1_inventory=bool(legacy) and all(
                      r['exact_v1_station_id_matches']==r['nstation_union'] and
                      r['exact_v1_uuid_matches']==r['nstation_union'] for r in probes),
                  notes=['Zero summary without hourly rows is no hourly data, not a confirmed dry day.',
                         'Missing depth dash stays missing; missing hourly rows are counted separately.',
                         'One nonclock row is a summary candidate; it is excluded from hourly observations.',
                         'Sum comparisons only use stations with 24 numeric cells, and do not establish interval semantics.',
                         'Name equality is diagnostic only, never an accepted historical/current ID crosswalk.',
                         'V1 and V2 current-export inventories have distinct identifiers; matching V1 IDs does not certify historical station positions.',
                         'Current inventory coordinates and historical clock rows do not establish network coverage over all years.'],
                  sources=sources, probes=probes)
    (args.output_dir/'access_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf8', newline='\n')
    scalar_fields = [k for k in probes[0] if k!='missing_cells_codes']
    with (args.output_dir/'history_probe_summary.csv').open('w', encoding='utf8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=scalar_fields, lineterminator='\n')
        writer.writeheader(); writer.writerows({k:r[k] for k in scalar_fields} for r in probes)
    print(json.dumps({k:report[k] for k in ('status','probe_count','probes_with_24_hourly_rows','probes_without_hourly_rows','test2025_read')}, indent=2))


if __name__=='__main__':
    main()
