# Two-User Website Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare the Streamlit law-study app for stable 1-2 person website deployment.

**Architecture:** Keep the existing Streamlit and SQLite architecture. Harden SQLite connection lifecycle, add small-concurrency pragmas and indexes, protect uploads, add retry behavior for transient AI failures, and add Streamlit deployment files.

**Tech Stack:** Python, Streamlit, SQLite, pytest, Tesseract OCR, GitHub, Streamlit Community Cloud.

---

### Task 1: SQLite Stability

**Files:**
- Modify: `services/storage.py`
- Create: `migrations/0002_sqlite_stability_indexes.sql`
- Modify: `services/versioning.py`
- Test: `tests/test_stability.py`

- [x] Write tests for closed connections, WAL, busy timeout, foreign keys, and common query indexes.
- [x] Implement a context-managed SQLite connection that commits, rolls back, and closes explicitly.
- [x] Add index creation for new databases and a versioned migration for existing databases.
- [x] Run `python -m pytest tests/test_stability.py tests/test_migrations.py -q`.

### Task 2: Upload And AI Resilience

**Files:**
- Modify: `services/storage.py`
- Modify: `services/ai_client.py`
- Test: `tests/test_stability.py`
- Test: `tests/test_ai_client.py`

- [x] Write upload-size and AI retry tests.
- [x] Reject oversized uploads at the storage layer.
- [x] Retry AI requests for HTTP 429 and 5xx responses.
- [x] Run targeted tests.

### Task 3: Website Deployment Readiness

**Files:**
- Create: `packages.txt`
- Create: `.streamlit/config.toml`
- Create: `.streamlit/secrets.toml.example`
- Modify: `.gitignore`
- Modify: `app.py`
- Modify: `tests/test_app_smoke.py`
- Create: `docs/DEPLOYMENT.md`

- [x] Add Streamlit Cloud config and Linux OCR package dependencies.
- [x] Add a secrets example and ignore real secrets.
- [x] Read AI defaults from Streamlit secrets while preserving sidebar overrides.
- [x] Document deployment steps and operational boundaries.

### Task 4: Final Verification And Publish

**Files:**
- All changed files

- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m py_compile app.py services/storage.py services/prompts.py services/analysis.py services/ai_client.py services/document_processor.py services/rag.py services/course_generator.py services/backup.py services/migrations.py services/versioning.py prompts/seed_templates.py`.
- [ ] Apply migrations to the real local database with automatic backup.
- [ ] Check `http://localhost:8501/`.
- [ ] Commit and push the branch.
