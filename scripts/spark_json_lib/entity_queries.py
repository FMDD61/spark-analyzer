from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

from .normalize import ReportRecord


def entity_locate(records: Iterable[ReportRecord], entity_type: str) -> List[Dict]:
    out: List[Dict] = []
    for r in records:
        for ch in r.chunks:
            c = int(ch.entity_counts.get(entity_type, 0))
            if c <= 0:
                continue
            out.append(
                {
                    "report_id": r.report_id,
                    "timestamp": r.timestamp,
                    "dimension": ch.dimension,
                    "x": ch.x,
                    "z": ch.z,
                    "region_x": ch.region_x,
                    "region_z": ch.region_z,
                    "entity_type": entity_type,
                    "entity_count": c,
                    "chunk_total_entities": ch.total_entities,
                }
            )
    return sorted(out, key=lambda x: x["entity_count"], reverse=True)


def region_view(records: Iterable[ReportRecord], dimension: str, rx: int, rz: int) -> List[Dict]:
    out: List[Dict] = []
    for r in records:
        chunks = [c for c in r.chunks if c.dimension == dimension and c.region_x == rx and c.region_z == rz]
        if not chunks:
            continue
        total = sum(c.total_entities for c in chunks)
        by_chunk = sorted(chunks, key=lambda c: c.total_entities, reverse=True)
        out.append(
            {
                "report_id": r.report_id,
                "timestamp": r.timestamp,
                "dimension": dimension,
                "region_x": rx,
                "region_z": rz,
                "region_total_entities": total,
                "chunk_count": len(chunks),
                "chunks": [
                    {
                        "x": c.x,
                        "z": c.z,
                        "total_entities": c.total_entities,
                    }
                    for c in by_chunk
                ],
            }
        )
    return out


def chunk_view(records: Iterable[ReportRecord], dimension: str, x: int, z: int) -> List[Dict]:
    out: List[Dict] = []
    for r in records:
        target = next((c for c in r.chunks if c.dimension == dimension and c.x == x and c.z == z), None)
        if not target:
            continue
        entities = sorted(target.entity_counts.items(), key=lambda kv: kv[1], reverse=True)
        out.append(
            {
                "report_id": r.report_id,
                "timestamp": r.timestamp,
                "dimension": dimension,
                "x": x,
                "z": z,
                "total_entities": target.total_entities,
                "entities": [{"type": k, "count": int(v)} for k, v in entities],
            }
        )
    return out
