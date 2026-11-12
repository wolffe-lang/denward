#!/usr/bin/env python3
"""Small stopping gate. A required missing dependency is a failure, never a skip."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def step(name, args, env=None):
    print('START ' + name, flush=True)
    started = time.monotonic()
    try:
        r = subprocess.run(args, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
        for line in r.stdout.decode('utf-8', 'replace').splitlines():
            print('  ' + line, flush=True)
        code = r.returncode
    except (OSError, subprocess.TimeoutExpired):
        print('  FAIL execution-prerequisite', flush=True)
        code = 1
    print('END ' + name + ' exit=' + str(code) + ' secs=' + str(round(time.monotonic() - started, 3)), flush=True)
    if code:
        raise SystemExit(code if code > 0 else 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--suite', choices=['core', 'native'], required=True)
    a = ap.parse_args()
    work = Path(os.environ.get('DENWARD_WORKSPACE', str(ROOT / '.work/gate'))).resolve()
    work.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['TMPDIR'] = str(work)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    step('contracts', [sys.executable, '-I', str(ROOT / 'tools/check-contracts.py')], env)
    step('storage-judge-replay', [sys.executable, '-I', str(ROOT / 'tests/qemu/assertions.py'), str(ROOT / 'tests/qemu/observed-v1.json'), '--mode', 'judge-replay'], env)
    if a.suite == 'core':
        return
    machine = platform.machine().lower()
    actual = 'macos-arm64' if platform.system() == 'Darwin' and machine in ('arm64', 'aarch64') else 'linux-x86_64' if platform.system() == 'Linux' and machine in ('x86_64', 'amd64') else 'unsupported'
    if actual == 'unsupported' or os.environ.get('DENWARD_EXPECT_PLATFORM', actual) != actual:
        raise RuntimeError('native platform mismatch')
    state = json.loads((ROOT / '.wolf-bin/toolchain.json').read_text())
    if state['pins_sha256'] != hashlib.sha256((ROOT / 'wolf-toolchain.toml').read_bytes()).hexdigest():
        raise RuntimeError('staged pins mismatch')
    wolf = Path(state['wolf'])
    std = Path(state['std'])
    if not wolf.is_file() or not (wolf.parent / 'libwolf_rt.a').is_file() or not std.is_dir():
        raise RuntimeError('staged toolchain missing')
    if subprocess.check_output(['git', '-C', str(std.parent), 'status', '--porcelain'], text=True):
        raise RuntimeError('standard library checkout modified')
    # Outputs and caches are ignored; tracked source must be the committed take.
    if subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT, text=True):
        raise RuntimeError('build requires committed tracked source')
    env['WOLF_STD'] = str(std)
    env['LUPIN_STD'] = str(std)
    if actual == 'linux-x86_64':
        cc = shutil.which('cc')
        if not cc:
            raise RuntimeError('native compiler driver missing')
        linker = work / 'linker'
        linker.mkdir(exist_ok=True)
        shutil.copyfile(ROOT / 'tools/link-static', linker / 'cc')
        (linker / 'cc').chmod(0o700)
        env['DENWARD_REAL_CC'] = cc
        env['PATH'] = str(linker) + os.pathsep + env['PATH']
        env['WOLF_LD'] = 'cc'
    for path in sorted((ROOT / 'src').rglob('*.lu')):
        step('fmt-' + path.stem, [str(wolf), 'fmt', '--check', str(path)], env)
    out = ROOT / 'target/bin'
    out.mkdir(parents=True, exist_ok=True)
    step('build-command', [str(wolf), 'build', '--deny-warnings', 'src/denward.lu', '-o', str(out / 'denward')], env)
    step('build-unit', [str(wolf), 'build', '--deny-warnings', 'src/cli_test.lu', '-o', str(out / 'cli-unit')], env)
    if actual == 'linux-x86_64':
        headers = subprocess.check_output(['readelf', '-l', str(out / 'denward')], text=True)
        if 'INTERP' in headers:
            raise RuntimeError('Linux command is not static')
        print('PASS static-linux-command', flush=True)
    step('cli-unit', [str(out / 'cli-unit')], env)
    step('cli-e2e', [sys.executable, '-I', str(ROOT / 'tests/cli/check.py'), '--program', str(out / 'denward'), '--workspace', str(work)], env)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('FAIL gate ' + type(e).__name__ + ' ' + str(e), flush=True)
        raise SystemExit(1)
