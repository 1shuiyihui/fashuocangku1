import json

from services.backup import create_backup


def test_create_backup_copies_database_and_manifest(storage, tmp_path):
    storage.create_weak_point(
        {
            "subject": "刑法",
            "question_type": "简答",
            "knowledge_point": "共同犯罪",
            "mistake_reason": "要件遗漏",
            "mastery_level": "模糊",
            "image_path": "",
            "question_text": "",
            "reference_answer": "",
            "notes": "",
        }
    )

    backup_dir = create_backup(
        storage,
        reason="unit_test_backup",
        backup_root=tmp_path / "backups",
    )
    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))

    assert (backup_dir / storage.db_path.name).exists()
    assert manifest["reason"] == "unit_test_backup"
    assert manifest["integrity"] == "ok"
    assert manifest["table_counts"]["weak_points"] == 1
