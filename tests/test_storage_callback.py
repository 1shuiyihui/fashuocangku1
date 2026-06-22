from __future__ import annotations

from pathlib import Path

from services.storage import Storage


def test_storage_after_write_callback_runs_only_for_committed_writes(tmp_path: Path):
    calls = []
    store = Storage(
        db_path=tmp_path / "fashuo-test.db",
        uploads_dir=tmp_path / "uploads",
        documents_dir=tmp_path / "documents",
        after_write=lambda reason: calls.append(reason),
    )
    store.init_db()
    calls.clear()

    store.list_weak_points()
    assert calls == []

    store.create_weak_point(
        {
            "subject": "刑法",
            "question_type": "简答",
            "knowledge_point": "共同犯罪",
            "mistake_reason": "要件遗漏",
            "mastery_level": "陌生",
        }
    )

    assert calls == ["sqlite_commit"]
