"""Install the licensed Đà Nẵng reference boundaries for the local rainfall map."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://www.tinhthanhpho.com/data/wards-48.geojson'
OUTPUT = ROOT / 'data/operational/station_map_areas/wards-48.geojson'


def verify(raw):
    data = json.loads(raw)
    features = data['features']
    meta = data['metadata']
    if (data['type'] != 'FeatureCollection' or meta['dataset'] != 'wards-48'
            or meta['license'] != 'CC BY 4.0' or meta['publisher'] != 'tinhthanhpho.com'
            or not features):
        raise ValueError('Expected CC BY 4.0 Đà Nẵng boundaries')
    codes = set()
    for feature in features:
        properties = feature['properties']
        code = properties['code']
        geom = feature['geometry']
        if (feature['type'] != 'Feature' or not code or not properties['name'] or code in codes
                or geom['type'] not in ('Polygon', 'MultiPolygon') or not geom['coordinates']):
            raise ValueError('Invalid or duplicate area')
        codes.add(code)
    return len(features), meta['data_version']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Install from an already downloaded source file')
    args = parser.parse_args()
    if args.source:
        raw = args.source.read_bytes()
    else:
        with urlopen(Request(SOURCE, headers={'User-Agent': 'PBL6-station-map/1.0'}), timeout=30) as response:
            raw = response.read(16_000_001)
    if len(raw) > 16_000_000:
        raise ValueError('Boundary file exceeds expected size')
    rows, version = verify(raw)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix('.' + uuid4().hex + '.part')
    temporary.write_bytes(raw)
    temporary.replace(OUTPUT)
    print(f'Installed {rows} boundaries, provider version {version}, SHA256 {hashlib.sha256(raw).hexdigest()}.')


if __name__ == '__main__':
    main()
