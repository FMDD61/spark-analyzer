from __future__ import annotations

from typing import Dict, List

from .normalize import ReportRecord


def _safe_delta(a, b):
    if a is None or b is None:
        return None
    return a - b


def build_compare(records: List[ReportRecord]) -> List[Dict]:
    items = sorted(records, key=lambda r: (r.timestamp, r.report_id))
    out: List[Dict] = []

    prev = None
    prev_ec: Dict[str, int] = {}
    for r in items:
        row = {
            "report_id": r.report_id,
            "timestamp": r.timestamp,
            "players_online": r.players_online,
            "tps_1m": r.tps_1m,
            "mspt_1m_mean": r.mspt_1m_mean,
            "mspt_1m_max": r.mspt_1m_max,
            "entities_total": r.entities_total,
            "chunks_total": r.chunks_total,
            "delta_tps_1m": _safe_delta(r.tps_1m, prev.tps_1m) if prev else None,
            "delta_mspt_1m_mean": _safe_delta(r.mspt_1m_mean, prev.mspt_1m_mean) if prev else None,
            "delta_players": r.players_online - prev.players_online if prev else None,
            "delta_entities": r.entities_total - prev.entities_total if prev else None,
            "delta_chunks": r.chunks_total - prev.chunks_total if prev else None,
            "top_entity_delta": None,
            "top_entity_delta_value": None,
        }
        if prev:
            keys = set(prev_ec) | set(r.entity_counts)
            best_name = None
            best_val = None
            for k in keys:
                dv = int(r.entity_counts.get(k, 0)) - int(prev_ec.get(k, 0))
                if best_val is None or abs(dv) > abs(best_val):
                    best_name = k
                    best_val = dv
            row["top_entity_delta"] = best_name
            row["top_entity_delta_value"] = best_val
        out.append(row)
        prev = r
        prev_ec = dict(r.entity_counts)
    return out
