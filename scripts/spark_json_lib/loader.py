from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Tuple


def _load_json_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_from_ids(report_ids: Iterable[str]) -> List[Tuple[str, dict]]:
    try:
        import requests
    except Exception as e:  # pragma: no cover
        raise RuntimeError("requests is required: pip install requests") from e

    out: List[Tuple[str, dict]] = []
    for rid in report_ids:
        url = f"https://spark.lucko.me/{rid}?raw=1"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        out.append((rid, resp.json()))
    return out


def load_from_files(files: Iterable[Path]) -> List[Tuple[str, dict]]:
    out: List[Tuple[str, dict]] = []
    for f in files:
        data = _load_json_file(f)
        report_id = data.get("id") or f.stem
        out.append((str(report_id), data))
    return out


def load_from_dir(raw_dir: Path, pattern: str) -> List[Tuple[str, dict]]:
    files = sorted(raw_dir.glob(pattern))
    return load_from_files(files)
