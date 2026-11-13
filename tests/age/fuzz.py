#!/usr/bin/env python3
"""Bounded differential against a grammar model written alongside the parser.

It detects implementation slips, not shared specification misreadings.
Python's base64 codec is reused as a black box; no codec implementation is
copied. This is parser/outcome coverage, not statement/branch coverage.
"""
import argparse
import base64
import binascii
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import random
import resource
import subprocess
import time


def canonical(data):
    if b'=' in data:
        raise ValueError('padding')
    decoded = base64.b64decode(data + b'=' * (-len(data) % 4), validate=True)
    if base64.b64encode(decoded).rstrip(b'=') != data:
        raise ValueError('noncanonical')
    return decoded


def oracle(raw):
    if len(raw) > 1048576:
        return 'budget'
    at = 0

    def line(limit, budget=True):
        nonlocal at
        end = raw.find(b'\n', at)
        if end < 0:
            if len(raw) - at > limit:
                return None, 'budget' if budget else 'header'
            return None, 'header'
        if end - at + 1 > limit:
            return None, 'budget' if budget else 'header'
        value = raw[at:end]
        at = end + 1
        return value, None

    first, error = line(4096)
    if error:
        return error
    if any(c < 32 or c > 126 for c in first):
        return 'header'
    if first != b'age-encryption.org/v1':
        return 'unsupported' if first.startswith(b'age-encryption.org/') or first == b'-----BEGIN AGE ENCRYPTED FILE-----' else 'header'
    count = 0
    scrypt = False
    try:
        while at < len(raw):
            args, error = line(4096)
            if error:
                return error
            if any(c < 32 or c > 126 for c in args):
                return 'header'
            if args.startswith(b'---'):
                if count == 0 or len(args) != 47 or not args.startswith(b'--- ') or at != len(raw):
                    return 'header'
                return 'parsed' if len(canonical(args[4:])) == 32 else 'header'
            if not args.startswith(b'-> ') or len(args) < 4 or args.endswith(b' ') or b'  ' in args:
                return 'header'
            arguments = args[3:].split(b' ')
            count += 1
            if count > 64:
                return 'budget'
            scrypt |= arguments[0] == b'scrypt'
            if scrypt and count > 1:
                return 'header'
            body = bytearray()
            while True:
                part, error = line(65, budget=False)
                if error:
                    return error
                body.extend(part)
                if len(part) < 64:
                    break
            decoded = canonical(bytes(body))
            if arguments[0] == b'X25519':
                if len(arguments) != 2 or len(decoded) != 32 or len(canonical(arguments[1])) != 32:
                    return 'header'
    except (ValueError, binascii.Error):
        return 'header'
    return 'header'


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (268435456, 268435456))
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--program', type=Path, required=True)
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--cases', type=int, default=1000)
    a = p.parse_args()
    if not 1 <= a.cases <= 10000:
        raise ValueError('test budget')
    a.workspace.mkdir(parents=True, exist_ok=False, mode=0o700)
    vector_data = (a.data / 'x25519').read_bytes()
    root = Path(__file__).resolve().parents[2]
    inventory = json.loads((root / 'tests/age/inventory.json').read_text())
    expected = next(c['sha256'] for c in inventory['cases'] if c['name'] == 'x25519')
    if len(vector_data) > 1048576 or hashlib.sha256(vector_data).hexdigest() != expected:
        raise ValueError('published vector digest mismatch')
    raw, encrypted = vector_data.split(b'\n\n', 1)
    end = encrypted.index(b'\n', encrypted.index(b'\n--- ') + 1) + 1
    baseline = encrypted[:end]
    outcomes, mutations = Counter(), Counter()
    started = time.monotonic()

    def execute(data):
        try:
            r = subprocess.run([str(a.program)], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3, preexec_fn=limits)
        except subprocess.TimeoutExpired:
            return 'timeout'
        answer = r.stdout.decode('ascii', 'replace').strip()
        if r.stderr or len(r.stdout) > 128 or (r.returncode, answer) not in [(0, 'parsed'), (1, 'header'), (1, 'budget'), (1, 'unsupported')]:
            return 'abnormal-' + str(r.returncode)
        return answer

    def minimize(data):
        trials = 0
        start = time.monotonic()
        width = max(1, len(data) // 2)
        while width and trials < 128 and time.monotonic() - start < 30:
            changed = False
            for at in range(0, len(data), width):
                candidate = data[:at] + data[at + width:]
                trials += 1
                if execute(candidate) != oracle(candidate):
                    data = candidate
                    changed = True
                    break
                if trials >= 128 or time.monotonic() - start >= 30:
                    break
            if not changed:
                width //= 2
        return data, trials

    journal = a.workspace / 'cases.jsonl'
    with journal.open('x') as log:
        for seed in [0x44573034, 0x137173, 0x8439]:
            rng = random.Random(seed)
            for case in range(a.cases):
                if time.monotonic() - started > 900:
                    print('FAIL parser-fuzz/time-budget', flush=True)
                    return 1
                op = case % 8
                data = baseline
                at = rng.randrange(len(data))
                if op == 0:
                    data = data[:at] + bytes([rng.randrange(256)]) + data[at + 1:]
                elif op == 1:
                    data = data[:at] + bytes([rng.randrange(256)]) + data[at:]
                elif op == 2:
                    data = data[:at] + data[at + 1:]
                elif op == 3:
                    data = data[:at]
                elif op == 4:
                    data = data.replace(b'\n', rng.choice([b'\r\n', b'\0\n', b'\xff\n']))
                elif op == 5:
                    body = b'A' * rng.randrange(0, 130)
                    data = b'age-encryption.org/v1\n-> unknown\n' + body + b'\n--- ' + b'A' * 43 + b'\n'
                elif op == 6:
                    count = rng.choice([0, 1, 2, 63, 64, 65])
                    data = b'age-encryption.org/v1\n' + b'-> unknown\n\n' * count + b'--- ' + b'A' * 43 + b'\n'
                else:
                    data = baseline[:at] + rng.choice([b' ', b'=', b'\x7f', b'\r', b'\0']) * rng.randrange(1, 20) + baseline[at:]
                if len(data) > 16384:
                    raise ValueError('mutation input budget exceeded')
                expected, actual = oracle(data), execute(data)
                outcomes[actual] += 1
                mutations[str(op)] += 1
                row = dict(seed=seed, case=case, mutation=op, input_sha256=hashlib.sha256(data).hexdigest(), expected=expected, actual=actual)
                log.write(json.dumps(row, sort_keys=True) + '\n')
                if actual != expected:
                    minimal, trials = minimize(data)
                    digest = hashlib.sha256(minimal).hexdigest()
                    (a.workspace / (digest + '.bin')).write_bytes(minimal)
                    (a.workspace / (digest + '.json')).write_text(json.dumps(dict(row, minimized_sha256=digest, minimized_bytes=len(minimal), minimization_trials=trials, minimized_expected=oracle(minimal), minimized_actual=execute(minimal)), indent=2) + '\n')
                    print('FAIL parser-fuzz/' + str(seed) + '/' + str(case) + ' counterexample=' + digest, flush=True)
                    return 1
                if case % 100 == 0:
                    print('PASS parser-fuzz-progress seed=' + str(seed) + ' cases=' + str(case + 1), flush=True)
    report = dict(seeds=[0x44573034, 0x137173, 0x8439], cases_per_seed=a.cases, seconds=time.monotonic() - started, outcomes=dict(outcomes), mutations=dict(mutations), counterexamples=0, allocation_limit=268435456, input_limit=16384, output_limit=128, coverage='grammar/outcome/mutation categories; not statement or branch coverage')
    (a.workspace / 'coverage.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS parser-fuzz cases=' + str(3 * a.cases) + ' seed-count=3 counterexamples=0', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
