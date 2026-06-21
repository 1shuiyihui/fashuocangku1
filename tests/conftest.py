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
