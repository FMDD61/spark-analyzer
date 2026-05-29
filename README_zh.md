# spark-analyzer

English | **[中文文档](README_zh.md)**

Minecraft 服务器统一 Spark 报告分析器 — raw JSON 批量处理 + protobuf 火焰图解码。

## 功能

- **raw** 子命令：批量分析 Spark raw JSON 报告
  - 多报告摘要（TPS / MSPT / 内存 / 实体）
  - 跨报告对比（含 `top_entity_delta`）
  - 告警规则引擎（`--rule` 内联 / `--rule-file` YAML/JSON）
  - 维度聚焦（任意维度名，含模组自定义维度）
  - 实体定位、Region 视图、Chunk 视图
  - `--print-keys` 列出可用规则表达式键名
  - `--init-rule-file` 生成规则模板文件
- **profile** 子命令：解码 Spark sampler protobuf
  - 方法级热点分析（self time / total time）
  - 线程过滤、Top N、完整调用树导出
  - protoc/grpc_tools 自动回退链
- **all** 子命令：一次命令同时执行 raw + profile 分析

## 快速开始

### 安装依赖

```bash
pip install requests pyyaml grpcio-tools
```

### 基本用法

```bash
# 多报告摘要 + 对比
python spark_analyzer.py raw --report-id <ID1> --report-id <ID2> --compare

# 告警检测
python spark_analyzer.py raw --report-id <ID> --alerts --rule "tps.last1m < 18"

# 实体定位
python spark_analyzer.py raw --report-id <ID> --entity-locate minecraft:enderman

# 维度 + 区块视图
python spark_analyzer.py raw --report-id <ID> --dimension-focus the_end --chunk-view the_end:-13,47

# 火焰图热点
python spark_analyzer.py profile --report-id <ID> --thread "Server thread" --top 30

# 联合分析
python spark_analyzer.py all --report-id <ID1> --report-id <ID2> \
  --compare --alerts --rule "tps.last1m < 18" \
  --thread "Server thread" --top 30
```

### 统一输入

所有子命令共享输入参数，`--report-id` 自动同时拉取 JSON 和 protobuf：

- `--report-id`（可重复）：Spark 报告 ID
- `--file`（可重复）：本地文件，自动识别 JSON/protobuf
- `--dir` + `--glob`：批量扫描本地目录

### 告警规则引擎

表达式格式：`KEY OP VALUE`

```bash
--rule "tps.last1m < 18"
--rule "mspt.last1m.max > 500"
--rule "dimension.the_end.entities_per_chunk > 3"
--rule "entity.minecraft:enderman.count > 30"
```

生成规则模板：

```bash
python spark_analyzer.py raw --init-rule-file alerts_template.yaml
python spark_analyzer.py raw --init-rule-file alerts_template.json
```

列出数据集可用键名：

```bash
python spark_analyzer.py raw --report-id <ID> --print-keys
```

## 项目结构

```
spark_analyzer.py          统一 CLI 入口
input_resolver.py          统一输入层（自动识别 JSON/protobuf）
spark_json_lib/            raw JSON 分析模块
  loader.py                报告加载（ID/文件/目录）
  normalize.py             字段抽取与 chunk/region 归一化
  compare.py               跨报告对比 + top_entity_delta
  alerts.py                规则引擎（--rule/--rule-file/--print-keys/--init-rule-file）
  dimension.py             维度趋势分析
  entity_queries.py        实体定位 / Region 视图 / Chunk 视图
  output.py                CSV/JSON/JSONL 输出工具
spark_profile_lib/         protobuf 解码模块
  proto_compile.py         protoc/grpc_tools 编译与导入
  loader.py                二进制加载（report-id/本地文件）
  traverse.py              children_refs 遍历与 NodeRow 生成
  hotspots.py              Top self/total 热点计算
  writers.py               JSONL/CSV 输出
proto/spark/               Spark protobuf schema 文件
docs/                      设计、使用、迁移文档
```

## 文档

- [设计文档](docs/spark_analyzer_design.md) — 架构、输入层、规则引擎、输出格式
- [使用指南](docs/spark_analyzer_usage.md) — 命令、示例、规则文件格式、场景 cookbook
- [迁移指南](docs/spark_analyzer_migration.md) — 旧脚本 → 新 CLI 参数映射

## 许可证

本项目采用 GNU General Public License v3.0 (GPL-3.0) 授权。

`proto/spark/` 下的 protobuf schema 文件衍生自 [spark](https://github.com/lucko/spark) 项目，同样采用 GPL-3.0 授权。
