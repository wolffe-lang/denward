#!/usr/bin/env python3
"""Linux generated streams under a process address-space cap; no plaintext spool."""
import argparse
import hashlib
import os
from pathlib import Path
import resource
import subprocess

IDENTITY = b'AGE-SECRET-KEY-1GFPYYSJZGFPYYSJZGFPYYSJZGFPYYSJZGFPYYSJZGFPYYSJZGFPQ4EGAEX\n'
RECIPIENT = b'age1zvkyg2lqzraa2lnjvqej32nkuu0ues2s82hzrye869xeexvn73equnujwj\n'


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (268435456, 268435456))
    resource.setrlimit(resource.RLIMIT_CPU, (1800, 1800))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--program', type=Path, required=True)
    p.add_argument('--workspace', type=Path, required=True)
    a = p.parse_args()
    a.workspace.mkdir(parents=True, exist_ok=False, mode=0o700)
    secret, public = a.workspace / 'published-test-key', a.workspace / 'published-recipient'
    for path, data in [(secret, IDENTITY), (public, RECIPIENT)]:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
    block = bytes(range(256)) * 256
    for size in [67108864, 536870912]:
        expected = hashlib.sha256()
        ciphertext = a.workspace / ('generated-' + str(size) + '.age')
        floor = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        with ciphertext.open('xb') as out:
            os.chmod(ciphertext, 0o600)
            process = subprocess.Popen([str(a.program), 'encrypt', str(public)], stdin=subprocess.PIPE, stdout=out, stderr=subprocess.PIPE, preexec_fn=limits)
            for _ in range(size // len(block)):
                process.stdin.write(block)
                expected.update(block)
            process.stdin.close()
            process.stdin = None
            _, error = process.communicate(timeout=1800)
            if process.returncode or error:
                raise ValueError('capped encryption failed')
        got = hashlib.sha256()
        count = 0
        with ciphertext.open('rb') as source:
            process = subprocess.Popen([str(a.program), 'decrypt', str(secret)], stdin=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=limits)
            while chunk := process.stdout.read(131072):
                got.update(chunk)
                count += len(chunk)
            _, error = process.communicate(timeout=1800)
            if process.returncode or error or count != size or got.digest() != expected.digest():
                raise ValueError('capped decryption failed')
        peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        if peak > 262144:
            raise ValueError('process RSS cap exceeded')
        print('PASS chunk-lifetimes bytes=' + str(size) + ' parent_floor_kib=' + str(floor) + ' child_peak_upper_kib=' + str(peak) + ' as_cap=268435456', flush=True)
        ciphertext.unlink()
    secret.unlink()
    public.unlink()


if __name__ == '__main__':
    main()
