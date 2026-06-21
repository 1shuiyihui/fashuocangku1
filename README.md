# 法硕苏格拉底本地学习工具

本项目是一个本地 Streamlit 应用，用于记录法硕考研错题和薄弱点，并通过可编辑提示词模板启动苏格拉底式追问训练。

## 功能

- 上传实体书错题照片并记录科目、题型、考点、错因和掌握度
- 管理可编辑的追问提示词模板
- 围绕薄弱点进行 AI 苏格拉底训练
- 统计薄弱科目、薄弱考点和高频错因
- 生成周度和月度复盘 Markdown 报告

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

## AI 配置

在侧边栏输入 OpenAI-compatible API 配置：

- API Base，例如 `https://api.openai.com/v1`
- Model，例如 `gpt-4.1-mini`
- API Key

没有 API Key 时，错题录入、模板管理、薄弱点分析和复盘仍可使用；苏格拉底训练聊天会提示补充配置。
