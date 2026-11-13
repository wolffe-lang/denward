#!/usr/bin/env python3
"""Capture selected generated code for an independent reader, not timing proof."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--workspace', type=Path, required=True)
args = parser.parse_args()
state = json.loads((ROOT / '.wolf-bin/toolchain.json').read_text())
pins_path = ROOT / 'wolf-toolchain.toml'
if hashlib.sha256(pins_path.read_bytes()).hexdigest() != state['pins_sha256']:
    raise ValueError('toolchain pin identity mismatch')
pins = tomllib.loads(pins_path.read_text())
for name, path in [('wolf', Path(state['wolf'])), ('lupin', Path(state['lupin'])), ('runtime', Path(state['wolf']).parent / 'libwolf_rt.a')]:
    if hashlib.sha256(path.read_bytes()).hexdigest() != state[name + '_sha256']:
        raise ValueError('toolchain binary identity mismatch')
env = os.environ.copy()
env.update(WOLF_STD=state['std'], TMPDIR=str(args.workspace))
args.workspace.mkdir(parents=True, exist_ok=True)
for mode in ['default', 'release']:
    stage = args.workspace / mode
    stage.mkdir(exist_ok=True)
    out = stage / 'codec.o'
    command = [state['wolf'], 'build', str(ROOT / 'tests/age/driver/main.lu'), '--emit=obj', '-o', str(out)]
    if mode == 'release':
        command.append('--release')
    subprocess.run([sys.executable, '-I', str(ROOT / 'tools/mac-resource.py')], cwd=ROOT, env=env, check=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True, timeout=180)
    objects = sorted(stage.glob('*.o'))
    if not objects:
        raise ValueError('missing generated objects')
    inventory = []
    for obj in objects:
        symbols = subprocess.check_output(['nm', str(obj)], text=True)
        obj.with_suffix('.symbols').write_text(symbols)
        command = ['otool', '-tvV', str(obj)] if platform.system() == 'Darwin' else ['objdump', '-dr', str(obj)]
        assembly = subprocess.check_output(command, text=True)
        obj.with_suffix('.asm').write_text(assembly)
        inventory.append({'object': obj.name, 'sha256': hashlib.sha256(obj.read_bytes()).hexdigest(), 'assembly_sha256': hashlib.sha256(assembly.encode()).hexdigest()})
    (stage / 'objects.json').write_text(json.dumps(inventory, indent=2) + '\n')
    if mode == 'release':
        subprocess.run([sys.executable, '-I', str(ROOT / 'tools/division-gate.py'), '--workspace', str(stage), '--inventory', str(ROOT / 'tests/age/division-known-sites.json'), '--target', state['target'], '--std', pins['std']['rev'], '--compiler', pins['wolf']['rev']], cwd=ROOT, env=env, check=True)
    print('PASS generated-code-capture/' + mode + ' review-required', flush=True)
