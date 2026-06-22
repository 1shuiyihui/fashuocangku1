from __future__ import annotations

import io
import sqlite3
from pathlib import Path

import pytest

from services.storage import Storage


class FakeUploadedFile(io.BytesIO):
    def __init__(self, name: str, data: bytes):
        super().__init__(data)
        self.name = name
        self.size = len(data)


def test_storage_connect_closes_connection_after_context(tmp_path: Path):
    storage = Storage(
        db_path=tmp_path / "fashuo.db",
        uploads_dir=tmp_path / "uploads",
        documents_dir=tmp_path / "documents",
    )
    storage.init_db()

    with storage.connect() as conn:
        assert conn.execute("SELECT 1").fetchone()[0] == 1

    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")


def test_storage_connect_enables_sqlite_pragmas(storage):
    with storage.connect() as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] >= 5000
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


def test_init_db_creates_common_query_indexes(storage):
    with storage.connect() as conn:
        index_names = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }

    assert "idx_weak_points_created_at" in index_names
    assert "idx_sessions_status_started_at" in index_names
    assert "idx_messages_session_id" in index_names
    assert "idx_document_chunks_document_id" in index_names


def test_save_upload_rejects_large_files(tmp_path: Path):
    storage = Storage(
        db_path=tmp_path / "fashuo.db",
        uploads_dir=tmp_path / "uploads",
        documents_dir=tmp_path / "documents",
    )
    too_large = FakeUploadedFile("large.png", b"x" * (16 * 1024 * 1024))

    with pytest.raises(ValueError, match="too large"):
        storage.save_upload(too_large)
