from __future__ import annotations

from typing import List

from .traverse import NodeRow


def print_hotspots(rows: List[NodeRow], top_n: int) -> None:
    stack_rows = [r for r in rows if r.kind == "stack"]

    by_self = sorted(stack_rows, key=lambda r: r.time_ms_self, reverse=True)[:top_n]
    by_total = sorted(stack_rows, key=lambda r: r.time_ms_total, reverse=True)[:top_n]

    print("\n=== Top Hotspots By SELF Time ===")
    print("rank\tself(ms)\ttotal(ms)\tthread%\tmethod")
    for i, r in enumerate(by_self, 1):
        method = f"{r.class_name}.{r.method_name}"
        print(f"{i}\t{r.time_ms_self:.3f}\t{r.time_ms_total:.3f}\t{r.percent_of_thread:.3f}%\t{method}")

    print("\n=== Top Hotspots By TOTAL Time ===")
    print("rank\tself(ms)\ttotal(ms)\tthread%\tmethod")
    for i, r in enumerate(by_total, 1):
        method = f"{r.class_name}.{r.method_name}"
        print(f"{i}\t{r.time_ms_self:.3f}\t{r.time_ms_total:.3f}\t{r.percent_of_thread:.3f}%\t{method}")