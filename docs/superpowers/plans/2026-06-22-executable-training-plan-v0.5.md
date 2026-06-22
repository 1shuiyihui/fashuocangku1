# v0.5.0 Executable Training Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade generated courses into executable Socratic training plans while keeping existing user data and schema stable.

**Architecture:** Keep the SQLite schema unchanged and improve behavior through prompt design, lesson normalization, Streamlit presentation, and session-only onboarding state. Storage remains the persistence boundary; `services/course_generator.py` owns AI prompt/JSON normalization; `app.py` owns page labels and first-run guidance.

**Tech Stack:** Python, Streamlit, SQLite, pytest, OpenAI-compatible AI client.

---

## Files

- Modify `services/course_generator.py`: prompt wording and normalization defaults.
- Modify `app.py`: onboarding CSS/UI, course generation labels, lesson task-card display.
- Modify `services/versioning.py`: bump app version to `0.5.0`.
- Modify `tests/test_course_generator.py`: add executable-plan prompt and normalization coverage.
- Modify `tests/test_app_smoke.py`: add onboarding text and version coverage.
- Modify `tests/test_storage.py`: assert imported lesson notes keep executable review plan.
- Create this design and implementation plan under `docs/superpowers/`.

## Task 1: Course Generator Behavior

- [ ] Add failing tests in `tests/test_course_generator.py`:
  - `test_build_course_prompt_requests_executable_training_plan`
  - `test_normalize_lessons_accepts_executable_plan_fields`
- [ ] Run `python -m pytest tests/test_course_generator.py -q` and confirm the new tests fail because prompt/normalization has not been upgraded.
- [ ] Update `services/course_generator.py` so the prompt asks for executable training-plan fields and `normalize_lessons()` folds optional fields such as `daily_tasks`, `socratic_drills`, `estimated_minutes`, `review_checklist`, and `importable_training_point` into existing persisted fields.
- [ ] Re-run `python -m pytest tests/test_course_generator.py -q` and confirm it passes.

## Task 2: Streamlit UI Copy and First-Run Guidance

- [ ] Add failing smoke tests in `tests/test_app_smoke.py` for:
  - `APP_VERSION == "0.5.0"`
  - `APP_GUIDE_STEPS` contains the three first-use steps.
  - course import labels are exposed as constants.
- [ ] Run `python -m pytest tests/test_app_smoke.py -q` and confirm failures.
- [ ] Update `app.py`:
  - Add constants for import labels and guide steps.
  - Add CSS for simple guide-card entrance animation.
  - Render the guide at the top of `page_today()`.
  - Change course-generation section copy to “生成可执行训练计划并导入训练点”.
  - Change lesson import selectbox/button labels to “训练点科目” and “导入为训练点”.
- [ ] Update `services/versioning.py` to `APP_VERSION = "0.5.0"`.
- [ ] Re-run `python -m pytest tests/test_app_smoke.py -q`.

## Task 3: Storage Compatibility Check

- [ ] Add a storage test confirming a generated lesson with executable review text imports into a weak point without schema changes.
- [ ] Run `python -m pytest tests/test_storage.py -q` and confirm it passes.

## Task 4: Full Verification

- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m py_compile app.py services/storage.py services/prompts.py services/analysis.py services/ai_client.py services/document_processor.py services/rag.py services/course_generator.py services/backup.py services/migrations.py services/versioning.py prompts/seed_templates.py`.
- [ ] If Streamlit is running, run `(Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8501/' -TimeoutSec 10).StatusCode`.
- [ ] Confirm `git status --short` only contains intended source, test, and docs changes.

## Task 5: GitHub Update

- [ ] Stage intended files only.
- [ ] Commit with `feat: upgrade executable training plans`.
- [ ] Push branch `codex/fashuo-socratic-local-tool` to GitHub.
- [ ] Report data impact, verification results, branch, and push status.

