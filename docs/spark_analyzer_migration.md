# Spark Analyzer 迁移文档

## 旧脚本 → 新 CLI 参数映射

### spark_json_analyzer.py → spark_analyzer.py raw

| 旧参数 | 新参数 | 说明 |
|--------|--------|------|
| `--report-id` | `--report-id` | 无变化 |
| `--raw-file` | `--file` | 名称简化，功能不变 |
| `--raw-dir` | `--dir` | 名称简化，功能不变 |
| `--glob` | `--glob` | 无变化 |
| `--compare` | `--compare` | 无变化 |
| `--alerts` | `--alerts` | 无变化 |
| `--rule` | `--rule` | 无变化 |
| `--rule-file` | `--rule-file` | 无变化 |
| `--print-keys` | `--print-keys` | 无变化 |
| `--init-rule-file` | `--init-rule-file` | 无变化 |
| `--dimension-focus` | `--dimension-focus` | 无变化 |
| `--entity-locate` | `--entity-locate` | 无变化 |
| `--region-view` | `--region-view` | 无变化 |
| `--chunk-view` | `--chunk-view` | 无变化 |
| `--out-summary` | `--out-summary` | 无变化 |
| `--out-details` | `--out-details` | 无变化 |
| `--out-compare` | `--out-compare` | 无变化 |
| `--out-alerts` | `--out-alerts` | 无变化 |

### spark_profile_decoder.py → spark_analyzer.py profile

| 旧参数 | 新参数 | 说明 |
|--------|--------|------|
| `--report-id` | `--report-id` | 无变化 |
| `--file` | `--file` | 无变化 |
| `--thread` | `--thread` | 无变化 |
| `--top` | `--top` | 无变化 |
| `--time-window-index` | `--time-window-index` | 无变化 |
| `--protoc` | `--protoc` | 无变化 |
| `--full-tree-out` | `--full-tree-out` | 无变化 |
| `--hotspots-out` | `--hotspots-out` | 无变化 |

## 迁移示例

### 旧命令 → 新命令

```bash
# 旧
python spark_json_analyzer.py --report-id lcwqNWJps6 --report-id SfcG9mKOie --compare --alerts --rule "tps.last1m < 18"
# 新
python spark_analyzer.py raw --report-id lcwqNWJps6 --report-id SfcG9mKOie --compare --alerts --rule "tps.last1m < 18"

# 旧
python spark_json_analyzer.py --raw-file report1.json --raw-file report2.json --compare
# 新
python spark_analyzer.py raw --file report1.json --file report2.json --compare

# 旧
python spark_json_analyzer.py --raw-dir ./reports --glob "*.json"
# 新
python spark_analyzer.py raw --dir ./reports --glob "*.json"

# 旧
python spark_profile_decoder.py --report-id lcwqNWJps6 --thread "Server thread" --top 30
# 新
python spark_analyzer.py profile --report-id lcwqNWJps6 --thread "Server thread" --top 30
```

## Wrapper 移除计划

- **当前状态**：旧脚本为 wrapper，打印 deprecated 提示后转发到 `spark_analyzer.py`
- **移除时机**：确认所有外部调用已迁移到新 CLI 后
- **移除操作**：删除 `spark_json_analyzer.py` 和 `spark_profile_decoder.py`
- **影响范围**：仅影响直接调用旧脚本路径的命令行或自动化脚本

## 新增能力（旧脚本不具备）

1. **`all` 子命令**：一次命令同时跑 raw + profile
2. **统一输入**：同一 `--report-id` 可同时拉取 JSON 和 protobuf
3. **`--file` 自动识别**：不再需要区分 json/protobuf 文件类型
4. **`--dir` 批量扫描**：目录下混合 json 和 protobuf 文件也能正确处理