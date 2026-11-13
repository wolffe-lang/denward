#!/usr/bin/env python3
"""Pinned release integer-division sites, not a timing certificate.

All div/idiv widths and arm64 sdiv/udiv are scanned in the selected crypto
function families, independent of object partition names. Known exceptions
track wolf-std#151 only; a new std pin requires an empty exception inventory.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

PREFIXES = ('std.x.crypto.curve25519.', 'std.x.crypto.chacha20.', 'std.x.crypto.sha2.', 'std.bech32.decode', 'std.bech32.value', 'std.bech32.power')
OPCODE = re.compile(r'\b(idiv[bwlq]?|div[bwlq]?|sdiv|udiv)\b', re.I)


def symbol(raw):
    raw = raw.lstrip('_')
    if raw.startswith('W'):
        raw = raw[1:]
    return re.sub(r'\$[0-9a-f]+', '', raw)


def scan(folder):
    sites = []
    functions = set()
    for path in sorted(Path(folder).glob('*.asm')):
        current = None
        start = None
        for line in path.read_text().splitlines():
            elf = re.match(r'^([0-9a-f]+) <([^>]+)>:$', line)
            mach = re.match(r'^(__W[^:]+):$', line)
            if elf or mach:
                current = symbol(elf[2] if elf else mach[1])
                start = int(elf[1], 16) if elf else None
                if current.startswith(PREFIXES):
                    functions.add(current)
                continue
            address = re.match(r'^\s*([0-9a-f]+)[:\s]\s*(.*)$', line)
            if not address or not current or not current.startswith(PREFIXES):
                continue
            if start is None:
                start = int(address[1], 16)
            # Disassembly comments/symbol references are not instructions.
            instruction = re.split(r'\s[;#]\s', address[2], 1)[0]
            match = OPCODE.search(instruction)
            if match:
                sites.append(dict(function=current, offset=hex(int(address[1], 16)-start), opcode=match[1].lower()))
    return sorted(sites, key=lambda x: (x['function'], int(x['offset'], 16), x['opcode'])), functions


def check(folder, inventory, target, std, compiler):
    actual, functions = scan(folder)
    required = ['std.x.crypto.curve25519.', 'std.x.crypto.chacha20.', 'std.x.crypto.sha2.', 'std.bech32.decode_bytes']
    if any(not any(f.startswith(prefix) for f in functions) for prefix in required):
        return False, 'missing-selected-function-family'
    if inventory['std'] != std or inventory['compiler'] != compiler:
        return False, 'pin-mismatch-exceptions-must-be-empty-after-std-fix'
    expected = inventory['targets'].get(target)
    if expected is None:
        return False, 'unlisted-target'
    counts = dict(sorted(Counter(s['function'] for s in actual).items()))
    if actual != expected['sites'] or counts != expected['counts']:
        return False, 'new-moved-or-missing-division-site'
    if any(s['issue'] != 'wolffe-lang/wolf-std#151' for s in expected['known']):
        return False, 'exception-without-tracking-issue'
    if {s['function'] for s in actual} != {s['function'] for s in expected['known']}:
        return False, 'untracked-known-function'
    return True, 'known-wolf-std-151-sites-only; empty-list-required-at-fixed-pin'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--inventory', type=Path, required=True)
    p.add_argument('--target', required=True)
    p.add_argument('--std', required=True)
    p.add_argument('--compiler', required=True)
    a = p.parse_args()
    inventory = json.loads(a.inventory.read_text())
    good, reason = check(a.workspace, inventory, a.target, a.std, a.compiler)
    actual, _ = scan(a.workspace)
    (a.workspace / 'division-sites.json').write_text(json.dumps(actual, indent=2) + '\n')
    print(('PASS ' if good else 'FAIL ') + 'release-secret-division-sites ' + reason, flush=True)
    return 0 if good else 1


if __name__ == '__main__':
    raise SystemExit(main())
