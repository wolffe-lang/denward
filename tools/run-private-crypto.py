#!/usr/bin/env python3
"""Run crypto rows in a hashed test copy, without exporting creation state."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--release', action='store_true')
    a = p.parse_args()
    a.workspace.mkdir(parents=True, exist_ok=False)
    state = json.loads((ROOT / '.wolf-bin/toolchain.json').read_text())
    for name, path in [('wolf', Path(state['wolf'])), ('lupin', Path(state['lupin'])), ('runtime', Path(state['wolf']).parent / 'libwolf_rt.a')]:
        if hashlib.sha256(path.read_bytes()).hexdigest() != state[name + '_sha256']:
            raise ValueError('toolchain identity mismatch')
    print('PINSET ' + json.dumps(state, sort_keys=True), flush=True)
    for name in ['wolf', 'lupin']:
        print('VERSION ' + subprocess.check_output([state[name], '--version'], text=True).strip(), flush=True)
    original = (ROOT / 'src/age/age.lu').read_text()
    template = (ROOT / 'tests/age/crypto/main.lu').read_text()
    template = re.sub(r'^use [^\n]+\n', '', template, flags=re.M)
    template = re.sub(r'\bage\.', '', template)
    copied = original + '\n' + template
    entry = a.workspace / 'main.lu'
    entry.write_text(copied)
    (a.workspace / 'wolf.pkg').write_text('pkg { name: "test/private-crypto", version: "0.0.0", edition: "1", capabilities: [env, fs] }\n')
    (a.workspace / 'provenance.json').write_text(json.dumps(dict(production_sha256=hashlib.sha256(original.encode()).hexdigest(), generated_sha256=hashlib.sha256(copied.encode()).hexdigest()), indent=2) + '\n')
    env = os.environ.copy()
    env.update(WOLF_STD=state['std'], TMPDIR=str(a.workspace), RAYON_NUM_THREADS='2')
    subprocess.run([sys.executable, '-I', str(ROOT / 'tools/mac-resource.py')], env=env, check=True)
    binary = a.workspace / 'row'
    command = [state['wolf'], 'build', '--deny-warnings', str(entry), '-o', str(binary)]
    if a.release:
        command.append('--release')
    subprocess.run(command, env=env, cwd=a.workspace, check=True, timeout=120)
    return subprocess.run([str(binary)], env=env, cwd=a.workspace, timeout=120).returncode


if __name__ == '__main__':
    raise SystemExit(main())
