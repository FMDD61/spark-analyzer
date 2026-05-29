from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .normalize import ReportRecord


EXPR_RE = re.compile(r"^\s*([A-Za-z0-9_.:-]+)\s*(<=|>=|==|!=|<|>)\s*(.+?)\s*$")

BASE_RULE_KEYS = [
    "report_id",
    "timestamp",
    "uptime.ms",
    "players.online",
    "tps.last1m",
    "tps.last5m",
    "tps.last15m",
    "mspt.last1m.mean",
    "mspt.last1m.max",
    "mspt.last1m.median",
    "mspt.last1m.p95",
    "mspt.last5m.mean",
    "mspt.last5m.max",
    "entities.total",
    "chunks.total",
    "memory.old_gen.post_gc_gb",
    "system.swap.used_gb",
    "dimension.<name>.entities",
    "dimension.<name>.chunks",
    "dimension.<name>.entities_per_chunk",
    "entity.<namespace:id>.count",
]


def load_rule_file(path: Path) -> List[Dict]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        obj = json.loads(text)
    else:
        try:
            import yaml
        except Exception as e:  # pragma: no cover
            raise RuntimeError("PyYAML required for YAML rule file: pip install pyyaml") from e
        obj = yaml.safe_load(text)

    if isinstance(obj, dict) and isinstance(obj.get("rules"), list):
        rules = obj["rules"]
    elif isinstance(obj, list):
        rules = obj
    else:
        raise ValueError("Rule file must be {'rules': [...]} or [...]")

    normalized = []
    for i, r in enumerate(rules):
        if isinstance(r, str):
            normalized.append({"id": f"file_rule_{i+1}", "expr": r, "severity": "info"})
        elif isinstance(r, dict):
            normalized.append(
                {
                    "id": r.get("id", f"file_rule_{i+1}"),
                    "expr": r.get("expr"),
                    "severity": r.get("severity", "info"),
                }
            )
    return normalized


def _to_num(v):
    try:
        return float(v)
    except Exception:
        return None


def _flatten(record: ReportRecord) -> Dict[str, object]:
    m: Dict[str, object] = {
        "report_id": record.report_id,
        "timestamp": record.timestamp,
        "uptime.ms": record.uptime_ms,
        "players.online": record.players_online,
        "tps.last1m": record.tps_1m,
        "tps.last5m": record.tps_5m,
        "tps.last15m": record.tps_15m,
        "mspt.last1m.mean": record.mspt_1m_mean,
        "mspt.last1m.max": record.mspt_1m_max,
        "mspt.last1m.median": record.mspt_1m_median,
        "mspt.last1m.p95": record.mspt_1m_p95,
        "mspt.last5m.mean": record.mspt_5m_mean,
        "mspt.last5m.max": record.mspt_5m_max,
        "entities.total": record.entities_total,
        "chunks.total": record.chunks_total,
        "memory.old_gen.post_gc_gb": record.old_gen_post_gc_gb,
        "system.swap.used_gb": record.swap_used_gb,
    }
    for d, vals in record.dimensions.items():
        entities = vals.get("entities")
        chunks = vals.get("chunks")
        m[f"dimension.{d}.entities"] = entities
        m[f"dimension.{d}.chunks"] = chunks
        m[f"dimension.{d}.entities_per_chunk"] = (entities / chunks) if chunks else 0.0
    for et, cnt in record.entity_counts.items():
        m[f"entity.{et}.count"] = int(cnt)
    return m


def available_rule_keys(records: Optional[Iterable[ReportRecord]] = None) -> List[str]:
    keys = set(BASE_RULE_KEYS)
    if records:
        for r in records:
            flat = _flatten(r)
            keys.update(flat.keys())
    return sorted(keys)


def init_rule_template(keys: List[str]) -> Dict:
    return {
        "rules": [
            {
                "id": "example_low_tps",
                "severity": "high",
                "expr": "tps.last1m < 18",
            },
            {
                "id": "example_high_mspt_spike",
                "severity": "high",
                "expr": "mspt.last1m.max > 500",
            },
            {
                "id": "example_server_specific",
                "severity": "medium",
                "expr": "memory.old_gen.post_gc_gb > 18",
            },
        ],
        "notes": [
            "Rules are evaluated per report independently.",
            "You can combine --rule and --rule-file; they will be merged.",
            "Use --print-keys to list all available expression keys.",
        ],
        "available_keys": keys,
    }


def _eval_expr(flat: Dict[str, object], expr: str) -> Optional[Dict]:
    m = EXPR_RE.match(expr)
    if not m:
        return None
    key, op, rhs_raw = m.group(1), m.group(2), m.group(3)
    if key not in flat:
        return {"valid": False, "reason": f"Unknown key: {key}", "key": key}

    left = flat.get(key)
    right = rhs_raw.strip().strip('"').strip("'")

    ln = _to_num(left)
    rn = _to_num(right)

    if ln is not None and rn is not None:
        lval, rval = ln, rn
    else:
        lval, rval = str(left), str(right)

    ok = False
    if op == "<":
        ok = lval < rval
    elif op == "<=":
        ok = lval <= rval
    elif op == ">":
        ok = lval > rval
    elif op == ">=":
        ok = lval >= rval
    elif op == "==":
        ok = lval == rval
    elif op == "!=":
        ok = lval != rval

    return {
        "valid": True,
        "key": key,
        "op": op,
        "rhs": rval,
        "actual": lval,
        "triggered": bool(ok),
    }


def evaluate_alerts(records: Iterable[ReportRecord], inline_rules: List[str], file_rules: List[Dict]) -> List[Dict]:
    rules: List[Dict] = []
    for i, expr in enumerate(inline_rules):
        rules.append({"id": f"inline_rule_{i+1}", "expr": expr, "severity": "info"})
    rules.extend(file_rules)

    out: List[Dict] = []
    for r in records:
        flat = _flatten(r)
        for rule in rules:
            expr = rule.get("expr")
            if not expr:
                continue
            result = _eval_expr(flat, str(expr))
            if result is None:
                out.append(
                    {
                        "report_id": r.report_id,
                        "timestamp": r.timestamp,
                        "rule_id": rule.get("id"),
                        "severity": rule.get("severity", "info"),
                        "expr": expr,
                        "valid": False,
                        "message": "Invalid expression",
                    }
                )
                continue
            if not result["valid"]:
                out.append(
                    {
                        "report_id": r.report_id,
                        "timestamp": r.timestamp,
                        "rule_id": rule.get("id"),
                        "severity": rule.get("severity", "info"),
                        "expr": expr,
                        "valid": False,
                        "message": result["reason"],
                    }
                )
                continue
            if result["triggered"]:
                out.append(
                    {
                        "report_id": r.report_id,
                        "timestamp": r.timestamp,
                        "rule_id": rule.get("id"),
                        "severity": rule.get("severity", "info"),
                        "expr": expr,
                        "valid": True,
                        "actual": result["actual"],
                        "key": result["key"],
                    }
                )
    return out
