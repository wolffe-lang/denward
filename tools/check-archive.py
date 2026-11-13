#!/usr/bin/env python3
"""Independent safe-member archive contracts; fake input only, bounded native rows."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
EMPTY = hashlib.sha256(b'').hexdigest()
ABC = hashlib.sha256(b'abc').hexdigest()


def require(ok, name):
    if not ok:
        raise AssertionError(name)
    print('PASS ' + name, flush=True)


def build():
    state = json.loads((ROOT / '.wolf-bin/toolchain.json').read_text())
    env = os.environ.copy()
    env['WOLF_STD'] = state['std']
    out = ROOT / 'target/tests/archive-probe'
    out.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([state['wolf'], 'build', '--deny-warnings', 'tests/archive-probe/main.lu', '-o', str(out)], cwd=ROOT, env=env)
    if result.returncode:
        print('FAIL A00-archive-probe-build compiler-exit=' + str(result.returncode), flush=True)
        raise SystemExit(1)
    print('PASS A00-archive-probe-build', flush=True)
    return out


def header(path, kind=b'0', length=0, mode=0o600, target='', uid=0):
    h = bytearray(512)
    for at, raw in [(0,path.encode()), (100,f'{mode:07o}\0'.encode()), (108,f'{uid:07o}\0'.encode()), (116,b'0000000\0'), (124,f'{length:011o}\0'.encode()), (136,b'00000000000\0'), (148,b'        '), (156,kind), (157,target.encode()), (257,b'ustar\0'), (263,b'00')]:
        assert len(raw) <= 100
        h[at:at+len(raw)] = raw
    h[148:156] = f'{sum(h):06o}  '.encode()
    return bytes(h)


def record(path, data=b'', kind=b'0', mode=0o600, target='', uid=0):
    return header(path, kind, len(data), mode, target, uid) + data + bytes((-len(data)) % 512)


def prefix():
    return record('control', kind=b'5', mode=0o700) + b''.join(record('control/' + n) for n in ['accounts', 'config-defaults', 'installed', 'manifest']) + record('objects', kind=b'5', mode=0o700)


def reference(data=b'abc', digest=ABC):
    return prefix() + record('objects/' + digest, data) + bytes(1024)


def inspect(binary, raw):
    p = subprocess.run([str(binary), 'inspect', str(len(raw))], input=raw, capture_output=True, timeout=60)
    assert p.returncode == 0 and not p.stderr
    return p.stdout.strip()


def hostile_rows(binary):
    raw = reference()
    require(inspect(binary, raw) == b'physical:7', 'A21-complete-physical-inventory')
    require(inspect(binary, prefix() + bytes(1024)) == b'physical:6', 'A22-physical-only-not-logical-validity')
    cases = [
        ('A23-extra-member', raw[:-1024] + record('control/extra') + bytes(1024), b'archive-member-name'),
        ('A24-missing-control', raw[:512] + raw[1024:], b'archive-missing-control'),
        ('A25-object-content-name', reference(b'abd'), b'archive-object-digest'),
        ('A26-physical-symlink', raw[:-1024] + record('objects/'+EMPTY, kind=b'2', target='../control/accounts') + bytes(1024), None),
        ('A27-physical-hardlink', raw[:-1024] + record('objects/'+EMPTY, kind=b'1', target='control/accounts') + bytes(1024), None),
        ('A28-mode-normalization', record('control', kind=b'5', mode=0o755) + raw[512:], b'archive-member-normalization'),
        ('A29-owner-normalization', record('control', kind=b'5', mode=0o700, uid=1) + raw[512:], b'archive-member-normalization'),
        ('A30-logical-path-not-authority', raw[:-1024] + record('home/user') + bytes(1024), None),
        ('A31-object-name-syntax', raw[:-1024] + record('objects/'+ABC.upper()) + bytes(1024), b'archive-member-name'),
        ('A32-exact-end', raw+b'\0', None),
        ('A33-truncated-input', raw[:-1], None),
    ]
    changed = bytearray(raw); changed[-1025] = 1
    cases.append(('A34-nonzero-padding', bytes(changed), None))
    for name, data, error in cases:
        result = inspect(binary, data)
        require(result == b'refused:'+error if error else result.startswith(b'refused:'), name)


def pipe_rows(binary):
    body = (bytes(range(256)) * 8193)[:2*1024*1024+3]
    digest = hashlib.sha256(body).hexdigest()
    child = subprocess.Popen([str(binary), 'emit', str(len(body)), digest], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    errors = []
    def feed():
        try:
            for at in range(0, len(body), 1031):
                child.stdin.write(body[at:at+1031]); child.stdin.flush()
        except Exception as e:
            errors.append(e)
        finally:
            child.stdin.close()
    feeder = threading.Thread(target=feed, daemon=True)
    feeder.start()
    actual = hashlib.sha256(); count = 0
    try:
        deadline = time.monotonic()+90
        while True:
            if time.monotonic() > deadline:
                raise AssertionError('archive pipe deadline')
            if not select.select([child.stdout], [], [], 1)[0]:
                continue
            block = os.read(child.stdout.fileno(), 4096)
            if not block:
                break
            actual.update(block); count += len(block)
            time.sleep(.001)
        feeder.join(timeout=10)
        require(not feeder.is_alive() and not errors and child.wait(timeout=10) == 0 and not child.stderr.read() and count == len(reference(body,digest)) and actual.digest() == hashlib.sha256(reference(body,digest)).digest(), 'A35-ragged-source-backpressure-exact-wire')
    finally:
        if child.poll() is None:
            child.kill(); child.wait()
        child.stdout.close(); child.stderr.close()
        feeder.join(timeout=10)
    child = subprocess.Popen([str(binary), 'emit', '3', ABC], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    child.stdout.close()
    try:
        _, error = child.communicate(input=b'abc', timeout=30)
        require(child.returncode != 0, 'A36-closed-consumer-not-success')
    finally:
        if child.poll() is None:
            child.kill(); child.wait()
    read_fd, write_fd = os.pipe()
    child = None
    try:
        os.set_blocking(write_fd, False)
        filled = 0
        while True:
            try:
                filled += os.write(write_fd, b'F'*4096)
                assert filled <= 2*1024*1024
            except BlockingIOError:
                break
        freed = min(8192, filled)
        left = freed
        while left:
            left -= len(os.read(read_fd, left))
        child = subprocess.Popen([str(binary), 'emit', str(len(body)), digest], stdin=subprocess.PIPE, stdout=write_fd, stderr=subprocess.PIPE)
        os.close(write_fd); write_fd = -1
        _, error = child.communicate(input=body, timeout=60)
        observed = bytearray()
        while True:
            part = os.read(read_fd, 65536)
            if not part:
                break
            observed.extend(part)
        require(child.returncode != 0 and b'archive:pack-write' in error and len(observed)-(filled-freed) >= 3584, 'A37-nonblocking-sink-error-propagated')
    finally:
        if child is not None and child.poll() is None:
            child.kill(); child.wait()
        os.close(read_fd)
        if write_fd >= 0:
            os.close(write_fd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--build-only', action='store_true')
    a = ap.parse_args()
    binary = build()
    if a.build_only:
        return
    with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR'], prefix='archive-') as tmp:
        p = subprocess.run([str(binary), 'unit', tmp], stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        print(p.stdout.decode(), end='', flush=True)
        print(p.stderr.decode(), end='', file=sys.stderr, flush=True)
        if p.returncode:
            raise AssertionError('archive unit probe exit='+str(p.returncode))
    p = subprocess.run([str(binary), 'emit', '3', ABC], input=b'abc', capture_output=True, timeout=60)
    require(p.returncode == 0 and not p.stderr and p.stdout == reference(), 'A20-independent-canonical-wire')
    hostile_rows(binary)
    for name, body, digest in [('A38-source-digest-failure', b'abc', EMPTY), ('A39-source-truncation', b'ab', ABC)]:
        p = subprocess.run([str(binary), 'emit', '3', digest], input=body, capture_output=True, timeout=60)
        require(p.returncode != 0 and p.stderr.startswith(b'archive:') and not p.stdout.endswith(bytes(1024)), name)
    pipe_rows(binary)
    print('PASS archive-adapter-contracts', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('FAIL archive-adapter-contracts '+type(e).__name__+' '+str(e), flush=True)
        raise SystemExit(1)
