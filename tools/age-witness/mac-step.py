#!/usr/bin/env python3
"""Mac record phases: release the build lock while the remote oracle runs."""
import contextlib
import hashlib
import json
import os
import platform
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time

ROOT = Path(os.environ['AGE_ROOT'])
OUT = Path(os.environ['AGE_OUT'])
STATE = json.loads((ROOT / '.wolf-bin/toolchain.json').read_text())
ENV = os.environ.copy()
ENV.update(WOLF_STD=STATE['std'], LUPIN_STD=STATE['std'], TMPDIR=str(OUT / 'tmp'), RAYON_NUM_THREADS='2', CARGO_BUILD_JOBS='2')
(OUT / 'tmp').mkdir(parents=True, exist_ok=True)


def run(command, **kwargs):
    if len(command) > 1 and command[1] == 'build':
        subprocess.run([sys.executable, '-I', str(ROOT / 'tools/mac-resource.py')], cwd=ROOT, env=ENV, check=True)
    subprocess.run([str(v) for v in command], cwd=ROOT, env=ENV, check=True, **kwargs)


@contextlib.contextmanager
def build_lock():
    lock = Path(os.environ['AGE_MAC_LOCK'])
    turn = Path(os.environ['AGE_MAC_TURN'])
    if turn.exists():
        gap = 60 - (time.time() - float(turn.read_text()))
        if gap > 0:
            print('WAIT Mac build turn', flush=True)
            time.sleep(gap)
    while True:
        try:
            lock.mkdir()
            break
        except FileExistsError:
            print('WAIT Mac build lock', flush=True)
            time.sleep(60)
    try:
        stats = subprocess.check_output(['vm_stat'], text=True)
        page = int(re.search(r'page size of (\d+)', stats)[1])
        available = sum(int(re.search(r'Pages ' + key + r':\s+(\d+)', stats)[1]) for key in ['free', 'inactive', 'speculative']) * page
        free = shutil.disk_usage(ROOT).free
        print('RESOURCE memory_available=' + str(available) + ' disk_free=' + str(free), flush=True)
        if available < 8 * 1024**3 or free <= 15 * 1024**3:
            raise SystemExit(75)
        yield
    finally:
        for p in list(ROOT.rglob('.lu-cache')) + list(OUT.rglob('.lu-cache')):
            if p.is_dir():
                shutil.rmtree(p)
        for p in OUT.rglob('row'):
            if p.is_file():
                p.unlink()
        for mode in ['default', 'release']:
            for name in ['keys', 'header', 'crypto', 'driver', 'parser']:
                (OUT / 'codec' / mode / name).unlink(missing_ok=True)
        (OUT / 'mac-reader').unlink(missing_ok=True)
        lock.rmdir()
        turn.write_text(str(time.time()))


phase = sys.argv[1]
if phase == 'preflight':
    assert platform.system() == 'Darwin' and platform.machine() == 'arm64'
    assert not subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'])
    for name, path in [('wolf', Path(STATE['wolf'])), ('lupin', Path(STATE['lupin'])), ('runtime', Path(STATE['wolf']).parent / 'libwolf_rt.a')]:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == STATE[name + '_sha256']
    assert hashlib.sha256((ROOT / 'wolf-toolchain.toml').read_bytes()).hexdigest() == STATE['pins_sha256']
    if os.environ.get('AGE_ORACLE_SLOT') != 'B':
        print('REFUSED oracle-image-requires-block-B', flush=True)
        raise SystemExit(75)
    print('PASS Mac standalone preflight; no build or codec row run', flush=True)
elif phase == 'source':
    with build_lock():
        run([sys.executable, '-I', ROOT / 'tools/age-gate.py', '--workspace', OUT / 'codec', '--data', ROOT / '.work/age-vectors'])
        run([sys.executable, '-I', ROOT / 'tests/age/mac-interop.py', '--phase', 'mac-write', '--program', OUT / 'codec/release/driver', '--keys', os.environ['AGE_MAC_KEYS'], '--output', OUT / 'mac-write'])
elif phase == 'oracle':
    host = os.environ['AGE_ORACLE_HOST']
    remote = {key: os.environ[key] for key in ['AGE_ORACLE_ROOT', 'AGE_ORACLE_OUT', 'AGE_ORACLE_INPUT', 'AGE_ORACLE_KEYS', 'AGE_ORACLE_REF', 'AGE_ORACLE_ENGINE', 'AGE_ORACLE_LIGHT', 'AGE_ORACLE_SLOT']}
    if remote['AGE_ORACLE_SLOT'] != 'B':
        print('REFUSED oracle-image-requires-block-B', flush=True)
        raise SystemExit(75)
    script = 'set -eu\numask 077\n'
    script += 'mkdir -p ' + shlex.quote(remote['AGE_ORACLE_INPUT']) + ' ' + shlex.quote(remote['AGE_ORACLE_OUT']) + '\n'
    run(['ssh', host, 'bash', '-s'], input=script.encode())
    run(['scp', '-pr', str(OUT / 'mac-write') + '/.', host + ':' + remote['AGE_ORACLE_INPUT'] + '/'])
    exports = {'AGE_ROOT': remote['AGE_ORACLE_ROOT'], 'AGE_OUT': remote['AGE_ORACLE_OUT'], 'AGE_REF': remote['AGE_ORACLE_REF'], 'AGE_KEYS': remote['AGE_ORACLE_KEYS'], 'AGE_INPUT': remote['AGE_ORACLE_INPUT'], 'AGE_ENGINE': remote['AGE_ORACLE_ENGINE'], 'AGE_IMAGE': 'localhost/r41-toolchain:1', 'AGE_CPUS': '6-11'}
    script = 'set -eu\n'
    for key, value in exports.items():
        script += 'export ' + key + '=' + shlex.quote(value) + '\n'
    script += 'cd "$AGE_ROOT"\npython3 -I tools/age-witness/preflight.py\n'
    script += shlex.quote(remote['AGE_ORACLE_LIGHT']) + ' ' + shlex.quote(remote['AGE_ORACLE_SLOT']) + ' bash "$AGE_ROOT/tools/age-witness/oracle.sh"\n'
    run(['ssh', host, 'bash', '-s'], input=script.encode())
    run(['scp', '-pr', host + ':' + remote['AGE_ORACLE_OUT'] + '/returned', OUT / 'mac-return'])
elif phase == 'finish':
    with build_lock():
        run([STATE['wolf'], 'build', '--release', '--deny-warnings', ROOT / 'tests/age/driver/main.lu', '-o', OUT / 'mac-reader'])
        run([sys.executable, '-I', ROOT / 'tests/age/mac-interop.py', '--phase', 'mac-read', '--program', OUT / 'mac-reader', '--keys', os.environ['AGE_MAC_KEYS'], '--input', OUT / 'mac-return', '--output', OUT / 'mac-read'])
        run([sys.executable, '-I', ROOT / 'tools/capture-age-code.py', '--workspace', OUT / 'generated-code'])
else:
    raise SystemExit(2)
