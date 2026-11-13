#!/usr/bin/env python3
"""Check exact public archive source bytes and explicitly separate import glue."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PIN = '2c69152ba9aa760ec5104b65a23ef961bfa83368'
MODULES = {'packing', 'payload', 'literal', 'schema', 'model', 'version'}


def check(directory):
    try:
        p = json.loads((directory / 'provenance.json').read_text())
        if set(p) != {'schema', 'repository', 'revision', 'files', 'local_package_glue'} or p['schema'] != 1 or p['repository'] != 'https://github.com/wolffe-lang/paxage' or p['revision'] != PIN:
            return 'archive-provenance-identity'
        source_paths = {name + '/' + name + '.lu' for name in MODULES} | {'LICENSE', 'LICENSE-TRAINING-DATA'}
        glue_paths = {name + '/wolf.pkg' for name in MODULES}
        if len(p['files']) != len(source_paths) or {x['path'] for x in p['files']} != source_paths or len(p['local_package_glue']) != len(glue_paths) or {x['path'] for x in p['local_package_glue']} != glue_paths:
            return 'archive-provenance-closure'
        actual = {str(x.relative_to(directory)) for x in directory.rglob('*') if x.suffix in {'.lu', '.pkg'} and x.is_file()}
        if actual != source_paths - {'LICENSE', 'LICENSE-TRAINING-DATA'} | glue_paths:
            return 'archive-provenance-extra-code'
        for item in p['files'] + p['local_package_glue']:
            path = directory / item['path']
            if path.resolve() != directory.resolve() / item['path'] or not path.is_file():
                return 'archive-provenance-path'
            raw = path.read_bytes()
            if not re.fullmatch('[0-9a-f]{64}', item['sha256']) or hashlib.sha256(raw).hexdigest() != item['sha256']:
                return 'archive-provenance-digest'
            if item in p['files']:
                wanted = item['path'] if item['path'].startswith('LICENSE') else 'src/' + item['path']
                blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
                if set(item) != {'path', 'upstream_path', 'sha256', 'git_blob'} or item['upstream_path'] != wanted or item['git_blob'] != blob:
                    return 'archive-provenance-blob'
            elif set(item) != {'path', 'sha256'}:
                return 'archive-provenance-glue'
        return ''
    except (OSError, ValueError, KeyError, TypeError):
        return 'archive-provenance-format'


def main():
    error = check(ROOT / 'vendor/package-archive')
    if error:
        raise SystemExit('FAIL V01-pinned-archive-source ' + error)
    print('PASS V01-pinned-archive-source ' + PIN)


if __name__ == '__main__':
    main()
