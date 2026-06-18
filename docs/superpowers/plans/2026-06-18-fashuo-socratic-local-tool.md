# Fashuo Socratic Local Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Streamlit app for law-master exam weak-point tracking, editable Socratic prompt templates, AI training sessions, and weekly/monthly review reports.

**Architecture:** Use Streamlit as the local UI, SQLite as the durable local store, and small service modules for storage, prompt rendering, analysis, and OpenAI-compatible model calls. Keep the app usable without an API key for weak-point entry, template management, and analytics; only the Socratic training chat requires AI configuration.

**Tech Stack:** Python 3, Streamlit, SQLite, pandas, requests, python-dotenv, pytest.

---

## File Structure

- `requirements.txt`: Python dependencies for the app and test suite.
- `.gitignore`: Ignore local database, uploads, caches, virtualenvs, and secrets.
- `README.md`: Local setup, API configuration, run commands, and workflow notes.
- `app.py`: Streamlit entrypoint and page router.
- `services/storage.py`: SQLite schema, migrations, CRUD operations, and seed-template insertion.
- `services/prompts.py`: Fixed Socratic system rules, template variable rendering, prompt snapshot construction.
- `services/analysis.py`: Weak-point statistics and Markdown weekly/monthly review generation.
- `services/ai_client.py`: OpenAI-compatible chat client and configuration errors.
- `prompts/seed_templates.py`: Six built-in editable prompt templates.
- `tests/conftest.py`: Test fixtures for isolated SQLite databases.
- `tests/test_storage.py`: Storage schema, seed data, weak-point, template, session, and message tests.
- `tests/test_prompts.py`: Prompt rendering and snapshot tests.
- `tests/test_analysis.py`: Weak-point aggregation and report-generation tests.
- `tests/test_ai_client.py`: AI client configuration and request-shaping tests with mocked HTTP.

---

### Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `README.md`
- Create: `services/__init__.py`
- Create: `prompts/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create dependency and ignore files**

Create `requirements.txt` with:

```text
streamlit>=1.36
pandas>=2.2
requests>=2.32
python-dotenv>=1.0
pytest>=8.2
```

Create `.gitignore` with:

```text
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
venv/
.env
data/fashuo.db
data/uploads/
```

- [ ] **Step 2: Create README**

Create `README.md` with:

```markdown
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
.\\.venv\\Scripts\\Activate.ps1
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
```

- [ ] **Step 3: Create package markers and pytest fixture**

Create empty `services/__init__.py` and `prompts/__init__.py`.

Create `tests/conftest.py` with:

```python
from pathlib import Path

import pytest

from services.storage import Storage


@pytest.fixture
def storage(tmp_path: Path) -> Storage:
    db_path = tmp_path / "fashuo-test.db"
    uploads_dir = tmp_path / "uploads"
    store = Storage(db_path=db_path, uploads_dir=uploads_dir)
    store.init_db()
    store.seed_templates()
    return store
```

- [ ] **Step 4: Run fixture import test to confirm expected failure**

Run:

```powershell
pytest tests/conftest.py -q
```

Expected: import failure because `services.storage.Storage` is not created yet.

- [ ] **Step 5: Commit scaffold**

```powershell
git add requirements.txt .gitignore README.md services/__init__.py prompts/__init__.py tests/conftest.py
git commit -m "chore: scaffold local fashuo app"
```

---

### Task 2: Storage Schema, Seed Templates, and CRUD

**Files:**
- Create: `prompts/seed_templates.py`
- Create: `services/storage.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write storage tests**

Create `tests/test_storage.py` with:

```python
from pathlib import Path


def test_seed_templates_are_inserted_once(storage):
    first = storage.list_templates(active_only=False)
    storage.seed_templates()
    second = storage.list_templates(active_only=False)

    assert len(first) == 6
    assert len(second) == 6
    assert {row["name"] for row in first} == {
        "概念辨析追问",
        "构成要件追问",
        "案例分析追问",
        "主观题采分追问",
        "考前速记追问",
        "错因修复追问",
    }


def test_create_weak_point_with_image_path(storage):
    weak_point_id = storage.create_weak_point(
        {
            "subject": "刑法",
            "question_type": "案例分析",
            "knowledge_point": "盗窃罪与侵占罪区分",
            "mistake_reason": "概念混淆",
            "mastery_level": "模糊",
            "image_path": "data/uploads/example.png",
            "question_text": "甲将代为保管的财物占为己有。",
            "reference_answer": "应围绕占有转移和非法占有目的分析。",
            "notes": "实体书第 23 页",
        }
    )

    row = storage.get_weak_point(weak_point_id)

    assert row["subject"] == "刑法"
    assert row["knowledge_point"] == "盗窃罪与侵占罪区分"
    assert row["image_path"] == "data/uploads/example.png"


def test_template_update_creates_new_version(storage):
    template = storage.list_templates()[0]
    new_version = storage.update_template(
        template["id"],
        {
            "name": template["name"],
            "subject_scope": "刑法",
            "question_type_scope": template["question_type_scope"],
            "body": template["body"] + "\n请加入一个反例追问。",
            "default_goal": template["default_goal"],
            "end_condition": template["end_condition"],
            "is_active": True,
        },
    )

    updated = storage.get_template(template["id"])
    versions = storage.list_template_versions(template["id"])

    assert new_version == 2
    assert updated["current_version"] == 2
    assert len(versions) == 2
    assert "反例追问" in versions[-1]["body"]


def test_training_session_messages_and_finish(storage):
    weak_point_id = storage.create_weak_point(
        {
            "subject": "民法",
            "question_type": "单选",
            "knowledge_point": "表见代理",
            "mistake_reason": "要件遗漏",
            "mastery_level": "陌生",
            "image_path": "",
            "question_text": "",
            "reference_answer": "",
            "notes": "",
        }
    )
    template = storage.list_templates()[0]
    session_id = storage.create_session(
        weak_point_id=weak_point_id,
        template_id=template["id"],
        template_version=template["current_version"],
        prompt_snapshot="系统规则 + 模板正文",
        mastery_before="陌生",
    )

    storage.add_message(session_id, "assistant", "表见代理首先要保护谁的信赖？")
    storage.add_message(session_id, "user", "保护相对人的合理信赖。")
    storage.finish_session(
        session_id,
        mastery_after="基本会",
        summary="能说出核心保护对象，但构成要件还不完整。",
        exposed_issues="遗漏权利外观和本人可归责性。",
        next_review_suggestion="2 天后用构成要件追问模板复习。",
    )

    session = storage.get_session(session_id)
    messages = storage.list_messages(session_id)

    assert session["status"] == "finished"
    assert session["mastery_after"] == "基本会"
    assert len(messages) == 2
    assert messages[0]["role"] == "assistant"
```

- [ ] **Step 2: Run storage tests to verify failure**

Run:

```powershell
pytest tests/test_storage.py -q
```

Expected: FAIL because `prompts.seed_templates` and `services.storage` do not exist.

- [ ] **Step 3: Create built-in template data**

Create `prompts/seed_templates.py` with a `SEED_TEMPLATES` list of six dictionaries:

```python
SEED_TEMPLATES = [
    {
        "name": "概念辨析追问",
        "subject_scope": "通用",
        "question_type_scope": "单选,多选,简答,案例分析",
        "body": """当前科目：{subject}
当前考点：{knowledge_point}
错因：{mistake_reason}

请围绕这个易混概念连续追问。先让学生分别给出两个概念的定义，再追问区别标准、典型陷阱和案例判断。每次只问一个问题，不要一次性给答案。""",
        "default_goal": "让学生能清楚区分易混概念，并能在案例事实中正确适用。",
        "end_condition": "学生能独立说出定义、区别标准、反例和考试表达。",
    },
    {
        "name": "构成要件追问",
        "subject_scope": "通用",
        "question_type_scope": "单选,多选,简答,论述,案例分析",
        "body": """当前科目：{subject}
当前考点：{knowledge_point}
掌握度：{mastery_level}

请按构成要件展开追问。先问定义，再问主体、客体或权利基础、主观方面、客观方面、法律效果和例外。学生答不全时，把问题拆小。""",
        "default_goal": "让学生能按考试需要完整拆出构成要件。",
        "end_condition": "学生能不看答案说出主要要件，并能解释每个要件的作用。",
    },
    {
        "name": "案例分析追问",
        "subject_scope": "通用",
        "question_type_scope": "案例分析,单选,多选",
        "body": """题干：{question_text}
参考答案：{reference_answer}

请把题干拆成事实、争点、规则、适用、结论五步追问。不要先给结论，先让学生识别关键事实。""",
        "default_goal": "训练从事实到法律规则再到结论的分析路径。",
        "end_condition": "学生能独立完成事实筛选、争点定位、规则适用和结论表达。",
    },
    {
        "name": "主观题采分追问",
        "subject_scope": "通用",
        "question_type_scope": "简答,论述,案例分析",
        "body": """当前考点：{knowledge_point}
参考答案：{reference_answer}

请按法硕主观题采分逻辑追问：定义、要件、展开、适用、结论。先让学生口述答案，再指出缺失采分点，并继续追问补齐。""",
        "default_goal": "让学生形成能拿分的主观题表达结构。",
        "end_condition": "学生能给出结构完整、术语准确、结论明确的答案。",
    },
    {
        "name": "考前速记追问",
        "subject_scope": "通用",
        "question_type_scope": "单选,多选,简答,论述",
        "body": """当前科目：{subject}
当前考点：{knowledge_point}
近期薄弱点：{recent_weaknesses}

请用高频短问答检查背诵漏洞。每个问题应短、准、可立即回答。学生答错时给一个记忆钩子，然后继续问。""",
        "default_goal": "快速暴露背诵漏洞并形成短时复习清单。",
        "end_condition": "学生连续正确回答 5 个关键短问。",
    },
    {
        "name": "错因修复追问",
        "subject_scope": "通用",
        "question_type_scope": "通用",
        "body": """错因：{mistake_reason}
当前考点：{knowledge_point}
学生备注：{notes}

请专门围绕错因追问。先让学生复盘为什么错，再追问正确判断路径，最后让学生用一句话写出防错规则。""",
        "default_goal": "把一次错误转化成可复用的防错规则。",
        "end_condition": "学生能说出错误原因、正确路径和防错提醒。",
    },
]
```

- [ ] **Step 4: Implement `Storage`**

Create `services/storage.py` with:

```python
from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from prompts.seed_templates import SEED_TEMPLATES


class Storage:
    def __init__(self, db_path: Path | str = "data/fashuo.db", uploads_dir: Path | str = "data/uploads"):
        self.db_path = Path(db_path)
        self.uploads_dir = Path(uploads_dir)

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS weak_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    question_type TEXT NOT NULL,
                    knowledge_point TEXT NOT NULL,
                    mistake_reason TEXT NOT NULL,
                    mastery_level TEXT NOT NULL,
                    image_path TEXT NOT NULL DEFAULT '',
                    question_text TEXT NOT NULL DEFAULT '',
                    reference_answer TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    subject_scope TEXT NOT NULL,
                    question_type_scope TEXT NOT NULL,
                    body TEXT NOT NULL,
                    default_goal TEXT NOT NULL,
                    end_condition TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    current_version INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS template_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id INTEGER NOT NULL,
                    version INTEGER NOT NULL,
                    body TEXT NOT NULL,
                    default_goal TEXT NOT NULL,
                    end_condition TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(template_id, version),
                    FOREIGN KEY(template_id) REFERENCES templates(id)
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    weak_point_id INTEGER NOT NULL,
                    template_id INTEGER NOT NULL,
                    template_version INTEGER NOT NULL,
                    prompt_snapshot TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT NOT NULL DEFAULT '',
                    mastery_before TEXT NOT NULL,
                    mastery_after TEXT NOT NULL DEFAULT '',
                    summary TEXT NOT NULL DEFAULT '',
                    exposed_issues TEXT NOT NULL DEFAULT '',
                    next_review_suggestion TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY(weak_point_id) REFERENCES weak_points(id),
                    FOREIGN KEY(template_id) REFERENCES templates(id)
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );
                """
            )

    def seed_templates(self) -> None:
        now = self._now()
        with self.connect() as conn:
            for template in SEED_TEMPLATES:
                exists = conn.execute("SELECT id FROM templates WHERE name = ?", (template["name"],)).fetchone()
                if exists:
                    continue
                cur = conn.execute(
                    """
                    INSERT INTO templates
                    (name, subject_scope, question_type_scope, body, default_goal, end_condition, is_active, current_version, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
                    """,
                    (
                        template["name"],
                        template["subject_scope"],
                        template["question_type_scope"],
                        template["body"],
                        template["default_goal"],
                        template["end_condition"],
                        now,
                        now,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO template_versions
                    (template_id, version, body, default_goal, end_condition, created_at)
                    VALUES (?, 1, ?, ?, ?, ?)
                    """,
                    (cur.lastrowid, template["body"], template["default_goal"], template["end_condition"], now),
                )

    def save_upload(self, uploaded_file: Any) -> str:
        if uploaded_file is None:
            return ""
        suffix = Path(uploaded_file.name).suffix or ".png"
        target = self.uploads_dir / f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}{suffix}"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            shutil.copyfileobj(uploaded_file, handle)
        return str(target)

    def create_weak_point(self, payload: dict[str, Any]) -> int:
        now = self._now()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO weak_points
                (subject, question_type, knowledge_point, mistake_reason, mastery_level, image_path, question_text, reference_answer, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["subject"],
                    payload["question_type"],
                    payload["knowledge_point"],
                    payload["mistake_reason"],
                    payload["mastery_level"],
                    payload.get("image_path", ""),
                    payload.get("question_text", ""),
                    payload.get("reference_answer", ""),
                    payload.get("notes", ""),
                    now,
                    now,
                ),
            )
            return int(cur.lastrowid)

    def list_weak_points(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM weak_points ORDER BY created_at DESC").fetchall()
            return [self._dict(row) for row in rows]

    def get_weak_point(self, weak_point_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM weak_points WHERE id = ?", (weak_point_id,)).fetchone()
            if row is None:
                raise KeyError(f"weak point not found: {weak_point_id}")
            return self._dict(row)

    def list_templates(self, active_only: bool = True) -> list[dict[str, Any]]:
        query = "SELECT * FROM templates"
        params: tuple[Any, ...] = ()
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY name"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._dict(row) for row in rows]

    def get_template(self, template_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM templates WHERE id = ?", (template_id,)).fetchone()
            if row is None:
                raise KeyError(f"template not found: {template_id}")
            return self._dict(row)

    def create_template(self, payload: dict[str, Any]) -> int:
        now = self._now()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO templates
                (name, subject_scope, question_type_scope, body, default_goal, end_condition, is_active, current_version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    payload["name"],
                    payload["subject_scope"],
                    payload["question_type_scope"],
                    payload["body"],
                    payload["default_goal"],
                    payload["end_condition"],
                    1 if payload.get("is_active", True) else 0,
                    now,
                    now,
                ),
            )
            template_id = int(cur.lastrowid)
            conn.execute(
                """
                INSERT INTO template_versions
                (template_id, version, body, default_goal, end_condition, created_at)
                VALUES (?, 1, ?, ?, ?, ?)
                """,
                (template_id, payload["body"], payload["default_goal"], payload["end_condition"], now),
            )
            return template_id

    def update_template(self, template_id: int, payload: dict[str, Any]) -> int:
        current = self.get_template(template_id)
        new_version = int(current["current_version"]) + 1
        now = self._now()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE templates
                SET name = ?, subject_scope = ?, question_type_scope = ?, body = ?, default_goal = ?,
                    end_condition = ?, is_active = ?, current_version = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    payload["name"],
                    payload["subject_scope"],
                    payload["question_type_scope"],
                    payload["body"],
                    payload["default_goal"],
                    payload["end_condition"],
                    1 if payload.get("is_active", True) else 0,
                    new_version,
                    now,
                    template_id,
                ),
            )
            conn.execute(
                """
                INSERT INTO template_versions
                (template_id, version, body, default_goal, end_condition, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (template_id, new_version, payload["body"], payload["default_goal"], payload["end_condition"], now),
            )
            return new_version

    def list_template_versions(self, template_id: int) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM template_versions WHERE template_id = ? ORDER BY version",
                (template_id,),
            ).fetchall()
            return [self._dict(row) for row in rows]

    def create_session(
        self,
        weak_point_id: int,
        template_id: int,
        template_version: int,
        prompt_snapshot: str,
        mastery_before: str,
    ) -> int:
        now = self._now()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO sessions
                (weak_point_id, template_id, template_version, prompt_snapshot, status, started_at, mastery_before)
                VALUES (?, ?, ?, ?, 'active', ?, ?)
                """,
                (weak_point_id, template_id, template_version, prompt_snapshot, now, mastery_before),
            )
            return int(cur.lastrowid)

    def get_session(self, session_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row is None:
                raise KeyError(f"session not found: {session_id}")
            return self._dict(row)

    def list_sessions(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM sessions ORDER BY started_at DESC").fetchall()
            return [self._dict(row) for row in rows]

    def add_message(self, session_id: int, role: str, content: str) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO messages (session_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, role, content, self._now()),
            )
            return int(cur.lastrowid)

    def list_messages(self, session_id: int) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
            return [self._dict(row) for row in rows]

    def finish_session(
        self,
        session_id: int,
        mastery_after: str,
        summary: str,
        exposed_issues: str,
        next_review_suggestion: str,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET status = 'finished', ended_at = ?, mastery_after = ?, summary = ?,
                    exposed_issues = ?, next_review_suggestion = ?
                WHERE id = ?
                """,
                (self._now(), mastery_after, summary, exposed_issues, next_review_suggestion, session_id),
            )

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat(timespec="seconds")

    @staticmethod
    def _dict(row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)
```

- [ ] **Step 5: Run storage tests**

Run:

```powershell
pytest tests/test_storage.py -q
```

Expected: `4 passed`.

- [ ] **Step 6: Commit storage layer**

```powershell
git add prompts/seed_templates.py services/storage.py tests/test_storage.py
git commit -m "feat: add local storage and seed templates"
```

---

### Task 3: Prompt Rendering Service

**Files:**
- Create: `services/prompts.py`
- Create: `tests/test_prompts.py`

- [ ] **Step 1: Write prompt tests**

Create `tests/test_prompts.py` with:

```python
from services.prompts import SYSTEM_RULES, build_training_prompt, render_template


def test_render_template_replaces_known_variables_and_blanks_missing_values():
    body = "科目：{subject}\n考点：{knowledge_point}\n备注：{missing_value}"
    rendered = render_template(
        body,
        {
            "subject": "刑法",
            "knowledge_point": "共同犯罪",
        },
    )

    assert "科目：刑法" in rendered
    assert "考点：共同犯罪" in rendered
    assert "备注：" in rendered
    assert "{missing_value}" not in rendered


def test_build_training_prompt_includes_rules_template_and_context(storage):
    weak_point_id = storage.create_weak_point(
        {
            "subject": "宪法",
            "question_type": "简答",
            "knowledge_point": "宪法监督",
            "mistake_reason": "记忆不牢",
            "mastery_level": "模糊",
            "image_path": "",
            "question_text": "",
            "reference_answer": "",
            "notes": "容易漏掉主体",
        }
    )
    weak_point = storage.get_weak_point(weak_point_id)
    template = storage.list_templates()[0]

    prompt = build_training_prompt(
        weak_point=weak_point,
        template=template,
        student_goal="考前快速补齐采分点",
        recent_weaknesses=["宪法监督", "法律解释"],
        prompt_override=None,
    )

    assert SYSTEM_RULES in prompt
    assert "宪法监督" in prompt
    assert "考前快速补齐采分点" in prompt
    assert "法律解释" in prompt
    assert template["default_goal"] in prompt


def test_build_training_prompt_uses_override_body(storage):
    weak_point = storage.get_weak_point(
        storage.create_weak_point(
            {
                "subject": "民法",
                "question_type": "单选",
                "knowledge_point": "无权代理",
                "mistake_reason": "要件遗漏",
                "mastery_level": "陌生",
                "image_path": "",
                "question_text": "",
                "reference_answer": "",
                "notes": "",
            }
        )
    )
    template = storage.list_templates()[0]

    prompt = build_training_prompt(
        weak_point=weak_point,
        template=template,
        student_goal="只追问构成要件",
        recent_weaknesses=[],
        prompt_override="请先问本人可归责性是什么。",
    )

    assert "请先问本人可归责性是什么。" in prompt
    assert template["body"] not in prompt
```

- [ ] **Step 2: Run prompt tests to verify failure**

Run:

```powershell
pytest tests/test_prompts.py -q
```

Expected: FAIL because `services.prompts` does not exist.

- [ ] **Step 3: Implement prompt rendering**

Create `services/prompts.py` with:

```python
from __future__ import annotations

import re
from typing import Any


SYSTEM_RULES = """你是法硕考研苏格拉底式导师。
目标是通过连续追问帮助学生掌握考点，而不是直接灌输答案。
每次只问一个问题。
不要一次性给完整解析。
学生回答后，先判断回答质量，再决定追问、提示、纠错或提高难度。
训练内容必须围绕法硕考试表达、考点辨析、案例适用和主观题采分点。"""


VARIABLE_PATTERN = re.compile(r"{([a-zA-Z_][a-zA-Z0-9_]*)}")


def render_template(body: str, values: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        value = values.get(match.group(1), "")
        if isinstance(value, list):
            return "、".join(str(item) for item in value)
        return str(value)

    return VARIABLE_PATTERN.sub(replace, body)


def build_training_prompt(
    weak_point: dict[str, Any],
    template: dict[str, Any],
    student_goal: str,
    recent_weaknesses: list[str],
    prompt_override: str | None,
) -> str:
    values = {
        "subject": weak_point.get("subject", ""),
        "question_type": weak_point.get("question_type", ""),
        "knowledge_point": weak_point.get("knowledge_point", ""),
        "mistake_reason": weak_point.get("mistake_reason", ""),
        "mastery_level": weak_point.get("mastery_level", ""),
        "question_text": weak_point.get("question_text", ""),
        "reference_answer": weak_point.get("reference_answer", ""),
        "notes": weak_point.get("notes", ""),
        "student_goal": student_goal,
        "recent_weaknesses": recent_weaknesses,
    }
    body = prompt_override if prompt_override is not None else template.get("body", "")
    rendered_body = render_template(body, values)
    return "\n\n".join(
        [
            SYSTEM_RULES,
            "【本次训练目标】\n" + (student_goal or template.get("default_goal", "")),
            "【结束条件】\n" + template.get("end_condition", ""),
            "【薄弱点信息】\n"
            + f"科目：{values['subject']}\n"
            + f"题型：{values['question_type']}\n"
            + f"考点：{values['knowledge_point']}\n"
            + f"错因：{values['mistake_reason']}\n"
            + f"掌握度：{values['mastery_level']}\n"
            + f"近期薄弱点：{render_template('{recent_weaknesses}', values)}",
            "【追问模板】\n" + rendered_body,
            "请先提出第一个问题。问题必须具体、短小，并且只包含一个问点。",
        ]
    )
```

- [ ] **Step 4: Run prompt tests**

Run:

```powershell
pytest tests/test_prompts.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit prompt service**

```powershell
git add services/prompts.py tests/test_prompts.py
git commit -m "feat: add Socratic prompt rendering"
```

---

### Task 4: Weak-Point Analysis and Review Reports

**Files:**
- Create: `services/analysis.py`
- Create: `tests/test_analysis.py`

- [ ] **Step 1: Write analysis tests**

Create `tests/test_analysis.py` with:

```python
from services.analysis import build_review_report, compute_weak_point_stats


def _create_sample_weak_points(storage):
    for payload in [
        {
            "subject": "刑法",
            "question_type": "案例分析",
            "knowledge_point": "共同犯罪",
            "mistake_reason": "要件遗漏",
            "mastery_level": "模糊",
            "image_path": "",
            "question_text": "",
            "reference_answer": "",
            "notes": "",
        },
        {
            "subject": "刑法",
            "question_type": "单选",
            "knowledge_point": "共同犯罪",
            "mistake_reason": "概念混淆",
            "mastery_level": "陌生",
            "image_path": "",
            "question_text": "",
            "reference_answer": "",
            "notes": "",
        },
        {
            "subject": "民法",
            "question_type": "多选",
            "knowledge_point": "表见代理",
            "mistake_reason": "要件遗漏",
            "mastery_level": "基本会",
            "image_path": "",
            "question_text": "",
            "reference_answer": "",
            "notes": "",
        },
    ]:
        storage.create_weak_point(payload)


def test_compute_weak_point_stats_groups_by_subject_point_and_reason(storage):
    _create_sample_weak_points(storage)

    stats = compute_weak_point_stats(storage.list_weak_points(), storage.list_sessions())

    assert stats["total_weak_points"] == 3
    assert stats["by_subject"][0]["subject"] == "刑法"
    assert stats["by_subject"][0]["count"] == 2
    assert stats["by_knowledge_point"][0]["knowledge_point"] == "共同犯罪"
    assert stats["by_knowledge_point"][0]["count"] == 2
    assert stats["by_mistake_reason"][0]["mistake_reason"] == "要件遗漏"
    assert stats["by_mistake_reason"][0]["count"] == 2


def test_review_report_mentions_priorities_and_training_recommendations(storage):
    _create_sample_weak_points(storage)

    report = build_review_report(
        period_label="本周",
        weak_points=storage.list_weak_points(),
        sessions=storage.list_sessions(),
    )

    assert "# 本周复盘" in report
    assert "共同犯罪" in report
    assert "要件遗漏" in report
    assert "建议优先训练" in report
```

- [ ] **Step 2: Run analysis tests to verify failure**

Run:

```powershell
pytest tests/test_analysis.py -q
```

Expected: FAIL because `services.analysis` does not exist.

- [ ] **Step 3: Implement analysis service**

Create `services/analysis.py` with:

```python
from __future__ import annotations

from collections import Counter
from typing import Any


MASTERY_RISK = {
    "陌生": 4,
    "模糊": 3,
    "基本会": 2,
    "熟练": 1,
}


def compute_weak_point_stats(
    weak_points: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
) -> dict[str, Any]:
    subject_counter = Counter(row["subject"] for row in weak_points)
    point_counter = Counter(row["knowledge_point"] for row in weak_points)
    reason_counter = Counter(row["mistake_reason"] for row in weak_points)
    low_mastery = [
        row
        for row in weak_points
        if MASTERY_RISK.get(row.get("mastery_level", ""), 0) >= 3
    ]
    finished_sessions = [row for row in sessions if row.get("status") == "finished"]

    return {
        "total_weak_points": len(weak_points),
        "total_sessions": len(sessions),
        "finished_sessions": len(finished_sessions),
        "by_subject": _counter_rows(subject_counter, "subject"),
        "by_knowledge_point": _counter_rows(point_counter, "knowledge_point"),
        "by_mistake_reason": _counter_rows(reason_counter, "mistake_reason"),
        "low_mastery": sorted(
            low_mastery,
            key=lambda row: (MASTERY_RISK.get(row.get("mastery_level", ""), 0), row["created_at"]),
            reverse=True,
        ),
    }


def build_review_report(
    period_label: str,
    weak_points: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
) -> str:
    stats = compute_weak_point_stats(weak_points, sessions)
    top_points = stats["by_knowledge_point"][:5]
    top_reasons = stats["by_mistake_reason"][:5]
    low_mastery = stats["low_mastery"][:5]

    lines = [
        f"# {period_label}复盘",
        "",
        "## 学习概况",
        f"- 新增/累计薄弱点：{stats['total_weak_points']} 个",
        f"- 苏格拉底训练：{stats['total_sessions']} 次，其中已完成 {stats['finished_sessions']} 次",
        "",
        "## 高频薄弱考点",
    ]
    lines.extend(_bullet_rows(top_points, "knowledge_point"))
    lines.extend(["", "## 高频错因"])
    lines.extend(_bullet_rows(top_reasons, "mistake_reason"))
    lines.extend(["", "## 建议优先训练"])
    if low_mastery:
        for row in low_mastery:
            lines.append(
                f"- {row['subject']}｜{row['knowledge_point']}｜掌握度：{row['mastery_level']}｜建议使用：错因修复追问或构成要件追问"
            )
    else:
        lines.append("- 暂无低掌握度考点，建议选择最近新增错题进行巩固追问。")
    lines.extend(
        [
            "",
            "## 下阶段计划",
            "- 每天至少选择 1 个低掌握度考点完成一次苏格拉底训练。",
            "- 对出现 2 次及以上的考点，优先使用概念辨析追问或案例分析追问。",
            "- 对主观题相关错因，训练结束后补写一版完整采分表达。",
        ]
    )
    return "\n".join(lines)


def _counter_rows(counter: Counter[str], key: str) -> list[dict[str, Any]]:
    return [
        {key: name, "count": count}
        for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def _bullet_rows(rows: list[dict[str, Any]], key: str) -> list[str]:
    if not rows:
        return ["- 暂无记录。"]
    return [f"- {row[key]}：{row['count']} 次" for row in rows]
```

- [ ] **Step 4: Run analysis tests**

Run:

```powershell
pytest tests/test_analysis.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit analysis service**

```powershell
git add services/analysis.py tests/test_analysis.py
git commit -m "feat: add weak point analysis reports"
```

---

### Task 5: OpenAI-Compatible AI Client

**Files:**
- Create: `services/ai_client.py`
- Create: `tests/test_ai_client.py`

- [ ] **Step 1: Write AI client tests**

Create `tests/test_ai_client.py` with:

```python
import pytest

from services.ai_client import AIClient, AIConfigurationError


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.text)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def post(self, url, headers, json, timeout):
        self.calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse({"choices": [{"message": {"content": "第一个问题：构成要件是什么？"}}]})


def test_missing_api_key_raises_configuration_error():
    client = AIClient(api_base="https://api.example.com/v1", api_key="", model="test-model")

    with pytest.raises(AIConfigurationError):
        client.chat([{"role": "user", "content": "hello"}])


def test_chat_sends_openai_compatible_request():
    session = FakeSession()
    client = AIClient(
        api_base="https://api.example.com/v1",
        api_key="key-123",
        model="test-model",
        http_session=session,
    )

    content = client.chat([{"role": "user", "content": "请开始追问"}])

    assert content == "第一个问题：构成要件是什么？"
    assert session.calls[0]["url"] == "https://api.example.com/v1/chat/completions"
    assert session.calls[0]["headers"]["Authorization"] == "Bearer key-123"
    assert session.calls[0]["json"]["model"] == "test-model"
    assert session.calls[0]["json"]["messages"][0]["content"] == "请开始追问"
```

- [ ] **Step 2: Run AI client tests to verify failure**

Run:

```powershell
pytest tests/test_ai_client.py -q
```

Expected: FAIL because `services.ai_client` does not exist.

- [ ] **Step 3: Implement AI client**

Create `services/ai_client.py` with:

```python
from __future__ import annotations

from typing import Any

import requests


class AIConfigurationError(RuntimeError):
    pass


class AIClient:
    def __init__(
        self,
        api_base: str,
        api_key: str,
        model: str,
        http_session: Any | None = None,
        timeout: int = 60,
    ):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.http_session = http_session or requests.Session()
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.api_base and self.api_key and self.model)

    def chat(self, messages: list[dict[str, str]]) -> str:
        if not self.is_configured():
            raise AIConfigurationError("请先在侧边栏配置 API Base、Model 和 API Key。")

        response = self.http_session.post(
            f"{self.api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.4,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]
```

- [ ] **Step 4: Run AI client tests**

Run:

```powershell
pytest tests/test_ai_client.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit AI client**

```powershell
git add services/ai_client.py tests/test_ai_client.py
git commit -m "feat: add OpenAI compatible AI client"
```

---

### Task 6: Streamlit Application

**Files:**
- Create: `app.py`
- Modify: `services/storage.py`

- [ ] **Step 1: Add template-copy storage helper**

Add this method to `Storage` in `services/storage.py`:

```python
    def copy_template(self, template_id: int, new_name: str) -> int:
        template = self.get_template(template_id)
        return self.create_template(
            {
                "name": new_name,
                "subject_scope": template["subject_scope"],
                "question_type_scope": template["question_type_scope"],
                "body": template["body"],
                "default_goal": template["default_goal"],
                "end_condition": template["end_condition"],
                "is_active": True,
            }
        )
```

Add this test to `tests/test_storage.py`:

```python
def test_copy_template_creates_independent_template(storage):
    template = storage.list_templates()[0]

    copied_id = storage.copy_template(template["id"], template["name"] + " 副本")
    copied = storage.get_template(copied_id)

    assert copied["name"].endswith("副本")
    assert copied["body"] == template["body"]
    assert copied["id"] != template["id"]
```

Run:

```powershell
pytest tests/test_storage.py -q
```

Expected: `5 passed`.

- [ ] **Step 2: Create Streamlit app**

Create `app.py` with these top-level constants and initialization functions:

```python
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from services.ai_client import AIClient, AIConfigurationError
from services.analysis import build_review_report, compute_weak_point_stats
from services.prompts import build_training_prompt
from services.storage import Storage


SUBJECTS = ["刑法", "民法", "法理", "宪法", "法制史"]
QUESTION_TYPES = ["单选", "多选", "简答", "论述", "案例分析"]
MISTAKE_REASONS = ["概念混淆", "要件遗漏", "法条不熟", "案例事实误判", "记忆不牢", "表达不规范"]
MASTERY_LEVELS = ["陌生", "模糊", "基本会", "熟练"]


@st.cache_resource
def get_storage() -> Storage:
    store = Storage()
    store.init_db()
    store.seed_templates()
    return store


def get_ai_client() -> AIClient:
    return AIClient(
        api_base=st.session_state.get("api_base", ""),
        api_key=st.session_state.get("api_key", ""),
        model=st.session_state.get("model", ""),
    )


def main() -> None:
    st.set_page_config(page_title="法硕苏格拉底学习器", layout="wide")
    store = get_storage()
    render_sidebar()
    page = st.sidebar.radio(
        "页面",
        ["今日学习", "错题/薄弱点录入", "苏格拉底训练", "模板管理", "薄弱点分析", "周度/月度复盘"],
    )

    if page == "今日学习":
        page_today(store)
    elif page == "错题/薄弱点录入":
        page_entry(store)
    elif page == "苏格拉底训练":
        page_training(store)
    elif page == "模板管理":
        page_templates(store)
    elif page == "薄弱点分析":
        page_analysis(store)
    else:
        page_review(store)
```

Add page functions in the same file. Keep `app.py` as the only Streamlit file for the first version.

- [ ] **Step 3: Implement sidebar and today page**

Add:

```python
def render_sidebar() -> None:
    st.sidebar.header("AI 配置")
    st.session_state["api_base"] = st.sidebar.text_input(
        "API Base",
        value=st.session_state.get("api_base", "https://api.openai.com/v1"),
    )
    st.session_state["model"] = st.sidebar.text_input(
        "Model",
        value=st.session_state.get("model", "gpt-4.1-mini"),
    )
    st.session_state["api_key"] = st.sidebar.text_input(
        "API Key",
        value=st.session_state.get("api_key", ""),
        type="password",
    )


def page_today(store: Storage) -> None:
    st.title("今日学习")
    weak_points = store.list_weak_points()
    sessions = store.list_sessions()
    stats = compute_weak_point_stats(weak_points, sessions)

    col1, col2, col3 = st.columns(3)
    col1.metric("薄弱点", stats["total_weak_points"])
    col2.metric("训练次数", stats["total_sessions"])
    col3.metric("完成训练", stats["finished_sessions"])

    st.subheader("建议优先处理")
    for row in stats["low_mastery"][:5]:
        st.write(f"- {row['subject']}｜{row['knowledge_point']}｜{row['mistake_reason']}｜{row['mastery_level']}")

    if not weak_points:
        st.info("先录入一个错题或薄弱点，再开始苏格拉底训练。")
```

- [ ] **Step 4: Implement weak-point entry page**

Add:

```python
def page_entry(store: Storage) -> None:
    st.title("错题/薄弱点录入")
    with st.form("weak_point_form", clear_on_submit=True):
        uploaded_file = st.file_uploader("错题照片", type=["png", "jpg", "jpeg", "webp"])
        subject = st.selectbox("科目", SUBJECTS)
        question_type = st.selectbox("题型", QUESTION_TYPES)
        knowledge_point = st.text_input("考点")
        mistake_reason = st.selectbox("错因", MISTAKE_REASONS)
        mastery_level = st.selectbox("掌握度", MASTERY_LEVELS)
        question_text = st.text_area("题干，可选", height=120)
        reference_answer = st.text_area("参考答案，可选", height=120)
        notes = st.text_area("备注，可选", height=80)
        submitted = st.form_submit_button("保存薄弱点")

    if submitted:
        if not knowledge_point.strip():
            st.error("考点不能为空。")
            return
        image_path = store.save_upload(uploaded_file) if uploaded_file else ""
        weak_point_id = store.create_weak_point(
            {
                "subject": subject,
                "question_type": question_type,
                "knowledge_point": knowledge_point.strip(),
                "mistake_reason": mistake_reason,
                "mastery_level": mastery_level,
                "image_path": image_path,
                "question_text": question_text,
                "reference_answer": reference_answer,
                "notes": notes,
            }
        )
        st.success(f"已保存薄弱点 #{weak_point_id}")
```

- [ ] **Step 5: Implement template management page**

Add:

```python
def page_templates(store: Storage) -> None:
    st.title("模板管理")
    templates = store.list_templates(active_only=False)
    if templates:
        selected = st.selectbox("选择模板", templates, format_func=lambda row: f"{row['name']} v{row['current_version']}")
        with st.form("template_edit_form"):
            name = st.text_input("模板名称", value=selected["name"])
            subject_scope = st.text_input("适用科目", value=selected["subject_scope"])
            question_type_scope = st.text_input("适用题型", value=selected["question_type_scope"])
            body = st.text_area("模板正文", value=selected["body"], height=260)
            default_goal = st.text_area("默认训练目标", value=selected["default_goal"], height=80)
            end_condition = st.text_area("结束条件", value=selected["end_condition"], height=80)
            is_active = st.checkbox("启用", value=bool(selected["is_active"]))
            save = st.form_submit_button("保存新版本")
        if save:
            store.update_template(
                selected["id"],
                {
                    "name": name,
                    "subject_scope": subject_scope,
                    "question_type_scope": question_type_scope,
                    "body": body,
                    "default_goal": default_goal,
                    "end_condition": end_condition,
                    "is_active": is_active,
                },
            )
            st.success("已保存模板新版本。")

        copy_name = st.text_input("复制为新模板名称", value=f"{selected['name']} 副本")
        if st.button("复制模板"):
            store.copy_template(selected["id"], copy_name)
            st.success("已复制模板。")

    st.subheader("新建模板")
    with st.form("template_create_form"):
        new_name = st.text_input("新模板名称")
        new_body = st.text_area("新模板正文", height=180)
        create = st.form_submit_button("创建模板")
    if create:
        if not new_name.strip() or not new_body.strip():
            st.error("模板名称和正文不能为空。")
            return
        store.create_template(
            {
                "name": new_name.strip(),
                "subject_scope": "通用",
                "question_type_scope": "通用",
                "body": new_body,
                "default_goal": "通过连续追问修复薄弱点。",
                "end_condition": "学生能独立说出正确路径。",
                "is_active": True,
            }
        )
        st.success("已创建模板。")
```

- [ ] **Step 6: Implement Socratic training page**

Add:

```python
def page_training(store: Storage) -> None:
    st.title("苏格拉底训练")
    weak_points = store.list_weak_points()
    templates = store.list_templates()
    if not weak_points:
        st.info("请先录入错题或薄弱点。")
        return
    if not templates:
        st.warning("没有启用中的模板，请先在模板管理中启用模板。")
        return

    weak_point = st.selectbox(
        "选择薄弱点",
        weak_points,
        format_func=lambda row: f"{row['subject']}｜{row['knowledge_point']}｜{row['mastery_level']}",
    )
    template = st.selectbox("选择追问模板", templates, format_func=lambda row: row["name"])
    student_goal = st.text_input("本次训练目标", value=template["default_goal"])
    prompt_override = st.text_area("本次提示词，可临时修改", value=template["body"], height=220)
    recent_weaknesses = [row["knowledge_point"] for row in weak_points[:5]]
    prompt_snapshot = build_training_prompt(
        weak_point=weak_point,
        template=template,
        student_goal=student_goal,
        recent_weaknesses=recent_weaknesses,
        prompt_override=prompt_override,
    )

    with st.expander("预览本次完整提示词"):
        st.code(prompt_snapshot)

    if "active_session_id" not in st.session_state:
        st.session_state["active_session_id"] = None

    if st.button("开始训练"):
        session_id = store.create_session(
            weak_point_id=weak_point["id"],
            template_id=template["id"],
            template_version=template["current_version"],
            prompt_snapshot=prompt_snapshot,
            mastery_before=weak_point["mastery_level"],
        )
        st.session_state["active_session_id"] = session_id
        try:
            reply = get_ai_client().chat([{"role": "system", "content": prompt_snapshot}])
            store.add_message(session_id, "assistant", reply)
        except AIConfigurationError as exc:
            st.warning(str(exc))
        except Exception as exc:
            st.error(f"AI 调用失败：{exc}")

    session_id = st.session_state.get("active_session_id")
    if not session_id:
        return

    messages = store.list_messages(session_id)
    for message in messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    user_input = st.chat_input("回答上一个问题")
    if user_input:
        store.add_message(session_id, "user", user_input)
        history = [{"role": "system", "content": store.get_session(session_id)["prompt_snapshot"]}]
        history.extend({"role": msg["role"], "content": msg["content"]} for msg in store.list_messages(session_id))
        try:
            reply = get_ai_client().chat(history)
            store.add_message(session_id, "assistant", reply)
            st.rerun()
        except AIConfigurationError as exc:
            st.warning(str(exc))
        except Exception as exc:
            st.error(f"AI 调用失败：{exc}")

    with st.form("finish_session_form"):
        mastery_after = st.selectbox("训练后掌握度", MASTERY_LEVELS, index=2)
        summary = st.text_area("训练总结", height=80)
        exposed_issues = st.text_area("暴露问题", height=80)
        next_review_suggestion = st.text_area("下次复习建议", height=80)
        finish = st.form_submit_button("结束训练")
    if finish:
        store.finish_session(session_id, mastery_after, summary, exposed_issues, next_review_suggestion)
        st.session_state["active_session_id"] = None
        st.success("训练已结束并保存。")
```

- [ ] **Step 7: Implement analysis and review pages**

Add:

```python
def page_analysis(store: Storage) -> None:
    st.title("薄弱点分析")
    weak_points = store.list_weak_points()
    sessions = store.list_sessions()
    stats = compute_weak_point_stats(weak_points, sessions)

    if not weak_points:
        st.info("暂无薄弱点记录。")
        return

    st.subheader("按科目")
    st.dataframe(pd.DataFrame(stats["by_subject"]), use_container_width=True)
    st.subheader("按考点")
    st.dataframe(pd.DataFrame(stats["by_knowledge_point"]), use_container_width=True)
    st.subheader("按错因")
    st.dataframe(pd.DataFrame(stats["by_mistake_reason"]), use_container_width=True)
    st.subheader("低掌握度优先清单")
    st.dataframe(pd.DataFrame(stats["low_mastery"]), use_container_width=True)


def page_review(store: Storage) -> None:
    st.title("周度/月度复盘")
    period = st.radio("复盘周期", ["本周", "本月"], horizontal=True)
    report = build_review_report(period, store.list_weak_points(), store.list_sessions())
    st.markdown(report)
    st.download_button(
        "下载 Markdown",
        data=report.encode("utf-8"),
        file_name=f"{period}复盘.md",
        mime="text/markdown",
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 8: Run tests and syntax checks**

Run:

```powershell
pytest -q
python -m py_compile app.py services/storage.py services/prompts.py services/analysis.py services/ai_client.py prompts/seed_templates.py
```

Expected: all pytest tests pass and `py_compile` exits with code 0.

- [ ] **Step 9: Commit Streamlit app**

```powershell
git add app.py services/storage.py tests/test_storage.py
git commit -m "feat: add Streamlit learning app"
```

---

### Task 7: Local Run Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Install dependencies**

Run:

```powershell
pip install -r requirements.txt
```

Expected: dependencies install without errors.

- [ ] **Step 2: Run full verification**

Run:

```powershell
pytest -q
python -m py_compile app.py services/storage.py services/prompts.py services/analysis.py services/ai_client.py prompts/seed_templates.py
```

Expected: tests pass and compile succeeds.

- [ ] **Step 3: Start local app**

Run:

```powershell
streamlit run app.py
```

Expected: Streamlit serves the app at `http://localhost:8501/`.

- [ ] **Step 4: Manual smoke test in browser**

In the app:

1. Open `错题/薄弱点录入`.
2. Create a weak point with subject `刑法`, type `案例分析`, point `共同犯罪`, reason `要件遗漏`, mastery `模糊`.
3. Open `模板管理` and confirm six templates exist.
4. Open `苏格拉底训练`, select the new weak point, select `构成要件追问`, and preview the prompt.
5. Without an API key, click `开始训练` and confirm the app shows the configuration warning rather than crashing.
6. Open `薄弱点分析` and confirm the new weak point appears in subject, point, reason, and low-mastery tables.
7. Open `周度/月度复盘` and confirm the Markdown report includes `共同犯罪`.

- [ ] **Step 5: Update README with smoke-test note**

Append to `README.md`:

```markdown
## 本地验收流程

1. 新增一个薄弱点。
2. 在模板管理确认 6 个内置模板存在。
3. 在苏格拉底训练页预览提示词。
4. 未配置 API Key 时，训练页应提示配置，不应影响其它页面。
5. 在薄弱点分析和周度/月度复盘中确认新增记录被统计。
```

- [ ] **Step 6: Commit verification docs**

```powershell
git add README.md
git commit -m "docs: add local verification workflow"
```

---

## Self-Review Checklist

- Spec coverage: the plan covers weak-point entry, image storage, editable prompt templates, template versions, Socratic training, prompt snapshots, message/session persistence, analysis, weekly/monthly reports, non-AI operation, and Streamlit local run.
- Scope control: OCR, automatic photo classification, accounts, billing, cloud sync, role art, and community features are excluded from the first implementation.
- Type consistency: storage methods return dictionaries and IDs consistently; prompt builder accepts dictionaries from storage; analysis accepts lists from storage; Streamlit uses the same method names as tests.
- Verification: every service module has pytest coverage; Streamlit has syntax checks and a manual browser smoke test.
