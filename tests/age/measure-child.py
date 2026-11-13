#!/usr/bin/env python3
"""Small Linux rusage parent for a single capped, public-fixture decrypt."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess


def limit():
    resource.setrlimit(resource.RLIMIT_AS, (268435456, 268435456))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    p = argparse.ArgumentParser()
    for name in ['program', 'ciphertext']:
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--identity', type=Path)
    p.add_argument('--mode', choices=['decrypt', 'parser'], default='decrypt')
    p.add_argument('--expected', required=True)
    a = p.parse_args()
    floor = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    command = [str(a.program)]
    if a.mode == 'decrypt':
        if a.identity is None:
            raise ValueError('private test-identity path required')
        command += ['decrypt', str(a.identity)]
    with a.ciphertext.open('rb') as source:
        r = subprocess.run(command, stdin=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=limit, timeout=90)
    digest = hashlib.sha256(r.stdout).hexdigest()
    if a.mode == 'parser':
        good = r.returncode == (0 if a.expected == 'parsed' else 1) and r.stdout == (a.expected + '\n').encode() and not r.stderr
    elif a.expected == 'budget':
        good = r.returncode == 1 and not r.stdout and b'budget' in r.stderr
    else:
        good = r.returncode == 0 and not r.stderr and digest == a.expected
    peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    good = good and peak <= 262144
    result = dict(mode=a.mode, parent_floor_kib=floor, child_peak_upper_kib=peak, returncode=r.returncode, stdout_bytes=len(r.stdout), stdout_sha256=digest, stderr_bytes=len(r.stderr), stderr_sha256=hashlib.sha256(r.stderr).hexdigest(), as_cap=268435456, passed=good)
    print(json.dumps(result, sort_keys=True))
    return 0 if good else 1


if __name__ == '__main__':
    raise SystemExit(main())
