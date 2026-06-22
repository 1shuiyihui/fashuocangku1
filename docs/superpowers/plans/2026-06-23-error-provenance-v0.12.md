# Error Provenance v0.12 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add structured error reconstruction, provenance file tracking, and drill recommendations to the learning loop.

**Architecture:** Add one focused analysis service and one provenance service, persist their outputs through versioned SQLite migrations, and surface the results in entry, training, analysis, review, and system pages. AI calls remain optional; deterministic rules keep the feature usable without API configuration.

**Tech Stack:** Python, Streamlit, SQLite migrations, pytest, local JSON/Markdown provenance files.

---

### Task 1: Migration and Storage APIs

**Files:**
- Create: `migrations/0003_error_provenance.sql`
- Modify: `services/versioning.py`
- Modify: `services/storage.py`
- Test: `tests/test_storage.py`
- Test: `tests/test_migrations.py`

- [x] Add `error_analyses` and `provenance_events` tables with foreign keys and indexes.
- [x] Bump `SUPPORTED_SCHEMA_VERSION` from `2` to `3`.
- [x] Add storage methods for creating/updating/listing error analyses and provenance events.
- [x] Verify migrations apply from version 2 to 3 without changing existing row counts.

### Task 2: Error Analysis Service

**Files:**
- Create: `services/error_analysis.py`
- Test: `tests/test_error_analysis.py`

- [x] Create deterministic `build_error_analysis()` that returns `error_location`, `root_cause`, `evidence`, `review_drill`, and `variant_drill`.
- [x] Use weak point fields plus optional session context.
- [x] Keep Chinese text as Python `str`, with no manual re-encoding.

### Task 3: Provenance File Service

**Files:**
- Create: `services/provenance.py`
- Test: `tests/test_provenance.py`

- [x] Save input JSON and output Markdown/JSON files under `data/provenance/YYYYMMDD/`.
- [x] Return paths and metadata for insertion into `provenance_events`.
- [x] Sanitize event names for filesystem safety.

### Task 4: App Integration

**Files:**
- Modify: `app.py`
- Test: `tests/test_app_smoke.py`

- [x] Generate initial error analysis after saving a weak point.
- [x] Save provenance for initial analysis, training AI calls, and review report generation.
- [x] Refresh error analysis when a session is finished.
- [x] Add UI sections for “错误还原”“根因证据”“复盘练习”“变式练习”“溯源记录”。

### Task 5: Review and Docs

**Files:**
- Modify: `services/analysis.py`
- Modify: `services/backup.py`
- Modify: `README.md`

- [x] Include provenance table counts in backup manifests.
- [x] Add error analysis and drills to review Markdown.
- [x] Document v0.12.0 behavior and data safety.

### Task 6: Verification

- [x] Run `python -m pytest -q`.
- [x] Run required `python -m py_compile ...`.
- [x] Check `http://localhost:8501/`.
- [x] Run browser smoke test for v0.12.0 sections.
- [x] Commit and push.
