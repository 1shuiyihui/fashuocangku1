# v0.6.0 Feishu Style UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the Streamlit UI into a Feishu-like workbench shell without changing storage, OCR, RAG, or training behavior.

**Architecture:** Keep the existing Streamlit single-file page functions and add a small UI shell layer in `app.py`: navigation grouping constants, global CSS, sidebar navigation buttons, a top workspace header, and improved `今日学习` workbench layout. Versioning remains in `services/versioning.py`; tests lock the public constants and helper behavior.

**Tech Stack:** Python, Streamlit, SQLite, pytest, CSS injected via `st.markdown`.

---

## Files

- Modify `app.py`: add navigation groups, shell CSS, topbar, grouped sidebar buttons, and workbench cards.
- Modify `services/versioning.py`: bump to `0.6.0`.
- Modify `tests/test_app_smoke.py`: add v0.6.0 UI shell tests.
- Create this spec and implementation plan under `docs/superpowers/`.

## Task 1: Test UI Shell Contracts

- [ ] Add tests in `tests/test_app_smoke.py` for `APP_VERSION == "0.6.0"`.
- [ ] Add tests that `NAV_GROUPS` covers every page in `PAGES`.
- [ ] Add tests for `get_page_group("资料知识库") == "资料"` and `get_page_group("周度/月度复盘") == "分析"`.
- [ ] Add tests that `APP_SHELL_STYLE` contains `app-topbar`, `workbench-card`, and `[data-testid="stSidebar"]`.
- [ ] Add tests for AI status helper returning `AI 已配置` when an API key exists and `AI 未配置` otherwise.
- [ ] Run `python -m pytest tests/test_app_smoke.py -q` and confirm failures.

## Task 2: Implement Shell Constants and Helpers

- [ ] Add `NAV_GROUPS`, `PAGE_SUBTITLES`, `APP_SHELL_STYLE`, `get_page_group()`, and `get_ai_status_label()` to `app.py`.
- [ ] Merge the existing guide CSS into `APP_SHELL_STYLE`.
- [ ] Update `services/versioning.py` to `APP_VERSION = "0.6.0"`.
- [ ] Run `python -m pytest tests/test_app_smoke.py -q` and confirm it passes.

## Task 3: Implement Feishu-Style Layout

- [ ] Change `render_global_style()` to inject `APP_SHELL_STYLE`.
- [ ] Change `render_sidebar()` to return the selected page and render grouped navigation buttons.
- [ ] Add `render_workspace_header(page)` and call it once in `main()` before page content.
- [ ] Remove repeated `st.title()` calls from page functions that now rely on the topbar.
- [ ] Refactor `page_today()` into a workbench layout using metric cards, next-action card, and a compact priority list.
- [ ] Keep all business calls to `Storage`, AI client, OCR, RAG, and analysis unchanged.

## Task 4: Verify

- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m py_compile app.py services/storage.py services/prompts.py services/analysis.py services/ai_client.py services/document_processor.py services/rag.py services/course_generator.py services/backup.py services/migrations.py services/versioning.py prompts/seed_templates.py`.
- [ ] Run HTTP check for `http://localhost:8501/`.
- [ ] Use the browser to verify:
  - homepage shows the topbar and workbench cards,
  - sidebar groups are visible,
  - `资料知识库` can be opened,
  - no obvious overlap at desktop width.

## Task 5: GitHub Update

- [ ] Stage only intended source, test, and docs files.
- [ ] Commit with `feat: refactor streamlit ui shell`.
- [ ] Push `codex/fashuo-socratic-local-tool` to GitHub.
- [ ] Report verification and data impact.

