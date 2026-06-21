# OCR RAG Course Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add OCR-backed document ingestion, local TF-IDF RAG retrieval, AI course generation, and one-click import of generated lessons into Socratic training weak points.

**Architecture:** Extend the existing Streamlit + SQLite app with focused service modules: `document_processor` handles file extraction and OCR, `rag` handles local retrieval, and `course_generator` handles AI JSON generation and parsing. Storage owns the new document/course tables and import operations; the app gets a new `资料知识库` page and training prompts can include retrieved source context.

**Tech Stack:** Python 3, Streamlit, SQLite, pypdf, Pillow, pytesseract, scikit-learn, requests, pytest.

---

## File Structure

- Modify `requirements.txt`: add OCR, PDF, and TF-IDF dependencies.
- Modify `services/storage.py`: add document, chunk, course, lesson, and RAG query tables plus CRUD helpers.
- Create `services/document_processor.py`: extract TXT/Markdown/PDF/image text and split text into chunks.
- Create `services/rag.py`: build a local TF-IDF index from SQLite chunks and return relevant snippets.
- Create `services/course_generator.py`: build course-generation prompts, parse model JSON, and save generated courses.
- Modify `services/prompts.py`: append optional RAG source context to training prompts.
- Modify `app.py`: add `资料知识库` page and inject source snippets into training prompt construction.
- Modify `README.md`: document OCR/RAG setup and Tesseract note.
- Create `tests/test_document_processor.py`: text extraction, OCR error, and chunking tests.
- Create `tests/test_rag.py`: retrieval ranking tests.
- Create `tests/test_course_generator.py`: JSON parsing and prompt construction tests.
- Modify `tests/test_storage.py`: new table and import tests.
- Modify `tests/test_prompts.py`: RAG context inclusion test.
- Modify `tests/test_app_smoke.py`: page registration test for `资料知识库`.

---

### Task 1: Dependencies and Storage Schema

- [ ] Write failing storage tests for creating a document, replacing chunks, saving courses/lessons, and importing a lesson into `weak_points`.
- [ ] Run `python -m pytest tests/test_storage.py -q`; expected failure: missing storage methods and tables.
- [ ] Add dependencies to `requirements.txt`: `pypdf>=5.0`, `pillow>=10.0`, `pytesseract>=0.3.13`, `scikit-learn>=1.5`.
- [ ] Extend `Storage.__init__` with `documents_dir`.
- [ ] Add SQLite tables: `documents`, `document_chunks`, `generated_courses`, `course_lessons`, `rag_queries`.
- [ ] Add storage methods:
  - `save_document_upload(uploaded_file) -> str`
  - `create_document(payload) -> int`
  - `update_document_processing(document_id, text_content, status, error_message='')`
  - `list_documents() -> list[dict]`
  - `get_document(document_id) -> dict`
  - `replace_document_chunks(document_id, chunks) -> None`
  - `list_document_chunks(document_id=None) -> list[dict]`
  - `create_rag_query(query, chunk_ids) -> int`
  - `create_course(title, source_document_id, raw_json, lessons) -> int`
  - `list_courses() -> list[dict]`
  - `list_course_lessons(course_id) -> list[dict]`
  - `mark_lesson_imported(lesson_id, weak_point_id) -> None`
  - `import_lesson_as_weak_point(lesson_id, subject) -> int`
- [ ] Run `python -m pytest tests/test_storage.py -q`; expected result: pass.
- [ ] Commit with `git commit -m "feat: add document and course storage"`.

### Task 2: Document Processor

- [ ] Write failing tests for TXT extraction, Markdown extraction, chunking, and image OCR unavailable handling.
- [ ] Run `python -m pytest tests/test_document_processor.py -q`; expected failure: module missing.
- [ ] Implement `services/document_processor.py` with:
  - `OCRUnavailableError`
  - `UnsupportedDocumentError`
  - `extract_text_from_file(path) -> str`
  - `extract_pdf_text(path) -> str`
  - `extract_image_text(path) -> str`
  - `chunk_text(text, max_chars=900, overlap=120) -> list[str]`
  - `process_document_file(path) -> tuple[str, list[str], str]`
- [ ] Run `python -m pytest tests/test_document_processor.py -q`; expected result: pass.
- [ ] Commit with `git commit -m "feat: add document extraction and OCR"`.

### Task 3: Local RAG Retrieval

- [ ] Write failing tests proving query terms rank the most relevant chunk first and empty inputs return an empty list.
- [ ] Run `python -m pytest tests/test_rag.py -q`; expected failure: module missing.
- [ ] Implement `services/rag.py` with char n-gram TF-IDF retrieval:
  - `search_chunks(query, chunks, top_k=5) -> list[dict]`
  - `format_rag_context(results, max_chars=2400) -> str`
- [ ] Run `python -m pytest tests/test_rag.py -q`; expected result: pass.
- [ ] Commit with `git commit -m "feat: add local RAG retrieval"`.

### Task 4: Course Generation Service

- [ ] Write failing tests for parsing plain JSON, parsing fenced JSON, building prompts with source context, and saving generated course lessons.
- [ ] Run `python -m pytest tests/test_course_generator.py -q`; expected failure: module missing.
- [ ] Implement `services/course_generator.py` with:
  - `CourseGenerationError`
  - `build_course_prompt(source_context, course_goal, days) -> list[dict[str, str]]`
  - `parse_course_json(content) -> dict`
  - `normalize_lessons(course) -> list[dict]`
  - `generate_course(ai_client, source_context, course_goal, days) -> dict`
- [ ] Run `python -m pytest tests/test_course_generator.py -q`; expected result: pass.
- [ ] Commit with `git commit -m "feat: add AI course generation service"`.

### Task 5: Prompt RAG Context

- [ ] Add a failing test that `build_training_prompt(..., source_context='...')` includes source snippets.
- [ ] Run `python -m pytest tests/test_prompts.py -q`; expected failure: unexpected parameter.
- [ ] Update `build_training_prompt` signature with `source_context: str = ""` and add a `【资料原文片段】` section when non-empty.
- [ ] Run `python -m pytest tests/test_prompts.py -q`; expected result: pass.
- [ ] Commit with `git commit -m "feat: include RAG context in training prompts"`.

### Task 6: Streamlit Integration

- [ ] Add failing App smoke test expecting `资料知识库` in `PAGES`.
- [ ] Run `python -m pytest tests/test_app_smoke.py -q`; expected failure: page missing.
- [ ] Modify `app.py`:
  - Add `资料知识库` to `PAGES`.
  - Add `page_knowledge_base(store)`.
  - Add document upload/extract/index UI.
  - Add RAG search UI.
  - Add AI course-generation UI.
  - Add generated course display and lesson import buttons.
  - In `page_training`, retrieve RAG snippets for selected weak point and pass them to `build_training_prompt`.
- [ ] Run `python -m pytest tests/test_app_smoke.py -q`; expected result: pass.
- [ ] Commit with `git commit -m "feat: add knowledge base Streamlit workflow"`.

### Task 7: Documentation and Verification

- [ ] Update `README.md` with OCR/RAG setup, supported file types, and Tesseract installation note.
- [ ] Run `python -m pip install -r requirements.txt`.
- [ ] Run `python -m pytest -q`; expected result: all tests pass.
- [ ] Run `python -m py_compile app.py services/storage.py services/prompts.py services/analysis.py services/ai_client.py services/document_processor.py services/rag.py services/course_generator.py prompts/seed_templates.py`; expected result: exit 0.
- [ ] Verify `http://localhost:8501/` returns status 200.
- [ ] Run a Chrome headless smoke check for `资料知识库`, upload-free empty state, and existing pages.
- [ ] Commit with `git commit -m "docs: document OCR RAG workflow"`.

## Self-Review Checklist

- Spec coverage: document upload, OCR, PDF/text extraction, local RAG, course generation, course persistence, lesson import, and training prompt grounding are covered.
- Scope control: advanced PaddleOCR, persistent vector DB, cloud OCR, and embedding APIs are not required for first completion.
- Type consistency: all new service functions pass dictionaries/lists compatible with current storage and Streamlit code.
- Verification: each service has tests, app registration has smoke tests, and final verification includes tests, compile, HTTP, and browser checks.
