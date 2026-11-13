#!/usr/bin/env python3
"""One locked, fixed-profile macOS correctness take; no timing claims."""
import hashlib,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
base=Path(os.environ['MANIFEST_LANE']).resolve()
root=Path(os.environ['MANIFEST_ROOT']).resolve()
lock=base.parent/'mac-build.lock'
def main():
 subprocess.run(['sw_vers'],check=True);subprocess.run(['uptime'],check=True)
 while os.getloadavg()[0]>=8:
  print('WAIT load='+str(os.getloadavg()),flush=True);time.sleep(30)
 if shutil.disk_usage(base).free<25*1024**3:raise RuntimeError('disk floor')
 busy=subprocess.check_output(['ps','-axo','pid,args'],text=True)
 for line in busy.splitlines():
  if re.search(r'\b(?:wolf build|cargo (?:build|test)|clang .* -o )',line):raise RuntimeError('another build active')
 last=base/'last-release'
 if last.exists():time.sleep(max(0,60-(time.time()-float(last.read_text()))))
 while True:
  try:lock.mkdir();break
  except FileExistsError:print('WAIT build lock',flush=True);time.sleep(30)
 (lock/'pid').write_text(str(os.getpid()));(lock/'lane').write_text('dw06')
 try:
  vm=subprocess.check_output(['vm_stat'],text=True);page=int(re.search(r'page size of (\d+)',vm)[1]);pages=sum(int(re.search(r'Pages '+n+r':\s*(\d+)',vm)[1]) for n in ['free','inactive','speculative'])
  if pages*page<8*1024**3:raise RuntimeError('memory floor')
  if shutil.disk_usage(base).free<25*1024**3 or os.getloadavg()[0]>=8:raise RuntimeError('resource state changed')
  state=json.loads((root/'.wolf-bin/toolchain.json').read_text());print('PINSET '+json.dumps(state,sort_keys=True),flush=True)
  for key in ['wolf','lupin']:
   if hashlib.sha256(Path(state[key]).read_bytes()).hexdigest()!=state[key+'_sha256']:raise RuntimeError('tool digest')
  if hashlib.sha256((Path(state['wolf']).parent/'libwolf_rt.a').read_bytes()).hexdigest()!=state['runtime_sha256']:raise RuntimeError('runtime digest')
  if hashlib.sha256((root/'wolf-toolchain.toml').read_bytes()).hexdigest()!=state['pins_sha256']:raise RuntimeError('pinset digest')
  std=Path(state['std']).parent
  if subprocess.check_output(['git','-C',str(std),'status','--porcelain'],text=True):raise RuntimeError('std modified')
  print('STD rev='+subprocess.check_output(['git','-C',str(std),'rev-parse','HEAD'],text=True).strip()+' tree='+subprocess.check_output(['git','-C',str(std),'rev-parse','HEAD^{tree}'],text=True).strip(),flush=True)
  for key in ['wolf','lupin']:subprocess.run([state[key],'--version'],check=True)
  print('CORRECTNESS load='+str(os.getloadavg())+' workers=2',flush=True)
  env=os.environ.copy();env.update(WOLF_STD=state['std'],TMPDIR=str(base),RAYON_NUM_THREADS='2',CARGO_BUILD_JOBS='2')
  subprocess.run([sys.executable,'-I',str(root/'tools/manifest-gate.py'),'--workspace',str(base/'mac-parser')],cwd=root,env=env,check=True)
 finally:
  for name in ['pid','lane']:(lock/name).unlink()
  lock.rmdir();last.write_text(str(time.time()))
if __name__=='__main__':main()
