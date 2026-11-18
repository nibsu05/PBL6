"""Conservative station identity mapping; never merges rainfall observations.

Exact current coordinates establish a metadata correspondence, not proof of
unchanged instruments, historical locations or identical measurements.
"""
from __future__ import annotations

from collections import Counter


def canonical_inventory(legacy, modern):
    """Return one modern-based inventory with nullable legacy aliases.

    Reject ambiguous or unmatched legacy locations instead of guessing by name.
    Inputs use the normalized schema from ``inventory_from_groups``.
    """
    if not legacy or not modern:
        raise ValueError('Both inventories are required')
    for records in (legacy, modern):
        for key in ('station_id', 'station_uuid'):
            if len({str(row[key]) for row in records}) != len(records):
                raise ValueError('Duplicate source identifier')
        coords = [(float(row['latitude']), float(row['longitude'])) for row in records]
        if any(count > 1 for count in Counter(coords).values()):
            raise ValueError('Ambiguous duplicate coordinates')
    lookup = {(float(row['latitude']), float(row['longitude'])): row for row in modern}
    aliases = {}
    for row in legacy:
        coord = (float(row['latitude']), float(row['longitude']))
        if coord not in lookup:
            raise ValueError('Legacy location has no exact modern match')
        aliases[str(lookup[coord]['station_id'])] = row
    result = []
    for index, row in enumerate(sorted(modern, key=lambda r: (
            float(r['latitude']), float(r['longitude']), str(r['station_uuid']))), 1):
        old = aliases.get(str(row['station_id']))
        result.append(dict(
            canonical_id=f'ST{index:03d}',
            modern_id=str(row['station_id']), modern_uuid=str(row['station_uuid']),
            modern_name=row['station_name'], latitude=float(row['latitude']),
            longitude=float(row['longitude']), altitude=row.get('altitude'),
            legacy_id=str(old['station_id']) if old else None,
            legacy_uuid=str(old['station_uuid']) if old else None,
            legacy_name=old['station_name'] if old else None,
            metadata_match='exact_unique_coordinates' if old else 'modern_only_location',
            name_equal=old['station_name'] == row['station_name'] if old else None,
            historical_location_confirmed=False,
            observation_equivalence_confirmed=False,
        ))
    return result
