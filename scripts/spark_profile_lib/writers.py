from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List

from .traverse import NodeRow


def write_jsonl(path: Path, rows: List[NodeRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        for r in rows:
            f.write(json.dumps(r.__dict__, ensure_ascii=False) + "\n")
    print(f"[ok] Full tree JSONL written: {path}")


def write_csv(path: Path, rows: List[NodeRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "node_id", "parent_id", "depth", "thread", "kind",
        "class_name", "method_name", "method_desc",
        "line_number", "parent_line_number",
        "time_ms_total", "time_ms_self", "percent_of_thread", "child_count",
        "window_times_ms",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            d = r.__dict__.copy()
            d["window_times_ms"] = json.dumps(d["window_times_ms"], ensure_ascii=False)
            writer.writerow(d)
    print(f"[ok] CSV written: {path}")