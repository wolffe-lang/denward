#!/usr/bin/env python3
"""Small hostile-stream rows. All key input is labelled published test material."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess

IDENTITY = b'AGE-SECRET-KEY-1GFPYYSJZGFPYYSJZGFPYYSJZGFPYYSJZGFPYYSJZGFPYYSJZGFPQ4EGAEX\n'
RECIPIENT = b'age1zvkyg2lqzraa2lnjvqej32nkuu0ues2s82hzrye869xeexvn73equnujwj\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--program', type=Path, required=True)
    ap.add_argument('--workspace', type=Path, required=True)
    args = ap.parse_args()
    args.workspace.mkdir(parents=True, exist_ok=True, mode=0o700)
    secret, public = args.workspace / 'published-test-key', args.workspace / 'published-recipient'
    for path, data in [(secret, IDENTITY), (public, RECIPIENT)]:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
    failures = []

    def run(mode, data):
        return subprocess.run([str(args.program), mode, str(secret if mode == 'decrypt' else public)], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)

    def expect(name, ok):
        print(('PASS ' if ok else 'FAIL ') + name, flush=True)
        if not ok:
            failures.append(name)

    def reject(name, data, prefix=b''):
        r = run('decrypt', data)
        expect(name, r.returncode == 1 and hashlib.sha256(r.stdout).digest() == hashlib.sha256(prefix).digest())

    def flip(data, i):
        out = bytearray(data)
        out[i] ^= 1
        return bytes(out)

    try:
        for size in [0, 1, 65535, 65536, 65537, 131072]:
            plain = bytes(i % 256 for i in range(size))
            enc = run('encrypt', plain)
            expect('stream-size-' + str(size) + '-encrypt', enc.returncode == 0 and not enc.stderr)
            ciphertext = enc.stdout
            dec = run('decrypt', ciphertext)
            expect('stream-size-' + str(size) + '-decrypt', dec.returncode == 0 and dec.stdout == plain and not dec.stderr)
            header_end = ciphertext.index(b'\n', ciphertext.index(b'\n--- ') + 1) + 1
            payload = header_end + 16
            chunks = max(1, (size + 65535) // 65536)
            expect('stream-size-' + str(size) + '-exact-length', len(ciphertext) == payload + size + 16 * chunks)
            if size in [0, 1, 65536]:
                for pos in range(16):
                    reject('payload-tag-' + str(size) + '-' + str(pos), flip(ciphertext, len(ciphertext) - 16 + pos))
            if size == 131072:
                first, second = ciphertext[payload:payload + 65552], ciphertext[payload + 65552:]
                for pos in range(16):
                    reject('failed-second-chunk-' + str(pos), flip(ciphertext, len(ciphertext) - 16 + pos), plain[:65536])
                for pos in range(16):
                    reject('payload-nonce-' + str(pos), flip(ciphertext, header_end + pos))
                reject('ciphertext-first', flip(ciphertext, payload))
                reject('chunks-swapped', ciphertext[:payload] + second + first)
                reject('chunk-dropped', ciphertext[:payload] + second)
                reject('chunk-duplicated', ciphertext[:payload] + first + first + second, plain[:65536])
                reject('file-concatenated', ciphertext + ciphertext, plain[:65536])
                for suffix in [b'\0', b'garbage', bytes(65553)]:
                    reject('appended-' + str(len(suffix)), ciphertext + suffix, plain[:65536])
                seams = [0, 1, 21, 22, header_end - 45, header_end - 1, header_end, header_end + 1, payload - 1, payload, payload + 1, payload + 65535, payload + 65536, payload + 65551, payload + 65552, payload + 65553, len(ciphertext) - 16, len(ciphertext) - 1]
                for seam in seams:
                    prefix = plain[:65536] if seam > payload + 65552 else b''
                    reject('truncation-' + str(seam), ciphertext[:seam], prefix)
        return 1 if failures else 0
    finally:
        secret.unlink(missing_ok=True)
        public.unlink(missing_ok=True)


if __name__ == '__main__':
    raise SystemExit(main())
