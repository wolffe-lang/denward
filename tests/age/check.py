#!/usr/bin/env python3
"""Judge published ciphertext and authenticated-prefix hashes, never key samples."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zlib

ROOT = Path(__file__).resolve().parents[1]


def vector(path, expected):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('vector digest mismatch')
    raw, body = data.split(b'\n\n', 1)
    fields = {}
    for line in raw.decode('ascii').splitlines():
        key, value = line.split(': ', 1)
        fields.setdefault(key, []).append(value)
    if fields.get('compressed') == ['zlib']:
        decoder = zlib.decompressobj()
        body = decoder.decompress(body, 32 * 1024 * 1024 + 1)
        if len(body) > 32 * 1024 * 1024 or decoder.unconsumed_tail or not decoder.eof or decoder.unused_data:
            raise ValueError('vector inflation bound')
    return fields, body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--program', type=Path, required=True)
    ap.add_argument('--data', type=Path, required=True)
    ap.add_argument('--workspace', type=Path, required=True)
    ap.add_argument('--small', action='store_true')
    args = ap.parse_args()
    inventory = json.loads((ROOT / 'age/inventory.json').read_text())
    args.workspace.mkdir(parents=True, exist_ok=True, mode=0o700)
    key_path = args.workspace / 'published-test-identity'
    passed = 0
    failures = []
    for case in inventory['cases']:
        name = case['name']
        if case['classification'] == 'unsupported':
            print('UNSUPPORTED published/' + name + ' reason=unimplemented-profile', flush=True)
            continue
        if args.small and not case['mac']:
            print('NOT-RUN published/' + name + ' reason=large-linux-row', flush=True)
            continue
        fields, ciphertext = vector(args.data / name, case['sha256'])
        identities = fields.get('identity', [])
        if any(not key.startswith('AGE-SECRET-KEY-1') for key in identities):
            raise ValueError('unexpected identity profile in selected vector')
        if key_path.exists():
            key_path.unlink()
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(('\n'.join(identities) + '\n').encode('ascii'))
        try:
            result = subprocess.run([str(args.program), 'decrypt', str(key_path)], input=ciphertext, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        finally:
            key_path.unlink()
        output_hash = hashlib.sha256(result.stdout).hexdigest()
        ok = result.returncode == 0 if case['classification'] == 'valid' else result.returncode == 1
        if case['payload_sha256'] is not None:
            ok = ok and output_hash == case['payload_sha256']
        else:
            ok = ok and not result.stdout
        expected = case['expect']
        if expected == 'HMAC failure':
            ok = ok and b'hmac' in result.stderr
        elif expected == 'no match':
            ok = ok and (b'no_match' in result.stderr or (name == 'x25519_lowercase' and b'unsupported' in result.stderr))
        elif expected == 'header failure':
            ok = ok and any(tag in result.stderr for tag in [b'header', b'truncated', b'unsupported'])
        elif expected == 'payload failure':
            ok = ok and any(tag in result.stderr for tag in [b'tag', b'truncated'])
        if expected == 'success':
            ok = ok and not result.stderr
        if ok:
            print('PASS published/' + name, flush=True)
            passed += 1
        else:
            # Do not display stderr/plaintext/key input, including on a trap.
            print('FAIL published/' + name + ' exit=' + str(result.returncode) + ' prefix_sha256=' + output_hash, flush=True)
            failures.append(name)
    print('Published selected passes=' + str(passed) + ' failures=' + str(len(failures)), flush=True)
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
