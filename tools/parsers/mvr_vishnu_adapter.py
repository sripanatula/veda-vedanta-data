
#!/usr/bin/env python3
"""
Adapter for MVR Vishnu raw verse files -> normalized JSON.
Expected to be passed to update_from_raw.py via --parser path.
Replace the parse_file() body to call your real extract_data functions if you prefer.
"""
from pathlib import Path
from typing import Dict

def parse_file(path: Path) -> Dict:
    # Minimal example:
    # Heuristic: try to split by lines with markers 'sa:', 'te:', 'en:'.
    # If not present, put entire file under 'sa' and leave others empty.
    text = path.read_text(encoding='utf-8').strip()
    sa, te, en = "", "", ""
    # Try very simple parsing
    cur = None
    for line in text.splitlines():
        l = line.strip()
        low = l.lower()
        if low.startswith('sa:'):
            cur = 'sa'; sa += l[3:].strip() + '\n'
        elif low.startswith('te:'):
            cur = 'te'; te += l[3:].strip() + '\n'
        elif low.startswith('en:'):
            cur = 'en'; en += l[3:].strip() + '\n'
        else:
            if cur == 'sa':
                sa += l + '\n'
            elif cur == 'te':
                te += l + '\n'
            elif cur == 'en':
                en += l + '\n'
            else:
                sa += l + '\n'  # default bucket

    def clean(s: str) -> str:
        return s.strip()

    obj = {
        "sa": clean(sa),
        "te": clean(te),
        "en": clean(en),
    }
    return obj
