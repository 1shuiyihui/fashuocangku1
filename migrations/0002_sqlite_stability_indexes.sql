CREATE INDEX IF NOT EXISTS idx_weak_points_created_at
    ON weak_points(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_weak_points_subject
    ON weak_points(subject);
CREATE INDEX IF NOT EXISTS idx_sessions_status_started_at
    ON sessions(status, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_weak_point_id
    ON sessions(weak_point_id);
CREATE INDEX IF NOT EXISTS idx_messages_session_id
    ON messages(session_id, id);
CREATE INDEX IF NOT EXISTS idx_documents_status_created_at
    ON documents(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id
    ON document_chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_course_lessons_course_id
    ON course_lessons(course_id, lesson_index);

INSERT OR IGNORE INTO schema_migrations (version, name, applied_at)
VALUES (2, 'sqlite_stability_indexes', datetime('now'));
