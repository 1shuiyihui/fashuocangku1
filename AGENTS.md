# Project Update Guardrails

These rules apply to every future project update in this repository.

## Mandatory First Step

Before changing code, dependencies, database schema, data directories, OCR/RAG behavior, or Streamlit workflows:

1. Read this file.
2. Read `docs/SYSTEM_UPDATE_RULES.md`.
3. Check `git status --short`.
4. Identify whether the change can affect persisted user data.

## Data Safety Rules

- Treat `data/fashuo.db`, `data/uploads/`, and `data/documents/` as user data.
- Never delete, overwrite, move, or reset user data unless the user explicitly asks for it.
- Before any data-affecting change, create a backup plan and document it in the update notes.
- Schema changes must use versioned migrations. Do not silently rebuild tables in a way that can drop data.
- New code must be able to refuse startup if the database schema is newer than the app supports.
- All text extraction and file reads must preserve Chinese text. Prefer UTF-8, then UTF-8 with BOM, then GB18030 fallback for user-uploaded text files.

## Verification Rules

Every project update must finish with:

- `python -m pytest -q`
- `python -m py_compile app.py services/storage.py services/prompts.py services/analysis.py services/ai_client.py services/document_processor.py services/rag.py services/course_generator.py services/backup.py services/migrations.py services/versioning.py prompts/seed_templates.py`
- HTTP check for `http://localhost:8501/` when the app is running
- A short note stating whether user data was touched, migrated, backed up, or left untouched

## Git Rules

- Work on a `codex/` branch unless the user explicitly says otherwise.
- Commit update-rule, migration, and implementation changes separately when practical.
- Do not use destructive git commands such as `git reset --hard` or `git checkout --` to clean user changes.
- For this private GitHub repository, `data/fashuo.db`, `data/uploads/`, and `data/documents/` may be versioned as the owner's approved full-project snapshot.
- Never commit `.env`, API keys, access tokens, `backups/`, `logs/`, Python caches, or virtual environments.
- If the repository will be made public, create a scrubbed branch or export package with sample data instead of real study data.
