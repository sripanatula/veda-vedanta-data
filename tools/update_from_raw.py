#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_from_raw.py — Build/refresh the vv-data "DB" from raw_data.

What this does
--------------
- Reads settings from tools/config.env (no hardcoded paths).
- Detects changed raw files (by SHA256) and parses only those.
- Optional: reprocess ALL files with --force-all (useful after parser changes).
- Writes verse JSON to vv/data/<source>/<collection>/verse-XXX.json.
- Rebuilds vv/data/.../index.json (count + file list).
- Updates vv/manifests/<MANIFEST_NAME> with { base, total, last_updated }.
- Tracks processed raw files in vv/state/raw_index.json.
- Optional: writes Cloudflare Pages _headers (CORS + no-store).
- Optional: git add/commit (and push) in the vv-data repo.

Run (from repo root: veda-vedanta-data)
---------------------------------------
    python3 tools/update_from_raw.py --dry-run
    python3 tools/update_from_raw.py
    python3 tools/update_from_raw.py --force-all
    python3 tools/update_from_raw.py --config tools/alt.env --push

Config precedence (highest -> lowest)
-------------------------------------
    1) --config path
    2) env var VVEDATA_CONFIG
    3) tools/config.env (default)
"""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

# ---------------------------- Config helpers ----------------------------

def _parse_bool(s: Optional[str], default: bool = False) -> bool:
    if s is None:
        return default
    return s.strip().lower() in {"1", "true", "yes", "y", "on"}

def _load_env_file(path: Path) -> Dict[str, str]:
    """Parse a simple KEY=VALUE file (no export, quotes optional)."""
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out

def load_config(repo_root: Path, explicit: Optional[Path]) -> Dict[str, Any]:
    """
    Load config from:
      1) explicit path (if provided),
      2) VVEDATA_CONFIG env,
      3) repo_root/tools/config.env (default).
    Resolve relative paths against repo_root.
    """
    if explicit and explicit.exists():
        cfg_path = explicit
    else:
        envp = os.getenv("VVEDATA_CONFIG")
        cfg_path = Path(envp) if envp else (repo_root / "tools" / "config.env")

    raw = _load_env_file(cfg_path)

    def resolve_path(val: Optional[str], default_rel: str) -> Path:
        p = Path((val or default_rel))
        return (repo_root / p).resolve() if not p.is_absolute() else p

    cfg: Dict[str, Any] = {
        "RAW_DIR":       resolve_path(raw.get("RAW_DIR"), "../veda-vedanta-raw/raw_data/mvr/vishnu"),
        "DATA_DIR":      resolve_path(raw.get("DATA_DIR"), "."),
        "BASE":          (raw.get("BASE") or "/vv/data/mvr/vishnu").strip("/"),
        "COLLECTION":    raw.get("COLLECTION") or "mvr/vishnu",
        "PARSER":        resolve_path(raw.get("PARSER"), "./tools/parsers/mvr_vishnu_adapter.py"),
        "MANIFEST_NAME": raw.get("MANIFEST_NAME") or "vishnu.json",
        "INDEX_NAME":    raw.get("INDEX_NAME") or "index.json",
        "WRITE_HEADERS": _parse_bool(raw.get("WRITE_HEADERS"), True),
        "GIT_AUTOCOMMIT":_parse_bool(raw.get("GIT_AUTOCOMMIT"), True),
        "GIT_AUTOPUSH":  _parse_bool(raw.get("GIT_AUTOPUSH"), False),
        "STATE_PATH":    resolve_path(raw.get("STATE_PATH"), "vv/state/raw_index.json"),
        "HEADERS_PATH":  resolve_path(raw.get("HEADERS_PATH"), "_headers"),
    }
    return cfg

# ---------------------------- Utilities ----------------------------

VERSE_RE = re.compile(r"verse[-_]?(\d+)\.(txt|md|json)$", re.IGNORECASE)

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def load_state(state_path: Path) -> Dict[str, Any]:
    if state_path.exists():
        return json.loads(state_path.read_text(encoding="utf-8"))
    return {"last_parsed_commit": "", "files": {}}

def save_state(state_path: Path, state: Dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def load_parser(parser_path: Path):
    """Dynamically load the adapter module which must expose parse_file(Path)->dict."""
    spec = importlib.util.spec_from_file_location("vv_parser", str(parser_path))
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot import parser from: {parser_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    if not hasattr(mod, "parse_file") or not callable(mod.parse_file):
        raise SystemExit("Parser module must expose parse_file(Path)->dict")
    return mod

def validate_minimal(obj: Dict[str, Any], verse_id: str) -> None:
    missing = [k for k in ("sa", "te", "en") if k not in obj]
    if missing:
        raise ValueError(f"{verse_id}: missing keys {missing}")

def ensure_headers(path: Path, write: bool) -> None:
    """Write Cloudflare Pages headers to allow CORS and disable caching (if enabled)."""
    if not write:
        return
    content = (
        "/vv/data/*\n"
        "  Access-Control-Allow-Origin: *\n"
        "  Cache-Control: no-store\n\n"
        "/vv/manifests/*\n"
        "  Access-Control-Allow-Origin: *\n"
        "  Cache-Control: no-store\n\n"
    )
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current != content:
        path.write_text(content, encoding="utf-8")

def git_commit_push(repo_root: Path, do_commit: bool, do_push: bool) -> Tuple[bool, bool]:
    """Stage vv/data + vv/manifests + vv/state/raw_index.json, commit, optionally push."""
    committed = False
    pushed = False
    if not do_commit and not do_push:
        return (False, False)

    # git add (best-effort)
    try:
        subprocess.run(
            ["git", "-C", str(repo_root), "add", "vv/data", "vv/manifests", "vv/state/raw_index.json"],
            check=True, capture_output=True
        )
    except subprocess.CalledProcessError:
        pass

    if do_commit:
        res = subprocess.run(
            ["git", "-C", str(repo_root), "commit", "-m", "Parsed updates from raw"],
            capture_output=True, text=True
        )
        if res.returncode == 0:
            committed = True

    if do_push:
        res = subprocess.run(["git", "-C", str(repo_root), "push"], capture_output=True, text=True)
        pushed = (res.returncode == 0)

    return (committed, pushed)

# ---------------------------- Main ----------------------------

def main():
    ap = argparse.ArgumentParser(description="Delta-update vv-data from raw_data")
    ap.add_argument("--config", help="Path to config.env (defaults to tools/config.env)")
    ap.add_argument("--dry-run", action="store_true", help="Parse & report; do not write files")
    ap.add_argument("--push", action="store_true", help="Force git push after commit (overrides config)")
    ap.add_argument("--force-all", action="store_true", help="Reprocess ALL raw files (ignore state)")
    args = ap.parse_args()

    # Determine repo root from this script location (robust if run from anywhere)
    script_path = Path(__file__).resolve()
    repo_root = script_path.parent.parent  # tools/ -> repo root

    cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)

    RAW_DIR: Path = cfg["RAW_DIR"]
    DATA_DIR: Path = cfg["DATA_DIR"]
    BASE: str = cfg["BASE"].strip("/")              # e.g., "vv/data/mvr/vishnu"
    COLLECTION: str = cfg["COLLECTION"]             # e.g., "mvr/vishnu"
    PARSER: Path = cfg["PARSER"]
    MANIFEST_NAME: str = cfg["MANIFEST_NAME"]       # e.g., "vishnu.json"
    INDEX_NAME: str = cfg["INDEX_NAME"]             # e.g., "index.json"
    STATE_PATH: Path = cfg["STATE_PATH"]            # vv/state/raw_index.json
    HEADERS_PATH: Path = cfg["HEADERS_PATH"]        # _headers
    WRITE_HEADERS: bool = cfg["WRITE_HEADERS"]
    GIT_AUTOCOMMIT: bool = cfg["GIT_AUTOCOMMIT"]
    GIT_AUTOPUSH: bool = cfg["GIT_AUTOPUSH"] or args.push

    data_dir = DATA_DIR / BASE                       # vv/data/mvr/vishnu
    manifests_dir = DATA_DIR / "vv" / "manifests"
    state_path = STATE_PATH

    # Prep
    if not RAW_DIR.exists():
        raise SystemExit(f"RAW_DIR not found: {RAW_DIR}")
    data_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    ensure_headers(HEADERS_PATH, WRITE_HEADERS)
    parser_mod = load_parser(PARSER)

    # Discover candidate raw files
    candidates: List[Tuple[Optional[int], Path]] = []
    for p in sorted(RAW_DIR.glob("*")):
        if p.is_file() and VERSE_RE.search(p.name):
            m = VERSE_RE.search(p.name)
            n = int(m.group(1)) if m else None
            candidates.append((n, p))
    if not candidates:
        print(f"No verse files found in {RAW_DIR}")
        return

    state = load_state(state_path)

    # Delta detection by SHA256 (or force-all)
    changed: List[Tuple[Optional[int], Path, str, str]] = []
    for n, src in candidates:
        rel = str(src.relative_to(RAW_DIR))
        if args.force_all:
            changed.append((n, src, rel, "FORCED"))
            continue
        digest = sha256_file(src)
        prev = state["files"].get(rel, {}).get("sha256")
        if prev != digest:
            changed.append((n, src, rel, digest))

    if not changed:
        print("No changes detected. Nothing to do.")
        return
    else:
        print(f"{len(changed)} file(s) to process: {[rel for _,_,rel,_ in changed]}")

    # Process changed items
    total_written = 0
    for n, src, rel, digest in changed:
        verse_num = n if n is not None else None
        if verse_num is None:
            print(f"Skip unnumbered file: {rel}")
            continue

        out_name = f"verse-{verse_num:03d}.json"
        out_file = data_dir / out_name

        # Parse one raw file -> JSON
        verse_obj = parser_mod.parse_file(src)
        validate_minimal(verse_obj, out_name)

        # Normalize metadata
        verse_obj.setdefault("id", f"{COLLECTION}/{verse_num:03d}")
        meta = verse_obj.setdefault("metadata", {})
        meta.setdefault("source", COLLECTION.split("/")[0])  # e.g., "mvr"
        meta["last_modified"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

        if not args.dry_run:
            out_file.write_text(json.dumps(verse_obj, ensure_ascii=False, indent=2), encoding="utf-8")

        total_written += 1
        state["files"][rel] = {"sha256": digest, "verse": verse_num, "target": out_name}

    # Rebuild index & manifest from actual data_dir (only if we wrote changes)
    if not args.dry_run:
        items = []
        for jp in sorted(data_dir.glob("verse-*.json")):
            m = re.search(r"verse-(\d{3})\.json$", jp.name)
            if m:
                items.append({"file": jp.name, "verse": int(m.group(1))})

        index_obj = {"collection": COLLECTION, "count": len(items), "items": items}
        manifest_obj = {
            "base": f"/{BASE}",
            "total": len(items),
            "schema_version": "1.0",
            "last_updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

        # Write index, manifest, state
        (data_dir / INDEX_NAME).write_text(json.dumps(index_obj, ensure_ascii=False, indent=2), encoding="utf-8")
        (manifests_dir / MANIFEST_NAME).write_text(json.dumps(manifest_obj, ensure_ascii=False, indent=2), encoding="utf-8")
        save_state(state_path, state)

        committed, pushed = git_commit_push(repo_root, GIT_AUTOCOMMIT, GIT_AUTOPUSH)
        if committed:
            print("Committed changes to git.")
        if GIT_AUTOPUSH:
            print("Pushed changes." if pushed else "Push failed or nothing to push.")

    print(f"Wrote {total_written} updated verse(s).")
    print(f"Data dir: {data_dir}")
    print(f"Manifest: {manifests_dir / MANIFEST_NAME}")
    print(f"State:    {state_path}")

if __name__ == "__main__":
    main()
