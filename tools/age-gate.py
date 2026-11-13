#!/usr/bin/env python3
"""Run codec-only development rows at both optimization levels, from a commit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def step(name, command, env, timeout=300):
    print('START ' + name, flush=True)
    result = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    for line in result.stdout.decode('utf-8', 'replace').splitlines():
        print(line if line.startswith('FAIL ') else '  ' + line, flush=True)
    print('END ' + name + ' exit=' + str(result.returncode), flush=True)
    if result.returncode:
        raise SystemExit(result.returncode if result.returncode > 0 else 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--build', choices=['default', 'release', 'both'], default='both')
    args = parser.parse_args()
    if subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT):
        raise ValueError('committed source required')
    state = json.loads((ROOT / '.wolf-bin/toolchain.json').read_text())
    for name, path in [('wolf', Path(state['wolf'])), ('lupin', Path(state['lupin'])), ('runtime', Path(state['wolf']).parent / 'libwolf_rt.a')]:
        if hashlib.sha256(path.read_bytes()).hexdigest() != state[name + '_sha256']:
            raise ValueError('toolchain binary identity mismatch')
    print('PINSET ' + json.dumps(state, sort_keys=True), flush=True)
    for name in ['wolf', 'lupin']:
        version = subprocess.check_output([state[name], '--version'], text=True).strip()
        print('VERSION ' + version, flush=True)
    args.workspace.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(WOLF_STD=state['std'], LUPIN_STD=state['std'], TMPDIR=str(args.workspace), CARGO_BUILD_JOBS='2', RAYON_NUM_THREADS='2')
    for mode in (['default', 'release'] if args.build == 'both' else [args.build]):
        stage = args.workspace / mode
        stage.mkdir(exist_ok=True)
        for unit in ['keys', 'header', 'crypto', 'driver', 'parser']:
            binary = stage / unit
            command = [state['wolf'], 'build', '--deny-warnings', str(ROOT / ('tests/age/' + unit + '/main.lu')), '-o', str(binary)]
            if mode == 'release':
                command.append('--release')
            step(mode + '-build-' + unit, command, env)
            if unit not in ['driver', 'parser']:
                step(mode + '-' + unit, [str(binary)], env)
        command = [sys.executable, '-I', str(ROOT / 'tests/age/check.py'), '--program', str(stage / 'driver'), '--data', str(args.data), '--workspace', str(stage / 'vectors')]
        if platform.system() == 'Darwin':
            command.append('--small')
        step(mode + '-published', command, env, timeout=600)
        step(mode + '-hostile', [sys.executable, '-I', str(ROOT / 'tests/age/hostile.py'), '--program', str(stage / 'driver'), '--workspace', str(stage / 'hostile')], env, timeout=600)
        command = [sys.executable, '-I', str(ROOT / 'tests/age/seams.py'), '--workspace', str(stage / 'fault-seams'), '--data', str(args.data)]
        if mode == 'release':
            command.append('--release')
        step(mode + '-fault-seams', command, env, timeout=300)


if __name__ == '__main__':
    main()
