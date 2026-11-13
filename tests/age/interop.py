#!/usr/bin/env python3
"""Pinned reference age binaries as black boxes; never print identities or payload."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess

PINS = {
    'age': 'eb7dd1b518f0a307c99cd97782623c5321da049154b04acd2d98d21aa7bc9b2c',
    'age-keygen': '0a0009db842259d6717f7eeb30acb6b90d2a2eb924c6acd0a0db0ca1f1537899',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--program', type=Path, required=True)
    ap.add_argument('--reference', type=Path, required=True)
    ap.add_argument('--workspace', type=Path, required=True)
    a = ap.parse_args()
    a.workspace.mkdir(parents=True, exist_ok=False, mode=0o700)
    for name, digest in PINS.items():
        if hashlib.sha256((a.reference / name).read_bytes()).hexdigest() != digest:
            raise ValueError('reference executable digest mismatch')

    def run(command, data=b''):
        return subprocess.run([str(x) for x in command], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)

    identities = [a.workspace / ('test-identity-' + str(i)) for i in range(3)]
    recipients = []
    # The pinned keygen explicitly documents native X25519 without -pq.
    # Reject anything else instead of depending on a future changing default.
    for identity in identities:
        result = run([a.reference / 'age-keygen', '-o', identity])
        if result.returncode:
            raise ValueError('reference test-key generation failed')
        data = identity.read_bytes()
        secret_lines = [line for line in data.splitlines() if line and not line.startswith(b'#')]
        if len(secret_lines) != 1 or not secret_lines[0].startswith(b'AGE-SECRET-KEY-1') or len(secret_lines[0]) != 74:
            raise ValueError('reference did not generate native X25519')
        if identity.stat().st_mode & 0o077:
            raise ValueError('test identity mode not private')
        result = run([a.reference / 'age-keygen', '-y', identity])
        if result.returncode or not result.stdout.startswith(b'age1') or len(result.stdout.strip()) != 62:
            raise ValueError('reference recipient profile mismatch')
        recipients.append(result.stdout)
    public = a.workspace / 'native-recipients'
    public.write_bytes(b''.join(recipients[:2]))
    os.chmod(public, 0o600)
    for size in [0, 1, 65535, 65536, 65537, 131072, 256, 100003]:
        plain = bytes(i % 256 for i in range(size))
        encrypted = run([a.program, 'encrypt', public], plain)
        if encrypted.returncode:
            raise ValueError('codec encryption failed')
        for i in range(2):
            decrypted = run([a.reference / 'age', '-d', '-i', identities[i]], encrypted.stdout)
            if decrypted.returncode or decrypted.stdout != plain:
                raise ValueError('codec to reference mismatch')
            print('PASS interop/codec-to-age/' + str(size) + '/recipient-' + str(i), flush=True)
        encrypted = run([a.reference / 'age', '-R', public], plain)
        if encrypted.returncode:
            raise ValueError('reference encryption failed')
        for i in range(2):
            decrypted = run([a.program, 'decrypt', identities[i]], encrypted.stdout)
            if decrypted.returncode or decrypted.stdout != plain:
                raise ValueError('reference to codec mismatch')
            print('PASS interop/age-to-codec/' + str(size) + '/recipient-' + str(i), flush=True)
        for program in [[a.program, 'decrypt', identities[2]], [a.reference / 'age', '-d', '-i', identities[2]]]:
            wrong = run(program, encrypted.stdout)
            if wrong.returncode == 0 or wrong.stdout:
                raise ValueError('wrong identity accepted or exposed plaintext')
        print('PASS interop/wrong-identity/' + str(size), flush=True)
    print('PASS interop/reference-age-v1.3.2-explicit-native-recipients', flush=True)


if __name__ == '__main__':
    main()
