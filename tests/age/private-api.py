#!/usr/bin/env python3
"""Source/API regression: production callers cannot obtain reusable creation state."""
from pathlib import Path
import re

source = (Path(__file__).resolve().parents[2] / 'src/age/age.lu').read_text()
good = not re.search(r'pub\s+(?:fn\s+create_header|struct\s+Created)\b', source)
print(('PASS ' if good else 'FAIL ') + 'private-header-creation-state', flush=True)
raise SystemExit(0 if good else 1)
