# Review Dashboard UI v0.10.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the weekly/monthly review page into a structured review dashboard and next-cycle training plan.

**Architecture:** Add a pure review dashboard state builder in `services/workflow.py`, then render it from `app.py` using the existing Streamlit app shell and navigation helpers. Preserve existing Markdown report generation for export only.

**Tech Stack:** Python, Streamlit, SQLite, pytest.

---

### Task 1: Contract Tests

**Files:**
- Modify: `tests/test_app_smoke.py`
- Modify: `tests/test_workflow.py`

- [x] Update app version assertions to `0.10.0`.
- [x] Add review workflow and dashboard section constants to the smoke contract.
- [x] Add CSS contract checks for review dashboard classes.
- [x] Add a pure workflow test for review KPI, subject progress and next-cycle plan.
- [x] Run targeted tests and confirm the new review state test fails before implementation.

### Task 2: Review State Builder

**Files:**
- Modify: `services/workflow.py`

- [x] Add `build_review_dashboard_state`.
- [x] Summarize KPI cards, subject progress, high-frequency knowledge points, mistake reasons, training queue and next-cycle plan.
- [x] Keep the function pure and independent from Streamlit.

### Task 3: Review UI

**Files:**
- Modify: `app.py`
- Modify: `services/versioning.py`

- [x] Bump `APP_VERSION` to `0.10.0`.
- [x] Add review workflow constants.
- [x] Add review-specific CSS classes and rendering helpers.
- [x] Replace direct Markdown output in `page_review` with dashboard cards, next-cycle plan and checklist.
- [x] Keep Markdown report in an expander and download button.

### Task 4: Documentation and Verification

**Files:**
- Modify: `README.md`
- Create: `docs/superpowers/specs/2026-06-22-review-dashboard-ui-v0.10-design.md`
- Create: `docs/superpowers/plans/2026-06-22-review-dashboard-ui-v0.10.md`

- [x] Document the v0.10.0 review dashboard change.
- [x] Run full tests.
- [x] Run py_compile guardrail command.
- [x] Check `http://localhost:8501/`.
- [x] Run browser smoke for the review page.
- [ ] Commit and push to GitHub.
