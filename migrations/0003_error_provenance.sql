CREATE TABLE IF NOT EXISTS error_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    weak_point_id INTEGER NOT NULL,
    error_location TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    evidence TEXT NOT NULL DEFAULT '',
    review_drill TEXT NOT NULL DEFAULT '',
    variant_drill TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(weak_point_id) REFERENCES weak_points(id)
);

CREATE TABLE IF NOT EXISTS provenance_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    event_type TEXT NOT NULL,
    input_path TEXT NOT NULL,
    output_path TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_error_analyses_weak_point_id
    ON error_analyses(weak_point_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_error_analyses_root_cause
    ON error_analyses(root_cause);
CREATE INDEX IF NOT EXISTS idx_provenance_events_entity
    ON provenance_events(entity_type, entity_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_provenance_events_type
    ON provenance_events(event_type, created_at DESC);

INSERT OR IGNORE INTO schema_migrations (version, name, applied_at)
VALUES (3, 'error_provenance', datetime('now'));
