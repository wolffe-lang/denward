#!/usr/bin/env python3
"""Public independent-review G40 reproducer: first unwrap controls header MAC."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
IDENTITY = b'AGE-SECRET-KEY-1GFPYYSJZGFPYYSJZGFPYYSJZGFPYYSJZGFPYYSJZGFPYYSJZGFPQ4EGAEX\n'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--program', type=Path, required=True)
    p.add_argument('--workspace', type=Path, required=True)
    a = p.parse_args()
    a.workspace.mkdir(parents=True, exist_ok=False, mode=0o700)
    fixture = (ROOT / 'tests/age/fixtures/first-unwrap.age').read_bytes()
    if hashlib.sha256(fixture).hexdigest() != '2544832f5325936f39afbb78cd8ed198adf92734acc54751d991feeec794bb4c':
        raise ValueError('review fixture digest mismatch')
    key = a.workspace / 'published-test-identity'
    fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(IDENTITY)
    try:
        r = subprocess.run([str(a.program), 'decrypt', str(key)], input=fixture, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        good = r.returncode == 1 and not r.stdout and b'hmac' in r.stderr
        print(('PASS ' if good else 'FAIL ') + 'first-unwrap-header-mac', flush=True)
        return 0 if good else 1
    finally:
        key.unlink()


if __name__ == '__main__':
    raise SystemExit(main())
