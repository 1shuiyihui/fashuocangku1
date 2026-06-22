from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.storage import Storage


BACKUP_TABLES = [
    "weak_points",
    "templates",
    "template_versions",
    "sessions",
    "messages",
    "documents",
    "document_chunks",
    "generated_courses",
    "course_lessons",
    "rag_queries",
    "error_analyses",
    "provenance_events",
]


def create_backup(
    storage: Storage,
    reason: str,
    backup_root: str | Path = "backups",
) -> Path:
    backup_root = Path(backup_root)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    backup_dir = backup_root / f"{timestamp}_before_{_safe_reason(reason)}"
    backup_dir.mkdir(parents=True, exist_ok=False)

    if storage.db_path.exists():
        shutil.copy2(storage.db_path, backup_dir / storage.db_path.name)
    if storage.uploads_dir.exists():
        shutil.copytree(storage.uploads_dir, backup_dir / "uploads", dirs_exist_ok=True)
    if storage.documents_dir.exists():
        shutil.copytree(storage.documents_dir, backup_dir / "documents", dirs_exist_ok=True)
    if storage.provenance_dir.exists():
        shutil.copytree(storage.provenance_dir, backup_dir / "provenance", dirs_exist_ok=True)

    manifest = {
        "backup_time": timestamp,
        "reason": reason,
        "branch": _git_value(["git", "branch", "--show-current"]),
        "commit": _git_value(["git", "rev-parse", "HEAD"]),
        "database_path": str(storage.db_path),
        "integrity": integrity_check(storage),
        "table_counts": collect_table_counts(storage),
    }
    (backup_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return backup_dir


def integrity_check(storage: Storage) -> str:
    with storage.connect() as conn:
        return str(conn.execute("PRAGMA integrity_check").fetchone()[0])


def collect_table_counts(storage: Storage) -> dict[str, int | None]:
    counts: dict[str, int | None] = {}
    with storage.connect() as conn:
        for table in BACKUP_TABLES:
            try:
                counts[table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            except Exception:
                counts[table] = None
    return counts


def list_backups(backup_root: str | Path = "backups") -> list[dict[str, Any]]:
    root = Path(backup_root)
    if not root.exists():
        return []
    backups = []
    for path in sorted(root.iterdir(), reverse=True):
        manifest_path = path / "manifest.json"
        if path.is_dir() and manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                manifest = {"reason": "manifest_parse_error"}
            backups.append({"path": str(path), **manifest})
    return backups


def _safe_reason(reason: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in reason).strip("_") or "backup"


def _git_value(command: list[str]) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except Exception:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()
