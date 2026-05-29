# Spark Analyzer 设计文档

## 1. 架构总览

```
spark_analyzer.py (统一 CLI 入口)
├── subcommand: raw        → spark_json_lib/*      (raw JSON 批处理)
├── subcommand: profile    → spark_profile_lib/*   (protobuf 火焰图解码)
└── subcommand: all        → 两者联合执行
│
├── input_resolver.py      (统一输入层，自动识别 JSON/protobuf)
│   ├── --report-id        → 自动同时拉取 raw JSON + spark-usercontent protobuf
│   ├── --file             → 按扩展名/内容探测自动归类
│   └── --dir + --glob     → 批量扫描与归类
│
├── spark_json_lib/        (raw JSON 分析模块)
│   ├── loader.py          报告加载（ID/文件/目录）
│   ├── normalize.py       字段抽取与 chunk/region 归一化
│   ├── compare.py         跨报告对比 + top_entity_delta
│   ├── alerts.py          规则引擎（--rule/--rule-file + --print-keys/--init-rule-file）
│   ├── dimension.py       维度趋势分析
│   ├── entity_queries.py  实体定位/Region 视图/Chunk 视图
│   └── output.py          CSV/JSON/JSONL 输出
│
├── spark_profile_lib/     (protobuf 解码模块)
│   ├── proto_compile.py   protoc/grpc_tools 编译与导入
│   ├── loader.py          二进制加载（report-id/本地文件）
│   ├── traverse.py        children_refs 展开与 NodeRow 生成
│   ├── hotspots.py        Top self/total 热点计算与打印
│   └── writers.py         JSONL/CSV 输出
│
└── _generated/spark/      (自动生成的 protobuf Python 模块)
```

## 2. 统一输入层设计

### 输入参数（所有子命令共享）

| 参数 | 说明 | 可重复 |
|------|------|--------|
| `--report-id` | Spark 报告 ID | 是 |
| `--file` | 本地文件路径，自动识别 JSON/protobuf | 是 |
| `--dir` | 本地目录，批量扫描 | 否 |
| `--glob` | `--dir` 的 glob 模式，默认 `*` | 否 |

### 文件类型识别策略

1. **扩展名猜测**（优先）
   - `.json/.rawjson/.raw` → raw
   - `.sparkprofile/.bin/.proto/.pb` → profile
2. **内容探测**（扩展名不可靠时）
   - 尝试 JSON 解析 → raw
   - 非文本二进制 → profile
3. **`--report-id`** 同时生成 raw 和 profile 两个候选（同一 ID 可同时拉取两种数据）

## 3. 子命令参数

### raw 子命令

| 参数 | 说明 |
|------|------|
| `--compare` | 跨报告对比 |
| `--alerts` | 启用规则告警 |
| `--rule EXPR` | 内联规则表达式（可重复） |
| `--rule-file PATH` | 规则文件（YAML/JSON，可重复） |
| `--print-keys` | 打印可用规则表达式键 |
| `--init-rule-file PATH` | 生成示例规则文件 |
| `--dimension-focus DIM` | 维度聚焦（可重复） |
| `--entity-locate TYPE` | 实体定位 |
| `--region-view DIM:RX,RZ` | Region 视图 |
| `--chunk-view DIM:X,Z` | Chunk 视图 |
| `--out-summary PATH` | Summary 输出 |
| `--out-details PATH` | Details JSONL 输出 |
| `--out-compare PATH` | Compare 输出 |
| `--out-alerts PATH` | Alerts JSON 输出 |

### profile 子命令

| 参数 | 说明 |
|------|------|
| `--thread NAME` | 线程名过滤（大小写不敏感包含匹配，默认 `Server thread`） |
| `--top N` | Top N 热点（默认 50） |
| `--time-window-index IDX` | 时间窗口索引（调试） |
| `--protoc PATH` | protoc 可执行文件路径 |
| `--full-tree-out PATH` | 完整调用树 JSONL |
| `--hotspots-out PATH` | 热点 CSV |

### all 子命令

同时接受 raw 和 profile 的全部参数。自动执行两套分析：能跑哪个跑哪个，缺输入则跳过并提示。

## 4. 规则引擎设计

- **表达式格式**：`KEY OP VALUE`，如 `tps.last1m < 18`
- **支持的比较运算**：`< <= > >= == !=`
- **键名体系**：
  - 固定键：`tps.last1m`、`mspt.last1m.max`、`memory.old_gen.post_gc_gb` 等
  - 动态维度键：`dimension.the_end.entities_per_chunk`
  - 动态实体键：`entity.minecraft:enderman.count`
- **--print-keys**：列出当前数据集实际可用的全部键名
- **--init-rule-file**：生成带示例规则和可用键列表的模板文件（YAML 或 JSON）

## 5. Protobuf 编译回退链

1. `--protoc` 显式指定
2. `PROTOC` 环境变量
3. PATH 中 `protoc`/`protoc.exe`
4. `grpc_tools.protoc`（Python 包 `grpcio-tools`）

## 6. 输出格式

| 数据 | 默认格式 | 可选格式 |
|------|----------|----------|
| Summary | JSON | CSV（路径后缀为 `.csv`） |
| Details | JSONL | — |
| Compare | JSON | CSV |
| Alerts | JSON | — |
| Profile tree | JSONL | — |
| Profile hotspots | CSV | — |

## 7. 旧脚本兼容

| 旧脚本 | 新对应 | 参数映射 |
|--------|--------|----------|
| `spark_json_analyzer.py` | `spark_analyzer.py raw` | `--raw-file→--file`，`--raw-dir→--dir` |
| `spark_profile_decoder.py` | `spark_analyzer.py profile` | 无变化 |

旧脚本当前为 wrapper，打印 deprecated 提示后转发到新 CLI。稳定后将移除。

## 8. 已知限制

- 直接访问 `raw.githubusercontent.com` 受限（Transport error），改用 GitHub API 获取源码。
- `protoc` 需安装或通过 `grpcio-tools` 回退。
- 规则表达式不支持逻辑组合（AND/OR），每条规则独立评估。
- `all` 子命令的 profile 部分逐报告顺序执行，多报告时较慢。