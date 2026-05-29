# Spark Analyzer 使用文档

## 快速开始

脚本路径：`references/scripts/spark_analyzer.py`

依赖安装：
```bash
pip install requests pyyaml grpcio-tools
```

## 1. raw 子命令 — 批量分析 JSON 报告

### 基本摘要

```bash
python spark_analyzer.py raw --report-id lcwqNWJps6 --report-id SfcG9mKOie
```

### 对比分析

```bash
python spark_analyzer.py raw --report-id lcwqNWJps6 --report-id SfcG9mKOie --compare --out-compare compare.csv
```

### 告警检测

```bash
# 内联规则
python spark_analyzer.py raw --report-id lcwqNWJps6 --alerts --rule "tps.last1m < 18" --rule "mspt.last1m.max > 500"

# 规则文件
python spark_analyzer.py raw --report-id lcwqNWJps6 --alerts --rule-file alerts.yaml
```

### 维度聚焦

```bash
python spark_analyzer.py raw --report-id lcwqNWJps6 --dimension-focus the_end --dimension-focus overworld
```

### 实体定位与视图

```bash
# 定位特定实体
python spark_analyzer.py raw --report-id lcwqNWJps6 --entity-locate minecraft:enderman

# Region 视图
python spark_analyzer.py raw --report-id lcwqNWJps6 --region-view the_end:-1,1

# Chunk 视图
python spark_analyzer.py raw --report-id lcwqNWJps6 --chunk-view the_end:-13,47
```

### 输出到文件

```bash
python spark_analyzer.py raw --report-id lcwqNWJps6 \
  --out-summary summary.json \
  --out-details details.jsonl \
  --out-compare compare.csv \
  --out-alerts alerts.json
```

### 规则模板与键名

```bash
# 查看可用键名（含动态维度/实体键）
python spark_analyzer.py raw --report-id lcwqNWJps6 --print-keys

# 生成 YAML 规则模板
python spark_analyzer.py raw --init-rule-file alerts_template.yaml

# 生成 JSON 规则模板
python spark_analyzer.py raw --init-rule-file alerts_template.json
```

### 本地文件输入

```bash
# 单文件
python spark_analyzer.py raw --file report1.json --file report2.json --compare

# 目录批量
python spark_analyzer.py raw --dir ./spark_reports --glob "*.json" --compare
```

## 2. profile 子命令 — 火焰图热点分析

### 基本热点

```bash
python spark_analyzer.py profile --report-id lcwqNWJps6 --thread "Server thread" --top 30
```

### 输出完整调用树

```bash
python spark_analyzer.py profile --report-id lcwqNWJps6 \
  --full-tree-out full_tree.jsonl \
  --hotspots-out hotspots.csv
```

### 指定线程

```bash
# 查看 Main 线程
python spark_analyzer.py profile --report-id lcwqNWJps6 --thread "main"

# 查看所有线程（空字符串匹配全部，PowerShell 需用 '""'）
python spark_analyzer.py profile --report-id lcwqNWJps6 --thread ""
```

### 本地 protobuf 文件

```bash
python spark_analyzer.py profile --file report.sparkprofile --top 80
```

### 自定义 protoc

```bash
python spark_analyzer.py profile --report-id lcwqNWJps6 --protoc /usr/local/bin/protoc
```

## 3. all 子命令 — 联合分析

一次命令同时运行 raw 和 profile，自动跳过无输入的部分。

```bash
python spark_analyzer.py all \
  --report-id lcwqNWJps6 \
  --report-id SfcG9mKOie \
  --compare --alerts --rule "tps.last1m < 18" \
  --thread "Server thread" --top 30 \
  --out-summary summary.json \
  --out-alerts alerts.json \
  --full-tree-out full_tree.jsonl \
  --hotspots-out hotspots.csv
```

## 4. 规则文件格式

### YAML 格式（alerts_template.yaml）

```yaml
rules:
  - id: low_tps
    severity: high
    expr: tps.last1m < 18
  - id: high_mspt_spike
    severity: high
    expr: mspt.last1m.max > 500
  - id: old_gen_pressure
    severity: medium
    expr: memory.old_gen.post_gc_gb > 18
notes:
  - Rules are evaluated per report independently.
  - Use --print-keys to list all available expression keys.
available_keys:
  - tps.last1m
  - mspt.last1m.max
  - memory.old_gen.post_gc_gb
```

### JSON 格式（alerts_template.json）

```json
{
  "rules": [
    {"id": "low_tps", "severity": "high", "expr": "tps.last1m < 18"},
    {"id": "high_mspt_spike", "severity": "high", "expr": "mspt.last1m.max > 500"}
  ],
  "notes": [
    "Rules are evaluated per report independently.",
    "Use --print-keys to list all available expression keys."
  ],
  "available_keys": ["tps.last1m", "mspt.last1m.max", "memory.old_gen.post_gc_gb"]
}
```

### 规则表达式语法

格式：`KEY OP VALUE`

- KEY：使用 `--print-keys` 列出的键名
- OP：`< <= > >= == !=`
- VALUE：数字或字符串

示例：
```
tps.last1m < 18
mspt.last1m.max > 500
dimension.the_end.entities_per_chunk > 3
entity.minecraft:enderman.count > 30
```

## 5. 常见场景 Cookbook

### 场景 1：卡顿报告联合分析

```bash
python spark_analyzer.py all \
  --report-id lcwqNWJps6 \
  --compare --alerts --rule "mspt.last1m.max > 200" \
  --thread "Server thread" --top 30 \
  --full-tree-out tree.jsonl \
  --out-summary summary.json
```

### 场景 2：末地刷怪塔实体密度

```bash
python spark_analyzer.py raw \
  --report-id SfcG9mKOie \
  --dimension-focus the_end \
  --entity-locate minecraft:enderman \
  --chunk-view the_end:-13,47 \
  --region-view the_end:-1,1
```

### 场景 3：跨时间点对比

```bash
python spark_analyzer.py raw \
  --report-id wf4kl5jgj7 --report-id lcwqNWJps6 --report-id SfcG9mKOie \
  --compare --out-compare timeline.csv
```

### 场景 4：定期巡检告警

```bash
# 先生成模板
python spark_analyzer.py raw --init-rule-file weekly_check.yaml

# 编辑后使用
python spark_analyzer.py raw --report-id NEW_REPORT_ID --alerts --rule-file weekly_check.yaml
```