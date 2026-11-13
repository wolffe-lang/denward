#!/usr/bin/env python3
"""Generate test-only copies with explicit import/provider seams; never alter std."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

MODEL_MAIN = r'''
fn model(data: List[byte], read_max: int, write_max: int, event: int, event_at: int) -> fs.File {
    var buffer = List[byte]()
    for value in data { (mut buffer).push(value) }
    fs.File { data: buffer, at: 0, read_max: read_max, write_max: write_max,
        event: event, event_at: event_at, calls: 0 }
}
fn main() -> !int {
    let public = recipient("age1zvkyg2lqzraa2lnjvqej32nkuu0ues2s82hzrye869xeexvn73equnujwj")?
    let secret = identity("AGE-SECRET-KEY-1GFPYYSJZGFPYYSJZGFPYYSJZGFPYYSJZGFPYYSJZGFPYYSJZGFPQ4EGAEX")?
    for size in [0, 1, 257, 65536, 65537] {
        region case {
            var plain = List[byte]()
            for i in 0..size { (mut plain).push((i % 256) as byte) }
            let stride = if size < 1000 { 1 } else { 4093 }
            var source = model(plain, stride, stride, 0, 0)
            var sink = model(List[byte](), stride, stride, 0, 0)
            let count = encrypt(mut source, mut sink, [copy public])?
            assert(count == size && sink.calls > 1)
            var ciphertext = model(sink.data, stride, stride, 0, 0)
            var recovered = model(List[byte](), stride, stride, 0, 0)
            let back = decrypt(mut ciphertext, mut recovered, [copy secret])?
            assert(back == size && bytes.is_equal_fixed_work(plain, recovered.data))
        }
    }
    print("PASS io-partial-progress")
    for event in [1, 2, 3] {
        for at in [0, 3] {
            region case {
                var source = model("labelled test bytes".bytes(), 2, 2, event, at)
                var sink = model(List[byte](), 2, 2, 0, 0)
                var failed = false
                let count = encrypt(mut source, mut sink, [copy public]) else |e| { failed = match e { io => true, _ => false }; 0 }
                assert(failed && count == 0)
                var stored = model(sink.data, 13, 13, 0, 0)
                var decoded = model(List[byte](), 13, 13, 0, 0)
                var complete = true
                let ignored = decrypt(mut stored, mut decoded, [copy secret]) else |_| { complete = false; 0 }
                assert(!complete && ignored == 0 && decoded.data.len == 0)
            }
            region case {
                var source = model("labelled test bytes".bytes(), 2, 2, 0, 0)
                var sink = model(List[byte](), 2, 2, event, at)
                var failed = false
                let count = encrypt(mut source, mut sink, [copy public]) else |e| { failed = match e { io => true, _ => false }; 0 }
                assert(failed && count == 0 && sink.data.len == at)
            }
        }
    }
    print("PASS io-zero-error-interruption-no-success")
    region prefix_case {
        var plain = List[byte]()
        for i in 0..65537 { (mut plain).push((i % 256) as byte) }
        var source = model(plain, 4093, 4093, 0, 0)
        var sink = model(List[byte](), 4093, 4093, 0, 0)
        let encrypted = encrypt(mut source, mut sink, [copy public])?
        assert(encrypted == 65537)
        // One native stanza: 168-byte header + 16-byte nonce + 65552-byte box.
        var interrupted = model(sink.data, 17, 17, 3, 65737)
        var prefix = model(List[byte](), 4093, 4093, 0, 0)
        var failed = false
        let count = decrypt(mut interrupted, mut prefix, [copy secret]) else |e| { failed = match e { io => true, _ => false }; 0 }
        assert(failed && count == 0 && prefix.data.len == 65536)
        assert(bytes.is_equal_fixed_work(prefix.data, plain[0..65536]))
    }
    print("PASS authenticated-prefix-interruption-not-stream-success")
    assert(add_count(0, 0)? == 0)
    assert(add_count(9223372036854775806, 1)? == 9223372036854775807)
    for pair in [[9223372036854775807, 1], [0 - 1, 0], [0, 0 - 1], [1, 9223372036854775807]] {
        var refused = false
        let n = add_count(pair[0], pair[1]) else |budget| { refused = true; 0 }
        assert(refused && n == 0)
    }
    print("PASS signed-accounting-seams")
    0
}
'''

PAX_MAIN = r'''
use std.hex
fn model(data: List[byte]) -> fs.File {
    var buffer = List[byte]()
    for value in data { (mut buffer).push(value) }
    fs.File { data: buffer, at: 0, read_max: 17, write_max: 3,
        event: 0, event_at: 0, calls: 0 }
}
fn main() -> !int {
    let public = recipient("age1zvkyg2lqzraa2lnjvqej32nkuu0ues2s82hzrye869xeexvn73equnujwj")?
    let secret = identity("@@IDENTITY@@")?
    var source = model("test plaintext must not be consumed".bytes())
    var sink = model(List[byte]())
    var refused = false
    let count = encrypt(mut source, mut sink, [copy public]) else |e| {
        refused = match e { entropy_unqualified => true, _ => false }; 0
    }
    assert(refused && count == 0 && source.calls == 0 && sink.calls == 0 && sink.data.len == 0)
    for size in [63, 64, 65] {
        var recipients = List[List[byte]]()
        for _ in 0..size { (mut recipients).push(copy public) }
        var right = false
        let ignored = create_header(recipients) else |e| {
            right = match e { entropy_unqualified => size <= 64, budget => size == 65, _ => false }
            Created { raw: List[byte](), file_key: List[byte](), payload_nonce: List[byte]() }
        }
        assert(right && ignored.raw.len == 0)
    }
    print("PASS entropy-unqualified-before-draw-or-io")
    let ciphertext = hex.decode("@@CIPHERTEXT@@")?
    let parsed = parse_header(ciphertext[0..@@HEADER_LENGTH@@])?
    let expected_key = hex.decode("@@FILE_KEY@@")?
    for size in [63, 64, 65] {
        region identity_budget {
            var keys = List[List[byte]]()
            for _ in 0..size { (mut keys).push(copy secret) }
            var correct = false
            let recovered_key = open_header(parsed, keys) else |e| {
                correct = match e { budget => size == 65, _ => false }
                List[byte]()
            }
            if size <= 64 { correct = bytes.is_equal_fixed_work(recovered_key, expected_key) }
            assert(correct)
        }
    }
    print("PASS identity-attempt-boundaries")
    var encrypted = model(ciphertext)
    var recovered = model(List[byte]())
    let back = decrypt(mut encrypted, mut recovered, [secret])?
    assert(back == recovered.data.len)
    assert(sha2.to_hex(sha2.sum256(recovered.data)) == "@@PAYLOAD@@")
    print("PASS decrypt-independent-of-pax-entropy-admission")
    0
}
'''

PROVIDER_MAIN = r'''
fn main() -> !int {
    let public = recipient("age1zvkyg2lqzraa2lnjvqej32nkuu0ues2s82hzrye869xeexvn73equnujwj")?
    var source = fs.stdin()
    var sink = fs.stdout()
    let n = encrypt(mut source, mut sink, [public])?
    if n < 0 { return 1 }
    0
}
'''


def package(name, deps=''):
    return 'pkg { name: "test/' + name + '", version: "0.0.0", edition: "1", capabilities: [env, fs],' + deps + ' }\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workspace', type=Path, required=True)
    ap.add_argument('--data', type=Path, required=True)
    ap.add_argument('--release', action='store_true')
    a = ap.parse_args()
    a.workspace.mkdir(parents=True, exist_ok=False)
    state = json.loads((ROOT / '.wolf-bin/toolchain.json').read_text())
    original = (ROOT / 'src/age/age.lu').read_text()
    random_source = (Path(state['std']) / 'os/random/random.lu').read_text()
    fake_fs = (ROOT / 'tests/age/seams/fake_fs.lu').read_text()
    vector_data = (a.data / 'x25519').read_bytes()
    inventory = json.loads((ROOT / 'tests/age/inventory.json').read_text())
    expected = next(c['sha256'] for c in inventory['cases'] if c['name'] == 'x25519')
    if len(vector_data) > 1048576 or hashlib.sha256(vector_data).hexdigest() != expected:
        raise ValueError('published vector digest mismatch')
    raw, ciphertext = vector_data.split(b'\n\n', 1)
    fields = dict(line.split(': ', 1) for line in raw.decode().splitlines())
    header_length = ciphertext.index(b'\n', ciphertext.index(b'\n--- ') + 1) + 1
    pax_main = PAX_MAIN.replace('@@IDENTITY@@', fields['identity']).replace('@@CIPHERTEXT@@', ciphertext.hex()).replace('@@PAYLOAD@@', fields['payload']).replace('@@HEADER_LENGTH@@', str(header_length)).replace('@@FILE_KEY@@', fields['file key'])
    provenance = {'production_sha256': hashlib.sha256(original.encode()).hexdigest(), 'std_random_sha256': hashlib.sha256(random_source.encode()).hexdigest(), 'fake_fs_sha256': hashlib.sha256(fake_fs.encode()).hexdigest(), 'generated': {}}
    env = os.environ.copy()
    env.update(WOLF_STD=state['std'], TMPDIR=str(a.workspace), RAYON_NUM_THREADS='2')
    for name, main_source in [('io', MODEL_MAIN), ('pax', pax_main), ('provider', PROVIDER_MAIN)]:
        stage = a.workspace / name
        stage.mkdir()
        source = original
        deps = []
        if name != 'provider':
            source = source.replace('use std.fs\n', 'use fake_fs as fs\n')
            module = stage / 'fake_fs'
            module.mkdir()
            (module / 'fake_fs.lu').write_text(fake_fs)
            (module / 'wolf.pkg').write_text(package('fake-fs'))
            deps.append('fake_fs: { path: "fake_fs" }')
        if name in ['pax', 'provider']:
            source = source.replace('use std.os.random\n', 'use fake_random as random\n')
            module = stage / 'fake_random'
            module.mkdir()
            if name == 'pax':
                substituted = random_source.replace('let platform = os_name()', 'let platform = "pax"')
            else:
                substituted = random_source.replace('let raw = os_random(n)', 'assert(n == 0)\n    let raw = List[int]()')
            if substituted == random_source:
                raise ValueError('expected single std provider seam missing')
            (module / 'fake_random.lu').write_text(substituted)
            (module / 'wolf.pkg').write_text(package('fake-random'))
            deps.append('fake_random: { path: "fake_random" }')
        (stage / 'wolf.pkg').write_text(package(name, ' deps: { ' + ','.join(deps) + ' },'))
        full = source + '\n' + main_source
        (stage / 'main.lu').write_text(full)
        provenance['generated'][name] = hashlib.sha256(full.encode()).hexdigest()
        binary = stage / 'row'
        command = [state['wolf'], 'build', '--deny-warnings', str(stage / 'main.lu'), '-o', str(binary)]
        if a.release:
            command.append('--release')
        compiled = subprocess.run(command, env=env, cwd=stage, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        if compiled.returncode:
            for line in compiled.stdout.decode('utf-8', 'replace').splitlines():
                if line.startswith('error[') or line.lstrip().startswith('-->'):
                    print(line, flush=True)
            print('FAIL seam-build/' + name, flush=True)
            return 1
        result = subprocess.run([str(binary)], input=b'public test input', env=env, cwd=stage, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if name == 'provider':
            good = result.returncode != 0 and not result.stdout and b'assert' in result.stderr
            print(('PASS ' if good else 'FAIL ') + 'provider-trap-no-ciphertext-or-fallback', flush=True)
        else:
            good = result.returncode == 0
            if good:
                print(result.stdout.decode(), end='', flush=True)
            else:
                print('FAIL seam/' + name + ' exit=' + str(result.returncode), flush=True)
        if not good:
            return 1
    (a.workspace / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print('PASS test-copy-provenance', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
