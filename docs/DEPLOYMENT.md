# 网站部署说明

本项目优先按 1-2 人内测网站部署，不做重型后端拆分。

## 推荐平台

首选 Streamlit Community Cloud：

- 仓库：`https://github.com/1shuiyihui/fashuocangku1`
- 分支：`codex/fashuo-socratic-local-tool`
- 入口文件：`app.py`
- Python 依赖：`requirements.txt`
- 系统依赖：`packages.txt`

## Secrets 配置

不要把真实 API Key 写进 GitHub。部署时在平台 Secrets 中填写：

```toml
[ai]
api_base = "https://api.deepseek.com"
model = "deepseek-v4-pro"
api_key = "replace-with-your-api-key"
```

本地可参考 `.streamlit/secrets.toml.example`，但真实 `.streamlit/secrets.toml` 已被 `.gitignore` 排除。

## 数据策略

当前私有仓库允许同步：

- `data/fashuo.db`
- `data/uploads/`
- `data/documents/`

仍然禁止提交：

- `.env`
- `.streamlit/secrets.toml`
- `backups/`
- `logs/`
- Python 缓存和虚拟环境

## 运行限制

当前架构适合 1-2 人使用。SQLite 已开启 WAL、外键检查和写入等待时间，上传文件大小限制为：

- 错题图片：15 MB
- 资料文件：30 MB

如果后续同时使用人数明显增加，或 OCR/课程生成经常排队，再考虑迁移到 FastAPI、PostgreSQL 和后台任务队列。

## Streamlit Cloud 持久化配置 v0.7.0

Streamlit Cloud 重启或重新部署时，运行时磁盘会回到 GitHub 代码快照。v0.7.0 增加了 GitHub 私有快照同步，避免新增记录、上传资料、RAG 片段、课程和训练消息在重启后丢失。

在 Streamlit Cloud 的 App Secrets 中填写：

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

`github_token` 建议使用 GitHub fine-grained personal access token，只授权当前私有仓库，权限选择 `Contents: Read and write`。不要把 token 写进代码或提交到 GitHub。

数据快照会写入单独的 `cloud-data` 分支，不写入正在部署的 `codex/fashuo-socratic-local-tool` 分支，避免每次保存学习记录都触发 Streamlit 重新部署。

配置后重启应用，顶栏应显示 `GitHub 云端快照`。如果显示 `本地临时存储`，说明 `[persistence]` 没有启用或 Secrets 没有生效。

## 上线后检查

部署完成后检查：

1. 首页可以打开。
2. `系统与备份` 页面显示数据库版本等于支持版本。
3. `资料知识库` 能上传 TXT 或 Markdown。
4. 未配置 API Key 时，普通记录和复盘功能仍可使用。
5. 配置 API Key 后，苏格拉底训练和课程生成可以调用模型。
