# Workspace UI v0.9.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the Streamlit workspace UI into a Feishu-like learning cockpit while preserving existing study data and workflows.

**Architecture:** Keep the current single Streamlit app structure and add focused UI helper functions in `app.py`. Preserve existing `Storage`, OCR/RAG, prompt, course generation, migration, and backup services.

**Tech Stack:** Python, Streamlit, SQLite, pytest, existing service modules.

---

### Task 1: Lock the v0.9.0 UI Contract

**Files:**
- Modify: `tests/test_app_smoke.py`

- [x] Add tests for `APP_VERSION == "0.9.0"`.
- [x] Add tests for new UI workflow constants: `ENTRY_WORKFLOW_STEPS`, `KNOWLEDGE_WORKFLOW_STEPS`, `TRAINING_PANEL_SECTIONS`, `SIDEBAR_STATUS_TITLE`.
- [x] Add tests that `APP_SHELL_STYLE` contains the layout classes required by the new pages.
- [x] Run targeted tests and confirm they fail before implementation.

### Task 2: Add Shared UI Layout Primitives

**Files:**
- Modify: `app.py`
- Modify: `services/versioning.py`

- [x] Bump `APP_VERSION` to `0.9.0`.
- [x] Add workflow constants for the entry, training, and knowledge-base pages.
- [x] Extend `APP_SHELL_STYLE` with sidebar status cards, process strips, workspace grids, training cockpit, source result cards, and lesson cards.
- [x] Add helper functions for process steps, panel intros, KPI cards, sidebar status, document cards, source result cards, and lesson plan cards.

### Task 3: Refactor Sidebar

**Files:**
- Modify: `app.py`

- [x] Render brand card, system status card, workflow card, beginner mode, AI config, and grouped navigation.
- [x] Preserve existing navigation state and `st.rerun()` behavior.
- [x] Keep API key entry in the sidebar, while reminding deployment usage through status labels.

### Task 4: Refactor Key Pages

**Files:**
- Modify: `app.py`

- [x] Rebuild `page_entry()` around source material, structured training point fields, and AI extraction preview.
- [x] Rebuild `page_training()` around training context, prompt/source preview, chat, timeline, and finish form.
- [x] Rebuild `page_knowledge_base()` around upload/index, retrieval, plan generation, and lesson import cards.
- [x] Preserve existing storage calls and button actions.

### Task 5: Documentation and Verification

**Files:**
- Modify: `README.md`
- Create: `docs/superpowers/specs/2026-06-22-workspace-ui-v0.9-design.md`
- Create: `docs/superpowers/plans/2026-06-22-workspace-ui-v0.9.md`

- [x] Document the v0.9.0 UI changes.
- [x] Run full tests.
- [x] Run full py_compile command from update guardrails.
- [x] Check `http://localhost:8501/`.
- [x] Run browser smoke for updated UI pages.
- [ ] Commit and push to GitHub.
