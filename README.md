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

## AI 配置

在侧边栏输入 OpenAI-compatible API 配置：

- API Base，例如 `https://api.openai.com/v1`
- Model，例如 `gpt-4.1-mini`
- API Key

没有 API Key 时，错题录入、模板管理、薄弱点分析和复盘仍可使用；苏格拉底训练聊天会提示补充配置。

## 本地验收流程

1. 新增一个薄弱点。
2. 在模板管理确认 6 个内置模板存在。
3. 在苏格拉底训练页预览提示词。
4. 未配置 API Key 时，训练页应提示配置，不应影响其它页面。
5. 在薄弱点分析和周度/月度复盘中确认新增记录被统计。
