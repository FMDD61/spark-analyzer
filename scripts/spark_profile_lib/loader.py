from __future__ import annotations

from pathlib import Path
from typing import Optional


def load_binary(report_id: Optional[str], file_path: Optional[Path]) -> bytes:
    if bool(report_id) == bool(file_path):
        raise ValueError("Use exactly one of report_id or file_path")

    if report_id:
        import requests

        url = f"https://spark-usercontent.lucko.me/{report_id}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content

    assert file_path is not None
    return file_path.read_bytes()