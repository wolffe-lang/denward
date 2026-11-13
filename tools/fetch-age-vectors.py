#!/usr/bin/env python3
"""Fetch published vector files as data only, verified against the inventory."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    inventory = json.loads((ROOT / 'tests/age/inventory.json').read_text())
    out = ROOT / '.work/age-vectors'
    out.mkdir(parents=True, exist_ok=True)
    for case in inventory['cases']:
        name = case['name']
        if not name.replace('_', '').isalnum():
            raise ValueError('vector path refused')
        path = out / name
        if path.exists():
            data = path.read_bytes()
        else:
            url = 'https://raw.githubusercontent.com/' + inventory['repository'] + '/' + inventory['revision'] + '/' + inventory['path'] + '/' + name
            request = urllib.request.Request(url, headers={'User-Agent': 'published-vector-fetch'})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read(1048577)
        if len(data) > 1048576 or hashlib.sha256(data).hexdigest() != case['sha256']:
            raise ValueError('vector digest mismatch')
        if not path.exists():
            path.write_bytes(data)
    print('PASS pinned-vector-data count=' + str(len(inventory['cases'])))


if __name__ == '__main__':
    main()
