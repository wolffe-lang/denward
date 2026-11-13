#!/usr/bin/env python3
"""Standalone host preflight. No compiler, codec or qualification row runs here."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

def refuse(reason):
    print('REFUSED ' + reason, flush=True)
    raise SystemExit(75)


mask = os.environ.get('AGE_CPUS', '')
if not mask:
    refuse('missing-take-cpu-mask')
try:
    for part in mask.split(','):
        ends = [int(v) for v in part.split('-')]
        if len(ends) == 1:
            ends *= 2
        if len(ends) != 2 or not 0 <= ends[0] <= ends[1] < 18:
            raise ValueError('mask')
except ValueError:
    refuse('invalid-or-reserved-take-cpu-mask')
root = Path(os.environ['AGE_ROOT'])
logdir = Path(os.environ['AGE_TASKSET_LOGDIR'])
if logdir.is_symlink() or not logdir.is_dir() or logdir.stat().st_uid != os.geteuid():
    refuse('translator-log-directory-not-owned')
if not logdir.resolve().is_relative_to(Path(os.environ['AGE_OUT']).resolve()):
    refuse('translator-log-directory-outside-record')
assert shutil.disk_usage(root).free >= 35 * 1024**3, 'disk floor'
mem = {line.split(':')[0]: int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
assert mem['MemAvailable'] >= 8 * 1024**2, 'memory floor'
assert not subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain']), 'dirty snapshot'
state = json.loads((root / '.wolf-bin/toolchain.json').read_text())
std = Path(state['std']).parent
assert subprocess.check_output(['git', '-C', str(std), 'rev-parse', 'HEAD'], text=True).strip() == 'bb002f3ed4f4cf87f62e50da3391cb224dc1ebc1', 'std head drift'
assert subprocess.check_output(['git', '-C', str(std), 'rev-parse', 'HEAD^{tree}'], text=True).strip() == '76f1553216ca42f1ad5f90c2059a12a5fd008481', 'std tree drift'
assert not subprocess.check_output(['git', '-C', str(std), 'status', '--porcelain']), 'dirty std'
assert hashlib.sha256((root / 'wolf-toolchain.toml').read_bytes()).hexdigest() == state['pins_sha256'], 'pin metadata drift'
for name, path in [('wolf', Path(state['wolf'])), ('lupin', Path(state['lupin'])), ('runtime', Path(state['wolf']).parent / 'libwolf_rt.a')]:
    assert hashlib.sha256(path.read_bytes()).hexdigest() == state[name + '_sha256'], 'toolchain drift'
ref = Path(os.environ['AGE_REF'])
for name, expected in [('age', 'eb7dd1b518f0a307c99cd97782623c5321da049154b04acd2d98d21aa7bc9b2c'), ('age-keygen', '0a0009db842259d6717f7eeb30acb6b90d2a2eb924c6acd0a0db0ca1f1537899')]:
    assert hashlib.sha256((ref / name).read_bytes()).hexdigest() == expected, 'reference drift'
engine = os.environ['AGE_ENGINE']
image = os.environ['AGE_IMAGE']
actual = subprocess.check_output([engine, 'image', 'inspect', image, '--format', '{{.Id}}'], text=True).strip()
assert actual.removeprefix('sha256:') == '77fdad6b841abfdb3968ea6137b1edf7248578bdfc4f92e4aab6b2a05f241485', 'image drift'
probe = '''for t in bash python3 git clang gcc nm objdump taskset; do command -v "$t" >/dev/null || exit 1; done
python3 -c "import tomllib"
python3 - <<'PY'
import os,tempfile
p='/work/notes/s263-evidence'
try:
 fd,name=tempfile.mkstemp(prefix='preflight-',dir=p)
 os.close(fd)
 os.unlink(name)
except OSError:
 print('REFUSED taskset-translator-log-unwritable path='+p,flush=True)
 raise SystemExit(75)
print('PASS translator log directory',flush=True)
PY
taskset -c "$AGE_CPUS" true || exit 75
taskset -c "$AGE_CPUS" python3 -I "$AGE_ROOT/tools/age-witness/affinity.py" "$AGE_CPUS" || exit 75
'''
result = subprocess.run([engine, 'run', '--rm', '--network', 'none', '--memory', '256m', '--volume', str(root)+':'+str(root)+':ro', '--volume', str(logdir)+':/work/notes/s263-evidence', '--env', 'AGE_ROOT', '--env', 'AGE_CPUS', '--env', 'PATH=/opt/s263-rust/bin:/usr/local/bin:/usr/bin:/bin', image, 'bash', '-c', probe])
if result.returncode:
    raise SystemExit(75 if result.returncode == 75 else result.returncode)
print('PASS standalone preflight: clean snapshot, disk/memory floors, binary/image pins and tools; no take run', flush=True)
