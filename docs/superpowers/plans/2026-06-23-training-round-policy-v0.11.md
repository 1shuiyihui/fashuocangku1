# v0.11.0 苏格拉底训练轮次策略计划

## 执行步骤

1. 用测试覆盖训练 prompt 轮次规则和页面辅助函数。
2. 在 `services/prompts.py` 中增加轮次策略参数与 prompt 规则。
3. 在 `app.py` 中增加轮次常量、归一化函数、训练页设置和结束前校验。
4. 更新应用版本到 `v0.11.0`。
5. 运行完整测试、编译检查、HTTP 检查和浏览器 smoke test。

## 风险判断

- 数据库结构：不变。
- 用户数据：不读取、不迁移、不覆盖。
- AI 行为：新会话的 prompt 会更明确地要求连续追问至少 3 轮。
- 旧会话：旧会话 prompt_snapshot 不被改写；页面侧默认按至少 3 轮校验。

## 验证清单

- `python -m pytest -q`
- `python -m py_compile app.py services/storage.py services/prompts.py services/analysis.py services/ai_client.py services/document_processor.py services/rag.py services/course_generator.py services/backup.py services/migrations.py services/versioning.py prompts/seed_templates.py`
- HTTP `http://localhost:8501/`
- 浏览器检查训练页出现“最少追问轮次”“最大追问轮次”“至少完成 3 轮”
