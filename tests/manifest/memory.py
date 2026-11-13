#!/usr/bin/env python3
"""Generated bounded fixtures, not inventory or backup production capacity."""
import argparse,base64,json,platform,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--program',required=True);p.add_argument('--workspace',required=True);a=p.parse_args()
 work=Path(a.workspace).resolve();work.mkdir(parents=True,exist_ok=True)
 vectors=json.loads((ROOT/'tests/manifest/vectors.json').read_text());raw=base64.b64decode(vectors[1]['base64']);rows=[json.loads(x) for x in raw.splitlines()]
 def line(row):return json.dumps(row,separators=(',',':'),ensure_ascii=False).encode()+b'\n'
 def case(name,count,width=0,want='parsed',users=False):
  path=work/(name+'.jsonl')
  with path.open('wb') as out:
   for row in rows[:5]:out.write(line(row))
   for i in range(count):
    f=dict(rows[-2]);f['path']=('%05d'%i)+('x'*width)
    if users:f.update(user='u'*4096,group='g'*4096)
    out.write(line(f))
   end=dict(rows[-1]);end['file_count']=count;out.write(line(end))
  cases.append((path,want))
 cases=[]
 # Linux growth series only. Mac is a fixed pair of bounded correctness extremes.
 if platform.system()=='Linux':
  for n in [1,128,1024]:case('entries-'+str(n),n)
 case('entry-limit',4090);case('entry-over',4091,want='manifest_budget')
 case('long-paths',1900,4091)
 case('text-over',1024,want='manifest_budget',users=True)
 # Exact encoded line bound is LF inclusive; whitespace remains ordinary JSON.
 first=line(rows[0]);rest=b''.join(line(x) for x in rows[1:])
 for length,want in [(1048576,'parsed'),(1048577,'manifest_budget')]:
  f=work/('line-'+str(length)+'.jsonl');f.write_bytes(first[:-1]+b' '*(length-len(first))+b'\n'+rest);cases.append((f,want))
 # Parent never holds the large generated fixture. Each rusage process starts anew.
 for source,want in cases:
  subprocess.run([sys.executable,'-I',str(ROOT/'tests/manifest/measure.py'),'--program',str(Path(a.program).resolve()),'--input',str(source),'--expected',want],check=True)
 print('PASS manifest_bounded_memory cases='+str(len(cases)),flush=True)
if __name__=='__main__':main()
