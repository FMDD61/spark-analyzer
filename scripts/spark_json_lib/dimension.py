from __future__ import annotations

from typing import Dict, Iterable, List

from .normalize import ReportRecord


def dimension_focus(records: Iterable[ReportRecord], dimensions: List[str]) -> List[Dict]:
    out: List[Dict] = []
    for r in sorted(records, key=lambda x: (x.timestamp, x.report_id)):
        for d in dimensions:
            vals = r.dimensions.get(d, {"entities": 0, "chunks": 0})
            entities = int(vals.get("entities", 0))
            chunks = int(vals.get("chunks", 0))
            ratio = (entities / chunks) if chunks else 0.0
            out.append(
                {
                    "report_id": r.report_id,
                    "timestamp": r.timestamp,
                    "dimension": d,
                    "entities": entities,
                    "chunks": chunks,
                    "entities_per_chunk": ratio,
                }
            )
    return out
