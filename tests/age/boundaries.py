#!/usr/bin/env python3
"""Admission boundaries and end-to-end worst-header memory, Linux only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SEAL_MAIN = r'''
use std.hex
fn main() -> !int {
    var source = fs.stdin()
    var raw = List[byte]()
    let ended = fill(mut source, mut raw, 1048578)?
    if !ended || raw.len < 48 { return 1 }
    let file_key = hex.decode("@@FILE_KEY@@")?
    let transcript = raw[0..raw.len - 45]
    let tag = header_tag(file_key, transcript)
    var output = copy transcript
    append(mut output, " {base64.encode_raw(tag)}\n".bytes())
    var sink = fs.stdout()
    write_all(mut sink, output)?
    0
}
'''


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (268435456, 268435456))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def exact_header(prefix, target):
    # Literal A lines describe zero-valued base64 fixture data. No encoder
    # or decoder is implemented here; the selected std decoder validates it.
    start = prefix + b'-> unknown'
    tail = b'--- ' + b'A' * 43 + b'\n'
    for pad in range(65):
        available = target - len(start) - pad - 1 - len(tail)
        full, short = divmod(available - 1, 65)
        if full >= 0 and short < 64 and short % 4 != 1:
            header = start + b'A' * pad + b'\n' + (b'A' * 64 + b'\n') * full + b'A' * short + b'\n' + tail
            if len(header) == target:
                return header
    raise ValueError('exact fixture size not representable')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--parser', type=Path, required=True)
    p.add_argument('--program', type=Path, required=True)
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--release', action='store_true')
    a = p.parse_args()
    a.workspace.mkdir(parents=True, exist_ok=False, mode=0o700)
    state = json.loads((ROOT / '.wolf-bin/toolchain.json').read_text())
    data = (a.data / 'x25519').read_bytes()
    inventory = json.loads((ROOT / 'tests/age/inventory.json').read_text())
    expected_digest = next(c['sha256'] for c in inventory['cases'] if c['name'] == 'x25519')
    if hashlib.sha256(data).hexdigest() != expected_digest:
        raise ValueError('published vector digest mismatch')
    raw, ciphertext = data.split(b'\n\n', 1)
    fields = dict(line.split(': ', 1) for line in raw.decode().splitlines())
    end = ciphertext.index(b'\n', ciphertext.index(b'\n--- ') + 1) + 1
    prefix = ciphertext[:end - 48]
    key = a.workspace / 'published-test-identity'
    fd = os.open(key, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(fields['identity'] + '\n')
    stage = a.workspace / 'sealer'
    stage.mkdir()
    (stage / 'main.lu').write_text((ROOT / 'src/age/age.lu').read_text() + SEAL_MAIN.replace('@@FILE_KEY@@', fields['file key']))
    (stage / 'wolf.pkg').write_text('pkg { name: "test/header-sealer", version: "0.0.0", edition: "1", capabilities: [env, fs] }\n')
    binary = stage / 'sealer'
    env = os.environ.copy()
    env.update(WOLF_STD=state['std'], TMPDIR=str(stage), RAYON_NUM_THREADS='2')
    command = [state['wolf'], 'build', '--deny-warnings', str(stage / 'main.lu'), '-o', str(binary)]
    if a.release:
        command.append('--release')
    built = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    if built.returncode:
        for line in built.stdout.decode('utf-8', 'replace').splitlines():
            if line.startswith('error[') or line.lstrip().startswith('-->'):
                print(line, flush=True)
        print('FAIL boundary-sealer-build', flush=True)
        return 1
    results = []

    def run(program, input, args=()):
        return subprocess.run([str(program), *map(str, args)], input=input, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=limits, timeout=90)

    for size in [4095, 4096, 4097]:
        header = b'age-encryption.org/v1\n-> ' + b'u' * (size - 4) + b'\n\n--- ' + b'A' * 43 + b'\n'
        row = run(a.parser, header)
        expected = b'parsed\n' if size <= 4096 else b'budget\n'
        good = row.stdout == expected and row.returncode == (0 if size <= 4096 else 1) and not row.stderr
        print(('PASS ' if good else 'FAIL ') + 'argument-line-boundary/' + str(size), flush=True)
        if not good:
            return 1
    for count in [63, 64, 65]:
        header = b'age-encryption.org/v1\n' + b'-> unknown\n\n' * count + b'--- ' + b'A' * 43 + b'\n'
        row = run(a.parser, header)
        good = row.stdout == (b'parsed\n' if count <= 64 else b'budget\n') and row.returncode == (0 if count <= 64 else 1) and not row.stderr
        print(('PASS ' if good else 'FAIL ') + 'stanza-boundary/' + str(count), flush=True)
        if not good:
            return 1
    # Compiler RSS is not included in the child measurement. Each measured
    # driver is launched by a fresh small Python parent below.
    for size in [1048575, 1048576, 1048577]:
        header = exact_header(prefix, size)
        raw_fixture = a.workspace / ('header-' + str(size) + '.bin')
        raw_fixture.write_bytes(header)
        command = ['python3', '-I', str(ROOT / 'tests/age/measure-child.py'), '--program', str(a.parser), '--ciphertext', str(raw_fixture), '--mode', 'parser', '--expected', 'parsed' if size <= 1048576 else 'budget']
        measured = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if not measured.stdout:
            print('FAIL raw-header-measurement/' + str(size), flush=True)
            return 1
        result = json.loads(measured.stdout)
        result['header_bytes'] = size
        results.append(result)
        (a.workspace / 'memory.json').write_text(json.dumps(results, indent=2) + '\n')
        good = measured.returncode == 0
        print(('PASS ' if good else 'FAIL ') + 'raw-header-boundary/' + str(size) + ' child_peak_upper_kib=' + str(result['child_peak_upper_kib']) + ' exit=' + str(result['returncode']), flush=True)
        if not good:
            return 1
        sealed = run(binary, header)
        if sealed.returncode or sealed.stderr or len(sealed.stdout) != size:
            print('FAIL worst-header-fixture/' + str(size), flush=True)
            return 1
        fixture = a.workspace / ('header-' + str(size) + '.age')
        fixture.write_bytes(sealed.stdout + ciphertext[end:])
        # A fresh parent starts without the compiler's inherited maxrss and
        # hashes stdout while never storing plaintext on disk.
        command = [os.environ.get('PYTHON', 'python3'), '-I', str(ROOT / 'tests/age/measure-child.py'), '--program', str(a.program), '--identity', str(key), '--ciphertext', str(fixture), '--expected', fields['payload'] if size <= 1048576 else 'budget']
        measured = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if not measured.stdout:
            print('FAIL worst-header-measurement/' + str(size), flush=True)
            return 1
        result = json.loads(measured.stdout)
        result['header_bytes'] = size
        results.append(result)
        (a.workspace / 'memory.json').write_text(json.dumps(results, indent=2) + '\n')
        good = measured.returncode == 0
        print(('PASS ' if good else 'FAIL ') + 'worst-header-hmac-memory/' + str(size) + ' parent_floor_kib=' + str(result['parent_floor_kib']) + ' child_peak_upper_kib=' + str(result['child_peak_upper_kib']) + ' exit=' + str(result['returncode']), flush=True)
        if not good:
            return 1
    (a.workspace / 'memory.json').write_text(json.dumps(results, indent=2) + '\n')
    key.unlink()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
