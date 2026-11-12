#!/usr/bin/env python3
"""Fetch only digest-pinned public toolchain artifacts into an ignored workspace."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tomllib
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.wolf-bin'


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while block := f.read(131072):
            h.update(block)
    return h.hexdigest()


def host():
    p = (platform.system(), platform.machine().lower())
    if p[0] == 'Linux' and p[1] in ('x86_64', 'amd64'):
        return 'x86_64-unknown-linux-gnu'
    if p[0] == 'Darwin' and p[1] in ('arm64', 'aarch64'):
        return 'aarch64-apple-darwin'
    raise RuntimeError('unsupported toolchain platform')


def command(args, **kw):
    return subprocess.check_output(args, text=True, **kw).strip()


def fetch(name, pin, target):
    directory = CACHE / 'downloads' / (name + '-' + target)
    directory.mkdir(parents=True, exist_ok=True)
    archive = directory / 'release.tar.gz'
    expected = pin[target]
    if not archive.exists():
        url = 'https://github.com/' + pin['repo'] + '/releases/download/v' + pin['version'] + '/' + name + '-' + pin['version'] + '-' + target + '.tar.gz'
        req = urllib.request.Request(url, headers={'User-Agent': 'pinned-toolchain-fetch'})
        partial = directory / 'download.part'
        try:
            with urllib.request.urlopen(req, timeout=90) as r, partial.open('xb') as out:
                shutil.copyfileobj(r, out, 131072)
            if sha256(partial) != expected:
                raise RuntimeError('release digest mismatch')
            partial.rename(archive)
        finally:
            partial.unlink(missing_ok=True)
    if sha256(archive) != expected:
        raise RuntimeError('cached release digest mismatch')
    extracted = CACHE / 'extracted' / (name + '-' + target)
    if not extracted.exists():
        extracted.mkdir(parents=True)
        if not hasattr(tarfile, 'data_filter'):
            raise RuntimeError('Python tar data filter required')
        with tarfile.open(archive, 'r:gz') as tar:
            tar.extractall(extracted, filter='data')
    if sha256(archive) != expected:
        raise RuntimeError('release changed during extraction')
    binaries = [p for p in extracted.rglob(name) if p.is_file() and not p.is_symlink() and os.access(p, os.X_OK)]
    if len(binaries) != 1:
        raise RuntimeError('ambiguous toolchain executable')
    binary = binaries[0]
    version = command([str(binary), '--version']).splitlines()[0]
    if not version.startswith(name + ' ' + pin['version'] + ' '):
        raise RuntimeError('toolchain version mismatch')
    print('PASS pin-' + name)
    return binary


def main():
    pins = tomllib.loads((ROOT / 'wolf-toolchain.toml').read_text())
    target = host()
    CACHE.mkdir(exist_ok=True)
    wolf = fetch('wolf', pins['wolf'], target)
    lupin = fetch('lupin', pins['lupin'], target)
    if not (wolf.parent / 'libwolf_rt.a').is_file():
        raise RuntimeError('paired runtime archive missing')
    std = CACHE / 'std-source'
    if not std.exists():
        subprocess.run(['git', 'init', '-q', str(std)], check=True)
        subprocess.run(['git', '-C', str(std), 'remote', 'add', 'origin', 'https://github.com/' + pins['std']['repo'] + '.git'], check=True)
    if command(['git', '-C', str(std), 'status', '--porcelain']):
        raise RuntimeError('standard library checkout is modified')
    try:
        current = command(['git', '-C', str(std), 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        current = ''
    if current != pins['std']['rev']:
        subprocess.run(['git', '-C', str(std), 'fetch', '--depth=1', 'origin', pins['std']['rev']], check=True)
        subprocess.run(['git', '-C', str(std), 'checkout', '--detach', '--quiet', pins['std']['rev']], check=True)
    tree = command(['git', '-C', str(std), 'rev-parse', 'HEAD^{tree}'])
    if tree != pins['std']['tree']:
        raise RuntimeError('standard library tree mismatch')
    if command(['git', '-C', str(std), 'status', '--porcelain']):
        raise RuntimeError('standard library checkout is modified')
    state = {'target': target, 'wolf': str(wolf), 'lupin': str(lupin), 'std': str(std / 'std'), 'pins_sha256': sha256(ROOT / 'wolf-toolchain.toml')}
    (CACHE / 'toolchain.json').write_text(json.dumps(state, indent=2) + '\n')
    print('PASS pin-std')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('FAIL toolchain ' + type(e).__name__)
        raise SystemExit(1)
