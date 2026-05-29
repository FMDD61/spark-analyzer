from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROFILE_EXTENSIONS = {".sparkprofile", ".bin", ".proto", ".pb"}
RAW_EXTENSIONS = {".json", ".rawjson", ".raw"}
RESOLVED_KEY = "resolved_type"


def _guess_by_ext(path: Path) -> Optional[str]:
    ext = path.suffix.lower()
    if ext in RAW_EXTENSIONS:
        return "raw"
    if ext in PROFILE_EXTENSIONS:
        return "profile"
    return None


def _probe_content(path: Path) -> Optional[str]:
    raw = path.read_bytes()[:8192]
    try:
        json.loads(raw.decode("utf-8-sig"))
        return "raw"
    except Exception:
        pass
    if raw and b"\x00" in raw:
        return "profile"
    return None


def resolve_file(path: Path) -> Dict:
    guessed = _guess_by_ext(path)
    if guessed:
        return {"path": path, RESOLVED_KEY: guessed}
    probed = _probe_content(path)
    if probed:
        return {"path": path, RESOLVED_KEY: probed}
    return {"path": path, RESOLVED_KEY: "unknown"}


def resolve_dir(directory: Path, pattern: str = "*") -> List[Dict]:
    out: List[Dict] = []
    for f in sorted(directory.glob(pattern)):
        if f.is_file():
            out.append(resolve_file(f))
    return out


def resolve_report_ids(report_ids: List[str]) -> List[Dict]:
    out: List[Dict] = []
    for rid in report_ids:
        out.append({"report_id": rid, RESOLVED_KEY: "report_id"})
    return out


def classify(entries: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    raw_entries: List[Dict] = []
    profile_entries: List[Dict] = []
    for e in entries:
        t = e.get(RESOLVED_KEY, "unknown")
        if t == "raw":
            raw_entries.append(e)
        elif t == "profile":
            profile_entries.append(e)
        elif t == "report_id":
            raw_entries.append(e)
            profile_entries.append(dict(e))
        elif t == "unknown":
            pass
    return raw_entries, profile_entries


def collect(
    report_ids: Optional[List[str]] = None,
    files: Optional[List[Path]] = None,
    directory: Optional[Path] = None,
    glob_pattern: str = "*",
) -> Tuple[List[Dict], List[Dict]]:
    entries: List[Dict] = []
    if report_ids:
        entries.extend(resolve_report_ids(report_ids))
    if files:
        for f in files:
            entries.append(resolve_file(f))
    if directory:
        entries.extend(resolve_dir(directory, glob_pattern))
    return classify(entries)