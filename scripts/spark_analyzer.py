#!/usr/bin/env python3
"""Unified Spark report analyzer — raw JSON batch + protobuf flame graph.

Subcommands:
  raw      Batch analyze raw JSON reports (summary, compare, alerts, dimensions, entities)
  profile  Decode spark sampler protobuf and analyze method hotspots
  all      Run both analyses on the same inputs (auto-skip unavailable)

Usage examples:
  python spark_analyzer.py raw --report-id lcwqNWJps6 --report-id SfcG9mKOie --compare --alerts
  python spark_analyzer.py profile --report-id lcwqNWJps6 --thread "Server thread" --top 30
  python spark_analyzer.py all --report-id lcwqNWJps6 --report-id SfcG9mKOie --compare --alerts --thread "Server thread"
  python spark_analyzer.py raw --print-keys
  python spark_analyzer.py raw --init-rule-file alerts_template.yaml
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from input_resolver import collect
from spark_json_lib.alerts import available_rule_keys, evaluate_alerts, init_rule_template, load_rule_file
from spark_json_lib.compare import build_compare
from spark_json_lib.dimension import dimension_focus
from spark_json_lib.entity_queries import chunk_view, entity_locate, region_view
from spark_json_lib.loader import load_from_dir, load_from_files, load_from_ids
from spark_json_lib.normalize import normalize
from spark_json_lib.output import write_csv, write_json, write_jsonl
from spark_profile_lib.hotspots import print_hotspots
from spark_profile_lib.loader import load_binary
from spark_profile_lib.proto_compile import ensure_generated_proto
from spark_profile_lib.traverse import NodeRow, traverse
from spark_profile_lib.writers import write_csv as profile_write_csv, write_jsonl as profile_write_jsonl


def _parse_region(s: str):
    d, coord = s.split(":", 1)
    rx, rz = coord.split(",", 1)
    return d, int(rx), int(rz)


def _parse_chunk(s: str):
    d, coord = s.split(":", 1)
    x, z = coord.split(",", 1)
    return d, int(x), int(z)


def _write_rule_template(path: Path, template: dict) -> None:
    suffix = path.suffix.lower()
    if suffix == ".json":
        write_json(path, template)
        return
    try:
        import yaml
    except Exception as e:
        raise RuntimeError("PyYAML required to write YAML template. Use .json or install pyyaml.") from e
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(template, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _add_common_input_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--report-id", action="append", default=[], help="spark report id, can repeat")
    p.add_argument("--file", action="append", default=[], help="local file (auto-detect json/protobuf), can repeat")
    p.add_argument("--dir", type=Path, default=None, help="directory for batch local files")
    p.add_argument("--glob", default="*", help="glob pattern for --dir (default: *)")


def _add_raw_analysis_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--compare", action="store_true")
    p.add_argument("--alerts", action="store_true")
    p.add_argument("--rule", action="append", default=[], help="alert expression, can repeat")
    p.add_argument("--rule-file", action="append", default=[], help="YAML/JSON alert rule file, can repeat")
    p.add_argument("--print-keys", action="store_true", help="print available keys for rule expressions")
    p.add_argument("--init-rule-file", type=Path, default=None, help="write starter rule file (.yaml/.json)")
    p.add_argument("--dimension-focus", action="append", default=[], help="dimension name, can repeat")
    p.add_argument("--entity-locate", default=None, help="entity type to locate across chunks")
    p.add_argument("--region-view", default=None, help="dimension:rx,rz")
    p.add_argument("--chunk-view", default=None, help="dimension:x,z")
    p.add_argument("--out-summary", type=Path, default=None)
    p.add_argument("--out-details", type=Path, default=None)
    p.add_argument("--out-alerts", type=Path, default=None)
    p.add_argument("--out-compare", type=Path, default=None)


def _add_profile_analysis_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--thread", default="Server thread", help="Thread name filter (case-insensitive contains)")
    p.add_argument("--top", type=int, default=50, help="Top N hotspots to print (default: 50)")
    p.add_argument("--time-window-index", type=int, default=None, help="Optional time window index for debug")
    p.add_argument("--protoc", default=None, help="Path to protoc executable")
    p.add_argument("--full-tree-out", type=Path, default=None, help="Write complete tree rows to JSONL")
    p.add_argument("--hotspots-out", type=Path, default=None, help="Write hotspots to CSV")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unified Spark report analyzer — raw JSON + protobuf flame graph",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    raw_p = sub.add_parser("raw", help="Batch analyze raw JSON reports", formatter_class=argparse.RawTextHelpFormatter)
    _add_common_input_args(raw_p)
    _add_raw_analysis_args(raw_p)

    prof_p = sub.add_parser("profile", help="Decode spark sampler protobuf and analyze hotspots", formatter_class=argparse.RawTextHelpFormatter)
    _add_common_input_args(prof_p)
    _add_profile_analysis_args(prof_p)

    all_p = sub.add_parser("all", help="Run raw + profile analyses on same inputs", formatter_class=argparse.RawTextHelpFormatter)
    _add_common_input_args(all_p)
    _add_raw_analysis_args(all_p)
    _add_profile_analysis_args(all_p)

    return parser


def _run_raw(args: argparse.Namespace, raw_entries: List[dict]) -> int:
    if not raw_entries and not args.print_keys and not args.init_rule_file:
        print("[raw] No raw-capable input found. Skipping.")
        return 0

    inputs = []
    for e in raw_entries:
        if e.get("resolved_type") == "report_id":
            inputs.extend(load_from_ids([e["report_id"]]))
        elif e.get("resolved_type") == "raw":
            inputs.extend(load_from_files([e["path"]]))

    keys = available_rule_keys([normalize(rid, d) for rid, d in inputs] if inputs else None)
    if args.print_keys:
        print(json.dumps(keys, ensure_ascii=False, indent=2))
    if args.init_rule_file:
        template = init_rule_template(keys)
        _write_rule_template(args.init_rule_file, template)
        print(f"Initialized rule template: {args.init_rule_file}")

    if not inputs:
        return 0

    records = [normalize(report_id, data) for report_id, data in inputs]
    records.sort(key=lambda r: (r.timestamp, r.report_id))

    summary_rows = [
        {
            "report_id": r.report_id,
            "timestamp": r.timestamp,
            "uptime_ms": r.uptime_ms,
            "players_online": r.players_online,
            "tps_1m": r.tps_1m,
            "mspt_1m_mean": r.mspt_1m_mean,
            "mspt_1m_max": r.mspt_1m_max,
            "entities_total": r.entities_total,
            "chunks_total": r.chunks_total,
            "old_gen_post_gc_gb": r.old_gen_post_gc_gb,
            "swap_used_gb": r.swap_used_gb,
        }
        for r in records
    ]

    compare_rows = build_compare(records) if args.compare else []

    file_rules = []
    for rf in args.rule_file:
        file_rules.extend(load_rule_file(Path(rf)))
    alert_rows = evaluate_alerts(records, args.rule, file_rules) if args.alerts else []

    dimension_rows = dimension_focus(records, args.dimension_focus) if args.dimension_focus else []
    entity_rows = entity_locate(records, args.entity_locate) if args.entity_locate else []
    region_rows = region_view(records, *_parse_region(args.region_view)) if args.region_view else []
    chunk_rows = chunk_view(records, *_parse_chunk(args.chunk_view)) if args.chunk_view else []

    if args.out_summary:
        if args.out_summary.suffix.lower() == ".csv":
            write_csv(args.out_summary, summary_rows)
        else:
            write_json(args.out_summary, summary_rows)
    if args.out_details:
        write_jsonl(args.out_details, [r.to_dict() for r in records])
    if args.out_compare and compare_rows:
        if args.out_compare.suffix.lower() == ".csv":
            write_csv(args.out_compare, compare_rows)
        else:
            write_json(args.out_compare, compare_rows)
    if args.out_alerts and alert_rows:
        write_json(args.out_alerts, alert_rows)

    print(f"[raw] Loaded reports: {len(records)}")
    print(f"[raw] Summary rows: {len(summary_rows)}")
    if compare_rows:
        print(f"[raw] Compare rows: {len(compare_rows)}")
    if alert_rows:
        print(f"[raw] Triggered alerts: {len(alert_rows)}")
    if dimension_rows:
        print(f"[raw] Dimension focus rows: {len(dimension_rows)}")
    if entity_rows:
        print(f"[raw] Entity locate rows: {len(entity_rows)}")
    if region_rows:
        print(json.dumps(region_rows, ensure_ascii=False, indent=2))
    if chunk_rows:
        print(json.dumps(chunk_rows, ensure_ascii=False, indent=2))

    if not args.out_summary and not args.out_details and not args.out_compare and not args.out_alerts:
        print(json.dumps(summary_rows, ensure_ascii=False, indent=2))

    return 0


def _run_profile(args: argparse.Namespace, profile_entries: List[dict]) -> int:
    if not profile_entries:
        print("[profile] No profile-capable input found. Skipping.")
        return 0

    ensure_generated_proto(args.protoc)
    from spark import spark_sampler_pb2

    all_rows: List[NodeRow] = []
    next_id = 0

    for e in profile_entries:
        rid = e.get("report_id")
        fpath = e.get("path")
        payload = load_binary(rid, fpath)

        data = spark_sampler_pb2.SamplerData()
        try:
            data.ParseFromString(payload)
        except Exception as exc:
            print(f"[profile] Failed to parse payload from {rid or fpath}: {exc}")
            continue

        if not data.threads:
            print(f"[profile] No threads in {rid or fpath}.")
            continue

        selected = [t for t in data.threads if args.thread.lower() in t.name.lower()]
        if not selected:
            names = ", ".join(sorted({t.name for t in data.threads})[:20])
            print(f"[profile] Thread '{args.thread}' not found in {rid or fpath}. Available: {names}")
            continue

        for idx, t in enumerate(selected):
            rows, next_id = traverse(t, thread_id=next_id, start_id=next_id, time_window_index=args.time_window_index)
            all_rows.extend(rows)

        print(f"[profile] {rid or fpath}: threads={len(data.threads)} selected={len(selected)} rows={len(all_rows)}")

    if all_rows:
        print_hotspots(all_rows, top_n=max(args.top, 1))
        if args.full_tree_out:
            profile_write_jsonl(args.full_tree_out, all_rows)
        if args.hotspots_out:
            profile_write_csv(args.hotspots_out, all_rows)

    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "raw":
        raw_entries, _ = collect(args.report_id, _file_list(args.file), args.dir, args.glob)
        return _run_raw(args, raw_entries)

    if args.command == "profile":
        _, profile_entries = collect(args.report_id, _file_list(args.file), args.dir, args.glob)
        return _run_profile(args, profile_entries)

    if args.command == "all":
        raw_entries, profile_entries = collect(args.report_id, _file_list(args.file), args.dir, args.glob)
        rc1 = _run_raw(args, raw_entries)
        rc2 = _run_profile(args, profile_entries)
        return rc1 or rc2

    raise SystemExit(f"Unknown command: {args.command}")


def _file_list(files: List[str]) -> List[Path]:
    return [Path(f) for f in files] if files else []


if __name__ == "__main__":
    raise SystemExit(main())