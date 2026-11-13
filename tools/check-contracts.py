#!/usr/bin/env python3
"""Compiler-independent specification, fixture and failure-witness checks."""
import hashlib
import json
from pathlib import Path
import re
import runpy
import subprocess
import types
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def require(ok, name):
    if not ok:
        raise AssertionError(name)
    print('PASS ' + name)


def main():
    pins = tomllib.loads((ROOT / 'wolf-toolchain.toml').read_text())
    require(pins['wolf']['version'] == '0.2.39' and pins['lupin']['version'] == '0.1.61', 'K01-paired-pins')
    require(all(re.fullmatch('[0-9a-f]{64}', pins[k][p]) for k in ['wolf', 'lupin'] for p in ['aarch64-apple-darwin', 'x86_64-unknown-linux-gnu']), 'K02-release-digests')
    require(re.fullmatch('[0-9a-f]{40}', pins['std']['rev']) and re.fullmatch('[0-9a-f]{40}', pins['std']['tree']), 'K03-std-pin')
    hashes = {'LICENSE': '3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986', 'LICENSE-TRAINING-DATA': '39d16667f8215642b3e1f6b65c5169dc4ca288c5cef87b17f2c16a0be5a74da3'}
    require(all(hashlib.sha256((ROOT / n).read_bytes()).hexdigest() == h for n, h in hashes.items()), 'K04-license-pair')
    specs = ['cli-v1', 'backup-v1', 'manifest-v1', 'stream-v1', 'stores-v1', 'restore-state-v1', 'compatibility-v1', 'encryption-v1']
    require(all((ROOT / 'spec' / (n + '.md')).is_file() for n in specs), 'K05-versioned-contracts')
    stream = (ROOT / 'spec/stream-v1.md').read_text()
    require(all(t in stream for t in ['Encryption is the default', 'Without a key', 'With a key', 'No stage may buffer the entire archive', 'No exception handler substitutes a pass-through']), 'K06-encryption-seam')
    store = (ROOT / 'spec/stores-v1.md').read_text()
    require(all(t in store for t in ['macOS arm64', 'OpenSSH', 'encrypted volume', '**received**', '--commit', 'No transfer resume']), 'K07-mac-first-store')
    rows = json.loads((ROOT / 'tests/cli/cases.json').read_text())
    require(len(rows) == 52 and len({r['id'] for r in rows}) == 52, 'K08-cli-fixture-census')
    require({r['id'] for r in rows} >= {'C08-encrypted-default', 'C10-plaintext-ack-required', 'C12-no-implicit-plaintext', 'C17-ciphertext-verify-only', 'C18-keyed-verify'}, 'K09-refusal-boundaries')
    cli_test = runpy.run_path(str(ROOT / 'tests/cli/check.py'))
    sample = {'code': 2, 'err': 'denward: unsupported: encrypted-format-provider\n'}
    result = types.SimpleNamespace(returncode=2, stdout=b'', stderr=sample['err'].encode())
    require(cli_test['check_result'](sample, result, 'sentinel') == '', 'K10-cli-judge-positive')
    result.returncode = 0
    require(cli_test['check_result'](sample, result, 'sentinel') == 'exit-status', 'K11-cli-judge-sees-wrong-success')
    result.returncode = 2
    result.stderr = b'sentinel'
    require(cli_test['check_result'](sample, result, 'sentinel') != '', 'K12-cli-judge-sees-secret-output')
    qemu = runpy.run_path(str(ROOT / 'tests/qemu/assertions.py'))
    facts = json.loads((ROOT / 'tests/qemu/observed-v1.json').read_text())
    require(qemu['self_test'](facts), 'K13-storage-judge-mutations')
    workflow = (ROOT / '.github/workflows/ci.yml').read_text()
    require(all(t in workflow for t in ['pull_request:', 'push:', 'schedule:', 'workflow_dispatch:', 'ubuntu-24.04', 'macos-15', '--suite core', '--suite native', 'timeout-minutes:']), 'K14-workflow-shape-not-execution')
    require(re.search(r'actions/checkout@[0-9a-f]{40}', workflow) is not None, 'K15-action-pin')
    tracked = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files'], text=True).splitlines()
    require(not any(Path(n).name == 'CLAUDE.md' for n in tracked), 'K16-no-local-rules-file')
    bad = []
    for name in tracked:
        p = ROOT / name
        if not p.is_file():
            continue
        text = p.read_text()
        # Workstation paths and decision identifiers are not public contract data.
        if re.search(r'[/]Users[/]|[/]home[/][^\s]+[/]lanes[/]|R-[a-z][a-z0-9]*-[0-9]+', text):
            bad.append(name)
    require(not bad, 'K17-publication-path-boundary')
    source = '\n'.join(p.read_text() for p in (ROOT / 'src').rglob('*.lu'))
    require(not re.search(r'\b(?:fs_|net_|process_)\w+|\bextern\b', source), 'K18-refusal-shell-no-data-io')
    live = [ROOT / 'src/denward.lu', *sorted((ROOT / 'src/cli').rglob('*.lu'))]
    imports = {m for p in live for m in re.findall(r'(?m)^\s*use[ \t]+([^\n]+)', p.read_text())}
    command_pkg = (ROOT / 'src/wolf.pkg').read_text()
    cli_pkg = (ROOT / 'src/cli/wolf.pkg').read_text()
    require(imports == {'cli', 'std.str as text'} and re.search(r'capabilities:\s*\[env\]', command_pkg) and re.search(r'capabilities:\s*\[\]', cli_pkg) and 'deps:' not in command_pkg + cli_pkg, 'K19-refusal-shell-closed-import-boundary')
    print('CONTRACT-RESULT rows=19 failures=0')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('FAIL contracts ' + type(e).__name__ + ' ' + str(e))
        raise SystemExit(1)
