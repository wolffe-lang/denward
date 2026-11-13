#!/usr/bin/env python3
"""Read back affinity inside the translator's child; never change its mask."""
import json
import os
import sys


def mask(text):
    cpus = set()
    for part in text.split(','):
        ends = part.split('-')
        if len(ends) == 1:
            cpus.add(int(ends[0]))
        elif len(ends) == 2:
            cpus.update(range(int(ends[0]), int(ends[1]) + 1))
        else:
            raise ValueError('CPU mask')
    if not cpus or not cpus <= set(range(18)):
        raise ValueError('reserved or empty CPU mask')
    return cpus


requested = sys.argv[1]
held = os.environ.get('AGE_HELD_CPUS', requested)
allowed = mask(held)
mask(requested)
actual = set(os.sched_getaffinity(0))
print('AFFINITY ' + json.dumps(dict(requested=requested, held=held, actual=sorted(actual)), sort_keys=True), flush=True)
if not actual or not actual <= allowed:
    print('REFUSED translator-affinity-outside-held-mask', flush=True)
    raise SystemExit(75)
