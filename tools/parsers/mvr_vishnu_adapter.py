#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mvr_vishnu_adapter.py — Raw -> JSON adapter for MVR Vishnu verses.

Consistent with your original splitter rules:
- Telugu wins if present on a line  -> "te"
- Else English wins over Sanskrit   -> "en"
- Else Sanskrit if Devanagari found -> "sa"
- If none detected, stick with current bucket; default to Sanskrit ("sa").
- Lines of only dashes (-----) create paragraph breaks in the current bucket.
"""

from pathlib import Path
from typing import Dict, List, Optional
import re

RE_TEL = re.compile(r"[\u0C00-\u0C7F]")   # Telugu
RE_DEV = re.compile(r"[\u0900-\u097F]")   # Devanagari (Sanskrit/Hindi)
RE_LAT = re.compile(r"[A-Za-z]")          # English (ASCII letters)
SEP_LINE = re.compile(r"^\s*-{3,}\s*$")   # lines of only dashes
BLANK = re.compile(r"^\s*$")

def detect_language(line: str) -> Optional[str]:
    if RE_TEL.search(line):
        return "te"
    if RE_LAT.search(line):               # English takes precedence over Sanskrit
        return "en"
    if RE_DEV.search(line):
        return "sa"
    return None

def parse_file(path: Path) -> Dict:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    sa: List[str] = []
    te: List[str] = []
    en: List[str] = []
    current: Optional[str] = None  # last chosen bucket

    def put(bucket: str, line: str):
        if bucket == "sa": sa.append(line)
        elif bucket == "te": te.append(line)
        else: en.append(line)

    for raw in text.split("\n"):
        line = raw.rstrip()

        if SEP_LINE.match(line):
            if current:
                put(current, "")          # paragraph break in the active bucket
            continue

        if BLANK.match(line):
            if current:
                put(current, "")
            continue

        bucket = detect_language(line) or current or "sa"
        put(bucket, line)
        current = bucket

    def join_clean(parts: List[str]) -> str:
        s = "\n".join(parts).strip()
        # collapse 3+ blank lines to 2 to avoid excessive spacing
        return re.sub(r"\n{3,}", "\n\n", s)

    return {
        "sa": join_clean(sa),
        "te": join_clean(te),
        "en": join_clean(en),
    }
