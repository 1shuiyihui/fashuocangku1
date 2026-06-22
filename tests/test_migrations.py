import pytest

from services.migrations import (
    SUPPORTED_SCHEMA_VERSION,
    SchemaTooNewError,
    apply_migrations,
    get_schema_version,
)
from services.storage import Storage


def test_apply_migrations_records_baseline_and_creates_backup(tmp_path):
    storage = Storage(
        db_path=tmp_path / "fashuo.db",
        uploads_dir=tmp_path / "uploads",
        documents_dir=tmp_path / "documents",
    )
    storage.init_db()
    storage.seed_templates()

    result = apply_migrations(
        storage,
        backup_root=tmp_path / "backups",
        reason="unit_test_migration",
    )

    assert result["from_version"] == 0
    assert result["to_version"] == SUPPORTED_SCHEMA_VERSION
    assert result["backup_dir"] is not None
    assert get_schema_version(storage) == SUPPORTED_SCHEMA_VERSION
    with storage.connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert "error_analyses" in tables
    assert "provenance_events" in tables


def test_newer_database_version_is_rejected(tmp_path):
    storage = Storage(
        db_path=tmp_path / "fashuo.db",
        uploads_dir=tmp_path / "uploads",
        documents_dir=tmp_path / "documents",
    )
    storage.init_db()
    with storage.connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
            (SUPPORTED_SCHEMA_VERSION + 1, "future", "2099-01-01T00:00:00"),
        )

    with pytest.raises(SchemaTooNewError):
        apply_migrations(storage, backup_root=tmp_path / "backups", reason="future")
