#!/usr/bin/env python3
"""Independent safe-member archive contracts; fake input only."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def build():
    state = json.loads((ROOT / '.wolf-bin/toolchain.json').read_text())
    env = os.environ.copy()
    env['WOLF_STD'] = state['std']
    out = ROOT / 'target/tests/archive-probe'
    out.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([state['wolf'], 'build', '--deny-warnings', 'tests/archive-probe/main.lu', '-o', str(out)], cwd=ROOT, env=env)
    if result.returncode:
        print('FAIL A00-archive-probe-build compiler-exit=' + str(result.returncode), flush=True)
        raise SystemExit(1)
    print('PASS A00-archive-probe-build', flush=True)
    return out


def main():
    subprocess.run([str(build())], check=True)


if __name__ == '__main__':
    main()
