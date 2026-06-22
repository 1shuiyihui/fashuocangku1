# Learning Loop UI v0.8 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the UI around the real study loop instead of raw dataframe tables.

**Architecture:** `services/workflow.py` computes loop-ready rows and next actions from existing data. `app.py` renders Feishu-style workflow components and uses session state to route user actions between existing pages. No database schema changes are required.

**Tech Stack:** Python, Streamlit, SQLite, pytest.

---

### Task 1: Workflow Data Layer

**Files:**
- Create: `services/workflow.py`
- Create: `tests/test_workflow.py`

- [ ] Write failing tests for `build_learning_loop_state`, recent row labels, priority queue sorting, and next action choices.
- [ ] Run `python -m pytest tests/test_workflow.py -q` and confirm import failure.
- [ ] Implement the smallest workflow module that passes the tests.
- [ ] Re-run `python -m pytest tests/test_workflow.py -q`.

### Task 2: Navigation Helpers

**Files:**
- Modify: `app.py`
- Modify: `tests/test_app_smoke.py`

- [ ] Add tests for v0.8 version and workflow state key constants.
- [ ] Implement `route_to_page`, `route_to_training`, and `route_to_review`.
- [ ] Make `page_training` default-select `focus_weak_point_id`.
- [ ] Run `python -m pytest tests/test_app_smoke.py -q`.

### Task 3: Page Refactor

**Files:**
- Modify: `app.py`
- Modify: `services/versioning.py`

- [ ] Replace `page_today` metrics with the loop dashboard.
- [ ] Replace `page_analysis` raw dataframes with workflow cards, worktable rows, ranking, and repair queue.
- [ ] Add focused context to `page_review`.
- [ ] Update `APP_VERSION` to `0.8.0`.

### Task 4: Verification and Release

**Files:**
- All changed files

- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m py_compile app.py services/storage.py services/prompts.py services/analysis.py services/ai_client.py services/document_processor.py services/rag.py services/course_generator.py services/backup.py services/migrations.py services/versioning.py prompts/seed_templates.py services/cloud_sync.py services/workflow.py`.
- [ ] Check `http://localhost:8501/` or a new local Streamlit port.
- [ ] Use the in-app browser to confirm v0.8.0 and workflow labels render.
- [ ] Commit and push `codex/fashuo-socratic-local-tool`.
