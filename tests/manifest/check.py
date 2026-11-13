#!/usr/bin/env python3
"""Frozen hostile bytes, independent outcomes; no production credentials."""
import argparse, base64, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--program',required=True);p.add_argument('--only');a=p.parse_args()
 rows=json.loads((ROOT/'tests/manifest/vectors.json').read_text())
 rows.append(dict(name='manifest_line_budget',raw=b' '*1048576+b'\n',reason='manifest_budget'))
 failed=[]
 for row in rows:
  if a.only and row['name']!=a.only:continue
  raw=row.get('raw',base64.b64decode(row.get('base64','')))
  r=subprocess.run([a.program],input=raw,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
  want=row['reason'];ok=r.returncode==(0 if want=='parsed' else 1) and r.stdout== (want+'\n').encode() and r.stderr==b''
  print(('PASS ' if ok else 'FAIL ')+row['name'],flush=True)
  if not ok:
   print('  expected='+want+' actual='+repr(r.stdout[:100])+' status='+str(r.returncode),flush=True);failed.append(row['name'])
 if a.only and not any(r['name']==a.only for r in rows):raise RuntimeError('unknown row')
 raise SystemExit(bool(failed))
if __name__=='__main__':main()
