CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_migrations (version, name, applied_at)
VALUES (1, 'baseline_existing_schema', datetime('now'));

