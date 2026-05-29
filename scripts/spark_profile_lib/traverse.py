from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple


def sum_times(values: Sequence[float]) -> float:
    return float(sum(values)) if values else 0.0


def safe_value(seq: Sequence[float], idx: int) -> float:
    return float(seq[idx]) if idx < len(seq) else 0.0


@dataclass
class NodeRow:
    node_id: int
    parent_id: Optional[int]
    depth: int
    thread: str
    kind: str
    class_name: str
    method_name: str
    method_desc: str
    line_number: int
    parent_line_number: int
    time_ms_total: float
    time_ms_self: float
    percent_of_thread: float
    child_count: int
    window_times_ms: List[float]


def traverse(thread_node, thread_id: int, start_id: int, time_window_index: Optional[int] = None) -> Tuple[List[NodeRow], int]:
    rows: List[NodeRow] = []
    next_id = start_id
    thread_label = thread_node.name
    thread_total = sum_times(thread_node.times)
    thread_win = safe_value(thread_node.times, time_window_index) if time_window_index is not None else 0.0
    flat = list(thread_node.children)
    root_refs = [r for r in list(thread_node.children_refs) if 0 <= r < len(flat)]

    child_sum = sum(sum_times(flat[r].times) for r in root_refs)
    rows.append(
        NodeRow(
            node_id=thread_id,
            parent_id=None,
            depth=0,
            thread=thread_label,
            kind="thread",
            class_name="",
            method_name=thread_label,
            method_desc="",
            line_number=-1,
            parent_line_number=-1,
            time_ms_total=thread_total,
            time_ms_self=max(thread_total - child_sum, 0.0),
            percent_of_thread=100.0,
            child_count=len(root_refs),
            window_times_ms=list(thread_node.times),
        )
    )

    def walk(node_ref: int, parent_id: int, depth: int) -> None:
        nonlocal next_id
        node = flat[node_ref]
        node_id = next_id
        next_id += 1

        total = sum_times(node.times)
        child_refs = [r for r in list(node.children_refs) if 0 <= r < len(flat)]
        child_total = sum(sum_times(flat[r].times) for r in child_refs)
        pct = (total / thread_total * 100.0) if thread_total > 0 else 0.0

        rows.append(
            NodeRow(
                node_id=node_id,
                parent_id=parent_id,
                depth=depth,
                thread=thread_label,
                kind="stack",
                class_name=node.class_name,
                method_name=node.method_name,
                method_desc=getattr(node, "method_desc", "") or "",
                line_number=getattr(node, "line_number", -1),
                parent_line_number=getattr(node, "parent_line_number", -1),
                time_ms_total=total,
                time_ms_self=max(total - child_total, 0.0),
                percent_of_thread=pct,
                child_count=len(child_refs),
                window_times_ms=list(node.times),
            )
        )

        for child_ref in child_refs:
            walk(child_ref, node_id, depth + 1)

    for child_ref in root_refs:
        walk(child_ref, thread_id, 1)

    if time_window_index is not None:
        print(
            f"[info] Thread '{thread_label}' window[{time_window_index}]={thread_win:.3f} ms, "
            f"total(sum of windows)={thread_total:.3f} ms"
        )

    return rows, next_id