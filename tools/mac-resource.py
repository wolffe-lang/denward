#!/usr/bin/env python3
"""Local shared-Mac build floor; isolated hosted runners do not use this lock."""
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

if platform.system() == 'Darwin' and os.environ.get('AGE_MAC_LOCK'):
    stats = subprocess.check_output(['vm_stat'], text=True)
    page = int(re.search(r'page size of (\d+)', stats)[1])
    available = sum(int(re.search(r'Pages ' + key + r':\s+(\d+)', stats)[1]) for key in ['free', 'inactive', 'speculative']) * page
    free = shutil.disk_usage(Path(__file__).resolve().parents[1]).free
    print('RESOURCE before-build memory_available=' + str(available) + ' disk_free=' + str(free), flush=True)
    if available < 8 * 1024**3 or free <= 15 * 1024**3:
        raise SystemExit(75)
