from __future__ import annotations

from dataclasses import dataclass, asdict
from math import floor
from typing import Dict, List, Optional, Tuple


def _get(d: dict, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _first(d: dict, paths: List[Tuple[str, ...]], default=None):
    for p in paths:
        v = _get(d, *p, default=None)
        if v is not None:
            return v
    return default


@dataclass
class ChunkRecord:
    report_id: str
    timestamp: int
    dimension: str
    x: int
    z: int
    region_x: int
    region_z: int
    total_entities: int
    entity_counts: Dict[str, int]


@dataclass
class ReportRecord:
    report_id: str
    timestamp: int
    uptime_ms: int
    players_online: int
    tps_1m: Optional[float]
    tps_5m: Optional[float]
    tps_15m: Optional[float]
    mspt_1m_mean: Optional[float]
    mspt_1m_max: Optional[float]
    mspt_1m_median: Optional[float]
    mspt_1m_p95: Optional[float]
    mspt_5m_mean: Optional[float]
    mspt_5m_max: Optional[float]
    entities_total: int
    chunks_total: int
    old_gen_post_gc_gb: Optional[float]
    swap_used_gb: Optional[float]
    dimensions: Dict[str, Dict[str, int]]
    entity_counts: Dict[str, int]
    chunks: List[ChunkRecord]

    def to_dict(self):
        d = asdict(self)
        d["chunks"] = [asdict(c) for c in self.chunks]
        return d


def _to_gb(v: Optional[int]) -> Optional[float]:
    if v is None:
        return None
    return float(v) / 1073741824.0


def normalize(report_id: str, data: dict) -> ReportRecord:
    meta = _first(data, [("metadata",), ("healthMetadata",)], default={}) or {}
    ps = _first(data, [("platformStatistics",), ("metadata", "platformStatistics")], default={}) or {}
    if ps == {}:
        ps = _get(meta, "platformStatistics", default={}) or {}
    ss = _first(data, [("systemStatistics",), ("metadata", "systemStatistics")], default={}) or {}
    if ss == {}:
        ss = _get(meta, "systemStatistics", default={}) or {}

    timestamp = int(
        _first(
            meta,
            [("generatedTime",), ("startTime",), ("endTime",)],
            default=0,
        )
        or 0
    )
    uptime_ms = int(_first(ps, [("uptime",)], default=0) or _first(ss, [("uptime",)], default=0) or 0)

    tps = _get(ps, "tps", default={}) or {}
    mspt = _get(ps, "mspt", default={}) or {}
    mspt1 = _get(mspt, "last1m", default={}) or {}
    mspt5 = _get(mspt, "last5m", default={}) or {}

    mem = _get(ps, "memory", default={}) or {}
    pools = _get(mem, "pools", default=[]) or []
    old_pool = next((p for p in pools if p.get("name") == "G1 Old Gen"), None)
    old_post = None
    if old_pool:
        old_post = _to_gb(_get(old_pool, "collectionUsage", "used", default=None))

    swap_used = _to_gb(_get(ss, "memory", "swap", "used", default=None))

    world = _get(ps, "world", default={}) or {}
    dims = _get(world, "worlds", default=[]) or []
    entity_counts = _get(world, "entityCounts", default={}) or {}

    dim_summary: Dict[str, Dict[str, int]] = {}
    chunks: List[ChunkRecord] = []
    chunks_total = 0
    for w in dims:
        dname = w.get("name", "unknown")
        total_entities = int(w.get("totalEntities", 0) or 0)
        reg_list = w.get("regions", []) or []
        d_chunks = 0
        for r in reg_list:
            for ch in (r.get("chunks", []) or []):
                x = int(ch.get("x", 0) or 0)
                z = int(ch.get("z", 0) or 0)
                te = int(ch.get("totalEntities", 0) or 0)
                ec = ch.get("entityCounts", {}) or {}
                chunks.append(
                    ChunkRecord(
                        report_id=report_id,
                        timestamp=timestamp,
                        dimension=dname,
                        x=x,
                        z=z,
                        region_x=floor(x / 32),
                        region_z=floor(z / 32),
                        total_entities=te,
                        entity_counts={k: int(v) for k, v in ec.items()},
                    )
                )
                d_chunks += 1
        dim_summary[dname] = {"entities": total_entities, "chunks": d_chunks}
        chunks_total += d_chunks

    return ReportRecord(
        report_id=report_id,
        timestamp=timestamp,
        uptime_ms=uptime_ms,
        players_online=int(ps.get("playerCount", 0) or 0),
        tps_1m=tps.get("last1m"),
        tps_5m=tps.get("last5m"),
        tps_15m=tps.get("last15m"),
        mspt_1m_mean=mspt1.get("mean"),
        mspt_1m_max=mspt1.get("max"),
        mspt_1m_median=mspt1.get("median"),
        mspt_1m_p95=mspt1.get("percentile95"),
        mspt_5m_mean=mspt5.get("mean"),
        mspt_5m_max=mspt5.get("max"),
        entities_total=int(world.get("totalEntities", 0) or 0),
        chunks_total=chunks_total,
        old_gen_post_gc_gb=old_post,
        swap_used_gb=swap_used,
        dimensions=dim_summary,
        entity_counts={k: int(v) for k, v in entity_counts.items()},
        chunks=chunks,
    )
