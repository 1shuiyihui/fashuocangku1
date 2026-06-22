# Cloud Persistence v0.7 Design

## Problem

Streamlit Community Cloud restores the application from GitHub on restart or redeploy. The current app writes study records, uploaded files, extracted document text, generated courses, and session messages to local `data/` files inside the runtime. That runtime storage is not durable, so records can disappear after a restart. The sidebar API key is also held only in `st.session_state`, so it is lost between sessions.

## Goal

Add a small durable persistence layer for the current 1-2 user deployment without introducing a separate database service. The app should restore a GitHub-hosted private snapshot before database initialization and upload a fresh snapshot after writes.

## Non-Goals

- No database schema change.
- No migration to PostgreSQL or Supabase in this version.
- No public data export.
- No API keys or access tokens committed to Git.

## Architecture

- `services/cloud_sync.py` owns cloud snapshot configuration, zip archive creation, archive restore, and GitHub Contents API calls.
- `Storage` accepts an optional `after_write` callback. It calls this callback only after a connection committed real SQLite changes.
- `app.get_storage()` loads persistence config from Streamlit secrets, restores the snapshot before `init_db()`, and installs the upload callback.
- The default snapshot branch is `cloud-data`, separate from the deployed code branch, to avoid a redeploy loop when user data changes.

## Snapshot Contents

The snapshot archive contains:

- `fashuo.db`
- `uploads/**`
- `documents/**`
- `manifest.json`

The archive excludes SQLite WAL/SHM files, logs, backups, caches, `.env`, and Streamlit secrets.

## Streamlit Secrets

```toml
[ai]
api_base = "https://api.deepseek.com"
model = "deepseek-v4-pro"
api_key = "replace-with-deepseek-key"

[persistence]
enabled = true
provider = "github"
repo = "1shuiyihui/fashuocangku1"
branch = "cloud-data"
source_branch = "codex/fashuo-socratic-local-tool"
snapshot_path = "fashuo-cloud-snapshot.zip"
github_token = "replace-with-github-token"
```

## Failure Behavior

- If persistence is disabled, the app keeps using local runtime storage.
- If persistence is enabled but required config is missing, startup stops with a clear error.
- If remote snapshot is missing, startup continues with the local data snapshot and the first write creates the remote snapshot.
- If restore fails, startup stops instead of writing an empty local database over the remote snapshot.
- If upload fails after a write, the local write remains committed and the UI reports the sync error.

## Data Impact

No schema migration is required. Existing local `data/fashuo.db`, `data/uploads/`, and `data/documents/` are not deleted or moved by this update. Existing Streamlit Cloud runtime data that was already lost by reboot cannot be recovered unless an older backup or snapshot exists.
