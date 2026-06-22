# 法硕苏格拉底本地学习工具

本项目是一个本地 Streamlit 应用，用于记录法硕考研错题和薄弱点，并通过可编辑提示词模板启动苏格拉底式追问训练。

## 功能

- 上传实体书错题照片并记录科目、题型、考点、错因和掌握度
- 管理可编辑的追问提示词模板
- 围绕薄弱点进行 AI 苏格拉底训练
- 上传 PDF、图片、TXT、Markdown 资料并建立本地 RAG 知识库
- 基于资料片段调用大模型生成课程和训练点
- 统计薄弱科目、薄弱考点和高频错因
- 生成周度和月度复盘 Markdown 报告
- v0.8.0 起，今日学习、薄弱点分析和周度/月度复盘围绕“录入训练点 → 苏格拉底训练 → 分析 → 复盘 → 再训练”的闭环组织，页面操作会真实跳转到后续训练或复盘步骤。
- v0.9.0 起，左侧边栏、错题/薄弱点录入、苏格拉底训练、资料知识库和训练计划页面重构为工作台式 UI：上传/录入、追问训练、资料检索、计划生成和导入训练点都围绕同一学习闭环展示。
- v0.10.0 起，周度/月度复盘重构为复盘驾驶舱：先看训练队列、学习概况、高频薄弱点和高频错因，再生成下一轮训练计划，Markdown 原文保留为折叠预览和下载。

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 运行

```powershell
streamlit run app.py
```

打开 `http://localhost:8501/`。

## 第一次使用

1. 保持侧边栏的 `新手模式` 开启。
2. 进入 `错题/薄弱点录入`，先只填科目、题型、考点、错因和掌握度。
3. 进入 `苏格拉底训练`，选择刚录入的薄弱点和一个模板，第一次不用修改提示词。
4. 如果还没有配置 API Key，训练页会提示配置；其它页面仍可正常记录和复盘。
5. 训练后进入 `周度/月度复盘` 查看薄弱点和下一步建议。

## 资料知识库、OCR 和 RAG

进入 `资料知识库` 页面可以上传：

- PDF
- 图片：PNG、JPG、JPEG、WEBP
- TXT
- Markdown

处理逻辑：

- TXT/Markdown 直接读取文本。
- PDF 优先抽取内嵌文字。
- 图片使用本地 Tesseract OCR。
- 抽取后的文本会切成片段，使用本地 TF-IDF RAG 检索，不需要下载 embedding 模型。

如果需要图片 OCR，请先安装 Tesseract：

```powershell
winget install UB-Mannheim.TesseractOCR
```

安装后重启终端或 Codex，再运行应用。没有 Tesseract 时，PDF/TXT/Markdown 仍可正常处理；图片 OCR 会显示明确提示。

## 资料生成课程

在 `资料知识库` 页面完成资料处理后：

1. 输入课程目标，例如 `法硕刑法共同犯罪 7 天冲刺`。
2. 选择复习周期。
3. 点击 `调用大模型生成课程`。
4. 系统会保存课程和小节。
5. 每个小节都可以一键导入为 `苏格拉底训练` 的薄弱点。

训练时，如果知识库里有相关资料，系统会自动检索资料片段并注入本次追问提示词。

## 系统与备份

进入 `系统与备份` 页面可以查看：

- 当前应用版本
- 当前数据库 schema 版本
- SQLite 完整性检查结果
- 关键表数据量
- 已执行迁移记录
- 最近备份

应用启动时会检查数据库版本。旧数据库会先自动备份，再执行迁移；如果发现数据库版本高于当前应用支持版本，系统会拒绝继续写入，避免旧代码破坏新数据。

也可以在页面中手动点击 `立即创建备份`，备份会复制数据库、错题图片目录、资料目录和 manifest.json。

## AI 配置

在侧边栏输入 OpenAI-compatible API 配置：

- API Base，例如 `https://api.deepseek.com`
- Model，例如 `deepseek-v4-pro`
- API Key

没有 API Key 时，错题录入、模板管理、薄弱点分析和复盘仍可使用；苏格拉底训练聊天会提示补充配置。

## Streamlit Cloud 云端持久化

部署到 Streamlit Cloud 时，建议把 DeepSeek 和数据持久化都配置在 App Secrets：

```toml
[ai]
api_base = "https://api.deepseek.com"
model = "deepseek-v4-pro"
api_key = "replace-with-your-deepseek-key"

[persistence]
enabled = true
provider = "github"
repo = "1shuiyihui/fashuocangku1"
branch = "cloud-data"
source_branch = "codex/fashuo-socratic-local-tool"
snapshot_path = "fashuo-cloud-snapshot.zip"
github_token = "replace-with-github-token"
```

开启后，应用启动时会先从 `cloud-data` 分支恢复 `data/fashuo.db`、`data/uploads/` 和 `data/documents/`，写入学习记录后会自动上传新的快照。`github_token` 只放在 Streamlit Secrets，不要提交到 GitHub。

部署或重启后，页面顶部和左侧状态卡应显示：

- `AI 已配置`
- `GitHub 云端快照`

当前 GitHub fine-grained token 配置提醒：

- Expiration：`90 days (Sep 20, 2026)`，到期前需要重新生成并更新 Streamlit Secrets。
- Repository access：`Only select repositories`。
- Repository：`1shuiyihui/fashuocangku1`。
- Repository permissions：`Contents` 必须为 `Read and write`。
- Account permissions 不需要额外添加。

## 本地验收流程

1. 新增一个薄弱点。
2. 在模板管理确认 6 个内置模板存在。
3. 在苏格拉底训练页预览提示词。
4. 未配置 API Key 时，训练页应提示配置，不应影响其它页面。
5. 在薄弱点分析和周度/月度复盘中确认新增记录被统计。
