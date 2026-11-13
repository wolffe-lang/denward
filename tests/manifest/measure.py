#!/usr/bin/env python3
"""Single small parent per observation; inherited peaks reported, never subtracted."""
import argparse,json,platform,resource,subprocess
from pathlib import Path
CAP=268435456

def main():
 p=argparse.ArgumentParser();p.add_argument('--program',required=True);p.add_argument('--input',required=True);p.add_argument('--expected',required=True);a=p.parse_args()
 linux=platform.system()=='Linux'
 def limit():
  if linux:resource.setrlimit(resource.RLIMIT_AS,(CAP,CAP))
  resource.setrlimit(resource.RLIMIT_CPU,(60,60));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 parent=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
 with Path(a.input).open('rb') as source:
  r=subprocess.run([a.program],stdin=source,stdout=subprocess.PIPE,stderr=subprocess.PIPE,preexec_fn=limit,timeout=70)
 peak=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
 scale=1024 if linux else 1
 ok=r.returncode==(0 if a.expected=='parsed' else 1) and r.stdout==(a.expected+'\n').encode() and not r.stderr and peak*scale<CAP
 print(json.dumps(dict(input=Path(a.input).name,parent_peak_bytes=parent*scale,child_peak_upper_bytes=peak*scale,as_cap=CAP if linux else None,returncode=r.returncode,passed=ok),sort_keys=True),flush=True)
 raise SystemExit(not ok)
if __name__=='__main__':main()
