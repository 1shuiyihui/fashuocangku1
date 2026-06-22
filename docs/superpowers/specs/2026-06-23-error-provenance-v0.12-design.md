# v0.12.0 错因还原与溯源闭环设计

## 问题

当前系统能记录薄弱点、训练会话和复盘统计，但错因仍停留在标签层面。用户无法稳定看到：

- 具体错在题干、答案、法条要件或表达的哪一处。
- 为什么会错，是概念混淆、要件遗漏、事实匹配失败还是表达采分失败。
- 每次 AI 追问、课程生成、复盘生成使用了哪些输入，输出了什么。
- 回顾复盘后应该做什么复盘练习和变式练习。

## 目标

- 保存结构化错因分析，包含错误位置、错误根因、证据、复盘练习和变式练习。
- 每个分析和 AI 调用都写入输入/输出文件，形成可追溯记录。
- 在薄弱点分析和周度/月度复盘中优先展示“错在何处、为什么错、下一步怎么练”。
- 不覆盖历史用户数据；通过版本迁移新增表和索引。

## 数据设计

新增 `error_analyses` 表：

- `weak_point_id`：关联训练点。
- `error_location`：错误发生位置，例如“题干事实识别”“构成要件”“主观题表达”。
- `root_cause`：根因，例如“要件遗漏”“概念混淆”。
- `evidence`：从题干、参考答案、备注或训练总结中还原出的证据。
- `review_drill`：复盘练习。
- `variant_drill`：变式练习。
- `status`：`draft` 或 `confirmed`。
- `created_at` / `updated_at`。

新增 `provenance_events` 表：

- `entity_type` / `entity_id`：关联 weak_point、session、review、course 等对象。
- `event_type`：entry_analysis、training_ai_call、review_report 等。
- `input_path` / `output_path`：本地留档文件。
- `metadata_json`：模型、模板、轮次、chunk 等上下文。
- `created_at`。

新增目录：

```text
data/provenance/
  YYYYMMDD/
    <event>_<id>_input.json
    <event>_<id>_output.md
```

## 行为设计

录入训练点后，系统基于结构化字段生成一条初始错因分析；如果题干、参考答案、备注越完整，错误还原越具体。无 AI Key 时仍可使用规则分析。

开始训练和每轮追问时，系统保存 prompt、历史消息、模型信息和 AI 回复。这样后续可以回看“当时 AI 为什么这样问”。

结束训练时，系统把 summary、暴露问题和下一次复习建议合入错因分析，刷新错误位置、根因和练习建议。

复盘页不再只列频次，还展示错因簇和练习包：每个高频错因给出复盘练习、变式练习和可跳转训练点。

## 数据安全

这是数据敏感更新。执行前必须备份 `data/fashuo.db`、`data/uploads/`、`data/documents/`，迁移只新增表和索引，不删除旧表和旧列。`data/provenance/` 是新增用户数据目录，会纳入云端快照。
