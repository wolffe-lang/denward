#!/usr/bin/env python3
"""Internal parser native gate; never enables data verbs or host inventory."""
import argparse,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--workspace',required=True);a=p.parse_args();work=Path(a.workspace).resolve();work.mkdir(parents=True,exist_ok=True)
 state=json.loads((ROOT/'.wolf-bin/toolchain.json').read_text())
 env=os.environ.copy();env.update(WOLF_STD=state['std'],TMPDIR=str(work),RAYON_NUM_THREADS='2')
 for mode in ['default','release']:
  stage=work/mode;stage.mkdir(exist_ok=True);program=stage/'parser'
  args=[state['wolf'],'build','--deny-warnings']
  if mode=='release':args.append('--release')
  subprocess.run(args+[str(ROOT/'tests/manifest/driver/main.lu'),'-o',str(program)],check=True,cwd=ROOT,env=env)
  for script,extra in [('check.py',[]),('mutate.py',[]),('memory.py',['--workspace',str(stage/'memory')])]:
   subprocess.run([sys.executable,'-I',str(ROOT/'tests/manifest'/script),'--program',str(program),*extra],check=True,cwd=ROOT,env=env)
  print('PASS manifest_'+mode,flush=True)
if __name__=='__main__':main()
