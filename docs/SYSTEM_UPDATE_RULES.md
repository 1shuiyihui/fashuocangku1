# 系统更新守则

这份守则用于后续每一次项目更新。目标是：代码可以持续升级，用户已经保存的错题、资料、OCR 文本、RAG 片段、课程和训练记录不能因为更新丢失、错乱或乱码。

## 1. 更新前必须先判断风险

每次修改前先回答：

- 是否会改数据库结构？
- 是否会改 `data/` 目录读写方式？
- 是否会改文件上传、OCR、PDF 抽取、RAG 切块或课程生成？
- 是否会改中文文本读写、编码、导入导出？
- 是否会改依赖版本？

只要任意一项为“是”，就按数据敏感更新处理。

## 2. 代码版本和用户数据必须分离

代码仓库可以更新、切分支、合并；用户数据不能跟随代码变动被覆盖。

当前需要视为用户数据的位置：

```text
data/fashuo.db
data/uploads/
data/documents/
```

后续推荐迁移到仓库外的数据根目录，例如：

```text
C:\Users\yhshi16\Documents\ai网课_data\
  current\
    fashuo.db
    uploads\
    documents\
  backups\
  exports\
```

在完成外置数据目录之前，任何操作都不能删除或重建 `data/` 中的真实用户数据。

## 3. 数据库升级必须使用 schema 版本

后续需要新增：

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL
);
```

每次数据库结构变化都要新增迁移文件：

```text
migrations/
  0001_initial.sql
  0002_add_documents.sql
  0003_add_courses.sql
```

规则：

- 迁移只能向前执行。
- 迁移前必须备份。
- 迁移后必须跑完整性检查。
- 不能通过删除旧表再建新表的方式偷懒，除非先完整复制数据并验证数量。
- 旧版本应用打开新版本数据库时必须拒绝写入。

## 4. 更新前必须备份

对数据敏感更新，先创建备份目录：

```text
backups/YYYY-MM-DD_HHMMSS_before_<update-name>/
  fashuo.db
  uploads/
  documents/
  manifest.json
```

`manifest.json` 至少记录：

- app branch
- git commit
- database path
- backup time
- table counts
- update reason

表数量至少检查：

- weak_points
- templates
- template_versions
- sessions
- messages
- documents
- document_chunks
- generated_courses
- course_lessons
- rag_queries

## 5. 更新前后必须做完整性检查

SQLite 检查：

```sql
PRAGMA integrity_check;
```

如果结果不是 `ok`，停止更新。

更新后还要比较关键表数量。除非本次更新明确要删除数据，否则数量异常减少时必须停止并提示用户。

## 6. 中文和文件编码规则

所有项目源代码和 Markdown 文档使用 UTF-8。

用户上传文本文件读取顺序：

1. `utf-8-sig`
2. `utf-8`
3. `gb18030`

不能用 PowerShell 终端里的中文显示结果判断文件是否乱码。验证中文时优先用 Python 读取并断言实际字符串。

OCR、PDF 抽取、RAG 切块和课程生成中，任何文本写入 SQLite 前都应保持 Python `str`，不要手动 encode/decode 多次。

## 7. 依赖升级规则

升级依赖前先说明原因。升级后必须验证：

- OCR 依赖是否仍可导入。
- PDF 抽取是否仍可导入。
- scikit-learn TF-IDF 是否仍可运行。
- Streamlit 页面是否仍可启动。

依赖升级不能顺手改业务逻辑，除非当前任务明确需要。

## 8. 每次更新的最小验证

所有更新完成后必须运行：

```powershell
python -m pytest -q
python -m py_compile app.py services/storage.py services/prompts.py services/analysis.py services/ai_client.py services/document_processor.py services/rag.py services/course_generator.py services/backup.py services/migrations.py services/versioning.py prompts/seed_templates.py
```

如果本地应用正在运行，还要检查：

```powershell
(Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8501/' -TimeoutSec 10).StatusCode
```

涉及页面交互时，还要做浏览器 smoke test。

## 9. 更新说明必须包含数据状态

每次完成更新时，最终说明必须写清楚：

- 是否修改了数据库结构。
- 是否执行了迁移。
- 是否创建了备份。
- 是否触碰了用户数据。
- 测试命令和结果。
- 当前分支和工作区状态。

如果没有触碰数据，也要明确写：`用户数据未修改`。

## 10. 禁止事项

- 禁止为了修 bug 删除 `data/fashuo.db`。
- 禁止清空 `data/uploads/` 或 `data/documents/`。
- 禁止用新空数据库覆盖旧数据库。
- 禁止没有备份就做 schema 变更。
- 禁止没有验证就声称更新完成。
- 禁止用终端乱码判断源文件损坏。
- 禁止为了通过测试而降低数据安全规则。

## 11. 推荐的未来实现任务

守则已开始自动化，当前已实现：

- `services/versioning.py`
- `services/backup.py`
- `services/migrations.py`
- `migrations/` 目录
- `系统与备份` 页面

页面功能：

- 当前应用版本。
- 当前数据库版本。
- 一键备份。
- 一键导出完整数据包。
- 最近备份列表。
- 数据完整性检查。
- 迁移日志。
