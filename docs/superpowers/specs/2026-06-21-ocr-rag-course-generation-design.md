# OCR RAG 课程生成增强设计

## 目标

在现有法硕苏格拉底本地学习工具中增加资料知识库能力，让用户上传法硕资料后，系统可以本地抽取文本、必要时 OCR、建立 RAG 检索索引，并基于资料生成后续课程、复习计划和可导入的苏格拉底训练点。

## 核心流程

1. 用户进入 `资料知识库` 页面上传 PDF、图片、TXT 或 Markdown。
2. 系统保存原文件到本地 `data/documents/`。
3. 系统按文件类型抽取文本：
   - TXT/Markdown：直接读取文本。
   - PDF：优先用 `pypdf` 抽取文本。
   - 图片：用 `pytesseract` 做 OCR。
   - PDF 抽取结果过短时提示用户这可能是扫描版，需要拆成图片或后续接更强 OCR。
4. 系统将文本按段落切块，保存到 `document_chunks`。
5. 系统用本地 TF-IDF 检索实现 RAG，不依赖额外模型下载。
6. 用户可输入查询词检索资料片段。
7. 用户点击生成课程后，系统先检索相关片段，再调用 OpenAI-compatible 大模型生成结构化课程 JSON。
8. 课程保存到本地数据库，并可一键把课程小节导入为 `weak_points`，进入现有苏格拉底训练。
9. 苏格拉底训练页在选择薄弱点后，可自动检索相关资料片段并注入提示词，减少模型凭空发挥。

## 新增页面

### 资料知识库

页面面向新手默认展示三步：

- 上传资料。
- 检索资料。
- 生成课程并导入训练点。

高级信息放入折叠区：

- OCR 可用性。
- 抽取文本预览。
- RAG 命中片段。
- 大模型返回原始 JSON。

## 数据模型

新增表：

### documents

- id
- filename
- file_type
- file_path
- text_content
- status
- error_message
- created_at

### document_chunks

- id
- document_id
- chunk_index
- content
- source_label
- created_at

### generated_courses

- id
- title
- source_document_id
- raw_json
- created_at

### course_lessons

- id
- course_id
- lesson_index
- title
- objective
- knowledge_points
- mistake_risks
- recommended_template
- review_plan
- imported_weak_point_id
- created_at

### rag_queries

- id
- query
- result_chunk_ids
- created_at

## 服务模块

### services/document_processor.py

职责：

- 保存上传文件。
- 根据后缀抽取文本。
- OCR 图片。
- 将长文本切成可检索块。

第一版依赖：

- `pypdf`
- `pillow`
- `pytesseract`

如果本地没有安装 Tesseract 可执行程序，图片 OCR 返回明确错误，PDF/TXT/Markdown 不受影响。

### services/rag.py

职责：

- 使用 `TfidfVectorizer` 对 chunks 建立临时索引。
- 根据 query 返回最相关文本块。
- 不在第一版持久化向量，避免复杂迁移；每次查询从 SQLite 读取 chunks 后构建轻量索引。

依赖：

- `scikit-learn`

### services/course_generator.py

职责：

- 构建课程生成 prompt。
- 调用 AIClient。
- 解析模型返回 JSON。
- 做容错解析，支持模型返回 ```json 代码块。
- 将课程保存到数据库。

输出 JSON 结构固定为：

```json
{
  "title": "课程标题",
  "lessons": [
    {
      "title": "小节标题",
      "objective": "学习目标",
      "knowledge_points": ["考点1"],
      "mistake_risks": ["易错点1"],
      "recommended_template": "构成要件追问",
      "review_plan": "复习安排"
    }
  ]
}
```

## AI 约束

课程生成提示词必须要求：

- 仅基于提供的资料片段生成。
- 不确定时标记为“资料不足”。
- 面向法硕考研表达。
- 优先输出可训练的考点，而不是泛泛摘要。
- 输出合法 JSON，不输出多余解释。

## 错误处理

- 未配置 API Key 时，上传、抽取、切块和检索仍可用；课程生成按钮显示配置提示。
- OCR 不可用时，图片上传保留原文件并显示安装提示。
- 文本抽取为空时，不创建 chunks，并提示换更清晰资料或使用 OCR。
- 模型返回非 JSON 时，在页面显示原文，并不写入课程表。
- 导入弱点时避免重复导入同一 lesson。

## 测试范围

- TXT/Markdown 抽取。
- 文本切块。
- RAG 查询排序。
- AI JSON 解析。
- 课程落库。
- lesson 导入 weak_points。
- 未配置 AI 时错误明确。
- App 页面注册 `资料知识库`。

