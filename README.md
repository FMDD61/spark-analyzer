# spark-analyzer

**[中文文档](README_zh.md)** | English

Unified Spark report analyzer for Minecraft servers — raw JSON batch processing + protobuf flame graph decoding.

## Features

- **raw** subcommand: batch analyze Spark raw JSON reports
  - Multi-report summary with TPS / MSPT / memory / entities
  - Cross-report comparison with `top_entity_delta`
  - Alert rule engine (`--rule` inline / `--rule-file` YAML/JSON)
  - Dimension focus (any dimension name, including modded)
  - Entity locate, region view, chunk view
  - `--print-keys` to list available rule expression keys
  - `--init-rule-file` to generate starter rule templates
- **profile** subcommand: decode Spark sampler protobuf
  - Method-level hotspot analysis (self time / total time)
  - Thread filtering, top-N, full call tree export
  - Automatic protoc/grpc_tools fallback chain
- **all** subcommand: run both analyses in one command

## Quick Start

### Dependencies

```bash
pip install requests pyyaml grpcio-tools
```

### Usage

```bash
# Multi-report summary + comparison
python spark_analyzer.py raw --report-id <ID1> --report-id <ID2> --compare

# Alert detection
python spark_analyzer.py raw --report-id <ID> --alerts --rule "tps.last1m < 18"

# Entity locate
python spark_analyzer.py raw --report-id <ID> --entity-locate minecraft:enderman

# Dimension + chunk view
python spark_analyzer.py raw --report-id <ID> --dimension-focus the_end --chunk-view the_end:-13,47

# Flame graph hotspots
python spark_analyzer.py profile --report-id <ID> --thread "Server thread" --top 30

# Combined analysis
python spark_analyzer.py all --report-id <ID1> --report-id <ID2> \
  --compare --alerts --rule "tps.last1m < 18" \
  --thread "Server thread" --top 30
```

### Input Sources

All subcommands share unified input parameters:

- `--report-id` (repeatable): Spark report ID, auto-fetches both JSON and protobuf
- `--file` (repeatable): local file, auto-detects JSON vs protobuf by extension + content probing
- `--dir` + `--glob`: batch scan local directory

### Alert Rule Engine

Expression format: `KEY OP VALUE`

```bash
--rule "tps.last1m < 18"
--rule "mspt.last1m.max > 500"
--rule "dimension.the_end.entities_per_chunk > 3"
--rule "entity.minecraft:enderman.count > 30"
```

Generate a starter template:

```bash
python spark_analyzer.py raw --init-rule-file alerts_template.yaml
python spark_analyzer.py raw --init-rule-file alerts_template.json
```

List all available keys for a dataset:

```bash
python spark_analyzer.py raw --report-id <ID> --print-keys
```

## Project Structure

```
spark_analyzer.py          Unified CLI entry point
input_resolver.py          Unified input layer (auto-detect JSON/protobuf)
spark_json_lib/            Raw JSON analysis modules
  loader.py                Report loading (ID/file/directory)
  normalize.py             Field extraction & chunk/region normalization
  compare.py               Cross-report comparison + top_entity_delta
  alerts.py                Rule engine (--rule/--rule-file/--print-keys/--init-rule-file)
  dimension.py             Dimension trend analysis
  entity_queries.py        Entity locate / region view / chunk view
  output.py                CSV/JSON/JSONL output utilities
spark_profile_lib/         Protobuf decoding modules
  proto_compile.py         protoc/grpc_tools compilation & import
  loader.py                Binary loading (report-id/local file)
  traverse.py              children_refs traversal & NodeRow generation
  hotspots.py              Top self/total hotspot computation
  writers.py               JSONL/CSV output
proto/spark/               Spark protobuf schema files
docs/                      Design, usage, and migration documentation
```

## Documentation

- [Design document](docs/spark_analyzer_design.md) — architecture, input layer, rule engine, output formats
- [Usage guide](docs/spark_analyzer_usage.md) — commands, examples, rule file format, cookbook
- [Migration guide](docs/spark_analyzer_migration.md) — old script → new CLI parameter mapping

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0).

The protobuf schema files under `proto/spark/` are derived from the [spark](https://github.com/lucko/spark) project by lucko, also licensed under GPL-3.0.
