#!/usr/bin/env bash
set -eu
cd "$AGE_ROOT"
case "$1" in
  default|release)
    python3 -I tools/age-gate.py --workspace "$AGE_OUT/codec" --data "$AGE_ROOT/.work/age-vectors" --build "$1"
    ;;
  native)
    export DENWARD_WORKSPACE="$AGE_OUT/cli"
    python3 -I tools/gate.py --suite native
    ;;
  code)
    python3 -I tools/capture-age-code.py --workspace "$AGE_OUT/generated-code"
    ;;
  interop)
    python3 -I tests/age/interop.py --program "$AGE_OUT/codec/release/driver" --reference "$AGE_REF" --workspace "$AGE_OUT/interop"
    ;;
  lifetimes)
    python3 -I tests/age/lifetimes.py --program "$AGE_OUT/codec/release/driver" --workspace "$AGE_OUT/lifetimes"
    ;;
  primitives)
    python3 -I - <<'PY'
import json,os,pathlib,subprocess,sys
root=pathlib.Path(os.environ['AGE_ROOT']); out=pathlib.Path(os.environ['AGE_OUT'])
state=json.loads((root/'.wolf-bin/toolchain.json').read_text())
std=pathlib.Path(state['std']).parent
cmd=[sys.executable,'-I',str(std/'docs/dw03-witness/run-selected.py'),str(std),str(out/'primitive-postures'),'--wolf',state['wolf'],'--lupin',state['lupin'],'--all-selected','--tiers','checked,native,lupin,release']
process=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
for line in process.stdout:
 if line.startswith('PASS ') and ' unsupported' in line: line='UNSUPPORTED '+line[5:]
 print(line,end='',flush=True)
sys.exit(process.wait())
PY
    ;;
  *) exit 2 ;;
esac
