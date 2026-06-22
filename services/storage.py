from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prompts.seed_templates import SEED_TEMPLATES


SQLITE_BUSY_TIMEOUT_MS = 5000
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_DOCUMENT_UPLOAD_BYTES = 30 * 1024 * 1024
IMAGE_UPLOAD_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
DOCUMENT_UPLOAD_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".md", ".markdown"}


class Storage:
    def __init__(
        self,
        db_path: Path | str = "data/fashuo.db",
        uploads_dir: Path | str = "data/uploads",
        documents_dir: Path | str = "data/documents",
        max_upload_bytes: int = MAX_UPLOAD_BYTES,
        max_document_upload_bytes: int = MAX_DOCUMENT_UPLOAD_BYTES,
        after_write: Callable[[str], None] | None = None,
    ):
        self.db_path = Path(db_path)
        self.uploads_dir = Path(uploads_dir)
        self.documents_dir = Path(documents_dir)
        self.max_upload_bytes = max_upload_bytes
        self.max_document_upload_bytes = max_document_upload_bytes
        self.after_write = after_write

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)
        conn.row_factory = sqlite3.Row
        changed = False
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
            conn.execute("PRAGMA journal_mode = WAL")
            changes_before = conn.total_changes
            yield conn
            changed = conn.total_changes > changes_before
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        if changed and self.after_write is not None:
            self.after_write("sqlite_commit")

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

                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    text_content TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    error_message TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS document_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    source_label TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                );

                CREATE TABLE IF NOT EXISTS generated_courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    source_document_id INTEGER,
                    raw_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(source_document_id) REFERENCES documents(id)
                );

                CREATE TABLE IF NOT EXISTS course_lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id INTEGER NOT NULL,
                    lesson_index INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    knowledge_points TEXT NOT NULL,
                    mistake_risks TEXT NOT NULL,
                    recommended_template TEXT NOT NULL,
                    review_plan TEXT NOT NULL,
                    imported_weak_point_id INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(course_id) REFERENCES generated_courses(id),
                    FOREIGN KEY(imported_weak_point_id) REFERENCES weak_points(id)
                );

                CREATE TABLE IF NOT EXISTS rag_queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    result_chunk_ids TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_weak_points_created_at
                    ON weak_points(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_weak_points_subject
                    ON weak_points(subject);
                CREATE INDEX IF NOT EXISTS idx_sessions_status_started_at
                    ON sessions(status, started_at DESC);
                CREATE INDEX IF NOT EXISTS idx_sessions_weak_point_id
                    ON sessions(weak_point_id);
                CREATE INDEX IF NOT EXISTS idx_messages_session_id
                    ON messages(session_id, id);
                CREATE INDEX IF NOT EXISTS idx_documents_status_created_at
                    ON documents(status, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id
                    ON document_chunks(document_id, chunk_index);
                CREATE INDEX IF NOT EXISTS idx_course_lessons_course_id
                    ON course_lessons(course_id, lesson_index);
                """
            )

    def seed_templates(self) -> None:
        now = self._now()
        with self.connect() as conn:
            for template in SEED_TEMPLATES:
                exists = conn.execute(
                    "SELECT id FROM templates WHERE name = ?",
                    (template["name"],),
                ).fetchone()
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
                    (
                        cur.lastrowid,
                        template["body"],
                        template["default_goal"],
                        template["end_condition"],
                        now,
                    ),
                )

    def save_upload(self, uploaded_file: Any) -> str:
        if uploaded_file is None:
            return ""
        suffix = Path(uploaded_file.name).suffix or ".png"
        self._validate_upload(
            uploaded_file,
            max_bytes=self.max_upload_bytes,
            allowed_extensions=IMAGE_UPLOAD_EXTENSIONS,
            label="image upload",
        )
        target = self.uploads_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}{suffix}"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self._rewind_upload(uploaded_file)
        with target.open("wb") as handle:
            shutil.copyfileobj(uploaded_file, handle)
        return str(target)

    def save_document_upload(self, uploaded_file: Any) -> str:
        if uploaded_file is None:
            return ""
        suffix = Path(uploaded_file.name).suffix
        stem = Path(uploaded_file.name).stem or "document"
        self._validate_upload(
            uploaded_file,
            max_bytes=self.max_document_upload_bytes,
            allowed_extensions=DOCUMENT_UPLOAD_EXTENSIONS,
            label="document upload",
        )
        target = self.documents_dir / f"{stem}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}{suffix}"
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self._rewind_upload(uploaded_file)
        with target.open("wb") as handle:
            shutil.copyfileobj(uploaded_file, handle)
        return str(target)

    def create_document(self, payload: dict[str, Any]) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO documents
                (filename, file_type, file_path, text_content, status, error_message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["filename"],
                    payload["file_type"],
                    payload["file_path"],
                    payload.get("text_content", ""),
                    payload["status"],
                    payload.get("error_message", ""),
                    self._now(),
                ),
            )
            return int(cur.lastrowid)

    def update_document_processing(
        self,
        document_id: int,
        text_content: str,
        status: str,
        error_message: str = "",
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE documents
                SET text_content = ?, status = ?, error_message = ?
                WHERE id = ?
                """,
                (text_content, status, error_message, document_id),
            )

    def list_documents(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
            return [self._dict(row) for row in rows]

    def get_document(self, document_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
            if row is None:
                raise KeyError(f"document not found: {document_id}")
            return self._dict(row)

    def replace_document_chunks(self, document_id: int, chunks: list[dict[str, Any] | str]) -> None:
        now = self._now()
        with self.connect() as conn:
            conn.execute("DELETE FROM document_chunks WHERE document_id = ?", (document_id,))
            for index, chunk in enumerate(chunks, start=1):
                if isinstance(chunk, str):
                    content = chunk
                    source_label = f"document:{document_id}#{index}"
                else:
                    content = chunk["content"]
                    source_label = chunk.get("source_label", f"document:{document_id}#{index}")
                conn.execute(
                    """
                    INSERT INTO document_chunks
                    (document_id, chunk_index, content, source_label, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (document_id, index, content, source_label, now),
                )

    def list_document_chunks(self, document_id: int | None = None) -> list[dict[str, Any]]:
        if document_id is None:
            query = "SELECT * FROM document_chunks ORDER BY document_id DESC, chunk_index"
            params: tuple[Any, ...] = ()
        else:
            query = "SELECT * FROM document_chunks WHERE document_id = ? ORDER BY chunk_index"
            params = (document_id,)
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._dict(row) for row in rows]

    def create_rag_query(self, query: str, chunk_ids: list[int]) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO rag_queries (query, result_chunk_ids, created_at)
                VALUES (?, ?, ?)
                """,
                (query, json.dumps(chunk_ids, ensure_ascii=False), self._now()),
            )
            return int(cur.lastrowid)

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
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY name"
        with self.connect() as conn:
            rows = conn.execute(query).fetchall()
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
                (
                    template_id,
                    payload["body"],
                    payload["default_goal"],
                    payload["end_condition"],
                    now,
                ),
            )
            return template_id

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
                (
                    template_id,
                    new_version,
                    payload["body"],
                    payload["default_goal"],
                    payload["end_condition"],
                    now,
                ),
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
                (
                    weak_point_id,
                    template_id,
                    template_version,
                    prompt_snapshot,
                    now,
                    mastery_before,
                ),
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
                (
                    self._now(),
                    mastery_after,
                    summary,
                    exposed_issues,
                    next_review_suggestion,
                    session_id,
                ),
            )

    def create_course(
        self,
        title: str,
        source_document_id: int | None,
        raw_json: str,
        lessons: list[dict[str, Any]],
    ) -> int:
        now = self._now()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO generated_courses
                (title, source_document_id, raw_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (title, source_document_id, raw_json, now),
            )
            course_id = int(cur.lastrowid)
            for index, lesson in enumerate(lessons, start=1):
                conn.execute(
                    """
                    INSERT INTO course_lessons
                    (course_id, lesson_index, title, objective, knowledge_points, mistake_risks,
                     recommended_template, review_plan, imported_weak_point_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
                    """,
                    (
                        course_id,
                        index,
                        lesson.get("title", f"第 {index} 课"),
                        lesson.get("objective", ""),
                        json.dumps(lesson.get("knowledge_points", []), ensure_ascii=False),
                        json.dumps(lesson.get("mistake_risks", []), ensure_ascii=False),
                        lesson.get("recommended_template", "构成要件追问"),
                        lesson.get("review_plan", ""),
                        now,
                    ),
                )
            return course_id

    def list_courses(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM generated_courses ORDER BY created_at DESC").fetchall()
            return [self._dict(row) for row in rows]

    def get_course(self, course_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM generated_courses WHERE id = ?", (course_id,)).fetchone()
            if row is None:
                raise KeyError(f"course not found: {course_id}")
            return self._dict(row)

    def list_course_lessons(self, course_id: int) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM course_lessons WHERE course_id = ? ORDER BY lesson_index",
                (course_id,),
            ).fetchall()
            lessons = [self._dict(row) for row in rows]
        for lesson in lessons:
            lesson["knowledge_points"] = json.loads(lesson["knowledge_points"] or "[]")
            lesson["mistake_risks"] = json.loads(lesson["mistake_risks"] or "[]")
        return lessons

    def get_course_lesson(self, lesson_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM course_lessons WHERE id = ?", (lesson_id,)).fetchone()
            if row is None:
                raise KeyError(f"course lesson not found: {lesson_id}")
            lesson = self._dict(row)
        lesson["knowledge_points"] = json.loads(lesson["knowledge_points"] or "[]")
        lesson["mistake_risks"] = json.loads(lesson["mistake_risks"] or "[]")
        return lesson

    def mark_lesson_imported(self, lesson_id: int, weak_point_id: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE course_lessons SET imported_weak_point_id = ? WHERE id = ?",
                (weak_point_id, lesson_id),
            )

    def import_lesson_as_weak_point(self, lesson_id: int, subject: str) -> int:
        lesson = self.get_course_lesson(lesson_id)
        if lesson.get("imported_weak_point_id"):
            return int(lesson["imported_weak_point_id"])
        knowledge_points = lesson.get("knowledge_points") or [lesson["title"]]
        mistake_risks = lesson.get("mistake_risks") or ["资料生成待训练"]
        weak_point_id = self.create_weak_point(
            {
                "subject": subject,
                "question_type": "简答",
                "knowledge_point": knowledge_points[0],
                "mistake_reason": mistake_risks[0],
                "mastery_level": "陌生",
                "image_path": "",
                "question_text": "",
                "reference_answer": lesson.get("objective", ""),
                "notes": f"课程导入：{lesson['title']}\n复习计划：{lesson.get('review_plan', '')}",
            }
        )
        self.mark_lesson_imported(lesson_id, weak_point_id)
        return weak_point_id

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _dict(row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    @staticmethod
    def _upload_size(uploaded_file: Any) -> int | None:
        size = getattr(uploaded_file, "size", None)
        if isinstance(size, int):
            return size
        if hasattr(uploaded_file, "getbuffer"):
            return len(uploaded_file.getbuffer())
        if not all(hasattr(uploaded_file, attr) for attr in ("tell", "seek")):
            return None
        current = uploaded_file.tell()
        uploaded_file.seek(0, 2)
        measured = uploaded_file.tell()
        uploaded_file.seek(current)
        return int(measured)

    @staticmethod
    def _rewind_upload(uploaded_file: Any) -> None:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)

    @classmethod
    def _validate_upload(
        cls,
        uploaded_file: Any,
        max_bytes: int,
        allowed_extensions: set[str],
        label: str,
    ) -> None:
        suffix = Path(uploaded_file.name).suffix.lower()
        if suffix not in allowed_extensions:
            raise ValueError(f"{label} type is not supported: {suffix or 'unknown'}")
        size = cls._upload_size(uploaded_file)
        if size is not None and size > max_bytes:
            max_mb = max_bytes / 1024 / 1024
            actual_mb = size / 1024 / 1024
            raise ValueError(f"{label} is too large: {actual_mb:.1f} MB > {max_mb:.1f} MB")
