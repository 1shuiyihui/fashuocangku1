# Cloud Persistence v0.7 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add GitHub-backed cloud snapshot persistence so Streamlit Cloud restarts do not lose app data.

**Architecture:** `services/cloud_sync.py` handles archive and GitHub Contents API behavior. `Storage` exposes a small write callback hook. `app.get_storage()` restores before database initialization and uploads after writes.

**Tech Stack:** Python, Streamlit, SQLite, requests, pytest, GitHub Contents API.

---

### Task 1: Cloud Sync Unit Tests

**Files:**
- Create: `tests/test_cloud_sync.py`
- Create later: `services/cloud_sync.py`

- [ ] **Step 1: Write failing tests**

Add tests covering:

```python
from pathlib import Path
import base64
import io
import zipfile

from services.cloud_sync import (
    CloudSyncConfig,
    CloudSyncError,
    GitHubSnapshotSync,
    build_snapshot_archive,
    load_cloud_sync_config,
    restore_snapshot_archive,
)


def test_load_cloud_sync_config_reads_streamlit_secrets():
    config = load_cloud_sync_config(
        {
            "persistence": {
                "enabled": True,
                "provider": "github",
                "repo": "1shuiyihui/fashuocangku1",
                "branch": "cloud-data",
                "source_branch": "codex/fashuo-socratic-local-tool",
                "snapshot_path": "fashuo-cloud-snapshot.zip",
                "github_token": "token",
            }
        }
    )

    assert config.enabled is True
    assert config.repo == "1shuiyihui/fashuocangku1"
    assert config.branch == "cloud-data"
    assert config.source_branch == "codex/fashuo-socratic-local-tool"
    assert config.snapshot_path == "fashuo-cloud-snapshot.zip"
    assert config.github_token == "token"
```

- [ ] **Step 2: Verify the tests fail**

Run: `python -m pytest tests/test_cloud_sync.py -q`

Expected: import failure because `services.cloud_sync` does not exist.

- [ ] **Step 3: Implement minimal cloud sync**

Create `services/cloud_sync.py` with config parsing, archive build/restore, path traversal checks, and GitHub download/upload helpers.

- [ ] **Step 4: Verify the tests pass**

Run: `python -m pytest tests/test_cloud_sync.py -q`

Expected: all tests in `tests/test_cloud_sync.py` pass.

### Task 2: Storage Write Callback

**Files:**
- Modify: `services/storage.py`
- Modify: `tests/test_storage.py`

- [ ] **Step 1: Write failing tests**

Add tests proving that reads do not call `after_write`, while inserts call it after commit:

```python
def test_storage_after_write_callback_runs_only_for_committed_writes(tmp_path):
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
```

- [ ] **Step 2: Verify the test fails**

Run: `python -m pytest tests/test_storage.py::test_storage_after_write_callback_runs_only_for_committed_writes -q`

Expected: `Storage.__init__()` does not accept `after_write`.

- [ ] **Step 3: Implement the callback**

Add `after_write` to `Storage.__init__`. In `connect()`, record `conn.total_changes` before yielding, commit, then call the callback if total changes increased.

- [ ] **Step 4: Verify storage tests pass**

Run: `python -m pytest tests/test_storage.py -q`

Expected: all storage tests pass.

### Task 3: App Wiring and Docs

**Files:**
- Modify: `app.py`
- Modify: `services/versioning.py`
- Modify: `README.md`
- Modify: `docs/DEPLOYMENT.md`
- Modify: optional `.streamlit/secrets.toml.example` if present

- [ ] **Step 1: Add app smoke tests**

Update `tests/test_app_smoke.py` for app version `0.7.0` and persistence status helper labels.

- [ ] **Step 2: Wire startup restore**

In `get_storage()`, load config, restore remote snapshot when enabled, initialize/migrate/seed the database, and pass `after_write` to upload snapshots.

- [ ] **Step 3: Add UI status**

Show a topbar/status-page hint for `GitHub 云端快照` when enabled and `本地临时存储` when disabled.

- [ ] **Step 4: Update documentation**

Document the DeepSeek `[ai]` secrets and GitHub `[persistence]` secrets. Explain that the first write creates `cloud-data` if the token can write Contents.

### Task 4: Verification and Release

**Files:**
- All changed files

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/test_cloud_sync.py tests/test_storage.py tests/test_app_smoke.py -q
```

- [ ] **Step 2: Run full tests**

Run:

```powershell
python -m pytest -q
```

- [ ] **Step 3: Compile important modules**

Run:

```powershell
python -m py_compile app.py services/storage.py services/prompts.py services/analysis.py services/ai_client.py services/document_processor.py services/rag.py services/course_generator.py services/backup.py services/migrations.py services/versioning.py prompts/seed_templates.py services/cloud_sync.py
```

- [ ] **Step 4: HTTP and browser smoke**

Run the app, check `http://localhost:8501/`, and use the in-app browser to confirm the app renders.

- [ ] **Step 5: Commit and push**

Commit with message `feat: add cloud persistence snapshots` and push `codex/fashuo-socratic-local-tool`.
