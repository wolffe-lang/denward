#!/usr/bin/env python3
"""Small macOS/reference cross-host fixture exchange; no plaintext spool."""
import argparse
import hashlib
import json
import os
import platform
import resource
import time
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SIZES = [0, 1, 65535, 65536, 65537, 131072, 256, 100003]
PINS = {'age': 'eb7dd1b518f0a307c99cd97782623c5321da049154b04acd2d98d21aa7bc9b2c', 'age-keygen': '0a0009db842259d6717f7eeb30acb6b90d2a2eb924c6acd0a0db0ca1f1537899'}


def main():
    started = time.monotonic()
    p = argparse.ArgumentParser()
    p.add_argument('--phase', choices=['mac-write', 'oracle', 'mac-read'], required=True)
    p.add_argument('--program', type=Path)
    p.add_argument('--reference', type=Path)
    p.add_argument('--keys', type=Path, required=True)
    p.add_argument('--input', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.phase.startswith('mac-') and (platform.system() != 'Darwin' or platform.machine() != 'arm64'):
        raise ValueError('native macOS arm64 execution required')
    a.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    if a.phase == 'oracle':
        for name, digest in PINS.items():
            if hashlib.sha256((a.reference / name).read_bytes()).hexdigest() != digest:
                raise ValueError('reference pin mismatch')
    identities = [a.keys / ('test-identity-' + str(i)) for i in range(3)]
    public = a.keys / 'native-recipients'
    public_lines = public.read_bytes().splitlines()
    if len(public_lines) != 2 or any(not line.startswith(b'age1') or len(line) != 62 for line in public_lines):
        raise ValueError('explicit native recipients required')
    for identity in identities:
        if identity.stat().st_mode & 0o077:
            raise ValueError('test identity not private')
        lines = [line for line in identity.read_bytes().splitlines() if line and not line.startswith(b'#')]
        if len(lines) != 1 or not lines[0].startswith(b'AGE-SECRET-KEY-1') or len(lines[0]) != 74:
            raise ValueError('test identity is not native X25519')
    report = dict(phase=a.phase, platform=platform.system() + '-' + platform.machine(), source_head=subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(), rows=[])
    if a.phase != 'mac-write':
        incoming = json.loads((a.input / 'results.json').read_text())
        if incoming['source_head'] != report['source_head']:
            raise ValueError('interoperability source head mismatch')
        expected_hashes = {row['size']: row['ciphertext_sha256'] for row in incoming['rows']}
        if set(expected_hashes) != set(SIZES):
            raise ValueError('interoperability inventory mismatch')
    if a.program:
        report['program_sha256'] = hashlib.sha256(a.program.read_bytes()).hexdigest()

    def run(command, data):
        return subprocess.run([str(x) for x in command], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)

    for size in SIZES:
        plain = bytes(i % 256 for i in range(size))
        name = 'size-' + str(size) + '.age'
        if a.phase == 'mac-write':
            r = run([a.program, 'encrypt', public], plain)
            if r.returncode or r.stderr:
                raise ValueError('Mac encryption failed')
            (a.output / name).write_bytes(r.stdout)
            os.chmod(a.output / name, 0o600)
            report['rows'].append(dict(size=size, ciphertext_sha256=hashlib.sha256(r.stdout).hexdigest()))
            print('PASS mac-fixture-written/' + str(size), flush=True)
        elif a.phase == 'oracle':
            ciphertext = (a.input / name).read_bytes()
            if hashlib.sha256(ciphertext).hexdigest() != expected_hashes[size]:
                raise ValueError('interoperability ciphertext digest mismatch')
            for i in range(2):
                r = run([a.reference / 'age', '-d', '-i', identities[i]], ciphertext)
                if r.returncode or r.stdout != plain:
                    raise ValueError('Mac codec to reference mismatch')
                print('PASS interop/mac-codec-to-age/' + str(size) + '/recipient-' + str(i), flush=True)
            r = run([a.reference / 'age', '-R', public], plain)
            if r.returncode or r.stderr:
                raise ValueError('reference native encryption failed')
            (a.output / name).write_bytes(r.stdout)
            os.chmod(a.output / name, 0o600)
            report['rows'].append(dict(size=size, ciphertext_sha256=hashlib.sha256(r.stdout).hexdigest(), native_recipient_paths=2))
        else:
            ciphertext = (a.input / name).read_bytes()
            if hashlib.sha256(ciphertext).hexdigest() != expected_hashes[size]:
                raise ValueError('interoperability ciphertext digest mismatch')
            for i in range(2):
                r = run([a.program, 'decrypt', identities[i]], ciphertext)
                if r.returncode or r.stdout != plain or r.stderr:
                    raise ValueError('reference to Mac codec mismatch')
                print('PASS interop/age-to-mac-codec/' + str(size) + '/recipient-' + str(i), flush=True)
            r = run([a.program, 'decrypt', identities[2]], ciphertext)
            if r.returncode != 1 or r.stdout or b'no_match' not in r.stderr:
                raise ValueError('wrong identity accepted or plaintext released')
            print('PASS interop/mac-wrong-identity/' + str(size), flush=True)
            report['rows'].append(dict(size=size, or_recovery_paths=2, wrong_identity_refused=True))
    own = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    report['cpu_seconds'] = own.ru_utime + own.ru_stime + children.ru_utime + children.ru_stime
    report['elapsed_seconds'] = time.monotonic() - started
    report['average_busy_cpus'] = report['cpu_seconds'] / report['elapsed_seconds']
    if hasattr(os, 'sched_getaffinity'):
        report['affinity'] = sorted(os.sched_getaffinity(0))
    print('CAPACITY average_busy_cpus=' + str(round(report['average_busy_cpus'], 3)), flush=True)
    (a.output / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
