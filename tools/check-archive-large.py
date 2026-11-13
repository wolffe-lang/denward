#!/usr/bin/env python3
"""Capped Linux-only generated archive streams; no archive/data spool or crypto claim."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import resource
import runpy
import select
import shutil
import signal
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
REF = runpy.run_path(str(ROOT/'tools/check-archive.py'))
BLOCK = 1024*1024


def pattern(length):
    left = length
    index = 0
    while left:
        n = min(BLOCK, left)
        yield bytes([index % 251])*n
        index += 1
        left -= n


def size_extension(length):
    body = b' size='+str(length).encode()+b'\n'
    n = len(body)+1
    while len(str(n))+len(body) != n:
        n = len(str(n))+len(body)
    raw = str(n).encode()+body
    return REF['header']('PaxHeader', b'x', len(raw), 0o644)+raw+bytes((-len(raw)) % 512)


def initial(length, digest):
    extension = size_extension(length) if length > 8589934591 else b''
    return REF['prefix']()+extension+REF['header']('objects/'+digest, length=0 if extension else length)


def peak(stderr):
    m = re.search(rb'Maximum resident set size \(kbytes\):\s*(\d+)', stderr)
    if not m:
        raise AssertionError('GNU time RSS absent')
    return int(m[1])


def stop_owned(child, binary):
    if child.poll() is not None:
        return
    # GNU time owns one native child. End only that verified descendant by pid,
    # then let its recorded parent reap it; never signal a process group.
    path = Path('/proc')/str(child.pid)/'task'/str(child.pid)/'children'
    try:
        children = path.read_text().split()
    except FileNotFoundError:
        children = []
    for item in children:
        pid = int(item)
        try:
            command = (Path('/proc')/item/'cmdline').read_bytes().split(b'\0')
            status = (Path('/proc')/item/'status').read_text()
            if command[0] == os.fsencode(binary) and re.search(r'^PPid:\s*'+str(child.pid)+r'\s*$',status,re.M):
                os.kill(pid,signal.SIGKILL)
        except ProcessLookupError:
            pass
        except FileNotFoundError:
            pass
    try:
        child.wait(timeout=10)
    except subprocess.TimeoutExpired:
        child.kill(); child.wait()


def case(binary, timer, length, floor):
    body_hash = hashlib.sha256()
    for block in pattern(length):
        body_hash.update(block)
    digest = body_hash.hexdigest()
    before = initial(length, digest)
    total = len(before)+length+(-length) % 512+1024
    env = os.environ.copy(); env['LC_ALL'] = 'C'
    reader = subprocess.Popen([timer,'-v',str(binary),'inspect',str(total)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    writer = subprocess.Popen([timer,'-v',str(binary),'emit',str(length),digest], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    errors = []
    def feed():
        try:
            for block in pattern(length):
                writer.stdin.write(block)
            writer.stdin.close()
        except Exception as e:
            errors.append(e)
    feeder = threading.Thread(target=feed, daemon=True); feeder.start()
    observed = hashlib.sha256(); wire = hashlib.sha256(); count = 0; next_progress = 1024**3
    deadline = time.monotonic()+3600
    os.set_blocking(reader.stdin.fileno(),False)
    try:
        while True:
            if time.monotonic()>deadline:
                raise AssertionError('archive stream deadline')
            if not select.select([writer.stdout],[],[],1)[0]:
                continue
            block = os.read(writer.stdout.fileno(),131072)
            if not block:
                break
            end = count+len(block)
            if end > total:
                raise AssertionError('extra archive output')
            if count < len(before):
                n = min(len(block),len(before)-count)
                assert block[:n] == before[count:count+n], 'independent prefix mismatch'
            start_data = max(count,len(before)); end_data = min(end,len(before)+length)
            if end_data > start_data:
                observed.update(memoryview(block)[start_data-count:end_data-count])
            if end > len(before)+length:
                assert not any(block[max(0,len(before)+length-count):]), 'nonzero final padding'
            at = 0
            while at < len(block):
                if time.monotonic()>deadline:
                    raise AssertionError('archive consumer deadline')
                if not select.select([],[reader.stdin],[],1)[1]:
                    continue
                try:
                    wrote = os.write(reader.stdin.fileno(),memoryview(block)[at:])
                except BlockingIOError:
                    continue
                assert wrote>0, 'zero observer write'
                at += wrote
            wire.update(block); count = end
            if count >= next_progress:
                print('archive-growth bytes='+str(length)+' transferred='+str(count),flush=True)
                next_progress += 1024**3
        reader.stdin.close()
        feeder.join(timeout=10)
        assert not feeder.is_alive() and not errors, 'source feeder failed'
        assert writer.wait(timeout=30) == 0, 'archive producer failed'
        assert reader.wait(timeout=30) == 0, 'archive inspector failed'
        result = reader.stdout.read().strip()
        writer_error = writer.stderr.read(); reader_error = reader.stderr.read()
        producer_peak = peak(writer_error); reader_peak = peak(reader_error)
        assert result == b'physical:7' and count == total and observed.hexdigest() == digest, 'archive stream mismatch'
        assert b'archive:' not in writer_error and b'refused:' not in result, 'unexpected archive error'
        assert producer_peak < 262144 and reader_peak < 262144, 'runtime RSS exceeds 256 MiB'
        assert floor < 32768, 'small-parent floor unqualified'
        print('ARCHIVE-GROWTH bytes='+str(length)+' wire_bytes='+str(count)+' producer_peak_kib='+str(producer_peak)+' reader_peak_kib='+str(reader_peak)+' floor_kib='+str(floor)+' wire_sha256='+wire.hexdigest(),flush=True)
        print('PASS L01-complete-archive-'+str(length),flush=True)
        return producer_peak,reader_peak
    finally:
        for child in [writer,reader]:
            stop_owned(child,binary)
        feeder.join(timeout=10)
        for stream in [writer.stdin,writer.stdout,writer.stderr,reader.stdin,reader.stdout,reader.stderr]:
            try:
                stream.close()
            except BrokenPipeError:
                pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sizes', choices=['smoke','full'], default='full')
    a = ap.parse_args()
    cap = resource.getrlimit(resource.RLIMIT_AS)[0]
    if not sys.platform.startswith('linux') or cap == resource.RLIM_INFINITY or cap > 2147483648:
        raise SystemExit('FAIL archive-growth-requires-capped-Linux')
    binary = ROOT/'target/tests/archive-probe'
    if not binary.is_file():
        raise SystemExit('FAIL archive-growth-probe-missing')
    timer = shutil.which('time')
    if not timer:
        raise SystemExit('FAIL archive-growth-GNU-time-missing')
    baseline = subprocess.run([timer,'-v','sleep','1'],capture_output=True,check=True,env={**os.environ,'LC_ALL':'C'})
    floor = peak(baseline.stderr)
    sizes = [1024**3] if a.sizes == 'smoke' else [1024**3,8*1024**3,32*1024**3]
    results = [case(binary,timer,n,floor) for n in sizes]
    if len(results)>1:
        assert max(x[0] for x in results)-min(x[0] for x in results)<8192, 'producer RSS growth'
        assert max(x[1] for x in results)-min(x[1] for x in results)<8192, 'reader RSS growth'
    print('PASS L02-fixed-buffer-archive-growth',flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('FAIL archive-growth '+type(e).__name__+' '+str(e),flush=True)
        raise SystemExit(1)
