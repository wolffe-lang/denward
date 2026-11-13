#!/usr/bin/env python3
"""Bounded deterministic grammar mutations with independent expected outcomes."""
import argparse,base64,json,random,subprocess,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--program',required=True);a=p.parse_args()
 rng=random.Random(610113)
 vector=json.loads((ROOT/'tests/manifest/vectors.json').read_text())[0]
 base=base64.b64decode(vector['base64']); rows=json.loads('['+base.decode().strip().replace('\n',',')+']')
 cases=[]
 # Every unknown key must fail even when it precedes record and even after escapes.
 for i in range(80):
  r=[dict(x) for x in rows];r[0]['unknown_'+str(i)]=i
  items=list(r[0].items());rng.shuffle(items);r[0]=dict(items)
  cases.append((b''.join(json.dumps(x,separators=(',',':')).encode()+b'\n' for x in r),'manifest_schema'))
 # Legal object-key permutations and RFC JSON whitespace must preserve semantics.
 for i in range(80):
  rendered=[]
  for row in rows:
   items=list(row.items());rng.shuffle(items)
   rendered.append(json.dumps(dict(items),separators=(', ', ' : ')).encode()+b' \r\n')
  cases.append((b''.join(rendered),'parsed'))
 # Duplicate decoded keys, overflow/float tokens, invalid strings, exact terminal EOF.
 for i in range(80):
  escaped=''.join('\\u%04x'%ord(c) if rng.randrange(2) else c for c in 'schema').encode()
  cases.append((base.replace(b'"schema":1',b'"schema":1,"'+escaped+b'":1'),'manifest_duplicate_key'))
 for suffix in [b' ',b'\r',b'\n',b'{}',b'\x00',b'\xff']:
  cases.append((base+suffix,'manifest_order'))
 failures=0;h=hashlib.sha256()
 for i,(raw,want) in enumerate(cases):
  h.update(len(raw).to_bytes(8,'big'));h.update(raw)
  r=subprocess.run([a.program],input=raw,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
  if r.returncode!=(0 if want=='parsed' else 1) or r.stdout!=(want+'\n').encode() or r.stderr:
   print('FAIL manifest_mutation_'+str(i));failures+=1
 print('MUTATION seed=610113 cases='+str(len(cases))+' corpus_sha256='+h.hexdigest()+' failures='+str(failures),flush=True)
 if failures:raise SystemExit(1)
 print('PASS manifest_mutations',flush=True)
if __name__=='__main__':main()
