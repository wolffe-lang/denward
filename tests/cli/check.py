#!/usr/bin/env python3
"""Run the real refusal command against independently declared CLI cases."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def snapshot(root):
    rows = []
    for p in sorted(root.rglob('*')):
        s = p.lstat()
        if stat.S_ISLNK(s.st_mode):
            content = os.readlink(p)
        elif stat.S_ISREG(s.st_mode):
            content = hashlib.sha256(p.read_bytes()).hexdigest()
        else:
            content = ''
        rows.append((str(p.relative_to(root)), stat.S_IFMT(s.st_mode), stat.S_IMODE(s.st_mode), s.st_size, content))
    return rows


def check_result(row, result, sentinel):
    # Never print captured bytes: a broken command could have leaked the sentinel.
    if result.returncode != row['code']:
        return 'exit-status'
    if result.stderr != row.get('err', '').encode():
        return 'stderr'
    if 'out' in row and result.stdout != row['out'].encode():
        return 'stdout'
    if 'out_contains' in row and row['out_contains'].encode() not in result.stdout:
        return 'stdout-claim'
    if row['code'] != 0 and result.stdout:
        return 'unexpected-stdout'
    if sentinel.encode() in result.stdout + result.stderr:
        return 'secret-output'
    return ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--program', type=Path, required=True)
    ap.add_argument('--workspace', type=Path, required=True)
    a = ap.parse_args()
    program = a.program.resolve()
    if not program.is_file() or not os.access(program, os.X_OK):
        print('FAIL C01-version executable-missing')
        return 1
    a.workspace.mkdir(parents=True, exist_ok=True)
    rows = json.loads((ROOT / 'tests/cli/cases.json').read_text())
    failures = 0
    with tempfile.TemporaryDirectory(prefix='cli-', dir=a.workspace) as d:
        root = Path(d)
        for name in ['source', 'receiver', 'target', 'home', 'scratch']:
            (root / name).mkdir()
        sentinel = 'fixture-private-' + secrets.token_hex(16)
        (root / 'source/data').write_bytes(b'personal fixture\x00\xff')
        (root / 'source/key').write_text(sentinel)
        (root / 'source/key').chmod(0o600)
        (root / 'input').write_bytes(b'not an archive\x00\xff')
        (root / 'baseline').write_bytes(b'not a baseline')
        (root / 'decisions').write_bytes(b'not decisions')
        before = snapshot(root)
        values = {'{ROOT}': str(root), '{SENTINEL}': sentinel, '{DIGEST}': '0' * 64, '{LONG}': 'x' * 4097}
        env = {'PATH': os.environ.get('PATH', ''), 'HOME': str(root / 'home'), 'TMPDIR': str(root / 'scratch'), 'LC_ALL': 'C'}
        for row in rows:
            args = []
            for value in row['args']:
                for key, replacement in values.items():
                    value = value.replace(key, replacement)
                args.append(value)
            try:
                r = subprocess.run([str(program), *args], input=b'fixture input that must not be consumed\n', stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=root, env=env, timeout=5)
                error = check_result(row, r, sentinel)
            except (OSError, subprocess.TimeoutExpired):
                error = 'execution-failed'
            if snapshot(root) != before:
                error = 'filesystem-mutated'
            print(('FAIL' if error else 'PASS') + ' ' + row['id'] + ((' ' + error) if error else ''))
            failures += bool(error)
        r = subprocess.run([str(program), 'stores', *(['--json'] * 256)], input=b'', stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=root, env=env, timeout=5)
        ok = r.returncode == 2 and r.stderr == b'denward: usage: argument limit\n' and not r.stdout and snapshot(root) == before
        print(('PASS' if ok else 'FAIL') + ' C41-argument-count')
        failures += not ok
    print('CLI-RESULT rows=41 failures=' + str(failures))
    return int(failures != 0)


if __name__ == '__main__':
    raise SystemExit(main())
