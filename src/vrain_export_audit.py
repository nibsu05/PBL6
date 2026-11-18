"""Structural/count-only checks for saved Vrain station and daily-table exports.

No authentication or network access. Clock labels identify hourly-looking rows;
they do not establish timezone, interval boundaries or measurement semantics.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
import math
import re

CLOCK = re.compile(r'^([0-2][0-9]):([0-5][0-9]) ([0-3][0-9])/([0-1][0-9])$')


def identifier(value, field):
    if not isinstance(value, (str, int)) or isinstance(value, bool) or not str(value).strip():
        raise ValueError(f'Invalid {field}')
    return str(value).strip()


def number(value, field):
    if isinstance(value, bool):
        raise ValueError(f'Invalid {field}')
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ValueError(f'Invalid numeric {field}') from None
    if not math.isfinite(result):
        raise ValueError(f'Nonfinite {field}')
    return result


def depth(value):
    if isinstance(value, str) and value.strip() == '-':
        return None
    result = number(value, 'depth')
    if result < 0:
        raise ValueError('Negative depth')
    return result


def inventory_from_groups(groups):
    if not isinstance(groups, list) or not groups:
        raise ValueError('Expected nonempty groups list')
    records, seen, seen_uuid = [], set(), set()
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get('stats'), list):
            raise ValueError('Expected group.stats list')
        for item in group['stats']:
            sid = identifier(item.get('stationID'), 'stationID')
            uuid = identifier(item.get('stationUuid'), 'stationUuid')
            if sid in seen or uuid in seen_uuid:
                raise ValueError('Duplicate or conflicting current inventory identifier')
            seen.add(sid); seen_uuid.add(uuid)
            lat, lon = number(item.get('lat'), 'latitude'), number(item.get('lng'), 'longitude')
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError('Coordinates out of bounds')
            altitude = None if item.get('alt') is None else number(item['alt'], 'altitude')
            records.append(dict(station_id=sid, station_uuid=uuid,
                                station_name=str(item.get('stationName', '')).strip(),
                                latitude=lat, longitude=lon, altitude=altitude,
                                group_name=str(group.get('groupName', ''))))
    if not records:
        raise ValueError('Empty current inventory')
    return records


def audit_history(payload, probe_date, inventory, sum_tolerance_source_units=1e-6, legacy_inventory=None):
    day = datetime.strptime(probe_date, '%Y-%m-%d')
    if day.year == 2025:
        raise ValueError('2025 is reserved and must not be audited')
    if sum_tolerance_source_units < 0 or not math.isfinite(sum_tolerance_source_units):
        raise ValueError('Invalid sum tolerance')
    if not isinstance(payload, dict) or not isinstance(payload.get('stats'), list):
        raise ValueError('Expected history.stats list')
    rows = payload['stats']
    hourly, summaries, clocks = [], [], []
    identities, reference_ids = {}, None
    names = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('timePoint'), str) or not isinstance(row.get('stations'), list):
            raise ValueError('Invalid history row schema')
        label = row['timePoint'].strip()
        match = CLOCK.fullmatch(label)
        if match:
            hh, mm, dd, month = map(int, match.groups())
            if hh > 23 or mm != 0:
                raise ValueError('Invalid or non-hourly clock label')
            candidates = []
            for year in (day.year - 1, day.year, day.year + 1):
                try:
                    candidate = datetime(year, month, dd, hh, mm)
                except ValueError:
                    continue
                candidates.append(candidate)
            if not candidates:
                raise ValueError('Invalid date in clock label')
            clock = min(candidates, key=lambda v: abs((v-day).total_seconds()))
            if abs((clock-day).total_seconds()) > 48*3600:
                raise ValueError('Clock label outside daily probe')
            if clock in clocks:
                raise ValueError('Duplicate clock label')
            clocks.append(clock)
        else:
            # A single nonclock row is only a summary candidate, never hourly rain.
            if not label or re.match(r'^\d{2}:', label):
                raise ValueError('Malformed clock label')
        values = {}
        for station in row['stations']:
            if not isinstance(station, dict):
                raise ValueError('Invalid station entry')
            sid = identifier(station.get('id'), 'history.id')
            alias = identifier(station.get('sid'), 'history.sid')
            name = str(station.get('name', '')).strip()
            if sid in values:
                raise ValueError('Duplicate history station identifier within row')
            if sid in identities and identities[sid] != (alias, name):
                raise ValueError('Conflicting history identifier mapping across rows')
            if any(other != sid and pair[0] == alias for other, pair in identities.items()):
                raise ValueError('History sid maps to conflicting identifiers')
            identities[sid] = (alias, name); names[sid] = name
            values[sid] = depth(station.get('depth'))
        if not values:
            raise ValueError('Empty station row')
        if reference_ids is None:
            reference_ids = set(values)
        elif set(values) != reference_ids:
            raise ValueError('Unexpected station count or membership across rows')
        (hourly if match else summaries).append(values)
    if len(summaries) != 1 or len(hourly) not in (0, 24):
        raise ValueError('Daily probe requires one summary candidate and either zero or 24 hourly rows')
    if clocks and any(b-a != timedelta(hours=1) for a, b in zip(sorted(clocks), sorted(clocks)[1:])):
        raise ValueError('Daily hourly rows must form 24 consecutive clocks')
    ids = reference_ids or set()
    counts = {sid: sum(row[sid] is not None for row in hourly) for sid in ids}
    complete = {sid for sid, count in counts.items() if count == 24}
    partial = {sid for sid, count in counts.items() if 0 < count < 24}
    none = {sid for sid, count in counts.items() if count == 0}
    compared = mismatches = missing_summary = 0
    for sid in complete:
        summary = summaries[0][sid]
        if summary is None:
            missing_summary += 1
            continue
        compared += 1
        mismatches += abs(sum(row[sid] for row in hourly)-summary) > sum_tolerance_source_units
    current_ids = {r['station_id'] for r in inventory}
    current_uuids = {r['station_uuid'] for r in inventory}
    current_names = Counter(r['station_name'] for r in inventory)
    legacy_ids = {r['station_id'] for r in legacy_inventory or []}
    legacy_uuids = {r['station_uuid'] for r in legacy_inventory or []}
    missing = sum(v is None for row in hourly for v in row.values())
    return dict(probe_date=probe_date, status='hourly_rows_present' if hourly else 'no_hourly_data',
                hourly_rows=len(hourly), unique_clock_labels=len(set(clocks)),
                excluded_nonclock_summary_rows=len(summaries), nstation_union=len(ids),
                expected_hourly_cells=24*len(ids), returned_hourly_cells=len(hourly)*len(ids),
                valid_numeric_cells=sum(counts.values()), missing_cells=missing,
                missing_cells_codes={'-': missing} if missing else {},
                absent_hour_rows=24-len(hourly), all24_complete_station_count=len(complete),
                partial_station_count=len(partial), no_hourly_values_station_count=len(none),
                complete_station_summary_comparisons=compared,
                complete_station_summary_missing=missing_summary,
                complete_station_sum_mismatches=int(mismatches), sum_tolerance_source_units=sum_tolerance_source_units,
                exact_current_station_id_matches=len(ids & current_ids),
                exact_current_uuid_matches=sum(alias in current_uuids for alias, _ in identities.values()),
                current_unique_name_diagnostic_matches=sum(current_names[name] == 1 for name in names.values()),
                exact_v1_station_id_matches=len(ids & legacy_ids),
                exact_v1_uuid_matches=sum(alias in legacy_uuids for alias, _ in identities.values()),
                names_are_not_an_identity_crosswalk=True,
                timezone_confirmed=False, interval_timestamp_semantics_confirmed=False,
                summary_interval_semantics_confirmed=False, measurement_units_confirmed=False)
