from __future__ import annotations

from pathlib import Path
from typing import Any

from services.backup import collect_table_counts, create_backup, integrity_check
from services.storage import Storage
from services.versioning import SUPPORTED_SCHEMA_VERSION


MIGRATIONS_DIR = Path("migrations")


class SchemaTooNewError(RuntimeError):
    pass


class MigrationError(RuntimeError):
    pass


def get_schema_version(storage: Storage) -> int:
    with storage.connect() as conn:
        exists = conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'schema_migrations'
            """
        ).fetchone()
        if not exists:
            return 0
        row = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        return int(row[0] or 0)


def apply_migrations(
    storage: Storage,
    backup_root: str | Path = "backups",
    reason: str = "schema_migration",
) -> dict[str, Any]:
    from_version = get_schema_version(storage)
    if from_version > SUPPORTED_SCHEMA_VERSION:
        raise SchemaTooNewError(
            f"当前数据库版本 {from_version} 高于应用支持版本 {SUPPORTED_SCHEMA_VERSION}，请使用新版应用或恢复备份。"
        )
    if from_version == SUPPORTED_SCHEMA_VERSION:
        return {
            "from_version": from_version,
            "to_version": from_version,
            "backup_dir": None,
            "applied": [],
            "before_counts": collect_table_counts(storage),
            "after_counts": collect_table_counts(storage),
        }

    before_integrity = integrity_check(storage)
    if before_integrity != "ok":
        raise MigrationError(f"迁移前数据库完整性检查失败：{before_integrity}")

    before_counts = collect_table_counts(storage)
    backup_dir = create_backup(storage, reason=reason, backup_root=backup_root)
    applied = []

    for version, path in _pending_migrations(from_version):
        sql = path.read_text(encoding="utf-8")
        with storage.connect() as conn:
            conn.executescript(sql)
        applied.append(version)

    to_version = get_schema_version(storage)
    after_integrity = integrity_check(storage)
    if after_integrity != "ok":
        raise MigrationError(f"迁移后数据库完整性检查失败：{after_integrity}")
    if to_version != SUPPORTED_SCHEMA_VERSION:
        raise MigrationError(f"迁移后版本为 {to_version}，但应用期望 {SUPPORTED_SCHEMA_VERSION}")

    return {
        "from_version": from_version,
        "to_version": to_version,
        "backup_dir": str(backup_dir),
        "applied": applied,
        "before_counts": before_counts,
        "after_counts": collect_table_counts(storage),
    }


def list_applied_migrations(storage: Storage) -> list[dict[str, Any]]:
    if get_schema_version(storage) == 0:
        return []
    with storage.connect() as conn:
        rows = conn.execute("SELECT * FROM schema_migrations ORDER BY version").fetchall()
        return [dict(row) for row in rows]


def _pending_migrations(from_version: int) -> list[tuple[int, Path]]:
    migrations = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        prefix = path.name.split("_", 1)[0]
        if not prefix.isdigit():
            continue
        version = int(prefix)
        if from_version < version <= SUPPORTED_SCHEMA_VERSION:
            migrations.append((version, path))
    return migrations

