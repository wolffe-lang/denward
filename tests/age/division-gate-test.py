#!/usr/bin/env python3
"""Gate planted instruction fixtures: all widths, additions, moves and removals."""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('division_gate', ROOT / 'tools/division-gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--require-wired', action='store_true')
    a = p.parse_args()
    a.workspace.mkdir(parents=True, exist_ok=False)
    assembly = a.workspace / 'fixture.asm'
    baseline = '''00000000 <_Wstd.x.crypto.curve25519.ladder$abc>:
   0: f6 f6 div %sil
00000010 <_Wstd.x.crypto.chacha20.poly1305$abc>:
  10: c3 ret
00000020 <_Wstd.x.crypto.sha2.compress256$abc>:
  20: c3 ret
00000030 <_Wstd.bech32.decode_bytes$abc>:
  30: c3 ret
'''
    assembly.write_text(baseline)
    sites, _ = gate.scan(a.workspace)
    known = {'std': 'std-pin', 'compiler': 'compiler-pin', 'targets': {'test': {'sites': sites, 'counts': {'std.x.crypto.curve25519.ladder': 1}, 'known': [{'function': 'std.x.crypto.curve25519.ladder', 'count': 1, 'issue': 'wolffe-lang/wolf-std#151'}]}}}
    assert gate.check(a.workspace, known, 'test', 'std-pin', 'compiler-pin')[0]
    for op in ['div', 'divb', 'divw', 'divl', 'divq', 'idiv', 'idivb', 'idivw', 'idivl', 'idivq', 'sdiv', 'udiv']:
        assembly.write_text(baseline.replace('  10: c3 ret', '  10: f7 f1 ' + op + ' %ecx'))
        assert not gate.check(a.workspace, known, 'test', 'std-pin', 'compiler-pin')[0], op
    for changed in [baseline.replace('   0: f6 f6 div %sil', '   0: c3 ret'), baseline.replace('   0: f6 f6 div %sil', '   1: f6 f6 div %sil'), baseline.replace('curve25519.ladder$', 'curve25519.other$')]:
        assembly.write_text(changed)
        assert not gate.check(a.workspace, known, 'test', 'std-pin', 'compiler-pin')[0]
    assembly.write_text(baseline)
    assert not gate.check(a.workspace, known, 'test', 'new-std-pin', 'compiler-pin')[0]
    print('PASS release-division-new-moved-missing-and-all-widths', flush=True)
    if a.require_wired and 'division-gate.py' not in (ROOT / 'tools/capture-age-code.py').read_text():
        print('FAIL release-division-gate-wired', flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
