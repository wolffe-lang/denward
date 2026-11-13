#!/usr/bin/env python3
"""Mutation tests for exact vendored-source provenance; never edit the real copy."""
import json
import os
from pathlib import Path
import runpy
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CHECK = runpy.run_path(str(ROOT / 'tools/check-archive-pin.py'))['check']


def main():
    original = ROOT / 'vendor/package-archive'
    assert CHECK(original) == ''
    cases = ['source-byte', 'missing-source', 'extra-code', 'glue-byte', 'wrong-revision', 'missing-record', 'symlink-source']
    for case in cases:
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR'], prefix='archive-pin-') as tmp:
            target = Path(tmp) / 'dependency'
            shutil.copytree(original, target, ignore=shutil.ignore_patterns('.lu-cache'))
            source = target / 'packing/packing.lu'
            if case == 'source-byte':
                source.write_bytes(source.read_bytes()+b'\n')
            elif case == 'missing-source':
                source.unlink()
            elif case == 'extra-code':
                (target/'packing/extra.lu').write_text('// unexpected module code\n')
            elif case == 'glue-byte':
                glue = target/'packing/wolf.pkg'
                glue.write_bytes(glue.read_bytes()+b'\n')
            elif case == 'symlink-source':
                source.unlink(); source.symlink_to(original/'packing/packing.lu')
            else:
                manifest = target/'provenance.json'
                data = json.loads(manifest.read_text())
                if case == 'wrong-revision':
                    data['revision'] = '0'*40
                else:
                    data['files'].pop()
                manifest.write_text(json.dumps(data))
            assert CHECK(target), case
            print('PASS V02-provenance-refuses-'+case, flush=True)


if __name__ == '__main__':
    main()
